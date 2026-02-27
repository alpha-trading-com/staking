#!/usr/bin/env python3
"""
Script to unstake TAO from subnets when their prices rise above thresholds:
- SN 101: threshold 0.005
- SN 115: threshold 0.01
- SN 125: threshold 0.01
"""

import sys
import os
import time

# Add the parent directory to the Python search path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt
from app.core.config import settings
from app.services.stake import stake_service
from app.services.wallets import wallets

# Subnet thresholds
SUBNET_THRESHOLDS = {
    101: 0.005,
    115: 0.01,
    125: 0.01,
}

settings.DEFAULT_MIN_TOLERANCE = True
settings.TOLERANCE_OFFSET = "*1.2"
settings.USE_ERA = True

def check_and_unstake(subnet_info, netuid, threshold, wallet_name, subtensor):
    """Check subnet price and unstake if price is above threshold."""
    if subnet_info is None:
        print(f"Subnet {netuid} does not exist, skipping...")
        return False
    
    try:
        alpha_price = subnet_info.alpha_to_tao(1)
        print(f"Subnet {netuid} current alpha token price: {alpha_price} TAO")
    except Exception as e:
        print(f"Error getting price for subnet {netuid}: {e}")
        return False
    
    if alpha_price >= bt.Balance.from_tao(threshold):
        # Price is above threshold - unstake if there's any stake
        print(f"Subnet {netuid} price {alpha_price} TAO is above threshold {threshold} TAO.")
        
        result = stake_service.unstake_not_limit(
            netuid=netuid,
            wallet_name=wallet_name,
            amount=None,  # Unstake all
        )
        
        if result.get("success"):
            print(f"✓ Successfully unstaked from subnet {netuid}")
            return True
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"✗ Failed to unstake from subnet {netuid}: {error_msg}")
            return False
    else:
        print(f"Subnet {netuid} price {alpha_price} TAO is below threshold {threshold} TAO. No action taken.")
        subtensor.wait_for_block()
        return False


def main():
    """Main function to continuously monitor prices and unstake when thresholds are exceeded."""
    if not wallets:
        print("No wallets available. Please check configuration.")
        return
    
    # Use the first available wallet (or you can modify to select a specific one)
    wallet_index = int(input("Enter the wallet index: "))
    wallet_name = list(wallets.keys())[wallet_index]
    print(f"Using wallet: {wallet_name}")
    
    subtensor = bt.Subtensor(network=settings.NETWORK)
    
    print("Monitoring subnet prices and unstaking when price > threshold...")
    print(f"Thresholds: {SUBNET_THRESHOLDS}")
    print("Will unstake when price >= threshold")
    print("Press Ctrl+C to stop the script\n")
    
    
    try:
        while True:
            try:
                # Fetch all subnet data
                subnet_infos = subtensor.all_subnets()
                
                # Check each subnet
                for netuid, threshold in SUBNET_THRESHOLDS.items():
                    try:
                        check_and_unstake(subnet_infos[netuid], netuid, threshold, wallet_name, subtensor)
                        print(f"\n{'='*60}\n")
                    except Exception as e:
                        print(f"Error processing subnet {netuid}: {e}")
                        continue
                print()
                
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait a bit before retrying on error
                continue
                
    except KeyboardInterrupt:
        print("\n\nExiting...")


if __name__ == "__main__":
    main()
