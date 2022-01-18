from eip712_structs import EIP712Struct, Address, Boolean, Bytes, Int, String, Uint
import eip712_structs

from web3 import Web3


class EIP712:

    EIP191_HEADER = bytes.fromhex("1901")

    amm_pool_domains: dict = {}

    @classmethod
    def init_env(cls, name, version, chain_id, verifying_contract):
        cls.exchange_domain = eip712_structs.make_domain(
            name=name,
            version=version,
            chainId=chain_id,
            verifyingContract=verifying_contract
        )
    
    @classmethod
    def init_amm_env(cls, name, version, chain_id, verifying_contract):
        cls.amm_pool_domains[verifying_contract] = eip712_structs.make_domain(
            name=name,
            version=version,
            chainId=chain_id,
            verifyingContract=verifying_contract
        )

    @classmethod
    def hash_packed(cls, domain_hash, data_hash):
        return Web3.keccak(b"".join([cls.EIP191_HEADER, domain_hash, data_hash]))


def generate_transfer_EIP712_hash(payload: dict):
    """
        struct Transfer
        {
            address from;
            address to;
            uint16  tokenID;
            uint    amount;
            uint16  feeTokenID;
            uint    fee;
            uint32  validUntil;
            uint32  storageID;
        }

    """

    class Transfer(EIP712Struct):
        pass

    setattr(Transfer, "from", Address())
    Transfer.amount = Uint(96)
    Transfer.fee_token_id = Uint(16)
    Transfer.max_fee = Uint(96)
    Transfer.to = Address()
    Transfer.token_id = Uint(16)
    Transfer.storage_id = Uint(32)
    Transfer.valid_until = Uint(32)

    transfer = Transfer(**{
        "from"          : payload["payerAddr"],
        "to"            : payload["payeeAddr"],
        "tokenID"       : payload["token"]["tokenId"],
        "amount"        : int(payload["token"]["volume"]),
        "feeTokenID"    : payload["maxFee"]["tokenId"],
        "maxFee"        : int(payload["maxFee"]["volume"]),
        "validUntil"    : payload["validUntil"],
        "storageID"     : payload["storageId"]
    })

    return EIP712.hash_packed(
        EIP712.exchange_domain.hash_struct(),
        transfer.hash_struct()
    )
