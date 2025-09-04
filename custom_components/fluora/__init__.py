"""The Fluora integration."""

from __future__ import annotations

import logging

from .libpixelair import PixelAirDevice
from .coordinator import FluoraDeviceCoordinator

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fluora from a config entry."""
    _LOGGER.debug("Setting up Fluora entry: %s", entry.entry_id)

    # Initialize domain data if needed
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entries": set()}

    # Track this entry
    hass.data[DOMAIN]["entries"].add(entry.entry_id)

    # Create device
    device = PixelAirDevice(entry.data[CONF_HOST])
    
    # Create coordinator
    coordinator = FluoraDeviceCoordinator(hass, device, entry)
    
    # Register device in device registry
    await coordinator.async_register_device()

    # Store entry-specific data
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_HOST: entry.data[CONF_HOST],
        CONF_NAME: entry.data[CONF_NAME],
        "device": device,
        "coordinator": coordinator,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Fluora entry: %s", entry.entry_id)

    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        device: PixelAirDevice = hass.data[DOMAIN][entry.entry_id]["device"]
        device.close()
        
        # Remove entry-specific data
        hass.data[DOMAIN]["entries"].discard(entry.entry_id)
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # If this was the last entry, stop the client
        if not hass.data[DOMAIN]["entries"]:
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    # No migrations needed yet since this is version 1
    if config_entry.version == 1:
        return True

    return False
