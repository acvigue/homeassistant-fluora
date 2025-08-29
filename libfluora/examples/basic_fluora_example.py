#!/usr/bin/env python3
"""
Complete PixelAirDevice Control Example

This example demonstrates the proper PixelAir architecture:
1. PixelAirClient listens on port 12345 for state packets from devices
2. PixelAirDevice sends OSC commands to device on port 6767
3. Device automatically responds with state updates sent to client on port 12345
4. Client routes state packets to the appropriate PixelAirDevice instance

Architecture Flow:
- PixelAirDevice.set_power(True) → OSC command to device:6767
- Device receives command and updates its state
- Device sends state packet to client:12345
- Client routes packet to PixelAirDevice.handle_state_packet()

Usage:
    python basic_fluora_example.py
"""

import logging
import time
import sys
from libfluora import PixelAirClient
from libfluora.pixelair_generated import PixelAirDevice as PixelAirDeviceFB

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("PixelAirExample")

def main():
    """Main example function."""
    device_ip = "192.168.4.30"
    
    print("🔧 PixelAir Device Control Example")
    print("=" * 50)
    print(f"Target Device: {device_ip}")
    print("Architecture: Client:12345 ← Device → Device:6767")
    print()
    
    # Create the client
    print("1️⃣  Creating PixelAirClient...")
    client = PixelAirClient()
    
    # Register our custom device
    print(f"2️⃣  Registering device at {device_ip}...")
    success = client.register_device(device_ip, device_id="example_device")
    if not success:
        print("❌ Failed to register device (might already be registered)")
        return 1
    
    # Get reference to our device
    device = client.devices[device_ip]

    # Start the client
    print("3️⃣  Starting client...")
    if not client.start():
        print("❌ Failed to start client")
        return 1
    
    try:
        print("4️⃣  Waiting for device discovery...")
        print("   (Client will automatically receive state packets from device)")
        
        # Wait a moment for the client to settle and potentially receive discovery packets
        time.sleep(2)
        
        print("\n5️⃣  Starting power toggle demonstration...")
        print("   Each command will trigger a state update from the device")
        print("   Toggling device on/off 5 times with 1 second intervals")
        print()
        
        # Toggle power 5 times
        for i in range(5):
            # Turn ON
            print(f"🔵 Cycle {i+1}/5: Turning device ON...")
            success = device.set_power(True)
            if success:
                print("   ✅ ON command sent successfully")
                print("   ⏳ Waiting for state update from device...")
            else:
                print("   ❌ Failed to send ON command")
            
            time.sleep(1)  # Wait 1 second (device should send state update during this time)
            
            # Turn OFF
            print(f"🔴 Cycle {i+1}/5: Turning device OFF...")
            success = device.set_power(False)
            if success:
                print("   ✅ OFF command sent successfully")
                print("   ⏳ Waiting for state update from device...")
            else:
                print("   ❌ Failed to send OFF command")
            
            time.sleep(1)  # Wait 1 second (device should send state update during this time)
            print()
        
        print("6️⃣  Demonstration complete!")
        
        # Show final device information if available
        info = device.get_device_info()
        if info:
            print("\n📊 Final Device Information:")
            for key, value in info.items():
                print(f"   {key}: {value}")
            
            # Show decode statistics
            stats = device.get_decode_stats()
            print(f"\n📈 Decode Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
        
        print("\n✨ Example completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during example: {e}")
        logger.exception("Example failed")
        return 1
    finally:
        # Clean shutdown
        print("\n7️⃣  Stopping client...")
        client.stop()
        print("✅ Client stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
