from typing import List, Union

from .token import Token
from .util.helpers import auto_repr, to_snake_case


class PoolPrecisions:
    """An PoolPrecisions model."""

    amount: int
    price: int  # price precision (aka. dp)

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class PoolTokens:
    """An PoolTokens model."""

    lp: Union[int, Token]
    pooled: List[Union[int, Token]]  # Sequence matters!

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    @classmethod
    def from_tokens(cls, *, t1: Token, t2: Token, minimum_lp: Token):
        """Used to help define AMM pool join parameters.
        
        Warning:
            Order matters here. You'll be joining the AMM Pool like so; \
                `AMM-t1-t2`
        
        Examples:
            >>> eth = Token(id=0, volume=1000000000)

        """
        return cls(**{"lp": minimum_lp, "pooled": [t1, t2]})

    def to_params(self):
        params = {}

        params["minimumLp"] = self.__dict__["lp"].to_params()
        params["pooled"] = [t.to_params() for t in self.__dict__["pooled"]]

        return params


class Pool:
    """A Pool model."""

    address: str
    fee_bips: int
    market: str
    name: str
    precisions: PoolPrecisions
    token: PoolTokens
    version: str

    def __init__(self, **data):
        for k in data.keys():
            if k == "precisions":
                setattr(self, to_snake_case(k), PoolPrecisions(**data[k]))
            elif k == "token":
                setattr(self, to_snake_case(k), PoolTokens(**data[k]))
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

