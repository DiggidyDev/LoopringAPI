import asyncio
import json
from asyncio.events import AbstractEventLoop
from typing import List, Union

import aiohttp

from .errors import *
from .exchange import Exchange
from .market import Candlestick, Market, Ticker, Trade
from .order import Order, OrderBook, PartialOrder
from .token import Price, Token, TokenConfig
from .util.enums import Endpoints as ENDPOINT
from .util.enums import Paths as PATH
from .util.helpers import raise_errors_in, ratelimit
from .util.request import Request
from .util.sdk.sig.eddsa import OrderEDDSASign, UrlEDDSASign

# TODO: Do something about exception classes... it's getting a bit messy.
#       Also, rewrite some of the descriptions.
#       Idea: group some of the error codes under other errors? e.g.
#       `OrderNotFound` could also be used when there isn't an order to cancel...


class Client:
    """The main class interacting with Loopring's API endpoints.

    .. _Examples: quickstart.html
    
    Args:
        account_id (int): The ID of the account belonging to the API Key.
        api_key (str): The API Key associated with your L2 account.
        endpoint (:class:`~loopring.util.enums.Endpoints`): The API endpoint \
            to interact with.
        handle_errors (bool): Whether the client should raise any exceptions returned \
            from API responses. `False` would mean the raw JSON response
            would be returned, and no exception would be raised.
        **config (dict): A dictionary-based version of the positional arguments. \
            It may be preferred to use this method over positional arguments, as \
            shown in the `Examples`_.

    """

    account_id: int
    api_key: str
    endpoint: ENDPOINT
    handle_errors: bool
    private_key: str
    publicX: str
    publicY: str

    def __init__(self,
                account_id: int=None,
                api_key: str=None,
                endpoint: ENDPOINT=None,
                *,
                handle_errors: bool=True,
                private_key: str=None,
                publicX: str=None,
                publicY: str=None,
                **config
                ):
        self.__handle_errors = handle_errors
        
        cfg = config.get("config", {})
        
        if not (cfg.get("account_id") or account_id):
            raise InvalidArguments("Missing account ID from config.")
        
        if not (cfg.get("api_key") or api_key):
            raise InvalidArguments("Missing API Key from config.")
        
        if not (cfg.get("endpoint") or endpoint):
            raise InvalidArguments("Missing endpoint from config.")
        
        if not (cfg.get("private_key") or private_key):
            raise InvalidArguments("Missing Private Key from config.")
        
        if not (cfg.get("publicX") or publicX):
            raise InvalidArguments("Missing publicX from config.")
        
        if not (cfg.get("publicY") or publicY):
            raise InvalidArguments("Missing publicY from config.")

        self.account_id  = cfg.get("account_id")  or account_id
        self.api_key     = cfg.get("api_key")     or api_key
        self.endpoint    = cfg.get("endpoint")    or endpoint
        self.private_key = cfg.get("private_key") or private_key
        self.publicX     = cfg.get("publicX")     or publicX
        self.publicY     = cfg.get("publicY")     or publicY

        self._loop: AbstractEventLoop = asyncio.get_event_loop()
        self._session = aiohttp.ClientSession(loop=self._loop)

    @property
    def handle_errors(self) -> bool:
        """A flag denoting whether errors should be raised from API responses.

        .. _documentation page: https://docs.loopring.io/en

        If set to `False`, you will receive a :py:class:`dict` containing
        the raw response from the API, which you will then need to deal with
        yourself. You'll be able to find the error codes from the respective
        `documentation page`_.  
        However, if set to `True`, all errors will be handled for you and raised
        where necessary from responses.

        .. seealso:: :class:`~loopring.util.mappings.Mappings.ERROR_MAPPINGS`
            in case you wish to handle the raw error JSON response yourself.

        """
        return self.__handle_errors

    async def cancel_order(self,
                        *,
                        client_order_id: str=None,
                        orderhash: str=None
                        ) -> PartialOrder:
        """Cancel order using order hash or client-side ID.

        Args:
            client_order_id (str): ...
            orderhash (str): ...

        Returns:
            :obj:`~loopring.order.PartialOrder`: ...
        
        Raises:
            EmptyAPIKey: ...
            InvalidAccountID: ...
            InvalidAPIKey: ...
            NoOrderToCancel: ...
            OrderCancellationFailed: ...
            UnknownError: ...

        """

        url = self.endpoint + PATH.ORDER
        params = {
            "accountId": self.account_id,
            "clientOrderId": client_order_id,
            "orderHash": orderhash
        }

        # Filter out unused params
        params = {k: v for k, v in params.items() if v}

        req = Request("delete", self.endpoint, PATH.ORDER, params=params)

        helper = UrlEDDSASign(self.private_key, self.endpoint)
        api_sig = helper.sign(req)

        headers = {
            "X-API-KEY": self.api_key,
            "X-API-SIG": api_sig
        }
        async with self._session.delete(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            order: PartialOrder = PartialOrder(**content)

            return order

    async def close(self) -> None:
        """Close the client's active connection session."""

        if not self._session.closed:
            await self._session.close()

    async def get_api_key(self) -> str:
        """Get the API Key associated with an account.
        
        Requires private key for X-API-SIG header signing.

        Returns:
            str: The API Key associated with the account ID.

        Raises:
            EmptyAPIKey: ...
            EmptySignature: ...
            InvalidAccountID: ...
            InvalidAPIKey: ...
            InvalidSignature: ...
            UnknownError: ...
            UserNotFound: ...

        """

        params = {
            "accountId": self.account_id
        }

        request = Request(
            "get",
            self.endpoint,
            PATH.API_KEY,
            params=params
        )

        helper = UrlEDDSASign(private_key=self.private_key)
        x_api_sig = helper.sign(request)

        headers = {
            "X-API-SIG": x_api_sig
        }

        url = self.endpoint + PATH.API_KEY

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            return content["apiKey"]

    async def get_exchange_configurations(self) -> Exchange:
        """Get configurations of loopring's exchange.

        Returns:
            :obj:`~loopring.exchange.Exchange`: ...

        """

        url = self.endpoint + PATH.EXCHANGES

        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            exchange = Exchange(**content)
            
            return exchange

    async def get_fiat_prices(self, currency: str="USD") -> List[Price]:
        """Fetches fiat prices for all tokens supported on Loopring.

        Args:
            currency (str): All supported values: "`USD`", "`CNY`", "`JPY`", 
                "`EUR`", "`GBP`", "`HKD`". Defaults to "`USD`".
        
        Returns:
            List[:obj:`~loopring.token.Price`]: ... .

        Raises:
            UnknownError: ...

        """

        url = self.endpoint + PATH.PRICE

        params = {
            "legal": currency
        }

        async with self._session.get(url, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            prices = []

            for p in content["prices"]:
                prices.append(Price(currency=currency, **p))
            
            return prices

    async def get_market_candlestick(self,
        market: str="LRC-ETH",
        interval:str="5min",
        *,
        start: int=None,
        end: int=None,
        limit: int=None) -> List[Candlestick]:
        """Get candlestick data for a given `market` (trading pair).

        Args:
            market (str): Defaults to "`LRC-ETH`".
            interval (str): All supported values;
                `1min`, `5min`, `15min`, `30min`, `1hr`, `2hr`, `4hr`,
                `12hr`, `1d`, `1w`. Defaults to `5min`.
            start (int): ... .
            end (int): ... .
            limit (int): Number of datapoints - if more are available, only
                the first limit data points will be returned.
        
        Returns:
            List[:obj:`~loopring.market.Candlestick`]: ... .

        Raises:
            InvalidArguments: ...
            UnknownError: ...

        """

        url = self.endpoint + PATH.CANDLESTICK

        params = {
            "market": market,
            "interval": interval,
            "start": start,
            "end": end,
            "limit": limit
        }

        params = {k: v for k, v in params.items() if v}

        async with self._session.get(url, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            candlesticks = []

            for c in content["candlesticks"]:
                candlesticks.append(Candlestick(*c))

            return candlesticks

    async def get_market_configurations(self) -> List[Market]:
        """Get all markets (trading pairs) on the exchange, both valid and invalid.
        
        Returns:
            List[:obj:`~loopring.market.Market`]: All the markets.
        
        Raises:
            UnknownError: ...

        """

        url = self.endpoint + PATH.MARKETS

        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            markets = []

            for m in content["markets"]:
                markets.append(Market(**m))
            
            return markets

    async def get_market_orderbook(self,
        market: str="LRC-ETH",
        *,
        price_aggregation: int=2,
        limit: int=50) -> OrderBook:
        """Get the orderbook of a specific market (trading pair).

        Args:
            limit (int): Default 50.
            market (str): Default 'LRC-ETH'.
            price_aggregation (int): Default 2.
        
        Returns:
            :obj:`loopring.order.Orderbook`: ... .

        Raises:
            OrderbookUnsupportedMarket: ...
            UnknownError: ...
            UnsupportedDepthLevel: ...

        """

        url = self.endpoint + PATH.DEPTH

        params = {
            "level": price_aggregation,
            "limit": limit,
            "market": market
        }

        async with self._session.get(url, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            orderbook = OrderBook(**content)

            return orderbook

    async def get_market_ticker(self, market: str="LRC-ETH") -> List[Ticker]:
        """Get a ticker for a specific market or multiple markets.
        
        Raises:
            InvalidArguments: ...
            UnknownError: ...

        """

        url = self.endpoint + PATH.TICKER

        params = {
            "market": market
        }

        async with self._session.get(url, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            tickers = []

            for t in content["tickers"]:
                tickers.append(Ticker(*t))

            return tickers

    async def get_multiple_orders(self, *,
                                end: int=0,
                                limit: int=50,
                                market: str=None,
                                offset: int=0,
                                order_types: str=None,
                                side: str=None,
                                start: int=0,
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
            List[:class:`~loopring.order.Order`]: A :obj:`list` of
            :class:`~loopring.order.Order` objects on a successful query.
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

            if self.handle_errors:
                raise_errors_in(content)

            orders: List[Order] = []

            for order in content["orders"]:
                orders.append(Order(**order))

            return orders

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
            :obj:`dict`: A :obj:`dict` containing the `orderId` and `offchainId`.

        Raises:
            EmptyAPIKey: No API Key was supplied.
            InvalidAccountID: Supplied account ID was deemed invalid.
            InvalidAPIKey: Supplied API Key was deemed invalid.
            InvalidArguments: Invalid arguments supplied.
            TypeError: 'sell_token_id' argument supplied was not of type :class:`int`.
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

            if self.handle_errors:
                raise_errors_in(content)

            return content

    async def get_order_details(self, orderhash: str) -> Order:
        """Get the details of an order based on order hash.
        
        Args:
            orderhash (str): The orderhash belonging to the order you want to
                find details of.
        
        Returns:
            :class:`~loopring.order.Order`: An instance of the order based on \
                the given orderhash.

        Raises:
            InvalidArguments: Missing the 'orderhash' argument.

        """

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

            if self.handle_errors:
                raise_errors_in(content)

            order: Order = Order(**content)

            return order

    async def get_recent_market_trades(self,
        market: str="LRC-ETH",
        *,
        limit: int=20,
        fill_types: str=None) -> List[Trade]:
        """Get trades of a specific trading pair.

        Args:
            market (str): Defaults to "`LRC-ETH`".
            limit (int): Defaults to 20.
            fill_types (str): ... .
        
        Returns:
            List[:obj:`~loopring.market.Trade`]: ... .
        
        Raises:
            UnknownError: ...

        """
        url = self.endpoint + PATH.TRADE

        params = {
            "fillTypes": fill_types,
            "limit": limit,
            "market": market
        }

        params = {k: v for k, v in params.items() if v}

        async with self._session.get(url, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            trades = []

            for t in content["trades"]:
                trades.append(Trade(*t))
            
            return trades

    # @ratelimit(5, 1)  # Work in progress
    async def get_relayer_timestamp(self) -> int:
        """Get relayer's current timestamp.

        Returns:
            :class:`int`: The Epoch Unix Timestamp according to the relayer.

        Raises:
            UnknownError: Something has gone wrong. Probably out of
                your control. Unlucky.

        """
        url = self.endpoint + PATH.RELAYER_CURRENT_TIME

        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            return content["timestamp"]

    async def submit_order(self,
                        *,
                        affiliate: str=None,
                        all_or_none: str,
                        buy_token: Token,
                        client_order_id: str=None,
                        exchange: str,
                        fill_amount_b_or_s: bool,
                        max_fee_bips: int,
                        order_type: str=None,
                        pool_address: str=None,
                        sell_token: Token,
                        storage_id: int,
                        taker: str=None,
                        trade_channel: str=None,
                        valid_until: int
                        ) -> PartialOrder:
        """Submit an order.
        
        Args:
            affiliate (str): An account ID to receive a share of the
                order's fee.
            all_or_none (str): Whether the order supports partial fills
                or not. Currently only supports `'false'`.
            buy_token (:obj:`~loopring.token.Token`): Wrapper object used \
                to describe a token associated with a certain quantity.
            client_order_id (str): An arbitrary, unique client-side
                order ID.
            exchange (str): The address of the exchange used to process
                this order.
            fill_amount_b_or_s (bool): Fill the size by the `'BUY'` (True) or `'SELL'` (False) \
                token.
            max_fee_bips (int): Maximum order fee that the user can accept, \
                value range (in ten thousandths) 1 ~ 63.
            order_type (str): The type of order: `'LIMIT_ORDER'`, `'AMM'`, \
                `'MAKER_ONLY'`, `'TAKER_ONLY'`.
            pool_address (str): The AMM Pool address if order type is `'AMM'`.
            sell_token (:obj:`~loopring.token.Token`): Wrapper object used \
                to describe a token associated with a certain quantity.
            storage_id (int): The unique ID of the L2 Merkle tree storage \
                slot where the burn made in order to exit the pool will be \
                stored or has been stored.
            taker (str): Used by the P2P order, where the user needs to \
                specify the taker's address.
            trade_channel (str): The channel to be used when ordering: \
                `'ORDER_BOOK'`, `'AMM_POOL'`, `'MIXED'`.
            valid_until (int): The order expiry time, in seconds.

        Returns:
            :class:`~loopring.order.PartialOrder`: The order just submitted.

        Raises:
            EmptyAPIKey: ... .
            EmptySignature: ... .
            FailedToFreeze: ... .
            FailedToSubmit: ... .
            InvalidAPIKey: ... .
            InvalidAccountID: ... .
            InvalidArguments: ... .
            InvalidExchangeID: ... .
            InvalidNonce: ... .
            InvalidOrder: ... .
            InvalidOrderID: ... .
            InvalidRate: ... .
            InvalidSignature: ... .
            InvalidUserBalance: ... .
            OrderAlreadyExists: ... .
            OrderAlreadyExpired: ... .
            OrderAmountExceeded: ... .
            OrderAmountTooSmall: ... .
            OrderInvalidAccountID: ... .
            OrderMissingSignature: ... .
            OrderUnsupportedMarket: ... .
            UnknownError: ... .
            UnsupportedTokenID: ... .
        
        """

        url = self.endpoint + PATH.ORDER

        payload = {
            "accountId": self.account_id,
            "affiliate": affiliate,
            "allOrNone": all_or_none,
            "buyToken": {
                "tokenId": buy_token.id,
                "volume": buy_token.volume
            },
            "clientOrderId": client_order_id,
            "exchange": exchange,
            "fillAmountBOrS": fill_amount_b_or_s,
            "maxFeeBips": max_fee_bips,
            "orderType": order_type,
            "poolAddress": pool_address,
            "sellToken": {
                "tokenId": sell_token.id,
                "volume": sell_token.volume
            },
            "storageId": storage_id,
            "taker": taker,
            "tradeChannel": trade_channel,
            "validUntil": valid_until
        }

        # Filter out unused params
        payload = {k: v for k, v in payload.items() if v}
        payload = {k: v for k, v in payload.items() if v is not None}

        request = Request(
            "post",
            self.endpoint,
            PATH.ORDER,
            payload=payload
        )

        helper = OrderEDDSASign(private_key=self.private_key)
        eddsa_signature = helper.sign(request.payload)

        payload["eddsaSignature"] = eddsa_signature

        headers = {
            "X-API-KEY": self.api_key
        }

        async with self._session.post(url, headers=headers, json=payload) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            order: PartialOrder = PartialOrder(**content)

            return order

    async def get_token_configurations(self) -> List[TokenConfig]:
        """Return the configs of all supporoted tokens (Ether included).
        
        Returns:
            List[:obj:`~loopring.token.TokenConfig`]: Token configs.
        
        Raises:
            UnknownError: ...

        """

        url = self.endpoint + PATH.TOKENS

        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            token_confs = []

            for t in content:
                print(t, type(t))
                token_confs.append(TokenConfig(**t))
            
            return token_confs

    # TODO: rename to `regenerate_api_key()`?
    async def update_api_key(self) -> str:
        """Update the account's API Key.
        
        Returns:
            str: Your account's new API Key.
        
        Raises:
            EmptyAPIKey: ...
            EmptySignature: ...
            InvalidAccountID: ...
            InvalidAPIKey: ...
            InvalidArguments: ...
            InvalidSignature: ...
            UnknownError: ...
            UserNotFound: ...

        """

        payload = {
            "accountId": self.account_id
        }

        request = Request(
            "post",
            self.endpoint,
            PATH.API_KEY,
            payload=payload
        )

        helper = UrlEDDSASign(private_key=self.private_key)
        x_api_sig = helper.sign(request)

        headers = {
            "X-API-KEY": self.api_key,
            "X-API-SIG": x_api_sig
        }

        url = self.endpoint + PATH.API_KEY

        # Use `json=` for POST, and `params=` for GET
        async with self._session.post(url, headers=headers, json=payload) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            new_api_key = content["apiKey"]
            self.api_key = new_api_key

            return self.api_key

