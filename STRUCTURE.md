# AprilBrother BLE Gateway Suite - Project Structure

This document explains the structure of the combined project.

## Repository Structure

```
hass-ab-ble-gateway-suite/
├── addon/                       # Add-ons directory (development version)
│   └── enhanced_ble_discovery/  # BLE Discovery Add-on development code
│       └── ...                  # Add-on implementation files
│
├── enhanced_ble_discovery/      # BLE Discovery Add-on (HA-compatible location)
│   ├── ble_discovery.py         # Main add-on code
│   ├── ble_*.yaml               # Dashboard configuration
│   ├── config.json              # Add-on configuration
│   ├── Dockerfile               # Container build definition
│   ├── rootfs/                  # Add-on container filesystem
│   │   ├── ble_discovery.py     # Discovery script
│   │   └── run.sh               # Container entry script
│   ├── run.sh                   # Local testing script
│   └── test_ble_discovery.py    # Unit tests
│
├── custom_components/            # Home Assistant Integration
│   └── ab_ble_gateway/          # AB BLE Gateway component
│       ├── __init__.py          # Component initialization
│       ├── config_flow.py       # Configuration UI
│       ├── const.py             # Constants and definitions
│       ├── manifest.json        # Component manifest
│       ├── scanner.py           # BLE scanner implementation
│       ├── scripts/             # Utility scripts
│       ├── services.yaml        # Service definitions
│       ├── strings.json         # UI strings
│       ├── translations/        # Language translations
│       └── util.py              # Utility functions
│
├── CLAUDE.md                    # Claude Code assistance file
├── gateway41.jpg                # Gateway image
├── hacs.json                    # HACS configuration
├── info.md                      # HACS information
├── LICENSE                      # License file
├── logo.png                     # Logo image
├── README.md                    # Main documentation
├── repository.json              # Home Assistant add-on repository definition
├── requirements_dev.txt         # Development dependencies
├── requirements_test.txt        # Testing dependencies
├── setup.cfg                    # Python setup configuration
└── STRUCTURE.md                 # This file
```

## Component Relationships

1. **AB BLE Gateway Integration**: 
   - Establishes connection with AprilBrother BLE Gateway via MQTT
   - Forwards BLE advertisements to Home Assistant Bluetooth component
   - Auto-discovers gateway devices on network via SSDP

2. **BLE Discovery Add-on**:
   - Provides user interface for BLE device management
   - Scans for BLE devices using all available gateways
   - Helps configure optimal signal thresholds
   - Categorizes devices based on advertisement data

## Repository Format

The repository is structured to serve two purposes:

1. **HACS Custom Repository** - For installing the custom component
   - The custom_components directory contains the integration
   - The hacs.json file defines the integration for HACS

2. **Home Assistant Add-on Repository** - For installing the BLE Discovery add-on
   - The repository.json in the root defines the repository
   - Add-ons are located in the root directory following Home Assistant standards
   - Each add-on has its own directory with a config.json file 
   - The addon/ directory contains development versions of the add-ons

## Important Notes on Repository Structure

Home Assistant has specific requirements for add-on repositories:
1. Repository must contain a repository.json file in the root
2. Add-ons must be located directly in the root directory, NOT in an /addons subfolder
3. Each add-on must have its own directory with a config.json

## Development Workflow

1. **Component Development**:
   - Edit files in `custom_components/ab_ble_gateway/`
   - Use `black`, `flake8`, and `isort` for code formatting
   - Test changes with `pytest`

2. **Add-on Development**:
   - Edit files in `addon/enhanced_ble_discovery/` for development
   - Copy changes to `enhanced_ble_discovery/` for deployment
   - Test locally with run.sh
   - Build container with Docker for full testing

## Release Process

Both components must be versioned together for compatibility. When updating:

1. Update version numbers in:
   - `custom_components/ab_ble_gateway/manifest.json`
   - `enhanced_ble_discovery/config.json`

2. Ensure all documentation is updated to reflect changes

3. Create a new release on GitHub that includes both component and add-on changes