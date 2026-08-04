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

Each fish is assigned a swimming mode based on how the animal actually moves:
thunniform and carangiform for rigid-bodied cruisers, subcarangiform and
anguilliform for fish that undulate, labriform and balistiform for reef fish
that hold the body still and row with their fins, plus one-off profiles for the
betta, pufferfish, shrimp and seahorse. See PROFILES.
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

def smoothstep(edge0, edge1, x):
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def mesh_warp(image, displace, cells=26):
    """Warp with a mesh so different parts of the body can move independently.

    `displace(u, v)` takes normalised coordinates and returns (dx, dy) in
    pixels. Sliding whole columns can only bend a body one way; a mesh lets the
    antennae flick while the legs flutter at a different rate and the shell
    stays rigid.
    """
    width, height = image.size
    mesh = []
    for i in range(cells):
        for j in range(cells):
            x0, x1 = i * width / cells, (i + 1) * width / cells
            y0, y1 = j * height / cells, (j + 1) * height / cells
            quad = []
            for px, py in ((x0, y0), (x0, y1), (x1, y1), (x1, y0)):
                dx, dy = displace(px / width, py / height)
                quad.extend((px - dx, py - dy))
            mesh.append(((int(x0), int(y0), int(x1), int(y1)), tuple(quad)))
    # NEAREST, not BILINEAR: these are hard-edged pixel sprites and bilinear
    # resampling visibly smudges them.
    return image.transform((width, height), Image.MESH, mesh, Image.NEAREST)


def rigid_offset(u, v, angle_deg, pivot=(0.32, 0.44), size=FRAME):
    """Displacement for rotating a point about a pivot as part of a solid body.

    Applied across the whole frame this rotates the sprite rigidly - no shear,
    no bending. Points far from the pivot travel furthest, so a pivot set behind
    the head makes the torso swing while the nose barely moves, which is what
    sculling actually looks like.
    """
    angle = math.radians(angle_deg)
    x, y = u * size, v * size
    px, py = pivot[0] * size, pivot[1] * size
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    dx = (cos_a - 1) * (x - px) - sin_a * (y - py)
    dy = sin_a * (x - px) + (cos_a - 1) * (y - py)
    return dx, dy


def frame_veil(base, phase, body_line=0.42, fin_start=0.10, caudal_start=0.55):
    """Long-finned hoverer: compact body, huge fins that trail behind it.

    A betta barely undulates - the character is entirely in the veil fins, which
    lag the body and keep rippling after it has stopped. That lag is produced by
    shifting each point's phase by how far it sits from the body line, so fin
    edges are furthest behind. A single body wave cannot express this, because
    the fins have to move on a different phase from the spine they hang off.

    Every frequency multiplier is a whole number, so the cycle closes seamlessly
    at frame 16.
    """
    def displace(u, v):
        # how far from the body's centre line, and how far into the tail fan
        vertical_fin = smoothstep(fin_start, 0.42, abs(v - body_line))
        caudal_fin = smoothstep(caudal_start, 0.95, u)
        fin = max(vertical_fin, caudal_fin)

        # The torso swings as one solid piece rather than bending. Rotating the
        # whole frame about a pivot behind the head keeps the body rigid and
        # still carries the fins along, since they sit furthest from the pivot.
        dx, dy = rigid_offset(u, v, 4.0 * math.sin(phase), pivot=(0.30, 0.44))

        # bob and a little surge, again as whole-body movement
        dy += 3.0 * math.sin(phase + 0.6)
        dx += 1.6 * math.sin(phase * 2 + 0.3)

        # Fins ripple on their own account, on top of the rigid swing. Dorsal
        # and anal are given opposite phase so the fish doesn't look like it is
        # pulsing symmetrically, which reads as unnatural.
        above = v < body_line
        side_phase = 0.0 if above else 1.5
        lag = 1.9 * fin

        dy += 9.5 * fin * math.sin(phase - lag + side_phase + u * 3.0)
        dx += 4.0 * caudal_fin * math.sin(phase - lag + 0.6)

        # a finer ripple across the membrane, twice per cycle
        dy += 4.0 * fin * math.sin(phase * 2 - lag + side_phase + v * 7.0)

        # the outermost edge curls further than the fin base
        edge = fin ** 2
        dy += 4.5 * edge * math.sin(phase * 2 - lag * 1.4 + u * 5.0)
        dx += 2.5 * edge * math.sin(phase - lag * 1.4 + v * 4.0)

        # pectoral fan just behind the head flutters fast and independently
        pectoral = (smoothstep(0.16, 0.24, u) * (1.0 - smoothstep(0.30, 0.40, u))
                    * smoothstep(0.30, 0.42, v) * (1.0 - smoothstep(0.52, 0.62, v)))
        dy += 3.0 * pectoral * math.sin(phase * 3)

        return dx, dy

    return mesh_warp(base, displace, cells=32)


