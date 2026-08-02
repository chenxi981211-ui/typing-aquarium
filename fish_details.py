# fish_details.py

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QSizePolicy)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize
from datetime import datetime

from ui_components import first_frame_pixmap


class FishDetailsWindow(QWidget):
    def __init__(self, fish_data, time_manager, parent=None):
        super().__init__(None, Qt.WindowType.Window)

        # === SET THESE FIRST ===
        self.fish_data = fish_data
        self.time_manager = time_manager
        self.fish_id = fish_data["id"]

        print(f"🐟 FishDetailsWindow for: {fish_data['name']} (ID: {self.fish_id})")

        # Set window flags - frameless with stay on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 520)
        self.setWindowTitle("")

        # === Main container with rounded corners ===
        main_container = QFrame(self)
        main_container.setGeometry(0, 0, 360, 520)
        main_container.setStyleSheet("""
            QFrame {
                background-color: rgba(7, 18, 35, 240);
                border-radius: 20px;
            }
        """)

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
        name_label = QLabel(fish_data["name"])
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
        scientific_name = fish_data.get("scientific_name", f"{fish_data['name']} sp.")
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
        self.image_label = QLabel()
        self.image_label.setFixedSize(80, 80)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)

        print(f"📷 Loading image for: {self.fish_id}")
        img_path = f"assets/thumbnails/{self.fish_id}.png"
        if not os.path.exists(img_path):
            img_path = f"assets/{self.fish_id}_swim.png"
            if os.path.exists(img_path):
                pixmap = first_frame_pixmap(img_path).scaled(
                    80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            else:
                pixmap = QPixmap("assets/default_fish.png")
        else:
            pixmap = QPixmap(img_path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio)

        self.image_label.setPixmap(pixmap)
        main_layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ===== RARITY BADGE (matching Collection screen style) =====
        rarity = fish_data.get("rarity", 50)
        if rarity >= 50:
            rarity_text = "COMMON"
            rarity_color = "#56D4C9"
        elif rarity >= 10:
            rarity_text = "RARE"
            rarity_color = "#9B59B6"
        else:
            rarity_text = "LEGENDARY"
            rarity_color = "#F39C12"

        # Container with pill shape - matches Collection screen
        rarity_container = QFrame()
        rarity_container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.5);
                border-radius: 12px;
                padding: 2px 8px;
            }}
        """)
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

        # ===== DIVIDER =====
        main_layout.addWidget(self.create_divider())

        # ===== FUN FACT =====
        fun_fact_label = QLabel("FUN FACT")
        fun_fact_label.setStyleSheet("""
            color: #56D4C9;
            font-size: 11px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
            letter-spacing: 0.5px;
        """)
        main_layout.addWidget(fun_fact_label)

        description = fish_data.get("display", {}).get("description", "No description available.")
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.85);
            font-size: 13px;
            font-family: 'DM Sans';
            background: transparent;
            line-height: 1.5;
        """)
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # ===== DIVIDER =====
        main_layout.addWidget(self.create_divider())

        # ===== DISCOVERED DATE =====
        discovered_label = QLabel("DISCOVERED")
        discovered_label.setStyleSheet("""
            color: #56D4C9;
            font-size: 10px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
            letter-spacing: 0.5px;
        """)
        main_layout.addWidget(discovered_label)

        discovered_date = self.get_discovery_date()
        discovered_value = QLabel(discovered_date)
        discovered_value.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-family: 'DM Sans';
            background: transparent;
        """)
        main_layout.addWidget(discovered_value)

        # ===== UNLOCK CONDITION =====
        unlock_label = QLabel("UNLOCK CONDITION")
        unlock_label.setStyleSheet("""
            color: #56D4C9;
            font-size: 10px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
            letter-spacing: 0.5px;
        """)
        main_layout.addWidget(unlock_label)

        unlock_text = self.get_unlock_condition()
        unlock_value = QLabel(unlock_text)
        unlock_value.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-family: 'DM Sans';
            background: transparent;
        """)
        unlock_value.setWordWrap(True)
        main_layout.addWidget(unlock_value)

        main_layout.addStretch()

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

    def get_unlock_condition(self):
        """Get the unlock condition as a readable string"""
        unlock = self.fish_data.get("unlock", {})
        unlock_type = unlock.get("type", "unknown")
        unlock_value = unlock.get("value", 0)
        label_reason = unlock.get("label_reason", "")

        if isinstance(unlock_value, (int, float)):
            formatted_value = f"{unlock_value:,}"
        else:
            formatted_value = str(unlock_value)

        type_map = {
            "char_count": f"Type {formatted_value} characters total",
            "typing_speed": f"Reach {formatted_value} WPM",
            "focus": f"Focus for {formatted_value} minutes",
            "burst": f"Maintain burst speed for {formatted_value} minutes",
            "streak": f"Log in for {formatted_value} days in a row",
            "day_night": f"Unlocked during {formatted_value}",
            "random": "Completely random chance!"
        }

        if label_reason:
            return label_reason
        return type_map.get(unlock_type, f"Unknown: {unlock_type}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()