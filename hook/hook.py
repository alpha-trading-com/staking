import sys
from collections import deque
from pathlib import Path
import bittensor as bt

_HOOK_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HOOK_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

from event_watch import fetch_extrinsic_data, get_owner_coldkeys
from pre_built_add_stake import add_stake, rebuild_prebuilt_extrinsics, _get_staking_context
from hook_constants import (
    SEEN_MAX,
    EXTRINSIC_START_CALL,
    EXTRINSIC_SUBMIT_ENCRYPTED,
    WHITELISTED_SUBNETS,
    STAKE_AMOUNT_TAO,
    BLACK_LISTED_COLDKEYS,
    PREBUILT_EXTRINSICS_INTERVAL,
)


def process_event(event: dict):
    event_type = event.get('event_type')
    subnet = event.get('subnet')
    address = event.get('address')
    if subnet not in WHITELISTED_SUBNETS:
        return

    if address in BLACK_LISTED_COLDKEYS:
        return

    if event_type == EXTRINSIC_START_CALL or event_type == EXTRINSIC_SUBMIT_ENCRYPTED:
        add_stake(subnet, STAKE_AMOUNT_TAO)


if __name__ == "__main__":
    subtensor, proxy, _, _ = _get_staking_context()
    rebuild_prebuilt_extrinsics(force=True)

    seen_order: deque = deque(maxlen=SEEN_MAX)
    seen_set: set = set()
    last_checked_block = 0
    bt.logging.off()

    print("Starting hook...")
    owner_coldkeys = []
    prev_extrinsics_len = 0

    while True:
        extrinsics = subtensor.substrate.retrieve_pending_extrinsics()
        cur_extrinsics_len = len(extrinsics)

        if prev_extrinsics_len > cur_extrinsics_len:
            #owner_coldkeys = get_owner_coldkeys(subtensor)
            print("New Block started")
            proxy.init_runtime()
            
        prev_extrinsics_len = cur_extrinsics_len

        events = fetch_extrinsic_data(extrinsics, owner_coldkeys, seen_order, seen_set)
        if events:
            for event in events:
                process_event(event)
