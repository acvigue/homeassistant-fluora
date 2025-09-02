"""PixelAirState - Data class for PixelAir device state information."""

from dataclasses import dataclass


@dataclass
class PixelAirState:
    """State information for a PixelAir device."""

    nickname: str | None = None
    model: str | None = None
    serial_number: str | None = None
    mac_address: str | None = None
    brightness: int = 0  # 0-100
    is_on: bool = False  # True if the device is on
