"""API for Tuya services."""

from datetime import datetime
import json
import logging
from typing import Literal
import uuid

import aiohttp

from ..const import DATA_COOLDOWN, DATA_MODE, DATA_SWITCH
from .signature import Signature

_LOGGER = logging.getLogger(__name__)


class TuyaApi:
    """Main class for interact with Tuya services."""

    __token_expire: float

    def __init__(self, client_id: str, secret: str, server: str):
        """Initialize API."""
        self.client_id = client_id
        self._secret = secret
        self.server = server

        self.__access_token: str | None = None
        self.__token_expire = 0

    def headers(
        self,
        url: str,
        access_token: str = "",
        method: Literal["GET", "PUT", "POST"] = "GET",
    ):
        """Headers for request."""
        now = int(datetime.utcnow().timestamp())
        s = Signature()
        return {
            "client_id": self.client_id,
            "t": now,
            "sign_method": "HMAC-SHA256",
            "mode": "cors",
            "Content-Type": "application/json",
            "sign": s.get_sign(
                access_token=access_token,
                client_id=self.client_id,
                method=method,
                timestamp=now,
                uuid=uuid.uuid4().hex,
                secret=self._secret,
                request=url,
            ),
            "access_token": access_token,
        }

    async def _access_token(self):
        """Get access token for request."""

        if datetime.utcnow().timestamp() < self.__token_expire:
            return self.__access_token

        url = f"https://{self.server}/v1.0/token?grant_type=1&terminal_id=100"
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = await self.request(
                session=session,
                url=url,
            )
            if response["success"]:
                r = response["result"]
                self.__access_token = r["access_token"]
                self.__token_expire = r["expire_time"] + datetime.utcnow().timestamp()
                return self.__access_token
            _LOGGER.critical(f"Could not update token: {response}")
            raise RuntimeError

    @staticmethod
    def map_code_value(data: dict) -> dict:
        """Map list with coded values to dict."""
        result = {}
        for element in data:
            result[element["code"]] = element["value"]
        return result

    async def request(
        self, session: aiohttp.ClientSession, url: str, access_token: str = ""
    ) -> dict:
        """Make request to API."""
        _LOGGER.info(f"Sending API request to {url}")

        async with session.get(
            url=url, headers=self.headers(url=url, access_token=access_token)
        ) as response:
            try:
                assert response.status == 200
                _LOGGER.debug(f"{await response.text()}")
            except AssertionError as e:
                _LOGGER.error(f"Could not get data from API: {response}")
                raise aiohttp.ClientError(response.status, await response.text()) from e

            return json.loads(await response.text())

    async def status(self, device_id: str):
        """Get status of device."""

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"https://{self.server}/v1.0/devices/{device_id}/status"
            r = self.map_code_value(
                await self.request(
                    session=session,
                    url=url,
                    access_token=(await self._access_token()),
                )
            )["result"]
        return {
            DATA_SWITCH: r["switch"],
            DATA_MODE: r["mode"],
            DATA_COOLDOWN: r["temp_set"],
        }
