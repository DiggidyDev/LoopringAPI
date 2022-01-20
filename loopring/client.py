import asyncio
import json
import time
from asyncio.events import AbstractEventLoop
from datetime import datetime
from typing import List, Sequence, Tuple, Union

import aiohttp
from py_eth_sig_utils.signing import v_r_s_to_signature
from py_eth_sig_utils.utils import ecsign

from .account import Account, Balance
from .amm import Pool, PoolSnapshot, PoolTokens
from .errors import *
from .exchange import Block, DepositHashData, Exchange, TransactionHashData, TransferHashData, WithdrawalHashData
from .market import Candlestick, Market, Ticker, Trade
from .order import CounterFactualInfo, Order, OrderBook, PartialOrder, Transfer
from .token import Fee, Price, Rate, RateInfo, Token, TokenConfig
from .util.enums import Endpoints as ENDPOINT
from .util.enums import Paths as PATH
from .util.helpers import clean_params, raise_errors_in, ratelimit, validate_timestamp
from .util.request import Request
from .util.sdk.sig.ecdsa import EIP712, generate_offchain_withdrawal_EIP712_hash, generate_onchain_data_hash, generate_transfer_EIP712_hash, generate_amm_pool_join_EIP712_hash
from .util.sdk.sig.eddsa import MessageEDDSASign, OrderEDDSASign, TransferEDDSASign, UrlEDDSASign, WithdrawalEDDSASign

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
    nonce: int
    private_key: str
    publicX: str
    publicY: str

    # misc.
    endpoint: ENDPOINT
    exchange: Exchange
    handle_errors: bool
    offchain_ids: list = [0] * 2 ** 16
    order_ids: list    = [0] * 2 ** 16

    def __init__(self,
            account_id: int=None,
            api_key: str=None,
            endpoint: ENDPOINT=None,
            *,
            address: str=None,
            handle_errors: bool=True,
            nonce: int=None,
            private_key: str=None,
            publicX: str=None,
            publicY: str=None,
            **config
        ):
        self.__exchange_domain_initialised = False
        self.__handle_errors = handle_errors
        
        cfg = config.get("config", {})
        
        if not (cfg.get("account_id") or account_id):
            raise InvalidArguments("Missing account ID from config.")
        
        if not (cfg.get("api_key") or api_key):
            raise InvalidArguments("Missing API Key from config.")
        
        if not (cfg.get("endpoint") or endpoint):
            raise InvalidArguments("Missing endpoint from config.")
        
        if not (cfg.get("nonce") or endpoint):
            raise InvalidArguments("Missing nonce from config.")
        
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
        self.nonce       = cfg.get("nonce", nonce)
        self.private_key = cfg.get("private_key", private_key)
        self.publicX     = cfg.get("publicX", publicX)
        self.publicY     = cfg.get("publicY", publicY)

        self.chain_id = 5  # Testnet

        if self.endpoint == ENDPOINT.MAINNET:
            self.chain_id = 1

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

    async def get_amm_pool_balance(self, address: str) -> PoolSnapshot:
        """Get an AMM Pool's balance.
        
        Args:
            address (str): ...
        
        Returns:
            :obj:`~loopring.amm.PoolSnapshot
        
        Raises:
            UnknownError: ...
        
        """

        url = self.endpoint + PATH.AMM_BALANCE

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "poolAddress": address
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            ps = PoolSnapshot(**content)

            return ps

    async def get_amm_pool_configurations(self) -> List[Pool]:
        """Get all AMM Pool configurations.
        
        Returns:
            List[:obj:`~loopring.amm.Pool`]: ...
        
        Raises:
            UnknownError: ...

        """

        url = self.endpoint + PATH.AMM_POOLS

        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            pools = []

            for p in content["pools"]:
                pool = Pool(**p)

                # TODO: Storage IDs and such
                EIP712.init_amm_env(
                    name=pool.name,
                    version=pool.version,
                    chain_id=self.chain_id,
                    verifying_contract=pool.address
                )
                pools.append(pool)
            
            return pools

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

    async def get_block(self,
        *,
        id_or_status: str="confirmed") -> Block:
        """Get block info by ID or status.
        
        Args:
            id_or_status (str): Any of the following; '`finalized`', '`confirmed`', \
                '`12345`'. Defaults to '`confirmed`'.
        
        Returns:
            :obj:`~loopring.exchange.Block`: ...
        
        Raises:
            UnknownError: ...
        
        """

        url = self.endpoint + PATH.BLOCK_INFO

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "id": id_or_status
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            block = Block(**content)

            return block

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

    async def get_user_transfer_history(self,
        *,
        account_id: int=None,
        end: Union[int, datetime]=None,
        hashes: Union[str, Sequence[str]]=None,
        limit: int=None,
        offset: int=None,
        start: Union[int, datetime]=None,
        status: str=None,
        token_symbol: str=None,
        transfer_types: str=None) -> List[TransferHashData]:
        """Get a user's transfer history."""

        url = self.endpoint + PATH.USER_TRANSFERS

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
            "transferTypes": transfer_types
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            transfers = []

            for t in content["transactions"]:
                transfers.append(TransferHashData(**t))
            
            return transfers

    async def init_exchange_configuration(self) -> None:
        """Initialise the exchange config for L1 requests."""
        self.exchange = await self.get_exchange_configurations()

        if not self.__exchange_domain_initialised:
            EIP712.init_env(
                chain_id=self.exchange.chain_id,
                verifying_contract=str(self.exchange)
            )

            self.__exchange_domain_initialised = True

    async def join_amm_pool(self,
        *,
        fee: Union[int, Fee],
        join_tokens: PoolTokens,
        owner: str=None,
        pool: Union[str, Pool],
        storage_ids: List[int]=None,
        valid_until: Union[int, datetime]=None) -> Transfer:
        """Join an AMM Pool."""

        supplied_storage_ids = True

        if valid_until is None:
            valid_until = int(time.time()) + 60 * 60 * 24 * 60
        
        if not storage_ids:
            supplied_storage_ids = False
            assert len(join_tokens.pooled) == 2

            storage_ids = [
                self.offchain_ids[join_tokens.pooled[0].id],
                self.offchain_ids[join_tokens.pooled[1].id]
            ]

        url = self.endpoint + PATH.AMM_JOIN

        headers = {
            "X-API-KEY": self.api_key
        }
        payload = clean_params({
            "fee": fee if isinstance(fee, int) else fee.fee,
            "joinTokens": join_tokens.to_params(),
            "owner": owner or self.address,
            "poolAddress": pool if isinstance(pool, str) else pool.address,
            "storageIds": storage_ids,
            "validUntil": validate_timestamp(valid_until, "seconds", validate_future=True)
        })

        request = Request(
            "post",
            self.endpoint,
            PATH.AMM_JOIN,
            payload=payload
        )

        message = generate_amm_pool_join_EIP712_hash(request.payload)

        if not supplied_storage_ids:
            self.offchain_ids[join_tokens.pooled[0].id] += 2
            self.offchain_ids[join_tokens.pooled[1].id] += 2

        helper = MessageEDDSASign(private_key=self.private_key)
        payload["eddsaSignature"] = helper.sign(message)

        print(payload)
        exit()

        async with self._session.post(url, headers=headers, payload=payload) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            transfer = Transfer(**content)

            return transfer

    # TODO: Mapping for request types!
    async def query_order_fee(self,
        *,
        account_id: int=None,
        amount: str=None,
        request_type: int=1,
        token_symbol: str="LRC") -> Tuple[str, List[Fee]]:
        """Return a fee amount.

        Args:
            account_id (int): ...
            amount (str): ...
            request_type (int): 0=Order, 1=Offchain Withdrawal, 2=Update Account, \
                3=Transfer, 4=Fast Offchain Withdrawal, 5=Open Account, 6=AMM Exit, \
                7=Deposit, 8=AMM Join
            token_symbol: ...

        Returns:
            Tuple[str, List[:obj:`~loopring.token.Fee`]]: ...

        Raises:
            UnknownError: ... .

        """

        url = self.endpoint + PATH.USER_OFFCHAIN_FEE

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "amount": amount,
            "requestType": request_type,
            "tokenSymbol": token_symbol
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            fees = []

            for f in content["fees"]:
                fees.append(Fee(**f))

            return content["gasPrice"], fees

    async def query_order_minimum_fees(self,
        *,
        account_id: int=None,
        market: str="LRC-ETH") -> Tuple[str, datetime, List[RateInfo]]:
        """Get the current trading pair (market)'s  fees.
        
        Args:
            account_id (int): ...
            market (str): ...
        
        Returns:
            Tuple[str, :class:`~datetime.datetime`, List[:obj:`~loopring.token.RateInfo`]]: ...

        Raises:
            UnknownError: ...

        """

        url = self.endpoint + PATH.USER_ORDER_RATES

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "market": market
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            rates = []
            
            for a in content["amounts"]:
                rates.append(RateInfo(**a))

            cache_expiry = datetime.fromtimestamp(content["cacheOverdueAt"])

            return content["gasPrice"], cache_expiry, rates

    async def query_order_rates(self,
        *,
        account_id: int=None,
        market: str="LRC-ETH",
        token: Token) -> Rate:
        """Query an order fee on a market for a given token and volume.

        Args:
            account_id (int): ... .
            market (str): Defaults to '`LRC-ETH`'.
            token (:obj:`~loopring.token.Token`): ... .

        Returns:
            :obj:`~loopring.token.Fee`: ...

        Raises:
            UnknownError: ... .

        """

        url = self.endpoint + PATH.USER_ORDER_FEE

        headers = {
            "X-API-KEY": self.api_key
        }
        params = {
            "accountId": account_id or self.account_id,
            "amountB": token.volume,
            "market": market,
            "tokenB": token.id
        }

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            rate_content: dict = content.pop("feeRate")
            rate_content.update(content)

            rate = Rate(**rate_content)

            return rate

    async def submit_internal_transfer(self,
        *,
        client_id: str=None,
        ecdsa_key: str,
        exchange: Union[str, Exchange]=None,
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
        memo: str=None) -> Transfer:
        """Submit an internal transfer.

        Args:
            client_id (str): ... .
            counter_factual_info (:obj:`~loopring.order.CounterFactualInfo`): ... .
            ecdsa_key (str): Ethereum L1 private key.
            exchange (Union[str, :obj:`~loopring.exchange.Exchange`]): ... .
            max_fee (:obj:`~loopring.token.Token`): ... .
            memo (str): ... .
            payee_address (str): ... .
            payee_id (int): ... .
            payer_address (str): ... .
            payer_id (int): ... .
            storage_id (int): ... .
            token (:obj:`~loopring.token.Token`): ... .
            valid_since (Union[int, :class:`~datetime.datetime`]): ... .
            valid_until (Union[int, :class:`~datetime.datetime`]): ... .

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
        valid_since = int(datetime.timestamp(datetime.now()))

        url = self.endpoint + PATH.TRANSFER

        payload = clean_params({
            "clientId": client_id,
            "counterFactualInfo": counter_factual_info,
            "exchange": exchange or str(self.exchange),
            "maxFee": {
                "tokenId": max_fee.id,
                "volume": max_fee.volume
            },
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
            "validSince": validate_timestamp(valid_since, "seconds"),
            "validUntil": validate_timestamp(valid_until, "seconds", True)
        })

        request = Request(
            "post",
            self.endpoint,
            PATH.TRANSFER,
            payload=payload
        )

        # EcDSA Signature
        message = generate_transfer_EIP712_hash(request.payload)

        ecdsa_key_bytes = int(ecdsa_key, 16).to_bytes(32, byteorder="big")
        v, r, s = ecsign(message, ecdsa_key_bytes)

        ecdsa_signature = "0x" + bytes.hex(v_r_s_to_signature(v, r, s)) + "02"  # EIP_712

        headers = {
            "X-API-KEY": self.api_key,
            "X-API-SIG": ecdsa_signature
        }

        # EdDSA Signature
        helper = TransferEDDSASign(private_key=self.private_key)
        eddsa_signature = helper.sign(request.payload)

        payload["eddsaSignature"] = eddsa_signature

        async with self._session.post(url, headers=headers, json=payload) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            return Transfer(**content)

    async def submit_offchain_withdrawal_request(self,
        *,
        account_id: int=None,
        counter_factual_info: CounterFactualInfo=None,
        ecdsa_key: str,
        exchange: Union[str, Exchange]=None,
        extra_data: bytes=b"",
        fast_withdrawal_mode: bool=None,
        hash_approved: str=None,
        owner: str,
        max_fee: Token,
        min_gas: int=0,
        storage_id: int,
        to: str,
        token: Token,
        valid_since: Union[int, datetime]=None,
        valid_until: Union[int, datetime]=None) -> PartialOrder:
        """Submit an offchain withdrawal request."""

        if not valid_until:
            # Default to 2 months:
            # See 'https://docs.loopring.io/en/basics/orders.html#timestamps'
            # for information about order validity and time
            valid_until = int(time.time()) + 60 * 60 * 24 * 60
        valid_since = int(datetime.timestamp(datetime.now()))

        url = self.endpoint + PATH.USER_WITHDRAWALS

        onchain_data_hash = "0x" + bytes.hex(
            generate_onchain_data_hash(
                min_gas=min_gas, to=to, extra_data=extra_data
            )
        )

        payload = clean_params({
            "accountId": account_id or self.account_id,
            "counterFactualInfo": counter_factual_info,
            "exchange": exchange or str(self.exchange),
            "extraData": extra_data,
            "fastWithdrawalMode": fast_withdrawal_mode,
            "hashApproved": hash_approved,
            "onChainDataHash": onchain_data_hash,
            "owner": owner,
            "maxFee": {
                "tokenId": max_fee.id,
                "volume": max_fee.volume
            },
            "minGas": min_gas,
            "storageId": storage_id,
            "to": to,
            "token": {
                "tokenId": token.id,
                "volume": token.volume
            },
            "validSince": validate_timestamp(valid_since, "seconds"),
            "validUntil": validate_timestamp(valid_until, "seconds", True)
        })

        request = Request(
            "post",
            self.endpoint,
            PATH.USER_WITHDRAWALS,
            payload=payload
        )

        message = generate_offchain_withdrawal_EIP712_hash(request.payload)
        ecdsa_key_bytes = int(ecdsa_key, 16).to_bytes(32, byteorder="big")
        v, r, s = ecsign(message, ecdsa_key_bytes)

        ecdsa_signature = "0x" + bytes.hex(v_r_s_to_signature(v, r, s)) + "02"

        headers = {
            "X-API-KEY": self.api_key,
            "X-API-SIG": ecdsa_signature
        }

        helper = WithdrawalEDDSASign(private_key=self.private_key)
        eddsa_signature = helper.sign(request.payload)

        payload["ecdsaSignature"] = ecdsa_signature
        payload["eddsaSignature"] = eddsa_signature
        payload["extraData"] = payload.get("extraData", b"").decode()

        async with self._session.post(url, headers=headers, json=payload) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            withdrawal = PartialOrder(**content)

            return withdrawal

    async def submit_order(self,
                        *,
                        affiliate: str=None,
                        all_or_none: str=False,
                        buy_token: Token,
                        client_order_id: str=None,
                        exchange: Union[str, Exchange]=None,
                        fill_amount_b_or_s: bool,
                        max_fee_bips: int,
                        order_type: str=None,
                        pool_address: str=None,
                        sell_token: Token,
                        storage_id: int,
                        taker: str=None,
                        trade_channel: str=None,
                        valid_since: Union[int, datetime]=None,
                        valid_until: Union[int, datetime]=None
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
            exchange (Union[str, :obj:`~loopring.exchange.Exchange`]): The address of \
                the exchange used to process this order.
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
            valid_since (Union[int, :class:`~datetime.datetime`): The order's init \
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

        if not (self.__exchange_domain_initialised or exchange):
            raise InvalidArguments("Please initialise the exchange or provide one.")
        
        if not valid_until:
            # Default to 2 months:
            # See 'https://docs.loopring.io/en/basics/orders.html#timestamps'
            # for information about order validity and time
            valid_until = int(time.time()) + 60 * 60 * 24 * 60
        valid_since = int(datetime.timestamp(datetime.now()))

        url = self.endpoint + PATH.ORDER

        payload = clean_params({
            "accountId": self.account_id,
            "affiliate": affiliate,

            # 'allOrNone' currently doesn't accept anything
            # other than 'False' - this will be editable
            # once the API starts accepting other values
            "allOrNone": False,

            "buyToken": {
                "tokenId": buy_token.id,
                "volume": buy_token.volume
            },
            "clientOrderId": client_order_id,
            "exchange": exchange or str(self.exchange),
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
            "validSince": validate_timestamp(valid_since, "seconds"),
            "validUntil": validate_timestamp(valid_until, "seconds", True)
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

