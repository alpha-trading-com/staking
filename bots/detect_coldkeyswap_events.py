import sys
import os

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt
import os
import requests
import json
import time
import threading
import requests

from bots.modules.coldkey_swap_detector import ColdkeySwapFetcher
from bots.modules.staking import Staking

fetcher = ColdkeySwapFetcher()
staking = Staking()

free_balance = staking.subtensor.get_balance(staking.delegator).tao - 0.5
print(f"Free balance: {free_balance}")
    
def stake_when_coldkey_swaps(coldkey_swaps, identity_changes):
    global free_balance
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
        #69: 100, # pluton
        70: 100, # pluton
        72: 100, # pluton
        73: 100, # pluton
        74: 100, # pluton
        76: 100, # pluton
        77: 100, # pluton
        #78: 40, # pluton
        79: 100, # pluton
        80: 100, # pluton
        #82: 40, # pluton
        83: 100, # pluton
        84: 100, # pluton
        86: 10,  # _______
        #87: 40, # checkerchain
        88: 100, # pluton
        89: 100, # pluton
        #90: 100, # ohmeg
        91: 100, # pluton
        93: 100, # pluton
        95: 50, # pluton
        96: 100, # pluton
        97: 100, # pluton
        98: 100, # pluton
        99: 100, # pluton
        101: 100, # pluton
        #102: 100, # pluton
        103: 100, # pluton
        104: 100, # pluton
        105: 20, # pluton
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
    subnet_infos = fetcher.subtensor_finney.all_subnets()
    pool_tao_in = [subnet_info.tao_in.tao for subnet_info in subnet_infos]
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
        if not staking.is_staked(subnet_id):
            if subnet_id in ALL_IN_SUBNETS:
                staking.all_in(subnet_id)
            else:
                amount = SAFE_SUBNETS[subnet_id]
                    
                if pool_tao_in[subnet_id] < 300:
                    amount = 25
                
                if amount > free_balance:
                    amount = free_balance
                
                staking.stake_until_success(subnet_id, amount)        


if __name__ == "__main__":
    fetcher.run(stake_when_coldkey_swaps)