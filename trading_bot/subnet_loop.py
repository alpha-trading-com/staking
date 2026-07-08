import bittensor as bt

from trading_config import DROP_PCT_THRESHOLD, WATCHED_SUBNETS


def _check_subnets(
    subnets: list[bt.DynamicInfo],
    prev_subnets: list[bt.DynamicInfo],
) -> list:

    for i in range(len(subnets)):
        prev_price = prev_subnets[i].price.tao
        current_price = subnets[i].price.tao
        if current_price < prev_price:
            drop_pct = ((prev_price - current_price) / prev_price) * 100
            print(f"Subnet {subnets[i].netuid} dropped {drop_pct:.2f}%")

        prev_identity = prev_subnets[i].subnet_name
        current_identity = subnets[i].subnet_name
        print(f"Current identity: {current_identity}, previous identity: {prev_identity}")
        if current_identity != prev_identity:
            print(f"Subnet {subnets[i].netuid} changed from {prev_identity} to {current_identity}")

def main():
    subtensor = bt.Subtensor("finney")
    prev_subnets = subtensor.all_subnets()
    prev_block = subtensor.get_current_block()

    while True:
        try:
            block = subtensor.get_current_block()
            if block != prev_block:
                print(f"Current block: {block}")
                subnets = subtensor.all_subnets()
                _check_subnets(subnets, prev_subnets)
                prev_subnets = subnets
                prev_block = block
        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == "__main__":
    main()
