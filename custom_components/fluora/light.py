"""Light platform for Fluora integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import FluoraDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fluora light platform."""
    coordinator: FluoraDataUpdateCoordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]

    async_add_entities(
        [FluoraLight(coordinator, entry)],
    )


class FluoraLight(CoordinatorEntity[FluoraDataUpdateCoordinator], LightEntity):
    """Representation of a Fluora light."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.TRANSITION

    def __init__(
        self,
        coordinator: FluoraDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_light"
        self._entry = entry

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_data = self.coordinator.data.get("device_info", {})
        
        return {
            "identifiers": {(DOMAIN, self.coordinator.ip_address)},
            "name": device_data.get("nickname") or device_data.get("model", "Fluora Device"),
            "manufacturer": MANUFACTURER,
            "model": device_data.get("model", MODEL),
            "sw_version": device_data.get("version"),
            "hw_version": device_data.get("serial_number"),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        
        # Check if device was seen recently (within 5 minutes)
        import time
        last_seen = self.coordinator.data.get("last_seen", 0)
        return time.time() - last_seen < 300

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.coordinator.data.get("is_on", False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        brightness_pct = self.coordinator.data.get("brightness", 0)
        # Convert from 0-100 to 0-255 for Home Assistant
        return int(brightness_pct * 255 / 100) if brightness_pct > 0 else 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        
        if brightness is not None:
            # Convert from 0-255 to 0-100 for the device
            brightness_pct = int(brightness * 100 / 255)
            await self.coordinator.async_set_brightness(brightness_pct)
        
        # Always turn on the device
        await self.coordinator.async_set_power(True)
        
        # Request immediate update
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.async_set_power(False)
        
        # Request immediate update
        await self.coordinator.async_request_refresh()
