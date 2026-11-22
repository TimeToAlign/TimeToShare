"""The fonts that draw, and the one table that measures, every text of a drawing.

``docs/drawing.md`` draws every text in DejaVu Sans 2.37 and every code point
DejaVu Sans does not map and Noto Music 2.004 does in Noto Music, chiefly the
Musical Symbols, Byzantine Musical Symbols and Ancient Greek Musical Notation
blocks; a code point neither maps takes DejaVu Sans's glyph 0. A text is
measured from one table of advance widths covering both fonts in DejaVu Sans's
units. The TrueType files, their licences and the table are bundled with the
package.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from .validate import data_root

FONT_FILES = ("DejaVuSans.ttf", "NotoMusic-Regular.ttf")
"""The bundled TrueType files in fallback order: the text font, DejaVu Sans
2.37, then the music font, Noto Music 2.004, which draws what DejaVu Sans
does not map. Each file's licence lies beside it as ``DejaVuSans-LICENSE``
and ``NotoMusic-LICENSE``."""
METRICS_FILE = "dejavu-sans-2.37+noto-music-2.004.metrics.json"


def font_paths() -> tuple[Path, ...]:
    """Return the paths of the bundled TrueType files, in ``FONT_FILES`` order."""
    return tuple(data_root() / "fonts" / name for name in FONT_FILES)


@cache
def _metrics() -> dict[str, Any]:
    with (data_root() / "fonts" / METRICS_FILE).open(encoding="utf-8") as handle:
        return json.load(handle)


def font_metrics() -> dict[str, Any]:
    """Return the metrics that measure every text of a drawing.

    The members are DejaVu Sans's ``units_per_em``, ``ascender``,
    ``descender`` (a positive depth) and ``fallback`` (the advance of glyph 0,
    counted for a code point the table does not hold), and ``advances``,
    keyed by the code point in decimal: the advance of every code point
    DejaVu Sans maps, and of every code point Noto Music maps and DejaVu
    Sans does not, scaled to DejaVu Sans's units per em and rounded to the
    nearest integer, ties to even. The result is cached and shared; treat it
    as read-only.
    """
    return _metrics()
