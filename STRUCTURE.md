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
│       ├── ble_dashboard_snippets.yaml # Dashboard code snippets
│       ├── ble_input_text.yaml  # Input text configuration
│       ├── config_flow.py       # Configuration UI
│       ├── const.py             # Constants and definitions
│       ├── manifest.json        # Component manifest
│       ├── scanner.py           # BLE scanner implementation
│       ├── scripts/             # Utility scripts
│       ├── scripts.yaml         # Utility scripts configuration
│       ├── services.yaml        # Service definitions
│       ├── strings.json         # UI strings
│       ├── translations/        # Language translations
│       └── util.py              # Utility functions
│
├── scripts/                     # Utility scripts for the repository
│   └── analyze_structure.py     # Structure analysis script
│
├── CLAUDE.md                    # Claude Code assistance file
├── gateway41.jpg                # Gateway image
├── hacs.json                    # HACS configuration
├── info.md                      # HACS information
├── LICENSE                      # License file
├── logo.png                     # Logo image
├── README.md                    # Main documentation
├── repository.json              # Home Assistant add-on repository definition
├── requirements.txt             # Package dependencies
├── requirements_dev.txt         # Development dependencies
├── requirements_test.txt        # Testing dependencies
├── setup.cfg                    # Python setup configuration
├── setup_instructions.md        # Setup instructions
├── STRUCTURE.md                 # This file
├── pytest.ini                   # pytest configuration
│
├── .github/                     # GitHub configuration
│   ├── CODEOWNERS               # File ownership configuration
│   ├── ISSUE_TEMPLATE/          # GitHub issue templates
│   │   ├── bug_report.md        # Bug report template
│   │   └── feature_request.md   # Feature request template
│   └── dependabot.yml           # Dependabot configuration
│
├── Dashboard files:
│   ├── atomic_dashboard.yaml    # Atomic design dashboard
│   ├── basic_dashboard.yaml     # Basic dashboard
│   ├── btle_combined_dashboard.yaml  # Main combined dashboard
│   ├── btle_dashboard.yaml      # Default dashboard
│   ├── btle_gateway_management.yaml  # Gateway management dashboard
│   ├── btle_simple_dashboard.yaml    # Simple dashboard
│   ├── btle_ultra_simple.yaml   # Ultra-simple dashboard
│   ├── enhance_ble_devices.yaml # Device enhancement dashboard
│   ├── minimal_dashboard.yaml   # Minimal dashboard
│   ├── static_dashboard.yaml    # Static dashboard
│   └── verification_dashboard.yaml   # Verification dashboard
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

## Maintaining Repository Structure

To maintain a clean repository structure:

1. Use the analyze_structure.py script to identify issues:
   ```bash
   python3 scripts/analyze_structure.py
   ```

2. The script will identify:
   - Unnecessary files not documented in STRUCTURE.md
   - Missing files that are documented but don't exist
   - Duplicate files with identical content

3. Run the cleanup script to remove temporary files and caches:
   ```bash
   bash scripts/cleanup.sh
   ```

4. When adding new files to the repository:
   - Update STRUCTURE.md to document them
   - Update scripts/analyze_structure.py to include them in EXPECTED_PATHS

5. For duplicated files, consider:
   - Using symbolic links to maintain one source of truth
   - Implementing a build process to copy files from development to deployment locations