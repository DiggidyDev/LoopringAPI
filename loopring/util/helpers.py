from typing import Callable

from aiolimiter import AsyncLimiter

from ..util.mappings import Mappings


def clean_params(params: dict) -> dict:
    """Clean all NoneType parameters from a given dict.
    
    The API doesn't always require all the possible parameters to be passed
    to it when making a request, so this helper function should help to
    remove any paramaters that won't be needed.

    Note:
        This will only remove all values whose object evaluation returns True
        for `None`. In other words, all 
        [falsy](https://stackoverflow.com/a/39984051/7808223) values other than
        `None` will remain.

    Returns:
        dict: A clean parameter dictionary, removing all pairs with `None` values.

    """

    return {k: v for k, v in params.items() if v is not None}


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
    if not isinstance(content, dict):
        # For some reason, `get_token_configurations()` returns
        # a list instead of a dict :p
        #
        # And because of that, we can assume that the request
        # was successful, otherwise an error would've been
        # returned in a dict
        return

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


def to_snake_case(camel: str) -> str:
    """Take a 'camelCase' string and return its 'snake_case' format.

    This is primarily used in conjunction with :py:func:`setattr()`
    when dynamically instantiating classes when interacting with the
    API.
    
    Examples:
        >>> c = "myStringContents"
        >>> s = to_snake_case(c)
        >>> s
        'my_string_contents'
    
    Args:
        camel (str): The target camelCase string to turn into snake_case.
    
    Returns:
        str: The snake_case equivalent of the `camel` input.

    """

    snake = ""

    for _ in list(camel):
        if _.isupper():
            snake += f"_{_.lower()}"
            continue
        snake += _
    
    return snake
