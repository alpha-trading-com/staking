import bittensor as bt
import json
my_wallet = bt.Wallet("")
my_wallet.coldkey_file.save_password_to_env("")
my_wallet.coldkey_file.decrypt()
data = json.loads(my_wallet.coldkey_file.data)
print(data.get("secretPhrase"))