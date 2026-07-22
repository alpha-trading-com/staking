import sys
from pathlib import Path

import bittensor as bt

_HOOK_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HOOK_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

from app.core.config import settings
from hook_constants import (
    WHITELISTED_SUBNETS,
    STAKE_AMOUNT_TAO,
    NETWORK,
    LIMIT_PRICE_IN_RAO,
)

_subtensor: bt.Subtensor | None = None
_proxy = None
_wallet: bt.Wallet | None = None
_delegator: str | None = None
_prebuilt_extrinsics: dict[int, object] = {}

PREBUILT_USE_ERA = False


def _get_staking_context():
    global _subtensor, _proxy, _wallet, _delegator
    if _subtensor is None:
        from app.services.proxy import Proxy

        _subtensor = bt.Subtensor(NETWORK)
        _proxy = Proxy(network=NETWORK)
        _proxy.init_runtime()
        wallet_name = settings.WALLET_NAMES[0]
        _wallet = bt.Wallet(name=wallet_name)
        _wallet.unlock_coldkey()
        _delegator = settings.DELEGATORS[settings.WALLET_NAMES.index(wallet_name)]
    return _subtensor, _proxy, _wallet, _delegator


def rebuild_prebuilt_extrinsics(force: bool = False):
    """Pre-sign add_stake extrinsics for each whitelisted subnet."""
    global _prebuilt_extrinsics

    if not force and _prebuilt_extrinsics:
        return

    _, proxy, wallet, delegator = _get_staking_context()
    amount = bt.Balance.from_tao(STAKE_AMOUNT_TAO)
    hotkey = settings.DEFAULT_DEST_HOTKEY

    new_extrinsics = {}
    for netuid in WHITELISTED_SUBNETS:
        proxy_call = proxy.compose_add_stake_proxy_call(
            delegator=delegator,
            netuid=netuid,
            hotkey=hotkey,
            amount=amount,
            price_with_tolerance=LIMIT_PRICE_IN_RAO,
            allow_partial=True,
        )
        new_extrinsics[netuid] = proxy.create_signed_proxy_extrinsic(
            proxy_wallet=wallet,
            proxy_call=proxy_call,
            period=64 if PREBUILT_USE_ERA else 0,
        )

    _prebuilt_extrinsics = new_extrinsics
    print(f"Prebuilt {len(_prebuilt_extrinsics)} stake extrinsics")


def add_stake(subnet: int, amount: float):
    print(f"Adding stake to subnet {subnet}")
    extrinsic = _prebuilt_extrinsics.get(subnet)
    if extrinsic is None:
        print(f"No prebuilt extrinsic for subnet {subnet}, rebuilding...")
        rebuild_prebuilt_extrinsics(force=True)
        extrinsic = _prebuilt_extrinsics.get(subnet)
        if extrinsic is None:
            print(f"Failed to build extrinsic for subnet {subnet}")
            return

    result, msg = _proxy.submit_prepared_extrinsic(
        extrinsic=extrinsic,
        wait_for_inclusion=True,
        wait_for_finalization=False,
    )
    if result:
        print(f"Stake submitted: {amount} TAO to subnet {subnet}")
    else:
        print(f"Stake failed on subnet {subnet}: {msg}")

    rebuild_prebuilt_extrinsics(force=True)


def add_stake_encrypted(subnet: int, amount: float):
    """Submit an MEV-protected (encrypted) add_stake for the given subnet.

    Unlike add_stake(), this can't use a pre-signed extrinsic: the encrypted
    path composes the call fresh and submits it via MevShield.submit_encrypted,
    so it's built and signed on demand.
    """
    print(f"Adding encrypted stake to subnet {subnet}")
    _, proxy, wallet, delegator = _get_staking_context()

    result, msg = proxy.add_stake(
        proxy_wallet=wallet,
        delegator=delegator,
        netuid=subnet,
        hotkey=settings.DEFAULT_DEST_HOTKEY,
        amount=bt.Balance.from_tao(amount),
        price_with_tolerance=LIMIT_PRICE_IN_RAO,
        allow_partial=True,
        mev_protection=True,
    )
    if result:
        print(f"Encrypted stake submitted: {amount} TAO to subnet {subnet}")
    else:
        print(f"Encrypted stake failed on subnet {subnet}: {msg}")


if __name__ == "__main__":
    _get_staking_context()
    rebuild_prebuilt_extrinsics(force=True)
    print("Prebuilt extrinsics rebuilt")
    import time
    time.sleep(30)
    #add_stake(16, 1)
