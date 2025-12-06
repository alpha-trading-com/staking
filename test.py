import bittensor as bt
from bittensor_cli.src.bittensor.utils import get_hotkey_wallets_for_wallet

if __name__ == "__main__":
    wallets = get_hotkey_wallets_for_wallet(bt.wallet(name="tck"))
    print(wallets)
    wallet = wallets[0]
    
    hotkey_file = wallet.hotkey_file
    print(hotkey_file)
    with open(hotkey_file.path, "r") as f:
        content = f.read()
    print(content)
    # content is in JSON format; extract mnemonic directly
    # The mnemonic is likely under a key such as "mnemonic" in the JSON
    import json
    try:
        data = json.loads(content)
        mnemonic = data.get("secretPhrase", None)
        if mnemonic:
            print("Mnemonic words:", mnemonic)
        else:
            print("Mnemonic words not found in the file.")
    except Exception as e:
        print("Could not parse JSON or find mnemonic:", e)
    hotkeys = [
        {
            "name": wallet.hotkey_str,
            "ss58_address": wallet.hotkey.ss58_address,
        } for wallet in wallets
        if wallet.hotkey.ss58_address is not None
    ]
    print(hotkeys)