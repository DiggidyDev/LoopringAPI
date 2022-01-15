import hashlib
import json
import urllib.parse

from aiohttp import ClientResponse
from pyblake2 import blake2b

from ...enums import Endpoints, IntSig, StrSig
from ...request import Request
from ..ethsnarks.eddsa import PoseidonEdDSA, PureEdDSA, Signature, _SignatureScheme
from ..ethsnarks.field import FQ
from ..ethsnarks.poseidon import poseidon, poseidon_params


class EDDSASign:

    def __init__(self, poseidon_sign_param, private_key: str="0x1"):
        self.poseidon_sign_param = poseidon_sign_param
        self.private_key = FQ(int(private_key, 16))

        assert self.private_key != FQ.zero()
    
    def hash(self, data):
        serialised_data = self.serialise(data)
        msg_hash = poseidon(serialised_data, self.poseidon_sign_param)
        
        return msg_hash 
    
    def sign(self, data):
        msg_hash = self.hash(data)
        signed_msg = PoseidonEdDSA.sign(msg_hash, self.private_key)

        return "0x" + "".join([
            hex(int(signed_msg.sig.R.x))[2:].zfill(64),
            hex(int(signed_msg.sig.R.y))[2:].zfill(64),
            hex(int(signed_msg.sig.s))[2:].zfill(64)
        ])
    
    def sig_str_to_signature(self, sig):
        assert len(sig) == 194
        pure_hex = sig[2:]
        return Signature(
            [
                int(pure_hex[:64], 16),
                int(pure_hex[64:128], 16)
            ],
            int(pure_hex[128:], 16)
        )
    
    def serialise(self, data):
        pass

    def verify(self, msg, sig):
        return PoseidonEdDSA.verify(sig.A, sig.sig, sig.msg)


class DummyEDDSA(EDDSASign):

    def __init__(self, private_key):
        super().__init__(
            poseidon_sign_param=poseidon_params(
                IntSig.SNARK_SCALAR_FIELD, 2, 6, 53, b"poseidon", 5, security=128
            ),
            private_key=private_key
        )
    
    def serialise(self, dummy):
        return [
            int(dummy["data"])
        ]


class UrlEDDSASign(EDDSASign):

    def __init__(self, private_key, host: str=""):
        self.host = host
        super().__init__(
            poseidon_sign_param=poseidon_params(
                IntSig.SNARK_SCALAR_FIELD, 2, 6, 53, b"poseidon", 5, security=128
            ),
            private_key=private_key
        )
    
    def hash(self, data):
        serialised_data = self.serialise(data)
        hasher = hashlib.sha256()
        hasher.update(serialised_data.encode("utf-8"))
        msg_hash = int(hasher.hexdigest(), 16) % IntSig.SNARK_SCALAR_FIELD

        return msg_hash
    
    def serialise(self, request: Request):
        method = request.method
        host = self.host or request.host

        assert host.startswith(("http://", "https://"))

        path = request.path
        params = request.params
        payload = request.payload


        url = urllib.parse.quote(host + path, safe="")

        if method in ["GET", "DELETE"]:
            data = urllib.parse.quote(
                "&".join([f"{k}={urllib.parse.quote(str(v), safe='')}" for 
                k, v in params.items()]), safe=""
                )
        elif method in ["POST", "PUT"]:
            assert payload is not None

            data = urllib.parse.quote(
                json.dumps(payload, separators=(",", ":")), safe=""
            )
        else:
            raise Exception(f"Unknown request method: {repr(method)}")
        
        return "&".join([method, url, data])


class OrderEDDSASign(EDDSASign):

    def __init__(self, private_key):
        super().__init__(
            poseidon_params(
                IntSig.SNARK_SCALAR_FIELD, 12, 6, 53, b"poseidon", 5, security=128
            ),
            private_key=private_key
        )
    
    def serialise(self, order):
        return [

        ]


