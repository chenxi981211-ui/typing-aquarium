# ui_aquarium.py

import random
import os
import json

from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QFrame, QStackedWidget, QHBoxLayout, QVBoxLayout, QScrollArea, QGridLayout, QSizePolicy
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint

from ui_components import RoundedBackgroundWidget, StatCard, SpriteSheetFish, TabButton
from fish_manager import SwimmingFish
from sound_manager import sounds


class AquariumWidget(QWidget):

    def create_divider(self):
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        divider.setFixedHeight(1)
        return divider

    def __init__(self, initial_fish_list=None, time_manager=None):
        super().__init__()

        self.time_manager = time_manager

        self.active_fish_sprites = []
        self.current_fish_count = len(initial_fish_list) if initial_fish_list else 0
        self.drag_position = None

        # Load fish configurations from JSON
        self.load_fish_configs()

        # Window dimensions
        self.window_width = 378
        self.window_height = 460
        self.setFixedSize(self.window_width, self.window_height)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main border frame
        self.border_widget = QFrame(self)
        self.border_widget.setGeometry(0, 0, self.window_width, self.window_height)
        self.border_widget.setStyleSheet("""
            QFrame {
                background-color: rgba(7, 18, 35, 240);
                border-radius: 20px;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self.border_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ===== TOP BAR =====
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(26)
        top_bar_layout = QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(0, 12, 0, 0)

        # Left side - Window controls
        left_controls = QWidget()
        left_layout = QHBoxLayout(left_controls)
        left_layout.setSpacing(6)
        left_layout.setContentsMargins(14, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.off_btn = QPushButton()
        self.off_btn.setIcon(QIcon("assets/off_button.png"))
        self.off_btn.setIconSize(QSize(11, 11))
        self.off_btn.setFixedSize(11, 11)
        self.off_btn.setStyleSheet("background: transparent; border: none;")
        self.off_btn.clicked.connect(self.close_app)

        self.minimize_btn = QPushButton()
        self.minimize_btn.setIcon(QIcon("assets/minimize_button.png"))
        self.minimize_btn.setIconSize(QSize(11, 11))
        self.minimize_btn.setFixedSize(11, 11)
        self.minimize_btn.setStyleSheet("background: transparent; border: none;")
        self.minimize_btn.clicked.connect(self.minimize_app)

        left_layout.addWidget(self.off_btn)
        left_layout.addWidget(self.minimize_btn)

        # Center - Title with fish icon
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setSpacing(6)
        title_layout.setContentsMargins(0, 0, 0, 0)

        self.title_icon = QPushButton()
        self.title_icon.setIcon(QIcon("assets/glow_fish_icon.png"))
        self.title_icon.setIconSize(QSize(16, 16))
        self.title_icon.setFixedSize(16, 16)
        self.title_icon.setStyleSheet("background: transparent; border: none;")
        self.title_icon.setFlat(True)

        self.title_label = QLabel("Typing Aquarium")
        self.title_label.setStyleSheet("""
            color: white;
            font-size: 11px;
            font-weight: semibold;
            font-family: 'DM Sans';
            background: transparent;
        """)

        title_layout.addWidget(self.title_icon)
        title_layout.addWidget(self.title_label)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Right side - Settings controls
        right_controls = QWidget()
        right_layout = QHBoxLayout(right_controls)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(0, 0, 14, 0)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(QIcon("assets/settings_icon.png"))
        self.settings_btn.setIconSize(QSize(16, 16))
        self.settings_btn.setFixedSize(16, 16)
        self.settings_btn.setStyleSheet("background: transparent; border: none;")

        self.view_btn = QPushButton()
        self.view_btn.setIcon(QIcon("assets/minimal_mode_icon.png"))
        self.view_btn.setIconSize(QSize(16, 16))
        self.view_btn.setFixedSize(16, 16)
        self.view_btn.setStyleSheet("background: transparent; border: none;")

        self.pin_btn = QPushButton()
        self.pin_btn.setIcon(QIcon("assets/pin_deactivate_button.png"))
        self.pin_btn.setIconSize(QSize(16, 16))
        self.pin_btn.setFixedSize(16, 16)
        self.pin_btn.setStyleSheet("background: transparent; border: none;")

        right_layout.addWidget(self.settings_btn)
        right_layout.addWidget(self.view_btn)
        right_layout.addWidget(self.pin_btn)

        self.large_mode = True
        self.view_btn.clicked.connect(self.toggle_view_mode)

        top_bar_layout.addWidget(left_controls)
        top_bar_layout.addWidget(title_widget)
        top_bar_layout.addWidget(right_controls)
        top_bar_layout.setStretch(0, 1)
        top_bar_layout.setStretch(1, 2)
        top_bar_layout.setStretch(2, 1)

        main_layout.addWidget(self.top_bar)

        # ===== DIVIDER 1 =====
        divider1 = self.create_divider()
        main_layout.addWidget(divider1)
        self.divider1 = divider1

        # ===== CONTENT STACK =====
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: transparent;")

        # Create aquarium content
        self.aquarium_content = QWidget()
        aquarium_layout = QVBoxLayout(self.aquarium_content)
        aquarium_layout.setContentsMargins(0, 0, 0, 0)
        aquarium_layout.setSpacing(0)

        # Aquarium container
        aquarium_width = 354
        aquarium_height = 275

        self.aquarium_container = QWidget()
        self.aquarium_container.setFixedSize(aquarium_width, aquarium_height)
        self.aquarium_container.setStyleSheet("background: transparent;")
        self.aquarium_container.setObjectName("aquarium_container")

        self.background_widget = RoundedBackgroundWidget(self.aquarium_container)
        self.background_widget.setGeometry(0, 0, aquarium_width, aquarium_height)
        saved_background = (self.time_manager.get_setting("tank_background")
                            if self.time_manager else "aquarium_background.png")
        self.background_widget.set_image_path(os.path.join("assets", saved_background))
        self.background_widget.set_water_overlay(True)
        self.background_widget.lower()

        # Fish count overlay
        self.fish_count_widget = QWidget(self.aquarium_container)
        self.fish_count_widget.setGeometry(aquarium_width - 88, 8, 80, 30)
        self.fish_count_widget.setStyleSheet("""
            background: rgba(0, 0, 0, 0.5);
            border-radius: 15px;
        """)

        fish_count_layout = QHBoxLayout(self.fish_count_widget)
        fish_count_layout.setContentsMargins(12, 0, 8, 0)
        fish_count_layout.setSpacing(8)

        self.fish_count_icon = QPushButton()
        self.fish_count_icon.setIcon(QIcon("assets/fish_count_icon.png"))
        self.fish_count_icon.setIconSize(QSize(18, 18))
        self.fish_count_icon.setFixedSize(18, 18)
        self.fish_count_icon.setStyleSheet("background: transparent; border: none;")
        self.fish_count_icon.setFlat(True)
        self.fish_count_icon.setEnabled(True)

        self.fish_count_label = QLabel(f"{self.current_fish_count} fish")
        self.fish_count_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 10px;
            font-weight: bold;
            font-family: 'DM Sans';
            background: transparent;
        """)

        fish_count_layout.addWidget(self.fish_count_icon)
        fish_count_layout.addWidget(self.fish_count_label)
        self.fish_count_widget.raise_()

        aquarium_layout.addWidget(self.aquarium_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Stats cards
        self.stats_container = QWidget()
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setSpacing(8)
        stats_layout.setContentsMargins(0, 12, 0, 0)

        self.chars_card = StatCard("Chars today")
        self.wpm_card = StatCard("wpm")
        self.focus_card = StatCard("Total typing time")

        stats_layout.addWidget(self.chars_card, 1)
        stats_layout.addWidget(self.wpm_card, 1)
        stats_layout.addWidget(self.focus_card, 1)

        aquarium_layout.addWidget(self.stats_container, alignment=Qt.AlignmentFlag.AlignCenter)

        self.content_stack.addWidget(self.aquarium_content)
        # Expanding vertically so the scrolling pages fill the taller windows;
        # the aquarium page centres its fixed-size contents inside it.
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Collection page
        from collection_widget import CollectionWidget
        self.collection_page = CollectionWidget(self.time_manager)
        self.content_stack.addWidget(self.collection_page)

        # Statistics page
        from statistics_widget import StatisticsPage
        self.statistics_page = StatisticsPage(self.time_manager)
        self.content_stack.addWidget(self.statistics_page)

        # Settings page
        from settings_widget import SettingsPage
        self.settings_page = SettingsPage(
            self.time_manager,
            on_background_change=self.apply_tank_background,
            on_back=self.show_aquarium)
        self.content_stack.addWidget(self.settings_page)

        main_layout.addWidget(self.content_stack)

        # ===== DIVIDER 2 =====
        divider2 = self.create_divider()
        main_layout.addWidget(divider2)
        self.divider2 = divider2

        # ===== TAB BAR AT BOTTOM =====
        self.bottom_buttons = QWidget()
        self.bottom_buttons.setFixedHeight(44)
        bottom_layout = QHBoxLayout(self.bottom_buttons)
        bottom_layout.setSpacing(56)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.chest_btn = TabButton("assets/treasure_chest_icon.png", "Collection", self.show_collection)
        self.tank_btn = TabButton("assets/fish_count_icon.png", "Aquarium", self.show_aquarium)
        self.stats_btn = TabButton("assets/statistics_icon.png", "Statistics", self.show_statistics)

        bottom_layout.addWidget(self.chest_btn)
        bottom_layout.addWidget(self.tank_btn)
        bottom_layout.addWidget(self.stats_btn)

        main_layout.addWidget(self.bottom_buttons)

        # Pin state - ONLY CONTROLS AQUARIUM
        self.pin_state = True
        self.pin_btn.clicked.connect(self.toggle_pin_status)

        # Store aquarium dimensions
        self.aquarium_width = aquarium_width
        self.aquarium_height = aquarium_height

        # Gear in the top bar opens Settings
        self.settings_btn.clicked.connect(self.show_settings)

        # Aquarium is the landing page
        self.tank_btn.set_active(True)

        # Start movement timer
        self.movement_timer = QTimer()
        self.movement_timer.timeout.connect(self.update_fish_positions)
        self.movement_timer.start(20)

        # Spawn initial fish
        if initial_fish_list:
            for fish_id in initial_fish_list:
                self.spawn_fish_sprite(fish_id)

    def toggle_view_mode(self):
        """Toggle between large mode and minimal mode with smooth animation"""

        # Minimal mode only makes sense on the tank; from any other page it would
        # capture that page's height as the "normal" one.
        if self.content_stack.currentWidget() is not self.aquarium_content:
            self.show_aquarium()
            return

        if not hasattr(self, 'original_window_height'):
            self.original_window_height = self.height()

        current_rect = self.geometry()

        if self.large_mode:
            target_height = self.top_bar.height() + self.aquarium_container.height() + 25
            target_rect = QRect(current_rect.x(), current_rect.y(),
                                self.window_width, target_height)

            self.fade_out_widgets()
            self.border_widget.setGeometry(0, 0, self.window_width, target_height)
            self.animate_resize(target_rect)

            self.view_btn.setIcon(QIcon("assets/large_mode_icon.png"))
            self.large_mode = False

        else:
            target_rect = QRect(current_rect.x(), current_rect.y(),
                                self.window_width, self.original_window_height)

            self.border_widget.setGeometry(0, 0, self.window_width, self.original_window_height)
            self.animate_resize(target_rect)
            QTimer.singleShot(300, self.fade_in_widgets)

            self.view_btn.setIcon(QIcon("assets/minimal_mode_icon.png"))
            self.large_mode = True

    def animate_resize(self, target_rect):
        """Smoothly animate window resize"""
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim.setEndValue(target_rect)
        self.anim.finished.connect(self.restore_fixed_size)
        self.anim.start()

    def restore_fixed_size(self):
        """Restore fixed size after animation completes"""
        self.setFixedSize(self.width(), self.height())

    def fade_in_widgets(self):
        """Fade in stats and buttons (dots removed)"""
        self.stats_container.show()
        self.bottom_buttons.show()

        if hasattr(self, 'divider1'):
            self.divider1.show()
            self.divider2.show()

    def fade_out_widgets(self):
        """Fade out stats and buttons (dots removed)"""
        self.stats_container.hide()
        self.bottom_buttons.hide()

        if hasattr(self, 'divider1'):
            self.divider1.hide()
            self.divider2.hide()

    def toggle_pin_status(self):
        """Toggle the window's 'always on top' state - ONLY CONTROLS AQUARIUM"""
        if self.pin_state:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            self.pin_btn.setIcon(QIcon("assets/pin_activate_button.png"))
            self.pin_btn.setStyleSheet("background: transparent; border: none;")
            self.pin_state = False
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self.pin_btn.setIcon(QIcon("assets/pin_deactivate_button.png"))
            self.pin_btn.setStyleSheet("background: transparent; border: none;")
            self.pin_state = True
        self.show()

    def close_all_details_windows(self):
        """Close all open fish details windows"""
        for window in self.collection_page.details_windows:
            window.close()
        self.collection_page.details_windows.clear()
        print("📋 Closed all details windows")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Escape:
            # Close all details windows
            self.close_all_details_windows()
        else:
            # Pass other keys to parent
            super().keyPressEvent(event)

    # Sized so the grid shows 2.5 rows of 130px cards - the half row is the cue
    # that the list scrolls. 12px grid margin + 2 rows + 2 gaps + half a card,
    # plus the 40px filter bar and the window chrome.
    COLLECTION_PAGE_HEIGHT = 521

    def show_collection(self):
        """Switch to the Collection page.

        CollectionWidget.showEvent refreshes the grid on its own, so there is no
        need to call apply_filter() here as well.
        """
        self.go_to_page(self.collection_page, self.COLLECTION_PAGE_HEIGHT,
                        active_tab=self.chest_btn)

    # ===== Page navigation =====

    def show_aquarium(self):
        """Switch back to the tank."""
        self.go_to_page(self.aquarium_content, self.window_height, active_tab=self.tank_btn)

    def show_statistics(self):
        """Switch to the Statistics page, refreshing it from current data."""
        self.statistics_page.refresh()
        self.go_to_page(self.statistics_page, self.statistics_page.PAGE_HEIGHT,
                        active_tab=self.stats_btn)

    def show_settings(self):
        """Switch to the Settings page (reached from the gear in the top bar)."""
        sounds.play("click")
        self.go_to_page(self.settings_page, self.settings_page.PAGE_HEIGHT, active_tab=None)

    def go_to_page(self, page, target_height, active_tab=None):
        """Show a page and grow/shrink the window to fit it."""
        self.content_stack.setCurrentWidget(page)

        for tab in (self.chest_btn, self.tank_btn, self.stats_btn):
            tab.set_active(tab is active_tab)

        # Never grow past the screen the window is on
        screen = self.screen()
        if screen is not None:
            target_height = min(target_height, screen.availableGeometry().height() - 60)

        if self.height() != target_height:
            self.animate_resize(QRect(self.x(), self.y(), self.window_width, target_height))
            self.border_widget.setGeometry(0, 0, self.window_width, target_height)

    def apply_tank_background(self, filename):
        """Swap the tank artwork (called from Settings)."""
        self.background_widget.set_image_path(os.path.join("assets", filename))
        print(f"🎨 Tank background set to {filename}")

    def load_fish_configs(self):
        """Load fish sprite sheet configurations from fish.json"""
        try:
            with open("fish.json", "r") as f:
                fish_data = json.load(f)

            self.fish_configs = {}
            for fish in fish_data:
                fish_id = fish["id"]
                self.fish_configs[fish_id] = {
                    "frame_width": fish.get("frame_width", 128),
                    "frame_height": fish.get("frame_height", 128),
                    "rows": fish.get("sprite_rows", 2),
                    "cols": fish.get("sprite_cols", 4),
                    "fps": fish.get("animation_fps", 10),
                    "default_facing": fish.get("default_facing", "left")
                }
            print(f"Loaded configurations for {len(self.fish_configs)} fish")
        except Exception as e:
            print(f"Error loading fish configs: {e}")
            self.fish_configs = {}

    def get_fish_config(self, fish_id):
        """Get sprite sheet configuration for a fish"""
        if fish_id in self.fish_configs:
            return self.fish_configs[fish_id]
        else:
            return {
                "frame_width": 128,
                "frame_height": 128,
                "rows": 2,
                "cols": 4,
                "fps": 10,
                "default_facing": "left"
            }

    def update_fish_positions(self):
        """Update positions of all swimming fish"""
        if not hasattr(self, 'aquarium_container') or self.aquarium_container is None:
            return

        container = self.aquarium_container
        container_width = container.width()
        container_height = container.height()

        for fish in self.active_fish_sprites:
            if random.random() < 0.008:
                fish.dx = fish.dx + random.choice([-0.5, -0.3, 0, 0.3, 0.5])
                fish.dy = fish.dy + random.choice([-0.5, -0.3, 0, 0.3, 0.5])
                fish.dx = max(-1.2, min(1.2, fish.dx))
                fish.dy = max(-1, min(1, fish.dy))
                if abs(fish.dx) < 0.2:
                    fish.dx = 0.5 if random.random() > 0.5 else -0.5
                self.flip_fish_direction(fish)

            new_x = fish.x + fish.dx
            new_y = fish.y + fish.dy

            bounced = False
            direction_changed = False
            WALL_PADDING = -7

            if new_x <= WALL_PADDING:
                new_x = WALL_PADDING
                fish.dx = abs(fish.dx)
                bounced = True
                direction_changed = True
            elif new_x + fish.width >= container_width - WALL_PADDING:
                new_x = container_width - fish.width - WALL_PADDING
                fish.dx = -abs(fish.dx)
                bounced = True
                direction_changed = True

            if new_y <= WALL_PADDING:
                new_y = WALL_PADDING
                fish.dy = abs(fish.dy)
                bounced = True
            elif new_y + fish.height >= container_height - WALL_PADDING:
                new_y = container_height - fish.height - WALL_PADDING
                fish.dy = -abs(fish.dy)
                bounced = True

            if direction_changed:
                self.flip_fish_direction(fish)

            fish.label.move(int(new_x), int(new_y))
            fish.x = new_x
            fish.y = new_y

            if bounced and random.random() < 0.08:
                fish.dx = fish.dx + random.choice([-0.3, 0, 0.3])
                fish.dy = fish.dy + random.choice([-0.3, 0, 0.3])
                fish.dx = max(-1.2, min(1.2, fish.dx))
                fish.dy = max(-1, min(1, fish.dy))
                if abs(fish.dx) < 0.2:
                    fish.dx = 0.5 if random.random() > 0.5 else -0.5

    def flip_fish_direction(self, fish):
        """Flip the fish sprite sheet only if direction changed"""
        if not hasattr(fish, 'label') or not hasattr(fish.label, 'flip'):
            return

        should_face_right = fish.dx > 0

        if not hasattr(fish, 'facing_right'):
            fish.facing_right = not fish.label.is_flipped

        if should_face_right != fish.facing_right:
            fish.label.flip()
            fish.facing_right = should_face_right

    def spawn_fish_sprite(self, fish_id):
        print(f"[UI] Spawning Fish : {fish_id}")

        MAX_FISH = 15
        if len(self.active_fish_sprites) >= MAX_FISH:
            self.remove_oldest_fish()
            if len(self.active_fish_sprites) >= MAX_FISH:
                print(f"Maximum limit ({MAX_FISH}) reached. Cannot spawn more.")
                return

        container = self.aquarium_container

        padding = 10
        fish_width = 64
        fish_height = 64

        min_x = padding
        max_x = container.width() - fish_width - padding
        min_y = padding
        max_y = container.height() - fish_height - padding

        if min_x >= max_x or min_y >= max_y:
            start_x = 50
            start_y = 50
        else:
            start_x = random.randint(min_x, max_x)
            start_y = random.randint(min_y, max_y)

        sprite_path = f"assets/{fish_id}_swim.png"

        if not os.path.exists(sprite_path):
            print(f"⚠️ WARNING: Sprite sheet not found: {sprite_path}")
            print(f"   Fish '{fish_id}' will not be spawned. Please add sprite sheet to assets folder.")
            return

        initial_dx = random.choice([-1, -0.8, -0.5, 0.5, 0.8, 1])
        initial_dy = random.choice([-0.5, -0.3, 0, 0.3, 0.5])

        fish_label = SpriteSheetFish(sprite_path, container)

        if initial_dx > 0:
            fish_label.flip()
            fish_facing_right = True
        else:
            fish_facing_right = False

        fish_label.setGeometry(start_x, start_y, fish_width, fish_height)

        swimming_fish = SwimmingFish(
            fish_id=fish_id,
            label=fish_label,
            sprite_path=sprite_path,
            x=start_x,
            y=start_y,
            width=fish_width,
            height=fish_height
        )

        swimming_fish.dx = initial_dx
        swimming_fish.dy = initial_dy
        swimming_fish.facing_right = fish_facing_right

        fish_label.show()
        fish_label.raise_()
        self.active_fish_sprites.append(swimming_fish)

        self.current_fish_count = len(self.active_fish_sprites)
        self.fish_count_label.setText(f"{self.current_fish_count} fish")

        print(f"✅ Fish spawned successfully! Total fish: {self.current_fish_count}")

    def remove_oldest_fish(self):
        """Removes the oldest NON-FAVORITE fish to make room"""
        favorites = self.time_manager.user_data.get("favorite_fish", [])

        fish_to_remove = None
        for fish in self.active_fish_sprites:
            if fish.fish_id not in favorites:
                fish_to_remove = fish
                break

        if not fish_to_remove and self.active_fish_sprites:
            fish_to_remove = self.active_fish_sprites[0]

        if fish_to_remove:
            self.active_fish_sprites.remove(fish_to_remove)
            fish_to_remove.label.stop()
            fish_to_remove.label.deleteLater()
            print(f"Removed fish {fish_to_remove.fish_id} to make room.")

    def update_hud(self, live_stats, accumulated_active_time):
        current_wpm = live_stats.get("wpm", 0)
        total_chars = live_stats.get("total_chars", 0)

        self.wpm_card.set_value(current_wpm)
        self.chars_card.set_value(total_chars)
        self.focus_card.set_value(accumulated_active_time)

        # Keep Statistics live while it is the visible page
        if self.content_stack.currentWidget() is self.statistics_page:
            self.statistics_page.refresh()

    def close_app(self):
        if hasattr(self, 'movement_timer'):
            self.movement_timer.stop()
        for fish in self.active_fish_sprites:
            fish.label.stop()
        self.close()

    def minimize_app(self):
        self.showMinimized()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.border_widget.setGeometry(0, 0, self.width(), self.height())

    def _in_drag_zone(self, pos):
        """Where the window may be dragged from: the title bar, plus the tank.

        Clicks on non-interactive children - a settings row label, a section
        heading - bubble up to mousePressEvent. If any of those armed a drag,
        the tiny mouse movement in an ordinary click would shift the window.
        """
        bar_bottom = self.top_bar.mapTo(self, QPoint(0, self.top_bar.height())).y()
        if pos.y() <= bar_bottom:
            return True

        if self.content_stack.currentWidget() is self.aquarium_content:
            top_left = self.aquarium_container.mapTo(self, QPoint(0, 0))
            return QRect(top_left, self.aquarium_container.size()).contains(pos)

        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._in_drag_zone(event.position().toPoint()):
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            self.drag_position = None

    def mouseMoveEvent(self, event):
        if self.drag_position is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        super().mouseReleaseEvent(event)