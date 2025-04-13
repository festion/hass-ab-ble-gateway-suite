#\!/bin/bash
# Script to clean up the repository based on structure analysis

echo "Cleaning up repository structure..."

# Get the repository root directory
REPO_ROOT="$(dirname "$(dirname "$0")")"
cd "$REPO_ROOT" || exit 1

# Process temporary directories
echo "Removing temporary directories..."
rm -rf temp/

# Clean up Python cache files
echo "Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} +  2>/dev/null || true
find . -name "*.pyc" -delete

# Run the structure analysis to show duplicates
echo "Running structure analysis..."
python3 scripts/analyze_structure.py

echo "Cleanup complete\!"
echo "Run 'git status' to see what files were removed."
EOF < /dev/null
