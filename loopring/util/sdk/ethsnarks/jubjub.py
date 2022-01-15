from abc import ABC, abstractmethod
from collections import namedtuple
from hashlib import sha256
from os import urandom

from ...enums import IntSig
from ..errors import SquareRootError
from .field import FQ



try:
    FQ(IntSig.JUBJUB_A).sqrt()
except SquareRootError:
    raise RuntimeError("JUBJUB_A is required to be a square.")

try:
    FQ(IntSig.JUBJUB_D).sqrt()
    raise RuntimeError("JUBJUB_D is required to be non-square.")
except SquareRootError:
    pass



assert IntSig.MONT_A24 * 4 == IntSig.MONT_A + 2
assert IntSig.JUBJUB_A == (IntSig.MONT_A + 2) / IntSig.MONT_B
assert IntSig.JUBJUB_D == (IntSig.MONT_A - 2) / IntSig.MONT_B


_EtecPoint = namedtuple("_EtecPoint", ("x", "y", "t", "z"))
_MontPoint = namedtuple("_MontPoint", ("u", "v"))
_Point = namedtuple("_Point", ("x", "y"))
_ProjPoint = namedtuple("_ProjPoint", ("x", "y", "z"))



def is_negative(value):
    assert isinstance(value, FQ)

    return value.n > (-value).n


# Might need `mult_naf()`


def mult_naf_lut(point, scalar, width=2):
    a = point.infinity()
    w = naf_window(point, width)

    for k_i in wNAF(scalar, width):
        a = a.double()
        p = w[k_i]
        
        if p:
            a = a.add(p)
    
    return a


def naf_window(point, nbits):
    a = (1 << nbits) // 2
    res = {0: None}

    for n in list(range(0, a))[1:]:
        if n == 1:
            p_n = point
        elif n == 2:
            p_n = point.double()
        elif n > 2 and n % 2 == 0:
            continue
        else:
            p_n = res[n-2] + res[2]
        
        res[n] = p_n
        res[-n] = -p_n
    
    return res


def wNAF(k: int, width=2):
    a = 2 ** width
    b = 2 ** (width-1)
    output = []

    while k > 0:
        if k % 2 == 1:
            c = k % a

            if c > b:
                k_i = c - a
            else:
                k_i = c
            
            k = k - k_i
        else:
            k_i = 0
        
        output.append(k_i)
        k //= 2

    return output[::-1]


class CurveOps(ABC):

    def __add__(self, other):
        return self.add(other)

    def __mul__(self, n):
        return self.mult(n)

    def __neg__(self):
        return self.neg()

    def __new__(cls, *args, **kwargs):
        abstractmethods = getattr(cls, '__abstractmethods__', None)
        if abstractmethods:
            msg = "Can't instantiate abstract class {name} with abstract method{suffix} {methods}"
            suffix = 's' if len(abstractmethods) > 1 else ''
            raise TypeError(msg.format(name=cls.__name__, suffix=suffix, methods=', '.join(abstractmethods)))
        return super().__new__(cls, *args, **kwargs)

    def __sub__(self, other):
        return self.add(other.neg())

    @abstractmethod
    def add(self):
        pass
    
    @abstractmethod
    def as_point(self):
        pass

    @abstractmethod
    def neg(self):
        pass

    @classmethod
    def all_loworder_points(cls):
        return [
            Point(FQ(0), FQ(1)),
            Point(FQ(0), FQ(21888242871839275222246405745257275088548364400416034343698204186575808495616)),
            Point(FQ(2957874849018779266517920829765869116077630550401372566248359756137677864698), FQ(0)),
            Point(FQ(4342719913949491028786768530115087822524712248835451589697801404893164183326), FQ(4826523245007015323400664741523384119579596407052839571721035538011798951543)),
            Point(FQ(4342719913949491028786768530115087822524712248835451589697801404893164183326), FQ(17061719626832259898845741003733890968968767993363194771977168648564009544074)),
            Point(FQ(17545522957889784193459637215142187266023652151580582754000402781682644312291), FQ(4826523245007015323400664741523384119579596407052839571721035538011798951543)),
            Point(FQ(17545522957889784193459637215142187266023652151580582754000402781682644312291), FQ(17061719626832259898845741003733890968968767993363194771977168648564009544074)),
            Point(FQ(18930368022820495955728484915491405972470733850014661777449844430438130630919), FQ(0))
        ]
    
    @classmethod
    def decompress(cls, point):
        return Point.decompress(point).as_proj()

    def compress(self):
        return self.as_point().compress()

    def double(self):
        return self.add(self)
    
    def is_negative(self):
        return is_negative(self.as_point().x)

    def mult(self, scalar):
        if isinstance(scalar, FQ):
            if scalar.m not in [IntSig.SNARK_SCALAR_FIELD, IntSig.JUBJUB_E, IntSig.JUBJUB_L]:
                raise ValueError("Invalid field modulus.")
            scalar = scalar.n
        
        p = self
        a = self.infinity()
        i = 0

        while scalar != 0:
            if (scalar & 1) != 0:
                a = a.add(p)
            
            p = p.double()
            scalar //= 2
            i += 1
        
        return a
    
    def mult_wnaf(self, scalar, window=5):
        return mult_naf_lut(self, scalar, window)

    def rescale(self):
        return self
    
    def sign(self):
        return 1 if self.is_negative() else 0


