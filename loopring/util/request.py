class Request:

    __slots__ = [
        "host",
        "method",
        "params",
        "path",
        "payload"
    ]

    def __init__(
        self,
        method: str,
        host: str,
        path: str,
        *,
        params: dict=None,
        payload: dict=None
    ):
        self.host = host
        self.method = method.upper()
        self.params = params
        self.path = path
        self.payload = payload
