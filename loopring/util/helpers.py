from typing import Callable

from aiolimiter import AsyncLimiter

from ..util.mappings import Mappings


def raise_errors_in(content: dict) -> None:
    """Raise the appropriate error from an API response.
    
    Exceptions are accessed from a mapping, using the corresponding
    enum, and passing the error message from the `content` to the
    error itself.
    Please note that the terms 'Exception' and 'Error' may be used
    interchangeably.

    Raises:
        LoopringError: The default base class for all Loopring exceptions.

    """

    if content.get("resultInfo"):
        result = content.get("resultInfo")
        error_occured = result.get("code") or False

        if error_occured:
            # For some reason it could return as 'msg' or 'message',
            # even though the docs only mention 'msg'...
            message = result.get("msg") or result.get("message")

            raise Mappings.ERROR_MAPPINGS[error_occured](message)


def ratelimit(rate: int, per: int) -> Callable:
    """A ratelimit decorator for an asynchronous function.
    
    Leaky bucket algorithm.

    Warning:
        This decorator has yet to be finished. W.I.P.

    Args:
        rate (int): The number of times the function can be executed.
        per (int): How often the target rate can be achieved.

    """

    async def wrapper(*args, **kwargs):
        limit: AsyncLimiter = AsyncLimiter(rate, per)
        
    return wrapper


def to_snake_case(target: str) -> str:
    """Take a 'camelCase' string and return its 'snake_case' format."""

    result = ""

    for _ in list(target):
        if _.isupper():
            result += f"_{_.lower()}"
            continue
        result += _
    
    return result
