from collections import namedtuple
from hashlib import sha512

from bitstring import BitArray

from ...enums import IntSig, StrSig
from .field import FQ
from .jubjub import Point
from .mimc import mimc_hash
from .pedersen import pedersen_hash_bits, pedersen_hash_bytes
from .poseidon.permutation import poseidon, poseidon_params


_SignedMessage = namedtuple("_SignedMessage", ("A", "sig", "msg"))


def as_scalar(*args):
    for x in args:
        if isinstance(x, FQ):
            yield int(x)
        elif isinstance(x, int):
            yield x
        elif isinstance(x, Point):
            yield int(x.x)
            yield int(x.y)
        elif isinstance(x, (tuple, list)):
            for _ in as_scalar(*x):
                yield _
        
        else:
            raise TypeError(f"Unknown type: {type(x)}")


class _SignatureScheme:

    @classmethod
    def B(cls) -> Point:
        return Point.generator()
    
    @classmethod
    def hash_public(cls, R, A, M):
        raise NotImplementedError()
    
    @classmethod
    def hash_secret(cls, k: FQ, *args):
        data = b"".join(cls.to_bytes(_) for _ in (k,) + args)
        return int.from_bytes(sha512(data).digest(), "little") % IntSig.JUBJUB_L

    @classmethod
    def prehash_message(cls, M):
        return M
    
    @classmethod
    def random_keypair(cls, B: Point=None):
        B = B or cls.B()
        k = FQ.random(IntSig.JUBJUB_L)
        A = B * k
        return k, A
    
    @classmethod
    def sign(cls, msg, key: FQ, B: Point=None):
        if key.n >= IntSig.JUBJUB_L or key.n <= 0:
            raise RuntimeError("Strict parsing of k failed.")
        
        B = B or cls.B()
        A = B * key

        M = cls.prehash_message(msg)
        r = cls.hash_secret(key, M)
        R = B * r

        t = cls.hash_public(R, A, M)
        S = (r + (key.n * t)) % IntSig.JUBJUB_E

        return SignedMessage(A, Signature(R, S), msg)

    @classmethod
    def to_bits(cls, *args):
        result = BitArray()

        for M in args:
            if isinstance(M, Point):
                result.append(M.x.bits())  # `M.y` not needed?
            elif isinstance(M, FQ):
                result.append(M.bits())
            elif isinstance(M, (list, tuple)):
                for _ in cls.to_bits(M):
                    result.append(_)
            elif isinstance(M, (bytes, BitArray)):
                result.append(M)
            else:
                raise TypeError(f"Bad type for M: {type(M)}")

        return result

    @classmethod
    def to_bytes(cls, *args):
        result = b""

        for M in args:
            if isinstance(M, Point):
                result += M.x.to_bytes("little")
                result += M.y.to_bytes("little")
            elif isinstance(M, FQ):
                result += M.to_bytes("little")
            elif isinstance(M, (list, tuple)):
                result += b"".join(cls.to_bytes(_) for _ in M)
            elif isinstance(M, int):
                result += M.to_bytes(32, "little")
            elif isinstance(M, BitArray):
                result += M.tobytes()
            elif isinstance(M, bytes):
                result += M
            else:
                raise TypeError(f"Bad type for M: {type(M)}")
        
        return result
    
    @classmethod
    def verify(cls, A, sig, msg, B: Point=None):
        if not isinstance(A, Point):
            A = Point(*A)
        
        if not isinstance(sig, Signature):
            sig = Signature(*sig)
        
        R, S = sig
        B = B or cls.B()
        lhs = B * S

        M = cls.prehash_message(msg)
        rhs = R + (A * cls.hash_public(R, A, M))

        return lhs == rhs


class PureEdDSA(_SignatureScheme):

    @classmethod
    def hash_public(cls, *args, p13n=StrSig.P13N_EDDSA_VERIFY_RAM):
        return pedersen_hash_bits(p13n, cls.to_bits(*args)).x.n


class EdDSA(PureEdDSA):

    @classmethod
    def prehash_message(cls, M, p13n=StrSig.P13N_EDDSA_VERIFY_M):
        return pedersen_hash_bytes(p13n, M)


class MiMCEdDSA(_SignatureScheme):

    @classmethod
    def hash_public(cls, *args, p13n=StrSig.P13N_EDDSA_VERIFY_RAM):
        return mimc_hash(list(as_scalar(*args)), seed=p13n)


class PoseidonEdDSA(_SignatureScheme):
    
    @classmethod
    def hash_public(cls, *args):
        poseidon_hash_params = poseidon_params(
            IntSig.SNARK_SCALAR_FIELD, 6, 6, 52, b"poseidon", 5, security=128
            )
        msg = list(as_scalar(*args))

        return poseidon(msg, poseidon_hash_params)


class Signature:

    R: Point
    s: FQ

    def __init__(self, R, s):
        self.R = R if isinstance(R, Point) else Point(*R)
        self.s = s if isinstance(s, FQ) else FQ(s)

        assert self.s.m == IntSig.JUBJUB_Q
    
    def __iter__(self):
        return iter([self.R, self.s])
    
    def __str__(self):
        return " ".join(str(_) for _ in [self.R.x, self.R.y, self.s])


class SignedMessage(_SignedMessage):

    def __str__(self):
        return " ".join(str(_) for _ in [self.A, self.sig, self.msg])
