from loopring.errors import *

from .enums import ErrorCodes as ERR


ERROR_MAPPINGS = {
    ERR.EMPTY_API_KEY: EmptyAPIKey,
    ERR.INVALID_ACCOUNT_ID: InvalidAccountID,
    ERR.INVALID_API_KEY: InvalidAPIKey,
    ERR.INVALID_ARGUMENTS: InvalidArguments,
    ERR.UNKNOWN_ERROR: UnknownError,
    ERR.USER_NOT_FOUND: UserNotFound
}