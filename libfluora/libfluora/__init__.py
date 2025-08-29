"""
libfluora - Library for handling fragmented state management and FlatBuffer protocols.
"""

from .fragmented_state_manager import FragmentedStateManager, FragmentedResponse, FragmentInfo
from .pixelair_client import PixelAirClient, DeviceInfo
from .pixelair_device import PixelAirDevice, PixelAirState

# Alias for consistency
DiscoveredDeviceInfo = DeviceInfo

__version__ = "0.1.0"
__all__ = [
    "FragmentedStateManager", 
    "FragmentedResponse", 
    "FragmentInfo",
    "PixelAirClient",
    "PixelAirDevice",
    "PixelAirState",
    "DeviceInfo",
    "DiscoveredDeviceInfo"
]