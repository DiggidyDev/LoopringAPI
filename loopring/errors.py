class LoopringError(Exception):
    """
    The default base class for all Loopring exceptions.
    """

    pass


class UnknownError(LoopringError):
    
    def __init__(self):
        message = "An unknown error occured."
        super().__init__(message)


class InvalidArguments(LoopringError):

    def __init__(self, message=None):
        super().__init__(message)


class AddressNotFound(LoopringError):

    def __init___(self):
        message = "Address wasn't found."
        super().__init__(message)


class UserNotFound(LoopringError):

    def __init__(self):
        message = "User wasn't found."
        super().__init__(message)


class IncorrectExchangeID(LoopringError):

    def __init__(self):
        message = "Incorrect Exchange ID supplied."
        super().__init__(message)
