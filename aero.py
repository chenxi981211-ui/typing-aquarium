# aero.py
"""Liquid glass painting for Typing Aquarium.

Every surface is the same recipe: the blurred theme art showing through, the
same art re-sampled larger inside a rim band so the edge bends light, a curved
specular highlight, and light piping along the bottom inner edge.

The window cannot blur the real desktop behind it - Qt has no cross-platform
way to do that - so the window paints a blurred copy of the currently selected
tank artwork as its own backdrop, and every panel refracts that. It also means
the whole app re-tints when the tank theme changes.
"""

import os

from PIL import Image, ImageFilter
from PyQt6.QtWidgets import QWidget, QFrame
from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QRadialGradient, QPainterPath,
                         QPixmap, QImage, QPen, QBrush, QTransform)
from PyQt6.QtCore import Qt, QRectF, QPoint, QPointF

# ===== palette =====
AQUA = "#8AF0FA"
VIOLET = "#C6B0FF"
AMBER = "#FFD696"
TEXT = "#FFFFFF"
TEXT_DIM = "rgba(235, 249, 255, 240)"

# Title-bar icons: a pale aqua rather than plain white, so they read as
# part of the glass instead of sitting on top of it.
ICON_TINT = QColor(174, 233, 247)

# Numerals get a clean humanist monospace - PT Mono is the closest face macOS
# ships to Sometype Mono, which the design calls for but isn't installed.
NUMERIC_FONT = "'PT Mono', 'Andale Mono', 'Courier New', monospace"

# ===== effect strength =====
# Turned down from the first pass: the gloss was washing out the top of every
# panel, which is what made white text hard to read.
GLOSS_ALPHA = 66          # was 132
PIPING_ALPHA = 44         # was 96
RIM_TOP_ALPHA = 170       # was 240
RING_LIGHT_ALPHA = 15     # was 30

# How much of the blurred tank art each surface paints. The shell stays low so
# the real desktop shows through the window; panels sit a little more solid so
# text has something to sit on.
SHELL_BACKDROP_OPACITY = 0.62
PANEL_BACKDROP_OPACITY = 0.78

SHELL_TINT = QColor(10, 48, 88, 168)
PANEL_TINT = QColor(22, 92, 148, 96)
BAR_TINT = QColor(20, 86, 142, 104)
ACTIVE_TINT = QColor(96, 216, 232, 120)
SUNK_TINT = QColor(8, 44, 82, 104)
TAB_ACTIVE_TINT = QColor(86, 212, 201, 175)   # the design's teal orb

# The backdrop is built once at this height and anchored to the top, so the
# window can animate between page heights without re-blurring every frame.
BACKDROP_HEIGHT = 820

_backdrop_cache = {}

# While the window animates between page heights, every glass surface would
# otherwise re-run its refraction pass on every frame - a scaled pixmap through
# a compound clip path, per panel, at 60fps. Fast mode drops the two expensive
# passes for the duration; full quality is restored when the animation ends.
_fast_mode = False


def set_fast_mode(enabled):
    global _fast_mode
    _fast_mode = enabled


def fast_mode():
    return _fast_mode


def rounded(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


_svg_cache = {}


def svg_pixmap(path, size, colour=None, scale=2):
    """Render an SVG to a pixmap, optionally recoloured.

    Rendered at `scale` and tagged with a device pixel ratio so it stays crisp,
    and recoloured via SourceIn so one icon file can serve several states.
    """
    key = (path, size, colour.name() if colour else None, scale)
    if key in _svg_cache:
        return _svg_cache[key]

    from PyQt6.QtSvg import QSvgRenderer

    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(Qt.GlobalColor.transparent)

    if os.path.exists(path):
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        QSvgRenderer(path).render(painter)
        if colour is not None:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), colour)
        painter.end()
    else:
        print(f"⚠️ Icon not found: {path}")

    pixmap.setDevicePixelRatio(scale)
    _svg_cache[key] = pixmap
    return pixmap


_icon_cache = {}


def contrast_icon(path, size, colour=QColor(255, 255, 255), halo=140):
    """A PNG icon recoloured and given a dark halo.

    The title-bar icons ship in pale tones that sit close to the glass behind
    them. Forcing them white and ringing them with a soft dark shadow separates
    them from the bar without darkening the bar itself.
    """
    key = (path, size, colour.name(), halo)
    if key in _icon_cache:
        return _icon_cache[key]

    source = QPixmap(path)
    if source.isNull():
        print(f"⚠️ Icon not found: {path}")
        _icon_cache[key] = source
        return source

    scale = 2
    box = size * scale
    source = source.scaled(box, box, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)

    # Silhouette of the icon, used for the halo
    shadow = QPixmap(source.size())
    shadow.fill(Qt.GlobalColor.transparent)
    sp = QPainter(shadow)
    sp.drawPixmap(0, 0, source)
    sp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    sp.fillRect(shadow.rect(), QColor(2, 18, 38, halo))
    sp.end()

    tinted = QPixmap(source.size())
    tinted.fill(Qt.GlobalColor.transparent)
    tp = QPainter(tinted)
    tp.drawPixmap(0, 0, source)
    tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    tp.fillRect(tinted.rect(), colour)
    tp.end()

    out = QPixmap(box + 2 * scale, box + 2 * scale)
    out.fill(Qt.GlobalColor.transparent)
    op = QPainter(out)
    op.setRenderHint(QPainter.RenderHint.Antialiasing)
    for dx, dy in ((0, scale), (scale, scale), (scale, 0), (0, 0), (2 * scale, scale),
                   (scale, 2 * scale)):
        op.drawPixmap(dx, dy, shadow)
    op.drawPixmap(scale, scale, tinted)
    op.end()

    out.setDevicePixelRatio(scale)
    _icon_cache[key] = out
    return out


