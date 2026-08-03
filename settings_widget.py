# settings_widget.py

import os

from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout,
                             QGridLayout, QSlider, QScrollArea, QMessageBox)
from PyQt6.QtGui import QPainter, QColor, QPixmap, QPainterPath, QPen, QRadialGradient
from PyQt6.QtCore import Qt, QRectF, QPointF

from sound_manager import sounds
import aero

TEAL = "#56D4C9"
CARD_BG = "rgba(255, 255, 255, 0.04)"

# (filename in assets/, display name) - order matches the design
BACKGROUNDS = [
    ("aquarium_background.png", "Coral island (Default)"),
    ("Pirate.png", "Pirate Bay"),
    ("Dino.png", "Jurassic Adventure"),
    ("Spongebob.png", "Bikini Bottom"),
]


# On/off must be readable at a glance, so they differ on three axes at once:
# track colour, track darkness, and knob brightness - not just knob position.
ON_TINT = QColor(80, 226, 236, 210)
OFF_TINT = QColor(3, 22, 44, 205)


class ToggleSwitch(aero.LiquidPanel):
    """A glass switch: liquid track, glossy knob."""

    def __init__(self, checked=False, on_toggle=None, parent=None):
        super().__init__(parent, radius=13, tint=ON_TINT if checked else OFF_TINT,
                         refract=1.5, thickness=3, backdrop_opacity=0.28)
        self.checked = checked
        self.on_toggle = on_toggle
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checked = not self.checked
            self.tint = ON_TINT if self.checked else OFF_TINT
            self.invalidate_glass()
            sounds.play("click")
            if self.on_toggle:
                self.on_toggle(self.checked)
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint_glass(painter)

        knob_d = self.height() - 8
        knob_x = self.width() - knob_d - 4 if self.checked else 4
        knob = QRectF(knob_x, 4, knob_d, knob_d)
        kg = QRadialGradient(knob.center() - QPointF(0, knob_d * 0.3), knob_d)
        if self.checked:
            kg.setColorAt(0.0, QColor(255, 255, 255, 255))
            kg.setColorAt(1.0, QColor(214, 240, 252, 255))
        else:
            # Dimmed when off, so the switch doesn't look lit from across the room
            kg.setColorAt(0.0, QColor(190, 205, 218, 255))
            kg.setColorAt(1.0, QColor(126, 146, 166, 255))
        painter.setBrush(kg)
        painter.setPen(QPen(QColor(4, 22, 44, 160), 1))
        painter.drawEllipse(knob)
        painter.end()


class SettingRow(aero.LiquidPanel):
    """Title + subtitle on the left, a control on the right."""

    def __init__(self, title, subtitle, control, parent=None):
        super().__init__(parent, radius=16, tint=aero.PANEL_TINT,
                         refract=1.3, thickness=5)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        text_column.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet(aero.label_css(12, aero.TEXT, 600))

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet(aero.label_css(10, aero.TEXT_DIM, 500))

        text_column.addWidget(title_label)
        text_column.addWidget(subtitle_label)

        layout.addLayout(text_column, 1)
        layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)


