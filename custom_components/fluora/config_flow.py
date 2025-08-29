"""Config flow for Fluora integration."""
from __future__ import annotations

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

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    ip_address = data[CONF_IP_ADDRESS]

    # Check if we have a shared client already
    domain_data = hass.data.get(DOMAIN, {})
    client = domain_data.get("client")

    def _test_connection():
        """Test connection to device."""
        if client is None:
            # Create temporary client for validation
            temp_client = PixelAirClient()
            try:
                if not temp_client.start():
                    raise CannotConnect("Failed to start client")

                # Wait briefly for any response
                import time
                time.sleep(2)

                # Check discovered devices
                discovered = temp_client.get_discovered_devices()
                if ip_address in discovered:
                    device_info = discovered[ip_address]
                    return {
                        "title": device_info.nickname or device_info.device_model or "Fluora Device",
                        "ip_address": ip_address,
                        "device_info": device_info.to_dict(),
                    }
                else:
                    # Try to register and test the device
                    success = temp_client.register_device(ip_address)
                    if not success:
                        raise CannotConnect("Failed to register device")

                    device = temp_client.get_device(ip_address)
                    if device is None:
                        raise CannotConnect("Device not found")

                    device_info = device.get_device_info()
                    return {
                        "title": device_info.get("model", "Fluora Device"),
                        "ip_address": ip_address,
                        "device_info": device_info,
                    }
            finally:
                temp_client.stop()
        else:
            # Use existing shared client
            discovered = client.get_discovered_devices()
            if ip_address in discovered:
                device_info = discovered[ip_address]
                return {
                    "title": device_info.nickname or device_info.device_model or "Fluora Device",
                    "ip_address": ip_address,
                    "device_info": device_info.to_dict(),
                }
            else:
                # Device not in discovery, assume it's valid for now
                return {
                    "title": "Fluora Device",
                    "ip_address": ip_address,
                    "device_info": {},
                }

    try:
        return await hass.async_add_executor_job(_test_connection)
    except Exception as exc:
        _LOGGER.error("Error connecting to Fluora device at %s: %s", ip_address, exc)
        raise CannotConnect from exc


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fluora."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._discovered_devices: dict[str, DeviceInfo] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Check for discovered devices first
        if not user_input:
            discovered = await self._async_get_discovered_devices()
            if discovered:
                return await self.async_step_discovery_confirm()

        errors: dict[str, str] = {}
        if user_input is not None:
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
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            ip_address = user_input["ip_address"]
            device_info = self._discovered_devices.get(ip_address)
            
            if device_info:
                await self.async_set_unique_id(ip_address)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=device_info.nickname or device_info.device_model or "Fluora Device",
                    data={CONF_IP_ADDRESS: ip_address},
                )

        # Show discovered devices for selection
        discovered = self._discovered_devices
        if not discovered:
            return await self.async_step_user()

        data_schema = vol.Schema(
            {
                vol.Required("ip_address"): vol.In(
                    {
                        ip: f"{info.nickname or info.device_model or 'Unknown'} ({ip})"
                        for ip, info in discovered.items()
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=data_schema,
            description_placeholders={"count": len(discovered)},
        )

    async def _async_get_discovered_devices(self) -> dict[str, DeviceInfo]:
        """Get discovered devices from client."""
        # Check if we have a shared client already
        domain_data = self.hass.data.get(DOMAIN, {})
        client = domain_data.get("client")

        def _discover():
            if client is not None:
                # Use existing shared client
                return client.get_discovered_devices()
            else:
                # Create temporary client for discovery
                temp_client = PixelAirClient()
                try:
                    if not temp_client.start():
                        return {}
                    
                    # Wait for discovery
                    import time
                    time.sleep(5)
                    
                    return temp_client.get_discovered_devices()
                finally:
                    temp_client.stop()

        try:
            discovered = await self.hass.async_add_executor_job(_discover)
            self._discovered_devices = discovered
            return discovered
        except Exception as exc:
            _LOGGER.error("Error during device discovery: %s", exc)
            return {}


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
