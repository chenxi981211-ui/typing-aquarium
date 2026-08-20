# this is the time_manager.py file

import calendar
import json
import os
import time
import random
import tempfile
from datetime import datetime, timedelta

from paths import data_path, save_file, is_demo

# Recording tuning, active only when AQUARIUM_SAVE is set. Normal play waits 60
# seconds of typing and then wins a coin flip; on camera that means long takes
# and half of them ending in nothing.
DEMO_SPAWN_SECONDS = 12.0
DEMO_FISH_ENV = "AQUARIUM_DEMO_FISH"


# The logical day rolls over at 2am, so "today" runs 2am -> 1am next morning.
DAY_START_HOUR = 2

# How many fish swim at once. The tank is 354x275 with 64px sprites, so much
# beyond this stops reading as an aquarium and starts reading as a shoal.
TANK_CAPACITY = 8

# A day needs more than this many characters to count towards a streak.
STREAK_MIN_CHARS = 100

# A gap longer than this ends the current sitting at the keyboard.
SESSION_GAP = 120.0

# Gaps up to this count as still typing, for the average-speed measure. Long
# enough to cover a pause mid-sentence, short enough that thinking time and
# breaks are excluded - the figure is speed while typing, not output per hour.
TYPING_GAP = 3.0

DEFAULT_SETTINGS = {
    "tank_background": "aquarium_background.png",
    "notify_new_fish": True,
    "notify_daily_reminder": False,
    "master_volume": 70,
    # Off by default - unrequested audio from a background app is the fastest
    # way to get it quit.
    "music_enabled": False,
    "music_volume": 35,
    "sound_notification": True,
    "sound_effects": True,
}

# Named stretches of the day, as clock hours. A logical day runs 2am to 2am,
# so a single day's hours read 2,3,...,23,0,1 - which is why night owns both
# the small hours at the start and the late hours at the end.
#
# The old day_night pair split the clock in half and qualified the moment you
# were simply awake. These are narrower and have to be earned inside the window.
TIME_WINDOWS = {
    "dawn": (5, 6, 7),
    "day": (8, 9, 10, 11, 12, 13, 14, 15, 16, 17),
    "evening": (18, 19, 20, 21),
    "night": (22, 23, 0, 1, 2, 3, 4),
}

WINDOW_LABELS = {
    "dawn": "at dawn, before 8am",
    "day": "during the day, 8am to 6pm",
    "evening": "in the evening, 6pm to 10pm",
    "night": "at night, after 10pm",
}

# Stats that describe today only, and the value they reset to at 2am.
DAILY_STATS = {
    "total_chars_today": 0,
    "total_active_time": 0.0,
    "highest_wpm_today": 0,
    "longest_focus_today": 0.0,
    # Best sustained fast stretch today, in minutes. Kept here rather than on
    # the spawn cycle so a burst earned at 10am still counts at 4pm.
    "longest_burst_today": 0.0,
    "wpm_sample_total": 0,
    "wpm_sample_count": 0,
    "typing_seconds_today": 0.0,
    # The tank shows what today's typing has earned; the inventory keeps the
    # permanent record. This is the list the tank is built from.
    "caught_today": [],
}


