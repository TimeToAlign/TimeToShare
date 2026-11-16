/**
 * The fonts that draw, and the one table that measures, every text of a
 * drawing.
 *
 * `docs/drawing.md` draws every text in DejaVu Sans 2.37 and every code point
 * DejaVu Sans does not map and Noto Music 2.004 does in Noto Music, chiefly
 * the Musical Symbols, Byzantine Musical Symbols and Ancient Greek Musical
 * Notation blocks; a code point neither maps takes DejaVu Sans's glyph 0. A
 * text is measured from one table of advance widths covering both fonts in
 * DejaVu Sans's units, bundled here as `fontMetrics`. The TrueType files and
 * their licences are shipped as `@timetoalign/timetoshare/fonts/<file>` for
 * each of `FONT_FILES` and
 * `@timetoalign/timetoshare/fonts/DejaVuSans-LICENSE` and
 * `@timetoalign/timetoshare/fonts/NotoMusic-LICENSE`.
 */

export { fontMetrics } from "./generated/font.js";

/**
 * The bundled TrueType files in fallback order: the text font, DejaVu Sans
 * 2.37, then the music font, Noto Music 2.004, which draws what DejaVu Sans
 * does not map.
 */
export const FONT_FILES = ["DejaVuSans.ttf", "NotoMusic-Regular.ttf"] as const;

/**
 * The advance-width metrics that measure a drawing's text, in DejaVu Sans's
 * font units.
 */
export interface FontMetrics {
  readonly units_per_em: number;
  readonly ascender: number;
  /** The descender as a positive depth. */
  readonly descender: number;
  /** The advance of glyph 0, counted for a code point the table does not hold. */
  readonly fallback: number;
  /**
   * The advance of every measured code point, keyed by the code point in
   * decimal: every code point DejaVu Sans maps, and every code point Noto
   * Music maps and DejaVu Sans does not, scaled to DejaVu Sans's units per
   * em and rounded to the nearest integer, ties to even.
   */
  readonly advances: Readonly<Record<string, number>>;
}
