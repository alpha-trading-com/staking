import bittensor as bt
import scalecodec.utils.ss58 as ss58

def to_ss58(addr_bytes, ss58_format = 42):
    if addr_bytes is None:
        return None
    pubkey_bytes = bytes(addr_bytes).hex()
    if not pubkey_bytes.startswith("0x"):
        pubkey_bytes = "0x" + pubkey_bytes
    return ss58.ss58_encode(pubkey_bytes, ss58_format=ss58_format)