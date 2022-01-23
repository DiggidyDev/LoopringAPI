from datetime import datetime
from typing import Any

from .util.helpers import auto_repr, to_snake_case
from .util.mappings import Mappings


class Fee:
    """A fee model for a query."""

    discount: float
    fee: int
    token: str

    def __init__(self, **data) -> None:
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __int__(self) -> int:
        return self.fee
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        return f"{self.fee}"


class Rate:
    """A rate model for a query."""

    gas_price: int
    maker_rate: int
    symbol: str
    taker_rate: int

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)

    def __str__(self) -> str:
        return f"{self.gas_price}"


class GasAmount:
    """Contains information about the gas amounts required by ETH L1 requests.

    Args:
        deposit (str): The gas amount for deposit.
        distribution (str): The gas amount for distribution.
    
    """

    deposit: str
    distribution: str

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class OrderAmount:
    """Contains information about the order amounts that are valid for usage \
        with the token in order-related APIs.
    
    Args:
        dust (str): The dust amount enforced when submitting orders for the token.
        maximum (str): The max amount enforced when submitting orders for the token.
        minimum (str): The min amount enforced when submitting orders for the token.
    
    """

    dust: str
    maximum: str
    minimum: str

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class OrderInfo:
    """An OrderInfo model."""

    maker_rate: int
    min_amount: str
    taker_rate: int

    def __init__(self,  **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class RateInfo:
    """A RateInfo model."""

    base_order_info: OrderInfo
    discount: float
    market_order_info: OrderAmount
    token_symbol: str
    user_order_info: OrderInfo

    def __init__(self, **data):
        for k in data.keys():
            if "market" in k:
                setattr(self, to_snake_case(k), OrderAmount(**data[k]))
            elif "Order" in k:
                setattr(self, to_snake_case(k), OrderInfo(**data[k]))
            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class Price:
    """A Price model.

    Note:
        You may want to refer to the :attr:`~loopring.token.Price.updated_at` \
        attribute, as the price may be delayed and not reflect the current live \
        price.
    
    Attributes:
        currency (str): ... .
        price (str): ... .
        symbol (str): ... .
        updated_at (:class:`~datetime.datetime`): ... .

    """

    currency: str
    price: str
    symbol: str
    updated_at: datetime

    def __init__(self, *, currency: str, **data):
        self.currency = currency
        for k in data.keys():
            if k == "updatedAt":

                # For some reason I don't need to do `data[k] / 1000`
                # like I've had to do in other places...
                # Bit annoying that there isn't a standard format of
                # timestamps :p
                self.updated_at = datetime.fromtimestamp(data[k])
                continue

            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        currency_map = Mappings.CURRENCY_MAPPINGS
        return f"1 {self.symbol} = {currency_map[self.currency.upper()]}" + \
            f"{self.price}"


class TokenConfig:
    """Token configuration model class.
    
    Attributes:
        address (str): ...
        decimals (int): ...
        enabled (bool): ...
        fast_withdraw_limit (str): ...
        gas_amounts (:obj:`~loopring.token.GasAmount`): ...
        lucky_token_amounts (:obj:`~loopring.token.OrderAmount`): ...
        name (str): ...
        order_amounts (:obj:`~loopring.token.OrderAmount`): ...
        precision (int): ...
        precision_for_order (int): ...
        symbol (str): ...
        token_id (int): ...
        type (str): ...

    """

    address: str
    decimals: int
    enabled: bool
    fast_withdraw_limit: str
    gas_amounts: GasAmount
    lucky_token_amounts: OrderAmount
    name: str
    order_amounts: OrderAmount
    precision: int
    precision_for_order: int
    symbol: str
    token_id: int
    type: str

    def __init__(self, **data):
        for k in data.keys():

            if k == "gasAmounts":
                setattr(self, to_snake_case(k), GasAmount(**data[k]))

            elif k in ("luckyTokenAmounts", "orderAmounts"):
                setattr(self, to_snake_case(k), OrderAmount(**data[k]))

            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __int__(self) -> int:
        return self.token_id
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        return f"{self.name} ({self.symbol})"


class Token:
    """Token class.
    
    Args:
        id (int): ...
        volume (str): ...

    """

    id: int
    volume: str

    def __getitem__(self, __name) -> Any:
        return self.__dict__[__name]

    def __init__(self, *, id: int=None, volume: str=None):
        self.id = id
        self.volume = volume
    
    def __int__(self) -> int:
        return self.id
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    @classmethod
    def from_quantity(cls, quantity: float, cfg: TokenConfig) -> "Token":

        # Bug squashed by BanthaFupa: https://github.com/blainecostello
        vol = int(quantity * 10 ** cfg.decimals)
        
        return cls(id=cfg.token_id, volume=vol)

    def to_params(self):
        """Converting any attributes back to the fields required for requests."""

        return {"tokenId": self.__dict__["id"], "volume": self.__dict__["volume"]}

