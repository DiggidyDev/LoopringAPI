from typing import List

from .token import Token
from .util.helpers import auto_repr, to_snake_case


class AMMPoolPrecisions:
    """An AMMPoolPrecisions model."""

    amount: int
    price: int  # price *precision*

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class AMMPoolTokens:
    """An AMMPoolTokens model."""

    lp: int
    pooled: List[int]  # Sequence matters!

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class Pool:
    """A Pool model."""

    address: str
    fee_bips: int
    market: str
    name: str
    precisions: AMMPoolPrecisions
    token: AMMPoolTokens
    version: str

    def __init__(self, **data):
        for k in data.keys():
            if k == "precisions":
                setattr(self, to_snake_case(k), AMMPoolPrecisions(**data[k]))
            elif k == "token":
                setattr(self, to_snake_case(k), AMMPoolTokens(**data[k]))
            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class PoolSnapshot:
    """A PoolSnapshot model."""

    lp: Token
    pool_address: str
    pool_name: str
    pooled: List[Token]
    risky: 100

    def __init__(self, **data):
        for k in data.keys():
            if k == "lp":
                data[k]["id"] = data[k].pop("tokenId")
                setattr(self, to_snake_case(k), Token(**data[k]))
            elif k == "pooled":
                tokens = []

                for t in data[k]:
                    t["id"] = t.pop("tokenId")
                    tokens.append(Token(**t))
                
                setattr(self, to_snake_case(k), tokens)
            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)
