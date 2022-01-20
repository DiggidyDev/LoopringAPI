import eip712_structs
from eip712_structs import Address, Array, Bytes, EIP712Struct, Uint
from web3 import Web3


class EIP712:

    EIP191_HEADER = bytes.fromhex("1901")

    amm_pool_domains: dict = {}

    @classmethod
    def init_env(cls,
        name="Loopring Protocol",
        version="3.6.0",
        chain_id=None,
        verifying_contract=None):
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


def generate_amm_pool_join_EIP712_hash(payload: dict):
    """
        struct PoolJoin
        {
            address   owner;
            uint96[]  joinAmounts;
            uint32[]  joinStorageIDs;
            uint96    mintMinAmount;
            uint32    validUntil;
        }
    """
    
    class PoolJoin(EIP712Struct):
        owner           = Address()
        joinAmounts     = Array(Uint(96))
        joinStorageIDs  = Array(Uint(32))
        mintMinAmount   = Uint(96)
        validUntil      = Uint(32)

    join = PoolJoin(
        owner           = payload["owner"],
        joinAmounts     = [int(token["volume"]) for token in payload["joinTokens"]["pooled"]],
        joinStorageIDs  = [int(i) for i in payload["storageIds"]],
        mintMinAmount   = int(payload["joinTokens"]["minimumLp"]["volume"]),
        validUntil      = payload["validUntil"]
    )

    return EIP712.hash_packed(
        EIP712.amm_pool_domains[payload["poolAddress"]].hash_struct(),
        join.hash_struct()
    )


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

    setattr(Transfer, "from", Address())  # because `from` is a reserved keyword
    Transfer.amount = Uint(96)
    Transfer.feeTokenID = Uint(16)
    Transfer.maxFee = Uint(96)
    Transfer.to = Address()
    Transfer.tokenID = Uint(16)
    Transfer.storageID = Uint(32)
    Transfer.validUntil = Uint(32)

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


def generate_offchain_withdrawal_EIP712_hash(payload: dict):
    """
        struct Withdrawal
        {
            address owner;
            uint32  accountID;
            uint16  tokenID;
            uint    amount;
            uint16  feeTokenID;
            uint    fee;
            address to;
            bytes32 extraDataHash;
            uint    minGas;
            uint32  validUntil;
            uint32  storageID;
        }
    """

    class Withdrawal(EIP712Struct):
        owner = Address()
        accountID = Uint(32)
        tokenID = Uint(16)
        amount = Uint(96)
        feeTokenID = Uint(16)
        maxFee = Uint(96)
        to = Address()
        extraData = Bytes()
        minGas = Uint()
        validUntil = Uint(32)
        storageID = Uint(32)

    withdrawal = Withdrawal(**{
        "accountID"     : payload["accountId"],
        "amount"        : int(payload["token"]["volume"]),
        "extraData"     : bytes.fromhex(payload["extraData"].decode()),
        "feeTokenID"    : payload["maxFee"]["tokenId"],
        "maxFee"        : int(payload["maxFee"]["volume"]),
        "minGas"        : int(payload["minGas"]),
        "owner"         : payload["owner"],
        "storageID"     : payload["storageId"],
        "to"            : payload["to"],
        "tokenID"       : payload["token"]["tokenId"],
        "validUntil"    : payload["validUntil"]
    })

    return EIP712.hash_packed(
        EIP712.exchange_domain.hash_struct(),
        withdrawal.hash_struct()
    )


def generate_onchain_data_hash(*,
    min_gas: int,
    to: str,
    extra_data: bytes):
    return Web3.keccak(b"".join(
        [
            int(min_gas).to_bytes(32, "big"),
            int(to, 16).to_bytes(20, "big"),
            extra_data
        ]
    ))[:20]
