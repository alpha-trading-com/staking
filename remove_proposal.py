import bittensor as bt



def main():
    subtensor = bt.Subtensor(network="finney")
    substrate  = subtensor.substrate

    other_signatories = ["5FZHE4ESjqYdoJV9FM6RsyrNze7jEonCJ7oxf9PY2RaLSQkZ"]  # This would need to be populated with actual signatories
    
    
    # Create the multisig proposal call
    multisig_call = substrate.compose_call(
        call_module='Multisig',
        call_function='cancel_as_multi',
        call_params={
            'threshold': 2,
            'other_signatories': other_signatories,
            'timepoint': {
                "height":8691738,
                "index":20
            },
            'call_hash': "0x4a75862397c6d5fcc95a92660b2c802dba0dfc0332fbb121c513ad3b199f083d"
        }
    )
    
    proxy_wallet = bt.Wallet(name = "soon_3")
    proxy_wallet.unlock_coldkey()

    extrinsic = substrate.create_signed_extrinsic(
        call=multisig_call,
        keypair=proxy_wallet.coldkey,
    )
    
    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    
    print(receipt.is_success, receipt.error_message)


main()