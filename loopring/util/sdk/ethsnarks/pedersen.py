from bitstring import BitArray

from .jubjub import Point, EtecPoint


def pedersen_hash_basepoint(name, i):
    if not isinstance(name, bytes):
        if isinstance(name, str):
            name = name.encode("ascii")
        else:
            raise TypeError("Name is not in a byte-friendly type")
        
    if i < 0 or i > 0xFFFF:
        raise ValueError("Invalid sequence number")
    if len(name) > 28:
        raise ValueError("Name too long")
    
    data = b"%-28s%04X" % (name, i)

    return Point.from_hash(data).as_etec()


def pedersen_hash_bits(name, bits):

    if isinstance(bits, BitArray):
        bits = bits.bin
    
    windows = [int(bits[i:i+3][::-1], 2) for i in range(0, len(bits), 3)]
    assert len(windows) > 0

    return pedersen_hash_windows(name, windows)


def pedersen_hash_bytes(name, data: bytes):
    assert len(data) > 0

    bits = "".join([bin(_)[2:].rjust(8, "0") for _ in data])

    return pedersen_hash_bits(name, bits)


def pedersen_hash_windows(name, windows):
    n_windows = 62
    result = EtecPoint.infinity()

    for j, window in enumerate(windows):
        if j % n_windows == 0:
            current = pedersen_hash_basepoint(name, j // n_windows)

        j %= n_windows

        if j != 0:
            current = current.double().double().double().double()
        segment = current  * ((window & 0b11) + 1)

        if window > 0b11:
            segment = segment.neg()
        
        result += segment
    
    return result.as_point()
