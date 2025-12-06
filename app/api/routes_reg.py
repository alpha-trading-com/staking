import bittensor as bt
from bittensor_cli.src.bittensor.utils import get_hotkey_wallets_for_wallet
from app.services.reg import get_hotkeys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.constants import ROUND_TABLE_HOTKEY, NETWORK
from app.services.stake import stake_service
from app.services.auth import get_current_username
from app.services.wallets import wallets
from app.core.config import settings



router = APIRouter()


class RegisterRequest(BaseModel):
    hotkey: str
    wallet_name: str
    subnet_id: int
    delegator: Optional[str] = None


@router.get("/wallet_list")
def wallet_list(wallet_name: str):
    hotkeys = get_hotkeys(wallet_name)
    return hotkeys


@router.post("/register")
def register(request: RegisterRequest):
    success, message = stake_service.burned_register(
        wallet_name=request.wallet_name,
        hotkey=request.hotkey,
        netuid=request.subnet_id
    )
    return {
        "success": success,
        "message": message
    }