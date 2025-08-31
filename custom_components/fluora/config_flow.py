"""Config flow for Fluora integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from libfluora import DeviceInfo

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_MODEL, CONF_MAC
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
    
    # Wait a moment for discovery to work, then check for the device
    await asyncio.sleep(1)
    discovered_devices = await hass.async_add_executor_job(client.get_discovered_devices)
    
    if ip_address not in discovered_devices:
        # Try to register the device directly if not discovered
        _LOGGER.debug("Device %s not in discovered devices, attempting direct registration", ip_address)
        try:
            await hass.async_add_executor_job(client.register_device, ip_address)
            # Wait a moment and check if the device is now available
            await asyncio.sleep(2)  # Increased wait time
            all_devices = await hass.async_add_executor_job(client.get_all_devices)
            
            if ip_address in all_devices:
                device = all_devices[ip_address]
                _LOGGER.debug("Device %s registered successfully", ip_address)
                device_info_dict = await hass.async_add_executor_job(device.get_device_info)
                
                # Check if device_info_dict is valid
                if device_info_dict is None:
                    _LOGGER.warning("Device %s returned None for device info", ip_address)
                    device_info_dict = {}
                
                # Create a basic DeviceInfo-like structure
                device_info = type('DeviceInfo', (), {
                    'nickname': device_info_dict.get('nickname'),
                    'device_model': device_info_dict.get('device_model', 'Unknown'),
                    'mac_address': device_info_dict.get('mac_address', ip_address)
                })()
            else:
                _LOGGER.error("Device %s not found after registration attempt", ip_address)
                raise Exception(f"Device at {ip_address} not reachable")
        except Exception as e:
            _LOGGER.error("Failed to register device %s: %s", ip_address, e)
            raise Exception(f"Device at {ip_address} not found or not reachable")
    else:
        _LOGGER.debug("Device %s found in discovered devices", ip_address)
        device_info = discovered_devices[ip_address]
    
    # Return info that you want to store in the config entry.
    return {
        "title": device_info.nickname or f"Fluora Device ({ip_address})",
        "data": {
            CONF_IP_ADDRESS: ip_address,
            CONF_MODEL: device_info.device_model,
            CONF_MAC: device_info.mac_address,
        },
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
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )

        if CONF_IP_ADDRESS in user_input and user_input[CONF_IP_ADDRESS]:
            # Manual IP entry
            try:
                info = await validate_input(self.hass, user_input)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors,
                )
            else:
                await self.async_set_unique_id(user_input[CONF_IP_ADDRESS])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=info["title"],
                    data={CONF_IP_ADDRESS: user_input[CONF_IP_ADDRESS],
                          CONF_MODEL: info["data"][CONF_MODEL],
                          CONF_MAC: info["data"][CONF_MAC]},
                )
        else:
            # Auto-discovery requested (empty or no IP address provided)
            await self._async_discover_devices()
            return await self.async_step_discovery_confirm()

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
                    data={CONF_IP_ADDRESS: ip_address,
                          CONF_MODEL: device_info.device_model,
                          CONF_MAC: device_info.mac_address},
                )
            else:
                errors["base"] = "device_not_found"

        # Build options for discovered devices
        device_options = {}
        for ip, device_info in self.discovered_devices.items():
            name = device_info.nickname or f"Device at {ip}"
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
            # Give the client a moment to discover devices if it just started
            await asyncio.sleep(2)
            
            # Get discovered devices
            discovered = await self.hass.async_add_executor_job(client.get_discovered_devices)
            
            # Filter out already configured devices
            for ip_address, device_info in discovered.items():
                # Check if this device is already configured
                if not any(
                    entry.unique_id == ip_address 
                    for entry in self._async_current_entries()
                ):
                    self.discovered_devices[ip_address] = device_info
            
            _LOGGER.debug("Found %d unconfigured devices", len(self.discovered_devices))
        
        except Exception as e:
            _LOGGER.error("Error during discovery: %s", e)
