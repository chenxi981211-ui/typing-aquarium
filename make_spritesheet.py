# make_spritesheet.py
"""Turn single fish stills into the 1024x1024 / 4x4 / 16-frame sheets the app animates.

    ~/.venvs/aquarium/bin/python make_spritesheet.py            # report only
    ~/.venvs/aquarium/bin/python make_spritesheet.py --write    # write the sheets

The original still for each fish is kept in assets/stills/ so sheets can be
regenerated with different settings later - once a still has been replaced by a
sheet the source is otherwise gone.

Sheets that already contain a 4x4 grid are detected by their transparent
gutters and left alone. Size is not a reliable test: pictus_catfish arrived as a
1024x1024 *still*, which the app would happily have sliced into 16 fragments.

Motion styles, because not everything in a tank swims like a fish:
  swim   travelling wave down the body, weighted to the tail (default)
  hover  body holds its shape and sculls - shrimp and other crustaceans
  sway   upright body, curled tail sways side to side - seahorses
"""

import argparse
import json
import math
import os
import shutil

from PIL import Image

SHEET, GRID = 1024, 4
FRAME = SHEET // GRID
FRAMES = GRID * GRID

ASSETS = "assets"
STILLS = os.path.join(ASSETS, "stills")

# Anything not listed swims.
MOTION = {
    "cherry_shrimp": "hover",
    "seahorse": "sway",
}


# ===== analysis ===========================================================

def content_bands(image, axis, step=3):
    """Runs of non-transparent pixels along an axis - a 4x4 grid shows 4 bands."""
    width, height = image.size
    alpha = image.getchannel("A").load()

    if axis == "x":
        filled = [any(alpha[x, y] > 12 for y in range(0, height, step)) for x in range(width)]
    else:
        filled = [any(alpha[x, y] > 12 for x in range(0, width, step)) for y in range(height)]

    runs, start = [], None
    for i, value in enumerate(filled):
        if value and start is None:
            start = i
        elif not value and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(filled) - 1))
    return runs


def is_grid(image):
    return len(content_bands(image, "x")) >= 3 and len(content_bands(image, "y")) >= 3


# ===== preparation ========================================================

def trim(image, pad=0.05):
    image = image.convert("RGBA")
    box = image.getbbox()
    if box:
        image = image.crop(box)
    margin = int(max(image.size) * pad) + 2
    canvas = Image.new("RGBA", (image.width + margin * 2, image.height + margin * 2), (0, 0, 0, 0))
    canvas.paste(image, (margin, margin))
    return canvas


def fit(image, size=FRAME):
    """Scale to fit one frame, centred, aspect preserved.

    Leaves headroom so the wave displacement can't push pixels out of frame.
    """
    usable = int(size * 0.88)
    ratio = min(usable / image.width, usable / image.height)
    image = image.resize((max(1, int(image.width * ratio)), max(1, int(image.height * ratio))),
                         Image.LANCZOS)
    cell = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cell.paste(image, ((size - image.width) // 2, (size - image.height) // 2))
    return cell


# ===== motion =============================================================

def frame_swim(base, phase, amplitude=9.0, waves=1.3):
    """Travelling wave along the body. The art faces left, so the tail is on the
    right - displacement grows towards it while the head stays steady."""
    width, height = base.size
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for x in range(width):
        t = x / max(1, width - 1)
        offset = amplitude * (t ** 2) * math.sin(phase + t * waves * 2 * math.pi)
        out.paste(base.crop((x, 0, x + 1, height)), (x, int(round(offset))))
    return out


def frame_hover(base, phase, amplitude=6.0):
    """Shrimp hold their shape and scull, so the whole body bobs and tilts
    instead of undulating."""
    width, height = base.size
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dy = amplitude * math.sin(phase)
    dx = amplitude * 0.5 * math.sin(phase * 2 + 0.6)
    body = base.rotate(2.2 * math.sin(phase + 0.4), resample=Image.BICUBIC, expand=False)
    out.paste(body, (int(round(dx)), int(round(dy))))
    return out


def frame_sway(base, phase, amplitude=9.0, bob=3.5):
    """Seahorses stay upright: rows are displaced horizontally, weighted towards
    the bottom so the curled tail sways while the head stays put."""
    width, height = base.size
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dy = int(round(bob * math.sin(phase)))
    for y in range(height):
        t = y / max(1, height - 1)
        offset = amplitude * (t ** 2.2) * math.sin(phase + t * 1.1 * 2 * math.pi)
        out.paste(base.crop((0, y, width, y + 1)), (int(round(offset)), y + dy))
    return out


FRAME_FN = {"swim": frame_swim, "hover": frame_hover, "sway": frame_sway}


def build_sheet(base, motion="swim"):
    make_frame = FRAME_FN[motion]
    sheet = Image.new("RGBA", (SHEET, SHEET), (0, 0, 0, 0))
    for i in range(FRAMES):
        cell = make_frame(base, 2 * math.pi * i / FRAMES)
        sheet.paste(cell, ((i % GRID) * FRAME, (i // GRID) * FRAME))
    return sheet


# ===== driver =============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the sheets into assets/")
    parser.add_argument("--only", help="regenerate a single fish id")
    args = parser.parse_args()

    known = {fish["id"] for fish in json.load(open("fish.JSON"))}
    if args.write:
        os.makedirs(STILLS, exist_ok=True)

    generated, already, unknown = [], [], []

    for fish_id in sorted(known):
        if args.only and fish_id != args.only:
            continue

        sheet_path = os.path.join(ASSETS, f"{fish_id}_swim.png")
        still_path = os.path.join(STILLS, f"{fish_id}.png")

        source_path = still_path if os.path.exists(still_path) else sheet_path
        if not os.path.exists(source_path):
            unknown.append(fish_id)
            continue

        source = Image.open(source_path).convert("RGBA")

        # Hand-drawn sheets stay untouched
        if source_path == sheet_path and is_grid(source):
            already.append(fish_id)
            continue

        motion = MOTION.get(fish_id, "swim")
        base = fit(trim(source))
        sheet = build_sheet(base, motion)

        if args.write:
            if not os.path.exists(still_path):
                shutil.copy2(source_path, still_path)
            sheet.save(sheet_path)

        generated.append((fish_id, motion, f"{source.width}x{source.height}"))

    print(f"{'fish':26s} {'motion':7s} source")
    print("-" * 52)
    for fish_id, motion, size in generated:
        print(f"{fish_id:26s} {motion:7s} {size}")

    if already:
        print(f"\nalready hand-animated, left alone ({len(already)}):")
        print("  " + ", ".join(already))
    if unknown:
        print(f"\nno artwork found ({len(unknown)}): " + ", ".join(unknown))

    print(f"\n{'WROTE' if args.write else 'DRY RUN - rerun with --write'} "
          f"{len(generated)} sheets")


if __name__ == "__main__":
    main()
