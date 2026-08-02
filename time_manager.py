# this is the time_manager.py file

import json
import os
import time
import random
from datetime import datetime, timedelta


DEFAULT_SETTINGS = {
    "tank_background": "aquarium_background.png",
    "notify_new_fish": True,
    "notify_milestones": True,
    "notify_daily_reminder": False,
    "master_volume": 70,
    "sound_notification": True,
    "sound_effects": True,
}

# Stats that describe today only, and the value they reset to at 2am.
DAILY_STATS = {
    "total_chars_today": 0,
    "total_active_time": 0.0,
    "highest_wpm_today": 0,
    "longest_focus_today": 0.0,
    "wpm_sample_total": 0,
    "wpm_sample_count": 0,
}


class UnlockManager:
    def __init__(self, fish_json_path="fish.json", save_json_path="save.json"):
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

        # Current spawn pool
        self.current_spawn_pool = []
        self.reset_spawn_pool()

    def _load_json(self, path, default):
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
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
            # New day - reset daily stats
            yesterday_logical_date = (datetime.now() - timedelta(days=1)
                                      if datetime.now().hour >= 2
                                      else datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

            if data["last_saved_date"] == yesterday_logical_date and data["total_chars_today"] > 100:
                data["streak_days"] += 1
            elif data["last_saved_date"] != yesterday_logical_date:
                data["streak_days"] = 1

            self._archive_day(data, saved_date)
            self._reset_daily_stats(data, current_logical_date)

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
            data[key] = value
        data["hourly_activity"] = {}
        data["last_saved_date"] = current_logical_date

    def _get_logical_date_string(self):
        now = datetime.now()
        if now.hour < 2:
            now = now - timedelta(days=1)
        return now.strftime("%Y-%m-%d")

    def save_state(self):
        self.user_data["last_saved_date"] = self._get_logical_date_string()
        self.user_data["total_chars_today"] = self.user_data["total_chars_today"]
        self.user_data["total_active_time"] = self.user_data["total_active_time"]
        self.user_data["highest_wpm_today"] = self.user_data["highest_wpm_today"]
        self.user_data["streak_days"] = self.user_data["streak_days"]
        self.user_data["owned_fish"] = self.user_data["owned_fish"]

        with open(self.save_json_path, "w") as f:
            json.dump(self.user_data, f, indent=4)

    def register_activity(self):
        current_time = time.time()
        current_logical_date = self._get_logical_date_string()

        # Check for day reset
        if self.user_data["last_saved_date"] != current_logical_date:
            self._archive_day(self.user_data, self.user_data["last_saved_date"])
            self._reset_daily_stats(self.user_data, current_logical_date)
            self.current_session_seconds = 0.0

        self.user_data["total_chars_today"] += 1
        self.user_data["total_chars_all_time"] = self.user_data.get("total_chars_all_time", 0) + 1

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
            # Only count time if the gap is very small (actively typing, not thinking)
            # This prevents counting pauses
            if elapsed <= 1.0:  # ← Changed from self.grace_period to 1 second
                self.user_data["total_active_time"] += elapsed
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

        # Track burst time for fish unlocks (10 second grace period)
        if self.last_burst_keystroke is not None:
            elapsed = current_time - self.last_burst_keystroke
            if elapsed <= self.burst_grace_period:
                if self.burst_start_time is None:
                    self.burst_start_time = current_time
                else:
                    current_burst_duration_mins = (current_time - self.burst_start_time) / 60.0
                    if current_burst_duration_mins > self.longest_burst_minutes_this_cycle:
                        self.longest_burst_minutes_this_cycle = current_burst_duration_mins
            else:
                self.burst_start_time = None
                self.longest_burst_minutes_this_cycle = 0.0
        else:
            self.burst_start_time = current_time
        self.last_burst_keystroke = current_time

        self.last_keystroke_time = current_time

        # Check spawn milestone
        milestone_reached = False
        if self._spawn_timer >= self.spawn_timer_threshold:
            self._spawn_timer -= self.spawn_timer_threshold
            milestone_reached = True

        return milestone_reached

    def update_qualifiers(self, live_typing_stats):
        current_wpm = live_typing_stats.get("wpm", 0)

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

        # Day/night period
        now = datetime.now()
        current_period = "night" if (now.hour >= 18 or now.hour < 2) else "day"

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
            elif u_type == "typing_speed" and self.user_data["highest_wpm_today"] >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (typing_speed: {self.user_data['highest_wpm_today']} >= {threshold})")
            elif u_type == "focus" and self.current_focus_minutes >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (focus: {self.current_focus_minutes:.1f} mins >= {threshold})")
            elif u_type == "burst" and self.longest_burst_minutes_this_cycle >= threshold:
                qualified = True
                print(
                    f"🔓 {fish['id']} qualified! (burst: {self.longest_burst_minutes_this_cycle:.1f} mins >= {threshold})")
            elif u_type == "streak" and self.user_data["streak_days"] >= threshold:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (streak: {self.user_data['streak_days']} days >= {threshold})")
            elif u_type == "day_night" and current_period == fish["unlock"]["value"]:
                qualified = True
                print(f"🔓 {fish['id']} qualified! (day_night: {current_period})")

            if qualified:
                self.current_spawn_pool.append(fish["id"])
                print(f"   📋 {fish['id']} added to spawn pool. Pool size: {len(self.current_spawn_pool)}")

    def check_ten_minute_milestone(self, force_spawn=False):
        print(f"\n🎲 SPAWN CHECK - Pool size: {len(self.current_spawn_pool)}")
        print(f"   Pool contents: {self.current_spawn_pool}")

        if not force_spawn and random.random() > 0.50:
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

        selected_fish = random.choices(eligible_fish, weights=rarity_weights, k=1)[0]

        # Record discovery date if this is the first time
        if "discovery_dates" not in self.user_data:
            self.user_data["discovery_dates"] = {}

        if selected_fish not in self.user_data["discovery_dates"]:
            self.user_data["discovery_dates"][selected_fish] = datetime.now().strftime("%Y-%m-%d")

        self.user_data["owned_fish"].append(selected_fish)
        self.save_state()
        self.reset_spawn_pool()
        return selected_fish

    def reset_spawn_pool(self):
        self.current_spawn_pool = []
        self.longest_burst_minutes_this_cycle = 0.0
        self.burst_start_time = None
        self.current_focus_minutes = 0.0

        for fish in self.fish_definitions:
            if fish["unlock"]["type"] == "random":
                self.current_spawn_pool.append(fish["id"])

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
        samples = self.user_data.get("wpm_sample_count", 0)
        if not samples:
            return 0
        return int(self.user_data.get("wpm_sample_total", 0) / samples)

    def get_hourly_activity(self):
        """Chars typed today per hour, as a 24-slot list indexed by hour."""
        hourly = self.user_data.get("hourly_activity", {})
        return [hourly.get(str(h), 0) for h in range(24)]

    def get_daily_history(self, days):
        """The last `days` days as [(date, stats_dict), ...], oldest first.

        Days with no record are included with zeroed stats so the chart keeps an
        even spacing and today is always the rightmost bar.
        """
        history = self.user_data.get("daily_history", {})
        today = datetime.now()
        if today.hour < 2:
            today = today - timedelta(days=1)

        result = []
        for offset in range(days - 1, -1, -1):
            date = today - timedelta(days=offset)
            key = date.strftime("%Y-%m-%d")

            if offset == 0:
                # Today isn't archived yet, so read it from the live counters
                stats = {
                    "chars": self.total_chars_today,
                    "focus_seconds": int(self.total_active_time),
                    "avg_wpm": self.avg_wpm_today,
                    "highest_wpm": self.highest_wpm_today,
                    "longest_focus": int(self.longest_focus_today),
                }
            else:
                stats = history.get(key, {"chars": 0, "focus_seconds": 0, "avg_wpm": 0,
                                          "highest_wpm": 0, "longest_focus": 0})
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
        self.current_session_seconds = 0.0
        self.reset_spawn_pool()
        self.save_state()
        print("🧹 All stats reset")