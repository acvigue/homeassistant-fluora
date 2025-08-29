"""Fluora integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from libfluora import PixelAirClient

from .const import DOMAIN
from .coordinator import FluoraDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fluora from a config entry."""
    
    # Get or create the shared PixelAirClient
    hass.data.setdefault(DOMAIN, {})
    
    if "client" not in hass.data[DOMAIN]:
        # Create the shared client for the first time
        def _create_client():
            client = PixelAirClient()
            if not client.start():
                raise RuntimeError("Failed to start PixelAir client")
            return client
        
        client = await hass.async_add_executor_job(_create_client)
        hass.data[DOMAIN]["client"] = client
        hass.data[DOMAIN]["coordinators"] = {}
        _LOGGER.info("Created shared PixelAirClient")
    else:
        client = hass.data[DOMAIN]["client"]
    
    # Create coordinator for this specific device
    coordinator = FluoraDataUpdateCoordinator(
        hass,
        client,
        entry.data[CONF_IP_ADDRESS],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Remove this coordinator
        coordinator = hass.data[DOMAIN]["coordinators"].pop(entry.entry_id)
        await coordinator.async_shutdown()
        
        # If this was the last coordinator, shut down the shared client
        if not hass.data[DOMAIN]["coordinators"]:
            client = hass.data[DOMAIN].pop("client")
            def _stop_client():
                client.stop()
            await hass.async_add_executor_job(_stop_client)
            _LOGGER.info("Stopped shared PixelAirClient")

    return unload_ok
