import bittensor as bt
import time

from app.constants import ROUND_TABLE_HOTKEY
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger


NETWORK = "finney"
COLDKEY_SWAP_EVENT_TYPE = "COLDKEY_SWAP"
IDENTITY_CHANGE_EVENT_TYPE = "IDENTITY_CHANGE"
COLDKEY_SWAP_FINISHED_EVENT_TYPE = "COLDKEY_SWAP_FINISHED"
DEREGISTERED_EVENT_TYPE = "DEREGISTERED"

class ColdkeySwapFetcher:
    def __init__(self):
        self.subtensor = bt.subtensor(NETWORK)
        self.subtensor_finney = bt.subtensor("finney")

        self.last_checked_block = self.subtensor.get_current_block()
        self.subnet_names = []
        self.owner_coldkeys = []
        
  
    def fetch_extrinsic_data(self, block_number):
        """Extract ColdkeySwapScheduled events from the data"""
        events = []
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
                    event_info = {
                        'event_type': COLDKEY_SWAP_EVENT_TYPE,
                        'old_coldkey': from_coldkey,
                        'new_coldkey': new_coldkey,
                        'subnet': subnet_id,
                    }
                    
                    events.append(event_info)
                except ValueError:
                    print(f"From coldkey {from_coldkey} not found in owner coldkeys")

            if (
                call.get('call_module') == 'SubtensorModule' and
                call.get('call_function') == 'set_subnet_identity'
            ):
                
                # Get the new coldkey from call_args
                address = ex.value.get('address', None)
                subnet_id = owner_coldkeys.index(address)
                # To get the old identity, use the current subnet identity from subnet_infos[subnet_id].
                # To get the new identity, get from call_args['subnet_name'].
                try:
                    old_identity = subnet_infos[subnet_id].subnet_name
                    call_args = call.get('call_args', [])
                    new_identity = next((a['value'] for a in call_args if a['name'] == 'subnet_name'), None)
                    event_info = {
                        'event_type': IDENTITY_CHANGE_EVENT_TYPE,
                        'subnet': subnet_id,
                        'old_identity': old_identity,
                        'new_identity': new_identity,
                    }
                    events.append(event_info)
                except ValueError:
                    print(f"Address {address} not found in owner coldkeys")

        for i in range(len(self.subnet_names)):
            if self.owner_coldkeys[i] != owner_coldkeys[i]:
                if self.subnet_names[i] != subnet_names[i]:
                    event_info = {
                        'event_type': DEREGISTERED_EVENT_TYPE,
                        'subnet': i,
                    }
                    events.append(event_info)
                else:
                    event_info = {
                        'event_type': COLDKEY_SWAP_FINISHED_EVENT_TYPE,
                        'subnet': i,
                    }
                    events.append(event_info)

        self.subnet_names = subnet_names
        self.owner_coldkeys = owner_coldkeys
        return events
 
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
                    events = self.fetch_extrinsic_data(self.last_checked_block)
                    if len(events) > 0:
                        if callback:
                            callback(events)
                        break
                    else:
                        print("No coldkey swaps found")
                    
                    self.last_checked_block += 1
                    break

                except Exception as e:
                    print(f"Error fetching coldkey swaps: {e}")
                    time.sleep(1)