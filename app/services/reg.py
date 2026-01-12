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
    wallets = get_hotkey_wallets_for_wallet(bt.Wallet(name=wallet_name))
    import re

    def extract_number(hotkey_name):
        match = re.match(r"hk(\d+)", hotkey_name)
        if match:
            return int(match.group(1))
        return float('inf')  # put any that don't match at the end

    hotkeys = [
        {
            "name": wallet.hotkey_str,
            "ss58_address": wallet.hotkey.ss58_address,
            "mnemonic": get_mnemonic(wallet)
        } for wallet in wallets
        if wallet.hotkey.ss58_address is not None
    ]
    hotkeys.sort(key=lambda hk: extract_number(hk["name"]))
    return hotkeys
