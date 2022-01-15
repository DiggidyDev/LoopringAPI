from typing import Any


class Token:
    """Token class.
    
    Args:
        id (int): ...
        volume (str): ...

    """

    id: int
    volume: str

    def __getitem__(self, __name) -> Any:
        return self.__dict__[__name]

    def __init__(self, *, id: int=None, volume: str=None):
        self.id = id
        self.volume = volume
