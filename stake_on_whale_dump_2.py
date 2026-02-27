#!/usr/bin/env python3
"""
Script to cross-stake between subnets when prices drop below thresholds:
- If SN 101's price is below threshold, stake to SN 115
- If SN 115's price is below threshold, stake to SN 101
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

# Subnet thresholds and cross-staking targets
# Format: {monitor_netuid: (threshold, stake_to_netuid)}
SUBNET_CONFIG = {
    101: (0.0035, 115),  # If 101's price < 0.0035, stake to 115
    115: (0.007, 101),  # If 115's price < 0.007, stake to 101
    125: (0.007, 115),  # If 125's price < 0.007, stake to 115
}

STAKE_AMOUNT = 120.0  # TAO

settings.DEFAULT_MIN_TOLERANCE = True
settings.TOLERANCE_OFFSET = "*1.2"
settings.USE_ERA = True

def check_and_cross_stake(subnet_info, monitor_netuid, threshold, stake_to_netuid, wallet_name):
    """Check if subnet price is below threshold and stake to the cross-subnet if so."""
    if subnet_info is None:
        print(f"Subnet {monitor_netuid} does not exist, skipping...")
        return False
    
    try:
        alpha_price = subnet_info.alpha_to_tao(1)
        print(f"Subnet {monitor_netuid} current alpha token price: {alpha_price} TAO")
    except Exception as e:
        print(f"Error getting price for subnet {monitor_netuid}: {e}")
        return False
    
    if alpha_price < bt.Balance.from_tao(threshold):
        print(f"Subnet {monitor_netuid} price {alpha_price} TAO is below threshold {threshold} TAO.")
        print(f"Staking {STAKE_AMOUNT} TAO to subnet {stake_to_netuid}...")
        
        result = stake_service.stake(
            tao_amount=STAKE_AMOUNT,
            netuid=stake_to_netuid,
            wallet_name=wallet_name,
        )
        
        if result.get("success"):
            print(f"✓ Successfully staked {STAKE_AMOUNT} TAO to subnet {stake_to_netuid}")
            return True
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"✗ Failed to stake to subnet {stake_to_netuid}: {error_msg}")
            return False
    else:
        print(f"Subnet {monitor_netuid} price {alpha_price} TAO is above threshold {threshold} TAO. No action taken.")
        return False


def main():
    """Main function to continuously monitor prices and stake when conditions are met."""
    if not wallets:
        print("No wallets available. Please check configuration.")
        return
    
    # Use the first available wallet (or you can modify to select a specific one)
    wallet_name = list(wallets.keys())[1]
    print(f"Using wallet: {wallet_name}")
    
    subtensor = bt.Subtensor(network=settings.NETWORK)
    
    print("Monitoring subnet prices and cross-staking when thresholds are met...")
    print("Cross-staking rules:")
    for monitor_netuid, (threshold, stake_to_netuid) in SUBNET_CONFIG.items():
        print(f"  - If SN {monitor_netuid}'s price < {threshold}, stake to SN {stake_to_netuid}")
    print(f"Stake amount: {STAKE_AMOUNT} TAO")
    print("Press Ctrl+C to stop the script\n")
    
    
    try:
        while True:
            try:
                # Fetch all subnet data
                subnet_infos = subtensor.all_subnets()
                
                # Check each subnet for cross-staking
                for monitor_netuid, (threshold, stake_to_netuid) in SUBNET_CONFIG.items():
                    try:
                        check_and_cross_stake(
                            subnet_infos[monitor_netuid], 
                            monitor_netuid, 
                            threshold, 
                            stake_to_netuid, 
                            wallet_name
                        )
                        print(f"\n{'='*60}\n")
                    except Exception as e:
                        print(f"Error processing subnet {monitor_netuid}: {e}")
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
