"""Tuya Smart Watering component."""

from __future__ import annotations

from datetime import datetime
from functools import cached_property
import json
import logging
from typing import Literal
import uuid

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, CONF_ID, CONF_TOKEN, URL_API, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DATA_COOLDOWN, DATA_MODE, DATA_SWITCH, DOMAIN, UPDATE_LISTENER
from .signature import Signature

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SELECT]
_LOGGER = logging.getLogger(__name__)


async def async_setup(
    _hass: HomeAssistant,
    _config_entry: ConfigEntry,
) -> bool:
    """Set up Integration Name."""
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Set up Integration Name entry."""

    _LOGGER.info("Setting up %s ", config_entry.unique_id)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.unique_id] = DataUpdater(
        hass=hass,
        logger=_LOGGER,
        name=f"{DOMAIN}_updater",
        config_entry=config_entry,
    )

    await hass.data[DOMAIN][config_entry.unique_id].async_config_entry_first_refresh()
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)

    update_listener = config_entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][config_entry.entry_id][UPDATE_LISTENER] = update_listener


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update options for entry that was configured via user interface."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove entry configured via user interface."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        update_listener = hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
        update_listener()
        hass.data[DOMAIN].pop(entry.entry_id)
        result = True
    else:
        result = False

    return result


class DataUpdater(DataUpdateCoordinator):
    """Data Updater for the integration."""

    __token_expire: float

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        name: str,
        config_entry: ConfigEntry,
    ):
        """Initialize updater."""
        super().__init__(hass, logger, name=name)
        self._config_entry = config_entry
        self.__access_token = None
        self.__token_expire = 0

    @cached_property
    def config(self) -> dict:
        """Return the configuration."""
        config = dict(self._config_entry.data)
        config.update(self._config_entry.options)
        return config

    @cached_property
    def device_id(self) -> str:
        """Tuya device ID."""
        return self.config[CONF_DEVICE]

    @cached_property
    def client_id(self) -> str:
        """Tuya API client ID."""
        return self.config[CONF_ID]

    @cached_property
    def server(self) -> str:
        """Tuya API server name."""
        return self.config[URL_API]

    @cached_property
    def _secret(self):
        """Tuya API secret."""
        return self.config[CONF_TOKEN]

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

    async def _async_update_data(self) -> dict:
        """Fetch the latest data from the source."""

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"https://{self.server}/v1.0/devices/{self.device_id}/status"
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

    async def request(
        self, session: aiohttp.ClientSession, url: str, access_token: str = ""
    ) -> dict:
        """Make request to API."""
        _LOGGER.info(f"Sending API request to {url}")

        async with session.get(
            url, headers=self.headers(url=url, access_token=access_token)
        ) as response:
            try:
                assert response.status == 200
                _LOGGER.debug(f"{await response.text()}")
            except AssertionError as e:
                _LOGGER.error(f"Could not get data from API: {response}")
                raise aiohttp.ClientError(response.status, await response.text()) from e

            return json.loads(await response.text())
