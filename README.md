# April Brother (AB) BLE Gateway - Enhanced

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

## Overview

This Home Assistant integration allows forwarding BLE data from the AprilBrother BLE Gateway V4 to the Home Assistant [bluetooth component](https://www.home-assistant.io/integrations/bluetooth/).

![AB BLE Gateway V4](gateway41.jpg)

AprilBrother BLE Gateway V4 is an ESP32- and NRF52832-based BLE to network gateway and bridge. It reads BLE advertisement data such as iBeacon, Eddystone or customized format data and sends to LAN/internet server via MQTT.

## Features

- Automatic discovery of gateways on the network (via SSDP)
- Support for MQTT forwarding
- Integration with Home Assistant's built-in Bluetooth component
- Validated MQTT settings during setup

## Installation

### HACS Installation
1. Add this repository to HACS as a custom repository
2. Install the "April Brother BLE Gateway - Enhanced" integration through HACS
3. Restart Home Assistant
4. Add the integration through the Home Assistant UI (Configuration → Integrations → Add Integration)
5. Select "April Brother BLE Gateway - Enhanced" and follow the setup instructions

### Manual Installation
1. Copy the `custom_components/ab_ble_gateway` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration through the Home Assistant UI

## Setup Requirements

1. Set up the [MQTT component](https://www.home-assistant.io/integrations/mqtt/) in Home Assistant
2. Configure the gateway to use MQTT (connection type 3)
3. Ensure gateway MQTT settings match Home Assistant's MQTT configuration
4. Provide MQTT Topic and MQTT ID Prefix during setup

## Add-on Repository

This repository also serves as a Home Assistant add-on repository containing the Enhanced BLE Device Discovery add-on.

To add this repository to your Home Assistant instance:

1. In Home Assistant, navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three-dot menu in the top right and select **Repositories**
3. Add this repository URL: `https://github.com/festion/hass-ab-ble-gateway-suite`
4. Click **Add** and then **Close**
5. The "Enhanced BLE Device Discovery" add-on should now appear in the add-on store

## Support

For issues, questions, or feature requests, please open an issue on GitHub.