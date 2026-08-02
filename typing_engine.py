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

    def _clean_old_timestamps(self):
        current_time = time.time()
        # Fast O(1) removals instead of creating a new list on every keystroke
        while self.timestamps and current_time - self.timestamps[0] > self.speed_window:
            self.timestamps.popleft()

    def get_current_speed(self):
        self._clean_old_timestamps()
        num_keys = len(self.timestamps)
        if num_keys == 0:
            return 0, 0

        cpm = int(num_keys * (60.0 / self.speed_window))
        wpm = int(cpm / 5)

        return cpm, wpm

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
        self.char_count += 1
        self.timestamps.append(time.time())
        self.broadcast_stats()

    def start(self):
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener.join()