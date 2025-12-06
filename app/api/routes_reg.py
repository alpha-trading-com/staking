import bittensor as bt
from bittensor_cli.src.bittensor.utils import get_hotkey_wallets_for_wallet
from app.services.reg import get_hotkeys
from fastapi import APIRouter

router = APIRouter()

@router.get("/wallet_list")
def wallet_list(wallet_name: str):
    hotkeys = get_hotkeys(wallet_name)
    return hotkeys