class EtecPoint(CurveOps, _EtecPoint):

    def __eq__(self, other):
        return self.x == other.x and \
            self.y == other.y and \
            self.t == other.t and \
            self.z == other.z
    
    def __hash__(self):
        return hash((self.x, self.y, self.t, self.z))

    @staticmethod
    def infinity():
        return EtecPoint(FQ(0), FQ(1), FQ(0), FQ(1))

    def add(self, other: "EtecPoint"):
        if self == self.infinity():
            return other
        
        assert self.z != 0 and other.z != 0

        x1x2 = self.x * other.x
        y1y2 = self.y * other.y
        dt1t2 = (IntSig.JUBJUB_D * self.t) * other.t
        z1z2 = self.z * other.z
        e = ((self.x + self.y) * (other.x + other.y)) - x1x2 - y1y2
        f = z1z2 - dt1t2
        g = z1z2 + dt1t2
        h = y1y2 - (IntSig.JUBJUB_A * x1x2)

        return EtecPoint(e*f, g*h, e*h, f*g)

    def as_etec(self):
        return self
    
    def as_mont(self):
        return self.as_point().as_mont()
    
    def as_point(self):
        inv_z = self.z.inv()
        return Point(self.x*inv_z, self.y*inv_z)
    
    def as_proj(self):
        return ProjPoint(self.x, self.y, self.z)
    
    def double(self):
        if self == self.infinity():
            return self.infinity()

        a = self.x * self.x
        b = self.y * self.y
        t0 = self.z * self.z
        c = t0 * 2
        d = IntSig.JUBJUB_A * a
        t1 = self.x + self.y
        t2 = t1 * t1
        t3 = t2 - a
        e = t3 - b
        g = d + b
        f = g - c
        h = d - b

        return EtecPoint(e*f, g*h, e*h, f*g)

    def neg(self):
        return EtecPoint(-self.x, self.y, -self.t, self.z)
    
    def valid(self):
        return self.as_point().valid()


class MontPoint(CurveOps, _MontPoint):

    def __eq__(self, other):
        return self.u == other.u and self.v == other.v
    
    def __hash__(self):
        return hash((self.u, self.v))

    @classmethod
    def from_edwards(cls, e):
        e = e.as_point()

        if e.y == FQ.one():
            return MontPoint(FQ.zero(), FQ.one())
        if e.x == FQ.zero():
            return MontPoint(FQ.zero(), FQ.zero())
        
        u = (FQ.one() + e.y) / (FQ.one() - e.y)
        v = u / e.x

        return cls(u, v)

    @classmethod
    def infinity(cls):
        return cls(FQ(0), FQ(1))
    
    def add(self, other):
        other = other.as_mont()
        infinity = self.infinity()

        if other == infinity:
            return self
        elif self == infinity:
            return other
        
        if self.u == other.u:
            if self.v == other.v:
                return self.double()
            
            return infinity
        
        delta = (other.v - self.v) / (other.u - self.u)
        x3 = (delta * delta) - IntSig.MONT_A - self.u - other.u
        y3 = -((x3 - self.u) * delta + self.v)

        return type(self)(x3, y3)
    
    def as_etec(self):
        return self.as_point().as_etec()
    
    def as_mont(self):
        return self
    
    def as_proj(self):
        return self.as_point().as_proj()

    def as_point(self):
        x = self.u / self.v
        y = (self.u - 1) / (self.u + 1)

        return Point(x, y)

    def double(self):
        if self.v == FQ.zero():
            return self.infinity()
        
        usq = self.u * self.u
        delta = (1 + (2 * (IntSig.MONT_A * self.u)) + usq + (usq * 2)) / (2 * self.v)
        x3 = (delta * delta) - IntSig.MONT_A - (2*self.u)
        y3 = -((x3 - self.u) * delta + self.v)

        return type(self)(x3, y3)
    
    def neg(self):
        return type(self)(self.u, -self.v)
    
    def valid(self):
        lhs = IntSig.MONT_B * (self.v ** 2)
        rhs = (self.u ** 3) + IntSig.MONT_A * (self.u ** 2) + self.u

        return lhs == rhs


