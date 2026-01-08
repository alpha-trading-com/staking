import bittensor as bt
from bots.modules.staking import Staking

if __name__ == "__main__":
    staking = Staking()
    staking.stake(1, 30)
    #staking.unstake(1)