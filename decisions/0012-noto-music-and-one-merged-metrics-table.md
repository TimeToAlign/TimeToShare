# 0012. Noto Music draws what DejaVu Sans does not map; one merged metrics table

Date: 2026-11-16

## Context

The drawing specification draws and measures every text in DejaVu Sans 2.37
(decision 0009). A coordinate label in whole notes shows the whole-note
symbol U+1D15D, and DejaVu Sans maps no code point of the Musical Symbols
block, U+1D100 to U+1D1FF. A renderer would draw a glyph of whatever font
its system finds, and the drawing would measure it as DejaVu Sans's glyph 0,
so neither the glyph nor the width were pinned.

Every text a drawing measures goes through one table of advance widths
(`units_per_em`, `ascender`, `descender`, `fallback`, `advances`), read by
the measurers of every implementation.

## Considered options

- Noto Music 2.004, the unhinted TrueType file of the upstream release.
- Bravura Text, the text font of the SMuFL reference font.
- Symbola or FreeSerif, general fonts that cover the block.
- Draw the symbol as a path instead of text.
- Spell the unit in letters and draw no symbol.

## Decision

Drawn text stays in DejaVu Sans 2.37. The code points from U+0020 up that
Noto Music 2.004 maps and DejaVu Sans does not are drawn in Noto Music:
549, the 233 of the Musical Symbols block (U+1D15D among them; DejaVu Sans
maps none of the block), the 246 of the Byzantine Musical Symbols (U+1D000
to U+1D0FF) and the 70 of the Ancient Greek Musical Notation block. Noto
Music also maps U+0000 and U+000D; a drawing turns every code point from
U+0000 to U+001F into a space before measuring or writing a text, so
neither is drawn and neither is in the table. The repository ships `fonts/NotoMusic-Regular.ttf`,
the release archive's `NotoMusic/unhinted/ttf/NotoMusic-Regular.ttf` (SHA-256
`26c0a28d7c6f96c70f1401db23066c5ea0ee1cdf155c79bc01ad2efb040de816`), beside
`fonts/DejaVuSans.ttf`. The licences take symmetric names:
`fonts/DejaVuSans-LICENSE` (formerly `fonts/LICENSE`) and
`fonts/NotoMusic-LICENSE`, the archive's `OFL.txt`.

**One table.** The drawing keeps one metrics table of the same shape, so no
measurer changes. `scripts/extract_font_metrics.py` verifies the SHA-256 of
both files and writes `fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json`:

- `units_per_em` (2048), `ascender`, `descender` and `fallback` are DejaVu
  Sans's, as before;
- `advances` holds every code point DejaVu Sans maps with its advance, each
  value byte-identical to the former table's, and every code point from
  U+0020 up that Noto Music maps and DejaVu Sans does not, with Noto
  Music's advance scaled to 2048 units per em and rounded to the nearest
  integer, ties to even: `round(advance × 2048 / 1000)` in exact integer
  arithmetic (Noto Music has 1000 units per em; no added advance lies on a
  tie). U+1D15D measures 1053 (514 of 1000).

No other code point is added; a code point neither font maps is measured
by `fallback`. Measuring matches drawing: the SVG writer's font-family list
`DejaVu Sans, Noto Music`, the TikZ writer's font fallback and a browser
draw exactly these code points in Noto Music, so a renderer needs no range
restriction.

Both packages name the TrueType files in fallback order as `FONT_FILES`
(`DejaVuSans.ttf`, `NotoMusic-Regular.ttf`); the metrics stay one accessor,
`font_metrics()` in Python and `fontMetrics` in JavaScript.

- **Fit.** Noto Music maps every assigned code point of the Musical Symbols
  block with glyphs designed to sit beside text, and its file is 80,716
  bytes. Bravura Text is built around SMuFL's private-use code points and
  sizes its symbols for engraving. Symbola and FreeSerif are large general
  fonts whose text glyphs would compete with DejaVu Sans's. A path is no
  text: it would need a second measuring rule, and a TikZ writer would draw
  it apart from the label. Letters lose the symbol the label is meant to
  show.
- **Maintenance.** Noto Music is part of the Noto project, maintained by
  Google Fonts and its contributors in `notofonts/music` (bus factor well
  above one), licence SIL Open Font License 1.1
  (https://github.com/notofonts/music/blob/main/OFL.txt). It is an asset,
  no code dependency; neither package reads a font at run time.
- **Writing it ourselves.** Designing and maintaining the block's 233
  glyphs is out of proportion to the need.
- **Audited version.** 2.004, released 2026-10-12
  (https://github.com/notofonts/music/releases/tag/NotoMusic-v2.004),
  release archive SHA-256
  `47c784aa4c73aceca48cfbb6959cfdf71b524d257eb453ef97ad3640a37e396d`.

## Consequences

A scaled advance is off from Noto Music's own by at most half a unit of 2048
per em. The ascender and descender stay DejaVu Sans's, so a line's height
does not follow a music symbol's extent. The metrics file has a new name,
and every consumer of the shipped licence follows its new name. Replacing
Noto Music touches the script, the table and the two files; the measurers
stay as they are. The exit cost is the replacement font and a regenerated
table.

## Review date

2027-11-16.
