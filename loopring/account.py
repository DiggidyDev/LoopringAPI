from .util.helpers import to_snake_case


class Account:
    """A model used to describe a Loopring account."""

    account_id: int
    frozen: bool
    key_nonce: int
    key_seed: str
    nonce: int
    owner: str
    publicX: str
    publicY: str
    tags: str

    def __init__(self, **data):
        for k in data.keys():
            if k == "publicKey":
                for pk in data[k].keys():
                    setattr(self, f"public{pk.upper()}", data[k][pk])
            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return f"<account_id={self.account_id} owner='{self.owner}' " + \
            f"publicX='{self.publicX}' publicY='{self.publicY}' nonce={self.nonce} " + \
            f"key_nonce={self.key_nonce} key_seed='{self.key_seed}' tags={self.tags}'>"
    
    def __str__(self) -> str:
        return self.owner


class _PendingBalance:

    deposit: int
    withdraw: int

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), int(data[k]))

    def __repr__(self) -> str:
        return f"<deposit={self.deposit} withdraw={self.withdraw}>"
    
    def __str__(self) -> str:
        return f"Deposit: {self.deposit}, Withdraw: {self.withdraw}"


class Balance:

    account_id: int
    locked: int
    pending: _PendingBalance
    token_id: int
    total: int

    def __init__(self, **data):
        for k in data.keys():
            if k == "pending":
                self.pending = _PendingBalance(**data[k])
            else:
                setattr(self, to_snake_case(k), int(data[k]))
    
    def __repr__(self) -> str:
        return f"<total={self.total} pending={repr(self.pending)} " + \
            f"token_id={self.token_id} locked={self.locked} " + \
            f"account_id={self.account_id}>"
    
    def __str__(self) -> str:
        return self.total
