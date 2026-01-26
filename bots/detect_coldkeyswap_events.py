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
        21: 100,
        # 82:200,
        # 28:200,
        # 69:200,
        # 102:200,
        # 126:200,
    }

    ALL_IN_SUBNETS = {
        #28: 100,
    }
    
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
    
                #staking.stake_until_success(subnet_id, amount)        
                staking.stake(subnet_id, amount)
                #staking.move_stake(
                #     origin_netuid=82,
                #     origin_hotkey="5Gn3dRM5C6KjZ6u46PcjU54cYsmyKRtsM8TQZpcn8s1CNEYm",
                #     destination_netuid=subnet_id,
                # )

        except (KeyError, ValueError) as e:
            print(f"Error: {e}")
            continue

if __name__ == "__main__":
    staking.stake(22, 10)
    #fetcher.run(stake_when_coldkey_swaps)