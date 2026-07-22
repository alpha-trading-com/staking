import sys
from collections import deque
from pathlib import Path
import bittensor as bt
from scalecodec import ScaleBytes

_HOOK_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HOOK_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

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



def retrieve_pending_extrinsics_safe(substrate) -> list:
    """Like substrate.retrieve_pending_extrinsics(), but tolerant of extrinsics
    the local metadata can't decode.

    The stock method decodes every pending extrinsic in a single loop, so one
    call referencing an unknown runtime type (e.g. "scale_info::405" from a
    newer/custom pallet) raises NotImplementedError and aborts the whole batch.
    Here each extrinsic is decoded independently and undecodable ones are
    skipped, so a single bad entry in the mempool doesn't crash the hook.
    """
    runtime = substrate.init_runtime()
    result_data = substrate.rpc_request("author_pendingExtrinsics", [])

    extrinsics = []
    for extrinsic_data in result_data["result"]:
        try:
            extrinsic = runtime.runtime_config.create_scale_object(
                "Extrinsic", metadata=runtime.metadata
            )
            extrinsic.decode(
                ScaleBytes(extrinsic_data),
                check_remaining=substrate.config.get("strict_scale_decode"),
            )
            extrinsics.append(extrinsic)
        except Exception:
            # Extrinsic uses a type this runtime metadata can't decode; ignore it.
            continue

    return extrinsics


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
    extrinsics: list,
    owner_coldkeys: list,
    seen_order: deque,
    seen_set: set,
):
    """Extract ColdkeySwapScheduled events from the data"""
    events = []

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

        if (
            call_module == 'SubtensorModule' and
            call_function == 'start_call'
        ):
            events.append({
                'event_type': EXTRINSIC_START_CALL,
                'subnet': subnet_id,
                'address': address,
            })

        if call_module == 'MevShield' and call_function == 'submit_encrypted':
            events.append({
                'event_type': EXTRINSIC_SUBMIT_ENCRYPTED,
                'subnet': subnet_id,
                'address': address,
            })

    return events

def get_owner_coldkeys(subtensor: bt.Subtensor) -> list:
    subnet_infos = subtensor.all_subnets()
    owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
    return owner_coldkeys


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
    block_count = 0

    while True:
        extrinsics = retrieve_pending_extrinsics_safe(subtensor.substrate)
        cur_extrinsics_len = len(extrinsics)

        if prev_extrinsics_len > cur_extrinsics_len:
            owner_coldkeys = get_owner_coldkeys(subtensor)
            print("New Block started")
            proxy.init_runtime()
            block_count += 1
            if block_count % PREBUILT_EXTRINSICS_INTERVAL == 0:
                rebuild_prebuilt_extrinsics(force=True)

            
        prev_extrinsics_len = cur_extrinsics_len

        events = fetch_extrinsic_data(extrinsics, owner_coldkeys, seen_order, seen_set)
        if events:
            for event in events:
                process_event(event)
