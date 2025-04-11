"""Bluetooth scanner for esphome."""
from __future__ import annotations

import re

from aioesphomeapi import BluetoothLEAdvertisement

from homeassistant.components.bluetooth import BaseHaRemoteScanner
from homeassistant.core import callback

TWO_CHAR = re.compile("..")


class ESPHomeScanner(BaseHaRemoteScanner):
    """Scanner for esphome."""

    @callback
    def async_on_advertisement(self, adv: BluetoothLEAdvertisement) -> None:
        """Call the registered callback."""
        from homeassistant.components.bluetooth import MONOTONIC_TIME
        
        address = ":".join(TWO_CHAR.findall("%012X" % adv.address))  # must be upper
        monotonic_time = MONOTONIC_TIME()
        
        try:
            self._async_on_advertisement(
                address,
                adv.rssi,
                adv.name,
                adv.service_uuids,
                adv.service_data,
                adv.manufacturer_data,
                None,
                dict(),  # details parameter
                [monotonic_time]  # advertisement_monotonic_time as an iterable
            )
        except TypeError as err:
            # Fall back to the old API if the new one fails
            if "advertisement_monotonic_time" in str(err):
                self._async_on_advertisement(
                    address,
                    adv.rssi,
                    adv.name,
                    adv.service_uuids,
                    adv.service_data,
                    adv.manufacturer_data,
                    None,
                )
            else:
                raise
