from datetime import datetime
from typing import List

from .util.helpers import auto_repr, to_snake_case


class _Order:

    account_id: int
    amount_b: str
    amount_s: str
    fee_bips: int
    fill_s:  int
    is_amm: bool
    nft_data: str
    storage_id: int
    taker: str
    token_b: int
    token_s: int
    valid_until: datetime

    def __init__(self, **data):
        for k in data.keys():
            if k == "validUntil":
                ts = datetime.fromtimestamp(data[k])
                setattr(self, to_snake_case(k), ts)
                continue

            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class _Token:

    amount: str
    nft_data: str
    nft_id: str
    token_address: str
    token_id: int

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class _TxModel:

    account_id: int
    fee: _Token
    from_address: str
    minter: str
    minter_account_id: int
    nft_token: _Token
    nft_type: str
    nonce: int
    owner: str
    order_a: _Order
    order_b: _Order
    storage_id: int
    to_account_address: str
    to_account_id: int
    to_address: str
    to_token: _Token
    token: _Token
    tx_type: str
    valid: bool
    valid_until: datetime

    def __init__(self, **data):
        for k in data.keys():
            if "order" in k:
                setattr(self, to_snake_case(k), _Order(**data[k]))

            elif k in ("fee", "nftToken", "toToken", "token"):
                setattr(self, to_snake_case(k), _Token(**data[k]))

            elif k == "validUntil":
                ts = datetime.fromtimestamp(data[k])
                setattr(self, to_snake_case(k), ts)

            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class Block:

    block_id: int
    block_size: int
    created_at: datetime
    exchange: str
    status: str
    transactions: List[_TxModel]
    tx_hash: str

    def __init__(self, **data):
        for k in data.keys():
            if k == "transactions":
                transactions = []

                for t in data[k]:
                    transactions.append(_TxModel(**t))
                
                setattr(self, to_snake_case(k), transactions)
            
            elif k == "createdAt":
                ts = datetime.fromtimestamp(data[k] / 1000)

                setattr(self, to_snake_case(k), ts)

            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        attrs = []

        for a in self.__annotations__.keys():
            if a != "transactions":
                attrs.append(f"{a}={getattr(self, a)}")
            else:
                n = len(getattr(self, a))
                attrs.append(f"{a}=[{n} Transaction{'s' if n != 1 else ''}]")

        return f"<{' '.join(attrs)}>"
    
    def __str__(self) -> str:
        return f"{self.block_id}"


class FeeInfo:

    fee: str
    type: str

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
        
    def __repr__(self) -> str:
        return f"<type='{self.type}' fee='{self.fee}'>"
    
    def __str__(self) -> str:
        return f"{self.type} {self.fee}"


class OffFeeInfo:

    fee: str
    token: str

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return f"<fee='{self.fee}' token='{self.token}'>"
    
    def __str__(self) -> str:
        return f"{self.fee} {self.token}"


class Exchange:
    
    amm_exit_fees: List[OffFeeInfo]
    chain_id: int
    deposit_address: str
    exchange_address: str
    fast_withdrawal_fees: List[OffFeeInfo]
    onchain_fees: List[FeeInfo]
    open_account_fees: List[OffFeeInfo]
    transfer_fees: List[OffFeeInfo]
    update_fees: List[OffFeeInfo]
    withdrawal_fees: List[OffFeeInfo]

    def __init__(self, **data):
        for k in data.keys():
            if "Fees" in k:
                fees = []

                if k == "onchainFees":

                    for f in data[k]:
                        fees.append(FeeInfo(**f))
                
                else:
                    for f in data[k]:
                        fees.append(OffFeeInfo(**f))

                setattr(self, to_snake_case(k), fees)
            
            else:
                setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        return self.exchange_address


class _BaseTransaction:

    block_id: int
    block_num: int
    hash: int
    id: int
    index_in_block: int
    progress: str
    status: str
    timestamp: datetime
    tx_hash: str
    updated_at: datetime

    def __init__(self, **data):
        for k in data.keys():
            if k in ("timestamp", "updatedAt"):
                setattr(self, to_snake_case(k), datetime.fromtimestamp(data[k] / 1000))
                continue

            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        return self.tx_hash


class DepositHashData(_BaseTransaction):

    amount: int
    symbol: str

    def __init__(self, **data):
        self.__annotations__.update(super().__annotations__)

        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return auto_repr(self)


class TransactionHashData(_BaseTransaction):
    
    fee_amount: int
    fee_token_symbol: str
    owner: str

    def __init__(self, **data):
        self.__annotations__.update(super().__annotations__)

        super().__init__(**data)
    
    def __repr__(self) -> str:
        return auto_repr(self)


class TransferHashData(DepositHashData):

    fee_amount: int
    fee_token_symbol: str
    memo: str
    receiver: int
    receiver_address: str
    sender_address: str
    tx_type: str

    def __init__(self, **data):
        self.__annotations__.update(super().__annotations__)

        super().__init__(**data)
    
    def __repr__(self) -> str:
        return auto_repr(self)
    
    def __str__(self) -> str:
        return self.hash


# TODO: Redesign these classes and inheritances to fix unwanted intellisense
#       suggestions (e.g. '.owner')
class WithdrawalHashData(TransactionHashData, DepositHashData):

    distribute_hash: str
    fast_status: str
    request_id: int
    tx_type: str

    def __init__(self, **data):
        self.__annotations__.update(super().__annotations__)

        super().__init__(**data)

    def __repr__(self) -> str:
        return auto_repr(self)
