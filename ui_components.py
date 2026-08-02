# this is the ui_components.py file

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QPushButton,
                             QGraphicsOpacityEffect)
from PyQt6.QtGui import (QPixmap, QPainter, QPainterPath, QColor, QLinearGradient, QTransform,
                         QIcon, QPen)
from PyQt6.QtCore import Qt, QTimer, QSize

import aero

# Only sheets of exactly this size hold a 4x4 animation grid
SHEET_SIZE = 1024


class RoundedBackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path = None
        self.pixmap = None
        self.corner_radius = 12
        self.water_overlay = True

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def set_image_path(self, image_path):
        self.image_path = image_path
        self.pixmap = QPixmap(image_path)
        self.update()

    def set_corner_radius(self, radius):
        self.corner_radius = radius
        self.update()

    def set_water_overlay(self, enabled):
        self.water_overlay = enabled
        self.update()

    def paintEvent(self, event):
        if not self.pixmap or self.pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            path = QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(),
                                self.corner_radius, self.corner_radius)
            painter.setClipPath(path)

            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(30, 60, 90))
            gradient.setColorAt(1, QColor(15, 40, 65))
            painter.fillRect(self.rect(), gradient)

            painter.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(),
                            self.corner_radius, self.corner_radius)
        painter.setClipPath(path)

        # Fill the tank and centre-crop the overflow. The themes have different
        # aspect ratios, and KeepAspectRatio would letterbox the wider ones.
        scaled_pixmap = self.pixmap.scaled(self.width(), self.height(),
                                           Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                           Qt.TransformationMode.SmoothTransformation)

        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)

        if self.water_overlay:
            # Surface caustics at the top, cool depth below, light piping at the
            # waterline - the tank reads as a pane of glass holding water.
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0.0, QColor(255, 255, 255, 92))
            gradient.setColorAt(0.22, QColor(190, 240, 255, 26))
            gradient.setColorAt(0.75, QColor(0, 60, 110, 30))
            gradient.setColorAt(1.0, QColor(120, 220, 255, 52))
            painter.fillRect(self.rect(), gradient)

        painter.setClipping(False)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(4, 26, 52, 140), 1.4))
        painter.drawPath(path)
        painter.setPen(QPen(QColor(255, 255, 255, 190), 1.2))
        inner = QPainterPath()
        inner.addRoundedRect(1.2, 1.2, self.width() - 2.4, self.height() - 2.4,
                             self.corner_radius - 1, self.corner_radius - 1)
        painter.drawPath(inner)

        painter.end()


class StatCard(QWidget, aero.LiquidMixin):
    def __init__(self, label_text, accent=aero.AQUA, parent=None):
        super().__init__(parent)
        self.radius = 18
        self.tint = aero.PANEL_TINT
        self.refract = 1.26
        self.thickness = 6
        self._init_glass()

        self.setFixedSize(112, 58)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_label = QLabel("0")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet(f"""
            color: {accent};
            font-size: 17px;
            font-weight: bold;
            font-family: 'Sometype Mono';
            background: transparent;
        """)

        self.desc_label = QLabel(label_text)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setStyleSheet(f"""
            color: {aero.TEXT_DIM};
            font-size: 9px;
            font-family: 'DM Sans';
            background: transparent;
        """)

        layout.addWidget(self.value_label)
        layout.addWidget(self.desc_label)
        self.setLayout(layout)

    def paintEvent(self, event):
        p = QPainter(self)
        self.paint_glass(p)
        p.end()

    def set_value(self, value):
        if isinstance(value, int) or isinstance(value, float):
            if self.desc_label.text() == "wpm":
                self.value_label.setText(f"{int(value)}")
            elif self.desc_label.text() == "Total typing time":
                seconds = int(value)

                if seconds >= 3600:  # 1 hour or more
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    if minutes > 0:
                        self.value_label.setText(f"{hours}h {minutes}m")
                    else:
                        self.value_label.setText(f"{hours}h")
                elif seconds >= 60:  # 1 minute or more
                    minutes = seconds // 60
                    remaining_seconds = seconds % 60
                    # Always show both minutes AND seconds when over 60 seconds
                    self.value_label.setText(f"{minutes}m {remaining_seconds}s")
                else:
                    self.value_label.setText(f"{seconds}s")
            else:
                self.value_label.setText(f"{int(value):,}")
        else:
            self.value_label.setText(str(value))


