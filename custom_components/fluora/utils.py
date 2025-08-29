"""Utility functions for the Fluora integration."""
from __future__ import annotations

import logging
from typing import Any

from libfluora import DeviceInfo

_LOGGER = logging.getLogger(__name__)


def format_device_name(device_info: DeviceInfo, ip_address: str) -> str:
    """Format a friendly device name from device info."""
    if device_info.nickname:
        return device_info.nickname
    
    if device_info.device_model:
        return f"{device_info.device_model} ({ip_address})"
    
    return f"Fluora Device ({ip_address})"


def format_device_model(device_info: DeviceInfo) -> str:
    """Format device model string."""
    return device_info.device_model or "Unknown Fluora Device"


def is_device_online(device_info: DeviceInfo, timeout: float = 300.0) -> bool:
    """Check if a device is considered online based on last seen time."""
    import time
    
    if not device_info.last_seen:
        return False
    
    return (time.time() - device_info.last_seen) < timeout


def get_device_attributes(device_info: DeviceInfo) -> dict[str, Any]:
    """Get common device attributes for entities."""
    return {
        "ip_address": device_info.ip_address,
        "mac_address": device_info.mac_address,
        "device_model": device_info.device_model,
        "nickname": device_info.nickname,
        "last_seen": device_info.last_seen,
    }
