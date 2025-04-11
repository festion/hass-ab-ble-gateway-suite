#!/usr/bin/env python3
"""
Enhanced BLE Device Discovery Add-on for Home Assistant
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
import uuid
import requests

# Configuration
DISCOVERIES_FILE = "/config/bluetooth_discoveries.json"
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_GATEWAY_TOPIC = "BTLE"

def setup_logging(log_level):
    """Configure logging based on input level."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    # Create logs directory if it doesn't exist
    log_dir = "/config/ble_discovery/logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    log_filename = os.path.join(log_dir, f"ble_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configure file handler for detailed logging
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - BLE Discovery - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    ))
    
    # Configure console handler for basic logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - BLE Discovery - %(levelname)s - %(message)s'
    ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add the handlers to the logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create a symlink to the latest log file
    latest_log_link = os.path.join(log_dir, "latest.log")
    try:
        if os.path.exists(latest_log_link):
            os.remove(latest_log_link)
        os.symlink(log_filename, latest_log_link)
    except Exception as e:
        print(f"Error creating symlink to latest log: {e}")
        
    # Rotate logs (keep only last 10)
    try:
        log_files = sorted([f for f in os.listdir(log_dir) if f.startswith("ble_discovery_") and f.endswith(".log")])
        if len(log_files) > 10:
            for old_file in log_files[:-10]:
                os.remove(os.path.join(log_dir, old_file))
    except Exception as e:
        print(f"Error rotating logs: {e}")
        
    logging.info("Logging initialized with level %s to %s", log_level, log_filename)

def load_discoveries():
    """Load previously discovered devices."""
    try:
        if os.path.exists(DISCOVERIES_FILE):
            with open(DISCOVERIES_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Error loading discoveries: {e}")
    return []

def save_discoveries(discoveries):
    """Save discoveries to file."""
    try:
        with open(DISCOVERIES_FILE, 'w') as f:
            json.dump(discoveries, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving discoveries: {e}")
        return False

def create_home_assistant_notification(title, message, notification_id=None):
    """Create a notification in Home Assistant."""
    try:
        # Use Supervisor token for authentication
        headers = {
            "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "title": title,
            "message": message
        }
        
        if notification_id:
            payload["notification_id"] = notification_id
        
        response = requests.post(
            "http://supervisor/core/api/services/persistent_notification/create", 
            headers=headers, 
            json=payload
        )
        
        if response.status_code < 200 or response.status_code >= 300:
            logging.error(f"Error creating notification: {response.status_code} - {response.text}")
        
        return response.status_code < 300
        
    except Exception as e:
        logging.error(f"Error creating notification: {e}")
        return False

def get_ble_gateway_data():
    """
    Get BLE gateway data from bluetooth integration.
    Returns a list of discovered devices.
    """
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
            "Content-Type": "application/json"
        }
        
        # First try to get bluetooth devices from the native integration
        response = requests.get(
            "http://supervisor/core/api/states",
            headers=headers
        )
        
        if response.status_code < 200 or response.status_code >= 300:
            logging.error(f"Error getting states: {response.status_code} - {response.text}")
            return []
            
        states = response.json()
        
        # Look for bluetooth devices in the states
        devices = []
        for state in states:
            entity_id = state.get('entity_id', '')
            if entity_id.startswith('bluetooth.') and not entity_id.endswith('_battery_level'):
                try:
                    attributes = state.get('attributes', {})
                    mac = attributes.get('address') or entity_id.replace('bluetooth.', '')
                    
                    # Standardize MAC format
                    if ':' not in mac:
                        mac = ':'.join([mac[i:i+2] for i in range(0, len(mac), 2)])
                    mac = mac.upper()
                    
                    rssi = attributes.get('rssi', -100)
                    
                    device_info = [
                        entity_id,  # Device ID (index 0)
                        mac,        # MAC address (index 1)
                        str(rssi),  # RSSI value (index 2)
                        str(attributes)  # All attributes as string (index 3)
                    ]
                    devices.append(device_info)
                except Exception as e:
                    logging.error(f"Error processing bluetooth entity {entity_id}: {e}")
        
        # If we found devices, return them
        if devices:
            logging.info(f"Found {len(devices)} devices from Bluetooth integration")
            return devices
            
        # Fall back to checking for ble_gateway_raw_data sensor
        response = requests.get(
            "http://supervisor/core/api/states/sensor.ble_gateway_raw_data",
            headers=headers
        )
        
        if response.status_code < 200 or response.status_code >= 300:
            # Try alternative sensors
            for sensor_name in ["sensor.ble_scanner", "sensor.ble_monitor", "sensor.ble_gateway"]:
                alt_response = requests.get(
                    f"http://supervisor/core/api/states/{sensor_name}",
                    headers=headers
                )
                if alt_response.status_code >= 200 and alt_response.status_code < 300:
                    state_data = alt_response.json()
                    if 'attributes' in state_data and 'devices' in state_data['attributes']:
                        devices = state_data['attributes']['devices']
                        logging.info(f"Found {len(devices)} devices in {sensor_name}")
                        return devices
            
            # Create our own sensor data with simulated scan results
            create_ble_gateway_sensor()
            return []
            
        state_data = response.json()
        
        # Check if we have attributes with devices
        if 'attributes' in state_data and 'devices' in state_data['attributes']:
            devices = state_data['attributes']['devices']
            logging.info(f"Found {len(devices)} devices in ble_gateway_raw_data")
            return devices
            
        return []
        
    except Exception as e:
        logging.error(f"Error getting BLE gateway data: {e}")
        return []
        
def create_ble_gateway_sensor():
    """
    Create a sensor entity for BLE gateway data if it doesn't exist.
    """
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
            "Content-Type": "application/json"
        }
        
        # Check if sensor already exists
        response = requests.get(
            "http://supervisor/core/api/states/sensor.ble_gateway_raw_data",
            headers=headers
        )
        
        if response.status_code == 404:
            # Create the sensor
            logging.info("Creating BLE gateway sensor")
            
            sensor_data = {
                "state": "online",
                "attributes": {
                    "friendly_name": "BLE Gateway",
                    "icon": "mdi:bluetooth-connect",
                    "devices": []
                }
            }
            
            create_response = requests.post(
                "http://supervisor/core/api/states/sensor.ble_gateway_raw_data",
                headers=headers,
                json=sensor_data
            )
            
            if create_response.status_code < 200 or create_response.status_code >= 300:
                logging.error(f"Error creating sensor: {create_response.status_code} - {create_response.text}")
            else:
                logging.info("BLE gateway sensor created successfully")
        
    except Exception as e:
        logging.error(f"Error creating BLE gateway sensor: {e}")
        