def first_frame_pixmap(sprite_path):
    """A single still of a fish, for cards and detail views.

    1024x1024 files are 4x4 sprite sheets, so take frame 0. Everything else is
    already a single image and is used whole - cropping 256x256 out of one of
    those just returns an empty corner.
    """
    pixmap = QPixmap(sprite_path)
    if pixmap.isNull():
        return pixmap
    if pixmap.width() == SHEET_SIZE and pixmap.height() == SHEET_SIZE:
        return pixmap.copy(0, 0, SHEET_SIZE // 4, SHEET_SIZE // 4)
    return pixmap


class TabButton(QWidget, aero.LiquidMixin):
    """Bottom-bar tab: icon over a caption, lit by a glass pill when active.

    The active state is a painted pill plus a bright caption. Qt stylesheets
    have no `opacity` property, so dimming the icon that way did nothing - the
    inactive icon is dimmed with a real opacity effect instead.
    """

    def __init__(self, icon_path, caption, on_click, parent=None):
        super().__init__(parent)
        self.radius = 20
        self.tint = aero.ACTIVE_TINT
        self.refract = 1.45
        self.thickness = 4
        self._init_glass()

        self.active = False
        self.setFixedSize(84, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 4)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(QPixmap(icon_path).scaled(
            22, 22, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent;")

        self.caption = QLabel(caption)
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.caption, alignment=Qt.AlignmentFlag.AlignCenter)

        self._dim = QGraphicsOpacityEffect(self.icon_label)
        self.icon_label.setGraphicsEffect(self._dim)

        self._on_click = on_click
        self.set_active(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            from sound_manager import sounds
            sounds.play("click")
            self._on_click()
            event.accept()

    def set_active(self, active):
        self.active = active
        self._dim.setOpacity(1.0 if active else 0.62)
        self.caption.setStyleSheet(
            f"color: {aero.TEXT if active else aero.TEXT_DIM};"
            f" font-size: 9px; font-family: 'DM Sans';"
            f" font-weight: {700 if active else 500}; background: transparent;")
        self.invalidate_glass()

    def paintEvent(self, event):
        if self.active:
            p = QPainter(self)
            self.paint_glass(p)
            p.end()


class SpriteSheetFish(QLabel):
    """Fish animator - animates a 1024x1024 4x4 sprite sheet (16 frames).

    Not every fish has a sprite sheet yet: the artwork in 'Static fishes' is a
    single still image per fish, not a grid. Slicing one of those into a 4x4
    grid shreds the fish into 16 fragments, so anything that isn't a sheet is
    shown as a single static frame instead.
    """

    SHEET_SIZE = SHEET_SIZE

    def __init__(self, sprite_path, parent=None):
        super().__init__(parent)

        self.ROWS = 4
        self.COLS = 4
        self.FPS = 10

        # Load the sprite sheet
        sprite_sheet = QPixmap(sprite_path)

        if sprite_sheet.isNull():
            print(f"⚠️ WARNING: Could not load sprite: {sprite_path}")

        self.is_animated = (sprite_sheet.width() == self.SHEET_SIZE
                            and sprite_sheet.height() == self.SHEET_SIZE)

        # We now store pre-calculated left and right frames
        self.left_frames = []
        self.right_frames = []

        if self.is_animated:
            self.FRAME_WIDTH = sprite_sheet.width() // self.COLS
            self.FRAME_HEIGHT = sprite_sheet.height() // self.ROWS

            # Extract each frame from the 4x4 grid
            for row in range(self.ROWS):
                for col in range(self.COLS):
                    x = col * self.FRAME_WIDTH
                    y = row * self.FRAME_HEIGHT
                    frame = sprite_sheet.copy(x, y, self.FRAME_WIDTH, self.FRAME_HEIGHT)

                    self.left_frames.append(frame)
                    # Instantly pre-calculate the flipped version
                    self.right_frames.append(frame.transformed(QTransform().scale(-1, 1)))
        else:
            # Single still image - one frame, no animation
            self.FRAME_WIDTH = sprite_sheet.width()
            self.FRAME_HEIGHT = sprite_sheet.height()
            self.left_frames.append(sprite_sheet)
            self.right_frames.append(sprite_sheet.transformed(QTransform().scale(-1, 1)))

        self.current_frames = self.left_frames
        self.current_frame = 0
        self.num_frames = len(self.left_frames)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.next_frame)
        if self.num_frames > 1:
            self.animation_timer.start(int(1000 / self.FPS))

        # Set the first frame
        self.setPixmap(self.current_frames[0])
        self.setScaledContents(True)
        self.is_flipped = False

    def next_frame(self):
        self.current_frame = (self.current_frame + 1) % self.num_frames
        self.setPixmap(self.current_frames[self.current_frame])

    def flip(self):
        """Lightning fast pointer swap - no image processing needed!"""
        self.is_flipped = not self.is_flipped

        if self.is_flipped:
            self.current_frames = self.right_frames
        else:
            self.current_frames = self.left_frames

        # Immediately update the visual to prevent a 1-frame stutter
        self.setPixmap(self.current_frames[self.current_frame])

    def set_frame_rate(self, fps):
        """Change animation speed"""
        self.FPS = fps
        self.animation_timer.start(int(1000 / fps))

    def stop(self):
        self.animation_timer.stop()

    def start(self):
        if self.num_frames > 1:
            self.animation_timer.start()