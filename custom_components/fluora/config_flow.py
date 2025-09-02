"""Config flow for Fluora integration."""

from __future__ import annotations

import logging
from typing import Any

from .libpixelair import PixelAirDevice
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from . import DOMAIN, async_get_shared_client

_LOGGER = logging.getLogger(__name__)

# Time to wait for device discovery
DISCOVERY_TIMEOUT = 10

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fluora."""

    VERSION = 1

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle a dhcp discovery."""
        return await self._process_discovered_device(discovery_info.ip)

    async def _process_discovered_device(self, ip_address: str) -> ConfigFlowResult:
        client = await async_get_shared_client(self.hass)
        device = client.get_device(ip_address)
        if device is None:
            print("Registering new device")
            device = PixelAirDevice(ip_address)
            client.register_device(device)

        result = await device.get_state(timeout=3)  # Initial state fetch
        print(f"Discovery result: {result}, state: {device.state}")
        if result is False:
            return self.async_abort(reason="cannot_connect")

        client.unregister_device(device)  # Clean up if not needed
        await self.async_set_unique_id(device.state.mac_address)
        self._abort_if_unique_id_configured(updates={CONF_HOST: ip_address})
        return await self.async_step_confirm_discovery(
            {
                CONF_HOST: ip_address,
                CONF_NAME: device.state.nickname or f"Fluora Device ({ip_address})",
            }
        )

    async def async_step_confirm_discovery(
        self, data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Allow the user to confirm adding the device."""
        if data is not None:
            return self.async_create_entry(
                title=data[CONF_NAME],
                data={
                    CONF_HOST: data[CONF_HOST],
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm_discovery",
            description_placeholders={
                CONF_HOST: self._discovered_ip,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            self._async_abort_entries_match({CONF_HOST: host})
            return await self._process_discovered_device(host)
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