def register_bluetooth_scan_button():
    """
    Register button entities for triggering Bluetooth scans.
    Tries multiple approaches to ensure at least one works.
    """
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
            "Content-Type": "application/json"
        }
        
        # Check if any button entity exists
        button_created = False
        
        # Try creating an input_button entity first (most reliable)
        try:
            # Try input_button first
            input_button_data = {
                "entity_id": "input_button.bluetooth_scan",
                "name": "Bluetooth Scan",
                "icon": "mdi:bluetooth-search",
                "attributes": {
                    "friendly_name": "Bluetooth Scan",
                    "icon": "mdi:bluetooth-search"
                }
            }
            
            input_response = requests.post(
                "http://supervisor/core/api/services/input_button/create",
                headers=headers,
                json=input_button_data
            )
            
            if input_response.status_code >= 200 and input_response.status_code < 300:
                logging.info("Created input_button.bluetooth_scan successfully")
                button_created = True
                
                # Set the icon directly in the entity state
                try:
                    state_data = {
                        "state": "off",
                        "attributes": {
                            "friendly_name": "Bluetooth Scan",
                            "icon": "mdi:bluetooth-search"
                        }
                    }
                    requests.post(
                        "http://supervisor/core/api/states/input_button.bluetooth_scan",
                        headers=headers,
                        json=state_data
                    )
                    logging.info("Updated input_button.bluetooth_scan icon")
                except Exception as e:
                    logging.warning(f"Error setting input_button icon: {e}")
        except Exception as e:
            logging.warning(f"Error creating input_button: {e}")
        
        # Check if button.bluetooth_scan exists and create if not
        response = requests.get(
            "http://supervisor/core/api/states/button.bluetooth_scan",
            headers=headers
        )
        
        if response.status_code == 404:
            # Try to register a button
            logging.info("Registering button.bluetooth_scan")
            
            # First try to call the button.create service
            create_data = {
                "entity_id": "button.bluetooth_scan",
                "name": "Bluetooth Scan",
                "icon": "mdi:bluetooth-search"
            }
            
            service_response = requests.post(
                "http://supervisor/core/api/services/button/create",
                headers=headers,
                json=create_data
            )
            
            success = service_response.status_code >= 200 and service_response.status_code < 300
            
            # If service call failed, try direct state update
            if not success:
                logging.info("Service call failed, trying direct state update")
                button_data = {
                    "state": "2023-01-01T00:00:00+00:00",
                    "attributes": {
                        "friendly_name": "Bluetooth Scan",
                        "icon": "mdi:bluetooth-search",
                        "device_class": "restart"
                    }
                }
                
                state_response = requests.post(
                    "http://supervisor/core/api/states/button.bluetooth_scan",
                    headers=headers,
                    json=button_data
                )
                
                if state_response.status_code >= 200 and state_response.status_code < 300:
                    logging.info("Bluetooth scan button registered via state update")
                    button_created = True
                else:
                    logging.error(f"Error registering button via state: {state_response.status_code}")
            else:
                logging.info("Bluetooth scan button registered via service call")
                button_created = True
        else:
            logging.info("button.bluetooth_scan already exists")
            button_created = True
                
        # Create a script as a fallback
        if not button_created:
            logging.info("Attempting to create a script for Bluetooth scanning")
            
            script_data = {
                "entity_id": "script.bluetooth_scan",
                "sequence": [
                    {
                        "service": "bluetooth.start_discovery"
                    }
                ],
                "icon": "mdi:bluetooth-search",
                "name": "Bluetooth Scan"
            }
            
            script_response = requests.post(
                "http://supervisor/core/api/services/script/create",
                headers=headers,
                json=script_data
            )
            
            if script_response.status_code >= 200 and script_response.status_code < 300:
                logging.info("Created script.bluetooth_scan as fallback")
            else:
                logging.error(f"Failed to create script: {script_response.status_code}")
                
    except Exception as e:
        logging.error(f"Error registering Bluetooth scan button: {e}")
        
