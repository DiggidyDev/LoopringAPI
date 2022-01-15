from collections import namedtuple
from math import floor, log2

from pyblake2 import blake2b

from ....enums import IntSig

PoseidonParamsStruct = namedtuple("PoseidonParams",
    (
        "p",
        "t",
        "n_rounds_f",
        "n_rounds_p",
        "seed",
        "e",
        "constants_C",
        "constants_M"
    )
)


def H(arg):
    if isinstance(arg, int):
        arg = arg.to_bytes(32, "little")

    hashed = blake2b(data=arg, digest_size=32).digest()
    return int.from_bytes(hashed, "little")


def poseidon_constants(p, seed, n: int):
    for _ in range(n):
        seed = H(seed)

        yield seed % p


def poseidon_matrix(p, seed, t):
    c = list(poseidon_constants(p, seed, t * 2))
    return [
        [pow((c[i] - c[t + j]) % p, p - 2, p) for j in range(t)] for i in range(t)
        ]


def poseidon_params(p,
                t,
                n_rounds_f,
                n_rounds_p,
                seed: bytes,
                e,
                constants_C=None,
                constants_M=None,
                security=None
                ) -> PoseidonParamsStruct:

    assert n_rounds_f % 2 == 0 and n_rounds_f > 0
    assert n_rounds_p > 0
    assert t >= 2

    n = floor(log2(p))
    M = n if not security else security

    assert n >= M

    if p % 2 == 3:
        assert e == 3

        grobner_attack_ratio_rounds = 0.32
        grobner_attack_ratio_sboxes = 0.18
        interpolation_attack_ratio = 0.63

    elif p % 5 != 1:
        assert e == 5

        grobner_attack_ratio_rounds = 0.21
        grobner_attack_ratio_sboxes = 0.14
        interpolation_attack_ratio = 0.43
    
    else:
        raise ValueError("Invalid p for congruency")
    
    assert (n_rounds_f + n_rounds_p) > ((interpolation_attack_ratio * min(n, M)) + log2(t))
    assert (n_rounds_f + n_rounds_p) > ((2 + min(M, n)) * grobner_attack_ratio_rounds)
    assert (n_rounds_f + (t * n_rounds_p)) > (M * grobner_attack_ratio_sboxes)

    if not constants_C:
        constants_C = list(poseidon_constants(p, seed + b"_constants", n_rounds_f + n_rounds_p))
    if not constants_M:
        constants_M = poseidon_matrix(p, seed + b"_matrix_0000", t)
    
    n_constraints = (n_rounds_f * t) + n_rounds_p

    if e == 5:
        n_constraints *= 3
    elif e == 3:
        n_constraints *= 2
    
    return PoseidonParamsStruct(p, t, n_rounds_f, n_rounds_p, seed, e, constants_C, constants_M)


default_params = poseidon_params(
    IntSig.SNARK_SCALAR_FIELD,
    6,
    8, 
    57,
    b"poseidon",
    5,
    security=126
)


def poseidon(inputs, params: PoseidonParamsStruct=default_params, chained: bool=False, trace: bool=False):
    assert len(inputs) > 0

    if not chained:
        assert len(inputs) < params.t

    state = [0] * params.t
    state[:len(inputs)] = inputs

    for i, C_i in enumerate(params.constants_C):
        state = [_ + C_i for _ in state]

        poseidon_sbox(state, i, params)

        state = poseidon_mix(state, params.constants_M, params.p)

        if trace:
            for j, val in enumerate(state):
                print(f"{i} {j} = {val}")

    if chained:
        return state

    return state[0]


def poseidon_mix(state, M, p):
    return [ sum([M[i][j] * _ for j, _ in enumerate(state)]) % p
        for i in range(len(M)) ]


def poseidon_sbox(state, i, params: PoseidonParamsStruct):
    half_f = params.n_rounds_f // 2
    e, p = params.e, params.p
    if i < half_f or i >= (half_f + params.n_rounds_p):
        for j, _ in enumerate(state):
            state[j] = pow(_, e, p)
    
    else:
        state[0] = pow(state[0], e, p)
