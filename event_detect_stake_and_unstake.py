import bittensor as bt
import threading
import requests
import re
import sys
import os
import time
from typing import List

from app.constants import ROUND_TABLE_HOTKEY
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger


COLDKEYS_TO_DETECT = ["5GHrA88kdA9mZqGuEEz5JU1rmwERKVLUB7ZctBP4DHVQkZww"]
NETWORK = "finney"
MAX_STAKE_AMOUNT = 1
#NETWORK = "ws://161.97.128.68:9944"
subtensor = bt.subtensor(NETWORK)

class EventDetector:

    def __init__(self, proxy: Proxy):
        self.proxy = proxy
        self.subtensor = bt.subtensor(network=NETWORK)
        self.wallet_name = settings.WALLET_NAMES[0]
        self.wallet = bt.wallet(name=self.wallet_name)
        self.delegator = settings.DELEGATORS[settings.WALLET_NAMES.index(self.wallet_name)]
        self.unlock_wallet()

    def unlock_wallet(self):
        for i in range(3):
            try:
                self.wallet.unlock_coldkey()
                break
            except Exception as e:
                print(f"Error unlocking wallet {self.wallet_name}: {e}")
                continue
        if i == 2:
            raise Exception(f"Failed to unlock wallet {self.wallet_name}")

    def stake(self, netuid):
        amount = max(MAX_STAKE_AMOUNT, self.subtensor.get_stake(self.delegator, self.wallet.coldkey.ss58_address, netuid).tao)
        print(f"Staking {amount} TAO to netuid {netuid}")
        result, msg = self.proxy.add_stake(
            proxy_wallet=self.wallet,
            delegator=self.delegator,
            netuid=netuid,
            hotkey=settings.DEFAULT_DEST_HOTKEY,
            amount=bt.Balance.from_tao(float(amount)),
            tolerance=0.5,
        )
        if result:
            print(f"Stake added: {self.wallet.coldkey.ss58_address} {amount} {netuid}")
            return True
        else:
            print(f"Stake failed: {msg}")
            return False

    def unstake(self, netuid):
        amount = self.subtensor.get_stake(self.delegator, settings.DEFAULT_DEST_HOTKEY, netuid).tao
        print(f"Unstaking {amount} TAO from netuid {netuid}")
        result, msg = self.proxy.remove_stake(
            proxy_wallet=self.wallet, 
            delegator=self.delegator, 
            hotkey=settings.DEFAULT_DEST_HOTKEY, 
            amount=bt.Balance.from_tao(float(amount)), 
            tolerance=0.5,
            netuid=netuid, 
        )
        if result:
            print(f"Stake removed: {self.wallet.coldkey.ss58_address} {amount} {netuid}")
            return True
        else:
            print(f"Unstake failed: {msg}")
            return False


