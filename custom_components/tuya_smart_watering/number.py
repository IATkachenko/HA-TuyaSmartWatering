"""Switch component."""

from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DataUpdater
from .const import DATA_COOLDOWN, DOMAIN, UPDATE_LISTENER

_LOGGER = logging.getLogger(__name__)

NUMBERS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key=DATA_COOLDOWN,
        name="Coldown",
        device_class="",
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
    updater = domain_data[UPDATE_LISTENER]

    entities: list[TuyaSmartWateringNumber] = [
        TuyaSmartWateringNumber(
            unique_id="{config_entry.unique_id}-{description.key}",
            updater=updater,
            description=description,
        )
        for description in NUMBERS
    ]
    async_add_entities(entities)


class TuyaSmartWateringNumber(NumberEntity, CoordinatorEntity):
    coordinator: DataUpdater

    def set_value(self, value: float) -> None:
        pass

    def __init__(
        self, unique_id: str, updater: DataUpdater, description: NumberEntityDescription
    ):
        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_device_info = self.coordinator.device_info
        self._attr_mode = NumberMode.BOX
        for i in self.coordinator.tuya.schema(self.coordinator.config[CONF_DEVICE]):
            if i["code"] == self.entity_description.key:
                self._attr_step = i["values"]["step"]
                self._attr_max_value = i["values"]["max"]
                self._attr_min_value = i["values"]["min"]
                self._attr_unit_of_measurement = i["values"]["unit"]

    def _handle_coordinator_update(self) -> None:
        self._attr_value = self.coordinator.data.get(self.entity_description.key)