def frame_rigid_fins(base, phase, pectoral=(0.44, 0.66, 0.34, 0.66), caudal_start=0.76):
    """Inflated body that cannot bend at all, driven entirely by its fins.

    A pufferfish is the opposite of the betta: there the body was still and the
    fins flowed, here the body is genuinely rigid - an inflated pufferfish
    physically cannot flex - and the small pectoral fan whirring at 4x the body
    rate is what moves it, with the tail trailing as a rudder.

    `pectoral` is (u0, u1, v0, v1) bounding the pectoral fan.
    """
    u0, u1, v0, v1 = pectoral

    def displace(u, v):
        # the whole animal rocks and bobs, but never deforms
        dx, dy = rigid_offset(u, v, 2.2 * math.sin(phase), pivot=(0.45, 0.50))
        dy += 3.5 * math.sin(phase)
        dx += 1.2 * math.sin(phase * 2 + 0.4)

        # tail acts as a rudder rather than a motor - slower, wider sweep
        caudal = smoothstep(caudal_start, 1.0, u)
        dy += 7.5 * caudal * math.sin(phase * 2 + 0.5)
        dx += 2.2 * caudal * math.sin(phase * 2 + 1.3)

        # pectoral fan: small, fast, and the actual source of propulsion
        fan = (smoothstep(u0, u0 + 0.06, u) * (1.0 - smoothstep(u1 - 0.06, u1, u))
               * smoothstep(v0, v0 + 0.06, v) * (1.0 - smoothstep(v1 - 0.06, v1, v)))
        dy += 4.5 * fan * math.sin(phase * 4)
        dx += 3.0 * fan * math.sin(phase * 4 + 1.6)

        return dx, dy

    return mesh_warp(base, displace, cells=32)


def frame_shrimp(base, phase):
    """Cherry shrimp: rigid shell, beating swimmerets, flicking antennae.

    The source art faces right but is mirrored before it gets here, so as with
    every other sprite the rostrum and antennae sit at u=0 and the tail fan at
    u=1. Crustaceans can't undulate - the body holds its shape and hovers while
    the appendages do the work, which is what separates this from a fish.
    """
    def displace(u, v):
        # whole animal hovers, with a slight nose-up/nose-down pitch
        dy = 4.5 * math.sin(phase)
        dy += 2.6 * math.sin(phase + 0.7) * (0.5 - u) * 2
        dx = 1.8 * math.sin(phase * 2 + 0.4)

        # antennae: long, thin, upper front - flick faster and lag the body
        antenna = (1.0 - smoothstep(0.0, 0.34, u)) * (1.0 - smoothstep(0.30, 0.72, v))
        dy += 5.0 * antenna * math.sin(phase * 2 + 1.1)
        dx += 2.4 * antenna * math.sin(phase * 2 + 1.8)

        # pleopods and walking legs: ventral, fast, travelling front to back
        legs = smoothstep(0.55, 0.86, v) * (1.0 - smoothstep(0.70, 0.92, u))
        dy += 2.8 * legs * math.sin(phase * 3 + (1.0 - u) * 5.5)

        # tail fan gives a small flex at the far end
        fan = smoothstep(0.78, 1.0, u)
        dy += 2.2 * fan * math.sin(phase + 2.4)

        return dx, dy

    return mesh_warp(base, displace)


def frame_bcf(base, phase, amplitude=9.0, envelope=2.0, waves=1.1, beat=1,
              swing=2.0, pivot_u=0.24, bob=1.6):
    """Body-and-caudal-fin swimming, the mode most fish use.

    `envelope` is the whole story. It controls how far forward the wave reaches:
    1.0 undulates end to end like an eel, 4.0 confines everything to the tail
    like a tuna whose body is effectively a rigid spear. Between those two sit
    most reef fish.

    A rigid swing is applied underneath so the fish also moves as a solid body
    rather than only rippling in place.
    """
    def displace(u, v):
        dx, dy = rigid_offset(u, v, swing * math.sin(beat * phase), pivot=(pivot_u, 0.5))
        dy += bob * math.sin(beat * phase + 0.9)
        dy += amplitude * (u ** envelope) * math.sin(beat * phase + u * waves * 2 * math.pi)
        return dx, dy

    return mesh_warp(base, displace, cells=28)


