import time
from datetime import datetime
from typing import Callable, Iterable, Union

from aiolimiter import AsyncLimiter

from ..errors import ValidationException
from ..util.mappings import Mappings


# TODO: Maybe do something like this for `setattr()` too?
def auto_repr(obj: object):
    """A lazy '__repr__()' substitute."""
    attrs = []

    for a in obj.__annotations__.keys():
        try:
            if isinstance(getattr(obj, a), datetime):
                attrs.append(f"{a}='{getattr(obj, a)}'")
            else:
                attrs.append(f"{a}={repr(getattr(obj, a))}")

        except AttributeError:
            continue

    return f"<{' '.join(attrs)}>"


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


def fetch(seq: Iterable, **attrs) -> object:
    """A helper for fetching an object from an iterable.
    
    Only the first instance will be returned where all ``attrs`` match.

    Args:
        seq: A sequence of objects to search through.

    """

    if isinstance(seq, dict):
        seq = seq.values()
    
    for obj in seq:
        if all(getattr(obj, attr) == attrs[attr] for attr in attrs):
            return obj


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

            try:
                raise Mappings.ERROR_MAPPINGS[error_occured](message)
            except KeyError:
                raise KeyError(f"{error_occured} not registered in 'enums.py'. " + \
                f"'{message}'.")


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

    # Edge cases: e.g. `accountID`, `storageID`
    if len(camel) > 1 and camel[-1].isupper() and camel[-2].isupper():
        camel = camel[:-1] + camel[-1].lower()

    for _ in list(camel):
        if _.isupper():
            snake += f"_{_.lower()}"
            continue
        snake += _
    
    return snake


def validate_timestamp(
        timestamp: Union[int, datetime],
        unit: str="ms",
        validate_future: bool=False
    ) -> int:
    """Validate whether the given time will be suitable for the API.
    
    The API seems to like taking timestamps in both ms and seconds format, which
    requires a length of 13 and 10 respectively. A datetime object's timestamp can
    be multiplied by 1000, but if a user wishes to pass an int, it has to be the 
    right length. The :meth:`~datetime.datetime.fromtimestamp()` method takes a 10
    digit timestamp.

    Args:
        timestamp (Union[int, :obj:`~datetime.datetime`]): The `int` or
            :obj:`datetime.datetime` object to be validated.
        unit (str): Whether to validate the timestamp as seconds or 'ms'.
    
    Returns:
        int: A 13 digit or 10 digit timestamp.

    Raises:
        ValidationException: The int wasn't the right length, or the timestamp \
            was in the past.
        TypeError: The `time` wasn't of the expected type.

    """
    multiplier = 1000 if unit == "ms" else 1

    if isinstance(timestamp, datetime):
        ts = int(timestamp.timestamp() * multiplier)

        # Check that the timestamp is in the future
        # TODO: Maybe raise a warning if the timestamp
        #       is in the near future?
        if validate_future and ts < int(time.time()) * multiplier:
            raise ValidationException("Please enter a future time.")

        return ts
    
    if isinstance(timestamp, int):
        exp_len = 13 if unit == "ms" else 10

        if len(str(timestamp)) != exp_len:
            raise ValidationException(
                f"Invalid length (received `{len(str(timestamp))}` instead of " + \
                f"`{exp_len}`). Try using a datetime object, or refer to the " + \
                "documentation."
            )
        
        # Check the timestamp is in the future
        if validate_future and timestamp < int(time.time()) * multiplier:
            raise ValidationException("Please enter a future timestamp.")

        return timestamp
    
    if timestamp:
        raise TypeError(
            f"Invalid type. Expected 'int' or 'datetime.datetime', got '{type(timestamp)}'."
        )


# TODO: Fix circular import for `TokenConfig` :p
def volume_fp(volume: str, cfg) -> float:
    """Convert a normalised volume to floating point."""

    return int(volume) * 10**-(cfg.decimals)

