import sys
import os
import time

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
import bittensor as bt
from typing import List

from app.constants import ROUND_TABLE_HOTKEY
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger


WALLET_NAMES: List[str] = ["soon", "soon_2"]
DELEGATORS: List[str] = ["5CsiGTsNBAn1bNiGNEd5LYpo6bm3PXT5ogPrQmvpZaUb2XzZ", "5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7"]

if __name__ == '__main__':
    subtensor = bt.Subtensor(network=settings.NETWORK)
    
    
    netuid = int(input("Enter the netuid: "))
    threshold = float(input("Enter the threshold: "))
    wallet_name = input("Enter the wallet name: ")
    delegator = DELEGATORS[WALLET_NAMES.index(wallet_name)]
    dest_hotkey = input("Enter the dest hotkey (default is Round table): ") or ROUND_TABLE_HOTKEY

    proxy = Proxy(network=settings.NETWORK)
    proxy.init_runtime()
    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()

    amount_balance = subtensor.get_stake(
        coldkey_ss58=delegator,
        hotkey_ss58=dest_hotkey,
        netuid=netuid
    )

    print("Press Ctrl+C to stop the script")
    print(f"Wallet: {wallet_name}, Delegator: {delegator}, Dest Hotkey: {dest_hotkey}, Amount: {amount_balance.tao}")

    time.sleep(10)
    while True:
        try:
            subnet = subtensor.subnet(netuid=netuid)
            if subnet is None:
                logger.error(f"Subnet is None for netuid: {netuid}")
                continue

            amount_balance = subtensor.get_stake(
                coldkey_ss58=delegator,
                hotkey_ss58=dest_hotkey,
                netuid=netuid
            )

            if amount_balance is None:
                logger.error(f"Amount balance is None for netuid: {netuid}")
                continue
            
            alpha_price = subnet.alpha_to_tao(1)
            logger.info(f"Current alpha token price: {alpha_price} TAO")
            
            if threshold != -1 and alpha_price < bt.Balance.from_tao(threshold):
                logger.info(f"Current price {alpha_price} TAO is below threshold {threshold} TAO. Skipping...")
                continue
            
            success, msg = proxy.remove_stake_not_limit(
                proxy_wallet=wallet,
                delegator=delegator,
                netuid=netuid,
                hotkey=dest_hotkey,
                amount=amount_balance,
                use_era=True,
            )
            if success:
                break
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
        