def silhouette_extents(image, samples=96):
    """Top and bottom of the sprite for each of `samples` columns, normalised.

    Used to find the body's outline. Fins are the outline - so motion aimed at
    fins has to follow the actual silhouette rather than a rectangle guessed in
    advance, which on a deep-bodied fish just lands on the belly and dents it.
    """
    # Cached on the image itself. Keying a dict by id() would be a trap: CPython
    # reuses ids once an object is collected, so one fish could be handed
    # another's silhouette.
    cached = getattr(image, "_extents", None)
    if cached and cached[0] == samples:
        return cached[1]

    width, height = image.size
    alpha = image.getchannel("A").load()
    tops, bottoms = [], []
    for i in range(samples):
        x = min(width - 1, int((i + 0.5) * width / samples))
        column = [y for y in range(0, height, 2) if alpha[x, y] > 25]
        if column:
            tops.append(min(column) / height)
            bottoms.append(max(column) / height)
        else:
            tops.append(None)
            bottoms.append(None)
    image._extents = (samples, (tops, bottoms))
    return tops, bottoms


def frame_mpf(base, phase, swing=1.5, bob=2.8, tail_amp=3.5, tail_beat=1,
              pectoral_amp=3.6, pectoral_beat=3, pectoral_span=(0.26, 0.58),
              median_amp=0.0, median_beat=2, margin=0.22):
    """Median- and paired-fin swimming: the body stays stiff, fins do the work.

    Wrasses, parrotfish, tangs and angelfish row with their pectorals and hold
    the body almost straight; triggerfish instead ripple the dorsal and anal
    fins. Both are expressed here - `pectoral_amp` for the rowers, `median_amp`
    for the ripplers - because in both cases the body itself barely bends.

    Fin movement is applied near the silhouette edge rather than inside a fixed
    box: `margin` is how far in from the outline counts as fin, as a fraction of
    the body's depth at that point. Deep in the body the weight falls to zero,
    so the belly never gets pushed around.
    """
    tops, bottoms = silhouette_extents(base)
    samples = len(tops)
    pu0, pu1 = pectoral_span

    def edge_weight(u, v):
        """1 at the silhouette's top/bottom edge, 0 deep inside the body."""
        i = min(samples - 1, max(0, int(u * samples)))
        top, bottom = tops[i], bottoms[i]
        if top is None or bottom - top < 1e-3:
            return 0.0, 0.0
        depth = bottom - top
        upper = 1.0 - smoothstep(0.0, margin, (v - top) / depth)
        lower = 1.0 - smoothstep(0.0, margin, (bottom - v) / depth)
        return max(0.0, upper), max(0.0, lower)

    def displace(u, v):
        dx, dy = rigid_offset(u, v, swing * math.sin(phase), pivot=(0.30, 0.50))
        dy += bob * math.sin(phase + 0.5)

        upper, lower = edge_weight(u, v)

        # the tail still contributes, but as a trailing rudder
        tail = smoothstep(0.70, 1.0, u)
        dy += tail_amp * tail * math.sin(tail_beat * phase + 0.4)

        if pectoral_amp:
            # pectorals sit low on the flank, just behind the head
            span = smoothstep(pu0, pu0 + 0.07, u) * (1.0 - smoothstep(pu1 - 0.07, pu1, u))
            fan = span * lower
            dy += pectoral_amp * fan * math.sin(pectoral_beat * phase)
            dx += pectoral_amp * 0.6 * fan * math.sin(pectoral_beat * phase + 1.5)

        if median_amp:
            # dorsal above and anal below, travelling tail-ward in antiphase
            body = smoothstep(0.20, 0.36, u)
            dy += median_amp * upper * body * math.sin(median_beat * phase + u * 6.0)
            dy += median_amp * lower * body * math.sin(median_beat * phase + u * 6.0 + math.pi)

        return dx, dy

    return mesh_warp(base, displace, cells=30)


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


