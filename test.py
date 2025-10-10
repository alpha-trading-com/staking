import bittensor as bt

if __name__ == "__main__":
    subtensor = bt.subtensor("finney")
    wallet_ss58 = "5FWhdv8o7fGo6yn54qXCn1xTxXsMaNLaotKYzUSG2iZp4tVZ"
    stake_infos = subtensor.get_stake_for_coldkey(
        coldkey_ss58=wallet_ss58
    )
    all_subnets = subtensor.all_subnets()

    for stake_info in stake_infos:
        subnet = all_subnets[stake_info.netuid]
        print(f"Netuid: {stake_info.netuid}, Stake: {stake_info.stake.tao}, Price: {subnet.price.tao}")
        print(f"Price: subnet.tao_in.tao, subnet.alpha_in.tao, stake_info.stake.tao: {subnet.tao_in.tao}, {subnet.alpha_in.tao}, {stake_info.stake.tao} ")
        print(f"Value: {subnet.tao_in.tao / subnet.alpha_in.tao }")