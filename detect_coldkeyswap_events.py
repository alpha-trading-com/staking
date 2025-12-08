import bittensor as bt
import os
import requests
import json
import time
import threading
import requests


from app.constants import ROUND_TABLE_HOTKEY
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger



NETWORK = "finney"

MAX_STAKE_AMOUNT = 1

class ColdkeySwapDetector:

    def __init__(self, proxy: Proxy):
        self.proxy = proxy
        self.subtensor = bt.subtensor(network=NETWORK)
        self.wallet_name = settings.WALLET_NAMES[0]
        self.wallet = bt.wallet(name=self.wallet_name)
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

    def stake(self, netuid, amount):
        print(f"Staking {amount} TAO to netuid {netuid}")
        result, msg = self.proxy.add_stake(
            proxy_wallet=self.wallet,
            delegator=self.delegator,
            netuid=netuid,
            hotkey=settings.DEFAULT_DEST_HOTKEY,
            amount=bt.Balance.from_tao(float(amount)),
            tolerance=0.5,
        )
        if result:
            print(f"Stake added: {self.wallet.coldkey.ss58_address} {amount} {netuid}")
            return True
        else:
            print(f"Stake failed: {msg}")
            return False

    def all_in(self, netuid):
        while True:
            amount = self.subtensor.get_balance(self.delegator).tao
            if amount == 0:
                break

            print(f"All-in staking {amount} TAO to netuid {netuid}")
            result, msg = self.proxy.add_stake(
                proxy_wallet=self.wallet,
                delegator=self.delegator,
                netuid=netuid,
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
                if staked_amount == 0:
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
        result, msg = self.proxy.remove_stake(
            proxy_wallet=self.wallet, 
            delegator=self.delegator, 
            hotkey=settings.DEFAULT_DEST_HOTKEY, 
            amount=bt.Balance.from_tao(float(amount)), 
            tolerance=0.5,
            netuid=netuid, 
        )
        if result:
            print(f"Stake removed: {self.wallet.coldkey.ss58_address} {amount} {netuid}")
            return True
        else:
            print(f"Unstake failed: {msg}")
            return False



class ColdkeySwapFetcher:
    def __init__(self, coldkey_swap_detector: ColdkeySwapDetector):
        self.coldkey_swap_detector = coldkey_swap_detector
        self.subtensor = bt.subtensor(NETWORK)
        self.subtensor_finney = bt.subtensor("finney")

        self.last_checked_block = self.subtensor.get_current_block()
        self.subnet_names = []
        self.owner_coldkeys = []
  
    def fetch_extrinsic_data(self, block_number):
        """Extract ColdkeySwapScheduled events from the data"""
        coldkey_swaps = []
        identity_changes = []
        print(f"Fetching events from chain")
        block_hash = self.subtensor.substrate.get_block_hash(block_id=block_number)
        extrinsics = self.subtensor.substrate.get_extrinsics(block_hash=block_hash)
        subnet_infos = self.subtensor.all_subnets()
        owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
        subnet_names = [subnet_info.subnet_name for subnet_info in subnet_infos]
        print(f"Fetched {len(extrinsics)} events from chain and {len(subnet_infos)} subnets")

        for ex in extrinsics:
            call = ex.value.get('call', {})
            if (
                call.get('call_module') == 'SubtensorModule' and
                call.get('call_function') == 'schedule_swap_coldkey'
            ):
                # Get the new coldkey from call_args
                args = call.get('call_args', [])
                new_coldkey = next((a['value'] for a in args if a['name'] == 'new_coldkey'), None)
                from_coldkey = ex.value.get('address', None)
                print(f"Swap scheduled: from {from_coldkey} to {new_coldkey}")
                
                try:
                    subnet_id = owner_coldkeys.index(from_coldkey)
                    swap_info = {
                        'old_coldkey': from_coldkey,
                        'new_coldkey': new_coldkey,
                        'subnet': subnet_id,
                    }
                    
                    coldkey_swaps.append(swap_info)
                except ValueError:
                    print(f"From coldkey {from_coldkey} not found in owner coldkeys")
                
        subnet_count = len(self.subnet_names)
        for i in range(subnet_count):
            if owner_coldkeys[i] != self.owner_coldkeys[i]:
                print(f"deregistering or coldkey swap for subnet {i}")
                continue

            if subnet_names[i] != self.subnet_names[i]:
                identity_change_info = {
                    'subnet': i,
                    'old_identity': self.subnet_names[i],
                    'new_identity': subnet_names[i],
                }
                identity_changes.append(identity_change_info)

        self.subnet_names = subnet_names
        self.owner_coldkeys = owner_coldkeys
        return coldkey_swaps, identity_changes
 
    def run(self):
        while True:
            current_block = self.subtensor.get_current_block()
            print(f"Current block: {current_block}")
            if current_block < self.last_checked_block:
                time.sleep(2)
                continue

            print(f"Fetching coldkey swaps for block {self.last_checked_block}")
            while True:
                try:
                    coldkey_swaps, identity_changes = self.fetch_extrinsic_data(self.last_checked_block)
                    if len(coldkey_swaps) > 0 or len(identity_changes) > 0:
                        try:
                            with open("coldkey_swaps.log", "a") as f:
                                for swap in coldkey_swaps:
                                    f.write(f"{swap}\n")
                        except Exception as e:
                            print(f"Error writing to file: {e}")
        
                        try:
                            with open("identity_changes.log", "a") as f:
                                for change in identity_changes:
                                    f.write(f"{change}\n")
                        except Exception as e:
                            print(f"Error writing to file: {e}")

                        self.stake_coldkey_swaps(coldkey_swaps, identity_changes)
                    else:
                        print("No coldkey swaps found")

                    self.last_checked_block += 1
                    break

                except Exception as e:
                    print(f"Error fetching coldkey swaps: {e}")
                    time.sleep(1)


    def stake_coldkey_swaps(self, coldkey_swaps, identity_changes):
        # Bug Review and Rewrite:
        # 1. If multiple swaps/changes for the same subnet are present in coldkey_swaps or identity_changes,
        #    coldkey_swap_detector.stake could be called multiple times for a subnet in a single run.
        # 2. The way the code checks is_staked twice (once in swaps, once in changes) may  
        #    cause a duplicate stake attempt for the same subnet if a swap and an identity change concern the same subnet.
        # 3. The amount value for a subnet in SAFE_SUBNETS could not exist if a new subnet was added, but that's handled (not in SAFE_SUBNETS).
        # 4. No input validation issues for .get('subnet') because the dicts are always parsed the same way but type safety could be considered.

        SAFE_SUBNETS = {
            7: 100, # pluton
            10: 100, # pluton
            11: 100, # pluton
            12: 100, # pluton
            13: 100, # pluton
            15: 100, # pluton
            16: 100, # pluton
            17: 100, # pluton
            18: 100, # pluton
            19: 100, # pluton
            20: 100, # pluton
            21: 100, # pluton
            22: 100, # pluton
            24: 100, # pluton
            25: 100, # pluton
            26: 100, # pluton
            27: 100, # pluton
            28: 100, # fish
            29: 100, # coldint
            31: 100, # pluton
            32: 100, # pluton
            33: 100, # pluton
            34: 100, # pluton
            36: 100, # pluton
            37: 100, # pluton
            38: 100, # pluton
            40: 100, # chunking
            42: 100, # pluton
            43: 100, # pluton
            44: 100, # pluton
            47: 100, # pluton       
            52: 100, # pluton
            53: 100, # pluton
            54: 100, # pluton
            55: 100, # pluton
            57: 100, # pluton
            58: 100, # pluton
            60: 100, # pluton
            61: 100, # pluton
            65: 100, # pluton
            69: 100, # pluton
            70: 100, # pluton
            72: 100, # pluton
            73: 100, # pluton
            74: 100, # pluton
            76: 100, # pluton
            77: 100, # pluton
            78: 40, # pluton
            79: 100, # pluton
            80: 100, # pluton
            82: 40, # pluton
            83: 100, # pluton
            84: 100, # pluton
            87: 40, # checkerchain
            88: 100, # pluton
            89: 100, # pluton
            90: 100, # pluton
            91: 100, # pluton
            93: 100, # pluton
            95: 100, # pluton
            96: 100, # pluton
            97: 100, # pluton
            98: 100, # pluton
            99: 100, # pluton
            101: 100, # pluton
            102: 100, # pluton
            103: 100, # pluton
            104: 100, # pluton
            105: 100, # pluton
            106: 100, # pluton
            107: 100, # pluton
            108: 100, # pluton
            109: 100, # pluton
            110: 100, # pluton
            111: 100, # pluton
            112: 100, # pluton
            113: 100, # pluton
            114: 20, # pluton
            115: 100, # pluton
            116: 100, # pluton
            117: 100, # pluton
            118: 100, # pluton
            119: 100, # pluton
            122: 100, # pluton
            126: 100, # pluton
            128: 100, # pluton
        }

        ALL_IN_SUBNETS = [
            28,
        ]
        # Collect all relevant subnets from swaps and changes
        stake_candidates = set()
        for swap in coldkey_swaps:
            try:
                subnet_id = int(swap['subnet'])
            except (KeyError, ValueError):
                continue
            if subnet_id in SAFE_SUBNETS:
                stake_candidates.add(subnet_id)

        for change in identity_changes:
            try:
                subnet_id = int(change['subnet'])
            except (KeyError, ValueError):
                continue
            if subnet_id in SAFE_SUBNETS:
                stake_candidates.add(subnet_id)

        # Only stake once per subnet
        for subnet_id in stake_candidates:
            if not self.coldkey_swap_detector.is_staked(subnet_id):
                if subnet_id in ALL_IN_SUBNETS:
                    self.coldkey_swap_detector.all_in(subnet_id)
                else:
                    amount = SAFE_SUBNETS[subnet_id]
                    self.coldkey_swap_detector.stake(subnet_id, amount)        




if __name__ == "__main__":
   
    proxy = Proxy(network=settings.NETWORK)
    proxy.init_runtime()
    coldkey_swap_detector = ColdkeySwapDetector(proxy)

    fetcher = ColdkeySwapFetcher(coldkey_swap_detector)
    fetcher.run()