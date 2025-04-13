#!/usr/bin/env python3
"""
Script to analyze the repository structure and identify unneeded files.
This script helps maintain consistency in the repository by identifying files
that are not part of the documented structure.
"""

import os
import sys
import re
import json
from pathlib import Path

# Define the expected structure based on documentation
EXPECTED_PATHS = [
    # Add-on development directories
    "addon/",
    "addon/Dockerfile",
    "addon/README.md",
    "addon/ble_discovery.py",
    "addon/ble_input_text.yaml",
    "addon/ble_scripts.yaml",
    "addon/btle_dashboard.yaml",
    "addon/enhanced_ble_discovery/",
    "addon/enhanced_ble_discovery/ble_discovery.py",
    "addon/enhanced_ble_discovery/ble_input_text.yaml",
    "addon/enhanced_ble_discovery/ble_scripts.yaml",
    "addon/enhanced_ble_discovery/btle_dashboard.yaml",
    "addon/enhanced_ble_discovery/config.json",
    "addon/enhanced_ble_discovery/Dockerfile",
    "addon/enhanced_ble_discovery/README.md",
    "addon/enhanced_ble_discovery/rootfs/",
    "addon/enhanced_ble_discovery/rootfs/ble_discovery.py",
    "addon/enhanced_ble_discovery/rootfs/run.sh",
    "addon/enhanced_ble_discovery/run.sh",
    "addon/enhanced_ble_discovery/test_ble_discovery.py",
    "addon/rootfs/",
    "addon/rootfs/ble_discovery.py",
    "addon/rootfs/run.sh",
    "addon/run.sh",
    "addon/test_ble_discovery.py",
    
    # Add-on for HA
    "enhanced_ble_discovery/",
    "enhanced_ble_discovery/ble_discovery.py",
    "enhanced_ble_discovery/ble_input_text.yaml",
    "enhanced_ble_discovery/ble_scripts.yaml",
    "enhanced_ble_discovery/btle_dashboard.yaml",
    "enhanced_ble_discovery/btle_gateway_management.yaml",
    "enhanced_ble_discovery/config.json",
    "enhanced_ble_discovery/Dockerfile",
    "enhanced_ble_discovery/README.md",
    "enhanced_ble_discovery/rootfs/",
    "enhanced_ble_discovery/rootfs/ble_discovery.py",
    "enhanced_ble_discovery/rootfs/run.sh",
    "enhanced_ble_discovery/run.sh",
    "enhanced_ble_discovery/test_ble_discovery.py",
    
    # Custom component
    "custom_components/",
    "custom_components/ab_ble_gateway/",
    "custom_components/ab_ble_gateway/__init__.py",
    "custom_components/ab_ble_gateway/ble_dashboard_snippets.yaml",
    "custom_components/ab_ble_gateway/ble_input_text.yaml",
    "custom_components/ab_ble_gateway/config_flow.py",
    "custom_components/ab_ble_gateway/const.py",
    "custom_components/ab_ble_gateway/manifest.json",
    "custom_components/ab_ble_gateway/scanner.py",
    "custom_components/ab_ble_gateway/scripts/",
    "custom_components/ab_ble_gateway/scripts/README.md",
    "custom_components/ab_ble_gateway/scripts/clean_config_entries.py",
    "custom_components/ab_ble_gateway/scripts.yaml",
    "custom_components/ab_ble_gateway/services.yaml",
    "custom_components/ab_ble_gateway/strings.json",
    "custom_components/ab_ble_gateway/translations/",
    "custom_components/ab_ble_gateway/translations/en.json",
    "custom_components/ab_ble_gateway/util.py",
    
    # Documentation and configuration files
    "CLAUDE.md",
    "CODEOWNERS", 
    "gateway41.jpg",
    "hacs.json",
    "info.md",
    "LICENSE",
    "logo.png",
    "README.md",
    "repository.json",
    "requirements.txt",
    "requirements_dev.txt",
    "requirements_test.txt",
    "setup.cfg",
    "setup_instructions.md",
    "STRUCTURE.md",
    "pytest.ini",
    
    # GitHub configuration files
    ".github/",
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE/",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/dependabot.yml",
    
    # Dashboard files
    "atomic_dashboard.yaml",
    "basic_dashboard.yaml",
    "btle_combined_dashboard.yaml",
    "btle_dashboard.yaml",
    "btle_gateway_management.yaml",
    "btle_simple_dashboard.yaml",
    "btle_ultra_simple.yaml",
    "enhance_ble_devices.yaml",
    "minimal_dashboard.yaml",
    "static_dashboard.yaml",
    "verification_dashboard.yaml",
    
    # Scripts directory
    "scripts/",
    "scripts/analyze_structure.py",
    "scripts/cleanup.sh",
    
    # Test directory
    "tests/",
    "tests/__init__.py",
    "tests/test_init.py",
]

# Directories and files to exclude from analysis
EXCLUSIONS = [
    ".git/",
    ".github/",  # GitHub-specific configuration
    "__pycache__/",
    "*.pyc",
    "venv/",
    ".vscode/",
    ".idea/",
]

def should_exclude(path):
    """Check if a path should be excluded from analysis."""
    for exclusion in EXCLUSIONS:
        if exclusion.endswith('/'):
            # Directory exclusion
            if str(path).startswith(exclusion) or str(path).startswith('./' + exclusion):
                return True
        elif '*' in exclusion:
            # Pattern exclusion
            pattern = exclusion.replace('.', '\\.').replace('*', '.*')
            if re.match(pattern, os.path.basename(path)):
                return True
        else:
            # Exact file exclusion
            if os.path.basename(path) == exclusion:
                return True
    return False

