"""Tuya Smart Watering component."""

from __future__ import annotations

from homeassistant.exceptions import ConfigEntryNotReady

from tuya_iot import TuyaOpenAPI, TuyaOpenMQ, AuthType, TUYA_LOGGER
from functools import cached_property
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE,
    CONF_ID,
    CONF_NAME,
    CONF_TOKEN,
    URL_API,
    Platform, CONF_USERNAME, CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, UPDATE_LISTENER, UPDATER
from .tuya_api import TuyaApi

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SELECT, Platform.NUMBER]
_LOGGER = logging.getLogger(__name__)
# TUYA_LOGGER.setLevel(logging.DEBUG)


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
    updater = DataUpdater(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_updater",
            config_entry=config_entry,
    )
    hass.data[DOMAIN][config_entry.entry_id] = {
        UPDATER: updater,
        UPDATE_LISTENER: config_entry.add_update_listener(async_update_options)
    }
    hass.data[DOMAIN][config_entry.entry_id][UPDATER]: DataUpdater

    # await updater.async_config_entry_first_refresh()
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)

    config = dict(config_entry.data)
    config.update(config_entry.options)

    tuya_api_instance = TuyaOpenAPI(
        endpoint=f"https://{config[URL_API]}",
        access_id=config[CONF_ID],
        access_secret=config[CONF_TOKEN],
        auth_type=AuthType.SMART_HOME,
    )
    response = await hass.async_add_executor_job(
        tuya_api_instance.connect,
        config[CONF_USERNAME],
        config[CONF_PASSWORD],
        "RU",
        "smartlife",
    )

    if response.get("success", False) is False:
        raise ConfigEntryNotReady(response)

    updater.setup_mq(tuya_api_instance)
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
        super().__init__(hass, logger, name=name)

        self._config_entry = config_entry
        self.tuya = TuyaApi(
            client_id=self.config[CONF_ID],
            secret=self.config[CONF_TOKEN],
            server=self.config[URL_API],
        )
        self.data = self._async_update_data()

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

    @callback
    def on_message(self, msg):
        _msg = {
            'data': {
                'dataId': '54572faf-4c51-40e2-a2de-849ca075df49',
                'devId': 'bf8ae7a397ff27335eoxaj',
                'productKey': 'abzzvtulukkwzynv',
                'status': [
                    {'1': True, 'code': 'switch', 't': '1656947179', 'value': True}
                ]
            },
            'protocol': 4,
            'pv': '2.0',
            'sign': '125bf4fc214f55e349198cbfecdffa58',
            't': 1656947179,
        }

        _LOGGER.debug(f"{msg=}")

    def setup_mq(self, api: TuyaOpenAPI):
        tuya_mq = TuyaOpenMQ(api)
        # tuya_mq.start()
        tuya_mq.add_message_listener(self.on_message)
