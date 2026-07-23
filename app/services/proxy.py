from sys import stderr
import bittensor as bt
from bittensor.core.settings import DEFAULT_MEV_PROTECTION
from bittensor.core.extrinsics.mev_shield import submit_encrypted_extrinsic
from pydantic_core.core_schema import int_schema
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import SubstrateRequestException
from typing import Optional, cast, List, Tuple

from bittensor.utils.balance import Balance, FixedPoint, fixed_to_float
from utils.stake_list import get_stake_custom

DEFAULT_WAIT_FOR_INCLUSION = True
DEFAULT_WAIT_FOR_FINALIZATION = False
DEFAULT_PERIOD = 128


class Proxy:
    def __init__(self, network: str):
        self.network = network
        self.subtensor = bt.Subtensor(network=network)


    def init_runtime(self):
        self.substrate = SubstrateInterface(
            url=self.network,
            ss58_format=42,
            type_registry_preset='substrate-node-template',
            auto_reconnect=True,
        )

    def compose_add_stake_proxy_call(
        self,
        delegator: str,
        netuid: int,
        hotkey: str,
        amount: Balance,
        price_with_tolerance: int,
        allow_partial: bool = False,
    ):
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='add_stake_limit',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_staked": amount.rao,
                "limit_price": price_with_tolerance,
                "allow_partial": allow_partial,
            }
        )
        return self.substrate.compose_call(
            call_module='Proxy',
            call_function='proxy',
            call_params={
                'real': delegator,
                'force_proxy_type': 'Staking',
                'call': call,
            }
        )

    def create_signed_proxy_extrinsic(
        self,
        proxy_wallet: bt.Wallet,
        proxy_call,
        nonce: Optional[int] = None,
        period: Optional[int] = None,
        block_number: Optional[int] = None,
    ):
        self.init_runtime()
        kwargs = {
            "call": proxy_call,
            "keypair": proxy_wallet.coldkey,
        }
        if nonce is not None:
            kwargs["nonce"] = nonce
        if period is not None:
            if block_number is None:
                block_number = self.substrate.get_block_number(None)
            kwargs["era"] = {"period": period, "current": block_number}
        return self.substrate.create_signed_extrinsic(**kwargs)

    def submit_prepared_extrinsic(
        self,
        extrinsic,
        wait_for_inclusion: bool = DEFAULT_WAIT_FOR_INCLUSION,
        wait_for_finalization: bool = DEFAULT_WAIT_FOR_FINALIZATION,
    ) -> tuple[bool, str]:
        receipt = self.substrate.submit_extrinsic(
            extrinsic,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
        )
        return receipt.is_success, str(receipt.error_message)

    def add_stake(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        netuid: int,
        hotkey: str,
        amount: Balance,
        price_with_tolerance: Optional[int] = None,
        allow_partial: bool = False,
        period: Optional[int] = None,
        mev_protection: bool = DEFAULT_MEV_PROTECTION
    ) -> tuple[bool, str]:
        self.init_runtime()
        if price_with_tolerance is not None:
            call = self.substrate.compose_call(
                call_module='SubtensorModule',
                call_function='add_stake_limit',
                call_params={
                    "hotkey": hotkey,
                    "netuid": netuid,
                    "amount_staked": amount.rao,
                    "limit_price": price_with_tolerance,
                    "allow_partial": allow_partial,
                }
            )
        else:
            call = self.substrate.compose_call(
                call_module='SubtensorModule',
                call_function='add_stake',
                call_params={
                    "hotkey": hotkey,
                    "netuid": netuid,
                    "amount_staked": amount.rao,
                }
            )
        return self._do_proxy_call(proxy_wallet, delegator, call, period=period, mev_protection=mev_protection)

    def remove_stake(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        netuid: int,
        hotkey: str,
        amount: Balance,
        price_with_tolerance: Optional[int] = None,
        allow_partial: bool = False,
        period: Optional[int] = None,
        mev_protection: bool = DEFAULT_MEV_PROTECTION,
    ) -> tuple[bool, str]:
        self.init_runtime()
        if price_with_tolerance is not None:
            call = self.substrate.compose_call(
                call_module='SubtensorModule',
                call_function='remove_stake_limit',
                call_params={
                    "hotkey": hotkey,
                    "netuid": netuid,
                    "amount_unstaked": amount.rao - 1,
                    "limit_price": price_with_tolerance,
                    "allow_partial": allow_partial,
                }
            )
        else:
            call = self.substrate.compose_call(
                call_module='SubtensorModule',
                call_function='remove_stake',
                call_params={
                    "hotkey": hotkey,
                    "netuid": netuid,
                    "amount_unstaked": amount.rao - 1,
                }
            )
        return self._do_proxy_call(proxy_wallet, delegator, call, period=period, mev_protection=mev_protection)


    def unstake_all(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        hotkey: str,
        unstake_all_alpha: bool = False,
        period: Optional[int] = None,
        mev_protection: bool = DEFAULT_MEV_PROTECTION,
    ) -> tuple[bool, str]:
        """Remove all stake from a hotkey across every subnet.

        When unstake_all_alpha is True, the alpha is moved to root (netuid 0) instead
        of being converted to TAO on the coldkey.
        """
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='unstake_all_alpha' if unstake_all_alpha else 'unstake_all',
            call_params={
                "hotkey": hotkey,
            }
        )
        return self._do_proxy_call(proxy_wallet, delegator, call, period=period, mev_protection=mev_protection)


    def move_stake(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        origin_hotkey: str,
        destination_hotkey: str,
        origin_netuid: int,
        destination_netuid: int,
        amount: Balance,
        period: Optional[int] = None,
        mev_protection: bool = DEFAULT_MEV_PROTECTION,
    ) -> tuple[bool, str]:
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='move_stake',
            call_params={
                'origin_hotkey': origin_hotkey,
                'destination_hotkey': destination_hotkey,
                'origin_netuid': origin_netuid,
                'destination_netuid': destination_netuid,
                'alpha_amount': amount.rao - 1,
            }
        )
        return self._do_proxy_call(proxy_wallet, delegator, call, period=period, mev_protection=mev_protection)


    def _do_proxy_call(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        call,
        proxy_type: str = 'Staking',
        period: Optional[int] = None,
        mev_protection: bool = DEFAULT_MEV_PROTECTION,
    ) -> tuple[bool, str]:
        proxy_call = self.substrate.compose_call(
            call_module='Proxy',
            call_function='proxy',
            call_params={
                'real': delegator,
                'force_proxy_type': proxy_type,
                'call': call,
            }
        )
        print("test-mev")
        if mev_protection:
            print("here mev protection", file=stderr, flush=True)
            extrinsic_response = submit_encrypted_extrinsic(
                subtensor=self.subtensor,
                wallet=proxy_wallet,
                call=proxy_call,
                period=None,
                raise_error=False,
                wait_for_inclusion=True,
                wait_for_finalization=False,
                wait_for_revealed_execution=False,
            )
            print(extrinsic_response.success, file=stderr, flush=True)
            print(extrinsic_response.error, file=stderr, flush=True)
            return extrinsic_response.success, extrinsic_response.error

        kwargs = {"call": proxy_call, "keypair": proxy_wallet.coldkey}
        if period is not None:
            kwargs["era"] = {"period": period}
        extrinsic = self.substrate.create_signed_extrinsic(**kwargs)

        
        receipt = self.substrate.submit_extrinsic(
            extrinsic,
            wait_for_inclusion=DEFAULT_WAIT_FOR_INCLUSION,
            wait_for_finalization=DEFAULT_WAIT_FOR_FINALIZATION,
        )
        return receipt.is_success, receipt.error_message

    def _batch_proxy_calls(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        calls: list,
        period: Optional[int] = None,
        mev_protection: bool = DEFAULT_MEV_PROTECTION,
    ) -> tuple[bool, str]:
        if not calls:
            return False, "No calls to batch"
        self.init_runtime()
        proxy_calls = []
        for call in calls:
            proxy_call = self.substrate.compose_call(
                call_module='Proxy',
                call_function='proxy',
                call_params={
                    'real': delegator,
                    'force_proxy_type': 'Staking',
                    'call': call,
                }
            )
            proxy_calls.append(proxy_call)
        batch_call = self.substrate.compose_call(
            call_module='Utility',
            call_function='batch',
            call_params={'calls': proxy_calls}
        )

        if mev_protection:
            extrinsic_response = submit_encrypted_extrinsic(
                subtensor=self.subtensor,
                wallet=proxy_wallet,
                call=batch_call,
                period=period,
                raise_error=False,
                wait_for_inclusion=True,
                wait_for_finalization=False,
                wait_for_revealed_execution=False,
            )
            return extrinsic_response.success, extrinsic_response.error

        kwargs = {"call": batch_call, "keypair": proxy_wallet.coldkey}
        if period is not None:
            kwargs["era"] = {"period": period}
        extrinsic = self.substrate.create_signed_extrinsic(**kwargs)
        receipt = self.substrate.submit_extrinsic(
            extrinsic,
            wait_for_inclusion=DEFAULT_WAIT_FOR_INCLUSION,
            wait_for_finalization=DEFAULT_WAIT_FOR_FINALIZATION,
        )
        return receipt.is_success, receipt.error_message
        
    def batch_stake_ops(
        self,
        proxy_wallet: bt.Wallet,
        delegator: str,
        operations: List[Tuple[str, int, str, int, Optional[int], bool]],
        period: Optional[int] = None,
        mev_protection: bool = DEFAULT_MEV_PROTECTION,
    ) -> tuple[bool, str]:
        self.init_runtime()
        calls = []
        for item in operations:
            action, netuid, hotkey_ss58, amount_rao = item[0], item[1], item[2], item[3]
            limit_price = item[4] if len(item) > 4 else None
            allow_partial = item[5] if len(item) > 5 else False
            if action == 'stake':
                if limit_price is not None:
                    call = self.substrate.compose_call(
                        call_module='SubtensorModule',
                        call_function='add_stake_limit',
                        call_params={
                            'hotkey': hotkey_ss58,
                            'netuid': netuid,
                            'amount_staked': amount_rao,
                            'limit_price': limit_price,
                            'allow_partial': allow_partial,
                        }
                    )
                else:
                    call = self.substrate.compose_call(
                        call_module='SubtensorModule',
                        call_function='add_stake',
                        call_params={
                            'hotkey': hotkey_ss58,
                            'netuid': netuid,
                            'amount_staked': amount_rao,
                        }
                    )
            else:
                amount_unstaked = max(0, amount_rao - 1)
                if limit_price is not None:
                    call = self.substrate.compose_call(
                        call_module='SubtensorModule',
                        call_function='remove_stake_limit',
                        call_params={
                            'hotkey': hotkey_ss58,
                            'netuid': netuid,
                            'amount_unstaked': amount_unstaked,
                            'limit_price': limit_price,
                            'allow_partial': allow_partial,
                        }
                    )
                else:
                    call = self.substrate.compose_call(
                        call_module='SubtensorModule',
                        call_function='remove_stake',
                        call_params={
                            'hotkey': hotkey_ss58,
                            'netuid': netuid,
                            'amount_unstaked': amount_unstaked,
                        }
                    )
            calls.append(call)
        return self._batch_proxy_calls(proxy_wallet, delegator, calls, period=period, mev_protection=mev_protection)


if __name__ == "__main__":
    proxy_wallet = bt.Wallet(name="black")
    delegator = "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2"
    amount = input("Enter amount to stake: ")
    netuid = input("Enter netuid: ")
    proxy_wallet.unlock_coldkey()
    proxy = Proxy("finney")
    is_success, error_message = proxy.add_stake(proxy_wallet, delegator, int(netuid), "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2", Balance.from_tao(int(amount)))
    print(is_success, error_message)
