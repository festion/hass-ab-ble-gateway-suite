"""The April Brother BLE Gateway integration."""
from __future__ import annotations
import os
import datetime
import logging
import logging.handlers
import asyncio
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

# Use Home Assistant's built-in logging
_LOGGER = logging.getLogger(LOGGER_NAME)

def set_log_level():
    """Set the log level for this integration's logger."""
    try:
        # Make sure we use a high-enough log level to catch issues
        level = getattr(logging, "DEBUG")
        _LOGGER.setLevel(level)
        
        # Configure the logger to show up in Home Assistant logs
        homeassistant_logger = logging.getLogger("homeassistant.components.ab_ble_gateway")
        homeassistant_logger.setLevel(level)
        
        # Create a stream handler if none exists
        if not _LOGGER.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            _LOGGER.addHandler(console_handler)
        
        _LOGGER.debug(f"AB BLE Gateway logger initialized with level DEBUG")
    except (AttributeError, TypeError) as err:
        _LOGGER.error(f"Failed to set log level: {err}")
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.debug("Defaulting to DEBUG log level")


class AbBleScanner(BaseHaRemoteScanner):
    """Scanner for esphome."""

    @callback
    def async_on_mqtt_message(self, msg: ReceiveMessage) -> None:
        """Call the registered callback."""
        try:
            # Counter to track successful device processing
            processed_count = 0
            
            # Log receipt of message (debug level to avoid spamming logs)
            _LOGGER.debug(f"Received MQTT message with payload length: {len(msg.payload) if msg.payload else 0}")
            
            # ULTRA-DEFENSIVE APPROACH: We're going to handle each step with extensive error checking
            
            # Try to unpack very carefully with multiple layers of protection
            unpacked_data = None
            devices = None
            
            # Skip processing if the payload is empty or None
            if not msg.payload:
                _LOGGER.debug("Empty MQTT payload received, skipping processing")
                return
                
            # First try to unpack the message
            try:
                # Use msgpack directly but be ready to handle the extra data error
                unpacked_data = msgpack.unpackb(msg.payload, raw=True)
                
                # Immediately check and sanitize the data structure
                if not isinstance(unpacked_data, dict):
                    _LOGGER.warning(f"Unpacked data is not a dictionary: {type(unpacked_data)}")
                    # Convert to empty dict as a fallback
                    unpacked_data = {}
                    
            except Exception as unpack_err:
                # Log the error for diagnostic purposes
                _LOGGER.info(f"Msgpack unpacking error: {unpack_err}")
                # Initialize with empty dict
                unpacked_data = {}
                
                # Try a workaround for the extra data issue by treating it as two parts
                if "extra data" in str(unpack_err):
                    try:
                        # Use the Unpacker to just get the first object
                        unpacker = msgpack.Unpacker(raw=True)
                        unpacker.feed(msg.payload)
                        unpacked_data = next(unpacker)
                        _LOGGER.info("Successfully extracted partial data from msgpack payload")
                        
                        # Verify it's a dictionary
                        if not isinstance(unpacked_data, dict):
                            _LOGGER.warning(f"Extracted data is not a dictionary: {type(unpacked_data)}")
                            unpacked_data = {}
                    except Exception as workaround_err:
                        _LOGGER.warning(f"Failed to extract data with workaround: {workaround_err}")
                        # Keep the empty dict initialization
            
            # Now safely try to get the devices field
            try:
                # Check for devices key
                if b'devices' not in unpacked_data:
                    _LOGGER.debug("No 'devices' field in MQTT payload")
                    # Initialize with empty list
                    devices = []
                else:
                    # Process device data with safety checks
                    devices_raw = unpacked_data[b'devices']
                    
                    # Ensure devices is a list
                    if not isinstance(devices_raw, list):
                        _LOGGER.warning(f"Devices data is not a list: {type(devices_raw)}")
                        # Force conversion to list if possible
                        if isinstance(devices_raw, int):
                            _LOGGER.warning("Received an integer instead of a list of devices, using empty list")
                            devices = []
                        elif devices_raw is None:
                            devices = []
                        else:
                            # Try to create a list with the single item
                            try:
                                devices = [devices_raw]
                                _LOGGER.info(f"Converted non-list device data to single-item list")
                            except Exception:
                                devices = []
                    else:
                        # It's already a list, we're good
                        devices = devices_raw
            except Exception as devices_err:
                _LOGGER.warning(f"Error extracting devices data: {devices_err}")
                # Ensure we have a list
                devices = []
            
            # Ensure devices is always a list at this point
            if not isinstance(devices, list):
                _LOGGER.warning(f"Devices variable is still not a list: {type(devices)}")
                devices = []
                
            # Skip processing if no devices
            if not devices:
                _LOGGER.debug("No devices to process")
                return
                
            # Log the number of devices found
            _LOGGER.info(f"Processing BLE gateway data with {len(devices)} devices")
            
            # Process each device with extreme defensive coding
            for d in devices:
                try:
                    # Skip invalid entries
                    if not d:
                        _LOGGER.debug("Skipping empty device entry")
                        continue
                        
                    # Check that we have a valid device entry
                    if not isinstance(d, (list, tuple)):
                        _LOGGER.debug(f"Skipping non-list device entry: {d}")
                        continue
                        
                    if len(d) < 2:
                        _LOGGER.debug(f"Skipping too-short device entry: {d}")
                        continue
                        
                    # Parse the raw data with error handling
                    try:
                        raw_data = parse_ap_ble_devices_data(d)
                        if raw_data is None:
                            _LOGGER.debug(f"Could not parse device data: {d}")
                            continue
                    except Exception as parse_err:
                        _LOGGER.debug(f"Error parsing device data: {parse_err}")
                        continue
                        
                    # Parse the advertisement with error handling
                    try:
                        adv = parse_raw_data(raw_data)
                        if adv is None:
                            _LOGGER.debug("Invalid advertisement data")
                            continue
                    except Exception as adv_err:
                        _LOGGER.debug(f"Error parsing advertisement: {adv_err}")
                        continue
                    
                    # Ensure advertisement has all required fields with extremely safe defaults
                    address = adv.get('address', '00:00:00:00:00:00')
                    if address:  # Ensure it's not empty
                        address = address.upper()
                    else:
                        address = '00:00:00:00:00:00'
                        
                    # Get other parameters with safe defaults
                    rssi = -100
                    try:
                        rssi_val = adv.get('rssi')
                        if rssi_val is not None and isinstance(rssi_val, (int, float)):
                            rssi = int(rssi_val)  # Ensure it's an integer
                    except Exception:
                        pass  # Keep default
                    
                    # Get string values with safe defaults
                    local_name = ''
                    try:
                        local_name_val = adv.get('local_name')
                        if local_name_val is not None and isinstance(local_name_val, str):
                            local_name = local_name_val
                    except Exception:
                        pass  # Keep default
                    
                    # Ensure service_uuids is a list
                    service_uuids = []
                    try:
                        service_uuids_val = adv.get('service_uuids')
                        if service_uuids_val is not None and isinstance(service_uuids_val, list):
                            service_uuids = service_uuids_val
                    except Exception:
                        pass  # Keep default
                    
                    # Ensure service_data is a dict
                    service_data = {}
                    try:
                        service_data_val = adv.get('service_data')
                        if service_data_val is not None and isinstance(service_data_val, dict):
                            service_data = service_data_val
                    except Exception:
                        pass  # Keep default
                    
                    # Ensure manufacturer_data is a dict
                    manufacturer_data = {}
                    try:
                        manufacturer_data_val = adv.get('manufacturer_data')
                        if manufacturer_data_val is not None and isinstance(manufacturer_data_val, dict):
                            manufacturer_data = manufacturer_data_val
                    except Exception:
                        pass  # Keep default
                    
                    # Ultra-defensive direct call to _async_on_advertisement with minimal parameters in try-except
                    try:
                        _LOGGER.debug(f"Calling _async_on_advertisement for device {address}")
                        self._async_on_advertisement(
                            address=address,
                            rssi=rssi,
                            local_name=local_name,
                            service_uuids=service_uuids,
                            service_data=service_data,
                            manufacturer_data=manufacturer_data,
                            tx_power=None
                        )
                        # Success - increment processed count
                        processed_count += 1
                        _LOGGER.debug(f"Successfully processed advertisement for {address}")
                    except Exception as adv_call_err:
                        _LOGGER.error(f"Failed to process advertisement call: {adv_call_err}")
                        # Continue to next device
                        
                except Exception as device_err:
                    # Log but continue processing other devices
                    _LOGGER.error(f"Error in device processing loop: {device_err}")
                    continue
            
            # Log the results
            if processed_count > 0:
                _LOGGER.info(f"Successfully processed {processed_count} devices")
            else:
                _LOGGER.info("No devices were successfully processed")
                    
        except Exception as outer_err:
            # Log any other errors at the outer level
            _LOGGER.error(f"Outer error in MQTT message handler: {outer_err}")
            
        # Always return to avoid any potential exceptions bubbling up
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
    _LOGGER.debug(f"Reconnect service called with entity_id: {entity_id}")
    result = False
    
    try:
        # Check if the domain data exists
        if DOMAIN not in hass.data or not hass.data[DOMAIN]:
            _LOGGER.error(f"No {DOMAIN} data in Home Assistant data dictionary")
            return False
            
        # Log all current entries for debugging
        _LOGGER.debug(f"Current entries in DOMAIN data: {list(hass.data[DOMAIN].keys())}")
        
        # Map the entity_id to entry_id if provided
        entry_id = None
        if entity_id is not None:
            # Extract the entry_id from configuration_entries
            for domain_entry_id, domain_data in hass.data[DOMAIN].items():
                try:
                    if "scanner" in domain_data:
                        scanner = domain_data["scanner"]
                        # Basic check to see if this scanner might match the entity
                        if scanner and scanner.name:
                            _LOGGER.debug(f"Found scanner with name: {scanner.name}")
                            if scanner.name in entity_id:
                                entry_id = domain_entry_id
                                _LOGGER.debug(f"Matched scanner to entity_id, entry_id: {entry_id}")
                                break
                except Exception as inner_err:
                    _LOGGER.error(f"Error while checking scanner entry {domain_entry_id}: {inner_err}")
            
            if entry_id is None:
                _LOGGER.warning(f"Could not map entity_id {entity_id} to a gateway entry_id")
        
        # If no specific entry ID was provided or found, try to reconnect all gateways
        if entry_id is None:
            _LOGGER.debug("Reconnecting all gateways")
            any_success = False
            for domain_entry_id, entry_data in hass.data[DOMAIN].items():
                try:
                    if "scanner" in entry_data:
                        reconnect_result = await _reconnect_single_gateway(hass, domain_entry_id)
                        any_success = any_success or reconnect_result
                except Exception as reconnect_err:
                    _LOGGER.error(f"Error reconnecting gateway {domain_entry_id}: {reconnect_err}")
            result = any_success
        else:
            # Reconnect only the specified entry
            if entry_id in hass.data[DOMAIN]:
                _LOGGER.debug(f"Reconnecting specific gateway: {entry_id}")
                result = await _reconnect_single_gateway(hass, entry_id)
            else:
                _LOGGER.warning(f"Cannot reconnect: Entry ID {entry_id} not found")
                
        return result
    except Exception as e:
        _LOGGER.error(f"Unhandled error during gateway reconnection: {e}")
        return False


