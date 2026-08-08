# tray.py
"""The menu bar icon, and the system notifications that go with it.

Two jobs that share one object, because on macOS they are the same thing: the
status item is what gives the app a place in the menu bar, and Qt routes
showMessage() through it into Notification Center.

It also closes a real hole. The window is frameless with its own red button, and
the app deliberately keeps running when that window closes (it has to, or the
keystroke count would stop the moment you tidied your desktop). Before this
there was no way back to a closed window and no way to quit - the app just sat
there invisibly. Now both live in the menu bar.
"""

import os

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtCore import QTimer, QTime

MENU_ICON = os.path.join("assets", "menu_fish.png")
MENU_ICON_2X = os.path.join("assets", "menu_fish@2x.png")
APP_ICON = os.path.join("assets", "logo.png")

# Don't nag: at most one reminder a day, and only once the evening has set in
# with nothing typed.
REMINDER_HOUR = 19


class MenuBarPresence:
    """Status item in the menu bar, plus the app's notifications."""

    def __init__(self, window, time_manager, parent=None):
        self.window = window
        self.time_manager = time_manager
        self._reminded_on = None

        self.tray = QSystemTrayIcon(self._icon(), parent)
        self.tray.setToolTip("Typing Aquarium")

        menu = QMenu()

        # Not clickable - just today's figure, refreshed each time the menu opens
        self.count_action = QAction("", menu)
        self.count_action.setEnabled(False)
        menu.addAction(self.count_action)
        menu.addSeparator()

        self._add(menu, "Show Aquarium", self.show_window)
        self._add(menu, "Full View", self.window.open_full_view)
        menu.addSeparator()
        self._add(menu, "Collection", lambda: self._go(self.window.show_collection))
        self._add(menu, "Statistics", lambda: self._go(self.window.show_statistics))
        self._add(menu, "Settings", lambda: self._go(self.window.show_settings))
        menu.addSeparator()
        self._add(menu, "Send Test Notification", self.test_notification)
        self._add(menu, "Quit Typing Aquarium", QApplication.quit)

        menu.aboutToShow.connect(self._refresh_count)
        self.tray.setContextMenu(menu)
        self._menu = menu

        # Clicking the icon itself brings the tank back, which is what people
        # try first when the window has gone.
        self.tray.activated.connect(self._activated)
        self.tray.show()

        # Hourly is often enough for a once-a-day nudge and costs nothing.
        self._reminder_timer = QTimer(parent)
        self._reminder_timer.timeout.connect(self.maybe_remind)
        self._reminder_timer.start(60 * 60 * 1000)

        # Also look once shortly after launch, so opening the app at 9pm having
        # typed nothing does not wait until 10 for the reminder it should have
        # given straight away. Held on self so it is not garbage collected.
        self._first_check = QTimer(parent)
        self._first_check.setSingleShot(True)
        self._first_check.timeout.connect(self.maybe_remind)
        self._first_check.start(20 * 1000)

    # ===== plumbing =====

    @staticmethod
    def _add(menu, text, slot):
        action = QAction(text, menu)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _icon(self):
        """A template image, so macOS tints it for the current menu bar."""
        icon = QIcon()
        for path in (MENU_ICON, MENU_ICON_2X):
            if os.path.exists(path):
                icon.addPixmap(QPixmap(path))
        if icon.isNull():
            icon = QIcon(APP_ICON)
        else:
            # Lets macOS invert it against a dark menu bar and when highlighted.
            icon.setIsMask(True)
        return icon

    def _activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    def _refresh_count(self):
        chars = self.time_manager.total_chars_today
        owned = len(set(self.time_manager.user_data.get("owned_fish", [])))
        self.count_action.setText(f"{chars:,} characters today  ·  {owned} fish")

    def _go(self, page_method):
        self.show_window()
        page_method()

    def show_window(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    # ===== notifications =====

    def notify(self, title, body, seconds=6):
        """Post a system notification, or do nothing if the platform can't.

        Never raises: a notification failing is not a reason to interrupt
        whatever the app was doing when it tried to speak up.
        """
        try:
            if not QSystemTrayIcon.supportsMessages():
                return False
            self.tray.showMessage(title, body, self._icon(), seconds * 1000)
            return True
        except Exception as exc:
            print(f"🔔 Notification failed: {exc}")
            return False

    def test_notification(self):
        """Post a notification on demand, and say where it will come from.

        Notifications are attributed to the process's bundle identifier. Run as
        a bundled app that is com.chenxi.typingaquarium and macOS shows them as
        Typing Aquarium. Run from source it is com.apple.python3 - Apple's own
        Python.app - so anything posted arrives filed under "Python", if it
        arrives at all. That difference is invisible until you go looking, which
        is why this button exists.
        """
        identity = "unknown"
        try:
            from AppKit import NSBundle
            identity = NSBundle.mainBundle().bundleIdentifier() or "none"
        except Exception:
            pass

        bundled = identity == "com.chenxi.typingaquarium"
        print(f"🔔 Test notification. Bundle identity: {identity}")
        if not bundled:
            print("🔔 Running from source - macOS will file this under Python, "
                  "not Typing Aquarium. Launch the built .app for proper ones.")

        sent = self.notify(
            "Typing Aquarium",
            "Notifications are working." if bundled
            else "Working, but filed under Python - use the built app.")
        if not sent:
            print("🔔 The platform reported it cannot show messages.")
        return sent

    def notify_new_fish(self, fish_name, rarity_word=None):
        """Announce a catch, if the user asked to be told."""
        if not self.time_manager.get_setting("notify_new_fish"):
            return False
        detail = f"A {rarity_word.lower()} find." if rarity_word else "Added to your collection."
        return self.notify(f"{fish_name} joined your aquarium", detail)

    def maybe_remind(self):
        """One evening nudge, only if nothing has been typed today."""
        if not self.time_manager.get_setting("notify_daily_reminder"):
            return False

        today = self.time_manager._get_logical_date_string()
        if self._reminded_on == today:
            return False
        if QTime.currentTime().hour() < REMINDER_HOUR:
            return False
        if self.time_manager.total_chars_today > 0:
            return False

        self._reminded_on = today
        return self.notify("Your aquarium is quiet",
                           "No typing logged today. A few hundred characters is enough for a new fish.")
