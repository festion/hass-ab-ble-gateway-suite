"""Constants for the April Brother BLE Gateway integration."""

DOMAIN = "ab_ble_gateway"

# Services
SERVICE_CLEAN_FAILED_ENTRIES = "clean_failed_entries"
SERVICE_RECONNECT = "reconnect"
ATTR_DRY_RUN = "dry_run"

# Logging
LOGGER_NAME = "ab_ble_gateway"
LOG_FILE = "ab_ble_gateway.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_LEVEL = "INFO"
