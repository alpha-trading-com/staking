import bittensor as bt
from pydantic_core.core_schema import int_schema
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import SubstrateRequestException
from typing import Optional, cast, List, Tuple

from bittensor.utils.balance import Balance, FixedPoint, fixed_to_float
from utils.stake_list import get_stake_custom

DEFAULT_WAIT_FOR_INCLUSION = True
DEFAULT_WAIT_FOR_FINALIZATION = False

class Proxy:
    def __init__(self, network: str, use_era: bool = True):
        """
        Initialize the RonProxy object.
        
        Args:
            network: Network name
            use_era: Whether to use era parameter in extrinsic creation
        """
        self.network = network
        self.use_era = use_era
        self.subtensor = bt.Subtensor(network=network)
        

    def init_runtime(self):
        self.substrate = SubstrateInterface(
            url=self.network,
            ss58_format=42,
            type_registry_preset='substrate-node-template',
            auto_reconnect=True,
        )

    def add_stake(
        self, 
        proxy_wallet: bt.Wallet,
        delegator: str,
        netuid: int, 
        hotkey: str, 
        amount: Balance, 
        price_with_tolerance: int,
        allow_partial: bool = False,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Add stake to a subnet.
        
        Args:
            proxy_wallet: Proxy wallet
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to stake
            tolerance: Tolerance for stake amount
            allow_partial: Whether to allow partial staking
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='add_stake_limit',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_staked": amount.rao,
                "limit_price": price_with_tolerance,
                "allow_partial": allow_partial,
            }
        )
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call, use_era=use_era)
        
        if is_success:
            return True, f"Stake added successfully"
        else:
            return False, f"Error: {error_message}"


    def add_stake_not_limit(
        self, 
        proxy_wallet: bt.Wallet,
        delegator: str,
        netuid: int, 
        hotkey: str, 
        amount: Balance, 
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Add stake to a subnet.
        
        Args:
            proxy_wallet: Proxy wallet
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to stake
            tolerance: Tolerance for stake amount
            allow_partial: Whether to allow partial staking
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='add_stake',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_staked": amount.rao,
            }
        )
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call, use_era=use_era)
        
        if is_success:
            return True, f"Stake added successfully"
        else:
            return False, f"Error: {error_message}"

    def remove_stake(
        self, 
        proxy_wallet: bt.Wallet,
        delegator: str,
        netuid: int,
        hotkey: str,
        amount: Balance,
        price_with_tolerance: int,
        allow_partial: bool = False,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Remove stake from a subnet.
        
        Args:
            proxy_wallet: Proxy wallet
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to unstake (if not using --all)
            price_with_tolerance: Price with tolerance
            allow_partial: Whether to allow partial unstaking
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='remove_stake_limit',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_unstaked": amount.rao - 1,
                "limit_price": price_with_tolerance,
                "allow_partial": allow_partial,
            }
        )
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call, use_era=use_era)
        if is_success:
            return True, f"Stake removed successfully"
        else:
            return False, f"Error: {error_message}"
            
    def remove_stake_not_limit(
        self, 
        proxy_wallet: bt.Wallet,
        delegator: str,
        netuid: int,
        hotkey: str,
        amount: Balance,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Remove stake from a subnet.
        
        Args:
            proxy_wallet: Proxy wallet
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to unstake (if not using --all)
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        self.init_runtime()
        print(f"Remove stake not limit: {amount.rao - 1}")
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='remove_stake',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_unstaked": amount.rao - 1,
            }
        )
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call, use_era=use_era)
        if is_success:
            return True, f"Stake removed successfully"
        else:
            return False, f"Error: {error_message}"

    def burned_register(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        hotkey: str,
        netuid: int,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Do burned register.
        
        Args:
            proxy_wallet: Proxy wallet
            delegator: Delegator address
            hotkey: Hotkey address
            netuid: Subnet ID
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        print(f"Proxy wallet: {proxy_wallet}")
        print(f"Delegator: {delegator}")
        print(f"Hotkey: {hotkey}")
        print(f"Netuid: {netuid}")
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='burned_register',
            call_params={
                'netuid': netuid,
                'hotkey': hotkey,
            }
        )
        print(f"Call: {call}")
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call, 'Registration', use_era=use_era)
        print(f"Register successfully: {is_success}")
        print(f"Error: {error_message}")
        return is_success, error_message

    

    def move_stake(
        self, 
        proxy_wallet: bt.Wallet,
        delegator: str,
        origin_hotkey: str, 
        destination_hotkey: str, 
        origin_netuid: int, 
        destination_netuid: int, 
        amount: Balance,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Move stake between validators
        
        Args:
            proxy_wallet: Proxy wallet
            delegator: Delegator address
            origin_hotkey: Origin hotkey address
            destination_hotkey: Destination hotkey address
            origin_netuid: Source subnet ID
            destination_netuid: Destination subnet ID
            amount: Amount to move
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        balance = get_stake_custom(
            self.subtensor,
            coldkey_ss58=delegator,
            hotkey_ss58=origin_hotkey,
            netuid=origin_netuid,
        )
        print(f"Current alpha balance on netuid {origin_netuid}: {balance}")
        
        if amount.rao > balance.rao:
            return False, f"Error: Amount to swap is greater than current balance"

        self.init_runtime()
        
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='move_stake',
            call_params={
                'origin_hotkey': origin_hotkey,
                'destination_hotkey': destination_hotkey,
                'origin_netuid': origin_netuid,
                'destination_netuid': destination_netuid,
                'alpha_amount': amount.rao - 1,
            }
        )
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call, use_era=use_era)
        new_balance = get_stake_custom(
            self.subtensor,
            coldkey_ss58=delegator,
            hotkey_ss58=origin_hotkey,
            netuid=origin_netuid,
        )
        print(f"New alpha balance on netuid {origin_netuid}: {new_balance}")
        if new_balance.rao < balance.rao:
            return True, f"Stake swapped successfully"
        else:
            return False, f"Error: {error_message}"

    def _do_proxy_call(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        call,
        proxy_type: str = 'Staking',
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        print(f"Proxy wallet: {proxy_wallet}")
        print(f"Delegator: {delegator}")
        print(f"Call: {call}")
        proxy_call = self.substrate.compose_call(
            call_module='Proxy',
            call_function='proxy',
            call_params={
                'real': delegator,
                'force_proxy_type': proxy_type,
                'call': call,
            }
        )
        # Use provided use_era if given, otherwise use instance default
        use_era_value = use_era if use_era is not None else self.use_era
        if use_era_value:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=proxy_call,
                keypair=proxy_wallet.coldkey,
                era={"period": 1},
            )
        else:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=proxy_call,
                keypair=proxy_wallet.coldkey,
            )
        try:
            receipt = self.substrate.submit_extrinsic(
                extrinsic,
                wait_for_inclusion=DEFAULT_WAIT_FOR_INCLUSION,
                wait_for_finalization=DEFAULT_WAIT_FOR_FINALIZATION,
            )
        except Exception as e:
            error_message = str(e)
            return False, error_message
        
        is_success = receipt.is_success
        error_message = receipt.error_message
        return is_success, str(error_message)

    def _batch_proxy_calls(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        calls: list,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Execute multiple proxy calls in a single extrinsic via Utility.batch.

        Args:
            proxy_wallet: Proxy wallet
            delegator: Delegator address
            calls: List of composed inner calls (e.g. add_stake / remove_stake)
            use_era: Whether to use era parameter

        Returns:
            (success, error_message)
        """
        if not calls:
            return False, "No calls to batch"
        self.init_runtime()
        proxy_calls = []
        for call in calls:
            proxy_call = self.substrate.compose_call(
                call_module='Proxy',
                call_function='proxy',
                call_params={
                    'real': delegator,
                    'force_proxy_type': 'Staking',
                    'call': call,
                }
            )
            proxy_calls.append(proxy_call)
        batch_call = self.substrate.compose_call(
            call_module='Utility',
            call_function='batch',
            call_params={'calls': proxy_calls}
        )
        use_era_value = use_era if use_era is not None else self.use_era
        if use_era_value:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=batch_call,
                keypair=proxy_wallet.coldkey,
                era={"period": 64},
            )
        else:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=batch_call,
                keypair=proxy_wallet.coldkey,
            )
        try:
            receipt = self.substrate.submit_extrinsic(
                extrinsic,
                wait_for_inclusion=DEFAULT_WAIT_FOR_INCLUSION,
                wait_for_finalization=DEFAULT_WAIT_FOR_FINALIZATION,
            )
        except Exception as e:
            return False, str(e)
        is_success = receipt.is_success
        error_message = receipt.error_message
        return is_success, str(error_message)

    def batch_stake_ops(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        operations: List[Tuple[str, int, str, int, Optional[int], bool]],
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Run multiple stake and/or unstake operations in one extrinsic.
        Each op: (action, netuid, hotkey_ss58, amount_rao, limit_price, allow_partial).
        limit_price None = use add_stake/remove_stake; else use add_stake_limit/remove_stake_limit.
        """
        self.init_runtime()
        calls = []
        for item in operations:
            action, netuid, hotkey_ss58, amount_rao = item[0], item[1], item[2], item[3]
            limit_price = item[4] if len(item) > 4 else None
            allow_partial = item[5] if len(item) > 5 else False
            if action == 'stake':
                if limit_price is not None:
                    call = self.substrate.compose_call(
                        call_module='SubtensorModule',
                        call_function='add_stake_limit',
                        call_params={
                            'hotkey': hotkey_ss58,
                            'netuid': netuid,
                            'amount_staked': amount_rao,
                            'limit_price': limit_price,
                            'allow_partial': allow_partial,
                        }
                    )
                else:
                    call = self.substrate.compose_call(
                        call_module='SubtensorModule',
                        call_function='add_stake',
                        call_params={
                            'hotkey': hotkey_ss58,
                            'netuid': netuid,
                            'amount_staked': amount_rao,
                        }
                    )
            else:  # unstake
                amount_unstaked = max(0, amount_rao - 1)
                if limit_price is not None:
                    call = self.substrate.compose_call(
                        call_module='SubtensorModule',
                        call_function='remove_stake_limit',
                        call_params={
                            'hotkey': hotkey_ss58,
                            'netuid': netuid,
                            'amount_unstaked': amount_unstaked,
                            'limit_price': limit_price,
                            'allow_partial': allow_partial,
                        }
                    )
                else:
                    call = self.substrate.compose_call(
                        call_module='SubtensorModule',
                        call_function='remove_stake',
                        call_params={
                            'hotkey': hotkey_ss58,
                            'netuid': netuid,
                            'amount_unstaked': amount_unstaked,
                        }
                    )
            calls.append(call)
        return self._batch_proxy_calls(proxy_wallet, delegator, calls, use_era=use_era)


if __name__ == "__main__":
    proxy_wallet = bt.Wallet(name="black")
    delegator = "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2"
    amount = input("Enter amount to stake: ")
    netuid = input("Enter netuid: ")
    proxy_wallet.unlock_coldkey()
    proxy = Proxy("finney")
    is_success, error_message = proxy.add_stake(proxy_wallet, delegator, int(netuid), "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2", Balance.from_tao(int(amount)))
    print(is_success, error_message)