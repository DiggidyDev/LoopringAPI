class Token:
    """Token class.
    
    Args:
        id (int): ...
        volume (str): ...

    """

    id: int
    volume: str

    def __init__(self, *, id: int=None, volume: str=None):
        self.id = id
        self.volume = volume
