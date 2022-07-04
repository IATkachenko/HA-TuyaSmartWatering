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
from homeassistant.components.tuya import DOMAIN as TUYA_DOMAIN

from .const import DOMAIN, UPDATE_LISTENER, UPDATER, DATA_SWITCH, DATA_MODE, DATA_COOLDOWN, DATA_PUMP

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SELECT, Platform.NUMBER]
_LOGGER = logging.getLogger(__name__)
#TUYA_LOGGER.setLevel(logging.DEBUG)


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
    config = dict(config_entry.data)
    config.update(config_entry.options)

    tuya_api_instance = TuyaOpenAPI(
        endpoint=f"https://{config[URL_API]}",
        access_id=config[CONF_ID],
        access_secret=config[CONF_TOKEN],
        auth_type=AuthType.SMART_HOME, )
    response = await hass.async_add_executor_job(
        tuya_api_instance.connect,
        config[CONF_USERNAME],
        config[CONF_PASSWORD],
        "RU",
        "smartlife",
    )
    if response.get("success", False) is False:
        raise ConfigEntryNotReady(response)

    hass.data.setdefault(DOMAIN, {})
    updater = DataUpdater(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_updater",
            config_entry=config_entry,
            api=tuya_api_instance,
    )
    hass.data[DOMAIN][config_entry.entry_id] = {
        UPDATER: updater,
        UPDATE_LISTENER: config_entry.add_update_listener(async_update_options)
    }

    updater.setup_mq(tuya_api_instance)
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
        api: TuyaOpenAPI
    ):
        """Initialize updater."""
        super().__init__(hass, logger, name=name)

        self._config_entry = config_entry
        self._api = api
        self._specification = {}

        hass.async_add_executor_job(
            self._api.get,
            f"/v1.0/iot-03/devices/{self.config[CONF_DEVICE]}/specification"
        ).add_done_callback(self.set_specification)

        hass.async_add_executor_job(
            self._api.get,
            f"/v1.0/iot-03/devices/{self.config[CONF_DEVICE]}/status",
        ).add_done_callback(self.set_initial_data)

    def set_specification(self, specification):
        self._specification = specification.result()["result"]["status"]

    def set_initial_data(self, data):
        mapped_data = {}
        data = data.result()["result"]
        for element in data:
            mapped_data[element["code"]] = element["value"]

        result = {
            DATA_SWITCH: mapped_data["switch"],
            DATA_MODE: mapped_data["mode"],
            DATA_COOLDOWN: mapped_data["temp_set"],
            DATA_PUMP: None,
        }
        self.async_set_updated_data(result)

    @property
    def specification(self) -> dict:
        return self._specification

    @cached_property
    def config(self) -> dict:
        """Return the configuration."""
        config = dict(self._config_entry.data)
        config.update(self._config_entry.options)
        return config

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
    def on_message(self, msg: dict):
        _LOGGER.debug(f"{msg=}")
        if msg['data']['devId'] != self.config[CONF_DEVICE]:
            _LOGGER.debug(f"Skipping. My device id is {self.config[CONF_DEVICE]}")
            return

        data = self.data
        for status in msg["data"]["status"]:
            _LOGGER.debug(f"{status=}")
            try:
                if status["code"] == "switch":
                    data[DATA_SWITCH] = status["value"]
                elif status['code'] == "mode":
                    data[DATA_MODE] = status["value"]
                elif status['code'] == "temp_set":
                    data[DATA_COOLDOWN] = status["value"]
                else:
                    _LOGGER.warning(f"Unknown code! {status=}")
            except KeyError:
                status: dict
                if "56" in status.keys():
                    data[DATA_COOLDOWN] = status["56"]
                if "28" in status.keys():
                    data[DATA_PUMP] = status["28"]

        self.async_set_updated_data(data)

    def setup_mq(self, api: TuyaOpenAPI):
        tuya_mq = TuyaOpenMQ(api)
        tuya_mq.start()
        tuya_mq.add_message_listener(self.on_message)

    def set_pump(self, pump: str):
        _LOGGER.debug(f"Need set {pump=}")

    def set_mode(self, mode: str):
        _LOGGER.debug(f"Need set {mode=}")

    def turn_on(self):
        _LOGGER.debug(f"Need turn on")

    def turn_off(self):
        _LOGGER.debug(f"Need turn off")

    def set_cooldown(self, cooldown: float):
        cooldown = int(cooldown)
        _LOGGER.debug(f"Need set {cooldown=}")