def backdrop_pixmap(image_path, width, height=BACKDROP_HEIGHT, blur=30, dim=0.42):
    """Blurred, blue-shifted copy of the tank art, used as the window backdrop."""
    key = (image_path, width, height, blur, dim)
    if key in _backdrop_cache:
        return _backdrop_cache[key]

    if not os.path.exists(image_path):
        pix = QPixmap(width, height)
        pix.fill(QColor(10, 46, 84))
        _backdrop_cache[key] = pix
        return pix

    im = Image.open(image_path).convert("RGB")
    ratio = max(width / im.width, height / im.height)
    im = im.resize((int(im.width * ratio) + 1, int(im.height * ratio) + 1), Image.LANCZOS)
    left, top = (im.width - width) // 2, (im.height - height) // 2
    im = im.crop((left, top, left + width, top + height))
    im = im.filter(ImageFilter.GaussianBlur(blur))
    if dim:
        im = Image.blend(im, Image.new("RGB", im.size, (4, 22, 46)), dim)

    im = im.convert("RGBA")
    qimg = QImage(im.tobytes("raw", "RGBA"), im.width, im.height, QImage.Format.Format_RGBA8888)
    pix = QPixmap.fromImage(qimg.copy())
    _backdrop_cache[key] = pix
    return pix


def paint_liquid(painter, rect, radius, backdrop, origin=QPoint(0, 0),
                 tint=PANEL_TINT, refract=1.26, gloss=True, piping=True, thickness=6,
                 backdrop_opacity=PANEL_BACKDROP_OPACITY):
    """Paint one pane of liquid glass.

    `origin` is where this widget sits inside the window, so the backdrop lines
    up across every panel instead of restarting at each widget's corner.

    `backdrop_opacity` below 1 lets whatever is behind the window show through,
    since the art is painted onto a translucent window rather than an opaque one.
    """
    body = rounded(rect, radius)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    # 1. frosted body
    painter.setClipPath(body)
    if backdrop is not None:
        painter.setOpacity(backdrop_opacity)
        painter.drawPixmap(-origin.x(), -origin.y(), backdrop)
        painter.setOpacity(1.0)

    # 2. refracted rim - the same backdrop, larger, only inside the border band
    inner = QRectF(rect.x() + thickness, rect.y() + thickness,
                   rect.width() - thickness * 2, rect.height() - thickness * 2)
    if not _fast_mode and inner.width() > 0 and inner.height() > 0:
        ring = body.subtracted(rounded(inner, max(1.0, radius - thickness)))
        painter.setClipPath(ring)
        if backdrop is not None:
            t = QTransform()
            t.translate(rect.center().x(), rect.center().y())
            t.scale(refract, refract)
            t.translate(-rect.center().x(), -rect.center().y())
            painter.setTransform(t, True)
            painter.setOpacity(backdrop_opacity)
            painter.drawPixmap(-origin.x(), -origin.y(), backdrop)
            painter.setOpacity(1.0)
            painter.resetTransform()
            painter.setClipPath(ring)
        painter.fillPath(ring, QColor(255, 255, 255, RING_LIGHT_ALPHA))

    # 3. tint
    painter.setClipPath(body)
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    grad.setColorAt(0.0, QColor(tint.red(), tint.green(), tint.blue(), min(255, int(tint.alpha() * 1.15))))
    # The middle used to thin out to 55%, which left text sitting on almost
    # nothing over a bright desktop. Keeping it closer to full holds contrast.
    grad.setColorAt(0.5, QColor(tint.red(), tint.green(), tint.blue(), int(tint.alpha() * 0.80)))
    grad.setColorAt(1.0, QColor(tint.red(), tint.green(), tint.blue(), int(tint.alpha() * 0.95)))
    painter.fillPath(body, grad)

    # 4. curved specular - an ellipse overshooting the top reads as a bulge
    if gloss and not _fast_mode:
        h = rect.height() * 0.62
        bulge = QRectF(rect.x() - rect.width() * 0.18, rect.y() - h * 0.72,
                       rect.width() * 1.36, h * 1.55)
        rg = QRadialGradient(bulge.center(), bulge.width() / 2)
        rg.setColorAt(0.0, QColor(255, 255, 255, GLOSS_ALPHA))
        rg.setColorAt(0.62, QColor(255, 255, 255, int(GLOSS_ALPHA * 0.4)))
        rg.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(rg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(bulge)

    # 5. light piping - light exiting thick glass at the bottom
    if piping:
        band = QRectF(rect.x(), rect.bottom() - rect.height() * 0.34,
                      rect.width(), rect.height() * 0.34)
        bg = QLinearGradient(band.topLeft(), band.bottomLeft())
        bg.setColorAt(0.0, QColor(255, 255, 255, 0))
        bg.setColorAt(0.78, QColor(190, 245, 255, int(PIPING_ALPHA * 0.28)))
        bg.setColorAt(1.0, QColor(226, 252, 255, PIPING_ALPHA))
        painter.fillRect(band, bg)

    painter.setClipping(False)

    # 6. rims - gradient pen, bright where the light lands
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(4, 24, 48, 96), 1.2))
    painter.drawPath(body)

    rim = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    rim.setColorAt(0.0, QColor(255, 255, 255, RIM_TOP_ALPHA))
    rim.setColorAt(0.30, QColor(255, 255, 255, int(RIM_TOP_ALPHA * 0.42)))
    rim.setColorAt(0.75, QColor(255, 255, 255, int(RIM_TOP_ALPHA * 0.20)))
    rim.setColorAt(1.0, QColor(226, 250, 255, int(RIM_TOP_ALPHA * 0.50)))
    painter.setPen(QPen(QBrush(rim), 1.3))
    painter.drawPath(rounded(QRectF(rect.x() + 1.2, rect.y() + 1.2,
                                    rect.width() - 2.4, rect.height() - 2.4),
                             max(0.5, radius - 1)))
    painter.restore()


