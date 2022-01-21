from datetime import datetime
from re import S
from typing import List, Union

from .token import Token
from .util.helpers import auto_repr, to_snake_case


class AMMTrade:
    """An AMMTrade model."""

    account_id: int
    created_at: datetime
    fee_amount: str
    market: str
    order_hash: str
    price: str  # float
    side: str
    size: str

    def __init__(self, **data):
        for k in data.keys():
            if "At" in k:
                dt = datetime.fromtimestamp(data[k] // 1000)
                setattr(self, to_snake_case(k), dt)
            else:
                setattr(self,  to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class AMMToken:
    """An AMMToken model."""

    actual_amount: str
    amount: str
    fee_amount: str
    token_id: int

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
        
    def __repr__(self) -> str:
        return auto_repr(self)


class AMMTransaction:
    """An AMMTransaction model."""

    amm_layer_type: str
    amm_pool_address: str
    block_id: int
    created_at: datetime
    hash: str
    index_in_block: int
    lp_tokens: List[AMMToken]
    pool_tokens: List[AMMToken]
    tx_status: str
    tx_type: str
    updated_at: datetime

    def __init__(self, **data):
        for k in data.keys():
            if "At" in k:
                dt = datetime.fromtimestamp(data[k] // 1000)
                setattr(self, to_snake_case(k), dt)
            elif "Tokens" in k:
                tokens = []

                for t in data[k]:
                    tokens.append(AMMToken(**t))

                setattr(self, to_snake_case(k), tokens)
            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class PoolPrecisions:
    """An PoolPrecisions model."""

    amount: int
    price: int  # price precision (aka. dp)

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class ExitPoolTokens:
    """An ExitPoolTokens model."""

    burned: Token
    unpooled: List[Token]

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    @classmethod
    def from_tokens(cls, t1: Token, t2: Token, burned: Token):
        """Describe the tokens to be removed from an AMM Pool. Order matters!"""
        return cls(**{"burned": burned, "unpooled": [t1, t2]})

    def to_params(self):
        params = {}

        params["burned"] = self.__dict__["burned"].to_params()
        params["unPooled"] = [t.to_params() for t in self.__dict__["unpooled"]]

        return params


class JoinPoolTokens:
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
    token: JoinPoolTokens
    version: str

    def __init__(self, **data):
        for k in data.keys():
            if k == "precisions":
                setattr(self, to_snake_case(k), PoolPrecisions(**data[k]))
            elif k == "token":
                setattr(self, to_snake_case(k), JoinPoolTokens(**data[k]))
            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        return self.address


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
    
    def __str__(self) -> str:
        return self.pool_address

