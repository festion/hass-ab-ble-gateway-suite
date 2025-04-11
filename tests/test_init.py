"""Test integration initialization."""
from unittest.mock import patch

from homeassistant.setup import async_setup_component

from custom_components.ab_ble_gateway.const import DOMAIN


async def test_async_setup(hass):
    """Test the component gets setup."""
    with patch("custom_components.ab_ble_gateway.setup_abble"):
        assert await async_setup_component(hass, DOMAIN, {}) is True