# sound_manager.py

import os

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QSoundEffect

SOUND_DIR = "assets/sounds"

# QSoundEffect only decodes PCM WAV - MP3 sources must be converted first:
#   afconvert -f WAVE -d LEI16@44100 -c 1 input.mp3 output.wav
SOUND_FILES = {
    "click": "click.wav",
    "unlock": "unlock.wav",
}

# Every setting that must be on for a sound to play
REQUIRES = {
    "click": ("sound_effects",),
    "unlock": ("notify_new_fish", "sound_notification"),
}


class SoundManager:
    """Plays the short UI sounds, gated by the Settings toggles.

    Every method is safe to call before load() or when a file is missing - it
    just does nothing, so the app runs fine with no audio assets at all.
    """

    def __init__(self):
        self.effects = {}
        self.time_manager = None

    def load(self, time_manager):
        """Preload the effects. Must run after QApplication exists.

        Preloading matters: building a QSoundEffect on first play makes that
        first sound audibly late.
        """
        self.time_manager = time_manager

        for name, filename in SOUND_FILES.items():
            path = os.path.join(SOUND_DIR, filename)
            if not os.path.exists(path):
                print(f"🔇 Sound not found, skipping: {path}")
                continue

            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            # Held on self so Python doesn't collect it mid-playback
            self.effects[name] = effect

        if self.effects:
            print(f"🔊 Loaded sounds: {', '.join(sorted(self.effects))}")

    def _volume(self):
        if not self.time_manager:
            return 0.7
        return max(0.0, min(1.0, self.time_manager.get_setting("master_volume") / 100.0))

    def _enabled(self, name):
        if not self.time_manager:
            return False
        return all(self.time_manager.get_setting(key) for key in REQUIRES.get(name, ()))

    def play(self, name):
        effect = self.effects.get(name)
        if effect is None or not self._enabled(name):
            return

        volume = self._volume()
        if volume <= 0.0:
            return

        effect.setVolume(volume)
        effect.play()

    def stop_all(self):
        for effect in self.effects.values():
            effect.stop()


# Module-level singleton, mirroring logger.py
sounds = SoundManager()
