# TODO: This file might get a bit cramped and spaghetti-ish...
#       Perhaps start subclassing more errors and using the returned
#       exception messages to your advantage.

class LoopringError(Exception):
    """The default base class for all Loopring exceptions."""
    pass


class UnknownError(LoopringError):
    
    def __init__(self, message=None):
        if not message:
            message = "An unknown error occured."

        super().__init__(message)


class EmptyAPIKey(LoopringError):

    def __init__(self, message=None):
        if not message:
            message = "Empty API key."
        
        super().__init__(message)


class InvalidAPIKey(LoopringError):

    def __init__(self, message=None):
        if not message:
            message = "Invalid API key."
        
        super().__init__(message)


class InvalidAccountID(LoopringError):

    def __init__(self, message=None):
        if not message:
            message = "Invalid account ID."
        
        super().__init__(message)


class InvalidArguments(LoopringError):

    def __init__(self, message=None):
        if not message:
            message = "Invalid arguments supplied."
        super().__init__(message)


class AddressNotFound(LoopringError):

    def __init___(self):
        message = "Address wasn't found."
        super().__init__(message)


class UserNotFound(LoopringError):

    def __init__(self, message=None):
        if not message:
            message = "User wasn't found."
        super().__init__(message)


class IncorrectExchangeID(LoopringError):

    def __init__(self):
        message = "Incorrect Exchange ID supplied."
        super().__init__(message)
