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
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FluoraDeviceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fluora light from a config entry."""
    coordinator: FluoraDeviceCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    name: str = hass.data[DOMAIN][config_entry.entry_id][CONF_NAME]
    host: str = hass.data[DOMAIN][config_entry.entry_id][CONF_HOST]

    # Create the light entity
    light = FluoraLight(coordinator, name, host, config_entry.entry_id)
    async_add_entities([light], True)


class FluoraLight(CoordinatorEntity[FluoraDeviceCoordinator], LightEntity):
    """Representation of a Fluora light."""

    def __init__(
        self,
        coordinator: FluoraDeviceCoordinator,
        name: str,
        host: str,
        entry_id: str,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._name = name
        self._host = host
        self._entry_id = entry_id
        
        # Initialize state from coordinator data
        self._attr_available = True

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this light."""
        return f"{DOMAIN}_{self._host}_{self._entry_id}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this light."""
        return self.coordinator.get_device_info()

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.coordinator.data.get("is_on", False) if self.coordinator.data else False

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light (0-255)."""
        if not self.coordinator.data:
            return None
        device_brightness = self.coordinator.data.get("brightness", 100.0)
        # Convert from device brightness (0-100) to Home Assistant brightness (0-255)
        ha_brightness = int((device_brightness / 100.0) * 255.0)
        return max(0, min(255, ha_brightness))

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.BRIGHTNESS

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        return {ColorMode.BRIGHTNESS}

    @property
    def supported_features(self) -> LightEntityFeature:
        """Return the supported features."""
        return LightEntityFeature.NONE

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        
        # If brightness is specified, set it first
        if brightness is not None:
            # Convert from Home Assistant brightness (0-255) to device brightness (0-100)
            device_brightness = int((brightness / 255.0) * 100.0)
            device_brightness = max(1, min(100, device_brightness))  # Ensure range 1-100
            
            _LOGGER.debug("Setting brightness to %d%% (HA: %d)", device_brightness, brightness)
            success = await self.coordinator.async_set_brightness(device_brightness)
            if not success:
                _LOGGER.warning("Failed to set brightness for %s", self._name)
                return

        # Turn on the device
        _LOGGER.debug("Turning on light %s", self._name)
        success = await self.coordinator.async_set_power(True)
        if not success:
            _LOGGER.warning("Failed to turn on light %s", self._name)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the light off."""
        _LOGGER.debug("Turning off light %s", self._name)
        success = await self.coordinator.async_set_power(False)
        if not success:
            _LOGGER.warning("Failed to turn off light %s", self._name)