class LiquidMixin:
    """Shared glass painting + a render cache.

    The cache matters: the fish repaint at 50 FPS, and re-running the refraction
    pass for every panel on every frame would be wasteful. Chrome only rebuilds
    when its size, position or theme actually changes.
    """

    radius = 16
    tint = PANEL_TINT
    refract = 1.26
    gloss = True
    piping = True
    thickness = 6
    backdrop_opacity = PANEL_BACKDROP_OPACITY

    def _init_glass(self):
        self._glass_cache = None
        self._glass_key = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _backdrop(self):
        window = self.window()
        getter = getattr(window, "glass_backdrop", None)
        return getter() if getter else None

    def _origin(self):
        return self.mapTo(self.window(), QPoint(0, 0))

    def invalidate_glass(self):
        self._glass_key = None
        self.update()

    def paint_glass(self, painter):
        backdrop = self._backdrop()
        origin = self._origin()
        key = (self.width(), self.height(), origin.x(), origin.y(),
               id(backdrop), self.tint.rgba(), self.radius,
               self.backdrop_opacity, _fast_mode)

        if self._glass_key != key or self._glass_cache is None:
            cache = QPixmap(self.size())
            cache.fill(Qt.GlobalColor.transparent)
            cp = QPainter(cache)
            paint_liquid(cp, QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
                         self.radius, backdrop, origin, self.tint,
                         self.refract, self.gloss, self.piping, self.thickness,
                         self.backdrop_opacity)
            cp.end()
            self._glass_cache = cache
            self._glass_key = key

        painter.drawPixmap(0, 0, self._glass_cache)


class LiquidPanel(QWidget, LiquidMixin):
    def __init__(self, parent=None, radius=16, tint=PANEL_TINT, refract=1.26,
                 gloss=True, piping=True, thickness=6,
                 backdrop_opacity=PANEL_BACKDROP_OPACITY):
        super().__init__(parent)
        self.radius, self.tint, self.refract = radius, tint, refract
        self.gloss, self.piping, self.thickness = gloss, piping, thickness
        self.backdrop_opacity = backdrop_opacity
        self._init_glass()

    def paintEvent(self, event):
        p = QPainter(self)
        self.paint_glass(p)
        p.end()


class LiquidShell(QFrame, LiquidMixin):
    """The window body: blurred theme art, then glass over it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.radius = 22
        self.tint = SHELL_TINT
        self.refract = 1.16
        self.thickness = 9
        self.gloss = False   # too large for a single highlight to look right
        self.backdrop_opacity = SHELL_BACKDROP_OPACITY
        self._init_glass()

    def paintEvent(self, event):
        p = QPainter(self)
        self.paint_glass(p)
        p.end()


def label_css(size, colour=TEXT, weight=500, italic=False):
    return (f"color: {colour}; font-size: {size}px; font-family: 'DM Sans';"
            f" font-weight: {weight}; background: transparent;"
            f" {'font-style: italic;' if italic else ''}")