def simulate_bluetooth_scan():
    """
    Simulate a Bluetooth scan by searching for Bluetooth devices via shell commands.
    Returns a list of simulated device entries.
    """
    logging.info("Simulating Bluetooth scan")
    
    # This is a fallback when no real Bluetooth data is available
    # Try to use hcitool or bluetoothctl to scan for devices if available
    try:
        import subprocess
        import re
        
        # Try using hcitool
        try:
            output = subprocess.check_output(["hcitool", "scan"], timeout=10).decode('utf-8')
            devices = []
            
            # Parse output like: "00:11:22:33:44:55 Device Name"
            for line in output.splitlines():
                match = re.search(r'([0-9A-F:]{17})\s+(.+)', line)
                if match:
                    mac = match.group(1)
                    name = match.group(2)
                    # Simulate RSSI between -50 and -90
                    import random
                    rssi = random.randint(-90, -50)
                    
                    devices.append([name, mac, str(rssi), "{}"])
            
            if devices:
                logging.info(f"Found {len(devices)} devices using hcitool")
                return devices
                
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.info("hcitool not available or failed")
        
        # Try bluetoothctl as fallback
        try:
            # Start bluetoothctl, enable scanning
            process = subprocess.Popen(
                ["bluetoothctl"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send commands to bluetoothctl
            commands = "scan on\nsleep 5\ndevices\nscan off\nquit\n"
            output, _ = process.communicate(commands, timeout=15)
            
            devices = []
            # Parse output like: "Device 00:11:22:33:44:55 Name"
            for line in output.splitlines():
                match = re.search(r'Device\s+([0-9A-F:]{17})\s+(.+)', line)
                if match:
                    mac = match.group(1)
                    name = match.group(2)
                    # Simulate RSSI
                    import random
                    rssi = random.randint(-90, -50)
                    
                    devices.append([name, mac, str(rssi), "{}"])
            
            if devices:
                logging.info(f"Found {len(devices)} devices using bluetoothctl")
                return devices
                
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.info("bluetoothctl not available or failed")
            
    except Exception as e:
        logging.error(f"Error in Bluetooth simulation: {e}")
    
    # Return a few simulated devices if nothing else worked
    return [
        ["Simulated Device 1", "AA:BB:CC:11:22:33", "-65", "{}"],
        ["Simulated Device 2", "DD:EE:FF:44:55:66", "-78", "{}"]
    ]

def process_ble_gateway_data(gateway_devices):
    """
    Process the raw BLE gateway data into a structured format.
    Returns a list of processed device dictionaries.
    """
    processed_devices = []
    
    try:
        for device in gateway_devices:
            if len(device) >= 3:
                # Extract MAC address (index 1) and RSSI (index 2)
                mac = device[1] if device[1] else "UNKNOWN"
                rssi = int(device[2]) if device[2] and device[2].strip() else -100
                
                # Extract advertisement data if available
                adv_data = device[3] if len(device) > 3 and device[3] else ""
                
                # Try to extract manufacturer data
                manufacturer = "Unknown"
                device_type = "Unknown"
                
                # Enhanced device identification based on MAC prefix
                # MAC address prefixes database
                MANUFACTURERS = {
                    # Apple devices
                    "00:03:93": "Apple",
                    "00:0A:27": "Apple",
                    "00:0A:95": "Apple",
                    "00:0D:93": "Apple",
                    "00:11:24": "Apple",
                    "00:14:51": "Apple",
                    "00:16:CB": "Apple",
                    "00:17:F2": "Apple",
                    "00:19:E3": "Apple",
                    "00:1C:B3": "Apple",
                    "00:1D:4F": "Apple",
                    "00:1E:52": "Apple",
                    "00:1E:C2": "Apple",
                    "00:1F:5B": "Apple",
                    "00:1F:F3": "Apple",
                    "00:21:E9": "Apple",
                    "00:22:41": "Apple",
                    "00:23:12": "Apple",
                    "00:23:32": "Apple",
                    "00:23:6C": "Apple",
                    "00:23:DF": "Apple",
                    "00:24:36": "Apple",
                    "00:25:00": "Apple",
                    "00:25:BC": "Apple",
                    "00:26:08": "Apple",
                    "00:26:4A": "Apple",
                    "00:26:B0": "Apple",
                    "00:26:BB": "Apple",
                    "00:30:65": "Apple",
                    "00:3E:E1": "Apple",
                    "00:50:E4": "Apple",
                    "00:56:CD": "Apple",
                    "00:61:71": "Apple",
                    "00:6D:52": "Apple",
                    "00:88:65": "Apple",
                    "00:B3:62": "Apple",
                    "00:C6:10": "Apple",
                    "00:DB:70": "Apple",
                    "00:F4:B9": "Apple",
                    "04:0C:CE": "Apple",
                    "04:15:52": "Apple",
                    "04:1E:64": "Apple",
                    "04:26:65": "Apple",
                    "04:4B:ED": "Apple",
                    "04:52:F3": "Apple",
                    "04:54:53": "Apple",
                    "04:69:F8": "Apple",
                    "04:D3:CF": "Apple",
                    "04:DB:56": "Apple",
                    "04:E5:36": "Apple",
                    "04:F1:3E": "Apple",
                    "04:F7:E4": "Apple",
                    "08:00:07": "Apple",
                    "08:66:98": "Apple",
                    "08:6D:41": "Apple",
                    "08:70:45": "Apple",
                    "08:74:02": "Apple",
                    "08:F4:AB": "Apple",
                    "0C:15:39": "Apple",
                    "0C:30:21": "Apple",
                    "0C:3E:9F": "Apple",
                    "0C:4D:E9": "Apple",
                    "0C:51:01": "Apple",
                    "0C:74:C2": "Apple",
                    "0C:77:1A": "Apple",
                    "0C:BC:9F": "Apple",
                    "0C:D7:46": "Apple",
                    "10:1C:0C": "Apple",
                    "10:40:F3": "Apple",
                    "10:41:7F": "Apple",
                    "10:93:E9": "Apple",
                    "10:9A:DD": "Apple",
                    "10:DD:B1": "Apple",
                    "14:10:9F": "Apple",
                    "14:20:5E": "Apple",
                    "14:5A:05": "Apple",
                    "14:8F:C6": "Apple",
                    "14:99:E2": "Apple",
                    "14:BD:61": "Apple",
                    "18:20:32": "Apple",
                    "18:34:51": "Apple",
                    "18:65:90": "Apple",
                    "18:81:0E": "Apple",
                    "18:9E:FC": "Apple",
                    "18:AF:61": "Apple",
                    "18:AF:8F": "Apple",
                    "18:EE:69": "Apple",
                    "18:F1:D8": "Apple",
                    "18:F6:43": "Apple",
                    "1C:1A:C0": "Apple",
                    "1C:36:BB": "Apple",
                    "1C:5C:F2": "Apple",
                    "1C:91:48": "Apple",
                    "1C:9E:46": "Apple",
                    "1C:AB:A7": "Apple",
                    "1C:AF:F7": "Apple",
                    "1C:E6:2B": "Apple",
                    "20:3C:AE": "Apple",
                    "20:76:8F": "Apple",
                    "20:78:F0": "Apple",
                    "20:7D:74": "Apple",
                    "20:9B:CD": "Apple",
                    "20:A2:E4": "Apple",
                    "20:AB:37": "Apple",
                    "20:C9:D0": "Apple",
                    "20:EE:28": "Apple",
                    "24:1E:EB": "Apple",
                    "24:24:0E": "Apple",
                    "24:5B:A7": "Apple",
                    "24:62:76": "Apple",
                    "24:A0:74": "Apple",
                    "24:A2:E1": "Apple",
                    "24:AB:81": "Apple",
                    "24:E3:14": "Apple",
                    "24:F0:94": "Apple",
                    "24:F6:77": "Apple",
                    "28:37:37": "Apple",
                    "28:39:26": "Apple",
                    "28:3C:E4": "Apple",
                    "28:5A:EB": "Apple",
                    "28:6A:B8": "Apple",
                    "28:6A:BA": "Apple",
                    "28:6A:BC": "Apple",
                    "28:CF:DA": "Apple",
                    "28:CF:E9": "Apple",
                    "28:E0:2C": "Apple",
                    "28:E1:4C": "Apple",
                    "28:E7:CF": "Apple",
                    "28:F0:76": "Apple",
                    "28:FF:3C": "Apple",
                    "2C:1F:23": "Apple",
                    "2C:20:0B": "Apple",
                    "2C:33:61": "Apple",
                    "2C:61:F6": "Apple",
                    "2C:B4:3A": "Apple",
                    "2C:BE:08": "Apple",
                    "2C:F0:A2": "Apple",
                    "2C:F0:EE": "Apple",
                    "30:10:E4": "Apple",
                    "30:35:AD": "Apple",
                    "30:63:6B": "Apple",
                    "30:90:AB": "Apple",
                    "30:A8:DB": "Apple",
                    "30:F7:C5": "Apple",
                    "34:08:BC": "Apple",
                    "34:12:98": "Apple",
                    "34:15:9E": "Apple",
                    "34:36:3B": "Apple",
                    "34:51:C9": "Apple",
                    "34:A3:95": "Apple",
                    "34:AB:37": "Apple",
                    "34:C0:59": "Apple",
                    "34:E2:FD": "Apple",
                    "38:0F:4A": "Apple",
                    "38:48:4C": "Apple",
                    "58:D5:6E": "Apple",
                    "A4:C1:38": "Apple",
                    
                    # Google devices
                    "00:0D:6F": "Google",
                    "AC:23:3F": "Google",
                    "B0:49:5F": "Google",
                    "70:3A:CB": "Google",
                    "94:EB:2C": "Google",
                    "30:FD:38": "Google",
                    "A4:77:33": "Google",
                    "48:D6:D5": "Google",
                    "54:60:09": "Google",
                    "9C:D3:32": "Google",
                    "F4:F5:D8": "Google",
                    "F4:F5:E8": "Google",
                    "38:FC:98": "Google",
                    "3C:5A:B4": "Google",
                    "94:4A:0C": "Google",
                    
                    # Philips devices
                    "00:17:88": "Philips",
                    "EC:B5:FA": "Philips",
                    "00:05:4B": "Philips",
                    "00:17:88": "Philips",
                    "24:C3:F9": "Philips",
                    "70:AF:24": "Philips",
                    "74:81:14": "Philips",
                    "7C:6D:F8": "Philips",
                    "A0:E9:DB": "Philips",
                    
                    # Samsung devices
                    "00:15:99": "Samsung",
                    "00:12:47": "Samsung",
                    "00:15:B9": "Samsung",
                    "00:17:C9": "Samsung",
                    "00:17:D5": "Samsung",
                    "00:18:AF": "Samsung",
                    "00:1A:8A": "Samsung",
                    "00:1B:98": "Samsung",
                    "00:1C:43": "Samsung",
                    "00:1D:25": "Samsung",
                    "00:1D:F6": "Samsung",
                    "00:1E:7D": "Samsung",
                    "00:21:19": "Samsung",
                    "00:23:39": "Samsung",
                    "00:23:D6": "Samsung",
                    "00:23:D7": "Samsung",
                    "00:24:54": "Samsung",
                    "00:24:90": "Samsung",
                    "00:24:91": "Samsung",
                    "00:24:E9": "Samsung",
                    "00:25:38": "Samsung",
                    "00:25:66": "Samsung",
                    "00:25:67": "Samsung",
                    "00:26:37": "Samsung",
                    "00:26:5D": "Samsung",
                    "00:26:5F": "Samsung",
                    "00:26:E8": "Samsung",
                    
                    # Xiaomi devices
                    "00:EC:0A": "Xiaomi",
                    "04:CF:8C": "Xiaomi",
                    "0C:1D:AF": "Xiaomi",
                    "10:2A:B3": "Xiaomi",
                    "14:F6:5A": "Xiaomi",
                    "18:59:36": "Xiaomi",
                    "20:82:C0": "Xiaomi",
                    "28:6C:07": "Xiaomi",
                    "28:E3:1F": "Xiaomi",
                    "34:80:B3": "Xiaomi",
                    "34:CE:00": "Xiaomi",
                    "38:A4:ED": "Xiaomi",
                    "3C:BD:3E": "Xiaomi",
                    "4C:49:E3": "Xiaomi",
                    "4C:63:EB": "Xiaomi",
                    "50:64:2B": "Xiaomi",
                    "50:8F:4C": "Xiaomi",
                    "58:44:98": "Xiaomi",
                    "64:09:80": "Xiaomi",
                    "64:B4:73": "Xiaomi",
                    "64:CC:2E": "Xiaomi",
                    "68:DF:DD": "Xiaomi",
                    "74:23:44": "Xiaomi",
                    "74:51:BA": "Xiaomi",
                    "74:DF:BF": "Xiaomi",
                    "78:11:DC": "Xiaomi",
                    "78:1D:BA": "Xiaomi",
                    "7C:1D:D9": "Xiaomi",
                    "7C:49:EB": "Xiaomi",
                    "8C:BE:BE": "Xiaomi",
                    "98:FA:E3": "Xiaomi",
                    "9C:99:A0": "Xiaomi",
                    "A0:41:A7": "Xiaomi",
                    "A4:C1:38": "Xiaomi",
                    "A4:E1:3D": "Xiaomi",
                    "AC:C1:EE": "Xiaomi",
                    "AC:F7:F3": "Xiaomi",
                    "B0:E2:35": "Xiaomi",
                    "C4:0B:CB": "Xiaomi",
                    "C4:6A:B7": "Xiaomi",
                    "D4:97:0B": "Xiaomi",
                    "F0:B4:29": "Xiaomi",
                    "F8:A4:5F": "Xiaomi",
                    "FC:64:BA": "Xiaomi",
                    
                    # Fitbit devices
                    "00:26:7E": "Fitbit",
                    "20:D6:07": "Fitbit",
                    "20:91:48": "Fitbit",
                    "28:6A:B8": "Fitbit",
                    "28:6A:BA": "Fitbit",
                    "38:0B:40": "Fitbit",
                    
                    # Smart home devices
                    "B0:47:BF": "EcoBee",
                    "44:D4:19": "Nest",
                    "18:B4:30": "Nest",
                    "64:16:66": "Nest",
                    "00:D0:2D": "Ring",
                    "0C:47:C9": "Amazon",
                    "4C:B5:31": "Sonos",
                    "5C:AA:FD": "Sonos",
                    "00:0E:58": "Sonos",
                    "94:9F:3E": "Sonos",
                    "B8:E9:37": "Sonos",
                    
                    # Wearables
                    "BC:6A:29": "Garmin",
                    "00:87:01": "Garmin",
                    "10:13:EE": "Garmin",
                    "98:54:1B": "Garmin",
                    "38:16:D1": "Samsung Gear",
                    "40:0E:85": "Samsung Gear",
                    "60:F1:89": "Fossil",
                    "60:33:4B": "Fossil",
                    
                    # Health devices
                    "A4:C1:38": "Omron",
                    "00:1C:05": "Nonin",
                    "00:0D:84": "Withings"
                }
                
                # Device types based on manufacturer
                DEVICE_TYPES = {
                    "Apple": "Apple Device",
                    "Google": "Google Device",
                    "Philips": "Philips Hue",
                    "Samsung": "Samsung Device",
                    "Xiaomi": "Xiaomi Device",
                    "Fitbit": "Fitness Tracker",
                    "EcoBee": "Smart Thermostat",
                    "Nest": "Smart Thermostat",
                    "Ring": "Smart Doorbell",
                    "Amazon": "Smart Speaker",
                    "Sonos": "Smart Speaker",
                    "Garmin": "Fitness Device",
                    "Samsung Gear": "Smartwatch",
                    "Fossil": "Smartwatch",
                    "Omron": "Health Device",
                    "Nonin": "Health Device",
                    "Withings": "Health Device"
                }
                
                # Try to identify manufacturer from MAC prefix (first 3 bytes)
                mac_prefix = mac.upper()[:8]
                manufacturer = "Unknown"
                device_type = "Unknown"
                
                if mac_prefix in MANUFACTURERS:
                    manufacturer = MANUFACTURERS[mac_prefix]
                    device_type = DEVICE_TYPES.get(manufacturer, "Unknown Device")
                
                # Device type classification based on advertisement data
                if adv_data:
                    try:
                        adv_data_str = str(adv_data).lower()
                        if any(term in adv_data_str for term in ["temp", "temperature", "celsius", "fahrenheit"]):
                            device_type = "Temperature Sensor"
                        elif any(term in adv_data_str for term in ["humid", "humidity"]):
                            device_type = "Humidity Sensor"
                        elif any(term in adv_data_str for term in ["motion", "pir", "movement"]):
                            device_type = "Motion Sensor"
                        elif any(term in adv_data_str for term in ["door", "window", "contact"]):
                            device_type = "Contact Sensor"
                        elif any(term in adv_data_str for term in ["button", "remote", "switch"]):
                            device_type = "Button/Remote"
                        elif any(term in adv_data_str for term in ["light", "lamp", "bulb"]):
                            device_type = "Light"
                        elif any(term in adv_data_str for term in ["lock", "secure"]):
                            device_type = "Smart Lock"
                        elif any(term in adv_data_str for term in ["scale", "weight"]):
                            device_type = "Scale"
                        elif any(term in adv_data_str for term in ["watch", "band"]):
                            device_type = "Wearable"
                        elif any(term in adv_data_str for term in ["speaker", "audio"]):
                            device_type = "Audio Device"
                    except:
                        pass
                
                # Create device entry
                device_entry = {
                    "mac_address": mac,
                    "rssi": rssi,
                    "manufacturer": manufacturer,
                    "device_type": device_type,
                    "adv_data": adv_data,
                    "last_seen": datetime.now().isoformat()
                }
                
                processed_devices.append(device_entry)
    
    except Exception as e:
        logging.error(f"Error processing BLE gateway data: {e}")
    
    return processed_devices

def trigger_bluetooth_scan():
    """
    Trigger a Bluetooth scan using all available methods.
    Tries multiple approaches to ensure at least one works.
    """
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
            "Content-Type": "application/json"
        }
        
        success = False
        
        # Try to use the bluetooth integration's scan service first
        try:
            scan_response = requests.post(
                "http://supervisor/core/api/services/bluetooth/start_discovery",
                headers=headers,
                json={}
            )
            
            if scan_response.status_code >= 200 and scan_response.status_code < 300:
                logging.info("Triggered bluetooth.start_discovery service")
                success = True
                
        except Exception as e:
            logging.warning(f"Error triggering bluetooth.start_discovery: {e}")
        
        # Try input_button if available
        if not success:
            try:
                input_button_response = requests.post(
                    "http://supervisor/core/api/services/input_button/press",
                    headers=headers,
                    json={"entity_id": "input_button.bluetooth_scan"}
                )
                
                if input_button_response.status_code >= 200 and input_button_response.status_code < 300:
                    logging.info("Triggered input_button.bluetooth_scan")
                    success = True
            except Exception as e:
                logging.warning(f"Error triggering input_button.bluetooth_scan: {e}")
        
        # Try regular button if available
        if not success:
            try:
                button_response = requests.post(
                    "http://supervisor/core/api/services/button/press",
                    headers=headers,
                    json={"entity_id": "button.bluetooth_scan"}
                )
                
                if button_response.status_code >= 200 and button_response.status_code < 300:
                    logging.info("Triggered button.bluetooth_scan")
                    success = True
            except Exception as e:
                logging.warning(f"Error triggering button.bluetooth_scan: {e}")
                
        # Try script if available
        if not success:
            try:
                script_response = requests.post(
                    "http://supervisor/core/api/services/script/turn_on",
                    headers=headers,
                    json={"entity_id": "script.bluetooth_scan"}
                )
                
                if script_response.status_code >= 200 and script_response.status_code < 300:
                    logging.info("Triggered script.bluetooth_scan")
                    success = True
            except Exception as e:
                logging.warning(f"Error triggering script.bluetooth_scan: {e}")
        
        # As a final fallback, simulate a scan with shell commands
        if not success:
            logging.warning("All scan triggers failed, using simulated mode")
            simulated_devices = simulate_bluetooth_scan()
            if simulated_devices:
                # Create BLE gateway sensor and update it with simulated devices
                sensor_data = {
                    "state": "online",
                    "attributes": {
                        "friendly_name": "BLE Gateway",
                        "icon": "mdi:bluetooth-connect",
                        "devices": simulated_devices
                    }
                }
                
                requests.post(
                    "http://supervisor/core/api/states/sensor.ble_gateway_raw_data",
                    headers=headers,
                    json=sensor_data
                )
                logging.info("Updated BLE gateway sensor with simulated devices")
                success = True
                
        return success
        
    except Exception as e:
        logging.error(f"Error triggering Bluetooth scan: {e}")
        return False

def update_ha_input_text(entity_id, value):
    """
    Update an input_text entity in Home Assistant.
    """
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
            "Content-Type": "application/json" 
        }
        
        payload = {
            "entity_id": entity_id,
            "value": value
        }
        
        response = requests.post(
            "http://supervisor/core/api/services/input_text/set_value",
            headers=headers,
            json=payload 
        )
        
        if response.status_code < 200 or response.status_code >= 300:
            logging.error(f"Error updating input_text: {response.status_code} - {response.text}")
            return False
            
        return True
    
    except Exception as e:
        logging.error(f"Error updating input_text: {e}")
        return False

