import bittensor as bt
import time

from app.constants import ROUND_TABLE_HOTKEY
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger
from utils.tolerance import calculate_stake_limit_price

class Staking:
    def __init__(self):
        self.proxy = Proxy(network=settings.NETWORK)
        self.proxy.init_runtime()
        self.subtensor = bt.Subtensor(network=settings.NETWORK)
        self.wallet_name = settings.WALLET_NAMES[0]
        self.wallet = bt.Wallet(name=self.wallet_name)
        self.delegator = settings.DELEGATORS[settings.WALLET_NAMES.index(self.wallet_name)]
        self.unlock_wallet()

    def unlock_wallet(self):
        for i in range(3):
            try:
                self.wallet.unlock_coldkey()
                break
            except Exception as e:
                print(f"Error unlocking wallet {self.wallet_name}: {e}")
                continue
        if i == 2:
            raise Exception(f"Failed to unlock wallet {self.wallet_name}")

    def is_staked(self, netuid):
        return self.subtensor.get_stake(self.delegator, settings.DEFAULT_DEST_HOTKEY, netuid).tao > 0

    def stake(self, netuid, amount, retries=1):
        print(f"Staking {amount} TAO to netuid {netuid}")
        limit_price = calculate_stake_limit_price(
            amount, 
            netuid, 
            min_tolerance_staking=True, 
            default_rate_tolerance=0.035,
            subtensor=self.subtensor,
            tolerance_offset="*1.2"
        )
        for _ in range(retries):
            result, msg = self.proxy.add_stake(
                proxy_wallet=self.wallet,
                delegator=self.delegator,
                netuid=netuid,
                hotkey=settings.DEFAULT_DEST_HOTKEY,
                amount=bt.Balance.from_tao(amount),
                price_with_tolerance=limit_price,
            )
            if result:
                print(f"Stake added: {self.wallet.coldkey.ss58_address} {amount} {netuid}")
                return True
            else:
                print(f"Stake failed: {msg}")
                continue
        return False

    def move_stake(
        self, 
        origin_netuid,  
        destination_netuid, 
        amount = None,
        origin_hotkey=settings.DEFAULT_DEST_HOTKEY,
        destination_hotkey=settings.DEFAULT_DEST_HOTKEY,
        retries=3,
    ):
        if amount is None:
            amount_balance = self.subtensor.get_stake(
                coldkey_ss58=self.delegator,
                hotkey_ss58=origin_hotkey,
                netuid=origin_netuid,
            )
        else:
            amount_balance = bt.Balance.from_tao(amount, origin_netuid)

        print(f"Moving {amount} TAO from netuid {origin_netuid} to netuid {destination_netuid}")
        for _ in range(retries):
            result, msg = self.proxy.move_stake(
                proxy_wallet=self.wallet,
                delegator=self.delegator,
                origin_hotkey=origin_hotkey, 
                destination_hotkey=destination_hotkey,  
                origin_netuid=origin_netuid,
                destination_netuid=destination_netuid,
                amount=amount_balance,
            )
            if result:
                print(f"Stake moved: {self.wallet.coldkey.ss58_address} {amount} {origin_netuid} {destination_netuid}")
                return True
            else:
                print(f"Stake move failed: {msg}")
                continue
        return False

    def stake_until_success(self, netuid, amount):
        while not self.is_staked(netuid):
            self.stake(netuid, amount)
            time.sleep(1)
        return True

    def all_in(self, netuid):
        while True:
            amount = self.subtensor.get_balance(self.delegator).tao
            if amount < 1:
                break

            print(f"All-in staking {amount} TAO to netuid {netuid}")
            result, msg = self.proxy.add_stake(
                proxy_wallet=self.wallet,
                delegator=self.delegator,
                netuid=netuid,
                hotkey=settings.DEFAULT_DEST_HOTKEY,
                amount=bt.Balance.from_tao(float(amount)),
                tolerance=0.9,
            )
            if result:
                print(f"Stake added: {self.wallet.coldkey.ss58_address} {amount} {netuid}")
                break
            else:
                print(f"Stake failed: {msg}")
                time.sleep(1)

        while True:
            still_staking = False
            for subnet_id in range(1, 129):
                if subnet_id == netuid:
                    continue
                staked_amount = self.subtensor.get_stake(self.delegator, settings.DEFAULT_DEST_HOTKEY, subnet_id).tao
                if staked_amount < 1:
                    continue    
                still_staking = True
                result, msg = self.proxy.move_stake(
                    proxy_wallet=self.wallet,
                    delegator=self.delegator,
                    origin_hotkey=settings.DEFAULT_DEST_HOTKEY,
                    destination_hotkey=settings.DEFAULT_DEST_HOTKEY,
                    origin_netuid=subnet_id,
                    destination_netuid=netuid,
                    amount=bt.Balance.from_tao(float(staked_amount)),
                )
                if result:
                    print(f"Stake moved: {self.wallet.coldkey.ss58_address} {staked_amount} {subnet_id} {netuid}")
                else:
                    print(f"Stake move failed: {msg}")
            if not still_staking:
                break

    def unstake(self, netuid):
        amount = self.subtensor.get_stake(self.delegator, settings.DEFAULT_DEST_HOTKEY, netuid).tao
        print(f"Unstaking {amount} TAO from netuid {netuid}")
        if amount < 1:
            print(f"No stake to unstake from netuid {netuid}")
            return False

        result, msg = self.proxy.remove_stake(
            proxy_wallet=self.wallet, 
            delegator=self.delegator, 
            hotkey=settings.DEFAULT_DEST_HOTKEY, 
            amount=bt.Balance.from_tao(float(amount)), 
            tolerance=0.9,
            netuid=netuid, 
        )
        if result:
            print(f"Stake removed: {self.wallet.coldkey.ss58_address} {amount} {netuid}")
            return True
        else:
            print(f"Unstake failed: {msg}")
            return False

if __name__ == "__main__":
    staking = Staking()
    staking.stake(1, 5)