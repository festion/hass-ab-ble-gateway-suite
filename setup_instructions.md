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

## Home Assistant Integration Setup

1. Make sure the MQTT integration is already set up in Home Assistant
2. Install the AprilBrother BLE Gateway integration
   - Via HACS (recommended): Add this repository to HACS custom repositories
   - Manual: Copy the `custom_components/ab_ble_gateway` folder to your HA config folder
3. Restart Home Assistant
4. Go to Settings > Devices & Services > Add Integration and search for "AprilBrother BLE Gateway"
5. Configure with the following:
   - MQTT Topic: `xbg` (must match gateway configuration)
   - Gateway ID: Choose a unique ID for this gateway (e.g., "ble_gateway_1")
   - Location: Optional label for this gateway's location

## Dashboard Installation

### Option 1: Verification Dashboard (Recommended for Troubleshooting)

1. Go to Home Assistant UI
2. Navigate to Settings > Dashboards
3. Click "Add Dashboard" then select "From YAML"
4. Copy the contents from `verification_dashboard.yaml`
5. Save the dashboard

This verification dashboard shows:
- Status of all required entities
- Raw MQTT payload display
- Gateway attributes in YAML format
- MQTT reconnect button
- Log viewer shortcut

### Option 2: Minimal Dashboard (For Initial Testing)

1. Go to Home Assistant UI
2. Navigate to Settings > Dashboards
3. Click "Add Dashboard" then select "From YAML"
4. Copy the contents from `minimal_dashboard.yaml`
5. Save the dashboard

The minimal dashboard includes only:
- Raw gateway data display
- MQTT reconnect button
- Device addition form

### Option 3: Basic Dashboard (More Features)

1. Go to Home Assistant UI
2. Navigate to Settings > Dashboards
3. Click "Add Dashboard" then select "From YAML"
4. Copy the contents from `basic_dashboard.yaml`
5. Save the dashboard

Features:
- Gateway status and connection information
- Attribute display (IP, MAC, gateway ID, etc.)
- Device counter
- MQTT reconnect button

### Option 4: Combined Dashboard (Full Features)

Only use this once the basic functionality is confirmed working with simpler dashboards.

1. Go to Home Assistant UI
2. Navigate to Settings > Dashboards
3. Click "Add Dashboard" then select "From YAML"
4. Copy the contents from `btle_combined_dashboard.yaml`
5. Save the dashboard

## Troubleshooting

### Dashboard Not Visible in Sidebar

1. Go to Settings > Dashboards
2. Make sure your dashboard is listed
3. Ensure the "Show in sidebar" toggle is on
4. Try different browsers or clear browser cache

### Entity Not Available Errors

1. Check MQTT connection:
   - Verify MQTT broker is running
   - Check credentials in both HA and gateway
   - Verify topic matches (`xbg` by default)

2. Verify gateway is sending data:
   - Check MQTT Explorer or similar tool to see messages on the topic
   - Verify payload format matches expected JSON structure

3. Restart integration:
   - Go to Settings > Devices & Services
   - Find the AprilBrother BLE Gateway integration
   - Click on it and choose "Reload"

### Missing Required Input Helpers

The integration should create these automatically. If missing:

1. Go to Settings > Devices & Controls > Helpers
2. Create these input text helpers:
   - `input_text.new_ble_device_name` (Label: "New BLE Device Name")
   - `input_text.new_ble_device_mac` (Label: "New BLE Device MAC")
   - `input_text.new_ble_device_category` (Label: "New BLE Device Category")

### Null or Empty Data in Dashboard

1. Check if gateway is sending data:
   - Use the Verification Dashboard to see raw payloads
   - Make sure payload structure matches expected format:
     ```json
     {
       "devices": [[0, "D0:E2:9D:3E:51:BA", -86, "0201061AFF..."]],
       "metadata": {
         "gateway_id": "ble_gateway_1",
         "device_map": {
           "D0:E2:9D:3E:51:BA": "Friendly Name"
         }
       }
     }
     ```

2. Verify integration configuration:
   - Make sure MQTT topic matches what gateway is sending to
   - Ensure gateway ID matches the one in MQTT payload

3. Try the reconnection steps:
   - Use the "Reconnect MQTT" button in the dashboard
   - Check logs for any errors during reconnection
   - Restart Home Assistant if needed

### Missing Entities in Dashboard

1. Check that `sensor.ble_gateway_raw_data` exists:
   - Go to Developer Tools > States
   - Search for "ble_gateway"
   - If missing, the integration may not be correctly set up

2. Verify your MQTT configuration:
   - Make sure gateway is sending properly formatted messages
   - Use MQTT Explorer to confirm messages are arriving
   - Check your Home Assistant logs for MQTT connection issues