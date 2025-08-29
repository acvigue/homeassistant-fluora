"""Services for Koios Digital Clock integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, API_LED_CHANNEL, API_NIXIE, API_FIBONACCI, LED_CHANNEL_BACKLIGHT
from .coordinator import KoiosClockDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_LED_EFFECT = "set_led_effect"
SERVICE_SET_FIBONACCI_THEME = "set_fibonacci_theme"
SERVICE_SET_NIXIE_CONFIG = "set_nixie_config"

SET_LED_EFFECT_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Required("effect"): cv.string,
        vol.Optional("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        vol.Optional("color"): vol.All(
            vol.ExactSequence([vol.Coerce(int), vol.Coerce(int), vol.Coerce(int)]),
            [vol.Range(min=0, max=255), vol.Range(min=0, max=255), vol.Range(min=0, max=255)],
        ),
    }
)

SET_FIBONACCI_THEME_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Required("theme"): cv.string,
        vol.Optional("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    }
)

SET_NIXIE_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Optional("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("military_time"): cv.boolean,
        vol.Optional("blinking_dots"): cv.boolean,
        vol.Optional("enabled"): cv.boolean,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Koios Clock integration."""

    async def set_led_effect(call: ServiceCall) -> None:
        """Service to set LED effect with optional parameters."""
        entity_ids = call.data["entity_id"]
        effect = call.data["effect"]
        brightness = call.data.get("brightness")
        color = call.data.get("color")

        for entity_id in entity_ids:
            # Get coordinator from entity
            coordinator = _get_coordinator_from_entity_id(hass, entity_id)
            if not coordinator:
                continue

            # Find the effect ID for the effect name using API data or fallback
            led_effects_data = coordinator.data.get("led_effects", [])
            effect_id = "SOLID"  # Default fallback
            
            # Try to find from API effects first
            for api_effect in led_effects_data:
                if api_effect.get("name") == effect:
                    effect_id = api_effect.get("id", "SOLID")
                    break

            data = {"effect_id": effect_id}
            if brightness is not None:
                data["brightness"] = brightness
            if color is not None:
                data["color"] = {"r": color[0], "g": color[1], "b": color[2]}
                if len(color) > 3:
                    data["color"]["w"] = color[3]

            endpoint = f"{API_LED_CHANNEL}/{LED_CHANNEL_BACKLIGHT}"
            response = await coordinator.async_post_data(endpoint, data)
            
            if response:
                # Update the coordinator data with the response
                led_channels = coordinator.data.setdefault("led_channels", {})
                led_channels[LED_CHANNEL_BACKLIGHT] = response
                coordinator.async_set_updated_data(coordinator.data)

    async def set_fibonacci_theme(call: ServiceCall) -> None:
        """Service to set Fibonacci theme."""
        entity_ids = call.data["entity_id"]
        theme = call.data["theme"]
        brightness = call.data.get("brightness")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_from_entity_id(hass, entity_id)
            if not coordinator or coordinator.model != "fibonacci":
                continue

            # Find theme ID by name
            fib_data = coordinator.data.get("fibonacci", {})
            themes_data = fib_data.get("themes", [])
            theme_id = next(
                (t["id"] for t in themes_data if t.get("name") == theme),
                0
            )

            data = {"theme_id": theme_id}
            if brightness is not None:
                data["brightness"] = brightness

            response = await coordinator.async_post_data(API_FIBONACCI, data)
            
            if response:
                # Update the coordinator data with the response
                coordinator.data["fibonacci"] = response
                coordinator.async_set_updated_data(coordinator.data)

    async def set_nixie_config(call: ServiceCall) -> None:
        """Service to set Nixie configuration."""
        entity_ids = call.data["entity_id"]

        for entity_id in entity_ids:
            coordinator = _get_coordinator_from_entity_id(hass, entity_id)
            if not coordinator or coordinator.model != "nixie":
                continue

            data = {}
            for key in ["brightness", "military_time", "blinking_dots"]:
                if key in call.data:
                    data[key] = call.data[key]
            
            # Handle the 'enabled' parameter mapping to 'on'
            if "enabled" in call.data:
                data["on"] = call.data["enabled"]

            if data:
                response = await coordinator.async_post_data(API_NIXIE, data)
                
                if response:
                    # Update the coordinator data with the response
                    coordinator.data["nixie"] = response
                    coordinator.async_set_updated_data(coordinator.data)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LED_EFFECT,
        set_led_effect,
        schema=SET_LED_EFFECT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FIBONACCI_THEME,
        set_fibonacci_theme,
        schema=SET_FIBONACCI_THEME_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_NIXIE_CONFIG,
        set_nixie_config,
        schema=SET_NIXIE_CONFIG_SCHEMA,
    )

    _LOGGER.info("Koios Clock services registered")


def _get_coordinator_from_entity_id(hass: HomeAssistant, entity_id: str) -> KoiosClockDataUpdateCoordinator | None:
    """Get coordinator from entity ID."""
    # This is a simplified approach - in a real implementation you'd need to
    # properly map entity IDs to coordinators
    domain_data = hass.data.get(DOMAIN, {})
    for coordinator in domain_data.values():
        if isinstance(coordinator, KoiosClockDataUpdateCoordinator):
            return coordinator
    return None


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Koios Clock services."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_LED_EFFECT)
    hass.services.async_remove(DOMAIN, SERVICE_SET_FIBONACCI_THEME)
    hass.services.async_remove(DOMAIN, SERVICE_SET_NIXIE_CONFIG)
