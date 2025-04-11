# April Brother (AB) BLE Gateway - Enhanced

This Home Assistant integration allows forwarding BLE data from the AprilBrother BLE Gateway V4 to the Home Assistant bluetooth component.

## Features

- Automatic discovery of gateways on the network (via SSDP)
- Support for MQTT forwarding
- Integration with Home Assistant's built-in Bluetooth component
- Validated MQTT settings during setup

## Setup Requirements

1. Set up the [MQTT component](https://www.home-assistant.io/integrations/mqtt/) in Home Assistant
2. Configure the gateway to use MQTT (connection type 3)
3. Ensure gateway MQTT settings match Home Assistant's MQTT configuration
4. Provide MQTT Topic and MQTT ID Prefix during setup

## Add-on Repository

This repository also serves as a Home Assistant add-on repository containing the Enhanced BLE Device Discovery add-on that works with this integration.