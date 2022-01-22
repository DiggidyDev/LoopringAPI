import asyncio
import json
import logging
import time
from asyncio.events import AbstractEventLoop
from datetime import datetime
from typing import Dict, List, Literal, Sequence, Tuple, Union

import aiohttp
from py_eth_sig_utils.signing import v_r_s_to_signature
from py_eth_sig_utils.utils import ecsign

from .account import Account, Balance
from .amm import AMMTrade, AMMTransaction, ExitPoolTokens, JoinPoolTokens, Pool, PoolSnapshot
from .errors import *
from .exchange import Block, DepositHashData, Exchange, TransactionHashData, TransferHashData, TxModel, WithdrawalHashData
from .market import Candlestick, Market, Ticker, Trade
from .order import CounterFactualInfo, Order, OrderBook, PartialOrder, Transfer
from .token import Fee, Price, Rate, RateInfo, Token, TokenConfig
from .util.enums import Endpoints as ENDPOINT
from .util.enums import IntSig
from .util.enums import Paths as PATH
from .util.helpers import clean_params, raise_errors_in, ratelimit, validate_timestamp
from .util.request import Request
from .util.sdk.sig.ecdsa import EIP712, generate_amm_pool_exit_EIP712_hash, generate_offchain_withdrawal_EIP712_hash, generate_onchain_data_hash, generate_transfer_EIP712_hash, generate_amm_pool_join_EIP712_hash, generate_update_account_EIP712_hash
from .util.sdk.sig.eddsa import MessageEDDSASign, OrderEDDSASign, TransferEDDSASign, UpdateAccountEDDSASign, UrlEDDSASign, WithdrawalEDDSASign

# TODO: Do something about exception classes... it's getting a bit messy.
#       Also, rewrite some of the descriptions.
#       Idea: subclass some of the errors? e.g.
#       `OrderNotFound` could also be used when there isn't an order to cancel...

# TODO: UpdateAccountEDDSAKey endpoint (need keySeed? from account query)

# TODO: Maybe accept `Fee` as the type for `max_fee` args, instead of `Token`


