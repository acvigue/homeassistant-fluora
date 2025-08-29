# Fluora Home Assistant Integration

This is a custom Home Assistant integration for Fluora devices using the `libfluora` library.

## Features

- **Automatic Discovery**: Discovers Fluora devices on the local network using the PixelAirClient
- **Shared Client**: Uses a single PixelAirClient instance for the lifetime of the integration
- **Device Identification**: Identifies devices by IP address/hostname (no device_ids)
- **Multiple Platforms**: Supports light and switch entities

## Architecture

### Core Components

1. **`__init__.py`**: Integration setup and teardown

   - Creates and manages the shared PixelAirClient
   - Handles entry setup and cleanup
   - Manages the client lifecycle

2. **`config_flow.py`**: Configuration flow for device discovery

   - Automatic device discovery using PixelAirClient
   - Manual IP address entry fallback
   - Device selection from discovered devices

3. **`coordinator.py`**: Data update coordinator

   - Manages device state updates
   - Handles communication with PixelAirClient
   - Provides device info and state to entities

4. **`light.py`**: Light platform implementation

   - Controls device lighting functionality
   - Supports brightness control
   - Uses ColorMode.BRIGHTNESS

5. **`switch.py`**: Switch platform implementation
   - Main power switch for devices
   - Simple on/off control

### Key Design Decisions

- **Single Client Instance**: The PixelAirClient is created once when the first device is added and shared across all entries
- **IP-based Identification**: Devices are identified by their IP address rather than device IDs
- **Discovery-first Approach**: The config flow prioritizes automatic discovery over manual configuration
- **Coordinator Pattern**: Uses Home Assistant's coordinator pattern for efficient data updates

## Usage

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Fluora"
3. The integration will automatically discover devices on your network
4. Select a device from the discovered list or enter an IP address manually
5. The device will be added with light and switch entities

## Device State

The integration monitors device state through the coordinator, which:

- Polls device information every 30 seconds
- Tracks online/offline status
- Maintains device attributes (model, MAC address, nickname, etc.)

## Error Handling

- Connection failures are handled gracefully with retry logic
- Devices that go offline are marked as unavailable
- Discovery timeouts are handled with fallback to manual entry

## Dependencies

- `libfluora>=0.1.3`: Core library for device communication
- Home Assistant core libraries for integration framework
