import asyncio
import loopring


cfg = {

}

client = loopring.Client("", config=cfg)


async def main():
    timestamp = await client.get_relayer_timestamp()
    print(timestamp)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
