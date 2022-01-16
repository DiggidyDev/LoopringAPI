import asyncio

import loopring
from loopring.util.enums import Endpoints


cfg = {
    "account_id": 12345,
    "api_key": "",
    "endpoint": Endpoints.MAINNET
}

client = loopring.Client(handle_errors=True, config=cfg)


async def main():

    markets = await client.get_market_configurations()

    print(markets)

    for m in markets:
        if not m.enabled:
            print(m)

    # orders = await client.get_multiple_orders()
    # for _ in orders:
    #     print(_.hash)


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    finally:
        # Prevents errors complaining about unclosed client sessions
        asyncio.ensure_future(client.close())
