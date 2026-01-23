import bittensor as bt
from typing import Dict, Tuple, Optional, Any

from app.core.config import settings
from app.services.proxy import Proxy
from app.services.wallets import wallets
from utils.tolerance import (
    get_stake_min_tolerance,
    get_unstake_min_tolerance,
    calculate_stake_limit_price,
    calculate_unstake_limit_price
)


class StakeService:
    """
    Service class for handling stake-related business logic.
    Encapsulates all staking operations including min tolerance calculations,
    stake/unstake operations with retry mechanisms, and error handling.
    """
    
    def __init__(self, wallets: Dict[str, Tuple[bt.Wallet, str]]):
        """
        Initialize the StakeService with wallets and proxy instance.
        
        Args:
            wallets: Dictionary mapping wallet names to (wallet, delegator) tuples
            proxy: Proxy instance for handling stake operations
        """
        self.wallets = wallets
        self.proxy = Proxy(settings.NETWORK, use_era=settings.USE_ERA)
        self.subtensor = bt.Subtensor(network=settings.NETWORK)
    
    def get_stake_min_tolerance(self, tao_amount: float, netuid: int) -> float:
        """
        Calculate the minimum tolerance for staking operations.
        
        Args:
            tao_amount: Amount in TAO
            netuid: Network/subnet ID
            
        Returns:
            float: Minimum tolerance value
        """
        return get_stake_min_tolerance(tao_amount, netuid, self.subtensor)


    def get_unstake_min_tolerance(self, tao_amount: float, netuid: int) -> float:
        """
        Calculate the minimum tolerance for unstaking operations.
        """
        return get_unstake_min_tolerance(tao_amount, netuid, self.subtensor)

    
    def stake(
        self,
        tao_amount: float,
        netuid: int,
        wallet_name: str,
        dest_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
        rate_tolerance: float = settings.DEFAULT_RATE_TOLERANCE,
        min_tolerance_staking: bool = settings.DEFAULT_MIN_TOLERANCE,
        allow_partial: bool = False,
        retries: int = settings.DEFAULT_RETRIES,
        use_era: bool = settings.USE_ERA
    ) -> Dict[str, Any]:
        """
        Execute staking operation with retry mechanism and error handling.
        
        Args:
            tao_amount: Amount to stake in TAO
            netuid: Network/subnet ID
            wallet_name: Name of the wallet to use
            dest_hotkey: Destination hotkey address
            rate_tolerance: Tolerance for rate calculations
            min_tolerance_staking: Whether to use minimum tolerance
            allow_partial: Whether to allow partial staking if full amount cannot be staked
            retries: Number of retry attempts
            use_era: Whether to use era parameter in extrinsic creation
            
        Returns:
            Dict containing success status, result, and min_tolerance
        """ 
        wallet, delegator = self.wallets[wallet_name]
        
        # Calculate rate tolerance
        try:
            price_with_tolerance = calculate_stake_limit_price(
                tao_amount=tao_amount,
                netuid=netuid,
                min_tolerance_staking=min_tolerance_staking,
                default_rate_tolerance=rate_tolerance,
                subtensor=self.subtensor
            )
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        
        # Execute staking with retry mechanism
        success = False
        msg = None

        for _ in range(retries):
            try:
                result, msg = self.proxy.add_stake(
                    amount=bt.Balance.from_tao(tao_amount),
                    proxy_wallet=wallet,
                    delegator=delegator,
                    netuid=netuid,
                    hotkey=dest_hotkey,
                    price_with_tolerance=price_with_tolerance,
                    allow_partial=allow_partial,
                    use_era=use_era,
                )
                
                if result:
                    success = True
                    break
            except Exception as e:
                msg = str(e)
                continue
        
        # This should never be reached, but required for type checking
        return {
            "success": success,
            "error": msg
        }
    
    def unstake(
        self,
        netuid: int,
        wallet_name: str,
        amount: Optional[float] = None,
        dest_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
        rate_tolerance: float = settings.DEFAULT_RATE_TOLERANCE,
        min_tolerance_unstaking: bool = settings.DEFAULT_MIN_TOLERANCE,
        allow_partial: bool = False,
        retries: int = settings.DEFAULT_RETRIES,
        use_era: bool = settings.USE_ERA
    ) -> Dict[str, Any]:
        """
        Execute unstaking operation with retry mechanism and error handling.
        
        Args:
            netuid: Network/subnet ID
            wallet_name: Name of the wallet to use
            amount: Amount to unstake (if None, unstakes all available)
            dest_hotkey: Destination hotkey address
            rate_tolerance: Tolerance for rate calculations
            min_tolerance_unstaking: Whether to use minimum tolerance
            allow_partial: Whether to allow partial unstaking if full amount cannot be unstaked
            retries: Number of retry attempts
            use_era: Whether to use era parameter in extrinsic creation
            
        Returns:
            Dict containing success status, result, and min_tolerance
        """ 
        wallet, delegator = self.wallets[wallet_name]
        
        # Determine amount to unstake
        if amount is None:
            # Unstake all available balance
            amount_balance = self.subtensor.get_stake(
                coldkey_ss58=delegator,
                hotkey_ss58=dest_hotkey,
                netuid=netuid
            )
        else:
            if amount < 1:
                # Unstake percentage of the total staked amount (100 * amount percent)
                total_stake = self.subtensor.get_stake(
                    coldkey_ss58=delegator,
                    hotkey_ss58=dest_hotkey,
                    netuid=netuid
                )
                amount_balance = total_stake * amount
            else:
                amount_balance = bt.Balance.from_tao(amount, netuid)

        if amount_balance.rao <= 0:
            return {
                "success": False,
                "error": "No balance to unstake"
            }
        
        # Calculate rate tolerance
        try:
            price_with_tolerance = calculate_unstake_limit_price(
                tao_amount=amount_balance.tao,
                netuid=netuid,
                min_tolerance_unstaking=min_tolerance_unstaking,
                default_rate_tolerance=rate_tolerance,
                subtensor=self.subtensor
            )
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        
        # Execute unstaking with retry mechanism
        success = False
        msg = None

        for _ in range(retries):
            try:
                result, msg = self.proxy.remove_stake(
                    netuid=netuid,
                    proxy_wallet=wallet,
                    delegator=delegator,
                    amount=amount_balance,
                    hotkey=dest_hotkey,
                    price_with_tolerance=price_with_tolerance,
                    allow_partial=allow_partial,
                    use_era=use_era,
                )
                if result:
                    success = True
                    break     
            except Exception as e:
                msg = str(e)                
                continue
        
        # This should never be reached, but required for type checking
        return {
            "success": success,
            "error": msg
        }
    
    def burned_register(self, wallet_name: str, hotkey: str, netuid: int) -> Dict[str, Any]:
        """
        Do burned register.
        
        Args:
            hotkey: Hotkey address
            netuid: Subnet ID
        """
        print(f"Wallet name: {wallet_name}")
        wallet, delegator = self.wallets[wallet_name]
        print(f"Wallet: {wallet}")
        print(f"Delegator: {delegator}")
        print(f"Hotkey: {hotkey}")
        print(f"Netuid: {netuid}")
        result, msg = self.proxy.burned_register(
            proxy_wallet=wallet,
            delegator=delegator,
            hotkey=hotkey,
            netuid=netuid,
        )
        return {
            "success": result,
            "error": msg
        }

    def move_stake(
        self,
        wallet_name: str,
        origin_netuid: int, 
        destination_netuid: int, 
        amount: Optional[float] = None, 
        origin_hotkey: str = settings.DEFAULT_DEST_HOTKEY, 
        destination_hotkey: str = settings.DEFAULT_DEST_HOTKEY, 
        retries: int = settings.DEFAULT_RETRIES,
        use_era: bool = settings.USE_ERA
    ) -> Dict[str, Any]:
        """
        Execute move stake operation with retry mechanism and error handling.
        
        Args:
            wallet_name: Name of the wallet to use
            origin_netuid: Source subnet ID
            destination_netuid: Destination subnet ID
            amount: Amount to move (if None, moves all available)
            origin_hotkey: Origin hotkey address
            destination_hotkey: Destination hotkey address
            retries: Number of retry attempts
            use_era: Whether to use era parameter in extrinsic creation
            
        Returns:
            Dict containing success status and error message
        """
        wallet, delegator = self.wallets[wallet_name]

        if amount is None:
            amount_balance = self.subtensor.get_stake(
                coldkey_ss58=delegator,
                hotkey_ss58=origin_hotkey,
                netuid=origin_netuid
            )
        else:
            if amount < 1:
                amount_balance = self.subtensor.get_stake(
                    coldkey_ss58=delegator,
                    hotkey_ss58=origin_hotkey,
                    netuid=origin_netuid
                ) * amount
            else:
                amount_balance = bt.Balance.from_tao(amount, origin_netuid)   
        
        # Execute move stake with retry mechanism
        success = False
        msg = None

        for _ in range(retries):
            try:
                result, msg = self.proxy.move_stake(
                    amount=amount_balance,
                    proxy_wallet=wallet,
                    delegator=delegator,
                    origin_hotkey=origin_hotkey,
                    destination_hotkey=destination_hotkey,
                    origin_netuid=origin_netuid,
                    destination_netuid=destination_netuid,
                    use_era=use_era,
                )
                if result:
                    success = True
                    break
            except Exception as e:
                msg = str(e)
                continue
        
        # This should never be reached, but required for type checking
        return {
            "success": success,
            "error": msg
        }

stake_service = StakeService(wallets)