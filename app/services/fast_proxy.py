import bittensor as bt
from bittensor.core.chain_data.proxy import ProxyType
from bittensor.core.extrinsics.pallets import SubtensorModule
from bittensor.core.extrinsics.proxy import proxy_extrinsic
from bittensor.utils.balance import Balance

from app.core.config import settings


class FastProxy:
    def __init__(self, network: str, use_era: bool = True):
        """
        Initialize the Proxy object.

        Args:
            network: Network name
            use_era: Whether to use era parameter in extrinsic creation (deprecated, kept for compatibility)
        """
        self.network = network
        self.subtensor = bt.Subtensor(network=network)
        self.proxy_subtensor = bt.Subtensor(network=network)

    def init_proxy_subtensor(self):
        self.proxy_subtensor = bt.Subtensor(network=self.network)
            
    def add_stake(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        netuid: int,
        hotkey: str,
        amount: Balance,
        tolerance: float = 0.005,
        use_era: bool = settings.USE_ERA,   
        mev_protection: bool = settings.USE_MEV_PROTECTION,
    ) -> tuple[bool, str]:
        """
        Add stake to a subnet.

        Args:
            proxy_wallet: Proxy wallet
            delegator: Delegator address
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to stake
            tolerance: Tolerance for stake amount
            use_era: Whether to use era parameter in extrinsic creation (default: True)
            mev_protection: Whether to use MEV protection (default: True)
        """
        free_balance = self.subtensor.get_balance(
            address=delegator,
        )
        print(f"free_balance: {free_balance}")
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            return False, f"Subnet with netuid {netuid} does not exist"

        if free_balance.rao < amount.rao:
            amount = free_balance
            print(f"Amount is greater than free balance, setting amount to free balance: {amount.rao}")

        if subnet_info.is_dynamic:
            rate = 1 / subnet_info.price.tao or 1
            _rate_with_tolerance = rate * (1 + tolerance)  # Rate only for display
            rate_with_tolerance = f"{_rate_with_tolerance:.4f}"
            price_with_tolerance = subnet_info.price.rao * (1 + tolerance)
        else:
            rate_with_tolerance = "1"
            price_with_tolerance = 10000000000000000000

        print(f"price_with_tolerance: {price_with_tolerance}")
        self.init_proxy_subtensor()
        # Create the inner call
        call = SubtensorModule(self.proxy_subtensor).add_stake_limit(
            netuid=netuid,
            hotkey=hotkey,
            amount_staked=amount.rao,
            limit_price=price_with_tolerance,
            allow_partial=False,
        )

        # Execute through proxy
        response = proxy_extrinsic(
            subtensor=self.proxy_subtensor,
            wallet=proxy_wallet,
            real_account_ss58=delegator,
            force_proxy_type=ProxyType.Staking,
            call=call,
            mev_protection=mev_protection,
            period = settings.DEFAULT_PERIOD if use_era else None,
            wait_for_inclusion=True,
            wait_for_finalization=False,
        )

        new_free_balance = self.subtensor.get_balance(
            address=delegator,
        )
        if new_free_balance.rao < free_balance.rao:
            return True, "Stake added successfully"
        else:
            return False, f"Error: {response.message}"

    def remove_stake(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        netuid: int,
        hotkey: str,
        amount: Balance,
        tolerance: float = 0.005,
        mev_protection: bool = settings.USE_MEV_PROTECTION,
        use_era: bool = settings.USE_ERA,
    ) -> tuple[bool, str]:
        """
        Remove stake from a subnet.

        Args:
            proxy_wallet: Proxy wallet
            delegator: Delegator address
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to unstake
            tolerance: Tolerance for stake amount
            use_era: Whether to use era parameter in extrinsic creation (default: True)
            mev_protection: Whether to use MEV protection (default: True)
        """
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            return False, f"Subnet with netuid {netuid} does not exist"

        if subnet_info.is_dynamic:
            rate = subnet_info.price.tao or 1
            rate_with_tolerance = rate * (1 - tolerance)  # Rate only for display
            price_with_tolerance = subnet_info.price.rao * (
                1 - tolerance
            )  # Actual price to pass to extrinsic
        else:
            rate_with_tolerance = 1
            price_with_tolerance = 1

        print(f"amount: {amount.rao}")

        # Create the inner call
        self.init_proxy_subtensor()
        call = SubtensorModule(self.proxy_subtensor).remove_stake_limit(
            netuid=netuid,
            hotkey=hotkey,
            amount_unstaked=amount.rao - 1,
            limit_price=price_with_tolerance,
            allow_partial=False,
        )

        free_balance = self.subtensor.get_balance(
            address=delegator,
        )

        # Execute through proxy
        response = proxy_extrinsic(
            subtensor=self.proxy_subtensor,
            wallet=proxy_wallet,
            real_account_ss58=delegator,
            force_proxy_type=ProxyType.Staking,
            call=call,
            mev_protection=mev_protection,
            period = settings.DEFAULT_PERIOD if use_era else None,
            wait_for_inclusion=True,
            wait_for_finalization=False,
        )

        new_free_balance = self.subtensor.get_balance(
            address=delegator,
        )
        if new_free_balance.rao > free_balance.rao:
            return True, "Stake removed successfully"
        else:
            return False, f"Error: {response.message}"

    def burned_register(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        hotkey: str,
        netuid: int,
        mev_protection: bool = settings.USE_MEV_PROTECTION,
        use_era: bool = settings.USE_ERA,
    ) -> tuple[bool, str]:
        """
        Do burned register.

        Args:
            proxy_wallet: Proxy wallet
            delegator: Delegator address
            hotkey: Hotkey address
            netuid: Subnet ID
            use_era: Whether to use era parameter in extrinsic creation (default: True)
            mev_protection: Whether to use MEV protection (default: True)
        """
        print(f"Proxy wallet: {proxy_wallet}")
        print(f"Delegator: {delegator}")
        print(f"Hotkey: {hotkey}")
        print(f"Netuid: {netuid}")

        # Create the inner call
        self.init_proxy_subtensor()
        call = SubtensorModule(self.proxy_subtensor).burned_register(
            netuid=netuid,
            hotkey=hotkey,
        )

        print(f"Call: {call}")

        # Execute through proxy
        response = proxy_extrinsic(
            subtensor=self.proxy_subtensor,
            wallet=proxy_wallet,
            real_account_ss58=delegator,
            force_proxy_type=ProxyType.Registration,
            call=call,
            mev_protection=mev_protection,
            period = settings.DEFAULT_PERIOD if use_era else None,
            wait_for_inclusion=True,
            wait_for_finalization=False,
        )

        print(f"Register successfully: {response.success}")
        print(f"Error: {response.message}")
        return response.success, response.message

    def move_stake(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        origin_hotkey: str,
        destination_hotkey: str,
        origin_netuid: int,
        destination_netuid: int,
        amount: Balance,
        use_era: bool = settings.USE_ERA,
        mev_protection: bool = settings.USE_MEV_PROTECTION,
    ) -> tuple[bool, str]:
        """
        Move stake between validators

        Args:
            proxy_wallet: Proxy wallet
            delegator: Delegator address
            origin_hotkey: Source hotkey address
            destination_hotkey: Destination hotkey address
            origin_netuid: Source subnet ID
            destination_netuid: Destination subnet ID
            amount: Amount to swap
            use_era: Whether to use era parameter in extrinsic creation (default: True)
            mev_protection: Whether to use MEV protection (default: True)
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=delegator,
            hotkey_ss58=origin_hotkey,
            netuid=origin_netuid,
        )
        print(f"Current alpha balance on netuid {origin_netuid}: {balance}")

        if amount.rao > balance.rao:
            return False, "Error: Amount to swap is greater than current balance"

        # Create the inner call
        self.init_proxy_subtensor()
        call = SubtensorModule(self.proxy_subtensor).move_stake(
            origin_netuid=origin_netuid,
            origin_hotkey_ss58=origin_hotkey,
            destination_netuid=destination_netuid,
            destination_hotkey_ss58=destination_hotkey,
            alpha_amount=amount.rao - 1,
        )

        # Execute through proxy
        response = proxy_extrinsic(
            subtensor=self.proxy_subtensor,
            wallet=proxy_wallet, 
            real_account_ss58=delegator,
            force_proxy_type=ProxyType.Staking,
            call=call,
            mev_protection=mev_protection,
            period = settings.DEFAULT_PERIOD if use_era else None,
            wait_for_inclusion=True,
            wait_for_finalization=False,
        )

        new_balance = self.subtensor.get_stake(
            coldkey_ss58=delegator,
            hotkey_ss58=origin_hotkey,
            netuid=origin_netuid,
        )
        print(f"New alpha balance on netuid {origin_netuid}: {new_balance}")
        if new_balance.rao < balance.rao:
            return True, "Stake swapped successfully"
        else:
            return False, f"Error: {response.message}"


if __name__ == "__main__":
    proxy_wallet = bt.Wallet(name="black")
    delegator = "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2"
    hotkey = "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2"
    amount = input("Enter amount to stake: ")
    netuid = input("Enter netuid: ")
    use_mev_protection = input("Do you want to use MEV protection? (y/n): ").lower() in ["y", "yes"]
    proxy_wallet.unlock_coldkey()
    proxy = Proxy("finney")
    success, message = proxy.add_stake(
        proxy_wallet=proxy_wallet,
        delegator=delegator,
        netuid=int(netuid),
        hotkey=hotkey,
        amount=Balance.from_tao(int(amount)),
        mev_protection=use_mev_protection,
    )
    print(success, message)
