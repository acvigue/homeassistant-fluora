"""Config flow for Koios Digital Clock integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, API_ABOUT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=80): int,
    }
)


class PlaceholderAuth:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str, port: int) -> None:
        """Initialize."""
        self.host = host
        self.port = port

    async def authenticate(self, session: aiohttp.ClientSession) -> dict[str, Any]:
        """Test if we can authenticate with the host."""
        try:
            url = f"http://{self.host}:{self.port}{API_ABOUT}"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    # Handle both 'subtype' (legacy clocks) and 'type' (MATRX devices)
                    device_type = data.get("subtype") or data.get("type")
                    return {
                        "subtype": device_type,
                        "version": data.get("version"),
                        "model": data.get("model"),
                    }
                else:
                    raise CannotConnect
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to %s:%s - %s", self.host, self.port, err)
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.error("Unexpected error connecting to %s:%s - %s", self.host, self.port, err)
            raise InvalidAuth from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Koios Digital Clock."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_port: int | None = None
        self._discovered_model: str | None = None
        self._discovered_hostname: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                hub = PlaceholderAuth(user_input[CONF_HOST], user_input[CONF_PORT])
                device_info = await hub.authenticate(session)
                
                # Use hostname for unique ID if available, otherwise fall back to host:port
                hostname = device_info.get("hostname", user_input[CONF_HOST])
                await self.async_set_unique_id(hostname)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=device_info.get("model", "Koios Digital Clock"),
                    data={
                        **user_input,
                        "model": device_info.get("subtype", "unknown"),
                    }
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        _LOGGER.debug("Zeroconf discovery received: %s", discovery_info)
        
        host = discovery_info.host
        port = discovery_info.port or 80
        properties = discovery_info.properties
        
        _LOGGER.debug("Discovery properties: %s", properties)

        # Extract info from zeroconf properties - use mDNS hostname for discovery
        # Properties might be bytes, so decode them
        subtype = properties.get("subtype") or properties.get(b"subtype")
        if isinstance(subtype, bytes):
            subtype = subtype.decode("utf-8")
            
        hostname = discovery_info.hostname.replace(".local.", "")  # Use mDNS hostname

        _LOGGER.debug("Extracted subtype: %s, hostname: %s", subtype, hostname)

        # If no subtype in mDNS properties, try to get it from the device API
        device_info = None
        if not subtype:
            _LOGGER.debug("No subtype in mDNS properties, trying to fetch from device API")
            try:
                session = async_get_clientsession(self.hass)
                hub = PlaceholderAuth(host, port)
                device_info = await hub.authenticate(session)
                # Handle both 'subtype' (legacy clocks) and 'type' (MATRX devices)
                subtype = device_info.get("subtype") or device_info.get("type")
                _LOGGER.debug("Got subtype from device API: %s", subtype)
            except Exception as err:
                _LOGGER.warning("Failed to get device info during discovery: %s", err)
                return self.async_abort(reason="cannot_connect")
            
        if not subtype:
            _LOGGER.warning("No subtype found in discovery properties or device API, aborting")
            return self.async_abort(reason="invalid_discovery")

        # Set unique ID to prevent duplicates - use hostname for uniqueness
        await self.async_set_unique_id(hostname)
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: host, CONF_PORT: port}
        )

        self._discovered_host = host
        self._discovered_port = port
        self._discovered_model = subtype  # Use subtype as model
        self._discovered_hostname = hostname

        # If we didn't authenticate above, do it now to verify connectivity
        if device_info is None:
            try:
                session = async_get_clientsession(self.hass)
                hub = PlaceholderAuth(host, port)
                await hub.authenticate(session)
                _LOGGER.debug("Successfully authenticated with discovered device at %s:%s", host, port)
            except Exception as err:
                _LOGGER.warning("Failed to authenticate with discovered device at %s:%s: %s", host, port, err)
                return self.async_abort(reason="cannot_connect")

        self.context.update({"title_placeholders": {"name": hostname}})
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_hostname,
                data={
                    CONF_HOST: self._discovered_host,
                    CONF_PORT: self._discovered_port,
                    "model": self._discovered_model,
                },
            )

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": self._discovered_hostname},
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
