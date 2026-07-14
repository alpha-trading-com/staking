import sys
from collections import deque
from pathlib import Path
import bittensor as bt
from bittensor.core.chain_data import subnet_info

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


if __name__ == "__main__":
    subtensor, proxy, _, _ = _get_staking_context()
    rebuild_prebuilt_extrinsics(force=True)

    seen_order: deque = deque(maxlen=SEEN_MAX)
    seen_set: set = set()
    last_checked_block = 0
    bt.logging.off()
    print("Starting hook...")

    limit_price = 0.015

    while True:
        subnet_info = subtensor.all_subnets()[15]
        price = subnet_info.price.tao
        print(price)
        if price < limit_price:
            add_stake(15, STAKE_AMOUNT_TAO)

        subtensor.wait_for_block()

        