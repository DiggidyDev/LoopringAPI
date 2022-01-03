import asyncio
import loopring


cfg = {

}

client = loopring.Client(66825, "", config=cfg)  # TODO: endpoint param



async def main():
    resp = await client.get_next_storage_id(0)
    print(resp)


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    finally:
        asyncio.ensure_future(client.close())
