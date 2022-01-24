import asyncio
import json
from datetime import timedelta

import loopring
from loopring.util import Endpoints


with open("account.json", "r") as fp:
    cfg = json.load(fp)

cfg["endpoint"] = Endpoints.MAINNET

client = loopring.Client(config=cfg)


async def main():

    # Get orders made in the past 8 days
    rt = await client.get_relayer_time()
    start = rt - timedelta(8)

    orders = await client.get_multiple_orders(start=start)
    print(orders)

    client.stop()  # Exit the program


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