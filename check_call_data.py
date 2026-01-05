
import hashlib
B58_ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, 'big')
    out = bytearray()
    while n > 0:
        n, rem = divmod(n, 58)
        out.append(B58_ALPHABET[rem])
    for byte in b:
        if byte == 0:
            out.append(B58_ALPHABET[0])
        else:
            break
    return out[::-1].decode()
def ss58_encode(account_id: bytes, ss58_prefix: int = 42) -> str:
    assert len(account_id) == 32, "AccountId must be 32 bytes"
    if ss58_prefix < 0 or ss58_prefix > 16383:
        raise ValueError("Unsupported ss58_prefix")
    if ss58_prefix <= 63:
        fmt = bytes([ss58_prefix])
    else:
        lower = (ss58_prefix & 0b00111111) | 0b01000000
        upper = (ss58_prefix >> 6) & 0xFF
        fmt = bytes([lower, upper])
    h = hashlib.blake2b(b'SS58PRE' + fmt + account_id, digest_size=64).digest()
    checksum = h[:2]
    return b58encode(fmt + account_id + checksum)
def decode_compact_u128(data: bytes, offset: int = 0):
    b0 = data[offset]
    mode = b0 & 0b11
    if mode == 0:
        return (b0 >> 2), offset + 1
    elif mode == 1:
        b1 = data[offset + 1]
        return ((b0 >> 2) | (b1 << 6)), offset + 2
    elif mode == 2:
        b1 = data[offset + 1]
        b2 = data[offset + 2]
        b3 = data[offset + 3]
        val = ((b0 >> 2) |
               (b1 << 6) |
               (b2 << 14) |
               (b3 << 22))
        return val, offset + 4
    else:
        length = (b0 >> 2) + 4
        payload = data[offset + 1: offset + 1 + length]
        return int.from_bytes(payload, 'little'), offset + 1 + length
def parse(calldata_hex: str, ss58_prefix: int = 42):
    s = calldata_hex.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    data = bytes.fromhex(s)
    if len(data) < 35:
        print("calldata too short")
        return
    pallet = data[0]; call = data[1]
    addr_variant = data[2]
    if addr_variant != 0x00:
        print(f"unsupported MultiAddress variant {addr_variant:#x}")
        return
    account_id = data[3:35]
    amount_base, _ = decode_compact_u128(data, 35)
    ss58 = ss58_encode(account_id, ss58_prefix)
    tao = amount_base / 1_000_000_000
    print(f"target_ss58: {ss58}")
    print(f"amount_tao: {tao:g}")
def main():
    print("please input call data (hex), e.g., 0x...")
    calldata = input("> ").strip()
    
    prefix_input = 42
    parse(calldata, prefix_input)
if __name__ == "__main__":
    main()
