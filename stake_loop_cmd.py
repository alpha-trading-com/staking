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
from app.services.proxy import DEFAULT_WAIT_FOR_INCLUSION, DEFAULT_WAIT_FOR_FINALIZATION
# File to store last action
LAST_ACTION_FILE = Path(__file__).parent / "last_action.json"
DEFAULT_WAIT_FOR_INCLUSION = False
DEFAULT_WAIT_FOR_FINALIZATION = False

settings.DEFAULT_MIN_TOLERANCE = True
settings.TOLERANCE_OFFSET = "*1.2"
settings.USE_ERA = True

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'


def save_last_action(last_action):
    """Save last action to file."""
    try:
        with open(LAST_ACTION_FILE, 'w') as f:
            json.dump(last_action, f, indent=2)
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Could not save last action: {e}{Colors.RESET}")


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
        print(f"{Colors.YELLOW}Warning: Could not load last action: {e}{Colors.RESET}")
    
    return None


def select_from_list(prompt, options, default_index=0):
    """Display numbered list and get user selection."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{prompt}{Colors.RESET}")
    print(f"{Colors.GRAY}Select one of the following:{Colors.RESET}")
    for i, option in enumerate(options, 1):
        default_marker = f" {Colors.GREEN}(default){Colors.RESET}" if i == default_index + 1 else ""
        print(f"{Colors.BLUE}[{i}]{Colors.RESET} {option}{default_marker}")
    
    while True:
        try:
            choice = input(f"\n{Colors.YELLOW}Enter your choice (default: {default_index + 1}):{Colors.RESET} ").strip()
            if not choice:
                # Use default when Enter is pressed
                return options[default_index]
            index = int(choice) - 1
            if 0 <= index < len(options):
                return options[index]
            else:
                print(f"{Colors.RED}Invalid choice. Please enter a number between 1 and {len(options)}.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.RESET}")
        except KeyboardInterrupt:
            # Re-raise to be caught by outer handler
            raise


def main():
    print(f"{Colors.CYAN}{Colors.BOLD}=== Staking/Unstaking Command Loop ==={Colors.RESET}\n")
    
    if not wallets:
        print(f"{Colors.RED}No wallets available. Please check configuration.{Colors.RESET}")
        return
    
    wallet_list = list(wallets.keys())
    action_options = ["Stake", "Unstake"]
    
    # Load last action from file
    last_action = load_last_action()
    if last_action:
        amount_str = last_action.get('amount', 'all')
        if amount_str == 'all':
            amount_str = f"{Colors.YELLOW}all{Colors.RESET}"
        print(f"{Colors.GREEN}Loaded last action:{Colors.RESET} {Colors.CYAN}{last_action['action']}{Colors.RESET} {amount_str} TAO on netuid {Colors.BLUE}{last_action['netuid']}{Colors.RESET} with wallet {Colors.MAGENTA}{last_action['wallet_name']}{Colors.RESET}\n")
    
    try:
        # Main loop
        while True:
            # Build wallet selection list with "Repeat last action" and "Exit" options
            wallet_selection_list = wallet_list.copy()
            exit_option = "Exit"
            if last_action:
                # Format the repeat option with last action details
                action = last_action['action']
                netuid = last_action['netuid']
                wallet_name = last_action['wallet_name']
                amount = last_action.get('amount')
                if amount is None:
                    amount_str = "all"
                else:
                    amount_str = f"{amount}"
                repeat_option = f"Repeat last action ({action} {amount_str} TAO on netuid {netuid} with {wallet_name})"
                wallet_selection_list.append(repeat_option)
            wallet_selection_list.append(exit_option)
            
            # Select wallet (default: second wallet, index 1)
            try:
                selected = select_from_list("Select Wallet:", wallet_selection_list, default_index=1)
            except KeyboardInterrupt:
                print(f"\n\n{Colors.YELLOW}Cancelled. Returning to main menu...{Colors.RESET}\n")
                continue
            
            if selected is None:
                print(f"\n{Colors.YELLOW}Cancelled. Returning to main menu...{Colors.RESET}\n")
                continue
            
            # Check if "Exit" was selected
            if selected == exit_option:
                print(f"\n{Colors.CYAN}Exiting program...{Colors.RESET}\n")
                break
            
            # Check if "Repeat last action" was selected
            if selected.startswith("Repeat last action") and last_action:
                wallet_name = last_action["wallet_name"]
                action = last_action["action"]
                netuid = last_action["netuid"]
                amount = last_action["amount"]
                action_lower = action.lower()
                
                print(f"\n{Colors.CYAN}{Colors.BOLD}Repeating last action:{Colors.RESET}")
                print(f"  {Colors.GRAY}Wallet:{Colors.RESET} {Colors.MAGENTA}{wallet_name}{Colors.RESET}")
                print(f"  {Colors.GRAY}Action:{Colors.RESET} {Colors.CYAN}{action}{Colors.RESET}")
                print(f"  {Colors.GRAY}Netuid:{Colors.RESET} {Colors.BLUE}{netuid}{Colors.RESET}")
                if amount is None:
                    print(f"  {Colors.GRAY}Amount:{Colors.RESET} {Colors.YELLOW}All available{Colors.RESET}\n")
                else:
                    print(f"  {Colors.GRAY}Amount:{Colors.RESET} {Colors.GREEN}{amount} TAO{Colors.RESET}\n")
            else:
                wallet_name = selected
                print(f"\n{Colors.GREEN}Using wallet:{Colors.RESET} {Colors.MAGENTA}{wallet_name}{Colors.RESET}\n")

                # Select action (Stake or Unstake, default: Stake)
                try:
                    action = select_from_list("Select Action:", action_options, default_index=0)
                except KeyboardInterrupt:
                    print(f"\n\n{Colors.YELLOW}Cancelled. Returning to main menu...{Colors.RESET}\n")
                    continue
                
                if action is None:
                    print(f"\n{Colors.YELLOW}Cancelled. Returning to main menu...{Colors.RESET}\n")
                    continue
                
                action_lower = action.lower()
                
                # Get netuid
                try:
                    while True:
                        try:
                            netuid_input = input(f"\n{Colors.YELLOW}Enter netuid:{Colors.RESET} ").strip()
                            if not netuid_input:
                                continue
                            netuid = int(netuid_input)
                            break
                        except ValueError:
                            print(f"{Colors.RED}Invalid netuid. Please enter a number.{Colors.RESET}")
                except KeyboardInterrupt:
                    print(f"\n\n{Colors.YELLOW}Cancelled. Returning to main menu...{Colors.RESET}\n")
                    continue
                
                # Get amount
                amount = None
                try:
                    if action_lower == "unstake":
                        # For unstake, allow empty input to unstake all
                        while True:
                            try:
                                amount_input = input(f"{Colors.YELLOW}Enter amount (TAO) (press Enter to unstake all):{Colors.RESET} ").strip()
                                if not amount_input:
                                    # Empty input means unstake all
                                    amount = None
                                    break
                                amount = float(amount_input)
                                if amount <= 0:
                                    print(f"{Colors.RED}Amount must be greater than 0.{Colors.RESET}")
                                    continue
                                break
                            except ValueError:
                                print(f"{Colors.RED}Invalid amount. Please enter a number.{Colors.RESET}")
                    else:
                        # For stake, require an amount
                        while True:
                            try:
                                amount_input = input(f"{Colors.YELLOW}Enter amount (TAO):{Colors.RESET} ").strip()
                                if not amount_input:
                                    continue
                                amount = float(amount_input)
                                if amount <= 0:
                                    print(f"{Colors.RED}Amount must be greater than 0.{Colors.RESET}")
                                    continue
                                break
                            except ValueError:
                                print(f"{Colors.RED}Invalid amount. Please enter a number.{Colors.RESET}")
                except KeyboardInterrupt:
                    print(f"\n\n{Colors.YELLOW}Cancelled. Returning to main menu...{Colors.RESET}\n")
                    continue
            
            # Execute operation
            if amount is None:
                print(f"\n{Colors.CYAN}{Colors.BOLD}{action}ing all available TAO from netuid {netuid}...{Colors.RESET}\n")
            else:
                print(f"\n{Colors.CYAN}{Colors.BOLD}{action}ing {amount} TAO to netuid {netuid}...{Colors.RESET}\n")
            
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
            
           
            
            # Store the last action (regardless of success or failure)
            last_action = {
                "wallet_name": wallet_name,
                "action": action,
                "netuid": netuid,
                "amount": amount
            }
            save_last_action(last_action)
            
            if result.get("success"):
                print(f"{Colors.GREEN}✓ {action} successful!{Colors.RESET}\n")
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"{Colors.RED}✗ {action} failed: {error_msg}{Colors.RESET}\n")
            
    except KeyboardInterrupt:
        # Only exit if Ctrl+C is pressed when not in any prompt
        print(f"\n\n{Colors.CYAN}Exiting program...{Colors.RESET}\n")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}\n")


if __name__ == "__main__":
    main()
