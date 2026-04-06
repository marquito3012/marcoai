#!/bin/bash
# Run tests for Marco AI backend
# Memory-efficient test runner for Raspberry Pi 3

set -e

echo "=== Marco AI Test Suite ==="

# Check if running in Docker container
if [ -f /.dockerenv ]; then
    echo "Running in Docker container..."
    PYTHON_CMD="python"
elif [ -d ".venv" ]; then
    echo "Using existing virtual environment..."
    PYTHON_CMD="./.venv/bin/python"
else
    echo "Running locally - installing dependencies..."
    PYTHON_CMD="python3"
    # Try to install dependencies, but handle externally managed environments
    $PYTHON_CMD -m pip install -q --disable-pip-version-check -r requirements.txt 2>/dev/null || echo "Note: Global pip install skipped (managed environment). Use a venv for local runs."
fi

# Install test dependencies
python -m pip install -q --disable-pip-version-check --no-warn-script-location pytest pytest-asyncio

echo "Running tests..."
cd "$(dirname "$0")"

# Run tests using python -m pytest (avoids PATH issues)
# -p no:cacheprovider avoids permission issues in Docker containers
$PYTHON_CMD -m pytest tests/ \
    -v \
    --tb=short \
    -x \
    -p no:cacheprovider \
    -q

echo "=== Tests Complete ==="
