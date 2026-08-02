# statistics_widget.py

from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QFont
from PyQt6.QtCore import Qt, QRectF

import aero

TEAL = aero.AQUA
PURPLE = aero.VIOLET
GOLD = aero.AMBER
CHART_GREEN = QColor("#B5F06E")
CHART_TEAL = QColor("#56D4C9")
CARD_BG = "rgba(255, 255, 255, 0.04)"
CHART_BG = "rgba(0, 0, 0, 0.25)"


def format_count(value):
    """5200 -> '5,200';  38200 -> '38.2k';  1200000 -> '1.2M'"""
    value = int(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value / 1000:.1f}k"
    return f"{value:,}"


def format_duration(seconds):
    """Compact duration for the stat cards: '5hrs', '42min', '30s'."""
    seconds = int(seconds)
    if seconds >= 3600:
        hours = seconds / 3600
        return f"{hours:.0f}hrs" if hours >= 2 else f"{hours:.1f}hr"
    if seconds >= 60:
        return f"{seconds // 60}min"
    return f"{seconds}s"


class StatHalf(QWidget):
    """One side of a split stat row: a big coloured value over a caption."""

    def __init__(self, caption, emphasis, accent, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 9, 12, 9)
        layout.setSpacing(2)

        self.value_label = QLabel("0")
        self.value_label.setStyleSheet(f"""
            color: {accent};
            font-size: 20px;
            font-weight: bold;
            font-family: 'Sometype Mono';
            background: transparent;
        """)

        self.caption_label = QLabel()
        self.caption_label.setTextFormat(Qt.TextFormat.RichText)
        self.caption_label.setText(
            f"<span style='color: rgba(222,243,255,0.75);'>{caption} • </span>"
            f"<span style='color: #FFFFFF; font-weight: 600;'>{emphasis}</span>"
        )
        self.caption_label.setStyleSheet("""
            font-size: 11px;
            font-family: 'DM Sans';
            background: transparent;
        """)

        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, text):
        self.value_label.setText(str(text))


class SplitStatRow(aero.LiquidPanel):
    """A glass card holding two StatHalfs separated by a vertical rule."""

    def __init__(self, left, right, accent, parent=None):
        super().__init__(parent, radius=18, tint=aero.PANEL_TINT,
                         refract=1.28, thickness=6)
        self.setFixedHeight(58)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.left = StatHalf(left[0], left[1], accent)
        self.right = StatHalf(right[0], right[1], accent)

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.12); border: none;")

        layout.addWidget(self.left, 1)
        layout.addWidget(divider)
        layout.addWidget(self.right, 1)


class BarChart(QWidget):
    """Rounded-cap bar chart. Bars never fall below a dot so empty days stay visible."""

    def __init__(self, bar_color, bar_width=22, parent=None):
        super().__init__(parent)
        self.bar_color = bar_color
        self.bar_width = bar_width
        self.values = []
        self.labels = []
        self.edge_labels = None  # (left, middle, right) instead of per-bar labels
        self.setStyleSheet("background: transparent;")

    def set_data(self, values, labels=None, edge_labels=None):
        self.values = list(values)
        self.labels = list(labels) if labels else []
        self.edge_labels = edge_labels
        self.update()

    def paintEvent(self, event):
        if not self.values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        label_height = 22
        top_pad = 8
        chart_height = max(1, self.height() - label_height - top_pad)

        peak = max(self.values) or 1
        count = len(self.values)
        slot = self.width() / count
        bar_w = min(self.bar_width, slot * 0.62)
        radius = bar_w / 2

        font = QFont("DM Sans", 9)
        painter.setFont(font)

        for i, value in enumerate(self.values):
            centre = slot * (i + 0.5)
            x = centre - bar_w / 2

            if value <= 0:
                # Empty slot: a dim stub, so the axis still reads as a series
                bar_h = bar_w * 0.45
                painter.setBrush(QColor(255, 255, 255, 28))
            else:
                bar_h = max(bar_w, (value / peak) * chart_height)
                painter.setBrush(self.bar_color)

            painter.setPen(Qt.PenStyle.NoPen)
            y = top_pad + chart_height - bar_h
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, y, bar_w, bar_h), radius, radius)
            painter.drawPath(path)

            if self.labels and i < len(self.labels):
                painter.setPen(QColor(255, 255, 255, 140))
                painter.drawText(
                    QRectF(centre - slot / 2, self.height() - label_height, slot, label_height),
                    Qt.AlignmentFlag.AlignCenter, self.labels[i])

        if self.edge_labels:
            painter.setPen(QColor(255, 255, 255, 140))
            left, middle, right = self.edge_labels
            band = QRectF(0, self.height() - label_height, self.width(), label_height)
            painter.drawText(band, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, left)
            painter.drawText(band, Qt.AlignmentFlag.AlignCenter, middle)
            painter.drawText(band, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right)

        painter.end()


