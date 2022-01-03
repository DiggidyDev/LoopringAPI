import asyncio
import json
from asyncio.events import AbstractEventLoop
from typing import Union

import aiohttp

from loopring.errors import *

from .util.enums import Endpoints as ENDPOINT, ErrorCodes
from .util.enums import Paths as PATH
from .util.helpers import raise_errors_in, ratelimit


class Client:

    def __init__(self, account_id, api_key, **config):
        self.account_id = account_id
        self.api_key = api_key

        # TODO: Remember to add endpoint param to init
        self.cur_endpoint = ENDPOINT.MAINNET

        self._loop: AbstractEventLoop = asyncio.get_event_loop()
        self._session = aiohttp.ClientSession(loop=self._loop)

    async def close(self):
        if not self._session.closed:
            await self._session.close()
    
    # @ratelimit(5, 1)  # Work in progress
    async def get_relayer_timestamp(self) -> int:
        """Get relayer's current timestamp.
        
        Returns:
            int: The Epoch Unix Timestamp according to the relayer.
        Raises:
            UnknownError: Something has gone wrong. Probably out of
                your control. Unlucky.

        """
        url = self.cur_endpoint + PATH.RELAYER_CURRENT_TIME
        
        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            raise_errors_in(content)

            return content["timestamp"]

    async def get_next_storage_id(self, sellTokenID) -> dict:
        """Get the next storage ID.

        Fetches the next order id for a given sold token. If the need
        arises to repeatedly place orders in a short span of time, the
        order id can be initially fetched through the API and then managed
        locally.
        Each new order id can be derived from adding 2 to the last one.
        
        Args:
            sellTokenID (int): The unique identifier of the token which the user
                wants to sell in the next order.
        Returns:
            dict: A dictionary containing the `orderId` and `offchainId`.
        Raises:
            EmptyAPIKey: No API Key was supplied.
            InvalidAccountID: Supplied account ID was deemed invalid.
            InvalidAPIKey: Supplied API Key was deemed invalid.
            InvalidArguments: Invalid arguments supplied.
            UnknownError: Something has gone wrong. Probably out of
                your control. Unlucky.
            UserNotFound: Didn't find the user from the given account ID.

        """

        url = self.cur_endpoint + PATH.STORAGE_ID
        headers = {
            "X-API-KEY": self.api_key
        }
        params = {
            "accountId": self.account_id,
            "sellTokenId": sellTokenID
        }

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            raise_errors_in(content)

            return content

