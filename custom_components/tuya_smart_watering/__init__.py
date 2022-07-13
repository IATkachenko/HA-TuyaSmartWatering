"""Tuya Smart Watering component."""

from __future__ import annotations

import datetime
import json
from asyncio import Future

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

from .const import DOMAIN, UPDATE_LISTENER, UPDATER, DATA_SWITCH, DATA_MODE, DATA_COOLDOWN, DATA_PUMP, DATA_ONLINE

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
            name=config[CONF_NAME],
            config_entry=config_entry,
            api=tuya_api_instance,
    )
    hass.data[DOMAIN][config_entry.entry_id] = {
        UPDATER: updater,
        UPDATE_LISTENER: config_entry.add_update_listener(async_update_options)
    }

    updater.setup_mq(tuya_api_instance)
    await updater.async_config_entry_first_refresh()
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
        super().__init__(hass, logger, name=name, update_interval=datetime.timedelta(minutes=30))

        self._config_entry = config_entry
        self._api = api
        self._specification = {}
        self.data = {
            DATA_PUMP: None,
            DATA_COOLDOWN: 0,
        }

        hass.async_add_executor_job(
            self._api.get,
            f"/v1.0/iot-03/devices/{self.config[CONF_DEVICE]}/specification"
        ).add_done_callback(self.set_specification)

    async def _async_update_data(self) -> _T:
        self._update()

    def _update(self):
        self.hass.async_add_executor_job(
            self._api.get,
            f"/v1.0/iot-03/devices/{self.config[CONF_DEVICE]}/status",
        ).add_done_callback(self.set_data)

        self.hass.async_add_executor_job(
            self._api.get,
            f"/v1.1/iot-03/devices/{self.config[CONF_DEVICE]}",
        ).add_done_callback(self.set_state)

        self.hass.async_add_executor_job(
            self._api.get,
            f"/v1.0/iot-03/devices/{self.config[CONF_DEVICE]}/capabilities/level"
        ).add_done_callback(self.set_pump_state)

        self.hass.async_add_executor_job(
            self._api.get,
            f"/v1.0/iot-03/devices/{self.config[CONF_DEVICE]}/capabilities/ClockTime"
        ).add_done_callback(self.set_cooldown_state)

    def set_cooldown_state(self, state: Future):
        initial_data = self.data or {}
        state = state.result()
        _LOGGER.debug(f"{state=}")
        try:
            result = {DATA_COOLDOWN: state["result"][0]["value"]}
            self.async_set_updated_data({**initial_data, **result})
        except KeyError:
            _LOGGER.critical(f"KeyError in set_initial_state with {state=}")

    def set_pump_state(self, state: Future):
        initial_data = self.data or {}
        state = state.result()
        _LOGGER.debug(f"{state=}")
        try:
            result = {DATA_PUMP: state["result"][0]["value"]}
            self.async_set_updated_data({**initial_data, **result})
        except KeyError:
            _LOGGER.critical(f"KeyError in set_initial_state with {state=}")

    def set_state(self, state: Future):
        initial_data = self.data or {}
        state = state.result()

        try:
            result = {DATA_ONLINE: state["result"]["online"]}
            self.async_set_updated_data({**initial_data, **result})
        except KeyError:
            _LOGGER.critical(f"KeyError in set_initial_state with {state=}")

    def set_specification(self, specification: Future):
        self._specification = specification.result()["result"]["status"]

    def set_data(self, data: Future):
        mapped_data = {}
        initial_data = self.data or {}
        data = data.result()["result"]
        for element in data:
            mapped_data[element["code"]] = element["value"]

        result = {
            DATA_SWITCH: mapped_data["switch"],
            DATA_MODE: mapped_data["mode"],
        }

        self.async_set_updated_data({**initial_data, **result})

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
        if msg['data']['devId'] != self.config[CONF_DEVICE]:
            _LOGGER.debug(f"Skipping. This is not my update. My device id is {self.config[CONF_DEVICE]}, "
                          f"but update for {msg['data']['devId']}")
            return

        data = self.data
        _LOGGER.debug(f"{msg=}")
        if 'bizCode' in msg['data'].keys():
            if msg['data']['bizCode'] == 'offline':
                data[DATA_ONLINE] = False
            elif msg['data']['bizCode'] == 'online':
                data[DATA_ONLINE] = True
        elif "status" not in msg["data"].keys():
            _LOGGER.debug(f"Skipping: status not in keys of {msg=}.")
            return

        try:
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
                    # cooldown_codes = ["56", "102"]
                    cooldown_codes = ["102"]
                    for i in cooldown_codes:
                        if i in status.keys():
                            data[DATA_COOLDOWN] = status[i]

                    if "28" in status.keys():
                        data[DATA_PUMP] = status["28"]
        except KeyError:
            _LOGGER.warning(f"have no status in msg['data']")

        self.async_set_updated_data(data)

    def setup_mq(self, api: TuyaOpenAPI):
        tuya_mq = TuyaOpenMQ(api)
        tuya_mq.start()
        tuya_mq.add_message_listener(self.on_message)

    def set_pump(self, pump: str):
        _LOGGER.debug(f"Need set {pump=}.")
        self.hass.async_add_executor_job(
            self._api.post,
            f"/v1.0/iot-03/devices/{self.config[CONF_DEVICE]}/capabilities/level",
            {"value": pump},
        )

    def set_mode(self, mode: str):
        _LOGGER.debug(f"Need set {mode=}.")
        self.send_commands(json.dumps([{"code": "mode", "value": mode}]))

    def turn_on(self):
        _LOGGER.debug(f"Need turn on.")
        self.send_commands(json.dumps([{"code": "switch", "value": True}]))

    def turn_off(self):
        _LOGGER.debug(f"Need turn off.")
        self.send_commands(json.dumps([{"code": "switch", "value": False}]))

    def set_cooldown(self, cooldown: float):
        cooldown = int(cooldown)
        _LOGGER.debug(f"Need set {cooldown=}.")
        self.hass.async_add_executor_job(
            self._api.post,
            f"/v1.0/iot-03/devices/{self.config[CONF_DEVICE]}/capabilities/runtime", {"value": cooldown},
        )

    def send_commands(self, commands: str):
        _LOGGER.debug(f"Sending {commands=}")
        self.hass.async_add_executor_job(
            self._api.post,
            f"/v1.0/devices/{self.config[CONF_DEVICE]}/commands",
            {"commands": commands},
        )
