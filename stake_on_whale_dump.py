#!/usr/bin/env python3
"""
Script to stake 100 TAO to subnets when their prices drop below thresholds:
- SN 101: price < 0.003
- SN 115: price < 0.005
- SN 125: price < 0.007
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
    # 115: 0.005,
    # 125: 0.007,
}

STAKE_AMOUNT = 10.0  # TAO

settings.DEFAULT_RATE_TOLERANCE = 0.005
settings.DEFAULT_MIN_TOLERANCE = False
settings.TOLERANCE_OFFSET = "*1.2"
settings.USE_ERA = True

print(f"Tolerance offset: {settings.TOLERANCE_OFFSET}")
def check_and_stake(subnet_info, netuid, threshold, wallet_name):
    """Check if subnet price is alpha token price below threshold and stake if so."""
    if subnet_info is None:
        print(f"Subnet {netuid} does not exist, skipping...")
        return False
    
    try:
        alpha_price = subnet_info.alpha_to_tao(1)
        print(f"Subnet {netuid} current alpha token price: {alpha_price} TAO")
    except Exception as e:
        print(f"Error getting price for subnet {netuid}: {e}")
        return False
    
    if alpha_price < bt.Balance.from_tao(threshold):
        print(f"Subnet {netuid} price {alpha_price} TAO is below threshold {threshold} TAO. Staking {STAKE_AMOUNT} TAO...")
        
        result = stake_service.stake(
            tao_amount=STAKE_AMOUNT,
            netuid=netuid,
            wallet_name=wallet_name,
        )
        
        if result.get("success"):
            print(f"✓ Successfully staked {STAKE_AMOUNT} TAO to subnet {netuid}")
            return True
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"✗ Failed to stake to subnet {netuid}: {error_msg}")
            return False
    else:
        print(f"Subnet {netuid} price {alpha_price} TAO is above threshold {threshold} TAO. No action taken.")
        return False


def main():
    """Main function to continuously monitor prices and stake when conditions are met."""
    if not wallets:
        print("No wallets available. Please check configuration.")
        return
    
    # Use the first available wallet (or you can modify to select a specific one)
    wallet_name = list(wallets.keys())[0]
    print(f"Using wallet: {wallet_name}")
    
    subtensor = bt.Subtensor(network=settings.NETWORK)
    
    print("Monitoring subnet prices and staking if thresholds are met...")
    print(f"Thresholds: {SUBNET_THRESHOLDS}")
    print(f"Stake amount: {STAKE_AMOUNT} TAO")
    print("Press Ctrl+C to stop the script\n")
    
    
    try:
        while True:
            try:
                # Fetch all subnet data
                subnet_infos = subtensor.all_subnets()
                
                # Check each subnet
                for netuid, threshold in SUBNET_THRESHOLDS.items():
                    # Skip if already staked to this subnet in this session
                    
                    try:
                        check_and_stake(subnet_infos[netuid], netuid, threshold, wallet_name)
                        print(f"\n{'='*60}\n")
                    except Exception as e:
                        print(f"Error processing subnet {netuid}: {e}")
                        continue
                
                # Wait for next block before checking again
                print("\nWaiting for next block...")
                subtensor.wait_for_block()
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
