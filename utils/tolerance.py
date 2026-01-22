import bittensor as bt
from typing import Optional
from app.core.config import settings


def get_stake_min_tolerance(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
    return get_stake_min_tolerance_v2(tao_amount, netuid, subtensor)

def get_stake_min_tolerance_v1(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
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


def get_stake_min_tolerance_v2(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
    if subtensor is None:
        subtensor = bt.Subtensor(network=settings.NETWORK)
    subnet = subtensor.subnet(netuid=netuid)
    sim_swap = subtensor.sim_swap(
        origin_netuid=0,
        destination_netuid=netuid,
        amount=bt.Balance.from_tao(tao_amount)
    )
    
    if subnet is None:
        raise ValueError(f"Subnet with netuid {netuid} does not exist")
    
    deviation = subnet.price.tao - subnet.tao_in.tao / subnet.alpha_in.tao

    tao_amount_after = subnet.tao_in.tao + tao_amount
    alpha_amount_after = subnet.alpha_in.tao - sim_swap.alpha_amount.tao
    limit_price = (tao_amount_after / alpha_amount_after) + deviation
    reference_price = subnet.price.tao
    if reference_price == 0:
        raise ValueError("Reference price cannot be zero for tolerance calculation.")

    tolerance = (limit_price / reference_price) - 1
    return tolerance

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
    If min_tolerance_staking is True, calculates minimum tolerance.
    - If TOLERANCE_OFFSET starts with '*', multiplies min_tolerance by that value
    - Otherwise, adds TOLERANCE_OFFSET to min_tolerance
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
        # Check if TOLERANCE_OFFSET starts with '*' for multiplication
        if isinstance(settings.TOLERANCE_OFFSET, str) and settings.TOLERANCE_OFFSET.startswith('*'):
            multiplier = float(settings.TOLERANCE_OFFSET[1:])
            return min_tolerance * multiplier
        else:
            return min_tolerance + float(settings.TOLERANCE_OFFSET)
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
    If min_tolerance_unstaking is True, calculates minimum tolerance.
    - If TOLERANCE_OFFSET starts with '*', multiplies min_tolerance by that value
    - Otherwise, adds TOLERANCE_OFFSET to min_tolerance
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
        # Check if TOLERANCE_OFFSET starts with '*' for multiplication
        if isinstance(settings.TOLERANCE_OFFSET, str) and settings.TOLERANCE_OFFSET.startswith('*'):
            multiplier = float(settings.TOLERANCE_OFFSET[1:])
            return min_tolerance * multiplier
        else:
            return min_tolerance + float(settings.TOLERANCE_OFFSET)
    else:
        return default_rate_tolerance

