"""Data update coordinator for Koios Digital Clock."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_ABOUT,
    API_LED_CONFIG,
    API_LED_CHANNEL,
    API_LED_EFFECTS,
    API_NIXIE,
    API_FIBONACCI,
    API_SYSTEM_CONFIG,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LED_CHANNEL_BACKLIGHT,
    MODEL_FIBONACCI,
    MODEL_NIXIE,
    MODEL_WORDCLOCK,
    MODEL_MATRX,
    MODEL_TRANQUIL,
)

_LOGGER = logging.getLogger(__name__)


class KoiosClockDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Koios Clock API."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        model: str,
    ) -> None:
        """Initialize."""
        self.host = host
        self.port = port
        self.model = model
        self.session = session
        self.base_url = f"http://{host}:{port}"

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            data = {}

            # Get device info
            about_data = await self._async_get_data(API_ABOUT)
            if about_data:
                data["about"] = about_data

            # Get model-specific configuration based on subtype
            if self.model == MODEL_FIBONACCI:
                # Fibonacci clocks only use /api/fibonacci endpoint
                fib_data = await self._async_get_data(API_FIBONACCI)
                if fib_data:
                    data["fibonacci"] = fib_data

            elif self.model == MODEL_NIXIE:
                # Nixie clocks use both LED channels and /api/nixie endpoints
                led_config = await self._async_get_data(API_LED_CONFIG)
                if led_config:
                    data["led_config"] = led_config
                    
                # Get available LED effects
                led_effects = await self._async_get_data(API_LED_EFFECTS)
                if led_effects:
                    data["led_effects"] = led_effects
                    
                # Get state for each LED channel
                channels = led_config.get("channels", []) if led_config else []
                led_channels = {}
                for channel in channels:
                    channel_idx = channel.get("index")
                    if channel_idx is not None:
                        channel_data = await self._async_get_data(f"{API_LED_CHANNEL}/{channel_idx}")
                        if channel_data:
                            led_channels[channel_idx] = channel_data
                
                if led_channels:
                    data["led_channels"] = led_channels

                nixie_data = await self._async_get_data(API_NIXIE)
                if nixie_data:
                    data["nixie"] = nixie_data

            elif self.model == MODEL_WORDCLOCK:
                # Wordclock only uses LED channels
                led_config = await self._async_get_data(API_LED_CONFIG)
                if led_config:
                    data["led_config"] = led_config
                    
                # Get available LED effects
                led_effects = await self._async_get_data(API_LED_EFFECTS)
                if led_effects:
                    data["led_effects"] = led_effects
                    
                # Get state for each LED channel
                channels = led_config.get("channels", []) if led_config else []
                led_channels = {}
                for channel in channels:
                    channel_idx = channel.get("index")
                    if channel_idx is not None:
                        channel_data = await self._async_get_data(f"{API_LED_CHANNEL}/{channel_idx}")
                        if channel_data:
                            led_channels[channel_idx] = channel_data
                
                if led_channels:
                    data["led_channels"] = led_channels

            elif self.model == MODEL_MATRX:
                # MATRX devices use system config endpoint
                system_config = await self._async_get_data(API_SYSTEM_CONFIG)
                if system_config:
                    data["system_config"] = system_config

            elif self.model == MODEL_TRANQUIL:
                # Tranquil only uses LED channel 0 (similar to wordclock but only channel 0)
                led_config = await self._async_get_data(API_LED_CONFIG)
                if led_config:
                    data["led_config"] = led_config
                    
                # Get available LED effects
                led_effects = await self._async_get_data(API_LED_EFFECTS)
                if led_effects:
                    data["led_effects"] = led_effects
                    
                # Get state for LED channel 0 only
                channel_data = await self._async_get_data(f"{API_LED_CHANNEL}/{LED_CHANNEL_BACKLIGHT}")
                if channel_data:
                    data["led_channels"] = {LED_CHANNEL_BACKLIGHT: channel_data}

            return data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _async_get_data(self, endpoint: str) -> dict[str, Any] | None:
        """Get data from an endpoint."""
        try:
            url = f"{self.base_url}{endpoint}"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    _LOGGER.warning("API endpoint %s returned status %s", endpoint, response.status)
                    return None
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching data from %s: %s", endpoint, err)
            return None
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout fetching data from %s: %s", endpoint, err)
            return None

    async def async_post_data(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Post data to an endpoint and return the response."""
        try:
            url = f"{self.base_url}{endpoint}"
            async with self.session.post(url, json=data, timeout=10) as response:
                if response.status == 200:
                    # API returns the entire endpoint state after update
                    return await response.json()
                else:
                    _LOGGER.error("API endpoint %s returned status %s", endpoint, response.status)
                    return None
        except aiohttp.ClientError as err:
            _LOGGER.error("Error posting data to %s: %s", endpoint, err)
            return None
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout posting data to %s: %s", endpoint, err)
            return None
