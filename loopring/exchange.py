from datetime import datetime
from typing import List

from loopring.util.helpers import to_snake_case


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
        return f"<exchange_address='{self.exchange_address}' " + \
            f"deposit_address='{self.deposit_address}' chain_id={self.chain_id} " + \
            f"onchain_fees={self.onchain_fees} update_fees={self.update_fees} " + \
            f"withdrawal_fees={self.withdrawal_fees} " + \
            f"fast_withdrawal_fees={self.fast_withdrawal_fees} " + \
            f"open_account_fees={self.open_account_fees} " + \
            f"transfer_fees={self.transfer_fees} amm_exit_fees={self.amm_exit_fees}>"
    
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
    
    def __str__(self) -> str:
        return self.tx_hash


class DepositHashData(_BaseTransaction):

    amount: int
    symbol: str

    def __init__(self, **data):
        for k in data.keys():
            setattr(self, to_snake_case(k), data[k])
    
    def __repr__(self) -> str:
        return f"<hash='{self.hash}' tx_hash='{self.tx_hash}' " + \
            f"amount={self.amount} status='{self.status}' " + \
            f"progress='{self.progress}' symbol='{self.symbol}' " + \
            f"block_num='{self.block_num}' block_id={self.block_id} " + \
            f"updated_at='{self.updated_at}' timestamp='{self.timestamp}' " + \
            f"index_in_block={self.index_in_block} id={self.id}>"


class TransactionHashData(_BaseTransaction):
    
    fee_amount: int
    fee_token_symbol: str
    owner: str

    def __init__(self, **data):
        super().__init__(**data)
    
    def __repr__(self) -> str:
        return f"<hash='{self.hash}' tx_hash='{self.tx_hash}' " + \
            f"owner='{self.owner}' status='{self.status}' " + \
            f"progress='{self.progress}' fee_token_symbol={self.fee_token_symbol} " + \
            f"fee_amount='{self.fee_amount}' block_id={self.block_id} " + \
            f"updated_at='{self.updated_at}' timestamp='{self.timestamp}' " + \
            f"index_in_block={self.index_in_block} id={self.id} " + \
            f"block_num={self.block_num}>"



# TODO: Redesign these classes and inheritances to fix unwanted intellisense
#       suggestions (e.g. '.owner')
class WithdrawalHashData(TransactionHashData, DepositHashData):

    distribute_hash: str
    fast_status: str
    request_id: int
    tx_type: str

    def __init__(self, **data):
        super().__init__(**data)
    
    def __repr__(self) -> str:
        return f"<hash='{self.hash}' tx_hash='{self.tx_hash}' " + \
            f"tx_type='{self.tx_type}' status='{self.status}' " + \
            f"progress='{self.progress}' fee_token_symbol={self.fee_token_symbol} " + \
            f"fee_amount='{self.fee_amount}' block_id={self.block_id} " + \
            f"updated_at='{self.updated_at}' timestamp='{self.timestamp}' " + \
            f"index_in_block={self.index_in_block} id={self.id} " + \
            f"block_num={self.block_num} distribute_hash='{self.distribute_hash}' " + \
            f"fast_status='{self.fast_status}' request_id={self.request_id}>"
