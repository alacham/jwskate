import secrets
from typing import Iterable, List, Optional, Tuple, Union

from cryptography.hazmat.primitives import hashes, hmac, keywrap
from cryptography.hazmat.primitives.ciphers import aead

from ..utils import b64u_decode, b64u_encode
from .alg import get_alg, get_algs
from .base import Jwk


class SymmetricJwk(Jwk):
    """
    Implement Symetric keys, with `"kty": "oct"`.
    """

    kty = "oct"
    PARAMS = {
        # name: ("Description", is_private, is_required, "kind"),
        "k": ("Key Value", True, True, "b64u"),
    }

    SIGNATURE_ALGORITHMS = {
        # name: (MAC, alg, min_key_size)
        "HS256": (hmac.HMAC, hashes.SHA256(), 256),
        "HS384": (hmac.HMAC, hashes.SHA384(), 384),
        "HS512": (hmac.HMAC, hashes.SHA512(), 512),
    }

    KEY_MANAGEMENT_ALGORITHMS = {
        # name: ("Description", wrap_method, unwrap_method, key_size)
        "A128KW": (
            "AES Key Wrap with default initial value using 128-bit key",
            keywrap.aes_key_wrap,
            keywrap.aes_key_unwrap,
            128,
        ),
        "A192KW": (
            "AES Key Wrap with default initial value using 192-bit key",
            keywrap.aes_key_wrap,
            keywrap.aes_key_unwrap,
            192,
        ),
        "A256KW": (
            "AES Key Wrap with default initial value using 256-bit key",
            keywrap.aes_key_wrap,
            keywrap.aes_key_unwrap,
            256,
        ),
    }

    ENCRYPTION_ALGORITHMS = {
        # name: (description, alg, key_size, iv_size, tag_size),
        "A128CBC-HS256": ("AES_128_CBC_HMAC_SHA_256", aead.AESCCM, 128, 96, 16),
        "A192CBC-HS384": ("AES_192_CBC_HMAC_SHA_384", aead.AESCCM, 192, 96, 24),
        "A256CBC-HS512": ("AES_128_CBC_HMAC_SHA_256", aead.AESCCM, 256, 96, 32),
        "A128GCM": ("AES GCM using 128-bit key", aead.AESGCM, 128, 96, 16),
        "A192GCM": ("AES GCM using 192-bit key", aead.AESGCM, 192, 96, 16),
        "A256GCM": ("AES GCM using 256-bit key", aead.AESGCM, 256, 96, 16),
    }

    def public_jwk(self) -> "Jwk":
        raise ValueError("Symmetric keys don't have a public key")

    @classmethod
    def from_bytes(cls, k: Union[bytes, str], **params: str) -> "SymmetricJwk":
        """
        Initializes a SymmetricJwk from a raw secret key.
        The provided secret key is encoded and used as the `k` parameter for the returned SymetricKey.
        :param k: the key to use
        :param params: additional parameters for the returned Jwk
        :return: a SymmetricJwk
        """
        return cls(dict(key="oct", k=b64u_encode(k), **params))

    @classmethod
    def generate(cls, size: int = 128, **params: str) -> "SymmetricJwk":
        """
        Generates a random SymmetricJwk, with a given key size.
        :param size: the size of the generated key, in bytes.
        :param params: additional parameters for the returned Jwk
        :return: a SymmetricJwk with a random key
        """
        key = secrets.token_bytes(size)
        return cls.from_bytes(key, **params)

    @classmethod
    def generate_for_alg(cls, alg: str, **params: str) -> "SymmetricJwk":
        if alg in cls.SIGNATURE_ALGORITHMS:
            _, _, min_key_size = cls.SIGNATURE_ALGORITHMS[alg]
            return cls.generate(min_key_size, alg=alg, **params)
        if alg in cls.ENCRYPTION_ALGORITHMS:
            _, _, key_size, _, _ = cls.ENCRYPTION_ALGORITHMS[alg]
            return cls.generate(key_size, alg=alg, **params)
        raise ValueError("Unsupported alg", alg)

    @property
    def key(self) -> bytes:
        """
        Returns the raw symmetric key.
        :return: the key from the `k` parameter, base64u-decoded.
        """
        return b64u_decode(self.k)

    @property
    def key_size(self) -> int:
        return len(self.key) * 8

    def sign(self, data: bytes, alg: Optional[str] = None) -> bytes:
        alg = get_alg(self.alg, alg, self.supported_signing_algorithms)

        try:
            mac, hashalg, min_key_size = self.SIGNATURE_ALGORITHMS[alg]
        except KeyError:
            raise ValueError("Unsupported signing alg", alg)

        m = mac(self.key, hashalg)
        m.update(data)
        signature = m.finalize()
        return signature

    def verify(
        self,
        data: bytes,
        signature: bytes,
        alg: Optional[str] = None,
        algs: Optional[Iterable[str]] = None,
    ) -> bool:
        for alg in get_algs(self.alg, alg, algs, self.supported_signing_algorithms):
            try:
                mac, hashalg, min_key_size = self.SIGNATURE_ALGORITHMS[alg]
            except KeyError:
                raise ValueError("Unsupported signing alg", alg)

            m = mac(self.key, hashalg)
            m.update(data)
            candidate_signature = m.finalize()
            if signature == candidate_signature:
                return True

        return False

    def encrypt(
        self,
        plaintext: bytes,
        aad: Optional[bytes] = None,
        alg: Optional[str] = None,
        iv: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes, bytes]:
        alg = get_alg(self.alg, alg, self.supported_encryption_algorithms)

        (
            description,
            alg_class,
            key_size,
            iv_size,
            tag_size,
        ) = self.ENCRYPTION_ALGORITHMS[alg]

        if self.key_size != key_size:
            raise ValueError(
                f"This key size of {self.key_size} doesn't match the expected keysize for {description} of {key_size} bits"
            )

        if iv is None:
            iv = secrets.token_bytes(iv_size)

        alg_key = alg_class(self.key)
        cyphertext_with_tag = alg_key.encrypt(iv, plaintext, aad)
        cyphertext = cyphertext_with_tag[:-tag_size]
        tag = cyphertext_with_tag[-tag_size:]

        return cyphertext, tag, iv

    def decrypt(
        self,
        cyphertext: bytes,
        tag: bytes,
        iv: bytes,
        aad: Optional[bytes] = None,
        alg: Optional[str] = None,
    ) -> bytes:
        alg = get_alg(self.alg, alg, self.supported_encryption_algorithms)

        (
            description,
            alg_class,
            key_size,
            iv_size,
            tag_size,
        ) = self.ENCRYPTION_ALGORITHMS[alg]

        if self.key_size != key_size:
            raise ValueError(
                f"This key size of {self.key_size} doesn't match the expected keysize for {description} of {key_size} bits"
            )

        alg_key = alg_class(self.key)
        cyphertext_with_tag = cyphertext + tag
        plaintext: bytes = alg_key.decrypt(iv, cyphertext_with_tag, aad)

        return plaintext

    def wrap_key(self, key: bytes, alg: Optional[str] = None) -> bytes:
        alg = get_alg(self.alg, alg, self.supported_key_management_algorithms)

        (
            description,
            wrap_method,
            unwrap_method,
            key_size,
        ) = self.KEY_MANAGEMENT_ALGORITHMS[alg]

        if self.key_size != key_size:
            raise ValueError(
                f"This key size of {self.key_size} doesn't match the expected keysize for {description} of {key_size} bits"
            )

        cypherkey = wrap_method(self.key, key)
        return cypherkey

    def unwrap_key(self, cypherkey: bytes, alg: Optional[str] = None) -> bytes:
        alg = get_alg(self.alg, alg, self.supported_key_management_algorithms)

        (
            description,
            wrap_method,
            unwrap_method,
            key_size,
        ) = self.KEY_MANAGEMENT_ALGORITHMS[alg]

        if self.key_size != key_size:
            raise ValueError(
                f"This key size of {self.key_size} doesn't match the expected keysize for {description} of {key_size} bits"
            )

        plaintext = unwrap_method(self.key, cypherkey)
        return plaintext
