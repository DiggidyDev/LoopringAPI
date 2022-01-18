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
            f"publicX='{self.publicX}' publicY='{self.publicY}' nonce={self.nonce}" + \
            f"key_nonce={self.key_nonce} key_seed='{self.key_seed} tags={self.tags}'>"
    
    def __str__(self) -> str:
        return self.owner
