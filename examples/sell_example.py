import asyncio
import json

import loopring
from loopring import Token
from loopring.util import Endpoints


with open("account.json", "r") as fp:
    cfg = json.load(fp)

cfg["endpoint"] = Endpoints.MAINNET

client = loopring.Client(config=cfg)


async def main():
    """Submit an order, selling 100 LRC @ 0.02 ETH/LRC"""
    
    symbols = ["LRC", "ETH"]

    # Load the cached `TokenConfig` for each symbol above
    configs = [client.tokens[s] for s in symbols]

    # Update the cached storage IDs for local handling
    await asyncio.gather(*[client.get_next_storage_id(token=tc) for tc in configs])

    lrc_cfg, eth_cfg = configs

    # Define the token quantities
    LRC = Token.from_quantity(100, lrc_cfg)
    ETH = Token.from_quantity(2, eth_cfg)

    # Request to submit the order
    submitted = await client.submit_order("sell", LRC, in_return_for=ETH, max_fee_bips=50)

    # See the order's status
    print(repr(submitted))

    client.stop()


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # Prevents errors complaining about unclosed client sessions
        asyncio.ensure_future(client.close())