import bittensor as bt
from typing import Optional
from app.core.config import settings


def get_stake_min_tolerance(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
    """
    Calculate the minimum tolerance for staking operations.
    
    Args:
        tao_amount: Amount in TAO
        netuid: Network/subnet ID
        subtensor: Optional Subtensor instance. If not provided, creates one using settings.NETWORK
        
    Returns:
        float: Minimum tolerance value
        
    Raises:
        ValueError: If subnet with netuid does not exist
    """
    if subtensor is None:
        subtensor = bt.Subtensor(network=settings.NETWORK)
    
    subnet = subtensor.subnet(netuid=netuid)
    if subnet is None:
        raise ValueError(f"Subnet with netuid {netuid} does not exist")
    
    min_tolerance = tao_amount / subnet.tao_in.tao
    return min_tolerance


def get_unstake_min_tolerance(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
    """
    Calculate the minimum tolerance for unstaking operations.
    
    Args:
        tao_amount: Amount in TAO
        netuid: Network/subnet ID
        subtensor: Optional Subtensor instance. If not provided, creates one using settings.NETWORK
        
    Returns:
        float: Minimum tolerance value
        
    Raises:
        ValueError: If subnet with netuid does not exist
    """
    if subtensor is None:
        subtensor = bt.Subtensor(network=settings.NETWORK)
    
    subnet = subtensor.subnet(netuid=netuid)
    if subnet is None:
        raise ValueError(f"Subnet with netuid {netuid} does not exist")
    
    min_tolerance = tao_amount / (tao_amount + subnet.alpha_in.tao)
    return min_tolerance


def calculate_stake_rate_tolerance(
    tao_amount: float,
    netuid: int,
    min_tolerance_staking: bool,
    default_rate_tolerance: float,
    subtensor: Optional[bt.Subtensor] = None
) -> float:
    """
    Calculate the rate tolerance for staking operations.
    If min_tolerance_staking is True, calculates minimum tolerance and adds 0.001.
    Otherwise, returns the default_rate_tolerance.
    
    Args:
        tao_amount: Amount in TAO
        netuid: Network/subnet ID
        min_tolerance_staking: Whether to use minimum tolerance
        default_rate_tolerance: Default tolerance value to use if not using min tolerance
        subtensor: Optional Subtensor instance. If not provided, creates one using settings.NETWORK
        
    Returns:
        float: Rate tolerance value
    """
    if min_tolerance_staking:
        min_tolerance = get_stake_min_tolerance(tao_amount, netuid, subtensor)
        return min_tolerance + 0.001
    else:
        return default_rate_tolerance


def calculate_unstake_rate_tolerance(
    tao_amount: float,
    netuid: int,
    min_tolerance_unstaking: bool,
    default_rate_tolerance: float,
    subtensor: Optional[bt.Subtensor] = None
) -> float:
    """
    Calculate the rate tolerance for unstaking operations.
    If min_tolerance_unstaking is True, calculates minimum tolerance and adds 0.001.
    Otherwise, returns the default_rate_tolerance.
    
    Args:
        tao_amount: Amount in TAO
        netuid: Network/subnet ID
        min_tolerance_unstaking: Whether to use minimum tolerance
        default_rate_tolerance: Default tolerance value to use if not using min tolerance
        subtensor: Optional Subtensor instance. If not provided, creates one using settings.NETWORK
        
    Returns:
        float: Rate tolerance value
    """
    if min_tolerance_unstaking:
        min_tolerance = get_unstake_min_tolerance(tao_amount, netuid, subtensor)
        return min_tolerance + 0.001
    else:
        return default_rate_tolerance

