import sys
import os

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt
import os
import requests

from bots.modules.coldkey_swap_detector import ColdkeySwapFetcher
from bots.modules.staking import Staking


from bots.constants import (
    SAFE_SUBNETS, 
    SAFE_SUBNETS_SLEEP, 
    ALL_IN_SUBNETS,
)


fetcher = ColdkeySwapFetcher()
staking = Staking()

is_sleeping = False
def stake_when_coldkey_swaps(coldkey_swaps, identity_changes):
    print(f"Is sleeping: {is_sleeping}")
    

    safe_subnets = SAFE_SUBNETS if not is_sleeping else SAFE_SUBNETS_SLEEP

    subnet_infos = fetcher.subtensor_finney.all_subnets()
    pool_tao_in = [subnet_info.tao_in.tao for subnet_info in subnet_infos]
    # Collect all relevant subnets from swaps and changes
    stake_candidates = set()
    for swap in coldkey_swaps:
        try:
            subnet_id = int(swap['subnet'])
        except (KeyError, ValueError):
            continue
        if subnet_id in safe_subnets:
            stake_candidates.add(subnet_id)

    for change in identity_changes:
        try:
            subnet_id = int(change['subnet'])
        except (KeyError, ValueError):
            continue
        if subnet_id in safe_subnets:
            stake_candidates.add(subnet_id)

    # Only stake once per subnet
    for subnet_id in stake_candidates:
        if not staking.is_staked(subnet_id):
            if subnet_id in ALL_IN_SUBNETS:
                staking.all_in(subnet_id)
            else:
                amount = safe_subnets[subnet_id]
                    
                if pool_tao_in[subnet_id] < 300:
                    amount = 25

                staking.stake_until_success(subnet_id, amount)        


if __name__ == "__main__":
    confirm = input("Are you sleeping? (y/n): ")
    if confirm == "y":
        is_sleeping = True
    else:
        is_sleeping = False
    print(f"Is sleeping: {is_sleeping}")
    fetcher.run(stake_when_coldkey_swaps)