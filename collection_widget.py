# collection_widget.py

import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QGridLayout, QLabel, QPushButton, QFrame, QSizePolicy)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor
from PyQt6.QtCore import Qt, QSize, QTimer

from ui_components import first_frame_pixmap
import aero
from sound_manager import sounds
from time_manager import TANK_CAPACITY


class CollectionWindow(QWidget):
    """Separate window for collection view with custom title bar"""

    def __init__(self, time_manager, parent=None):
        super().__init__(parent)
        self.time_manager = time_manager

        # These flags remove the macOS title bar
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 700)
        self.setWindowTitle("")

        # Main container with rounded corners
        main_container = QFrame(self)
        main_container.setGeometry(0, 0, 400, 700)
        main_container.setStyleSheet("""
            QFrame {
                background-color: rgba(7, 18, 35, 240);
                border-radius: 20px;
            }
        """)

        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Top bar
        top_bar = QWidget()
        top_bar.setFixedHeight(26)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(14, 12, 0, 0)

        self.close_btn = QPushButton()
        self.close_btn.setIcon(QIcon("assets/off_button.png"))
        self.close_btn.setIconSize(QSize(11, 11))
        self.close_btn.setFixedSize(11, 11)
        self.close_btn.setStyleSheet("background: transparent; border: none;")
        self.close_btn.clicked.connect(self.close)

        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)

        title_icon = QLabel()
        title_icon.setPixmap(QPixmap("assets/glow_fish_icon.png").scaled(16, 16,
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation))

        title_label = QLabel("Fish Collection")
        title_label.setStyleSheet("""
            color: white;
            font-size: 13px;
            font-weight: 600;
            font-family: 'DM Sans';
            background: transparent;
        """)

        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_bar_layout.addWidget(self.close_btn)
        top_bar_layout.addWidget(title_widget)
        top_bar_layout.setStretch(0, 1)
        top_bar_layout.setStretch(1, 3)
        top_bar_layout.setStretch(2, 1)

        container_layout.addWidget(top_bar)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                margin: 0px 16px;
                padding: 0px;
            }
        """)
        divider.setFixedHeight(1)
        container_layout.addWidget(divider)

        # Create the collection widget (this handles the grid)
        self.collection_widget = CollectionWidget(time_manager, main_container)
        container_layout.addWidget(self.collection_widget)

        self.drag_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for the collection window"""
        if event.key() == Qt.Key.Key_Escape:
            # Close all details windows
            if hasattr(self, 'collection_widget'):
                for window in self.collection_widget.details_windows:
                    window.close()
                self.collection_widget.details_windows.clear()
                print("📋 Closed all details windows from CollectionWindow")
        else:
            super().keyPressEvent(event)


def silhouette(pixmap):
    """Flatten a sprite to a soft dark shape, keeping its outline."""
    if pixmap.isNull():
        return pixmap

    shape = QPixmap(pixmap.size())
    shape.fill(Qt.GlobalColor.transparent)

    painter = QPainter(shape)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(shape.rect(), QColor(6, 26, 50, 205))
    painter.end()
    return shape


