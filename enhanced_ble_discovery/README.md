# Enhanced BLE Device Discovery Add-on

## Overview
This Home Assistant add-on provides advanced Bluetooth Low Energy (BLE) device discovery and management with a user-friendly dashboard interface.

## Features
- Continuous BLE device scanning
- User-friendly discovery dashboard
- Direct device management through the UI
- Signal strength testing for optimal threshold setting
- Easy device addition to Home Assistant
- Persistent device tracking
- Adaptive scan intervals based on time of day and activity
- Enhanced device type detection with extensive MAC address database
- Automatic device categorization based on advertisement data
- Energy-efficient operation
- Comprehensive device categorization with 12 device types

## Setup Instructions

### 1. Install the Add-on
1. Add this repository to your Home Assistant Add-on Store
2. Install the "Enhanced BLE Device Discovery" add-on
3. Configure and start the add-on

### 2. Configure Input Helpers
This add-on requires several input helpers to function correctly. After installing the add-on, you'll need to add the following to your Home Assistant configuration:

#### Option 1: Add to Your Configuration Files

Add these sections to your appropriate configuration files:

**For input_text.yaml:**
```yaml
discovered_ble_devices:
  name: Discovered BLE Devices
  initial: '{}'
  max: 1024
  icon: mdi:bluetooth-transfer

selected_ble_device:
  name: Selected BLE Device
  initial: ''
  max: 255
  icon: mdi:bluetooth
  
ble_device_name:
  name: BLE Device Name
  initial: ''
  max: 255
  icon: mdi:rename
  
ble_device_icon:
  name: BLE Device Icon
  initial: 'mdi:bluetooth'
  max: 255
  icon: mdi:pencil
```

**For input_button.yaml (or in configuration.yaml):**
```yaml
input_button:
  bluetooth_scan:
    name: Bluetooth Scan
    icon: mdi:bluetooth-search
```

**For input_select.yaml:**
```yaml
ble_device_type:
  name: BLE Device Type
  options:
    - presence
    - temperature
    - humidity
    - motion
    - contact
    - button
    - light
    - lock
    - scale
    - wearable
    - speaker
    - other
  initial: presence
  icon: mdi:devices
```

**For input_number.yaml:**
```yaml
ble_rssi_threshold:
  name: BLE RSSI Threshold
  min: -100
  max: -40
  step: 1
  initial: -80
  unit_of_measurement: dBm
  icon: mdi:signal
```

#### Option 2: Use Helper UI
You can also create these helpers using the Home Assistant UI:
1. Go to Configuration → Helpers
2. Click "Add Helper"
3. Create each helper with the attributes listed above

### 3. Restart Home Assistant

After adding the helpers, restart Home Assistant and then restart this add-on.

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `log_level` | Log level (trace, debug, info, warning, error, fatal) | info |
| `scan_interval` | Seconds between BLE scans (10-3600) | 60 |
| `gateway_topic` | MQTT topic for the BLE gateway | BTLE |

## Usage
1. Navigate to the BLE Dashboard from your Home Assistant sidebar
2. Click "Scan for BLE Devices" to discover nearby Bluetooth devices
3. Select a device from the discovered list to configure it
4. Set a friendly name and device type
5. Set the RSSI threshold (use the testing tool to determine optimal value)
6. Click "Add Selected Device" to add the device to Home Assistant

## Troubleshooting

If you're seeing errors about invalid input_text configuration:
1. Make sure you've added the input helpers as described above
2. Ensure each input helper type is in its correct section (input_text, input_button, input_select, input_number)
3. Restart Home Assistant after making configuration changes

## Support
For issues, questions, or feature requests, please open an issue on GitHub.