# Each profile is a frame function plus its parameters. Assignments below follow
# how these animals actually swim - the classification is real biomechanics, not
# invention - though at ~64px in the tank the coarse groups read far more
# clearly than the fine distinctions between them.
PROFILES = {
    # --- body and caudal fin: the wave reaches progressively further forward ---
    "thunniform":     (frame_bcf, dict(amplitude=6.5, envelope=4.2, waves=0.55,
                                       beat=1, swing=1.5, pivot_u=0.16, bob=1.0)),
    "carangiform":    (frame_bcf, dict(amplitude=9.0, envelope=2.6, waves=0.95,
                                       beat=1, swing=2.0, pivot_u=0.22, bob=1.4)),
    "subcarangiform": (frame_bcf, dict(amplitude=7.5, envelope=1.9, waves=1.15,
                                       beat=2, swing=2.2, pivot_u=0.26, bob=1.6)),
    "anguilliform":   (frame_bcf, dict(amplitude=7.5, envelope=1.0, waves=1.75,
                                       beat=1, swing=1.0, pivot_u=0.38, bob=1.2)),
    # A uniform bob applies equally to head and tail, so keep it small here or
    # it drowns out the tail beat on these big slow fish.
    "slow_cruise":    (frame_bcf, dict(amplitude=7.0, envelope=2.8, waves=0.6,
                                       beat=1, swing=1.3, pivot_u=0.16, bob=1.0)),

    # --- median and paired fins: body stiff, fins doing the work ---
    "labriform":      (frame_mpf, dict(pectoral_amp=4.2, pectoral_beat=3,
                                       median_amp=0.0, tail_amp=3.2, swing=1.5, bob=3.0)),
    "balistiform":    (frame_mpf, dict(pectoral_amp=1.0, pectoral_beat=2,
                                       median_amp=5.0, median_beat=2, margin=0.26,
                                       tail_amp=2.2, swing=1.1, bob=2.6)),

    # --- one-off shapes that none of the above describe ---
    "veil":   (frame_veil, {}),
    "rigid":  (frame_rigid_fins, {}),
    "shrimp": (frame_shrimp, {}),
    "sway":   (frame_sway, {}),
}

# Artwork that arrived facing right. The app assumes fish face left and mirrors
# them for rightward travel, so these are flipped before framing - otherwise the
# tail wave lands on the head and they swim backwards in the tank.
MIRROR = {"cherry_shrimp", "blue_hippo_tang"}

# Anything unlisted falls back to DEFAULT_PROFILE.
DEFAULT_PROFILE = "carangiform"

MOTION = {
    # rigid-bodied speed: only the tail moves
    "tuna": "thunniform",
    "swordfish": "thunniform",
    "lost_shark": "thunniform",

    # large and unhurried
    "mega_mouth_shark": "slow_cruise",
    "coelacanth": "slow_cruise",
    "opah": "slow_cruise",

    # steady cruisers, wave over the rear third
    "sardine": "carangiform",
    "squirrelfish": "carangiform",

    # small and quick, wave over the rear half, twice per cycle
    "devil_pupfish": "subcarangiform",
    "florida_flag_fish": "subcarangiform",
    "long_finned_zebra_dania": "subcarangiform",
    "pictus_catfish": "subcarangiform",

    # juvenile sweetlips genuinely undulate end to end
    "ribboned_sweetlips": "anguilliform",

    # reef fish that row with their pectorals and hold the body straight
    "parrotfish": "labriform",
    "green_bird_wrasse": "labriform",
    "blue_hippo_tang": "labriform",
    "longnose_butterfly_fish": "labriform",
    "peppermint_angelfish": "labriform",
    "royal_gramma": "labriform",
    "coral_grouper": "labriform",

    # triggerfish ripple the dorsal and anal fins instead
    "picasso_triggerfish": "balistiform",

    # shapes of their own
    "betta_fish": "veil",
    "pufferfish": "rigid",
    "cherry_shrimp": "shrimp",
    "seahorse": "sway",
}


def build_sheet(base, profile=DEFAULT_PROFILE):
    make_frame, options = PROFILES[profile]
    sheet = Image.new("RGBA", (SHEET, SHEET), (0, 0, 0, 0))
    for i in range(FRAMES):
        cell = make_frame(base, 2 * math.pi * i / FRAMES, **options)
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
        if fish_id in MIRROR:
            source = source.transpose(Image.FLIP_LEFT_RIGHT)

        # Hand-drawn sheets stay untouched
        if source_path == sheet_path and is_grid(source):
            already.append(fish_id)
            continue

        motion = MOTION.get(fish_id, DEFAULT_PROFILE)
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
