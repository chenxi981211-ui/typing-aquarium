# make_screenshots.py
"""Render one promotional screenshot per feature.

    QT_QPA_PLATFORM=offscreen ~/.venvs/aquarium/bin/python make_screenshots.py

These are genuine renders of the real widgets, not mockups - the same code paths
the app runs. What they are NOT is a picture of your actual progress: they are
drawn against a demo save built below, because an honest screenshot of a fresh
install is one fish and an empty chart, which shows nothing off.

Your real save is never opened. Everything here works from a throwaway file.

The menu bar item and the notification banners are drawn by macOS, not by the
app, so they cannot be captured this way - grab those with Cmd+Shift+4.
"""

import io
import json
import os
import random
import shutil
import tempfile

from PIL import Image, ImageDraw, ImageFilter
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QBuffer, QIODevice

import paths
paths.use_resource_cwd()

OUT_DIR = "promo"
SCALE = 2                      # retina-density output

# A collection part-way filled: enough variety to show rarities and silhouettes
DEMO_OWNED = [
    "guppy", "clownfish", "sardine", "royal_gramma", "coral_grouper",
    "parrotfish", "blue_hippo_tang", "ribboned_sweetlips", "dwarf_gouramis",
    "cherry_shrimp", "opah", "moorish_idol", "seahorse",
]
DEMO_FAVOURITES = ["clownfish", "moorish_idol", "cherry_shrimp"]


def demo_save(path):
    """A plausible few weeks of use, so the charts have something to draw."""
    rng = random.Random(20260808)
    history = {}
    for day in range(1, 29):
        date = f"2026-07-{day:02d}"
        chars = rng.choice([0, 0, 1800, 3200, 4700, 6100, 7400, 9200, 11500])
        if chars:
            history[date] = {
                "chars": chars,
                "focus_seconds": int(chars / 4.2),
                "avg_wpm": rng.randint(48, 72),
                "highest_wpm": rng.randint(70, 96),
                "longest_focus": rng.randint(180, 900),
            }

    # The current week needs filling too, or the Week chart shows a single bar -
    # it reads from calendar Mon-Sun, and the July history above falls outside it.
    for date, chars in (("2026-08-03", 7400), ("2026-08-04", 9775),
                        ("2026-08-05", 10786), ("2026-08-06", 4200),
                        ("2026-08-07", 8600)):
        history[date] = {
            "chars": chars,
            "focus_seconds": int(chars / 4.2),
            "avg_wpm": rng.randint(52, 70),
            "highest_wpm": rng.randint(74, 94),
            "longest_focus": rng.randint(240, 900),
        }

    # A day with a believable shape: a morning block, a dip, a long afternoon
    hourly = {"8": 420, "9": 1180, "10": 1640, "11": 980, "12": 260,
              "13": 540, "14": 1720, "15": 2050, "16": 1380, "17": 610}

    json.dump({
        "last_saved_date": "2026-08-08",
        "total_chars_today": sum(hourly.values()),
        "total_chars_all_time": 128_400,
        "highest_wpm_today": 88,
        "highest_wpm_all_time": 96,
        "longest_focus_today": 742.0,
        "longest_focus_all_time": 1120.0,
        "longest_burst_today": 2.4,
        "typing_seconds_today": 1900.0,
        "total_active_time": 5400.0,
        "wpm_sample_total": 61_000,
        "wpm_sample_count": 1000,
        "streak_days": 6,
        "owned_fish": list(DEMO_OWNED),
        "favorite_fish": list(DEMO_FAVOURITES),
        "viewed_fish": [f for f in DEMO_OWNED if f not in ("moorish_idol", "opah")],
        "discovery_dates": {f: "2026-07-21" for f in DEMO_OWNED},
        "caught_today": ["moorish_idol", "opah"],
        "daily_history": history,
        "hourly_activity": hourly,
        "settings": {
            "tank_background": "Spongebob.png",
            "notify_new_fish": True,
            "notify_daily_reminder": True,
            "master_volume": 55,
            "music_enabled": True,
            "music_volume": 70,
            "sound_notification": True,
            "sound_effects": True,
        },
    }, open(path, "w"), indent=2)


