from typing import Callable
from aiolimiter import AsyncLimiter


def ratelimit(rate: int, per: int) -> Callable:
    """A ratelimit decorator for an asynchronous function.
    
    Leaky bucket algorithm.

    Args:
        rate (int): The number of times the function can be executed.
        per (int): How often the target rate can be achieved.

    """

    async def wrapper(*args, **kwargs):
        limit: AsyncLimiter = AsyncLimiter(rate, per)
        
        

    return wrapper
