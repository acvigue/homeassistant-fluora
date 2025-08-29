"""
PixelAirClient - UDP client for receiving fragmented packets from PixelAir devices.

This module provides the main client class that listens for UDP packets on port 12345,
manages fragmented packet reassembly, and maintains a registry of connected devices.
"""

import socket
import threading
import time
import ipaddress
import netifaces
import logging
from typing import Dict, Optional, List, Union, Any
from dataclasses import dataclass
from pythonosc.osc_message_builder import OscMessageBuilder

from .fragmented_state_manager import FragmentedStateManager
from .pixelair_generated import PixelAirDevice as PixelAirDeviceFB
from .pixelair_device import PixelAirDevice, PixelAirState


@dataclass
class DeviceInfo:
    """Information about a discovered PixelAir device in the registry."""
    ip_address: str
    last_seen: float
    nickname: Optional[str] = None
    mac_address: Optional[str] = None
    device_model: Optional[str] = None

    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = time.time()
    
    def update_from_packet(self, device_state: 'PixelAirDeviceFB') -> None:
        """Update device information from a decoded FlatBuffer packet."""
        # Update device model
        if device_state.Model():
            self.device_model = device_state.Model()
        
        # Update nickname
        if device_state.Nickname() and device_state.Nickname().Value():
            self.nickname = device_state.Nickname().Value()
        
        # Update MAC address from network info
        if device_state.Network() and device_state.Network().MacAddress():
            self.mac_address = device_state.Network().MacAddress()
        
        # Update last seen timestamp
        self.last_seen = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization/display."""
        return {
            'ip_address': self.ip_address,
            'nickname': self.nickname,
            'mac_address': self.mac_address,
            'device_model': self.device_model,
            'last_seen': self.last_seen
        }


# Aliases for consistency
DiscoveredDeviceInfo = DeviceInfo


class PixelAirClient:
    """
    UDP client for receiving fragmented packets from PixelAir devices.
    
    This class manages:
    - UDP socket listening on port 12345
    - Device registry to track connected devices
    - Fragmented packet reassembly per device
    - Packet routing to appropriate devices
    """
    
    def __init__(self, 
                 mtu: int = 2048,
                 bind_address: str = "0.0.0.0",
                 device_timeout: float = 300.0):
        """
        Initialize the PixelAir client.
        
        Args:
            mtu: Maximum transmission unit (default 2048)
            bind_address: Address to bind to (default "0.0.0.0" for all interfaces)
            device_timeout: Timeout for considering devices stale (default 5 minutes)
        """
        self.port = 12345  # Always use port 12345
        self.mtu = mtu
        self.bind_address = bind_address
        self.device_timeout = device_timeout
        
        # Device registry: IP address -> PixelAirDevice (manually registered/configured devices)
        self.devices: Dict[str, PixelAirDevice] = {}
        self.devices_lock = threading.RLock()
        
        # Discovered devices: IP address -> discovery info (separate from registered devices)
        self.discovered_devices: Dict[str, DeviceInfo] = {}
        self.discovered_lock = threading.RLock()
        
        # Fragment managers per device: IP address -> FragmentedStateManager
        self.fragment_managers: Dict[str, FragmentedStateManager] = {}
        self.fragment_lock = threading.RLock()
        
        # Socket and threading
        self.socket: Optional[socket.socket] = None
        self.discovery_socket: Optional[socket.socket] = None
        self.running = False
        self.listen_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None
        self.discovery_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.stats = {
            'packets_received': 0,
            'packets_processed': 0,
            'fragments_received': 0,
            'complete_payloads': 0,
            'errors': 0
        }
        self.stats_lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger(f"PixelAirClient:{self.port}")
    
    def start(self) -> bool:
        """
        Start the UDP listener and background threads.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            self.logger.warning("Client is already running")
            return False
        
        try:
            # Create and bind socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Set receive buffer size based on MTU
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.mtu * 16)
            
            self.socket.bind((self.bind_address, self.port))
            self.socket.settimeout(1.0)  # 1 second timeout for clean shutdown
            
            # Create discovery socket for broadcasting
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            self.running = True
            
            # Start listener thread
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            
            # Start cleanup thread
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()
            
            # Start discovery thread
            self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
            self.discovery_thread.start()
            
            # Send initial discovery broadcast
            self._send_discovery_broadcast()
            
            self.logger.info(f"PixelAirClient started on {self.bind_address}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start client: {e}")
            self.running = False
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def stop(self):
        """Stop the UDP listener and background threads."""
        if not self.running:
            return
        
        self.logger.info("Stopping PixelAirClient...")
        self.running = False
        
        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None
            
        # Close discovery socket
        if self.discovery_socket:
            self.discovery_socket.close()
            self.discovery_socket = None
        
        # Wait for threads to finish
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2.0)
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2.0)
        
        # Shutdown all fragment managers
        with self.fragment_lock:
            for manager in self.fragment_managers.values():
                manager.shutdown()
            self.fragment_managers.clear()
        
        self.logger.info("PixelAirClient stopped")
    
    def register_device(self, ip_address: str) -> bool:
        """
        Register a device in the client registry (creates PixelAirDevice instance).
        
        Args:
            ip_address: IP address of the device to register
            
        Returns:
            True if registered successfully, False if already exists
        """
        with self.devices_lock:
            if ip_address in self.devices:
                self.logger.warning(f"Device {ip_address} already registered")
                return False
            
            # Create PixelAirDevice instance directly (no more circular import)
            device = PixelAirDevice(ip_address)
            self.devices[ip_address] = device
            self.logger.info(f"Registered PixelAir device: {device}")
            return True
    
    def unregister_device(self, ip_address: str) -> bool:
        """
        Unregister a device from the client registry.
        
        Args:
            ip_address: IP address of device to unregister
            
        Returns:
            True if unregistered successfully, False if not found
        """
        with self.devices_lock:
            if ip_address not in self.devices:
                return False
            
            device = self.devices.pop(ip_address)
            self.logger.info(f"Unregistered device: {device}")
            
            # Clean up fragment manager for this device
            with self.fragment_lock:
                if ip_address in self.fragment_managers:
                    self.fragment_managers[ip_address].shutdown()
                    del self.fragment_managers[ip_address]
            
            return True
    
    def get_device(self, ip_address: str) -> Optional[PixelAirDevice]:
        """
        Get a registered device by IP address.
        
        Args:
            ip_address: IP address of the device
            
        Returns:
            PixelAirDevice instance or None if not found
        """
        with self.devices_lock:
            return self.devices.get(ip_address)
    
    def get_all_devices(self) -> Dict[str, PixelAirDevice]:
        """
        Get all registered devices.
        
        Returns:
            Dictionary mapping IP addresses to PixelAirDevice instances
        """
        with self.devices_lock:
            return self.devices.copy()
    
    def get_registered_devices(self) -> Dict[str, PixelAirDevice]:
        """
        Get all registered devices (alias for get_all_devices).
        
        Returns:
            Dictionary mapping IP addresses to PixelAirDevice instances
        """
        return self.get_all_devices()
    
    def get_discovered_devices(self) -> Dict[str, DeviceInfo]:
        """
        Get all discovered devices (not registered/configured).
        
        Returns:
            Dictionary mapping IP addresses to DeviceInfo instances
        """
        with self.discovered_lock:
            return self.discovered_devices.copy()
    
    def clear_discovered_devices(self):
        """Clear the discovered devices list."""
        with self.discovered_lock:
            count = len(self.discovered_devices)
            self.discovered_devices.clear()
            self.logger.info(f"Cleared {count} discovered device(s)")
    
    def remove_discovered_device(self, ip_address: str) -> bool:
        """
        Remove a specific device from the discovered list.
        
        Args:
            ip_address: IP address of the device to remove
            
        Returns:
            True if device was removed, False if not found
        """
        with self.discovered_lock:
            if ip_address in self.discovered_devices:
                del self.discovered_devices[ip_address]
                self.logger.info(f"Removed discovered device: {ip_address}")
                return True
            return False
    
    def get_discovered_device(self, ip_address: str) -> Optional[DeviceInfo]:
        """
        Get a specific discovered device by IP address.
        
        Args:
            ip_address: IP address of the device
            
        Returns:
            DeviceInfo instance or None if not found
        """
        with self.discovered_lock:
            return self.discovered_devices.get(ip_address)
    
    def get_discovered_devices_by_model(self, model: str) -> List[DeviceInfo]:
        """
        Get all discovered devices of a specific model.
        
        Args:
            model: Device model to filter by
            
        Returns:
            List of DeviceInfo instances matching the model
        """
        with self.discovered_lock:
            return [device for device in self.discovered_devices.values() 
                   if device.device_model == model]
    
    def get_discovered_devices_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all discovered devices.
        
        Returns:
            Dictionary with summary information about discovered devices
        """
        with self.discovered_lock:
            devices = list(self.discovered_devices.values())
            
        total_count = len(devices)
        models = {}
        with_nicknames = 0
        with_mac_addresses = 0
        
        for device in devices:
            # Count by model
            model = device.device_model or "Unknown"
            models[model] = models.get(model, 0) + 1
            
            # Count devices with additional info
            if device.nickname:
                with_nicknames += 1
            if device.mac_address:
                with_mac_addresses += 1
        
        return {
            'total_discovered': total_count,
            'models': models,
            'devices_with_nicknames': with_nicknames,
            'devices_with_mac_addresses': with_mac_addresses,
            'devices': [device.to_dict() for device in devices]
        }
    
    def _track_discovered_device(self, ip_address: str, 
                                device_state: Optional[PixelAirDeviceFB] = None) -> DeviceInfo:
        """
        Track a discovered device (does NOT auto-register it).
        
        Args:
            ip_address: IP address of the device (used as the device identifier)
            device_state: Optional decoded device state for extracting additional info
            
        Returns:
            The DeviceInfo for the discovered device
        """
        with self.discovered_lock:
            if ip_address in self.discovered_devices:
                # Update existing discovery info
                device_info = self.discovered_devices[ip_address]
                device_info.last_seen = time.time()
                
                # Update from packet data if available
                if device_state:
                    device_info.update_from_packet(device_state)
            else:
                # Add new discovered device
                device_info = DeviceInfo(
                    ip_address=ip_address,
                    last_seen=time.time(),
                )
                
                # Update from packet data if available
                if device_state:
                    device_info.update_from_packet(device_state)
                
                self.discovered_devices[ip_address] = device_info
                self.logger.debug(f"Discovered new device: {ip_address} "
                                f"(model: {device_info.device_model or 'unknown'}, "
                                f"nickname: {device_info.nickname or 'none'})")
        
        return device_info
    
    def _get_fragment_manager(self, ip_address: str) -> FragmentedStateManager:
        """Get or create a fragment manager for a device."""
        with self.fragment_lock:
            if ip_address not in self.fragment_managers:
                # Create callback that routes complete payloads to the device
                def payload_callback(payload: bytes, is_response: bool):
                    self._handle_complete_payload(ip_address, payload, is_response)
                
                self.fragment_managers[ip_address] = FragmentedStateManager(payload_callback)
            
            return self.fragment_managers[ip_address]
    
    def _handle_complete_payload(self, ip_address: str, payload: bytes, is_response: bool):
        """Handle a complete defragmented payload from a device."""
        with self.stats_lock:
            self.stats['complete_payloads'] += 1
        
        # Check if this is a registered device
        device = self.get_device(ip_address)
        if device is not None:
            # This is a registered device - handle the packet
            device.update_last_seen()
            try:
                device.handle_packet(payload, is_response)
            except Exception as e:
                self.logger.error(f"Error handling packet for device {ip_address}: {e}")
                with self.stats_lock:
                    self.stats['errors'] += 1
        else:
            # This is NOT a registered device - decode and track it as discovered
            try:
                # Decode the payload to extract device information
                device_state = PixelAirDeviceFB.GetRootAs(payload)
                self._track_discovered_device(ip_address, device_state=device_state)
                self.logger.debug(f"Received packet from unregistered device {ip_address} - tracked as discovered")
            except Exception as e:
                # If decoding fails, still track basic discovery info
                self._track_discovered_device(ip_address)
                self.logger.debug(f"Received packet from unregistered device {ip_address} - tracked as discovered (decode failed: {e})")
    
    def _listen_loop(self):
        """Main UDP listening loop."""
        self.logger.info("UDP listener started")
        
        while self.running and self.socket:
            try:
                data, address = self.socket.recvfrom(self.mtu)
                ip_address = address[0]
                self.logger.debug(f"Received {len(data)} bytes from {ip_address}")
                
                with self.stats_lock:
                    self.stats['packets_received'] += 1
                    self.stats['fragments_received'] += 1
                
                # Get fragment manager for this device
                fragment_manager = self._get_fragment_manager(ip_address)
                
                # Process the fragment
                try:
                    fragment_manager.process_buffer(data)
                    with self.stats_lock:
                        self.stats['packets_processed'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Error processing fragment from {ip_address}: {e}")
                    with self.stats_lock:
                        self.stats['errors'] += 1
                
            except socket.timeout:
                # Normal timeout, continue loop
                continue
            except OSError as e:
                if self.running:
                    self.logger.error(f"Socket error in listen loop: {e}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in listen loop: {e}")
                with self.stats_lock:
                    self.stats['errors'] += 1
        
        self.logger.info("UDP listener stopped")
    
    def _cleanup_loop(self):
        """Background cleanup loop for stale devices and connections."""
        while self.running:
            try:
                time.sleep(30)  # Clean up every 30 seconds
                
                if not self.running:
                    break
                
                current_time = time.time()
                stale_devices = []
                stale_discovered = []
                
                # Find stale registered devices
                with self.devices_lock:
                    for ip_address, device in self.devices.items():
                        if device.is_stale(self.device_timeout):
                            stale_devices.append(ip_address)
                
                # Find stale discovered devices
                with self.discovered_lock:
                    for ip_address, device_info in self.discovered_devices.items():
                        if current_time - device_info.last_seen > self.device_timeout:
                            stale_discovered.append(ip_address)
                
                # Remove stale registered devices
                for ip_address in stale_devices:
                    self.logger.info(f"Removing stale registered device: {ip_address}")
                    self.unregister_device(ip_address)
                
                # Remove stale discovered devices
                for ip_address in stale_discovered:
                    self.logger.info(f"Removing stale discovered device: {ip_address}")
                    self.remove_discovered_device(ip_address)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    def get_stats(self) -> Dict:
        """Get client statistics."""
        with self.stats_lock:
            stats = self.stats.copy()
        
        stats['devices_registered'] = len(self.devices)
        stats['devices_discovered'] = len(self.discovered_devices)
        stats['fragment_managers'] = len(self.fragment_managers)
        
        return stats
    
    def reset_stats(self):
        """Reset client statistics."""
        with self.stats_lock:
            for key in self.stats:
                self.stats[key] = 0
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    def _get_interface_ips(self) -> Dict[str, Dict[str, str]]:
        """Get all network interface IP addresses with netmask information."""
        interface_data = {}
        try:
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info.get('addr')
                        netmask = addr_info.get('netmask', '255.255.255.0')  # Default netmask
                        if ip and ip != '127.0.0.1':  # Skip localhost
                            interface_data[interface] = {
                                'ip': ip,
                                'netmask': netmask
                            }
        except Exception as e:
            self.logger.error(f"Error getting interface IPs: {e}")
            # Fallback to basic socket method
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                fallback_ip = s.getsockname()[0]
                interface_data['default'] = {
                    'ip': fallback_ip,
                    'netmask': '255.255.255.0'  # Assume common netmask
                }
                s.close()
            except Exception as fallback_e:
                self.logger.error(f"Fallback IP detection failed: {fallback_e}")
        
        return interface_data
    
    def _send_discovery_packet(self, interface_name: str, interface_ip: str, netmask: str):
        """
        Send a discovery packet on a specific interface.
        
        Args:
            interface_name: Name of the network interface
            interface_ip: IP address of the interface
            netmask: Netmask of the interface
        """
        try:
            # Build OSC message with IP address as ASCII integers
            builder = OscMessageBuilder("/fluoraDiscovery")
            
            # Convert IP address to ASCII integers
            for char in interface_ip:
                builder.add_arg(ord(char))
            
            # Get the OSC message bytes
            msg = builder.build()
            osc_bytes = msg.dgram
            
            # Calculate proper broadcast address using ipaddress module
            try:
                host = ipaddress.IPv4Address(interface_ip)
                network = ipaddress.IPv4Network(f"{interface_ip}/{netmask}", strict=False)
                broadcast_ip = str(network.broadcast_address)
                
                self.logger.debug(f"Interface {interface_name}: IP={interface_ip}, "
                                f"Mask={netmask}, Network={network}, Broadcast={broadcast_ip}")
                
            except (ipaddress.AddressValueError, ipaddress.NetmaskValueError) as e:
                self.logger.warning(f"Failed to calculate broadcast for {interface_ip}/{netmask}: {e}")
                # Fallback to simple .255 replacement
                ip_parts = interface_ip.split('.')
                if len(ip_parts) == 4:
                    broadcast_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
                else:
                    broadcast_ip = "255.255.255.255"
            
            if hasattr(self.discovery_socket, 'sendto') is False:
                self.logger.info("Discovery socket is not available for sending")
                return
            
            # Send to port 9090
            self.discovery_socket.sendto(osc_bytes, (broadcast_ip, 9090))
            self.logger.debug(f"Sent discovery packet from {interface_name} ({interface_ip}) to {broadcast_ip}:9090")
            
        except Exception as e:
            self.logger.error(f"Error sending discovery packet on {interface_name}: {e}")
    
    def _send_discovery_broadcast(self):
        """Send discovery packets on all available interfaces."""
        if not self.discovery_socket:
            return
            
        interface_data = self._get_interface_ips()
        
        if not interface_data:
            self.logger.warning("No network interfaces found for discovery broadcast")
            return
            
        for interface_name, data in interface_data.items():
            self._send_discovery_packet(interface_name, data['ip'], data['netmask'])
            
        self.logger.info(f"Sent discovery broadcast on {len(interface_data)} interface(s)")
    
    def _discovery_loop(self):
        """Background loop for sending discovery packets every minute."""
        while self.running:
            try:
                time.sleep(5)  # Wait 60 seconds between broadcasts
                
                if not self.running:
                    break
                    
                self._send_discovery_broadcast()
                
            except Exception as e:
                self.logger.error(f"Error in discovery loop: {e}")
    
    def __str__(self) -> str:
        return f"PixelAirClient(port={self.port}, devices={len(self.devices)})"
    
    def __repr__(self) -> str:
        return self.__str__()
