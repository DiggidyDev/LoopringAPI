from datetime import datetime

from .util import auto_repr, to_snake_case


class Market:

    base_token_id: int
    enabled: bool
    market: str
    orderbook_agg_levels: int
    precision_for_price: int
    quote_token_id: int

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        return self.market


# Not sure if this is the right file for this
# class, but I'll leave it here for now :p
class Ticker:

    base_token_volume: int
    closing_price: str
    highest_bid: str
    highest_price: str
    lowest_ask: str
    lowest_price: str
    market: str
    number_of_trades: int
    opening_price: str
    quote_token_volume: int
    timestamp: datetime

    # These two are only for AMM
    base_fee_amount: str
    quote_fee_amount: str

    # God this init looks horrible...
    # Need to find a better way to do it logically
    def __init__(self,
        market,
        timestamp,
        base_token_volume,
        quote_token_volume,
        opening_price,
        highest_price,
        lowest_price,
        closing_price,
        number_of_trades,
        highest_bid,
        lowest_ask,
        base_fee_amount=None,
        quote_fee_amount=None):
        self.market             = market or "N/A"
        self.timestamp          = datetime.fromtimestamp(int(timestamp) / 1000) or "N/A"
        self.base_token_volume  = int(base_token_volume) or "N/A"
        self.quote_token_volume = int(quote_token_volume) or "N/A"
        self.opening_price      = opening_price or "N/A"
        self.highest_price      = highest_price or "N/A"
        self.lowest_price       = lowest_price or "N/A"
        self.closing_price      = closing_price or "N/A"
        self.number_of_trades   = int(number_of_trades) or "N/A"
        self.highest_bid        = highest_bid or "N/A"
        self.lowest_ask         = lowest_ask or "N/A"

        # The "N/A" should only happen for these two, but I
        # added it as a precaution for the other attrs too
        self.base_fee_amount    = base_fee_amount or "N/A"
        self.quote_fee_amount   = quote_fee_amount or "N/A"
    
    def __repr__(self) -> str:
        amm_fees = ""
        if self.base_fee_amount:
            amm_fees = f" base_fee_amount='{self.base_fee_amount}'" + \
                       f" quote_fee_amount='{self.quote_fee_amount}"

        return f"<market='{self.market}' highest_price='{self.highest_price}' " + \
            f"lowest_price='{self.lowest_price}' highest_bid='{self.highest_bid}' " + \
            f"lowest_ask='{self.lowest_ask}' closing_price='{self.closing_price}' " + \
            f"opening_price='{self.opening_price}' timestamp='{self.timestamp}' " + \
            f"base_token_volume={self.base_token_volume} " + \
            f"quote_token_volume={self.quote_token_volume}{amm_fees}>"
    
    def __str__(self) -> str:
        return f"({self.market}) High: {self.highest_price}, Low: {self.lowest_price}"


class Trade:

    action: str  # Rename to `direction`?
    block_id: int
    block_num: int
    fees: str
    market: str
    price: str
    record_id: str
    trade_time: datetime
    volume: int

    def __init__(self,
        trade_time,
        record_id,
        action,
        volume,
        price,
        market,
        fees,
        block_id=None,
        block_num=None):
        self.action = action
        self.block_id = int(block_id)
        self.block_num = int(block_num)
        self.fees = fees
        self.market = market
        self.price = price
        self.record_id = record_id
        self.trade_time = datetime.fromtimestamp(int(trade_time) / 1000)
        self.volume = int(volume)

    def __repr__(self) -> str:
        if self.block_id is not None:
            block_info = f" block_id={self.block_id} block_num={self.block_num}"
        return f"<action='{self.action.title()}' market='{self.market}' " + \
            f"price='{self.price}' trade_time={self.trade_time} " + \
            f"volume='{self.volume}' record_id='{self.record_id}' " + \
            f"fees='{self.fees}'{block_info}>"
    
    def __str__(self) -> str:
        # Add volume
        return f"{self.action.title()} {self.market} @ {self.price}"  


class Candlestick:

    """A candlestick model class.
    
    Attributes:
        base_transaction_volume (int): ...
        closing_price (str): ...
        highest_price (str): ...
        lowest_price (str): ...
        number_of_transactions (int): ...
        opening_price (str): ...
        quote_transaction_volume (int): ...
        start_time (:class:`~datetime.datetime`): ...

    """

    base_transaction_volume: int
    closing_price: str
    highest_price: str
    lowest_price: str
    number_of_transactions: int
    opening_price: str
    quote_transaction_volume: int
    start_time: datetime

    def __init__(self,
    start_time,
    number_of_transactions,
    opening_price,
    closing_price,
    highest_price,
    lowest_price,
    base_transaction_volume,
    quote_transaction_volume):
        self.base_transaction_volume = int(base_transaction_volume)
        self.closing_price = closing_price
        self.highest_price = highest_price
        self.lowest_price = lowest_price
        self.number_of_transactions = int(number_of_transactions)
        self.opening_price = opening_price
        self.quote_transaction_volume = int(quote_transaction_volume)
        self.start_time = datetime.fromtimestamp(int(start_time) / 1000)
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        return f"High: {self.highest_price} Low: {self.lowest_price} " + \
            f"Open: {self.opening_price} Close: {self.closing_price}"
