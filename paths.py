# paths.py
"""Where the app reads its assets from, and where it is allowed to write.

Running from source these are the same folder, which is why everything used to
get away with plain relative paths. Inside a .app bundle they must be different:
the bundle is read-only in practice - macOS may relocate or replace it, and a
signed bundle breaks its own signature if anything inside changes - so the save
file and logs have to live in the user's Application Support instead.
"""

import os
import sys

APP_NAME = "Typing Aquarium"


def is_frozen():
    """True when running from a PyInstaller bundle rather than source."""
    return getattr(sys, "frozen", False)


def resource_root():
    """Folder holding the read-only files: assets/, fish.JSON."""
    if is_frozen():
        # PyInstaller unpacks bundled data here
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """Per-user writable folder for the save file and logs.

    From source this stays alongside the code, so development runs keep using
    the same save.json as before and nothing moves under you.
    """
    if is_frozen():
        base = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    else:
        base = resource_root()
    os.makedirs(base, exist_ok=True)
    return base


def data_path(name):
    return os.path.join(data_dir(), name)


# Set AQUARIUM_SAVE to run against a different save file. Used by demo mode for
# recording, so a staged collection never touches the real one.
SAVE_ENV = "AQUARIUM_SAVE"


def save_file():
    """Where progress is read from and written to."""
    override = os.environ.get(SAVE_ENV)
    if override:
        override = os.path.abspath(os.path.expanduser(override))
        os.makedirs(os.path.dirname(override), exist_ok=True)
        return override
    return data_path("save.json")


def is_demo():
    return bool(os.environ.get(SAVE_ENV))


def use_resource_cwd():
    """Point the working directory at the bundled resources.

    Assets are loaded by relative path from a couple of dozen call sites; one
    chdir fixes all of them at once, so only the two writable paths need
    handling individually.
    """
    os.chdir(resource_root())