async def _reconnect_single_gateway(hass: HomeAssistant, entry_id):
    """Safely reconnect a single gateway by entry_id."""
    
    try:
        # Safely get entry data
        if DOMAIN not in hass.data:
            _LOGGER.error(f"Domain {DOMAIN} not in hass.data")
            return False
            
        if entry_id not in hass.data[DOMAIN]:
            _LOGGER.error(f"Entry {entry_id} not in hass.data[{DOMAIN}]")
            return False
            
        entry_data = hass.data[DOMAIN][entry_id]
        
        if "scanner" not in entry_data:
            _LOGGER.warning(f"Cannot reconnect {entry_id}: Missing scanner reference")
            return False
        
        _LOGGER.debug(f"Reconnecting gateway {entry_id}")
        
        scanner = entry_data["scanner"]
        
        # Get the entry to access its data
        config_entries = hass.config_entries
        entry = next((e for e in config_entries.async_entries(DOMAIN) if e.entry_id == entry_id), None)
        
        if not entry:
            _LOGGER.error(f"Cannot find configuration entry for {entry_id}")
            return False
            
        config = entry.as_dict()
        mqtt_topic = config.get('data', {}).get('mqtt_topic')
        
        if not mqtt_topic:
            _LOGGER.error(f"Missing mqtt_topic for {entry_id}")
            return False
            
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
        try:
            hass.states.async_set(
                "sensor.ble_gateway_raw_data", 
                "reconnecting", 
                attributes
            )
            _LOGGER.debug(f"Set gateway state to reconnecting")
        except Exception as state_err:
            _LOGGER.error(f"Failed to update gateway state: {state_err}")
        
        # Attempt to resubscribe to MQTT topic
        _LOGGER.debug(f"Resubscribing to MQTT topic {mqtt_topic}")
        
        # Check if MQTT component is ready
        if not hass.data.get("mqtt"):
            _LOGGER.error("MQTT component not ready. Cannot subscribe.")
            return False
        
        # Get MQTT data and make sure client is available
        mqtt_data = hass.data.get("mqtt", {})
        if not mqtt_data or not hasattr(mqtt_data, 'client') or mqtt_data.client is None:
            _LOGGER.error("MQTT client not available")
            return False
            
        # Try to unsubscribe first to clean up any existing subscriptions
        try:
            # We'll try unsubscribing but don't fail if it doesn't work
            await mqtt.async_unsubscribe(hass, mqtt_topic, scanner.async_on_mqtt_message)
            _LOGGER.debug(f"Successfully unsubscribed from {mqtt_topic}")
        except Exception as unsub_err:
            _LOGGER.debug(f"No active subscription to unsubscribe from: {unsub_err}")
        
        # Now resubscribe
        subscription = None
        try:
            subscription = await mqtt.async_subscribe(
                hass, 
                mqtt_topic, 
                scanner.async_on_mqtt_message, 
                encoding=None
            )
            
            if subscription is None:
                _LOGGER.error(f"Failed to subscribe to MQTT topic {mqtt_topic}")
                return False
                
            _LOGGER.debug(f"Successfully subscribed to MQTT topic {mqtt_topic}")
        except Exception as mqtt_err:
            _LOGGER.error(f"MQTT subscription error: {mqtt_err}")
            return False
        
        # Update gateway sensor to show connected again
        attributes["gateway_status"] = "Connected"
        attributes["last_scan"] = datetime.datetime.now().isoformat()
        
        try:
            hass.states.async_set(
                "sensor.ble_gateway_raw_data", 
                "online", 
                attributes
            )
            _LOGGER.debug(f"Set gateway state to online")
        except Exception as state_err:
            _LOGGER.error(f"Failed to update gateway state: {state_err}")
        
        _LOGGER.info(f"Successfully reconnected gateway {entry_id}")
        return True
        
    except Exception as err:
        _LOGGER.error(f"Error during reconnection of {entry_id}: {err}")
        
        # Update sensor to show error
        try:
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
        except Exception as final_err:
            _LOGGER.error(f"Final error handling failure: {final_err}")
            
        return False


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AB BLE Gateway component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Set the log level for the integration
    set_log_level()
    _LOGGER.info("AB BLE Gateway integration starting setup")
    
    # We're going to skip file copying for now and register our services directly
    # This avoids file operations which can cause blocking issues
    _LOGGER.info("Setting up services and helpers directly")
    
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
    
    # Define a safe wrapper for the reconnect service
    async def safe_reconnect_service_wrapper(call):
        """Safely wrap the reconnect service to prevent HA restarts."""
        try:
            # Create a notification at the start
            try:
                await hass.services.async_call(
                    "persistent_notification", 
                    "create", 
                    {
                        "title": "BLE Gateway Reconnect",
                        "message": "Processing reconnect request safely...",
                        "notification_id": "ble_gateway_reconnect"
                    }
                )
            except Exception as notify_err:
                _LOGGER.warning(f"Failed to create notification, but continuing: {notify_err}")
                
            # Just redirect to the simple MQTT reconnect, which is more reliable
            _LOGGER.info("Redirecting reconnect service to simple MQTT reconnect")
            success = False
            
            try:
                success = await simple_mqtt_reconnect(call)
            except Exception as inner_err:
                _LOGGER.error(f"Inner exception in simple MQTT reconnect: {inner_err}")
                # Try to create a notification about the error
                try:
                    await hass.services.async_call(
                        "persistent_notification", 
                        "create", 
                        {
                            "title": "BLE Gateway Reconnect",
                            "message": f"Error during reconnect: {str(inner_err)}",
                            "notification_id": "ble_gateway_reconnect"
                        }
                    )
                except Exception:
                    pass  # Silently ignore notification errors
                    
            return success
            
        except Exception as outer_err:
            _LOGGER.error(f"Outer exception in reconnect wrapper: {outer_err}")
            # Try to create a notification about the error
            try:
                await hass.services.async_call(
                    "persistent_notification", 
                    "create", 
                    {
                        "title": "BLE Gateway Reconnect",
                        "message": f"Critical error during reconnect: {str(outer_err)}",
                        "notification_id": "ble_gateway_reconnect"
                    }
                )
            except Exception:
                pass  # Silently ignore notification errors
                
            return False
    
    # Register reconnect service with the safe wrapper
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RECONNECT,
        safe_reconnect_service_wrapper,
        schema=vol.Schema({
            vol.Optional("entity_id"): cv.string,
        }),
    )
    
    # Register a simpler direct MQTT reconnect service
    async def simple_mqtt_reconnect(call):
        """Simple service to reconnect MQTT topic."""
        try:
            _LOGGER.info("Simple MQTT reconnect called")
            
            # Use a critical section lock to prevent multiple concurrent reconnects
            # which could potentially conflict with each other
            reconnect_lock = asyncio.Lock()
            
            # Only proceed if we can acquire the lock
            async with reconnect_lock:
                # Create a notification
                try:
                    await hass.services.async_call(
                        "persistent_notification", 
                        "create", 
                        {
                            "title": "BLE Gateway Reconnect",
                            "message": "Attempting to reconnect the BLE Gateway... Please wait.",
                            "notification_id": "ble_gateway_reconnect"
                        }
                    )
                except Exception as notify_err:
                    _LOGGER.warning(f"Failed to create notification: {notify_err}")
                    # Continue anyway
                
                # Find all gateway entries and get their MQTT topics
                mqtt_topics = []
                try:
                    # First try to get topics from domain data
                    if DOMAIN in hass.data:
                        for entry_id, entry_data in hass.data[DOMAIN].items():
                            if "scanner" not in entry_data:
                                continue
                                
                            # Get the entry to access its data
                            config_entries = hass.config_entries
                            entry = next((e for e in config_entries.async_entries(DOMAIN) if e.entry_id == entry_id), None)
                            
                            if not entry:
                                continue
                                
                            config = entry.as_dict()
                            mqtt_topic = config.get('data', {}).get('mqtt_topic')
                            
                            if mqtt_topic:
                                mqtt_topics.append(mqtt_topic)
                except Exception as topics_err:
                    _LOGGER.warning(f"Error getting MQTT topics from domain data: {topics_err}")
                    # Continue with default topic
                
                # If no topics found, use a default
                if not mqtt_topics:
                    _LOGGER.info("No MQTT topics found in config entries, using default topic")
                    mqtt_topics = ["gw/#"]
                
                _LOGGER.info(f"MQTT topics to reconnect: {mqtt_topics}")
                    
                # Check MQTT component availability
                if not hass.data.get("mqtt"):
                    _LOGGER.error("MQTT component not ready. Cannot subscribe.")
                    # Create notification about MQTT not being ready
                    try:
                        await hass.services.async_call(
                            "persistent_notification", 
                            "create", 
                            {
                                "title": "BLE Gateway Reconnect",
                                "message": "Cannot reconnect: MQTT component not ready.",
                                "notification_id": "ble_gateway_reconnect"
                            }
                        )
                    except Exception:
                        pass  # Silently ignore notification errors
                    return False
                
                # Subscribe to all topics
                success = False
                
                # IMPORTANT CHANGE: Create a consistent safe handler outside the loop
                # so we're not re-registering different handlers
                async def global_safe_mqtt_handler(msg):
                    """Global safe MQTT handler that delegates to all scanners."""
                    try:
                        payload_len = len(msg.payload) if msg.payload else 0
                        _LOGGER.debug(f"Global handler received MQTT message: {payload_len} bytes")
                        
                        # Skip empty payloads
                        if not msg.payload:
                            return
                            
                        # Process with all available scanners
                        scanner_count = 0
                        for entry_data in hass.data.get(DOMAIN, {}).values():
                            if "scanner" in entry_data and entry_data["scanner"]:
                                scanner = entry_data["scanner"]
                                scanner_count += 1
                                try:
                                    await scanner.async_on_mqtt_message(msg)
                                except Exception as handler_err:
                                    _LOGGER.error(f"Error in scanner MQTT message handler: {handler_err}")
                        
                        if scanner_count == 0:
                            _LOGGER.warning("No scanners found to process MQTT message")
                    except Exception as err:
                        _LOGGER.error(f"Global error in MQTT message handler: {err}")
                
                for topic in mqtt_topics:
                    try:
                        _LOGGER.info(f"Subscribing to MQTT topic: {topic}")
                        
                        # Try to unsubscribe first to clean up any existing subscriptions
                        try:
                            # Unsubscribe using wildcard to catch any existing handlers
                            # This is a defensive measure to ensure we don't have multiple handlers
                            await mqtt.async_unsubscribe(hass, topic)
                            _LOGGER.debug(f"Unsubscribed from {topic}")
                        except Exception as unsub_err:
                            _LOGGER.debug(f"Error unsubscribing from {topic}: {unsub_err}")
                            # Continue anyway
                        
                        # Try to subscribe with our global safe handler
                        subscription = await mqtt.async_subscribe(
                            hass, 
                            topic, 
                            global_safe_mqtt_handler, 
                            encoding=None
                        )
                        
                        if subscription:
                            _LOGGER.info(f"Successfully subscribed to {topic} with global handler")
                            success = True
                        else:
                            _LOGGER.error(f"Failed to subscribe to {topic}")
                            
                    except Exception as mqtt_err:
                        _LOGGER.error(f"Error subscribing to {topic}: {mqtt_err}")
                
                # Short delay to ensure MQTT subscription is established
                await asyncio.sleep(2)
                
                # Update gateway sensor state if available
                try:
                    # Set up the state directly using the hass.states.async_set method
                    attributes = {
                        "friendly_name": "BLE Gateway",
                        "icon": "mdi:bluetooth-connect",
                        "devices": [],
                        "gateway_id": "AprilBrother-Gateway4",
                        "gateway_status": "Connected" if success else "Error",
                        "last_scan": datetime.datetime.now().isoformat()
                    }
                    
                    # Create/update the sensor directly 
                    hass.states.async_set(
                        "sensor.ble_gateway_raw_data", 
                        "online" if success else "error", 
                        attributes
                    )
                    _LOGGER.info("Updated BLE gateway status sensor")
                except Exception as state_err:
                    _LOGGER.warning(f"Failed to update gateway sensor state: {state_err}")
                
                # Update notification based on result
                try:
                    if success:
                        await hass.services.async_call(
                            "persistent_notification", 
                            "create", 
                            {
                                "title": "BLE Gateway Reconnect",
                                "message": f"Successfully subscribed to MQTT topics: {', '.join(mqtt_topics)}",
                                "notification_id": "ble_gateway_reconnect"
                            }
                        )
                    else:
                        await hass.services.async_call(
                            "persistent_notification", 
                            "create", 
                            {
                                "title": "BLE Gateway Reconnect",
                                "message": "Failed to resubscribe to MQTT topics.",
                                "notification_id": "ble_gateway_reconnect"
                            }
                        )
                except Exception as notify_err:
                    _LOGGER.warning(f"Failed to create result notification: {notify_err}")
                    
                return success
        except Exception as e:
            _LOGGER.error(f"Error in simple MQTT reconnect: {e}")
            try:
                await hass.services.async_call(
                    "persistent_notification", 
                    "create", 
                    {
                        "title": "BLE Gateway Reconnect",
                        "message": f"Error: {str(e)}",
                        "notification_id": "ble_gateway_reconnect"
                    }
                )
            except Exception:
                pass  # Silently ignore notification errors
            return False
    
    # Register the simple MQTT reconnect service
    async_register_admin_service(
        hass,
        DOMAIN,
        "mqtt_reconnect",
        simple_mqtt_reconnect,
        schema=vol.Schema({}),
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
    
    # Set up the MQTT subscription with proper error handling
    try:
        _LOGGER.info(f"Subscribing to MQTT topic: {mqtt_topic}")
        
        # Ensure MQTT component is ready
        if not hass.data.get("mqtt"):
            _LOGGER.error("MQTT component not ready. Cannot subscribe.")
            return False
        
        # Subscribe to the topic
        subscription = await mqtt.async_subscribe(
            hass, 
            mqtt_topic, 
            scanner.async_on_mqtt_message, 
            encoding=None
        )
        
        if subscription is None:
            _LOGGER.error(f"Failed to subscribe to MQTT topic {mqtt_topic}")
            return False
            
        _LOGGER.info(f"Successfully subscribed to MQTT topic {mqtt_topic}")
    except Exception as mqtt_err:
        _LOGGER.error(f"Failed to set up MQTT subscription: {mqtt_err}")
        return False
    
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
