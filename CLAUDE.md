# AprilBrother BLE Gateway Suite for Home Assistant

## How Claude Should Assist

Claude should help users with the following tasks related to this Home Assistant integration suite for AprilBrother BLE Gateways and BLE device discovery:

### Home Assistant Integration Component
- Modifications to Python code in the custom component
- Configuration flow adjustments
- MQTT integration enhancements
- Scanner functionality improvements
- Service definition updates

### BLE Discovery Add-on
- Modifications to Python code in `ble_discovery.py`
- Adjustments to YAML configuration files
- Docker-related configuration and build issues
- Add-on UI customization

## Key Commands to Run

### Custom Component
- Format: `black custom_components/`
- Lint: `flake8 custom_components/`
- Import sorting: `isort custom_components/`
- Test: `pytest tests/`

### BLE Discovery Add-on
- Lint and check Python code: `flake8 addon/ble_discovery.py`
- Run the add-on locally: `./addon/run.sh`
- Build Docker image: `docker build -t ble-discovery-addon ./addon`

## Important Files

### Custom Component
- `custom_components/ab_ble_gateway/`: Main component directory
- `custom_components/ab_ble_gateway/__init__.py`: Component initialization
- `custom_components/ab_ble_gateway/config_flow.py`: Configuration UI flow
- `custom_components/ab_ble_gateway/scanner.py`: BLE gateway scanner
- `custom_components/ab_ble_gateway/const.py`: Component constants

### BLE Discovery Add-on
- `addon/ble_discovery.py`: Main Python code for BLE device discovery
- `addon/ble_input_text.yaml`, `addon/ble_scripts.yaml`, `addon/btle_dashboard.yaml`: YAML configuration files
- `addon/config.json`: Add-on configuration
- `addon/Dockerfile`: Container build configuration
- `addon/run.sh`: Script to run the add-on

## Key Concepts
- AprilBrother BLE Gateway integration
- BLE device scanning and discovery
- MQTT integration with Home Assistant
- Signal strength (RSSI) threshold settings
- Dashboard UI components
- Device categorization and management

## Style Guidelines
- Follow Home Assistant custom component conventions
- Line length: 88 characters (black default)
- Imports: Use isort with sections (stdlib, third-party, first-party)
- Type hints: Required for function parameters and return values
- Error handling: Use try/except blocks with specific exceptions, log errors
- Naming: snake_case for variables/functions, PascalCase for classes
- String formatting: Use f-strings

## Current Improvements (2024-04-12)

### Fixed Issues:
1. **Home Assistant Restart on Gateway Reconnect**
   - Fixed the MQTT reconnect service that was causing Home Assistant to restart
   - Implemented improved error handling for MQTT message processing
   - Added safe wrapper for scanner MQTT handlers
   - Added empty message payload check to prevent processing errors
   - Removed automatic restart from device addition scripts (v1.4.1)

2. **"Extracted data is not a dictionary: <class 'int'>" Error**
   - Added better error handling in MQTT message processing
   - MQTT messages with integer payloads now handled gracefully
   - Added additional defensive coding in the message handler

### Implementation Details:
1. In `__init__.py`:
   - Created a `safe_mqtt_handler` wrapper for scanner MQTT handlers
   - Added proper error catching for the message handler
   - Implemented a debug handler as fallback when no scanner is found
   - Added check for empty payloads to skip processing

2. In `ble_scripts.yaml` (v1.4.1):
   - Removed the automatic `homeassistant.restart` service call from the `add_ble_device` script
   - Updated notification to inform users that a manual restart may be needed
   - This prevents unintended Home Assistant restarts when using the reconnect button

3. Next steps may include:
   - Testing MQTT reconnection with the new handlers
   - Reviewing other potential error sources in message processing
   - Adding more detailed documentation for diagnostic purposes