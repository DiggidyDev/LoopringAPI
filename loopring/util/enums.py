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
        approaches:

        `102003`, `104003` & `108000`, `102005`

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
    INVALID_QUERY_STRING = 104007
    USER_NOT_FOUND = 101002

    # Orders
    FAILED_TO_FREEZE_AMOUNT = 102014
    FAILED_TO_SUBMIT_ORDER = 102027
    INSUFFICIENT_BALANCE_FOR_FEES = 102030  # Undocumented error code
    INVALID_ORDER = 102120
    INVALID_ORDER_ID = 102004
    INVALID_RATE = 102006
    INVALID_USER_BALANCE = 102011
    MINIMUM_FEES_NOT_EXCEEDED = 114002  # Undocumented error code
    NO_ORDER_TO_CANCEL = 102117
    ORDER_ALREADY_EXISTS = 102007
    ORDER_ALREADY_EXPIRED = 102008
    ORDER_AMOUNT_EXCEEDED = 102020
    ORDER_AMOUNT_TOO_SMALL = 102012
    ORDER_CANCEL_FAILURE = 102118
    ORDER_INVALID_ACCOUNT_ID = 102003  # Duplicate: (Orders, Market, AMM Pools `104003`)
    ORDER_MISSING_SIG = 102010
    ORDER_UNSUPPORTED_MARKET = 102005  # Duplicate: (Orderbook `108000`)
    UNSUPPORTED_TOKEN_ID = 102002

    # Orders, Transaction histories
    EMPTY_USER = 107001
    EMPTY_ORDERHASH = 107002
    INVALID_BLOCK = 103011  # Undocumented error code
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
    INVALID_API_KEY = 104002
    INVALID_SIG = 104005

    # ! Not yet implemented !
    IMPL_CONTRACT_NFT_URI = 500001
    """
    .. warning:: This error code has yet to be implemented (or at least \
                isn't referenced in the official API docs).
    
    """

    # Possibly deprecated, but in documentation
    DEPR_DUPLICATE_REQUEST = 100204
    """.. deprecated:: 0.0.1a"""
    DEPR_INTERNAL_PERSISTENCE_ERROR = 100203
    """.. deprecated:: 0.0.1a"""
    DEPR_REQUEST_TIMEOUT = 100002
    """.. deprecated:: 0.0.1a"""
    DEPR_UPDATE_FAILURE = 100202
    """.. deprecated:: 0.0.1a"""


class Paths(str, Enum):
    """All paths available on the API."""

    ACCOUNT = "/api/v3/account"
    API_KEY = "/api/v3/apiKey"
    BLOCK_INFO = "/api/v3/block/getBlock"
    CANDLESTICK = "/api/v3/candlestick"
    DEPTH = "/api/v3/depth"
    EXCHANGES = "/api/v3/exchange/info"
    MARKETS = "/api/v3/exchange/markets"
    ORDER = "/api/v3/order"
    ORDERS = "/api/v3/orders"
    PRICE = "/api/v3/price"
    RELAYER_CURRENT_TIME = "/api/v3/timestamp"
    STORAGE_ID = "/api/v3/storageId"
    TICKER = "/api/v3/ticker"
    TOKENS = "/api/v3/exchange/tokens"
    TRADE = "/api/v3/trade"
    TRADE_HISTORY = "/api/v3/user/trades"
    TRANSFER = "/api/v3/transfer"
    USER_BALANCES = "/api/v3/user/balances"
    USER_DEPOSITS = "/api/v3/user/deposits"
    USER_OFFCHAIN_FEE = "/api/v3/user/offchainFee"
    USER_ORDER_FEE = "/api/v3/user/orderFee"
    USER_ORDER_RATES = "/api/v3/user/orderUserRateAmount"
    USER_PASSWORD_RESETS = "/api/v3/user/updateInfo"
    USER_REGISTRATION = "/api/v3/user/createInfo"
    USER_TRANSFERS = "/api/v3/user/transfers"
    USER_WITHDRAWALS = "/api/v3/user/withdrawals"



class IntSig(IntEnum):

    DEFAULT_EXPONENT = 7
    DEFAULT_ROUNDS = 91

    FR_ORDER = 21888242871839275222246405745257275088614511777268538073601725287587578984328
    SNARK_SCALAR_FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617

    JUBJUB_Q = SNARK_SCALAR_FIELD
    JUBJUB_E = 21888242871839275222246405745257275088614511777268538073601725287587578984328
    JUBJUB_C = 8
    JUBJUB_L = JUBJUB_E // JUBJUB_C
    JUBJUB_A = 168700
    JUBJUB_D = 168696

    MONT_A = 168698
    MONT_A24 = int((MONT_A + 2) / 4)
    MONT_B = 1


class StrSig(str, Enum):

    DEFAULT_SEED = b"mimc"

    P13N_EDDSA_VERIFY_M = "EdDSA_Verify.M"
    P13N_EDDSA_VERIFY_RAM = "EdDSA_Verify.RAM"
