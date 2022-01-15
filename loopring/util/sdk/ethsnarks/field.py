import sys
from collections import defaultdict
from math import ceil, log2
from os import urandom
from typing import Type

import bitstring

from ...enums import IntSig
from .numtheory import square_root_mod_prime

# aiohttp only supports 3.6+
if sys.version_info.major > 2 and sys.version_info.minor > 5:
    int_types = (int,)
else:
    raise ValueError("Please use Python 3.6 or newer.")


class FQ:

    _COUNTS = None

    def __init__(self, n, field_modulus=IntSig.SNARK_SCALAR_FIELD):
        if isinstance(n, self.__class__):
            if n.m != field_modulus:
                raise ValueError("Field modulus mismatch")

            self.m = n.m
            self.n = n.n
            
        else:
            if not isinstance(n, int_types):
                raise TypeError(f"Invalid number type: {type(n)}")

            if not isinstance(field_modulus, int_types):
                raise TypeError(f"Invalid modulus type: {type(field_modulus)}")

            self.m = field_modulus
            self.n = n % self.m

    def __add__(self, other):
        on = self._validate_n(other)
        self._count("add")
        return FQ((self.n + on) % self.m, self.m)

    def __div__(self, other):
        on = self._validate_n(other)
        self._count("inv")
        return FQ((self.n * pow(on, self.m-2, self.m)) % self.m, self.m)

    def __eq__(self, other):
        if other == 0.:
            other = 0
        # TODO: verify modulus matches other?
        return self.n == self._validate_n(other)

    def __floordiv__(self, other):
        return self.__div__(other)

    def __hash__(self):
        return hash((self.n, self.m))

    def __int__(self):
        return self.n

    def __mul__(self, other):
        on = self._validate_n(other)
        self._count("mul")
        return FQ((self.n * on) % self.m, self.m)

    def __ne__(self, other):
        return not self == other

    def __neg__(self):
        self._count("sub")
        return FQ(-self.n, self.m)

    def __pow__(self, e):
        return self.exp(e)

    def __radd__(self, other):
        return self + other

    def __rdiv__(self, other):
        on = self._validate_n(other)
        self._count("inv")
        self._count("mul")
        return FQ((pow(self.n, self.m-2, self.m) * on) % self.m, self.m)

    def __repr__(self):
        return repr(self.n)

    def __rmul__(self, other):
        return self * other

    def __rsub__(self, other):
        on = self._validate_n(other)
        self._count("sub")
        return FQ((on - self.n) % self.m, self.m)

    def __rtruediv__(self, other):
        return self.__rdiv__(other)

    def __sub__(self, other):
        on = self._validate_n(other)
        self._count("sub")
        return FQ((self.n - on) % self.m, self.m)

    def __truediv__(self, other):
        return self.__div__(other)

    @classmethod
    def _disable_counting(cls):
        cls._COUNTS = None
    
    @classmethod
    def _print_counts(cls):
        for k in sorted(cls._COUNTS.keys()):
            print(k, "=", cls._COUNTS[k], "\n")
    
    @classmethod
    def _count(cls, k):
        if cls._COUNTS:
            cls._COUNTS[k] += 1
    
    @classmethod
    def _reset_counts(cls):
        cls._COUNTS = defaultdict(int)

    @classmethod
    def one(self, modulus=IntSig.SNARK_SCALAR_FIELD):
        if isinstance(modulus, FQ):
            modulus = modulus.m
        return FQ(1, modulus)

    @classmethod
    def random(cls, modulus=IntSig.SNARK_SCALAR_FIELD):
        if isinstance(modulus, FQ):
            modulus = modulus.m

        nbytes = ceil(ceil(log2(modulus)) / 8) + 1
        rand_n = int.from_bytes(urandom(nbytes), "little")
        return FQ(rand_n, modulus)

    @classmethod
    def zero(self, modulus=IntSig.SNARK_SCALAR_FIELD):
        if isinstance(modulus, FQ):
            modulus = modulus.m
        return FQ(0, modulus)

    def _validate_n(self, other):
        """Check number's modulus and type"""

        if isinstance(other, FQ):
            if other.m != self.m:
                raise RuntimeError("Other field element has different modulus")

            return other.n

        if not isinstance(other, int_types):
            raise RuntimeError(f"Not a valid value type: {type(other).__name__}")

        return other

    def bits(self):
        # TODO: endian
        nbits = ceil(log2(self.m))
        bits = bin(self.n)[2:][::-1].ljust(nbits, "0")

        return bitstring.BitArray("0b" + bits)

    def exp(self, e):
        e = self._validate_n(e)
        self._count("exp")

        return FQ(pow(self.n, e, self.m), self.m)

    def inv(self):
        self._count("inv")

        return FQ(pow(self.n, self.m - 2, self.m), self.m)

    def sqrt(self):
        self._count("sqrt")

        return FQ(square_root_mod_prime(self.n, self.m), self.m)

    def to_bytes(self, endian="big"):
        nbits = ceil(log2(self.m))
        nbits += 8 - (nbits % 8)
        nbytes = nbits // 8

        return self.n.to_bytes(nbytes, endian)


class FR(FQ):

    def __init__(self, n, field_modulus=IntSig.FR_ORDER):
        FQ.__init__(self, n, field_modulus)
