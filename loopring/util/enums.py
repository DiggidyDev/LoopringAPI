from enum import Enum, IntEnum


# TODO: Add unit tests


class Endpoints(str, Enum):
    MAINNET = "https://api3.loopring.io"

    TESTNET_2 = "https://uat2.loopring.io"
    TESTNET_3 = "https://uat3.loopring.io"


class ErrorCodes(IntEnum):
    """An Enumeration class containing all possible error codes returned from the API.

    All error codes found in the official GitHub repository and documentation
    are listed here.  Some have yet to be listed in the documentation, but were
    found in the repository, and vice versa - these have been denoted by a
    preceding `IMPL_` or `DEPR_`.

    Note:
        Two sets of 'duplicates' were found in the documentation,
        returning the same error fundamentally, but via different
        approaches.

    Examples:
        Letting `resp` be a returned response from the API;
        
        >>> resp = { "code": 100001, "msg": "Invalid parameter." }
        >>> resp["code"] == ErrorCodes.INVALID_ARGUMENTS
        True
    """

    # General errors
    INVALID_ARGUMENTS = 100001
    UNKNOWN_ERROR = 100000

    # User querying
    ADDRESS_NOT_FOUND = 101001
    USER_NOT_FOUND = 101002

    # Orders
    FAILED_TO_FREEZE_AMOUNT = 102014
    FAILED_TO_SUBMIT_ORDER = 102027
    INVALID_ORDER = 102120
    INVALID_ORDER_ID = 102004
    INVALID_RATE = 102006
    INVALID_USER_BALANCE = 102011
    NO_ORDER_TO_CANCEL = 102117
    ORDER_ALREADY_EXISTS = 102007
    ORDER_ALREADY_EXPIRED = 102008
    ORDER_AMOUNT_EXEECEDED = 102020
    ORDER_AMOUNT_TOO_SMALL = 102012
    ORDER_CANCEL_FAILURE = 102118
    ORDER_INVALID_ACCOUNT_ID = 102003  # Duplicate: (Orders, Market, AMM Pools `104003`)
    ORDER_MISSING_SIG = 102010
    ORDER_UNSUPPORTED_MARKET = 102005  # Duplicate: (Orderbook `108000`)
    UNSUPPORTED_TOKEN_ID = 102002

    # Orders, Transaction histories
    EMPTY_USER = 107001
    EMPTY_ORDERHASH = 107002
    NON_EXISTENT_ORDER = 107003

    # Orders, Market, AMM Pools
    INCONSISTENT_TRANSFER_TOKEN_FEE_TOKEN = 102025  # Rename to `TOKEN_INCONSISTENCY`?
    INVALID_ACCOUNT_ID = 104003  # Duplicate: (Order submission `102003`)
    INVALID_EXCHANGE_ID = 102001
    INVALID_NONCE = 102021
    INVALID_TRANSFER_SENDER = 102022
    INVALID_TRANSFER_RECEIVER = 102023
    ORDERBOOK_UNSUPPORTED_MARKET = 108000  # Duplicate: (Order submission `102005`)
    UNSUPPORTED_DEPTH_LEVEL = 108001
    UNSUPPORTED_FEE_TOKEN = 102024

    # Account interactions
    EMPTY_API_KEY = 104001
    EMPTY_SIG = 104004
    INCORRECT_SIG = 104005
    INVALID_API_KEY = 104002

    # ! Not yet implemented !
    IMPL_CONTRACT_NFT_URI = 500001

    # Possibly deprecated, but in documentation
    DEPR_DUPLICATE_REQUEST = 100204
    DEPR_INTERNAL_PERSISTENCE_ERROR = 100203
    DEPR_REQUEST_TIMEOUT = 100002
    DEPR_UPDATE_FAILURE = 100202


class Paths(str, Enum):
    RELAYER_CURRENT_TIME = "/api/v3/timestamp"
    STORAGE_ID = "/api/v3/storageId"
