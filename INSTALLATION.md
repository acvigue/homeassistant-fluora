# Fluora Home Assistant Integration - Installation Guide

## Overview

This custom Home Assistant integration provides support for Fluora devices using the `libfluora` library. The integration features automatic device discovery, shared client management, and supports light and switch entities.

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the "+" button
4. Search for "Fluora"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/fluora` folder to your Home Assistant `custom_components` directory
2. Ensure your `custom_components` folder structure looks like:
   ```
   custom_components/
   └── fluora/
       ├── __init__.py
       ├── config_flow.py
       ├── coordinator.py
       ├── light.py
       ├── switch.py
       ├── const.py
       ├── utils.py
       ├── manifest.json
       ├── strings.json
       └── translations/
   ```
3. Restart Home Assistant

## Configuration

### Adding Devices

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Fluora"**
4. The integration will automatically scan for devices on your network
5. Select a discovered device or enter an IP address manually
6. Click **"Submit"**

### Discovery Process

The integration uses the following discovery process:

1. **Automatic Discovery**: Starts a PixelAirClient that listens on UDP port 12345
2. **Device Detection**: Waits 10 seconds for devices to announce themselves
3. **Device Selection**: Presents discovered devices for user selection
4. **Manual Fallback**: Allows manual IP address entry if no devices are found

## Features

### Supported Entities

- **Light**: Controls device lighting with brightness support
- **Switch**: Main power control for the device

### Device Attributes

Each entity provides the following attributes:

- IP Address
- MAC Address
- Device Model
- Nickname (if set)
- Last Seen timestamp

### Shared Client Architecture

- Single `PixelAirClient` instance shared across all devices
- Client starts when first device is added
- Client stops when last device is removed
- Efficient resource usage and network management

## Troubleshooting

### No Devices Found

1. Ensure devices are on the same network as Home Assistant
2. Check that UDP port 12345 is not blocked by firewall
3. Try manual IP address entry in the configuration flow
4. Check Home Assistant logs for discovery errors

### Device Offline

1. Check device power and network connectivity
2. Verify IP address hasn't changed
3. Remove and re-add the integration if necessary

### Commands Not Working

1. Ensure UDP port 6767 (OSC) is accessible on the device
2. Check device-specific logs for command reception
3. Verify device supports the commands being sent

## Logs

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: info
  logs:
    custom_components.fluora: debug
    libfluora: debug
```

## Advanced Configuration

### Custom Client Settings

The integration uses default settings, but the underlying `libfluora` supports:

- Custom MTU sizes
- Binding to specific interfaces
- Adjustable device timeouts

### Network Requirements

- **Incoming**: UDP port 12345 (device state packets)
- **Outgoing**: UDP port 6767 (OSC commands to devices)
- **Discovery**: UDP broadcast capabilities

## Support

- **Documentation**: See README.md files in the integration
- **Issues**: Report issues in the project repository
- **Library**: libfluora documentation for device-specific features
