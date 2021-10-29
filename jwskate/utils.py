import base64
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union


def b64_encode(
    data: Union[bytes, str], encoding: str = "utf-8", padded: bool = True
) -> str:
    """
    Encodes the string or bytes `data` using Base64.
    If `data` is a string, encode it to bytes using `encoding` before converting it to Base64.
    If `padded` is `True` (default), outputs includes a padding with `=` to make its length a multiple of 4. If `False`,
    no padding is included.
    :param data: value to base64-encode.
    :param encoding: if `data` is a `str`, use this encoding to convert it to `bytes` first.
    :param padded: whether to include padding in the output
    :return: a `str` with the base64-encoded data.
    """
    if not isinstance(data, bytes):
        if not isinstance(data, str):
            data = str(data)
        data = data.encode(encoding)

    encoded = base64.b64encode(data)
    if not padded:
        encoded = encoded.rstrip(b"=")
    return encoded.decode("ascii")


def b64_decode(data: Union[str, bytes]) -> bytes:
    """
    Decodes a base64-encoded string or bytes.
    :param data: the data to base64-decode
    :return: the decoded data, as bytes
    """
    if not isinstance(data, bytes):
        if not isinstance(data, str):
            data = str(data)
        data = data.encode("ascii")

    padding_len = len(data) % 4
    if padding_len:
        data = data + b"=" * padding_len

    decoded = base64.urlsafe_b64decode(data)
    return decoded


def b64u_encode(
    data: Union[bytes, str], encoding: str = "utf-8", padded: bool = False
) -> str:
    """
    Encodes some data using Base64url.
    If `data` is a string, encode it to bytes using `encoding` before converting it to Base64.
    If `padded` is `False` (default), no padding is added. If `True`, outputs includes a padding with `=` to make
    its length a multiple of 4.
    :param data: the data to encode.
    :param encoding: if `data` is a string, the encoding to use to convert it to `bytes`
    :param padded: if `True`, pad the output with `=` to make its length a multiple of 4
    :return: the base64url encoded data, as a string
    """
    if not isinstance(data, bytes):
        if not isinstance(data, str):
            data = str(data)
        data = data.encode(encoding)

    encoded = base64.urlsafe_b64encode(data)
    if not padded:
        encoded = encoded.rstrip(b"=")
    return encoded.decode("ascii")


def b64u_decode(
    data: Union[str, bytes],
) -> bytes:
    """
    Decodes a base64url-encoded data.
    :param data: the data to decode.
    :return: the decoded data as bytes.
    """
    if not isinstance(data, bytes):
        if not isinstance(data, str):
            data = str(data)
        data = data.encode("ascii")

    padding_len = len(data) % 4
    if padding_len:
        data = data + b"=" * padding_len

    decoded = base64.urlsafe_b64decode(data)
    return decoded


def _default_json_encode(data: Any) -> Any:
    if isinstance(data, datetime):
        return int(data.timestamp())
    return str(data)


def json_encode(
    obj: Any,
    compact: bool = True,
    default_encoder: Callable[[Any], Any] = _default_json_encode,
) -> str:
    """
    Encodes a dict to a JSON string. By default, this produces a compact output (no extra whitespaces), and datetimes are
    converted to epoch-style integers. Any unhandled value is stringified using `str()`. You can override this with the
    parameters `compact` and `default_encoder`.
    :param obj: the data to JSON-encode.
    :param compact: if `True` (default), produces a compact output.
    :param default_encoder: the default encoder to use for types that the default `json` module doesn't handle.
    :return: the JSON-encoded data.
    """
    separators = (",", ":") if compact else (", ", ": ")

    return json.dumps(obj, separators=separators, default=default_encoder)


def json_decode(s: Union[bytes, str]) -> Dict[str, Any]:
    """
    Decodes a string representation of a JSON into a dict.
    """
    obj = json.loads(s)
    if not isinstance(obj, dict):
        raise ValueError("This is not a JSON object")
    return obj


def b64u_encode_json(
    j: Dict[str, Any], encoder: Callable[[Dict[str, Any]], str] = json_encode
) -> str:
    encoded_json = encoder(j)
    return b64u_encode(encoded_json)


def b64u_decode_json(
    b64: Union[bytes, str],
    decoder: Callable[[Union[str, bytes]], Dict[str, Any]] = json_decode,
) -> Dict[str, Any]:
    encoded_json = b64u_decode(b64)
    return decoder(encoded_json)


def int_to_bytes(i: int, length: Optional[int] = None) -> bytes:
    if length is None:
        length = (i.bit_length() + 7) // 8
    data = i.to_bytes(length, "big", signed=False)
    return data


def int_to_b64u(i: int, length: Optional[int] = None) -> str:
    """
    Encodes an integer to the base64url encoding of the octet string representation of that integer, as defined in
    Section 2.3.5 of SEC1 [SEC1].
    :param i: the integer to encode
    :param length: the length of the encoding (left padding the integer if necessary)
    :return: the encoded representation
    """
    data = int_to_bytes(i, length)
    return b64u_encode(data)


def b64u_to_int(b: str) -> int:
    """
    Decodes a base64url encoding of the octet string representation of an integer.
    :param b: the encoded integer
    :return: the decoded integer
    """
    return int.from_bytes(b64u_decode(b), "big", signed=False)
