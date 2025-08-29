"""Fluora integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import FluoraDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fluora from a config entry."""
    coordinator = FluoraDataUpdateCoordinator(
        hass,
        entry.data[CONF_IP_ADDRESS],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok
