#!/bin/bash
# Launch Typing Aquarium against the staged demo save, for recording video.
#
# AQUARIUM_SAVE redirects every read and write to promo/demo-save.json, so the
# real save file is not opened at all - type as much as you like on camera and
# your actual collection is untouched.

cd "$(dirname "$0")" || exit 1

VENV="$HOME/.venvs/aquarium/bin/python"
if [ -x "$VENV" ]; then
    PYTHON="$VENV"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
else
    echo "Python 3 not found."
    read -r -n 1
    exit 1
fi

# Rebuild it each launch so the dates are always current - a week chart that
# stops three weeks ago looks broken on camera.
"$PYTHON" make_demo_save.py || exit 1

export AQUARIUM_SAVE="$PWD/promo/demo-save.json"
# The fish that arrives when you type on camera. Change it to stage a different
# reveal - any id from fish.JSON works, owned or not.
export AQUARIUM_DEMO_FISH="antennata_lionfish"

echo ""
echo "=============================================="
echo "  DEMO MODE - recording only"
echo "  save file: promo/demo-save.json"
echo "  your real save is NOT being used"
echo ""
echo "  type for ~12 seconds to trigger the unlock"
echo "  arriving fish: $AQUARIUM_DEMO_FISH"
echo "=============================================="
echo ""

exec "$PYTHON" main.py
