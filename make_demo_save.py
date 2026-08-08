# make_demo_save.py
"""Build a staged save file for recording video.

    ~/.venvs/aquarium/bin/python make_demo_save.py

Writes promo/demo-save.json: a collection part-way filled, a few weeks of
history, and a tank with fish already in it. A fresh install is one fish and an
empty chart, which is honest but shows nothing off.

It never touches the real save. The app reads this file only when AQUARIUM_SAVE
points at it, which is what "Demo Mode.command" does - so recording and normal
use cannot get mixed up.

Dates are written relative to whenever you run this, so the week chart is always
full and "today" always has data, however long after this was written you record.
"""

import json
import os
import random
from datetime import datetime, timedelta

OUT = os.path.join("promo", "demo-save.json")

# Exactly the five that should be swimming. Owning only these keeps the tank to
# five - tank_lineup fills any spare room from the rest of the collection, so a
# longer owned list would quietly add fish you did not ask for.
OWNED = [
    "guppy",
    "parrotfish",
    "clownfish",
    "moorish_idol",
    "dwarf_gouramis",
]

# Favourites are placed in the tank first, so listing all five pins the cast.
FAVOURITES = list(OWNED)

# Left unviewed so it carries the NEW badge in the collection on camera
CAUGHT_TODAY = ["moorish_idol"]

# Staged for the on-camera unlock. Not owned, so it arrives as a genuine catch -
# a lionfish is the most dramatic thing in the set to have swim in.
DEMO_UNLOCK = "antennata_lionfish"


def build():
    rng = random.Random(4242)
    now = datetime.now()
    today = (now - timedelta(days=1)) if now.hour < 2 else now

    history = {}
    # Four weeks back, skipping the odd day so the month view looks lived-in
    for back in range(1, 29):
        day = today - timedelta(days=back)
        chars = rng.choice([0, 1800, 3200, 4700, 6100, 7400, 9200, 11500])
        if not chars:
            continue
        history[day.strftime("%Y-%m-%d")] = {
            "chars": chars,
            "focus_seconds": int(chars / 4.2),
            "avg_wpm": rng.randint(52, 71),
            "highest_wpm": rng.randint(74, 94),
            "longest_focus": rng.randint(240, 900),
        }

    # Guarantee the current Mon-Sun week is full, whatever day it is recorded on
    for back in range(1, today.weekday() + 1):
        day = today - timedelta(days=back)
        history[day.strftime("%Y-%m-%d")] = {
            "chars": rng.choice([4200, 6800, 7400, 9775, 10786]),
            "focus_seconds": rng.randint(900, 2400),
            "avg_wpm": rng.randint(55, 70),
            "highest_wpm": rng.randint(78, 93),
            "longest_focus": rng.randint(300, 880),
        }

    # A believable day: a morning block, a lunch dip, a long afternoon
    hourly = {"8": 420, "9": 1180, "10": 1640, "11": 980, "12": 260,
              "13": 540, "14": 1720, "15": 2050, "16": 1380, "17": 610}
    chars_today = sum(hourly.values())

    return {
        "last_saved_date": today.strftime("%Y-%m-%d"),
        "total_chars_today": chars_today,
        "total_chars_all_time": 128_400,
        # 2,156 words over ~31 minutes of actual typing reads as about 68 wpm
        "typing_seconds_today": 1900.0,
        "total_active_time": 5400.0,
        "highest_wpm_today": 88,
        "highest_wpm_all_time": 96,
        "longest_focus_today": 742.0,
        "longest_focus_all_time": 1120.0,
        "longest_burst_today": 2.4,
        "wpm_sample_total": 61_000,
        "wpm_sample_count": 1000,
        "streak_days": 6,
        "owned_fish": list(OWNED),
        "favorite_fish": list(FAVOURITES),
        "viewed_fish": [f for f in OWNED if f not in CAUGHT_TODAY],
        "discovery_dates": {
            f: (today - timedelta(days=i + 2)).strftime("%Y-%m-%d")
            for i, f in enumerate(OWNED)
        },
        "caught_today": list(CAUGHT_TODAY),
        "daily_history": history,
        "hourly_activity": hourly,
        "settings": {
            # Original artwork rather than the SpongeBob theme, which is
            # recognisable enough to be a problem in a public post
            "tank_background": "aquarium_background.png",
            "notify_new_fish": True,
            "notify_daily_reminder": True,
            "master_volume": 55,
            "music_enabled": True,
            "music_volume": 70,
            "sound_notification": True,
            "sound_effects": True,
        },
    }


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = build()
    with open(OUT, "w") as handle:
        json.dump(data, handle, indent=2)

    print(f"wrote {OUT}")
    print(f"  {len(data['owned_fish'])} fish owned, {len(data['daily_history'])} days of history")
    print(f"  staged unlock: {DEMO_UNLOCK} (arrives after ~12s of typing)")
    print(f"  {data['total_chars_today']:,} characters today, {data['streak_days']}-day streak")
    print("\nrecord with:  ./'Demo Mode.command'")


if __name__ == "__main__":
    main()
