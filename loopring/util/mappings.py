from loopring.errors import *

from .enums import ErrorCodes as ERR


class Mappings:

    """A class containing some useful dictionaries.
    
    These shouldn't be any real reason to be using this, unless
    you've disabled :obj:`~loopring.client.Client.handle_errors` \ 
    and know what you're doing.

    """

    ERROR_MAPPINGS = {
        ERR.EMPTY_API_KEY: EmptyAPIKey,
        ERR.EMPTY_ORDERHASH: EmptyOrderhash,
        ERR.EMPTY_SIG: EmptySignature,
        ERR.EMPTY_USER: EmptyUser,

        ERR.FAILED_TO_FREEZE_AMOUNT: FailedToFreeze,
        ERR.FAILED_TO_SUBMIT_ORDER: FailedToSubmit,

        ERR.INVALID_ACCOUNT_ID: InvalidAccountID,
        ERR.INVALID_API_KEY: InvalidAPIKey,
        ERR.INVALID_ARGUMENTS: InvalidArguments,
        ERR.INVALID_EXCHANGE_ID: InvalidExchangeID,
        ERR.INVALID_NONCE: InvalidNonce,
        ERR.INVALID_ORDER: InvalidOrder,
        ERR.INVALID_ORDER_ID: InvalidOrderID,
        ERR.INVALID_RATE: InvalidRate,
        ERR.INVALID_SIG: InvalidSignature,
        ERR.INVALID_USER_BALANCE: InvalidUserBalance,

        ERR.NO_ORDER_TO_CANCEL: NoOrderToCancel,
        ERR.NON_EXISTENT_ORDER: OrderNotFound,
        ERR.ORDER_ALREADY_EXISTS: OrderAlreadyExists,
        ERR.ORDER_ALREADY_EXPIRED: OrderAlreadyExpired,
        ERR.ORDER_AMOUNT_EXCEEDED: OrderAmountExceeded,
        ERR.ORDER_AMOUNT_TOO_SMALL: OrderAmountTooSmall,
        ERR.ORDER_CANCEL_FAILURE: OrderCancellationFailed,
        ERR.ORDER_INVALID_ACCOUNT_ID: OrderInvalidAccountID,
        ERR.ORDER_MISSING_SIG: OrderMissingSignature,
        ERR.ORDER_UNSUPPORTED_MARKET: OrderUnsupportedMarket,

        ERR.UNKNOWN_ERROR: UnknownError,
        ERR.UNSUPPORTED_TOKEN_ID: UnsupportedTokenID,
        ERR.USER_NOT_FOUND: UserNotFound
    }
    """dict[:class:`~loopring.util.enums.ErrorCodes`, \ 
    :exc:`~loopring.errors.LoopringError`]"""

    ORDER_ATTR_MAPPINGS = {
        "clientOrderId": "client_order_id",
        "isIdempotent": "is_idempotent",
        "orderType": "order_type",
        "tradeChannel": "trade_channel"
    }

    VOLUME_ATTR_MAPPINGS = {
        "baseAmount": "base_amount",
        "baseFilled": "base_filled",
        "quoteAmount": "quote_amount",
        "quoteFilled": "quote_filled"
    }