def settle(app, window=None, passes=8):
    for _ in range(passes):
        app.processEvents()
    # Jump any running geometry animation straight to its end, rather than
    # catching the window mid-resize.
    anim = getattr(window, "anim", None)
    if anim is not None:
        anim.setCurrentTime(anim.duration())
    for _ in range(passes):
        app.processEvents()


def light_backdrop(width, height):
    """A soft, near-white wash with a hint of aqua at the bottom."""
    base = Image.new("RGB", (width, height), (255, 255, 255))
    top, bottom = (252, 253, 255), (228, 240, 248)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        blend = y / max(1, height - 1)
        draw.line([(0, y), (width, y)],
                  fill=tuple(round(a + (b - a) * blend) for a, b in zip(top, bottom)))
    return base


def to_pil(pixmap):
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
    pixmap.save(buffer, "PNG")
    return Image.open(io.BytesIO(buffer.data().data())).convert("RGBA")


def shoot_light(widget, name, app, pad=56, shadow=True):
    """Render the widget onto a light background, with a soft drop shadow.

    The window has rounded, part-transparent edges, so its own alpha doubles as
    the shape of the shadow - no need to guess a rectangle.
    """
    settle(app, widget)

    size = widget.size()
    shot = QPixmap(size.width() * SCALE, size.height() * SCALE)
    shot.setDevicePixelRatio(SCALE)
    shot.fill(Qt.GlobalColor.transparent)
    widget.render(shot)

    window_img = to_pil(shot)
    w, h = window_img.size
    p = pad * SCALE
    canvas = light_backdrop(w + p * 2, h + p * 2).convert("RGBA")

    if shadow:
        # Built from the window's own alpha, blurred and dropped a little.
        blur = 18 * SCALE
        drop = 10 * SCALE
        shade = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        silhouette = Image.new("RGBA", window_img.size, (12, 38, 66, 150))
        silhouette.putalpha(window_img.split()[3].point(lambda a: int(a * 0.55)))
        shade.paste(silhouette, (p, p + drop), silhouette)
        shade = shade.filter(ImageFilter.GaussianBlur(blur))
        canvas = Image.alpha_composite(canvas, shade)

    canvas.paste(window_img, (p, p), window_img)

    path = os.path.join(OUT_DIR, name)
    canvas.convert("RGB").save(path)
    print(f"  {name:28s} {canvas.width}x{canvas.height} px")
    return path


def shoot(widget, name, app, pad=28, backdrop=(9, 38, 68)):
    """Render a widget onto a plain deep-water mat, at retina density.

    QT_SCALE_FACTOR is ignored by the offscreen platform, so the density comes
    from the target pixmap instead: give it a device pixel ratio and Qt paints
    the widget at that scale into it, which is a true 2x render rather than an
    upscale of a 1x one.
    """
    settle(app, widget)

    size = widget.size()
    shot = QPixmap(size.width() * SCALE, size.height() * SCALE)
    shot.setDevicePixelRatio(SCALE)
    shot.fill(Qt.GlobalColor.transparent)
    widget.render(shot)

    canvas = QPixmap((size.width() + pad * 2) * SCALE, (size.height() + pad * 2) * SCALE)
    canvas.setDevicePixelRatio(SCALE)
    canvas.fill(QColor(*backdrop))
    painter = QPainter(canvas)
    painter.drawPixmap(pad, pad, shot)
    painter.end()

    path = os.path.join(OUT_DIR, name)
    canvas.save(path)
    print(f"  {name:28s} {canvas.width()}x{canvas.height()} px")
    return path


