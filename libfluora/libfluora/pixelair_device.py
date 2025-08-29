"""
PixelAirDevice - Individual device management and OSC control.

This module provides the PixelAirDevice class that handles individual device state,
packet decoding, and OSC command sending.
"""

import socket
import time
import logging
from typing import Dict, Optional, List, Union, Any

from pythonosc.osc_message_builder import OscMessageBuilder

from .pixelair_generated import PixelAirDevice as PixelAirDeviceFB


class PixelAirState:
    """State information for a PixelAir device."""
    nickname: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    
    brightness: int = 0  # 0-100
    is_on: bool = False  # True if the device is on


class PixelAirDevice:
    """
    A PixelAir device that automatically decodes FlatBuffer packets and supports OSC control.
    
    This class handles both receiving state packets on port 12345 and sending OSC commands
    to the device on port 6767.
    """
    
    def __init__(self, ip_address: str):
        """
        Initialize a PixelAir device.
        
        Args:
            ip_address: IP address of the device (used as the device identifier)
        """
        self.ip_address = ip_address
        self.port = 12345  # Always use port 12345 for incoming packets
        self.last_seen = time.time()
        self.name: Optional[str] = None
        
        # Device state tracking
        self.last_decoded_state: Optional[PixelAirDeviceFB] = None
        self.decode_errors = 0
        self.successful_decodes = 0
        self.state = PixelAirState()
        
        # Logger for this device
        self.logger = logging.getLogger(f"PixelAirDevice:{self.ip_address}")
    
    def set_power(self, on: bool) -> bool:
        """
        Set the power state of the device.
        
        Args:
            on: True to turn on, False to turn off
        
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        route = "/SyYOTiXjQBjW"
        params = [1 if on else 0]
        return self._send_osc_message(route, params)
    
    def set_brightness(self, brightness: int) -> bool:
        """
        Set the brightness of the device.
        
        Args:
            brightness: Brightness level (0-100)
        
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        if brightness < 0 or brightness > 100:
            self.logger.error("Brightness must be between 0 and 100")
            return False
        
        route = "/Uv7aMFw5P2lX"
        params = [float(brightness) / 100.0]
        return self._send_osc_message(route, params)
    
    def _send_osc_message(self, route: str, params: List[Union[int, float, str, bool]] = None) -> bool:
        """
        Send a binary OSC message to the device on port 6767.
        
        This is a private helper method for sending OSC commands to the device.
        
        Args:
            route: OSC route/address (e.g., "/device/brightness")
            params: Optional list of parameters to include in the message
        
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if params is None:
            params = []
        
        try:
            # Build the OSC message
            msg_builder = OscMessageBuilder(route)
            
            # Add parameters to the message
            for param in params:
                if isinstance(param, int):
                    msg_builder.add_arg(param, 'i')  # integer
                elif isinstance(param, float):
                    msg_builder.add_arg(param, 'f')  # float
                elif isinstance(param, str):
                    msg_builder.add_arg(param, 's')  # string
                elif isinstance(param, bool):
                    msg_builder.add_arg(param, 'T' if param else 'F')  # true/false
                else:
                    # Try to convert to string as fallback
                    msg_builder.add_arg(str(param), 's')
            
            # Build the binary message
            osc_message = msg_builder.build()
            
            # Create UDP socket and send the message
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(5.0)  # 5 second timeout
                sock.sendto(osc_message.dgram, (self.ip_address, 6767))
                
            self.logger.debug(f"Sent OSC message to {self.ip_address}:6767 - Route: {route}, Params: {params}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send OSC message to {self.ip_address}:6767 - Route: {route}, Error: {e}")
            return False
    
    def handle_packet(self, payload: bytes, is_response: bool):
        """
        Handle a complete defragmented packet from this device.
        
        This method decodes the payload as a PixelAir FlatBuffer and calls
        the appropriate handler method.
        
        Args:
            payload: Complete defragmented payload
            is_response: True if this is a response to a request, False if proactive
        """
        self.update_last_seen()
        
        try:
            # Decode the payload as a PixelAir FlatBuffer
            device_state = PixelAirDeviceFB.GetRootAs(payload)
            self.last_decoded_state = device_state
            self.successful_decodes += 1
            
            # Log successful decode
            self.logger.debug(f"Successfully decoded {len(payload)} byte packet "
                            f"({'response' if is_response else 'proactive'})")
            
            # Call the state packet handler
            self.handle_state_packet(device_state, is_response)
            
        except Exception as e:
            self.decode_errors += 1
            self.logger.error(f"Failed to decode packet: {e}")
            
            # Call the error handler
            self.handle_decode_error(payload, is_response, e)
    
    def handle_state_packet(self, device_state: PixelAirDeviceFB, is_response: bool):
        """
        Handle a decoded PixelAir device state packet.
        
        This method can be overridden by subclasses to implement
        device-specific state handling logic.
        
        Args:
            device_state: Decoded PixelAir device state FlatBuffer
            is_response: True if this is a response to a request, False if proactive
        """
        # Default implementation logs basic device information
        model = device_state.Model() or "Unknown"
        serial = device_state.SerialNumber() or "Unknown"
        
        self.state.model = model
        self.state.serial_number = serial
        
        if device_state.Nickname():
            self.state.nickname = device_state.Nickname().Value()
        
        if device_state.Engine():
            self.state.is_on = device_state.Engine().IsDisplaying().Value()
            if device_state.Engine().Brightness():
                self.state.brightness = device_state.Engine().Brightness().Value() * 100.0
        
        self.logger.info(f"State: {self.state.model} - Power: {'ON' if self.state.is_on else 'OFF'}, "
                        f"Brightness: {self.state.brightness:.1f}%")
    
    def handle_decode_error(self, payload: bytes, is_response: bool, error: Exception):
        """
        Handle a packet decode error.
        
        This method is called when packet decoding fails and can be overridden
        by subclasses to implement custom error handling.
        
        Args:
            payload: Raw payload that failed to decode
            is_response: True if this is a response to a request, False if proactive
            error: The exception that occurred during decoding
        """
        msg_type = "response" if is_response else "proactive"
        self.logger.error(f"Decode error for {msg_type} packet from {self.ip_address}: {error}")
        self.logger.error(f"Payload size: {len(payload)} bytes")
        
        # Log first few bytes for debugging
        preview = payload[:16] if len(payload) >= 16 else payload
        hex_preview = ' '.join(f'{b:02x}' for b in preview)
        self.logger.error(f"Payload preview: {hex_preview}")
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get current device information from the last decoded state.
        
        Returns:
            Dictionary containing device information, or empty dict if no state
        """
        if not self.last_decoded_state:
            return {}
        
        state = self.last_decoded_state
        info = {
            'ip_address': self.ip_address,
            'protocol': state.Protocol(),
            'version': state.Version(),
            'model': state.Model(),
            'serial_number': state.SerialNumber(),
            'rssi': state.Rssi(),
            'last_seen': self.last_seen,
            'successful_decodes': self.successful_decodes,
            'decode_errors': self.decode_errors
        }
        
        # Add optional components
        if state.Nickname():
            info['nickname'] = state.Nickname().Label()
        
        if state.Network():
            info['has_network_config'] = True
        
        if state.Audio():
            info['has_audio_config'] = True
        
        if state.Engine():
            info['has_engine_config'] = True
        
        if state.Clock():
            info['has_clock_config'] = True
        
        return info
    
    def get_protocol_info(self) -> Optional[str]:
        """Get the protocol from the last decoded state."""
        return self.last_decoded_state.Protocol() if self.last_decoded_state else None
    
    def get_device_version(self) -> Optional[str]:
        """Get the version from the last decoded state."""
        return self.last_decoded_state.Version() if self.last_decoded_state else None
    
    def get_device_model(self) -> Optional[str]:
        """Get the model from the last decoded state."""
        return self.last_decoded_state.Model() if self.last_decoded_state else None
    
    def get_serial_number(self) -> Optional[str]:
        """Get the serial number from the last decoded state."""
        return self.last_decoded_state.SerialNumber() if self.last_decoded_state else None
    
    def get_rssi(self) -> int:
        """Get the RSSI from the last decoded state."""
        return self.last_decoded_state.Rssi() if self.last_decoded_state else 0
    
    def get_decode_stats(self) -> Dict[str, int]:
        """
        Get packet decode statistics.
        
        Returns:
            Dictionary with successful_decodes and decode_errors counts
        """
        return {
            'successful_decodes': self.successful_decodes,
            'decode_errors': self.decode_errors,
            'total_packets': self.successful_decodes + self.decode_errors
        }
    
    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = time.time()
    
    def is_stale(self, timeout: float = 300.0) -> bool:
        """
        Check if this device hasn't been seen recently.
        
        Args:
            timeout: Timeout in seconds (default 5 minutes)
            
        Returns:
            True if device hasn't been seen within timeout period
        """
        return time.time() - self.last_seen > timeout
    
    def __str__(self) -> str:
        model = self.get_device_model() or "Unknown"
        serial = self.get_serial_number() or "Unknown"
        return f"PixelAirDevice({self.ip_address}, model={model}, serial={serial})"
    
    def __repr__(self) -> str:
        return self.__str__()
