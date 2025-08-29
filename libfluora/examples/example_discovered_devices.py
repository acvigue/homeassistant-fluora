#!/usr/bin/env python3
"""
Example script demonstrating the new typed discovered device registry.

This script shows how to use the DeviceInfo class and the 
enhanced discovery features of the PixelAirClient.
"""

import time
import logging
from libfluora.pixelair_client import PixelAirClient, DeviceInfo

# Set up logging to see discovery messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def print_discovered_devices(client: PixelAirClient):
    """Print information about all discovered devices."""
    devices = client.get_discovered_devices()
    
    if not devices:
        print("No devices discovered yet.")
        return
    
    print(f"\n--- Discovered Devices ({len(devices)} total) ---")
    for ip_address, device_info in devices.items():
        print(f"IP Address: {ip_address}")
        print(f"  Nickname: {device_info.nickname or 'Not set'}")
        print(f"  Model: {device_info.device_model or 'Unknown'}")
        print(f"  MAC Address: {device_info.mac_address or 'Not available'}")
        print(f"  Last Seen: {time.ctime(device_info.last_seen)}")
        print()

def print_discovery_summary(client: PixelAirClient):
    """Print a summary of discovered devices."""
    summary = client.get_discovered_devices_summary()
    
    print(f"\n--- Discovery Summary ---")
    print(f"Total discovered devices: {summary['total_discovered']}")
    print(f"Devices with nicknames: {summary['devices_with_nicknames']}")
    print(f"Devices with MAC addresses: {summary['devices_with_mac_addresses']}")
    
    if summary['models']:
        print("\nDevices by model:")
        for model, count in summary['models'].items():
            print(f"  {model}: {count}")

def main():
    """Main function demonstrating discovered device registry usage."""
    print("PixelAir Device Discovery Example")
    print("================================")
    
    # Create client with shorter timeout for this example
    client = PixelAirClient(device_timeout=120.0)  # 2 minutes
    
    try:
        # Start the client
        if not client.start():
            print("Failed to start PixelAir client")
            return
        
        print("PixelAir client started. Listening for devices...")
        print("Press Ctrl+C to stop\n")
        
        # Monitor for discovered devices
        last_check = time.time()
        
        while True:
            time.sleep(5)  # Check every 5 seconds
            
            current_time = time.time()
            if current_time - last_check >= 10:  # Print summary every 10 seconds
                print_discovered_devices(client)
                print_discovery_summary(client)
                last_check = current_time
            
            # Example: Get devices by specific model
            pixelair_devices = client.get_discovered_devices_by_model("PixelAir")
            if pixelair_devices:
                print(f"Found {len(pixelair_devices)} PixelAir model devices")
            
            # Example: Get specific device info
            example_ip = "192.168.1.100"
            device = client.get_discovered_device(example_ip)
            if device:
                print(f"Device at {example_ip}: {device.to_dict()}")
    
    except KeyboardInterrupt:
        print("\nStopping...")
    
    finally:
        client.stop()
        print("Client stopped.")

if __name__ == "__main__":
    main()
