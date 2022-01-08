from typing import Any, Union
from loopring.util.mappings import Mappings



class Validity:
    """A class representative of an order's validity.
    
    Attributes:
        end (int): ...
        start (int): ...
    
    """
    
    end: int
    start: int

    def __init__(self, **data) -> None:
        for k in data:
            setattr(self, k, data[k])
    
    def __repr__(self) -> None:
        return f"<end={self.end} start={self.start}>"


class Volume:
    """A class wrapping data regarding an order's volume.
    
    Attributes:
        base_amount (str): ...
        base_filled (str): ...
        fee (str): ...
        quote_amount (str): ...
        quote_filled (str): ...
    
    """
    
    base_amount: str
    base_filled: str
    fee: str
    quote_amount: str
    quote_filled: str

    def __init__(self, **data) -> None:
        for k in data:
            if not k.islower():
                setattr(self, Mappings.VOLUME_ATTR_MAPPINGS[k], data[k])
                continue

            setattr(self, k, data[k])
    
    def __repr__(self) -> str:
        return f"<base_amount='{self.base_amount}' " + \
            f"base_filled='{self.base_filled}' fee='{self.fee}' " + \
            f"quote_amount='{self.quote_amount}' quote_filled='{self.quote_filled}'>"


class PartialOrder:
    """A partial order object, usually returned when making a new order.
    
    Attributes:
        client_order_id (str): ...
        hash (str): ...
        is_idempotent (bool): ...
        status (str): ...
    
    """

    client_order_id: str
    hash: str
    is_idempotent: bool
    status: str

    def __init__(self, **data):
        self.__json = data

        if self._is_error(data):
            return

        for k in data.keys():
            if not k.islower():
                setattr(self, Mappings.ORDER_ATTR_MAPPINGS[k], data[k])
            
            else:
                setattr(self, k, data[k])
    
    def __repr__(self) -> str:
        if self._is_error():
            return "<Incomplete PartialOrder>"

        return f"<hash='{self.hash}' id='{self.client_order_id}' " + \
            f"is_idempotent={self.is_idempotent} status='{self.status}'>"
    
    def __str__(self) -> str:
        if self._is_error():
            return f"Incomplete {self.__class__.__name__}."
        
        return self.hash
    
    def _is_error(self, init: dict=None) -> bool:
        # On an unsuccessful response, the only data in
        # the dictionary would be "resultInfo" along
        # with an error code.
        if not init:
            return not hasattr(self, "hash")
        
        return len(self.__json) < 2

    @property
    def json(self) -> dict[str, Union[str, dict[str, Union[str, int]]]]:
        """Returns the original data from which the object was initialised.

        Disabling :obj:`~loopring.client.Client.handle_errors` will prevent
        exceptions from being raised. On a successful response, you will
        still have an :obj:`~loopring.order.PartialOrder` or
        :obj:`~loopring.order.Order` object returned, but in the event that
        an exception occurs, you'll receive a :py:class:`dict` containing
        the raw error response data.
        
        .. seealso:: :class:`~loopring.util.mappings.Mappings.ERROR_MAPPINGS`
            in case you have disabled :obj:`~loopring.client.Client.handle_errors`
            and wish to handle the raw error JSON response yourself.

        """
        return self.__json


class Order(PartialOrder):
    """You shouldn't need to directly instantiate an :obj:`Order` object.

    This class inherits from :obj:`~loopring.order.PartialOrder`.

    Attributes:
        client_order_id (str): The client-side ID of the order.
        hash (str): The order's hash.
        market (str): The trading pair associated with the order.
        order_type (str): Whether the order was a limit, maker, or taker.
        price (str): The price at which the order was executed.
        side (str): Indicator of a sell or buy.
        status (str): The order's current state (`cancelled`, `cancelling`, \
            `expired`, `processed`, `processing`, `waiting`)
        trade_channel (str): The order's channel origin (`order_book`, \
            `amm_pool`, `mixed`)
        validity (:obj:`Validity`): ...
        volumes (:class:`Volume`): ...

    """

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

    def __getattribute__(self, __name: str) -> Any:
        if __name in ("is_idempotent",):
            raise AttributeError(f"type object 'Order' has no attribute '{__name}'")
        return super().__getattribute__(__name)

    def __init__(self, **data) -> None:
        super().__init__(**data)

        if self._is_error(data):
            return

        for k in data:
            if not k.islower():
                setattr(self, Mappings.ORDER_ATTR_MAPPINGS[k], data[k])
            
            elif k == "validity":
                setattr(self, k, Validity(**data[k]))
            
            elif k == "volumes":
                setattr(self, k, Volume(**data[k]))
            
            else:
                setattr(self, k, data[k])
    
    def __repr__(self) -> str:
        if self._is_error():
            return f"<Incomplete Order>"

        return f"<hash='{self.hash}' id='{self.client_order_id}' " + \
            f"side='{self.side}' market='{self.market}' price='{self.price}' " + \
            f"order_type='{self.order_type}' trade_channel='{self.trade_channel}' " + \
            f"status='{self.status}' validity={self.validity} volumes={self.volumes}>"
