"""Number platform for Koios Digital Clock integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MODEL_FIBONACCI,
    MODEL_NIXIE,
    MODEL_WORDCLOCK,
    MODEL_TRANQUIL,
)
from .coordinator import KoiosClockDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Koios Clock number entities based on a config entry."""
    coordinator: KoiosClockDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    # No brightness number entities - brightness is now handled by light entities
    # Could add other number entities here in the future (e.g., LED speed, etc.)

    if entities:
        async_add_entities(entities, True)


class KoiosClockNumberEntity(CoordinatorEntity, NumberEntity):
    """Base class for Koios Clock number entities."""

    def __init__(
        self,
        coordinator: KoiosClockDataUpdateCoordinator,
        number_type: str,
        name: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.number_type = number_type
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_{number_type}"
        self._attr_name = f"Koios Clock {name}"
        self._attr_mode = NumberMode.SLIDER
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.host}_{coordinator.port}")},
            "name": f"Koios Clock ({coordinator.host})",
            "manufacturer": "Koios Digital",
            "model": coordinator.model.title(),
            "sw_version": coordinator.data.get("about", {}).get("version"),
        }

# Brightness number entities removed - brightness is now handled by light entities
