# AprilBrother BLE Gateway Setup Instructions

## Gateway Configuration

Configure your AprilBrother BLE Gateway with these settings:

1. Access the gateway config page at its IP address (e.g., http://192.168.1.82)
2. Set the following parameters:
   - **MQTT Topic**: `xbg` (this is what the integration uses by default)
   - **MQTT Broker**: Your Home Assistant MQTT broker IP
   - **MQTT Port**: 1883 (or your configured port)
   - **MQTT Username/Password**: Your MQTT credentials
   - **MQTT ID Prefix**: `XBG_` (must be uppercase)

The gateway will then publish all BLE advertisements to the MQTT topic `xbg`.

## Home Assistant Dashboard Setup

### Option 1: Simple Dashboard (Recommended)

1. Go to Settings > Dashboards > Add Dashboard > From YAML
2. Copy and paste the contents of `btle_simple_dashboard.yaml`
3. This dashboard shows:
   - Gateway status
   - Raw device data
   - Device mapping
   - Controls for reconnecting

### Option 2: Advanced Dashboard (Requires Additional Setup)

The advanced dashboard requires additional input helpers and scripts:

1. Add the following to your Home Assistant configuration:
   - Copy the input helpers from `enhance_ble_devices.yaml` to your `configuration.yaml`
   - Copy the automation from `enhance_ble_devices.yaml` to your `automations.yaml`
   - Copy the scripts from `enhance_ble_devices.yaml` to your `scripts.yaml`

2. Go to Settings > Dashboards > Add Dashboard > From YAML
3. Copy and paste the contents of `btle_combined_dashboard.yaml`

## Troubleshooting

If entities are missing:
1. Check that all input helpers are defined in your configuration
2. Ensure scripts are properly defined
3. Verify the MQTT integration is working with your AprilBrother gateway

The logs will show messages like:
```
[custom_components.ab_ble_gateway] Successfully processed advertisement for D0:E2:9D:3E:51:BA
```

If you're seeing these logs but no data appears in the UI, try using the simple dashboard first to verify the data is being correctly received.