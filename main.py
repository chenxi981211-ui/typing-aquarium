# main.py
import os
import sys
import logging

# Must run before anything loads an asset by relative path
import paths
from paths import use_resource_cwd
use_resource_cwd()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

APP_ICON = os.path.join("assets", "logo.png")


def apply_app_icon(app):
    """Set the window icon, and on macOS the Dock icon too.

    setWindowIcon alone does not touch the Dock when the app is run as a plain
    script rather than a bundle - macOS takes that image from the bundle, so
    without this the Dock keeps showing the generic Python rocket. Wrapped in
    try/except because a missing icon is never a reason to fail to start.
    """
    if not os.path.exists(APP_ICON):
        print(f"🖼️  No app icon at {APP_ICON}")
        return

    app.setWindowIcon(QIcon(APP_ICON))

    if sys.platform == "darwin":
        try:
            from AppKit import NSApplication, NSImage
            image = NSImage.alloc().initByReferencingFile_(os.path.abspath(APP_ICON))
            NSApplication.sharedApplication().setApplicationIconImage_(image)
        except Exception as exc:
            print(f"🖼️  Dock icon unavailable ({exc}) - window icon still set")

from typing_engine import TypingManager
from time_manager import UnlockManager
from ui_aquarium import AquariumWidget
from logger import logger
from sound_manager import sounds
from tray import MenuBarPresence

# Kept in the tank when the day has not produced anything yet.
STARTER_FISH = "guppy"


class AppBridge(QObject):
    stats_updated = pyqtSignal(dict, float)
    fish_spawned = pyqtSignal(str)
    keystroke_received = pyqtSignal(dict)  # NEW: Safely bridges the background thread to the main thread


def main():
    logger.start()
    try:

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        app.setApplicationName("Typing Aquarium")
        apply_app_icon(app)

        # Initialize managers
        time_manager = UnlockManager()

        if paths.is_demo():
            print("🎬 DEMO MODE - reading and writing "
                  f"{time_manager.save_json_path}")
            print("🎬 The real save file is not in use.")

        # Sounds need QApplication to exist before they can be built
        sounds.load(time_manager)

        # The tank keeps its fish - an aquarium that empties overnight reads as
        # the fish dying, not as a fresh start. UnlockManager.tank_lineup picks
        # who is swimming: favourites, then today's catches, then a rotating
        # cast of the rest.
        initial_fish = time_manager.tank_lineup()
        if not initial_fish:
            initial_fish = [STARTER_FISH]

        aquarium = AquariumWidget(initial_fish, time_manager)
        aquarium.show()

        # Set up signal bridge
        bridge = AppBridge()
        bridge.stats_updated.connect(aquarium.update_hud)
        bridge.fish_spawned.connect(aquarium.spawn_fish_sprite)

        # Store live WPM for display
        current_live_wpm = 0


        def update_ui():
            """Update UI with current stats"""
            stats = {
                "total_chars": time_manager.total_chars_today,
                "cpm": 0,
                "wpm": current_live_wpm
            }
            total_time = time_manager.total_active_time
            bridge.stats_updated.emit(stats, total_time)

        # Menu bar icon, and the notifications that ride on it
        menu_bar = MenuBarPresence(aquarium, time_manager)

        def announce_catch(fish_id):
            """Tell the user what they just caught, if they asked to be told."""
            fish = next((f for f in time_manager.fish_definitions if f["id"] == fish_id), None)
            if fish is None:
                return
            rarity = fish.get("rarity", 50)
            word = "Common" if rarity >= 50 else ("Rare" if rarity >= 10 else "Legendary")
            menu_bar.notify_new_fish(fish["name"], word)

        def handle_keystroke(live_typing_stats):
            """Now safely runs strictly on the main UI thread"""
            nonlocal current_live_wpm
            current_live_wpm = live_typing_stats.get("wpm", 0)

            # Update time_manager
            time_manager.update_qualifiers(live_typing_stats)
            milestone_reached = time_manager.register_activity()

            # Check for fish spawn
            if milestone_reached:
                spawn_result = time_manager.check_ten_minute_milestone()
                if spawn_result not in ["coin_flip_failed", "pool_empty"]:
                    # The splash plays inside spawn_fish_sprite, where the fish
                    # actually appears.
                    bridge.fish_spawned.emit(spawn_result)
                    announce_catch(spawn_result)

            # Update UI with fresh stats
            update_ui()

        # Connect the new signal to our handler
        bridge.keystroke_received.connect(handle_keystroke)

        def background_callback(live_typing_stats):
            """This runs in the pynput background thread. Emitting a signal here is 100% thread-safe."""
            bridge.keystroke_received.emit(live_typing_stats)

        def auto_save():
            """Auto-save progress periodically"""
            time_manager.save_state()
            print("💾 Auto-saved progress")

        # Start typing engine (pass the background_callback, NOT handle_keystroke)
        typing_engine = TypingManager(on_key_callback=background_callback)
        typing_engine.start()

        def handle_reset():
            """Clear the live speed reading the moment stats are reset."""
            nonlocal current_live_wpm
            current_live_wpm = 0
            typing_engine.reset_speed()
            update_ui()

        time_manager.on_reset = handle_reset

        auto_save_timer = QTimer()
        auto_save_timer.timeout.connect(auto_save)
        auto_save_timer.start(30000)

        # Update UI every second (for smooth time display)
        ui_timer = QTimer()
        ui_timer.timeout.connect(update_ui)
        ui_timer.start(1000)

        # Run application
        try:
            sys.exit(app.exec())
        except SystemExit:
            pass
        finally:
            ui_timer.stop()
            auto_save_timer.stop()
            time_manager.save_state()
            typing_engine.stop()

    except Exception as e:
        logging.exception(f"Fatal error in main file: {e}")
        raise
    finally:
        logger.stop()


if __name__ == "__main__":
    main()