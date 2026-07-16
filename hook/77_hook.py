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

from app.core.config import settings
from app.services.proxy import Proxy
from hook_constants import SEEN_MAX, STAKE_AMOUNT_TAO
from utils.tolerance import calculate_stake_limit_price

NETUID_77 = 51
OWNER_COLDKEY_77 = "5GxxsUeYRyJSJKCuPeG1jZZiCummHJttmTNsfgDRSfxVnhGi"
STAKE_AMOUNT_TO_77 = 200

_proxy: Proxy | None = None
_wallet: bt.Wallet | None = None
_delegator: str | None = None


def _init_staking():
    global _proxy, _wallet, _delegator
    if _proxy is None:
        _proxy = Proxy(network=settings.NETWORK)
        _proxy.init_runtime()
        wallet_name = settings.WALLET_NAMES[0]
        _wallet = bt.Wallet(name=wallet_name)
        _wallet.unlock_coldkey()
        _delegator = settings.DELEGATORS[settings.WALLET_NAMES.index(wallet_name)]


def add_stake_limit():
    amount = STAKE_AMOUNT_TO_77
    limit_price = calculate_stake_limit_price(
        amount,
        NETUID_77,
        min_tolerance_staking=True,
        default_rate_tolerance=settings.DEFAULT_RATE_TOLERANCE,
        subtensor=_proxy.subtensor,
        tolerance_offset="*1.2",
    )
    result, msg = _proxy.add_stake(
        proxy_wallet=_wallet,
        delegator=_delegator,
        netuid=NETUID_77,
        hotkey=settings.DEFAULT_DEST_HOTKEY,
        amount=bt.Balance.from_tao(amount),
        price_with_tolerance=limit_price,
        use_era=settings.USE_ERA,
    )
    if result:
        print(f"Stake added: {amount} TAO to subnet {NETUID_77} (limit_price={limit_price})")
    else:
        print(f"Stake failed on subnet {NETUID_77}: {msg}")


def _remember_hash(extrinsic_hash, seen_order: deque, seen_set: set) -> bool:
    if extrinsic_hash in seen_set:
        return True
    if len(seen_order) == seen_order.maxlen:
        seen_set.discard(seen_order[0])
    seen_order.append(extrinsic_hash)
    seen_set.add(extrinsic_hash)
    return False


def fetch_extrinsic_data_process(
    subtensor: bt.Subtensor,
    seen_order: deque,
    seen_set: set,
):
    extrinsics = subtensor.substrate.retrieve_pending_extrinsics()
    print(f"Fetched {len(extrinsics)} events from mempool")

    for ex in extrinsics:
        call = ex.value.get('call', {})
        extrinsic_hash = ex.value.get('extrinsic_hash', None)
        call_module = call.get('call_module', None)
        call_function = call.get('call_function', None)
        address = ex.value.get('address', None)

        if _remember_hash(extrinsic_hash, seen_order, seen_set):
            continue

        if address != OWNER_COLDKEY_77:
            continue

        if call_module == 'MevShield' and call_function == 'submit_encrypted':
            print(f"SN{NETUID_77} owner submit_encrypted detected, staking...")
            add_stake_limit()


if __name__ == "__main__":
    _init_staking()

    subtensor = bt.Subtensor("finney")
    seen_order: deque = deque(maxlen=SEEN_MAX)
    seen_set: set = set()

    print(f"Starting SN{NETUID_77} hook...")

    while True:
        print("77 hook running...")
        fetch_extrinsic_data_process(subtensor, seen_order, seen_set)
