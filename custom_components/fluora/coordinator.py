"""Data update coordinator for Fluora."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from libfluora import PixelAirClient, PixelAirDevice

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class FluoraDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Class to manage fetching data from the Fluora device."""

    def __init__(
        self,
        hass: HomeAssistant,
        ip_address: str,
    ) -> None:
        """Initialize."""
        self.ip_address = ip_address
        self.client: PixelAirClient | None = None
        self.device: PixelAirDevice | None = None
        self._client_started = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_setup_client(self) -> None:
        """Set up the Fluora client."""
        if self.client is not None:
            return

        # Create client and device in executor to avoid blocking
        def _create_client_and_device():
            client = PixelAirClient()
            client.register_device(self.ip_address)
            device = client.get_device(self.ip_address)
            return client, device

        self.client, self.device = await self.hass.async_add_executor_job(
            _create_client_and_device
        )

        if self.device is None:
            raise UpdateFailed(f"Failed to register device {self.ip_address}")

        # Start client if not already started
        if not self._client_started:
            def _start_client():
                return self.client.start()

            success = await self.hass.async_add_executor_job(_start_client)
            if not success:
                raise UpdateFailed("Failed to start Fluora client")
            self._client_started = True

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        await self._async_setup_client()

        if self.device is None:
            raise UpdateFailed("Device not available")

        def _get_device_info():
            return {
                "ip_address": self.device.ip_address,
                "device_info": self.device.get_device_info(),
                "brightness": self.device.state.brightness,
                "is_on": self.device.state.is_on,
                "last_seen": self.device.last_seen,
            }

        try:
            return await self.hass.async_add_executor_job(_get_device_info)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def async_set_power(self, on: bool) -> bool:
        """Set device power state."""
        if self.device is None:
            return False

        def _set_power():
            return self.device.set_power(on)

        return await self.hass.async_add_executor_job(_set_power)

    async def async_set_brightness(self, brightness: int) -> bool:
        """Set device brightness."""
        if self.device is None:
            return False

        def _set_brightness():
            return self.device.set_brightness(brightness)

        return await self.hass.async_add_executor_job(_set_brightness)

    async def async_shutdown(self) -> None:
        """Shutdown the client."""
        if self.client is not None and self._client_started:
            def _stop_client():
                self.client.stop()

            await self.hass.async_add_executor_job(_stop_client)