def extract_stake_events_from_data(events_data):
    """
    Extract stake and unstake events from blockchain event data.
    
    Args:
        events_data: List of event dictionaries from blockchain
    
    Returns:
        List of dictionaries containing stake/unstake event information
    """
    stake_events = []
    
    for event in events_data:
        phase = event.get('phase', {})
        event_info = event.get('event', {})
        
        # Check if this is a SubtensorModule event
        if event_info.get('module_id') == 'SubtensorModule':
            event_id = event_info.get('event_id')
            attributes = event_info.get('attributes', {})
            
            # Convert coldkey and hotkey to ss58 addresses if possible
            def to_ss58(addr_bytes, ss58_format = 42):
                if addr_bytes is None:
                    return None
                pubkey_bytes = bytes(addr_bytes).hex()
                if not pubkey_bytes.startswith("0x"):
                    pubkey_bytes = "0x" + pubkey_bytes
                return subtensor.substrate.ss58_encode(pubkey_bytes, ss58_format=ss58_format)
                
            if event_id == 'StakeAdded':
                # The attributes for StakeAdded are a tuple, not a dict.
                # Example: (
                #   ((coldkey_bytes,), (hotkey_bytes,), amount, stake, netuid, block_number)
                # )
                # So we need to unpack the tuple accordingly.
                if isinstance(attributes, tuple) and len(attributes) >= 6:
                    coldkey_tuple = to_ss58(attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                    hotkey_tuple = to_ss58(attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
                    amount = attributes[2]
                    # attributes[3] is stake, but we use amount for TAO
                    netuid = attributes[4]
                else:
                    coldkey_tuple = None
                    hotkey_tuple = None
                    amount = None
                    netuid = None
                stake_events.append({
                    'type': 'StakeAdded',
                    'coldkey': coldkey_tuple,
                    'hotkey': hotkey_tuple,
                    'netuid': netuid,
                    'amount': amount,
                    'amount_tao': amount / 1e9 if amount else 0,
                })
                
            elif event_id == 'StakeRemoved':
                # Extract unstake information - also a tuple
                if isinstance(attributes, tuple) and len(attributes) >= 6:
                    coldkey_tuple = to_ss58(attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                    hotkey_tuple = to_ss58(attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
                    amount = attributes[2]
                    netuid = attributes[4]
                else:
                    coldkey_tuple = None
                    hotkey_tuple = None
                    amount = None
                    netuid = None
                    block_number = None

                stake_events.append({
                    'type': 'StakeRemoved',
                    'coldkey': coldkey_tuple,
                    'hotkey': hotkey_tuple,
                    'netuid': netuid,
                    'amount': amount,
                    'amount_tao': amount / 1e9 if amount else 0,
                })
                
            elif event_id == 'StakeMoved':
                # Extract stake move information - also a tuple
                if isinstance(attributes, tuple) and len(attributes) >= 6:
                    coldkey_tuple = to_ss58(attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                    from_hotkey_tuple = to_ss58(attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
                    to_hotkey_tuple = to_ss58(attributes[3][0]) if isinstance(attributes[3], tuple) and len(attributes[3]) > 0 else attributes[3]
                    netuid = attributes[4]
                    amount = attributes[5]
                else:
                    coldkey_tuple = None
                    from_hotkey_tuple = None
                    to_hotkey_tuple = None
                    netuid = None
                    amount = None
                
                stake_events.append({
                    'type': 'StakeMoved',
                    'coldkey': coldkey_tuple,
                    'from_hotkey': from_hotkey_tuple,
                    'to_hotkey': to_hotkey_tuple,
                    'netuid': netuid,
                    'amount': amount,
                    'amount_tao': amount / 1e9 if amount else 0,
                })
    
    return stake_events


def check_stake_events(stake_events):
    global COLDKEYS_TO_DETECT

    for event in stake_events:
        netuid_val = int(event['netuid'])
        tao_amount = float(event['amount_tao'])
        coldkey = event['coldkey']
        
        # Green for stake added, red for stake removed (bright)
        if event['type'] == 'StakeAdded' and coldkey in COLDKEYS_TO_DETECT:
            print(f"Stake added: {coldkey} {tao_amount} {netuid_val}")
            return netuid_val
        else:
            continue

    return -1


if __name__ == "__main__":    
    max_stake_amount = int(input("Enter the max stake amount: "))
    proxy = Proxy(network=settings.NETWORK)
    proxy.init_runtime()
    event_detector = EventDetector(proxy)
    while True:
        block_number = subtensor.get_current_block()
        
        block_hash = subtensor.substrate.get_block_hash(block_id=block_number)
        events = subtensor.substrate.get_events(block_hash=block_hash)
        
        print(f"==============Block number: {block_number}==============")
        stake_events = extract_stake_events_from_data(events)
        netuid_val = check_stake_events(stake_events)
        if netuid_val != -1:
            result = event_detector.stake(netuid_val)
            if result:
                print(f"Stake added successfully: {netuid_val}")
            else:
                print(f"Stake failed to add: {netuid_val}")
            break;
        subtensor.wait_for_block()