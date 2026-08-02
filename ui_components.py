# this is the ui_components.py file

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QLinearGradient, QTransform, QIcon
from PyQt6.QtCore import Qt, QTimer, QSize

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
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(0, 100, 150, 30))
            gradient.setColorAt(0.5, QColor(0, 120, 160, 20))
            gradient.setColorAt(1, QColor(0, 80, 130, 40))
            painter.fillRect(self.rect(), gradient)

        painter.end()


class StatCard(QWidget):
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.setFixedSize(112, 51)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_label = QLabel("0")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("""
            color: #56D4C9;
            font-size: 16px;
            font-weight: bold;
            font-family: 'Sometype Mono';
            background: transparent;
        """)

        self.desc_label = QLabel(label_text)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setStyleSheet("""
            color: #7DB8C8;
            font-size: 10px;
            font-family: 'DM Sans';
            background: transparent;
        """)

        layout.addWidget(self.value_label)
        layout.addWidget(self.desc_label)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(86, 212, 201, 16);
                border-radius: 12px;
            }
        """)

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


class TabButton(QWidget):
    """Bottom-bar tab: an icon with a small dot marking the active page."""

    def __init__(self, icon_path, tooltip, on_click, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 40)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button = QPushButton()
        self.button.setIcon(QIcon(icon_path))
        self.button.setIconSize(QSize(22, 22))
        self.button.setFixedSize(28, 24)
        self.button.setToolTip(tooltip)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setStyleSheet("background: transparent; border: none;")
        self.button.clicked.connect(self._clicked)
        self._on_click = on_click

        self.dot = QLabel()
        self.dot.setFixedSize(4, 4)

        layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.dot, alignment=Qt.AlignmentFlag.AlignCenter)

        self.set_active(False)

    def _clicked(self):
        from sound_manager import sounds
        sounds.play("click")
        self._on_click()

    def set_active(self, active):
        self.button.setStyleSheet(f"""
            background: transparent;
            border: none;
            opacity: {1.0 if active else 0.6};
        """)
        self.dot.setStyleSheet(f"""
            background-color: {'#56D4C9' if active else 'transparent'};
            border-radius: 2px;
        """)


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