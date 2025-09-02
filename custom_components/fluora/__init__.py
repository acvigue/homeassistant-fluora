"""The Fluora integration."""

from __future__ import annotations

import logging

from .libpixelair import PixelAirClient, PixelAirDevice

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    #    Platform.LIGHT,
]


async def async_get_shared_client(hass: HomeAssistant) -> PixelAirClient:
    """Get or create the shared PixelAirClient."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if "client" not in hass.data[DOMAIN]:
        _LOGGER.debug("Creating new shared PixelAirClient")
        client = PixelAirClient()

        # Start the client
        if not await hass.async_add_executor_job(client.start):
            _LOGGER.error("Failed to start PixelAirClient")
            raise ConfigEntryNotReady("Failed to start PixelAirClient")

        hass.data[DOMAIN]["client"] = client
        hass.data[DOMAIN]["entries"] = set()

        _LOGGER.info("PixelAirClient started successfully")

        # Register cleanup on shutdown
        async def cleanup_client(event):
            """Clean up the client on shutdown."""
            _LOGGER.debug("Shutting down PixelAirClient")
            await hass.async_add_executor_job(client.stop)

        hass.bus.async_listen_once("homeassistant_stop", cleanup_client)

    return hass.data[DOMAIN]["client"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fluora from a config entry."""
    _LOGGER.debug("Setting up Fluora entry: %s", entry.entry_id)

    # Ensure the shared client is initialized
    client = await async_get_shared_client(hass)

    # Track this entry
    hass.data[DOMAIN]["entries"].add(entry.entry_id)

    # Store entry-specific data
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_HOST: entry.data[CONF_HOST],
    }

    device = client.get_device(entry.data[CONF_HOST])
    if device is None:
        device = PixelAirDevice(entry.data[CONF_HOST])
        client.register_device(device)

    hass.data[DOMAIN][entry.entry_id]["device"] = device

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Fluora entry: %s", entry.entry_id)

    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        device: PixelAirDevice = hass.data[DOMAIN][entry.entry_id]["device"]
        client: PixelAirClient = hass.data[DOMAIN]["client"]

        client.unregister_device(device)

        # Remove entry-specific data
        hass.data[DOMAIN]["entries"].discard(entry.entry_id)
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # If this was the last entry, stop the client
        if not hass.data[DOMAIN]["entries"]:
            client = hass.data[DOMAIN].pop("client", None)
            if client:
                await hass.async_add_executor_job(client.stop)

            # Clean up the domain data if empty
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    # No migrations needed yet since this is version 1
    if config_entry.version == 1:
        return True

    return False
