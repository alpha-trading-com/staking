import bittensor as bt
import time

from app.constants import ROUND_TABLE_HOTKEY
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger


NETWORK = "finney"

class ColdkeySwapFetcher:
    def __init__(self):
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
 
    def run(self, callback = None):
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
                        if callback:
                            callback(coldkey_swaps, identity_changes)
                    else:
                        print("No coldkey swaps found")

                    self.last_checked_block += 1
                    break

                except Exception as e:
                    print(f"Error fetching coldkey swaps: {e}")
                    time.sleep(1)

