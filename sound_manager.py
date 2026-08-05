# sound_manager.py

import os

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput

SOUND_DIR = "assets/sounds"
MUSIC_FILE = "ambient.wav"

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
        self.music = None
        self._music_output = None

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

        self._load_music()
        self.refresh_music()

    def _load_music(self):
        """Ambient bed on an endless loop, on its own player and output.

        QSoundEffect is for short one-shots; a 40-second bed belongs on
        QMediaPlayer, and giving it a separate audio output means music volume
        can sit low without dragging the splash down with it.
        """
        path = os.path.join(SOUND_DIR, MUSIC_FILE)
        if not os.path.exists(path):
            print(f"🔇 No ambient track at {path}")
            return

        self._music_output = QAudioOutput()
        self.music = QMediaPlayer()
        self.music.setAudioOutput(self._music_output)
        self.music.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self.music.setLoops(QMediaPlayer.Loops.Infinite)

    def _music_volume(self):
        if not self.time_manager:
            return 0.0
        level = self.time_manager.get_setting("music_volume") or 0
        master = self.time_manager.get_setting("master_volume") or 0
        return max(0.0, min(1.0, (level / 100.0) * (master / 100.0)))

    def refresh_music(self):
        """Start, stop or re-level the bed to match the current settings."""
        if self.music is None or not self.time_manager:
            return

        wanted = bool(self.time_manager.get_setting("music_enabled"))
        volume = self._music_volume()

        if self._music_output:
            self._music_output.setVolume(volume)

        if wanted and volume > 0:
            if self.music.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.music.play()
        else:
            self.music.pause()

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
