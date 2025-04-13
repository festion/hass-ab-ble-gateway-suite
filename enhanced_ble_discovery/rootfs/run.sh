#!/bin/bash
source /usr/lib/bashio/bashio.sh

# Get configuration options
LOG_LEVEL=$(bashio::config 'log_level')
SCAN_INTERVAL=$(bashio::config 'scan_interval')
GATEWAY_TOPIC=$(bashio::config 'gateway_topic')

# Ensure the data directory exists
mkdir -p /config/ble_discovery

# Install any additional dependencies if needed
if [ ! -f "/.dependencies_installed" ]; then
    bashio::log.info "Installing additional dependencies..."
    pip3 install --no-cache-dir requests
    
    # Try to install Bluetooth packages if needed and available
    if command -v apk >/dev/null 2>&1; then
        bashio::log.info "Trying to install Bluetooth tools if available..."
        apk add --no-cache bluez bluez-deprecated || bashio::log.warning "Could not install Bluetooth packages, using fallback mode"
    elif command -v apt-get >/dev/null 2>&1; then
        bashio::log.info "Detected Debian/Ubuntu, trying to install Bluetooth tools if available..."
        apt-get update && apt-get install -y --no-install-recommends bluez || bashio::log.warning "Could not install Bluetooth packages, using fallback mode"
    else
        bashio::log.warning "No package manager detected for Bluetooth tools, using fallback mode"
    fi
    
    touch "/.dependencies_installed"
fi

# Create dashboard if it doesn't exist
if [ ! -f "/config/dashboards/btle_dashboard.yaml" ] || [ ! -f "/config/dashboards/btle_combined_dashboard.yaml" ]; then
    bashio::log.info "Creating BLE dashboards..."
    mkdir -p /config/dashboards
    
    # Copy the basic dashboard if it doesn't exist
    if [ ! -f "/config/dashboards/btle_dashboard.yaml" ]; then
        cp /btle_dashboard.yaml /config/dashboards/
    fi
    
    # Copy the enhanced combined dashboard if it doesn't exist
    if [ ! -f "/config/dashboards/btle_combined_dashboard.yaml" ] && [ -f "/btle_combined_dashboard.yaml" ]; then
        cp /btle_combined_dashboard.yaml /config/dashboards/
        bashio::log.info "Installed enhanced combined BLE dashboard - access it at /lovelace/ble-utility"
        
        # Add a persistent notification to inform the user about the dashboard
        curl -s -X POST \
             -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
             -H "Content-Type: application/json" \
             -d '{"message": "BLE Utility Dashboard has been installed at /dashboards/ble-utility. To add it to your sidebar, go to Configuration > Dashboards, find BLE Utility, click the menu icon, and select Show in Sidebar.", "title": "BLE Dashboard Installed", "notification_id": "ble_dashboard_installed"}' \
             http://supervisor/core/api/services/persistent_notification/create
    fi
fi

# Check if input helpers exist
if ! grep -q "discovered_ble_devices" "/config/input_text.yaml" 2>/dev/null; then
    bashio::log.info "Required input helpers not found. Creating setup instructions..."
    
    # Create a notification file to guide the user
    INSTRUCTION_FILE="/config/ble_discovery/setup_instructions.md"
    mkdir -p /config/ble_discovery
    
    cat > "$INSTRUCTION_FILE" << 'EOF'
# BLE Discovery Add-on Setup Instructions

The add-on requires specific input helpers to function correctly. You need to add the following to your Home Assistant configuration.

## Option 1: Add to Your Configuration Files

Add these sections to your appropriate configuration files:

### For input_text.yaml:
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

### For input_button.yaml (or in configuration.yaml):
```yaml
input_button:
  bluetooth_scan:
    name: Bluetooth Scan
    icon: mdi:bluetooth-search
```

### For input_select.yaml:
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

### For input_number.yaml:
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

## Option 2: Use Helper UI

You can also create these helpers using the Home Assistant UI:
1. Go to Configuration → Helpers
2. Click "Add Helper"
3. Create each helper with the attributes listed above

After adding the helpers, restart Home Assistant and then restart this add-on.
EOF

    # Create notice
    bashio::log.warning "========================================================"
    bashio::log.warning "BLE Discovery add-on requires specific input helpers."
    bashio::log.warning "Setup instructions have been saved to:"
    bashio::log.warning "$INSTRUCTION_FILE"
    bashio::log.warning "Please follow these instructions, then restart the add-on."
    bashio::log.warning "========================================================"
    
    # Also create a persistent notification
    curl -s -X POST \
         -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
         -H "Content-Type: application/json" \
         -d '{"message": "BLE Discovery add-on requires configuration. See /config/ble_discovery/setup_instructions.md", "title": "BLE Discovery Setup Required", "notification_id": "ble_discovery_setup"}' \
         http://supervisor/core/api/services/persistent_notification/create
fi

# Install scripts if they don't exist
if [ ! -f "/config/scripts/ble_scripts.yaml" ]; then
    bashio::log.info "Installing BLE scripts..."
    mkdir -p /config/scripts
    cp /ble_scripts.yaml /config/scripts/
fi

# Also install individual scripts to ensure they are available
if [ -f "/scan_and_display_ble_devices.yaml" ]; then
    cp /scan_and_display_ble_devices.yaml /config/scripts/
    bashio::log.info "Installed scan_and_display_ble_devices script"
fi

if [ -f "/test_ble_signal.yaml" ]; then
    cp /test_ble_signal.yaml /config/scripts/
    bashio::log.info "Installed test_ble_signal script"
fi

# Create script.yaml reference if it doesn't exist
if [ ! -f "/config/configuration.yaml" ] || ! grep -q "script: !include scripts.yaml" "/config/configuration.yaml"; then
    if [ -f "/config/configuration.yaml" ]; then
        echo "" >> /config/configuration.yaml
        echo "# Include scripts for BLE discovery" >> /config/configuration.yaml
        echo "script: !include_dir_merge_named scripts/" >> /config/configuration.yaml
        bashio::log.info "Added script include directive to configuration.yaml"
    fi
fi

# Announce startup
bashio::log.info "Starting Enhanced BLE Device Discovery..."

# Run the Python script
python3 /ble_discovery.py \
    --log-level "${LOG_LEVEL}" \
    --scan-interval "${SCAN_INTERVAL}" \
    --gateway-topic "${GATEWAY_TOPIC}"