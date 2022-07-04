"""Switch component."""

from __future__ import annotations

import logging

from homeassistant.components.number import (NumberEntity, NumberEntityDescription, NumberMode, ENTITY_ID_FORMAT, )
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DataUpdater
from .const import DATA_COOLDOWN, DOMAIN, UPDATER, DATA_ONLINE

_LOGGER = logging.getLogger(__name__)

NUMBERS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key=DATA_COOLDOWN,
        name="Cooldown",
        device_class="",
        entity_registry_enabled_default=True,
        icon="mdi:timer",
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

    entities: list[TuyaSmartWateringNumber] = [
        TuyaSmartWateringNumber(
            unique_id=f"{config_entry.unique_id}-{description.key}",
            updater=updater,
            description=description,
        )
        for description in NUMBERS
    ]
    async_add_entities(entities)


class TuyaSmartWateringNumber(NumberEntity, CoordinatorEntity):
    coordinator: DataUpdater

    def set_value(self, value: float) -> None:
        self.coordinator.set_cooldown(value)

    def __init__(
        self, unique_id: str, updater: DataUpdater, description: NumberEntityDescription
    ):
        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_device_info = self.coordinator.device_info
        self._attr_mode = NumberMode.BOX
        self._attr_value = 0
        self._attr_name = f"{self.coordinator.name} {self.entity_description.name}"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{self.coordinator.name}_{self.entity_description.name}",
            hass=self.coordinator.hass,
        )
        for i in self.coordinator.specification:
            if i["code"] == self.entity_description.key:
                self._attr_step = float(i["values"]["step"])
                self._attr_max_value = float(i["values"]["max"])
                self._attr_min_value = float(i["values"]["min"])
                self._attr_unit_of_measurement = i["values"]["unit"]

    async def async_added_to_hass(self) -> None:
        await CoordinatorEntity.async_added_to_hass(self)
        self._handle_coordinator_update()

    def _handle_coordinator_update(self) -> None:
        self._attr_value = float(self.coordinator.data.get(self.entity_description.key))
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self.coordinator.data.get(DATA_ONLINE, False)
