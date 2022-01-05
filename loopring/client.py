import asyncio
import json
from asyncio.events import AbstractEventLoop
from typing import List

import aiohttp

from loopring.errors import *
from loopring.order import Order

from .util.enums import Endpoints as ENDPOINT
from .util.enums import Paths as PATH
from .util.helpers import raise_errors_in, ratelimit

# TODO: In the future, return custom objects instead of dicts


class Client:

    def __init__(self,
                account_id: int=None,
                api_key: str=None,
                endpoint: ENDPOINT=None,
                **config
                ):
        cfg = config["config"]
        
        if not (cfg.get("account_id") or account_id):
            raise InvalidArguments("Missing account ID from config.")
        
        if not (cfg.get("api_key") or api_key):
            raise InvalidArguments("Missing API Key from config.")
        
        if not (cfg.get("endpoint") or endpoint):
            raise InvalidArguments("Missing endpoint from config.")

        self.account_id = cfg.get("account_id") or account_id
        self.api_key    = cfg.get("api_key")    or api_key
        self.endpoint   = cfg.get("endpoint")   or endpoint

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
        url = self.endpoint + PATH.RELAYER_CURRENT_TIME
        
        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            raise_errors_in(content)

            return content["timestamp"]

    async def get_next_storage_id(self, sell_token_id: int=None) -> dict:
        """Get the next storage ID.

        Fetches the next order ID for a given sold token. If the need
        arises to repeatedly place orders in a short span of time, the
        order ID can be initially fetched through the API and then managed
        locally.
        Each new order ID can be derived from adding 2 to the last one.
        
        Args:
            sell_token_id (int): The unique identifier of the token which the user
                wants to sell in the next order.
        Returns:
            A :obj:`dict` containing the `orderId` and `offchainId`.
        Raises:
            EmptyAPIKey: No API Key was supplied.
            InvalidAccountID: Supplied account ID was deemed invalid.
            InvalidAPIKey: Supplied API Key was deemed invalid.
            InvalidArguments: Invalid arguments supplied.
            TypeError: 'sell_token_id' argument supplied was not of type 'int'.
            UnknownError: Something has gone wrong. Probably out of
                your control. Unlucky.
            UserNotFound: Didn't find the user from the given account ID.

        """

        if not sell_token_id:
            raise InvalidArguments("Missing 'sellTokenID' argument.")

        url = self.endpoint + PATH.STORAGE_ID
        headers = {
            "X-API-KEY": self.api_key
        }
        params = {
            "accountId": self.account_id,
            "sellTokenId": sell_token_id
        }

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            raise_errors_in(content)

            return content

    async def get_order_details(self, orderhash: str=None) -> Order:
        """Get the details of an order based on order hash.
        
        Args:
            orderhash (str): The orderhash belonging to the order you want to
                find details of.
        
        Returns:
            An :obj:`Order` object.

        Raises:
            InvalidArguments: Missing the 'orderhash' argument.

        """

        if not orderhash:
            raise InvalidArguments("Missing 'orderhash' argument.")
        
        url = self.endpoint + PATH.ORDER
        headers = {
            "X-API-KEY": self.api_key
        }
        params = {
            "accountId": self.account_id,
            "orderHash": orderhash
        }

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            raise_errors_in(content)

            order: Order = Order(**content)

            return order
        
    async def get_multiple_orders(self, *,
                                end: int=0,
                                limit: int=50,
                                market: str=None,
                                offset: int=0,
                                order_types: str=None,
                                side: str=None,
                                start: int=None,
                                status: str=None,
                                trade_channels: str=None
                                ) -> List[Order]:
        """Get a list of orders satisfying certain criteria.

        Note:
            All arguments are optional. \ 
            All string-based arguments are case-insensitive. For example,
            `trade_channels='MIXED'` returns the same results as `trade_channels='mIxEd'`.
        
        Args:
            end (int): The upper bound of an order's creation timestamp,
                in milliseconds. Defaults to `0`.
            limit (int): The maximum number of orders to be returned. Defaults
                to `50`.
            market (str): The trading pair. Example: `'LRC-ETH'`.
            offset (int): The offset of orders. Defaults to `0`. \            
            order_types (str): Types of orders available:
                `'LIMIT_ORDER'`, `'MAKER_ONLY'`, `'TAKER_ONLY'`, `'AMM'`. 
            side (str): The type of order made, a `'BUY'` or `'SELL'`.
            start (int): The lower bound of an order's creation timestamp,
                in milliseconds. Defaults to `0`.
            status (str): The order's status:
                `'PROCESSING'`, `'PROCESSED'`, `'FAILED'`, `'CANCELLED'`, `'CANCELLING'`,
                `'EXPIRED'`.

                Multiple statuses can be selected:
                `'CANCELLING, CANCELLED'`
            trade_channels (str): The channel which said trade was made in:
                `'ORDER_BOOK'`, `'AMM_POOL'`, `'MIXED'`.
        
        Returns:
            A :obj:`list` of :obj:`Order` objects on a successful query.
            The returned list could be empty if no orders met the given conditions.

        Raises:
            EmptyAPIKey: The API Key cannot be empty.
            EmptyUser: The user ID cannot be empty.
            InvalidAccountID: The account ID is invalid.
            InvalidAPIKey: The API Key is invalid.
            UnknownError: Something out of your control went wrong.

        """

        url = self.endpoint + PATH.ORDERS
        headers = {
            "X-API-KEY": self.api_key
        }
        params = {
            "accountId": self.account_id,
            "end": end,
            "limit": limit,
            "market": market,
            "offset": offset,
            "orderTypes": order_types,
            "side": side,
            "start": start,
            "status": status,
            "tradeChannels": trade_channels
        }

        # Filter out unspecified parameters
        params = {k: v for k, v in params.items() if v}

        print(params)

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            raise_errors_in(content)

            orders: List[Order] = []

            for order in content["orders"]:
                orders.append(Order(**order))

            return orders

