"""This module implements JWK representing Elliptic Curve keys."""

from __future__ import annotations

from typing import Any, List, Mapping, Union

from binapy import BinaPy
from cryptography.hazmat.primitives import asymmetric

from jwskate.jwa import (
    ES256,
    ES256K,
    ES384,
    ES512,
    P_256,
    P_384,
    P_521,
    EcdhEs,
    EcdhEs_A128KW,
    EcdhEs_A192KW,
    EcdhEs_A256KW,
    EllipticCurve,
    secp256k1,
)

from .base import Jwk, JwkParameter


class UnsupportedEllipticCurve(KeyError):
    """Raised when an unsupported Elliptic curve is requested."""


class ECJwk(Jwk):
    """Represent an Elliptic Curve Jwk, with `kty=EC`."""

    KTY = "EC"

    CRYPTOGRAPHY_KEY_CLASSES = (
        asymmetric.ec.EllipticCurvePrivateKey,
        asymmetric.ec.EllipticCurvePublicKey,
    )

    PARAMS: Mapping[str, JwkParameter] = {
        "crv": JwkParameter("Curve", is_private=False, is_required=True, kind="name"),
        "x": JwkParameter(
            "X Coordinate", is_private=False, is_required=True, kind="b64u"
        ),
        "y": JwkParameter(
            "Y Coordinate", is_private=False, is_required=True, kind="b64u"
        ),
        "d": JwkParameter(
            "ECC Private Key", is_private=True, is_required=True, kind="b64u"
        ),
    }

    CURVES: Mapping[str, EllipticCurve] = {
        curve.name: curve for curve in [P_256, P_384, P_521, secp256k1]
    }

    SIGNATURE_ALGORITHMS = {
        sigalg.name: sigalg for sigalg in [ES256, ES384, ES512, ES256K]
    }

    KEY_MANAGEMENT_ALGORITHMS = {
        keyalg.name: keyalg
        for keyalg in [EcdhEs, EcdhEs_A128KW, EcdhEs_A192KW, EcdhEs_A256KW]
    }

    def _validate(self) -> None:
        if not isinstance(self.crv, str) or self.crv not in self.CURVES:
            raise UnsupportedEllipticCurve(self.crv)
        super()._validate()

    @classmethod
    def get_curve(cls, crv: str) -> EllipticCurve:
        """Get the EllipticCurve instance for a given curve identifier.

        Args:
          crv: the curve identifier

        Returns:
            the matching EllipticCurve instance

        Raises:
            UnsupportedEllipticCurve: if the curve identifier is not supported
        """
        curve = cls.CURVES.get(crv)
        if curve is None:
            raise UnsupportedEllipticCurve(crv)
        return curve

    @property
    def curve(self) -> EllipticCurve:
        """Get the EllipticCurve instance for this key.

        Returns:
            the EllipticCurve instance
        """
        return self.get_curve(self.crv)

    @classmethod
    def public(cls, crv: str, x: int, y: int, **params: str) -> "ECJwk":
        """Initialize a public ECJwk from its public parameters.

        Args:
          crv: the curve to use
          x: the x coordinate
          y: the y coordinate
          **params: additional member to include in the Jwk

        Returns:
          an ECJwk initialized with the supplied parameters
        """
        coord_size = cls.get_curve(crv).coordinate_size
        return cls(
            dict(
                key="EC",
                crv=crv,
                x=BinaPy.from_int(x, length=coord_size).encode_to("b64u"),
                y=BinaPy.from_int(y, length=coord_size).encode_to("b64u"),
                **params,
            )
        )

    @classmethod
    def private(cls, crv: str, x: int, y: int, d: int, **params: Any) -> "ECJwk":
        """Initialize a private ECJwk from its private parameters.

        Args:
          crv: the curve to use
          x: the x coordinate
          y: the y coordinate
          d: the elliptic curve private key
          **params: additional members to include in the JWK

        Returns:
          an ECJWk initialized with the supplied parameters
        """
        coord_size = cls.get_curve(crv).coordinate_size
        return cls(
            dict(
                kty="EC",
                crv=crv,
                x=BinaPy.from_int(x, coord_size).encode_to("b64u").decode(),
                y=BinaPy.from_int(y, coord_size).encode_to("b64u").decode(),
                d=BinaPy.from_int(d, coord_size).encode_to("b64u").decode(),
                **params,
            )
        )

    @property
    def coordinate_size(self) -> int:
        """The coordinate size to use with the key curve.

        Returns:
          32, 48, or 66 (bits)
        """
        return self.curve.coordinate_size

    @classmethod
    def from_cryptography_key(cls, key: Any) -> ECJwk:
        """Initialize an ECJwk from a `cryptography` key.

        Args:
          key: `cryptography` key

        Returns:
            an ECJwk initialized from the provided `cryptography` key
        """
        parameters = EllipticCurve.get_jwk_parameters(key)
        return cls(parameters)

    def to_cryptography_key(
        self,
    ) -> Union[
        asymmetric.ec.EllipticCurvePrivateKey,
        asymmetric.ec.EllipticCurvePublicKey,
    ]:
        """Initialize a `cryptography` key based on this Jwk.

        Returns:
            an EllipticCurvePublicKey or EllipticCurvePrivateKey
        """
        if self.is_private:
            return asymmetric.ec.EllipticCurvePrivateNumbers(
                private_value=self.ecc_private_key,
                public_numbers=asymmetric.ec.EllipticCurvePublicNumbers(
                    x=self.x_coordinate,
                    y=self.y_coordinate,
                    curve=self.curve.cryptography_curve,
                ),
            ).private_key()
        else:
            return asymmetric.ec.EllipticCurvePublicNumbers(
                x=self.x_coordinate,
                y=self.y_coordinate,
                curve=self.curve.cryptography_curve,
            ).public_key()

    @classmethod
    def generate(cls, crv: str = "P-256", **params: str) -> "ECJwk":
        """Generates a random ECJwk.

        Args:
          crv: the curve to use
          **params:

        Returns:
          a generated ECJwk

        Raises:
            UnsupportedEllipticCurve: if the provided curve identifier is not supported.
        """
        curve = cls.get_curve(crv)
        if curve is None:
            raise UnsupportedEllipticCurve(crv)
        x, y, d = curve.generate()
        return cls.private(
            crv=crv,
            x=x,
            y=y,
            d=d,
            **params,
        )

    @property
    def x_coordinate(self) -> int:
        """Return the x coordinate from this ECJwk.

        Returns:
         the x coordinate (from parameter `x`)
        """
        return BinaPy(self.x).decode_from("b64u").to_int()

    @property
    def y_coordinate(self) -> int:
        """Return the y coordinate from this ECJwk.

        Returns:
            the y coordinate (from parameter `y`)
        """
        return BinaPy(self.y).decode_from("b64u").to_int()

    @property
    def ecc_private_key(self) -> int:
        """Return the ECC private key from this ECJwk.

        Returns:
             the ECC private key (from parameter `d`)
        """
        return BinaPy(self.d).decode_from("b64u").to_int()

    def supported_signing_algorithms(self) -> List[str]:
        """Return the list of supported signature algorithms for this key.

        Returns:
            a list of supported algorithms identifiers
        """
        return [
            name
            for name, alg in self.SIGNATURE_ALGORITHMS.items()
            if alg.curve == self.curve
        ]

    def supported_key_management_algorithms(self) -> List[str]:
        """Return the list of supported Key Management algorithms for this key.

        Returns:
             a list of supported algorithms identifiers
        """
        return list(self.KEY_MANAGEMENT_ALGORITHMS)

    def supported_encryption_algorithms(self) -> List[str]:
        """Return the list of support Encryption algorithms for this key.

        Returns:
             a list of supported algorithms identifiers
        """
        return list(self.ENCRYPTION_ALGORITHMS)
