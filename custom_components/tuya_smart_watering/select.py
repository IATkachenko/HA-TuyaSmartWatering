"""Switch component."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DataUpdater
from .const import DATA_MODE, DOMAIN, UPDATE_LISTENER

_LOGGER = logging.getLogger(__name__)

SELECTS: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key=DATA_MODE,
        name="State",
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

    entities: list[TuyaSmartWateringSelect] = [
        TuyaSmartWateringSelect(
            unique_id="{config_entry.unique_id}-{description.key}",
            updater=updater,
            description=description,
        )
        for description in SELECTS
    ]
    async_add_entities(entities)


class TuyaSmartWateringSelect(SelectEntity, CoordinatorEntity):
    coordinator: DataUpdater

    def select_option(self, option: str) -> None:
        pass

    async def async_select_option(self, option: str) -> None:
        pass

    def __init__(
        self, unique_id: str, updater: DataUpdater, description: SelectEntityDescription
    ):
        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_device_info = self.coordinator.device_info
        self._attr_options = []
        for i in self.coordinator.tuya.schema(self.coordinator.config[CONF_DEVICE]):
            if i["code"] == self.entity_description.key:
                self._attr_options = i["values"]["range"]
                break

    def _handle_coordinator_update(self) -> None:
        self._attr_current_option = self.coordinator.data.get(
            self.entity_description.key
        )
