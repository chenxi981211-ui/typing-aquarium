# make_splash.py
"""Synthesise the sound a new fish arrives on.

    ~/.venvs/aquarium/bin/python make_splash.py

The previous one built to its loudest point 1.76 seconds in and peaked at 0.85 -
a sting, arriving after the fish had already appeared, at a volume that made a
background app feel like it wanted attention.

This is a water droplet instead: a soft-edged bloop, a smaller one behind it,
and a little wet texture underneath. Under a second, and quiet enough to be
pleasant on the twentieth fish rather than only the first.

The rising pitch is what makes it read as water. A bubble's resonant frequency
climbs as it shrinks, so a falling sweep sounds like a cartoon boing while a
rising one sounds like something dropping into a pond.
"""

import struct
import wave

import numpy as np

RATE = 44100
OUT = "assets/sounds/unlock.wav"
LENGTH = 0.85

rng = np.random.default_rng(11)


def bloop(start, f_from, f_to, level, decay, attack=0.012, sweep=0.10):
    """One droplet: a rising sine with a soft edge on the front."""
    n = int(LENGTH * RATE)
    out = np.zeros(n)
    begin = int(start * RATE)
    length = min(n - begin, int(0.5 * RATE))
    if length <= 0:
        return out

    t = np.arange(length) / RATE
    # Pitch climbs quickly, then settles - the shape of a shrinking bubble
    climb = 1.0 - np.exp(-t / sweep)
    freq = f_from + (f_to - f_from) * climb
    phase = 2 * np.pi * np.cumsum(freq) / RATE

    # A few milliseconds of attack is the whole difference between a plop and
    # a click; an instant onset is what the ear hears as abrupt.
    envelope = (1.0 - np.exp(-t / attack)) * np.exp(-t / decay)
    out[begin:begin + length] = level * envelope * np.sin(phase)
    return out


def wet_texture(start, level, decay):
    """Soft filtered noise - the water around the droplet, not the droplet."""
    n = int(LENGTH * RATE)
    out = np.zeros(n)
    begin = int(start * RATE)
    length = min(n - begin, int(0.35 * RATE))
    if length <= 0:
        return out

    noise = rng.normal(0, 1, length)
    # Cheap low-pass: a running mean. Unfiltered noise is hiss, and hiss is
    # exactly the harsh edge being designed out here.
    window = 28
    noise = np.convolve(noise, np.ones(window) / window, mode="same")

    t = np.arange(length) / RATE
    envelope = (1.0 - np.exp(-t / 0.006)) * np.exp(-t / decay)
    out[begin:begin + length] = level * envelope * noise
    return out


def build():
    audio = np.zeros(int(LENGTH * RATE))

    # The main droplet
    audio += bloop(0.00, 430, 880, 0.55, decay=0.16)
    # A smaller one just behind it, the way a real drop rings twice
    audio += bloop(0.13, 620, 1180, 0.22, decay=0.10)
    # A third, barely there, for the tail
    audio += bloop(0.26, 780, 1420, 0.09, decay=0.07)

    # A little weight underneath so it does not sound thin on laptop speakers
    audio += bloop(0.00, 150, 210, 0.20, decay=0.22, attack=0.020, sweep=0.16)

    audio += wet_texture(0.00, 0.10, decay=0.05)
    audio += wet_texture(0.13, 0.05, decay=0.04)

    # A gentle fade on the very end, so nothing is cut off mid-ring
    tail = int(0.08 * RATE)
    audio[-tail:] *= np.linspace(1.0, 0.0, tail)

    peak = np.abs(audio).max() or 1.0
    # Deliberately well below the old 0.85 - this fires every time a fish
    # arrives, and a background app should not startle anyone.
    audio *= 0.42 / peak
    return np.clip(audio, -1.0, 1.0)


def main():
    audio = build()
    samples = (audio * 32767).astype(np.int16)
    with wave.open(OUT, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(samples.tobytes())
    print(f"wrote {OUT}  {LENGTH}s  peak {np.abs(audio).max():.2f}")


if __name__ == "__main__":
    main()