_BLOCK_TYPEHINT = Union[int, Literal["finalized", "confirmed"]]
_INTERVALS_TYPEHINT = Literal[
    "1min", "5min", "15min", "30min", "1hr", "2hr", "4hr", "12hr", "1d", "1w"
]
_KT_STORAGE = Literal["offchainId", "orderId"]
_SIDE = Literal["buy", "sell"]


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

    # Account annotations
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
    markets: Dict[str, Market] = {}
    pools: Dict[str, Pool] = {}
    storage_ids: Dict[int, Dict[_KT_STORAGE, int]] = {}
    tokens: Dict[int, TokenConfig] = {}

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

        # I had the option to run this concurrently in a different thread,
        # but decided it would be best to have the initialisation step be
        # blocking so the user's requests don't go through until it's safe
        self._loop.run_until_complete(self.__init_local_storage())

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

    # TODO: Check order status as soon as order is submitted;
    #       need to verify assumption in docs with `status` arg.
    async def cancel_order(self,
            *,
            client_order_id: str=None,
            orderhash: str=None
        ) -> PartialOrder:
        """Cancel a submitted order.

        The order hash can either be stored locally upon submission creation, or \
            fetched with :meth:`~loopring.client.Client.get_multiple_orders()` using \
            the `status` argument set to '`processing`'

        Args:
            client_order_id: A label to describe the order. This has no \
                impact on trading.
            orderhash: The order hash of a submitted order response.

        Returns:
            An object containing information about the cancelled order.  See \
                :meth:`~loopring.client.Client.submit_order()`.
        
        Raises:
            EmptyAPIKey: No API Key was provided in the request header.
            InvalidAccountID: An invalid account ID was supplied.
            InvalidAPIKey: An incorrect API Key was provided in the request header.
            NoOrderToCancel: No order could be found matching the given critera.
            OrderCancellationFailed: Your order cancellation request failed.
            UnknownError: Something out of your control (probably) went wrong!

        """

        url = self.endpoint + PATH.ORDER
        params = clean_params({
            "accountId": self.account_id,
            "clientOrderId": client_order_id,
            "orderHash": orderhash
        })

        req = Request("delete", self.endpoint, PATH.ORDER, params=params)

        helper = UrlEDDSASign(self.private_key, self.endpoint)
        eddsa_signature = helper.sign(req)

        headers = {
            "X-API-KEY": self.api_key,
            "X-API-SIG": eddsa_signature
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

    async def exit_amm_pool(self,
            *,
            exit_tokens: ExitPoolTokens,
            max_fee: int,
            pool: Union[str, Pool, PoolSnapshot],
            valid_until: Union[int, datetime]=None
        ) -> Transfer:
        """Exit an AMM pool.
        
        Args:
            exit_tokens: The exit tokens with which to exit.  Bear in mind that the \
                order of the `unpooled` tokens does matter.
            max_fee: ... .
            pool: The AMM pool you wish to exit.
            valid_until: A UNIX timestamp or datetime object representing the time \
                of expiry for the submitted order.  Please note that your order may \
                be cancelled by the relayer if this date is shorter than a week in \
                the future.  See \
                `here <https://docs.loopring.io/en/basics/orders.html#timestamps>`_ \
                for more info.
        
        Returns:
            A transfer record containing information about the AMM exit event.
        
        Raise:
            InconsistentTokens: Transfer token is inconsistent with the fee token.
            InvalidArguments: Invalid arguments supplied.
            InvalidExchangeID: Invalid exchange ID supplied.
            InvalidNonce: Invalid nonce supplied.
            InvalidTransferReceiver: Transfer receiver address is invalid.
            InvalidTransferSender: Transfer sender address is invalid.
            UnknownError: Something out of your control went wrong.
            UnsupportedFeeToken: Provided fee token is unsupported.  See \
                :meth:`~loopring.client.Client.get_token_configurations()`.
            
        """

        url = self.endpoint + PATH.AMM_EXIT

        headers = {
            "X-API-KEY": self.api_key
        }
        # No need for `clean_params()` because all keys here are required
        payload = {
            "exitTokens": exit_tokens.to_params(),
            "maxFee": max_fee,
            "owner": self.address,
            "poolAddress": str(pool),
            "storageId": self.offchain_ids[exit_tokens.burned.id],
            "validUntil": validate_timestamp(valid_until, "seconds", validate_future=True)
        }

        request = Request(
            "post",
            self.endpoint,
            PATH.AMM_EXIT,
            payload=payload
        )

        message = generate_amm_pool_exit_EIP712_hash(request.payload)
        
        helper = MessageEDDSASign(private_key=self.private_key)
        eddsa_signature = helper.sign(message)

        payload["eddsaSignature"] = eddsa_signature

        self.storage_ids[exit_tokens.burned.id]["offchainId"] += 2

        async with self._session.post(url, headers=headers, json=payload) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            transfer = Transfer(**content)
            return transfer

    async def get_account_info(self, address: str) -> Account:
        """Returns data associated with the user's exchange account.
        
        Args:
            address: The ethereum address belonging to the account of which you \
                want information from.
        
        Returns:
            An account containing all publicly available information.
        
        Raises:
            AddressNotFound: The ethereum address wasn't found.
            UnknownError: Something out of of your control went wrong.
            UserNotFound: User account not found.

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

    async def get_amm_pool_balance(self, pool: Union[str, Pool]) -> PoolSnapshot:
        """Get an AMM Pool's balance.
        
        Args:
            pool: The pool whose balance you want to query.
        
        Returns:
            A pool snapshot containing LP token information and general pool data.
        
        Raises:
            UnknownError: Something out of your control went wrong.
        
        """

        url = self.endpoint + PATH.AMM_BALANCE

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "poolAddress": str(pool)
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

        This function only needs to be called once, as the pools are stored in
        local storage.  For longer-running clients, it is recommended to
        periodically call this function to keep local storage pools up to date.

        Returns:
            A list containing all pools supported on the Loopring exchange.

        Raises:
            UnknownError: Something out of your control went wrong.

        """
        logging.debug("Initialising pool config...")

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

                self.pools[pool.market] = pool

            logging.debug("Finished initialising pool config...")

            return pools

    # TODO: Find out how many trades are returned by default.
    #       Also, maybe store `totalNum` from the response?
    #       Remove EmptyUser and InvalidAccountID from docstring?
    #       It doesn't make sense, given the args supplied
    async def get_amm_trade_history(self,
            amm_pool: Union[str, Pool, PoolSnapshot],
            limit: int=None,
            offset: int=None
        ) -> List[AMMTrade]:
        """Get a pool's AMM trade history.

        Combining `limit` and `offset` together can be useful for implementing
        pagination.
        
        Args:
            amm_pool: The pool whose trade history you want to query.
            limit: The number of trade records to be returned.
            offset: Apply an offset when searching through the trade records.
        
        Returns:
            A list of trades, capped to a length of `limit`.
        
        Raises:
            EmptyAPIKey: No API Key has been supplied.
            EmptyUser: No User ID has been supplied.
            InvalidAccountID: The supplied Account ID was invalid.
            InvalidAPIKey: The supplied API Key was invalid.
            UnknownError: Something out of your control went wrong.

        """

        url = self.endpoint + PATH.AMM_TRADES

        params = clean_params({
            "ammPoolAddress": str(amm_pool),
            "limit": limit,
            "offset": offset
        })

        async with self._session.get(url, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            trades = []

            for t in content["trades"]:
                trades.append(AMMTrade(**t))
            
            return trades

    # TODO: Remove unnecessary error codes?
    async def get_api_key(self) -> str:
        """Get the API Key associated with the account.

        Your L2 wallet private key must be supplied in the client config in order
        for the API's authentication to succeed.

        Returns:
            str: The API Key associated with the account ID.

        Raises:
            EmptyAPIKey: No API Key has been supplied.
            EmptySignature: No API Signature was supplied.
            InvalidAccountID: An invalid Account ID was supplied.
            InvalidAPIKey: An invalid API Key was supplied.
            InvalidSignature: An invalid signature was supplied in the header.
            UnknownError: Something went wrong out of your control.
            UserNotFound: User wasn't found.

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

    async def get_block(self, *, id_or_status: _BLOCK_TYPEHINT="confirmed") -> Block:
        """Get a layer 2 block by ID or status.
        
        Args:
            id_or_status: Any of the following values are accepted; '`finalized`', \
                '`confirmed`', '`12345`'. Defaults to '`confirmed`'.
        
        Returns:
            A layer 2 block, with a list of transactions (txs) belonging to it.
        
        Raises:
            UnknownError: Something out of your control went wrong.
        
        """

        url = self.endpoint + PATH.BLOCK_INFO

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "id": str(id_or_status)
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            block = Block(**content)

            return block

    async def get_exchange_configurations(self) -> Exchange:
        """Get configurations of loopring's exchange.

        Returns:
            The exchange configuration for the currently connected endpoint.

        Raises:
            UnknownError: Something went wrong out of your control

        """

        logging.debug("Initialising exchange config...")

        url = self.endpoint + PATH.EXCHANGES

        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            exchange = Exchange(**content)

            self.exchange = exchange

            if not self.__exchange_domain_initialised:
                EIP712.init_env(
                    chain_id=self.exchange.chain_id,
                    verifying_contract=str(self.exchange)
                )

                self.__exchange_domain_initialised = False
            
            logging.debug("Finished initialising exchange config...")

            return exchange

    async def get_fiat_prices(self, currency: str="USD") -> List[Price]:
        """Fetches fiat prices for all tokens supported on Loopring.

        Note:
            Check the `updated_at` property of the returned prices, as they could be
            out of sync by a couple of days.

        Args:
            currency (str): All supported values: "`USD`", "`CNY`", "`JPY`", 
                "`EUR`", "`GBP`", "`HKD`". Defaults to "`USD`".
        
        Returns:
            All prices of supported tokens, in the given `currency`.

        Raises:
            UnknownError: Something went wrong out of your control.

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

    async def get_market_candlesticks(self,
            market: Union[str, Market]="LRC-ETH",
            interval: _INTERVALS_TYPEHINT="5min",
            *,
            end: Union[int, datetime]=None,
            limit: int=None,
            start: Union[int, datetime]=None
        ) -> List[Candlestick]:
        """Get candlestick data for a given `market` (trading pair).

        Args:
            market: Defaults to "`LRC-ETH`".  See all possible trading pairs in \
                :meth:`~loopring.client.Client.get_market_configurations()`.
            interval: Defaults to `5min`.
            start: The earliest time from which candlesticks can be returned (i.e. \
                from `start` to `end`, or from `start` to the current time if `end` \
                is `None`).
            end: The latest time of which a candlestick could indicate.
            limit: Number of candlesticks returned - if more are available, only
                the first, `limit` number data points will be returned.
        
        Returns:
            A list of candlestick objects, capped at `limit` sticks, between `start`
            and `end`.

        Raises:
            InvalidArguments: Supplied arguments are invalid.
            TypeError: From timestamp validation.
            UnknownError: Something out of your control went wrong.
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
            All markets listed on the exchange.
        
        Raises:
            UnknownError: Something out of your control went wrong.

        """

        logging.debug("Initialising market config...")

        url = self.endpoint + PATH.MARKETS

        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            markets = []

            for m in content["markets"]:
                market = Market(**m)
                markets.append(market)

                self.markets[market.market] = market

            logging.debug("Finished initialising market config...")
            
            return markets

    async def get_market_orderbook(self,
            market: Union[str, Market]="LRC-ETH",
            *,
            depth: int=2,
            limit: int=50
        ) -> OrderBook:
        """Get the orderbook of a specific market (trading pair).

        Args:
            limit: The maximum number of orders (bids/asks combined) to receive.  \
                Defaults to 50.
            market: The `market` (trading pair) whose orderbook you want to receive.  \
                Defaults to 'LRC-ETH'.
            depth: The order book's aggregation level - the larger, the larger the \
                depth will be.  Defaults to 2.
        
        Returns:
            An orderbook containing bids and asks.

        Raises:
            OrderbookUnsupportedMarket: An unsupported trading pair was supplied.
            UnknownError: Something out of your control went wrong.
            UnsupportedDepthLevel: An unsupported price aggregation

        """

        url = self.endpoint + PATH.DEPTH

        params = {
            "level": depth,
            "limit": limit,
            "market": str(market)
        }

        async with self._session.get(url, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            orderbook = OrderBook(**content)

            return orderbook

    async def get_market_ticker(self,
            market: Union[str, Market, List[Market]]="LRC-ETH"
        ) -> List[Ticker]:
        """Get a ticker for a specific market or multiple markets.

        Args:
            market: A market, or multiple markets, whose ticker(s) you want to \
                receive.  If passing multiple trading pairs as a string, you may \
                separate with commas;
                `"LRC-ETH,LINK-ETH,HEX-ETH"`

        Returns:
            A list of tickers, matching the order of supplied markets if multiple 
            markets were supplied.

        Raises:
            InvalidArguments: A supplied argument was invalid.
            UnknownError: Something out of your control went wrong.

        """

        if isinstance(market, list):
            market = ",".join([str(m) for m in market])

        url = self.endpoint + PATH.TICKER

        params = {
            "market": str(market)
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

    # TODO: Add order types enum?
    async def get_multiple_orders(self, *,
            end: Union[int, datetime]=None,
            limit: int=50,
            market: Union[str, Market]=None,
            offset: int=0,
            order_types: str=None,
            side: str=None,
            start: Union[int, datetime]=None,
            status: str=None,
            trade_channels: str=None
        ) -> List[Order]:
        """Get a list of orders satisfying certain criteria.

        Note:
            All arguments are optional. All string-based arguments are
            case-insensitive. For example, `trade_channels='MIXED'` returns the
            same results as `trade_channels='mIxEd'`.

        Args:
            end: The upper bound of an order's creation time.
            limit: The maximum number of orders to be returned. Defaults to `50`.
            market: The trading pair. Example: `'LRC-ETH'`.
            offset: The offset of orders. Defaults to `0`.
            order_types: Types of orders available:
                `'LIMIT_ORDER'`, `'MAKER_ONLY'`, `'TAKER_ONLY'`, `'AMM'`. 
            side: The type of order made, a `'BUY'` or `'SELL'`.
            start: The lower bound of an order's creation time.
            status: The order's status: \
                `'PROCESSING'`, `'PROCESSED'`, `'FAILED'`, `'CANCELLED'`, \
                `'CANCELLING'`, `'EXPIRED'`. Multiple statuses can be selected: \
                `'CANCELLING, CANCELLED'`
            trade_channels: The channel which said trade was made in: `'ORDER_BOOK'`, \
                `'AMM_POOL'`, `'MIXED'`.
        
        Returns:
            A list of orders on a successful query. The returned list could be empty
            if no orders met the given conditions.

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

    async def get_next_storage_id(self,
            *,
            max_next: int=None,
            token: Union[int, Token, TokenConfig]
        ) -> Dict[_KT_STORAGE, int]:
        """Get the next storage ID.

        When making any offchain or order request for the first time each session,
        it's important to call this method to update the cached storage ID
        information.
        
        Once you've queried the storage ID for a token, you won't need
        to worry about making another query for the same token during the program's
        lifetime.  There is an exception to this - for longer running programs that
        don't restart often, it's a good idea to periodically make this API request
        in order to keep in sync with the relayer.

        Examples:
            If you know ahead of time which tokens you'll be interacting with on the
            blockchain, you're able to query those tokens concurrently to cut down
            on program runtime;

            .. code-block:: python3

                symbols = ["LRC", "ETH", "LINK"]
                tokens = [fetch(client.tokens, symbol=s) for s in symbols]

                await asyncio.gather(*[client.get_next_storage_id(token=t) for t in tokens])
        
            It's important to not do this with too many symbols at once, as you
            could be ratelimited (TODO: check info on ratelimiting!).

            .. seealso:: Coroutines can be executed concurrently using
                :py:func:`asyncio.gather()`

        Args:
            max_next: ... .
            token: The unique identifier of the token which the user wants \
                to sell in the next order.

        Returns:
            A :obj:`dict` containing the `orderId` and `offchainId`.

        Raises:
            EmptyAPIKey: No API Key was supplied.
            InvalidAccountID: Supplied account ID was deemed invalid.
            InvalidAPIKey: Supplied API Key was deemed invalid.
            InvalidArguments: Invalid arguments supplied.
            TypeError: A given argument was an invalid type.
            UnknownError: Something out of your control has gone wrong.
            UserNotFound: Didn't find the user from the given account ID.

        """

        url = self.endpoint + PATH.STORAGE_ID
        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": self.account_id,
            "sellTokenId": int(token),
            "maxNext": max_next
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: Dict[_KT_STORAGE, int] = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            self.storage_ids[int(token)] = content

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
            withdrawal_types: str=None
        ) -> List[WithdrawalHashData]:
        """Get a user's onchain withdrawal history.
        
        Args:
            account_id: The Account ID of the user whose withdrawal history you want \
                to query.
            end: --
            hashes: --
            limit: The number of withdrawal records to get.
            offset: 
            start:
            status:
            token_symbol:
            withdrawal_types:

        Returns:
            A list of 

        Raises:
            EmptyAPIKey: No API Key was supplied.
            EmptyUser: No Account ID was supplied.
            InvalidAccountID: An invalid Account ID was supplied.
            InvalidAPIKey: An invalid API Key was supplied.
            UnknownError: Something out of your control went wrong.

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
            InvalidArguments: ...

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

    async def get_pending_block_transactions(self) -> List[TxModel]:
        """Get pending txs to be packed into the next block."""

        url = self.endpoint + PATH.BLOCK_PENDING_TXS

        headers = {
            "X-API-KEY": self.api_key
        }

        async with self._session.get(url, headers=headers) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            transactions = []

            for tx in content:
                transactions.append(TxModel(**tx))

            return transactions

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

    # TODO: deal with timezone differences
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
            UnknownError: Something out of your control went wrong.

        """

        logging.debug("Initialising token config...")

        url = self.endpoint + PATH.TOKENS

        async with self._session.get(url) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)

            token_confs = []

            for t in content:
                token_config = TokenConfig(**t)
                token_confs.append(token_config)

                self.tokens[token_config.token_id] = token_config
                self.storage_ids[token_config.token_id] = {
                    "offchainId": 0,
                    "orderId": 1
                }

            logging.debug("Finished initialising token config...")
            
            return token_confs

    async def get_user_amm_join_exit_history(self,
        *,
        account_id: int=None,
        amm_pool: Union[str,  Pool, PoolSnapshot],
        end: Union[int, datetime]=None,
        limit: int=None,
        offset: int=None,
        start: Union[int, datetime]=None,
        tx_status: str=None,
        tx_types: str=None) -> List[AMMTransaction]:
        """Get a user's AMM join/exit history."""

        url = self.endpoint + PATH.AMM_USER_TRANSACTIONS

        headers = {
            "X-API-KEY": self.api_key
        }
        params = clean_params({
            "accountId": account_id or self.account_id,
            "ammPoolAddress": str(amm_pool),
            "end": validate_timestamp(end),
            "limit": limit,
            "offset": offset,
            "start": validate_timestamp(start),
            "txStatus": tx_status,
            "txTypes": tx_types
        })

        async with self._session.get(url, headers=headers, params=params) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            transactions = []

            for t in content["transactions"]:
                transactions.append(AMMTransaction(**t))

            return transactions

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

    async def __init_local_storage(self) -> None:
        """Initialise all local storage."""

        configs = [
            self.get_amm_pool_configurations(),
            self.get_exchange_configurations(),
            self.get_market_configurations(),
            self.get_token_configurations()
        ]

        gathered = await asyncio.gather(*configs, return_exceptions=True)

        for result in gathered:
            if isinstance(result, Exception):
                raise result

        logging.info("Finished local storage initialisation")

    async def join_amm_pool(self,
            *,
            fee: Union[int, Fee],
            join_tokens: JoinPoolTokens,
            pool: Union[str, Pool],
            valid_until: Union[int, datetime]=None
        ) -> Transfer:
        """Join an AMM Pool."""

        if valid_until is None:
            valid_until = int(time.time()) + 60 * 60 * 24 * 60
        
        assert len(join_tokens.pooled) == 2

        storage_ids = [
            self.storage_ids[_.id]["offchainId"] for _ in join_tokens.pooled
        ]

        url = self.endpoint + PATH.AMM_JOIN

        headers = {
            "X-API-KEY": self.api_key
        }
        payload = clean_params({
            "fee": int(fee),
            "joinTokens": join_tokens.to_params(),
            "owner": self.address,
            "poolAddress": str(pool),
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

        self.storage_ids[join_tokens.pooled[0].id]["offchainId"] += 2
        self.storage_ids[join_tokens.pooled[1].id]["offchainId"] += 2

        helper = MessageEDDSASign(private_key=self.private_key)
        payload["eddsaSignature"] = helper.sign(message)

        async with self._session.post(url, headers=headers, json=payload) as r:
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
            account_id: 
            market: The trading pair, or market, to receive fees information about.
        
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

    def stop(self) -> None:
        """Exit out of the program."""
        self._loop.stop()

    async def submit_internal_transfer(self,
            *,
            client_id: str=None,
            ecdsa_key: str,
            payer_id: int,
            payer_address: str,
            payee_id: int,
            payee_address: str,
            token: Token,
            max_fee: Token,
            valid_until: Union[int, datetime]=None,
            counter_factual_info: CounterFactualInfo=None,
            memo: str=None
        ) -> Transfer:
        """Submit an internal transfer.

        Args:
            client_id (str): ... .
            counter_factual_info (:obj:`~loopring.order.CounterFactualInfo`): ... .
            ecdsa_key (str): Ethereum L1 private key.
            max_fee (:obj:`~loopring.token.Token`): ... .
            memo (str): ... .
            payee_address (str): ... .
            payee_id (int): ... .
            payer_address (str): ... .
            payer_id (int): ... .
            token (:obj:`~loopring.token.Token`): ... .
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
        
        storage_id = self.storage_ids[token.id]["offchainId"]
        self.storage_ids[token.id]["offchainId"] += 2

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
            "exchange": str(self.exchange),
            "maxFee": max_fee.to_params(),
            "memo": memo,
            "payeeAddr": payee_address,
            "payeeId": payee_id,
            "payerAddr": payer_address,
            "payerId": payer_id,
            "storageId": storage_id,
            "token": token.to_params(),
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
        counter_factual_info: CounterFactualInfo=None,
        ecdsa_key: str,
        extra_data: bytes=b"",
        fast_withdrawal_mode: bool=None,
        hash_approved: str=None,
        owner: str,
        max_fee: Token,
        min_gas: int=0,
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

        storage_id = self.storage_ids[token.id]["offchainId"]
        self.storage_ids[token.id]["offchainId"] += 2

        url = self.endpoint + PATH.USER_WITHDRAWALS

        onchain_data_hash = "0x" + bytes.hex(
            generate_onchain_data_hash(
                min_gas=min_gas, to=to, extra_data=extra_data
            )
        )

        payload = clean_params({
            "accountId": self.account_id,
            "counterFactualInfo": counter_factual_info,
            "exchange": str(self.exchange),
            "extraData": extra_data,
            "fastWithdrawalMode": fast_withdrawal_mode,
            "hashApproved": hash_approved,
            "onchainDataHash": onchain_data_hash,
            "owner": owner,
            "maxFee": max_fee.to_params(),
            "minGas": min_gas,
            "storageId": storage_id,
            "to": to,
            "token": token.to_params(),
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
            side: _SIDE,
            target: Token,
            *,
            affiliate: int=None,
            client_order_id: str=None,
            in_return_for: Token=None,
            max_fee_bips: int,
            order_type: str=None,
            pool_address: Union[str, Pool, PoolSnapshot]=None,
            taker: str=None,
            trade_channel: str=None,
            using: Token=None,
            valid_until: Union[int, datetime]=None
        ) -> PartialOrder:
        """Submit an order.

        Place an order on loopring's market exchange.

        Note:
            Loopring doesn't support market price orders.
            
            See :meth:`~loopring.client.Client.get_next_storage_id()` for more
            information on storage IDs.

        Examples:
            The method for placing a buy order for 100 LRC @ 0.01 ETH/LRC is as
            follows;

            - Find the number of decimal places (``decimals``) to which a token can \
                be expressed in their smallest unit.
            - Multiply the quantity of tokens by 10 raised to the power of \
                ``decimals`` to get the floating point value.
            - Pass this into a dictionary, with the token's ID, next available \
                storage ID, and send it along in a request to the order submission \
                endpoint.

            That can be a bit of a headache, so that's what this code is doing
            behind the scenes:

            .. code-block:: python3


                # from loopring.util.helpers import fetch
                lrc_cfg = fetch(client.tokens, symbol="LRC")
                eth_cfg = fetch(client.tokens, symbol="ETH")

                # from loopring import Token
                LRC = Token.from_quantity(100, lrc_cfg)
                ETH = Token.from_quantity(1, eth_cfg)

                await client.get_next_storage_id(token=LRC)
                await client.get_next_storage_id(token=ETH)

                await client.submit_order("buy", token=LRC, using=ETH, ...)

        Args:
            affiliate: An account ID to receive a share of the order's fee.
            client_order_id: An arbitrary, unique client-side order ID.
            in_return_for: If selling, this is the token that you'll be receiving \
                in return for your ``target`` token (i.e. the token you're buying).
            max_fee_bips: Maximum order fee that the user can accept, \
                value range (in ten thousandths) 1 ~ 63.
            order_type: The type of order: `'LIMIT_ORDER'`, `'AMM'`, \
                `'MAKER_ONLY'`, `'TAKER_ONLY'`.
            pool_address: The AMM Pool address if order type is `'AMM'`.
            side: Determine whether to submit a '`BUY`' order or a '`SELL`' \
                order.
            taker: Used by the P2P order, where the user needs to \
                specify the taker's address.
            trade_channel: The channel to be used when ordering: \
                `'ORDER_BOOK'`, `'AMM_POOL'`, `'MIXED'`.
            using: If buying, this is the token you'll be giving in exchange \
                for the one you wish to buy.
            valid_until: The order expiry \
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

        side = side.lower()

        assert side in ["buy", "sell"]
        assert not (in_return_for and using)  # Mutually exclusive

        # Not happy with these conditionals, but I'll come
        # back to it another day
        if side == "sell" and in_return_for is None:
            examples = "https://diggydev.co.uk/loopring/apireference.html#loopring.client.Client.submit_order"
            raise InvalidArguments(
                f"Missing 'in_return_for' argument. Refer to " +
                f"the API Reference examples if you need help - {examples}"
            )

        elif side == "buy" and using is None:
            examples = "https://diggydev.co.uk/loopring/apireference.html#loopring.client.Client.submit_order"
            raise InvalidArguments(
                f"Missing 'using' argument. Refer to " +
                f"the API Reference examples if you need help - {examples}"
            )

        if not valid_until:
            # Default to 2 months:
            # See 'https://docs.loopring.io/en/basics/orders.html#timestamps'
            # for information about order validity and time
            valid_until = int(time.time()) + 60 * 60 * 24 * 60
        valid_since = int(datetime.timestamp(datetime.now()))

        side = True if side == "buy" else False

        sell_token = in_return_for or target
        buy_token = using or target

        order_id = self.storage_ids[sell_token.id]["orderId"]
        assert order_id < IntSig.MAX_ORDER_ID

        self.storage_ids[sell_token.id]["orderId"] += 2

        url = self.endpoint + PATH.ORDER

        payload = clean_params({
            "accountId": self.account_id,
            "affiliate": affiliate,

            # 'allOrNone' currently doesn't accept anything
            # other than 'False' - this will be editable
            # once the API starts accepting other values
            "allOrNone": False,

            "buyToken": buy_token.to_params(),
            "clientOrderId": client_order_id,
            "exchange": str(self.exchange),
            "fillAmountBOrS": side,
            "maxFeeBips": max_fee_bips,
            "orderType": order_type,
            "poolAddress": pool_address,
            "sellToken": sell_token.to_params(),
            "storageId": order_id,
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

    async def update_account_eddsa_key(self,
        *,
        account_id: int=None,
        ecdsa_key: str,
        exchange: Union[str, Exchange]=None,
        max_fee: Token,
        owner: str=None,
        valid_until: Union[int, datetime]=None) -> ...:
        """Update the EdDSA key associated with an account."""

        url = self.endpoint + PATH.ACCOUNT

        if not valid_until:
            ts = int(time.time()) + 60 * 60 * 24 * 60
            valid_until = datetime.fromtimestamp(ts)

        payload = {
            "accountId": account_id or self.account_id,
            "exchange": exchange or str(self.exchange),
            "maxFee": max_fee.to_params(),
            "nonce": self.nonce,
            "owner": owner or self.address,
            "publicKey": {
                "x": self.publicX,
                "y": self.publicY
            },
            "validUntil": validate_timestamp(valid_until, "seconds", validate_future=True)
        }

        request = Request(
            "post",
            self.endpoint,
            PATH.ACCOUNT,
            payload=payload
        )

        message = generate_update_account_EIP712_hash(request.payload)

        ecdsa_key = int(ecdsa_key, 16).to_bytes(32, byteorder="big")

        v, r, s = ecsign(message, ecdsa_key)
        headers = {
            "X-API-SIG": "0x" + bytes.hex(v_r_s_to_signature(v, r, s)) + "03"
        }

        helper = UpdateAccountEDDSASign(private_key=self.private_key)
        eddsa_signature = helper.sign(payload)

        payload["eddsaSignature"] = eddsa_signature

        async with self._session.post(url, headers=headers, json=payload) as r:
            raw_content = await r.read()

            content: dict = json.loads(raw_content.decode())

            if self.handle_errors:
                raise_errors_in(content)
            
            return content
