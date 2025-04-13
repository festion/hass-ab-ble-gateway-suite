# Repository Management Scripts

This directory contains scripts used for repository maintenance and management.

## Available Scripts

### analyze_structure.py

Analyzes the repository structure against the documented structure in STRUCTURE.md:

```bash
python3 scripts/analyze_structure.py
```

Features:
- Identifies unnecessary files not documented in STRUCTURE.md
- Finds missing files that are documented but don't exist
- Detects duplicate files with identical content
- Provides recommendations for cleanup

Optional arguments:
- `--json <output_file>`: Save results to a JSON file
  ```bash
  python3 scripts/analyze_structure.py --json structure_analysis.json
  ```

### cleanup.sh

Helps maintain a clean repository by removing temporary files and caches:

```bash
bash scripts/cleanup.sh
```

Features:
- Removes temporary directories (`temp/`)
- Cleans Python cache files (`__pycache__/` and `*.pyc`)
- Runs structure analysis to show any remaining issues

## Maintaining Repository Structure

When adding new files to the repository:
1. Update STRUCTURE.md to document them
2. Update scripts/analyze_structure.py to include them in EXPECTED_PATHS

For more information, see the "Maintaining Repository Structure" section in STRUCTURE.md.