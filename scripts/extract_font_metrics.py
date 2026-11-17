#!/usr/bin/env python
"""Write the advance-width metrics of the bundled fonts as one table.

A drawing draws its text in DejaVu Sans 2.37 (``fonts/DejaVuSans.ttf``) and
every code point DejaVu Sans does not map and Noto Music 2.004
(``fonts/NotoMusic-Regular.ttf``) does in Noto Music, as the font-family list
``DejaVu Sans, Noto Music`` does. The script verifies the SHA-256 of both
TrueType files and writes
``fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json`` in pretty JSON
with ``dumps``, one table measuring both:

- ``units_per_em`` (``head``), ``ascender`` and ``descender`` (``hhea``, the
  descender as a positive depth) and ``fallback`` (the advance of glyph 0)
  are DejaVu Sans's.
- ``advances``, keyed by the code point in decimal, holds the advance of every
  code point of DejaVu Sans's best character map, as the font states it, and
  the advance of every code point that Noto Music's best character map holds
  and DejaVu Sans's does not. Such an advance is Noto Music's, scaled to
  DejaVu Sans's units per em and rounded to the nearest integer, ties to
  even: ``round(advance * 2048 / units_per_em)`` in exact integer
  arithmetic, ``units_per_em`` being Noto Music's. Of Noto Music's code
  points only those from U+0020 up are added: a drawing turns every code
  point from U+0000 to U+001F into a space before it measures or writes a
  text (section 5.1 of ``docs/drawing.md``), so an advance for one of them
  would never be read. No other code point is added; one neither font maps
  is measured by ``fallback``.

``dumps`` writes it in pretty JSON, every object's keys sorted by code point.
Run it from ``python/`` with ``uv run python ../scripts/extract_font_metrics.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont

from timetoshare import dumps

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FONTS = REPOSITORY_ROOT / "fonts"
TEXT_FONT = FONTS / "DejaVuSans.ttf"
MUSIC_FONT = FONTS / "NotoMusic-Regular.ttf"
METRICS = FONTS / "dejavu-sans-2.37+noto-music-2.004.metrics.json"
TEXT_SHA256 = "7da195a74c55bef988d0d48f9508bd5d849425c1770dba5d7bfc6ce9ed848954"
"""The SHA-256 of ``ttf/DejaVuSans.ttf`` in the upstream DejaVu 2.37 release."""
MUSIC_SHA256 = "26c0a28d7c6f96c70f1401db23066c5ea0ee1cdf155c79bc01ad2efb040de816"
"""The SHA-256 of ``NotoMusic/unhinted/ttf/NotoMusic-Regular.ttf`` in the
upstream Noto Music 2.004 release."""
FIRST_DRAWN = 0x20
"""The first code point a drawing draws: U+0000 to U+001F become spaces."""


def _verified(font: Path, sha256: str) -> TTFont:
    """Open a TrueType file, refusing one whose SHA-256 is not ``sha256``."""
    digest = hashlib.sha256(font.read_bytes()).hexdigest()
    if digest != sha256:
        raise SystemExit(f"{font}: SHA-256 {digest}, expected {sha256}")
    return TTFont(font)


def metrics(
    text_font: Path = TEXT_FONT, music_font: Path = MUSIC_FONT
) -> dict[str, Any]:
    """Return the merged metrics of the two fonts, refusing any other files."""
    text = _verified(text_font, TEXT_SHA256)
    music = _verified(music_font, MUSIC_SHA256)
    units_per_em = text["head"].unitsPerEm
    text_cmap = text.getBestCmap()
    music_cmap = music.getBestCmap()
    music_units_per_em = music["head"].unitsPerEm
    advances = {
        code_point: text["hmtx"][glyph][0] for code_point, glyph in text_cmap.items()
    }
    for code_point, glyph in music_cmap.items():
        if code_point >= FIRST_DRAWN and code_point not in text_cmap:
            advance = music["hmtx"][glyph][0]
            advances[code_point] = round(
                Fraction(advance * units_per_em, music_units_per_em)
            )
    return {
        "units_per_em": units_per_em,
        "ascender": text["hhea"].ascent,
        "descender": -text["hhea"].descent,
        "fallback": text["hmtx"][text.getGlyphOrder()[0]][0],
        "advances": {
            str(code_point): advance for code_point, advance in sorted(advances.items())
        },
    }


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and write the metrics file."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--text-font", type=Path, default=TEXT_FONT)
    parser.add_argument("--music-font", type=Path, default=MUSIC_FONT)
    parser.add_argument("--output", type=Path, default=METRICS)
    args = parser.parse_args(argv)
    args.output.write_text(
        dumps(metrics(args.text_font, args.music_font), serialization="json"),
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
