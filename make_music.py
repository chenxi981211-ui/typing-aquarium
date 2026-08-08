# make_music.py
"""Synthesise the ambient aquarium loop.

    ~/.venvs/aquarium/bin/python make_music.py

Written rather than sourced, which avoids any licensing question and - more
usefully - lets the loop be seamless by construction. A join every time the
track repeats is far more noticeable than a plain track, and it is the usual
reason ambient loops fail.

Seamlessness comes from one rule: every oscillator, every slow swell and every
noise partial runs at a whole number of cycles per loop. The loop's fundamental
is 1/LENGTH Hz, so each frequency is rounded to the nearest multiple of that -
a shift of at most 0.008 Hz, inaudible - and the waveform then arrives back
exactly where it started. Struck sounds are wrapped round the join instead, so
a bell ringing at the end continues into the start rather than being cut.

The sound aims at the bright, glossy Frutiger Aero register: a major-9 pad with
a lydian shimmer, chorused and wide, a soft bed of moving water, and sparse
glass bell notes. numpy is a build-time dependency only - it is in the
PyInstaller excludes and never ships with the app.
"""

import struct
import wave

import numpy as np

RATE = 44100
LENGTH = 64                     # longer than the old 40s, so it repeats less
OUT = "assets/sounds/ambient.wav"

FUNDAMENTAL = 1.0 / LENGTH
FRAMES = RATE * LENGTH
T = np.arange(FRAMES) / RATE
TAU = 2.0 * np.pi

rng = np.random.default_rng(20260808)


def locked(frequency):
    """Round to the nearest whole number of cycles per loop."""
    return max(1, round(frequency / FUNDAMENTAL)) * FUNDAMENTAL


def osc(frequency, phase=0.0):
    return np.sin(TAU * locked(frequency) * T + phase)


def swell(cycles, depth=0.45, phase=0.0):
    """Slow breathing that returns to its start, never reaching silence."""
    return (1.0 - depth) + depth * np.sin(TAU * cycles * FUNDAMENTAL * T + phase)


# D major add9 with a maj7 and a lydian G# well back in the mix. Bright and
# open rather than the old minor 9th, which read as wistful - wrong register for
# a tank full of tropical fish.
#   frequency, level, swell cycles, stereo position (-1 left .. +1 right)
# Levels are weighted up towards the middle and top on purpose. Voiced by ear
# from the note names alone, the low D2 and A2 dominated: 77% of the energy sat
# under 120Hz, which is muddy on speakers and inaudible rumble on a laptop,
# eating the headroom either way. The bass is now only a hint of foundation.
PAD = [
    (73.42,  0.038, 1,  0.00),   # D2  root, just a floor
    (110.00, 0.062, 2, -0.35),   # A2
    (146.83, 0.105, 1,  0.30),   # D3
    (185.00, 0.098, 3, -0.55),   # F#3
    (220.00, 0.092, 2,  0.50),   # A3
    (329.63, 0.072, 4, -0.30),   # E4  the 9th
    (554.37, 0.042, 3,  0.45),   # C#5 maj7, air
    (415.30, 0.024, 5, -0.65),   # G#4 lydian shimmer
    (739.99, 0.022, 6,  0.60),   # F#5 top gloss
]

# Pentatonic glass notes. Sparse and high, the Aero signature.
BELL_SCALE = [587.33, 659.26, 739.99, 880.00, 987.77, 1174.66]   # D5 E5 F#5 A5 B5 D6


def pan(mono, position):
    """Constant-power pan. Returns (left, right)."""
    angle = (position + 1.0) * 0.25 * np.pi
    return mono * np.cos(angle), mono * np.sin(angle)


def build_pad():
    left = np.zeros(FRAMES)
    right = np.zeros(FRAMES)

    for frequency, level, cycles, position in PAD:
        # Three barely detuned copies per voice. The slow beating between them
        # is what turns a bare sine into something with movement in it.
        voice = np.zeros(FRAMES)
        for detune, weight in ((1.0, 1.0), (1.0015, 0.6), (0.9985, 0.6)):
            voice += weight * osc(frequency * detune, phase=rng.uniform(0, TAU))
        # A touch of second harmonic keeps it from sounding like a test tone.
        voice += 0.16 * osc(frequency * 2.0, phase=rng.uniform(0, TAU))
        voice *= level * swell(cycles, 0.42, rng.uniform(0, TAU)) / 2.2

        l, r = pan(voice, position)
        left += l
        right += r

    return left, right


