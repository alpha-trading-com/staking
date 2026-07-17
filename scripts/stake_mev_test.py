"""Stake 1 TAO into subnet 1 with MEV protection enabled.

    python scripts/stake_mev_test.py
"""
import argparse
import os
import sys
import traceback

# Make `app` importable and resolve .env / tolerance_offset.json regardless of cwd.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
os.chdir(REPO_ROOT)

from app.core.config import settings
from app.services.stake import stake_service


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amount", type=float, default=1.0, help="TAO to stake")
    parser.add_argument("--netuid", type=int, default=1, help="subnet id")
    parser.add_argument("--wallet", default=settings.WALLET_NAMES[0], help="wallet name")
    parser.add_argument("--hotkey", default=settings.DEFAULT_DEST_HOTKEY, help="destination hotkey")
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()

    print(f"network={settings.NETWORK} wallet={args.wallet} netuid={args.netuid} "
          f"amount={args.amount} TAO hotkey={args.hotkey} mev_protection=True")

    try:
        result = stake_service.stake(
            tao_amount=args.amount,
            netuid=args.netuid,
            wallet_name=args.wallet,
            dest_hotkey=args.hotkey,
            retries=args.retries,
            mev_protection=True,
        )
    except Exception:
        traceback.print_exc()
        raise

    print(f"success={result['success']} error={result['error']!r}")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
