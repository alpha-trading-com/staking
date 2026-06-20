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

from event_watch import fetch_extrinsic_data, get_owner_coldkeys
from hook_constants import (
    SEEN_MAX, 
    EXTRINSIC_START_CALL, 
    EXTRINSIC_SUBMIT_ENCRYPTED, 
    WHITELISTED_SUBNETS, 
    STAKE_AMOUNT_TAO, 
    BLACK_LISTED_COLDKEYS,
    NETWORK,
    STAKE_PRICE_UPPER_BOUND,
    MIN_STAKE_RAO,
)

_subtensor: bt.Subtensor | None = None
_proxy = None
_wallet: bt.Wallet | None = None
_delegator: str | None = None


def _get_staking_context():
    global _subtensor, _proxy, _wallet, _delegator
    if _subtensor is None:
        from app.core.config import settings
        from app.services.proxy import Proxy

        _subtensor = bt.Subtensor(NETWORK)
        _proxy = Proxy(network=NETWORK, use_era=settings.USE_ERA)
        _proxy.init_runtime()
        wallet_name = settings.WALLET_NAMES[0]
        _wallet = bt.Wallet(name=wallet_name)
        _wallet.unlock_coldkey()
        _delegator = settings.DELEGATORS[settings.WALLET_NAMES.index(wallet_name)]
    return _subtensor, _proxy, _wallet, _delegator


def add_stake(subnet: int, amount: float):
    from app.core.config import settings
    from utils.tolerance import calculate_stake_limit_price

    subtensor, proxy, wallet, delegator = _get_staking_context()

    subnet_info = subtensor.subnet(netuid=subnet)
    if subnet_info is None:
        print(f"Subnet {subnet} does not exist, skipping stake")
        return

    try:
        alpha_price = subnet_info.alpha_to_tao(1)
        print(f"Subnet {subnet} alpha price: {alpha_price} TAO")
    except Exception as e:
        print(f"Error getting price for subnet {subnet}: {e}")
        return

    if alpha_price >= bt.Balance.from_tao(STAKE_PRICE_UPPER_BOUND):
        print(
            f"Subnet {subnet} price {alpha_price} TAO >= "
            f"bound {STAKE_PRICE_UPPER_BOUND}, skipping stake"
        )
        return

    amount = min(amount, subtensor.get_balance(delegator).tao)
    amount_balance = bt.Balance.from_tao(amount)
    if amount_balance.rao < MIN_STAKE_RAO:
        print(f"Amount {amount} TAO below minimum for subnet {subnet}, skipping stake")
        return

    limit_price = calculate_stake_limit_price(
        amount,
        subnet,
        min_tolerance_staking=True,
        default_rate_tolerance=0.035,
        subtensor=subtensor,
        tolerance_offset="*1.2",
    )

    result, msg = proxy.add_stake(
        proxy_wallet=wallet,
        delegator=delegator,
        netuid=subnet,
        hotkey=settings.DEFAULT_DEST_HOTKEY,
        amount=amount_balance,
        price_with_tolerance=limit_price,
        use_era=settings.USE_ERA,
    )
    if result:
        print(f"Stake added: {amount} TAO to subnet {subnet}")
    else:
        print(f"Stake failed on subnet {subnet}: {msg}")

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
        #If the price is below 0.015, stake 200 TAO



if __name__ == "__main__":
    subtensor = bt.Subtensor(NETWORK)
    seen_order: deque = deque(maxlen=SEEN_MAX)
    seen_set: set = set()
    last_checked_block = 0
    print("Starting hook...")

    while True:
        current_block = subtensor.get_current_block()
        if current_block > last_checked_block:
            owner_coldkeys = get_owner_coldkeys(subtensor)
            last_checked_block = current_block
        events = fetch_extrinsic_data(subtensor, owner_coldkeys, seen_order, seen_set)
        if events:
            for event in events:
                process_event(event)
