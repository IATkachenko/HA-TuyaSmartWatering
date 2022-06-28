"""Tuya signing module."""
from hashlib import sha256
import hmac
from typing import Literal


class Signature:
    """Tuya signing."""

    @staticmethod
    def _encrypt(data: str = "") -> str:
        if data == "":
            return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        return sha256(data.encode("utf-8")).hexdigest()

    def get_sign(
        self,
        client_id: str,
        secret: str,
        timestamp: int,
        uuid: str,
        method: Literal["GET", "PUT", "POST"],
        request: str,
        access_token: str = "",
        body: str = "",
        parameters: dict[str, str] | None = None,
    ):
        """Sign a request."""
        # https://developer.tuya.com/en/docs/iot/singnature?id=Ka43a5mtx1gsc
        if parameters is None:
            parameters = {}

        string = (
            f"{client_id}{access_token}{timestamp}{uuid}{method}\n{self._encrypt(body)}"
        )
        for k, v in parameters.items():
            string += f"\n{k}:{v}"
        string += f"\n\n{request}"

        return (
            hmac.new(
                key=secret.encode("utf-8"), msg=string.encode("utf-8"), digestmod=sha256
            )
            .hexdigest()
            .upper()
        )
