from loopring.errors import *

from .enums import ErrorCodes as ERR


class Mappings:

    """A class containing some useful dictionaries.
    
    These shouldn't be any real reason to be using this, unless
    you've disabled :obj:`~loopring.client.Client.handle_errors` \ 
    and know what you're doing.

    """

    CURRENCY_MAPPINGS = {
        "CNY": "¥",
        "EUR": "€",
        "GBP": "£",
        "HKD": "HK$",
        "JPY": "¥",
        "USD": "$"
    }

    ERROR_MAPPINGS = {
        ERR.ADDRESS_NOT_FOUND: AddressNotFound,

        ERR.EMPTY_API_KEY: EmptyAPIKey,
        ERR.EMPTY_ORDERHASH: EmptyOrderhash,
        ERR.EMPTY_SIG: EmptySignature,
        ERR.EMPTY_USER: EmptyUser,

        ERR.FAILED_TO_FREEZE_AMOUNT: FailedToFreeze,
        ERR.FAILED_TO_SUBMIT_ORDER: FailedToSubmit,

        ERR.INCONSISTENT_TRANSFER_TOKEN_FEE_TOKEN: InconsistentTokens,
        ERR.INVALID_ACCOUNT_ID: InvalidAccountID,
        ERR.INVALID_API_KEY: InvalidAPIKey,
        ERR.INVALID_ARGUMENTS: InvalidArguments,
        ERR.INVALID_EXCHANGE_ID: InvalidExchangeID,
        ERR.INVALID_NONCE: InvalidNonce,
        ERR.INVALID_ORDER: InvalidOrder,
        ERR.INVALID_ORDER_ID: InvalidOrderID,
        ERR.INVALID_QUERY_STRING: InvalidQueryString,
        ERR.INVALID_RATE: InvalidRate,
        ERR.INVALID_SIG: InvalidSignature,
        ERR.INVALID_TRANSFER_RECEIVER: InvalidTransferReceiver,
        ERR.INVALID_TRANSFER_SENDER: InvalidTransferSender,
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
        ERR.ORDERBOOK_UNSUPPORTED_MARKET: OrderbookUnsupportedMarket,

        ERR.UNKNOWN_ERROR: UnknownError,
        ERR.UNSUPPORTED_DEPTH_LEVEL: UnsupportedDepthLevel,
        ERR.UNSUPPORTED_FEE_TOKEN: UnsupportedFeeToken,
        ERR.UNSUPPORTED_TOKEN_ID: UnsupportedTokenID,
        ERR.USER_NOT_FOUND: UserNotFound
    }
    """dict[:class:`~loopring.util.enums.ErrorCodes`, \ 
    :exc:`~loopring.errors.LoopringError`]"""
