import bittensor as bt


def start_call_extrinsic(subtensor: bt.Subtensor, netuid: int, wallet: bt.Wallet):
    call = subtensor.substrate.compose_call(
        call_module='SubtensorModule',
        call_function='start_call',
        call_params={
            "netuid": netuid,
        }
    )

    extrinsic = subtensor.substrate.create_signed_extrinsic(
        call=call,
        keypair=wallet.coldkey,
    )

    receipt = subtensor.substrate.submit_extrinsic(
        extrinsic,
        wait_for_inclusion=True,
        wait_for_finalization=False,
    )

    if receipt.is_success:
        print("Call started successfully")
    else:
        print(f"Error starting call: {receipt.error_message}")

if __name__ == "__main__":
    netuid = 38
    subtensor = bt.subtensor(network="finney")
    wallet = bt.Wallet(name="proxy")
    wallet.unlock_coldkey()
    result, error_message = start_call_extrinsic(subtensor, netuid, wallet)
    print(f"Result: {result}")
    print(f"Error message: {error_message}")