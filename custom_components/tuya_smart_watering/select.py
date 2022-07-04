"""Switch component."""

from __future__ import annotations

import json
import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DataUpdater
from .const import DATA_MODE, DOMAIN, UPDATER

_LOGGER = logging.getLogger(__name__)

SELECTS: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key=DATA_MODE,
        name="Mode",
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
    updater = domain_data[UPDATER]

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
        self._attr_current_option = None
        for i in self.coordinator.tuya.schema:
            if i["code"] == self.entity_description.key:
                _LOGGER.debug(f"select init: {i=}")
                self._attr_options = json.loads(i["values"])["range"]
                break

    def _handle_coordinator_update(self) -> None:
        self._attr_current_option = self.coordinator.data.get(
            self.entity_description.key
        )
        self.async_write_ha_state()
