# Hand-derived drawings

Forty-one of the 109 drawings in this directory are derived by hand from
the [drawing specification](../../../docs/drawing.md) and the metrics table
of its two fonts alone. Their `figure.svg` files are never regenerated:
the emitting script compares each with its writer's output instead. Every
other figure in this directory, and every `figure.tex` and `inputs.json`,
is emitted (see [`fixtures/README.md`](../../README.md)). The key
arithmetic of each hand-derived drawing is given below, so that any
implementation can check where it first parts from the specification: the
start and the term that sets it, the largest right edge `R`, the block
`W × H`, and the page.

Section numbers (§) refer to the drawing specification. Every drawing here
is placed alone at `(0, 0)` with the writer's scale `z` = 1, so the page is
`PW = W + 32` by `PH = H + 32` and the drawing lies at `(16, 16)` (§7.1).
An `inputs.json` here supplies an application layer only where the table
names one: the layers are then the defaults, that layer and the manifest's
own `graphical` object (§1), and otherwise the defaults and the manifest's
`graphical` object. Each `inputs.json` names its manifest's canonical YAML
file in the same version's directory, as the table does. Exact values are
given in full; a value as the writer prints it (§7.3) follows an arrow
(`→`).

| Drawing | Manifest | Non-default inputs |
|---|---|---|
| `bare` | `bare.yaml` | none |
| `nested` | `nested.yaml` | none |
| `map` | `map.yaml` | none |
| `flow_control` | `flow_control.yaml` | none |
| `with_region` | `with_region.yaml` | none |
| `styled__score` | `styled__score.yaml` | none (the manifest's own `graphical` object styles it and orders its bands) |
| `nested__length-800-card-spacing-8` | `nested.yaml` | `length` 800, `places` `{clt_1: {spacing: 8}}` |
| `segment_line` | `segment_line.yaml` | none |
| `segment_pages_accolades` | `segment_pages_accolades.yaml` | none |
| `group__group_child_member` | `groups/group_child_member.yaml` | none |
| `group__group_parents_mixed` | `groups/group_parents_mixed.yaml` | none |
| `group__group_grandchild` | `groups/group_grandchild.yaml` | none |
| `unknown_length` | `unknown_length.yaml` | none |
| `unknown_length_empty` | `unknown_length_empty.yaml` | none |
| `unknown_length_locked` | `unknown_length_locked.yaml` | none |
| `unknown_length_child` | `unknown_length_child.yaml` | none |
| `group__group_unknown_length` | `groups/group_unknown_length.yaml` | none |
| `unknown_length_segments` | `unknown_length_segments.yaml` | none |
| `bundle_ungrouped__places` | `bundles/bundle_ungrouped.yaml` | `places` `{score: {x: -60, y: -150, height: 120}}` |
| `bundle_ungrouped__scale` | `bundles/bundle_ungrouped.yaml` | `places` `{recording: {scale: 1.5}}` |
| `bundle_ungrouped__spacing` | `bundles/bundle_ungrouped.yaml` | `spacing` 24, `places` `{score: {spacing: 8}}` |
| `styled_score_flow_inner` | `styled_score_flow_inner.yaml` | none (the manifest's own `graphical` object styles it and orders its bands) |
| `map_child_band_order` | `map_child_band_order.yaml` | none |
| `map_root_band_order` | `map_root_band_order.yaml` | none |
| `joint_rows` | `joint_rows.yaml` | none |
| `map_row_siblings` | `map_row_siblings.yaml` | none |
| `map_row_subslots` | `map_row_subslots.yaml` | none |
| `map_row_moved` | `map_row_moved.yaml` | none |
| `label_float_rounding` | `label_float_rounding.yaml` | none |
| `timestamps` | `timestamps.yaml` | none (each named timestamp's own `display` chooses what it draws) |
| `bundle__bundle_matchstamp_cards` | `bundles/bundle_matchstamp_cards.yaml` | none (the manifest's own `graphical` object names its MatchStamps) |
| `map_band_order_subset` | `map_band_order_subset.yaml` | none (the manifest's own `graphical` object orders the bands of `melody`) |
| `group__group_child_member_stamps` | `groups/group_child_member_stamps.yaml` | none (the manifest's own `graphical` object names its timestamps and its MatchStamp) |
| `group__group_grandchild_parent_on_top` | `groups/group_grandchild_parent_on_top.yaml` | none (the manifest's own `graphical` object orders the bands of `movement`) |
| `group__group_elided_inside` | `groups/group_elided_inside.yaml` | none |
| `group__group_elided_inside__full` | `groups/group_elided_inside.yaml` | the application layer `[{"select": {"element": "elision"}, "set": {"display": "none"}}]` |
| `group__group_grandchild__full` | `groups/group_grandchild.yaml` | the application layer `[{"select": {"element": "elision"}, "set": {"display": "none"}}]` |
| `group__group_grandchild_parent_on_top__full` | `groups/group_grandchild_parent_on_top.yaml` | the application layer `[{"select": {"element": "elision"}, "set": {"display": "none"}}]` (and the manifest's own band order of `movement`) |
| `group__group_parents_mixed__full` | `groups/group_parents_mixed.yaml` | the application layer `[{"select": {"element": "elision"}, "set": {"display": "none"}}]` |
| `group__group_elided_members` | `groups/group_elided_members.yaml` | none (the manifest's own `graphical` object holds its two group elisions) |
| `bundle__bundle_arranged_roots__horizontal` | `bundles/bundle_arranged_roots.yaml` | `arrangement` `{"direction": "horizontal", "order": ["page", "group_3", "group_1", "group_2"]}` |

## Shared quantities

Every manifest is drawn as one block (§8). Twenty-four of these drawings show
one ungrouped root, drawn in its card, twelve one group, drawn as a frame,
`bundle_ungrouped__places`, `bundle_ungrouped__scale` and
`bundle_ungrouped__spacing` three ungrouped roots, each in its own card,
`bundle__bundle_matchstamp_cards` two groups sharing a member, each
drawn as a frame, and `bundle__bundle_arranged_roots__horizontal` three
groups and an ungrouped root side by side. Only the manifests of these
five have a `name`, so only their block has a title; no other manifest
has a `name` or an `id`.

Every element carries its address (§2.2) as the attributes `data-id`,
`data-facet` and `data-part`, each only when the address has its member,
the words of `part` joined by one space (§7.2): the map `tempo` of `map`
carries `data-id="tempo"`, the region `region_1` of `with_region`
`data-id="region_1"`, the symbol of the jump `jump_1` of `flow_control`
`data-id="jump_1" data-part="symbol"`, the label of the region `intro` of
`styled__score` `data-id="intro" data-part="label"`, and the wedge of the named timestamp `timestamp_1` of
`timestamps` `data-id="timestamp_1"`, its name `data-id="timestamp_1"
data-part="name"`, its cross-section line `data-id="timestamp_1"
data-part="line"`, and the ID and coordinate labels of `timestamp_3`
`data-id="timestamp_3" data-part="id"` and `data-id="timestamp_3"
data-part="coordinate"`, whichever root's tree holds the element. A manifest's
title, wherever one is drawn, carries `data-part="name"` alone, and the
block, addressed `{}`, carries none of them. A band draws nothing (§2.1),
so no element carries a band's address.

The specification draws no mark of a root's start or end. Every manifest
here but `timestamps` names instead the origin and length of each root it
draws, as an editor marks them ([`fixtures/README.md`](../../README.md)):
the named timestamp `origin` at 0 and, where the root's length is known,
`length` at that length, each with the `display` `["wedge", "coordinate"]`
(§2), so each draws its wedge, addressed `{"id": X}`, and its coordinate
label, `{"id": X, "part": ["coordinate"]}`, `X` its `timestamp_N`; in a
manifest of one root `origin` is `timestamp_1` and `length` `timestamp_2`.
A member that is a child timeline has its `origin` and `length` as
groupstamps (§2), as an editor gives them when a child joins a group, with
the `display` `["wedge", "coordinate", "cross_section"]`, so each also
draws its cross-section lines (below).
Below, "`origin`'s label" and "`length`'s label" are those coordinate
labels, `0 ♩` and the length in its unit, each its pretty text (§5.2): an
integer on an `int` axis grouped by three (`441 000 smp`), a value in
seconds a clock (`0″`, `5′12.49″`).

Every figure names the fonts `font-family="DejaVu Sans, Noto Music"`
(§7.3), and every width is `A × s / 2048`, `A` the sum of the advances of
the text's code points in `fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json`
(§5.1). The advances used below are 1303 for each digit, 651 for the
space and the point, 1067 `s`, 1995 `m`, 1300 `p`, 1212 `x`, 465 `′` and
765 `″`.

- Constants (§6.2): padding `P` = 8 (also above and below a member
  drawing's content), card padding `K` = 8, frame padding `Q` = 8, gap
  after the manifest's title `F` = 8, gap after the names `G'` = 8
  whenever a name is drawn, card shadow offset 2. The spacings take their
  defaults (§8.6) unless the table states one: the block's spacing, the gap
  between its items at their default `y`, is 8; a frame's spacing `Sf`,
  the gap between its cards, is 8; a card's spacing `S`, the gap between
  bands and the `S` of §6.2, is 4, so the row pitch is `p` = max(10 + 4,
  `h(s)`).
- The block has one horizontal layout (§8.2), computed in item coordinates,
  from the item's left edge and before its scale. The name column starts at
  `n = K` = 8 when the block holds no frame and at `n = Q + K` = 16 when it
  holds one. `N` is the widest row name of any member drawing of the block; a
  title is not a row name. The start `s0` is the largest of `n + N + G'`,
  of `n + wj / 2 − Li × uj` for every centred label `j` of every item `i`,
  and of `n + N + G' + 8 × wa` for every ancestor line `a` of the block that
  runs on to the left; each candidate is listed below only when it decides
  or comes close. The right margin `Mr` is the largest of `e − (s0 + Li)`,
  `e` a member drawing's right edge, and an item's right edge is `Ri = s0 +
  Li + Mr` or its group's title's right edge when that is larger.
- Each item, a group's frame or an ungrouped root's card, lies at its place
  (§8.6), whose `x` is `P` = 8 unless `places` states another, and whose
  `scale` is 1 except for `recording` in `bundle_ungrouped__scale`. Only
  two drawings state a spacing: the card spacing `S` = 8 of `clt_1` in
  `nested__length-800-card-spacing-8`, and in `bundle_ungrouped__spacing`
  the block's spacing 24 and the card spacing `S` = 8 of `score`. No
  spacing multiplies another (§8.6): the block's moves its items, a card's
  widens only the gaps inside that card. A
  position `px` in item coordinates is drawn at `x + px` at scale 1 and at
  `x + scale × px` otherwise, and every length of a scaled item (widths,
  heights, radii, stroke widths, dashes, font sizes) is multiplied by its
  scale. In a block of one item `Mr` is that item's own `R − (s0 + L)`, so
  `Ri` is its largest right edge `R`, its group's title included.
- An ungrouped card spans 0 to `Ri + K` in item coordinates; in a frame, a
  card spans `Q` to `Ri + K` and the frame 0 to `Ri + K + Q`. The sections
  of the one-item drawings give every position as drawn at the default
  place, `x` = 8 plus the item-coordinate value: their `xn` is `8 + n`, 16
  in a card and 24 in a frame, and their `x0` is `8 + s0`.
- Every position is computed in place coordinates (§8.4): `Wb` = (`P` plus
  the largest right edge, a card's shadow (`+ 2`) included) − `Xl`, and
  `Hb` = (`P` plus the largest bottom edge, likewise) − `Yt`, with `Xl` the
  smaller of 0 and the smallest left edge minus `P`, and `Yt` the smaller of
  0 and the smallest top minus `Pt`; `Pt` = `P + h(11) + F` = 28.8046875 when
  the manifest's title is displayed and `P` otherwise. The place origin
  `(Ox, Oy)` = (0 − `Xl`, 0 − `Yt`) is added to every position last. Of
  the hand-derived drawings, twelve reach left of the padding or above `Pt`:
  an item does in `bundle_ungrouped__places`, and an ancestor card (below)
  does in the eleven drawings of a group with a child member
  (`group__group_child_member`, `group__group_parents_mixed`,
  `group__group_grandchild`, `group__group_child_member_stamps`,
  `group__group_grandchild_parent_on_top`, `group__group_elided_inside`,
  `group__group_elided_members` and the four `__full` cases), each to the
  left, and in `group__group_grandchild_parent_on_top` also above `Pt`. In
  every other hand-derived drawing `Xl` = `Yt` = 0 and the origin is (0,
  0), so `Wb = P` plus the largest right edge and `Hb = P` plus the
  largest bottom edge. No drawing here requests a block size, so `W = Wb`
  and `H = Hb`.
- Font measures (§5.1) at size 9: `a(9)` = 8.35400390625, `d(9)` =
  2.12255859375, `h(9)` = 10.4765625; at size 11: `a(11)` =
  10.21044921875, `d(11)` = 2.59423828125, `h(11)` = 12.8046875.
  With the wedges of `origin` and `length` below and their labels at `u` =
  0 and 1 in one tier, the markers band is `w / 2 + 13 + 2 + h(9)` =
  26.9765625 wide for a line of width `w` = 3 (§6.4), and at level −1,
  where it starts at `c` = 0, it reaches as far below the line; a root
  whose end is open has only `origin`, and its markers band is as wide. Only in
  `map_root_band_order` does another band lie between a root's line and its
  markers band.
- A regions band of one row whose labels have the size 9, or that draws no
  label, is `pr − S` = 18.4765625 wide, `pr` = 6 + 2 + `h(9)` + `S` =
  22.4765625 (§6.2); in `styled__score` and `styled_score_flow_inner` its
  label has the size 10, and `h(10)` = 11.640625 makes it 19.640625 wide. In
  the default band order, beyond a root's markers band of 26.9765625 at
  level −1, it starts at 30.9765625, so the root's below side's outer edge
  is `Eb` = 49.453125 when no band lies beyond it. A regions or flow control
  band at level ±1 of a line of width `w` = 3 that reaches nothing on that
  side starts at `S` beyond `w / 2`, 1.5 + 4 = 5.5, so that its content
  keeps the gap `S` from the line's stroke (§6.4).
- The conversion maps bands of the lines of one row, on one side and at one
  level, share one sequence of slots (§6.4, Conversion maps). A map's key
  is its `name` and its `type`, or its `type` alone when it has no name;
  keys with a name come first, by name, then by type. The maps of one key,
  taken line by line in traversal order, each line's own in canonical order
  before those its segments join to it, take that key's sub-slots by first
  fit over the extents of the timelines they span; the sub-slots of the
  keys, in key order, are the slots 1 to `J`. Every band here lies at
  level 1 or −1, so `c0` = 0, and every line with maps is 3 wide but the
  root of `styled__score` and `styled_score_flow_inner`, 4 wide (its map
  centred 2 + 5 − 1 = 6 from it). With `w` = 3 the map in slot `j` is
  centred `w / 2 + j × (g + d) − d / 2` = 1.5 + 5`j` − 1 from its
  line: slot 1 at 5.5, its outline from 4.5 to 6.5 from the line, and slot
  2 at 10.5, from 9.5 to 11.5. Each band of the set is `e = w / 2 + J × (g
  + d)` wide, 6.5 for `J` = 1 and 11.5 for `J` = 2, whichever slots its own
  maps take, and that is the reach of its line's map stack. Only in
  `map_row_siblings` does a row hold two lines with maps; in every other
  drawing a row's slots are those of one line and its segments.
- As the only band above a root's line, the conversion maps band of one key
  holding one map (`J` = 1) puts the line at `y_root` = max(`P` + 6.5, `P`
  + `h(11) / 2`) = `P` + 6.5 = 14.5, since 6.5 exceeds `h(11) / 2` =
  6.40234375 (§6.5); with the markers band below of 26.9765625, `Hm` =
  14.5 + 26.9765625 + 8 = 49.4765625. Both bands start at `c` = 0, against
  the line, so no gap between bands and no card spacing enters this height.
- A root of unknown length is scaled to its reach `λ` (§3.2, §3.4). A child
  of unknown length is drawn on its root's axis and ends, open, at its
  start plus its own reach (rule 5 of §3.4), with its three chevrons beyond
  that end as a root has; a segment of unknown length ends by rules 3 and 4.
  A root's open end lies at `Xe = x0 + L`; its line runs on to `Xr = Xe +
  4w` and the outer of its three chevrons has its tip, and the right edge,
  at `Xr + 5.5w`, `Xr` computed first (§6.6, §6.7): `(x0 + L + 12) + 16.5`
  for `w` = 3, 28.5 past `Xe`.
- A child member `M` is drawn with the faded lines of its ancestors (§8.3).
  An ancestor whose band order puts its children above its line, as the
  default does, has its line below `M`'s, in the ancestor band of the below
  side; one whose order puts them below its line, in
  `group__group_grandchild_parent_on_top` alone, has it above. Below `M`'s
  line its markers band of 26.9765625 lies at level −1, so the ancestor band
  there starts at max(`p0 / 2` = 7, max(26.9765625, 1.5) + `S`) = 30.9765625.
  No ancestor line draws a wedge or a label: no ancestor here names a
  timestamp, and the secondary coordinates of `M`'s groupstamps on it are
  hidden by the defaults (§4) and take no room. So each of its rows has the
  inner half 7 and the outer half 7 (§8.3): the nearest ancestor line lies
  30.9765625 + 7 = 37.9765625 below `M`'s, each further one `Δ` = max(`d`,
  7 + 7) below the one before, `d` the distance of the same two lines in
  the ancestor card as it is drawn, its elisions' label stacks included
  (below): 14 where the card draws no name of an elision between them, and
  33.9765625 in `group__group_grandchild` and `group__group_elided_inside`,
  whose derived names widen the markers band between them (§8.3). `Eb` is
  30.9765625 + 7 + 7 = 44.9765625 for one row, 30.9765625 + 7 + 14 + 7 =
  58.9765625 for two rows 14 apart and 30.9765625 + 7 + 33.9765625 + 7 =
  78.953125 for two rows 33.9765625 apart. `M` with no band above its line
  has `y_root` = `P + h(11) / 2` = 14.40234375, so `Hm` = 14.40234375 +
  44.9765625 + 8 = 67.37890625 with one ancestor row and 81.37890625 or
  101.35546875 with two. The frame a card's proportion reads (§8.9, `Fh`)
  is laid out before its rows align, every `Δ` 14, so with `Hm`
  81.37890625.
- `M`'s `origin` and `length` draw their cross-section lines (§6.6): across
  `M`'s card, from its top to its bottom, less the gap of their wedge and
  label, from the wedge's tip 1.5 to the label's line end 1.5 + 13 + 2 +
  `h(9)` = 26.9765625 below `M`'s line, as two lines, the upper first,
  `origin`'s before `length`'s, the last descriptors of `M`'s member
  drawing; likewise across the ancestor card, below `M`'s row there; and,
  being groupstamps, across the frame, from the top of its topmost member
  card to the bottom of its bottommost, less `M`'s card, after every item
  (§8.5), at the proportion 0 and 1 of the frame, `x0` and `x0 + L`.
- The defaults show every ancestor card (§4, §8.8). For the root `R` of a
  child member `M` of a frame of length `L` = 400 starting at `s0` (in item
  coordinates): `ts` = −(the offsets from `R` down to `M`, summed), `λ`
  `M`'s length, `te = ts + λR`, `us = ts / λ`, `ue = te / λ`, `xs = s0 + L ×
  us`, `xe = s0 + L × ue` and `LA = xe − xs`. The card is `R` drawn as the
  one ungrouped root of a block holding nothing else, at the length `LA`,
  spacing 4 and margin 0: its own start `s0' = K + N' + G'`, `N'` the widest
  name of `R`'s own drawing (every name there at size 11, none faded), and
  `Mr'` the furthest a right edge of that drawing lies past `s0' + LA`. Its
  axis has two seams (§3.2, §8.8 step 2), at the start and the end of
  `M`'s span on `R`: `OL = s0`, the frame's room from its left edge to its
  member drawings, and `OR = Fw − (s0 + L')`, `Fw` the frame's width, the
  room from the members' drawn end to its right edge. Everything left of
  the span, the names included, lies `OL` further left than without them,
  and everything right of it `OR` further right; a position at either seam
  lies on the span's side, and `R`'s line runs whole across both. So the
  card is moved by `dx = (xs − OL) − s0'` without gaps, its left edge
  `xs − OL − s0'`, and its width is `OL + s0' + LA + Mr' + K`, plus `OR`
  where `R` ends right of `M`'s span. It is moved so
  that `R`'s line lies on `R`'s faded line in `M`'s card, and drawn at
  the frame's place, after the block's background and before the frame
  (§8.5). It takes no room here, since the frame is the block's first
  item, which keeps its default `y` (a later item would lie below the
  ancestor cards before it and its own, §8.8 No room), but the block
  grows to hold it, its shadow included, so the origin moves by (0 − `Xl`, 0 − `Yt`) and every other
  element lies where it lies without it, moved by that origin. In each of
  the eleven drawings `R` draws no wedge of its own, and its drawing holds
  one child row above `R`'s line for `M` and one for each timeline between
  them (in `group__group_elided_inside` the row of `first` also holds its
  sibling `second`). In the drawings of default band orders `M` lies outermost
  (§6.4, §6.5): each children band starts `p0 / 2` = 7
  from its timeline's line, each row's line lies `p / 2` = 7 inside its
  row, and `M`'s row draws `M`'s `origin` and `length` wedges and their
  labels in a markers band of 26.9765625 below its line. So `M`'s line
  lies `P + 7` = 15 below the card's top; the next line down, `M`'s parent,
  lies 26.9765625 + 7 = 33.9765625 below it, and every further line 7 + 7
  = 14 below the one before, `R`'s last; the card is `R`'s line plus
  `h(11) / 2` = 6.40234375 plus `P` high. With `R` the parent of `M`, the
  card puts `M`'s row 33.9765625 above `R`'s line where `M`'s card puts
  `R`'s faded line 37.9765625 below `M`'s: the row lies 4 lower than `M`'s
  own line, `S` parting `M`'s markers band from its ancestor band in `M`'s
  card and having no counterpart in `R`'s drawing; every further ancestor
  row lies at exactly its height on the card behind (§8.3).
- The defaults draw an ancestor card with the elisions it derives (§8.9)
  wherever its mode is `auto` with no stored card elision, as in every
  drawing here, and its proportion `r` is below 1, and draw it whole
  otherwise; an application layer hiding every elision, `{"element":
  "elision"}` set to `display` `none`, leaves out no stretch (§2.4), so
  each `__full` case draws its card whole. Every drawing here is drawn for
  the default view 1280 × 720 at scale 1 (§1): `0.8 × VW` = 1024, `0.8 ×
  VH` = 576, `Z` = 0.7142857142857143, the double nearest 5/7, and wherever
  `zG` exceeds `Z`, `zb` = `Z` and `B` = 1024 / (2 × `Z`) = 716.8. `r` =
  min(1, `λ / E × (L' / L)`, (`B − dl`) / (`L × uL`), (`B − dr`) / (`L ×
  uR`)), `σ` = `K + N' + G'`, here equal to `s0'`, `c` = `Fw / 2`, `dl =
  c + σ` and `dr = (Fw + 8) − c`, the seams putting what lies outside
  `M`'s span outside the frame's edges, and `L' = L` but in
  `group__group_elided_members`. With `elision-depths` `auto` every
  depth is chosen: the pieces are taken from `M`'s parent's depth up to
  `R`'s, each stretch outside `M`'s span and outside every earlier one.
  Each piece over `[a, b]` of its timeline's axis has the natural width `n
  = LA × ub − LA × ua` (on `R`'s axis) and is drawn `W = r × n` wide, its
  middle left out: with `h = (W − min(32, W)) / 2` and `k = n / (b − a)`
  its gap leaves out `⌊a + h / k⌋` to `⌈b − h / k⌉`, clamped to `[a, b]`,
  the visible ends `e1` and `e2` keep their natural widths, and the gap is
  `g = W − e1 − e2` wide, its shrink its own natural width less `g`. The
  card's own x is `s0' + (LA × u − D)`, `D` the shrinks of the gaps ending
  at or before the position, and `−OL` and `−OR` for the seams it lies
  right of (on the span's side of), summed from the left; the card is moved by `dx = (xs + DL) −
  s0'`, `DL` the shrinks left of `M` less `OL`, so its width is its elided right edge
  plus `K` and, where it is the leftmost item, the origin is `−dx`, the
  card drawn at `x` = 8 and each of its x at 8 plus its own. A gap is not
  filled and writes no rectangle. Every line of the card whose span holds
  the whole gap stops at its left edge and resumes at its right edge: it is
  written as one `<line>` per piece between the gaps, from the left, a
  piece of no length not written, then its start mark and its end mark,
  each kept where the line really starts or ends at a gap's edge. A gap
  that ends where `M`'s span starts, or starts where it ends, lies wholly
  outside the frame: its edge at the seam lies on its own side, at the
  frame's edge, and the rows running on from it cross the seam whole
  under the frame (§8.9, Carried gaps; §8.8 step 2: everything left of the
  span lies left of the frame, everything right of it right of the frame,
  and `R`'s line runs whole across both seams). The gap draws one ellipsis, three
  `<circle>`s of radius 2 filled `#000000` at `xm − 6`, `xm` and `xm + 6`
  and `ym`, `xm = (x(a) + x(b)) / 2` in the card's own coordinates and
  `ym` the middle of the card's height, addressed `{"id": T, "part":
  ["elision", "ellipsis"]}` (`data-part="elision ellipsis"`), `T` the
  timeline the piece lies on; and, the card's `elision-display` being
  `ellipsis name` (§2.5), its name label, the name of `T` at size 9,
  filled `#6B7280`, centred on `xm` with its baseline at `ym + 4 + a(9)`
  = `ym` + 12.35400390625 (§6.6), addressed `{"id": T, "part":
  ["elision", "name"]}`. The label's room is a stack in `T`'s markers
  band of the card, one tier at its full-scale place (§6.4, Markers), so
  `T`'s markers band below its line is 26.9765625 wide: a row of
  movements so gets the inner half 26.9765625 for 7 and `R` the outer
  edge 26.9765625 below its line for 6.40234375, which moves the card's
  rows and its height, and with them the ancestor rows of `M`'s card that
  lie beyond such a stack: the distance `d` of two rows counts every stack
  the card draws (§8.3). The defaults draw no continuation. The gaps
  follow the card's member drawing, from the left, each its ellipsis then
  its label (§8.5). No element but a line marks a position inside a gap
  here: the cross-section lines of `M`'s `origin` and `length` lie at the
  ends of `M`'s span, which no gap holds, and cross the card from its top
  to its bottom less their gap.

## `bare`

The root `bare` ("Bare", 8 quarters), with nothing else.

- `N` = w(`Bare`, 11) = 25.5771484375.
- `x0` = `xn + N + G'` = 16 + 25.5771484375 + 8 = 49.5771484375 → 49.5771;
  the label `0 ♩` of `origin` gives only 16 + 6.416015625 − 0 = 22.416015625.
- `R` = the arrowhead tip `Xe + 3w` = 449.5771484375 + 9 = 458.5771484375.
- `Hm` = 14.40234375 + 26.9765625 + 8 = 49.37890625.
- `W` = 8 + (10 + 458.5771484375) = 476.5771484375; `H` = 8 + (10 +
  49.37890625) = 67.37890625.
- Page 508.5771484375 × 99.37890625 → **508.5771 × 99.3789**.

## `nested`

The root `clt_1` (16 quarters), its locked child `clt_3` (8 at 4), and
that child's locked child `clt_2` (2 at 3/2). No timeline has a name, so
each row shows its ID.

- `N` = w(`clt_1`, 11) = 25.91552734375, the same for all three.
- `x0` = 16 + 25.91552734375 + 8 = 49.91552734375 → 49.9155.
- `R` = the label `16 ♩` of `length` at 449.91552734375 + 9.279052734375 =
  459.194580078125.
- `Hm` = 43 + 26.9765625 + 8 = 77.9765625.
- `W` = 8 + 469.194580078125 = 477.194580078125; `H` = 8 + 87.9765625 =
  95.9765625.
- Page 509.194580078125 × 127.9765625 → **509.1946 × 127.9766**.

## `map`

The root `melody` ("Melody", 8 quarters) with the map `tempo` and the child
`phrase` ("Phrase", 4 at 2) with the map `ticks`, addressed `{"id":
"tempo"}` and `{"id": "ticks"}`.

- `N` = max(w(`Melody`, 11), w(`Phrase`, 11)) = max(39.53662109375,
  37.36669921875) = 39.53662109375.
- `x0` = 16 + 39.53662109375 + 8 = 63.53662109375 → 63.5366.
- `R` = the arrowhead tip 463.53662109375 + 9 = 472.53662109375.
- `Hm` = 32.5 + 26.9765625 + 8 = 67.4765625.
- `W` = 8 + 482.53662109375 = 490.53662109375; `H` = 8 + 77.4765625 =
  85.4765625.
- Page 522.53662109375 × 117.4765625 → **522.5366 × 117.4766**.

## `flow_control`

The root `flow:quarters` ("Flow control", 16 quarters) with the jump
targets `jump_target_1` (`repeat_start`) at 2 and `jump_target_2`
(`segno`) at 4, the jump `jump_1` at 8 to `jump_target_1`, the break
`break_1` (named `fine`, labelled "Fine", manifestation `fine`) at 12 and
the jump `jump_2` at 16 to `jump_target_2`. The defaults hide the arcs of
the jumps (§4), and with them their labels `Repeat` and `D.S.` (§2.4), so
each element draws its symbol on the symbol row (§6.4, Symbols), black at
size 12: 𝄆 and 𝄋 for the jump targets, 𝄇 (`repeat_end`) and 𝄉
(`dal_segno`) for the jumps' one destination each, and the text `Fine` for
the break. Neither jump has a `name` or a `label`, so neither has a stack;
the break's `label-display` is the initial `name label` (§2.5), so its
stack holds its name `fine` and its label `Fine`, in that order (§6.4,
Flow labels). Above the line no band is present; below it lie the markers
band at level −1 and the flow control band at level −2 (its regions band
is absent).

- `N` = w(`Flow control`, 11) = 66.9775390625.
- `x0` = 16 + 66.9775390625 + 8 = 90.9775390625 → 90.9775; the symbols,
  centred on their positions (§6.7), give at most 16 + 3.3310546875 − 50
  = −30.6689453125 (𝄆, 6.662109375 wide, at `u` = 2/16).
- `R` = the label `16 ♩` of `length` at 490.9775390625 + 18.55810546875 / 2 =
  500.256591796875, beyond the arrowhead tip 499.9775390625, the symbol 𝄉
  (10.0546875 wide) at `x(16)` + 5.02734375 = 496.0048828125 and the
  stack's wider label `Fine` at `x(12)` + 3 + 18.91845703125 =
  412.89599609375.
- Above: no band, so `Ea` = 0 and `y_root` = max(8 + 0, 8 + 6.40234375) =
  14.40234375.
- Below: the markers band of 26.9765625 (Shared quantities); the flow
  control band from 26.9765625 + 4 = 30.9765625. The break's stack, two
  lines high, fills one flow label tier of two lines, `T` = 2, so the flow
  row lies at `f0` = 30.9765625 + 2 × 10.4765625 = 51.9296875, and the
  symbol row beyond it is `Hs` = 2 + `h(12)` + 2 = 17.96875 wide, the symbol gap 2 on
  both sides of the glyph boxes (§6.2). No fork and no arc is drawn, so the
  band is 20.953125 + 17.96875 = 38.921875 wide and `Eb` = 30.9765625 +
  38.921875 = 69.8984375.
- `Hm` = 14.40234375 + 69.8984375 + 8 = 92.30078125 → 92.3008.
- Drawn, each ordinate the card's top 8 plus its item-coordinate value: the
  line at 22.40234375 → 22.4023 and the flow row at 74.33203125 → 74.332.
- The break at `x(12)` = 390.9775390625 → 390.9775, from the flow row
  to `P`, drawn at 16, dotted red (`#D62728`, 1.5 wide, dashed `1.5 1.5`,
  §4). Its stack starts at 393.9775390625 → 393.9775: the name `fine` on
  line 1, nearest the flow row, its baseline at 74.33203125 −
  2.12255859375 = 72.20947265625 → 72.2095, and the label `Fine` on line
  2, `h(9)` further in, at 74.33203125 − 10.4765625 − 2.12255859375 =
  61.73291015625 → 61.7329.
- The symbols, after the stack and in the order of the band's elements
  (§7.2), are centred on `x(2)` = 140.9775390625, `x(4)` =
  190.9775390625, `x(8)` = 290.9775390625, `x(12)` and `x(16)` =
  490.9775390625, each with its baseline at the flow row plus the symbol
  gap plus `a(12)`, 8 + 14.40234375 + (51.9296875 + 2) + 11.138671875 =
  87.470703125 → 87.4707.
- `W` = 8 + 510.256591796875 = 518.256591796875; `H` = 8 + (10 +
  92.30078125) = 110.30078125.
- Page 550.256591796875 × 142.30078125 → **550.2566 × 142.3008**.

## `with_region`

The root `clt_1` (12 quarters) with two children and the region
`region_1` ("theme", 2 to 6).

- `N` = 25.91552734375 (`clt_1`, `clt_2`, `clt_3` alike).
- `x0` = 16 + 25.91552734375 + 8 = 49.91552734375 → 49.9155.
- `R` = the label `12 ♩` of `length` at 459.194580078125.
- `Hm` = 43 + 49.453125 + 8 = 100.453125.
- `W` = 8 + (10 + 459.194580078125) = 477.194580078125; `H` = 8 + (10 +
  100.453125) = 118.453125.
- Page 509.194580078125 × 150.453125 → **509.1946 × 150.4531**.

## `styled__score`

The root `score` (8 quarters) with the children `a` (hidden) and `b`, the
map `ticks`, the region `intro` and the jump `da-capo` from 8 to the
timeline `score` itself, styled by its own rules: the root's line is 4
wide and its name, at size 12, reads `Styled score`. Its band order
`children`, `markers`, `line`, `conversion_maps`, `regions`,
`flow_control` (§6.4) lays the markers band against the line above it and
the children band beyond, and below it the conversion maps band, then the
regions band and the flow control band. The defaults hide the jump's arc
and with it the arc's label `D.C.` (§2.4, §4); its one destination's
manifestation `da_capo` draws the symbol 𝄊 (§6.4, Symbols), black at size
12 (the default rule selecting `symbol` sets its `fill`, and no rule of
the manifest selects a symbol), and the jump has neither `name` nor
`label`, so no stack.

- `N` = max(w(`Styled score`, 12), w(`b`, 11)) = max(74.080078125,
  6.982421875) = 74.080078125.
- `x0` = 16 + 74.080078125 + 8 = 98.080078125 → 98.0801.
- `R` = the arrowhead tip `Xe + 3w` = 498.080078125 + 12 = 510.080078125,
  beyond the symbol 𝄊 (10.763671875 wide) at 498.080078125 + 5.3818359375
  = 503.4619140625.
- Above, as in `styled_score_flow_inner`: the markers band of 28.640625,
  the children band from 32.640625, `b`'s row with the halves 7 and 7, `Ea`
  = 46.640625 and `y_root` = 54.640625; the root's line is drawn at
  62.640625 → 62.6406 and `b`'s at 23.
- Below: the conversion maps band at level −1 from `c` = 0 reaches `e` =
  2 + 5 = 7 (the map's outline from 67.640625 → 67.6406 to 69.640625 →
  69.6406). The regions band at level −2 starts at 7 + 4 = 11; its one row,
  its label at size 10, has `pr1` = 6 + 2 + `h(10)` + 4 = 23.640625, so it
  is 19.640625 wide and ends at 30.640625. The flow control band at level
  −3 starts at 30.640625 + 4 = 34.640625: no stack (`T` = 0), so the flow
  row lies at its start, `f0` = 34.640625, and the symbol row is `Hs` = 2 + `h(12)` + 2 = 17.96875
  wide; no fork and no arc, so the band is 17.96875 wide and `Eb` =
  52.609375.
- The region `intro` runs from `x(0)` to `x(2)` = 198.080078125, its tip at
  `x(1)` = 148.080078125: its arms at 62.640625 + 11 = 73.640625 →
  73.6406, its tip at 79.640625 → 79.6406, its label's baseline at
  62.640625 + (11 + 6 + 2) + `a(10)` = 90.9228515625 → 90.9229.
- The symbol 𝄊 is centred on `x(8)` = 498.080078125 → 498.0801, its
  baseline at 62.640625 + (34.640625 + 2) + `a(12)` = 110.419921875 →
  110.4199.
- `Hm` = 54.640625 + 52.609375 + 8 = 115.25.
- `W` = 8 + 520.080078125 = 528.080078125; `H` = 8 + (10 + 115.25) =
  133.25.
- Page 560.080078125 × 165.25 → **560.0801 × 165.25**.

## `nested__length-800-card-spacing-8`

`nested` with `L` = 800 and the card spacing `S` = 8 of its one card,
`places` `{clt_1: {spacing: 8}}` (§8.6). `S` is the gap between bands and
enters the row pitch, `p` = `p0` = max(10 + 8, `h(11)`) = 18 (§6.2); the
padding `P` = 8 above and below the content does not change with it
(§6.5), and neither does the horizontal layout.

- `x0` = 16 + 25.91552734375 + 8 = 49.91552734375 → 49.9155, as in
  `nested`.
- `R` = the label `16 ♩` of `length` at 49.91552734375 + 800 + 9.279052734375 =
  859.194580078125.
- The children bands of `clt_1` and of `clt_3` lie above their lines,
  which reach nothing there, so each starts at the larger of `S` beyond
  `w / 2`, 1.5 + 8 = 9.5, and `p / 2` = 9: 9.5 (§6.4, Where a band lies).
  At `S` = 4 the half pitch, 7, was the larger.
- The row of `clt_2` has the halves 9 and 9, so `clt_2`'s line lies 9.5 +
  9 = 18.5 above `clt_3`'s, and `clt_3`'s band is 18 wide: `clt_3`'s
  above edge is 9.5 + 18 = 27.5, and its below edge 0. The row of `clt_3`
  has the inner half max(9, 0) = 9 and the outer half max(9, 27.5) =
  27.5, so `clt_3`'s line lies 9.5 + 9 = 18.5 above `clt_1`'s, the band
  is 9 + 27.5 = 36.5 wide, and `Ea` = 9.5 + 36.5 = 46.
- `y_root` = max(8 + 46, 8 + 6.40234375) = 54. Below, the markers band
  lies against the line from `c` = 0 and reaches `Eb` = 26.9765625
  (Shared quantities), whatever `S`. `Hm` = 54 + 26.9765625 + 8 =
  88.9765625 → 88.9766.
- Drawn, each line at the card's top 8 plus its ordinate: `clt_1` at 62,
  `clt_3` at 62 − 18.5 = 43.5 and `clt_2` at 43.5 − 18.5 = 25; the names'
  baselines at each line's ordinate plus (`a(11)` − `d(11)`) / 2 =
  3.80810546875, 65.80810546875 → 65.8081, 47.30810546875 → 47.3081 and
  28.80810546875 → 28.8081; the diamonds' corners `1.2w` = 3.6 above and
  below their lines, from 39.9 to 47.1 (`clt_3`) and from 21.4 to 28.6
  (`clt_2`); the wedges from 63.5 to 76.5, and their labels' baseline at
  (62 + 16.5) + `a(9)` = 86.85400390625 → 86.854.
- `W` = 8 + 869.194580078125 = 877.194580078125; `H` = 8 + (10 +
  88.9765625) = 106.9765625.
- Page 909.194580078125 × 138.9765625 → **909.1946 × 138.9766**.

## `segment_line`

The nested segment line `form` ("Form", 32 quarters) of the segments `a`
(8), `b` (12) and `c` (12), each a segment line itself; `b` holds `b1` and
`b2` (6 each).

- `N` = w(`Form`, 11) = 28.294921875.
- `x0` = 16 + 28.294921875 + 8 = 52.294921875 → 52.2949; the segment
  labels give at most `A` −30.921630859375 and `origin`'s label
  22.416015625.
- `R` = the label `32 ♩` of `length` at 461.573974609375, beyond the arrowhead tip
  461.294921875.
- `Hm` = 60.953125 + 26.9765625 + 8 = 95.9296875.
- `W` = 8 + ((8 + 2) + 461.573974609375) = 479.573974609375; `H` = 8 +
  105.9296875 = 113.9296875.
- Page 511.573974609375 × 145.9296875 → **511.574 × 145.9297**.

## `segment_pages_accolades`

The unlocked segment line `pages` ("Pages", 7016 pixels) of four pages of
1754 pixels, each a segment line of four accolades of 400, 450, 452 and 452
pixels. A row of segment lines has no name, so `Pages` is the only one.

- `N` = w(`Pages`, 11) = 32.85498046875.
- `x0` = 16 + 32.85498046875 + 8 = 56.85498046875 → 56.855; the label of
  the first accolade, `u` = 200 / 7016, gives only 7.460528557493586.
- `R` = the label `7 016 px` of `length`, its digits grouped by three on
  the `int` axis (§5.2): the advances 4 × 1303 + 2 × 651 + 1300 + 1212 =
  9026, so it is 9026 × 9 / 2048 = 39.6650390625 wide and ends at
  456.85498046875 + 19.83251953125 = 476.6875.
- `Hm` = 60.953125 + 26.9765625 + 8 = 95.9296875.
- `W` = 8 + (10 + 476.6875) = 494.6875; `H` = 8 + 105.9296875 =
  113.9296875.
- Page 526.6875 × 145.9296875 → **526.6875 × 145.9297**.

## `group__group_child_member`

The group "Second half" in the display order `second-half`, `recording`:
the child `second-half` (8 quarters at 8) of the piece `piece` (16
quarters), and the root `recording` (10.0 seconds). The member
`second-half` carries the ancestor line of `piece` below its own line
(Shared quantities), which runs on to the left, and `piece` is drawn in
its ancestor card behind the frame (§8.8), with the elision it derives
(§8.9). The bullets before the
ancestor card's give positions in place coordinates; drawn, each lies
447.99018554687495 further right.

- `xn` = 24 (a frame). `N` = w(`Second half`, 11) = 64.61962890625, of
  `Second half`, `Piece` and `Recording`.
- `x0` = the chevron term `xn + N + G' + 8 × wa` = 24 + 64.61962890625 + 8
  + 24 = 120.61962890625 → 120.6196, above `xn + N + G'` =
  96.61962890625; the outer chevron's tip `x0 − 8w` lies exactly at the
  latter.
- The labels of `recording` are clocks (§5.2): `origin`'s `0″` (advances
  1303 + 765 = 2068, 9.087890625 wide) and `length`'s `10″` (2 × 1303 + 765
  = 3371, 14.81396484375 wide).
- `R` = the arrowhead tips of `piece`'s ancestor line, which ends with
  `second-half` (`te` = −8 + 16 = 8 = `λ`), and of `recording`, both at
  520.61962890625 + 9 = 529.61962890625, beyond the label `10″` of
  `length` at 520.61962890625 + 7.406982421875 = 528.026611328125. Each
  card is 529.61962890625 − 8 = 521.61962890625 → 521.6196 wide and the
  frame 529.61962890625 + 8 = 537.61962890625 → 537.6196.
- `Hm` = 14.40234375 + 44.9765625 + 8 = 67.37890625 (`second-half`,
  nothing above its line, below it its markers band and its ancestor band
  of one row, Shared quantities) and 49.37890625 (`recording`); the frame
  is 8 + 12.8046875 + 4 + 67.37890625 + 8 + 49.37890625 + 8 = 157.5625
  high, `second-half`'s card at 8 + 8 + 12.8046875 + 4 = 32.8046875 →
  32.8047 and `recording`'s at 32.8046875 + 67.37890625 + 8 = 108.18359375
  → 108.1836.
- Drawn, each line at its card's top plus `y_root`: `second-half` at
  32.8046875 + 14.40234375 = 47.20703125 → 47.207, its wedges from their
  tips at 48.707 to their bases at 61.707 and the baseline of its labels
  `0 ♩` and `8 ♩` at 47.20703125 + 24.85400390625 = 72.06103515625 →
  72.061; `piece`'s ancestor line 37.9765625 below it, at 85.18359375 →
  85.1836, with nothing on it; the names `Second half` at 47.20703125 +
  3.80810546875 = 51.01513671875 → 51.0151 and `Piece`, at size 9, at
  85.18359375 + 3.11572265625 = 88.29931640625 → 88.2993; `recording` at
  108.18359375 + 14.40234375 = 122.5859375 → 122.5859.
- The cross-section lines of `origin` and `length` (Shared quantities), at
  488.6196 and 888.6196 drawn: across `second-half`'s card from 32.8047 to
  48.707 and from 74.1836 to 100.1836 (32.8046875 + 67.37890625 =
  100.18359375); across the frame from `second-half`'s card's bottom to
  the bottom of `recording`'s, 100.1836 to 157.5625, the last two
  descriptors.
- The ancestor card of `piece` (Shared quantities), aligned to
  `second-half`: `s0` = 112.61962890625 (`x0` less the place's 8), `ts` =
  −8, `λ` = 8, `te` = −8 + 16 = 8, so `us` = −1, `ue` = 1, `xs` =
  −287.38037109375, `xe` = 512.61962890625 and `LA` = 800. `N'` =
  w(`Second half`, 11) = 64.61962890625 (wider than `Piece`, 29.2724609375),
  `s0'` = 80.61962890625; `Mr'` = the arrowhead of `piece`, `3w` = 9,
  beyond the half of the label `8 ♩` of `length` at the end of
  `second-half` (2920 advances, 12.83203125 wide). The seams: `OL` =
  112.61962890625 and `OR` = 537.61962890625 − 512.61962890625 = 25, at
  `piece`'s 8 and 16; `piece` ends with `second-half`, at the second
  seam, on the span's side, so nothing lies right of the span.
- Derived (Shared quantities): `Fw` = 537.61962890625, `Fh` = 157.5625,
  `zG` = min(4, 1.9046923604394008, 3.6556921856406186) =
  1.9046923604394008, `zb` = `Z`, `B` = 716.8, `c` = 268.809814453125,
  `σ` = 80.61962890625, `dl` = 349.429443359375; `EL` = 8, `ER` = 0, `E`
  = 8, `uL` = 1: `r` = min(1, 1, (716.8 − 349.429443359375) / 400) =
  0.9184263916015624, set by the left term, the right one left out.
  Depth 1 gives `piece` 0–8, natural width 400 at `LA` = 800 (`k` = 50),
  `W` = 367.37055664062495, `h` = 167.68527832031248 and `h / k` =
  3.3537055664062496: the gap leaves out `piece` 3–5, the visible ends
  150 each, the gap 67.37055664062495 wide of 100, shrink
  32.629443359375045. `DL` = 32.629443359375045 − 112.61962890625 =
  −79.99018554687495, `dx` = (−287.38037109375 − 79.99018554687495) −
  80.61962890625 = −447.99018554687495, the card's place
  −439.99018554687495; own x(3) = 230.61962890625, x(5) =
  297.99018554687495, x(8) = 560.609814453125 and x(16) =
  960.609814453125, the card 960.609814453125 + 9 + 8 = 977.609814453125
  → 977.6098 wide. Vertically the stack `Piece` of the gap in `piece`'s
  markers band makes the card 48.9765625 + 26.9765625 + 8 = 83.953125 →
  83.9531 high, `piece`'s line still 48.9765625 below its top.
  `piece`'s ancestor line in `second-half`'s card lies at 85.18359375, so
  the card's top is 85.18359375 − 48.9765625 = 36.20703125 → 36.207, its
  bottom 120.16015625 and with its shadow 122.16015625, inside the frame.
  `Xl` = −447.99018554687495 and `Yt` = 0: the origin is
  (447.99018554687495, 0), and the card is drawn at (8, 36.207), its
  shadow at (10, 38.207). In it (drawn): `piece`'s line at 85.1836 from
  8 + 80.61962890625 = 88.61962890625 → 88.6196 to the gap at
  238.61962890625 → 238.6196 and from 305.99018554687495 → 305.9902 to
  968.609814453125 → 968.6098, its arrowhead's tip at 977.6098;
  `second-half`'s row at 36.20703125 + 15 = 51.20703125 → 51.207 from
  568.6098, where its own line starts in the frame (120.61962890625 +
  447.99018554687495), to 968.6098, the wedges of `origin` and `length`
  and their labels `0 ♩` and `8 ♩` (baseline 76.061) at its ends, and
  their cross-section lines from 36.207 to 52.707 and from 78.1836 to the
  card's bottom 120.1602; the names `Second half` and `Piece` at 8 + `K`
  = 16, with the baselines 55.0151 and 88.9917; then the gap's ellipsis
  at `xm` = 272.3049072265625 (circles at 266.3049, 272.3049 and
  278.3049) and `ym` = (36.20703125 + 120.16015625) / 2 = 78.18359375 →
  78.1836, and its label `Piece` at 272.3049 with the baseline
  90.53759765625 → 90.5376.
- `W` = 8 + (529.61962890625 + 8 + 8) + 447.99018554687495 =
  1001.609814453125, the frame's right edge beyond the card's shadow at
  −439.99018554687495 + 977.609814453125 + 2 = 539.61962890625; `H` = 8 +
  (8 + 157.5625) = 173.5625.
- Page 1033.609814453125 × 205.5625 → **1033.6098 × 205.5625**.


## `group__group_parents_mixed`

The group "Exposition" in the display order `exposition`, `take`,
`system`, `audio`: three child members of different parents (the
exposition, 32 quarters at 16 in the locked sonata of 48; the take, 25.5
seconds at 30.0 in the session of 90.0 seconds; the system, 600 pixels at 0
in the page of 1754) and the root `audio` (1323000 samples). `take` holds
the map `cmap_1` (`SecondsToSamples`) and `audio` the map `cmap_2`
(`SamplesToSeconds`), addressed `{"id": "cmap_1"}` and `{"id": "cmap_2"}`
(§2.2), although `session`, which holds `take`, is drawn only as an
ancestor line. Both maps lie above their lines and take the
colour of the physical domain they convert to, the first dotted `1 1`
(samples are discrete), the second solid (§4). The roots `sonata`,
`session` and `page` are drawn in their ancestor cards behind the frame
(§8.8), `session` and `page` with the elisions they derive (§8.9) and every
card whole in `group__group_parents_mixed__full`, and `take`'s map is drawn
again in `session`'s. The bullets before the ancestor cards' give
positions in place coordinates; drawn, each lies 273.0302734375 further
right, and 528.5579618566177 in the `__full` case.

- `xn` = 24. `N` = w(`Exposition`, 11) = 57.0302734375.
- `x0` = the chevron term 24 + 57.0302734375 + 8 + 24 = 113.0302734375 →
  113.0303, set by the ancestor lines of `sonata` and `session`, which run
  on to the left; `page` starts with its member and does not.
- The labels in seconds are clocks (§5.2): `take`'s `origin`'s and
  `length`'s, `0″` and `25.5″` (the advances 2 × 1303 + 651 + 1303 + 765 =
  5325, 23.40087890625 wide).
- `R` = the label `1 323 000 smp` of `length`, its digits grouped by three
  on the `int` axis (§5.2): the advances 7 × 1303 + 3 × 651 + 1067 + 1995
  + 1300 = 15436, 15436 × 9 / 2048 = 67.833984375 wide, ending at
  513.0302734375 + 33.9169921875 = 546.947265625, beyond the outer chevron
  tips of `session` and `page` at 537.0302734375 and the label `25.5″` at
  513.0302734375 + 11.700439453125 = 524.730712890625. Each map spans its
  member's line, from `x0` to `x0 + L` = 513.0302734375, and reaches no
  further right. Each card is 546.947265625 − 8 = 538.947265625 →
  538.9473 wide and the frame 546.947265625 + 8 = 554.947265625 →
  554.9473.
- The map stacks: each holds one map, 5.5 above its member's line and
  reaching `e` = 6.5 (Shared quantities). Neither member draws a wedge
  above, so above lies its conversion maps band alone, reaching 6.5; below,
  every member's markers band reaches 26.9765625.
- `audio` has no other band above: `Ea` = 6.5, so `y_root` = 14.5 and `Hm`
  = 49.4765625 (Shared quantities).
- Every ancestor line lies below its member, 37.9765625 below the member's
  line, and every child member's `Eb` is 44.9765625 (Shared quantities).
  `take`'s map lies above `take`'s line, on the side away from `session`'s:
  `Ea` = 6.5, `y_root` = 14.5 and `Hm` = 14.5 + 44.9765625 + 8 =
  67.4765625. `exposition` and `system` have no band above: `y_root` =
  14.40234375 and `Hm` = 67.37890625. Every ancestor line so lies
  52.37890625 below its card's top, `take`'s 52.4765625.
- The frame's rows (§8.4): the cards start at 8 + (8 + 12.8046875 + 4) =
  32.8046875 → 32.8047 (`exposition`) and each the frame's spacing `Sf` =
  8 below the one before, at 108.18359375 → 108.1836 (`take`),
  183.66015625 → 183.6602 (`system`) and 259.0390625 → 259.0391 (`audio`);
  the frame is 8 + 12.8046875 + 4 + 67.37890625 + 8 + 67.4765625 + 8 +
  67.37890625 + 8 + 49.4765625 + 8 = 308.515625 → 308.5156 high.
- Drawn, each line at its card's top plus `y_root` and each ancestor line
  37.9765625 below its member's: `exposition` at 47.20703125 → 47.207 and
  `sonata` at 85.18359375 → 85.1836; `take` at 122.68359375 → 122.6836,
  its map's outline from 116.18359375 → 116.1836 to 118.18359375 →
  118.1836, and `session` at 160.66015625 → 160.6602; `system` at
  198.0625 and `page` at 236.0390625 → 236.0391; `audio` at 273.5390625 →
  273.5391, its map's outline from 267.0390625 → 267.0391 to 269.0390625 →
  269.0391.
- The six groupstamps, `origin` and `length` of each child member, lie at
  the proportions 0 and 1 of the frame, all at `x0` → 281.0303 and `x0 +
  L` → 681.0303 drawn: each crosses its own card, less its gap 1.5 to
  26.9765625 below its member's line, and the frame from the top of
  `exposition`'s card, 32.8047, to the bottom of `audio`'s, 308.5156, less
  its member's card, written after `audio`'s card, `timestamp_3` to
  `timestamp_8` in turn: `exposition`'s from 100.1836 down, `system`'s
  from 32.8047 to 183.6602 and from 251.0391 down, `take`'s from 32.8047
  to 108.1836 and from 175.6602 down.
- The ancestor cards (Shared quantities), one per root in the members'
  display order, `s0` = 105.0302734375 (`x0` less the place's 8), each
  with the seams `OL` = 105.0302734375 and `OR` = 554.947265625 −
  505.0302734375 = 49.9169921875 at the ends of its member's span:
  - `sonata`, aligned to `exposition`: `ts` = −16, `λ` = 32, `λR` = 48, `te`
    = 32, `us` = −0.5, `ue` = 1, `xs` = −94.9697265625, `LA` = 600; `N'` =
    w(`Exposition`, 11) = 57.0302734375, `s0'` = 73.0302734375, left
    −273.0302734375, place −265.0302734375; `sonata` is locked and ends in
    a circle, at the second seam with `exposition`, so `Mr'` is the half of
    the label `32 ♩` of `length` at the end of `exposition` (4223 advances
    at size 9, 18.55810546875 wide), 9.279052734375: the card is
    105.0302734375 + 73.0302734375 + 600 + 9.279052734375 + 8 =
    795.339599609375 → 795.3396 wide.
  - `session`, aligned to `take`, in seconds (floats, binary64): `ts` =
    −30.0, `λ` = 25.5, `te` = 60.0, `us` = −30.0 / 25.5 =
    −1.1764705882352942, `ue` = 60.0 / 25.5 = 2.3529411764705883, `xs` =
    105.0302734375 + 400 × `us` = −365.5579618566177, `xe` =
    1046.2067440257354, `LA` = `xe − xs` = 1411.7647058823532; `N'` =
    w(`Session`, 11) = 41.9697265625, `s0'` = 57.9697265625, left
    −528.5579618566177, place −520.5579618566177; `Mr'` = the arrowhead 9:
    the card is 1641.6816980698532 → 1641.6817 wide, `OL` and `OR`
    included. `take`'s map lies
    above `take`'s row, 4.5 to 6.5 from its line, inside the row's `p / 2`.
  - `page`, aligned to `system`, in pixels (`int`): `ts` = 0, `λ` = 600,
    `λR` = 1754, `us` = 0, `ue` = 1754 / 600 = 2.9233333333333333, `xs` =
    `s0`, `xe` = 1274.3636067708333, `LA` = 1169.3333333333333; `N'` =
    w(`System`, 11) = 41.01904296875, `s0'` = 57.01904296875, left
    −57.01904296875, place −49.01904296875 (`page` starts at the first
    seam, on the span's side, its names `OL` further left); `Mr'` = 9: the
    card is 1398.2996419270833 → 1398.2996 wide, `OL` and `OR` included.
  Each card's top is its member's ancestor line less 48.9765625 (in
  `session`'s card, too, `take`'s row has the inner half 26.9765625, its
  markers band, and the outer half 7, its map reaching only 6.5): 85.18359375,
  160.66015625 and 236.0390625 give 36.20703125 → 36.207, 111.68359375 →
  111.6836 and 187.0625, each 63.37890625 → 63.3789 high, and each
  member's row lies 15 below its card's top, at 51.207, 126.6836 and
  202.0625, its `origin` and `length` crossing the card. Whole
  (`__full`): `Xl` = −520.5579618566177 − 8 and `Yt` = 0: the origin is
  (528.5579618566177, 0), and the cards are drawn at `x` 263.5276884191177
  → 263.5277, 8 and 479.5389188878677 → 479.5389, the lines of `sonata`
  from 336.558 to 1041.5882, of `session` from 65.9697, whole across both
  seams, to 1632.6817 and of `page` from 641.5882 to 1860.8386, each
  member's row in them from 641.5882, where its own line starts in the
  frame. The lowest card, `page`'s, ends with its shadow at 252.44140625,
  inside the frame. `W` = 8 + 1351.2805989583333 + 528.5579618566177 =
  1887.838560814951, the right edge of `page`'s card with its shadow,
  −49.01904296875 + 1398.2996419270833 + 2, beyond the frame's
  554.947265625 + 8; `H` = 8 + (8 + 308.515625) = 324.515625; the page
  1919.838560814951 × 356.515625 → **1919.8386 × 356.5156**.
- Derived (Shared quantities): `Fw` = 554.947265625, `Fh` = 308.515625,
  `zG` = min(4, 1024 / `Fw`, 576 / `Fh`) = 1.8452203721496623, so `zb` =
  `Z`, `B` = 716.8 and `c` = 277.4736328125; `dr` = 285.4736328125 for
  every card.
  - `sonata` (`σ` = 73.0302734375): `EL` = 16, `ER` = 0, `λ / E` = 2,
    `dl` = 350.50390625 and the left term (716.8 − 350.50390625) /
    (400 × 0.5) = 1.8314804687499997, so `r` = 1: drawn whole.
  - `session` (`σ` = 57.9697265625, floats): `EL` = 30.0, `ER` = 60.0 −
    25.5 = 34.5, `E` = 64.5, `dl` = 335.443359375; `r` = min(1, 25.5 /
    64.5 = 0.3953488372093023, 0.8103828613281249, 0.7970161132812498) =
    0.3953488372093023. Depth 1 holds `session` alone: the pieces
    `session` 0.0–30.0 and 55.5–90.0, natural widths 470.5882352941177 and
    541.1764705882354 at `LA` = 1411.7647058823532, `W` = 186.046511627907
    and 213.95348837209303, `k` = 15.686274509803923 for both and `h / k`
    = 4.910232558139535 and 5.799767441860465: the gaps leave out
    `session` 4.0–26.0 and 61.0–85.0, the visible ends 62.7450980392157 and
    62.74509803921569, 86.27450980392166 and 78.43137254901967, the gaps
    60.55631554947561 and 49.2476060191517 wide of 345.0980392156863 and
    376.47058823529403, shrinks 284.5417236662107 and 327.2229822161423,
    `DL` = 284.5417236662107 − 105.0302734375 = 179.51145022871071. The
    card is 1029.9169921875 → 1029.917 wide, `dx` = −244.01623819040697,
    its place −236.01623819040697.
  - `page` (`σ` = 57.01904296875, `int`): `EL` = 0, `ER` = 1154, `dl` =
    334.49267578125; `r` = min(1, 600 / 1154 = 0.5199306759098787,
    0.5606495240738734) = 0.5199306759098787, the left term left out. The
    piece `page` 600–1754, natural width 769.3333333333333, `W` = 400,
    `h` = 184, `k` = 0.6666666666666666 and `h / k` = 276: its gap leaves
    out `page` 876–1478, the visible ends 184 each, the gap 32 wide,
    shrink 369.33333333333326, `DL` = −105.0302734375, `dx` =
    −57.01904296875 as whole. The card is 1028.96630859375 → 1028.9663
    wide, its place −49.01904296875.
  Vertically the stacks `Session`, of the two gaps on `session`, and
  `Page` take the markers bands below those roots' lines, 26.9765625
  wide, so those two cards are 48.9765625 + 26.9765625 + 8 = 83.953125 →
  83.9531 high, their tops where they were, their bottoms at
  195.63671875 and 271.015625, the latter with its shadow 273.015625,
  inside the frame; the cross-section lines of `take`'s and `system`'s
  `origin` and `length` run down to those bottoms.
  The leftmost card is still `sonata`'s: `Xl` = −273.0302734375, `Yt` = 0,
  the origin (273.0302734375, 0). Drawn: the cards at `x` 8,
  37.014035247093034 → 37.014 and 224.01123046875 → 224.0112; `sonata`'s
  line from 81.0303, whole across both seams, to its circle at 786.0605;
  `session`'s from 94.9838 to 1049.931 (its arrowhead's tip at 1058.931)
  in three pieces, stopping at the gaps 157.7289–218.2852 and
  922.252–971.4997 and running whole across both seams between them;
  `page`'s from 386.0605 to 1235.9775 (tip 1244.9775) in two, stopping
  at the gap 1019.9775–1051.9775; each member's row in them from
  386.0605, where its own line starts in the frame, and `take`'s map over
  `take`'s row from 386.0605 to 786.0605. One ellipsis per gap at the
  middle of its card: `session`'s centred at 188.007 and 946.8759 and at
  `ym` = (111.68359375 + 195.63671875) / 2 = 153.66015625 → 153.6602,
  each with its label `Session` below it with the baseline 166.0142, and
  `page`'s centred at 1035.9775 and at `ym` = 229.0390625 → 229.0391, its
  label `Page` with the baseline 241.3931. `W` = 8 + 981.947265625 +
  273.0302734375 = 1262.9775390625, the right edge of `page`'s card with
  its shadow, −49.01904296875 + 1028.96630859375 + 2; `H` = 324.515625.
- Page 1294.9775390625 × 356.515625 → **1294.9775 × 356.5156**.

## `group__group_grandchild`

The group "Theme" in the display order `theme`, `recording`: the grandchild
`theme` (8 quarters at 8 in the movement of 16 quarters at 16 in the score
of 64) and the root `recording` (12.0 seconds). `theme` carries two
ancestor lines below its own, `movement` nearer and `score` beyond it
(Shared quantities), both running on to the left, and
`score` is drawn in its ancestor card behind the frame (§8.8), with the
elisions it derives (§8.9) and whole in `group__group_grandchild__full`.
The bullets before the ancestor card's give positions in place
coordinates; drawn, each lies 245.69419642857133 further right, and
1274.265625 in the `__full` case.

- `xn` = 24. `N` = w(`Recording`, 11) = 55.70361328125, of `Theme`,
  `Score`, `Movement` and `Recording`.
- `x0` = the chevron term 24 + 55.70361328125 + 8 + 24 = 111.70361328125 →
  111.7036.
- `R` = the outer chevron tip of `score`, which also runs on to the right,
  `Xr + 4w` = (111.70361328125 + 400 + 12) + 12 = 535.70361328125 (§8.3),
  beyond the label of `recording`'s `length`, the clock `12″` (§5.2; the
  advances 2 × 1303 + 765 = 3371, 14.81396484375 wide), at 511.70361328125
  + 7.406982421875 = 519.110595703125. `origin`'s label is `0″`.
- Before the rows align on the card behind (§8.3), as `__full`, which
  draws no elision, draws them, and as the proportion reads the frame
  (§8.9, `Fh`): `Hm` = 14.40234375 + 58.9765625 + 8 = 81.37890625 (`theme`, nothing
  above its line, below it its markers band and its ancestor band of two
  rows, Shared quantities) and 49.37890625 (`recording`); the frame is 8 +
  12.8046875 + 4 + 81.37890625 + 8 + 49.37890625 + 8 = 171.5625 high,
  `theme`'s card at 32.8046875 → 32.8047 and `recording`'s at 32.8046875 +
  81.37890625 + 8 = 122.18359375 → 122.1836.
- Drawn so (`__full`): `theme`'s line at 32.8046875 + 14.40234375 = 47.20703125 →
  47.207; `movement`'s ancestor line 37.9765625 below it at 85.18359375 →
  85.1836, `score`'s `Δ` = 14 further at 99.18359375 → 99.1836, nothing on
  either; the names `Theme` at 51.0151, `Movement` at 88.2993 and `Score`
  at 99.18359375 + 3.11572265625 = 102.29931640625 → 102.2993;
  `recording`'s line at 122.18359375 + 14.40234375 = 136.5859375 →
  136.5859. The cross-section lines of `theme`'s `origin` and `length` at
  `x0` and `x0 + L` cross `theme`'s card from 32.8047 to 48.707 and from
  74.1836 to 114.1836, and the frame from 114.1836 to the bottom of
  `recording`'s card, 171.5625.
- The ancestor card of `score` (Shared quantities), aligned to `theme`:
  `s0` = 103.70361328125, `ts` = −(16 + 8) = −24, `λ` = 8, `te` = −24 + 64
  = 40, `us` = −3, `ue` = 5, `xs` = −1096.29638671875, `xe` =
  2103.70361328125, `LA` = 3200. `N'` = w(`Movement`, 11) = 58.265625
  (10848 advances; `Theme` 37.94140625, `Score` 31.05029296875), `s0'` =
  74.265625; `Mr'` = the arrowhead 9. The seams, at `score`'s 24 and
  32: `OL` = 103.70361328125 and `OR` = 543.70361328125 −
  503.70361328125 = 40; `score` runs on past both. Whole, the card is
  103.70361328125 + 74.265625 + 3200 + 40 + 9 + 8 = 3434.96923828125 →
  3434.9692 wide, its left edge `xs − OL − s0'` = −1274.265625, the place
  −1266.265625. In it `theme`'s line lies 15 below the top, `movement`'s
  15 + 33.9765625 = 48.9765625 and `score`'s 62.9765625; the card is
  62.9765625 + 6.40234375 + 8 = 77.37890625 → 77.3789 high. `score`'s
  ancestor line in `theme`'s card of `__full` lies at 99.18359375, so the card's top
  is 99.18359375 − 62.9765625 = 36.20703125 → 36.207, below `Pt` = 8, and
  its bottom with its shadow at 115.5859375, inside the frame:
  `movement`'s line in it lies on `movement`'s faded line, at 85.1836,
  `theme`'s 4 lower than `theme`'s own line, at 51.207.
- Whole (`__full`): `Yt` = 0 and `Xl` = −1274.265625, the origin
  (1274.265625, 0), and the card is drawn at (8, 36.207). In it (drawn):
  `score`'s line at 99.1836 from 82.265625 → 82.2656, whole across both
  seams, to 3425.96923828125 → 3425.9692, `movement`'s from 882.2656 (16
  of 64 quarters) at 85.1836 to its diamond at 1785.9692 and `theme`'s
  from 1385.9692 (24 of 64) at 51.207, where `theme`'s own line starts in
  the frame, 111.70361328125 + 1274.265625, to its diamond at 1785.9692,
  its `origin` and `length` crossing the card from 36.207 to 52.707 and
  from 78.1836 to 113.5859; the names `Theme`, `Movement` and `Score` at
  16, with the baselines 55.0151, 88.9917 and 102.9917. `W` = 8 +
  2170.70361328125 + 1274.265625 = 3452.96923828125, the right edge of the
  card with its shadow, −1266.265625 + 3434.96923828125 + 2, beyond the
  frame's 551.70361328125; `H` = 8 + (8 + 171.5625) = 187.5625; the page
  3484.96923828125 × 219.5625 → **3484.9692 × 219.5625**.
- Derived (Shared quantities): `Fw` = 543.70361328125, `Fh` = 171.5625
  (the frame before its rows align),
  so `zG` = min(4, 1024 / `Fw`, 576 / `Fh`) = 1.8833790598156273, `zb` =
  `Z`, `B` = 716.8; `c` = 271.851806640625, `σ` = 74.265625, `dl` =
  346.117431640625, `dr` = 279.851806640625; `EL` = 24, `ER` = 32, `E` =
  56, `uL` = 3 and `uR` = 4: `r` = min(1, 0.14285714285714285,
  0.30890214029947916, 0.27309262084960934) = 0.14285714285714285, set by
  `λ / E`. Depth 2 holds `movement`, which covers 16 to 24 of `score`'s
  axis outside `theme`: the piece `movement` 0–8; depth 1 `score` 0–16 and
  32–64. Their natural widths at `LA` = 3200 (`k` = 50 for each) are 800,
  400 and 1600 (from the left), `W` = 114.28571428571428,
  57.14285714285714 and 228.57142857142856, summing to 400, `h / k` =
  0.8228571428571427, 0.2514285714285714 and 1.9657142857142855: the
  first two are gaps whole, the third leaves out `score` 33–63, 50 of
  `score` at full scale on either side, its gap 128.57142857142856 wide of
  1500. The shrinks are 685.7142857142858, 342.8571428571429 and
  1371.4285714285716, `DL` = (685.7142857142858 + 342.8571428571429) −
  103.70361328125 = 924.8678152901787 and `D` = 2400 in all. In `score`'s
  own drawing x(0) = 74.265625, x(16) = 188.55133928571422, x(24) =
  245.69419642857133 left of the first seam and 349.3978097098213 right
  of it, x(32) = 749.3978097098213 on the span's side, x(33) =
  839.3978097098213, x(63) = 967.96923828125 and x(64) =
  1017.96923828125: the card (1017.96923828125 + 9) + 8 = 1034.96923828125
  → 1034.9692 wide. `dx` = (−1096.29638671875 + 924.8678152901787) −
  74.265625 = −245.69419642857133, the card's place −237.69419642857133,
  so `Xl` = −245.69419642857133 and the origin (245.69419642857133, 0).
  Vertically the stacks `Score`, of the two gaps on `score`, take
  `score`'s markers band, 26.9765625 below its line, and the stack
  `Movement` `movement`'s, below its line, so `movement`'s row has the
  inner half 26.9765625: `movement`'s line lies 7 + 26.9765625 =
  33.9765625 above `score`'s and `theme`'s 33.9765625 above that, `Ea` =
  7 + 26.9765625 + 40.9765625 = 74.953125, `score`'s line 82.953125 below
  the card's top and the card 82.953125 + 26.9765625 + 8 = 117.9296875 →
  117.9297 high.
- Rows aligned (§8.3): the stack `Movement` lies between the lines of
  `movement` and `score`, so `d` = 33.9765625 there (Shared quantities)
  and in `theme`'s card `score`'s ancestor row lies `Δ` = max(33.9765625,
  14) = 33.9765625 beyond `movement`'s, at 85.18359375 + 33.9765625 =
  119.16015625 → 119.1602, `movement`'s staying at 85.1836. `theme`'s
  card is 14.40234375 + 78.953125 + 8 = 101.35546875 → 101.3555 high, the
  frame 8 + 12.8046875 + 4 + 101.35546875 + 8 + 49.37890625 + 8 =
  191.5390625 → 191.5391, `recording`'s card at 32.8046875 + 101.35546875
  + 8 = 142.16015625 → 142.1602 and its line at 156.5625, its wedges,
  name and labels 19.9765625 lower than in `__full`; `score`'s faded name
  at 119.16015625 + 3.11572265625 = 122.27587890625 → 122.2759; the
  cross-section lines of `theme`'s `origin` and `length` cross `theme`'s
  card from 32.8047 to 48.707 and from 74.1836 to 134.1602, and the frame
  from 134.1602 to the bottom of `recording`'s card, 191.5391. `Fh`, and
  so `r` and every abscissa, does not move. The ancestor card's top is
  119.16015625 − 82.953125 = 36.20703125 → 36.207, its bottom
  154.13671875 and with its shadow 156.13671875, inside the frame, `Yt`
  still 0.
- Drawn with its derived elisions, the card at (8, 36.207): `theme`'s row
  at 51.20703125 → 51.207, `movement`'s at 85.18359375 → 85.1836, on
  `movement`'s faded line, and `score`'s line at 119.1602; `score`'s start circle at 82.2656 and its
  line in two pieces, from 253.6942, the right edge of the gap of
  `movement`, which ends at the first seam and so lies left of the frame,
  whole across that seam and the second to 847.3978, and from 975.9692 to
  1025.9692, its arrowhead's tip at 1034.9692 (the pieces of no length at
  the touching gaps' edges 82.2656 and 196.5513 are not written);
  `movement`'s start circle at 196.5513 and its line from 253.6942 to its
  diamond at 757.3978; `theme`'s from 357.3978, where `theme`'s own line
  starts in the frame (111.70361328125 + 245.69419642857133), to its
  diamond at 757.3978, its wedges and labels `0 ♩` and `8 ♩` there
  (baseline 76.061) and its `origin` and `length` crossing the card at
  357.3978 and 757.3978, from 36.207 to 52.707 and from 78.1836 to
  154.1367; the names `Theme`, `Movement` and `Score` at 16, with the
  baselines 55.0151, 88.9917 and 122.9683. The gaps `score` 0–16 from
  82.2656 to 196.5513, `movement` 0–8 from 196.5513 to 253.6942 and
  `score` 33–63 from 847.3978 to 975.9692 draw one ellipsis each, centred
  at 139.4085, 225.1228 and 911.6835 and at `ym` = (36.20703125 +
  154.13671875) / 2 = 95.171875 → 95.1719, and below it their labels
  `Score`, `Movement` and `Score` with the baseline 107.52587890625 →
  107.5259. `W` = 8 + 799.2750418526787 + 245.69419642857133 =
  1052.96923828125, the right edge of the card with its shadow,
  −237.69419642857133 + 1034.96923828125 + 2; `H` = 8 + (8 + 191.5390625) =
  207.5390625.
- Page 1084.96923828125 × 239.5390625 → **1084.9692 × 239.5391**.

## `unknown_length`

The root `score` (quarters, length `null`) with the region `region_1` (2
to 8), the jump target `jump_target_1` (`segno`) at 6 and the locked
child `coda` (4 at 10). No timeline has a name. The jump target draws its
symbol 𝄋 alone (§6.4, Symbols) in the root's flow control band, at level
−3 beyond the markers band and the regions band.

- The reach is the end of `coda`, 10 + 4 = 14, beyond the region's end 8 and
  the jump target 6, so `λ` = 14 and `u(t)` = `t / 14`, rounded once: `x(2)`
  = 110.94168526785714 → 110.9417, `x(6)` = 225.22739955357142 →
  225.2274, `x(10)` = 339.5131138392857 → 339.5131.
  `coda` ends at 14, known, in its diamond at `x0 + L`.
- `N` = w(`score`, 11) = 29.798828125.
- `x0` = 16 + 29.798828125 + 8 = 53.798828125 → 53.7988; the label
  `0 ♩` of `origin` gives only 22.416015625.
- `R` = the outer chevron tip `Xr + 5.5w` = 465.798828125 + 16.5 =
  482.298828125. The root has no `length`, so nothing is drawn at its end.
- Above, `coda` in the children band: `Ea` = 21, so `y_root` = 29. Below,
  `origin` in the markers band (26.9765625), the region in the regions
  band from 30.9765625 (18.4765625 wide, to 49.453125), and the flow
  control band from 49.453125 + 4 = 53.453125: no stack, no fork and no
  arc, only the symbol row, `Hs` = 2 + `h(12)` + 2 = 17.96875 wide, so `Eb` =
  71.421875.
- `Hm` = 29 + 71.421875 + 8 = 108.421875 → 108.4219.
- The symbol 𝄋 is centred on `x(6)` → 225.2274, its baseline at 37 +
  (53.453125 + 2) + `a(12)` = 103.591796875 → 103.5918, the root's line
  being drawn at 37.
- `W` = 8 + (10 + 482.298828125) = 500.298828125; `H` = 8 + (10 +
  108.421875) = 126.421875.
- Page 532.298828125 × 158.421875 → **532.2988 × 158.4219**.

## `unknown_length_empty`

The root `score` (quarters, length `null`) with no content.

- The reach is 0, so every `u` is 0 (§3.2), and the line is still drawn
  `L` long, from `x0` to `Xe = x0 + L` (§3.4).
- `N` = 29.798828125; `x0` = 53.798828125 → 53.7988.
- `R` = the outer chevron tip 482.298828125.
- `Hm` = 14.40234375 + 26.9765625 + 8 = 49.37890625: nothing above, so
  `y_root` = `P + h(11) / 2`.
- `W` = 500.298828125; `H` = 8 + (10 + 49.37890625) = 67.37890625.
- Page 532.298828125 × 99.37890625 → **532.2988 × 99.3789**.

## `unknown_length_locked`

The locked root `score` (quarters, length `null`) with the locked child
`coda` (4 at 12).

- The reach is 12 + 4 = 16 = `λ`; `x(12)` = 353.798828125. The root's end
  is open, and the three chevrons come before the end circle of a locked
  root in §6.6, so the root ends in the chevrons; `coda` ends in its diamond
  at `x0 + L`.
- `N` = 29.798828125; `x0` = 53.798828125 → 53.7988.
- `R` = the outer chevron tip 482.298828125.
- `Hm` = 29 + 26.9765625 + 8 = 63.9765625.
- `W` = 500.298828125; `H` = 8 + (10 + 63.9765625) = 81.9765625.
- Page 532.298828125 × 113.9765625 → **532.2988 × 113.9766**.

## `unknown_length_child`

The root `score` (32 quarters) and its locked child `movement` at 8, of
length `null`, holding the region `region_1` (0 to 6). No timeline has a
name. No default hides a band (§4), so the region is drawn in
`movement`'s regions band, at `movement`'s line. `movement` has no band
order of its own and follows `score`'s, the default one (§6.4), so its
regions band lies below its line, towards `score`'s; its markers band
draws nothing, so the regions band is at level −1 and the only band
`movement` draws. `score` holds no region, so its own regions band is
absent.

- `λ` = 32, the root's length. The reach of `movement` on its own axis is
  6, the end of its region. So `movement` ends under rule 5 of §3.4 at 8 +
  6 = 14, open: `Xs` = `x(8)` = 183.490234375 → 183.4902, `Xe` = `x(14)` =
  258.490234375, `Xr` = 270.490234375 → 270.4902, and the outer chevron's
  tip lies at 286.990234375 → 286.9902. `score`'s children band places
  `movement` alone, so it is aligned (§6.4, Children) and places it by its
  line extent, from 100 on `9.5w` past its end, to 175 + 28.5 = 203.5.
- `N` = w(`movement`, 11) = 59.490234375, wider than `score`
  (29.798828125).
- `x0` = 16 + 59.490234375 + 8 = 83.490234375 → 83.4902. The label
  `0 ♩` of `origin` gives only 16 + 6.416015625 = 22.416015625. The region
  has no label and its brace lies inside `movement`'s span.
- `R` = the label `32 ♩` of `length` at 483.490234375 + 9.279052734375 =
  492.769287109375, beyond the arrowhead tip 492.490234375.
- The regions band of `movement` (§6.4, Where a band lies): `movement`'s
  line has no map and no boundary, so it reaches 0 below, less than `w / 2`
  = 1.5. The band therefore starts at `S` beyond `w / 2`, `c` = 1.5 + 4 =
  5.5, and its brace keeps the gap `S` from the line's stroke. It has one
  row, so it is `pr1 − S` = 18.4765625 wide (Shared quantities), and
  `movement`'s edge below is 5.5 + 18.4765625 = 23.9765625; its edge above
  is 0.
- Above `score`, the children band alone, at level 1. `score`'s line
  reaches nothing there, so the band's own start is the larger of 1.5 + 4 =
  5.5 and `p0 / 2` = 7: 7. Its one row holds `movement`: the outer half is
  `movement`'s above side, max(7, 0) = 7, and the inner half its below
  side, max(7, 23.9765625) = 23.9765625. So `movement`'s line lies `l1` =
  7 + 23.9765625 = 30.9765625 above `score`'s, the band is 23.9765625 + 7 =
  30.9765625 wide, and `Ea` = 7 + 30.9765625 = 37.9765625. Below, the
  markers band alone: `Eb` = 26.9765625 (Shared quantities).
- `y_root` = 8 + 37.9765625 = 45.9765625; `Hm` = 45.9765625 + 26.9765625 +
  8 = 80.953125 → 80.9531.
- Drawn, each ordinate the card's top 8 plus its item-coordinate value:
  - `score`'s line at 53.9765625 → 53.9766, and `movement`'s at 53.9765625
    − 30.9765625 = 23;
  - the brace's arms at 23 + 5.5 = 28.5, from `x(8)` = 183.490234375 →
    183.4902 to `x(14)` = 258.490234375 → 258.4902; its tip at 23 + (5.5 +
    6) = 34.5 on `x(11)` = 220.990234375 → 220.9902, `u` = 11/32, the
    midpoint of 8 and 14 on `score`'s axis (§3.1); its path's `Ym` = 31.5
    and `k` = 3 (§7.2);
  - the wedges from 53.9765625 + 1.5 = 55.4765625 → 55.4766 to 53.9765625
    + 14.5 = 68.4765625 → 68.4766, and their labels' baseline at
    (53.9765625 + 16.5) + 8.35400390625 = 78.83056640625 → 78.8306;
  - the names' baselines at 23 + 3.80810546875 = 26.80810546875 → 26.8081
    (`movement`) and 53.9765625 + 3.80810546875 = 57.78466796875 → 57.7847
    (`score`).
- `W` = 8 + (10 + 492.769287109375) = 510.769287109375; `H` = 8 + (10 +
  80.953125) = 98.953125.
- Page 542.769287109375 × 130.953125 → **542.7693 × 130.9531**.

## `group__group_unknown_length`

The group "Edition" in the display order `performance`, `score`: the root
`performance` (seconds, length `null`) with the region `region_1` (0.0 to
9.5), and the root `score` (12 quarters).

- `performance` is scaled to its reach 9.5, a float: `u(9.5)` = 1.0, so the
  region spans `x0` to `x0 + L`, and its tip lies at the midpoint (0.0 +
  9.5) / 2 = 4.75, `u` = 0.5, `x` = 302.640625 (§3.1). `origin`'s label is
  the clock `0″` (§5.2), the advances 1303 + 765 = 2068, 9.087890625 wide.
- `xn` = 24. `N` = w(`performance`, 11) = 70.640625.
- `x0` = 24 + 70.640625 + 8 = 102.640625 → 102.6406; the label
  `0″` of `origin` gives only 24 + 4.5439453125 = 28.5439453125.
- `R` = the outer chevron tip of `performance`, `Xr + 5.5w` = (102.640625 +
  400 + 12) + 16.5 = 531.140625, beyond the label `12 ♩` of `score`'s `length` at
  511.919677734375.
- `Hm` = 71.85546875 (`performance`, its regions band below) and
  49.37890625 (`score`); the frame is 8 + 12.8046875 + 4 + 71.85546875 + 8
  + 49.37890625 + 8 = 162.0390625 high.
- `W` = 8 + (531.140625 + 8 + 8) = 555.140625; `H` = 8 + (8 +
  162.0390625) = 178.0390625.
- Page 587.140625 × 210.0390625 → **587.1406 × 210.0391**.

## `unknown_length_segments`

The unlocked segment line `form` (quarters, length `null`) of three
segments, none a segment line and none named: `a` at 0, of length `null`,
holding the region `region_1` (0 to 4); `b` (6 at 8); `c` at 14, of length
`null`, holding the region `region_2` (0 to 3). No default hides a band
(§4): the regions bands of `a` and `c` are displayed, and what they hold
joins `form`'s regions band, after `form`'s own content (none), segment
after segment in traversal order (§6.4, Segments without a line):
`region_1` of `a` and then `region_2` of `c`, laid out by one first fit.

- The reach is the largest of 0 + 4, 8 + 6 and 14 + 3, so `λ` = 17. `a`
  ends where `b` starts (rule 3 of §3.4), and `c` where `form` ends (rule
  4), open. The three chevrons come before the open arrowhead of a segment
  line in §6.6.
- The boundaries of `b` and `c` lie at `x(8)` = 238.07562614889704 →
  238.0756 and `x(14)` = 379.2520967371323 → 379.2521, and reach `k` = 8
  to both sides. No band is present above: the children band holds only
  segments without a line and draws nothing, and there is no map. The
  above side's outer edge is therefore the line's reach, `Ea` = 8, and
  `y_root` = 8 + 8 = 16 in the member drawing. No segment has a label.
- Below, the markers band lies against the line at level −1, `origin`'s
  wedge and its label `0 ♩` in one tier, 26.9765625 wide and beyond the
  boundaries' 8.
- The regions band lies at level −2, beyond the markers band, and starts
  at 26.9765625 + 4 = 30.9765625. On `form`'s axis the regions span 0 to
  4 and 14 to 17, so both lie in row 1. Neither has a label, so the band
  is 18.4765625 wide and `Eb` = 49.453125 (Shared quantities).
- `N` = w(`form`, 11) = 25.84033203125.
- `x0` = 16 + 25.84033203125 + 8 = 49.84033203125 → 49.8403; the
  label `0 ♩` of `origin` gives only 22.416015625.
- `R` = the outer chevron tip 478.34033203125; both braces end at or
  before `x(17)` = `x0 + L` = 449.84033203125.
- The braces have their arms at 24 + 30.9765625 = 54.9765625 → 54.9766
  and their tips at 24 + 36.9765625 = 60.9765625 → 60.9766, and open
  towards `form`'s line.
  - `region_1` runs from `x(0)` = 49.8403 to `x(4)` =
    143.95797909007354 → 143.958, with its tip at `x(2)` =
    96.89915556066177 → 96.8992.
  - `region_2` runs from `x(14)` = 379.2521 to `x(17)` = 449.8403,
    with its tip at `x(31/2)` = 414.54621438419116 → 414.5462.
- `Hm` = 16 + 49.453125 + 8 = 73.453125.
- `W` = 8 + (10 + 478.34033203125) = 496.34033203125; `H` = 8 + (10 +
  73.453125) = 91.453125.
- Page 528.34033203125 × 123.453125 → **528.3403 × 123.4531**.

## `bundle_ungrouped__places`

The block "Sketches" of three ungrouped roots, in drawing order the segment
line `pages` ("Pages", 5262 pixels, the segments `Page 1` to `Page 3` of
1754 each, none a segment line and none with a map) with the map `cmap_3` to
points, the root `recording` ("Recording", 441000 samples) with the map
`cmap_2` to seconds, and the root `score` ("Score", 16 quarters) with the
map `cmap_1` to ticks, the break `break_1` (no name, labelled "Fine",
manifestation `fine`) at 8 and the jump `jump_1` from 16 to the timeline
`score` itself, at 0, its one destination `da_capo_al_fine`. The defaults
hide the jump's arc and the arc's label `D.C. al Fine` (§2.4, §4), so the
jump draws its symbol 𝄊 and the break its symbol `Fine`, both at size 12
(§6.4, Symbols), and the break its stack, its label `Fine` alone, since it
has no name (§6.4, Flow labels); the jump has no stack. The place of `score` is
stated as `{x: -60, y: -150, height: 120}`, left of the padding and above
the title's slot. The three cards share one horizontal layout (§8.2), so
they are equally wide; every place not stated takes its default (§8.6).
Every position below is in item coordinates until it is drawn at its place,
and in place coordinates until the place origin is added, last (§8.4).

- The layout, in item coordinates: `n` = `K` = 8 (no frame); `N` =
  w(`Recording`, 11) = 55.70361328125, of `Pages` (32.85498046875),
  `Recording` and `Score` (31.05029296875); `s0` = `n + N + G'` = 8 +
  55.70361328125 + 8 = 71.70361328125, above the largest label term, the
  label `0 smp` of `recording`'s `origin`, 8 + 13.8779296875 − 0 =
  21.8779296875; the symbol `Fine` (25.224609375 wide), centred on `u` =
  1/2, gives only 8 + 12.6123046875 − 200 = −179.3876953125. The shared end is
  `s0 + L` = 471.70361328125.
- The right margin: the right edges are the labels of `length`, their
  digits grouped by three on the `int` axes (§5.2), `5 262 px` (the
  advances 4 × 1303 + 2 × 651 + 1300 + 1212 = 9026, 39.6650390625 wide) at
  471.70361328125 + 19.83251953125 = 491.5361328125 (`pages`), `441 000
  smp` (6 × 1303 + 2 × 651 + 1067 + 1995 + 1300 = 13482, 59.2470703125
  wide) at 471.70361328125 + 29.62353515625 = 501.3271484375 (`recording`)
  and `16 ♩` at 471.70361328125 + 9.279052734375 = 480.982666015625
  (`score`), so `Mr` = 501.3271484375 − 471.70361328125 = 29.62353515625,
  from `recording`, and `Ri` = 471.70361328125 + 29.62353515625 =
  501.3271484375 for every card. The maps end at the shared end, the
  symbol 𝄊 (10.763671875 wide) at `x(16)` + 5.3818359375 =
  477.08544921875, and the stack's label `Fine` at 274.70361328125 +
  18.91845703125 = 293.6220703125. Each card
  spans 0 to `Ri + K` = 509.3271484375.
- The map stacks: each root's one map lies above its line (§4), 5.5 above
  it, its outline from 6.5 to 4.5 above it and from `s0` to `s0 + L`, and
  the stack reaches `e` = 6.5 (Shared quantities). Each map takes the
  colour and pattern of its `target_unit` (§2.1, §4): solid red to points
  on `pages`, solid blue to seconds on `recording`, green dashed `1 1` to
  ticks on `score`.
- Heights: on `pages`, a segment line with drawn boundaries, the stack lies
  within the boundaries' `k`: its line reaches above max(`e`, `k`) =
  max(6.5, 8) = 8, plus 2 + `h(9)` for its one tier of segment labels
  (§6.4), so the map changes nothing of it: `y_root` = 8 + (8 + 2 +
  10.4765625) = 28.4765625, its segment labels' baseline 28.4765625 − (8 +
  2) − `d(9)` = 16.35400390625, and `Hm` = 28.4765625 + 26.9765625 + 8 =
  63.453125. `recording` and `score` have their conversion maps band as
  their only band above, `Ea` = 6.5, so `y_root` = 14.5 (Shared
  quantities); `recording` has `Hm` = 49.4765625 → 49.4766.
- The flow control band of `score` (§6.4) lies below at level −2, beyond its
  markers band of 26.9765625 (its regions band is absent), from 26.9765625 +
  4 = 30.9765625. The break's stack, one line, fills one flow label tier,
  `T` = 1, so the flow row lies at `f0` = 30.9765625 + 10.4765625 =
  41.453125, and the symbol row beyond it is `Hs` = 2 + `h(12)` + 2 = 17.96875 wide;
  no fork and no arc is drawn. The band is 10.4765625 + 17.96875 =
  28.4453125 wide, so `Eb` = 59.421875, `Hm` = 14.5 + 59.421875 + 8 =
  81.921875, and the card of `score` is max(81.921875, 120) = 120 high.
- The flow of `score`, in item coordinates: the break at `x(8)` =
  71.70361328125 + 400 × 1/2 = 271.70361328125, from the flow row `yf` =
  14.5 + 41.453125 = 55.953125 to `P` = 8, its stack's label from
  274.70361328125 with its baseline at `yf − d(9)` = 53.83056640625 (line
  1). The symbols `Fine` and 𝄊, in the order of the band's elements, are
  centred on `x(8)` and `x(16)` = 471.70361328125, each with its baseline
  at `y_root + (f0 + 2) + a(12)` = 14.5 + 43.453125 + 11.138671875 =
  69.091796875, the symbol gap 2 beyond the flow row.
- Places (§8.6): `pages` at (8, 28.8046875), the first item, `P + h(11) +
  F`; `recording` at (8, 100.2578125), the block's spacing 8 below the
  bottom edge `d` = 28.8046875 + 63.453125 = 92.2578125 of `pages`' card,
  its shadow not counted; `score` at (−60, −150). Every `length` is 400
  and every `scale` 1, so an item-coordinate position `px` lies at `x +
  px`.
- The block: `Pt` = 28.8046875, `Xl` = min(0, −60 − 8) = −68 and `Yt` =
  min(0, −150 − 28.8046875) = −178.8046875, so `(Ox, Oy)` = (68,
  178.8046875). `Xr` = 8 + (517.3271484375 + 2) = 527.3271484375, from
  the shadows of `pages` and `recording`, which end at 8 +
  509.3271484375 + 2; `Yb` = 8 + (100.2578125 + (49.4765625 + 2)) =
  159.734375, from `recording`'s shadow. `W` = 527.3271484375 − (−68) =
  595.3271484375 and `H` = 159.734375 − (−178.8046875) = 338.5390625.
- The title `Sketches` lies at the block's top left: `x` = `Xl + P` = −60,
  baseline (−178.8046875 + 8) + 10.21044921875 = −160.59423828125, right
  edge −60 + 49.951171875 = −10.048828125, slot ending at −178.8046875 + 8
  + 12.8046875 = −158, `F` above the top of `score`.
- Drawn, each position plus (68, 178.8046875): the title at `x` 8 with its
  baseline at −160.59423828125 + 178.8046875 = 18.21044921875 → 18.2104,
  where it lies in a block with no places; the cards of `score` at (8,
  28.8046875 → 28.8047), where the first item lies by default, of `pages` at
  (76, 207.609375 → 207.6094) and of `recording` at (76, 279.0625), each
  509.3271484375 → 509.3271 wide; the starts (8 + 71.70361328125) + 68 =
  147.70361328125 → 147.7036 (`pages`, `recording`) and (−60 +
  71.70361328125) + 68 = 79.70361328125 → 79.7036 (`score`); the lines at
  `y` 236.0859375 → 236.0859 (`pages`), 293.5625 (`recording`) and
  43.3046875 → 43.3047 (`score`), and their maps' outlines from 229.5859375
  → 229.5859 to 231.5859375 → 231.5859, from 287.0625 to 289.0625 and from
  36.8046875 → 36.8047 to 38.8046875 → 38.8047; the boundaries of `pages` at
  `u` = 1/3 and 2/3, item x 205.03694661458331 and 338.37027994791663, →
  281.0369 and 414.3703; the break of `score` at `x` 279.70361328125 →
  279.7036, from the flow row at 84.7578125 → 84.7578 to 36.8046875 →
  36.8047, where the top of its map's outline lies too, dotted red
  (`#D62728`, 1.5 wide, dashed `1.5 1.5`, §4), its label's baseline at
  82.63525390625 → 82.6353, and its symbols at 279.7036 and 479.7036 with
  their baselines at 97.896484375 → 97.8965. The shadow of
  `score`'s card ends at 150.8046875, 56.8046875 above the card of `pages`,
  and no card overlaps another or the title.
- Page 627.3271484375 × 370.5390625 → **627.3271 × 370.5391**.

## `bundle_ungrouped__scale`

The manifest of `bundle_ungrouped__places` with `places` `{recording:
{scale: 1.5}}` and nothing else stated: every item at its default place,
`recording` drawn half as large again, its map and text included. A scale
changes neither the layout in item coordinates nor any other item, except
that the items after a scaled one start below its drawn bottom (§8.6).

- The layout and the member drawings are those of
  `bundle_ungrouped__places`, which no place changes: `n` = 8, `s0` =
  71.70361328125, `Mr` = 29.62353515625, `Ri` = 501.3271484375, every
  card 0 to 509.3271484375 in item coordinates, `Hm` = 63.453125
  (`pages`), 49.4765625 (`recording`) and 81.921875 (`score`).
- Places: `pages` at (8, 28.8046875); `recording` at (8, 100.2578125),
  scale 1.5, its drawn bottom 100.2578125 + 1.5 × 49.4765625 =
  174.47265625; `score` at (8, 182.47265625), the block's spacing 8 below
  that. Every `length` is 400.
- `recording`, drawn at `(8 + 1.5 × px, 100.2578125 + 1.5 × py)`: its card
  at (8, 100.2578125), 1.5 × 509.3271484375 = 763.99072265625 →
  763.9907 wide and 1.5 × 49.4765625 = 74.21484375 → 74.2148 high, `rx`
  7.5, stroke width 1.125; its shadow at the item position (2, 2), drawn
  at (11, 103.2578125); its line from 8 + 1.5 × 71.70361328125 =
  115.555419921875 → 115.5554 to 8 + 1.5 × 471.70361328125 =
  715.555419921875 → 715.5554 at `y` 100.2578125 + 1.5 × 14.5 =
  122.0078125 → 122.0078, 4.5 wide, dashed `4.5 4.5`, its start circle of
  radius 4.5 and its arrowhead's tip at 8 + 1.5 × 480.70361328125 =
  729.055419921875 → 729.0554; its map's outline as long as its line, from
  100.2578125 + 1.5 × 8 = 112.2578125 → 112.2578 to 100.2578125 + 1.5 × 10
  = 115.2578125 → 115.2578, stroke width 1.5; its wedges from
  100.2578125 + 1.5 × 16 = 124.2578125 → 124.2578 to 100.2578125 + 1.5 ×
  29 = 143.7578125 → 143.7578, 9 wide; its name at `x` 8 + 1.5 × 8 = 20 in
  size 16.5, baseline 100.2578125 + 1.5 × 18.30810546875 =
  127.719970703125 → 127.72; its labels in size 13.5, baseline 100.2578125
  + 1.5 × 39.35400390625 = 159.288818359375 → 159.2888.
- `pages` and `score` are drawn as in a block with no places, `score`
  24.73828125 = 0.5 × 49.4765625 lower: its line at 182.47265625 + 14.5 =
  196.97265625 → 196.9727, its flow row at 182.47265625 + 55.953125 =
  238.42578125 → 238.4258, its symbols' baselines at 182.47265625 +
  69.091796875 = 251.564453125 → 251.5645, its card 81.921875 → 81.9219
  high.
- The block: `Xl` = `Yt` = 0 (the first item lies at `Pt` = 28.8046875), so
  the origin is (0, 0) and the title at (8, 18.21044921875 → 18.2104).
  `W` = 8 + (8 + 1.5 × (509.3271484375 + 2)) = 8 + 774.99072265625 =
  782.99072265625, from `recording`'s shadow; `H` = 8 + (182.47265625 +
  (81.921875 + 2)) = 8 + 266.39453125 = 274.39453125, from `score`'s
  shadow. No card overlaps another or the title.
- Page 814.99072265625 × 306.39453125 → **814.9907 × 306.3945**.

## `bundle_ungrouped__spacing`

The manifest of `bundle_ungrouped__places` with the block's `spacing` 24 and
`places` `{score: {spacing: 8}}`, nothing else stated: every item at its
default place. The block's spacing is the gap between its items at their
default `y` (§8.6), so `recording` lies 24 below `pages` and `score` 24
below `recording`; the gap `F` = 8 after the title does not change. The
card spacing `S` = 8 of `score` is the gap between that card's bands
(§6.2, §6.4): its conversion maps band above and its markers band below
lie against its line, from `c` = 0, and do not move, but its flow control
band at level −2 starts `S` beyond its markers band, so that band lies 4
further out and the card is 4 higher than at `S` = 4; the band draws no
arc, so the first jump depth `4 + S` enters nothing. Its row pitch `p0` = max(10 + 8,
`h(11)`) = 18 places no row, since its children band holds nothing, and
its padding `P` = 8 does not change (§8.6). No spacing multiplies another:
`pages` and `recording` keep `S` = 4 and are drawn as in a block with no
places, only lower.

- The layout is that of `bundle_ungrouped__places`, which no place
  changes: `n` = 8, `s0` = 71.70361328125, `Mr` = 29.62353515625, `Ri` =
  501.3271484375, every card 0 to 509.3271484375 in item coordinates,
  `Hm` = 63.453125 (`pages`) and 49.4765625 (`recording`).
- `score` (§6.4, §6.5): `Ea` = 6.5, its map stack's reach, so `y_root` =
  14.5, as at `S` = 4. Its flow control band starts at 26.9765625 + 8 =
  34.9765625, beyond its markers band; the break's stack `Fine` fills one
  flow label tier, `T` = 1, so the flow row lies at `f0` = 34.9765625 +
  10.4765625 = 45.453125, and the symbol row beyond it is `Hs` = 2 + `h(12)` + 2 = 17.96875
  wide. The band is 10.4765625 + 17.96875 = 28.4453125 wide, as at `S` =
  4, so `Eb` = 34.9765625 + 28.4453125 = 63.421875 and `Hm` = 14.5 +
  63.421875 + 8 = 85.921875 → 85.9219.
- The flow of `score`, in item coordinates: the break at `x(8)` =
  271.70361328125, from the flow row `yf` = 14.5 + 45.453125 = 59.953125 to
  `P` = 8, its stack's label from 274.70361328125 with its baseline at
  `yf − d(9)` = 57.83056640625; the symbols `Fine` and 𝄊 centred on
  `x(8)` and `x(16)` = 471.70361328125, each with its baseline at `y_root
  + (f0 + 2) + a(12)` = 14.5 + 47.453125 + 11.138671875 = 73.091796875.
- Places: `pages` at (8, 28.8046875), the first item, `P + h(11) + F`, its
  bottom 28.8046875 + 63.453125 = 92.2578125; `recording` at (8,
  92.2578125 + 24 = 116.2578125 → 116.2578), its bottom 116.2578125 +
  49.4765625 = 165.734375; `score` at (8, 165.734375 + 24 = 189.734375 →
  189.7344). Every `length` is 400 and every `scale` 1, so a position
  `(px, py)` in item coordinates is drawn at `(8 + px, y + py)` (§8.6).
- `recording`, 16 lower than in a block with no places: its card at (8,
  116.2578125), 509.3271484375 → 509.3271 wide and 49.4766 high, its
  shadow at (10, 118.2578125); its map's outline from 116.2578125 + 8 =
  124.2578125 → 124.2578 to 126.2578125 → 126.2578; its line at `y`
  116.2578125 + 14.5 = 130.7578125 → 130.7578, from 79.70361328125 →
  79.7036 to 479.70361328125 → 479.7036, the arrowhead's base from
  126.2578 to 135.2578; its wedges from 116.2578125 + 16 = 132.2578125 →
  132.2578 to 116.2578125 + 29 = 145.2578125 → 145.2578; its name at `x`
  16, baseline 116.2578125 + (14.5 + 3.80810546875) = 134.56591796875 →
  134.5659; its labels at baseline 116.2578125 + ((14.5 + 16.5) +
  8.35400390625) = 155.61181640625 → 155.6118.
- `score`, 32 lower than in a block with no places: its card at (8,
  189.734375), 509.3271 wide and 85.9219 high, its shadow at (10, 191.734375
  → 191.7344); its line at 189.734375 + 14.5 = 204.234375 → 204.2344, its
  map's outline from 197.734375 → 197.7344 to 199.734375 → 199.7344, its
  name's baseline at 208.04248046875 → 208.0425, its labels' at
  229.08837890625 → 229.0884, all as at `S` = 4; its flow row at 189.734375
  + 59.953125 = 249.6875, the break from there to 189.734375 + 8 =
  197.734375 → 197.7344 and its label's baseline at 189.734375 +
  57.83056640625 = 247.56494140625 → 247.5649, and its symbols'
  baselines at 189.734375 + 73.091796875 = 262.826171875 → 262.8262.
- The block: `Xl` = `Yt` = 0, so the origin is (0, 0) and the title at (8,
  18.21044921875 → 18.2104). `W` = 8 + (8 + (509.3271484375 + 2)) =
  527.3271484375, from the shadows of all three cards; `H` = 8 +
  (189.734375 + (85.921875 + 2)) = 8 + 277.65625 = 285.65625, from
  `score`'s shadow. No card overlaps another or the title.
- Page 559.3271484375 × 317.65625 → **559.3271 × 317.6562**.

## `styled_score_flow_inner`

The manifest of `styled__score` with the band order `children`,
`markers`, `line`, `conversion_maps`, `flow_control`, `regions` for
`score` in its `graphical.order`
(§6.4). Above the root's line, the markers band lies against the line and
the children band beyond it, as in `styled__score`. Below, the conversion
maps band lies against the line, the flow control band next to it, and the
regions band beyond that. `b` follows the root's band order (§6.4) but
draws nothing there: it has no maps, no children, no regions and no named
timestamp, and draws no flow control band (§6.4, Gathering). `a` is
hidden and takes no room. As in `styled__score`, the jump's arc and its
label are hidden (§4) and the jump draws its symbol 𝄊 alone.

- Above: the markers band lies at level 1 from `c` = 0. Its labels, at size
  10, fill one tier, so it is `w / 2 + 13 + 2 + h(10)` = 2 + 13 + 2 +
  11.640625 = 28.640625 wide. The children band lies at level 2 from
  max(28.640625 + 4, `p0 / 2` = 7) = 32.640625. Its one row, `b`, has the
  halves 7 and 7, so `b`'s line lies 39.640625 out and `Ea` = 46.640625.
  `y_root` = 8 + 46.640625 = 54.640625. The root's line is drawn at
  62.640625 → 62.6406 and `b`'s at 23.
- Below: the conversion maps band lies at level −1 from `c` = 0. The map
  `ticks` is centred `w / 2 + (g + d) − d / 2` = 2 + 5 − 1 = 6 below the
  line, its outline from 67.640625 → 67.6406 to 69.640625 → 69.6406, and the
  band reaches `e` = 2 + 5 = 7. The flow control band lies at level −2 from
  7 + 4 = 11. It has no stack, so the flow row lies at its start, `f0` =
  11 (73.640625), and the symbol row is `Hs` = 2 + `h(12)` + 2 = 17.96875 wide; no
  fork and no arc, so the band is 17.96875 wide and its outer edge is
  28.96875. The regions band lies at level −3 from 28.96875 + 4 =
  32.96875. With `pr1` = 6 + 2 + `h(10)` + 4 = 23.640625 it is 19.640625
  wide, so `Eb` = 52.609375. The flow control and regions bands swap
  places with those of `styled__score`, so `Eb` and the height stay that
  drawing's.
- The symbol 𝄊 is centred on `x(8)` = 498.080078125 → 498.0801, its
  baseline at 62.640625 + (11 + 2) + `a(12)` = 86.779296875 → 86.7793.
- The region `intro` runs from `x(0)` to `x(2)` = 198.080078125, with its
  tip at `x(1)` = 148.080078125. Its arms lie at 62.640625 + 32.96875 =
  95.609375 → 95.6094 and its tip at 101.609375 → 101.6094. Its label's
  baseline is 62.640625 + 40.96875 + `a(10)` = 112.8916015625 → 112.8916.
- As in `styled__score`: `x0` = 98.080078125 → 98.0801, `R` =
  510.080078125, `Hm` = 54.640625 + 52.609375 + 8 = 115.25, `W` =
  528.080078125 and `H` = 133.25.
- Page 560.080078125 × 165.25 → **560.0801 × 165.25**.

## `map_child_band_order`

The manifest of `map` with the band order `children`, `line`,
`conversion_maps`, `markers`, `regions`, `flow_control` for the child
`phrase` in its `graphical.order` (§6.4). So `phrase`'s map `ticks`,
addressed `{"id": "ticks"}`, lies against
its line below it. `melody` has no entry and keeps the default band order
(§4).

- Above `melody`'s line: the conversion maps band lies at level 1, with
  `tempo` centred 5.5 above the line and reaching `e` = 6.5 (Shared
  quantities). The children band lies at level 2 from max(6.5 + 4, `p0 / 2`
  = 7) = 10.5.
- `phrase` lies in that band's row 1. Its conversion maps band lies at
  level −1 below its own line from `c` = 0, with `ticks` centred 5.5 below.
  Its other bands draw nothing, so its below edge is 6.5 and its above edge
  0. The row's inner half, towards `melody`'s line, is max(7, 6.5) = 7, and
  its outer half is max(7, 0) = 7. In `map` the two edges are the other way
  round, and the halves are the same. So `phrase`'s line lies 10.5 + 7 =
  17.5 above `melody`'s, `Ea` = 10.5 + 14 = 24.5 and `y_root` = 32.5.
- Below `melody`'s line: the markers band lies at level −1 and is 26.9765625
  wide (Shared quantities), so `Hm` = 32.5 + 26.9765625 + 8 = 67.4765625.
- Drawn: `melody`'s line at 40.5, with `tempo`'s outline from 34 to 36.
  `phrase`'s line at 23, with the outline of `ticks` from 27.5 to 29.5 and
  from `x(2)` = 163.53662109375 → 163.5366 to `x(6)` = 363.53662109375 →
  363.5366, between `phrase`'s line and `melody`'s map.
- As in `map`: `x0` = 63.53662109375 → 63.5366, `R` = 472.53662109375, `W`
  = 490.53662109375 and `H` = 85.4765625. The figure differs from `map`'s
  only in the outline of `ticks`.
- Page 522.53662109375 × 117.4765625 → **522.5366 × 117.4766**.

## `map_root_band_order`

The manifest of `map` with the band order `children`, `line`,
`conversion_maps`, `markers`, `regions`, `flow_control` for the root
`melody` in its `graphical.order`. `phrase` has no entry, so it follows
`melody`'s band order (§6.4). Both lines therefore have their maps against them, below. Above
`melody`'s line lies its children band alone. Below it, the markers band
lies beyond the maps.

- Above: the line reaches 0 there, since its map stack lies below. So the
  children band at level 1 starts at the larger of 1.5 + 4 = 5.5 and `p0 /
  2` = 7: 7. Its row 1 holds `phrase`, whose edges are 6.5 below (its map)
  and 0 above, so the halves are 7 and 7. `phrase`'s line lies 14 above
  `melody`'s, and `Ea` = 21.
- `y_root` = max(8 + 21, 8 + 6.40234375) = 29.
- Below: the conversion maps band lies at level −1 from `c` = 0, with
  `tempo` centred 5.5 below the line, so its outer edge is 6.5. The markers
  band lies at level −2 from 6.5 + 4 = 10.5 and is 26.9765625 wide, so `Eb`
  = 37.4765625. The wedges' tips lie 10.5 + 1.5 = 12 below the line and
  their bases 12 + 13 = 25 below it. The labels' tier starts 25 + 2 = 27
  below it.
- `Hm` = 29 + 37.4765625 + 8 = 74.4765625 → 74.4766.
- Drawn, `melody`:
  - its line at 37, with its arrowhead from 32.5 to 41.5;
  - `tempo`'s outline from 41.5 to 43.5;
  - the wedges from 49 to 62;
  - their labels' baseline at 37 + 27 + `a(9)` = 72.35400390625 → 72.354;
  - the name `Melody`'s baseline at 40.80810546875 → 40.8081.
- Drawn, `phrase`, as in `map_child_band_order`: its line at 23, the
  outline of `ticks` from 27.5 to 29.5, and the name `Phrase`'s baseline at
  26.80810546875 → 26.8081.
- As in `map`: `x0` = 63.53662109375 → 63.5366 and `R` = 472.53662109375.
  `W` = 490.53662109375 and `H` = 8 + (10 + 74.4765625) = 92.4765625.
- Page 522.53662109375 × 124.4765625 → **522.5366 × 124.4766**.

## `joint_rows`

The root `piece` ("Piece", 16 quarters) with two branches of nested
children, every child locked: `b` ("B", 6 at 0) with the map `ticks_b`
holds `b1` ("B1", 4 at 1), which holds `b11` ("B11", 2 at 1); `d` ("D", 8
at 8) holds `d1` ("D1", 4 at 2) with the maps `tempo_d1` and `ticks_d1`,
which holds `d11` ("D11", 2 at 1) with the maps `tempo_d11` and
`ticks_d11`. Every map is an unnamed `LinearMap`, so all have one key
(Shared quantities); the two maps of one line span one timeline and so
conflict, and take the key's two sub-slots in canonical order, by ID: each
`tempo_*` (to seconds, solid blue) in slot 1, nearest its line, and each
`ticks_*` (to ticks, green dashed `1 1`) in slot 2, beyond it (§2.1, §4).
Every row holds one line with maps at most. Every children band lies above
its line, beyond the line's conversion maps band where it has one, and the
children bands of the lines of one row are laid out together (§6.4,
Children).

- The rows, by first fit (§6.3, extents `L × u` with `u` = t / 16): `b`
  (0 to 150) and `d` (200 to 400) share row 1 of the children band of
  `piece`; `b1` (25 to 125) and `d1` (250 to 350), each in row 1 of its
  parent's band, form row 1 of those two bands laid out together; so do
  `b11` (50 to 100) and `d11` (275 to 325). The rows are `{piece}`,
  `{b, d}`, `{b1, d1}` and `{b11, d11}`, every name of size 11, so every
  pitch is `p` = `p0` = max(10 + 4, `h(11)`) = 14 (§6.2).
- One map reaches `e` = 6.5 from its line (Shared quantities); two maps
  reach `e` = 1.5 + 2 × 5 = 11.5, centred 5.5 and 10.5 from the line.
- Distances, from the deepest row up (§6.4):
  - row `{b11, d11}`: inner half 7, outer half max(7, 11.5) = 11.5, the
    conversion maps band of `d11`;
  - the children bands of `b1` and `d1`: own starts max(1.5 + 4, 7) = 7
    (`b1`, no map) and max(11.5 + 4, 7) = 15.5 (`d1`, beyond its conversion
    maps band), so both start at `c0` = 15.5, row 1 lies 15.5 + 7 = 22.5
    out, each band is 7 + 11.5 = 18.5 wide, and the above edges of `b1` and
    `d1` are both 15.5 + 18.5 = 34;
  - row `{b1, d1}`: inner 7, outer 34;
  - the children bands of `b` and `d`: own starts max(6.5 + 4, 7) = 10.5
    (`b`) and 7 (`d`), so `c0` = 10.5, row 1 at 10.5 + 7 = 17.5, each band
    7 + 34 = 41 wide, both above edges 51.5;
  - row `{b, d}`: inner 7, outer 51.5;
  - `piece` has no map: its children band starts at `p0 / 2` = 7, row 1
    at 14, 7 + 51.5 = 58.5 wide, so `Ea` = 65.5; below, its markers band
    reaches `Eb` = 26.9765625 (Shared quantities).
- Laid out alone, the children bands of `d` and of `b1` would start at 7,
  `d1` lying 14 above `d` and `b11` 14 above `b1`; laid out together they
  lie 17.5 and 22.5 above, in the rows of `b1` and of `d11`.
- `y_root` = max(8 + 65.5, 8 + 6.40234375) = 73.5 and `Hm` = 73.5 +
  26.9765625 + 8 = 108.4765625 → 108.4766 (§6.5).
- Drawn, each line at the card's top 8 plus its ordinate: `piece` at 81.5,
  `b` and `d` at 81.5 − 14 = 67.5, `b1` and `d1` at 67.5 − 17.5 = 50,
  `b11` and `d11` at 50 − 22.5 = 27.5. The maps' outlines: `ticks_b` from
  61 to 63; `tempo_d1` from 43.5 to 45.5 and `ticks_d1` from 38.5 to 40.5;
  `tempo_d11` from 21 to 23 and `ticks_d11` from 16 to 18, at `P` below
  the card's top exactly. The wedges' tips at 83, their bases at 96.
- Names (§6.6), one text per row, the row's names joined in traversal
  order and addressed by its first name, each baseline the row's ordinate
  plus (`a(11)` − `d(11)`) / 2 = 3.80810546875: `B11, D11` (`{"id": "b11", "part": ["name"]}`) at
  31.30810546875 → 31.3081, `B1, D1` (`{"id": "b1", "part": ["name"]}`) at 53.80810546875 →
  53.8081, `B, D` (`{"id": "b", "part": ["name"]}`) at 71.30810546875 → 71.3081, `Piece` at
  85.30810546875 → 85.3081.
- `N` = w(`B11, D11`, 11) = 51.00390625, of `Piece` (29.2724609375),
  `B, D` (23.009765625), `B1, D1` (37.0068359375) and `B11, D11`.
- `x0` = 16 + 51.00390625 + 8 = 75.00390625 → 75.0039; the label
  `0 ♩` of `origin` gives only 22.416015625. Every position lies a multiple of 25 from
  `x0`: `b` from 75.0039 to 225.0039, `b1` from 100.0039 to 200.0039,
  `b11` from 125.0039 to 175.0039, `d` from 275.0039 to 475.0039, `d1`
  from 325.0039 to 425.0039, `d11` from 350.0039 to 400.0039; each map
  spans its timeline.
- `R` = the label `16 ♩` of `length` at 475.00390625 + 9.279052734375 =
  484.282958984375, beyond the arrowhead tip 484.00390625 and the diamond
  corner of `d` at 479.50390625.
- `W` = 8 + (10 + 484.282958984375) = 502.282958984375; `H` = 8 + (10 +
  108.4765625) = 126.4765625.
- Page 534.282958984375 × 158.4765625 → **534.283 × 158.4766**.

## `map_row_siblings`

The root `piece` ("Piece", 8 quarters) and its locked children `ante`
("Ante", 4 at 0) and `cons` ("Cons", 4 at 4). `ante` carries the maps
`a_ticks` ("Ticks", to ticks) and `b_tempo` ("Tempo", to seconds), `cons`
the maps `a_tempo` ("Tempo") and `b_ticks` ("Ticks"); all four are
`LinearMap`s, so their names tell their keys apart. `piece` has no map.

- The rows, by first fit (§6.3): `ante` (0 to 200) and `cons` (200 to 400)
  do not conflict, since one starts where the other ends, so both lie in
  row 1 of `piece`'s children band. The rows are `{piece}` and `{ante,
  cons}`, every pitch `p` = `p0` = max(10 + 4, `h(11)`) = 14 (§6.2).
- The conversion maps bands of `ante` and `cons` lie above their lines at
  level 1, neither line having a children band, so they share one sequence
  of slots (§6.4, Conversion maps). Taken in traversal order: `a_ticks`,
  `b_tempo`, `a_tempo`, `b_ticks`. The keys are `Tempo` before `Ticks` (`e`
  before `i`). `Tempo`: `b_tempo` (0 to 200) and `a_tempo` (200 to 400) do
  not conflict and share sub-slot 1; `Ticks`: `a_ticks` and `b_ticks`
  likewise. So slot 1 holds both Tempo maps, slot 2 both Ticks maps, `J` =
  2: every Tempo map is centred 5.5 above its line and every Ticks map
  10.5, although `ante`'s Ticks map comes first in its canonical order. Each
  band is 11.5 wide (Shared quantities), so the above edges of `ante` and
  `cons` are 11.5 and their below edges 0. The maps are written in the
  order they are taken (§6.4, §7.2).
- Above `piece`: its children band at level 1. `piece`'s line reaches
  nothing there, so the band's own start is the larger of 1.5 + 4 = 5.5 and
  `p0 / 2` = 7: 7. Row 1 has the inner half max(7, 0) = 7 and the outer half
  max(7, 11.5) = 11.5, so the row lies `l1` = 7 + 7 = 14 out, the band is 7
  + 11.5 = 18.5 wide and `Ea` = 7 + 18.5 = 25.5. Below, the markers band
  alone: `Eb` = 26.9765625 (Shared quantities).
- `y_root` = max(8 + 25.5, 8 + 6.40234375) = 33.5; `Hm` = 33.5 + 26.9765625
  + 8 = 68.4765625 → 68.4766.
- Drawn, each ordinate the card's top 8 plus its item-coordinate value:
  `piece`'s line at 41.5, `ante`'s and `cons`'s at 41.5 − 14 = 27.5; the
  Tempo maps' outlines from 21 to 23, the Ticks maps' from 16 to 18, at `P`
  below the card's top exactly; the diamonds from 23.9 to 31.1; the wedges
  from 43 to 56, and their labels' baseline at 41.5 + 16.5 + `a(9)` =
  66.35400390625 → 66.354.
- Names (§6.6): `Ante, Cons`, addressed `{"id": "ante", "part": ["name"]}`,
  with its baseline at 27.5 + 3.80810546875 = 31.30810546875 → 31.3081, and
  `Piece` at 45.30810546875 → 45.3081.
- `N` = w(`Ante, Cons`, 11) = 59.68359375, above w(`Piece`, 11) =
  29.2724609375.
- `x0` = 16 + 59.68359375 + 8 = 83.68359375 → 83.6836; the label `0 ♩` of `origin`
  gives only 22.416015625. `x(4)` = 283.68359375 → 283.6836 and `x(8)` =
  483.68359375 → 483.6836: `ante`'s maps and line span `x0` to `x(4)`, its
  line stopping at the diamond's left corner 279.18359375 → 279.1836, and
  `cons`'s `x(4)` to `x(8)`.
- `R` = the arrowhead tip 483.68359375 + 9 = 492.68359375, beyond `length`'s
  label at 483.68359375 + 6.416015625 = 490.099609375 and `cons`'s diamond
  corner at 488.18359375.
- `W` = 8 + (10 + 492.68359375) = 510.68359375; `H` = 8 + (10 + 68.4765625)
  = 86.4765625.
- Page 542.68359375 × 118.4765625 → **542.6836 × 118.4766**.

## `map_row_subslots`

The root `form` ("Form", 32 quarters), an unlocked segment line of the
unnamed segments `a` (8 at 0), `b` (12 at 8) and `c` (12 at 20). `form`
carries the map `ticks_form`, `b` the map `ticks_b` and `c` the map
`ticks_c`, each "Ticks" to ticks, so all three have one key. The segments
have no line of their own: their maps join `form`'s conversion maps band
(§6.4, Segments without a line), which lies at level 1 above `form`'s line,
since no segment is a segment line and `form`'s children band so holds
nothing. A segment without a name has no label.

- The slots (§6.4, Conversion maps): taken, `form`'s own map first, then
  `b`'s and `c`'s. `ticks_form` spans `form`, 0 to 400, and takes sub-slot 1;
  `ticks_b` spans `b`, 100 to 250, conflicts with it and takes sub-slot 2;
  `ticks_c` spans `c`, 250 to 400, conflicts with `ticks_form` but not with
  `ticks_b`, which ends where it starts, and shares sub-slot 2. So `J` = 2,
  `ticks_form` lies 5.5 above the line and `ticks_b` and `ticks_c` 10.5, and
  the band is 11.5 wide (Shared quantities).
- The boundaries of `b` and `c` reach `k` = 8 on both sides of the line, and
  no segment label fills a tier, so the line reaches max(11.5, 8) = 11.5
  above and 8 below (§6.4, Segment lines). Above, the conversion maps band at
  level 1 is the outer edge, `Ea` = 11.5; below, the markers band at level
  −1 reaches max(26.9765625, 8) = 26.9765625 = `Eb`.
- `y_root` = max(8 + 11.5, 8 + 6.40234375) = 19.5; `Hm` = 19.5 + 26.9765625
  + 8 = 54.4765625 → 54.4766.
- Drawn: the line at 27.5; `ticks_form`'s outline from 21 to 23, those of
  `ticks_b` and `ticks_c` from 16 to 18, at `P` below the card's top; the
  boundaries from 19.5 to 35.5; the wedges from 29 to 42, and their labels'
  baseline at 27.5 + 16.5 + `a(9)` = 52.35400390625 → 52.354; the name
  `Form`'s baseline at 31.30810546875 → 31.3081.
- `N` = w(`Form`, 11) = 28.294921875.
- `x0` = 16 + 28.294921875 + 8 = 52.294921875 → 52.2949. `x(8)` =
  152.294921875 → 152.2949 (the boundary of `b`, the start of `ticks_b`),
  `x(20)` = 302.294921875 → 302.2949 (the boundary of `c`, where `ticks_b`
  ends and `ticks_c` starts) and `x(32)` = 452.294921875 → 452.2949.
- `R` = the label `32 ♩` of `length` at 452.294921875 + 9.279052734375 =
  461.573974609375, beyond the open arrowhead's tip 461.294921875.
- `W` = 8 + (10 + 461.573974609375) = 479.573974609375; `H` = 8 + (10 +
  54.4765625) = 72.4765625.
- Page 511.573974609375 × 104.4765625 → **511.574 × 104.4766**.

## `map_row_moved`

The root `piece` ("Piece", 8 quarters) and its locked children `ante`
("Ante", 4 at 0), with the maps `tempo_ante` ("Tempo") and `ticks_ante`
("Ticks"), and `cons` ("Cons", 4 at 3), with the map `ticks_cons`
("Ticks"); all are `LinearMap`s.

- The rows, by first fit (§6.3): `ante` (0 to 200) takes row 1; `cons` (150
  to 350) conflicts with it and takes row 2. The rows are `{piece}`,
  `{ante}` and `{cons}`, every pitch 14.
- The slots of each row (§6.4, Conversion maps): row `{ante}` has the keys
  `Tempo` and `Ticks`, so `tempo_ante` takes slot 1 (5.5 above `ante`'s
  line) and `ticks_ante` slot 2 (10.5), `J` = 2 and an above edge of 11.5;
  row `{cons}` has `Ticks` alone, so `ticks_cons` takes slot 1 (5.5), `J`
  = 1 and an above edge of 6.5. With `cons` at 4, in one row with `ante`,
  `ticks_cons` would lie in slot 2, 10.5 out.
- Above `piece`: its children band starts at 7, as in `map_row_siblings`.
  Row 1 has the halves `i1` = max(7, 0) = 7 and `o1` = max(7, 11.5) = 11.5,
  row 2 the halves `i2` = max(7, 0) = 7 and `o2` = max(7, 6.5) = 7. So `l1`
  = 7 + 7 = 14, `l2` = 14 + (11.5 + 7) = 32.5, the band is 7 + 11.5 + 7 +
  7 = 32.5 wide and `Ea` = 7 + 32.5 = 39.5. `Eb` = 26.9765625.
- `y_root` = 8 + 39.5 = 47.5; `Hm` = 47.5 + 26.9765625 + 8 = 82.4765625 →
  82.4766.
- Drawn: `piece`'s line at 55.5, `ante`'s at 55.5 − 14 = 41.5 and `cons`'s
  at 55.5 − 32.5 = 23; the outlines of `tempo_ante` from 35 to 37, of
  `ticks_ante` from 30 to 32 and of `ticks_cons` from 16.5 to 18.5; the
  diamonds from 37.9 to 45.1 (`ante`) and from 19.4 to 26.6 (`cons`); the
  wedges from 57 to 70, and their labels' baseline at 55.5 + 16.5 + `a(9)`
  = 80.35400390625 → 80.354; the names `Cons`, `Ante` and `Piece`, from the
  top row down, with their baselines at 26.80810546875 → 26.8081,
  45.30810546875 → 45.3081 and 59.30810546875 → 59.3081.
- `N` = w(`Piece`, 11) = 29.2724609375, above w(`Cons`, 11) = 27.11328125
  and w(`Ante`, 11) = 25.5771484375.
- `x0` = 16 + 29.2724609375 + 8 = 53.2724609375 → 53.2725; `x(3)` =
  203.2724609375 → 203.2725, `x(4)` = 253.2724609375 → 253.2725, `x(7)` =
  403.2724609375 → 403.2725 and `x(8)` = 453.2724609375 → 453.2725.
- `R` = the arrowhead tip 453.2724609375 + 9 = 462.2724609375.
- `W` = 8 + (10 + 462.2724609375) = 480.2724609375; `H` = 8 + (10 +
  82.4765625) = 100.4765625.
- Page 512.2724609375 × 132.4765625 → **512.2725 × 132.4766**.

## `label_float_rounding`

The root `take` ("Take") of 312.48979591836735 seconds, a float, with
nothing else but its two timestamps. Both labels are clocks (§5.2):
`origin` is labelled `0″` and `length`, its coordinate rounded as Python's
`round(x, 3)` rounds it, to 312.49, and split into 5 minutes and 12.49
seconds, `5′12.49″`; the wedge of
`length` still lies at `x0 + L`, since no position is computed from a
label. The line, its arrowhead and the start circle are
the physical domain's blue `#0050EF` (§4).

- Vertically the drawing is that of `bare`: `y_root` = 14.40234375, the
  markers band below of one tier, `Hm` = 49.37890625; the line at
  22.40234375 → 22.4023, the wedges from 23.90234375 → 23.9023 to
  36.90234375 → 36.9023, their labels' baseline at 47.25634765625 →
  47.2563, the name's at 26.21044921875 → 26.2104.
- `N` = w(`Take`, 11) = 26.59765625.
- `x0` = 16 + 26.59765625 + 8 = 50.59765625 → 50.5977; the label `0″` of
  `origin` (the advances 1303 + 765 = 2068, 9.087890625 wide) gives only
  16 + 4.5439453125 = 20.5439453125.
- `R` = the label `5′12.49″` of `length` (the advances 1303 + 465 + 2 ×
  1303 + 651 + 2 × 1303 + 765 = 8396, 36.896484375 wide) at 450.59765625 +
  18.4482421875 = 469.0458984375, beyond the arrowhead tip 459.59765625.
  The card is 469.0458984375 → 469.0459 wide.
- `W` = 8 + (10 + 469.0458984375) = 487.0458984375; `H` = 8 + (10 +
  49.37890625) = 67.37890625.
- Page 519.0458984375 × 99.37890625 → **519.0459 × 99.3789**.

## `timestamps`

The root `clt_1` (8 quarters) and its locked child `clt_2` (4 at 2), with
three named timestamps (§2): `timestamp_1` `Downbeat` at 3/2 and
`timestamp_2` `Climax` at 6 on `clt_1`, and `timestamp_3` `Entry` at 1 on
`clt_2`. No timeline has a name, so each row shows its ID, and the
manifest's `graphical` object has no rule. `Downbeat` draws the
default `display`, its wedge, its name and its cross-section line;
`Climax` draws `["wedge", "name"]`, so no cross-section line; `Entry`
draws all five, its labels stacked name, ID, coordinate (§6.4, Markers).
Every markers band is shown (§4), so `clt_2`'s draws `Entry`; it lies
after `line` in the default band order, so below `clt_2`'s line, towards
the root.

- `N` = w(`clt_1`, 11) = 25.91552734375, the same for `clt_2`.
- `x0` = 16 + 25.91552734375 + 8 = 49.91552734375 → 49.9155; the labels
  give only 16 + 22.897705078125 − 75 = −36.102294921875 (`Downbeat`)
  and 16 + 29.38623046875 − 150 = −104.61376953125 (`timestamp_3`, the
  widest label of `Entry`). `L` = 400 over 8 quarters, so a root position
  `q` lies at `x0 + 50q`: `Downbeat` at 49.91552734375 + 75 =
  124.91552734375 → 124.9155, `Climax` at 49.91552734375 + 300 =
  349.91552734375 → 349.9155, and `Entry`, at 2 + 1 = 3 on the root's
  axis (§3.1), at 49.91552734375 + 150 = 199.91552734375 → 199.9155.
  `clt_2` runs from `x(2)` = 149.91552734375 to `x(6)` = 349.91552734375,
  its line stopping at `Xe − 1.5w` = 345.41552734375 → 345.4155 for its
  diamond.
- The labels (§5.3), at size 9: `Downbeat` 45.79541015625 wide, `Climax`
  30.8935546875, `Entry` 23.94580078125, `timestamp_3` (advances 13374)
  13374 × 9 / 2048 = 58.7724609375, and the coordinate of `Entry`, the
  Fraction `[1, 1]` in quarters, `1 ♩` (§5.2), 12.83203125.
- `R` = the arrowhead tip 449.91552734375 + 9 = 458.91552734375; `Climax`
  ends at 349.91552734375 + 15.44677734375 = 365.3623046875,
  `timestamp_3` at 199.91552734375 + 29.38623046875 = 229.3017578125, and
  `clt_2`'s diamond at 349.91552734375 + 4.5 = 354.41552734375.
- The root's markers band, at level −1 from `c` = 0: the stacks of
  `Downbeat` and `Climax`, one line each, with the extents [75 −
  22.897705078125 − 1, 75 + 22.897705078125 + 1] = [51.102294921875,
  98.897705078125] and [300 − 15.44677734375 − 1, 300 + 15.44677734375 +
  1] = [283.55322265625, 316.44677734375] (§6.3), share tier 1, one line
  high, so `T` = 1: the band is 1.5 + 13 + 2 + 10.4765625 = 26.9765625
  wide, and `Eb` = 26.9765625.
- `clt_2`'s markers band, at level −1 of `clt_2` from `c` = 0: the stack
  of `Entry`, three lines, one item as wide as `timestamp_3`, [150 −
  29.38623046875 − 1, 150 + 29.38623046875 + 1] = [119.61376953125,
  180.38623046875], alone in tier 1, three lines high, so `T` = 3: the
  band is 1.5 + 13 + 2 + 3 × 10.4765625 = 16.5 + 31.4296875 = 47.9296875
  wide, towards the root. Nothing else of `clt_2` is present.
- Above the root, the children band alone. `clt_1`'s line reaches nothing
  there, so the band starts at the larger of 1.5 + 4 = 5.5 and `p0 / 2` =
  14 / 2 = 7 (`p0` = max(10 + 4, 12.8046875) = 14): 7. `clt_2`'s row has
  the inner half max(7, 47.9296875) = 47.9296875, its markers band, and
  the outer half max(7, 0) = 7; its line lies 7 + 47.9296875 = 54.9296875
  above the root's, the band is 47.9296875 + 7 = 54.9296875 wide, and
  `Ea` = 7 + 54.9296875 = 61.9296875.
- `y_root` = max(8 + 61.9296875, 8 + 6.40234375) = 69.9296875 in the
  member drawing; `Hm` = 69.9296875 + 26.9765625 + 8 = 104.90625 →
  104.9062 (a tie, to the even multiple, §7.3). Drawn, the root's line
  lies at 8 + 69.9296875 = 77.9296875 → 77.9297 and `clt_2`'s at
  77.9296875 − 54.9296875 = 23.
- The wedges (§6.6): the root's two from 77.9296875 + 1.5 = 79.4296875 →
  79.4297 to 77.9296875 + 14.5 = 92.4296875 → 92.4297; `Entry`'s from 23
  + 1.5 = 24.5 to 23 + 14.5 = 37.5.
- The labels (§6.6), line `n` starting 1.5 + 13 + 2 + (`n` − 1) ×
  10.4765625 out, each baseline `a(9)` = 8.35400390625 beyond that start:
  `Downbeat` and `Climax` on line 1, 16.5 out, at 77.9296875 + 16.5 +
  8.35400390625 = 102.78369140625 → 102.7837; `Entry` on line 1 at 23 +
  16.5 + 8.35400390625 = 47.85400390625 → 47.854, `timestamp_3` on line
  2, 16.5 + 10.4765625 = 26.9765625 out, at 49.9765625 + 8.35400390625 =
  58.33056640625 → 58.3306, and `1 ♩` on line 3, 16.5 + 20.953125 =
  37.453125 out, at 60.453125 + 8.35400390625 = 68.80712890625 → 68.8071.
  The names' baselines lie at 23 + (10.21044921875 − 2.59423828125) / 2 =
  26.80810546875 → 26.8081 and 77.9296875 + 3.80810546875 =
  81.73779296875 → 81.7378.
- The cross-section lines (§6.6), drawn last (§7.2), each across the
  whole card, from its top at 8 to its bottom at 8 + 104.90625 =
  112.90625 → 112.9062, less its gap, where its own wedge (at the
  rotation 0) and its labels stand. `timestamp_1`, at 124.9155, has its
  wedge's tip 1.5 below `clt_1`'s line and its one label's line ending
  1.5 + 13 + 2 + 10.4765625 = 26.9765625 below it, so the gap runs from
  79.4296875 to 77.9296875 + 26.9765625 = 104.90625, and the line is
  drawn as two: from `y1` = 8 to `y2` = 79.4296875 → 79.4297, through
  the children band and `clt_1`'s line, and from 104.90625 → 104.9062
  to 112.90625 → 112.9062. `timestamp_3`, at 199.9155, has its gap below
  `clt_2`'s line, from its tip at 24.5 to the end of its third line, 23 +
  (16.5 + 3 × 10.4765625) = 23 + 47.9296875 = 70.9296875: from 8 to 24.5,
  through `clt_2`'s line, and from 70.9296875 → 70.9297 to 112.90625 →
  112.9062, through `clt_1`'s line and its markers band, which holds
  nothing at that `x`. `timestamp_2` does not list `cross_section` and
  draws no line. No line takes room or reaches the card's shadow.
  `timestamp_3`'s line crosses `clt_1` at 3, a secondary coordinate
  (§2), whose wedge and labels the last default rule hides (§4): it
  draws nothing, takes no room and cuts no line; `timestamp_1`, at 3/2,
  lies before `clt_2`'s start and crosses no other timeline.
- The descriptors (§7.2): the card's shadow and the card; `clt_1`'s line,
  circle and arrowhead; `clt_2`'s line, circle and diamond; the wedges of
  `timestamp_1`, `timestamp_2` and `timestamp_3`; the names `clt_2` and
  `clt_1`; the labels `Downbeat`, `Climax`, `Entry`, `timestamp_3` and
  `1 ♩`, addressed `{"id": X, "part": ["name"]}` for each timestamp `X` and
  `{"id": "timestamp_3", "part": ["id"]}` and `{"id": "timestamp_3",
  "part": ["coordinate"]}`; and the two lines of `timestamp_1`'s
  cross-section line, then the two of `timestamp_3`'s, each pair from the
  top down, all addressed `{"id": X, "part": ["line"]}`.
- `W` = 8 + (10 + 458.91552734375) = 476.91552734375; `H` = 8 + (10 +
  104.90625) = 122.90625 → 122.9062.
- Page 508.91552734375 × 154.90625 → **508.9155 × 154.9062**.

## `bundle__bundle_matchstamp_cards`

The block "MatchStamp cards" of two groups that share the member `score`
(8 quarters), which holds the child `second-half` (4 quarters at 4): the
frame of `group_1` "Performance", in the display order `score`,
`performance` (4.0 seconds), and below it the frame of `group_2` "Page",
in the display order `score`, `page` (800 pixels). `score` is so drawn in
two cards, one in each frame, each with its children band holding the row
of `second-half` (§8.1). Three match timestamps (§2) draw only their
cross-section lines (`display` `["cross_section"]`), so none has a gap
(§6.6): `timestamp_1` at 4 on
`score`, `timestamp_2` at 1.0 on `performance` and `timestamp_3` at 2 on
`second-half`. The MatchStamp `matchstamp_1` "Bar 2, performed" has the
anchor `anchor_1` from `timestamp_2` to `timestamp_1`, and `matchstamp_2`
"Second half, bar 1" the anchor `anchor_2` from `timestamp_1` to
`timestamp_3`; both anchors list `name` in their `display`. The drawing
proves the branches of §8.7 that `bundle__bundle_matchstamps` does not
reach: two segments that overlap vertically, the shortest line over the
several segments of a timestamp drawn in two cards, and the tie between
two equally short lines.

- `xn` = 24 (frames). `N` = w(`Performance`, 11) = 70.29150390625 (13087
  advances), of `Score`, `Second half` (64.61962890625), `Performance` and
  `Page`.
- `x0` = 24 + 70.29150390625 + 8 = 102.29150390625 → 102.2915; no
  ancestor line runs on to the left, and the centred labels of `origin`
  and `length` give less. `L` = 400 over each member's length, so a
  position `q` of `score` lies at `x0 + 50q`, a second `t` of
  `performance` at `x0 + 100t`.
- `R` = the label `800 px` of `page`'s `length`, 7072 × 9 / 2048 =
  31.078125 wide, ending at 502.29150390625 + 15.5390625 =
  517.83056640625, beyond the arrowhead tips at 511.29150390625 and the
  diamond of `second-half` at 506.79150390625; neither frame's title
  reaches as far. Each card is 517.83056640625 − 8 = 509.83056640625 →
  509.8306 wide and each frame 517.83056640625 + 8 = 525.83056640625
  → 525.8306, from `x` = 8.
- The member drawing of `score`, alike in both frames: above its line
  only the children band, starting at the larger of 1.5 + 4 = 5.5 and `p0
  / 2` = 7; the row of `second-half` has the inner and outer halves 7 (no
  match timestamp draws a wedge or a label, so its markers band holds
  nothing that takes room), so its line lies 14 above `score`'s and `Ea`
  = 7 + 14 = 21. `y_root` = max(8 + 21, 8 + 6.40234375) = 29 and `Hm` =
  29 + 26.9765625 + 8 = 63.9765625 → 63.9766. `performance` and `page`
  have no band above: `y_root` = 8 + 6.40234375 = 14.40234375 and `Hm` =
  14.40234375 + 26.9765625 + 8 = 49.37890625 → 49.3789.
- The frames (§8.4): `Pt` = 28.8046875, so `group_1`'s frame starts at
  28.8046875 → 28.8047 and is 8 + 12.8046875 + 4 + 63.9765625 + 8 +
  49.37890625 + 8 = 154.16015625 → 154.1602 high; its cards start at
  28.8046875 + 24.8046875 = 53.609375 → 53.6094 (`score`) and 53.609375 +
  63.9765625 + 8 = 125.5859375 → 125.5859 (`performance`). `group_2`'s
  frame, the block's spacing 8 below, starts at 28.8046875 + 154.16015625
  + 8 = 190.96484375 → 190.9648, its cards at 215.76953125 → 215.7695
  (`score`) and 287.74609375 → 287.7461 (`page`).
- Drawn, each line at its card's top plus `y_root`: in `group_1`, `score`
  at 82.609375 → 82.6094, `second-half` 14 above at 68.609375 → 68.6094,
  `performance` at 139.98828125 → 139.9883; in `group_2`, `score` at
  244.76953125 → 244.7695 and `second-half` at 230.76953125 → 230.7695.
- The match timestamps' abscissae: `timestamp_1` at `x0 + 200` =
  302.29150390625 → 302.2915, `timestamp_2` at `x0 + 100` =
  202.29150390625 → 202.2915, and `timestamp_3`, at 4 + 2 = 6 on the
  root's axis (§3.1), at `x0 + 300` = 402.29150390625 → 402.2915.
- The cross-section segments (§6.6, §8.7), each a match timestamp's line
  across the whole card that draws its timeline's line, from its top to
  its bottom: `timestamp_1` and `timestamp_3`, whose `second-half` is drawn
  in both `score` cards, from 53.609375 → 53.6094 to 53.609375 +
  63.9765625 = 117.5859375 → 117.5859 in `group_1` and from
  215.76953125 → 215.7695 to 279.74609375 → 279.7461 in `group_2`;
  `timestamp_2` from 125.5859375 → 125.5859 to 125.5859375 + 49.37890625
  = 174.96484375 → 174.9648 in `performance`'s card. Each is drawn as one
  line (`data-id="timestamp_N" data-part="line"`). In each `score` card
  the line of `timestamp_1` also crosses `second-half` at its start 0, its
  ends included, and that of `timestamp_3` crosses `score` at 6: secondary
  coordinates (§2), which draw nothing, a match timestamp's `display`
  listing neither a wedge nor a label and the last default rule hiding
  them (§4).
- `anchor_1`, `A` the segment of `timestamp_2` (`a1` = 125.5859375, `a2`
  = 174.96484375), `B` a segment of `timestamp_1`: in `group_1`, `lo` =
  125.5859375 > `hi` = 117.5859375 and `a2` ≥ `b1` = 53.609375, so the
  third branch, from (`Xa`, `a1`) to (`Xb`, `b2`): (202.29150390625,
  125.5859375) to (302.29150390625, 117.5859375), `dx` = 100, `dy` = −8,
  `dx² + dy²` = 10064; in `group_2`, `a2` < `b1` = 215.76953125, so the
  second branch, from (202.29150390625, 174.96484375) to
  (302.29150390625, 215.76953125), `dy` = 40.8046875,
  11665.02252197265625. The line of `group_1` is shorter: from
  (202.2915, 125.5859), the top of `performance`'s card, to (302.2915,
  117.5859), the bottom of `score`'s.
- `anchor_2`, `A` a segment of `timestamp_1`, `B` a segment of
  `timestamp_3`, four pairs in the order of `A`'s segments, then `B`'s:
  `group_1` with `group_1` overlaps wholly (`lo` = 53.609375, `hi` =
  117.5859375), so the line is horizontal at their middle 85.59765625,
  `dx` = 100, 10000; `group_1` with `group_2`, `a2` = 117.5859375 < `b1`
  = 215.76953125, `dy` = 98.18359375, 19640.0180816650390625; `group_2` with `group_1`, the third branch from
  (302.29150390625, 215.76953125) to (402.29150390625, 117.5859375), `dy`
  = −98.18359375, the same; `group_2` with `group_2` overlaps at
  247.7578125, 10000. The first and the last tie, so the first in that
  order is drawn: from (302.2915, 85.5977) to (402.2915, 85.5977).
- The names, at size 9, centred on each line's midpoint with the baseline
  `(a(9) − d(9)) / 2` = 3.11572265625 below it: `Bar 2, performed`
  (17531 advances, 77.04052734375 wide) at (252.29150390625,
  121.5859375 + 3.11572265625 = 124.70166015625) → (252.2915,
  124.7017), and `Second half, bar 1` (18684 advances, 82.107421875 wide)
  at (352.29150390625, 85.59765625 + 3.11572265625 = 88.71337890625) →
  (352.2915, 88.7134). Neither line nor name takes room: `R`, the frames
  and the cards are as without them.
- The descriptors (§7.2, §8.5): each frame, its title and its cards as
  for any frame, the cross-section lines of `timestamp_1` and then
  `timestamp_3` last in each `score` card, that of `timestamp_2` last in
  `performance`'s; after `page`'s card the lines of `anchor_1` and
  `anchor_2` (`data-id="anchor_1"`, `data-id="anchor_2"`), then their
  names (`data-id="anchor_1" data-part="name"`, `data-id="anchor_2"
  data-part="name"`).
- `W` = 8 + 525.83056640625 + 8 = 541.83056640625, the frames' right
  edge beyond the cards' shadows at 527.83056640625; `H` = 190.96484375 +
  154.16015625 + 8 = 353.125.
- Page 573.83056640625 × 385.125 → **573.8306 × 385.125**.

## `map_band_order_subset`

The manifest of `map` with the band order `["markers", "line"]` for the
root `melody` in its `graphical.order`, which lists two of the six
entries. Completed against the default order (§6.4, The band order), the
facets it leaves out keep their side and lie beyond the listed ones:
`children`, `conversion_maps`, `markers`, `line`, `regions`,
`flow_control`. `phrase` has no entry, so it follows that completed order.
The markers band of `melody` so lies against its line above it, the map
`tempo` beyond it, and the children band beyond both.

- As in `map`: `N` = 39.53662109375, `x0` = 16 + 39.53662109375 + 8 =
  63.53662109375 → 63.5366, `R` = the arrowhead tip 472.53662109375, beyond
  the end of `length`'s label `8 ♩` at 463.53662109375 + 6.416015625 =
  469.95263671875.
- Above `melody`'s line, outwards (§6.4, Levels): the markers band at level
  1 from `c` = 0, 26.9765625 wide (Shared quantities), so its wedges' tips
  lie 1.5 above the line and their bases 14.5 above it; the conversion maps
  band at level 2 from `c0` = 26.9765625 + 4 = 30.9765625, `tempo` in slot 1
  centred `c0 + w / 2 + (g + d) − d / 2` = 30.9765625 + 1.5 + 5 − 1 =
  36.4765625 above the line, its outline from 35.4765625 to 37.4765625,
  the band `e` = 6.5 wide and so ending at 37.4765625; the children band at
  level 3 from max(37.4765625 + 4, `p0 / 2` = 7) = 41.4765625.
- `phrase` lies in that band's row 1. Its own order puts its conversion
  maps band above its line; its markers band, holding no named timestamp,
  is absent, so the map band lies at level 1 from `c` = 0, `ticks`
  centred 5.5 above its line and reaching 6.5. Below its line nothing is
  present. The row's inner half, towards `melody`'s line, is max(7, 0) = 7
  and its outer half max(7, 6.5) = 7, so `phrase`'s line lies 41.4765625 +
  7 = 48.4765625 above `melody`'s, and `Ea` = 41.4765625 + 14 =
  55.4765625.
- Below `melody`'s line nothing is present: its map stack lies above, so
  `Eb` = 0 and the name's half slot `h(11) / 2` = 6.40234375 sets the
  content below the line (§6.5).
- `y_root` = max(8 + 55.4765625, 8 + 6.40234375) = 63.4765625 and `Hm` =
  63.4765625 + max(0, 6.40234375) + 8 = 77.87890625 → 77.8789.
- Drawn, from the card's top at 8:
  - `melody`'s line at 71.4765625 → 71.4766, its arrowhead from 66.9765625
    to 75.9765625;
  - the wedges of `origin` and `length` from their tips at 69.9765625 →
    69.9766 to their bases at 56.9765625 → 56.9766;
  - their labels' line starts 1.5 + 13 + 2 = 16.5 above the line, and the
    baseline lies `d(9)` beyond that start: at 71.4765625 − 16.5 −
    2.12255859375 = 52.85400390625 → 52.854;
  - `tempo`'s outline from 34 to 36;
  - `phrase`'s line at 23, the outline of `ticks` from 16.5 to 18.5, as in
    `map`;
  - the names' baselines, centred on their lines with `(a(11) − d(11)) /
    2` = 3.80810546875: `Melody` at 75.28466796875 → 75.2847, `Phrase` at
    26.80810546875 → 26.8081.
- `W` = 8 + 482.53662109375 = 490.53662109375; `H` = 8 + (8 + 77.87890625
  + 2) = 95.87890625, the card's shadow included.
- Page 522.53662109375 × 127.87890625 → **522.5366 × 127.8789**.

## `group__group_child_member_stamps`

The group "Middle" of `group_parent_both` in the display order `middle`,
`recording`: the child `middle` (8 quarters at 4) of the piece `piece` (16
quarters), and the root `recording` (10.0 seconds). The member `middle`
carries the ancestor line of `piece` below its own line (Shared
quantities), which runs on to both sides. Three
timestamps on the members draw their cross-section lines alone: `timestamp_1`
"Bar 2" at 2 on `middle`, and the match timestamps `timestamp_2` at 4 on
`middle` and `timestamp_3` at 5.0 on `recording`, which the anchor
`anchor_1` of the MatchStamp "Middle, bar 3" joins, its name drawn;
`middle`'s `origin` and `length` are the groupstamps `timestamp_4` and
`timestamp_5`. The drawing proves that a cross-section line crosses each
card its timeline is drawn in, a child member's ancestor line and an
ancestor card included (§6.6, Cross-section lines), and that an anchor
joins two such lines across the gap between their cards (§8.7). `piece`
is drawn whole in its ancestor card behind the frame (§8.8). The bullets
before the ancestor card's give positions in place coordinates; drawn,
each lies 252.33544921875 further right.

- `xn` = 24 (a frame). `N` = w(`Recording`, 11) = 55.70361328125 (10371
  advances), of `Middle` (36.33544921875), `Recording` and `Piece` (at
  size 9, 23.9501953125).
- `x0` = the chevron term `xn + N + G' + 8 × wa` = 24 + 55.70361328125 + 8
  + 24 = 111.70361328125 → 111.7036, `piece` starting at −4 on `middle`'s
  axis (§8.3); the centred labels give less. `L` = 400 over each member's
  length, so a quarter `q` of `middle` lies at `x0 + 50q` and a second `t`
  of `recording` at `x0 + 40t`.
- `R` = the tip of the outer right chevron of `piece`, `x0 + L + 8w` =
  535.70361328125, since `piece` ends at 12 on `middle`'s axis, beyond its
  length 8; the arrowhead tip of `recording` lies at 520.70361328125. Each
  card is 535.70361328125 − 8 = 527.70361328125 → 527.7036 wide and the
  frame 535.70361328125 + 8 = 543.70361328125 → 543.7036.
- The member drawing of `middle`: no band above its line, so `y_root` = 8
  + 6.40234375 = 14.40234375; below it its markers band of 26.9765625 and
  then its ancestor band of one row, `piece` (Shared quantities), 37.9765625
  below `middle`'s line: `Eb` = 44.9765625 and `Hm` = 14.40234375 +
  44.9765625 + 8 = 67.37890625, as in `group__group_child_member`.
  `recording`: `y_root` = 14.40234375 and `Hm` = 49.37890625.
- The frame (§8.4) starts at 8 and is 8 + 12.8046875 + 4 + 67.37890625 +
  8 + 49.37890625 + 8 = 157.5625 high; `middle`'s card starts at 8 + 8 +
  12.8046875 + 4 = 32.8046875 → 32.8047, `recording`'s at 32.8046875 +
  67.37890625 + 8 = 108.18359375 → 108.1836.
- Drawn: `middle`'s line at 32.8046875 + 14.40234375 = 47.20703125 →
  47.207, `piece`'s ancestor line at 47.20703125 + 37.9765625 =
  85.18359375 → 85.1836, `recording`'s line at 108.18359375 + 14.40234375
  = 122.5859375 → 122.5859.
- The cross-section lines (§6.6), written after the member drawing's
  labels in the order of `middle`'s markers band: `timestamp_4` at `x0` =
  111.7036 and `timestamp_5` at `x0 + 400` = 511.7036 each from the card's
  top, 32.8047, to 48.707 and from 74.1836 to the card's bottom, 32.8046875
  + 67.37890625 = 100.18359375 → 100.1836 (Shared quantities); between
  them `timestamp_1` at `x0 + 100` = 211.70361328125 → 211.7036 and
  `timestamp_2` at `x0 + 200` = 311.70361328125 → 311.7036, neither
  drawing a wedge or a label and so without a gap, each written `y1="32.8047"
  y2="100.1836"`, crossing `middle`'s line, its markers band, whose wedges
  and labels lie at its quarters 0 and 8, away from both lines, and the
  ancestor line of `piece` at 85.18359375, where each has a secondary
  coordinate (§2), at 6 and 8 of `piece`'s quarters, which draws nothing
  (its `display` lists no wedge or label, and the last default rule hides
  them, §4); `timestamp_3`, at `x0 + 200` = 311.70361328125, across
  `recording`'s card, `y1="108.1836" y2="157.5625"` (108.18359375 to
  108.18359375 + 49.37890625 = 157.5625). The groupstamps `timestamp_4`
  and `timestamp_5` also cross the frame below `middle`'s card, from
  100.1836 to 157.5625, after `recording`'s card.
- `anchor_1` (§8.7), `A` the segment of `timestamp_2` from `a1` =
  32.8046875 to `a2` = 100.18359375, `B` that of `timestamp_3` from `b1` =
  108.18359375 to `b2` = 157.5625 (the ancestor card gives none): `a2 <
  b1`, so `A` lies above `B` and the line runs from (`Xa`, `a2`) to (`Xb`,
  `b1`), from (311.7036, 100.1836) to (311.7036, 108.1836), vertical and 8
  long, across the frame's spacing between the two cards, the two
  coordinates lying at one proportion of the frame's length (4 of 8
  quarters, 5.0 of 10.0 seconds): with the two cross-section lines it
  forms one vertical from 32.8046875 to 157.5625.
- Its name `Middle, bar 3` (13418 advances at size 9, 58.9658203125 wide)
  is centred on the line's midpoint, (311.70361328125, (100.18359375 +
  108.18359375) / 2 = 104.18359375), with its baseline `(a(9) − d(9)) /
  2` = 3.11572265625 below it, at 107.29931640625 → 107.2993. Neither
  line nor name takes room.
- The descriptors (§8.5): the frame's lines of the groupstamps, then the
  line and the name of `anchor_1` are the last four, after `recording`'s
  card and member drawing.
- The ancestor card of `piece` (Shared quantities), aligned to `middle`:
  `s0` = 103.70361328125, `ts` = −4, `λ` = 8, `te` = 12, `us` = −0.5,
  `ue` = 1.5, `xs` = −96.29638671875, `xe` = 703.70361328125, `LA` = 800.
  `N'` = w(`Middle`, 11) = 36.33544921875 (wider than `Piece`), `s0'` =
  52.33544921875; `Mr'` = the arrowhead 9. The seams, at `piece`'s 4 and
  12: `OL` = 103.70361328125 and `OR` = 543.70361328125 −
  503.70361328125 = 40; `piece` runs on past both. `r` = 1: with `Fw` =
  543.70361328125 and `Fh` = 157.5625, `zG` = 1.8833790598156273, `zb` =
  `Z`, `B` = 716.8, `c` = 271.851806640625, `σ` = 52.33544921875, `dl` =
  324.187255859375 and `dr` = 279.851806640625, `EL` = `ER` = 4, `uL` =
  `uR` = 0.5: `r` = min(1, 1, 1.9630637207031247, 2.1847409667968747),
  drawn whole. `dx` = (−96.29638671875 − 103.70361328125) −
  52.33544921875 = −252.33544921875, the left edge −252.33544921875, the
  place −244.33544921875; the card is 103.70361328125 + 52.33544921875 +
  800 + 40 + 9 + 8 = 1013.0390625 → 1013.0391 wide, 63.37890625 → 63.3789
  high, its top 85.18359375 − 48.9765625 = 36.20703125 → 36.207 and its
  bottom with its shadow at 101.5859375, inside the frame. The origin is
  (252.33544921875, 0), and the card is drawn at (8, 36.207). In it
  (drawn): `piece`'s line at 85.1836 from 60.3354, whole across both
  seams, to 1004.0390625 → 1004.0391, its arrowhead's tip at 1013.0391;
  `middle`'s row at 51.207 from 364.0391 (4 of 16 quarters, where
  `middle`'s own line starts in the frame, 111.70361328125 +
  252.33544921875) to 764.0391 with the wedges and labels of `origin` and
  `length`; `middle`'s timestamps draw their cross-section lines across
  the ancestor card, in the order `timestamp_4`, `timestamp_1`,
  `timestamp_2`, `timestamp_5`, at 364.0391, 464.0391, 564.0391 and
  764.0391 drawn, `timestamp_1`'s and `timestamp_2`'s each from its top at

  36.20703125 → 36.207 to its bottom at 36.20703125 + 63.37890625 =
  99.5859375 → 99.5859, `origin`'s and `length`'s from 36.207 to 52.707
  and from 78.1836 to 99.5859, written last in the card's drawing, before
  the frame.
- `W` = 8 + 770.70361328125 + 252.33544921875 = 1031.0390625, the right
  edge of the card with its shadow, −244.33544921875 + 1013.0390625 + 2,
  beyond the frame's 551.70361328125; `H` = 8 + (8 + 157.5625) =
  173.5625.
- Page 1063.0390625 × 205.5625 → **1063.0391 × 205.5625**.


## `group__group_grandchild_parent_on_top`

The manifest of `group__group_grandchild` (the grandchild `theme`, 8
quarters at 8 in the movement `movement` of 16 quarters at 16 in the score
`score` of 64, and the root `recording`, 12.0 seconds, in the group "Theme"
in the display order `theme`, `recording`) with the band order `["line",
"children", "conversion_maps", "markers", "regions", "flow_control"]` for
`movement` in its `graphical.order` (§6.4, The band order):
`movement`'s children lie below its line. `theme` has no entry and follows
that order, its markers band below its line as in the default, and
neither carries a map, so where the conversion maps band lies moves
nothing. So in `theme`'s card the faded line of `movement` lies
above `theme`'s, the parent on top, and that of `score`, whose order is the
default, below it (§8.3, Sides): the member drawing has an ancestor band on
each side. `score` is drawn in its ancestor card behind the frame (§8.8),
with the elisions it derives (§8.9) and whole in
`group__group_grandchild_parent_on_top__full`, and there `theme`'s row
lies between the lines of `movement` and `score`, as in `theme`'s card.
The bullets before the ancestor card's give positions in place
coordinates; drawn, each lies 245.69419642857133 further right and
2.171875 lower, and 1274.265625 further right in the `__full` case.

- As in `group__group_grandchild`: `xn` = 24, `N` = w(`Recording`, 11) =
  55.70361328125, `x0` = the chevron term 111.70361328125 → 111.7036 (both
  ancestor lines run on to the left, `movement` starting at −8 and `score`
  at −24 on `theme`'s axis), and `R` = the outer chevron tip of `score`,
  which runs on to the right, 535.70361328125. `movement` ends with
  `theme`, `te` = −8 + 16 = 8 = `λ`, so its faded line ends at `x0 + L` =
  511.70361328125 with its own end, the diamond of a child (§8.3). Each
  card is 535.70361328125 − 8 = 527.70361328125 → 527.7036 wide and the
  frame 535.70361328125 + 8 = 543.70361328125 → 543.7036.
- `theme`'s card, above its line: `theme` has no map, so no band of its
  own lies there, and the ancestor band starts at max(`p0 / 2` = 7,
  max(0, 1.5) + 4) = 7 (§8.3). Its one row, `movement`, on the side away
  from `score`'s, has the inner half 7 and the outer half 7 (Shared
  quantities), so `movement`'s faded line lies 7 + 7 = 14 above `theme`'s
  and `Ea` = 7 + 7 + 7 = 21.
- Below `theme`'s line: its markers band of 26.9765625 and the ancestor
  band of one row, `score` (Shared quantities): `score`'s faded line lies
  30.9765625 + 7 = 37.9765625 below `theme`'s, and `Eb` = 44.9765625.
- `y_root` = max(8 + 21, 8 + 6.40234375) = 29 and `Hm` = 29 + 44.9765625 +
  8 = 81.9765625 → 81.9766 (`theme`) and 49.37890625 (`recording`); the
  frame starts at 8 and is 8 + 12.8046875 + 4 + 81.9765625 + 8 +
  49.37890625 + 8 = 172.16015625 → 172.1602 high, `theme`'s card at
  32.8046875 → 32.8047 and `recording`'s at 32.8046875 + 81.9765625 + 8 =
  122.78125 → 122.7812.
- Drawn, in `theme`'s card:
  - `theme`'s line at 32.8046875 + 29 = 61.8046875 → 61.8047, its diamond
    from 58.2047 to 65.4047 (`61.8046875 ∓ 1.2w` in binary64), its
    wedges from their tips at 63.3046875 → 63.3047 to their bases at
    76.3046875 → 76.3047, and its labels `0 ♩` and `8 ♩` with the baseline
    61.8046875 + 24.85400390625 = 86.65869140625 → 86.6587;
  - `movement`'s faded line at 61.8046875 − 14 = 47.8046875 → 47.8047,
    its chevrons on the left and its diamond;
  - `score`'s faded line at 61.8046875 + 37.9765625 = 99.78125 → 99.7812,
    its chevrons on both sides;
  - the names at 1194.562 drawn: `Score` (size 9) at 99.78125 +
    3.11572265625 = 102.89697265625 → 102.897, `Movement` (size 9) at
    47.8046875 + 3.11572265625 = 50.92041015625 → 50.9204 and `Theme` at
    61.8046875 + 3.80810546875 = 65.61279296875 → 65.6128;
  - the cross-section lines of `origin` and `length` from 32.8047 to
    63.3047 and from 88.78125 → 88.7812 to the card's bottom 114.78125 →
    114.7812, crossing both faded lines; across the frame from 114.7812 to
    the bottom of `recording`'s card, 172.1602;
  - the descriptors follow §8.5, each kind from `A1` to `Ak`: the faded
    line of `score` and its chevrons before `movement`'s, and the names
    `Score` and `Movement` before `Theme`.
- `recording`'s line at 122.78125 + 14.40234375 = 137.18359375 →
  137.1836, its labels `0″` and `12″` with the baseline 162.0376.
- The ancestor card of `score`, aligned to `theme`, horizontally as in
  `group__group_grandchild`: `s0` = 103.70361328125, `ts` = −24, `λ` = 8,
  `te` = 40, `us` = −3, `ue` = 5, `xs` = −1096.29638671875, `xe` =
  2103.70361328125, `LA` = 3200, `N'` = w(`Movement`, 11) = 58.265625,
  `s0'` = 74.265625, `Mr'` = the arrowhead 9, the seams `OL` =
  103.70361328125 and `OR` = 40, and whole the left edge −1274.265625, the
  place −1266.265625 and the card 3434.96923828125 → 3434.9692 wide. Vertically, `score`'s own drawing (§6.4): its children
  band lies above its line, from max(1.5 + 4, `p0 / 2` = 7) = 7, and holds
  `movement`'s row. `movement` draws no wedge, so its markers band is
  absent and its children band lies at level −1, below its line, from
  max(1.5 + 4, 7) = 7, holding `theme`'s row: the inner half 7 (`theme`
  draws nothing above its line) and the outer half 26.9765625 (its markers
  band below it). So `theme`'s line lies 7 + 7 = 14 below `movement`'s,
  and `movement`'s below side reaches 7 + 7 + 26.9765625 = 40.9765625.
  `movement`'s row in `score`'s band has the inner half max(7, 40.9765625)
  = 40.9765625, towards `score`'s line, and the outer half 7: `movement`'s
  line lies 7 + 40.9765625 = 47.9765625 above `score`'s, `theme`'s
  47.9765625 − 14 = 33.9765625 above it, and `Ea` = 7 + 40.9765625 + 7 =
  54.9765625. `score`'s line lies 8 + 54.9765625 = 62.9765625 below the
  card's top, `movement`'s 15 and `theme`'s 29, and the card is 62.9765625
  + 6.40234375 + 8 = 77.37890625 → 77.3789 high.
- `score`'s faded line in `theme`'s card lies at 99.78125, so the card's
  top is 99.78125 − 62.9765625 = 36.8046875 → 36.8047, below `Pt` = 8, and
  its bottom with its shadow at 116.18359375, inside the frame, whole;
  `movement`'s row in it at 51.8046875 → 51.8047 and `theme`'s at
  65.8046875 → 65.8047 lie 4 lower than their faded and own lines in
  `theme`'s card (Shared quantities). Whole (`__full`):
  `Yt` = 0 and `Xl` = −1274.265625, the origin (1274.265625, 0),
  and the card is drawn at (8, 36.8047), its shadow at (10, 38.8047). In it
  (drawn): `score`'s line at 99.7812 from 82.2656, whole across both
  seams, to 3425.9692, its arrowhead's tip at 3434.9692; `movement`'s from
  882.2656 (16 of 64 quarters) to its diamond at 1785.9692; `theme`'s from
  1385.9692 (24 of 64), where `theme`'s own line starts in the frame, to
  its diamond at 1785.9692, its wedges and labels `0 ♩` and `8 ♩` with the baseline
  90.6587, its `origin` and `length` crossing the card from 36.8047 to
  67.3047 and from 92.7812 to 114.1836; the names at 16, all at size 11:
  `Movement` at 55.6128, `Theme` at 69.6128 and `Score` at 103.5894. `W` =
  8 + 2170.70361328125 + 1274.265625 = 3452.96923828125, the right edge of
  the card with its shadow, as in `group__group_grandchild`; `H` = 8 + (8 +
  172.16015625) = 188.16015625; the page 3484.96923828125 × 220.16015625 →
  **3484.9692 × 220.1602**.
- Derived: horizontally as `group__group_grandchild`, whose frame and card
  have the same widths, `σ` and pieces: `r` = 0.14285714285714285, the
  gaps `score` 0–16, `movement` 0–8 and `score` 33–63, `dx` =
  −245.69419642857133, the card 1034.96923828125 → 1034.9692 wide, the
  origin's `x` 245.69419642857133; `Fh` = 172.16015625 changes no term,
  `zG` being set by `Fw`. Vertically the stacks of the gaps take room:
  `Score` twice in `score`'s markers band, 26.9765625 below its line, and
  `Movement` in `movement`'s, which `movement`'s band order puts after
  its children band, at level −2, from 40.9765625 + 4 = 44.9765625 to
  71.953125 below `movement`'s line. So `movement`'s row in `score`'s
  children band has the inner half 71.953125: `movement`'s line lies 7 +
  71.953125 = 78.953125 above `score`'s, `theme`'s 14 below `movement`'s,
  `Ea` = 85.953125, `score`'s line 93.953125 below the card's top and the
  card 93.953125 + 26.9765625 + 8 = 128.9296875 → 128.9297 high. Its top
  lies at 99.78125 − 93.953125 = 5.828125, above `Pt` = 8: `Yt` = −2.171875
  and the origin (245.69419642857133, 2.171875), so the block is 8 + (8 +
  172.16015625) + 2.171875 = 190.33203125 high. Drawn: the card at (8, 8),
  its bottom at 136.9296875 and with its shadow at 138.9296875, inside the
  frame, which lies at (253.6942, 10.1719); `movement`'s row at 23,
  `theme`'s at 37 and `score`'s line at 101.953125 → 101.9531, each name
  at 16 (baselines 26.8081, 40.8081 and 105.7612); `score`'s start circle
  at 82.2656 and its line from 253.6942, whole across both seams, to
  847.3978 and from 975.9692 to 1025.9692, its arrowhead's tip at
  1034.9692; `movement`'s start circle at 196.5513 and its line from
  253.6942 to its diamond at 757.3978; `theme`'s from 357.3978 to its
  diamond at 757.3978, its labels `0 ♩` and `8 ♩` with the baseline 61.854
  and its `origin` and `length` crossing the card from 8 to 38.5 and from
  63.9766 to 136.9297. The gaps draw one ellipsis each, centred at
  139.4085, 225.1228 and 911.6835 and at `ym` = (8 + 136.9296875) / 2 =
  72.46484375 → 72.4648, and below it the labels `Score`, `Movement` and
  `Score` with the baseline 84.81884765625 → 84.8188. `W` =
  1052.96923828125, as in `group__group_grandchild`; `H` = 190.33203125.
- Page 1084.96923828125 × 222.33203125 → **1084.9692 × 222.332**.

## `group__group_elided_inside`

The group "Excerpt" in the display order `excerpt`, `recording`: the
excerpt `excerpt` (8 quarters at 8 in the movement `first`, 32 quarters
at 0 in the piece `piece` of 64, which holds the movement `second`, 32
quarters at 32) and the root `recording` (10.0 seconds). `piece` is drawn
in its ancestor card behind the frame (§8.8), with the elisions it derives
(§8.9) and whole in `group__group_elided_inside__full`. The frame is that
of `group__group_grandchild` with other names and labels: `excerpt`
carries the faded lines of `first`, nearer, and `piece` below its own,
and both run on to both sides (`first` from −8 to 24 and `piece` from −8
to 56 on `excerpt`'s axis), so `first`'s line ends in the two chevrons on
the right where `movement`'s ended in its diamond; `excerpt`'s `origin`
and `length` are `timestamp_1` and `timestamp_2`, `recording`'s
`timestamp_3` and `timestamp_4`, labelled `0″` and `10″` (3371 advances
as `12″`). The bullets before the ancestor card's give positions in place
coordinates; drawn, each lies 144.5676618303571 further right, and
487.4248046875 in the `__full` case.

- As in `group__group_grandchild`: `xn` = 24, `N` = w(`Recording`, 11) =
  55.70361328125 (`Excerpt` is 42.09326171875 wide), `x0` = the chevron
  term 111.70361328125 → 111.7036, `R` = the outer chevron tip of `piece`
  and of `first`, 535.70361328125, the cards 527.70361328125 → 527.7036
  and, before the rows align and in `__full`, the frame 543.70361328125
  × 171.5625 → 543.7036 × 171.5625, with `excerpt`'s line at 47.207,
  `first`'s faded line at 85.1836, `piece`'s `Δ` = 14 further at 99.1836,
  `recording`'s line at 136.5859, and the cross-section lines of
  `excerpt`'s `origin` and `length` as there. With the rows aligned, as
  there too: `piece`'s ancestor row at 119.1602, `excerpt`'s card
  101.3555 and the frame 191.5391 high, `recording`'s line at 156.5625
  (below).
- The ancestor card of `piece`, aligned to `excerpt`: `s0` =
  103.70361328125, `ts` = −8, `λ` = 8, `λR` = 64, `te` = 56, `us` = −1,
  `ue` = 7, `xs` = −296.29638671875, `xe` = 2903.70361328125, `LA` =
  3200. `first` and `second` touch and share one row of `piece`'s children
  band (§6.3), named `First, Second` and addressed `{"id": "first", "part":
  ["name"]}` (§6.6); `N'` = w(`First, Second`, 11) = 71.4248046875 (13298
  advances), wider than `Excerpt` and `Piece`, so `s0'` = 87.4248046875.
  The seams lie at `piece`'s 8 and 16: `OL` = 103.70361328125 and `OR` =
  40. Vertically the card drawn whole is that of
  `group__group_grandchild__full`: its top at
  36.20703125 → 36.207, 77.37890625 → 77.3789 high, `excerpt`'s row at
  51.207 with its wedges and labels `0 ♩` and `8 ♩` (the baseline 76.061)
  and its `origin` and `length` crossing the card, the row of `first` and
  `second` at 85.1836 and `piece`'s line at 99.1836; the names at 16 with
  the baselines 55.0151, 88.9917 and 102.9917. `first` ends at 32 in its
  diamond, where `second` starts with its circle; `second` ends at 64 in
  its diamond, under `piece`'s arrowhead.
- Whole (`__full`): the card 103.70361328125 + 87.4248046875 + 3200 + 40
  + 9 + 8 = 3448.12841796875 → 3448.1284 wide, `dx` = (−296.29638671875 −
  103.70361328125) − 87.4248046875 = −487.4248046875, so `Xl` =
  −487.4248046875, the origin (487.4248046875, 0), and the card is drawn
  at (8, 36.207): `piece`'s line from 95.4248, whole across both seams, to
  3439.1284, `first`'s from 95.4248 to its diamond at 1839.1284,
  `second`'s from 1839.1284 to its diamond at 3439.1284 and `excerpt`'s
  from 599.1284, where `excerpt`'s own line starts in the frame
  (111.70361328125 + 487.4248046875), to its diamond at 999.1284. `W` = 8
  + 2970.70361328125 + 487.4248046875 = 3466.12841796875, the right edge
  of the card with its shadow, −479.4248046875 + 3448.12841796875 + 2;
  `H` = 8 + (8 + 171.5625) = 187.5625; the page 3498.12841796875 ×
  219.5625 → **3498.1284 × 219.5625**.
- Derived (Shared quantities): `zG` = 1.8833790598156273, `zb`, `B`, `c`
  and `dr` = 279.851806640625 as in `group__group_grandchild` (the same
  frame), `σ` = 87.4248046875 and `dl` = 359.276611328125; `EL` = 8, `ER`
  = 48, `E` = 56, `uL` = 1 and `uR` = 6: `r` = min(1,
  0.14285714285714285, 0.8938084716796874, 0.1820617472330729) =
  0.14285714285714285, set by `λ / E`. Depth 2 holds `first` and
  `second`, in canonical order: `first` gives its 0–8 and 16–32, outside
  `excerpt`, `second` its 0–32 (32 to 64 of `piece`'s axis), and depth 1,
  `piece`, is left nothing. Natural widths 400, 800 and 1600 at `LA` =
  3200 (`k` = 50), `W` = 57.14285714285714, 114.28571428571428 and
  228.57142857142856 (400 together), `h / k` = 0.2514285714285714,
  0.8228571428571427 and 1.9657142857142855 (§8.9): the first two are
  gaps whole, the third leaves out `second` 1–31, 50 of `second` at full
  scale on either side, its gap 128.57142857142856 wide. Shrinks
  342.8571428571429, 685.7142857142858 and 1371.4285714285716, `DL` =
  342.8571428571429 − 103.70361328125 = 239.1535295758929. Own x(0) =
  87.4248046875, x(8) = 144.5676618303571 left of the first seam and
  248.2712751116071 right of it, x(16) = 648.2712751116071 left of the
  second seam and 688.2712751116071 right of it, x(32) =
  802.5569893973213, x(33) = 852.5569893973213, x(63) = 981.12841796875
  and x(64) = 1031.12841796875; the card is (1031.12841796875 + 9) + 8 =
  1048.12841796875 → 1048.1284 wide; `dx` = (−296.29638671875 +
  239.1535295758929) − 87.4248046875 = −144.5676618303571, so `Xl` =
  −144.5676618303571 and the origin (144.5676618303571, 0). The gaps
  `first` 0–8 and `first` 16–32 touch the seams, and each lies wholly
  outside the frame (Shared quantities). Vertically the stacks `First`,
  `First` and `Second` take the markers bands of `first` and `second`,
  26.9765625 below their row, so that row has the inner half 26.9765625:
  it lies 7 + 26.9765625 = 33.9765625 above `piece`'s line and
  `excerpt`'s 33.9765625 above it, `piece`'s line 8 + 7 + 26.9765625 +
  40.9765625 = 82.953125 below the card's top, and the card 82.953125 +
  6.40234375 + 8 = 97.35546875 → 97.3555 high.
- Rows aligned (§8.3): the stacks `First`, `First` and `Second` lie
  between the lines of the row of `first` and `second` and of `piece`, so
  `d` = 33.9765625 (Shared quantities), and in `excerpt`'s card `piece`'s
  ancestor row lies 85.18359375 + 33.9765625 = 119.16015625 → 119.1602,
  the card is 101.35546875 → 101.3555 and the frame 191.5390625 →
  191.5391 high, every ordinate below `first`'s faded row 19.9765625
  lower, as in `group__group_grandchild`; `Fh`, `r` and every abscissa do
  not move.
- Drawn with its derived elisions: the card at (8, 36.20703125 →
  36.207), its top 119.16015625 − 82.953125, its bottom 133.5625 and
  with its shadow 135.5625, inside the frame; `excerpt`'s row at
  51.20703125 → 51.207, the row of `first` and `second` at 85.18359375 →
  85.1836, on `first`'s faded line, and `piece`'s line at 119.1602, the
  names at 16 with the baselines 55.0151, 88.9917 and 122.9683. `piece`'s start circle at
  95.4248 and its line from 152.5677, at the frame's left edge, whole
  across the seam at 8, to 696.2713, at the frame's right edge, from
  810.557 to 860.557 and from 989.1284 to 1039.1284, its arrowhead's tip
  at 1048.1284; `first`'s start circle at 95.4248, its line from 152.5677
  to 696.2713 and its diamond at 810.557, at the right edge of the gap
  over its 16–32, which leaves the line no piece there; `second`'s start
  circle at 810.557 and its line from 810.557 to 860.557 and from
  989.1284 to its diamond at 1039.1284; `excerpt`'s from 256.2713, where
  `excerpt`'s own line starts in the frame (111.70361328125 +
  144.5676618303571), to its diamond at 656.2713, with its wedges and
  labels there (the baseline 76.061) and its `origin` and `length`
  crossing the card from 36.207 to 52.707 and from 78.1836 to 133.5625.
  The gaps `first` 0–8 from 95.4248 to 152.5677, `first` 16–32 from
  696.2713 to 810.557 and `second` 1–31 from 860.557 to 989.1284 draw one
  ellipsis each, centred at 123.9962, 753.4141 and 924.8427 and at `ym` =
  (36.20703125 + 133.5625) / 2 = 84.884765625 → 84.8848, and below it
  their labels `First`, `First` and `Second`, with the baseline
  97.23876953125 → 97.2388. `W` = 8 + 913.5607561383929 +
  144.5676618303571 = 1066.12841796875, the right edge of the card with
  its shadow, −136.5676618303571 + 1048.12841796875 + 2; `H` = 8 + (8 +
  191.5390625) = 207.5390625.
- Page 1098.12841796875 × 239.5390625 → **1098.1284 × 239.5391**.


## `group__group_elided_members`

The group "Theme" in the display order `excerpt`, `voice`, `sketch`: the
child `excerpt` (16 quarters at 16) of the piece `piece` (48 quarters), the
root `voice` (24 quarters) with its child `phrase` (8 at 12), and the root
`sketch` (seconds, of unknown length). Two group elisions (§8.9) lie on
timelines lying in the group: `elision_1` "Development" on the member
`excerpt` from 2 to 8, its `display` `["ellipsis", "name", "coordinate"]`
and no `width`, and `elision_2` on `voice`'s child `phrase` from 2 to 6
with `{"ratio": 0.5}`; each is drawn across the frame, one gap through all
three cards, and carried into the ancestor card of `piece` behind it. The
groupstamps `timestamp_1` "Climax" at 15 and `timestamp_2` "Return" at 21
on `voice` draw their wedge, name and lines. The drawing is the reference
for a frame's elided axis, carried gaps and the proportion with `L'`. The
bullets before the ancestor card's give positions in place coordinates;
drawn, each lies 182.42659505208337 further right.

- `xn` = 24. `N` = w(`Excerpt`, 11) = 42.09326171875, wider than `Voice`,
  `Phrase`, `Sketch` and `Piece` at size 9. `x0` = the chevron term 24 +
  42.09326171875 + 8 + 24 = 98.09326171875 → 98.0933, the ancestor line of
  `piece` running on to the left (`ts` = −16).
- The frame's gaps (§3.2, §8.9): `elision_1`, carried to `excerpt`'s own
  axis, has the stretch `p` = 2 / 16 = 0.125 to `q` = 8 / 16 = 0.5, the
  natural width 400 × 0.5 − 400 × 0.125 = 150 and the standard gap 32;
  `elision_2` lies at 14 to 18 on `voice`'s axis, `p` = 0.5833333333333334
  and `q` = 0.75, the natural width 300 − 233.33333333333334 =
  66.66666666666666 and the gap 0.5 × that = 33.33333333333333. The
  shrinks 118 and 33.33333333333333 give `DG` = 151.33333333333331 and
  `L'` = 248.66666666666669. On the frame's axis `x(u) = x0 + (400 × u −
  D)`: the gaps run from 148.09326171875 to 180.09326171875 and from
  213.42659505208334 to 246.75992838541669, and the members' shared end
  lies at 98.09326171875 + 248.66666666666669 = 346.7599283854167 →
  346.7599.
- `R` = the outer chevron tip of `sketch`, whose end is open: `Xr =
  346.7599283854167 + 12` and the tip `Xr + 16.5` = 375.2599283854167,
  beyond the outer chevron tip of `piece`'s ancestor line, `x0 + L' + 8w`
  = 370.7599283854167, which runs on to the right (`te` = 32 > 16), and
  the arrowhead tip of `voice` at 355.7599283854167; `Mr` = 28.5. Each
  card is 375.2599283854167 − 8 = 367.2599283854167 → 367.2599 wide and
  the frame 383.2599283854167 → 383.2599, `DG` narrower than at full
  scale (§8.2).
- `excerpt`'s markers band holds the wedges and labels `0 ♩` and `16 ♩` of
  its `origin` and `length` and the stack of `elision_1`, `Development`
  over `2–8 ♩`, centred at full scale on `L × um` = 400 × 0.3125 = 125, in
  one tier two lines high (§6.4, Markers): it is 1.5 + 13 + 2 + 2 ×
  10.4765625 = 37.453125 wide. The ancestor band below starts at max(7,
  37.453125 + 4) = 41.453125, its row `piece` at 41.453125 + 7 =
  48.453125 below `excerpt`'s line, `Eb` = 55.453125 and `Hm` =
  14.40234375 + 55.453125 + 8 = 77.85546875 → 77.8555. `phrase` draws no
  wedge, but `elision_2`, which states no `display`, draws its name label
  `Phrase` (§2), whose stack, centred at full scale on 400 × (0.5833333333333334
  + 0.75) / 2, takes `phrase`'s markers band, 26.9765625 below its line:
  `voice`'s children band holds `phrase` 7 + 26.9765625 = 33.9765625
  above `voice`'s line, so `Ea` = 40.9765625, `y_root` = 48.9765625 and
  `Hm` = 48.9765625 + 26.9765625 + 8 = 83.953125 → 83.9531, `Climax`
  keeping its room in the band although it is not drawn (§3.2). `sketch`:
  `Hm` = 49.37890625. The frame is 8 + 12.8046875 + 4 + 77.85546875 + 8 +
  83.953125 + 8 + 49.37890625 + 8 = 259.9921875 → 259.9922 high, the cards
  at 32.8046875, 118.66015625 and 210.61328125.
- Drawn lines: `excerpt` at 47.207, the faded `piece` at 95.66015625 →
  95.6602, `phrase` at 133.66015625 → 133.6602, `voice` at 167.63671875 →
  167.6367, `sketch` at 225.015625 → 225.0156. Every row whose span holds
  a gap, `phrase` only the second (it starts at `voice`'s 12, the
  proportion 0.5, the first gap's right edge), stops at its left edge and
  resumes at its right edge, written in pieces from the left: drawn the
  gaps run from 330.5199 to 362.5199 and from 395.8532 to 429.1865, and
  the lines end at 529.1865, `sketch`'s three chevrons beyond 541.1865.
- The frame's gaps are written after `sketch`'s card (§8.5), from the
  left, each drawing one ellipsis at its middle `xm` and at `ym` = (32.8046875
  + 259.9921875) / 2 = 146.3984375 → 146.3984, the middle of the member
  cards together (§6.6), and below it its labels: `elision_1`'s ellipsis
  at 346.5199, then its labels `Development` and `2–8 ♩`, centred at
  346.5199, with the baselines 146.3984375 + 4 + 8.35400390625 =
  158.75244140625 → 158.7524 and 158.75244140625 + 10.4765625 =
  169.22900390625 → 169.229, filled `#6B7280`; `elision_2`'s ellipsis at
  412.5199 and its label `Phrase` with the baseline 158.7524. Then the
  groupstamps' lines across the frame (§6.6), each less its member's card
  and with the part over the card of `sketch`, of unknown length, cut out
  and drawn at opacity 0.35: `timestamp_3` and `timestamp_4` (`excerpt`'s
  `origin` and `length`) at 280.5199 and 529.1865 from 110.6602 to
  210.6133 and, faded, to 259.9922; `timestamp_2` "Return" at 21 of 24, the
  proportion 0.875, at 479.1865, from 32.8047 to 118.6602, from 202.6133 to
  210.6133 and, faded, to 259.9922. `timestamp_1` "Climax" at 15, the
  proportion 0.625, lies in the second gap and draws nothing.
- The ancestor card of `piece`, aligned to `excerpt`: `s0` =
  90.09326171875, `ts` = −16, `λ` = 16, `λR` = 48, `te` = 32, `us` = −1,
  `ue` = 2, `xs` = −309.90673828125, `LA` = 1200 (25 canvas units per
  quarter); `N'` = w(`Excerpt`, 11), `s0'` = `σ` = 58.09326171875; its
  `excerpt` row draws no label of `elision_1`, so it lies 7 + 26.9765625
  above `piece`'s line, at 15 below the card's top; the stacks `Piece` of
  its two derived gaps take `piece`'s markers band, 26.9765625 below its
  line, so the card is 48.9765625 + 26.9765625 + 8 = 83.953125 → 83.9531
  high, its top 95.66015625 − 48.9765625 = 46.68359375 → 46.6836 and its
  bottom 130.63671875. Its seams lie at `piece`'s 16 and 32: `OL` =
  90.09326171875 and `OR` = 383.2599283854167 − (90.09326171875 +
  248.66666666666669) = 44.5. It carries the frame's gaps over `piece` 18 to 24 and 76/3
  to 28 (`−ts + p × λ`, `−ts + q × λ` with the exact proportions 1/8, 1/2,
  7/12 and 3/4, so exact on `piece`'s fraction axis; its x, shifted
  by `dx`, is 205.42659505208337 in the frame's item coordinates, where
  the frame's own gap starts at 205.42659505208334), 32 and
  33.33333333333333 wide of 150 and 66.66666666666666. Its proportion
  (§8.9): `Fw` = 383.2599283854167, `Fh` = 259.9921875, `zG` =
  2.2154511854322547, `zb` = `Z`, `B` = 716.8, `c` = 191.62996419270834,
  `dl` = 249.72322591145834, `dr` = 199.62996419270834, `EL` = `ER` = 16:
  `r` = min(1, 0.5 × (248.66666666666669 / 400), 1.167691935221354,
  1.292925089518229) = 0.31083333333333335. Depth 1 gives `piece` 0–16 and
  32–48, natural width 400 each, `W` = 124.33333333333334, `k` = 25 and
  `h / k` = 1.846666666666667: their gaps leave out `piece` 1–15 and 33–47,
  25 at full scale on either side, each 74.33333333333334 wide of 350,
  shrink 275.66666666666663. `DL` = 275.66666666666663 − 90.09326171875 =
  185.57340494791663, `dx` = (−309.90673828125 + 185.57340494791663) −
  58.09326171875 = −182.42659505208337, so the origin is
  (182.42659505208337, 0) and the card, 707.0198567708335 → 707.0199 wide
  (`piece`'s arrowhead tip at x(48) + 9 plus `K`, `OL` and `OR`
  included), is drawn at (8, 46.6836). In it: `piece`'s line at 95.6602,
  its start circle at 66.0933 and its pieces 66.0933–91.0933,
  165.4266–330.5199 and 429.1865–598.6865, each whole across a seam (at
  280.5199 and 529.1865 on the left and the right of the span),
  362.5199–395.8532 and 673.0199–698.0199, its arrowhead's tip at
  707.0199; `excerpt`'s row at 61.6836 from 280.5199, where `excerpt`'s
  own line starts, to its diamond at 529.1865, in three pieces about the
  carried gaps, with its `origin` and `length` crossing the card from
  46.6836 to 63.1836 and from 88.6602 to 130.6367; the carried gaps lie
  over the frame's (the second's x, shifted by `dx`, is
  205.42659505208337 in the frame's item coordinates, where the frame's
  own gap starts at 205.42659505208334); the gaps from the left, `piece`
  1–15 (ellipsis at 128.2599, its label `Piece` below it), `elision_1` and
  `elision_2` (ellipses at 346.5199 and 412.5199, no label) and `piece`
  33–47 (ellipsis at 635.8532, label `Piece`), every ellipsis at `ym` =
  (46.68359375 + 130.63671875) / 2 = 88.66015625 → 88.6602 and each label
  with the baseline 101.01416015625 → 101.0142.
- `W` = 8 + 534.5932617187501 + 182.42659505208337 = 725.0198567708335,
  the right edge of the ancestor card with its shadow, −174.42659505208337
  + 707.0198567708335 + 2, beyond the frame's 391.2599283854167; `H` = 8 +
  (8 + 259.9921875) = 275.9921875.
- Page 757.0198567708335 × 307.9921875 → **757.0199 × 307.9922**.

## `bundle__bundle_arranged_roots__horizontal`

The bundle "Arranged" side by side (§8.6, §8.8 Drawn once), its worked
example in §8.8. The stored order `page`, `group_3`, `group_1`,
`group_2` becomes the row `page`, `group_1`, `group_2`, `group_3`: on
`score` Exposition (0–16) comes before Development (16–32) before
Recapitulation (32–48), touching, on `session` Exposition (0.0–30.0)
before Recapitulation (100.0–130.0), and `page`, hanging on nothing,
keeps its first place. The roots are `score` above `session` (Exposition
and Recapitulation hold them in that order). Each frame and card is laid
out by §8.2 and §8.4 as in the drawing of the manifest with the default
placement: `x0` = 127.39013671875 (the chevron term of the ancestor
lines that run on to the left), `R` = 551.39013671875 (the right
chevrons, 24 past the shared end 527.39013671875), every item
567.39013671875 wide; a child member's card 67.37890625 high, its
ancestor line 52.37890625 below its top, a root member's card
49.37890625; the frames' titles put the first card 24.8046875 below
their tops. The once cards are the ancestor cards behind Exposition laid
out alone (§8.8, step 1):

- `score`'s at `LA` = 1200. Its children band places three children of
  one band order, so it is aligned and places them by their line extents
  (§6.4, Children), 0–400, 400–800 and 800–1200, touching: one row of one
  band order. Its markers bands place the six stacks of the movements'
  `origin` and `length` by one first fit, line after line (§6.4, Rows of
  one band order): the `0 ♩` of `development` at 400 meets the `16 ♩` of
  `exposition` there and goes to tier 2, as the `0 ♩` of
  `recapitulation` at 800 does, so every movement's markers band is `w /
  2 + 13 + 2 + 2 × h(9)` = 37.453125 wide. The row's inner half is
  37.453125 and its outer half 7, and the children band starts at `p0 /
  2` = 7, so the movements' line lies 7 + 37.453125 = 44.453125 above
  `score`'s, `Ea` = 7 + (37.453125 + 7) = 51.453125, and `score`'s line
  lies at `yR` = 8 + 51.453125 = 59.453125 of `Hm` = 59.453125 +
  6.40234375 + 8 = 73.85546875 (no band below it). The row's name
  `Exposition, Development, Recapitulation` (224.4580078125 wide) is cut
  to `Exposition, Development, …` (156.06787109375, §6.6, Names), so `N'`
  = 156.06787109375 and `s0'` = 8 + 156.06787109375 + 8 =
  172.06787109375; `Ri' + K − xe'` = 17.279052734375 (the label `16 ♩` of
  `recapitulation`'s `length` past its end).
- `session`'s at `LA` = 1733.3333333333333, `s0'` = 98.2529296875, its
  line at 48.9765625 of 83.953125 (below its line the markers band of
  26.9765625 that the label stack of its one gap takes, §6.4), `Ri' + K −
  xe'` = 17, its arrowhead.

Each root starts where its first stretch starts and ends where its last
one ends, so the seams `s1 × OL` and `sN × OR` (§8.8, Drawn once) lie at
its own start and end, which lie on their stretches' sides: nothing of
either line lies left of the first stretch or right of the last. The
names, as in an ancestor card behind one frame, lie left of Exposition's
frame: they keep their distance `s0'` from `X(start) − s1 × OL`, `OL` =
`x0` = 127.39013671875 and `s1` = 1 (§8.8, Drawn once).

- Row: `x` 8, 623.39013671875, 1238.7802734375 and 1854.17041015625
  (row gap 48).
- Lines: `score` at 0; `session` at max(0 + 14.40234375 + 8 + 48.9765625,
  0 + (152.5625 − 77.18359375), 0 + (209.94140625 − 77.18359375)) =
  max(71.37890625, 75.37890625, 132.7578125) = 132.7578125, `bR` =
  73.85546875 − 59.453125 = 14.40234375. Padding in Exposition above
  `take_a`: 132.7578125 − 75.37890625 = 57.37890625, so `take_a`'s card
  lies at 157.5625 in the frame and Exposition is 232.94140625 high, as
  Recapitulation is; Development is 157.5625 high.
- Tops: −77.18359375 (each frame), −59.453125 (`score`'s card), 83.78125
  (`session`'s); `T0` = −77.18359375, `Y` = 28.8046875, everything moves
  by 105.98828125: frames and `page` at 28.8046875, `score`'s line at
  105.98828125 → 105.9883, `session`'s at 238.74609375 → 238.7461, the
  once cards' tops at 46.53515625 → 46.5352 and 189.76953125 → 189.7695.
  No once card lies left of `P`.
- `score`'s runs, `XM(t)` = `xG` + (127.39013671875 + 400 × ((t − a) /
  16)): seams at 16 (`c` = 1214.7802734375; `s` = 17, `XA(18)` =
  1200.7802734375 > 1198.7802734375; `e` = 11, `XB(10)` =
  1216.17041015625 < 1230.7802734375), from 1150.7802734375 → 1150.7803
  to 1366.17041015625 → 1366.1704, and at 32 (`c` = 1830.17041015625),
  from 1766.17041015625 → 1766.1704 to 1981.560546875 → 1981.5605; a seam
  draws nothing (§3.2), and the line of `score`, the one row crossing
  them, is one `<line>` from 750.7802734375 → 750.7803 to 2381.560546875
  → 2381.5605, its circle and arrowhead at its ends. The movements' line
  lies at 46.53515625 + (8 + 7) = 61.53515625 → 61.5352, each movement
  from its start to its end diamond; the wedges, coordinate labels and
  cross-section lines of `timestamp_6` (the end of `exposition`) and
  `timestamp_4` lie on the left runs, at 1150.7803 and 1766.1704; those of
  `timestamp_3` and `timestamp_11` (the starts of `development` and
  `recapitulation`) and the lines' starts on the right ones, at 1366.1704
  and 1981.5605. Every wedge runs from 63.03515625 → 63.0352 to
  76.03515625 → 76.0352; the labels in tier 1 have their baselines at
  61.53515625 + 16.5 + 8.35400390625 = 86.38916015625 → 86.3892, those of
  `timestamp_3` and `timestamp_11` in tier 2 at 96.86572265625 →
  96.8657. Each cross-section line runs from the card's top 46.5352 to
  its wedge's tip 63.0352 and from the end of its label's line, 88.51171875
  → 88.5117 (tier 1) or 98.98828125 → 98.9883 (tier 2), to the card's
  bottom 46.53515625 + 73.85546875 = 120.390625 → 120.3906. The names'
  baselines lie at 61.53515625 + 3.80810546875 = 65.34326171875 →
  65.3433 (`Exposition, Development, …`, addressed by `exposition`) and
  105.98828125 + 3.80810546875 = 109.79638671875 → 109.7964 (`Score`).
- `session`'s runs, `XM(t)` = `xG` + (127.39013671875 + 400 × ((t − a) /
  30.0)): the gap over 33.0–44.0 from 1190.7802734375 → 1190.7803 to
  1234.8938802083335 → 1234.8939 (`XA(34.0)` = 1204.1136067708333 >
  1198.7802734375, `XB(43.0)` = 1221.560546875 < 1230.7802734375), its
  one ellipsis at `xm` = 1212.8370768229167 and the middle of the once
  card, `ym` = (189.76953125 + 273.72265625) / 2 = 231.74609375: the
  circles at 1206.8371, 1212.8371 and 1218.8371 on 231.7461, and below
  them its label `Session` (the card's `elision-display` `ellipsis
  name`), centred at 1212.8371 with the baseline 231.74609375 + 4 +
  8.35400390625 = 244.10009765625 → 244.1001; the line of `session` in
  two pieces, from 750.7802734375 → 750.7803 to the gap and from the gap
  to 2381.560546875.
- The once cards: `score` from 750.7802734375 − 127.39013671875 −
  172.06787109375 = 451.322265625 → 451.3223, 2398.839599609375 −
  451.322265625 = 1947.517333984375 → 1947.5173 wide and 73.85546875 →
  73.8555 high, its names at 451.322265625 + 8 → 459.3223; `session`
  from 750.7802734375 − 127.39013671875 − 98.2529296875 =
  525.13720703125 → 525.1372, 2398.560546875 − 525.13720703125 =
  1873.42333984375 → 1873.4233 wide and 83.953125 → 83.9531 high, from
  189.76953125 to 273.72265625, its names at 533.1372, the cross-section
  lines of `take_a`'s and `take_b`'s `origin` and `length` in it running
  down to 273.7227; the start circles of both lines stay at 750.7803,
  under Exposition's frame; both cards written before the items,
  `score`'s first.
- `W` = 8 + 2421.560546875 = 2429.560546875, the right edge of
  Recapitulation's frame plus `P`; `H` = 8 + 275.72265625 = 283.72265625,
  the bottom of `session`'s once card with its shadow plus `P`; the page
  2461.560546875 × 315.72265625 → **2461.5605 × 315.7227**.
