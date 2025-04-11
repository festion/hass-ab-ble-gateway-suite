#!/usr/bin/python3
"""
Script to clean up failed integration config entries.
Usage: ./clean_config_entries.py <path-to-config-dir> [--domain DOMAIN] [--dry-run]
"""

import argparse
import json
import os
import sys


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Clean up failed integration config entries")
    parser.add_argument("config_dir", help="Path to Home Assistant config directory")
    parser.add_argument("--domain", help="Only remove entries for this domain")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Don't actually modify the file, just show what would be done")
    return parser.parse_args()


def clean_config_entries(config_dir, domain=None, dry_run=False):
    """Clean up failed integration config entries."""
    # Path to the storage file
    storage_file = os.path.join(config_dir, ".storage/core.config_entries")
    
    if not os.path.exists(storage_file):
        print(f"Error: Config entries file not found at {storage_file}")
        return 1
    
    # Load current config entries
    with open(storage_file, 'r') as f:
        config_data = json.load(f)
    
    entries = config_data.get("data", {}).get("entries", [])
    original_count = len(entries)
    
    # Create backup
    backup_file = f"{storage_file}.bak"
    if not dry_run:
        with open(backup_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"Created backup at {backup_file}")
    
    # Filter entries
    if domain:
        filtered_entries = [entry for entry in entries if entry.get("domain") != domain]
        removed = original_count - len(filtered_entries)
        print(f"Would remove {removed} entries for domain '{domain}'")
    else:
        # Keep only entries that are not in a failed state
        filtered_entries = [entry for entry in entries 
                           if entry.get("state") != "failed_unload"]
        removed = original_count - len(filtered_entries)
        print(f"Would remove {removed} failed entries")
    
    if removed == 0:
        print("No entries to remove.")
        return 0
    
    # Update the data
    if not dry_run:
        config_data["data"]["entries"] = filtered_entries
        with open(storage_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"Removed {removed} entries. Original file backed up at {backup_file}")
        print("You should restart Home Assistant to apply these changes.")
    else:
        print("Dry run complete. No changes were made.")
    
    return 0


def main():
    """Main entry point."""
    args = parse_args()
    return clean_config_entries(args.config_dir, args.domain, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())