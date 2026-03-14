import os
import random
import bittensor as bt
from substrateinterface import SubstrateInterface, Keypair

# Connect to the Substrate node (update URL as needed)
substrate = SubstrateInterface(
    url="wss://entrypoint-finney.opentensor.ai:443",
    ss58_format=42,
    type_registry_preset='substrate-node-template'
)

# Dynamic tip (in rao). 1 TAO = 10^9 rao.
# - TX_TIP_RAO: fixed tip (e.g. 50000). Unset = use random.
# - TX_TIP_MIN / TX_TIP_MAX: random range in rao (default 1000–1000000).
def get_tip_rao() -> int:
    return random.randint(0, 10000)

wallet = bt.Wallet(name="soon")
wallet.unlock_coldkey()
# Load the keypair (replace with your own private key or mnemonic)
# Example using mnemonic
keypair = wallet.coldkey

# Compose the call to announce the ML‑KEM public key as the next key in mevShield
call = substrate.compose_call(
    call_module='MevShield',
    call_function='announce_next_key',
    call_params={
        'public_key': b'\x01\x02\x03\x04'  # Replace with your actual ML‑KEM public key bytes
    }

)

tip_rao = get_tip_rao()
# Create signed extrinsic with dynamic tip
extrinsic = substrate.create_signed_extrinsic(
    call=call,
    keypair=keypair,
    tip=tip_rao,
)

# Submit the extrinsic and print the receipt or error
print("Submitting with tip: {} rao".format(tip_rao))
try:
    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    print("Extrinsic '{}' sent and included in block '{}'".format(receipt.extrinsic_hash, receipt.block_hash))
except Exception as e:
    print("Failed to submit extrinsic:", e)