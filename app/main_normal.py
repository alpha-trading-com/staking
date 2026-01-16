import os
import fastapi
import bittensor as bt
import uvicorn
import subprocess
from typing import Dict, Optional
from fastapi import Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv


from app.core.config import settings
from app.services.auth import get_current_username
from app.constants import ROUND_TABLE_HOTKEY, NETWORK
from utils.tolerance import get_stake_min_tolerance, get_unstake_min_tolerance
from utils.stake_list_v2 import get_stake_list_v2

app = fastapi.FastAPI()

# Set up templates
templates = Jinja2Templates(directory="app/templates")

wallet_names = ["soon"]
wallets: Dict[str, bt.Wallet] = {}

def unlock_wallets():
    for wallet_name in wallet_names:
        wallet = bt.Wallet(name=wallet_name)
        print(f"Unlocking wallet {wallet_name}")
        retries = 3
        for _ in range(retries):
            try:
                wallet.unlock_coldkey()
                break
            except Exception as e:
                print(f"Error unlocking wallet {wallet_name}: {e}")
                continue
        wallets[wallet_name] = wallet


unlock_wallets()

@app.get("/")
def read_root(request: fastapi.Request, username: str = Depends(get_current_username)):
    try:
        subtensor = bt.Subtensor(network=NETWORK)
        def get_balance_html():
            balance_html = ""
            for wallet_name in wallet_names:
                wallet = wallets[wallet_name]
                balance = subtensor.get_balance(wallet.coldkey.ss58_address)
                balance_html += f"""
                    <div class="balance-container">
                        <div class="balance-title"><a target="_blank" href="/stake_list_v3?wallet_name={wallet_name}" style="text-decoration: none; color: inherit; cursor: pointer; text-decoration: underline;">{wallet_name}</a></div>
                        <div class="balance-amount">{balance} TAO</div>
                    </div>
                """
            return balance_html

        return templates.TemplateResponse(
            "index.html",
            {"request": request, "balance_html": get_balance_html(), "wallet_names": wallet_names}
        )
    except Exception as e:
        print(e)



@app.get("/min_stake_tolerance")
def min_stake_tolerance(
    tao_amount: float,
    netuid: int,
):
    """Calculate minimum stake tolerance for a given TAO amount and netuid"""
    try:
        subtensor = bt.Subtensor(network=NETWORK)
        min_tol = get_stake_min_tolerance(tao_amount, netuid, subtensor)
        return {"min_tolerance": min_tol}
    except Exception as e:
        return {"error": str(e), "min_tolerance": 0.0}


@app.get("/min_unstake_tolerance")
def min_unstake_tolerance(
    tao_amount: float,
    netuid: int,
):
    """Calculate minimum unstake tolerance for a given TAO amount and netuid"""
    try:
        subtensor = bt.Subtensor(network=NETWORK)
        min_tol = get_unstake_min_tolerance(tao_amount, netuid, subtensor)
        return {"min_tolerance": min_tol}
    except Exception as e:
        return {"error": str(e), "min_tolerance": 0.0}


@app.get("/stake")
def stake(
    tao_amount: float, 
    netuid: int, 
    wallet_name: str, 
    dest_hotkey: str = ROUND_TABLE_HOTKEY, 
    rate_tolerance: float = 0.005,
    min_tolerance_staking: bool = True,
    allow_partial: bool = False,
    use_era: bool = False,
    retries: int = 1,
    username: str = Depends(get_current_username)
):
    if retries < 1:
        retries = 1
    result = None
    wallet = wallets[wallet_name]
    subtensor = bt.Subtensor(network=NETWORK)

    # Calculate rate tolerance if min_tolerance_staking is True
    if min_tolerance_staking:
        try:
            min_tol = get_stake_min_tolerance(tao_amount, netuid, subtensor)
            rate_tolerance = min_tol + 0.001
        except Exception as e:
            print(f"Error calculating min tolerance: {e}")
            # Continue with provided rate_tolerance
    
    while retries > 0:
        try:
            result = subtensor.add_stake(
                netuid=netuid,
                amount=bt.Balance.from_tao(tao_amount, netuid),
                wallet=wallet,
                hotkey_ss58=dest_hotkey,
                safe_staking=True,
                rate_tolerance=rate_tolerance,
                allow_partial_stake=allow_partial,
                period= 1 if use_era else 128,
            )
            if not result:
                raise Exception("Stake failed")
            
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            retries -= 1
            if retries == 0:
                return {
                    "success": False,
                    "error": str(e),
                    "result": result,
                }