class Point(CurveOps, _Point):

    x: FQ
    y: FQ
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))

    def __str__(self):
        return " ".join([f"{_}" for _ in self])
    
    @classmethod
    def decompress(cls, point):
        if len(point) != 32:
            raise ValueError("Invalid input length for decompression")
        
        y = int.from_bytes(point, "little")
        sign = y >> 255
        y &= (1 << 255) - 1

        return cls.from_y(FQ(y), sign)

    @classmethod
    def from_hash(cls, entropy: bytes) -> "Point":
        entropy = sha256(entropy).digest()
        entropy_as_int = int.from_bytes(entropy, "big")
        y = FQ(entropy_as_int)

        while True:
            try:
                p = cls.from_y(y)
            except SquareRootError:
                y += 1
                continue
                
            p *= IntSig.JUBJUB_C

            if (p * IntSig.JUBJUB_L) != Point.infinity():
                raise RuntimeError("Point not on prime-ordered subgroup")
            
            return p

    @classmethod
    def from_x(cls, x: FQ):
        """y^2 = ((a * x^2) / (d * x^2 - 1)) - (1 / (d * x^2 - 1))"""

        assert x.m == IntSig.JUBJUB_Q
        xsq = x * x
        ax2 = IntSig.JUBJUB_A * xsq
        dxsqm1 = (IntSig.JUBJUB_D * xsq - 1).inv()  # TODO: .inv() doesn't exist?
        ysq = dxsqm1 * (ax2 - 1)
        y = ysq.sqrt()

        return cls(x, y)

    @classmethod
    def from_y(cls, y: FQ, sign=None):
        """x^2 = (y^2 - 1) / (d * y^2 - a)"""

        assert y.m == IntSig.JUBJUB_Q

        ysq = y * y
        lhs = ysq - 1
        rhs = (IntSig.JUBJUB_D * ysq - IntSig.JUBJUB_A)
        xsq = lhs / rhs
        x = xsq.sqrt()

        if sign:
            if is_negative(x) ^ (sign != 0):
                x = -x
        
        else:
            if is_negative(x):
                x = -x
        
        return cls(x, y)
    
    @classmethod
    def generator(cls):
        x = 16540640123574156134436876038791482806971768689494387082833631921987005038935
        y = 20819045374670962167435360035096875258406992893633759881276124905556507972311
        return Point(FQ(x), FQ(y))
    
    @classmethod
    def random(cls):
        return cls.from_hash(urandom(32))
    
    @staticmethod
    def infinity():
        return Point(FQ(0), FQ(1))

    def add(self, other: "Point"):
        if self.x == 0 and self.y == 0:
            return other
        
        u1, v1 = self.x, self.y
        u2, v2 = other.x, other.y
        u3 = (u1*v2 + v1*u2) / (FQ.one() + IntSig.JUBJUB_D * u1*u2 * v1*v2)
        v3 = (v1*v2 - IntSig.JUBJUB_A*u1*u2) / (FQ.one() - IntSig.JUBJUB_D * u1*u2 * v1*v2)

        return Point(u3, v3)
    
    def as_etec(self):
        return EtecPoint(self.x, self.y, self.x*self.y, FQ(1))
    
    def as_mont(self):
        return MontPoint.from_edwards(self)
    
    def as_point(self):
        return self
    
    def as_proj(self):
        return ProjPoint(self.x, self.y, FQ(1))

    def compress(self):
        x = self.x
        y = self.y.n

        return int.to_bytes(y | (is_negative(x) << 255), 32, "little")
    
    def neg(self):
        return Point(-self.x, self.y)
    
    def valid(self):
        xsq = self.x * self.x
        ysq = self.y * self.y
        return (IntSig.JUBJUB_A * xsq) + ysq == (1 + IntSig.JUBJUB_D * xsq * ysq)


class ProjPoint(CurveOps, _ProjPoint):
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z
    
    def __hash__(self):
        return hash((self.x, self.y, self.z))

    @staticmethod
    def infinity():
        return ProjPoint(FQ(0), FQ(1), FQ(1))

    def add(self, other: "ProjPoint"):
        if self == self.infinity():
            return other
        
        a = self.z * other.z
        b = a * a
        c = self.x * other.x
        d = self.y * other.y
        t0 = c*d
        e = IntSig.JUBJUB_D * t0
        f = b - e
        g = b + e
        t1 = self.x + self.y
        t2 = other.x + other.y
        t3 = t1 * t2
        t4 = t3 - c
        t5 = t4 - d
        t6 = f * t5
        x3 = a * t6
        t7 = IntSig.JUBJUB_A * c
        t8 = d - t7
        t9 = g * t8
        y3 = a * t9
        z3 = f * g

        return ProjPoint(x3, y3, z3)

    def as_etec(self):
        return EtecPoint(self.x, self.y, self.x*self.y, self.z)

    def as_mont(self):
        return self.as_point().as_mont()
    
    def as_point(self):
        assert self.z != 0
        inv_z = self.z.inv()

        return Point(self.x*inv_z, self.y*inv_z)

    def as_proj(self):
        return self
	
    def double(self):
        if self == self.infinity():
            return self.infinity()

        t0 = self.x + self.y
        b = t0 * t0
        c = self.x * self.x
        d = self.y * self.y
        e = IntSig.JUBJUB_A * c
        f = e + d
        h = self.z * self.z
        t1 = 2 * h
        j = f - t1
        t2 = b - c
        t3 = t2 - d
        x3 = t3 * j
        t4 = e - d
        y3 = f * t4
        z3 = f * j

        return ProjPoint(x3, y3, z3)
    
    def neg(self):
        return ProjPoint(-self.x, self.y, self.z)

    def rescale(self):
        return ProjPoint(self.x/self.z, self.y/self.z, FQ(1))
    
    def valid(self):
        return self.as_point().valid()
