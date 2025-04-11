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