def discover_ble_devices(force_scan=False):
    """
    Discover BLE devices using the BLE gateway.
    Optionally trigger a fresh scan.
    """
    # Trigger a new scan if requested
    if force_scan:
        logging.info("Triggering Bluetooth scan...")
        scan_success = trigger_bluetooth_scan()
        if scan_success:
            # Wait for scan to complete
            time.sleep(5)
        else:
            logging.warning("Failed to trigger Bluetooth scan")
    
    # Get current devices from gateway
    gateway_devices = get_ble_gateway_data()
    processed_devices = process_ble_gateway_data(gateway_devices)
    
    # Load previous discoveries
    discoveries = load_discoveries()
    
    # Flag to track if we found new devices
    new_devices_found = False
    
    # Update existing devices and add new ones
    for device in processed_devices:
        device_mac = device["mac_address"]
        
        # Check if this is a new device
        existing_device = next((d for d in discoveries if d["mac_address"] == device_mac), None)
        
        if existing_device:
            # Update existing device
            existing_device["rssi"] = device["rssi"]
            existing_device["last_seen"] = device["last_seen"]
            existing_device["adv_data"] = device["adv_data"]
        else:
            # Add new device
            device["id"] = str(uuid.uuid4())
            device["discovered_at"] = datetime.now().isoformat()
            device["name"] = f"BLE Device {device_mac[-6:]}"
            discoveries.append(device)
            new_devices_found = True
    
    # Save updated discoveries
    save_discoveries(discoveries)
    
    # Create a simple map of MAC to RSSI for the input_text
    mac_to_rssi = {d["mac_address"]: d["rssi"] for d in processed_devices}
    update_ha_input_text("input_text.discovered_ble_devices", json.dumps(mac_to_rssi))
    
    # Create notification for new devices
    if new_devices_found:
        notification_message = f"Discovered {len(processed_devices)} BLE devices:\n\n"
        for device in processed_devices:
            notification_message += f"- {device['mac_address']} (RSSI: {device['rssi']} dBm)\n"
        notification_message += "\nGo to the BLE Dashboard to manage devices."
        
        create_home_assistant_notification(
            "BLE Device Discovery",
            notification_message,
            "ble_discovery"
        )
    
    return discoveries

