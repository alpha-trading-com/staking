import bittensor as bt

import sys
import os

# Ensure parent dir is in sys.path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "bots"))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from bots.modules.coldkey_swap_detector import ColdkeySwapFetcher
from bots.modules.staking import Staking
from utils.sim_swap import sim_swap
from utils.sim_swap import TAO_TO_RAO


def print_all_owner_wallets_stake_info(sell_tao_amount):
    # Fetch all subnets with owner_coldkeys and subnet_name
    subtensor = bt.Subtensor(network="finney")
    subnet_infos = subtensor.all_subnets()
    print(f"Found {len(subnet_infos)} subnets.")

    subnets = []
    for i, subnet in enumerate(subnet_infos):
        if i == 0:
            continue
        owner_coldkey = subnet.owner_coldkey
        stake_info = subtensor.get_stake_info_for_coldkey(owner_coldkey)
        stake_amount = 0
        for info in stake_info:
            if info.netuid == i:
                stake_amount += info.stake.tao
        sim_swap_result = sim_swap(subtensor, i, 0, stake_amount)
        tao_amount = sim_swap_result["tao_amount"] / TAO_TO_RAO
        subnets.append({
            "netuid": i,
            "tao_amount": tao_amount
        })

    subnets.sort(key=lambda x: abs(x["tao_amount"] - sell_tao_amount), reverse=True)
    return subnets
if __name__ == '__main__':
    subnets = print_all_owner_wallets_stake_info(sell_tao_amount=1750)
    for subnet in subnets:
        print(f"Netuid: {subnet['netuid']} |  Sim Swap Result: {round(subnet['tao_amount'], 2)}")
