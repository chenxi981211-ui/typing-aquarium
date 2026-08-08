# full_view.py
"""The tank on its own, filling the screen.

A separate window with its own fish, movement timer and background, rather than
a resized main window. The main window keeps a fixed geometry that the pages,
the glass backdrop and the minimal-mode maths all depend on, and stretching it
to the screen would unpick all of that.

Because the fish here are their own sprites, the desktop tank carries on
undisturbed underneath. It shows the same fish, the same number of them, and
scaled by the same factor as the tank - this is a magnified view of that tank,
not a second one with its own stock.
"""

import os
import random

from PyQt6.QtWidgets import QWidget, QPushButton, QLabel
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QColor, QLinearGradient
from PyQt6.QtCore import Qt, QSize, QTimer

import aero
from fish_manager import SwimmingFish
from ui_components import SpriteSheetFish

# The desktop tank, which this view is a magnified copy of. Fish are scaled by
# the same factor as the tank itself, so the density on screen is identical -
# eight fish here look exactly as crowded as eight fish in the small tank.
TANK_WIDTH, TANK_HEIGHT = 354, 275
TANK_FISH_SIZE = 64

# Used when the screen cannot be queried. A plain menu bar is about 25px, so
# this clears one comfortably and is only a floor - a notched display reports
# more and that larger value wins.
MENU_BAR_FALLBACK = 28


class FullTankWindow(QWidget):
    """Borderless full-screen tank. Esc or the close button dismisses it."""

    def __init__(self, time_manager, background, parent=None):
        super().__init__(None, Qt.WindowType.Window)
        self.time_manager = time_manager
        self.background_name = background
        self.active_fish_sprites = []

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setWindowTitle("Aquarium")

        screen = self.screen() or self.parent().screen()
        self.setGeometry(screen.geometry())

        self._art = QPixmap(os.path.join("assets", background))

        # Scale on the tighter axis so the magnified tank still fits the screen
        self.scale = min(self.width() / TANK_WIDTH, self.height() / TANK_HEIGHT)
        self.fish_size = int(TANK_FISH_SIZE * self.scale)

        # Spelled out rather than a bare icon: with no window frame there is
        # nothing else on screen to indicate how to get out of here.
        self.close_btn = QPushButton("\u2715   Exit full view", self)
        self.close_btn.setFixedSize(158, 40)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(6, 30, 58, 0.55);
                border: 1px solid rgba(174, 233, 247, 0.35);
                border-radius: 20px;
                color: {aero.TEXT};
                font-size: 13px;
                font-family: 'DM Sans';
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(12, 56, 100, 0.85);
                border-color: rgba(174, 233, 247, 0.7);
            }}
        """)
        self.close_btn.clicked.connect(self.close)

        self.hint = QLabel("or press Esc", self)
        self.hint.setStyleSheet(aero.label_css(11, aero.TEXT_DIM, 500))
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setFixedWidth(158)

        self.movement_timer = QTimer(self)
        self.movement_timer.timeout.connect(self.update_fish_positions)
        self.movement_timer.start(20)

        self._place_controls()

    # ===== presentation =====

    def _top_inset(self):
        """How far down the menu bar reaches on this screen.

        The window covers the screen's full geometry, but macOS keeps drawing
        the menu bar over the top of it, so anything placed near y=0 ends up
        underneath. The gap between the full and available geometry is exactly
        that strip - 43px on a notched display, around 25 without - which is
        why this is measured rather than assumed.
        """
        screen = self.screen()
        if screen is None:
            return MENU_BAR_FALLBACK
        inset = screen.availableGeometry().top() - screen.geometry().top()
        return max(inset, MENU_BAR_FALLBACK)

    def _place_controls(self):
        top = self._top_inset() + 16
        self.close_btn.move(self.width() - self.close_btn.width() - 24, top)
        self.hint.move(self.close_btn.x(), self.close_btn.y() + self.close_btn.height() + 6)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_controls()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if not self._art.isNull():
            scaled = self._art.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width() - scaled.width()) // 2,
                               (self.height() - scaled.height()) // 2, scaled)
        else:
            painter.fillRect(self.rect(), QColor(10, 46, 84))

        # Same water treatment as the small tank, so it still reads as one app
        water = QLinearGradient(0, 0, 0, self.height())
        water.setColorAt(0.0, QColor(255, 255, 255, 70))
        water.setColorAt(0.22, QColor(190, 240, 255, 20))
        water.setColorAt(0.75, QColor(0, 60, 110, 26))
        water.setColorAt(1.0, QColor(120, 220, 255, 44))
        painter.fillRect(self.rect(), water)
        painter.end()

    # ===== fish =====

    def stock(self, fish_ids):
        """Mirror the desktop tank exactly - the same fish, once each.

        Padding this out with copies made one fish look like a shoal, which is
        not a bigger view of the tank, it is a different tank.
        """
        for fish_id in fish_ids:
            self.spawn(fish_id)

    def spawn(self, fish_id):
        sprite_path = f"assets/{fish_id}_swim.png"
        if not os.path.exists(sprite_path):
            return

        label = SpriteSheetFish(sprite_path, self)
        # Speeds scale with the tank as well, so a fish still crosses it in
        # about the same time rather than appearing to crawl.
        pace = self.scale
        dx = random.choice([-1.0, -0.8, -0.5, 0.5, 0.8, 1.0]) * pace
        dy = random.choice([-0.5, -0.3, 0.0, 0.3, 0.5]) * pace
        if dx > 0:
            label.flip()

        size = self.fish_size
        x = random.randint(0, max(1, self.width() - size))
        y = random.randint(0, max(1, self.height() - size))
        label.setGeometry(x, y, size, size)
        label.show()

        fish = SwimmingFish(fish_id=fish_id, label=label, sprite_path=sprite_path,
                            x=x, y=y, width=size, height=size)
        fish.dx, fish.dy = dx, dy
        fish.facing_right = dx > 0
        self.active_fish_sprites.append(fish)

    def update_fish_positions(self):
        for fish in self.active_fish_sprites:
            if random.random() < 0.006:
                limit_x, limit_y = 1.2 * self.scale, 1.0 * self.scale
                fish.dx = max(-limit_x, min(limit_x, fish.dx + random.choice([-0.4, 0, 0.4]) * self.scale))
                fish.dy = max(-limit_y, min(limit_y, fish.dy + random.choice([-0.3, 0, 0.3]) * self.scale))
                if abs(fish.dx) < 0.25 * self.scale:
                    fish.dx = (0.6 if random.random() > 0.5 else -0.6) * self.scale
                self._face(fish)

            new_x = fish.x + fish.dx
            new_y = fish.y + fish.dy
            turned = False

            if new_x <= 0:
                new_x, fish.dx, turned = 0, abs(fish.dx), True
            elif new_x + fish.width >= self.width():
                new_x, fish.dx, turned = self.width() - fish.width, -abs(fish.dx), True

            if new_y <= 0:
                new_y, fish.dy = 0, abs(fish.dy)
            elif new_y + fish.height >= self.height():
                new_y, fish.dy = self.height() - fish.height, -abs(fish.dy)

            if turned:
                self._face(fish)

            fish.label.move(int(new_x), int(new_y))
            fish.x, fish.y = new_x, new_y

    @staticmethod
    def _face(fish):
        wants_right = fish.dx > 0
        if wants_right != getattr(fish, "facing_right", False):
            fish.label.flip()
            fish.facing_right = wants_right

    # ===== lifecycle =====

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.movement_timer.stop()
        for fish in self.active_fish_sprites:
            fish.label.stop()
        self.active_fish_sprites.clear()
        super().closeEvent(event)
