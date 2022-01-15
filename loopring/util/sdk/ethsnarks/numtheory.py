from ..errors import *



def jacobi(a, n):
    assert n >= 3
    assert n % 2 == 1

    a = a % n
    if not a:
        return 0
    if a == 1:
        return 1
    
    a1, e = a, 0
    while a1 % 2 == 0:
        a1, e = a1 // 2, e + 1
    
    s = -1
    if e % 2 == 0 or n % 8 in (1, 7):
        s = 1
    
    if a1 == 1:
        return s

    if n % 4 == 3 and a1 % 4 == 3:
        s = -s
    
    return s * jacobi(n % a1, a1)


def modular_exp(base, exp, mod):
    if exp < 0:
        raise NegativeExponentError(f"Negative exponents ({exp}) not allowed")

    return pow(base, exp, mod)


def polynomial_exp_mod(base, exp, pmod, p):
    assert exp < p

    if not exp: return [1]

    G = base
    k = exp
    if k % 2 == 1:
        s = G
    else:
        s = [1]
    
    while k > 1:
        k //= 2
        G = polynomial_multiply_mod(G, G, pmod, p)

        if k % 2 == 1:
            s = polynomial_multiply_mod(G, s, pmod, p)
    
    return s


def polynomial_multiply_mod(m1, m2, pmod, p):
    prod = (len(m1) + len(m2) - 1) * [0]

    for i in range(len(m1)):
        for j in range(len(m2)):
            prod[i + j] = (prod[i + j] + m1[i] * m2[j]) % p
    
    return polynomial_reduce_mod(prod, pmod, p)


def polynomial_reduce_mod(poly, pmod, p):
    assert pmod[-1] == 1
    assert len(pmod) > 1

    while len(poly) >= len(pmod):
        if poly[-1] != 0:
            for i in range(2, len(pmod) + 1):
                poly[-i] = (poly[-i] - poly[-1] * pmod[-i]) % p
        poly = poly[:-1]
    
    return poly


def square_root_mod_prime(a, p):

    if not a:
        return 0
    if p == 2:
        return a
    
    jac = jacobi(a, p)

    if jac == -1:
        raise SquareRootError(f"{a} has no square root modulo {p}")
    
    if p % 4 == 3:
        return modular_exp(a, (p+1) // 4, p)
    
    if p % 8 == 5:
        d = modular_exp(a, (p-1) // 4, p)
        if d == 1:
            return modular_exp(a, (p+3) // 8, p)
        
        if d == p-1:
            return (2 * a * modular_exp(4*a, (p-5) // 8, p)) % p
        
        raise SDKError("Something's gone wrong :)")
    
    for b in range(2, p):
        if jacobi(b*b - 4*a, p) == -1:
            f = (a, -b, 1)
            ff = polynomial_exp_mod((0, 1), (p+1) // 2, f, p)

            assert ff[1] == 0

            return ff[0]
    
    raise SDKError("No b found.")
