"""The April Brother BLE Gateway integration."""
from __future__ import annotations
import os
import datetime
import logging
import logging.handlers
from pathlib import Path
from homeassistant.components.bluetooth import BaseHaRemoteScanner
from .util import parse_ap_ble_devices_data, parse_raw_data
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

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
from .const import (
    DOMAIN, 
    SERVICE_CLEAN_FAILED_ENTRIES, 
    SERVICE_RECONNECT,
    ATTR_DRY_RUN,
    LOGGER_NAME,
    LOG_FILE,
    LOG_FORMAT,
    DEFAULT_LOG_LEVEL
)
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

# Set up custom logging
_LOGGER = logging.getLogger(LOGGER_NAME)

def _setup_logger_sync(hass_config_dir, log_filename, log_format, log_level):
    """Synchronous function to set up the logger, to be run in executor."""
    try:
        # Create logs directory if it doesn't exist
        log_dir = Path(hass_config_dir) / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / log_filename
        
        # Configure the file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB max file size
            backupCount=5,  # Keep 5 backup copies
        )
        
        # Set log format
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)
        
        # Configure the logger
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(getattr(logging, log_level))
        logger.addHandler(file_handler)
        
        return str(log_file)
    except Exception as err:
        return f"Error: {err}"


async def setup_custom_logger(hass: HomeAssistant) -> None:
    """Set up a custom logger for the AB BLE Gateway integration, avoiding blocking calls."""
    try:
        # Run the synchronous logger setup in the executor to avoid blocking the event loop
        result = await hass.async_add_executor_job(
            _setup_logger_sync,
            hass.config.path(),
            LOG_FILE,
            LOG_FORMAT,
            DEFAULT_LOG_LEVEL
        )
        
        if result.startswith("Error:"):
            _LOGGER.error(f"Failed to setup custom logger: {result}")
        else:
            _LOGGER.info(f"AB BLE Gateway logger initialized, logging to {result}")
    except Exception as err:
        _LOGGER.error(f"Exception during custom logger setup: {err}")


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


async def async_reconnect_gateway(hass: HomeAssistant, entity_id=None):
    """Service call to safely reconnect the BLE Gateway."""
    _LOGGER.info(f"Reconnect service called with entity_id: {entity_id}")
    
    try:
        # Map the entity_id to entry_id if provided
        entry_id = None
        if entity_id is not None:
            # Extract the entry_id from configuration_entries
            for domain_entry_id, domain_data in hass.data[DOMAIN].items():
                if "scanner" in domain_data:
                    scanner = domain_data["scanner"]
                    # Basic check to see if this scanner might match the entity
                    if scanner and scanner.name and scanner.name in entity_id:
                        entry_id = domain_entry_id
                        break
            
            if entry_id is None:
                _LOGGER.warning(f"Could not map entity_id {entity_id} to a gateway entry_id")
        
        # If no specific entry ID was provided or found, try to reconnect all gateways
        if entry_id is None:
            _LOGGER.info("Reconnecting all gateways")
            for domain_entry_id, entry_data in hass.data[DOMAIN].items():
                if "scanner" in entry_data:
                    await _reconnect_single_gateway(hass, domain_entry_id)
        else:
            # Reconnect only the specified entry
            if entry_id in hass.data[DOMAIN]:
                _LOGGER.info(f"Reconnecting specific gateway: {entry_id}")
                await _reconnect_single_gateway(hass, entry_id)
            else:
                _LOGGER.warning(f"Cannot reconnect: Entry ID {entry_id} not found")
                
        return True
    except Exception as e:
        _LOGGER.error(f"Error during gateway reconnection: {e}")
        return False


async def _reconnect_single_gateway(hass: HomeAssistant, entry_id):
    """Safely reconnect a single gateway by entry_id."""
    
    entry_data = hass.data[DOMAIN][entry_id]
    
    if "scanner" not in entry_data or "hass" not in entry_data:
        _LOGGER.warning(f"Cannot reconnect {entry_id}: Missing scanner or hass reference")
        return
    
    _LOGGER.info(f"Reconnecting gateway {entry_id}")
    
    scanner = entry_data["scanner"]
    
    try:
        # Get the entry to access its data
        config_entries = hass.config_entries
        entry = next((e for e in config_entries.async_entries(DOMAIN) if e.entry_id == entry_id), None)
        
        if not entry:
            _LOGGER.error(f"Cannot find configuration entry for {entry_id}")
            return
            
        config = entry.as_dict()
        mqtt_topic = config.get('data', {}).get('mqtt_topic')
        
        if not mqtt_topic:
            _LOGGER.error(f"Missing mqtt_topic for {entry_id}")
            return
            
        # Update gateway sensor to show reconnection in progress
        attributes = {
            "friendly_name": "BLE Gateway",
            "icon": "mdi:bluetooth-connect",
            "devices": [],
            "gateway_id": "AprilBrother-Gateway4",
            "gateway_status": "Reconnecting",
            "last_scan": datetime.datetime.now().isoformat()
        }
        
        # Set status to reconnecting
        hass.states.async_set(
            "sensor.ble_gateway_raw_data", 
            "reconnecting", 
            attributes
        )
        
        # Attempt to resubscribe to MQTT topic
        _LOGGER.info(f"Resubscribing to MQTT topic {mqtt_topic}")
        await mqtt.async_subscribe(hass, mqtt_topic, scanner.async_on_mqtt_message, encoding=None)
        
        # Update gateway sensor to show connected again
        attributes["gateway_status"] = "Connected"
        attributes["last_scan"] = datetime.datetime.now().isoformat()
        
        hass.states.async_set(
            "sensor.ble_gateway_raw_data", 
            "online", 
            attributes
        )
        
        _LOGGER.info(f"Successfully reconnected gateway {entry_id}")
        
    except Exception as err:
        _LOGGER.error(f"Error during reconnection of {entry_id}: {err}")
        
        # Update sensor to show error
        attributes = {
            "friendly_name": "BLE Gateway",
            "icon": "mdi:bluetooth-off",
            "devices": [],
            "gateway_id": "AprilBrother-Gateway4", 
            "gateway_status": f"Error: {str(err)}",
            "last_scan": datetime.datetime.now().isoformat()
        }
        
        hass.states.async_set(
            "sensor.ble_gateway_raw_data", 
            "error", 
            attributes
        )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AB BLE Gateway component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Set up the custom logger (using await to properly wait for the async operation)
    await setup_custom_logger(hass)
    _LOGGER.info("AB BLE Gateway integration starting setup")
    
    # Register services
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_CLEAN_FAILED_ENTRIES,
        async_clean_failed_entries,
        schema=vol.Schema({
            vol.Optional(ATTR_DRY_RUN, default=False): cv.boolean,
        }),
    )
    
    # Register reconnect service
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RECONNECT,
        async_reconnect_gateway,
        schema=vol.Schema({
            vol.Optional(ATTR_ENTITY_ID): cv.string,
        }),
    )
    
    _LOGGER.info("AB BLE Gateway integration setup complete with dedicated logging")
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
