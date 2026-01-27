import requests

def get_subnet_history(block_number):

    url = f"https://api.taostats.io/api/dtao/pool/history/v1?frequency=by_block&block_number={block_number}&page=1&limit=200"

    headers = {
        "accept": "application/json",
        "Authorization": "tao-883738a0-4d77-4b2e-b452-7d9aeb848040:50268f86"
    }

    response = requests.get(url, headers=headers)

    result = response.json()
    subnets = result["data"]
    return result["data"]


if __name__ == "__main__":
    block_number = 7409411
    subnets = get_subnet_history(block_number)
    print(subnets)
    for subnet in subnets:
        print(subnet["netuid"], subnet["price"])