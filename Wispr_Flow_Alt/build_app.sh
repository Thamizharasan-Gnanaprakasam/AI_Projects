#!/bin/bash
# Build script for VoiceInk macOS Application (.app bundle)
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=== Building VoiceInk macOS Application ==="

# Check Python environment
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "Error: Python 3 not found."
    exit 1
fi

# Ensure PyInstaller is installed
$PYTHON -m PyInstaller --version >/dev/null 2>&1 || {
    echo "Installing PyInstaller..."
    if command -v uv &>/dev/null; then
        uv pip install pyinstaller
    else
        $PYTHON -m pip install pyinstaller
    fi
}

echo "Running PyInstaller with VoiceInk.spec..."
$PYTHON -m PyInstaller --clean -y VoiceInk.spec

echo "=== Build Complete ==="
echo "Application bundle available at: dist/VoiceInk.app"