class FishCard(aero.LiquidPanel):
    """Individual fish card in the collection grid"""

    def __init__(self, fish_data, is_owned, is_new, time_manager, parent=None):
        super().__init__(parent, radius=16,
                         tint=aero.PANEL_TINT if is_owned else aero.SUNK_TINT,
                         refract=1.3, thickness=5)
        self.fish_data = fish_data
        self.is_owned = is_owned
        self.is_new = is_new
        self.fish_id = fish_data["id"]
        self.time_manager = time_manager
        self._scroll_timer = None  # Timer for marquee effect
        self._scroll_offset = 0  # Current scroll position
        self._is_hovering = False  # Track hover state
        # A locked fish keeps its name hidden - the silhouette is the tease, the
        # name would give it away.
        self._full_name = fish_data["name"] if is_owned else "???"
        self._max_chars = 10  # Maximum characters before truncating

        self.setFixedSize(110, 130)


        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 8)
        layout.setSpacing(4)

        # Image container
        image_container = QWidget()
        image_container.setFixedSize(72, 72)
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # No panel behind the fish - it floats on the card's own glass, which
        # reads cleaner and lets the sprite fill more of the card.
        image_container.setStyleSheet("background: transparent;")

        # Fish image
        self.image_label = QLabel()
        self.image_label.setFixedSize(72, 72)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Scaled explicitly below, so let the label centre it rather than
        # stretching it out of proportion.
        self.image_label.setScaledContents(False)

        thumbnail_path = f"assets/thumbnails/{fish_data['id']}.png"
        sprite_path = f"assets/{fish_data['id']}_swim.png"

        if os.path.exists(thumbnail_path):
            source = QPixmap(thumbnail_path)
        elif os.path.exists(sprite_path):
            source = first_frame_pixmap(sprite_path)
        else:
            source = QPixmap("assets/default_fish.png")

        source = source.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)

        if not is_owned:
            # Silhouette of the actual species rather than one generic fish, so
            # a locked card still hints at what is waiting behind it.
            source = silhouette(source)

        self.image_label.setPixmap(source)

        image_layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # NEW badge
        if is_new and is_owned:
            self.new_badge = QLabel("NEW", self)
            self.new_badge.setStyleSheet("""
                QLabel {
                    color: #FF6B6B;
                    font-size: 8px;
                    font-weight: bold;
                    font-family: 'DM Sans';
                    background-color: rgba(0, 0, 0, 0.8);
                    padding: 2px 6px;
                    border-radius: 10px;
                }
            """)
            self.new_badge.adjustSize()
            self.new_badge.move(image_container.x() + image_container.width() - self.new_badge.width() - 2,
                                image_container.y() + 2)

        # ===== FISH NAME WITH MARQUEE EFFECT (ONLY FOR UNLOCKED FISH) =====
        if is_owned:
            # Create a container for the name with clipping
            self.name_container = QWidget()
            self.name_container.setFixedHeight(16)
            self.name_container.setStyleSheet("""
                QWidget {
                    background: transparent;
                    border: none;
                }
            """)

            # Create a layout for the name container
            name_layout = QVBoxLayout(self.name_container)
            name_layout.setContentsMargins(0, 0, 0, 0)
            name_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # The name label that will scroll
            self.name_label = QLabel()
            self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name_label.setStyleSheet("""
                color: white;
                font-size: 11px;
                font-weight: bold;
                font-family: 'DM Sans';
                background: transparent;
            """)

            # Set initial truncated name
            self.update_name_display(truncated=True)

            name_layout.addWidget(self.name_label)
            layout.addWidget(self.name_container)

        # ===== LOCK INFO (FOR LOCKED FISH) =====
        if not is_owned:
            lock_container = QWidget()
            lock_layout = QHBoxLayout(lock_container)
            lock_layout.setContentsMargins(0, 0, 0, 0)
            lock_layout.setSpacing(4)
            lock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lock_icon = QLabel("🔒")
            lock_icon.setStyleSheet("""
                color: rgba(255, 255, 255, 0.5);
                font-size: 10px;
                background: transparent;
            """)
            lock_text = QLabel("LOCKED")
            lock_text.setStyleSheet("""
                color: rgba(255, 255, 255, 0.5);
                font-size: 9px;
                font-weight: bold;
                font-family: 'DM Sans';
                background: transparent;
            """)

            lock_layout.addWidget(lock_icon)
            lock_layout.addWidget(lock_text)
            layout.addWidget(lock_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Rarity badge
        rarity = fish_data.get("rarity", 50)
        if rarity >= 50:
            rarity_text = "COMMON"
            rarity_color = aero.AQUA
            rarity_rgb = "138, 240, 250"
        elif rarity >= 10:
            rarity_text = "RARE"
            rarity_color = aero.VIOLET
            rarity_rgb = "198, 176, 255"
        else:
            rarity_text = "LEGENDARY"
            rarity_color = aero.AMBER
            rarity_rgb = "255, 214, 150"

        # Just the coloured word - no box. A boxed badge fought with the glass
        # card behind it and added a hard corner to an otherwise round layout.
        rarity_container = QFrame()
        rarity_container.setFixedHeight(16)
        rarity_container.setStyleSheet("QFrame { background: transparent; border: none; }")
        rarity_container.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        rarity_layout = QHBoxLayout(rarity_container)
        rarity_layout.setContentsMargins(9, 0, 9, 0)
        rarity_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        rarity_label = QLabel(rarity_text)
        rarity_label.setStyleSheet(f"""
            color: {rarity_color};
            font-size: 9px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
        """)
        rarity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        rarity_layout.addWidget(rarity_label)
        layout.addWidget(rarity_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Favorite star button
        favorites = self.time_manager.user_data.get("favorite_fish", [])
        is_fav = self.fish_id in favorites

        self.fav_btn = QPushButton("★" if is_fav else "☆", self)
        self.fav_btn.setGeometry(self.width() - 22, 4, 18, 18)
        self.update_star_style(is_fav)

        if is_owned:
            self.fav_btn.clicked.connect(self.toggle_favorite)
        else:
            self.fav_btn.hide()

        self.setLayout(layout)

    def update_name_display(self, truncated=True):
        """Update the fish name display with truncation or full name"""
        if truncated:
            # Truncate the name if it's too long
            if len(self._full_name) > self._max_chars:
                display_name = self._full_name[:self._max_chars] + "..."
            else:
                display_name = self._full_name
            self.name_label.setText(display_name)
        else:
            # Show full name for scrolling
            self.name_label.setText(self._full_name)

        # Adjust label size to fit content
        self.name_label.adjustSize()

    def enterEvent(self, event):
        """Handle mouse entering the card - start marquee"""
        self._is_hovering = True
        self._scroll_offset = 0

        # Only start marquee if the name is actually too long AND the fish is owned
        if len(self._full_name) > self._max_chars and self.is_owned:
            # Show the full name
            self.update_name_display(truncated=False)

            # Start the scroll timer
            if self._scroll_timer is None:
                self._scroll_timer = QTimer()
                self._scroll_timer.timeout.connect(self.scroll_name)
            self._scroll_timer.start(200)  # Update every 200ms

        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leaving the card - stop marquee and reset"""
        self._is_hovering = False
        self._scroll_offset = 0

        # Stop the scroll timer
        if self._scroll_timer is not None:
            self._scroll_timer.stop()

        # Reset to truncated version (only if owned)
        if self.is_owned:
            self.update_name_display(truncated=True)

        super().leaveEvent(event)

    def scroll_name(self):
        """Scroll the fish name by updating the text with spaces"""
        if not self._is_hovering or not self.is_owned:
            return

        name = self._full_name
        # Add spaces to create scrolling effect
        self._scroll_offset += 1
        if self._scroll_offset > len(name) + 5:
            self._scroll_offset = 0

        # Create the scrolling effect with leading spaces
        if self._scroll_offset < len(name):
            scrolled_text = name[self._scroll_offset:] + "  " + name[:self._scroll_offset]
        else:
            scrolled_text = "  " + name

        self.name_label.setText(scrolled_text)
        self.name_label.adjustSize()

    def update_star_style(self, is_fav):
        color = "#F39C12" if is_fav else "rgba(255, 255, 255, 0.3)"
        self.fav_btn.setStyleSheet(f"background: transparent; border: none; font-size: 14px; color: {color};")

    def toggle_favorite(self):
        favorites = self.time_manager.user_data.get("favorite_fish", [])

        if self.fish_id in favorites:
            favorites.remove(self.fish_id)
            is_fav = False
        else:
            if len(favorites) >= TANK_CAPACITY:
                print(f"Tank holds {TANK_CAPACITY} fish - unstar one first.")
                return
            favorites.append(self.fish_id)
            is_fav = True

        self.time_manager.user_data["favorite_fish"] = favorites
        self.time_manager.save_state()
        self.fav_btn.setText("★" if is_fav else "☆")
        self.update_star_style(is_fav)
        print(f"{'Added' if is_fav else 'Removed'} {self.fish_id} to favorites.")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fav_btn.move(self.width() - 22, 4)
        if hasattr(self, 'new_badge'):
            for child in self.children():
                if isinstance(child, QWidget) and child.layout() == self.layout():
                    self.new_badge.move(child.x() + child.width() - self.new_badge.width() - 2,
                                        child.y() + 2)
                    break

    def mousePressEvent(self, event):
        """Handle mouse press on the card - emit click signal"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the click was on the star button (it will handle its own click)
            child = self.childAt(event.position().toPoint())
            if child == self.fav_btn or (child and child.parent() == self.fav_btn):
                return  # Let the star button handle it

            # Call the parent's method
            if self.parent() and hasattr(self.parent(), 'on_card_clicked'):
                self.parent().on_card_clicked(self)
        super().mousePressEvent(event)


class CollectionWidget(QWidget):
    """Collection tab - shows all fish in a grid"""

    def __init__(self, time_manager, parent=None):
        super().__init__(parent)
        self.time_manager = time_manager
        self.current_filter = "all"
        self.details_windows = []
        self.window_offset = 0
        self.WINDOW_OFFSET_STEP = 30
        self._is_refreshing = False
        self._saved_geometry = None
        self._is_moving = False

        self.setup_ui()
        self.load_fish_data()
        self.apply_filter()

    def setup_ui(self):
        """Set up the collection widget UI"""
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        filter_bar = self.create_filter_bar()
        main_layout.addWidget(filter_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)  # This is important
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 3px;
            }
        """)

        # The grid container should NOT have a fixed height set anywhere
        self.grid_container = QWidget()
        self.grid_container.setMinimumHeight(100)  # Minimum height only, not fixed

        # 3 x 110px cards + spacing has to fit the 378px window and leave room
        # for the scrollbar, so the margins are tighter than the old 400px window.
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(8, 12, 8, 12)

        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area)

    def create_filter_bar(self):
        filter_bar = QWidget()
        filter_bar.setFixedHeight(40)
        filter_bar.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(filter_bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.all_btn = self.create_filter_button("All")
        self.owned_btn = self.create_filter_button("Owned")
        self.locked_btn = self.create_filter_button("Locked")

        self.set_active_filter(self.all_btn)

        self.all_btn.clicked.connect(lambda: self.set_filter("all"))
        self.owned_btn.clicked.connect(lambda: self.set_filter("owned"))
        self.locked_btn.clicked.connect(lambda: self.set_filter("locked"))

        layout.addWidget(self.all_btn)
        layout.addWidget(self.owned_btn)
        layout.addWidget(self.locked_btn)
        layout.addStretch()

        self.discovery_label = QLabel()
        self.discovery_label.setStyleSheet("""
            color: #56D4C9;
            font-size: 12px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
        """)
        layout.addWidget(self.discovery_label)

        return filter_bar

    def create_filter_button(self, text):
        btn = QPushButton(text)
        btn.setFixedSize(70, 28)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(86, 212, 201, 0.3);
                border-radius: 14px;
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: 500;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: rgba(86, 212, 201, 0.1);
                color: white;
                border-color: rgba(86, 212, 201, 0.5);
            }
        """)
        return btn

    def set_active_filter(self, active_btn):
        for btn in [self.all_btn, self.owned_btn, self.locked_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: rgba(255, 255, 255, 0.6);
                    border: 1px solid rgba(86, 212, 201, 0.3);
                    border-radius: 14px;
                    font-size: 11px;
                    font-family: 'DM Sans';
                    font-weight: 500;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background: rgba(86, 212, 201, 0.1);
                    color: white;
                    border-color: rgba(86, 212, 201, 0.5);
                }
            """)

        active_btn.setStyleSheet("""
            QPushButton {
                background: rgba(86, 212, 201, 0.2);
                color: #56D4C9;
                border: 1px solid #56D4C9;
                border-radius: 14px;
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: bold;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: rgba(86, 212, 201, 0.3);
                color: #56D4C9;
            }
        """)

    def set_filter(self, filter_type):
        sounds.play("click")
        self.current_filter = filter_type

        if filter_type == "all":
            self.set_active_filter(self.all_btn)
        elif filter_type == "owned":
            self.set_active_filter(self.owned_btn)
        else:
            self.set_active_filter(self.locked_btn)

        self.apply_filter()

    def load_fish_data(self):
        try:
            with open("fish.json", "r") as f:
                self.all_fish = json.load(f)
            print(f"Loaded {len(self.all_fish)} fish")
        except Exception as e:
            print(f"Error loading fish.json: {e}")
            self.all_fish = []

    def apply_filter(self):
        if not self.all_fish:
            return

        owned_ids = self.time_manager.user_data.get("owned_fish", [])
        viewed_ids = self.time_manager.user_data.get("viewed_fish", [])

        filtered_fish = []
        for fish in self.all_fish:
            is_owned = fish["id"] in owned_ids
            is_new = is_owned and fish["id"] not in viewed_ids

            if self.current_filter == "all":
                filtered_fish.append((fish, is_owned, is_new))
            elif self.current_filter == "owned" and is_owned:
                filtered_fish.append((fish, is_owned, is_new))
            elif self.current_filter == "locked" and not is_owned:
                filtered_fish.append((fish, is_owned, is_new))

        # Collected fish first, then by rarity. Sorting on rarity alone
        # scattered the ones you own among the locked cards, so the collection
        # never looked like it was filling up.
        filtered_fish.sort(key=lambda x: (not x[1], -x[0].get("rarity", 50)))

        # owned_fish is a running list that repeats a species each time it is
        # caught again, so it has to be de-duplicated before counting.
        owned_count = len(set(owned_ids))
        total_count = len(self.all_fish)
        self.discovery_label.setText(f"{owned_count}/{total_count} discovered")

        # Rebuilding 30 cards costs ~100ms, which lands as a stutter right when
        # the page-resize animation starts. Only rebuild when something the grid
        # actually shows has changed.
        signature = (self.current_filter, tuple(sorted(owned_ids)), tuple(sorted(viewed_ids)),
                     tuple(sorted(self.time_manager.user_data.get("favorite_fish", []))))
        if signature == getattr(self, "_grid_signature", None):
            return
        self._grid_signature = signature

        self.populate_grid(filtered_fish)

    def populate_grid(self, fish_list):
        """Populate the grid with fish cards"""
        # Clear existing widgets. takeAt() detaches immediately - deleteLater()
        # alone leaves the item in the layout until the event loop runs, so a
        # second refresh before then would stack a duplicate set of cards.
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        columns = 3

        for index, (fish, is_owned, is_new) in enumerate(fish_list):
            row = index // columns
            col = index % columns

            card = FishCard(fish, is_owned, is_new, self.time_manager)
            card.fish_id = fish["id"]
            card.is_new_flag = is_new

            card.mousePressEvent = lambda e, c=card: self.on_card_clicked(c)

            self.grid_layout.addWidget(card, row, col)

        # Calculate the total height needed
        if fish_list:
            num_rows = (len(fish_list) + columns - 1) // columns
            card_height = 130
            card_spacing = 12
            padding = 12
            total_height = num_rows * card_height + (num_rows - 1) * card_spacing + padding * 2

            # Use setMinimumHeight instead of setFixedHeight
            # This allows the container to grow but not shrink below this size
            self.grid_container.setMinimumHeight(total_height)
            # Also set a reasonable maximum height to prevent infinite growth
            self.grid_container.setMaximumHeight(total_height + 50)

    def on_card_clicked(self, card):
        """Handle fish card click - show details window"""
        from fish_details import FishDetailsWindow
        from PyQt6.QtCore import QTimer

        if self._is_refreshing or self._is_moving:
            return

        fish_id = card.fish_id
        is_new = card.is_new_flag

        print(f"🖱️ Card clicked: {fish_id}")

        self.cleanup_details_windows()

        for window in self.details_windows:
            if hasattr(window, 'fish_id') and window.fish_id == fish_id:
                if window.isVisible():
                    window.raise_()
                    window.activateWindow()
                    print(f"📋 Details window already open for {fish_id}, bringing to front")
                    return

        collection_window = self.window()

        # Save position
        saved_x = collection_window.x()
        saved_y = collection_window.y()

        scroll_pos = self.scroll_area.verticalScrollBar().value()

        if is_new:
            viewed_ids = self.time_manager.user_data.get("viewed_fish", [])
            if fish_id not in viewed_ids:
                viewed_ids.append(fish_id)
                self.time_manager.user_data["viewed_fish"] = viewed_ids
                self.time_manager.save_state()

                self._is_refreshing = True
                self.apply_filter()
                self._is_refreshing = False

                # Restore scroll position
                self.scroll_area.verticalScrollBar().setValue(scroll_pos)

                # Restore window position
                collection_window.move(saved_x, saved_y)

        # Find the fish data
        fish_data = None
        for fish in self.all_fish:
            if fish["id"] == fish_id:
                fish_data = fish
                break

        if fish_data:
            details_window = FishDetailsWindow(fish_data, self.time_manager, parent=None)
            details_window.fish_id = fish_id
            self.details_windows.append(details_window)

            collection_pos = collection_window.pos()
            new_x = collection_pos.x() + 50 + (self.window_offset * self.WINDOW_OFFSET_STEP)
            new_y = collection_pos.y() + 50 + (self.window_offset * self.WINDOW_OFFSET_STEP)

            screen = self.screen().geometry()
            max_x = screen.width() - 360
            max_y = screen.height() - 520
            new_x = min(new_x, max_x)
            new_y = min(new_y, max_y)

            details_window.move(new_x, new_y)

            self.window_offset += 1
            if self.window_offset > 5:
                self.window_offset = 0

            details_window.show()
            details_window.raise_()
            details_window.activateWindow()

            print(f"📋 Details window shown for: {fish_data['name']}")
        else:
            print(f"❌ Fish data not found for ID: {fish_id}")

    def cleanup_details_windows(self):
        """Remove closed windows from the list"""
        self.details_windows = [w for w in self.details_windows if w.isVisible()]  # ← Add parentheses

    def mouseReleaseEvent(self, event):
        """Save the window position after dragging"""
        super().mouseReleaseEvent(event)
        self._is_moving = False
        collection_window = self.window()
        self._saved_geometry = collection_window.geometry()
        print(f"📌 Window position saved: ({collection_window.x()}, {collection_window.y()})")

    def moveEvent(self, event):
        """Track when the user is dragging the window"""
        self._is_moving = True
        super().moveEvent(event)
        # Update saved geometry when drag ends (will be set in mouseReleaseEvent)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Escape:
            # Close all details windows when Escape is pressed
            for window in self.details_windows:
                window.close()
            self.details_windows.clear()
        super().keyPressEvent(event)

    def moveEvent(self, event):
        """Save the window position whenever it's moved"""
        super().moveEvent(event)
        # Update the saved geometry when the window is dragged
        collection_window = self.window()
        self._saved_geometry = collection_window.geometry()

    def closeEvent(self, event):
        """Close all details windows when collection is closed"""
        for window in self.details_windows:
            window.close()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_filter()