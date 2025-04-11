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
if [ ! -f "/config/dashboards/btle_dashboard.yaml" ]; then
    bashio::log.info "Creating BLE dashboard..."
    mkdir -p /config/dashboards
    cp /btle_dashboard.yaml /config/dashboards/
fi

# Create input helpers if they don't exist
if [ ! -f "/config/input_text.yaml" ] || ! grep -q "discovered_ble_devices" "/config/input_text.yaml"; then
    bashio::log.info "Ensuring input helpers are available..."
    
    # Check if file exists first
    if [ -f "/config/input_text.yaml" ]; then
        # Append to existing file
        cat /ble_input_text.yaml >> /config/input_text.yaml
    else
        # Create new file
        cp /ble_input_text.yaml /config/input_text.yaml
    fi
    
    # Check if configuration.yaml is available and update it
    if [ -f "/config/configuration.yaml" ]; then
        bashio::log.info "Adding input helper references to configuration.yaml..."
        
        # Check if input_text: is already in configuration.yaml
        if ! grep -q "^input_text:" "/config/configuration.yaml"; then
            # Add input_text entries directly
            echo "" >> /config/configuration.yaml
            echo "# Added by BLE Discovery Add-on" >> /config/configuration.yaml
            echo "input_text:" >> /config/configuration.yaml
            echo "  discovered_ble_devices:" >> /config/configuration.yaml
            echo "    name: Discovered BLE Devices" >> /config/configuration.yaml
            echo "    initial: '{}'" >> /config/configuration.yaml
            echo "    max: 1024" >> /config/configuration.yaml
            echo "    icon: mdi:bluetooth-transfer" >> /config/configuration.yaml
            echo "" >> /config/configuration.yaml
            echo "  selected_ble_device:" >> /config/configuration.yaml
            echo "    name: Selected BLE Device" >> /config/configuration.yaml
            echo "    initial: ''" >> /config/configuration.yaml
            echo "    max: 255" >> /config/configuration.yaml
            echo "    icon: mdi:bluetooth" >> /config/configuration.yaml
            echo "" >> /config/configuration.yaml
            echo "  ble_device_name:" >> /config/configuration.yaml
            echo "    name: BLE Device Name" >> /config/configuration.yaml
            echo "    initial: ''" >> /config/configuration.yaml
            echo "    max: 255" >> /config/configuration.yaml
            echo "    icon: mdi:rename" >> /config/configuration.yaml
            echo "" >> /config/configuration.yaml
            echo "  ble_device_icon:" >> /config/configuration.yaml
            echo "    name: BLE Device Icon" >> /config/configuration.yaml
            echo "    initial: 'mdi:bluetooth'" >> /config/configuration.yaml
            echo "    max: 255" >> /config/configuration.yaml
            echo "    icon: mdi:pencil" >> /config/configuration.yaml
        fi
        
        # Check if input_button: is already in configuration.yaml
        if ! grep -q "^input_button:" "/config/configuration.yaml" && ! grep -q "input_button: !include" "/config/configuration.yaml"; then
            # Add input_button directly
            echo "input_button:" >> /config/configuration.yaml
            echo "  bluetooth_scan:" >> /config/configuration.yaml
            echo "    name: Bluetooth Scan" >> /config/configuration.yaml
            echo "    icon: mdi:bluetooth-search" >> /config/configuration.yaml
        fi
        
        # Check if input_select: is already in configuration.yaml
        if ! grep -q "^input_select:" "/config/configuration.yaml" && ! grep -q "input_select: !include" "/config/configuration.yaml"; then
            echo "# These entries added by BLE Discovery Add-on" >> /config/configuration.yaml
            echo "input_select:" >> /config/configuration.yaml
            echo "  ble_device_type:" >> /config/configuration.yaml
            echo "    name: BLE Device Type" >> /config/configuration.yaml
            echo "    options:" >> /config/configuration.yaml
            echo "      - presence" >> /config/configuration.yaml
            echo "      - temperature" >> /config/configuration.yaml
            echo "      - humidity" >> /config/configuration.yaml
            echo "      - motion" >> /config/configuration.yaml
            echo "      - contact" >> /config/configuration.yaml
            echo "      - button" >> /config/configuration.yaml
            echo "      - light" >> /config/configuration.yaml
            echo "      - lock" >> /config/configuration.yaml
            echo "      - scale" >> /config/configuration.yaml
            echo "      - wearable" >> /config/configuration.yaml
            echo "      - speaker" >> /config/configuration.yaml
            echo "      - other" >> /config/configuration.yaml
            echo "    initial: presence" >> /config/configuration.yaml
            echo "    icon: mdi:devices" >> /config/configuration.yaml
        fi
        
        # Check if input_number: is already in configuration.yaml
        if ! grep -q "^input_number:" "/config/configuration.yaml" && ! grep -q "input_number: !include" "/config/configuration.yaml"; then
            echo "input_number:" >> /config/configuration.yaml
            echo "  ble_rssi_threshold:" >> /config/configuration.yaml
            echo "    name: BLE RSSI Threshold" >> /config/configuration.yaml
            echo "    min: -100" >> /config/configuration.yaml
            echo "    max: -40" >> /config/configuration.yaml
            echo "    step: 1" >> /config/configuration.yaml
            echo "    initial: -80" >> /config/configuration.yaml
            echo "    unit_of_measurement: dBm" >> /config/configuration.yaml
            echo "    icon: mdi:signal" >> /config/configuration.yaml
        fi
        
        # Add a restart notification
        bashio::log.warning "Configuration updated. A Home Assistant restart may be required for all components to appear."
    fi
fi

# Install scripts if they don't exist
if [ ! -f "/config/scripts/ble_scripts.yaml" ]; then
    bashio::log.info "Installing BLE scripts..."
    mkdir -p /config/scripts
    cp /ble_scripts.yaml /config/scripts/
fi

# Announce startup
bashio::log.info "Starting Enhanced BLE Device Discovery..."

# Run the Python script
python3 /ble_discovery.py \
    --log-level "${LOG_LEVEL}" \
    --scan-interval "${SCAN_INTERVAL}" \
    --gateway-topic "${GATEWAY_TOPIC}"
