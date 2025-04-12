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

## Current Improvements (2024-04-13)

### Fixed Issues:
1. **Home Assistant Restart on Gateway Reconnect**
   - Fixed the MQTT reconnect service that was causing Home Assistant to restart
   - Implemented improved error handling for MQTT message processing
   - Added safe wrapper for scanner MQTT handlers
   - Added empty message payload check to prevent processing errors
   - Removed automatic restart from device addition scripts (v1.4.1)
   - Improved lock handling to prevent concurrent reconnects (v0.2.8)
   - Added a static MQTT handler to avoid duplicate subscriptions (v0.2.8)
   - Fixed argument mismatch in advertisement processing (v0.2.9)
   - Added 30-second cooldown between reconnect attempts (v0.3.0)
   - Implemented global reconnect state tracking to prevent concurrent reconnects (v0.3.0)

2. **"Extracted data is not a dictionary: <class 'int'>" Error**
   - Added better error handling in MQTT message processing
   - MQTT messages with integer payloads now handled gracefully
   - Added additional defensive coding in the message handler
   - Enhanced JSON parsing with verbose logging for troubleshooting (v0.2.8)
   - Added detailed device data format validation and logging (v0.2.8)

3. **JSON Payload Handling**
   - Added support for JSON-formatted payloads from BLE gateways
   - Improved extraction of device data from different payload formats
   - Enhanced metadata extraction from payloads
   - Added device mapping support for friendly device names

### Implementation Details:
1. In `__init__.py` (v0.3.0):
   - Implemented global reconnect state tracking at domain level
   - Added 30-second cooldown between reconnect attempts
   - Ensured proper cleanup of reconnect state even on error
   - Fixed critical issue with _async_on_advertisement call parameter mismatch
   - Added required monotonic timestamp and details parameters to advertisement calls
   - Implemented fallback MQTT message handling to prevent errors during reconnect
   - Enhanced the JSON parsing with more verbose logging
   - Created a persistent static MQTT handler to prevent multiple subscriptions
   - Improved the locking mechanism for MQTT reconnection
   - Added detailed device data format validation and logging
   - Implemented enhanced error handling in all critical sections
   - Added unsubscribe delay to ensure clean MQTT reconnects
   - Fixed potential race conditions in MQTT subscription handling

2. In `ble_scripts.yaml` (v1.4.1):
   - Removed the automatic `homeassistant.restart` service call from the `add_ble_device` script
   - Updated notification to inform users that a manual restart may be needed
   - This prevents unintended Home Assistant restarts when using the reconnect button

3. Debugging Improvements (v0.3.0):
   - Added domain-level logging of reconnect operations
   - Enhanced parameter validation in reconnect function
   - Added detailed payload structure logging for troubleshooting
   - Enhanced logging of device data format detection
   - Improved metadata extraction and device mapping
   - Added MQTT topic storage for easier diagnostics
   - Implemented better error messages throughout the codebase
   - Added defensive error handling for direct MQTT message processing