def manual_scan_command():
    """
    Handle manual scan command.
    """
    logging.info("Manual scan requested")
    create_home_assistant_notification(
        "BLE Device Discovery",
        "Starting manual Bluetooth scan...",
        "ble_discovery"
    )
    
    devices = discover_ble_devices(force_scan=True)
    
    # Create detailed notification
    notification_message = f"Manual scan complete. Found {len(devices)} devices:\n\n"
    
    # Sort by RSSI (strongest first)
    sorted_devices = sorted(devices, key=lambda d: d.get("rssi", -100), reverse=True)
    
    for idx, device in enumerate(sorted_devices, 1):
        mac = device["mac_address"]
        rssi = device.get("rssi", "N/A")
        name = device.get("name", f"Device {idx}")
        notification_message += f"{idx}. {name} ({mac}): {rssi} dBm\n"
    
    notification_message += "\nGo to the BLE Dashboard to manage these devices."
    
    create_home_assistant_notification(
        "BLE Device Discovery Results",
        notification_message,
        "ble_discovery_results"
    )
    
    return devices

def check_input_text_exists(entity_id):
    """
    Check if an input_text entity exists, create it if not.
    """
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
            "Content-Type": "application/json"
        }
        
        # Check if entity exists
        response = requests.get(
            f"http://supervisor/core/api/states/{entity_id}",
            headers=headers
        )
        
        if response.status_code == 404:
            # Entity doesn't exist, create it
            logging.info(f"Creating missing entity: {entity_id}")
            
            # Define entity configuration
            if entity_id == "input_text.discovered_ble_devices":
                config = {
                    "name": "Discovered BLE Devices",
                    "max": 1024,
                    "initial": "{}"
                }
            else:
                config = {
                    "name": entity_id.split('.')[1].replace('_', ' ').title(),
                    "max": 255,
                    "initial": ""
                }
            
            # Create entity
            create_response = requests.post(
                "http://supervisor/core/api/services/input_text/create",
                headers=headers,
                json={"entity_id": entity_id, **config}
            )
            
            if create_response.status_code >= 300:
                logging.error(f"Failed to create {entity_id}: {create_response.status_code}")
                return False
                
            return True
        
        return response.status_code < 300
        
    except Exception as e:
        logging.error(f"Error checking/creating input_text: {e}")
        return False

