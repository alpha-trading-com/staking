import json
import bittensor as bt
from bittensor_cli.src.bittensor.utils import get_hotkey_wallets_for_wallet


def get_mnemonic(wallet):
    hotkey_file = wallet.hotkey_file
    with open(hotkey_file.path, "r") as f:
        content = f.read()  
    data = json.loads(content)
    return data.get("secretPhrase", None)


def get_hotkeys(wallet_name: str):
    wallets = get_hotkey_wallets_for_wallet(bt.wallet(name=wallet_name))
    hotkeys = [
        {
            "name": wallet.hotkey_str,
            "ss58_address": wallet.hotkey.ss58_address,
            "mnemonic": get_mnemonic(wallet)
        } for wallet in wallets
        if wallet.hotkey.ss58_address is not None
    ]
    return hotkeys
