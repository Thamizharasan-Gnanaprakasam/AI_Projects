#!/bin/bash
# Launcher script for VoiceInk GUI
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python run_gui.py "$@"
else
    python3 run_gui.py "$@"
fi
