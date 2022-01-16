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
