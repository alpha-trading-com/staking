import bittensor as bt

# Initialize subtensor
subtensor = bt.Subtensor(network="finney")

# Define your staking parameters
origin_netuid = 0  # Root network (TAO)
destination_netuid = 1  # Target subnet you want to stake to
amount = bt.Balance.from_tao(10.0)  # Amount you want to stake

# Simulate the swap BEFORE executing
result = subtensor.sim_swap(
    origin_netuid=origin_netuid,
    destination_netuid=destination_netuid,
    amount=amount
)

# Check what you'll actually receive
print(f"TAO you're staking: {result.tao_amount}")
print(f"Alpha tokens you'll receive: {result.alpha_amount}")
print(f"TAO fee: {result.tao_fee}")
print(f"Alpha fee: {result.alpha_fee}")

# Calculate the effective price and tolerance
effective_price = result.tao_amount.tao / result.alpha_amount.tao
print(f"Effective price: {effective_price}")

# Now you can determine your tolerance based on the simulation
# For example, if you want 1% slippage protection:
tolerance = 0.01
max_acceptable_price = effective_price * (1 + tolerance)