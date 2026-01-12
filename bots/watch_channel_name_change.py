import bittensor as bt
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional

from app.constants import ROUND_TABLE_HOTKEY
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger



NETWORK = "finney"

MAX_STAKE_AMOUNT = 1

class ChannelMonitorStaker:

    def __init__(self, proxy: Proxy):
        self.proxy = proxy
        self.subtensor = bt.Subtensor(network=NETWORK)
        self.wallet_name = settings.WALLET_NAMES[0]
        self.wallet = bt.Wallet(name=self.wallet_name)
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

    def is_staked(self, netuid):
        return self.subtensor.get_stake(self.delegator, settings.DEFAULT_DEST_HOTKEY, netuid).tao > 0

    def stake(self, netuid, amount):
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


class ChannelMonitorBot:
    """Monitor Discord guild channels for creation, deletion, and name changes"""
    
    # Channel type mappings for better display
    CHANNEL_TYPES = {
        0: "Text",
        2: "Voice",
        4: "Category",
        5: "Announcement",
        13: "Stage",
        15: "Forum",
        16: "Media"
    }
    
    def __init__(self, staker: ChannelMonitorStaker, bot_token: str, guild_id: str, webhook_url: Optional[str] = None):
        """
        Initialize the channel monitor bot
        
        Args:
            bot_token: Discord bot token for authentication
            guild_id: Guild/Server ID to monitor
            webhook_url: Optional webhook URL for notifications
        """
        self.staker = staker
        self.bot_token = bot_token
        self.guild_id = guild_id
        self.webhook_url = webhook_url
        self.channels_state: Dict[str, Dict] = {}  # Store channel data by ID
        
    def get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Discord API"""
        return {
            "Authorization": f"{self.bot_token}",
            "Content-Type": "application/json"
        }
    
    def fetch_all_channels(self) -> List[Dict]:
        """Fetch all channels from the Discord guild"""
        url = f"https://discord.com/api/v10/guilds/{self.guild_id}/channels"
        
        retries = 5
        while retries > 0:
            try:
                response = requests.get(url, headers=self.get_headers())
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Error fetching channels: {response.status_code}")
                    print(f"Response: {response.text}")
                    retries -= 1
                    time.sleep(2)
            except Exception as e:
                print(f"Exception while fetching channels: {e}")
                retries -= 1
                time.sleep(2)
        
        print("Failed to fetch channels after retries")
        return []
    
    def get_channel_type_name(self, channel_type: int) -> str:
        """Get human-readable channel type name"""
        return self.CHANNEL_TYPES.get(channel_type, f"Unknown({channel_type})")
    
    def create_embed(self, event_type: str, channel_data: Dict, old_name: str = None) -> Dict:
        """
        Create Discord embed for channel event
        
        Args:
            event_type: Type of event (created, deleted, renamed)
            channel_data: Channel information
            old_name: Previous channel name (for rename events)
        """
        channel_id = channel_data.get('id')
        channel_name = channel_data.get('name', 'Unknown')
        channel_type = channel_data.get('type', 0)
        type_name = self.get_channel_type_name(channel_type)
        
        # Set color and description based on event type
        if event_type == "created":
            color = 0x00ff00  # Green for creation
            title = "🆕 New Channel Created"
            description = f"**{channel_name}** ({type_name})"
        elif event_type == "deleted":
            color = 0xff0000  # Red for deletion
            title = "🗑️ Channel Deleted"
            description = f"**{channel_name}** ({type_name})"
        elif event_type == "renamed":
            color = 0xffff00  # Yellow for rename
            title = "✏️ Channel Renamed"
            description = f"**{old_name}** → **{channel_name}** ({type_name})"
        else:
            color = 0x808080  # Gray for unknown
            title = "Channel Event"
            description = f"**{channel_name}** ({type_name})"
        
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "Channel ID",
                    "value": f"`{channel_id}`",
                    "inline": True
                },
                {
                    "name": "Type",
                    "value": type_name,
                    "inline": True
                }
            ]
        }
        
        # Add parent category if exists
        if channel_data.get('parent_id'):
            embed["fields"].append({
                "name": "Category",
                "value": f"<#{channel_data['parent_id']}>",
                "inline": True
            })
        
        return embed
    
    def send_webhook_notification(self, embeds: List[Dict]):
        """Send notification to Discord webhook"""
        if not self.webhook_url or not embeds:
            return
        
        payload = {
            "content": "@everyone ",
            "embeds": embeds,
            "username": "Channel Monitor",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/1.png"
        }
        
        retries = 5
        while retries > 0:
            try:
                response = requests.post(self.webhook_url, json=payload)
                if response.status_code in [200, 204]:
                    print(f"✓ Sent {len(embeds)} notification(s) to webhook")
                    return
                else:
                    print(f"Failed to send webhook: {response.status_code}")
                    retries -= 1
                    time.sleep(2)
            except Exception as e:
                print(f"Error sending webhook: {e}")
                retries -= 1
                time.sleep(2)
        
        print("Failed to send webhook after retries")
    
    def initialize_state(self):
        """Initialize the channel state by fetching current channels"""
        print(f"\n{'='*60}")
        print("Initializing Channel Monitor Bot")
        print(f"{'='*60}")
        
        channels = self.fetch_all_channels()
        if not channels:
            print("Warning: No channels fetched during initialization")
            return
        
        for channel in channels:
            channel_id = channel.get('id')
            if channel_id is None:
                # Skip channels without IDs
                continue
            
            # Store raw channel data from API
            self.channels_state[channel_id] = {
                'id': channel_id,
                'name': channel.get('name', ''),
                'type': channel.get('type', 0),
                'parent_id': channel.get('parent_id')
            }
        
        print(f"\n{'='*60}")
        print(f"Initial State: {len(self.channels_state)} channels")
        print(f"{'='*60}\n")
        
        # Display current channels grouped by type
        channels_by_type = {}
        for channel in self.channels_state.values():
            channel_type = channel['type']
            type_name = self.get_channel_type_name(channel_type)
            
            if type_name not in channels_by_type:
                channels_by_type[type_name] = []
            
            # Display channel name, handle empty string
            display_name = channel.get('name', '') or 'Unknown'
            channels_by_type[type_name].append(display_name)
        
        for type_name, names in sorted(channels_by_type.items()):
            print(f"{type_name} Channels ({len(names)}):")
            for name in sorted(names):
                print(f"  • {name}")
            print()
    
    def check_for_changes(self):
        """Check for channel changes and send notifications"""
        channels = self.fetch_all_channels()
        if not channels:
            print("Warning: Failed to fetch channels")
            return
        
        # Filter out any channels without IDs and create channel ID set
        valid_channels = [ch for ch in channels if ch.get('id') is not None]
        current_channel_ids = {ch['id'] for ch in valid_channels}
        previous_channel_ids = set(self.channels_state.keys())
        
        embeds = []
        
        # Check for new channels (created)
        new_channel_ids = current_channel_ids - previous_channel_ids
        for channel_id in new_channel_ids:
            channel = next((ch for ch in valid_channels if ch['id'] == channel_id), None)
            if channel:
                # Use raw channel name from API, not processed with 'Unknown' fallback
                channel_name = channel.get('name', '')
                if not channel_name:
                    channel_name = 'Unknown'
                    
                channel_type = self.get_channel_type_name(channel.get('type', 0))
                print(f"✓ NEW CHANNEL: {channel_name} ({channel_type})")
                
                # Add to state - store raw values from API
                self.channels_state[channel_id] = {
                    'id': channel_id,
                    'name': channel.get('name', ''),
                    'type': channel.get('type', 0),
                    'parent_id': channel.get('parent_id')
                }
                
                # Create embed for notification
                embeds.append(self.create_embed("created", channel))
        
        # Check for deleted channels
        deleted_channel_ids = previous_channel_ids - current_channel_ids
        for channel_id in deleted_channel_ids:
            channel_data = self.channels_state[channel_id]
            channel_name = channel_data.get('name', 'Unknown')
            channel_type = self.get_channel_type_name(channel_data.get('type', 0))
            print(f"✗ DELETED CHANNEL: {channel_name} ({channel_type})")
            
            # Create embed for notification
            embeds.append(self.create_embed("deleted", channel_data))
            
            # Remove from state
            del self.channels_state[channel_id]
        
        # Check for renamed channels and other property changes
        for channel in valid_channels:
            channel_id = channel['id']
            if channel_id in self.channels_state:
                old_name = self.channels_state[channel_id].get('name', '')
                new_name = channel.get('name', '')
                
                # Only trigger rename event if names actually differ (not None vs empty string)
                if old_name != new_name and new_name:
                    channel_type = self.get_channel_type_name(channel.get('type', 0))
                    display_old_name = old_name if old_name else 'Unknown'
                    display_new_name = new_name if new_name else 'Unknown'
                    print(f"✏ RENAMED CHANNEL: {display_old_name} → {display_new_name} ({channel_type})")
                    
                    # Update entire channel state with current values
                    self.channels_state[channel_id] = {
                        'id': channel_id,
                        'name': channel.get('name', ''),
                        'type': channel.get('type', 0),
                        'parent_id': channel.get('parent_id')
                    }
                    
                    # Create embed for notification
                    embeds.append(self.create_embed("renamed", channel, old_name=display_old_name))
        
        # Send all notifications at once
        if embeds:
            self.send_webhook_notification(embeds)
        else:
            print("No channel changes detected")
    
    def run(self, check_interval: int = 60):
        """
        Run the channel monitor with periodic checks
        
        Args:
            check_interval: Seconds between checks (default: 60)
        """
        # Initialize with current state
        self.initialize_state()
        
        print(f"\n{'='*60}")
        print(f"Starting Channel Monitor")
        print(f"Check Interval: {check_interval} seconds")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        # Start monitoring loop
        while True:
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n[{timestamp}] Checking for channel changes...")
                
                self.check_for_changes()
                
                print(f"Next check in {check_interval} seconds...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n\nChannel monitor stopped by user")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                print("Continuing in 60 seconds...")
                time.sleep(60)


def main():
    """Main entry point"""
    proxy = Proxy(network=settings.NETWORK)
    proxy.init_runtime()
    staker = ChannelMonitorStaker(proxy)
    # Configuration - Replace these with your actual values
    BOT_TOKEN = "MTIwNjY0MzY5NDEyODg1NzEwMw.GkBLIU.9yxK6xuxJbqYOJ7IcBFekUufJqNRCu-YqNE_I8"
    GUILD_ID = "799672011265015819"
    
    # Optional: Add webhook URL for notifications
    # WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
    WEBHOOK_URL = "https://discord.com/api/webhooks/1442889980962803855/L-rzuMa5KjmOdW_tQHWFFAG7gMiYBJ6FE8NkuV-qFmWhwogDF_9sGSVzmbZwt0NsvUfa"  # Set to None to disable webhook notifications
    
    # Create and run the monitor
    monitor = ChannelMonitorBot(
        staker=staker,
        bot_token=BOT_TOKEN,
        guild_id=GUILD_ID,
        webhook_url=WEBHOOK_URL
    )
    
    # Check every 60 seconds (adjust as needed)
    monitor.run(check_interval=60)


if __name__ == "__main__":
    main()