"""Device coordinator for Fluora integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .libpixelair import PixelAirDevice

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = 30  # seconds


class FluoraDeviceCoordinator(DataUpdateCoordinator):
    """Coordinator to manage device state updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: PixelAirDevice,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.device = device
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.name = entry.data[CONF_NAME]
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.host}",
            update_interval=None,  # We'll update manually when needed
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        try:
            success = await self.device.get_state()
            if not success:
                raise UpdateFailed("Failed to get device state")
                
            return {
                "is_on": getattr(self.device.state, "is_on", False),
                "brightness": getattr(self.device.state, "brightness", 100.0),
                "model": getattr(self.device.state, "model", "Unknown"),
                "serial_number": getattr(self.device.state, "serial_number", "Unknown"),
                "mac_address": getattr(self.device.state, "mac_address", "Unknown"),
                "nickname": getattr(self.device.state, "nickname", None),
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    def get_device_info(self) -> dict[str, Any]:
        """Return device information for device registry."""
        device_data = self.data or {}
        
        return {
            "identifiers": {(DOMAIN, self.host)},
            "name": self.name,
            "manufacturer": "PixelAir",
            "model": device_data.get("model", "PixelAir Device"),
            "sw_version": "1.0",
            "serial_number": device_data.get("serial_number"),
            "hw_version": None,
            "configuration_url": f"http://{self.host}",
        }

    async def async_register_device(self) -> None:
        """Register the device in the device registry."""
        device_registry = dr.async_get(self.hass)
        
        # Update device state first to get latest info
        try:
            await self.async_request_refresh()
        except UpdateFailed:
            _LOGGER.warning("Failed to get initial device state for %s", self.host)

        device_info = self.get_device_info()
        
        device_registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            **device_info,
        )
        
        _LOGGER.debug("Registered device %s in device registry", self.host)

    async def async_set_power(self, on: bool) -> bool:
        """Set device power state."""
        try:
            success = await self.device.set_power(on)
            if success:
                # Update our cached state
                if self.data:
                    self.data["is_on"] = on
                await self.async_request_refresh()
            return success
        except Exception as err:
            _LOGGER.error("Error setting power state: %s", err)
            return False

    async def async_set_brightness(self, brightness: int) -> bool:
        """Set device brightness (0-100)."""
        try:
            success = await self.device.set_brightness(brightness)
            if success:
                # Update our cached state
                if self.data:
                    self.data["brightness"] = float(brightness)
                await self.async_request_refresh()
            return success
        except Exception as err:
            _LOGGER.error("Error setting brightness: %s", err)
            return False
