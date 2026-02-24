import bittensor as bt
from pydantic_core.core_schema import int_schema
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import SubstrateRequestException
from typing import Optional, cast
from bittensor.utils.balance import Balance, FixedPoint, fixed_to_float
from scalecodec.types import GenericCall
class Normal:
    def __init__(self, network: str, use_era: bool = True):
        """
        Initialize the Normal object.
        
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
        wallet: bt.Wallet,
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
            wallet: Wallet
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
        is_success, error_message = self._do_normal_call(wallet, call, use_era=use_era)
        
        if is_success:
            return True, f"Stake added successfully"
        else:
            return False, f"Error: {error_message}"


    def add_stake_not_limit(
        self, 
        wallet: bt.Wallet,
        netuid: int, 
        hotkey: str, 
        amount: Balance, 
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Add stake to a subnet.
        
        Args:
            wallet: Wallet
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
        is_success, error_message = self._do_normal_call(wallet, call, use_era=use_era)
        
        if is_success:
            return True, f"Stake added successfully"
        else:
            return False, f"Error: {error_message}"

    def remove_stake(
        self, 
        wallet: bt.Wallet,
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
            wallet: Wallet
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
        is_success, error_message = self._do_normal_call(wallet, call, use_era=use_era)
        if is_success:
            return True, f"Stake removed successfully"
        else:
            return False, f"Error: {error_message}"
            
    def remove_stake_not_limit(
        self, 
        wallet: bt.Wallet,
        netuid: int,
        hotkey: str,
        amount: Balance,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Remove stake from a subnet.
        
        Args:
            wallet: Wallet
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to unstake (if not using --all)
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='remove_stake',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_unstaked": amount.rao - 1,
            }
        )
        is_success, error_message = self._do_normal_call(wallet, call, use_era=use_era)
        if is_success:
            return True, f"Stake removed successfully"
        else:
            return False, f"Error: {error_message}"

    def burned_register(
        self,
        wallet: bt.Wallet,
        hotkey: str,
        netuid: int,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Do burned register.
        
        Args:
            wallet: Wallet
            hotkey: Hotkey address
            netuid: Subnet ID
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        print(f"Wallet: {wallet}")
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
        is_success, error_message = self._do_normal_call(wallet, call, use_era=use_era)
        print(f"Register successfully: {is_success}")
        print(f"Error: {error_message}")
        return is_success, error_message

    

    def move_stake(
        self, 
        wallet: bt.Wallet,
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
            wallet: Wallet
            origin_hotkey: Origin hotkey address
            destination_hotkey: Destination hotkey address
            origin_netuid: Source subnet ID
            destination_netuid: Destination subnet ID
            amount: Amount to move
            use_era: Whether to use era parameter (overrides instance default if provided)
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=wallet.coldkey.ss58_address,
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
        is_success, error_message = self._do_normal_call(wallet, call, use_era=use_era)
        new_balance = self.subtensor.get_stake(
            coldkey_ss58=wallet.coldkey.ss58_address,
            hotkey_ss58=origin_hotkey,
            netuid=origin_netuid,
        )
        print(f"New alpha balance on netuid {origin_netuid}: {new_balance}")
        if new_balance.rao < balance.rao:
            return True, f"Stake swapped successfully"
        else:
            return False, f"Error: {error_message}"

    def _do_normal_call(
        self,
        wallet: bt.Wallet,
        call: GenericCall = None,
        use_era: Optional[bool] = None,
    ) -> tuple[bool, str]:
        print(f"Wallet: {wallet}")
        print(f"Call: {call}")   
        # Use provided use_era if given, otherwise use instance default
        use_era_value = use_era if use_era is not None else self.use_era
        if use_era_value:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call,
                keypair=wallet.coldkey,
                era={"period": 1},
            )
        else:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call,
                keypair=wallet.coldkey,
            )
        try:
            receipt = self.substrate.submit_extrinsic(
                extrinsic,
                wait_for_inclusion=True,
                wait_for_finalization=False,
            )
        except Exception as e:
            error_message = str(e)
            return False, error_message
        
        is_success = receipt.is_success
        error_message = receipt.error_message
        return is_success, str(error_message)


if __name__ == "__main__":
    wallet = bt.Wallet(name="black")
    delegator = "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2"
    amount = input("Enter amount to stake: ")
    netuid = input("Enter netuid: ")
    wallet.unlock_coldkey()
    normal = Normal("finney")
    is_success, error_message = normal.add_stake(wallet, delegator, int(netuid), "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2", Balance.from_tao(int(amount)))
    print(is_success, error_message)