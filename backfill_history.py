# backfill_history.py
"""Recover past daily totals from the log files into save.json.

daily_history only starts filling from the first day rollover after the feature
existed, so the Typing Activity chart had nothing to show for earlier days. The
logs do have the numbers though: every startup records which day the saved
counters belong to and what they were.

    ~/.venvs/aquarium/bin/python backfill_history.py           # report only
    ~/.venvs/aquarium/bin/python backfill_history.py --write

Only the character count is recoverable - the logs never carried focus time or
WPM - so those stay at zero for backfilled days rather than being invented.
Existing entries are never overwritten.
"""

import argparse
import collections
import glob
import json
import re
from datetime import datetime, timedelta

SAVE = "save.json"
LOGS = "logs/*.log"
DAY_START_HOUR = 2

SAVED_DATE = re.compile(r"Saved date: '(\d{4}-\d{2}-\d{2})'")
SAVED_CHARS = re.compile(r"Saved chars: (\d+)")


def logical_today():
    now = datetime.now()
    if now.hour < DAY_START_HOUR:
        now -= timedelta(days=1)
    return now.strftime("%Y-%m-%d")


def scan_logs():
    """Highest character count seen for each day, across every log file."""
    totals = collections.defaultdict(int)
    for path in sorted(glob.glob(LOGS)):
        try:
            text = open(path, errors="ignore").read()
        except OSError:
            continue
        day, chars = SAVED_DATE.search(text), SAVED_CHARS.search(text)
        if day and chars:
            totals[day.group(1)] = max(totals[day.group(1)], int(chars.group(1)))
    return totals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write into save.json")
    args = parser.parse_args()

    save = json.load(open(SAVE))
    history = save.setdefault("daily_history", {})
    today = logical_today()
    recovered = scan_logs()

    added, skipped = [], []
    for day in sorted(recovered):
        chars = recovered[day]
        if not chars:
            continue
        if day >= today:
            skipped.append((day, "still in progress"))
            continue
        if day in history:
            skipped.append((day, "already recorded"))
            continue
        history[day] = {
            "chars": chars,
            "focus_seconds": 0,
            "avg_wpm": 0,
            "highest_wpm": 0,
            "longest_focus": 0,
        }
        added.append((day, chars))

    for day, chars in added:
        print(f"  + {day}  {chars:>7,} chars")
    for day, why in skipped:
        print(f"  - {day}  skipped ({why})")

    if args.write:
        json.dump(save, open(SAVE, "w"), indent=4)
        print(f"\nWROTE {len(added)} days into {SAVE}")
    else:
        print(f"\nDRY RUN - {len(added)} days would be added; rerun with --write")


if __name__ == "__main__":
    main()
