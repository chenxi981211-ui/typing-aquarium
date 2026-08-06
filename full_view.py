# full_view.py
"""The tank on its own, filling the screen.

A separate window with its own fish, movement timer and background, rather than
a resized main window. The main window keeps a fixed geometry that the pages,
the glass backdrop and the minimal-mode maths all depend on, and stretching it
to the screen would unpick all of that.

Because the fish here are their own sprites, the desktop tank carries on
undisturbed underneath and the two can hold different numbers of fish - this
one has room for far more.
"""

import os
import random

from PyQt6.QtWidgets import QWidget, QPushButton, QLabel
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QColor, QLinearGradient
from PyQt6.QtCore import Qt, QSize, QTimer

import aero
from fish_manager import SwimmingFish
from ui_components import SpriteSheetFish

# The desktop tank tops out at 15; a full screen is roughly ten times the area,
# so it can carry a real shoal without looking crowded.
MAX_FISH = 40
FISH_SIZE = 96


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

        self.close_btn = QPushButton(self)
        self.close_btn.setIcon(QIcon(aero.contrast_icon("assets/off_button.png", 18, aero.ICON_TINT)))
        self.close_btn.setIconSize(QSize(20, 20))
        self.close_btn.setFixedSize(38, 38)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton { background: rgba(6, 30, 58, 0.45); border: none; border-radius: 19px; }
            QPushButton:hover { background: rgba(10, 48, 88, 0.75); }
        """)
        self.close_btn.clicked.connect(self.close)

        self.hint = QLabel("Esc to close", self)
        self.hint.setStyleSheet(aero.label_css(12, aero.TEXT_DIM, 500))
        self.hint.adjustSize()

        self.movement_timer = QTimer(self)
        self.movement_timer.timeout.connect(self.update_fish_positions)
        self.movement_timer.start(20)

        self._place_controls()

    # ===== presentation =====

    def _place_controls(self):
        self.close_btn.move(self.width() - 58, 20)
        self.hint.move(self.width() - 58 - self.hint.width() - 12, 30)

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
        """Fill the tank, repeating the day's catch so a big screen isn't bare."""
        if not fish_ids:
            return
        for index in range(min(MAX_FISH, max(len(fish_ids), 12))):
            self.spawn(fish_ids[index % len(fish_ids)])

    def spawn(self, fish_id):
        sprite_path = f"assets/{fish_id}_swim.png"
        if not os.path.exists(sprite_path) or len(self.active_fish_sprites) >= MAX_FISH:
            return

        label = SpriteSheetFish(sprite_path, self)
        dx = random.choice([-1.4, -1.0, -0.7, 0.7, 1.0, 1.4])
        dy = random.choice([-0.5, -0.3, 0.0, 0.3, 0.5])
        if dx > 0:
            label.flip()

        x = random.randint(0, max(1, self.width() - FISH_SIZE))
        y = random.randint(0, max(1, self.height() - FISH_SIZE))
        label.setGeometry(x, y, FISH_SIZE, FISH_SIZE)
        label.show()

        fish = SwimmingFish(fish_id=fish_id, label=label, sprite_path=sprite_path,
                            x=x, y=y, width=FISH_SIZE, height=FISH_SIZE)
        fish.dx, fish.dy = dx, dy
        fish.facing_right = dx > 0
        self.active_fish_sprites.append(fish)

    def update_fish_positions(self):
        for fish in self.active_fish_sprites:
            if random.random() < 0.006:
                fish.dx = max(-1.6, min(1.6, fish.dx + random.choice([-0.4, 0, 0.4])))
                fish.dy = max(-1.1, min(1.1, fish.dy + random.choice([-0.3, 0, 0.3])))
                if abs(fish.dx) < 0.25:
                    fish.dx = 0.7 if random.random() > 0.5 else -0.7
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
