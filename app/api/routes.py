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
    allow_partial: bool = False,
    retries: int = settings.DEFAULT_RETRIES,
    use_era: bool = settings.USE_ERA,
    username: str = Depends(get_current_username)
):
    # Validate retries parameter
    if retries < 1:
        retries = 1    

    if rate_tolerance > 1.9:
        return stake_service.stake_not_limit(
            tao_amount=tao_amount,
            netuid=netuid,
            wallet_name=wallet_name,
            dest_hotkey=dest_hotkey,
            retries=retries,
            use_era=use_era
        )
    
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
        allow_partial=allow_partial,
        retries=retries,
        use_era=use_era
    )


@router.get("/unstake")
def unstake(
    netuid: int,
    wallet_name: str,
    amount: Optional[float] = None,
    dest_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
    rate_tolerance: float = settings.DEFAULT_RATE_TOLERANCE,
    min_tolerance_unstaking: bool = settings.DEFAULT_MIN_TOLERANCE,
    allow_partial: bool = False,
    retries: int = settings.DEFAULT_RETRIES,
    use_era: bool = settings.USE_ERA,
    username: str = Depends(get_current_username)
):
    # Validate retries parameter
    if retries < 1:
        retries = 1    
    
    if rate_tolerance > 1.9:
        return stake_service.unstake_not_limit(
            netuid=netuid,
            wallet_name=wallet_name,
            amount=amount,
            dest_hotkey=dest_hotkey,
            retries=retries,
            use_era=use_era
        )
    
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
        allow_partial=allow_partial,
        retries=retries,
        use_era=use_era
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
    use_era: bool = settings.USE_ERA,
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
        retries=retries,
        use_era=use_era
    )

