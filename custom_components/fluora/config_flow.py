"""Config flow for Fluora integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from libfluora import PixelAirClient, DeviceInfo

from .const import DOMAIN
from . import async_get_shared_client

_LOGGER = logging.getLogger(__name__)

# Time to wait for device discovery
DISCOVERY_TIMEOUT = 10

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_IP_ADDRESS): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    ip_address = data[CONF_IP_ADDRESS]
    
    # Get the shared client
    client = await async_get_shared_client(hass)
    
    # Check if we can find the device
    discovered_devices = await hass.async_add_executor_job(client.get_discovered_devices)
    
    if ip_address not in discovered_devices:
        raise CannotConnect(f"Device at {ip_address} not found")
    
    device_info = discovered_devices[ip_address]
    
    # Return info that you want to store in the config entry.
    return {
        "title": device_info.nickname or f"Fluora Device ({ip_address})",
        "ip_address": ip_address,
        "device_info": device_info.to_dict(),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fluora."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.discovered_devices: dict[str, DeviceInfo] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is None:
            # Start discovery process
            await self._async_discover_devices()
            
            # If we found devices, show discovery confirmation
            if self.discovered_devices:
                return await self.async_step_discovery_confirm()
            
            # Otherwise, show manual entry form
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )

        if CONF_IP_ADDRESS in user_input and user_input[CONF_IP_ADDRESS]:
            # Manual IP entry
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_IP_ADDRESS])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=info["title"],
                    data={CONF_IP_ADDRESS: user_input[CONF_IP_ADDRESS]},
                )
        else:
            # No manual entry, try discovery again
            await self._async_discover_devices()
            if self.discovered_devices:
                return await self.async_step_discovery_confirm()
            else:
                errors["base"] = "no_devices_found"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle discovery confirmation step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            ip_address = user_input[CONF_IP_ADDRESS]
            device_info = self.discovered_devices.get(ip_address)
            
            if device_info:
                await self.async_set_unique_id(ip_address)
                self._abort_if_unique_id_configured()
                
                title = device_info.nickname or f"Fluora Device ({ip_address})"
                
                return self.async_create_entry(
                    title=title,
                    data={CONF_IP_ADDRESS: ip_address},
                )
            else:
                errors["base"] = "device_not_found"

        # Build options for discovered devices
        device_options = {}
        for ip, device_info in self.discovered_devices.items():
            name = device_info.nickname or f"Device at {ip}"
            if device_info.device_model:
                # Ensure device_model is a string (in case it's bytes)
                model = device_info.device_model
                if isinstance(model, bytes):
                    model = model.decode('utf-8', errors='replace')
                name += f" ({model})"
            device_options[ip] = name

        if not device_options:
            # No devices found, go back to manual entry
            return await self.async_step_user()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_IP_ADDRESS): vol.In(device_options),
            }
        )

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"count": len(device_options)},
        )

    async def _async_discover_devices(self) -> None:
        """Discover Fluora devices on the network."""
        _LOGGER.debug("Starting device discovery")
        
        # Get the shared client
        client = await async_get_shared_client(self.hass)
        
        try:
            # Wait for discovery (client is already running)
            await asyncio.sleep(DISCOVERY_TIMEOUT)
            
            # Get discovered devices
            discovered = await self.hass.async_add_executor_job(client.get_discovered_devices)
            
            # Filter out already configured devices
            for ip_address, device_info in discovered.items():
                # Check if this device is already configured
                await self.async_set_unique_id(ip_address)
                if not self._async_current_entries():
                    self.discovered_devices[ip_address] = device_info
            
            _LOGGER.debug("Found %d unconfigured devices", len(self.discovered_devices))
        
        except Exception as e:
            _LOGGER.error("Error during discovery: %s", e)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