@app.get("/unstake")
def unstake(
    netuid: int,
    wallet_name: str,
    amount: float = None,
    dest_hotkey: str = ROUND_TABLE_HOTKEY,
    rate_tolerance: float = 0.005,
    min_tolerance_unstaking: bool = True,
    allow_partial: bool = False,
    use_era: bool = False,
    retries: int = 1,
    username: str = Depends(get_current_username)
):
    if retries < 1:
        retries = 1
    result = None
    wallet = wallets[wallet_name]
    subtensor = bt.Subtensor(network=NETWORK)
    subnet = subtensor.subnet(netuid=netuid)

    if amount is None:
        amount = subtensor.get_stake(
            coldkey_ss58=wallet.coldkeypub.ss58_address,
            hotkey_ss58=dest_hotkey,
            netuid=netuid
        ) - bt.Balance.from_rao(1, netuid)
    else:
        if amount < 1:
            amount = subtensor.get_stake(
                coldkey_ss58=wallet.coldkeypub.ss58_address,
                hotkey_ss58=dest_hotkey,
                netuid=netuid
            ) * amount
        else:
            amount = bt.Balance.from_tao(amount , netuid)

    if min_tolerance_unstaking:
        try:
            min_tol = get_unstake_min_tolerance(amount.tao, netuid, subtensor)
            rate_tolerance = min_tol + 0.001
        except Exception as e:
            print(f"Error calculating min tolerance: {e}")
            # Continue with provided rate_tolerance
                    
    while retries > 0:
        try:
            result = subtensor.unstake(
                netuid=netuid, 
                wallet=wallet, 
                amount=amount,
                hotkey_ss58=dest_hotkey,
                safe_unstaking=True,
                rate_tolerance=rate_tolerance,
                allow_partial_stake=allow_partial,
                period= 1 if use_era else 128,
            )
            if not result:
                raise Exception("Unstake failed")
            
            return {
                "success": True,
                "result": result,
            }
        
        except Exception as e:
            retries -= 1
            if retries == 0:
                return {
                    "success": False,
                    "error": str(e),
                    "result": result,
                }


@app.get("/move_stake")
def move_stake(
    wallet_name: str,
    origin_netuid: int,
    destination_netuid: int,
    amount: Optional[float] = None,
    origin_hotkey: str = ROUND_TABLE_HOTKEY,
    destination_hotkey: str = ROUND_TABLE_HOTKEY,
    retries: int = 1,
    use_era: bool = False,
    username: str = Depends(get_current_username)
):
    """Move stake between validators on different subnets"""
    if retries < 1:
        retries = 1
    
    wallet = wallets.get(wallet_name)
    if not wallet:
        return {
            "success": False,
            "error": f"Wallet '{wallet_name}' not found"
        }
    
    subtensor = bt.Subtensor(network=NETWORK)
    
    # Get current stake amount
    if amount is None:
        amount_balance = subtensor.get_stake(
            coldkey_ss58=wallet.coldkeypub.ss58_address,
            hotkey_ss58=origin_hotkey,
            netuid=origin_netuid
        ) - bt.Balance.from_rao(1, origin_netuid)
    else:
        if amount < 1:
            amount_balance = subtensor.get_stake(
                coldkey_ss58=wallet.coldkeypub.ss58_address,
                hotkey_ss58=origin_hotkey,
                netuid=origin_netuid
            ) * amount
        else:
            amount_balance = bt.Balance.from_tao(amount , origin_netuid)
    
    result = None
    while retries > 0:
        try:
            result = subtensor.move_stake(
                wallet=wallet,
                origin_hotkey=origin_hotkey,
                destination_hotkey=destination_hotkey,
                origin_netuid=origin_netuid,
                destination_netuid=destination_netuid,
                amount=amount_balance,
                period= 1 if use_era else 128,
            )
            if not result:
                raise Exception("Move stake failed")
            
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            retries -= 1
            if retries == 0:
                return {
                    "success": False,
                    "error": str(e),
                    "result": result,
                }


@app.get("/stake_list_v3")
def stake_list_v3(wallet_name: str):
    """Display stake list for a wallet using get_stake_list_v2"""
    if wallet_name not in wallets:
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Wallet '{wallet_name}' not found</p></body></html>",
            status_code=404
        )
    
    wallet = wallets[wallet_name]
    subtensor = bt.Subtensor(network=NETWORK)
    coldkey_ss58 = wallet.coldkeypub.ss58_address
    stake_list = get_stake_list_v2(subtensor, coldkey_ss58)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{wallet_name} | Stake List</title>
    </head>
    <body>
        <pre>{stake_list}</pre>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)