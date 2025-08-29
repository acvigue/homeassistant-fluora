"""Device coordinator for Fluora integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from libfluora import PixelAirClient, PixelAirDevice, DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class FluoraDeviceCoordinator(DataUpdateCoordinator):
    """Coordinator to manage a single Fluora device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: PixelAirClient,
        ip_address: str,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.ip_address = ip_address
        self.device_info: DeviceInfo | None = None
        self.device: PixelAirDevice | None = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{ip_address}",
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        try:
            # Get device info from discovery
            discovered_devices = await self.hass.async_add_executor_job(
                self.client.get_discovered_devices
            )
            
            if self.ip_address not in discovered_devices:
                # Try to get device from registered devices
                all_devices = await self.hass.async_add_executor_job(
                    self.client.get_all_devices
                )
                
                if self.ip_address in all_devices:
                    self.device = all_devices[self.ip_address]
                    # Get the device info
                    device_info_dict = await self.hass.async_add_executor_job(
                        self.device.get_device_info
                    )
                    
                    return {
                        "device_info": device_info_dict,
                        "device_state": self.device.last_decoded_state,
                        "device_info_detailed": device_info_dict,
                        "is_online": True,
                        "last_seen": device_info_dict.get("last_seen"),
                    }
                else:
                    raise UpdateFailed(f"Device {self.ip_address} not found")
            
            # Update device info
            self.device_info = discovered_devices[self.ip_address]
            
            # Register device if not already registered
            all_devices = await self.hass.async_add_executor_job(
                self.client.get_all_devices
            )
            
            if self.ip_address not in all_devices:
                # Register the device
                await self.hass.async_add_executor_job(
                    self.client.register_device, self.ip_address
                )
                # Get the newly registered device
                all_devices = await self.hass.async_add_executor_job(
                    self.client.get_all_devices
                )
            
            self.device = all_devices.get(self.ip_address)
            
            # Get the latest device state
            device_state = None
            device_info_dict = None
            if self.device:
                device_info_dict = await self.hass.async_add_executor_job(
                    self.device.get_device_info
                )
                # The device state is accessed through the last_decoded_state
                device_state = self.device.last_decoded_state
            
            return {
                "device_info": self.device_info.to_dict() if self.device_info else device_info_dict,
                "device_state": device_state,
                "device_info_detailed": device_info_dict,
                "is_online": True,
                "last_seen": self.device_info.last_seen if self.device_info else None,
            }
            
        except Exception as err:
            _LOGGER.error("Error updating device %s: %s", self.ip_address, err)
            raise UpdateFailed(f"Error updating device {self.ip_address}: {err}")

    @property
    def device_name(self) -> str:
        """Return the device name."""
        if self.device_info and self.device_info.nickname:
            return self.device_info.nickname
        return f"Fluora Device ({self.ip_address})"

    @property
    def device_model(self) -> str | None:
        """Return the device model."""
        if self.device_info:
            return self.device_info.device_model
        return None

    @property
    def device_mac(self) -> str | None:
        """Return the device MAC address."""
        if self.device_info:
            return self.device_info.mac_address
        return None

    async def async_send_command(self, command: str, **kwargs) -> bool:
        """Send a command to the device."""
        if not self.device:
            _LOGGER.error("Device not available for command: %s", command)
            return False
        
        try:
            _LOGGER.debug("Sending command %s to device %s", command, self.ip_address)
            
            # Send commands using the PixelAirDevice API
            if command == "turn_on":
                result = await self.hass.async_add_executor_job(self.device.set_power, True)
            elif command == "turn_off":
                result = await self.hass.async_add_executor_job(self.device.set_power, False)
            elif command == "set_brightness":
                brightness = kwargs.get("brightness", 100)
                result = await self.hass.async_add_executor_job(self.device.set_brightness, brightness)
            else:
                _LOGGER.warning("Unknown command: %s", command)
                return False
            
            return result
            
        except Exception as err:
            _LOGGER.error("Error sending command %s to device %s: %s", command, self.ip_address, err)
            return False