class BackgroundCard(aero.LiquidPanel):
    """A selectable tank background thumbnail."""

    THUMB_W = 150
    THUMB_H = 78

    def __init__(self, filename, display_name, on_select, parent=None):
        super().__init__(parent, radius=18, tint=aero.PANEL_TINT,
                         refract=1.28, thickness=6)
        self.filename = filename
        self.display_name = display_name
        self.on_select = on_select
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.thumb = QLabel()
        self.thumb.setFixedSize(self.THUMB_W, self.THUMB_H)
        self.thumb.setScaledContents(False)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet("background: transparent; border: none;")
        self.thumb.setPixmap(self._rounded_thumb(os.path.join("assets", filename)))

        self.name_label = QLabel(display_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.thumb, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)

        self.set_selected(False)

    def _rounded_thumb(self, path):
        """Centre-crop to the card aspect so the wider themes aren't letterboxed."""
        source = QPixmap(path)
        canvas = QPixmap(self.THUMB_W, self.THUMB_H)
        canvas.fill(Qt.GlobalColor.transparent)

        if source.isNull():
            return canvas

        scaled = source.scaled(self.THUMB_W, self.THUMB_H,
                               Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                               Qt.TransformationMode.SmoothTransformation)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path_clip = QPainterPath()
        path_clip.addRoundedRect(QRectF(0, 0, self.THUMB_W, self.THUMB_H), 8, 8)
        painter.setClipPath(path_clip)
        painter.drawPixmap((self.THUMB_W - scaled.width()) // 2,
                           (self.THUMB_H - scaled.height()) // 2, scaled)
        painter.end()
        return canvas

    def set_selected(self, selected):
        self.selected = selected
        self.tint = aero.ACTIVE_TINT if selected else aero.PANEL_TINT
        self.invalidate_glass()
        self.name_label.setStyleSheet(
            aero.label_css(11, aero.TEXT, 700 if selected else 500))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_select(self.filename)
            event.accept()


class SettingsPage(QWidget):
    """The Settings screen.

    Tank background and Reset are fully wired. The notification and sound
    controls persist their state but have no engine behind them yet - they are
    here so the screen matches the design and is ready to hook up.
    """

    PAGE_HEIGHT = 700

    def __init__(self, time_manager, on_background_change=None, on_back=None, parent=None):
        super().__init__(parent)
        self.time_manager = time_manager
        self.on_background_change = on_background_change
        self.on_back = on_back
        self.background_cards = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ===== Back + title =====
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 2, 12, 6)
        header_layout.setSpacing(2)

        self.back_btn = QPushButton("‹  Back")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setFixedHeight(24)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
                font-family: 'DM Sans';
                text-align: left;
            }
            QPushButton:hover { color: #FFFFFF; }
        """)
        if on_back:
            self.back_btn.clicked.connect(on_back)

        title = QLabel("Settings")
        title.setStyleSheet(aero.label_css(17, aero.AQUA, 700))

        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(title)
        outer.addWidget(header)

        # ===== Scrolling body =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent; width: 6px; margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.18);
                border-radius: 3px; min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 0, 12, 12)
        layout.setSpacing(8)

        # --- Tank background ---
        layout.addWidget(self._section_label("Tank Background"))

        grid = QGridLayout()
        grid.setSpacing(8)
        current = self.time_manager.get_setting("tank_background")
        for index, (filename, display_name) in enumerate(BACKGROUNDS):
            card = BackgroundCard(filename, display_name, self._select_background)
            card.set_selected(filename == current)
            self.background_cards.append(card)
            grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(grid)

        # --- Notifications ---
        layout.addWidget(self._section_label("Notifications"))
        layout.addWidget(self._toggle_row(
            "New Fish Unlocked", "Alert when you earn a new fish", "notify_new_fish"))
        layout.addWidget(self._toggle_row(
            "Milestones", "Character count achievements", "notify_milestones"))
        layout.addWidget(self._toggle_row(
            "Daily Reminder", "Reminder to log your typing every day", "notify_daily_reminder"))

        # --- Sound ---
        layout.addWidget(self._section_label("Sound"))
        layout.addWidget(self._volume_row())
        layout.addWidget(self._toggle_row(
            "Notification Sound", "Enable sound when receiving a notification", "sound_notification"))
        layout.addWidget(self._toggle_row(
            "Sound Effects", "UI interaction sounds", "sound_effects"))

        # --- Data management ---
        layout.addWidget(self._section_label("Data management"))
        layout.addWidget(self._reset_row())

        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    def _section_label(self, text):
        label = QLabel(text)
        label.setContentsMargins(0, 8, 0, 0)
        label.setStyleSheet(aero.label_css(13, aero.TEXT, 700))
        return label

    def _toggle_row(self, title, subtitle, setting_key):
        toggle = ToggleSwitch(
            checked=bool(self.time_manager.get_setting(setting_key)),
            on_toggle=lambda value, k=setting_key: self.time_manager.set_setting(k, value))
        return SettingRow(title, subtitle, toggle)

    def _volume_row(self):
        card = aero.LiquidPanel(radius=16, tint=aero.PANEL_TINT, refract=1.3, thickness=5)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        label = QLabel("Master Volume")
        label.setStyleSheet(aero.label_css(12, aero.TEXT, 600))
        self.volume_value = QLabel(f"{int(self.time_manager.get_setting('master_volume'))}%")
        self.volume_value.setStyleSheet(aero.label_css(12, aero.AQUA, 700))
        top.addWidget(label)
        top.addStretch()
        top.addWidget(self.volume_value)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(self.time_manager.get_setting("master_volume")))
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 5px; background: rgba(4, 30, 58, 0.55); border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(214,255,255,245), stop:0.45 rgba(120,228,244,235),
                    stop:1 rgba(52,168,214,240));
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: #FFFFFF; width: 16px; height: 16px;
                margin: -6px 0; border-radius: 8px;
            }}
        """)
        slider.valueChanged.connect(self._on_volume_changed)

        layout.addLayout(top)
        layout.addWidget(slider)
        return card

    def _on_volume_changed(self, value):
        self.volume_value.setText(f"{value}%")
        self.time_manager.set_setting("master_volume", value)

    def _reset_row(self):
        # The design draws this as a toggle, but it is a one-shot destructive
        # action, so it gets a button and a confirmation instead.
        button = QPushButton("Reset")
        button.setFixedSize(72, 28)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 107, 107, 0.12);
                color: #FF6B6B;
                border: 1px solid rgba(255, 107, 107, 0.45);
                border-radius: 14px;
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(255, 107, 107, 0.22); }
        """)
        button.clicked.connect(self._confirm_reset)
        return SettingRow("Reset Settings", "Clean all your stats and start over", button)

    def _confirm_reset(self):
        box = QMessageBox(self)
        box.setWindowTitle("Reset everything?")
        box.setText("Reset all stats and fish?")
        box.setInformativeText(
            "Your character counts, WPM records, typing history and every fish you have "
            "collected will be permanently erased. This cannot be undone.")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Reset)
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)

        if box.exec() == QMessageBox.StandardButton.Reset:
            self.time_manager.reset_stats()
            print("🧹 Stats reset from Settings")

    def _select_background(self, filename):
        sounds.play("click")
        if filename == self.time_manager.get_setting("tank_background"):
            return

        self.time_manager.set_setting("tank_background", filename)
        for card in self.background_cards:
            card.set_selected(card.filename == filename)

        if self.on_background_change:
            self.on_background_change(filename)
