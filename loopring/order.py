from loopring.util.mappings import ORDER_ATTR_MAPPINGS, VOLUME_ATTR_MAPPINGS



class Validity:
    
    end: int
    start: int

    def __init__(self, **data) -> None:
        for k in data:
            setattr(self, k, data[k])
    
    def __repr__(self) -> None:
        return f"<end={self.end} start={self.start}>"


class Volume:
    
    base_amount: str
    base_filled: str
    fee: str
    quote_amount: str
    quote_filled: str

    def __init__(self, **data) -> None:
        for k in data:
            if not k.islower():
                setattr(self, VOLUME_ATTR_MAPPINGS[k], data[k])
                continue

            setattr(self, k, data[k])
    
    def __repr__(self) -> str:
        return f"<base_amount='{self.base_amount}' " + \
            f"base_filled='{self.base_filled}' fee='{self.fee}' " + \
            f"quote_amount='{self.quote_amount}' quote_filled='{self.quote_filled}'>"



class Order:
    """Shouldn't need to call directly."""

    client_order_id: str
    hash: str
    market: str
    order_type: str
    price: str
    side: str
    status: str
    trade_channel: str
    validity: Validity
    volumes: Volume

    def __init__(self, **data) -> None:
        for k in data:
            if not k.islower():
                setattr(self, ORDER_ATTR_MAPPINGS[k], data[k])
            
            elif k == "validity":
                setattr(self, k, Validity(**data[k]))
            
            elif k == "volumes":
                setattr(self, k, Volume(**data[k]))
            
            else:
                setattr(self, k, data[k])
    
    def __repr__(self) -> str:
        return f"<hash='{self.hash}' id='{self.client_order_id}' " + \
            f"side='{self.side}' market='{self.market}' price='{self.price}' " + \
            f"order_type='{self.order_type}' trade_channel='{self.trade_channel}' " + \
            f"status='{self.status}' validity={self.validity} volumes={self.volumes}>"
    
    def __str__(self) -> str:
        return self.hash
