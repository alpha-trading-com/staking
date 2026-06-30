import os
import sys
from collections import deque
from pathlib import Path

import bittensor as bt
import time

_HOOK_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HOOK_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

from hook_constants import SEEN_MAX, EXTRINSIC_START_CALL, EXTRINSIC_SUBMIT_ENCRYPTED, WHITELISTED_SUBNETS


def _remember_hash(extrinsic_hash, seen_order: deque, seen_set: set) -> bool:
    """Return True if already seen. Otherwise record hash and return False."""
    if extrinsic_hash in seen_set:
        return True
    if len(seen_order) == seen_order.maxlen:
        seen_set.discard(seen_order[0])
    seen_order.append(extrinsic_hash)
    seen_set.add(extrinsic_hash)
    return False


def fetch_extrinsic_data(
    subtensor: bt.Subtensor,
    owner_coldkeys: list,
    seen_order: deque,
    seen_set: set,
):
    """Extract ColdkeySwapScheduled events from the data"""
    events = []

    extrinsics = subtensor.substrate.retrieve_pending_extrinsics()

    for ex in extrinsics:
        call = ex.value.get('call', {})
        extrinsic_hash = ex.value.get('extrinsic_hash', None)
        call_module = call.get('call_module', None)
        call_function = call.get('call_function', None)
        # Get the new coldkey from call_args
        address = ex.value.get('address', None)
            
        if _remember_hash(extrinsic_hash, seen_order, seen_set):
            continue

        if address not in owner_coldkeys:
            continue
        subnet_id = owner_coldkeys.index(address)
        print(subnet_id)
        
        if subnet_id != 58:
            continue

        events.append({
            'event_type': EXTRINSIC_START_CALL,
            'subnet': subnet_id,
            'address': address,
        })

        # if (
        #     call_module == 'SubtensorModule' and
        #     call_function == 'start_call'
        # ):
        #     events.append({
        #         'event_type': EXTRINSIC_START_CALL,
        #         'subnet': subnet_id,
        #         'address': address,
        #     })

        # if call_module == 'MevShield' and call_function == 'submit_encrypted':
        #     events.append({
        #         'event_type': EXTRINSIC_SUBMIT_ENCRYPTED,
        #         'subnet': subnet_id,
        #         'address': address,
        #     })

    return events

def get_owner_coldkeys(subtensor: bt.Subtensor) -> list:
    subnet_infos = subtensor.all_subnets()
    owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
    return owner_coldkeys


if __name__ == "__main__":
    subtensor = bt.Subtensor("finney")
    seen_order: deque = deque(maxlen=SEEN_MAX)
    seen_set: set = set()
    last_checked_block = 0


    while True:
        current_block = subtensor.get_current_block()
        if current_block > last_checked_block:
            owner_coldkeys = get_owner_coldkeys(subtensor)
            last_checked_block = current_block
            print(owner_coldkeys.index("5CLUzEqecEfGFxMwHSU5vbgzpFQCGZuC56DDX354JKe69gtJ"))
        events = fetch_extrinsic_data(subtensor, owner_coldkeys, seen_order, seen_set)
        if events:
            print(events)
        time.sleep(1)
