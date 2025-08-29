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
        client: PixelAirClient,
        ip_address: str,
    ) -> None:
        """Initialize."""
        self.ip_address = ip_address
        self.client = client
        self.device: PixelAirDevice | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{ip_address}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_setup_device(self) -> None:
        """Set up the device registration."""
        if self.device is not None:
            return

        def _register_device():
            # Register device with the shared client
            success = self.client.register_device(self.ip_address)
            if not success:
                # Device might already be registered, try to get it
                device = self.client.get_device(self.ip_address)
                if device is None:
                    raise RuntimeError(f"Failed to register or find device {self.ip_address}")
                return device
            else:
                device = self.client.get_device(self.ip_address)
                if device is None:
                    raise RuntimeError(f"Device {self.ip_address} not found after registration")
                return device

        self.device = await self.hass.async_add_executor_job(_register_device)
        _LOGGER.info("Registered device %s with shared client", self.ip_address)

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        await self._async_setup_device()

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
        """Shutdown the device (unregister from shared client)."""
        if self.device is not None:
            def _unregister_device():
                self.client.unregister_device(self.ip_address)

            await self.hass.async_add_executor_job(_unregister_device)
            _LOGGER.info("Unregistered device %s from shared client", self.ip_address)
