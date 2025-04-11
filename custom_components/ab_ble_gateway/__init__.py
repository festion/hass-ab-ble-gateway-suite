"""The April Brother BLE Gateway integration."""
from __future__ import annotations
import os
import datetime
from homeassistant.components.bluetooth import BaseHaRemoteScanner
from .util import parse_ap_ble_devices_data, parse_raw_data
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
import msgpack
import json
from homeassistant.helpers.typing import ConfigType
from homeassistant.components import mqtt
from homeassistant.components.bluetooth.const import DOMAIN as BLUETOOTH_DOMAIN
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.setup import async_when_setup
from .const import DOMAIN, SERVICE_CLEAN_FAILED_ENTRIES, ATTR_DRY_RUN
from homeassistant.components.bluetooth import (
    HaBluetoothConnector,
    async_get_advertisement_callback,
    async_register_scanner,
    MONOTONIC_TIME,
)
from homeassistant.const import (
    ATTR_COMMAND,
    ATTR_ENTITY_ID,
    CONF_CLIENT_SECRET,
    CONF_HOST,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STOP,
)
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

import re
TWO_CHAR = re.compile("..")


# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
# No platform entities for this integration - it just registers BLE scanners
PLATFORMS: list[Platform] = []

_LOGGER = logging.getLogger(__name__)


class AbBleScanner(BaseHaRemoteScanner):
    """Scanner for esphome."""

    @callback
    def async_on_mqtt_message(self, msg: ReceiveMessage) -> None:
        """Call the registered callback."""
        try:
            # Counter to track successful device processing
            processed_count = 0
            
            # Try to unpack normally, but catch the exact error we expect
            try:
                # Use msgpack directly but be ready to handle the extra data error
                unpacked_data = msgpack.unpackb(msg.payload, raw=True)
            except Exception as unpack_err:
                # Log the error for diagnostic purposes
                _LOGGER.info(f"Msgpack unpacking error: {unpack_err}")
                
                # Try a workaround for the extra data issue by treating it as two parts
                if "extra data" in str(unpack_err):
                    try:
                        # Use the Unpacker to just get the first object
                        unpacker = msgpack.Unpacker(raw=True)
                        unpacker.feed(msg.payload)
                        unpacked_data = next(unpacker)
                        _LOGGER.info("Successfully extracted partial data from msgpack payload")
                    except Exception as workaround_err:
                        _LOGGER.error(f"Failed to extract data with workaround: {workaround_err}")
                        return
                else:
                    # Different error - just return
                    return
                
            # Check for devices key
            if b'devices' not in unpacked_data:
                _LOGGER.warning("No 'devices' field in MQTT payload")
                return
                
            # Process device data
            devices = unpacked_data[b'devices']
            if not devices:
                _LOGGER.info("No devices in payload")
                return
                
            # We aren't going to try to update the sensor here as we don't have direct access to Home Assistant
            # The sensor should already be set up with the correct gateway info by async_setup_entry
            # This is just a placeholder for future expansion if needed
            _LOGGER.info("Processing BLE gateway data")
            
            # For debugging: log the devices we received
            try:
                # Make sure devices is iterable
                if isinstance(devices, list):
                    device_macs = [d[1] if isinstance(d, list) and len(d) > 1 else str(d) for d in devices]
                    _LOGGER.info(f"Received data for devices: {device_macs[:5]}")
                    if len(device_macs) > 5:
                        _LOGGER.info(f"...and {len(device_macs) - 5} more devices")
                else:
                    _LOGGER.warning(f"Devices data is not a list: {type(devices)}")
            except Exception as e:
                _LOGGER.debug(f"Error logging device info: {e}")
                
            # Process each device, but first make sure devices is iterable
            if not isinstance(devices, list):
                _LOGGER.warning(f"Cannot process devices: expected list but got {type(devices)}")
                return
                
            for d in devices:
                try:
                    # Check that we have a valid device entry
                    if not isinstance(d, (list, tuple)) or len(d) < 2:
                        _LOGGER.debug(f"Skipping invalid device entry: {d}")
                        continue
                        
                    raw_data = parse_ap_ble_devices_data(d)
                    adv = parse_raw_data(raw_data)
                    
                    # Skip invalid data
                    if adv is None:
                        _LOGGER.debug("Invalid advertisement data")
                        continue
                        
                    # Basic validation
                    if not all(k in adv for k in ['address', 'rssi', 'local_name', 'service_uuids', 'service_data', 'manufacturer_data']):
                        _LOGGER.debug(f"Missing required fields in advertisement: {list(adv.keys())}")
                        continue
    
                    # Process the advertisement
                    monotonic_time = MONOTONIC_TIME()
                    self._async_on_advertisement(
                        address=adv['address'].upper(),
                        rssi=adv['rssi'],
                        local_name=adv['local_name'],
                        service_uuids=adv['service_uuids'],
                        service_data=adv['service_data'],
                        manufacturer_data=adv['manufacturer_data'],
                        tx_power=None,
                        details=dict(),
                        advertisement_monotonic_time=[monotonic_time]  # Wrap in a list as it expects an iterable
                    )
                    processed_count += 1
                except Exception as device_err:
                    # Log but continue with other devices
                    _LOGGER.error(f"Error processing device data: {device_err}")
                    continue
            
            # Log the results
            if processed_count > 0:
                _LOGGER.info(f"Successfully processed {processed_count} devices")
                    
        except Exception as err:
            # Log any other errors
            _LOGGER.error(f"Error in MQTT message handler: {err}")
            
        return


