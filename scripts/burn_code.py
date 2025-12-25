import sys
import os
import time

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt
import argparse
from utils.logger import logger


def set_weights_to_uid0(netuid: int, wallet_name: str, hotkey: str, weight_value: float = 1.0):
    """
    Set weights to UID 0 on the specified subnet.
    
    Args:
        netuid: The subnet ID
        wallet_name: Wallet name to use (defaults to first wallet in settings)
        weight_value: The weight value to set (default: 1.0)
    """
    
    # Initialize wallet and subtensor
    wallet = bt.wallet(name=wallet_name, hotkey=hotkey)
    subtensor = bt.subtensor(network="finney")
    
    
    # Get metagraph
    logger.info(f"Loading metagraph for netuid {netuid}")
    metagraph = subtensor.metagraph(netuid=netuid)
    metagraph.sync()
    
    # Check if wallet is registered
    if wallet.hotkey.ss58_address not in metagraph.hotkeys:
        logger.error(f"Wallet {wallet_name} (hotkey: {wallet.hotkey.ss58_address}) is not registered on netuid {netuid}")
        return False
    
    # Get the UID of the wallet
    my_uid = metagraph.hotkeys.index(wallet.hotkey.ss58_address)
    logger.info(f"Wallet UID: {my_uid}")
    
    # Check if UID 0 exists
    if len(metagraph.hotkeys) <= 0:
        logger.error(f"UID 0 does not exist on netuid {netuid}")
        return False
    
    # Create weight tensor: set weight to UID 0, zero for all others
    uids = [0]
    weights = [weight_value]
    
    logger.info(f"Setting weight {weight_value} to UID 0 on netuid {netuid}")
    
    while True:
        # Set weights
        try:
            success, error_message = subtensor.set_weights(
                wallet=wallet,
                netuid=netuid,
                uids=uids,
                weights=weights,
                wait_for_inclusion=True,
                wait_for_finalization=False
            )
            
            if success:
                logger.info(f"Successfully set weight {weight_value} to UID 0 on netuid {netuid}")
                time.sleep(1200) # 20 minutes
            else:
                logger.error(f"Failed to set weights: {error_message}")
                
        except Exception as e:
            logger.error(f"Error setting weights: {e}")
            import traceback
            traceback.print_exc()
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Set weights to UID 0')
    parser.add_argument('--netuid', type=int, required=True, help='NetUID to set weights on')
    parser.add_argument('--wallet', type=str, required=True, help='Wallet name')
    parser.add_argument('--hotkey', type=str, default=None, help='Hotkey name (defaults to first hotkey in settings)')
    
    args = parser.parse_args()
    
    set_weights_to_uid0(
        netuid=args.netuid,
        wallet_name=args.wallet,
        hotkey=args.hotkey,
        weight_value=1.0
    )

