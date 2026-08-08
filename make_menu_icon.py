# make_menu_icon.py
"""Draw the monochrome fish for the macOS menu bar.

    ~/.venvs/aquarium/bin/python make_menu_icon.py

The app logo is a detailed colour square, which turns to mush at 22 points and
looks wrong sitting among the system's monochrome glyphs. This draws a plain
silhouette instead, as a black shape on transparency - a "template image" in
macOS terms, which the system re-tints itself, so it stays legible against a
light or dark menu bar and inverts correctly when the menu is highlighted.

Shapes are laid out in a 100x100 space and scaled, so one description serves
every size that gets rendered.
"""

import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainter, QPainterPath, QPixmap, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF

OUT_DIR = "assets"
SIZES = {"menu_fish.png": 22, "menu_fish@2x.png": 44}


def fish_path():
    """A left-facing fish: almond body, notched tail, punched-out eye."""
    body = QPainterPath()
    # Nose at the left, sweeping over the back to the tail root on the right
    body.moveTo(6, 50)
    body.cubicTo(24, 22, 56, 20, 72, 40)
    body.lineTo(72, 60)
    body.cubicTo(56, 80, 24, 78, 6, 50)
    body.closeSubpath()

    tail = QPainterPath()
    tail.moveTo(70, 50)
    tail.lineTo(96, 27)
    tail.lineTo(88, 50)
    tail.lineTo(96, 73)
    tail.closeSubpath()

    fin = QPainterPath()
    fin.moveTo(38, 70)
    fin.cubicTo(44, 84, 56, 84, 58, 72)
    fin.closeSubpath()

    shape = body.united(tail).united(fin)

    # The eye is subtracted rather than drawn, so it reads as a hole at any
    # tint - a dark dot on a dark glyph would simply disappear.
    eye = QPainterPath()
    eye.addEllipse(QRectF(18, 42, 9, 9))
    return shape.subtracted(eye)


def render(size):
    scale = size / 100.0
    # Drawn at 4x then downsampled: Qt's antialiasing alone leaves the diagonal
    # tail edges ragged at 22px.
    ss = int(size * 4)
    big = QPixmap(ss, ss)
    big.fill(Qt.GlobalColor.transparent)

    painter = QPainter(big)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(ss / 100.0, ss / 100.0)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0))
    painter.drawPath(fish_path())
    painter.end()

    return big.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.SmoothTransformation)


def main():
    app = QApplication([])
    for name, size in SIZES.items():
        path = os.path.join(OUT_DIR, name)
        render(size).save(path)
        print(f"wrote {path}  {size}x{size}")
    del app


if __name__ == "__main__":
    main()
