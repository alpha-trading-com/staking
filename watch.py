import bittensor as bt

if __name__ == "__main__":
    subtensor = bt.Subtensor("finney")
    netuid = int(input("Enter the netuid: "))
    subnet = subtensor.subnet(netuid=netuid)
    prev_tao_in = subnet.tao_in

    while True:
        try:
            subnet = subtensor.subnet(netuid=netuid)
            now_tao_in = subnet.tao_in
            tao_flow = float(now_tao_in - prev_tao_in)
            print(f"SN {netuid:2d} => {round(float(subnet.price), 5):>8.5f}, {round(tao_flow, 2):>8.2f}")
            prev_tao_in = now_tao_in
            subtensor.wait_for_block()
        except Exception as e:
            print(f"Error in watching_price: {e}")
            continue