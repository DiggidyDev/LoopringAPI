from typing import Any

from loopring.util.helpers import to_snake_case


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
        return f"<deposit='{self.deposit}' distribution='{self.distribution}'>"


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
        return f"<dust='{self.dust}' maximum='{self.maximum}' " + \
            f"minimum='{self.minimum}'>"


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


class TokenConfig:
    """
    
    Args:
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

            if k == "gasAmount":
                setattr(self, to_snake_case(k), GasAmount(**data[k]))

            elif k in ("luckyTokenAmounts", "orderAmounts"):
                setattr(self, to_snake_case(k), OrderAmount(**data[k]))

            else:
                setattr(self, to_snake_case(k), data[k])
            
    def __repr__(self) -> str:
        return f"<symbol='{self.symbol}' name='{self.name}' " + \
            f"token_id={self.token_id} type='{self.type}' " + \
            f"address='{self.address}' enabled={self.enabled}" + \
            f"decimals={self.decimals} precision={self.precision} " + \
            f"precision_for_order={self.precision_for_order} " + \
            f"fast_withdraw_limit='{self.fast_withdraw_limit}' " + \
            f"lucky_token_amounts={repr(self.lucky_token_amounts)} " + \
            f"order_amounts={repr(self.order_amounts)}" + \
            f"gas_amounts={repr(self.gas_amounts)}>"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.symbol})"

