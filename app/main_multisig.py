import fastapi
import bittensor as bt
import subprocess
import requests
from fastapi import Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.core.config import settings, save_tolerance_offset
from app.constants import NETWORK
from app.services.wallets import wallets
from app.services.stake import stake_service
from app.services.auth import get_current_username
from utils.stake_list import get_stake_list
from utils.stake_list_v2 import get_stake_list_v2
from utils.subnet_history import get_subnet_history


app = fastapi.FastAPI()
app.include_router(router)


templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def read_root(request: fastapi.Request, username: str = Depends(get_current_username)):
    subtensor = stake_service.subtensor
    def get_balance_html():
        balance_html = ""
        for wallet_name in settings.WALLET_NAMES:
            _, delegator = wallets[wallet_name]
            balance = subtensor.get_balance(delegator)
            balance_html += f"""
                <div class="balance-container">
                    <div class="balance-title"><a target="_blank" href="/stake_list_v3?wallet_name={delegator}" style="text-decoration: none; color: inherit; cursor: pointer; text-decoration: underline;">{wallet_name}</a></div>
                    <div class="balance-amount">{balance} TAO</div>
                </div>
            """
        return balance_html

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request, 
            "balance_html": get_balance_html(), 
            "wallet_names": settings.WALLET_NAMES,
            "delegators": settings.DELEGATORS,
        }
    )



@app.get("/stake_list")
def stake_list(wallet_name: str):
    result = subprocess.run(["btcli", "stake", "list", "--name", wallet_name, "--no-prompt"], capture_output=True, text=True)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{wallet_name} | Stake List</title>
    </head>
    <body>
        <pre>{result.stdout}</pre>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/stake_list_v2")
def stake_list_v2(wallet_name: str):
    subtensor = stake_service.subtensor
    stake_list = get_stake_list(subtensor, wallet_name)
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


@app.get("/stake_list_v3")
def stake_list_v3(wallet_name: str):
    subtensor = stake_service.subtensor
    stake_list = get_stake_list_v2(subtensor, wallet_name)
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


@app.get("/subnets")
def subnets_page(request: fastapi.Request, username: str = Depends(get_current_username)):
    return templates.TemplateResponse(
        "subnets_bubble.html",
        {"request": request}
    )

@app.get("/subnets_data")
def subnets_data(
    period_minutes: int = Query(..., description="Time period in minutes to look back"),
    username: str = Depends(get_current_username)
):
    """
    Fetch historical subnet data from Taostats API.
    Returns subnet price changes over the specified time period.
    """
    try:
        # Get current block from subtensor
        subtensor = stake_service.subtensor
        current_block = subtensor.get_current_block()
        
        # Calculate historical block (approximately 12 seconds per block, so ~5 blocks per minute)
        blocks_per_minute = 5
        blocks_back = period_minutes * blocks_per_minute
        historical_block = max(1, current_block - blocks_back)
        
        # Fetch historical subnet data from Taostats API
        historical_subnets = get_subnet_history(historical_block)
        current_subnets = subtensor.all_subnets()

        # Convert lists to dicts for faster lookup by netuid
        historical_dict = {sub['netuid']: sub for sub in historical_subnets}
        current_dict = {sub.netuid: sub for sub in current_subnets}

        subnets = []
        for netuid, current_subnet in current_dict.items():
            historical_subnet = historical_dict.get(netuid)
            if historical_subnet is None:
                # subnet didn't exist at historical_block (or not found)
                continue
            
            # Get prices
            price_then = float(historical_subnet.get("price", 0) or 0)
            price_now = float(current_subnet.price.tao if hasattr(current_subnet.price, 'tao') else current_subnet.price)
            
            # Calculate price change percentage
            if price_then > 0:
                price_change = ((price_now - price_then) / price_then) * 100
            else:
                price_change = 0.0
            
            # Build subnet object with all required fields
            subnet_obj = {
                "netuid": netuid,
                "name": current_subnet.subnet_name if hasattr(current_subnet, 'subnet_name') else f'Subnet {netuid}',
                "price": price_now,
                "price_change": price_change,
            }
            
            # Add additional fields if available
            if hasattr(current_subnet, 'tao_in'):
                subnet_obj["tao_in"] = float(current_subnet.tao_in.tao if hasattr(current_subnet.tao_in, 'tao') else current_subnet.tao_in)
            else:
                subnet_obj["tao_in"] = 0.0
            
            if hasattr(current_subnet, 'alpha_in'):
                subnet_obj["alpha_in"] = float(current_subnet.alpha_in.tao if hasattr(current_subnet.alpha_in, 'tao') else current_subnet.alpha_in)
            else:
                subnet_obj["alpha_in"] = 0.0
            
            # Check if subnet is dynamic (has liquid_alpha_enabled or similar)
            subnet_obj["is_dynamic"] = getattr(current_subnet, 'liquid_alpha_enabled', False)
            
            subnets.append(subnet_obj)

        return JSONResponse(content={
            "success": True,
            "subnets": subnets,
            "current_block": current_block,
            "historical_block": historical_block,
            "period_minutes": period_minutes
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "details": str(e)
            }
        )
    


@app.get("/settings/tolerance_offset")
def get_tolerance_offset(username: str = Depends(get_current_username)):
    return {"tolerance_offset": settings.TOLERANCE_OFFSET}

@app.post("/settings/tolerance_offset")
def set_tolerance_offset(request: fastapi.Request, username: str = Depends(get_current_username)):
    tolerance_offset = request.query_params.get("tolerance_offset")
    if tolerance_offset is None:
        return {"error": "Tolerance offset is required"}
    # Allow both float and string values (e.g., "*1.1" for multiplication)
    tolerance_offset = tolerance_offset.strip()
    if tolerance_offset.startswith('*'):
        # Keep as string for multiplication mode
        settings.TOLERANCE_OFFSET = tolerance_offset
    else:
        # Convert to float for addition mode
        try:
            settings.TOLERANCE_OFFSET = float(tolerance_offset)
        except ValueError:
            return {"error": "Tolerance offset must be a valid number or multiplication (e.g., '*1.1')"}
    
    # Save to file for persistence
    save_tolerance_offset(settings.TOLERANCE_OFFSET)
    return {"success": True}
