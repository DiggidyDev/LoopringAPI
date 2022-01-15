class SDKError(Exception):
    """The base class for all SDK-related exceptions."""


class SquareRootError(SDKError):
    pass


class NegativeExponentError(SDKError):
    pass