class UnlockManager:
    def __init__(self, fish_json_path="fish.json", save_json_path=None):
        # fish.json is bundled and read-only, so a relative path is fine; the
        # save file has to land somewhere writable, which is not the bundle.
        if save_json_path is None:
            save_json_path = save_file()
        self.fish_json_path = fish_json_path
        self.save_json_path = save_json_path

        self.fish_definitions = self._load_json(self.fish_json_path, [])
        self.user_data = self._load_initial_user_data()

        # Time tracking attributes - ALL initialized here
        self.last_keystroke_time = None
        self.last_focus_keystroke = None
        self.last_burst_keystroke = None

        self.spawn_timer_threshold = 60.0  # 60 seconds for spawn checks
        self.grace_period = 30.0  # 30 seconds grace for focus timer
        self._spawn_timer = 0.0

        # Burst tracking
        self.burst_speed_threshold = 50
        self.burst_start_time = None
        self.longest_burst_minutes_this_cycle = 0.0
        self.burst_grace_period = 10.0  # 10 seconds max gap for burst

        # Focus tracking
        self.current_focus_minutes = 0.0
        self.focus_grace_period = 60.0  # 60 seconds max gap for focus

        # Length of the current unbroken typing session, for longest_focus_today
        self.current_session_seconds = 0.0

        # Set by the app so a stats reset can clear live readings on the spot
        self.on_reset = None

        # Recording mode: a short, certain unlock of a chosen fish
        self.demo_fish = None
        if is_demo():
            self.spawn_timer_threshold = DEMO_SPAWN_SECONDS
            self.demo_fish = os.environ.get(DEMO_FISH_ENV) or None

        # Current spawn pool
        self.current_spawn_pool = []
        self.reset_spawn_pool()

    def _load_json(self, path, default):
        """Load a JSON file, keeping a damaged one instead of overwriting it.

        A save file that will not parse used to raise straight out of startup.
        Starting fresh is the only way to carry on, but doing that silently
        would let the next autosave write over the damaged file and destroy any
        chance of getting the history back - so it is moved aside first.
        """
        if not os.path.exists(path):
            return default

        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            salvage = f"{path}.corrupt-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                os.replace(path, salvage)
                print(f"⚠️  {os.path.basename(path)} was unreadable ({exc}).")
                print(f"⚠️  Kept a copy at {salvage} - starting from defaults.")
            except OSError:
                print(f"⚠️  {os.path.basename(path)} is unreadable and could not be moved aside.")
            return default

    def _load_initial_user_data(self):
        default_data = {
            "total_chars_today": 0,
            "total_active_time": 0.0,
            "highest_wpm_today": 0,
            "streak_days": 0,
            "owned_fish": ["guppy"],
            "viewed_fish": [],
            "favorite_fish": [],
            "discovery_dates": {},
            "last_saved_date": self._get_logical_date_string(),
        }
        data = self._load_json(self.save_json_path, default_data)

        # Ensure all keys exist
        for key, value in DAILY_STATS.items():
            data.setdefault(key, value)
        data.setdefault("total_chars_all_time", 0)
        data.setdefault("highest_wpm_all_time", 0)
        data.setdefault("longest_focus_all_time", 0.0)
        data.setdefault("hourly_activity", {})
        data.setdefault("daily_history", {})

        # Settings, with any missing key falling back to its default
        settings = dict(DEFAULT_SETTINGS)
        settings.update(data.get("settings", {}))
        data["settings"] = settings

        saved_date = data.get("last_saved_date", "")
        current_logical_date = self._get_logical_date_string()

        print(f"📅 Saved date: '{saved_date}'")
        print(f"📅 Current date: '{current_logical_date}'")
        print(f"📊 Saved chars: {data.get('total_chars_today', 0)}")

        if saved_date != current_logical_date:
            self._archive_day(data, saved_date)
            self._reset_daily_stats(data, current_logical_date)

        # Always, not only on a new day: the stored numbers may be stale from a
        # session that spanned midnight without ever passing through here.
        self._recompute_all_time(data)
        self._recompute_streak(data)

        return data

    def _archive_day(self, data, date_string):
        """Snapshot a finished day into daily_history so the charts have history."""
        if not date_string or data.get("total_chars_today", 0) <= 0:
            return

        samples = data.get("wpm_sample_count", 0)
        avg_wpm = int(data.get("wpm_sample_total", 0) / samples) if samples else 0

        data.setdefault("daily_history", {})[date_string] = {
            "chars": data.get("total_chars_today", 0),
            "focus_seconds": int(data.get("total_active_time", 0.0)),
            "avg_wpm": avg_wpm,
            "highest_wpm": data.get("highest_wpm_today", 0),
            "longest_focus": int(data.get("longest_focus_today", 0.0)),
        }
        print(f"📆 Archived {date_string} to daily_history")

    def _reset_daily_stats(self, data, current_logical_date):
        for key, value in DAILY_STATS.items():
            # copy, or every day would share one list
            data[key] = list(value) if isinstance(value, list) else value
        data["hourly_activity"] = {}
        data["last_saved_date"] = current_logical_date

    def _recompute_all_time(self, data=None):
        """Reconcile the all-time character count against the daily record.

        It was a running counter and nothing else, so any day it did not see -
        history recovered from logs, a save restored from backup, a reset - was
        simply absent from it forever. The result was an "all time" figure of a
        few thousand sitting under a history holding ninety.

        Taking the larger of the counter and the record keeps whichever is more
        complete: the sum repairs a counter that missed days, and the counter
        survives a history that has been pruned.
        """
        data = self.user_data if data is None else data
        recorded = sum(day.get("chars", 0) for day in data.get("daily_history", {}).values())
        recorded += data.get("total_chars_today", 0)

        data["total_chars_all_time"] = max(data.get("total_chars_all_time", 0), recorded)
        return data["total_chars_all_time"]

    def _recompute_streak(self, data=None):
        """Derive the streak from the record, rather than counting it up.

        It used to be a stored number nudged in one place only: the launch path.
        Two things went wrong with that. An app left open - which is how this one
        is meant to run - never revisited it, so somebody typing every day for a
        week still showed the streak they had when they last quit, and the fish
        gated on streaks could not be earned at all. And returning after a break
        set it to 1 before a single key had been pressed.

        Counting back through daily_history each time cannot drift: it is a
        reading of what actually happened, so it self-corrects however the app
        is used.
        """
        data = self.user_data if data is None else data
        history = data.get("daily_history", {})

        day = datetime.strptime(self._get_logical_date_string(), "%Y-%m-%d")
        # Today counts only once enough has been typed. Before that the run
        # standing behind it is still shown, so the number does not drop to zero
        # every morning and climb back an hour later.
        streak = 1 if data.get("total_chars_today", 0) > STREAK_MIN_CHARS else 0

        day -= timedelta(days=1)
        while True:
            entry = history.get(day.strftime("%Y-%m-%d"))
            if not entry or entry.get("chars", 0) <= STREAK_MIN_CHARS:
                break
            streak += 1
            day -= timedelta(days=1)

        data["streak_days"] = streak
        return streak

    def _get_logical_date_string(self):
        now = datetime.now()
        if now.hour < 2:
            now = now - timedelta(days=1)
        return now.strftime("%Y-%m-%d")

    def save_state(self):
        """Write the save file atomically.

        Writing straight into save.json means any interruption - a crash, a
        force quit, or a second copy of the app reading the file halfway
        through - leaves truncated JSON behind, and the next start silently
        falls back to defaults and loses every day of history. Building the new
        file alongside and renaming it over the old one makes the swap atomic,
        so the save is either the old version or the new one, never a torn mix.
        """
        self.user_data["last_saved_date"] = self._get_logical_date_string()

        directory = os.path.dirname(os.path.abspath(self.save_json_path))
        os.makedirs(directory, exist_ok=True)

        handle, temp_path = tempfile.mkstemp(dir=directory, prefix=".save-", suffix=".json")
        try:
            with os.fdopen(handle, "w") as f:
                json.dump(self.user_data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.save_json_path)
        except BaseException:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def register_activity(self):
        current_time = time.time()
        current_logical_date = self._get_logical_date_string()

        # Check for day reset
        if self.user_data["last_saved_date"] != current_logical_date:
            self._archive_day(self.user_data, self.user_data["last_saved_date"])
            self._reset_daily_stats(self.user_data, current_logical_date)
            self.current_session_seconds = 0.0
            self._recompute_all_time()
            self._recompute_streak()

        self.user_data["total_chars_today"] += 1
        self.user_data["total_chars_all_time"] = self.user_data.get("total_chars_all_time", 0) + 1

        # The one keystroke that makes today count
        if self.user_data["total_chars_today"] == STREAK_MIN_CHARS + 1:
            self._recompute_streak()

        # Per-hour buckets for the "Today by Hour" chart
        hour_key = str(datetime.now().hour)
        hourly = self.user_data.setdefault("hourly_activity", {})
        hourly[hour_key] = hourly.get(hour_key, 0) + 1

        # Longest unbroken session today (a gap over the grace period starts a new one)
        if self.last_keystroke_time is not None and (current_time - self.last_keystroke_time) <= self.grace_period:
            self.current_session_seconds += current_time - self.last_keystroke_time
        else:
            self.current_session_seconds = 0.0

        if self.current_session_seconds > self.user_data.get("longest_focus_today", 0.0):
            self.user_data["longest_focus_today"] = self.current_session_seconds
        if self.current_session_seconds > self.user_data.get("longest_focus_all_time", 0.0):
            self.user_data["longest_focus_all_time"] = self.current_session_seconds

        # Track total active time - ONLY add time when actively typing (gap less than 1 second)
        if self.last_keystroke_time is not None:
            elapsed = current_time - self.last_keystroke_time

            # Focus duration is how long the user has been at the keyboard, so
            # short thinking pauses count; only a real break ends the sitting.
            # Measuring it on a 1-second gap, as before, reported a couple of
            # minutes for a whole day's work because it was really just adding
            # up the time between individual keystrokes.
            if elapsed <= SESSION_GAP:
                self.user_data["total_active_time"] += elapsed

            # Time spent actually typing, for the average-speed figure.
            if elapsed <= TYPING_GAP:
                self.user_data["typing_seconds_today"] = (
                    self.user_data.get("typing_seconds_today", 0.0) + elapsed)

            # The spawn timer keeps the strict rule - it paces fish unlocks and
            # loosening it here would make them arrive far too quickly.
            if elapsed <= 1.0:
                self._spawn_timer += elapsed

        # Track focus time for fish unlocks (30 second grace period - this is fine)
        if self.last_focus_keystroke is not None:
            elapsed = current_time - self.last_focus_keystroke
            if elapsed <= self.focus_grace_period:
                self.current_focus_minutes += elapsed / 60.0
            else:
                self.current_focus_minutes = 0.0
        else:
            self.current_focus_minutes = 0.0
        self.last_focus_keystroke = current_time

        # Burst is tracked in update_qualifiers instead, where the live WPM
        # reading is available - it is a speed condition, not a continuity one.

        self.last_keystroke_time = current_time

        # Check spawn milestone
        milestone_reached = False
        if self._spawn_timer >= self.spawn_timer_threshold:
            self._spawn_timer -= self.spawn_timer_threshold
            milestone_reached = True

        return milestone_reached

    def chars_in_window(self, window):
        """Characters typed today inside a named stretch of the day.

        Read straight off hourly_activity, which already counts per clock hour
        and clears at the 2am rollover, so no extra bookkeeping is needed.
        """
        hours = TIME_WINDOWS.get(window, ())
        hourly = self.user_data.get("hourly_activity", {})
        return sum(hourly.get(str(h), 0) for h in hours)

    def _track_burst(self, current_wpm):
        """Time spent held above the burst speed, as today's best unbroken run.

        The detail page promises "hold 50 WPM or more", so this has to actually
        watch the speed. It previously only measured typing continuity and
        ignored burst_speed_threshold entirely, which made burst a stricter
        copy of focus rather than a condition of its own.
        """
        now = time.time()

        # A pause long enough to break the run ends it. Without this an idle
        # spell would be counted as burst time, since nothing runs while idle.
        idle = self.last_burst_keystroke is not None and (now - self.last_burst_keystroke) > self.burst_grace_period
        self.last_burst_keystroke = now

        if current_wpm < self.burst_speed_threshold or idle:
            self.burst_start_time = None
            self.longest_burst_minutes_this_cycle = 0.0
            return

        if self.burst_start_time is None:
            self.burst_start_time = now
            return

        run = (now - self.burst_start_time) / 60.0
        self.longest_burst_minutes_this_cycle = max(self.longest_burst_minutes_this_cycle, run)
        if run > self.user_data.get("longest_burst_today", 0.0):
            self.user_data["longest_burst_today"] = run

    def update_qualifiers(self, live_typing_stats):
        current_wpm = live_typing_stats.get("wpm", 0)
        self._track_burst(current_wpm)

        # Update highest WPM
        if current_wpm > self.user_data["highest_wpm_today"]:
            self.user_data["highest_wpm_today"] = current_wpm
            print(f"📈 New highest WPM: {current_wpm}")

        if current_wpm > self.user_data.get("highest_wpm_all_time", 0):
            self.user_data["highest_wpm_all_time"] = current_wpm

        # Sample live WPM so Statistics can show a daily average.
        # Only non-zero samples count, otherwise idle time drags the average to 0.
        if current_wpm > 0:
            self.user_data["wpm_sample_total"] = self.user_data.get("wpm_sample_total", 0) + current_wpm
            self.user_data["wpm_sample_count"] = self.user_data.get("wpm_sample_count", 0) + 1

        focus_minutes_today = self.user_data.get("longest_focus_today", 0.0) / 60.0
        burst_minutes_today = self.user_data.get("longest_burst_today", 0.0)

        # Qualification loop
        for fish in self.fish_definitions:
            if fish["id"] in self.current_spawn_pool:
                continue

            u_type = fish["unlock"]["type"]
            threshold = fish["unlock"]["value"]
            qualified = False

            if u_type == "char_count" and self.user_data["total_chars_today"] >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (char_count: {self.user_data['total_chars_today']} >= {threshold})")
            # The one condition that never resets - a running lifetime total
            # rather than anything you can earn inside a single day.
            elif u_type == "total_chars" and self.user_data.get("total_chars_all_time", 0) >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (all-time: {self.user_data['total_chars_all_time']} >= {threshold})")
            elif u_type == "typing_speed" and self.user_data["highest_wpm_today"] >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (typing_speed: {self.user_data['highest_wpm_today']} >= {threshold})")
            # Focus and burst read today's best, not the current spawn cycle's.
            # reset_spawn_pool() runs every 60 seconds of typing and used to
            # zero both counters, so neither could ever climb past ~1 minute
            # and every fish gated on them was uncatchable.
            elif u_type == "focus" and focus_minutes_today >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (focus: {focus_minutes_today:.1f} mins >= {threshold})")
            elif u_type == "burst" and burst_minutes_today >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (burst: {burst_minutes_today:.1f} mins >= {threshold})")
            elif u_type == "streak" and self.user_data["streak_days"] >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (streak: {self.user_data['streak_days']} days >= {threshold})")
            elif u_type == "time_window":
                window = fish["unlock"].get("window", "day")
                typed = self.chars_in_window(window)
                if typed >= threshold:
                    qualified = True
                    print(f"🔓 {fish['id']} qualified! ({window}: {typed} chars >= {threshold})")
            # day_night is gone: it halved the clock and qualified the moment
            # you were awake. time_window replaces it.

            if qualified:
                self.current_spawn_pool.append(fish["id"])
                print(f"   📋 {fish['id']} added to spawn pool. Pool size: {len(self.current_spawn_pool)}")

    def check_ten_minute_milestone(self, force_spawn=False):
        print(f"\n🎲 SPAWN CHECK - Pool size: {len(self.current_spawn_pool)}")
        print(f"   Pool contents: {self.current_spawn_pool}")

        if not force_spawn and not is_demo() and random.random() > 0.50:
            print(f"   ❌ Coin flip failed (50% chance)")
            self.reset_spawn_pool()
            return "coin_flip_failed"

        eligible_fish = []
        rarity_weights = []

        for fish in self.fish_definitions:
            if self.user_data["owned_fish"].count(fish["id"]) >= fish["max_owned"]:
                continue
            if fish["id"] in self.current_spawn_pool:
                eligible_fish.append(fish["id"])
                rarity_weights.append(fish["rarity"])

        if not eligible_fish:
            print(f"   ❌ No eligible fish in pool")
            self.reset_spawn_pool()
            return "pool_empty"

        if self.demo_fish and self.demo_fish in eligible_fish:
            selected_fish = self.demo_fish
        else:
            selected_fish = random.choices(eligible_fish, weights=rarity_weights, k=1)[0]

        # Record discovery date if this is the first time
        if "discovery_dates" not in self.user_data:
            self.user_data["discovery_dates"] = {}

        if selected_fish not in self.user_data["discovery_dates"]:
            self.user_data["discovery_dates"][selected_fish] = datetime.now().strftime("%Y-%m-%d")

        self.user_data["owned_fish"].append(selected_fish)
        self.user_data.setdefault("caught_today", []).append(selected_fish)
        self.save_state()
        self.reset_spawn_pool()
        return selected_fish

    def reset_spawn_pool(self):
        self.current_spawn_pool = []
        # Deliberately does not touch burst_start_time or the focus timer: this
        # runs every 60 seconds of typing, so clearing them capped both at about
        # a minute and left every focus and burst fish permanently unreachable.
        self.longest_burst_minutes_this_cycle = 0.0

        for fish in self.fish_definitions:
            if fish["unlock"]["type"] == "random":
                self.current_spawn_pool.append(fish["id"])

        # The fish staged for the camera goes in regardless of its condition -
        # waiting on a 12-minute focus run mid-shoot is not workable.
        demo_fish = getattr(self, "demo_fish", None)
        if demo_fish and demo_fish not in self.current_spawn_pool:
            self.current_spawn_pool.append(demo_fish)

        print(f"🔄 Spawn pool reset. Random fish available: {self.current_spawn_pool}")

    @property
    def total_active_time(self):
        return self.user_data.get("total_active_time", 0.0)

    @property
    def total_chars_today(self):
        return self.user_data.get("total_chars_today", 0)

    @property
    def highest_wpm_today(self):
        return self.user_data.get("highest_wpm_today", 0)

    @property
    def caught_today(self):
        return self.user_data.get("caught_today", [])

    def tank_lineup(self, capacity=TANK_CAPACITY):
        """Which fish are swimming today.

        The tank never empties - fish you have caught are yours - but it also
        cannot hold the whole collection, so it is composed rather than dumped:

          1. favourites, because that is an explicit "keep this one visible"
          2. today's catches, so the day's typing visibly changes the tank
          3. a rotating cast of everything else, to fill the remaining room

        The rotation is seeded on the date, so it is stable all day and differs
        tomorrow. That is what keeps the tank feeling alive without anything
        ever being taken away.
        """
        owned = self.user_data.get("owned_fish", [])
        seen, unique = set(), []
        for fish_id in owned:
            if fish_id not in seen:
                seen.add(fish_id)
                unique.append(fish_id)

        lineup = []

        def add(fish_id):
            if fish_id in unique and fish_id not in lineup and len(lineup) < capacity:
                lineup.append(fish_id)

        for fish_id in self.user_data.get("favorite_fish", []):
            add(fish_id)
        for fish_id in self.caught_today:
            add(fish_id)

        remaining = [f for f in unique if f not in lineup]
        random.Random(self._logical_today().toordinal()).shuffle(remaining)
        for fish_id in remaining:
            add(fish_id)

        return lineup

    @property
    def total_chars_all_time(self):
        return self.user_data.get("total_chars_all_time", 0)

    @property
    def highest_wpm_all_time(self):
        return self.user_data.get("highest_wpm_all_time", 0)

    @property
    def longest_focus_today(self):
        return self.user_data.get("longest_focus_today", 0.0)

    @property
    def avg_wpm_today(self):
        """Average speed over the time actually spent typing.

        Averaging the live WPM readings understated this badly. That reading
        comes from a 10-second rolling window, so every pause produces a run of
        small non-zero samples as the window drains, and those drag the mean
        down - the figure ended up nearer a third of a realistic pace.

        Dividing words by typing time instead ignores the gaps entirely.
        """
        typing_seconds = self.user_data.get("typing_seconds_today", 0.0)
        if typing_seconds < 20:
            return 0        # too little to average meaningfully yet

        words = self.user_data.get("total_chars_today", 0) / 5.0
        return int(words / (typing_seconds / 60.0))

    def get_hourly_activity(self):
        """Chars typed today per hour, in logical-day order.

        The day rolls over at 2am, so the buckets that belong to "today" run
        2am -> 1am. Listing them 0..23 put the small hours at the wrong end of
        the chart, ahead of a morning that came before them.
        """
        hourly = self.user_data.get("hourly_activity", {})
        order = [(DAY_START_HOUR + i) % 24 for i in range(24)]
        return [(hour, hourly.get(str(hour), 0)) for hour in order]

    def _logical_today(self):
        """Today under the app's 2am day boundary, as a date."""
        now = datetime.now()
        if now.hour < DAY_START_HOUR:
            now = now - timedelta(days=1)
        return now.date()

    def get_calendar_range(self, period="week"):
        """A whole calendar week or month as [(date, stats), ...].

        A rolling "last 7 days" window makes it impossible to compare like for
        like, so this returns real calendar periods: Monday to Sunday, or the
        1st to the end of the month. Days that have not happened yet are
        included with zeros so the week keeps its shape.
        """
        today = self._logical_today()

        if period == "week":
            start = today - timedelta(days=today.weekday())   # Monday
            length = 7
        else:
            start = today.replace(day=1)
            length = calendar.monthrange(today.year, today.month)[1]

        history = self.user_data.get("daily_history", {})
        live = {
            "chars": self.total_chars_today,
            "focus_seconds": int(self.total_active_time),
            "avg_wpm": self.avg_wpm_today,
            "highest_wpm": self.highest_wpm_today,
            "longest_focus": int(self.longest_focus_today),
        }
        empty = {"chars": 0, "focus_seconds": 0, "avg_wpm": 0,
                 "highest_wpm": 0, "longest_focus": 0}

        result = []
        for offset in range(length):
            date = start + timedelta(days=offset)
            if date == today:
                stats = live            # today is not archived yet
            elif date > today:
                stats = empty           # hasn't happened
            else:
                stats = history.get(date.strftime("%Y-%m-%d"), empty)
            result.append((date, stats))
        return result

    # ===== Settings =====

    def get_setting(self, key):
        return self.user_data.get("settings", {}).get(key, DEFAULT_SETTINGS.get(key))

    def set_setting(self, key, value):
        self.user_data.setdefault("settings", dict(DEFAULT_SETTINGS))[key] = value
        self.save_state()

    def reset_stats(self):
        """Wipe all progress and start over. Settings themselves are kept."""
        self._reset_daily_stats(self.user_data, self._get_logical_date_string())
        self.user_data["total_chars_all_time"] = 0
        self.user_data["highest_wpm_all_time"] = 0
        self.user_data["longest_focus_all_time"] = 0.0
        self.user_data["streak_days"] = 0
        self.user_data["daily_history"] = {}
        self.user_data["owned_fish"] = ["guppy"]
        self.user_data["viewed_fish"] = []
        self.user_data["favorite_fish"] = []
        self.user_data["discovery_dates"] = {}
        self.user_data["caught_today"] = []
        self.current_session_seconds = 0.0
        self.current_focus_minutes = 0.0
        self.longest_burst_minutes_this_cycle = 0.0
        self.burst_start_time = None
        self.last_keystroke_time = None
        self.last_focus_keystroke = None
        self.last_burst_keystroke = None
        self.reset_spawn_pool()
        self.save_state()

        # Lets the app clear the live speed reading and repaint the stat cards
        # straight away. Without it the old WPM stayed on screen until the next
        # keystroke happened to overwrite it.
        if self.on_reset is not None:
            self.on_reset()
        print("🧹 All stats reset")