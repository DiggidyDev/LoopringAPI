# TODO: This file might get a bit cramped and spaghetti-ish...
#       Perhaps start subclassing more errors and using the returned
#       exception messages to your advantage.

class LoopringError(Exception):
    """The default base class for all Loopring exceptions."""
    pass


class AddressNotFound(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Address wasn't found."
        super().__init__(message)


class EmptyAPIKey(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Empty API key."
        super().__init__(message)


class EmptyOrderhash(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Orderhash cannot be empty."
        super().__init__(message)


class EmptySignature(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Supplied signature was empty. Please provide one."
        super().__init__(message)


class EmptyUser(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "User ID cannot be empty."
        super().__init__(message)


class FailedToFreeze(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Failed to freeze the amount. Please try again later."
        super().__init__(message)


class FailedToSubmit(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Failed to submit order."
        super().__init__(message)


class InvalidAccountID(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Invalid account ID."
        super().__init__(message)


class InvalidAPIKey(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Invalid API key."
        super().__init__(message)


class InvalidArguments(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Invalid arguments supplied."
        super().__init__(message)


class InvalidExchangeID(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Invalid exchange ID."
        super().__init__(message)


class InvalidNonce(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Invalid nonce."
        super().__init__(message)


class InvalidOrder(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Invalid Order."
        super().__init__(message)


class InvalidOrderID(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Invalid order ID."
        super().__init__(message)


class InvalidRate(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Illegal rate supplied."
        super().__init__(message)


class InvalidSignature(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Incorrect signature supplied."
        super().__init__(message)


class InvalidUserBalance(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Insufficient user balance."
        super().__init__(message)


class OrderAlreadyExists(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Order already exists."
        super().__init__(message)


class OrderAlreadyExpired(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Order already expired."
        super().__init__(message)


class OrderAmountTooSmall(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "The order amount is too small."
        super().__init__(message)


class OrderAmountExceeded(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Exceeded the maximum order amount."
        super().__init__(message)


class OrderInvalidAccountID(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Invalid account ID supplied to order."
        super().__init__(message)


class OrderMissingSignature(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Order signature is missing."
        super().__init__(message)


class OrderNotFound(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Order doesn't exist."
        super().__init__(message)


class OrderUnsupportedMarket(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Unsupported market for order operation."
        super().__init__(message)


class UnknownError(LoopringError):
    
    def __init__(self, message: str=None):
        if not message:
            message = "An unknown error occured."
        super().__init__(message)


class UnsupportedTokenID(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "Unsupported Token ID in the order."
        super().__init__(message)


class UserNotFound(LoopringError):

    def __init__(self, message: str=None):
        if not message:
            message = "User wasn't found."
        super().__init__(message)
