"""Switch platform for Fluora integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up Fluora switch from a config entry."""
    client = hass.data[DOMAIN]["client"]
    ip_address = hass.data[DOMAIN][config_entry.entry_id]["ip_address"]
    
    # Create coordinator for this device
    coordinator = FluoraDeviceCoordinator(hass, client, ip_address)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Create switch entities
    entities = [FluoraMainSwitch(coordinator, config_entry)]
    
    async_add_entities(entities)


class FluoraMainSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Fluora main power switch."""

    def __init__(
        self,
        coordinator: FluoraDeviceCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        
        self.config_entry = config_entry
        self._attr_unique_id = f"{coordinator.ip_address}_main_switch"
        self._attr_name = f"{coordinator.device_name} Power"
        self._attr_icon = "mdi:power"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.ip_address)},
            "name": self.coordinator.device_name,
            "manufacturer": "Fluora",
            "model": self.coordinator.device_model or "Unknown",
            "sw_version": "1.0.0",
            "configuration_url": f"http://{self.coordinator.ip_address}",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("is_online", False)
        )

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        # Check the device's internal state first
        if self.coordinator.device and self.coordinator.device.state:
            return self.coordinator.device.state.is_on
        
        # Fallback to detailed device info
        device_info = self.coordinator.data.get("device_info_detailed")
        if device_info:
            # This would depend on the actual state structure
            # For now, assume the device is on if we have recent communication
            return device_info.get("successful_decodes", 0) > 0
        
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_send_command("turn_on")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_send_command("turn_off")
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = {}
        
        device_info = self.coordinator.data.get("device_info")
        if device_info:
            attributes.update({
                "ip_address": self.coordinator.ip_address,
                "mac_address": device_info.get("mac_address"),
                "device_model": device_info.get("device_model"),
                "last_seen": device_info.get("last_seen"),
            })
        
        return attributes
