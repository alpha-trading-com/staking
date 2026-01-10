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


@router.get("/subnets_data")
def get_subnets_data(
    username: str = Depends(get_current_username)
):
    """
    Get all subnets with their price data for bubble visualization
    """
    try:
        subtensor = stake_service.subtensor
        subnet_infos = subtensor.all_subnets()
        
        subnets = []
        for netuid, subnet_info in enumerate(subnet_infos):
            if subnet_info:
                subnets.append({
                    "netuid": netuid,
                    "name": subnet_info.subnet_name if hasattr(subnet_info, 'subnet_name') else f"Subnet {netuid}",
                    "price": float(subnet_info.price.tao) if hasattr(subnet_info, 'price') else 0.0,
                    "tao_in": float(subnet_info.tao_in.tao) if hasattr(subnet_info, 'tao_in') else 0.0,
                    "alpha_in": float(subnet_info.alpha_in.tao) if hasattr(subnet_info, 'alpha_in') else 0.0,
                    "is_dynamic": subnet_info.is_dynamic if hasattr(subnet_info, 'is_dynamic') else False
                })
        
        return {
            "success": True,
            "subnets": subnets
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

