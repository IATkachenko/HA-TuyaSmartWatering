"""Switch component."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DataUpdater
from .const import DATA_SWITCH, DOMAIN, UPDATER

_LOGGER = logging.getLogger(__name__)

SWITCHES: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(
        key=DATA_SWITCH,
        name="State",
        device_class=SwitchDeviceClass.SWITCH,
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up weather "Yandex.Weather" sensor entry."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    updater = domain_data[UPDATER]

    entities: list[TuyaSmartWateringSwitch] = [
        TuyaSmartWateringSwitch(
            unique_id="{config_entry.unique_id}-{description.key}",
            updater=updater,
            description=description,
        )
        for description in SWITCHES
    ]
    async_add_entities(entities)


class TuyaSmartWateringSwitch(SwitchEntity, CoordinatorEntity):
    def turn_off(self, **kwargs: Any) -> None:
        pass

    def turn_on(self, **kwargs: Any) -> None:
        pass

    async def async_turn_on(self, **kwargs: Any) -> None:
        pass

    async def async_turn_off(self, **kwargs: Any) -> None:
        pass

    def __init__(
        self, unique_id: str, updater: DataUpdater, description: SwitchEntityDescription
    ):
        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_device_info = self.coordinator.device_info

    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.coordinator.data.get(self.entity_description.key)
        self.async_write_ha_state()
