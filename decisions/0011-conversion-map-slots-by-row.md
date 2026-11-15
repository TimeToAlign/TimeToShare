# 0011. Conversion maps share slots across the lines of a row

Date: 2026-11-15

## Context

A conversion map is drawn as a closed double line along the timeline it
converts from, in that timeline's conversion maps band (drawing
specification, section 6.4). The drawing stacked each line's maps on their
own, in canonical order, which is by ID, with one exception: a segment that
is not a segment line has no line, so its maps joined its segment line's
band after the line's own.

Two consequences made the drawing hard to read:

- Lines that lie side by side in one row, such as the sections of a movement
  or the phrases of a section, each stacked their maps from the line
  outwards. A map to ticks on one child and a tempo map on its neighbour
  could lie at the same height, and the two tempo maps of the row at
  different heights, so the eye could not follow one kind of map along the
  row.
- The order within a stack was the order of the IDs, which are minted or
  free and say nothing of what a map converts.

Rows are, for now, whatever the first fits of the children bands produce.
An editor is expected to let a user move a child from one row into
another, so rows may become explicit. The map layout must therefore follow
from row membership alone, whatever decides it.

## Considered options

- Keep a stack per line, in canonical order.
- Keep a stack per line, ordered by type.
- Give every type a fixed slot per member drawing, used or not.
- Share slots across the bands of one row, side and level, keyed by name
  and type, with first fit for maps of one key whose timelines overlap.

## Decision

The conversion maps bands of the lines of one row that lie on one side of
those lines at one level are laid out together, in one sequence of slots
(drawing specification, section 6.4, Conversion maps), in two sets where
their lines' children bands lie on both sides of them (below):

- **Key.** A map's key is its `name` and its `type` when its `name` is not
  null, else its `type` alone. Keys with a name come first, ordered by name
  and then by type; keys without one follow, ordered by type; strings are
  compared by Unicode code point. An ID never keys a slot: IDs are unique,
  so no two maps would ever share one.
- **Sub-slots by first fit.** The maps of the row are taken in the
  traversal order of their lines, each line's own maps in canonical order
  before those its segments without a line join to it. The maps of each key
  are placed in that order by the first fit of section 6.3, with the extent
  of the timeline each spans, into the key's sub-slots. The sub-slots of
  the keys, in key order, are the slots. Maps of one key share a slot where
  their timelines do not conflict and take the next where they do, so two
  sibling children with a tempo map each draw both at one height, while a
  segment line's map and its segment's map of the same key, which overlap,
  take two.
- **One geometry.** The bands start at one distance, the largest of their
  own starts, and the largest stroke width of their lines places every
  slot; every band of the set is as wide as all its slots. A segment
  without a line is no special case: its maps are maps of its segment
  line's band, and take slots like any other.
- **No waiting on itself.** Children bands laid out together may lie at
  different levels. Where one line of a row has its children band nearer
  the line than its conversion maps band and another line the reverse, one
  common start for their maps bands would wait on itself through the
  children bands. The conversion maps bands of one level are therefore
  laid out together in two sets: those whose line's children band lies
  nearer the line, and the others. Every start is then found step by step,
  laying out bands once the bands nearer their lines are laid out; any
  order of the steps gives one result.
- **The seam.** One sentence of the specification says which lines form a
  row (the root's row holds the root alone, every other row is one that the
  first fits of children bands laid out together fill); the slots depend on
  nothing else of the layout but each band's side and level and the side
  of it on which its line's children band lies. A later rule that assigns rows explicitly
  replaces that sentence and leaves the slot rule as it is.

The slots are found in the first pass of the layout, after the first fits
and before any distance, since they need the rows alone; maps add nothing
to a child's extent, so the rows never depend on the slots.

## Rejected options

- **A stack per line, in canonical order**: the problems listed under
  Context.
- **A stack per line, ordered by type**: one line reads better, but the
  maps of neighbouring lines in one row still lie at heights that depend on
  what each line holds.
- **A fixed slot per type for a whole member drawing**: maps of one type
  would align across rows that never meet, every band would be as wide as
  the number of types anywhere in the drawing, and two maps of one type
  with different names, such as two tempo maps from two sources, could not
  be told apart.

## Consequences

A line's conversion maps band may leave slots empty, the slots that other
lines of its row use, so the band can be wider than its own maps need; in
return, maps of one key read as one row of maps. Moving a child into
another row changes the slots of both rows and nothing else. A drawing
whose rows each hold at most one line with maps changes only where a band
holds maps of several keys whose key order differs from the order in which
they are taken.
Implementations compute slots from row membership, side, level, the place
of each line's children band, the displayed maps and the extents of their
timelines alone.

## Review date

2027-11-15.
