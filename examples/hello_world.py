import asyncio

import loopring
from loopring.util.enums import Endpoints


cfg = {
    "account_id": 12345,
    "api_key": "",
    "endpoint": Endpoints.MAINNET
}

client = loopring.Client(config=cfg)


async def main():
    resp = await client.get_next_storage_id(0)
    print(resp)


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    finally:
        asyncio.ensure_future(client.close())
