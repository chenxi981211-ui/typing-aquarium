# typing_aquarium.spec
"""PyInstaller recipe for the shareable macOS app.

Build with:  pyinstaller --noconfirm typing_aquarium.spec

Only the modules the app actually imports at runtime are collected; the helper
scripts that generate spritesheets and music are build-time tools and are left
out deliberately, along with their heavyweight dependencies.
"""

datas = [
    ("assets", "assets"),
    ("fish.JSON", "."),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # pynput picks its macOS backend at runtime, so the hooks miss it
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
    ],
    hookspath=[],
    runtime_hooks=[],
    # Qt ships several large stacks this app never touches; dropping them keeps
    # the download to something a person will actually wait for.
    excludes=[
        "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebEngineQuick",
        "PyQt6.QtQuick", "PyQt6.QtQml", "PyQt6.Qt3DCore", "PyQt6.QtBluetooth",
        "PyQt6.QtDesigner", "PyQt6.QtNetworkAuth", "PyQt6.QtPositioning",
        "PyQt6.QtSensors", "PyQt6.QtSerialPort", "PyQt6.QtTest",
        "tkinter", "matplotlib", "numpy", "scipy", "pandas",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Typing Aquarium",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Typing Aquarium",
)

app = BUNDLE(
    coll,
    name="Typing Aquarium.app",
    icon="assets/logo.icns",
    bundle_identifier="com.chenxi.typingaquarium",
    info_plist={
        "CFBundleName": "Typing Aquarium",
        "CFBundleDisplayName": "Typing Aquarium",
        "CFBundleShortVersionString": "1.1.0",
        "CFBundleVersion": "1.1.0",
        "NSHighResolutionCapable": True,
        # Counting keystrokes system-wide needs Accessibility. macOS shows this
        # string when it asks, so it should say plainly what is being counted.
        "NSAppleEventsUsageDescription":
            "Typing Aquarium counts how many keys you press. It never records which keys.",
        # Keep it out of the app switcher but visible in the Dock, matching how
        # the frameless always-on-top window is meant to be used.
        "LSUIElement": False,
        "LSMinimumSystemVersion": "11.0",
    },
)
