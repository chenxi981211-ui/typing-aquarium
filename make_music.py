# make_music.py
"""Synthesise the ambient aquarium loop.

    ~/.venvs/aquarium/bin/python make_music.py

Written rather than sourced, which avoids any licensing question and - more
usefully - lets the loop be seamless by construction. A join every time the
track repeats is far more noticeable than a plain track, and it is the usual
reason ambient loops fail.

Seamlessness comes from one rule: every oscillator and every slow swell runs at
a whole number of cycles per loop. A 40-second loop has a fundamental of
1/40 Hz, so any frequency is rounded to the nearest multiple of that - a shift
of at most 0.0125 Hz, which is inaudible - and the waveform then arrives back
exactly where it started.
"""

import math
import struct
import wave

RATE = 44100
SECONDS = 40
OUT = "assets/sounds/ambient.wav"

FUNDAMENTAL = 1.0 / SECONDS


def locked(frequency):
    """Round to the nearest whole number of cycles per loop."""
    return max(1, round(frequency / FUNDAMENTAL)) * FUNDAMENTAL


# A minor 9th, voiced wide and low. Gentle, unresolved, and it does not pull
# anywhere - which is what keeps it out of the way while you work.
PAD = [
    (110.00, 0.16, 1),   # A2  root drone
    (164.81, 0.10, 2),   # E3
    (220.00, 0.11, 1),   # A3
    (261.63, 0.085, 3),  # C4
    (329.63, 0.070, 2),  # E4
    (493.88, 0.030, 5),  # B4  the 9th, barely there
    (659.26, 0.018, 4),  # E5  air
]


def build():
    frames = RATE * SECONDS
    samples = [0.0] * frames

    for frequency, level, swell in PAD:
        f = locked(frequency)
        swell_rate = swell * FUNDAMENTAL          # also whole cycles per loop
        phase_offset = (frequency % 7) / 7.0 * math.tau

        for i in range(frames):
            t = i / RATE
            # slow breathing, never fully silent so the chord stays present
            envelope = 0.55 + 0.45 * math.sin(math.tau * swell_rate * t + phase_offset)
            samples[i] += level * envelope * math.sin(math.tau * f * t)

    # A slow filter-like sway: a very quiet detuned pair beating against itself,
    # which reads as water moving rather than as a second note.
    for frequency, level in ((110.0, 0.05), (220.0, 0.035)):
        a, b = locked(frequency), locked(frequency + 0.5)
        for i in range(frames):
            t = i / RATE
            samples[i] += level * 0.5 * (math.sin(math.tau * a * t) + math.sin(math.tau * b * t))

    # Bubbles: a short rising blip with a fast decay. Placed away from the loop
    # join so none of them is cut in half when it wraps.
    bubbles = [(3.2, 640), (9.7, 880), (14.1, 520), (19.6, 760),
               (24.3, 980), (28.8, 600), (34.5, 840)]
    for start, pitch in bubbles:
        begin = int(start * RATE)
        length = int(0.16 * RATE)
        for n in range(length):
            if begin + n >= frames:
                break
            t = n / RATE
            decay = math.exp(-t / 0.045)
            # upward sweep is what makes it read as a bubble rather than a beep
            sweep = pitch * (1.0 + 2.4 * t)
            samples[begin + n] += 0.10 * decay * math.sin(math.tau * sweep * t)

    peak = max(abs(s) for s in samples) or 1.0
    target = 0.62                      # deliberately quiet - this sits under work
    gain = target / peak

    return [int(max(-1.0, min(1.0, s * gain)) * 32767) for s in samples]


def main():
    samples = build()
    with wave.open(OUT, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(struct.pack("<%dh" % len(samples), *samples))

    seam = max(abs(samples[i] - samples[-len(samples) + i]) for i in range(1))
    print(f"wrote {OUT}  {SECONDS}s  {len(samples) / RATE:.0f}s of audio")
    print(f"loop join: first sample {samples[0]}, last {samples[-1]} "
          f"(difference {abs(samples[0] - samples[-1])})")


if __name__ == "__main__":
    main()
