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
LENGTH = 0.62

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


def spray(start, level, decay, low=18, high=90):
    """The sound of water breaking - a band of noise, not a hiss.

    Two running means at different widths, subtracted: the wide one is
    everything below the band, the narrow one everything below the top of it,
    so the difference is the band between. Keeping the very top out is what
    stops it turning into the harsh sss that made the first attempt unpleasant.
    """
    n = int(LENGTH * RATE)
    out = np.zeros(n)
    begin = int(start * RATE)
    length = min(n - begin, int(0.30 * RATE))
    if length <= 0:
        return out

    noise = rng.normal(0, 1, length + high * 2)
    wide = np.convolve(noise, np.ones(low) / low, mode="same")
    wider = np.convolve(noise, np.ones(high) / high, mode="same")
    band = (wide - wider)[:length]
    band /= (np.abs(band).max() or 1.0)

    t = np.arange(length) / RATE
    envelope = (1.0 - np.exp(-t / 0.004)) * np.exp(-t / decay)
    out[begin:begin + length] = level * envelope * band
    return out


def build():
    audio = np.zeros(int(LENGTH * RATE))

    # The spray goes first and loudest - this is the splash itself
    audio += spray(0.000, 0.34, decay=0.045)
    audio += spray(0.045, 0.16, decay=0.070, low=26, high=130)

    # A light plop, pitched up from the previous version so it reads as a small
    # fish rather than a rock going in
    audio += bloop(0.005, 700, 1500, 0.34, decay=0.085)

    # Droplets scattering afterwards. Staggered and each a little higher, which
    # is most of where the cuteness comes from - a single tone sounds like a
    # notification, several tumbling sound like water.
    for start, f_from, f_to, level, decay in (
        (0.075, 1150, 2000, 0.16, 0.055),
        (0.120, 1500, 2500, 0.11, 0.045),
        (0.175, 1900, 3000, 0.075, 0.038),
        (0.240, 2300, 3500, 0.045, 0.030),
        (0.310, 2700, 3900, 0.025, 0.026),
    ):
        audio += bloop(start, f_from, f_to, level, decay=decay, attack=0.005, sweep=0.05)

    # Only a touch of weight. Too much bass is what made it feel heavy before.
    audio += bloop(0.000, 190, 260, 0.10, decay=0.11, attack=0.014, sweep=0.10)

    tail = int(0.07 * RATE)
    audio[-tail:] *= np.linspace(1.0, 0.0, tail)

    peak = np.abs(audio).max() or 1.0
    audio *= 0.40 / peak
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
