#!/usr/bin/env python3
"""
Interactive command loop for staking/unstaking operations.
Uses numbered selection for menus.
"""

from app.core.config import settings
from app.services.stake import stake_service
from app.services.wallets import wallets


def select_from_list(prompt, options, default_index=0):
    """Display numbered list and get user selection."""
    print(f"\n{prompt}")
    print("Select one of the following:")
    for i, option in enumerate(options, 1):
        default_marker = " (default)" if i == default_index + 1 else ""
        print(f"[{i}] {option}{default_marker}")
    
    while True:
        try:
            choice = input(f"\nEnter your choice (default: {default_index + 1}): ").strip()
            if not choice:
                # Use default when Enter is pressed
                return options[default_index]
            index = int(choice) - 1
            if 0 <= index < len(options):
                return options[index]
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            return None


def main():
    print("=== Staking/Unstaking Command Loop ===\n")
    
    if not wallets:
        print("No wallets available. Please check configuration.")
        return
    
    wallet_list = list(wallets.keys())
    action_options = ["Stake", "Unstake"]
    
    try:
        # Main loop
        while True:
            # Select wallet (default: first wallet)
            wallet_name = select_from_list("Select Wallet:", wallet_list, default_index=0)
            
            if wallet_name is None:
                print("\nExiting...")
                return
            
            print(f"\nUsing wallet: {wallet_name}\n")

            # Select action (Stake or Unstake, default: Stake)
            action = select_from_list("Select Action:", action_options, default_index=0)
            
            if action is None:
                print("\nExiting...")
                break
            
            action_lower = action.lower()
            
            # Get netuid
            while True:
                netuid_input = input("\nEnter netuid: ").strip()
                if not netuid_input:
                    continue
                try:
                    netuid = int(netuid_input)
                    break
                except ValueError:
                    print("Invalid netuid. Please enter a number.")
            
            # Get amount
            amount = None
            if action_lower == "unstake":
                # For unstake, allow empty input to unstake all
                while True:
                    amount_input = input("Enter amount (TAO) (press Enter to unstake all): ").strip()
                    if not amount_input:
                        # Empty input means unstake all
                        amount = None
                        break
                    try:
                        amount = float(amount_input)
                        if amount <= 0:
                            print("Amount must be greater than 0.")
                            continue
                        break
                    except ValueError:
                        print("Invalid amount. Please enter a number.")
            else:
                # For stake, require an amount
                while True:
                    amount_input = input("Enter amount (TAO): ").strip()
                    if not amount_input:
                        continue
                    try:
                        amount = float(amount_input)
                        if amount <= 0:
                            print("Amount must be greater than 0.")
                            continue
                        break
                    except ValueError:
                        print("Invalid amount. Please enter a number.")
            
            # Execute operation
            if amount is None:
                print(f"\n{action}ing all available TAO from netuid {netuid}...\n")
            else:
                print(f"\n{action}ing {amount} TAO to netuid {netuid}...\n")
            
            if action_lower == "stake":
                result = stake_service.stake(
                    tao_amount=amount,
                    netuid=netuid,
                    wallet_name=wallet_name,
                )
            else:  # unstake
                result = stake_service.unstake_not_limit(
                    netuid=netuid,
                    wallet_name=wallet_name,
                    amount=amount,
                )
            
            if result.get("success"):
                print(f"✓ {action} successful!\n")
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"✗ {action} failed: {error_msg}\n")
            
    except KeyboardInterrupt:
        print("\n\nExiting...\n")
    except Exception as e:
        print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
