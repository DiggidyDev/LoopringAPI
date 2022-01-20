import asyncio
import json
import time
from asyncio.events import AbstractEventLoop
from datetime import datetime
from typing import List, Sequence, Union
import requests

import aiohttp
from py_eth_sig_utils.signing import v_r_s_to_signature
from py_eth_sig_utils.utils import ecsign

from .account import Account, Balance
from .errors import *
from .exchange import DepositHashData, Exchange, TransactionHashData, WithdrawalHashData
from .market import Candlestick, Market, Ticker, Trade
from .order import CounterFactualInfo, Order, OrderBook, PartialOrder, Transfer
from .token import Price, Token, TokenConfig
from .util.enums import Endpoints as ENDPOINT
from .util.enums import Paths as PATH
from .util.helpers import clean_params, raise_errors_in, ratelimit, validate_timestamp
from .util.request import Request
from .util.sdk.sig.ecdsa import generate_transfer_EIP712_hash
from .util.sdk.sig.eddsa import OrderEDDSASign, UrlEDDSASign

# TODO: Do something about exception classes... it's getting a bit messy.
#       Also, rewrite some of the descriptions.
#       Idea: group some of the error codes under other errors? e.g.
#       `OrderNotFound` could also be used when there isn't an order to cancel...


# TODO: UpdateAccountEDDSAKey endpoint (need keySeed? from account query)



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
    address: str
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
                address: str=None,
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

        self.account_id  = cfg.get("account_id", account_id)
        self.address     = cfg.get("address", address)
        self.api_key     = cfg.get("api_key", api_key)
        self.endpoint    = cfg.get("endpoint", endpoint)
        self.private_key = cfg.get("private_key", private_key)
        self.publicX     = cfg.get("publicX", publicX)
        self.publicY     = cfg.get("publicY", publicY)

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
        """Cancel an order.

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
        params = clean_params({
            "accountId": self.account_id,
            "clientOrderId": client_order_id,
            "orderHash": orderhash
        })

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

    async def get_account_info(self, address: str) -> Account:
        """Returns data associated with the user's exchange account.
        
        Args:
            address (str): ... .
        
        Returns:
            :obj:`~loopring.account.Account`: ... .
        
        Raises:
            AddressNotFound: ... .
            UnknownError: ... .
            UserNotFound: ... .

        """

        url = self.endpoint + PATH.ACCOUNT

        params = {
            "owner": address
        }

        async with self._session.get(url, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            account = Account(**content)

            return account

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

        Raises:
            UnknownError: ... .

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
        interval: str="5min",
        *,
        start: Union[int, datetime]=None,
        end: Union[int, datetime]=None,
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
            TypeError: From timestamp validation.
            UnknownError: ...
            ValidationException: From timestamp validation.

        """

        url = self.endpoint + PATH.CANDLESTICK

        params = clean_params({
            "market": market,
            "interval": interval,
            "start": validate_timestamp(start),
            "end": validate_timestamp(end),
            "limit": limit
        })

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
                                end: Union[int, datetime]=None,
                                limit: int=50,
                                market: str=None,
                                offset: int=0,
                                order_types: str=None,
                                side: str=None,
                                start: Union[int, datetime]=None,
                                status: str=None,
                                trade_channels: str=None) -> List[Order]:
        """Get a list of orders satisfying certain criteria.

        Note:
            All arguments are optional. \ 
            All string-based arguments are case-insensitive. For example,
            `trade_channels='MIXED'` returns the same results as `trade_channels='mIxEd'`.

        Args:
            end (Union[int, :class:`~datetime.datetime`]): The upper bound of an order's creation timestamp,
                in milliseconds. Defaults to `0`.
            limit (int): The maximum number of orders to be returned. Defaults
                to `50`.
            market (str): The trading pair. Example: `'LRC-ETH'`.
            offset (int): The offset of orders. Defaults to `0`. \            
            order_types (str): Types of orders available:
                `'LIMIT_ORDER'`, `'MAKER_ONLY'`, `'TAKER_ONLY'`, `'AMM'`. 
            side (str): The type of order made, a `'BUY'` or `'SELL'`.
            start (Union[int, :class:`~datetime.datetime`): The lower bound of an
                order's creation timestamp, in milliseconds. Defaults to `0`.
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
        params = clean_params({
            "accountId": self.account_id,
            "end": validate_timestamp(end),
            "limit": limit,
            "market": market,
            "offset": offset,
            "orderTypes": order_types,
            "side": side,
            "start": validate_timestamp(start),
            "status": status,
            "tradeChannels": trade_channels
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            orders: List[Order] = []

            for order in content["orders"]:
                orders.append(Order(**order))

            return orders

    # TODO: Return obj instead of dict?
    async def get_next_storage_id(self, sell_token_id: Union[int, Token]=None) -> dict:
        """Get the next storage ID.

        Fetches the next order ID for a given sold token. If the need
        arises to repeatedly place orders in a short span of time, the
        order ID can be initially fetched through the API and then managed
        locally.
        Each new order ID can be derived from adding 2 to the last one.
        
        Args:
            sell_token_id (Union[int, :int:`~loopring.token.Token`): The unique
                identifier of the token which the user wants to sell in the next
                order.

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

        if isinstance(sell_token_id, Token):
            sell_token_id = Token.id

        url = self.endpoint + PATH.STORAGE_ID
        headers = {
            "X-API-KEY": self.api_key
        }
        params = {
            "accountId": self.account_id,
            "sellTokenId": sell_token_id,
            "maxNext": 0
        }

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            return content

    async def get_onchain_withdrawal_history(self,
        *,
        account_id: int=None,
        end: Union[int, datetime]=None,
        hashes: Union[str, Sequence[str]]=None,
        limit: int=None,
        offset: int=None,
        start: Union[int, datetime]=None,
        status: str=None,
        token_symbol: str=None,
        withdrawal_types: str=None) -> List[WithdrawalHashData]:
        """Get a user's onchain withdrawal history.
        
        Args:
            account_id (int): ... .
            end (Union[int, :class:`~datetime.datetime`]): ... .
            hashes (Union[str, Sequence[str]]): ... .
            limit (int): ... .
            offset (int): ... .
            start (Union[int, :class:`~datetime.datetime`]): ... .
            status (str): ... .
            token_symbol (str): ... .
            withdrawal_types: ... .

        Returns:
            List[:obj:`~loopring.exchange.WithdrawalHashData`]: ...

        Raises:
            EmptyAPIKey: ...
            EmptyUser: ...
            InvalidAccountID: ...
            InvalidAPIKey: ...
            UnknownError: ...

        """

        url = self.endpoint + PATH.USER_WITHDRAWALS

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "end": validate_timestamp(end),
            "hashes": hashes,
            "limit": limit,
            "offset": offset,
            "start": validate_timestamp(start),
            "status": status,
            "tokenSymbol": token_symbol,
            "withdrawalTypes": withdrawal_types
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            withdrawals = []

            for w in content["transactions"]:
                withdrawals.append(WithdrawalHashData(**w))
            
            return withdrawals

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

    # TODO: Accept a list of str for status?
    async def get_password_reset_transactions(self,
        *,
        account_id: int=None,
        end: Union[int, datetime]=None,
        limit: int=None,
        offset: int=None,
        start: Union[int, datetime]=None,
        status: str=None) -> List[TransactionHashData]:
        """Get eth transactions from a user from password resets on the exchange.
        
        Args:
            account_id (int): ... .
            end (Union[int, :class:`~datetime.datetime`]): ... .
            limit (int): ... .
            offset (int): ... .
            start (Union[int, :class:`~datetime.datetime`]): ... .
            status (str): "`processing`", "`processed`", "`received`", "`failed`".
        
        Returns:
            List[:obj:`~loopring.exchange.TransactionHashData`]: ... .
        
        Raises:
            EmptyAPIKey: ... .
            InvalidAccountID: ... .

        """

        url = self.endpoint + PATH.USER_PASSWORD_RESETS

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "end": validate_timestamp(end),
            "limit": limit,
            "offset": offset,
            "start": validate_timestamp(start),
            "status": status
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            tx_list = []

            for t in content["transactions"]:
                tx_list.append(TransactionHashData(**t))
            
            return tx_list

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

        params = clean_params({
            "fillTypes": fill_types,
            "limit": limit,
            "market": market
        })

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
    async def get_relayer_time(self) -> datetime:
        """Get relayer's current time as a datetime object.

        Returns:
            :class:`~datetime.datetime`: The Epoch Unix Time according \
                to the relayer.

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

            dt = datetime.fromtimestamp(content["timestamp"] / 1000)

            return dt

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
                token_confs.append(TokenConfig(**t))
            
            return token_confs

    async def get_user_deposit_history(self,
        *,
        account_id: int=None,
        end: Union[int, datetime]=None,
        hashes: Union[str, Sequence[str]]=None,
        limit: int=None,
        offset: int=None,
        start: Union[int, datetime]=None,
        status: str=None,
        token_symbol: str=None) -> List[DepositHashData]:
        """Get a user's deposit records.
        
        Args:
            account_id (int): ... .
            end (Union[int, :class:`~datetime.datetime`]): ... .
            hashes (Union[str, Sequence[str]]): ... .
            limit (int): ... .
            offset (int): ... .
            start (Union[int, :class:`~datetime.datetime`]): ... .
            status (str): ... .
            token_symbol (str): ... .

        Returns:
            List[:obj:`~loopring.exchange.DepositHashData`]: ...

        Raises:
            EmptyAPIKey: ...
            EmptyUser: ...
            InvalidAccountID: ...
            InvalidAPIKey: ...
            UnknownError: ...

        """

        url = self.endpoint + PATH.USER_DEPOSITS

        if isinstance(hashes, (list, tuple)):
            hashes = ",".join(hashes)

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "end": validate_timestamp(end),
            "hashes": hashes,
            "limit": limit,
            "offset": offset,
            "start": validate_timestamp(start),
            "status": status,
            "tokenSymbol": token_symbol
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            deposits = []

            for d in content["transactions"]:
                deposits.append(DepositHashData(**d))
            
            return deposits

    async def get_user_exchange_balances(self,
        *,
        account_id: int=None,
        tokens: Union[str, int, Sequence[Union[str, int, Token]]]="0,1"
        ) -> List[Balance]:
        """Get all eth and token balances on a user's exchange account.

        Args:
            account_id (int): ... .
            tokens (Union[str, int, Sequence[Union[str, int, Token]]]): ... .

        Returns:
            List[:obj:`~loopring.account.Balance`]: ... .

        Raises:
            EmptyAPIKey: ...
            InvalidAccountID: ...
            InvalidAPIKey: ...
            UnknownError: ...

        """

        url = self.endpoint + PATH.USER_BALANCES

        # Not sure if this is really necessary, just an
        # extra layer of protection from user error x)
        if isinstance(tokens, (tuple, list)):
            old = tokens.copy()
            tokens = []

            for t in old:
                if isinstance(t, Token):
                    tokens.append(t.id)
                elif isinstance(t, (int, str)):
                    tokens.append(t)

            # Ensure all `_` are strings
            tokens = ",".join([f"{_}" for _ in tokens])

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "tokens": tokens
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            balances = []

            for b in content:
                balances.append(Balance(**b))
            
            return balances

    async def get_user_registration_transactions(self,
        *,
        account_id: int=None,
        end: Union[int, datetime]=None,
        limit: int=None,
        offset: int=None,
        start: Union[int, datetime]=None,
        status: str=None) -> List[TransactionHashData]:
        """Return all ethereum transactions from a user upon account registration.
        
        Args:
            account_id (int): Leave blank to receive your client config account's
                transactions.
            end (Union[int, :class:`~datetime.datetime`): ... .
            limit (int): ... .
            offset (int): ... .
            start (Union[int, :class:`~datetime.datetime`): ... .
            status (str): ... .
        
        Returns:
            List[:obj:`~loopring.exchange.TransactionHashData`]: ... .
        
        Raises:
            EmptyAPIKey: ... .
            EmptyUser: ... .
            InvalidAccountID: ... .
            InvalidAPIKey: ... .
            UnknownError: ... .

        """
        url = self.endpoint + PATH.USER_REGISTRATION

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "end": validate_timestamp(end),
            "limit": limit,
            "offset": offset,
            "start": validate_timestamp(start),
            "status": status
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            tx_list = []

            for tx in content["transactions"]:
                tx_list.append(TransactionHashData(**tx))

            return tx_list

    async def get_user_trade_history(self,
        market: str="LRC-ETH",
        *,
        account_id: int=None,
        fill_types: str=None,
        from_id: int=None,
        limit: int=None,
        offset: int=None,
        order_hash: str=None) -> List[Trade]:
        """Get a user's trade history.
        
        Args:
            account_id (int): ... .
            fill_types (str): Supports '`dex`' and '`amm`'.
            from_id (int): ... .
            limit (int): ... .
            market (str): Defaults to '`LRC-ETH`'.
            offset (int): ... .
            order_hash (str): ... .

        """

        url = self.endpoint + PATH.TRADE_HISTORY

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "fillTypes": fill_types,
            "fromId": from_id,
            "limit": limit,
            "market": market,
            "offset": offset,
            "orderHash": order_hash
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            trades = []

            for t in content["trades"]:
                trades.append(Trade(*t))
            
            return trades

    async def submit_internal_transfer(self,
        *,
        exchange: Union[str, Exchange],
        payer_id: int,
        payer_address: str,
        payee_id: int,
        payee_address: str,
        token: Token,
        max_fee: Token,
        storage_id: int,
        valid_until: Union[int, datetime]=None,
        valid_since: Union[int, datetime]=None,
        counter_factual_info: CounterFactualInfo=None,
        memo: str=None,
        client_id: str=None) -> Transfer:
        """Submit an internal transfer.
        
        Args:
            client_id (str): ... .
            counter_factual_info (:obj:`~loopring.order.CounterFactualInfo`): ... .
            exchange (Union[str, :obj:`~loopring.exchange.Exchange`]): ... .
            max_fee (:obj:`~loopring.token.Token`): ... .
            memo (str): ... .
            payee_address (str): ... .
            payee_id (int): ... .
            payer_address (str): ... .
            payer_id (int): ... .
            storage_id (int): ... .
            token (:obj:`~loopring.token.Token`): ... .
            valid_until (Union[int, :class:`~datetime.datetime`]): ... .
            valid_since (Union[int, :class:`~datetime.datetime`]): ... .

        Returns:
            :obj:`~loopring.order.Transfer`: ... .
        
        Raises:
            InvalidArguments: ... .
            InvalidExchangeID: ... .
            InvalidNonce: ... .
            InvalidTransferReceiver: ... .
            InvalidTransferSender: ... .
            UnknownError: ... .
            UnsupportedFeeToken: ... .

        """

        if isinstance(exchange, Exchange):
            exchange = str(exchange)
        
        if not valid_until:
            # Default to 2 months:
            # See 'https://docs.loopring.io/en/basics/orders.html#timestamps'
            # for information about order validity and time
            valid_until = int(time.time()) + 60 * 60 * 24 * 60
        valid_since = datetime.timestamp(datetime.now())

        url = self.endpoint + PATH.TRANSFER

        # For some reason, ECDSASig and EDDSASig aren't
        # required parameters in the payload...
        # Need to look into this...
        payload = clean_params({
            "clientId": client_id,
            "counterFactualInfo": counter_factual_info,
            "exchange": exchange,
            "maxFee": max_fee,
            "memo": memo,
            "payeeAddr": payee_address,
            "payeeId": payee_id,
            "payerAddr": payer_address,
            "payerId": payer_id,
            "storageId": storage_id,
            "token": {
                "tokenId": token.id,
                "volume": token.volume
            },
            "validUntil": validate_timestamp(valid_until, "seconds", True),
            "validSince": validate_timestamp(valid_since, "seconds")
        })

        request = Request(
            "post",
            self.endpoint,
            PATH.TRANSFER,
            payload=payload
        )

        message = generate_transfer_EIP712_hash(request.payload)
        v, r, s = ecsign(message, self.private_key)

        x_api_sig = "0x" + bytes.hex(v_r_s_to_signature(v, r, s)) + "02"  # EIP_712

        headers = {
            "X-API-KEY": self.api_key,
            "X-API-SIG": x_api_sig 
        }

        async with self._session.post(url, headers=headers, json=payload) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            return Transfer(**content)

    async def submit_order(self,
                        *,
                        affiliate: str=None,
                        all_or_none: str=False,
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
                        valid_until: Union[int, datetime]=None,
                        valid_since: Union[int, datetime]=None
                        ) -> PartialOrder:
        """Submit an order.
        
        Args:
            affiliate (str): An account ID to receive a share of the
                order's fee.
            all_or_none (str): Whether the order supports partial fills
                or not. Currently only supports `False`, no need to provide this arg.
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
            valid_until (Union[int, :class:`~datetime.datetime`): The order expiry \
                time, in seconds.
            valid_until (Union[int, :class:`~datetime.datetime`): The order expiry \
                time, in seconds.

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

        payload = clean_params({
            "accountId": self.account_id,
            "affiliate": affiliate,
            "allOrNone": False,  # all_or_none,
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
            "validUntil": validate_timestamp(valid_until, "seconds", True),
            "validSince": validate_timestamp(valid_since, "seconds")
        })

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





#========================================================================================================================
#=========================================={Enhanced Order Functionality & Testing}======================================
#========================================================================================================================

    # update parameters to take only the client - 1. replace get_balance function with client-based solution
    async def market_order(self,
                         *,
                         asset1: float = None,
                         asset2: str = None,
                         trade_pair: str = None,
                         funding: float = None,
                         size:  int = None
                         ) -> str:

        """Market Order - allow user to execute market order at strike price, that exhibits bi-directional market orders
                            by switching the order of assets.
            Args:
                asset1 (str): asset to buy
                asset2 (str): asset to sell
                trade_pair (str): trade pair
                funding (float): amount of asset 2 to sell (units: asset2)
                size (float): amount of asset 1 to buy (units: asset1)

            Returns:
                str: transaction hash of specified order.

            Raises:
                EmptyAPIKey: ...
                EmptySignature: ...


             ############################
            #### UNDER CONSTRUCTION ####
           ############################
        """

        # Does Exchange represent the address of the exchange for the client?
        EXC = Exchange

        # get token ids
        tid1 = int(get_token_id(asset1))
        tid2 = int(get_token_id(asset2))
        trade_pair = asset1 + "-" + asset2


        # get relayer timestamp and calculate some future time... (the added 60x60x1000 'seconds?' is virtual duct tape)
        time_now = get_relayer_time()
        time_now = datetime.datetime.utcfromtimestamp(time_now / 1000)
        print(time_now)
        in5min = time_now + datetime.timedelta(days=100)
        print(in5min)
        print(datetime.datetime.timestamp(in5min))
        in5min = int(datetime.datetime.timestamp(in5min))
        time_now = int(datetime.datetime.timestamp(time_now))

        # get print lowest ask (for debug)
        bp = get_asks(trade_pair)
        bp = float(bp[0][0])
        sp = get_asks(trade_pair)
        sp = float(sp[0][0])
        print("sp,bp = " + str(sp) + ", " + str(bp))

        # get volumes based on 'funding' (print for debug)
        va1 = int(funding/float(bp)    * 10 ** 18)
        va2 = int(funding       * 10 ** 18)
        # print("~ Volumes (1), (2), (2/1) ~")
        print("Trading " + str(va1) + " " + str(asset1)+ " for " + str(va2) + " " + str(asset2) + " (i.e. price = " + str(va2/va1) + ")")
        # print(va2)
        # print(va2 / va1)
        # print()
        # Define Tokens
        buyTok = self.token.Token(id=tid1, volume=va1)
        sellTok = self.token.Token(id=tid2, volume=va2)

        # Execute trades
        sid = await self.get_next_storage_id(sell_token_id=get_token_id(asset1),)
        print(sid)
        msg = await self.submit_order(buy_token=buyTok, sell_token=sellTok, exchange=EXC, fill_amount_b_or_s=False,
                                               max_fee_bips=50, order_type="TAKER_ONLY", storage_id=str(sid['orderId']+2),
                                               trade_channel="MIXED",valid_since=time_now,valid_until=in5min, all_or_none=False)
        return msg


# Future work:
    async def limit_order(self) -> str:
        return -1

#========================================================================================================================
#=================================={Public Client Data & Utilities}======================================================
#========================================================================================================================

# The public client consists of a set of global functions that facilitate interaction with the loopring ecosystem.
# most functions are built for data retrieval, some for data conversion.

def get_depth(trade_pair, level=2, limit=50):
    """ get depth - gets the market depth at the current time
        Args:
            trade_pair (str): the trade pair or market you wish to check
            level: ...
            limit: ...

        Returns:
            json object representing current market depth
    """
    API_URL = "https://api3.loopring.io/api/v3/depth?market=" + trade_pair + "&level=" + str(level) + "&limit=" + str(limit)
    data = {
        "Host": "api3.loopring.io",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh,en;q=0.9",
    }
    response = requests.get(API_URL, data)
    depth = response.json()
    return depth


# ----------------------------------------------------

def get_bids(trade_pair, level=1):
    API_URL = "https://api3.loopring.io/api/v3/depth?market=" + trade_pair + "&level=" + str(level) + "&limit=50"
    data = {
        "Host": "api3.loopring.io",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh,en;q=0.9",
    }
    response = requests.get(API_URL, data)
    depth = response.json()
    bids = depth['bids']
    return bids


# ----------------------------------------------------

def get_asks(trade_pair, level=1):
    API_URL = "https://api3.loopring.io/api/v3/depth?market=" + trade_pair + "&level=" + str(level) + "&limit=50"
    data = {
        "Host": "api3.loopring.io",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh,en;q=0.9",
    }
    response = requests.get(API_URL, data)
    depth = response.json()
    asks = depth['asks']
    return asks


# ==================================================================

def get_ticker(trade_pair):
    API_URL = "https://api3.loopring.io/api/v3/ticker?market=" + trade_pair + ""
    data = {
        "Host": "api3.loopring.io",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept - Language": "zh, enq = 0.9",
    }
    response = requests.get(API_URL, data)
    tickers = response.json()
    ticker = tickers['tickers'][0]
    return ticker

# ==================================================================

def get_relayer_time():
    API_URL = "https://api3.loopring.io/api/v3/timestamp"
    data = {
        "Host": "api3.loopring.io",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept - Language": "zh, enq = 0.9",
    }
    response = requests.get(API_URL, data)
    timestamp = response.json()
    return timestamp['timestamp']


# ==================================================================

def get_trade_pairs():
    # get trade pairs on loopring exchange
    API_URL = "https://api3.loopring.io/api/v3/exchange/markets"
    data = {
        "Host": "api3.loopring.io",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept - Language": "zh, enq = 0.9",
    }
    response = requests.get(API_URL, data)
    mkts = response.json()
    mkt_list = mkts['markets']
    pairs = [''] * len(mkt_list)
    for i in range(0, len(mkt_list)):
        pairs[i] = mkt_list[i]['market']
    return pairs


# ==================================================================

def get_token_id(asset):
    # get trade pairs on loopring exchange
    API_URL = "https://api3.loopring.io/api/v3/exchange/tokens"
    data = {
        "Host": "api3.loopring.io",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept - Language": "zh, enq = 0.9",
    }
    response = requests.get(API_URL, data)
    tkns = response.json()
    tokenid = -1
    # tkn_list = tkns['tokens']
    for i in range(0, len(tkns)):
        if tkns[i]['symbol'] == asset:
            tokenid = tkns[i]['tokenId']

    return tokenid