def build_water():
    """A soft bed of moving water.

    Built by summing many locked partials rather than from random samples, so
    it is periodic over the loop and cannot click at the join. Weighting the
    partials down with frequency gives it a pink, watery tilt instead of the
    harsh hiss of white noise.
    """
    left = np.zeros(FRAMES)
    right = np.zeros(FRAMES)

    for _ in range(320):
        frequency = float(np.exp(rng.uniform(np.log(180), np.log(5200))))
        weight = (300.0 / frequency) ** 0.55
        phase = rng.uniform(0, TAU)
        position = rng.uniform(-1.0, 1.0)
        l, r = pan(weight * osc(frequency, phase), position)
        left += l
        right += r

    # Two overlapping slow swells, so the water rises and falls unevenly
    # rather than pulsing in an obvious cycle.
    motion = 0.55 * swell(1, 0.5, 0.0) + 0.45 * swell(3, 0.5, 1.7)
    peak = max(np.abs(left).max(), np.abs(right).max()) or 1.0
    scale = 0.075 / peak
    return left * motion * scale, right * motion * scale


def add_struck(left, right, start, mono, position):
    """Mix a decaying sound in, wrapping it round the loop join.

    A bell struck near the end should ring on into the beginning of the next
    pass. Truncating it there would put a click exactly where the loop repeats.
    """
    begin = int(start * RATE) % FRAMES
    index = (begin + np.arange(mono.size)) % FRAMES
    l, r = pan(mono, position)
    np.add.at(left, index, l)
    np.add.at(right, index, r)


def bell(frequency, seconds=2.6, level=0.16):
    """A glass bell: fast attack, long decay, slightly inharmonic partials."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    body = np.zeros(n)
    # Struck-bar partials. The stretched ratios are what make it read as glass
    # or metal rather than as a flute.
    for ratio, weight, decay in ((1.0, 1.0, seconds * 0.42),
                                 (2.76, 0.34, seconds * 0.20),
                                 (5.40, 0.14, seconds * 0.11),
                                 (8.93, 0.05, seconds * 0.07)):
        body += weight * np.exp(-t / decay) * np.sin(TAU * frequency * ratio * t)
    attack = 1.0 - np.exp(-t / 0.004)
    return level * attack * body / 1.5


def bubble(pitch, level=0.085):
    """Short rising blip - the upward sweep is what makes it a bubble."""
    n = int(0.17 * RATE)
    t = np.arange(n) / RATE
    decay = np.exp(-t / 0.042)
    sweep = pitch * (1.0 + 2.6 * t)
    return level * decay * np.sin(TAU * sweep * t)


def build():
    left, right = build_pad()
    wl, wr = build_water()
    left += wl
    right += wr

    # Bells on an irregular spacing so no bar line emerges. Two land late on
    # purpose, to exercise the wrap.
    hits = [2.5, 9.0, 15.5, 21.0, 29.5, 36.0, 43.5, 49.0, 56.5, 62.0]
    for i, start in enumerate(hits):
        frequency = BELL_SCALE[(i * 3 + 1) % len(BELL_SCALE)]
        position = -0.7 + 1.4 * ((i * 5) % 7) / 6.0
        add_struck(left, right, start, bell(frequency), position)

    for i, (start, pitch) in enumerate([(4.2, 660), (12.7, 900), (18.1, 540),
                                        (25.6, 780), (33.3, 1000), (40.8, 620),
                                        (47.4, 860), (53.9, 700), (60.2, 940)]):
        add_struck(left, right, start, bubble(pitch), -0.8 + 1.6 * (i % 5) / 4.0)

    stereo = np.stack([left, right], axis=1)
    peak = np.abs(stereo).max() or 1.0
    stereo *= 0.66 / peak          # deliberately quiet - this sits under work
    return np.clip(stereo, -1.0, 1.0)


def main():
    stereo = build()
    flat = (stereo.reshape(-1) * 32767).astype(np.int16)

    with wave.open(OUT, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(flat.tobytes())

    print(f"wrote {OUT}  {LENGTH}s stereo  {flat.size // 2} frames")


if __name__ == "__main__":
    main()
