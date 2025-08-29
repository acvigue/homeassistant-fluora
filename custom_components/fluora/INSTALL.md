# Installation Guide for Koios Digital Clock Home Assistant Integration

## Prerequisites

- Home Assistant Core 2023.1 or later
- Koios Digital Clock device on your network
- Network access between Home Assistant and the clock device

## Installation Steps

### Option 1: Manual Installation

1. **Download the Integration**

   ```bash
   # Navigate to your Home Assistant custom_components directory
   cd /config/custom_components/

   # Create the integration directory
   mkdir koiosdigital
   ```

2. **Copy Integration Files**

   - Copy all files from the `hass` folder to `/config/custom_components/koiosdigital/`
   - Ensure the following files are present:
     - `__init__.py`
     - `manifest.json`
     - `config_flow.py`
     - `const.py`
     - `coordinator.py`
     - `light.py`
     - `switch.py`
     - `select.py`
     - `number.py`
     - `services.py`
     - `services.yaml`
     - `strings.json`
     - `device.py`
     - `exceptions.py`

3. **Restart Home Assistant**
   - Restart Home Assistant to load the new integration
   - Check the logs for any errors during startup

### Option 2: HACS Installation (If Published)

1. **Add Custom Repository** (if not in default HACS)

   - Open HACS in Home Assistant
   - Go to "Integrations"
   - Click the three dots menu
   - Select "Custom repositories"
   - Add repository URL and select "Integration"

2. **Install Integration**
   - Search for "Koios Digital Clock"
   - Click "Install"
   - Restart Home Assistant

## Configuration

### Automatic Discovery

1. **Enable Discovery**

   - Go to **Configuration** → **Integrations**
   - Click **"+ Add Integration"**
   - The Koios clock should appear in the discovered devices list
   - Click **"Configure"** next to your device

2. **Confirm Device**
   - Verify the device details
   - Click **"Submit"** to add the device

### Manual Configuration

1. **Add Integration Manually**

   - Go to **Configuration** → **Integrations**
   - Click **"+ Add Integration"**
   - Search for **"Koios Digital Clock"**
   - Click on the integration

2. **Enter Connection Details**

   - **Host**: IP address of your clock device
   - **Port**: HTTP port (usually 80)
   - Click **"Submit"**

3. **Verify Connection**
   - The integration will test the connection
   - If successful, the device will be added

## Post-Installation Setup

### 1. Verify Entities

Check that the following entities are created based on your device model:

**All Devices:**

- `light.koiosdigital_backlight`
- `select.koiosdigital_led_effect`
- `number.koiosdigital_led_brightness`

**Fibonacci Clock:**

- `light.koiosdigital_theme`
- `select.koiosdigital_fibonacci_theme`
- `number.koiosdigital_fibonacci_brightness`

**Nixie Clock:**

- `light.koiosdigital_nixie_tubes`
- `switch.koiosdigital_military_time`
- `switch.koiosdigital_blinking_dots`
- `number.koiosdigital_nixie_brightness`

### 2. Test Basic Functions

1. **Test LED Control**

   ```yaml
   service: light.turn_on
   target:
     entity_id: light.koiosdigital_backlight
   data:
     brightness: 200
     rgbw_color: [255, 0, 0, 0]
     effect: "Solid"
   ```

2. **Test Effects**
   ```yaml
   service: select.select_option
   target:
     entity_id: select.koiosdigital_led_effect
   data:
     option: "Rainbow"
   ```

### 3. Create Automation Examples

See the `examples.py` file for automation templates you can adapt.

## Troubleshooting

### Common Issues

#### Device Not Discovered

- **Check Network**: Ensure device and Home Assistant are on same network
- **Check mDNS**: Verify mDNS is working on your network
- **Manual Setup**: Try manual configuration with device IP

#### Connection Errors

- **Firewall**: Check firewall settings on both ends
- **HTTP Access**: Test device API manually: `http://DEVICE_IP/api/about`
- **Network Connectivity**: Ensure network connectivity between devices

#### Entity Updates Slow

- **Polling Interval**: Default is 30 seconds
- **Check Logs**: Look for API errors in Home Assistant logs
- **Device Response**: Verify device is responding to API calls

#### Integration Fails to Load

- **Check Logs**: Look for errors in `home-assistant.log`
- **Dependencies**: Ensure all required packages are installed
- **File Permissions**: Check file permissions in custom_components

### Advanced Troubleshooting

#### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.koiosdigital: debug
```

#### Manual API Testing

Test the device API manually:

```bash
# Get device info
curl http://DEVICE_IP/api/about

# Get LED config
curl http://DEVICE_IP/api/led/config

# Set LED color
curl -X POST http://DEVICE_IP/api/led/config \
  -H "Content-Type: application/json" \
  -d '{"mode": "solid", "color": {"r": 255, "g": 0, "b": 0, "w": 0}}'
```

## Updating the Integration

### Manual Update

1. Download latest files
2. Replace files in `/config/custom_components/koiosdigital/`
3. Restart Home Assistant

### HACS Update

1. Go to HACS → Integrations
2. Find "Koios Digital Clock"
3. Click "Update" if available
4. Restart Home Assistant

## Uninstalling

1. **Remove Integration**

   - Go to Configuration → Integrations
   - Find "Koios Digital Clock"
   - Click three dots → "Delete"

2. **Remove Files** (if desired)

   ```bash
   rm -rf /config/custom_components/koiosdigital/
   ```

3. **Restart Home Assistant**

## Support

For issues and support:

- Check the device firmware is up to date
- Review Home Assistant logs
- Verify network connectivity
- Test API endpoints manually

## Version Compatibility

- **Home Assistant**: 2023.1+
- **Python**: 3.10+
- **Firmware**: Check device compatibility
- **Dependencies**: aiohttp>=3.8.0