def find_unnecessary_files(root_dir):
    """
    Find files that are not in the expected structure.
    
    Args:
        root_dir: The root directory of the repository
        
    Returns:
        list: List of files that are not in the expected structure
    """
    unnecessary_files = []
    
    # Convert to absolute paths for comparison
    root_path = Path(root_dir).resolve()
    expected_absolute = [str((root_path / path).resolve()) for path in EXPECTED_PATHS]
    
    # Add all parent directories of expected paths
    parent_dirs = set()
    for path in expected_absolute:
        current_dir = os.path.dirname(path)
        while current_dir and current_dir.startswith(str(root_path)):
            parent_dirs.add(current_dir)
            current_dir = os.path.dirname(current_dir)
    
    # Walk through the directory structure
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirpath_rel = os.path.relpath(dirpath, root_path)
        
        # Skip excluded directories
        if should_exclude(dirpath_rel):
            # Remove this directory from further processing
            dirnames[:] = []
            continue
            
        # Check directories
        for dirname in dirnames:
            dir_path = os.path.join(dirpath, dirname)
            if dir_path not in parent_dirs and not should_exclude(os.path.join(dirpath_rel, dirname)):
                unnecessary_files.append(os.path.join(dirpath_rel, dirname + '/'))
        
        # Check files
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_rel_path = os.path.relpath(file_path, root_path)
            
            if str(file_path) not in expected_absolute and not should_exclude(file_rel_path):
                unnecessary_files.append(file_rel_path)
    
    return sorted(unnecessary_files)

def find_missing_files(root_dir):
    """
    Find files that are in the expected structure but missing from the filesystem.
    
    Args:
        root_dir: The root directory of the repository
        
    Returns:
        list: List of files that are missing
    """
    missing_files = []
    root_path = Path(root_dir).resolve()
    
    for path in EXPECTED_PATHS:
        file_path = root_path / path
        if not file_path.exists():
            missing_files.append(path)
    
    return sorted(missing_files)

def find_duplicate_files(root_dir):
    """
    Find duplicate files across add-on directories by comparing content.
    
    Args:
        root_dir: The root directory of the repository
        
    Returns:
        dict: Dictionary of duplicate files keyed by content hash
    """
    root_path = Path(root_dir).resolve()
    content_map = {}
    
    # Only check ble_discovery.py and yaml files
    check_patterns = [
        "**/ble_discovery.py",
        "**/*.yaml"
    ]
    
    # Skip known duplicates like rootfs copies
    skip_pattern = re.compile(r'rootfs/|__pycache__/')
    
    for pattern in check_patterns:
        for file_path in root_path.glob(pattern):
            if skip_pattern.search(str(file_path)):
                continue
                
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                content_hash = hash(content)
                
                if content_hash not in content_map:
                    content_map[content_hash] = []
                content_map[content_hash].append(str(file_path.relative_to(root_path)))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    # Filter to only return groups with more than one file
    duplicates = {k: v for k, v in content_map.items() if len(v) > 1}
    return duplicates

def evaluate_project_structure(root_dir='.'):
    """
    Evaluate the project structure and print results.
    
    Args:
        root_dir: The root directory of the repository
    """
    print("Analyzing project structure...")
    print(f"Repository root: {os.path.abspath(root_dir)}")
    print()
    
    unnecessary_files = find_unnecessary_files(root_dir)
    missing_files = find_missing_files(root_dir)
    duplicate_files = find_duplicate_files(root_dir)
    
    # Print results
    print("=== STRUCTURE ANALYSIS RESULTS ===")
    print()
    
    if unnecessary_files:
        print(f"UNNECESSARY FILES: {len(unnecessary_files)} found")
        print("These files are not part of the documented structure:")
        for file in unnecessary_files:
            print(f"  - {file}")
        print()
    else:
        print("UNNECESSARY FILES: None found")
        print()
        
    if missing_files:
        print(f"MISSING FILES: {len(missing_files)} found")
        print("These files are in the documented structure but missing from the filesystem:")
        for file in missing_files:
            print(f"  - {file}")
        print()
    else:
        print("MISSING FILES: None found")
        print()
    
    if duplicate_files:
        print(f"DUPLICATE FILES: {len(duplicate_files)} groups found")
        print("These files have identical content (excluding rootfs/ copies which are expected):")
        for content_hash, files in duplicate_files.items():
            print(f"  Group:")
            for file in files:
                print(f"    - {file}")
        print()
    else:
        print("DUPLICATE FILES: None found")
        print()
    
    print("=== RECOMMENDATIONS ===")
    if unnecessary_files:
        print("Consider removing unnecessary files or updating STRUCTURE.md to include them.")
    if missing_files:
        print("Create missing files or update STRUCTURE.md to remove them.")
    if duplicate_files:
        print("Consider consolidating duplicate files to maintain consistency.")
    
    if not (unnecessary_files or missing_files or duplicate_files):
        print("Project structure looks good! No issues found.")
    
    return {
        "unnecessary_files": unnecessary_files,
        "missing_files": missing_files,
        "duplicate_files": duplicate_files
    }

if __name__ == "__main__":
    # Use the provided directory or the current directory
    root_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    results = evaluate_project_structure(root_dir)
    
    # Optionally write results to a JSON file
    if len(sys.argv) > 2 and sys.argv[2] == '--json':
        output_file = sys.argv[3] if len(sys.argv) > 3 else 'structure_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {output_file}")