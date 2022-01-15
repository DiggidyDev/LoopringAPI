try:
    from sha3 import keccak_256  # pysha3
except ImportError:
    from Crypto.Hash import keccak  # pycryptodome
    keccak_256 = lambda *args: keccak.new(*args, digest_bits=256)
