"""
Test/Example script for the Fluora Home Assistant Integration

This script demonstrates how the integration components work together
and can be used for testing the libfluora integration components.
"""

import asyncio
import logging
import sys
from unittest.mock import MagicMock

# Mock Home Assistant modules for testing
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.exceptions'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.components.light'] = MagicMock()
sys.modules['homeassistant.components.switch'] = MagicMock()
sys.modules['voluptuous'] = MagicMock()

from libfluora import PixelAirClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("FluoraIntegrationTest")


async def test_discovery():
    """Test device discovery functionality."""
    print("🔍 Testing Fluora Device Discovery")
    print("=" * 40)
    
    # Create client
    client = PixelAirClient()
    
    try:
        # Start the client
        print("Starting PixelAirClient...")
        if not client.start():
            print("❌ Failed to start client")
            return
        
        print("✅ Client started successfully")
        
        # Wait for discovery
        print("Waiting 10 seconds for device discovery...")
        await asyncio.sleep(10)
        
        # Get discovered devices
        discovered_devices = client.get_discovered_devices()
        print(f"📱 Found {len(discovered_devices)} devices:")
        
        for ip_address, device_info in discovered_devices.items():
            print(f"  • {ip_address}")
            print(f"    Nickname: {device_info.nickname}")
            print(f"    Model: {device_info.device_model}")
            print(f"    MAC: {device_info.mac_address}")
            print(f"    Last seen: {device_info.last_seen}")
            print()
        
        # Test device registration
        if discovered_devices:
            first_device_ip = list(discovered_devices.keys())[0]
            print(f"🔗 Testing device registration for {first_device_ip}")
            
            # Register device
            if client.register_device(first_device_ip):
                print("✅ Device registered successfully")
                
                # Get registered devices
                registered_devices = client.get_all_devices()
                device = registered_devices.get(first_device_ip)
                
                if device:
                    print("📊 Device info:")
                    device_info = device.get_device_info()
                    for key, value in device_info.items():
                        print(f"    {key}: {value}")
                    
                    # Test sending commands
                    print("\n🎮 Testing device control...")
                    print("Turning device on...")
                    device.set_power(True)
                    
                    await asyncio.sleep(2)
                    
                    print("Setting brightness to 50%...")
                    device.set_brightness(50)
                    
                    await asyncio.sleep(2)
                    
                    print("Turning device off...")
                    device.set_power(False)
                    
                else:
                    print("❌ Device not found after registration")
            else:
                print("❌ Failed to register device")
        else:
            print("⚠️  No devices found for testing")
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        client.stop()
        print("✅ Client stopped")


async def simulate_home_assistant_flow():
    """Simulate the Home Assistant integration flow."""
    print("\n🏠 Simulating Home Assistant Integration Flow")
    print("=" * 50)
    
    # This would simulate the flow that happens in Home Assistant:
    # 1. Integration starts -> creates shared PixelAirClient
    # 2. Config flow discovers devices
    # 3. User selects device -> creates coordinator
    # 4. Entities are created and use coordinator
    
    from custom_components.fluora.coordinator import FluoraDeviceCoordinator
    
    # Mock Home Assistant instance
    class MockHass:
        def __init__(self):
            self.data = {}
        
        async def async_add_executor_job(self, func, *args):
            return func(*args)
    
    mock_hass = MockHass()
    client = PixelAirClient()
    
    print("1️⃣  Starting client...")
    if not client.start():
        print("❌ Failed to start client")
        return
    
    print("2️⃣  Waiting for device discovery...")
    await asyncio.sleep(5)
    
    discovered_devices = client.get_discovered_devices()
    if not discovered_devices:
        print("❌ No devices discovered")
        client.stop()
        return
    
    device_ip = list(discovered_devices.keys())[0]
    print(f"3️⃣  Creating coordinator for device {device_ip}")
    
    # Create coordinator (similar to what happens in the integration)
    coordinator = FluoraDeviceCoordinator(mock_hass, client, device_ip)
    
    try:
        print("4️⃣  Performing initial data fetch...")
        await coordinator.async_config_entry_first_refresh()
        
        print(f"✅ Coordinator data: {coordinator.data}")
        
        print("5️⃣  Testing command sending...")
        result = await coordinator.async_send_command("turn_on")
        print(f"Turn on result: {result}")
        
        await asyncio.sleep(2)
        
        result = await coordinator.async_send_command("set_brightness", brightness=75)
        print(f"Set brightness result: {result}")
        
    except Exception as e:
        print(f"❌ Error with coordinator: {e}")
    
    finally:
        client.stop()
        print("✅ Test completed")


async def main():
    """Main test function."""
    print("🧪 Fluora Integration Testing Suite")
    print("=" * 50)
    
    await test_discovery()
    await simulate_home_assistant_flow()


if __name__ == "__main__":
    asyncio.run(main())
