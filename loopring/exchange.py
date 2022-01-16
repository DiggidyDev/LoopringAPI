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
