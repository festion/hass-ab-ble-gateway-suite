#!/usr/bin/env python3
"""
Unit tests for the BLE Discovery add-on
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta

# Import code to test
from ble_discovery import (
    setup_logging,
    load_discoveries,
    save_discoveries,
    process_ble_gateway_data,
    determine_adaptive_scan_interval,
    get_home_assistant_activity_level
)

class TestBleDiscovery(unittest.TestCase):
    """Test cases for BLE Discovery addon"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temp file for discoveries
        self.test_discoveries_file = "/tmp/test_discoveries.json"
        os.environ["DISCOVERIES_FILE"] = self.test_discoveries_file
        
        # Sample test data
        self.sample_discoveries = [
            {
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "rssi": -75,
                "manufacturer": "Apple",
                "device_type": "Apple Device",
                "last_seen": datetime.now().isoformat()
            },
            {
                "mac_address": "11:22:33:44:55:66",
                "rssi": -85,
                "manufacturer": "Google",
                "device_type": "Google Device",
                "last_seen": datetime.now().isoformat()
            }
        ]
        
        # Sample gateway data
        self.sample_gateway_data = [
            ["entity_id", "AA:BB:CC:DD:EE:FF", "-75", "{}"],
            ["entity_id", "11:22:33:44:55:66", "-85", "{}"]
        ]
    
    def tearDown(self):
        """Clean up after tests"""
        if os.path.exists(self.test_discoveries_file):
            os.remove(self.test_discoveries_file)
    
    def test_load_discoveries_file_not_exists(self):
        """Test loading discoveries when file doesn't exist"""
        # Ensure file doesn't exist
        if os.path.exists(self.test_discoveries_file):
            os.remove(self.test_discoveries_file)
            
        # Test loading non-existent file
        with patch('ble_discovery.DISCOVERIES_FILE', self.test_discoveries_file):
            result = load_discoveries()
            self.assertEqual(result, [])
    
    def test_save_and_load_discoveries(self):
        """Test saving and loading discoveries from file"""
        with patch('ble_discovery.DISCOVERIES_FILE', self.test_discoveries_file):
            # Save discoveries
            save_discoveries(self.sample_discoveries)
            
            # Load discoveries
            loaded = load_discoveries()
            
            # Verify data was correctly saved and loaded
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["mac_address"], "AA:BB:CC:DD:EE:FF")
            self.assertEqual(loaded[1]["mac_address"], "11:22:33:44:55:66")
    
    def test_process_ble_gateway_data(self):
        """Test processing gateway data into structured format"""
        processed = process_ble_gateway_data(self.sample_gateway_data)
        
        # Check processed data structure
        self.assertEqual(len(processed), 2)
        self.assertEqual(processed[0]["mac_address"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(processed[0]["rssi"], -75)
    
    def test_determine_adaptive_scan_interval_night_mode(self):
        """Test adaptive scan interval calculation during night hours"""
        # Mock datetime to simulate night time
        midnight = datetime.now().replace(hour=2, minute=0, second=0, microsecond=0)
        
        with patch('ble_discovery.datetime') as mock_datetime:
            # Configure the mock to return a specific time
            mock_datetime.now.return_value = midnight
            # Pass through the nowattr call in the datetime.timedelta constructor
            mock_datetime.timedelta = timedelta
            
            # Test with low activity at night
            devices = self.sample_discoveries
            base_interval = 60
            activity_level = 10
            
            # Should return longer interval at night with low activity
            interval = determine_adaptive_scan_interval(base_interval, devices, activity_level)
            # Expecting interval to be increased (multiplier > 1)
            self.assertGreater(interval, base_interval)
    
    def test_determine_adaptive_scan_interval_active(self):
        """Test adaptive scan interval calculation during active periods"""
        # Mock datetime to simulate daytime
        noon = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        
        with patch('ble_discovery.datetime') as mock_datetime:
            # Configure the mock to return daytime
            mock_datetime.now.return_value = noon
            # Pass through the nowattr call in the datetime.timedelta constructor
            mock_datetime.timedelta = timedelta
            
            # Test with high activity during day
            devices = self.sample_discoveries
            base_interval = 60
            activity_level = 80
            
            # Should return shorter interval with high activity
            interval = determine_adaptive_scan_interval(base_interval, devices, activity_level)
            # Expecting interval to be decreased (multiplier < 1)
            self.assertLess(interval, base_interval)

if __name__ == "__main__":
    unittest.main()