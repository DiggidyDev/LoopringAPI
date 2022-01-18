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
    info = await client.get_account_info(address=client.address)

    print(info, type(info))


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    finally:
        # Prevents errors complaining about unclosed client sessions
        asyncio.ensure_future(client.close())
