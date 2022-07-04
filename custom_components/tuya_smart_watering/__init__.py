"""Tuya Smart Watering component."""

from __future__ import annotations

from datetime import timedelta
from functools import cached_property
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE,
    CONF_ID,
    CONF_NAME,
    CONF_TOKEN,
    URL_API,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, UPDATE_LISTENER, UPDATER
from .tuya_api import TuyaApi

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SELECT, Platform.NUMBER]
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
) -> bool:
    """Set up Integration Name entry."""

    _LOGGER.info(f"Setting up {config_entry.unique_id=} ", )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        UPDATER: DataUpdater(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_updater",
            config_entry=config_entry,
        ),
        UPDATE_LISTENER: config_entry.add_update_listener(async_update_options)
    }

    await hass.data[DOMAIN][config_entry.entry_id][UPDATER].async_config_entry_first_refresh()
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)

    return True


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

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        name: str,
        config_entry: ConfigEntry,
    ):
        """Initialize updater."""
        super().__init__(hass, logger, name=name, update_interval=timedelta(seconds=10))

        self._config_entry = config_entry
        self.tuya = TuyaApi(
            client_id=self.config[CONF_ID],
            secret=self.config[CONF_TOKEN],
            server=self.config[URL_API],
        )

    @cached_property
    def config(self) -> dict:
        """Return the configuration."""
        config = dict(self._config_entry.data)
        config.update(self._config_entry.options)
        return config

    async def _async_update_data(self) -> dict:
        """Fetch the latest data from the source."""

        return await self.tuya.status(self.config[CONF_DEVICE])

    @property
    def device_info(self):
        """Device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self.config[CONF_DEVICE])},
            manufacturer="Tuya",
            name=self.config[CONF_NAME],
        )
