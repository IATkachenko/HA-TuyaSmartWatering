"""Tuya Smart Watering component."""

from __future__ import annotations

import aiohttp
import json
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .const import DOMAIN, UPDATE_LISTENER, DATA_MODE, DATA_SWITCH, DATA_COOLDOWN

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

    @property
    def device_id(self) -> str:
        raise NotImplementedError

    @property
    def client_id(self) -> str:
        raise NotImplementedError

    @property
    def server(self) -> str:
        raise NotImplementedError

    @property
    def _access_token(self):
        raise NotImplementedError

    @staticmethod
    def map_code_value(data: dict) -> dict:
        """Map list with coded values to dict"""
        result = {}
        for element in data:
            result[element["code"]] = element["value"]
        return result

    async def _async_update_data(self) -> dict:
        """Fetch the latest data from the source."""

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = await self.request(
                session=session,
                url=f"https://{self.server}/v1.0/devices/{self.device_id}/status"
            )
            r = self.map_code_value(json.loads(response)["result"])
            return {
                DATA_SWITCH: r["switch"],
                DATA_MODE: r["mode"],
                DATA_COOLDOWN: r["temp_set"],
            }
    @staticmethod
    def encrypt(data: str = ""):
        if data == "":
            return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        return sha256(data)

    def get_sign(self, data) -> str:
        # https://developer.tuya.com/en/docs/iot/singnature?id=Ka43a5mtx1gsc
        data.update({
            "method": "GET"
        })
        stringToSign = f"{data["client_id"]}{data["t"]}{self.uuid}GET" \
                       "{self.encrypt(data='')}"
        
        return "4A89B047504BEF31798E6172242A34C31A10AF5B1AF518CD3D0957CEB213510B"

    @property
    def _headers(self) -> dict:
        headers = {
                   "sign_method": "HMAC-SHA256",
                   "client_id": self.client_id,
                   "t": 1656350916747,
                   "mode": "cors",
                   "Content-Type": "application/json",
                   "access_token": self._access_token,
        }
        headers.update({"sign": self.get_sign(headers)})
        return headers

    async def request(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ):
        """
        Make request to API endpoint.

        :param session: aiohttp.ClientSession: HTTP session for request
        :param url: url to query

        :returns: dict with response data
        :raises AssertionError: when response.status is not 200
        """

        _LOGGER.info(f"Sending API request to {url}")
        async with session.get(url, headers=self._headers) as response:
            try:
                assert response.status == 200
                _LOGGER.debug(f"{await response.text()}")
            except AssertionError as e:
                _LOGGER.error(f"Could not get data from API: {response}")
                raise aiohttp.ClientError(response.status, await response.text()) from e

            return await response.text()
