import bittensor as bt

if __name__ == "__main__":
    wallet = bt.wallet(name="tck", hotkey="tck_hotkey_1")
    # Test create_new_hotkey (should create a new hotkey under this wallet)
    wallet.create_new_hotkey(
        n_words=12,
        use_password=False,
        overwrite=True,
    )