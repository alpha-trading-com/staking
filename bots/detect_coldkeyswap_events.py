import sys
import os

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)



from bots.modules.coldkey_swap_detector import (
    COLDKEY_SWAP_FINISHED_EVENT_TYPE,
    DEREGISTERED_EVENT_TYPE,
)

from bots.modules.coldkey_swap_detector import ColdkeySwapFetcher
from bots.modules.staking import Staking

fetcher = ColdkeySwapFetcher()
staking = Staking()
    
def stake_when_coldkey_swaps(events):
    SAFE_SUBNETS = {
        82:100,
        28:100,
        69:100,
    }

    ALL_IN_SUBNETS = {
        #28: 100,
    }
    
    subnet_infos = fetcher.subtensor_finney.all_subnets()
    pool_tao_in = [subnet_info.tao_in.tao for subnet_info in subnet_infos]
    # Collect all relevant subnets from swaps and changes
    for event in events:
        try:
            event_type = event['event_type']
            if event_type == COLDKEY_SWAP_FINISHED_EVENT_TYPE:
                continue
        
            if event_type == DEREGISTERED_EVENT_TYPE:
                continue

            subnet_id = int(event['subnet'])
            if subnet_id in ALL_IN_SUBNETS:
                staking.all_in(subnet_id)
            else:
                amount = SAFE_SUBNETS[subnet_id]
                    
                if pool_tao_in[subnet_id] < 300:
                    amount = 25

                staking.stake_until_success(subnet_id, amount)        

        except (KeyError, ValueError):
            continue

if __name__ == "__main__":
    fetcher.run(stake_when_coldkey_swaps)