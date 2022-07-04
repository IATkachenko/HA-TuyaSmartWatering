"""Switch component."""

from __future__ import annotations

import json
import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription, ENTITY_ID_FORMAT
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DataUpdater
from .const import DATA_MODE, DOMAIN, UPDATER, DATA_PUMP, DATA_ONLINE

_LOGGER = logging.getLogger(__name__)

SELECTS: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key=DATA_MODE,
        name="Mode",
        device_class="",
        entity_registry_enabled_default=True,
    ),
    SelectEntityDescription(
        key=DATA_PUMP,
        name="Pump",
        device_class="",
        entity_registry_enabled_default=True,
        icon="mdi:water-pump"
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
            unique_id=f"{config_entry.unique_id}-{description.key}",
            updater=updater,
            description=description,
        )
        for description in SELECTS
    ]
    async_add_entities(entities)


class TuyaSmartWateringSelect(SelectEntity, CoordinatorEntity):
    coordinator: DataUpdater

    def select_option(self, option: str) -> None:
        if self.entity_description.key == DATA_MODE:
            self.coordinator.set_mode(option)
        elif self.entity_description.key == DATA_PUMP:
            self.coordinator.set_pump(option)

    def __init__(
        self, unique_id: str, updater: DataUpdater, description: SelectEntityDescription
    ):
        CoordinatorEntity.__init__(self, coordinator=updater)

        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_device_info = self.coordinator.device_info
        self._attr_options = []
        self._attr_current_option = None
        self._attr_name = f"{self.coordinator.name} {self.entity_description.name}"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{self.coordinator.name}_{self.entity_description.name}",
            hass=self.coordinator.hass,
        )
        _LOGGER.debug(f"Setting up {self.entity_description.key=}, {self.unique_id=}")
        if self.entity_description.key == DATA_MODE:
            for i in self.coordinator.specification:
                if i["code"] == self.entity_description.key:
                    _LOGGER.debug(f"select init: {i=}")
                    self._attr_options = json.loads(i["values"])["range"]
                    break
        elif self.entity_description.key == DATA_PUMP:
            self._attr_options = ["PumpA", "PumpB", "PumpAB"]

    async def async_added_to_hass(self) -> None:
        await CoordinatorEntity.async_added_to_hass(self)
        self._handle_coordinator_update()

    def _handle_coordinator_update(self) -> None:
        self._attr_current_option = self.coordinator.data.get(
            self.entity_description.key
        )
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self.coordinator.data.get(DATA_ONLINE, False)