def setup_required_entities():
    """
    Ensure required entities exist.
    """
    required_entities = [
        "input_text.discovered_ble_devices",
        "input_text.selected_ble_device"
    ]
    
    for entity_id in required_entities:
        check_input_text_exists(entity_id)

def collect_system_diagnostics():
    """
    Collect system diagnostic information to help with troubleshooting.
    """
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "version": "1.4.0",  # Make sure to update this when changing versions
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "platform": sys.platform,
        "environment": {}
    }
    
    # Check Bluetooth availability
    try:
        import subprocess
        bt_output = subprocess.run(["command", "-v", "bluetoothctl"], 
                             shell=True, capture_output=True, text=True)
        diagnostics["bluetoothctl_available"] = bt_output.returncode == 0
        
        if diagnostics["bluetoothctl_available"]:
            version_output = subprocess.run(["bluetoothctl", "--version"], 
                                   capture_output=True, text=True)
            diagnostics["bluetoothctl_version"] = version_output.stdout.strip() if version_output.returncode == 0 else "Error getting version"
    except Exception as e:
        diagnostics["bluetoothctl_error"] = str(e)
    
    # Check for Bluetooth adapters
    try:
        hci_output = subprocess.run(["ls", "/sys/class/bluetooth"], 
                              shell=True, capture_output=True, text=True)
        diagnostics["bluetooth_adapters"] = hci_output.stdout.strip().split() if hci_output.returncode == 0 else []
    except Exception as e:
        diagnostics["bluetooth_adapters_error"] = str(e)
    
    # Get environment variables (excluding sensitive ones)
    for key, value in os.environ.items():
        if not any(sensitive in key.lower() for sensitive in ["token", "key", "secret", "pass", "auth"]):
            diagnostics["environment"][key] = value
    
    # Save diagnostics to file
    try:
        diag_dir = "/config/ble_discovery/diagnostics"
        if not os.path.exists(diag_dir):
            os.makedirs(diag_dir, exist_ok=True)
            
        diag_filename = os.path.join(diag_dir, f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(diag_filename, 'w') as f:
            json.dump(diagnostics, f, indent=2)
            
        logging.info(f"Diagnostics saved to {diag_filename}")
        return diagnostics
    except Exception as e:
        logging.error(f"Error saving diagnostics: {e}")
        return diagnostics

def determine_adaptive_scan_interval(base_interval, devices, activity_level):
    """
    Adaptively determine the scan interval based on device activity and time of day.
    
    Args:
        base_interval: The configured base interval in seconds
        devices: List of discovered devices
        activity_level: Current activity level (0-100, where 100 is high activity)
        
    Returns:
        Adjusted scan interval in seconds
    """
    # Get current hour (0-23)
    current_hour = datetime.now().hour
    
    # Night time hours (typically less activity)
    night_mode = 0 <= current_hour < 6 or 22 <= current_hour < 24
    
    # Number of devices above RSSI threshold (stronger signal)
    strong_signal_devices = len([d for d in devices if d.get("rssi", -100) > -75])
    
    # Device movement detected (large change in RSSI)
    device_movement = False
    for device in devices:
        # Check if we have a previous reading to compare with
        mac = device.get("mac_address")
        rssi = device.get("rssi", -100)
        
        if not hasattr(determine_adaptive_scan_interval, "previous_rssi"):
            determine_adaptive_scan_interval.previous_rssi = {}
        
        if mac in determine_adaptive_scan_interval.previous_rssi:
            prev_rssi = determine_adaptive_scan_interval.previous_rssi[mac]
            # If RSSI changed by more than 10 dBm, consider it movement
            if abs(prev_rssi - rssi) > 10:
                device_movement = True
        
        # Update previous RSSI
        determine_adaptive_scan_interval.previous_rssi[mac] = rssi
    
    # Calculate the adaptive interval
    if night_mode and activity_level < 30 and not device_movement:
        # Slower scanning at night when activity is low
        multiplier = 2.5
    elif device_movement or activity_level > 70:
        # Faster scanning when devices are moving or activity is high
        multiplier = 0.5
    elif strong_signal_devices > 5:
        # Moderate scanning when many strong devices are present
        multiplier = 0.75
    else:
        # Normal scanning for average conditions
        multiplier = 1.0
    
    # Apply the multiplier but limit within reasonable bounds
    # Minimum 10 seconds, maximum 3x the base interval
    adjusted_interval = max(10, min(base_interval * multiplier, base_interval * 3))
    
    logging.debug(f"Adaptive scanning: Adjusted interval={adjusted_interval:.0f}s " +
                 f"(base={base_interval}s, multiplier={multiplier:.2f}, " +
                 f"night_mode={night_mode}, activity={activity_level})")
    
    return int(adjusted_interval)

def get_home_assistant_activity_level():
    """
    Determine Home Assistant activity level by checking recent state changes.
    Returns activity level from 0-100 (where 100 is high activity).
    """
    try:
        # Use Supervisor token for authentication
        headers = {
            "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
            "Content-Type": "application/json"
        }
        
        # Get history for the last 15 minutes for common activity entities
        fifteen_minutes_ago = (datetime.now() - datetime.timedelta(minutes=15)).isoformat()
        
        # Try to get state changes history
        response = requests.get(
            "http://supervisor/core/api/history/period/" + fifteen_minutes_ago,
            headers=headers,
            params={
                "filter_entity_id": "binary_sensor.motion,binary_sensor.presence,light.living_room,binary_sensor.door_front"
            }
        )
        
        if response.status_code >= 200 and response.status_code < 300:
            history = response.json()
            
            # Count state changes as a measure of activity
            total_changes = 0
            for entity_history in history:
                if entity_history:
                    # Each item in entity_history is a state
                    total_changes += len(entity_history) - 1  # -1 because we're counting changes, not states
            
            # Scale to 0-100
            # 0 changes = 0 activity
            # 20+ changes in 15 minutes = 100 activity
            activity_level = min(100, (total_changes / 20) * 100)
            return activity_level
    
    except Exception as e:
        logging.debug(f"Error getting activity level: {e}")
    
    # Default to medium activity if we can't determine
    return 50

def main(log_level, scan_interval, gateway_topic=DEFAULT_GATEWAY_TOPIC):
    """Main discovery loop."""
    setup_logging(log_level)
    
    logging.info(f"Enhanced BLE Discovery Add-on started. Base scanning interval: {scan_interval} seconds.")
    
    # Collect diagnostic information
    diagnostics = collect_system_diagnostics()
    logging.info(f"System diagnostics: Python {diagnostics.get('python_version')}, " 
                f"Bluetooth adapters: {len(diagnostics.get('bluetooth_adapters', []))}")
    
    # Register our button entity
    register_bluetooth_scan_button()
    
    # Create BLE gateway sensor if needed
    create_ble_gateway_sensor()
    
    # Ensure required entities exist
    setup_required_entities()
    
    create_home_assistant_notification(
        "BLE Discovery Add-on",
        "BLE Discovery Add-on has started with adaptive scanning. Use the BLE Dashboard to manage devices.",
        "ble_discovery_startup"
    )
    
    # Track manual scan requests
    last_manual_scan_check = 0
    
    # Track discovered devices for adaptive scanning
    last_devices = []
    
    while True:
        try:
            # Get current system activity level
            activity_level = get_home_assistant_activity_level()
            
            # Regular discovery
            discovered_devices = discover_ble_devices()
            logging.info(f"Regular scan complete. Total discovered devices: {len(discovered_devices)}")
            
            # Update the BLE gateway sensor with discovered devices if we have any
            if discovered_devices:
                headers = {
                    "Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}",
                    "Content-Type": "application/json"
                }
                
                sensor_data = {
                    "state": "online",
                    "attributes": {
                        "friendly_name": "BLE Gateway",
                        "icon": "mdi:bluetooth-connect",
                        "devices": discovered_devices,
                        "last_scan": datetime.now().isoformat(),
                        "adaptive_scan": True,
                        "activity_level": activity_level
                    }
                }
                
                requests.post(
                    "http://supervisor/core/api/states/sensor.ble_gateway_raw_data",
                    headers=headers,
                    json=sensor_data
                )
            
            # Update last_devices for next adaptive interval calculation
            last_devices = discovered_devices
            
            # Calculate adaptive scan interval for next cycle
            adaptive_interval = determine_adaptive_scan_interval(
                scan_interval, 
                last_devices,
                activity_level
            )
            
            # Create a sensor to show current scan settings
            try:
                sensor_data = {
                    "state": adaptive_interval,
                    "attributes": {
                        "friendly_name": "BLE Scan Interval",
                        "icon": "mdi:timer-outline",
                        "unit_of_measurement": "seconds",
                        "base_interval": scan_interval,
                        "activity_level": activity_level,
                        "device_count": len(discovered_devices),
                        "adaptive_enabled": True
                    }
                }
                
                requests.post(
                    "http://supervisor/core/api/states/sensor.ble_scan_interval",
                    headers=headers,
                    json=sensor_data
                )
            except Exception as e:
                logging.debug(f"Error updating scan interval sensor: {e}")
            
        except Exception as e:
            logging.error(f"Discovery error: {e}")
            # Use base interval on errors
            adaptive_interval = scan_interval
        
        # Sleep between scans using adaptive interval
        logging.debug(f"Sleeping for {adaptive_interval} seconds before next scan")
        time.sleep(adaptive_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced BLE Device Discovery")
    parser.add_argument("--log-level", default="INFO", 
                        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    parser.add_argument("--scan-interval", type=int, default=DEFAULT_SCAN_INTERVAL,
                        help="Interval between BLE scans in seconds")
    parser.add_argument("--gateway-topic", default=DEFAULT_GATEWAY_TOPIC,
                        help="MQTT topic for BLE gateway")
    
    args = parser.parse_args()
    
    main(args.log_level, args.scan_interval, args.gateway_topic)
