import bittensor as bt
from typing import Optional
from fastapi import APIRouter, Depends
from app.constants import ROUND_TABLE_HOTKEY, NETWORK
from app.services.stake import stake_service
from app.services.auth import get_current_username
from app.services.wallets import wallets
from app.core.config import settings


router = APIRouter()

@router.get("/min_stake_tolerance")
def min_stake_tolerance(
    tao_amount: float,
    netuid: int,
):
    min_tol = stake_service.get_stake_min_tolerance(tao_amount, netuid)
    return {"min_tolerance": min_tol}


@router.get("/min_unstake_tolerance")
def min_unstake_tolerance(
    tao_amount: float,
    netuid: int,
):
    min_tol = stake_service.get_unstake_min_tolerance(tao_amount, netuid)
    return {"min_tolerance": min_tol}
    

@router.get("/stake")
def stake(
    tao_amount: float,
    netuid: int,
    wallet_name: str,
    dest_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
    rate_tolerance: float = settings.DEFAULT_RATE_TOLERANCE,
    min_tolerance_staking: bool = settings.DEFAULT_MIN_TOLERANCE,
    retries: int = settings.DEFAULT_RETRIES,
    username: str = Depends(get_current_username)
):
    # Validate retries parameter
    if retries < 1:
        retries = 1    
    
    # Get wallet and delegator
    if wallet_name not in stake_service.wallets:
        return {
            "success": False,
            "error": f"Wallet '{wallet_name}' not found"
        }

    return stake_service.stake(
        tao_amount=tao_amount,
        netuid=netuid,
        wallet_name=wallet_name,
        dest_hotkey=dest_hotkey,
        rate_tolerance=rate_tolerance,
        min_tolerance_staking=min_tolerance_staking,
        retries=retries
    )


@router.get("/unstake")
def unstake(
    netuid: int,
    wallet_name: str,
    amount: Optional[float] = None,
    dest_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
    rate_tolerance: float = settings.DEFAULT_RATE_TOLERANCE,
    min_tolerance_unstaking: bool = settings.DEFAULT_MIN_TOLERANCE,
    retries: int = settings.DEFAULT_RETRIES,
    username: str = Depends(get_current_username)
):
    # Validate retries parameter
    if retries < 1:
        retries = 1    
    
    # Get wallet and delegator
    if wallet_name not in stake_service.wallets:
        return {
            "success": False,
            "error": f"Wallet '{wallet_name}' not found"
        }

    return stake_service.unstake(
        netuid=netuid,
        wallet_name=wallet_name,
        amount=amount,
        dest_hotkey=dest_hotkey,
        rate_tolerance=rate_tolerance,
        min_tolerance_unstaking=min_tolerance_unstaking,
        retries=retries
    )

@router.get("/move_stake")
def move_stake(
    wallet_name: str,
    origin_netuid: int, 
    destination_netuid: int,
    amount: Optional[float] = None,
    origin_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
    destination_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
    retries: int = settings.DEFAULT_RETRIES,
    username: str = Depends(get_current_username)
):
    # Validate retries parameter
    if retries < 1:
        retries = 1    
        
    return stake_service.move_stake(
        amount=amount,
        wallet_name=wallet_name,
        origin_hotkey=origin_hotkey,
        destination_hotkey=destination_hotkey,
        origin_netuid=origin_netuid,
        destination_netuid=destination_netuid,
        retries=retries
    )


archive_subtensor = bt.Subtensor("archive")
@router.get("/subnets_data")
def get_subnets_data(
    period_minutes: int = 60,
):
    """
    Get all subnets with their price data for bubble visualization
    Includes historical price changes based on the specified period
    """
    try:
        
        # Get current subnet data
        current_block = archive_subtensor.get_current_block()
        current_subnet_infos = archive_subtensor.all_subnets()
        
        # Calculate historical block (assuming 12 second block time)
        blocks_per_minute = 5  # 60 seconds / 12 seconds per block
        blocks_ago = period_minutes * blocks_per_minute
        historical_block = max(0, current_block - blocks_ago)
        
        # Get historical subnet data using all_subnets at historical block
        historical_prices = {}
        historical_subnet_infos = archive_subtensor.all_subnets(block=historical_block)
        for netuid, subnet_info in enumerate(historical_subnet_infos):
            if subnet_info and hasattr(subnet_info, 'price'):
                historical_prices[netuid] = float(subnet_info.price.tao)                        
      
        # Build subnet list with price changes
        subnets = []
        for netuid, subnet_info in enumerate(current_subnet_infos):
            if subnet_info:
                current_price = float(subnet_info.price.tao) if hasattr(subnet_info, 'price') else 0.0
                
                # Calculate price change
                price_change = 0.0
                if netuid in historical_prices and historical_prices[netuid] > 0:
                    price_change = ((current_price - historical_prices[netuid]) / historical_prices[netuid]) * 100
                
                subnets.append({
                    "netuid": netuid,
                    "name": subnet_info.subnet_name if hasattr(subnet_info, 'subnet_name') else f"Subnet {netuid}",
                    "price": current_price,
                    "tao_in": float(subnet_info.tao_in.tao) if hasattr(subnet_info, 'tao_in') else 0.0,
                    "alpha_in": float(subnet_info.alpha_in.tao) if hasattr(subnet_info, 'alpha_in') else 0.0,
                    "is_dynamic": subnet_info.is_dynamic if hasattr(subnet_info, 'is_dynamic') else False,
                    "price_change": price_change,
                    "historical_price": historical_prices.get(netuid, 0.0)
                })
        
        return {
            "success": True,
            "subnets": subnets,
            "current_block": current_block,
            "historical_block": historical_block,
            "period_minutes": period_minutes
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

