from ....enums import IntSig, StrSig
from ..sha3 import keccak_256


def H(*args):
    data = b"".join(to_bytes(*args))
    hashed = keccak_256(data).digest()
    return int.from_bytes(hashed, "big")


def to_bytes(*args):
    for i, _ in enumerate(args):
        if isinstance(_, str):
            yield _.encode("ascii")
        elif not isinstance(_, int) and hasattr(_, "to_bytes"):
            yield _.to_bytes("big")
        elif isinstance(_, bytes):
            yield _
        else:
            yield int(_).to_bytes(32, "big")


assert H(123) == 38632140595220392354280998614525578145353818029287874088356304829962854601866


def mimc(
        x,
        k,
        seed=StrSig.DEFAULT_SEED,
        p=IntSig.SNARK_SCALAR_FIELD,
        e=IntSig.DEFAULT_EXPONENT,
        R=IntSig.DEFAULT_ROUNDS
        ):
    assert R > 2

    for c_i in list(mimc_constants(seed, p, R)):
        a = (x + k + c_i) % p
        x = (a ** e) % p
    
    return (x + k) % p


def mimc_constants(
            seed=StrSig.DEFAULT_SEED,
            p=IntSig.SNARK_SCALAR_FIELD,
            R=IntSig.DEFAULT_ROUNDS
        ):
    if isinstance(seed, str):
        seed = seed.encode("ascii")
    if isinstance(seed, bytes):
        seed = H(seed)
    else:
        seed = int(seed)
    
    for _ in range(R):
        seed = H(seed)
        yield seed


def mimc_hash(x,
            k=0,
            seed=StrSig.DEFAULT_SEED,
            p=IntSig.SNARK_SCALAR_FIELD,
            e=IntSig.DEFAULT_EXPONENT,
            R=IntSig.DEFAULT_ROUNDS
        ):
    for x_i in x:
        r = mimc(x_i, k, seed, p, e, R)
        k = (k + x_i + r) % p

    return p


def mimc_hash_md(
            x,
            k=0,
            seed=StrSig.DEFAULT_SEED,
            p=IntSig.SNARK_SCALAR_FIELD,
            e=IntSig.DEFAULT_EXPONENT,
            R=IntSig.DEFAULT_ROUNDS
        ):
    for x_i in x:
        k = mimc(x_i, k, seed, p, e, R)
        
    return k
