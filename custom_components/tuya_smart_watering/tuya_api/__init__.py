"""API for Tuya services."""

from datetime import datetime
from functools import cache, cached_property
import json
import logging
from typing import Literal

import aiohttp

from ..const import DATA_COOLDOWN, DATA_MODE, DATA_SWITCH
from .signature import Signature

_LOGGER = logging.getLogger(__name__)


class TuyaApi:
    """Main class for interact with Tuya services."""

    __token_expire: float
    _schema: dict

    def __init__(self, client_id: str, secret: str, server: str):
        """Initialize API."""
        self.client_id = client_id
        self._secret = secret
        self.server = server

        self.__access_token: str | None = None
        self.__token_expire = 0

        self._timeout = aiohttp.ClientTimeout(total=20)
        self._schema = {}

    def headers(
        self,
        request: str,
        access_token: str = "",
        method: Literal["GET", "PUT", "POST"] = "GET",
    ):
        """Headers for request."""
        now = int(datetime.now().timestamp() * 1000)

        return {
            "client_id": self.client_id,
            "t": str(now),
            "sign_method": "HMAC-SHA256",
            "mode": "cors",
            "Content-Type": "application/json",
            "sign": Signature.get_sign(
                access_token=access_token,
                client_id=self.client_id,
                method=method,
                timestamp=now,
                uuid="",
                secret=self._secret,
                request=request,
            ),
            "access_token": access_token,
        }

    async def request(
        self,
        session: aiohttp.ClientSession,
        server: str,
        request: str,
        access_token: str = "",
    ) -> dict:
        """Make request to API."""
        url = f"{server}{request}"
        _LOGGER.info(f"Sending API request to {url}")

        async with session.get(
            url=url,
            headers=self.headers(request=request, access_token=access_token),
        ) as response:
            try:
                assert response.status == 200
                _LOGGER.debug(f"{await response.text()}")
            except AssertionError as e:
                _LOGGER.error(f"Could not get data from API: {response}")
                raise aiohttp.ClientError(response.status, await response.text()) from e

            result = json.loads(await response.text())
            if result["success"]:
                return result["result"]
            else:
                _LOGGER.critical(f"Could not update token: {response}")
                print(result)
                raise RuntimeError(result["msg"])

    async def _access_token(self):
        """Get access token for request."""

        if datetime.utcnow().timestamp() < self.__token_expire:
            return self.__access_token

        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            response = await self.request(
                session=session,
                server=f"https://{self.server}",
                request="/v1.0/token?grant_type=1&terminal_id=100",
            )
            self.__access_token = response["access_token"]
            self.__token_expire = (
                response["expire_time"] + datetime.utcnow().timestamp()
            )
            return self.__access_token

    @staticmethod
    def map_code_value(data: dict) -> dict:
        """Map list with coded values to dict."""
        result = {}
        for element in data:
            result[element["code"]] = element["value"]
        return result

    async def status(self, device_id: str):
        """Get status of device."""

        if self._schema == {}:
            self._schema = await self._update_schema(device_id=device_id)

        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            r = self.map_code_value(
                await self.request(
                    session=session,
                    server=f"https://{self.server}",
                    request=f"/v1.0/iot-03/devices/{device_id}/status",
                    access_token=(await self._access_token()),
                )
            )
        result = {
            DATA_SWITCH: r["switch"],
            DATA_MODE: r["mode"],
            DATA_COOLDOWN: r["temp_set"],
        }
        _LOGGER.debug(f"status is {result}")
        return result

    @property
    def schema(self) -> dict:
        return self._schema

    async def _update_schema(self, device_id: str):
        """Device data schema layout."""
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            return (
                await self.request(
                    session=session,
                    server=f"https://{self.server}",
                    request=f"/v1.0/iot-03/devices/{device_id}/specification",
                    access_token=(await self._access_token()),
                )
            )["status"]
