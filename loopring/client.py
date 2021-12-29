from typing import Union
import aiohttp
import asyncio
import json

from .util.const import *


class Client:

    def __init__(self, api_key, **config):
        self.loop = asyncio.get_event_loop()
        self.api_key = api_key

    
    async def get_relayer_timestamp(self) -> Union[None, int]:
        """
        Return an Epoch Unix Timestamp.
        """
        async with aiohttp.ClientSession() as s:
            async with s.get(ENDPOINT_MAINNET + RELAYER_CURRENT_TIME) as r:
                raw_content = await r.read()
                await s.close()

                content = json.loads(raw_content.decode())

                return content["timestamp"]
