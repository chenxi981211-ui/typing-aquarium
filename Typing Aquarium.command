#!/bin/bash
# Double-clickable launcher for Typing Aquarium.
#
# Finder runs .command files from the user's home directory, not from where the
# file lives, so this cds to its own folder first - the app loads assets, fish
# data and the save file by relative path and finds none of them otherwise.

cd "$(dirname "$0")" || exit 1

# Prefer the project venv; fall back to whatever python3 is on PATH so the file
# still works on a machine that never had the venv set up.
VENV="$HOME/.venvs/aquarium/bin/python"
if [ -x "$VENV" ]; then
    PYTHON="$VENV"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
else
    echo "Python 3 not found. Install it from https://www.python.org/downloads/"
    echo "Press any key to close."
    read -r -n 1
    exit 1
fi

if ! "$PYTHON" -c "import PyQt6" 2>/dev/null; then
    echo "Missing dependencies. Installing them now..."
    "$PYTHON" -m pip install --quiet PyQt6 pynput pillow || {
        echo "Install failed. Press any key to close."
        read -r -n 1
        exit 1
    }
fi

echo "Starting Typing Aquarium..."
echo "Typing is only counted once this app has Accessibility permission:"
echo "  System Settings > Privacy & Security > Accessibility"
echo ""
echo "Closing this Terminal window will quit the aquarium."
echo ""

exec "$PYTHON" main.py
