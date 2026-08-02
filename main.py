# main.py
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from typing_engine import TypingManager
from time_manager import UnlockManager
from ui_aquarium import AquariumWidget
from logger import logger
from sound_manager import sounds

# Play the milestone sound each time this many characters is crossed
MILESTONE_STEP = 1000


class AppBridge(QObject):
    stats_updated = pyqtSignal(dict, float)
    fish_spawned = pyqtSignal(str)
    keystroke_received = pyqtSignal(dict)  # NEW: Safely bridges the background thread to the main thread


def main():
    logger.start()
    try:

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        # Initialize managers
        time_manager = UnlockManager()

        # Sounds need QApplication to exist before they can be built
        sounds.load(time_manager)

        # Create and show aquarium - Prioritize Favorites!
        owned = time_manager.user_data.get("owned_fish", [])
        favorites = time_manager.user_data.get("favorite_fish", [])

        initial_fish = []

        # 1. Add favorites first (ensuring we actually own them)
        for f in favorites:
            if f in owned and f not in initial_fish:
                initial_fish.append(f)

        # 2. Pad with other owned fish up to our target tank capacity (e.g., 12)
        for f in owned:
            if f not in initial_fish and len(initial_fish) < 12:
                initial_fish.append(f)

        aquarium = AquariumWidget(initial_fish, time_manager)
        aquarium.show()

        # Set up signal bridge
        bridge = AppBridge()
        bridge.stats_updated.connect(aquarium.update_hud)
        bridge.fish_spawned.connect(aquarium.spawn_fish_sprite)

        # Store live WPM for display
        current_live_wpm = 0

        # Which 1000-character block we were in last time we checked
        last_milestone = time_manager.total_chars_today // MILESTONE_STEP

        def update_ui():
            """Update UI with current stats"""
            stats = {
                "total_chars": time_manager.total_chars_today,
                "cpm": 0,
                "wpm": current_live_wpm
            }
            total_time = time_manager.total_active_time
            bridge.stats_updated.emit(stats, total_time)

        def handle_keystroke(live_typing_stats):
            """Now safely runs strictly on the main UI thread"""
            nonlocal current_live_wpm, last_milestone
            current_live_wpm = live_typing_stats.get("wpm", 0)

            # Update time_manager
            time_manager.update_qualifiers(live_typing_stats)
            milestone_reached = time_manager.register_activity()

            # Check for fish spawn
            if milestone_reached:
                spawn_result = time_manager.check_ten_minute_milestone()
                if spawn_result not in ["coin_flip_failed", "pool_empty"]:
                    bridge.fish_spawned.emit(spawn_result)
                    sounds.play("unlock")

            # Character-count achievements
            current_milestone = time_manager.total_chars_today // MILESTONE_STEP
            if current_milestone > last_milestone:
                last_milestone = current_milestone
                print(f"🏆 Milestone: {current_milestone * MILESTONE_STEP} characters today")
                sounds.play("milestone")

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