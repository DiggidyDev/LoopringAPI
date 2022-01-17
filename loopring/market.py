from .util.helpers import to_snake_case


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
        return f"<market='{self.market}' enabled={self.enabled} " + \
            f"base_token_id={self.base_token_id} " + \
            f"quote_token_id={self.quote_token_id} " + \
            f"orderbook_agg_levels={self.orderbook_agg_levels}" + \
            f"precision_for_price={self.precision_for_price}>"
    
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
    timestamp: int

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
        self.timestamp          = timestamp or "N/A"
        self.base_token_volume  = base_token_volume or "N/A"
        self.quote_token_volume = quote_token_volume or "N/A"
        self.opening_price      = opening_price or "N/A"
        self.highest_price      = highest_price or "N/A"
        self.lowest_price       = lowest_price or "N/A"
        self.closing_price      = closing_price or "N/A"
        self.number_of_trades   = number_of_trades or "N/A"
        self.highest_bid        = highest_bid or "N/A"
        self.lowest_ask         = lowest_ask or "N/A"
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
            f"opening_price='{self.opening_price}' timestamp={self.timestamp} " + \
            f"base_token_volume={self.base_token_volume} " + \
            f"quote_token_volume={self.quote_token_volume}{amm_fees}>"
    
    def __str__(self) -> str:
        return f"({self.market}) High: {self.highest_price}, Low: {self.lowest_price}"


class Candlestick:

    base_transaction_volume: str
    closing_price: str
    highest_price: str
    lowest_price: str
    number_of_transactions: int
    opening_price: str
    quote_transaction_volume: str
    start_time: int

    def __init__(self,
    start_time,
    number_of_transactions,
    opening_price,
    closing_price,
    highest_price,
    lowest_price,
    base_transaction_volume,
    quote_transaction_volume):
        self.base_transaction_volume = base_transaction_volume
        self.closing_price = closing_price
        self.highest_price = highest_price
        self.lowest_price = lowest_price
        self.number_of_transactions = number_of_transactions
        self.opening_price = opening_price
        self.quote_transaction_volume = quote_transaction_volume
        self.start_time = start_time
    
    def __repr__(self) -> str:
        # Not all attrs added - maybe add them all?
        return f"<lowest_price='{self.lowest_price}' " + \
            f"highest_price='{self.highest_price}' " + \
            f"opening_price='{self.opening_price}' " + \
            f"closing_price='{self.closing_price}' " + \
            f"start_time={self.start_time}>"
    
    def __str__(self) -> str:
        return f"High: {self.highest_price} Low: {self.lowest_price} " + \
            f"Open: {self.opening_price} Close: {self.closing_price}"
