"""Device registry helper for Koios Clock integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MODEL_MATRX, MODEL_TRANQUIL


def get_device_info(
    coordinator,
    host: str,
    port: int,
    model: str,
) -> DeviceInfo:
    """Get device info for Koios Clock device."""
    about_data = coordinator.data.get("about", {})
    
    # Set appropriate device name based on model
    device_name = "Koios Clock"
    if model == MODEL_MATRX:
        device_name = "Koios MATRX"
    elif model == MODEL_TRANQUIL:
        device_name = "Koios Tranquil"
    
    return DeviceInfo(
        identifiers={(DOMAIN, f"{host}_{port}")},
        name=f"{device_name} ({host})",
        manufacturer="Koios Digital",
        model=model.title(),
        sw_version=about_data.get("version"),
        configuration_url=f"http://{host}:{port}",
    )
