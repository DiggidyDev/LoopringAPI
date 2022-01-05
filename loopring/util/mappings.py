from loopring.errors import *

from .enums import ErrorCodes as ERR


ERROR_MAPPINGS = {
    ERR.EMPTY_API_KEY: EmptyAPIKey,
    ERR.EMPTY_ORDERHASH: EmptyOrderhash,
    ERR.EMPTY_USER: EmptyUser,
    ERR.INVALID_ACCOUNT_ID: InvalidAccountID,
    ERR.INVALID_API_KEY: InvalidAPIKey,
    ERR.INVALID_ARGUMENTS: InvalidArguments,
    ERR.NON_EXISTENT_ORDER: OrderNotFound,
    ERR.UNKNOWN_ERROR: UnknownError,
    ERR.USER_NOT_FOUND: UserNotFound
}

ORDER_ATTR_MAPPINGS = {
    "clientOrderId": "client_order_id",
    "orderType": "order_type",
    "tradeChannel": "trade_channel"
}

VOLUME_ATTR_MAPPINGS = {
    "baseAmount": "base_amount",
    "baseFilled": "base_filled",
    "quoteAmount": "quote_amount",
    "quoteFilled": "quote_filled"
}