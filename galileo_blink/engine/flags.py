"""NASA's per-pixel quality flags, in plain words.

Every SPHEREx photo carries a FLAGS layer: one bit per kind of problem. Galileo Blink shows
them (so a blemish is not mistaken for a discovery) and treats only a few as "no data"
(constants.MASK_BITS).
"""
from __future__ import annotations

import numpy as np

FLAG_INFO: dict[int, tuple[str, str]] = {
    0: ("TRANSIENT", "Something changed during the exposure: usually a cosmic-ray hit"),
    1: ("OVERFLOW", "So bright the pixel overflowed"),
    2: ("SUR_ERROR", "On-board processing failed here, usually because a star saturated"),
    6: ("NONFUNC", "A permanently dead pixel"),
    7: ("DICHROIC", "Low sensitivity at the edge of the beam splitter"),
    9: ("MISSING_DATA", "Data lost on board"),
    10: ("HOT", "A hot pixel that glows by itself"),
    11: ("COLD", "A pixel with abnormally low signal"),
    14: ("PHANMISS", "A known electronic echo was not corrected"),
    15: ("NONLINEAR", "Very bright: the brightness here is not fully corrected"),
    17: ("PERSIST", "After-image of something bright seen earlier"),
    19: ("OUTLIER", "Differs from other photos of the same sky: a moving object, a variable star or a blemish"),
    20: ("CROSSTALK", "Electronic echo of a bright star elsewhere on the detector"),
    22: ("GHOST", "Reflection of a bright star in this photo"),
    23: ("GHOST_FPA", "Reflection of a bright star on another detector"),
    24: ("GHOST_EXT", "Reflection of a bright star outside the photo"),
    25: ("STREAK", "A satellite or aircraft trail"),
    26: ("BLOOM", "Charge spilling from a very bright star"),
    27: ("SNOWBALL", "A large cosmic-ray hit"),
    28: ("HALO", "The faint halo around a sudden change"),
    29: ("SATELLITE_HALO", "The glow around a satellite trail"),
}
"""Flags worth showing a person. Left out on purpose: 12 FULLSAMPLE and 21 SOURCE, which
describe the data rather than a problem with it."""

CONTAMINATION_MASK = sum(1 << b for b in FLAG_INFO)


def count_flags(flags: np.ndarray, inside: np.ndarray) -> dict[str, int]:
    """How many pixels inside the view carry each flag."""
    region = flags[inside]
    out = {}
    for bit, (name, _) in FLAG_INFO.items():
        n = int(np.count_nonzero(region & (1 << bit)))
        if n:
            out[name] = n
    return out


def describe() -> list[dict]:
    """The flag table for the interface."""
    from .constants import MASK_BITS
    return [dict(bit=b, name=n, meaning=m, treated_as_no_data=b in MASK_BITS)
            for b, (n, m) in sorted(FLAG_INFO.items())]
