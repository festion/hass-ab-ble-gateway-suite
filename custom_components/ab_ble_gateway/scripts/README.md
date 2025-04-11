# AB BLE Gateway Utility Scripts

This directory contains utility scripts for managing the AB BLE Gateway integration.

## Clean Config Entries

The `clean_config_entries.py` script helps remove failed integration entries from Home Assistant's configuration. This is particularly useful when you have multiple failed instances of the AB BLE Gateway integration.

### Usage

```bash
# First, stop Home Assistant
sudo systemctl stop home-assistant@homeassistant  # For systemd-based installations

# Run the script in dry-run mode first to see what would be changed
./clean_config_entries.py /path/to/your/homeassistant/config --dry-run

# Remove all failed entries
./clean_config_entries.py /path/to/your/homeassistant/config

# Remove only entries for a specific domain (e.g., ab_ble_gateway)
./clean_config_entries.py /path/to/your/homeassistant/config --domain ab_ble_gateway

# Start Home Assistant after cleaning
sudo systemctl start home-assistant@homeassistant  # For systemd-based installations
```

### Important Notes

1. **Always backup your configuration** before using this script.
2. The script will create a backup of the `core.config_entries` file before making changes.
3. Home Assistant should be stopped when running this script.
4. Restart Home Assistant after running this script to apply the changes.