class RangeToggle(QWidget):
    """The 7d / 30d pill pair."""

    def __init__(self, on_change, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        self.days = 7

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.btn_7 = QPushButton("7d")
        self.btn_30 = QPushButton("30d")

        for btn, days in ((self.btn_7, 7), (self.btn_30, 30)):
            btn.setFixedSize(46, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, d=days: self.select(d))
            layout.addWidget(btn)

        self._restyle()

    def select(self, days):
        if days == self.days:
            return
        self.days = days
        self._restyle()
        self.on_change(days)

    def _restyle(self):
        for btn, days in ((self.btn_7, 7), (self.btn_30, 30)):
            active = days == self.days
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'rgba(86, 212, 201, 0.15)' if active else 'transparent'};
                    color: {TEAL if active else 'rgba(255, 255, 255, 0.5)'};
                    border: 1px solid {'rgba(86, 212, 201, 0.6)' if active else 'rgba(255, 255, 255, 0.15)'};
                    border-radius: 13px;
                    font-size: 11px;
                    font-family: 'DM Sans';
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    border-color: rgba(86, 212, 201, 0.5);
                }}
            """)


class StatisticsPage(QWidget):
    """The Statistics screen. Call refresh() whenever it becomes visible."""

    PAGE_HEIGHT = 640

    def __init__(self, time_manager, parent=None):
        super().__init__(parent)
        self.time_manager = time_manager
        self.range_days = 7

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 4)
        layout.setSpacing(8)

        layout.addWidget(self._section_label("Typing Stats"))

        self.chars_row = SplitStatRow(("Characters", "Today"), ("All time chars", "Total"), TEAL)
        self.speed_row = SplitStatRow(("Avg speed", "Today"), ("Highest speed", "Total"), PURPLE)
        self.focus_row = SplitStatRow(("Focus duration", "Today"), ("Longest duration", "Today"), GOLD)

        layout.addWidget(self.chars_row)
        layout.addWidget(self.speed_row)
        layout.addWidget(self.focus_row)

        # ===== Typing activity =====
        activity_header = QHBoxLayout()
        activity_header.setContentsMargins(0, 4, 0, 0)
        activity_header.addWidget(self._section_label("Typing Activity"))
        activity_header.addStretch()
        self.range_toggle = RangeToggle(self._on_range_changed)
        activity_header.addWidget(self.range_toggle)
        layout.addLayout(activity_header)

        self.daily_chart = BarChart(CHART_GREEN, bar_width=22)
        layout.addWidget(self._chart_card(self.daily_chart, 126))

        # ===== Today by hour =====
        layout.addWidget(self._section_label("Today by Hour"))
        self.hourly_chart = BarChart(CHART_TEAL, bar_width=10)
        layout.addWidget(self._chart_card(self.hourly_chart, 78))

        layout.addStretch()

    def _section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 13px;
            font-family: 'DM Sans';
            font-weight: 600;
            background: transparent;
        """)
        return label

    def _chart_card(self, chart, height):
        card = aero.LiquidPanel(radius=18, tint=aero.SUNK_TINT,
                                refract=1.24, thickness=6, gloss=False)
        card.setFixedHeight(height)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 6)
        card_layout.addWidget(chart)
        return card

    def _on_range_changed(self, days):
        self.range_days = days
        self.refresh()

    def refresh(self):
        """Pull current numbers out of the manager and repaint."""
        tm = self.time_manager

        self.chars_row.left.set_value(format_count(tm.total_chars_today))
        self.chars_row.right.set_value(format_count(tm.total_chars_all_time))

        self.speed_row.left.set_value(f"{tm.avg_wpm_today} wpm")
        self.speed_row.right.set_value(f"{tm.highest_wpm_all_time} wpm")

        self.focus_row.left.set_value(format_duration(tm.total_active_time))
        self.focus_row.right.set_value(format_duration(tm.longest_focus_today))

        history = tm.get_daily_history(self.range_days)
        values = [stats["chars"] for _, stats in history]

        if self.range_days == 7:
            labels = [date.strftime("%a") for date, _ in history]
            self.daily_chart.set_data(values, labels=labels)
        else:
            # 30 labels won't fit; mark the ends instead
            first, last = history[0][0], history[-1][0]
            self.daily_chart.set_data(
                values, edge_labels=(first.strftime("%d %b"), "", last.strftime("%d %b")))

        self.hourly_chart.set_data(tm.get_hourly_activity(),
                                   edge_labels=("12am", "12pm", "11pm"))
