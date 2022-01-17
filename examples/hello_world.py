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

    candlesticks = await client.get_market_candlestick("LRC-USDT")

    for c in candlesticks:
        print(c)


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    finally:
        # Prevents errors complaining about unclosed client sessions
        asyncio.ensure_future(client.close())
