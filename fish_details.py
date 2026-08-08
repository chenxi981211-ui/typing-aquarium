# fish_details.py

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QSizePolicy)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize
from datetime import datetime

import aero
from ui_components import first_frame_pixmap
from collection_widget import silhouette
from time_manager import WINDOW_LABELS


class FishDetailsWindow(QWidget):
    def __init__(self, fish_data, time_manager, parent=None):
        super().__init__(None, Qt.WindowType.Window)

        # === SET THESE FIRST ===
        self.fish_data = fish_data
        self.time_manager = time_manager
        self.fish_id = fish_data["id"]
        owned = time_manager.user_data.get("owned_fish", []) if time_manager else []
        self.is_owned = self.fish_id in owned

        print(f"🐟 FishDetailsWindow for: {fish_data['name']} (ID: {self.fish_id})")

        # Set window flags - frameless with stay on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Width is fixed so every fish gets the same column; the height is
        # measured from the content at the end of __init__. A locked fish has
        # three short lines where a caught one has a paragraph, and one fixed
        # height left a large empty stretch under the sparser of the two.
        self.setFixedWidth(self.WIDTH)
        self.setWindowTitle("")

        # === Main container: the same glass shell as the main window ===
        # This was a flat navy QFrame, which made the detail page the only
        # surface in the app with no refraction, rim light or backdrop.
        #
        # The glass asks its top-level window for the art it refracts, and this
        # is its own window, so it has to supply that itself - derived from the
        # tank theme in use, so the detail page matches whatever is behind it.
        theme = "Spongebob.png"
        if time_manager is not None:
            theme = time_manager.get_setting("tank_background") or theme
        self._backdrop = aero.backdrop_pixmap(os.path.join("assets", theme), self.WIDTH)

        main_container = aero.LiquidShell(self)
        main_container.setFixedWidth(self.WIDTH)
        self.main_container = main_container

        # Main layout
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # ===== TOP BAR: Close button on LEFT =====
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)

        self.close_btn = QPushButton()
        self.close_btn.setIcon(QIcon("assets/off_button.png"))
        self.close_btn.setIconSize(QSize(11, 11))
        self.close_btn.setFixedSize(11, 11)
        self.close_btn.setStyleSheet("background: transparent; border: none;")
        self.close_btn.clicked.connect(self.close)

        top_bar_layout.addWidget(self.close_btn)
        top_bar_layout.addStretch()
        main_layout.addWidget(top_bar)

        # ===== FISH NAME =====
        name_label = QLabel(fish_data["name"] if self.is_owned else "???")
        name_label.setStyleSheet("""
            color: white;
            font-size: 22px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(name_label)

        # ===== SCIENTIFIC NAME =====
        scientific_name = (fish_data.get("scientific_name", f"{fish_data['name']} sp.")
                           if self.is_owned else "Not yet discovered")
        sci_label = QLabel(scientific_name)
        sci_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.5);
            font-size: 13px;
            font-style: italic;
            font-family: 'DM Sans';
            background: transparent;
        """)
        sci_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(sci_label)

        # ===== FISH SPRITE =====
        # Large, on no panel at all, and scaled with FastTransformation: these
        # are pixel sprites, and smooth scaling blurs them into mush.
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")

        print(f"📷 Loading image for: {self.fish_id}")
        # The still is the clean, undistorted artwork; the sheet frame is a
        # warped animation pose. Prefer the still and fall back only for the
        # hand-drawn fish, which never had one.
        still = f"assets/stills/{self.fish_id}.png"
        sprite = f"assets/{self.fish_id}_swim.png"

        if os.path.exists(still):
            source = QPixmap(still)
        elif os.path.exists(sprite):
            source = first_frame_pixmap(sprite)
        else:
            source = QPixmap("assets/default_fish.png")

        if not self.is_owned:
            source = silhouette(source)

        # Every fish gets the same footprint, so the page does not jump around
        # between a long swordfish and a round pufferfish.
        self.image_label.setPixmap(self._hero_pixmap(source))
        self.image_label.setFixedSize(self.HERO_W, self.HERO_H)

        # No panel behind the art. The fish sits directly on the window glass,
        # which keeps the focus on the animal rather than framing it in a box.
        main_layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ===== RARITY BADGE (matching Collection screen style) =====
        rarity = fish_data.get("rarity", 50)
        if rarity >= 50:
            rarity_text = "COMMON"
            rarity_color = aero.AQUA
        elif rarity >= 10:
            rarity_text = "RARE"
            rarity_color = aero.VIOLET
        else:
            rarity_text = "LEGENDARY"
            rarity_color = aero.AMBER

        # Container with pill shape - matches Collection screen
        # Just the coloured word - no box, matching the collection cards.
        rarity_container = QFrame()
        rarity_container.setStyleSheet("QFrame { background: transparent; border: none; }")
        rarity_container.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        rarity_layout = QHBoxLayout(rarity_container)
        rarity_layout.setContentsMargins(8, 4, 8, 4)  # Slightly more padding for details page
        rarity_layout.setSpacing(8)
        rarity_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Rarity label
        rarity_label = QLabel(rarity_text)
        rarity_label.setStyleSheet(f"""
            color: {rarity_color};
            font-size: 11px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
            letter-spacing: 0.5px;
        """)

        rarity_layout.addWidget(rarity_label)

        # Add to main layout, centered
        main_layout.addWidget(rarity_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # ===== INFO PANEL =====
        # One glass panel instead of hairline dividers, matching how Statistics
        # and Settings group their content.
        info_panel = aero.LiquidPanel(radius=16, tint=aero.PANEL_TINT,
                                      refract=1.28, thickness=5)
        info_layout = QVBoxLayout(info_panel)
        # Generous inset, and a small default gap that keeps each heading tied to
        # the line under it. The larger breaks between the three groups are added
        # explicitly below, so the panel reads as three blocks rather than seven
        # evenly spaced lines.
        info_layout.setContentsMargins(18, 16, 18, 18)
        info_layout.setSpacing(5)
        main_layout.addWidget(info_panel)

        # ===== FUN FACT =====
        fun_fact_label = QLabel("FUN FACT")
        fun_fact_label.setStyleSheet(f"""
            color: {aero.AQUA};
            font-size: 11px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
            letter-spacing: 0.5px;
        """)
        info_layout.addWidget(fun_fact_label)

        description = (fish_data.get("display", {}).get("description", "No description available.")
                       if self.is_owned
                       else "Catch this one to find out what it is.")
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.85);
            font-size: 13px;
            font-family: 'DM Sans';
            background: transparent;
            line-height: 1.5;
        """)
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)

        # ===== DISCOVERED DATE =====
        info_layout.addSpacing(14)
        discovered_label = QLabel("DISCOVERED")
        discovered_label.setStyleSheet(f"""
            color: {aero.AQUA};
            font-size: 10px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
            letter-spacing: 0.5px;
        """)
        info_layout.addWidget(discovered_label)

        discovered_date = self.get_discovery_date()
        discovered_value = QLabel(discovered_date)
        discovered_value.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-family: 'DM Sans';
            background: transparent;
        """)
        info_layout.addWidget(discovered_value)

        # ===== UNLOCK CONDITION =====
        info_layout.addSpacing(14)
        unlock_label = QLabel("UNLOCK CONDITION")
        unlock_label.setStyleSheet(f"""
            color: {aero.AQUA};
            font-size: 10px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
            letter-spacing: 0.5px;
        """)
        info_layout.addWidget(unlock_label)

        unlock_value = QLabel(self.get_unlock_condition())
        unlock_value.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-family: 'DM Sans';
            background: transparent;
        """)
        unlock_value.setWordWrap(True)
        info_layout.addWidget(unlock_value)

        # The flavour line sits under the real condition rather than replacing
        # it, which is what used to happen.
        # The flavour line is written in the past tense ("joined because...")
        # so it only makes sense once the fish is actually yours.
        flavour = self.get_unlock_flavour() if self.is_owned else ""
        if flavour:
            flavour_label = QLabel(flavour)
            flavour_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.55);
                font-size: 12px;
                font-style: italic;
                font-family: 'DM Sans';
                background: transparent;
            """)
            flavour_label.setWordWrap(True)
            info_layout.addSpacing(10)
            info_layout.addWidget(flavour_label)

        # No trailing stretch: the window is about to be sized to exactly what
        # the content needs, so there is no leftover space to push against.
        self._fit_to_content(main_layout)

        # Enable dragging
        self.drag_position = None

        print(f"🐟 FishDetailsWindow created successfully for {fish_data['name']}")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Escape:
            # Close ALL details windows, not just this one
            # Find the parent collection widget and close all
            parent = self.parent()

            # Search up the parent chain for the CollectionWidget
            while parent is not None:
                if hasattr(parent, 'details_windows'):
                    # Found the CollectionWidget
                    for window in parent.details_windows:
                        if window is not self:
                            window.close()
                    # Clear the list after closing all
                    parent.details_windows.clear()
                    print("📋 Closed all details windows from FishDetailsWindow")
                    break
                parent = parent.parent()

            # Close this window last
            self.close()
        else:
            super().keyPressEvent(event)

    def create_divider(self):
        """Create a divider line"""
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                padding: 0px;
                margin: 4px 0px;
            }
        """)
        divider.setFixedHeight(1)
        return divider

    def get_discovery_date(self):
        """Get the date this fish was discovered"""
        discovery_dates = self.time_manager.user_data.get("discovery_dates", {})
        if self.fish_id in discovery_dates:
            date = discovery_dates[self.fish_id]
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                return dt.strftime("%B %d, %Y")
            except:
                return date
        return "Not yet discovered"

    # The hero is a bare sprite on no panel, so it can be generously large.
    HERO_W, HERO_H = 232, 150

    # Fixed width, measured height. The bounds stop a one-line fish looking
    # stunted and keep the longest description on screen.
    WIDTH = 360
    MIN_HEIGHT, MAX_HEIGHT = 430, 700

    @staticmethod
    def _crop_to_content(pixmap):
        """Trim the transparent border off a sprite frame.

        Generated frames centre the fish inside 256x256 with a lot of empty
        space around it. Scaling that whole square just scales the emptiness -
        cropping first is what actually makes the fish big.
        """
        if pixmap.isNull():
            return pixmap

        image = pixmap.toImage()
        width, height = image.width(), image.height()
        left, top, right, bottom = width, height, -1, -1
        for y in range(height):
            for x in range(width):
                if image.pixelColor(x, y).alpha() > 10:
                    left = min(left, x)
                    right = max(right, x)
                    top = min(top, y)
                    bottom = max(bottom, y)
        if right < 0:
            return pixmap
        return pixmap.copy(left, top, right - left + 1, bottom - top + 1)

    def _hero_pixmap(self, source):
        """Crop to the fish, then scale it up without blurring.

        FastTransformation is deliberate: these are hard-edged pixel sprites and
        smooth scaling turns them to mush.
        """
        source = self._crop_to_content(source)
        if source.isNull() or source.width() == 0:
            return source

        return source.scaled(self.HERO_W, self.HERO_H,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.FastTransformation)

    def get_unlock_condition(self):
        """Spell out exactly what earns this fish.

        The wording tracks what UnlockManager.update_qualifiers actually tests -
        char_count and typing_speed are measured over a single day, not all
        time, which the previous text got wrong. The flavour line is returned
        separately so the real condition is never hidden behind it.
        """
        unlock = self.fish_data.get("unlock", {})
        unlock_type = unlock.get("type", "unknown")
        value = unlock.get("value", 0)
        amount = f"{value:,}" if isinstance(value, (int, float)) else str(value)
        window_label = WINDOW_LABELS.get(unlock.get("window", ""), "at any hour")

        # Half-minute thresholds exist, and "0.5 minutes" reads like a bug
        def duration(mins):
            # Every branch below is evaluated to build the dict, including for
            # day_night, whose value is a word rather than a number
            if not isinstance(mins, (int, float)):
                return str(mins)
            if mins < 1:
                return f"{int(round(mins * 60))} seconds"
            whole = int(mins)
            return f"{whole} minute" if whole == 1 else f"{whole} minutes"

        conditions = {
            "char_count": f"Type {amount} characters in one day",
            "total_chars": f"Type {amount} characters in total, across every day",
            "typing_speed": f"Reach {amount} WPM in one day",
            # 30 seconds, not a minute - this reads longest_focus_today, which
            # UnlockManager breaks on a gap longer than its 30 second grace.
            "focus": f"Type for {duration(value)} without pausing for more than 30 seconds",
            "burst": f"Hold 50 WPM or more for {duration(value)}",
            "streak": f"Type on {amount} days in a row",
            "time_window": f"Type {amount} characters {window_label}",
            "random": "Can turn up at any time, purely by chance",
        }
        return conditions.get(unlock_type, f"Unknown condition: {unlock_type}")

    def _fit_to_content(self, layout):
        """Size the window to exactly the height its content needs.

        Word-wrapped labels are the awkward part: a QLabel does not advertise
        heightForWidth unless its size policy says so, and without that the
        layout measures a paragraph as one line and the window comes out far too
        short. Turning it on for the wrapped labels first makes the layout's own
        heightForWidth trustworthy.
        """
        for label in self.findChildren(QLabel):
            if label.wordWrap():
                policy = label.sizePolicy()
                policy.setHeightForWidth(True)
                label.setSizePolicy(policy)
                label.setMinimumWidth(1)   # never widen the window to fit text

        if layout.hasHeightForWidth():
            height = layout.heightForWidth(self.WIDTH)
        else:
            height = layout.sizeHint().height()

        height = max(self.MIN_HEIGHT, min(self.MAX_HEIGHT, height))
        self.setFixedSize(self.WIDTH, height)
        self.main_container.setGeometry(0, 0, self.WIDTH, height)

    def glass_backdrop(self):
        """The blurred art this window's glass refracts, as LiquidMixin expects."""
        return self._backdrop

    def get_unlock_flavour(self):
        return self.fish_data.get("unlock", {}).get("label_reason", "")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()