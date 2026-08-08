# typing_engine.py
import time
from threading import Thread, Event
from pynput import keyboard
from collections import deque  # NEW: highly optimized for popping from the left

class TypingManager:
    def __init__(self, on_key_callback=None):
        self.on_key_callback = on_key_callback
        self.stop_event = Event()
        self.char_count = 0
        self.listener = None

        self.timestamps = deque()  # Replaced list with deque
        self.speed_window = 10.0

        # Holding a key down makes the OS fire on_press over and over - about
        # 20 a second - which is not typing and was pushing peak WPM to absurd
        # figures (a held backspace read as 244 WPM). The same key arriving
        # again this fast is auto-repeat: a real double tap cannot beat it.
        self._last_key = None
        self._last_key_time = 0.0
        self.repeat_threshold = 0.06

        # The last speed worth showing, kept for whenever the current window
        # cannot support a reading.
        self._held_speed = (0, 0)
        # Below these the sample is too thin to mean anything: a handful of keys
        # inside a fraction of a second says more about one quick word than
        # about how fast someone types.
        self.min_samples = 5
        self.min_span = 0.6
        # Idle longer than this and the reading is frozen where it was
        self.hold_after = 1.5

    def _clean_old_timestamps(self):
        current_time = time.time()
        # Fast O(1) removals instead of creating a new list on every keystroke
        while self.timestamps and current_time - self.timestamps[0] > self.speed_window:
            self.timestamps.popleft()

    def get_current_speed(self):
        """Live typing speed, measured over the keystrokes actually made.

        The old version divided the key count by the full ten-second window
        whether or not you had been typing for ten seconds. Type five characters
        and stop and it reported six words a minute - not a slow reading, just
        one second of typing averaged over ten seconds of mostly nothing. Since
        nothing recomputes once you stop, that nonsense figure was what stayed
        on screen.

        The rate now comes from the span between the first and last keystroke in
        the window, which is the speed you were actually typing at. When there is
        not enough to measure - too few keys, or you have stopped - the last real
        reading is held rather than replaced with a meaningless one.
        """
        self._clean_old_timestamps()
        num_keys = len(self.timestamps)

        if num_keys < self.min_samples:
            return self._held_speed

        # Stopped typing: keep the last speed rather than watching the window
        # drain. A held figure is the honest answer to "how fast do you type".
        if time.time() - self.timestamps[-1] > self.hold_after:
            return self._held_speed

        span = self.timestamps[-1] - self.timestamps[0]
        if span < self.min_span:
            return self._held_speed

        # num_keys - 1 because n keystrokes bound n-1 intervals
        cpm = int((num_keys - 1) / span * 60.0)
        self._held_speed = (cpm, int(cpm / 5))
        return self._held_speed

    def reset_speed(self):
        """Forget the recent keystrokes behind the live speed reading.

        After a stats reset the rolling window still holds up to ten seconds of
        history, so the WPM figure would keep reporting the old speed until it
        aged out. Clearing it makes the reset immediate.
        """
        self.timestamps.clear()
        self._last_key = None
        self._last_key_time = 0.0
        self._held_speed = (0, 0)

    def broadcast_stats(self):
        cpm, wpm = self.get_current_speed()
        if self.on_key_callback:
            stats = {
                "total_chars": self.char_count,
                "cpm": cpm,
                "wpm": wpm
            }
            self.on_key_callback(stats)

    def on_press(self, key):
        now = time.time()
        if key == self._last_key and (now - self._last_key_time) < self.repeat_threshold:
            self._last_key_time = now
            return
        self._last_key, self._last_key_time = key, now

        self.char_count += 1
        self.timestamps.append(now)
        self.broadcast_stats()

    def start(self):
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener.join()