def make_resize_instant(window):
    """Apply page resizes immediately instead of animating them.

    The 300ms geometry animation never completes under the offscreen platform,
    so every page came out at the tank's height - Statistics and Settings were
    cropped to the wrong size. Screenshots want the settled state anyway.
    """
    def instant(target_rect, on_finish=None):
        window.setMinimumSize(0, 0)
        window.setMaximumSize(16777215, 16777215)
        window.setGeometry(target_rect)
        window.border_widget.setGeometry(0, 0, target_rect.width(), target_rect.height())
        window.setFixedSize(target_rect.width(), target_rect.height())
        if on_finish is not None:
            on_finish()
        window.refresh_glass()

    window.animate_resize = instant


def main():
    app = QApplication([])

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    tmp = tempfile.mkdtemp(prefix="aq-promo-")
    save_path = os.path.join(tmp, "save.json")
    demo_save(save_path)

    from time_manager import UnlockManager
    from ui_aquarium import AquariumWidget
    from fish_details import FishDetailsWindow
    from full_view import FullTankWindow

    manager = UnlockManager(save_json_path=save_path)
    fish_by_id = {f["id"]: f for f in manager.fish_definitions}

    window = AquariumWidget([], manager)
    make_resize_instant(window)
    window.show()
    settle(app, window)

    # A stocked tank reads far better than an empty one. Positions are set by
    # hand afterwards: left to chance, two fish landed on top of each other.
    stock = ["clownfish", "blue_hippo_tang", "moorish_idol",
             "cherry_shrimp", "parrotfish", "opah"]
    for fish_id in stock:
        window.spawn_fish_sprite(fish_id)
    settle(app, window)

    spots = [(40, 150), (150, 60), (240, 165), (60, 40), (250, 45), (160, 175)]
    for fish, (x, y) in zip(window.active_fish_sprites, spots):
        fish.x, fish.y = x, y
        fish.label.move(x, y)

    # The stat cards are fed by a signal from main.py, which is not running
    # here, so they would read zero. Push the demo figures in directly.
    window.update_hud({"wpm": 74, "total_chars": manager.total_chars_today},
                      manager.total_active_time)
    settle(app, window)

    print("rendering:")
    window.show_aquarium()
    shoot_light(window, "01-tank.png", app)

    window.show_collection()
    shoot_light(window, "02-collection.png", app)

    window.show_statistics()
    shoot_light(window, "03-statistics.png", app)

    window.show_settings()
    shoot_light(window, "04-settings.png", app)

    # Minimal mode: the tank on its own
    window.show_aquarium()
    settle(app, window)
    window.toggle_view_mode()
    shoot_light(window, "05-minimal-mode.png", app)
    window.toggle_view_mode()
    settle(app, window)

    # Fish detail, caught and uncaught
    detail = FishDetailsWindow(fish_by_id["moorish_idol"], manager)
    detail.show()
    shoot_light(detail, "06-fish-detail.png", app)
    detail.close()

    locked = FishDetailsWindow(fish_by_id["swordfish"], manager)
    locked.show()
    shoot_light(locked, "07-locked-fish.png", app)
    locked.close()

    # Full-screen tank
    full = FullTankWindow(manager, "Spongebob.png", window)
    full.setFixedSize(1440, 900)
    # scale is worked out from the screen at construction, so it has to be
    # recomputed for the size actually being rendered or the fish come out wrong
    import full_view
    full.scale = min(1440 / full_view.TANK_WIDTH, 900 / full_view.TANK_HEIGHT)
    full.fish_size = int(full_view.TANK_FISH_SIZE * full.scale)
    full.stock(["clownfish", "blue_hippo_tang", "moorish_idol", "parrotfish"])
    full.show()
    shoot_light(full, "08-full-view.png", app, pad=0, shadow=False)
    full.close()

    window.close()
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nwrote {len(os.listdir(OUT_DIR))} screenshots to {OUT_DIR}/")
    print("menu bar item and notification banners are drawn by macOS - "
          "capture those with Cmd+Shift+4")


if __name__ == "__main__":
    main()