def _clean_failed_entries(config_dir, domain=None, dry_run=False):
    """Clean up failed integration config entries."""
    # Path to the storage file
    storage_file = os.path.join(config_dir, ".storage/core.config_entries")
    
    if not os.path.exists(storage_file):
        _LOGGER.error("Error: Config entries file not found at %s", storage_file)
        return 1
    
    # Load current config entries
    with open(storage_file, 'r') as f:
        config_data = json.load(f)
    
    entries = config_data.get("data", {}).get("entries", [])
    original_count = len(entries)
    
    # Create backup
    backup_file = f"{storage_file}.bak"
    if not dry_run:
        with open(backup_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        _LOGGER.info("Created backup at %s", backup_file)
    
    # Filter entries
    if domain:
        filtered_entries = [entry for entry in entries if entry.get("domain") != domain]
        removed = original_count - len(filtered_entries)
        _LOGGER.info("Would remove %d entries for domain '%s'", removed, domain)
    else:
        # Keep only entries that are not in a failed state
        filtered_entries = [entry for entry in entries 
                           if entry.get("state") != "failed_unload"]
        removed = original_count - len(filtered_entries)
        _LOGGER.info("Would remove %d failed entries", removed)
    
    if removed == 0:
        _LOGGER.info("No entries to remove.")
        return 0
    
    # Update the data
    if not dry_run:
        config_data["data"]["entries"] = filtered_entries
        with open(storage_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        _LOGGER.info("Removed %d entries. Original file backed up at %s", removed, backup_file)
        _LOGGER.warning("You should restart Home Assistant to apply these changes.")
    else:
        _LOGGER.info("Dry run complete. No changes were made.")
    
    return 0


async def async_clean_failed_entries(hass, dry_run=False):
    """Service call to clean up failed integration entries."""
    config_dir = hass.config.config_dir
    
    # This must be run in the executor since it involves file operations
    return await hass.async_add_executor_job(
        _clean_failed_entries, config_dir, DOMAIN, dry_run
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AB BLE Gateway component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Register the service
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_CLEAN_FAILED_ENTRIES,
        async_clean_failed_entries,
        schema=vol.Schema({
            vol.Optional(ATTR_DRY_RUN, default=False): cv.boolean,
        }),
    )
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up April Brother BLE Gateway from a config entry."""

    source_id = str(entry.unique_id)
    connectable = False

    connector = HaBluetoothConnector(
        client=None,
        source=source_id,
        can_connect=False,
    )
    scanner = AbBleScanner(scanner_id=source_id, name=entry.title,  connector=connector, connectable=connectable)

    config = entry.as_dict()
    
    # Get mqtt_topic from the correct location in config
    mqtt_topic = config.get('data', {}).get('mqtt_topic')
    
    if not mqtt_topic:
        _LOGGER.error("Missing mqtt_topic in configuration")
        return False
    
    # Create or update the gateway sensor with the proper gateway ID and status
    # This ensures the gateway information is set correctly even before we receive MQTT data
    try:
        # Set up the state directly using the hass.states.async_set method
        attributes = {
            "friendly_name": "BLE Gateway",
            "icon": "mdi:bluetooth-connect",
            "devices": [],
            "gateway_id": "AprilBrother-Gateway4",
            "gateway_status": "Connected",
            "last_scan": datetime.datetime.now().isoformat()
        }
        
        # Create/update the sensor directly 
        hass.states.async_set(
            "sensor.ble_gateway_raw_data", 
            "online", 
            attributes
        )
        _LOGGER.info("Created/Updated BLE gateway status sensor")
    except Exception as err:
        _LOGGER.warning(f"Could not create gateway sensor: {err}")
        
    await mqtt.async_subscribe(hass, mqtt_topic, scanner.async_on_mqtt_message, encoding=None)
    
    # Register the scanner
    unregister = async_register_scanner(hass, scanner, True)
    
    # Store references for future cleanup
    hass.data[DOMAIN][entry.entry_id] = {
        "scanner": scanner,
        "unregister": unregister,
        "hass": hass  # Store hass reference for use in the scanner
    }
    
    # We've already created the gateway sensor above, so nothing more to do here
    _LOGGER.info("BLE Gateway integration setup complete")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if entry.entry_id in hass.data[DOMAIN]:
            # Unregister the scanner
            if "unregister" in hass.data[DOMAIN][entry.entry_id]:
                hass.data[DOMAIN][entry.entry_id]["unregister"]()
            
            # Remove data
            hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
