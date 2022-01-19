import asyncio
from datetime import timedelta

import loopring
from loopring.util.enums import Endpoints


cfg = {
    "account_id": 12345,
    "api_key": "",
    "endpoint": Endpoints.MAINNET
}

client = loopring.Client(handle_errors=True, config=cfg)

async def main():
    
    # Get orders made in the past 8 days
    rt = await client.get_relayer_time()
    start = rt - timedelta(8)

    orders = await client.get_multiple_orders(start=start)
    print(orders)


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    finally:
        # Prevents errors complaining about unclosed client sessions
        asyncio.ensure_future(client.close())
