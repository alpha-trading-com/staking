#!/usr/bin/env python3
"""
Interactive command loop for staking/unstaking operations.
Uses numbered selection for menus.
"""

import json
import os
from pathlib import Path
from app.core.config import settings
from app.services.stake import stake_service
from app.services.wallets import wallets

# File to store last action
LAST_ACTION_FILE = Path(__file__).parent / "last_action.json"


def save_last_action(last_action):
    """Save last action to file."""
    try:
        with open(LAST_ACTION_FILE, 'w') as f:
            json.dump(last_action, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save last action: {e}")


def load_last_action():
    """Load last action from file."""
    if not LAST_ACTION_FILE.exists():
        return None
    
    try:
        with open(LAST_ACTION_FILE, 'r') as f:
            data = json.load(f)
            # Validate that all required fields are present
            if all(key in data for key in ["wallet_name", "action", "netuid"]):
                return data
    except Exception as e:
        print(f"Warning: Could not load last action: {e}")
    
    return None


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
            # Re-raise to be caught by outer handler
            raise


def main():
    print("=== Staking/Unstaking Command Loop ===\n")
    
    if not wallets:
        print("No wallets available. Please check configuration.")
        return
    
    wallet_list = list(wallets.keys())
    action_options = ["Stake", "Unstake"]
    
    # Load last action from file
    last_action = load_last_action()
    if last_action:
        print(f"Loaded last action: {last_action['action']} {last_action.get('amount', 'all')} TAO on netuid {last_action['netuid']} with wallet {last_action['wallet_name']}\n")
    
    try:
        # Main loop
        while True:
            # Build wallet selection list with "Repeat last action" and "Exit" options
            wallet_selection_list = wallet_list.copy()
            repeat_option = "Repeat last action"
            exit_option = "Exit"
            if last_action:
                wallet_selection_list.append(repeat_option)
            wallet_selection_list.append(exit_option)
            
            # Select wallet (default: second wallet, index 1)
            try:
                selected = select_from_list("Select Wallet:", wallet_selection_list, default_index=1)
            except KeyboardInterrupt:
                print("\n\nCancelled. Returning to main menu...\n")
                continue
            
            if selected is None:
                print("\nCancelled. Returning to main menu...\n")
                continue
            
            # Check if "Exit" was selected
            if selected == exit_option:
                print("\nExiting program...\n")
                break
            
            # Check if "Repeat last action" was selected
            if selected == repeat_option and last_action:
                wallet_name = last_action["wallet_name"]
                action = last_action["action"]
                netuid = last_action["netuid"]
                amount = last_action["amount"]
                action_lower = action.lower()
                
                print(f"\nRepeating last action:")
                print(f"Wallet: {wallet_name}")
                print(f"Action: {action}")
                print(f"Netuid: {netuid}")
                if amount is None:
                    print(f"Amount: All available\n")
                else:
                    print(f"Amount: {amount} TAO\n")
            else:
                wallet_name = selected
                print(f"\nUsing wallet: {wallet_name}\n")

                # Select action (Stake or Unstake, default: Stake)
                try:
                    action = select_from_list("Select Action:", action_options, default_index=0)
                except KeyboardInterrupt:
                    print("\n\nCancelled. Returning to main menu...\n")
                    continue
                
                if action is None:
                    print("\nCancelled. Returning to main menu...\n")
                    continue
                
                action_lower = action.lower()
                
                # Get netuid
                try:
                    while True:
                        try:
                            netuid_input = input("\nEnter netuid: ").strip()
                            if not netuid_input:
                                continue
                            netuid = int(netuid_input)
                            break
                        except ValueError:
                            print("Invalid netuid. Please enter a number.")
                except KeyboardInterrupt:
                    print("\n\nCancelled. Returning to main menu...\n")
                    continue
                
                # Get amount
                amount = None
                try:
                    if action_lower == "unstake":
                        # For unstake, allow empty input to unstake all
                        while True:
                            try:
                                amount_input = input("Enter amount (TAO) (press Enter to unstake all): ").strip()
                                if not amount_input:
                                    # Empty input means unstake all
                                    amount = None
                                    break
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
                            try:
                                amount_input = input("Enter amount (TAO): ").strip()
                                if not amount_input:
                                    continue
                                amount = float(amount_input)
                                if amount <= 0:
                                    print("Amount must be greater than 0.")
                                    continue
                                break
                            except ValueError:
                                print("Invalid amount. Please enter a number.")
                except KeyboardInterrupt:
                    print("\n\nCancelled. Returning to main menu...\n")
                    continue
            
             # Store the last action (regardless of success or failure)
            last_action = {
                "wallet_name": wallet_name,
                "action": action,
                "netuid": netuid,
                "amount": amount
            }
            
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
        # Only exit if Ctrl+C is pressed when not in any prompt
        print("\n\nExiting program...\n")
    except Exception as e:
        print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
