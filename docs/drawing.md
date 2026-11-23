# Drawing a TimeToShare manifest

This specification states how one TimeToShare manifest is drawn: the
`graphical` object of style rules (section 2), the arithmetic of
positions (section 3), the default style (section 4), the fonts that
measure every text (section 5), the layout that turns a manifest into a
**drawing** (section 6), and the writers that serialize a drawing as SVG and
TikZ text (section 7). Two implementations that follow it draw the same
manifest, with the same inputs, as the same SVG and TikZ text, byte for
byte.

A drawing is derived and never stored: there is no drawing schema, and no
JSON form of a drawing is exchanged. This specification pins the drawing.

Sections 1 to 7 specify the drawing of one timeline, called **the root**,
with all its descendants: a **member drawing**. Section 8 specifies the
block that holds member drawings. Every manifest is drawn as one block,
whether it holds one timeline or many, groups or none: its groups as
frames and its ungrouped roots as cards. Terms in `code` are JSON members.

The block draws the bundle, a frame a group, a card a timeline drawn as a
root, and a band a facet of a timeline (README, "Containers"); these four
containers are the **boxes** of a drawing.

## 1. Inputs and output

`draw(manifest, placement, layers, metrics)` returns the manifest's drawing.

- `manifest`: a TimeToShare manifest, read in its complete form, every
  key the manifest leaves out taking its default (README, "Defaults"), and
  in canonical order (README, "Canonical order"), whatever form and order it
  was written in. Its `graphical` object holds the manifest's own style
  rules and its `order` (section 2). The drawing reads the manifest
  alone, never a table that its `resources` name.
- `placement`: chosen by whoever places the drawing, such as an editor's
  canvas or a script:
  - `length`, the **graphical length** `L` of every item of the block
    without a length of its own (section 8.6), in canvas units (default
    400): the distance from a root's start to its end;
  - `spacing`, the block's **spacing**, the gap in canvas units between its
    items that lie at their default `y` (section 8.6), a finite number ≥ 0
    (default 8);
  - `margin`, the block's **margin**, empty space in canvas units drawn
    above its first item and below its last (section 8.4), a finite
    number ≥ 0 (default 0). A frame's and a card's spacing and margin are
    entries of `places` (section 8.6); none multiplies another;
  - `width` and `height`, the requested **block size** in canvas units, or
    `null` (the default) for the content's own size;
  - `places`, the **places** of the block's items and the sizes of its
    members' cards (section 8.6): an object keyed by the ID of a group
    (its frame) and by the ID of an ungrouped root (its card), each value
    an object with any of the members `x`, `y`, `length`, `scale`,
    `spacing`, `margin`, `width` and `height`; a group's value may also hold
    `cards`, an object keyed by the ID of a member `T`, whose value states
    the `width`, `height`, `spacing` and `margin` of `T`'s card in that group's
    frame, so that `places[G].cards[T]` is the card of member `T` in the
    frame of group `G` (default `{}`);
  - `arrangement`, the block's **arrangement** (section 8.6): `null` (the
    default), each item lying at its place, or an object `{direction,
    order}` that places the items in an order instead: `direction` is
    `"vertical"`, the items one under another, or `"horizontal"`, the
    items side by side in one row, every root that groups hang on drawn
    once behind the row (section 8.8, Drawn once); `order` is a list of
    the IDs of groups and ungrouped roots, the order to take the items in.
    Like every input here, an arrangement says where the drawing places
    things and is never part of the manifest;
  - `view`, the **view** `{width, height}`, the screen area the drawing
    is meant for, in canvas units at the scale 1 (CSS pixels), each a
    finite number > 0 (default `{width: 1280, height: 720}`). It sets the
    proportion of the elisions a card derives where its `elision-proportion`
    is `auto` (section 8.9) and nothing else: an editor passes the area of
    its canvas, a script its own or the default, and the manifest stores
    nothing of it, so one manifest drawn for two views may differ in the
    widths of its derived elisions.
- `layers`: the rule lists that style the drawing, from the lowest to
  the highest precedence: the defaults of section 4, then any lists an
  application supplies below the manifest (such as an editor's settings),
  then the manifest's own `graphical` object. No layer lies above the
  manifest: a drawing's own styling is its manifest's. Section 2 defines
  them.
- `metrics`: the advance widths of the fonts of section 5.1.

The drawing is a **block** of width `W` and height `H` and a list of drawn
**elements** in block-local canvas units, origin at the block's top-left corner,
y downwards, and the block-local position `(Ox, Oy)` of the **place origin**,
from which places are measured (section 8.6). Every element carries its
**address** (section 2.2) and, where it shows a coordinate, the exact
coordinate it shows, whatever its label's text (section 5.2). A drawing
of an arranged block also states its **arrangement**: its direction, the
order of its items (for `horizontal`, the row) and the roots drawn once,
top to bottom, or, where `horizontal` is refused, the conflict, its
groups, its roots and its reason (section 8.8, Drawn once). Canvas units become
CSS pixels in SVG and points in TikZ (section 7).

A drawing does not depend on its position on a canvas, nor on its scale: a
canvas or a writer places the block at a position and scales it uniformly by
a **scale** factor `z` (section 7.1). The three ways of resizing a drawing
change one input each:

| Resize | Input changed | Effect |
|---|---|---|
| Scale | scale `z` | everything scales, proportions kept, text included |
| Box | `width`, `height` | only the block changes; the content keeps its place at the top left; the block never becomes smaller than the content (section 8.4) |
| Stretch | `length` (horizontal), `spacing`, or `margin` for a container with exactly one content (vertical), both (a corner); `width`, `height` where a block size is requested | horizontally, distances along time stretch; vertically, the gaps between the container's contents grow or shrink, or, in a container with exactly one content, the equal margins above and below it; markers, line widths and text keep their size; the block follows the content (below) |

On a stretch, a requested block size larger than the content keeps its
proportion to the content, so the block follows the stretched content and
the room the request adds stretches with it: `width` (or `height`) becomes the
request times the stretched content's size divided by the content's size
before the stretch, multiplied first, in binary64 (an editor may round the
result to the grid it stores numbers on). A request no larger than the
content before the stretch becomes `null`, and `null` stays `null`. A
horizontal Stretch of the block scales every `x`, `length` and `width` that
`places` states by the ratio of the lengths, and keeps every `scale`.

A container's **contents** are a block's items, a frame's cards, a card's
root row, the root's present bands (section 6.4) and its ancestor bands
(section 8.3), none, one or two. A vertical Stretch of a container with two
or more contents changes its `spacing`; with exactly one it changes its
`margin` instead, the gaps being none, so that the container grows or
shrinks by equal margins above and below its contents (sections 6.5 and
8.4), and its `spacing` is unchanged; with none it changes its
`spacing`. Scale, Box and the horizontal Stretch keep every `margin`. A
vertical Stretch of the block so changes its `spacing` or its `margin`
alone: it moves the items at their default `y` and keeps every stated `y`
and `height`.

Every frame and card of the block is resized in the same three ways,
changing entries of `places` only (section 8.6). An item, a group's frame
or an ungrouped root's card: Scale changes its `scale`, Box its `width`
and `height`, Stretch its `length` (horizontal), its `spacing` or `margin`
(vertical, as above) or both (a corner), its `width` and `height` following the stretched
content as the block's do. The card of a member `T` in the frame of a group
`G`: Scale and the horizontal Stretch change `G`'s `scale` and `length`, since
the members of a group share them; the vertical Stretch changes the card's
own `spacing`, or its own `margin` when the card has exactly one content, and Box its own `width` and `height`, the entry
`places[G].cards[T]`, so the cards of the same member in other groups' frames keep
theirs. An item's or card's content,
for this rule, is its frame or card without its own request (for a
member's card, without its frame's request too, since the frame's width
widens its cards), in item coordinates: for `width` its right edge less its left (section 8.2), for
`height` its height of section 8.4. Every requested `width` or `height`
of a frame or card whose content a Stretch of an item or a member's card
changes keeps its proportion to
that content by the rule above: a horizontal Stretch of a group, from its
frame or a member's card, rescales every requested width of the frame and
of its members' cards, so the members' lines keep one length and the room
every request adds stretches with them; a vertical Stretch of a frame,
which changes only the gaps between its cards or the margins around its
one card, rescales its own requested height, and of a card, which changes
its gaps or its margins, its own and its frame's.

## 2. The `graphical` object

```json
"graphical": {
  "styles": {
    "highlight": {"stroke": "#7F00FF", "fill": "#7F00FF"}
  },
  "rules": [
    {"select": {"element": "label"}, "set": {"fill": "#404040"}},
    {"select": {"element": "wedge", "within": "#performance"}, "set": "highlight"},
    {"select": {"addresses": [{"id": "#region_1"}]}, "set": {"display": "none"}}
  ]
}
```

The object is optional; an absent `graphical` draws with the other layers alone.
`styles` maps a style name to a **declaration**, an object of properties
(section 2.4) and their values. `rules` is a list of **rules**,
each a selector (`select`, section 2.3) and either a declaration or the name
of a style in the same layer's `styles` (`set`). The order of the
rules matters, so writers never reorder them. Every layer of section 1
has this shape. The manifest's own `graphical` also holds `order`,
`timestamps`, `matchstamps` and `elisions`, which no other layer holds. `order` maps a group's ID to the
display order of the group's members (section 8.1) and a timeline's ID to
the timeline's band order (section 6.4).

`timestamps` is a list of **named timestamps** (default `[]`), each an
object `{id, timeline, coordinate, name, display?, matchstamp?, groupstamp?}` naming one position of
one timeline: `id` is its ID (README, "Identity"), `timeline` the ID of a
timeline of the manifest at any depth, a segment included, `coordinate` the
position on that timeline's own axis, a number as the timeline's number
type selects (README, "Values on a timeline's own axis"), at least the zero
of that number type and at most the timeline's `length` when the length is
a value, and `name` its name. A **match timestamp**, one with
`matchstamp: true` (default `false`), may leave out its `name`. A
**groupstamp**, one with `groupstamp: true` (default `false`), lies on a
timeline that **lies in a group**: the timeline or one of its ancestors
is listed in the group's `members`, so that it is drawn in the group's
frame, as a member or inside a member's card. An ancestor of a member
lies in no group through it. The groupstamp's line extends across the
frame of each group its timeline lies in, from the upper border of the
topmost member card drawn there to the lower border of the bottommost
(section 6.6, Cross-section lines); the members' coordinates at that line
are derived from the group and never stored. A match timestamp may be a
groupstamp too. Their canonical order is by `timeline`,
compared by Unicode code point, then by `coordinate`, compared by exact
value, then by `id`, compared by code point.

A named timestamp's **coordinates** in a card are what its cross-section
lines cross there (section 6.6): a coordinate on every timeline drawn in
the card whose line, as a root, a child or an ancestor line (section
8.3), spans the line's `x`, its ends included, and on every map drawn
there that spans it, each read on that timeline's or map's own axis; a
segment without a line of its own (section 6.4) is crossed where its
segment line is crossed within the segment's span. Its **primary
coordinate** is its `coordinate` on its `timeline`, the one its wedge and
its labels mark; every other is a **secondary coordinate**, a groupstamp's
coordinates on the other members of its groups among them. The primary
coordinates of a named MatchStamp are those of the match timestamps its
alignment anchors name, the two of a MatchClaim to each anchor, and its
secondary coordinates are theirs. An application that lists a
timestamp's coordinates, in a flag or a table, lists all of them, from
the top of the card down, and highlights the primary one.

Timestamps, groupstamps and match timestamps are drawn by one rule,
whether a timestamp is named on a root, on a child or on an ancestor of
a member: each draws what its `display` lists (below; a match
timestamp by default its cross-section line alone), its cross-section
line across the whole of every card that draws its timeline, as a line or
as an ancestor line, and its timeline decides only where its primary
coordinate's wedge and labels stand: in that timeline's markers band
(section 6.4, Markers), or beside its ancestor line (section 8.3). A
secondary coordinate on a timeline is drawn as the primary one is, by a wedge and the labels the timestamp's
`display` lists, in that timeline's markers band or beside its ancestor
line, its `coordinate` label read on that timeline's axis and written in
that timeline's number type: on an `int` axis the integer nearest the
exact value, ties to even, on a `float` axis the double nearest it, and on
a `fraction` axis the exact value (section 5.2); a map has no
markers band, and a coordinate on a map is listed but draws no wedge.
The words of `display` govern the elements of the secondary coordinates
as they govern the primary one's. The defaults hide every element of a
secondary coordinate and turn its wedge −45 (section 4); a rule selecting
them by the selector member `coordinates` (section 2.3) shows them.

A groupstamp's coordinates on the other members of its groups are read
at one proportion of each member's drawn length (section 6.6), and only a
known length gives a value there: one member's length is never carried
to another. So where the line crosses the card of a member whose length
is unknown, it gives that member, and every timeline its card draws, a
coordinate **without a value**; and where the member holding the
timestamp's own timeline has an unknown length, the proportion is one of
its reach, and the line gives every other member, and every timeline
their cards draw, a coordinate without a value. A coordinate without a
value is drawn faded and without its `coordinate` label (section 6.6),
and an application listing the coordinates lists it, in its place, with
no value.

A named timestamp draws up to five kinds of element, each named by one word of its
`display`: `wedge`, its coordinate marker, at its primary coordinate and
at each secondary one (above); `name`, `id` and `coordinate`, its three
labels, stacked at the thick end of each wedge (section 6.4, Markers):
its `name`, its ID, and the coordinate the wedge marks in that
timeline's unit (section 5.2); and `cross_section`, its **cross-section
line**, a vertical line across each card its timeline is drawn in, from
the card's upper border to its lower border, with a gap where the wedge
and the labels of its primary coordinate stand (section 6.6). `display` is an array of distinct words from these five,
listing what the timestamp draws; when it is absent the timestamp draws
`["wedge", "name", "cross_section"]`, a match timestamp
`["cross_section"]`, and an empty array draws nothing. A timestamp
without a `name` draws no name label.
Its order means nothing: writers write it in the canonical order `wedge`,
`name`, `id`, `coordinate`, `cross_section`. An element whose word
`display` does not list is not displayed, whatever the cascade sets
(section 2.4).

`matchstamps` is a list of **named MatchStamps** (default `[]`), each an
object `{id, name, alignment_anchors, match_claims}` (README, "Named
MatchStamps"). Each **alignment anchor** of `alignment_anchors` is an
object `{id, timestamps, display?}`: `timestamps` names two match
timestamps, and `display` lists what the anchor draws, distinct words
from `line`, its `alignment_anchor` element, and `name`, the MatchStamp's
name as a label at the middle of that line (section 8.7); when it is
absent the anchor draws `["line"]`. Writers write it in the canonical
order `line`, `name`. `match_claims` is never drawn. A match timestamp's
cross-section line is an ordinary cross-section line (section 6.6).

The drawing draws the named MatchStamps as the manifest stores them, and
the SVG and TikZ writers write them so. What an editor derives from a
MatchClaim table, such as the potential MatchStamps it shows in grey or
the anchors of a named MatchStamp that the current table no longer gives,
which it marks in red, is the editor's own and never part of a drawing.

`elisions` is a list of **elisions** (default `[]`), each an object `{id,
timeline, start, end, name?, width?, display?}` that leaves a stretch of
one timeline out of the drawing: every row drawn across the stretch stops
where the stretch starts and resumes where it ends, at full scale on
either side,
and a narrow **gap** lies between, holding one **ellipsis**, centred in
it, with the elision's labels below it (sections 6.6 and 8.9). `id` is its ID (README,
"Identity"); `timeline` names the timeline the elision **lies on**, at
any depth, a segment included, with the meaning and the validation of a
named timestamp's `timeline`; `start` and `end`, `start < end`, are its
**elided coordinates**, positions on that timeline's own axis, from its
zero to its `length` (and only from its zero when the length is `null`),
each a number as the timeline's number type selects (README, "Values on a
timeline's own axis"). An elision moves with its timeline when that
timeline's offset changes. Nothing refers to an elision but an address in
a rule (section 2.2), and no timeline lists its elisions. An elision is a
container: it leaves out what lies on its stretch by position (section
2.4), so a child added inside the stretch later is elided without any
edit. `name` is its name, a string its `name` label shows; an elision
without one is labelled with the name of the timeline it lies on (section
5.3). Its **natural width** is the width its stretch has at full scale
(section 3.2), and `width` sets the gap's drawn width in exactly one of
four forms:

| `width` | The gap's drawn width |
|---|---|
| absent | the **standard gap** of 32 canvas units |
| `{"ratio": q}`, `0 < q ≤ 1` | `q` times its natural width |
| `{"span": v}`, `v > 0` | the width of `v` units of its timeline at full scale |
| `{"canvas": c}`, `c > 0` | `c` canvas units |

A width larger than the natural width is drawn at the natural width: an
elision never widens its stretch. `display` lists what the elision draws
besides its gap, distinct words from `ellipsis`, its ellipsis, `name`,
`id` and `coordinate`, its three labels, stacked as a named timestamp's
are, and `continuation`, grey continuations of the rows across the gap;
when it is absent the elision draws `["ellipsis", "name"]`, an empty
array draws a bare gap, and writers write it in the canonical order `ellipsis`, `name`,
`id`, `coordinate`, `continuation`. Its order means nothing. Whatever
`display` lists, the gap leaves the stretch out. Elisions may overlap
each other and the span of a group member; neither is refused, and
section 8.9 states what is drawn. Their canonical order is by `timeline`,
compared by Unicode code point, then by `start`, compared by exact value,
then by `id`, compared by code point.

An elision on a timeline that **lies in a group**, as a groupstamp's
timeline does (above), is a **group elision** of that group: it is drawn
across the group's frame, at one place in every member card, and carried
into the ancestor cards behind the frame (section 8.9). Every other
elision is a **card elision**, drawn in the cards of its timeline's root
that draw that root whole: an ungrouped root's card and the ancestor
cards behind frames (section 8.8). Which card elisions a root's cards
draw, and whether they derive elisions of their own, the four elision
properties of section 2.4 decide, in a rule addressed to the root's cards
(section 8.9). Whether an elision is a group elision is read from its
timeline, never stored.

A reader that meets rules naming styles its `styles` does not hold
issues one warning naming every missing style, and adds each to `styles` as
an empty declaration; such a rule then sets nothing, and the
`graphical` object is valid.

### 2.1 Elements

Every drawn thing is an **element** of one **type**, and so is every band
of a timeline, which draws nothing of its own:

| Type | What it is |
|---|---|
| `block` | the block: the background of the drawing, holding everything drawn (section 8) |
| `frame` | a group's frame (section 8) |
| `card` | the raised container of a member drawing: one in the frame of each group that has the timeline as a member, or one for an ungrouped root (section 8) |
| `ancestor_card` | the card of a root that contains a member, behind the frame of that member's group, at the proportions of the root's axis; shown by default, hidden by a rule (section 8.8) |
| `timeline` | the line of a timeline drawn in a card (section 8) |
| `child` | a child timeline's line, at any depth |
| `band` | one of the five bands of a timeline, each drawing one of its facets: its markers, conversion maps, children, regions or flow control (below; section 6.4) |
| `boundary` | the start of a segment on its segment line, drawn as a thin vertical rule (section 6.4) |
| `ancestor` | the faded line of an ancestor of a member that is a child timeline, clipped to the member (section 8.3) |
| `map` | a conversion map, drawn as a closed double line |
| `region` | a region, drawn as a brace |
| `flow_marker` | a flow marker, a `flow_marker` element of `flow_control`, drawn as a vertical line |
| `jump_from` | a jump origin, a `jump_from` element of `flow_control`, drawn as an arc with an arrowhead to where it jumps; a jump target, a `jump_to` element, draws nothing of its own |
| `wedge` | a coordinate marker: of a named timestamp of any timeline, at its primary coordinate or at a secondary one (section 2) |
| `cross_section` | the cross-section line of a named timestamp, a vertical line across each card its timeline is drawn in, as a line or as an ancestor line, from border to border, with a gap where the wedge and labels of its primary coordinate stand, and for a groupstamp also its lines across the frame of each group its timeline lies in (section 6.6) |
| `alignment_anchor` | the line of an alignment anchor of a named MatchStamp, the shortest line between the cross-section lines of its two timestamps (section 8.7) |
| `elision` | the gap of an elision: the narrow rectangle in which a stretch of a timeline is left out, from its card's top border to its bottom border, or for a group elision across the frame's member cards; it draws nothing unless a rule fills it, and its stroke draws the continuations of the rows that cross it (sections 6.6 and 8.9) |
| `ellipsis` | the ellipsis of an elision, three filled dots, one centred in each drawing of its gap (section 6.6) |
| `name` | the name of a row, in the name column, or the title of a group or of the manifest (section 8) |
| `label` | any other text: the name, ID or coordinate of a named timestamp, the name of a MatchStamp at an alignment anchor, the name, ID or elided coordinates of an elision, or the label of a region, jump origin, flow marker or segment |

A drawing has two kinds of marker, and they are never confused. A
**coordinate marker** marks a position of a timeline: it is a wedge, and
the wedges of the named timestamps' coordinates on every timeline, held by
the markers band of that timeline or by its ancestor line, are the
coordinate markers this version draws. A **flow marker** is an element
of a timeline's `flow_control` (a fine, a section break, a double or a
final barline), held by the flow control band and drawn as a vertical line;
the markers band never holds one. A cross-section line is neither: it
belongs to its named timestamp's timeline and is held by that timeline's
line, never by its markers band nor by the timestamp's wedge.

An element **belongs** to a timeline (section 2.2); the `block`, a `frame`,
the titles of a group or of the manifest, and an `alignment_anchor`, which
joins two timelines, with its label belong to none, and have no
domain, modality or class. A card belongs to the timeline it holds, and so
has its domain, modality and class. A band belongs to its timeline but has
no domain and no modality, so no selector naming them matches it, and what
it holds inherits through it its timeline's values unless a rule
matches the band itself (section 2.5). An element has the **domain**
(`graphical`, `logical` or `physical`) and the **modality** (`continuous`
or `discrete`) of its timeline's `unit`. A map instead has the domain and
modality of the map's `target_unit`, so a map is drawn in the style of the
timelines it converts to:

| Domain | Units |
|---|---|
| `logical` | `number`, `floating_measures`, `whole_notes`, `quarters`, `ticks` |
| `physical` | `milliseconds`, `seconds`, `minutes`, `samples`, `frames` |
| `graphical` | `pixels`, `meters`, `centimeters`, `millimeters`, `inches`, `points`, `css_pixels`, `user_units` |

`ticks`, `samples`, `frames` and `pixels` are discrete, every other unit,
`css_pixels` and `user_units` included, continuous. A map whose `target_unit` is null has no domain and no
modality, so no selector naming them matches it and it inherits its style
through its band (section 2.5). An element's **class** is the timeline
class its timeline's unit decides: `Continuous` or `Discrete` for the
modality, then `Logical`, `Physical` or `Graphical` for the domain, then
`Timeline` (`seconds` decides `ContinuousPhysicalTimeline`, `ticks`
`DiscreteLogicalTimeline`). A manifest writes no class; the unit decides
it. A map instead has the map's `type`, one of the ten conversion-map
types of the schema (`LinearMap`, `TableMap`, `ConstantMap`,
`PiecewiseMap`, `ChainMap`, `CombinationMap`, `MeasureRecordMap`,
`MeasureNumberMap`, `FloatingMeasureMap`, `MeasureBeatMap`). A band has
no class; it has its **facet** instead: `markers`, `conversion_maps`,
`children`, `regions` or `flow_control`.

Elements form a **tree** that carries inheritance (section 2.5): the
`block` holds the `timeline`; a `timeline` or `child` holds its five
bands, and each band what it holds: the markers band the wedges of the
named timestamps' coordinates on its timeline, primary and secondary
(section 2), and their labels, each label beside its wedge and not held
by it, the conversion maps band its maps, the children band
its child timelines, the regions band its regions, and the flow control
band its flow markers and jump origins; a `timeline` or `child` also holds
the cross-section lines of its timeline's named timestamps and the gaps
of the card elisions and derived elisions lying on its timeline (section
8.9), each gap holding its ellipsis and its labels, directly and in no
band; any other element holds its own `name` and `label` where it has
one (section 5.3; a map and a band have neither), except that a segment's
label and its `boundary` are held by its segment line, directly and in no
band, as parts of that line (section 6.4). A segment is a child timeline of
its segment line, held by its children band. One that is not a segment
line is a node of the tree although no line of its own is drawn, holding
its five bands, its named timestamps' cross-section lines and the gaps
of the card and derived elisions lying on it as a line does, whose content is drawn at its segment line's line (section 6.4), and
has no element type, so `inside` never names it; one that is a segment
line is drawn as a `child` (section 6.1).
Section 8 states the top of the tree: the block, frames, cards, ancestor
cards and ancestor lines; a frame also holds the gaps of its group
elisions; the block also holds every `alignment_anchor`, and an
`alignment_anchor` holds its label.

### 2.2 Addresses

Every element of a drawing carries an **address**: an object `{id?,
facet?, part?}` built from the IDs of the manifest (README, "Identity")
and compared as a whole object. No address is a string composed from IDs.
`id` is an element's ID; `facet` is one of the five facets `markers`,
`conversion_maps`, `children`, `regions` and `flow_control`, and names a
band; `part` is a non-empty array of the words `start`, `end`, `name`,
`label`, `id`, `coordinate`, `card`, `line`, `elision` and `ellipsis`, and
names a part of an element; `end` names no element in this version. `facet` stands only with `id`, and never with `part`. The name or
label of an element is addressed by the element's address with `name` or
`label` appended to its `part`; a named timestamp has no row and so no
`name` element, and the part `name` of its address names its first label,
a `label` element like its other two. One rule addresses every element of
every manifest, one timeline or many. This specification states IDs bare, as
the `data-id` attributes of the SVG hold them; in a manifest file the `id` of
an address, the `within` of a selector and every other ID reference are
written `#` followed by the ID (README, "Written in a file"), as the snippets
of section 2 show. In this table `T` is a timeline's ID
and `X` an element's ID:

| Element | Address | Belongs to |
|---|---|---|
| the block, which draws the bundle | `{}` | none |
| the title of the manifest | `{"part": ["name"]}` | none |
| the root, or a child timeline with ID `T` | `{"id": T}` | `T` |
| the band drawing the facet `F` of a timeline with ID `T` | `{"id": T, "facet": F}` | `T` |
| a conversion map, region or flow-control element with ID `X` of `T` | `{"id": X}` | `T` |
| the wedge of a named timestamp with ID `X` of `T` | `{"id": X}` | `T` |
| the labels of that timestamp, all `label` elements: its name, its ID, its coordinate | `{"id": X, "part": ["name"]}`, `{"id": X, "part": ["id"]}`, `{"id": X, "part": ["coordinate"]}` | `T` |
| the wedge and the labels of that timestamp at a secondary coordinate on a timeline `U` (section 2) | the same addresses as at its primary coordinate | `U` |
| the cross-section line of that timestamp, and of a groupstamp each of its lines across a frame | `{"id": X, "part": ["line"]}` | `T` |
| the line of an alignment anchor with ID `A` | `{"id": A}` | none |
| the MatchStamp's name at that anchor, a `label` element | `{"id": A, "part": ["name"]}` | none |
| the gap of an elision with ID `E` lying on `T`, wherever it is drawn | `{"id": E}` | `T` |
| its ellipsis | `{"id": E, "part": ["ellipsis"]}` | `T` |
| its labels, all `label` elements: its name, its ID, its elided coordinates | `{"id": E, "part": ["name"]}`, `{"id": E, "part": ["id"]}`, `{"id": E, "part": ["coordinate"]}` | `T` |
| the gap of an elision a card derives on `T` (section 8.9) | `{"id": T, "part": ["elision"]}` | `T` |
| its ellipsis and labels | `{"id": T, "part": ["elision", "ellipsis"]}`, `{"id": T, "part": ["elision", "name"]}`, `{"id": T, "part": ["elision", "coordinate"]}` | `T` |
| the name of an element with ID `X` | `{"id": X, "part": ["name"]}` | that element's timeline |
| the label of an element with ID `X` | `{"id": X, "part": ["label"]}` | that element's timeline |
| every card of a timeline with ID `T`: an ungrouped root's, one in the frame of each group that has `T` as a member, or an ancestor card behind the frame of each group having a member below `T` | `{"id": T, "part": ["card"]}` | `T` |
| the boundary of a segment with ID `S` | `{"id": S, "part": ["start"]}` | `S` |
| the label of a segment with ID `S` | `{"id": S, "part": ["label"]}` | `S` |
| the ancestor line of a timeline with ID `A` | `{"id": A}` | `A` |
| the frame of a group with ID `G` | `{"id": G}` | none |
| the title of a group with ID `G` | `{"id": G, "part": ["name"]}` | none |

So a region `region_1` is `{"id": "region_1"}` and its label `{"id":
"region_1", "part": ["label"]}`, whether the manifest holds its root alone
or many roots, and also when a member below its root is drawn as the root
of its own member drawing; a jump origin `jump_from_1` is `{"id":
"jump_from_1"}`, its label `{"id": "jump_from_1", "part": ["label"]}`; a
named timestamp `timestamp_1` draws its wedge `{"id": "timestamp_1"}`, its
labels `{"id": "timestamp_1", "part": ["name"]}`, `{"id": "timestamp_1",
"part": ["id"]}` and `{"id": "timestamp_1", "part": ["coordinate"]}`, and
its cross-section line `{"id": "timestamp_1", "part": ["line"]}`, whichever
timeline it marks; its wedges and labels at secondary coordinates carry
the same addresses, and the selector member `coordinates` tells them
apart (section 2.3). A
band follows its timeline's ID: the regions band of a child `b` is `{"id":
"b", "facet": "regions"}`. A timeline `perf` that the groups `g1` and `g2`
both have as a member lies in two cards, one in each frame, both
addressed `{"id": "perf", "part": ["card"]}`, and an ungrouped root
`score` in the card `{"id": "score", "part": ["card"]}`. The manifest's
title is addressed `{"part": ["name"]}` whether or not the manifest has an
`id`: the manifest's own `id` addresses nothing, so giving a manifest an ID,
changing it or naming the manifest changes no address. A jump target is
addressed like a region but draws nothing. A MeasureMap belongs to no
timeline and is not drawn; `{"id": X}` with its ID `X` addresses it. A
derived elision has no ID: the elisions a card derives on `T`, one on
each of its pieces (section 8.9: none, one or several, on either side of
the protected span), share the address `{"id": T, "part": ["elision"]}`,
as every element drawn more than once does. A
stored elision clipped into several pieces (section 8.9) keeps its one
address on each, and so does a group elision on each of its drawings: its
gap across the frame of each group its timeline lies in and every gap of
it carried into an ancestor card. Its ellipsis, one in each drawing of
its gap, keeps its one address in every drawing, as its labels do in
every card that draws them.

One timeline may be drawn more than once: as a member in the frame of each
group that has it as a member, as an ancestor line of several members, in
the ancestor card behind each frame holding a member below it (section
8.8), or in several of these. An element drawn more than once,
such a timeline with its cards, descendants, bands, maps, regions,
flow-control elements, named timestamps and elisions, an ancestor line, and the parts of
each, keeps one address, which every drawing of it carries. No address
names a group but the group's own frame and title. So a rule
selecting that address styles every drawing of it (section 2.5), and an
application that selects or marks an element by its address marks every
drawing of it.

### 2.3 Selectors

A selector is an object with any of these members:

- `element`: an element type;
- `addresses`: a non-empty list of distinct addresses (section 2.2); it
  matches an element whose address equals one of them as a whole object,
  so `{"id": "score"}` matches the line of `score` and its ancestor lines,
  never its bands, cards or wedges. An address is open like every object:
  a member other than `id`, `facet` and `part` is an unknown key (README,
  "Unknown keys"), and the address holding it matches no element;
- `domain`, `modality`: a domain, a modality;
- `class`: a timeline class (section 2.1) or a conversion-map type;
- `facet`: a facet (section 2.1); it matches the bands drawing that facet;
- `within`: a timeline ID; it matches the elements belonging to that
  timeline or to any of its descendants;
- `inside`: an element type; it matches the elements held, at any depth,
  by an element of that type in the tree of section 2.1 (so
  `{"element": "name", "inside": "ancestor"}` matches the names of ancestor
  lines and no other name).
- `coordinates`: `primary` or `secondary`; it matches the elements of a
  named timestamp's primary coordinate, or those of its secondary
  coordinates (section 2): `wedge` elements and the `label` elements of
  their stacks, the parts `name`, `id` and `coordinate`. It matches no
  other element: not a cross-section line, which belongs to its timestamp
  as a whole and marks no one coordinate, nor an alignment anchor or its
  label, nor any element that is no named timestamp's.

An element matches a selector when it matches every member present. The
empty selector `{}` matches every element. A band is selected as every
element is: `{"element": "band"}` matches every band, `{"facet":
"regions"}` every regions band, `{"addresses": [{"id": "score", "facet":
"regions"}]}` the regions band of `score`, and `{"inside": "band"}` everything that bands
hold, the bands of every timeline but a member drawing's root included,
since a child is held by its parent's children band.
A timestamp's coordinates are selected so too: `{"element": "wedge",
"coordinates": "secondary"}` matches the wedge of every secondary
coordinate of every named timestamp, and the rule

```json
{"select": {"element": "wedge", "coordinates": "secondary"}, "set": {"display": "inline"}}
```

in a manifest's `graphical` shows those wedges, which the defaults hide
(section 4), still turned −45 by the defaults, since the rule outranks
every default rule by its layer and sets no `rotation` (section 2.5); the
same rule with the selector `{"coordinates": "secondary"}` shows their
labels too, and one selecting `{"element": "wedge", "coordinates":
"primary"}` restyles the own wedge of every timestamp at once.

### 2.4 Properties

Presentation properties carry SVG's names and values where SVG has the
property; the writers map them to TikZ (section 7.4). `content`,
`max-width`, `shadow`, `rotation` and the four elision properties are the
format's own; a turned wedge is written by its points, never with a
`transform` (section 7.2).

| Property | Values | Inherited | Read by |
|---|---|---|---|
| `stroke` | `#RRGGBB` (upper-case) or `none` | yes | every type but `block`, `band`, `wedge`, `ellipsis`, `name` and `label` (an `elision` draws its continuations with it) |
| `stroke-width` | a number ≥ 0 | yes | as `stroke` |
| `stroke-dasharray` | `none`, or numbers separated by single spaces | yes | as `stroke` |
| `fill` | `#RRGGBB` or `none` | yes | `block`, `frame`, `card`, `ancestor_card`, `timeline`, `child`, `ancestor` (the circles at their start and end, the arrowhead at their end), `jump_from` (its arrowhead), `wedge`, `elision` (its gap), `ellipsis`, `name`, `label` |
| `opacity` | a number from 0 to 1 | no | every type but `band` |
| `font-size` | a number > 0 | yes | `name`, `label` |
| `rx` | a number ≥ 0 | no | `block`, `frame`, `card`, `ancestor_card` (the corner radius) |
| `shadow` | `#RRGGBB` or `none` | no | `card`, `ancestor_card` (the colour of its offset shadow, section 8.4) |
| `display` | `inline` or `none` | no | every type but `block` |
| `content` | a text, or `none` | no | `name` (a row's own name, section 6.6) |
| `max-width` | a number > 0, or `none` | no | `name`, and the `label`s of an elision (section 6.6) |
| `rotation` | an integer from −180 to 180 | no | `wedge` (section 6.6) |
| `elision-mode` | `auto`, `full`, `proportional` or `custom` | no | `card`, `ancestor_card`, `frame` (section 8.9) |
| `elision-proportion` | `auto`, or a number greater than 0 and at most 1 | no | `card`, `ancestor_card` (section 8.9) |
| `elision-depths` | `auto`, or positive integers separated by single spaces | no | `card`, `ancestor_card` (section 8.9) |
| `elision-display` | `none`, or words of an elision's `display` separated by single spaces | no | `card`, `ancestor_card` (section 8.9) |

A rule may set any property on any element; an element ignores the
properties its type does not read. `display: none` is the filter: an element
that is not displayed is not drawn and takes no room. An element is
**displayed** when its `display` is `inline`, no rule of this list hides
it, and, for an element of a named timestamp, of an alignment anchor or
of an elision, the timestamp's, the anchor's or the elision's own
`display` lists its word (section 2; for an elision's ellipsis
`ellipsis`, for its labels `name`, `id` or `coordinate`, and for its
continuations `continuation`, while its gap has no word). The two are independent filters,
both of which an element of a named timestamp must pass: its `display`
array chooses what the timestamp draws at all, and the cascade's `display`
property may still hide any one element of it, its wedge, any of its
labels or its cross-section line, as it hides any other element, while a
cascaded `inline` never draws an element its array leaves out. The list
holds every way in which one element hides another, and the other sections
refer to it:

- **A band hides everything it holds.** A band that is not displayed hides
  every element it holds, at any depth of the tree of section 2.1.
- **An element hides its label.** The label of a region, jump origin or
  flow marker, and each ellipsis and label of an elision, is displayed
  only when that element, the elision's gap, is displayed. A named timestamp's labels are not its wedge's
  (section 2.1), and its wedge hides none of them.
- **A line hides its timeline's whole drawing.** A line that is not
  displayed, the root's and a child's alike, hides its name, the maps,
  boundaries and segment labels on it (section 6.4), the cross-section
  lines and the gaps it holds (section 2.1), and its five bands with everything they
  hold, at any depth, its children and its segments with everything of
  theirs included. It takes no room, its stroke
  included: a child whose line is not displayed is not placed and has no
  row (section 6.4, Children), and section 6.5 states what a member
  drawing whose root's line is not displayed still draws.
- **A segment without a line hides its bands.** A segment that is not a
  segment line has no line of its own (section 6.1); when it is not
  displayed, its five bands and everything they hold are not displayed
  either, nor are the cross-section lines it holds (section 2.1), so it
  adds nothing to its segment line's bands (section 6.4, Segments without
  a line) and draws no cross-section line. The boundary and the label of a segment, of
  either kind, are parts of its segment line's line (section 2.1): that
  line hides them, the segment never does.
- **An ancestor line hides its name and its timestamps.** An
  ancestor line (section 8.3) that is not displayed hides its name and
  what it holds of named timestamps (section 8.1): the wedges and labels of the
  coordinates on it and the cross-section lines of its timeline's
  timestamps in that card; it has no row.
- **An ancestor card hides its drawing.** An ancestor card (section 8.8)
  that is not displayed draws nothing of its member drawing, takes no
  room, and the block does not grow for it.
- **An elision leaves out what lies on its stretch.** A displayed gap
  (section 6.6, Elisions), of a card elision in its card or of a group
  elision across a frame and in the ancestor cards behind it, leaves out
  every element there that marks a position in the gap (section 3.2),
  whatever timeline holds it, and cuts every row that crosses it,
  whatever its `display` lists. A gap that is not displayed leaves out
  nothing: its stretch is drawn at full scale, as without the elision, and
  so is every stretch of an elision a card does not draw (section 8.9).

No other element hides another. A frame or card that is not displayed
keeps everything drawn in it (section 8.4); a member's line keeps its
ancestor lines, which are not part of its timeline's drawing; a named
timestamp's wedge, each of its labels and its cross-section line are
displayed or hidden each on its own, so hiding a timeline's markers band
hides its timestamps' wedges and labels and keeps their cross-section
lines; an alignment anchor's line and its label are displayed or hidden
each on its own too, whatever the cross-section lines it joins show,
though a timeline line that is not drawn gives an anchor no end there
(section 8.7); and no band
takes its `display` from another: hiding the band `{"id": "score",
"facet": "regions"}` hides the regions of `score` alone, and the regions of a child of `score` are drawn,
at the child's own line, only when the child's own regions band is
displayed. The defaults hide some bands (section 4).

### 2.5 The cascade

The value of a property on an element is found per property:

1. Of the rules matching the element that set this property, the
   highest-ranking sets it.
2. When none sets it and the property is inherited, the element takes its
   parent's value in the tree of section 2.1.
3. Otherwise the property's initial value applies: `stroke` `none`,
   `stroke-width` 1, `stroke-dasharray` `none`, `fill` `none`, `opacity` 1,
   `font-size` 9, `rx` 0, `shadow` `none`, `display` `inline`, `content`
   `none`, `max-width` `none`, `rotation` 0, `elision-mode` `auto`,
   `elision-proportion` `auto`, `elision-depths` `auto`, `elision-display`
   `ellipsis name`.

The rank of a rule is, from the most to the least significant:

1. its layer: a rule of a later layer outranks every rule of an
   earlier one;
2. whether its selector names `addresses`;
3. the depth of its `within`: none is 0, the root 1, its children 2, and
   so on; deeper outranks shallower;
4. whether its selector names `class`, `facet` or `coordinates`;
5. whether its selector names `element`;
6. whether its selector names `inside`;
7. how many of `domain` and `modality` its selector names;
8. its position: the later rule of one list wins.

The cascade runs on each drawing of an element at its own place in the
tree. Drawings that share an address (section 2.2) match the same `addresses`,
`within` and `element`, but each inherits from its own parent and matches
`inside` by its own holders: the name of an ancestor line matches
`{"inside": "ancestor"}`, the name of the same timeline's row in a card
that draws its line does not.

## 3. Numbers

### 3.1 Positions on the root's axis

A position derived from time is a value on the **root's axis**: a
coordinate of a timeline is carried to the root by adding the offsets of
its ancestors, from the root down. The root starts at the zero of its
number type (`0`, or `0.0` for a float) and ends at its length; a child of a timeline starting at `s`, with
offset `o`, starts at `s + o` and ends at that start plus its own length; a
region, flow-control element or named timestamp of a timeline starting at
`s` lies at `s` plus its coordinate. A jump origin runs from its own position, its
**from**, to its **to**: the position of its `target`, a jump target of the
same timeline, or, when it has no target (a da capo, or a repeat end that
returns to the start), the timeline's start `s`. Where a length is `null`, section 3.4 says where the timeline
ends.

A coordinate's value is read as its number type selects: a `float` value is
a float, an `int` or `fraction` value is exact. Values combine as Python's
numeric tower combines them: the sum of two exact values is exact; a sum
involving a float converts each exact operand to the nearest double (ties
to even) and adds in IEEE 754 binary64 arithmetic, rounding to nearest,
ties to even.

The **midpoint** of two positions `a` and `b`, on which section 6 centres
a segment label, a region's brace tip and label and a jump origin's label, is
`(a + b) / 2` in the same arithmetic: the sum `a + b` combined as above,
then halved, exactly when the sum is exact and as a binary64 division by 2
when it is a float. On a float axis it is therefore the double sum halved,
not the exact midpoint of the two doubles rounded once.

The format and both validators accept a child whose offset is negative,
which starts before its parent's zero. The readers of timetoalign and
TimeLineEditor refuse such a child as not supported yet, and this version
of the specification does not draw it.

### 3.2 From the axis to the canvas

A position `t` on the root's axis, with `λ` the root's length, or its reach
when its length is `null` (section 3.4), becomes the **proportion** `u = t
/ λ`: an exact quotient when both are exact, then
rounded once to the nearest double; a binary64 division when either is a
float; 0 when `λ` is 0. Its x in item coordinates (section 8.2) is

    x(t) = x0 + L × u

in binary64, `x0` the start of the root's line (section 8.2). This is the
only step from an exact value to a double, at any depth of nesting. A
label is spelled from the coordinate (section 5.2), never from the double.

**The elided axis.** A card that draws gaps (section 8.9: an ancestor
card, an ungrouped root's card, or a member's card in a frame with group
elisions) has an x-axis that is linear piece by piece: a sequence of
**runs**, the stretches drawn at full scale, parted by **gaps**. Each gap
lies over a stretch `[a, b]` of the root's axis, `a < b`, no two gaps of
a card overlap, and every gap comes from a stored elision or is derived
by the card (section 8.9). A gap's **natural width** is `n = L × ub − L ×
ua`, `ua` and `ub` the proportions of `a` and `b`, the products formed
first; its drawn width `g` (section 8.9) is at most `n`, and its
**shrink** is `n − g`. A position `t` lies **in** a gap when `a < t < b`,
compared exactly: the ends of a gap lie in none, but in the runs on
either side. A position in no gap has the x

    x(t) = x0 + (L × u − D)

`D` being the sum of the shrinks of the gaps with `b ≤ t`, compared
exactly, each shrink formed first and the shrinks summed from the left.
Before the first gap `D` is 0 and `x(t)` is the value above, `x0 + L ×
u`; so every run keeps the scale `L / λ` of the card, a gap is drawn
`x(b) − x(a)` wide, and every position right of a gap lies its shrink
further left. The end of a root of unknown length (section 3.4) lies at
`x0 + (L − D)`, `D` the sum of every shrink. A position in a gap has no
x: an element marking it is not drawn (section 6.6, Elisions). Wherever
sections 6.7 and 8.2 write `L × u` for a drawn position, it stands here
for `L × u − D`. Gaps move x alone: section 6 lays the card out as
without them, its first fits (section 6.3) measuring every extent by `L ×
u`, so that the card's rows, slots, widths and ordinates are those of the
card drawn whole, and an element that is not drawn because it lies in a
gap keeps its room; only the label stacks of elisions (section 6.4,
Markers) are added to the card's markers bands.

**Seams.** An ancestor card's axis may also jump where it leaves nothing
out. A **seam** at a position `m` of the root's axis parts two runs: the
run left of it ends at `m` and the run right of it starts at `m`, its
**width** `w ≥ 0` further right. On an axis of one scale, the card's
`L / λ`, a seam counts in `D` above as the shrink `−w` of every position
right of it, so everything right of it lies `w` further right; where the
runs on its two sides have scales of their own (section 8.8, Drawn once),
the section placing it gives each run's x. A position at `m`
itself lies on the side the section placing the seam states (section
8.8). A seam is no gap and no elision: it lies in no gap, leaves out no
stretch, has no address and draws no rectangle, ellipsis, continuation
or label: it is no element of the drawing (section 1), and an application
listing a drawing's elisions lists none. A row that crosses a seam, starting before `m` and ending
after it, compared exactly, is drawn across it whole, its line or
outline running on from the one run to the other without a break; an
element at a position other than `m` takes the x of the run it lies on.
Seams lie where an ancestor card's member lies behind its frame (section
8.8, step 2) and where an arrangement changes the scale of a root drawn
once without leaving anything out (section 8.8, Drawn once).

**The frame's elided axis.** The member drawings of a frame share `x0`
and `L` (section 8.2). A frame with group elisions (section 8.9) has one
elided axis for all of them, over **proportions of the frame**: each of
its gaps lies over a stretch `[p, q]` of proportions, `0 ≤ p < q ≤ 1`,
with the natural width `n = L × q − L × p`; a position of proportion `u`
(its proportion of its member drawing's root, section 3.2) lies in the
gap when `p < u < q`, compared as doubles, and one in no gap has the x `x0 + (L × u − D)`, `D` the sum of the shrinks of the gaps with
`q ≤ u`, compared as doubles, summed as above. So a gap lies at one x in
every member card of the frame, the rows of every card, their
descendants and their ancestor lines read x through it, and the frame's
first fits are as without its gaps.

### 3.3 Canvas arithmetic

Every other number of a drawing is a double, computed in IEEE 754 binary64
in the order its formula is written, left to right, multiplications and
divisions before additions and subtractions, and a constant factor such as
`4/3`, `9.5w`, `8w`, `5.5w`, `4w`, `2w`, `1.5w`, `1.2w` or `2.5w` formed before it multiplies
(`1.2w` is the double nearest the exact product of 6/5 and `w`, not the
binary64 product of the double `1.2` and `w`). A distance outwards is
summed whole, left to right as written and a label gap of 2 included,
before it becomes an ordinate `yl − o` or `yl + o`, `yl` the ordinate of
the line of the timeline whose band it lies in (section 6.4); the
boundaries and segment labels of a line are offset from that line (section
6.4), the wedges and labels of the named timestamps on an ancestor line
from that line (section 8.3), and a flow-marker label from the flow row
(section 6.4). A label's baseline is then that ordinate plus
`a(9)` or minus `d(9)`. `max` and `min` compare exactly.

### 3.4 Timelines of unknown length

A timeline whose `length` is `null` has an unknown length: the manifest
does not say where it ends, and the drawing never invents an end for it.
A root of unknown length is scaled to its reach; the end of a timeline of
unknown length is found by the rules below, and is marked as open where
they say so.

**The reach** of a timeline `T` is a value on `T`'s own axis: the largest
of the zero of `T`'s number type and of every coordinate its content
reaches on that axis, which is

- for each child at offset `o`, `o` plus the child's length, or, when the
  child's length is `null`, `o` plus the child's own reach, recursively;
- the `start` and the `end` of each region;
- the `coordinate` of each element of `flow_control`; the to of a jump
  origin (section 3.1) is a jump target's coordinate or the start, so it
  adds nothing further;
- the `coordinate` of each named timestamp of `T` (section 2).

Sums combine as section 3.1 combines values. The values compare exactly;
of several equal largest values, an exact one (`int` or `fraction`) is
taken before a float. Content counts whether or not it is displayed, so a
style never changes a scale. Conversion maps are not content. A timeline
without content, or whose content reaches no further than its start, has
the reach 0. The reach is a coordinate on an axis; the distances that
sections 6 and 8 call the reach of a map stack, a line, a band or a mark
are canvas distances outwards from a line, and have nothing to do with it.

**The end.** Every drawn timeline `T` starting at `S` (section 3.1) ends
at a position on the root's axis, and its end is either **known** or
**open**. The first of these rules that applies gives it:

1. `T`'s length is a value: `T` ends at `S` plus its length; known.
2. `T` is the root of its member drawing: it ends at `λ`, its reach;
   open.
3. `T` is a segment followed by another segment, in canonical order: it
   ends where the next segment starts; known, since the segment line fixes
   it.
4. `T` is the last segment of its segment line: it ends where its segment
   line ends; known or open as that end is.
5. Otherwise: `T` ends at `S` plus its reach; open.

The reach does not follow these rules. A segment of unknown length that is
followed by another counts towards its segment line's reach as every child
of unknown length does, with its offset plus its own reach, never with the
end rule 3 gives it; so when its content runs past the next segment's
start, that content counts towards the reach all the same, and is drawn
where it lies, past the segment's end.

`Xe`, `x` of the end, is `x` of the end's position (section 3.2), except
for an end that is the root's under rule 2, directly or through rule 4,
where `Xe = x0 + L` whatever the reach. So the reach of a
root of unknown length lies at the end of the graphical length, and a root
whose reach is 0 is still drawn `L` long, every position of it at `u = 0`
(section 3.2). A line whose end is open ends in three chevrons (section
6.6), never in a mark that would assert a position.

## 4. Defaults

The defaults are the lowest layer; an application may supply layers
between them and the manifest's own `graphical` object (section 1).

```json
{
  "styles": {
    "graphical-domain": {"stroke": "#FF0000", "fill": "#FF0000"},
    "logical-domain": {"stroke": "#00CC00", "fill": "#00CC00"},
    "physical-domain": {"stroke": "#0050EF", "fill": "#0050EF"}
  },
  "rules": [
    {"select": {"element": "block"}, "set": {"fill": "#F3F4F6", "rx": 10}},
    {"select": {"domain": "graphical"}, "set": "graphical-domain"},
    {"select": {"domain": "logical"}, "set": "logical-domain"},
    {"select": {"domain": "physical"}, "set": "physical-domain"},
    {"select": {"element": "timeline"}, "set": {"stroke-width": 3}},
    {"select": {"element": "child"}, "set": {"stroke-width": 3}},
    {"select": {"element": "timeline", "modality": "continuous"}, "set": {"stroke-dasharray": "none"}},
    {"select": {"element": "timeline", "modality": "discrete"}, "set": {"stroke-dasharray": "3 3"}},
    {"select": {"element": "child", "modality": "continuous"}, "set": {"stroke-dasharray": "none"}},
    {"select": {"element": "child", "modality": "discrete"}, "set": {"stroke-dasharray": "3 3"}},
    {"select": {"element": "map"}, "set": {"stroke-width": 1}},
    {"select": {"element": "map", "modality": "continuous"}, "set": {"stroke-dasharray": "none"}},
    {"select": {"element": "map", "modality": "discrete"}, "set": {"stroke-dasharray": "1 1"}},
    {"select": {"element": "wedge"}, "set": {"fill": "#000000"}},
    {"select": {"element": "region"}, "set": {"stroke": "#000000", "stroke-width": 1, "stroke-dasharray": "none"}},
    {"select": {"element": "jump_from"}, "set": {"stroke": "#000000", "fill": "#000000", "stroke-width": 1, "stroke-dasharray": "1 1"}},
    {"select": {"element": "flow_marker"}, "set": {"stroke": "#FF0000", "stroke-width": 1.5, "stroke-dasharray": "2 2"}},
    {"select": {"element": "boundary"}, "set": {"stroke": "#000000", "stroke-width": 1, "stroke-dasharray": "none"}},
    {"select": {"element": "cross_section"}, "set": {"stroke": "#1BA1E2", "stroke-width": 1, "stroke-dasharray": "3 3"}},
    {"select": {"element": "alignment_anchor"}, "set": {"stroke": "#1BA1E2", "stroke-width": 1, "stroke-dasharray": "3 3"}},
    {"select": {"element": "ancestor"}, "set": {"stroke-width": 3, "opacity": 0.35}},
    {"select": {"element": "ancestor", "modality": "continuous"}, "set": {"stroke-dasharray": "none"}},
    {"select": {"element": "ancestor", "modality": "discrete"}, "set": {"stroke-dasharray": "3 3"}},
    {"select": {"element": "frame"}, "set": {"fill": "#FFFFFF", "stroke": "#D1D5DB", "stroke-width": 1, "rx": 6}},
    {"select": {"element": "card"}, "set": {"fill": "#FFFFFF", "stroke": "#C4C9D1", "stroke-width": 0.75, "rx": 5, "shadow": "#B8BEC8"}},
    {"select": {"element": "ancestor_card"}, "set": {"fill": "#FFFFFF", "stroke": "#C4C9D1", "stroke-width": 0.75, "rx": 5, "shadow": "#B8BEC8"}},
    {"select": {"element": "elision"}, "set": {"fill": "none", "stroke": "#9CA3AF", "stroke-width": 1, "stroke-dasharray": "2 2"}},
    {"select": {"element": "ellipsis"}, "set": {"fill": "#000000"}},
    {"select": {"inside": "ancestor"}, "set": {"opacity": 0.35}},
    {"select": {"element": "cross_section", "inside": "ancestor"}, "set": {"opacity": 1}},
    {"select": {"coordinates": "primary", "inside": "ancestor"}, "set": {"opacity": 1}},
    {"select": {"element": "label"}, "set": {"fill": "#000000", "font-size": 9}},
    {"select": {"element": "name"}, "set": {"fill": "#000000", "font-size": 11, "max-width": 160}},
    {"select": {"addresses": [{"part": ["name"]}]}, "set": {"max-width": "none"}},
    {"select": {"element": "name", "inside": "ancestor"}, "set": {"fill": "#6B7280", "font-size": 9, "opacity": 1}},
    {"select": {"element": "label", "inside": "elision"}, "set": {"fill": "#6B7280"}},
    {"select": {"element": "band", "facet": "regions", "inside": "band"}, "set": {"display": "none"}},
    {"select": {"element": "band", "facet": "flow_control", "inside": "band"}, "set": {"display": "none"}},
    {"select": {"coordinates": "secondary"}, "set": {"display": "none", "rotation": -45}}
  ]
}
```

So a timeline takes the colour of its domain, dotted when discrete and
solid when continuous (dotted: dashes and gaps as long as the stroke is
wide); a conversion map takes the colour and pattern of the domain and
modality it converts to; wedges and braces are black and solid; jump
origins are thin, black and dotted, and flow markers dotted red; a name longer than 160 is
cut (section 6.6), but the manifest's title, whose addressed rule
outranks the rule of every name (section 2.5). Segment
boundaries are thin black rules; a named timestamp's cross-section line is
thin, dashed and light blue, a blue distinct from the physical domain's
(its rule names `element`, which outranks the domain rules, so a
cross-section line of a physical timeline keeps it, section 2.5), and an
alignment anchor's line is drawn alike; an
ancestor line is its timeline's line,
faded, and its name small and grey, while a timestamp named on its timeline keeps
the opacity 1 of a timestamp named on the member: its cross-section line
(its rule names `element` and `inside`) and the wedge and labels of its
primary coordinate (its rule names `coordinates` and `inside`) each
outrank the fading rule (section 2.5), so that a timestamp named on an
ancestor is drawn in the member's card as one named on the member is,
only beside the ancestor line; a secondary coordinate on an ancestor line,
where a rule shows it, stays faded with the line; a group's
frame is white with a light grey outline; a card is white with a grey
outline and a grey offset shadow, so that it stands out from the grey block
and from a frame alike. A card has its timeline's domain and modality, so
a rule can style the cards of one domain. An ancestor card looks like a
card and is shown; a rule setting its `display` to `none` hides it
(section 8.8). An elision's gap is not filled, so it draws nothing of
its own; its stroke, thin, dashed and grey, draws the continuations of
the rows across it where its `display` lists `continuation` (section
6.6); its ellipsis is black and its labels grey, as an ancestor's name
is. The rules selecting a gap and an ellipsis name `element` and so
outrank the domain rules (section 2.5): a gap is unfilled and an ellipsis
black on every timeline. A rule of a later layer setting a gap's `fill`
draws it as a filled rectangle under its ellipsis.
The two rules selecting `band`
hide the regions and flow control bands of every timeline that is
held by a band, which is every timeline of a member drawing but its root
(a child is held by its parent's children band, a segment without a line
of its own too); every markers band, conversion maps band and children band
is shown, so the nesting of a member drawing, every timeline's maps and
every named timestamp stay visible. The last rule hides every wedge and
label of a secondary coordinate (section 2) and turns such a wedge −45, so that a wedge shown by a later
rule points at its coordinate from beside the cross-section line; only
the primary coordinate of each timestamp is drawn by default (section
2.3 shows the rule that shows the others).

The **default band order** of a root of `timelines`, when
`graphical.order` has no entry for it (section 6.4), is

```json
["children", "conversion_maps", "line", "markers", "regions", "flow_control"]
```

So by default a root's conversion maps lie against its line above it and
its children beyond them, its coordinate markers (its named timestamps'
wedges, with their labels) against its line below it, then its regions and
its flow control; its descendants follow it, so every child's maps lie
against the child's line above it and its own children beyond them, and
its named timestamps' wedges against its line below it. The ancestors of a
member that is a child timeline all put their children above their lines,
so their faded lines lie below the member, beyond every band of its below
side (section 8.3). A cross-section line crosses its whole card, in every
band order: it has a gap where its own timestamp's wedge and labels stand,
and crosses every other wedge and label at its `x` (section 6.6).

## 5. Text

### 5.1 The fonts

Every text is drawn in **DejaVu Sans 2.37**, the file `DejaVuSans.ttf` of
that release (SHA-256
`7da195a74c55bef988d0d48f9508bd5d849425c1770dba5d7bfc6ce9ed848954`). Every
code point Noto Music maps and DejaVu Sans does not, such as those of the
Musical Symbols (U+1D100 to U+1D1FF), Byzantine Musical Symbols and Ancient
Greek Musical Notation blocks, is drawn in **Noto Music 2.004**, the
unhinted file `NotoMusic-Regular.ttf` of that release (SHA-256
`26c0a28d7c6f96c70f1401db23066c5ea0ee1cdf155c79bc01ad2efb040de816`), as
the whole note `𝅝` (U+1D15D) of a coordinate label is (section 5.2). Both
files are shipped in this repository under `fonts/`, with their licences
`DejaVuSans-LICENSE` and `NotoMusic-LICENSE` (the SIL Open Font License).
Kerning and ligatures are off everywhere.

Text is measured from the fonts' advance widths, never from a rendering.
One table, `fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json`, holds
them: `units_per_em` (2048), `ascender` (1901) and `descender` (483, as a
positive depth) from DejaVu Sans's `hhea` table, `fallback` (the advance
of DejaVu Sans's glyph 0, 1229), and `advances`, keyed by the code point
in decimal: the advance of every code point DejaVu Sans maps, and of every
code point from U+0020 on that Noto Music maps and DejaVu Sans does not,
Noto Music's advance scaled to 2048 units per em and rounded to the
nearest integer, ties to even. No code point below U+0020 is listed: each
becomes a space before it is measured (the last paragraph of this
section), and DejaVu Sans maps none. With `A` the sum of the advances of a
text's code points (an integer; a code point the table does not hold, one
neither font draws, counts `fallback`, and the drawing lists it), the text
at font size `s` has

| Measure | Value |
|---|---|
| width | `w(text, s) = A × s / 2048` |
| ascent | `a(s) = 1901 × s / 2048` |
| descent | `d(s) = 483 × s / 2048` |
| line height | `h(s) = 2384 × s / 2048` |

A name may hold any code point. Every code point from U+0000 to U+001F in a
text becomes a space before it is measured or written, since SVG and TeX
cannot carry most of them. IDs hold none: the schema refuses them.

### 5.2 Coordinates

A coordinate is labelled with its **pretty text**, rounded for the
drawing: its number, a space (U+0020) and the **pretty unit** of its
unit, or, in seconds, a clock with no pretty unit after it. A pretty unit
is a symbol (`♩`, `𝅝`), an abbreviation (`ms`, `smp`, `uu`), or else the
unit's name (`ticks`, `css_pixels`). Only the text is rounded: the element carries the exact
coordinate (section 1), and no position is computed from its label.

| Unit | Pretty unit |
|---|---|
| `quarters` | `♩` (U+2669) |
| `whole_notes` | `𝅝` (U+1D15D) |
| `milliseconds` | `ms` |
| `minutes` | `min` |
| `samples` | `smp` |
| `pixels` | `px` |
| `points` | `pt` |
| `meters`, `centimeters`, `millimeters`, `inches` | `m`, `cm`, `mm`, `in` |
| `user_units` | `uu` |
| any other unit | the unit's name (`ticks`, `frames`, `number`, `floating_measures`, `css_pixels`) |

`css_pixels` has no abbreviation, since `px` is the pretty unit of the
discrete `pixels`: a coordinate in CSS pixels is labelled with the unit's
name, `800.0 css_pixels`.

The value a label shows is a position of section 3.1, a float or an exact
value, or, on a secondary coordinate, that position written in its
timeline's number type (section 2): a float on a `float` axis, an integer
on an `int` axis and an exact value on a `fraction` axis. Its number is
written as follows; a negative value is written
as its magnitude preceded by `-`.

- **A float** is rounded to three decimal places as Python's `round(x, 3)`
  rounds it: the exact value of the double to the nearest multiple of
  1/1000, ties to even, the result being the double nearest that multiple.
  The result is spelled as Python's `repr` spells it. So
  312.48979591836735 is written `312.49`, 6.71875
  `6.719`, 0.0625 `0.062`, 6.0 `6.0` and 1e-05 `0.0`: a float shows at
  most three decimals and keeps the `.0` that marks a float axis.
- **An integer on an `int` axis** is written in decimal, its digits
  grouped by three from the right with one space between groups:
  `514 041 smp`, `-1 234 567 smp`, `999 smp`.
- **Any other exact value** is a fraction `n/d` in lowest terms. When `d`
  is at most 2520 (the least common multiple of 1 to 10) it is written
  mixed: its integer part when that is not 0, then, when a remainder `r`
  is left, `r/d`, with a space between the two when both are written. So
  219/16 is written `13 11/16`, −3/8 `-3/8`, 3 `3` and 1000 `1000`: the
  digits of a fraction are never grouped. When `d` is greater than 2520
  and has no prime factor other than 2 and 5, the value is written as its
  decimal, which ends, with every place it needs (1/4096 is
  `0.000244140625`). Otherwise it is written `≈`, a space, and the value
  rounded to twelve decimal places, ties to even, with all twelve places:
  1/2521 is `≈ 0.000396667989` and −1/2550 `≈ -0.000392156863`, the `≈`
  before the sign.

A value in **seconds** is written as a clock. Its magnitude, rounded as
above (a float to three places, an approximated fraction to twelve), is
split into whole hours, whole minutes and the seconds that remain, written
`{hours}h{minutes}′{seconds}″` with the prime `′` (U+2032) and the double
prime `″` (U+2033): the hours only when they are not 0, the minutes when
they are not 0 or follow hours, the seconds always, and each part that
follows a written part with its integer part padded to two digits. The
seconds are written as the value is. Those of a float are the decimal its
`repr` spells, with only the places they need and none when they are
whole: 312.48979591836735 is labelled `5′12.49″`, 42.5 `42.5″`, 75.0
`1′15″`, 3725.0 `1h02′05″`, 3599.9996 `1h00′00″` and 1e-05 `0″`. Those of
an exact value are mixed, a decimal that ends or approximated, as above:
151/2 is `1′15 1/2″`, 121/2 `1′00 1/2″`, 1/2 `1/2″`, 1/4096
`0.000244140625″` and 153001/2550 `≈ 1′00.000392156863″`; an integer's
are plain digits, never grouped (3725 is `1h02′05″`, −3600 `-1h00′00″`).
The sign, and `≈` before it, precede the whole clock.

### 5.3 Names and labels

The name of a timeline is its `name`, or, when `name` is null, its whole
`id`, which is never parsed (`original_score:dgt_1` is named
`original_score:dgt_1`). A
conversion map has no name or label in the drawing. A region's label is its `name`, and a region whose `name` is null has none; a jump origin's label is
its `label`, or its `manifestation` when `label` is null; a flow marker's
label is its `label`, and a flow marker whose `label` is null has none; a
jump target draws no label; a segment's label is
its `name`, and a segment whose `name` is null has none; a named
timestamp has three labels, its `name`, its whole `id`, and its
`coordinate`, labelled as section 5.2 labels a coordinate, in its
timeline's unit, and draws those its `display` lists (section 2). An
elision has three labels: its `name` label, its `name`, or the name of
the timeline it lies on where it has none (an elision a card derives
always the latter); its `id` label, its whole `id` (a derived elision has
none, so it draws no `id` label); and its `coordinate` label, the pretty
text (section 5.2) of the start of its gap's elided coordinates without
its pretty unit, `–` (U+2013) and the pretty text of their end, both on
that timeline's own axis, so `1–31 ♩` and `600–1 754 px`; in seconds
both values are clocks, `55.5″–1′30″`. The start and end are those of the
gap as drawn (section 8.9): a clipped elision shows the stretch of its
piece, a derived one the coordinates its gap leaves out. The title of a
group, or of the manifest, is its `name`, or, when `name` is null, its whole
`id`. A manifest with neither a `name` nor an `id`, an
anonymous bundle, has no title.

## 6. Layout

### 6.1 Traversal

The **traversal** lists the timelines in pre-order: the root, then each
child in canonical order (by offset, compared by exact value, then by ID,
compared by Unicode code point, whatever the order of the `children` keys), each followed by its own descendants.

A timeline whose `is_segment_line` is true is a **segment line**; its
children are its **segments**, contiguous from its start to its end. Every
segment lies on its segment line's line, which shows where it starts by a
**boundary** and its name by a label (section 6.4), both hidden with that
line (section 2.4). A segment that is not a
segment line has no line of its own: wherever this section speaks of its
line, it is its segment line's line.
A segment that is itself a segment line is drawn as a child line in its
segment line's children band (section 6.4, Children), and its own segments
lie on that line; neighbouring
segments drawn so meet end to start, the start circle of one inside the
open diamond of the other (section 6.6).

### 6.2 Constants

Distances marked with `S` depend on the card spacing `S` of the member
drawing (section 8.6), the gap between its rows and between its bands;
every other size is fixed. With the default `S = 4` every distance is the
number it has always had.

| Constant | Canvas units |
|---|---|
| padding `P` | 8 |
| gap between the name column and the root's start `G` | 8 |
| gap between bands | `S` |
| row pitch `p` | max(10 + S, h(s)) |
| map double-line spacing `d` | 2 |
| map gap `g` (1.5 × d) | 3 |
| wedge: base, height | 6, 13 |
| label gap (marker to label) | 2 |
| label separation (horizontal, between labels) | 2 |
| brace height | 6 |
| region row pitch `pr` | 6 + 2 + h(9) + S |
| first jump depth | 4 + S |
| jump row pitch `pj` | 6 + S + h(9) |
| flow-marker label offset | 3 |
| boundary half-height `k` | 8 |
| group frame padding `Q` | 8 |
| card padding `K` | 8 |
| gap after the manifest's title `F` | 8 |
| gap after a frame's title | 4 |
| card shadow offset | 2 |
| standard gap of an elision | 32 |
| ellipsis: dot radius, dot spacing, narrowest gap drawing one | 2, 6, 20 |

`s` is the name font size of children bands laid out together (section
6.4, Children): the largest font size of the names of the lines in their
rows, displayed or not (section 6.6); a child whose line is not displayed
has no row. A row whose lines contribute
no name (a row of segment lines, section 6.6) counts the font size the
`name` of its first line has under the cascade. The root's row counts on
its own: its pitch `p0` takes the root's name size alone. A row's **name
size** and **pitch** are the `s` and `p` of the children bands laid out
together whose row it is, at any depth, and the root's name size and `p0`
for the root's row; so all rows of children bands laid out together have
one pitch. Wherever `h(9)`, `a(9)` or `d(9)`
appears in section 3.3, anywhere in section 6 or in section 8, 9 stands
for the largest font size of the drawn labels of the band in question, and
is 9 when the band draws no label; every line at level 0 (section 6.4)
counts as a band of its own, whose labels are its segment labels. So a
regions band whose regions have no drawn label still keeps the label room
`2 + h(9)` in its row pitch `pr`, and is as wide as one with labels of size
9. The labels of a flow
control band are its drawn jump-origin labels and flow-marker labels
together, so its jump rows and flow-marker label tiers share one size.

### 6.3 First fit

Several steps below place items one at a time, in a given order, into
numbered **rows** (or tiers) 1, 2, 3, …: an item goes to the lowest row
holding no item whose extent **conflicts** with its own. Extents are x
intervals measured from the root's start, at any depth of the member
drawing, each end computed as `L × u` (section 3.2) and never as a
difference `x − x0`, so no row depends on `x0`; an extent named by
positions below runs from `L × u` of the one to `L × u` of the other.
`[a1, b1]` and `[a2, b2]` conflict when `a1 < b2` and `a2 < b1`, or when
`a1 = a2`. So an item that starts where another ends shares its row, and
two items starting at the same point never do. The extent of a label is
`[left − 1, right + 1]`, so labels keep the label separation apart: for a
label of width `wi` centred on a position of proportion `u`, `[L × u − wi /
2 − 1, L × u + wi / 2 + 1]`, and for a flow-marker label, `[L × u + 3 − 1, L × u
+ 3 + wi + 1]`, each end computed left to right. Every band fills its own
rows.

### 6.4 Levels and bands

**Every timeline's bands.** Every timeline drawn with a line of its own,
the root and every child at any depth alike, has its five bands, one for
each of its facets (section 2.1), at its own line, and this section lays them out for each such
timeline whose line is displayed (section 2.4) as for the root: a band's **timeline** is the timeline it belongs
to, and "its line", "above" and "below" are that timeline's. `yl` is the
ordinate of a timeline's line: `y_root` for the root (section 6.5), and for
a child the ordinate its row gives it (Children). A segment that is not a
segment line has its bands at its segment line's line (Segments without a
line).

**The band order.** The **band order** of a timeline lists `line`, its
own line, and its five facets, each standing for the band drawing it, from
top to bottom. A timeline without an entry in the manifest's
`graphical.order` (section 2; README, "Groups and the `graphical`
object") follows its **inherited order**: its parent's band order, and
for a root of `timelines` the default band order of section 4. A member
that is a child timeline follows its parent so too. Changing a timeline's
band order therefore changes that of every descendant without an entry of
its own. An entry lists `line` and any of the facets; it is completed
against the inherited order: the listed entries keep their order, and
every facet it leaves out keeps the side of `line` it has in the inherited
order and lies beyond the listed entries on that side, in the inherited
order's sequence, the facets left out above the line before the listed
entries and those below after them. For a root, `["markers", "line"]` is
so `["children", "conversion_maps", "markers", "line", "regions",
"flow_control"]`, `["regions", "line"]` is `["children",
"conversion_maps", "regions", "line", "markers", "flow_control"]`, and
`["line"]` the default; a child of that first root stating `["line",
"children"]` has `["conversion_maps", "markers", "line", "children",
"regions", "flow_control"]`. The bands listed before `line` lie **above**
its line, those after it **below**: up and down, whichever side of its
parent's line it lies on.

**What a band holds.** A band draws what its own timeline holds of its
facet (section 2.1), and what another timeline holds only where a segment
without a line of its own joins its segment line's bands (below):

- the **markers band** its coordinate markers (Markers): the wedges and
  labels of its named timestamps (section 2), and the label stacks of the
  elisions lying on its timeline, never their cross-section
  lines, which its timeline's line holds (section 2.1); no timeline's start
  or end is marked in it, and a flow marker is drawn by the flow control
  band, never by the markers band (section 2.1), so the markers band of a
  timeline that draws no wedge and no label of a named timestamp or an
  elision draws nothing and is absent (Levels);
- the **conversion maps band** its maps (Conversion maps);
- the **children band** its children (Children);
- the **regions band** its regions (Regions);
- the **flow control band** its jump origins and flow markers, with the
  flow markers' labels (Flow control, Flow markers); its jump targets draw
  nothing.

An element that is not displayed (section 2.4) is drawn in no band and
takes no room.

**Levels.** A timeline's line lies at **level** 0. A band is **present**
when it draws an element; the present bands above the line are the levels
1, 2, … outwards, level 1 being the present band listed nearest before
`line` in its band order, and those below it the levels −1, −2, …,
level −1 being the present band listed nearest after it. An absent band
has no level and takes no room. A distance `o` outwards from a timeline's
line lies at `yl − o` above and `yl + o` below.

**Where a band lies.** Each band is laid out from its **start** `c`, a
distance outwards from its timeline's line, so that a band starting at `c
= 0` lies against the line; the paragraphs below place its content from
`c`. A band's **width** is the distance its content reaches outwards from
`c`, and its **outer edge** is `c` plus its width, the width summed first.
The band at level 1, and the one at level −1, starts

- at `c = 0` when it is the markers band or the conversion maps band, each
  of which lies against the line and shares its room with the line's own
  reach (Level 0, below): its outer edge is then the larger of `c` plus its
  width and the line's reach on that side;
- otherwise at `S` beyond the larger of the line's reach on that side and
  `w / 2`, `w` the line's stroke width, so that its content keeps the gap
  `S` from the line's stroke even where the line reaches nothing.

Each further band starts at the outer edge of the band at the level before
it plus `S`. A children band's **own start** is instead the larger of the
start these rules give it and `pl / 2`, wherever it lies, `pl` the **row
pitch** of its timeline, the pitch of the row its line lies in (section
6.2; `p0` for the root), so that the rows of a side, its timeline's
included, lie one pitch apart when nothing widens them; the band starts
as Children lays it out, together with the children bands of the other
lines of that row. A conversion maps band's own start is the start these
rules give it, and the band starts as Conversion maps lays it out, together
with the conversion maps bands of the other lines of its row. The markers band
and the conversion maps band are two bands, never over each other: on one
side they lie at two levels, the outer starting at least `S` beyond the
outer edge of the inner. The **outer edge of a side** of a timeline is
that of its outermost band there, or, when no band is present there, the
line's reach on that side.

**The order of the starts.** A band's own start needs the outer edge of
the band at the level before it, and the start of bands laid out together
needs the own start of each of them. Children bands laid out together may
lie at different levels; conversion maps bands laid out together lie at
one level, and are kept apart where their lines' children bands lie on
different sides of them (Conversion maps). So no start needs itself, and
the starts of one side of a row are found step by step, until every band
is laid out: each step lays out a band, with every band laid out together
with it, once every band that lies between one of them and its line is
laid out. Every
order of the steps gives the same starts.

**Level 0.** A timeline's line reaches out on each side as every line does
(Segment lines, below): by its map stack (Conversion maps) and, when it is
a segment line, by its boundaries, `k` both ways, and above by its segment
labels, which belong to the line and to no band, so its segment labels lie
beyond the maps against it. A drawn boundary spans `k` to either side of
the line, so a line with a drawn boundary reaches at least `k` on both
sides. A markers or conversion maps band at level 1 or −1 thus lies over
the line's boundaries, and every other band beyond them and its segment
labels.

**Conversion maps.** The conversion maps band of a timeline holds its
displayed maps (section 2.4) and those that its segments without a line
join to it (Segments without a line). The present conversion maps bands of
the lines of one row (Children) that lie on one side of those lines, at
one level, are laid out **together**, also when there is only one, in one
sequence of numbered **slots** that their maps share, except that those
whose line's children band on that side lies nearer the line are laid out
together apart from the others, whose line's children band lies further
out or is not present there. Bands of one row on different sides, or at
different levels of one side, are laid out apart. So no conversion maps
band waits, through children bands, on its own start (Where a band lies,
The order of the starts):

- Their maps are **taken** in the traversal order of their lines (section
  6.1), each line's own maps in canonical order before those its segments
  join to it, segment after segment in traversal order, each segment's in
  canonical order.
- A map's **key** is its `name` and its `type` when its `name` is not
  null, else its `type` alone. Keys are ordered by comparing Unicode code
  points: those with a name by name, then by type; those without after
  every key with a name, by type. An ID keys nothing: IDs are unique, so no
  two maps would ever share a slot.
- The maps of each key are placed, in the order they are taken, by first
  fit (section 6.3) into that key's **sub-slots**, each with the extent of
  the timeline it spans, from that timeline's start to its end (sections
  3.1 and 3.4). The sub-slots of the keys, the keys in key order, are the
  slots 1 to `J`. So maps of one key share a slot where their timelines do
  not conflict, and take the next where they do, whichever line of the row
  holds them; a band leaves empty every slot in which it holds no map.
- The bands start at one distance `c0` outwards from their timelines'
  lines, the largest of their own starts (Where a band lies), so `c0 = 0`
  at level 1 or −1. With `w` the largest stroke width of their lines, the
  map in slot `j` is centred `c0 + w / 2 + j × (g + d) − d / 2` from the
  line of its band's timeline, on the bands' side, so that slot 1 lies `g`
  beyond `c0 + w / 2` and each next slot `g` beyond the one before; and
  each of the bands is `e = w / 2 + J × (g + d)` wide, whichever slots its
  own maps take.

At level 1 or −1 a line's conversion maps band is the line's **map stack**
on that side, which **reaches** `e` from the line; on every other side the
line's map stack is empty and reaches 0. A map spans its timeline, from
`Xs` to `Xe`. A band places its maps, and section 7.2 writes them, in the
order they are taken.

Which lines form a row is decided by Children: the root's row holds the
root alone, and every other row is one that the first fits of children
bands laid out together fill. The slots depend on nothing else of the
layout: only on which lines form the row, the displayed maps their bands
hold, the extents of the timelines those maps span, and the side and level
of each band and on which side of it its line's children band lies.

**Segment lines.** Every segment of a segment line except its first (in
canonical order) has a **boundary**: a thin vertical rule at `x` of the
segment's start, `k` to either side of the segment line's line. A line's
boundaries are those of its own segments, drawn on it; the boundary of a
segment that is itself a segment line lies on its segment line's line, not
on its own. The labels
(section 5.3) of the segments of one segment line, in canonical order, are
placed by one first fit into **segment-label tiers** above its line, each
centred on `x` of the midpoint (section 3.1) of its segment's start and end (the
end of section 3.4, so a segment of unknown length ends where the next
segment starts, and the last where its segment line ends). Tier
`n` has its baseline at `y − (m + 2 + (n − 1) × h(9)) − d(9)`, `y` the
line's ordinate and `m` the largest of the reach `e` of the line's stack
above, the width of its markers band when that band lies at level 1, and,
when the line has a drawn boundary, `k`, so that the segment labels lie
beyond the band against the line above, whichever of the two it is. A segment
that is not a segment line has no row, no name in the name column, and no
element type: a selector naming `element` never matches it, only its
boundary or label. A line therefore **reaches** above `m` plus `2 + T ×
h(9)` when its labels fill `T ≥ 1` tiers, and `m` when they fill none; and below the larger of its stack's reach below and,
when it has a drawn boundary, `k`. "Above" is up whichever side of its
parent's line the line lies on, as for every band.

**Segments without a line.** A segment that is not a segment line has no
line of its own, and its bands lie at its segment line's line: what each of
its displayed bands holds joins its segment line's band of the same facet,
after the segment line's own content, segment after segment in
traversal order, and that band draws it and lays it out as it lays out its
own. So the segment's maps lie in its segment line's conversion maps band,
each spanning the segment and taking a slot by its key and extent as every
map of that band does (Conversion maps), not after the segment line's own
maps, so that the maps of one key on two segments may share a slot; its
children in the children band, its regions
in the regions band, its flow-control elements in the flow control band,
and its named timestamps' wedges and labels in the markers band, each at
the segment's start plus its coordinate (section 3.1); its own band order
places nothing. Its named timestamps' cross-section lines, which it holds
itself (section 2.1), are drawn as every cross-section line, across the
card, their gaps where their wedges and labels stand in its segment
line's markers band (section 6.6).
Section 2.4 states when a segment adds nothing. A band of a segment line
is present when it draws anything, of its own or of its segments, also
when its own `display` is `none`, since each segment's bands are displayed
or hidden on their own (section 2.4).

**Markers.** The markers band of a timeline draws its named timestamps, in
canonical order (section 2), and after them those that its segments
without a line join to it, segment after segment in traversal order, each
segment's in canonical order (Segments without a line): of each timestamp
its wedge and its labels (section 5.3), those that are displayed (section
2.4), at `X`, `x` of its position (section 3.1). After them it draws the
secondary coordinates (section 2) on its timeline and on those segments,
of every named timestamp whose cross-section lines cross its line in the
card, in the canonical order of their timestamps, each by its wedge and
its labels at `X`, `x` of the line, as a timestamp of the band is drawn;
the defaults hide them (section 4), and one hidden takes no room. A
timestamp's displayed
labels form its **stack**, one label per line in the order name, ID,
coordinate, the first nearest the wedges; a timestamp without a
displayed label has no stack. The stacks are placed by one first fit
(section 6.3), in the order of their timestamps, into **tiers**: each stack
is one item, as many lines high as it has labels, whose extent is that of
one label as wide as its widest label, centred on `X`. A tier is as many
lines high as its highest stack, and each of its stacks starts on its first
line. Counting lines outwards from the wedges' room (section 6.6), from
1, the label `j` of a stack in tier `k` lies on line `n = m1 + … +
m(k−1) + j`, `mi` the
height of tier `i` in lines. The band is `w / 2 + 13` wide when it draws
no label, or `w / 2 + 13 + 2 + T × h(9)` (left to right) when its tiers
hold `T ≥ 1` lines together, `w` the stroke width of its timeline's line,
`T` the line count here; section 6.6 places
the wedges and the labels from the band's start. This is each stack's
**unturned place**, where it lies when its timestamp's wedge has the
`rotation` 0: at the thick end of the wedge, beyond its base. The room of
the wedges lies between the line and the labels whether or not a wedge is
displayed, so that showing or hiding a wedge moves no label; a band whose
timestamps draw labels and no wedge is as wide as with them. A turned
wedge carries its stack round with it, from its unturned place to the
thick end of the turned wedge (section 6.6, Labels of named timestamps);
the tiers, the first fit and the band's width are those of the unturned
places, so that turning a wedge moves no other label and takes no room
in its band.

After the secondary coordinates the band takes the room of the **label
stacks of elisions** on its timeline: of every gap the card draws for an elision
lying on the timeline (section 8.9) whose `display` lists a label, a card
elision's and a derived one's in the card that draws the gap, a group
elision's in the card of its own timeline in each frame that draws its
gap, never a gap carried into an ancestor card, in the order of the gaps
from the left. Each gap has one stack, its labels in the order name, ID,
coordinate, the first at the top, the words of the elision's
`display`, of a derived elision the card's `elision-display`, choosing
them. A stack enters the band's first fit after the stacks of the named
timestamps' coordinates, primary and secondary, as their stacks do, one
item as many lines high as it has labels, its extent that of one label as
wide as its widest label centred on `L × um`, `um` the proportion
(section 3.2) of the midpoint (section 3.1) of its gap's piece on the
root's axis (section 8.9), and for a group elision `(p + q) / 2` of its
piece in the frame, in binary64: its place at full scale,
so that its tier does not depend on the widths of the gaps. It lies at
its unturned place beyond the room of the wedges, which an elision leaves
empty. The band takes the stack's room there, so the stack's room sets
the band and the card's rows, but the stack is drawn centred below its
gap's ellipsis (section 6.6), whether or not the ellipsis is drawn, so
that showing or hiding an ellipsis moves no label. A band holding a
displayed elision label is present, and its width counts the tiers as for
a timestamp's labels.

A child's present markers
band is one of its bands like any other: it takes a level, widens its side
and so its edge, and its row takes that room (Children). The band never
holds a cross-section line: a named timestamp's cross-section line is held
by its timeline's line (section 2.1), is drawn when it is displayed,
whether or not its wedge, its labels or this band are, and takes no room in
any band (section 6.6).

**Children.** The children band of a timeline places its displayed
children that have a line of their own, every child that is not a segment
and every segment that is a segment line, in canonical order, by first
fit. Each is placed **as a whole**: its line together with everything its
own bands draw, at any depth, laid out from its line by this section. The
**extent** of a child is the smallest interval that holds the extent of its
line, the extent of every item that a first fit of its own drawing places
at any depth (its segment labels, the stacks of named timestamps' labels,
regions, jump origins and flow-marker labels of its bands, and its own
children, each with its extent by this rule), a stack where its wedge
carries it, its extent's centre moved by its carry `vx` (section 6.6,
Labels of named timestamps): `[(L × u + vx) − wi / 2 − 1, (L × u + vx) +
wi / 2 + 1]`, the extent `[L × u + a, L ×
u + b]` of every wedge it draws, `u` the proportion of the position it
marks and `a` and `b` the smallest and the largest of 0, `13 × s − 3 × k`
and `13 × s + 3 × k`, the offsets of its points from `X` (section 6.6,
Wedges), so `[L × u − 3, L × u + 3]` for a wedge not rotated, and the
position `L × u` of every flow marker it draws. The
cross-section lines it draws add nothing: each lies at a position of its
timeline and takes no room (section 6.6).
The maps it draws, at any depth, add nothing: each spans a timeline that
lies within the line it is drawn at, so no first fit of this paragraph
depends on a map's slot. The extent of a line runs
from its start to its end; when its end is open (section 3.4), it runs on
to `L × u + 9.5w`, `u` the proportion of its end and `w`
its stroke width, so that its three chevrons (section 6.6) take room in its
row: `9.5w` is the distance from the end to the outer chevron's tip. This
end of the extent is summed as written, `L × u` plus the constant `9.5w`
(section 3.3), measured from the root's start like every extent and only
compared, never computed from `Xr`; the drawn tip, and the right edge of
section 6.7, is `Xr + 5.5w`. So a child takes the room of its whole
drawing, also where that reaches beyond its span, as a label wider than the child
does, or the content of a segment of unknown length that runs on past the
next segment's start (section 3.4). Since an item that starts where
another ends shares its row (section 6.3), the segment lines among one
segment line's segments lie in one row when nothing of theirs reaches
beyond their spans.

A child's **edge** on a side is the outer edge of that side of its own
drawing (Where a band lies). The lines of a **row** lie at one ordinate:
the root's row holds the root, and every other row is a row of children
bands laid out together. The present children bands of the lines of one
row that lie on one side of those lines, above or below, are laid out
**together**, also when there is only one:

- They start at one distance `c0` outwards from their timelines' lines,
  the largest of their own starts (Where a band lies).
- Each places its own children by its own first fit, and their rows are
  numbered together: row `k` holds every child that any of them places in
  its row `k`, and lies at one distance `lk` outwards from their
  timelines' lines.
- Row `k` has an **inner** half (towards their timelines' lines) and an
  **outer** half: each is `p / 2`, `p` their row pitch (section 6.2), or
  the largest edge of row `k`'s children on that half's side, whichever
  band places them, when it is larger. The outer half's side is the bands'
  own side and the inner half's the opposite one, so a child in a band
  above its parent's line has its own above side in its row's outer half.
- With `ik` and `ok` the inner and outer halves of row `k`, row 1 lies at
  `l1 = c0 + i1` and row `k + 1` at `l(k+1) = lk + (ok + i(k+1))`. A band
  whose children fill `C` rows is `i1 + o1 + i2 + o2 + … + iC + oC` wide,
  summed left to right: its own rows, with the halves they have together.

A child in row `k` has its line at `yl − lk`, `yl` its parent's, when its
band lies above its parent's line and at `yl + lk` when it lies below, and
its own bands lie outwards from its line. The lines of a row lay out their
own children bands together in turn, at every depth, so the sections of a
row of movements share their rows whichever movement holds them.

The layout takes three passes. First every first fit, which uses extents
alone (section 6.3), so that which row holds which line, every row's name
size and pitch (section 6.2), and then every map's slot and the count of
slots of every conversion maps band (Conversion maps), which need the rows
alone, are known before any distance is. Then the distances, from the
deepest rows up: once every row of the children bands of a row's lines
has its halves, each of those lines has the starts and widths of its
bands, in the order of the starts (Where a band lies), and so its edges, and the row its
halves (the root's row the outer edges of the root's sides, section 6.5).
Last the ordinates, from the root's line (section 6.5) down.

No two children's drawings overlap, and no two names of rows (section 6.6)
do. The extents of two lines of a row never overlap, and meet at most
where one ends and the other starts: one band places both by one first
fit, or the bands of two lines of one row place them within those lines'
extents; and each row takes on each side the room that its children's
drawings take there. Rows laid out together lie at least a pitch apart,
since every half is at least half the pitch, and the rows of the children
bands of a row's lines lie within that row's room on their side (its half,
or the root's side) and at least half that row's pitch beyond its
ordinate; so any two rows lie at least half the sum of their pitches
apart, and a row's name is at most its row's pitch high (section 6.2).

A child that is not displayed is not placed; section 2.4 states what it
hides.

**Regions.** The regions band of a timeline places its displayed regions,
in canonical order, by first fit with the extent from the smaller to the
larger of their start and end, widened to the extent of their label when
it is drawn. Row `k` has its brace's arms at `r0 + (k − 1) × pr` from the
timeline's line, `r0` the start of the band; the band is `R × pr − S`
wide.

**Flow control.** The flow control band of a timeline holds first the
**flow-marker label tiers**, `T × h(9)` wide for `T` tiers (0 when it has
no drawn flow-marker label), and then the **flow row**, where the arcs of
jump origins leave and arrive and flow markers end: the flow row lies `T ×
h(9)` beyond the start of the band. The timeline's displayed jump origins,
in canonical order, are sorted stably by span (the absolute exact
difference of their to and from positions, section 3.1), smallest first,
and placed by first fit with the extent from the smaller to the larger of
their from and to, widened to the extent of their label, into **jump
rows**. Row `k` reaches its **apex** at the distance `f0 + (4 + S) + (k −
1) × pj` from the timeline's line, `f0` that of the flow row and `4 + S`
the first jump depth, so a jump origin whose arc encloses another's lies
further out. The band is `T × h(9) + (4 + S) + (K − 1) × pj +
2 + h(9)` wide for `K ≥ 1` jump rows,
and `T × h(9)` wide for none. Its jump-origin descriptors and labels follow this
order of first fit (section 7.2).

**Flow markers.** A displayed flow marker is a vertical line at `x` of its coordinate, from
the flow row across the line of the band's timeline to the far side of
that timeline's own drawing. For the root it runs across every band to the
card margin `V` of the opposite side, inside its padding: from `(x, yf)`
to `(x, P + V)` when the flow control band lies below the root's line and
to `(x, Hc − P − V)` when it lies above it (section 6.5), ordinates of the
member drawing counted from its top (section 8.4). For every other timeline it runs from `(x, yf)` to
`(x, yl − mb)` when the band lies below the timeline's line and to `(x, yl +
mb)` when it lies above it, `mb = max(E, h(s) / 2)`, `E` the outer edge of
the timeline's opposite side and `s` the name size of the row its line
lies in (section 6.2): the distance at which the root's
margin begins beyond the root's line, `s` there the root's name size
(section 6.5). So a flow marker crosses its own timeline's drawing from its flow
row to the far side, as the root's crosses the member drawing, and stays
inside the room the timeline's row takes (Children): of other timelines'
drawings it crosses only those of its own descendants that lie in its way. Its label sits at the line's end on the flow row, alongside the
line on the timeline's side of the flow row: the flow-marker labels are
placed by first fit, in canonical order, into the flow-marker label tiers. Tier 1
touches the flow row: its baseline is at `yf − d(9)` when the band lies
below the line and at `yf + a(9)` when it lies above it, `yf` the flow
row's ordinate, and tier `k` lies `(k − 1) × h(9)` further in, towards the
timeline's line.

### 6.5 Heights

The root's line lies at `y_root = max(P + Ea, P + h(s) / 2) + V`, `Ea`
the outer edge of the root's above side (section 6.4), its descendants'
drawings included in its children band, and `V` the **card margin** of
the member drawing (section 8.6), drawn inside the padding above the
first row or band. The content's height is
`Hc = y_root + max(Eb, h(s) / 2) + V + P`, `Eb` the outer edge of the below
side, the card margin drawn again inside the padding below the last row or
band. Where the member drawing has an ancestor band on a side (section
8.3), `Ea` or `Eb` is instead the outer edge of that band, which lies
beyond every other band of that side. Here `s` is the root's row's name
font size. So a card margin `V`
adds `V` to the card above its contents and `V` below them, and moves its
contents `V` down.

**A root whose line is not displayed** hides its whole drawing (section
2.4): none of its bands is present and its line reaches nothing, so the
outer edges of both its sides are 0. Its row remains, with the name size
`s` and the pitch `p0` of section 6.2, which count its name although the
name is hidden. The formulas above then hold with `Ea` and `Eb` the outer
edges of its ancestor bands above and below (section 8.3), each 0 where it
has none: `y_root = max(P + Ea, P + h(s) / 2) + V` and `Hc = y_root +
max(Eb, h(s) / 2) + V + P`. Each of its ancestor bands starts at
`max(p0 / 2, S)`, the start of section 8.3 with the side's outer edge and
`wm` 0. Such a member
drawing draws its displayed ancestor lines, with their displayed names
and what they hold of named timestamps (section 8.3, Named timestamps),
and nothing else, and lies in its card, `Hm = Hc`
high, as every member drawing does (section 8.4). One without a displayed
ancestor line draws nothing: `y_root = P + h(s) / 2 + V` and `Hc = y_root
+ h(s) / 2 + V + P`, and it gives section 8.2 no name, no centred label
and no right edge.

### 6.6 Elements

Every element below is drawn only when it is displayed, with the cascaded
values of its element. `Xs`, `Xe` are `x` of an element's start and end;
`y` is the ordinate of its line (section 6.4); "outwards" points away from
the line of the band's timeline, up in a band above that line and down in
one below it.

- **Root and children.** A line with stroke width `w` from `Xs`; a filled
  circle of radius `w` centred at the start. The end tells what the
  timeline is; the first of these that applies draws it:
  - a timeline whose end is open (section 3.4) ends with **three
    chevrons**: the line runs on past `Xe` to `Xr = Xe + 4w` and stops
    there, and three chevrons pointing right follow it, each `1.5w` long
    and `3w` high, each `1.5w` further right than the one before, so
    that the inner and the middle chevron each have their tip at the x of
    the next one's arms:
    - the inner chevron through `(Xr + w, y − 1.5w)`, `(Xr + 2.5w, y)`
      and `(Xr + w, y + 1.5w)`;
    - the middle chevron through `(Xr + 2.5w, y − 1.5w)`, `(Xr + 4w, y)`
      and `(Xr + 2.5w, y + 1.5w)`;
    - the outer chevron through `(Xr + 4w, y − 1.5w)`, `(Xr + 5.5w, y)`
      and `(Xr + 4w, y + 1.5w)`, so its tip is at `Xr + 5.5w`.

    Each x is `Xr` plus its own constant multiple of `w`, each ordinate
    `y` minus or plus `1.5w`, or `y` itself, and `Xr` is `Xe` plus `4w`
    (section 3.3); no point is computed from another chevron's.
    The line runs on `4w` past its end and the glyph ends `9.5w` past it,
    12 and 28.5 with the default stroke width 3 of a `timeline` or `child`
    line; these are distances, and the tip is written, and is the right
    edge (section 6.7), as `Xr + 5.5w`. Relative to `Xr`, the inner and middle chevrons lie where an
    ancestor line that runs on to the right draws its two (section 8.3),
    and the outer chevron is what tells the marks apart: **three
    chevrons** say that a timeline's length is unknown, **two** that an
    ancestor line runs on beyond the member it is clipped to. An ancestor line never ends in
    three chevrons, whatever its length or the member's, and an open end
    never in two. The three chevrons stand for a root, a child, a segment
    line or a member alike, locked or not: an end that is not known has no
    position for a circle, an arrowhead or a diamond to mark;
  - a top-level timeline (a root of the manifest) whose end is known and
    whose `locked` is false ends with an **arrowhead** of length `3w` and half-width `1.5w` whose base is
    at `Xe` and whose tip is at `Xe + 3w`, the line ending at `Xe`, so that
    the drawn timeline is longer than its length; when it is a segment line,
    the arrowhead is **open**: the same triangle, stroked with width `w / 2`
    and not filled, since prolonging it appends a segment;
  - a top-level timeline whose end is known and whose `locked` is true ends
    with a filled circle of radius `w` centred at `Xe`, like its start, the
    line ending at `Xe`;
  - a child timeline whose end is known, at any depth, ends with an **open
    diamond** of half-length `1.5w` and half-width `1.2w` centred at `Xe`
    and stroked with width `w / 2`, the line stopping at its left corner:
    the diamond marks where the child ends on its parent's axis, and is the
    same whether the child's `locked` is true or false. A member that is a
    child timeline ends so too, although its line is a `timeline` element.

  The circles and the arrowhead are
  filled and not stroked; the open arrowhead, the diamond and the chevrons
  are stroked and not filled, with no dash. Every arrow of a drawing follows one rule:
  its shaft ends at its head's base, and the head continues the shaft's
  direction at that point.
- **Boundaries.** A line from `(X, y − k)` to `(X, y + k)`, `X` the
  segment's start and `y` its segment line's ordinate (section 6.4), drawn
  over the line.
- **Segment labels.** Centred on `x` of the midpoint of the segment's start and end,
  in its tier (section 6.4).
- **Wedges.** A filled triangle, not stroked, its tip at `X`, at the
  distance `c + w / 2` outwards from the line of its band's timeline, `c`
  the start of the markers band (section 6.4) and `w` the stroke width of
  that line, so that with `c = 0` the tip lies on the line's edge. Its
  `rotation` `r` turns it about its tip: `r` is the angle in degrees from
  the outward direction to the direction from the tip to the middle of its
  base, the base lying to the left of `X` when `r < 0` and to the right
  when `r > 0`, on either side of the line, so that a wedge turned −45
  points at its coordinate from the lower left below the line and from the
  upper left above it. With `s` and `k` the sine and the cosine of `r`
  degrees, each rounded to four decimal places, ties to even, and read as
  the double nearest that decimal, its base's corners lie at `X + (13 × s −
  3 × k)` and `X + (13 × s + 3 × k)`, at the distances `c + w / 2 + (13 ×
  k + 3 × s)` and `c + w / 2 + (13 × k − 3 × s)` outwards, so that with `r
  = 0` its base, 6 wide and centred on `X`, lies 13 further out than its
  tip. −180 and 180 draw the same wedge. The vertical through `X` meets a
  wedge turned by 13 to 167 in either direction at its tip alone; at 168 and
  beyond, up to 180, the base's corners lie on either side of `X` and the
  vertical runs through the wedge's body. A
  wedge takes the room of an unrotated one: its band is as wide whatever
  its rotation, and what of it lies beyond that room takes none; its
  labels go round with it (Labels of named timestamps).
  The wedges of a markers band mark its named timestamps' primary
  coordinates and the secondary coordinates on its timeline (section 6.4,
  Markers; section 2): a wedge of a primary coordinate is turned by 0
  unless a rule sets its `rotation`, and the defaults turn a wedge of a
  secondary coordinate −45 (section 4).
- **Labels of named timestamps.** A timestamp's stack lies at the thick
  end of its wedge, centred on the wedge's **axis**, the line from the
  middle of its base to its tip, which points at the coordinate; whether
  or not the wedge is displayed, the stack lies where the wedge would
  carry it. At its unturned place (section 6.4, Markers), the wedge's
  `rotation` being 0, each label is centred on `X`, `x` of its
  timestamp's position, on its line of the band's tiers: line `n` starts
  `c + w / 2 + 13 + 2 + (n − 1) × h(9)` out, `c` and `w` as for the
  wedges, the label gap included, and the label's baseline lies beyond
  that start. A wedge turned by any other `r` carries its stack, kept
  upright, as one box: with `s` and `k` as for the wedges, `j` the number
  of the stack's labels, `W` the width of its widest label, `H = j × h(9)` its
  height and `D = 13 + 2 + (n1 − 1) × h(9)` the distance from the tip at
  which its first line `n1` starts at its unturned place, the box's centre
  lies on the axis at the distance

      t = D + W / 2 × |s| + H / 2 × |k|

  from the tip, summed left to right, so that the box lies wholly beyond
  the line that crosses the axis at the distance `D` from the tip at a
  right angle, and touches it: beyond the middle of the base by the label
  gap 2, and by the lines of the tiers before its own. The stack's
  **carry** is `vx = t × s`: its labels are centred on `X + vx`, and the
  box's centre lies `c + w / 2 + t × k` out, summed whole first (section
  3.3). Its lines, each `h(9)` high, fill the box from its side nearer the
  tip: when `k ≥ 0`, line `i` of the stack starts `(c + w / 2 + t × k) −
  H / 2 + (i − 1) × h(9)` out and its label's baseline lies beyond that
  start, outwards; when `k < 0`, the box lying across the line, line `i`
  starts `(c + w / 2 + t × k) + H / 2 − (i − 1) × h(9)` out and its
  label's baseline lies beyond that start inwards, away from the tip, as
  a label's of a band on the other side of the line does. A wedge at the
  rotation 0 carries nothing (`vx` 0). Section 8.3 carries the stacks of
  the named timestamps drawn on an ancestor line so.
- **Cross-section lines.** A vertical line at `X`, `x` of its named
  timestamp's position (section 3.1), across the whole card of each
  member drawing that draws its timeline's line, or draws its timeline as
  an ancestor line and the timestamp on it (section 8.3, Named
  timestamps), the ordinates being of the member drawing counted from its
  top (section 8.4). Let `T` be the timestamp's timeline, whose line or
  ancestor line holds the cross-section line (sections 2.1 and 8.1), or,
  for a timestamp of a segment without a line, that segment's segment
  line, whose line and bands are the segment's (section 6.4, Segments
  without a line). The line runs from `(X, yt)` to `(X, yb)`,
  `yt` the top of the card and `yb` its bottom, the card's rectangle as
  sections 8.4 and 8.6 write it (an ancestor card's as section 8.8 places
  it), its shadow not counted, whether or not the card is displayed: from
  the card's upper border to its lower border, in every band order and
  whatever the card holds, less its **gap**, where the wedge and the
  labels of its primary coordinate stand on it. The gap spans these
  distances outwards from `T`'s line, `c` and `w` as for the wedges; on
  an ancestor line they are measured from it on its outer side, with `c`
  0, `w` its stroke width and the tiers of its row (section 8.3):

  - when the wedge is displayed and the vertical through `X` runs through
    its body, that is when its `rotation` is −12 to 12 or beyond 167 in
    either direction (Wedges): the distance `c + w / 2` of its tip and
    those of its two corners, `c + w / 2 + (13 × k + 3 × s)` and `c + w /
    2 + (13 × k − 3 × s)`;
  - when its stack holds a displayed label and lies across `X`, its labels
    being centred on `X + vx` and the widest `W` wide, so that `X + vx −
    W / 2 ≤ X ≤ X + vx + W / 2` (Labels of named timestamps): the
    distances of the box's two sides, `(c + w / 2 + t × k) − H / 2` and
    `(c + w / 2 + t × k) + H / 2`; at its unturned place, with its stack
    in tier `k'` and `n1 = m1 + … + m(k' − 1) + 1` its first line, the
    distance `c + w / 2 + 13 + 2 + (n1 − 1) × h(9)` at which that line
    starts and that distance plus `j × h(9)`.

  The gap runs from the smallest of these distances to the largest, each
  summed whole before it becomes an ordinate `y ± o` (section 3.3), `y`
  the ordinate of `T`'s line and `o` the distance; with neither the wedge
  nor the stack counting there is no gap. What remains is drawn as up to
  two lines, from the top down, and a line of no length is not drawn. So
  a timestamp drawing its wedge, at the rotation 0, and its labels in tier
  1 has its line run from the card's border through its timeline's line
  to the wedge's tip, and on from the outer edge of its last label, the
  label gap between them left out too, to the card's other border; a
  match timestamp drawing its line alone draws it from border to border.
  The line is cut nowhere else: it crosses every other element of the
  card at `X`, the lines of every other timeline, ancestor lines
  included, every band, the wedges and labels of other
  timestamps, and the wedges and labels of its own secondary coordinates,
  each of which keeps its own `rotation`.

  A named timestamp whose timeline is drawn in several cards, as a member
  in the frame of each group that has it as a member, as a descendant in
  another member's drawing, in an ancestor card (section 8.8), as an
  ancestor line of a member whose span holds its position (section 8.3),
  or more than one of these, draws its cross-section line in each, by this
  rule in that card. A cross-section line is drawn over everything else of its
  member drawing (section 7.2), takes no room, and widens no band or row.
  A match timestamp's cross-section line is drawn by this rule, as every
  other; the alignment anchors that join such lines are drawn after every
  item (section 8.7).

  A **groupstamp** (section 2) on a timeline `T` draws further lines
  in the frame of each group `G` that `T` lies in, across the frame's
  member cards. Let `M` be the member of `G` that is `T` or has `T` as a
  descendant. The lines lie at `X`, `x` of the timestamp's position in
  `M`'s member drawing of that frame, where `T`'s line holds the
  timestamp's own cross-section line by the rule above. Every member
  drawing of a frame starts at the same `x0` and ends at `x0 + L` (section
  8.2), the line of a member of unknown length at its reach (section 3.4,
  rule 2), so the line marks on every member the same proportion of its
  drawn length: of its length, or, on a member of unknown length, of its
  reach. With `yt` the top of the topmost card of the members of `G` whose
  lines are drawn in the frame and `yb` the bottom of the bottommost, each
  card's rectangle as sections 8.4 and 8.6 write it, its shadow not
  counted, whether or not the card is displayed, the line runs from `(X,
  yt)` to `(X, yb)`: from the upper border of the topmost member card to
  the lower border of the bottommost, across the gaps between the cards
  and whatever lies between, less `M`'s card, from its top to its bottom,
  which the timestamp's own cross-section line crosses. What remains is
  drawn as up to two lines, above `M`'s card and below it, from the top
  down, and a line of no length is not drawn.

  The line lies within the drawn span of every member, a member of
  unknown length included, which it crosses up to its reach; but a
  proportion of a reach is no coordinate, so the line gives a coordinate
  without a value (section 2) on a member of unknown length other than
  `M`, and on every timeline that member's card draws, and, when `M` has
  an unknown length, on every member other than `M` and every timeline
  their cards draw. Such a coordinate is shown as undefined, as a rule of
  the drawing that no style changes: the part of the line over the card of
  a member it gives no value, from the card's top to its bottom, is cut
  out of the line above and drawn as a line of its own at opacity 0.35,
  the opacity the defaults give an ancestor line (section 4), in place of
  the opacity cascaded for the line; when `M` has an unknown length, both
  lines are drawn so, whole and uncut. On a timeline where the coordinate
  has no value, its wedge, where it is displayed, is drawn at opacity 0.35
  in place of its cascaded opacity, and no `coordinate` label is drawn,
  whatever its `display` lists, its `name` and `id` labels standing as at
  any secondary coordinate. Where every member's length is known, none
  of this applies.

  These lines have no gap:
  they cross secondary coordinates alone (section 2), and cross the
  wedges and labels of other timestamps and of those secondary
  coordinates where they meet them. The groupstamp's own
  wedge marks its primary coordinate and is turned by 0 unless a rule sets
  its `rotation`, as every named timestamp's (Wedges). The positions of
  these lines are item coordinates of the frame, drawn at the frame's
  place as every element of the frame is (section 8.6), and the lines take
  no room and widen nothing.

  Each of these lines, a faded one included, is a further drawing of the timestamp's cross-section line
  (section 2.2): it carries the line's address, belongs to `T`, has no
  settings of its own, and is drawn when the timestamp's `display` lists
  `cross_section` and that line is displayed in `M`'s card of the frame,
  in the values cascaded for it there. It has no wedge and no labels, and
  nothing is drawn in a frame where the line holding the timestamp's own
  cross-section line is not drawn. The timestamp's wedge, its labels and
  its own cross-section line are drawn in every card as every named
  timestamp's are.
- **Maps.** A closed double line: the outline of the rectangle from `Xs`
  to `Xe` of the map's timeline between the ordinates `yc − d / 2` and `yc
  + d / 2`, `yc` the map's centre (section 6.4), stroked and not filled.
- **Regions.** A brace from `Xs` to `Xe`, arms at `yb`, tip 6 further out
  at `Xm`, `x` of the midpoint (section 3.1) of the region's start and end, so it
  opens towards its timeline's line; its label centred on `Xm` beyond the
  tip, 2 further out. The arms lie at the distance `r0 + (k − 1) × pr` of their
  row (section 6.4), the tip at that distance plus 6, and the label's
  ordinate at that distance plus 6 plus 2, each distance summed whole
  before it becomes an ordinate (section 3.3), never computed from `yb`.
- **Jump origins.** An arrow from `(Xf, yf)` to `(Xt, yf)`, `Xf = x(from)`,
  `Xt = x(to)` (section 3.1), `yf` the flow row, `w` the jump origin's
  stroke width. Its **curve** is
  the cubic Bézier curve from `P0 = (Xf, yf)` to `P3 = (Xt, yf)` with
  controls `C1 = (Xf + q, yc)` and `C2 = (Xt − q, yc)`, `q = (Xt − Xf) / 4`
  and `yc = yf + 4/3 × (ya − yf)`, `ya` the ordinate of its jump row's apex:
  the controls lie a quarter of the span inwards, so the curve reaches its
  apex halfway, and a short arc arrives steeply and a long one flatly. The
  arrow is placed as TikZ places an arrow tip on a curve: the head points
  along the curve's direction at its end, the unit vector `u = (ux, uy)`
  from `C2 = (Cx, yc)` to `P3`, `ux = (Xt − Cx) / ℓ` and `uy = (yf − yc) /
  ℓ`, `ℓ = sqrt((Xt − Cx) × (Xt − Cx) + (yf − yc) × (yf − yc))` (the
  correctly rounded square root); the head is a filled triangle, not stroked, of length `4w` and
  half-width `2w`, its tip at `P3` and its base centred at `Bh = (Xt − 4w ×
  ux, yf − 4w × uy)`, its corners `Bh − 2w × n` and `Bh + 2w × n`, `n = (−uy, ux)`; the **shaft** is
  the curve with its end moved from `P3` to `Bh` and its controls kept, so
  it meets the head's base at a right angle. The label is centred on `x` of
  the midpoint of from and to, beyond the apex, 2 further out.
- **Flow markers.** The line of section 6.4 at `x` of the flow marker; its label
  starting at `x + 3`, in its tier (section 6.4).
- **Names.** For each **row** of lines (section 6.4, Children: the root's
  row and every row of children bands laid out together, at any depth, so
  that all lines at one ordinate form one row), the names (section 5.3) of
  its drawn lines whose names are displayed, in traversal order, joined by
  `, `; the line of a segment
  contributes no name, since its name is its label, so a row of segment
  lines alone has no name. When the
  `content` of the first of these names is not `none`, the row shows that
  text instead (an editor sets it to give a row its own name, and resets it
  to `none`). When the text is wider than that name's `max-width`, it is cut
  to its longest prefix that, followed by `…` (U+2026), fits, and the cut
  text is shown. It is drawn starting at `x = n` (section 8.2), vertically
  centred on the row: baseline at `y + (a(s) − d(s)) / 2`, `s` the font size of that first
  name, whose address the text carries. Name descriptors are ordered from
  the top row down.
- **Elisions.** A gap (section 8.9) over the stretch `[a, b]` of the
  card's root axis, or over `[p, q]` of a frame's proportions (section
  3.2), is the rectangle from `x(a)` to `x(b)` (`x(p)` to `x(q)`), and from
  the top `yt` to the bottom `yb` of its card, the card's rectangle as
  sections 8.4 and 8.8 write it, its shadow not counted; a gap across a
  frame (section 8.9, Group elisions) runs from the top of the topmost
  member card drawn in the frame to the bottom of the bottommost, as a
  groupstamp's line does, over the cards and the gaps between them. It is
  filled with its `fill` and not stroked, and draws no rectangle while its
  `fill` is `none`; the rectangle is its extent all the same, in which an
  application finds it. A **row crosses** a gap when it is a line or a map
  drawn in that card, or in one of the frame's member cards, the root's,
  a child's or an ancestor line alike, whose span holds the whole gap: its
  start (section 3.1) at or before `a` and its end (section 3.4) at or
  after `b`, compared exactly, or, across a frame, the proportions of its
  start and its end at or before `p` and at or after `q`, compared as
  doubles, the end of a member whose end is open (section 3.4, rule 2)
  counting as 1, and an ancestor line that runs on to the right (section
  8.3) counting as open like it, so that it crosses every gap at or after
  its start; its **ordinate** is its line's `y`, or a map's centre `yc`. A
  row that crosses a gap stops at `x(a)` and resumes at `x(b)`: its line
  or outline is drawn in pieces, from run to run, with no end mark where a
  piece stops at a gap and no start mark where one resumes after it, and
  nothing of it is drawn in the gap. A line or map whose start lies in a
  gap starts at that gap's right edge, without a start circle, one whose
  end lies in a gap ends at that gap's left edge, without an arrowhead,
  end circle, diamond or chevrons, and one whose start and end so meet or
  cross is not drawn. A line that really starts or ends at a gap's edge
  keeps its mark there, since an edge lies in no gap. The pieces are
  written from the left, each a `<line>` of the line (for a map a closed
  outline over the piece), and then the line's start and end marks
  (section 7.2); a piece that does not end right of where it starts, as
  where a line starts at a gap's left edge, two gaps touch, or a child's
  line ending at a gap's right edge would stop at its diamond's left
  corner before that edge, is not written.

  A gap draws, where its elision's `display` lists `ellipsis` (for a
  derived elision the card's `elision-display`), exactly one
  **ellipsis**, never one per row: three filled circles of radius 2
  centred at `xm − 6`, `xm` and `xm + 6`, at the ordinate `ym`, with `xm
  = (x(a) + x(b)) / 2` the gap's middle and `ym = (yt + yb) / 2` the
  middle of its height, `yt` and `yb` the top and the bottom border of
  the card that draws it, or, for a gap across a frame, the top of the
  topmost and the bottom of the bottommost member card (section 8.9), in
  binary64; an ellipsis is not drawn in a gap narrower than 20, `x(b) −
  x(a) < 20`. Where its `display` lists `continuation`, each row that
  crosses the gap gets a **continuation**, a line from `(x(a), y)` to
  `(x(b), y)`, `y` its ordinate, drawn in the gap's stroke, under the
  ellipsis. Its labels, the stack of section 6.4 (Markers), are drawn
  with the ellipsis, centred on `xm` just below it, whether or not the
  ellipsis is drawn: its `i`-th label, from 1, has its baseline at `ym +
  (2 + 2 + (i − 1) × h(9)) + a(9)`, the dot radius and the label gap
  below `ym`, `h(9)` and `a(9)` those of the markers band that takes the
  stack's room, in the card that draws them; each label is cut to its
  `max-width` as a name is cut (Names), never to the gap. Nothing else that lies on the stretch is
  drawn in a gap, but for the arc of a jump origin. An element that marks
  a position in a gap is not drawn: a wedge with its labels, a
  cross-section line, a groupstamp's lines across a frame, a boundary, a
  segment label, a flow marker with its label, a region whose start, end
  or midpoint lies in one with its label, and a jump origin whose from, to
  or the midpoint of the two does with its label. A region whose start,
  end and midpoint lie in no gap is drawn at their elided x, and its brace
  is **cut** at every gap it spans as a row is. Of the brace's two
  straight parts at `Ym`, from `X1 + k` to `Xm − k` and from `Xm + k` to
  `X2 − k` (`X1`, `X2`, `Xm`, `k` and `Ym` as section 7.2 writes the
  brace), the part a gap meets leaves out the stretch from the larger of
  the gap's left edge (`x(a)`, or `x(p)` across a frame) and the part's
  start to the smaller of its right edge (`x(b)`, `x(q)`) and the part's
  end, where that stretch has a length, with no tick or other mark at
  either end of the cut; cuts that touch are one cut, and the brace's
  arms, its tip and its label are drawn whole. A jump origin whose from,
  to and their midpoint lie in no gap is drawn whole at their elided x,
  its arc across every gap it spans: the one element drawn in a gap that
  is not the gap's own. A position at a gap's edge lies in no gap, so a
  named timestamp there is drawn.

A label "beyond" a point at ordinate `y` lies outwards from it: below, its
baseline is at `y + a(9)`; above, at `y − d(9)`, with the label gap added
where stated.

### 6.7 Extents

Section 8 places a member drawing in its card. Its **names**
are the name texts it draws, its ancestor names included, and every
centred label `i` it draws (segment, region and jump-origin labels, every
label of a named timestamp's stack on its own, and the labels of its
elisions) has width `wi` and the proportion `ui` (section 3.2) of the
exact position it is centred on, and its **carry** `vi`: a label of a
named timestamp is centred at its timestamp's position, moved by the
carry its wedge gives it (section 6.6, Labels of named timestamps;
section 8.3), a label of an elision at its gap's middle (section 6.6,
Elisions), for which `L × u` stands for `(l + r) / 2`, `l` and `r` the
gap's edges less `x0`: `l = L × ua − D` with `D` the shrinks of the gaps
left of it, and `r = L × ub − D'` with `D'` those and its own shrink
(section 3.2), so that no `x0` enters it, and every other
centred label has the carry 0.
A centred label at `X` ends at `(X + vi) + wi / 2`. Its **right edge** is the largest right edge of any element it
draws (lines, markers, wedges, braces, arcs, labels and names). Right
edges are geometric, no stroke width counted: a timeline's start circle
`Xs + w`, its arrowhead's tip `Xe + 3w`, its end circle `Xe + w` or its
diamond's corner `Xe + 1.5w`, the outer chevron's tip of an open end's
three chevrons `Xr + 5.5w`, with `Xr = Xe + 4w` computed first (section
6.6; `9.5w` past `Xe` only as a distance, never as the sum `Xe + 9.5w`),
the outer chevron's tip of the two chevrons of an ancestor line that runs
on to the right `Xr + 4w`, with `Xr = x0 + L + 4w` computed first (section
8.3; `8w` past `x0 + L` only as a distance), a map's `Xe`, a boundary's
or a cross-section line's `X`, the largest x of a wedge's three points
(section 6.6), `X + 3` for a wedge not rotated, the largest x of
the points written in a brace's or a jump origin's descriptors (control
points and a jump origin's arrowhead corners included), a gap's `x(b)`,
the right end `xm + 8` of an ellipsis, and a text's end from its advance
widths. In a card with gaps every x here is the elided one (section
3.2), and a line or map that ends in a gap ends at its left edge
without its mark (section 6.6, Elisions).

## 7. Writers

### 7.1 The page

A writer draws one or more drawings, each placed at a canvas position `(X,
Y)` with a scale `z` (one drawing alone: `(0, 0)` and 1). The page is the
bounding box of the placed blocks, each `W × z` by `H × z`, plus a margin of
16 on every side: with `left` and `top` the smallest `X` and `Y` and
`right` and `bottom` the largest `X + W × z` and `Y + H × z`, the page is
`PW = right − left + 32` wide and `PH = bottom − top + 32` high, and a
drawing at `(X, Y)` lies at the page position `(X − left + 16, Y − top +
16)`, y downwards. Canvas units are CSS pixels in SVG, whose `viewBox`
matches its unitless `width` and `height`, and points in TikZ.

### 7.2 Element descriptors

A member drawing becomes a list of SVG **element descriptors**, in this
order: the flow markers; the maps; the regions; the jump origins, each of these four
band by band in the traversal order of the bands' timelines, and each
band's in the order it places them (section 6.4); the root and
then the children in traversal order; the boundaries, in the traversal order
of their segments (a nested segment line's boundaries thus follow its own
boundary, not its siblings'); the wedges, band by band in the traversal
order of the bands' timelines, and each band's in the order it places its
timestamps and then the secondary coordinates on it (section 6.4,
Markers); the names; the **marker labels**, the labels of the named
timestamps' coordinates in the same order, coordinate by coordinate,
each one's in the order of its stack, its name, its ID and its
coordinate, whether or not its wedge is displayed; the segment labels, in
the traversal order of their segments, the region labels, the jump-origin
labels and the flow-marker labels; and last the cross-section lines, in
the order in which the markers bands place their timestamps, whether or not
a wedge, a label or its band is displayed, so that they lie over
everything else of the member drawing. Section
8.5 places them among the background, the titles, frames and cards, and
the ancestor lines. Every
descriptor carries the address of its element (section 2.2), the
background the block's empty address `{}`; the several descriptors of one
element carry the same address. The SVG writer writes an address as up to
three attributes, each only when the address has its member: `data-id`,
the `id`; `data-facet`, the `facet`; and `data-part`, the words of `part`
joined by one space (`data-part="start label"`). The background so
carries none. An editor renders these same descriptors on
screen; the SVG writer serializes them. An element's hit area is the
painted geometry of its descriptors, each standing for the element whose
address it carries; this specification gives no element a hit area beyond
them. So the three chevrons of an open end, part of their line like an
arrowhead, carry the line's address `{"id": T}` and hit the timeline.

A point in a template (`{p1}`, `{P0}`, `{P3}`, `{Bh − 2w × n}`, …) is
written by where it stands. In a `points` attribute it is `{x},{y}`, its
two numbers formatted by section 7.3 and joined by a comma without a
space, and the points are separated by one space, as the polygon templates
spell out; this holds for the chevrons' polylines and the jump origin's arrowhead
too. In path data (`d`) it is its two numbers separated by one space, as
the brace below writes them, so a jump origin's shaft `M{P0}C{C1} {C2} {Bh}`
opens like `M290.9775 63.8555C253.4775 74.5221`.

| Element | Descriptors |
|---|---|
| background | `<rect x="0" y="0" width="{W}" height="{H}" rx="{rx}" fill="{fill}"/>` |
| frame | `<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}">` filled and stroked (section 8) |
| card, ancestor card | when its `shadow` is not `none`, `<rect x="{x+2}" y="{y+2}" width="{w}" height="{h}" rx="{rx}" fill="{shadow}">`, not stroked; then `<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}">` filled and stroked (section 8.4) |
| a line's start | `<line x1="{Xs}" y1="{y}" x2="{Xl}" y2="{y}">`, `Xl` where the line stops; `<circle cx="{Xs}" cy="{y}" r="{w}">`, except where an ancestor line runs on |
| arrowhead | the line stops at `Xe`; `<polygon points="{Xe+3w},{y} {Xe},{y−1.5w} {Xe},{y+1.5w}">` |
| open arrowhead | the line stops at `Xe`; the same `<polygon>` with `fill="none"`, stroked in the line's `stroke` with width `w/2` and no dash |
| end circle | the line stops at `Xe`; `<circle cx="{Xe}" cy="{y}" r="{w}">` |
| diamond | the line stops at `Xe − 1.5w`; `<polygon points="{Xe−1.5w},{y} {Xe},{y−1.2w} {Xe+1.5w},{y} {Xe},{y+1.2w}" fill="none">` stroked in the line's `stroke` with width `w/2` and no dash |
| three chevrons | an open end (section 6.6): the line stops at `Xr`; three `<polyline points="{p1} {p2} {p3}" fill="none">`, the inner one, the middle one, then the outer one, each through its three points in the order section 6.6 lists them, stroked in the line's `stroke` with width `w/2` and no dash |
| two chevrons | an ancestor line running on (section 8.3): the line stops at `Xr` (to the right) or starts at `Xa` (to the left); two `<polyline points="{p1} {p2} {p3}" fill="none">`, inner one first, each through its three points in the order section 8.3 lists them, stroked as three chevrons are |
| wedge | `<polygon points="{X},{yt} {x1},{y1} {x2},{y2}">`, `(X, yt)` its tip and `(x1, y1)`, `(x2, y2)` the corners of its base in the order section 6.6 gives them |
| map | `<polygon points="{Xs},{yc−d/2} {Xe},{yc−d/2} {Xe},{yc+d/2} {Xs},{yc+d/2}" fill="none">` stroked |
| region | `<path d="{brace}">` |
| jump origin | `<path d="M{P0}C{C1} {C2} {Bh}">`, the shaft; `<polygon>` arrowhead `{P3} {Bh − 2w × n} {Bh + 2w × n}`, `n = (−uy, ux)` (section 6.6) |
| flow marker | `<line x1="{x}" y1="{yf}" x2="{x}" y2="{y2}">` (section 6.4) |
| boundary | `<line x1="{X}" y1="{y−k}" x2="{X}" y2="{y+k}">` (section 6.6) |
| cross-section line | for each of its lines (section 6.6: up to two in a card, one on each side of its gap, and a groupstamp's up to two in a frame), `<line x1="{X}" y1="{y1}" x2="{X}" y2="{y2}">`, from `(X, y1)` to `(X, y2)`, `y1` the smaller ordinate, the upper line first |
| alignment anchor | `<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">`, from the point on the first timestamp's line to the point on the second's (section 8.7) |
| elision | its gap, `<rect x="{x(a)}" y="{yt}" width="{x(b) − x(a)}" height="{yb − yt}">`, filled and not stroked, written only when its `fill` is not `none`; then its continuations, `<line x1="{x(a)}" y1="{y}" x2="{x(b)}" y2="{y}">` each, in the order of its rows (section 8.5) |
| ellipsis | `<circle cx="{xm − 6}" cy="{ym}" r="2">`, `<circle cx="{xm}" cy="{ym}" r="2">`, `<circle cx="{xm + 6}" cy="{ym}" r="2">`, filled and not stroked (section 6.6) |
| name, label | `<text x="{x}" y="{baseline}" text-anchor="{a}" font-size="{s}">`, `a` `start` for names and flow-marker labels, `middle` for the centred labels |

The **stroke attributes** are `stroke`, `stroke-width` and, unless it is
`none`, `stroke-dasharray`. A path carries `fill="none"` and a line no
`fill`; both carry the stroke attributes; a circle, a polygon
and a text carry `fill`, and the open arrowhead, the diamond and the map's
outline, the stroked polygons, also the stroke attributes (the map's dash
included); a polyline carries `fill="none"` and the stroke attributes; a
group frame, a card and an ancestor card carry `fill` and the stroke
attributes, a card's shadow and an elision's gap `fill` alone. A line's descriptors are, in this order, its `<line>`,
its start circle or left chevrons, and its end or right chevrons. Every
descriptor of an element, a card's shadow included, carries the element's
`opacity`, written when it is not 1. An
element without text is written self-closing (`<line …/>`); a text is written `<text …>{text}</text>`. Attributes are
written in this order, except the background's, which follow its template
and then `opacity`: `data-id`, `data-facet`, `data-part`, the template's geometric attributes
(`x`, `y`, `width`, `height`, `x1` to `y2`, `cx`, `cy`, `r`, `points`, `d`)
in the order shown, `rx`, `text-anchor`,
`font-size`, `fill`, `stroke`, `stroke-width`, `stroke-dasharray`,
`opacity`.

**The brace** from `X1` to `X2`, arms at `Yb`, tip at `(Xm, Ya)` (section
6.6): with `Ym = (Yb + Ya) / 2` and `k = |Ya − Yb| / 2`, the path is `M X1
Yb Q X1 Ym X1+k Ym L Xm−k Ym Q Xm Ym Xm Ya Q Xm Ym Xm+k Ym L X2−k Ym Q X2 Ym
X2 Yb`. A brace cut at gaps (section 6.6, Elisions) writes each of its
two straight parts as the pieces the cuts leave, from the left: the part
from `X1 + k` to `Xm − k` with the cuts `[c1, c1']`, …, `[cj, cj']`
becomes `L c1 Ym M c1' Ym L c2 Ym … M cj' Ym L Xm−k Ym`, every `L` to the
point the pen stands at left out, so that each `M` starts a piece after a
cut; the part from `Xm + k` to `X2 − k` alike. Path data is an upper-case
command letter followed by its coordinates, numbers separated by one
space, no space before a command letter (`M80 16L74 14`).

### 7.3 SVG profile

Every number either writer writes, each number of a `stroke-dasharray`
included, is formatted by one rule: take the exact value of the double,
round it to the nearest multiple of 1/10000, ties to the even multiple;
write it in decimal without exponent, without a leading `+`, with its
integer part (`0` when zero) and, when not an integer, a point and its
fractional digits without trailing zeros. A value that rounds to zero is
`0`, never `-0`.

The output is UTF-8, one element per line, no indentation, a final newline:

```
<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}" font-family="DejaVu Sans, Noto Music" text-rendering="geometricPrecision" style="font-kerning:none;font-variant-ligatures:none">
<g transform="translate({X} {Y}) scale({z})">
...
</g>
</svg>
```

with one `<g>` per drawing, `(X, Y)` its position on the page, and
` scale({z})` left out when `z` is 1. The `font-family` list names Noto
Music after DejaVu Sans, so that a renderer draws the code points of
section 5.1 that DejaVu Sans does not map in Noto Music. `text-rendering="geometricPrecision"`
keeps a renderer from hinting small text, which would move its glyphs off
the advance widths the layout measured. In text, `&`, `<` and `>` are written
`&amp;`, `&lt;` and `&gt;`; in attribute values, so are they, and `"` as
`&quot;`.

### 7.4 TikZ profile

Coordinates are bare numbers in points, y upwards: an SVG ordinate `y` of a
drawing of height `H` becomes `H − y`. With `standalone` (the default) the
output is a complete LuaLaTeX document:

```
\documentclass{standalone}
\usepackage{fontspec}
\directlua{luaotfload.add_fallback("music", {"[{font directory}/NotoMusic-Regular.ttf]:mode=node;"})}
\setsansfont{DejaVuSans.ttf}[Path={font directory}/,Kerning=Off,Ligatures={TeXOff,NoCommon},RawFeature={fallback=music}]
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}[x=1pt,y=1pt,miter limit=4,font=\sffamily]
\definecolor{ts00CC00}{HTML}{00CC00}
...
\end{tikzpicture}
\end{document}
```

`{font directory}` is a writer option, `.` by default, the directory that
holds both font files. Noto Music is a luaotfload fallback of the sans
font, so that the code points of section 5.1 that DejaVu Sans does not
map are drawn in it. Without
`standalone`, the output is the `tikzpicture` environment alone. Each
colour used is defined once, right after `\begin{tikzpicture}`, as
`\definecolor{ts<RRGGBB>}{HTML}{<RRGGBB>}`, sorted by its digits. Each
drawing is a `scope` shifted to the TikZ position of its block's bottom-left
corner, `({px},{PH − py − H × z})` for the page position `(px, py)` of
section 7.1 (`[shift={(…,…)}]`, with `,scale={z},transform shape` when `z`
is not 1).

Every descriptor of section 7.2 becomes one command, its attributes mapped
one to one:

| SVG | TikZ |
|---|---|
| `fill="#RRGGBB"` | `fill=tsRRGGBB` (`fill="none"`: no option) |
| `stroke="#RRGGBB"` | `draw=tsRRGGBB` (`stroke="none"`: no option) |
| `stroke-width="{v}"` | `line width={v}pt` |
| `stroke-dasharray="{a} {b} …"` | `dash pattern=on {a}pt off {b}pt …` (an odd list repeated once) |
| `opacity="{o}"` | `opacity={o}` |
| `rx="{r}"` | `rounded corners={r}pt` |
| `font-size="{s}"` | `font=\sffamily\fontsize{s}{h(s)}\selectfont` (TikZ's `font` key replaces the picture's font, so the family is restated) |

| Descriptor | Command |
|---|---|
| rect | `\path[{options}] ({x},{H − y − h}) rectangle ({x + w},{H − y});`, the background with `x = y = 0`, `w = W`, `h = H` |
| line | `\path[{options}] ({x1},{y1}) -- ({x2},{y2});` |
| circle | `\path[{options}] ({cx},{cy}) circle[radius={r}];` |
| polygon | `\path[{options}] ({p1}) -- ({p2}) -- … -- cycle;` |
| polyline | `\path[{options}] ({p1}) -- ({p2}) -- ({p3});` |
| path | `\path[{options}] ({P0}) .. controls ({C1}) and ({C2}) .. ({P3});`, a brace's quadratic `Q C P` from the current point `P0` written as the cubic with controls `P0 + 2/3 × (C − P0)` and `P + 2/3 × (C − P)`, computed as section 3.3 states (the factor `2/3` formed first), an `L P` as `-- ({P})`, an `M P` after the first as `({P})`, a move |
| text | `\node[anchor={base west|base},inner sep=0,{options}] at ({x},{baseline}) {{text}};` with `text=tsRRGGBB` for the fill |

An elision's descriptors take these commands as every other rect, line,
circle and text does: its gap a `rect` with the `fill` option alone, its
continuations `line`s, the dots of its ellipsis `circle`s with the
`fill` option, `\path[fill=ts000000] (…,…) circle[radius=2];`, and its
labels `text`s anchored `base`.

Options are written in the order of the attributes of section 7.2. In text,
`\` becomes `\textbackslash{}`, `~` becomes `\textasciitilde{}`, `^`
becomes `\textasciicircum{}`, each of `# $ % & _ { }` is preceded by
`\`, and a space at the start or end of a text or after another space is
written `\ `, so that TeX keeps it.

## 8. The block: frames and cards

Every manifest is an alignment bundle and is drawn as one **block**,
whatever it holds: a manifest of one root as a block holding that root as
an ungrouped root, a manifest of one group as a block holding that group's
frame, and every other manifest alike. The block opens with the
manifest's title (section 5.3), which an anonymous bundle, with neither a
`name` nor an `id`, does not have.
Every timeline drawn as a root (a member or an ungrouped root) is drawn as
sections 3 to 6 draw a root, in a **card**: an ungrouped root in one card
of its own, a member in one card in the frame of each group that has it as
a member. The block's **items** are
its frames and its ungrouped roots' cards; each lies at its own place
(section 8.6) and has its own graphical length `L`. The member drawings of
one item share its `L` and one start `x0`, so that the members of a group
by definition start and end at the same points. The **shared end** is
`x0 + L`, found
from `x0` and `L` alone and never from a length: a member or ungrouped
root of unknown length is drawn with its reach at the shared end (section
3.4), and its line runs on past it into its three chevrons (section 6.6).

### 8.1 What is drawn

- **Groups.** A block draws the manifest's groups in canonical order (by ID), and
  then every **ungrouped root**, a root of `timelines` that no group names
  as a member and that contains no member, in canonical order (by ID). A
  root that contains a member is no ungrouped root: it is drawn as an
  ancestor line of that member and, unless a rule hides it, whole in an
  ancestor card behind the member's frame (section 8.8). This is the
  block's **drawing order**; an arrangement takes the items in its own
  order instead (section 8.6).
- **Frames.** Each group is a **frame**, a `frame` element: a rounded
  rectangle holding the group's title and then its members' cards, one
  under the other, in the group's display order: the entry of
  `graphical.order` under the group's ID, or `members` when `order` has no
  entry for it. An ungrouped root has no frame.
- **Cards.** A **card** is a `card` element, a raised rounded rectangle
  around one member drawing of a timeline `M` (in the tree below, a card
  holds nothing). An ungrouped root `M` lies in one card; a member `M`
  lies in one card in the frame of each group that has it as a member,
  every card of `M` addressed `{"id": M, "part": ["card"]}` (section 2.2).
  A timeline that several groups have
  as a member is so drawn once in each of their frames, each drawing laid
  out with its own frame's length and scale and its own card's spacing,
  margin and size (section 8.6), and its elements carry the same addresses in
  every one. The card is the same whether it lies on the grey block or in a
  frame.
- **Member drawings.** A **member drawing** is the drawing of sections 3
  to 6 of one timeline `M` taken as the root: its line is a `timeline`
  element, its markers band draws its named timestamps, and positions are
  on `M`'s axis (section 3.1). A
  member that is a child timeline in `timelines` is still a `timeline`
  element in its member drawing, so rules selecting `child` do not
  reach its line, and it ends with the diamond, or with three chevrons
  when its length is `null` (section 6.6). Such a member's drawing also has
  the faded lines of its ancestors, in an **ancestor band** on each side of
  its line where one of them lies (section 8.3): by default all of them
  below it.
- **Titles.** A group's title, a `name` element with the address `{"id":
  G, "part": ["name"]}`, opens its frame. The manifest's title, a `name`
  element with the address `{"part": ["name"]}`, opens the block.

The tree of section 2.1: the `block` holds the manifest's title, the
ancestor cards and the `timeline` elements of their roots, the frames,
and the cards and `timeline` elements of the ungrouped roots; a frame holds
its title, its members' cards and `timeline` elements and the gaps of its
group elisions (section 8.9), each gap holding its ellipsis and its
labels; a card or ancestor card holds nothing; a member's `timeline`
element holds what a root holds (section 2.1) and its ancestor lines; an
ancestor line holds its `name`, the
wedges of the named timestamps' coordinates on it, primary and secondary,
and their labels, each label beside its wedge and not held by it, and the
cross-section lines of its timeline's named timestamps drawn there
(section 8.3).
`within` names a timeline at any depth of `timelines`; a timeline's depth
(section 2.5) is its depth in its root's tree, the roots being 1.

### 8.2 Horizontal

The block has **one horizontal layout**, which every item applies at its own
place: the name column, the line's start and the right margin are found
once over all items, so that items of one length are equally wide wherever
they lie, unless a frame's group elisions shorten it (below). Each quantity below is computed in **item coordinates**, measured
from the item's left edge, before the item's scale (section 8.6); `Li` is
the graphical length of item `i`.

The **name column** starts at `n = Q + K` when the block holds a frame and at
`n = K` otherwise: inside the cards, at the same offset for every card of
every item. Every row name of every member drawing, ancestor names
included, is drawn at `x = n`. `N` is the width of the widest name of any
member drawing of the block (section 6.7), and `G' = 8` when any such name is
drawn and 0 otherwise; titles are not names of rows and count for neither.
The **start** is

    s0 = max(n + N + G', max over i, j of (n + wj / 2 − (Li × uj + vj)), max over a of (n + N + G' + 8 × wa))

where `j` runs over every centred label of every member drawing of item
`i` (section 6.7, with the member's own proportions and the item's length
`Li`, and `vj` its carry, 0 unless its wedge is turned) and `a` over every ancestor line of the block that runs on to the left
(section 8.3), `wa` its stroke width. So no label crosses the name column's
left edge, and no chevron crosses the gap after the names. Every member
drawing of item `i` starts at `s0`, its shared end is `s0 + Li`, and the
`x0` of sections 3 and 8.3 is `s0` in item coordinates.

A frame with group elisions is drawn shorter by `DGi`, the sum of the
shrinks of its gaps (section 8.9), summed from the left, and 0 for every
other item: its members' shared end is `s0 + (Li − DGi)` and their
**drawn length** `Li − DGi`, the `L'` of section 8.9. The **right margin**
`Mr` is the largest of `e − (s0 + (Li − DGi))` over every member drawing
of every item `i` that draws anything, `e` its right edge (section 6.7);
it may be negative. Item `i`'s right edge is `Ri =
max(s0 + (Li − DGi) + Mr, t)`, `t` the right edge of its group's title, which
starts at `Q` (none for an ungrouped root's card), or `Ri = max(s0, t)`
when no member drawing of the block draws anything; section 8.6 widens it on
request. A block of one item so has the right edge of its widest content. A card
inside a frame spans `Q` to `Ri + K`, so that every card of a frame ends
at one x, unless its own request widens it (section 8.6); a frame spans `0`
to `Ri + K + Q`; an ungrouped root's card spans `0` to `Ri + K + Q` when
the block holds a frame and to `Ri + K` otherwise, so that the frames and
ungrouped cards of one length end at one x where no frame has group
elisions, and a frame with group elisions ends `DGi` further left, unless
its title holds it wider.

### 8.3 Ancestor lines

For a member `M` that is a child timeline, let `A1, …, Ak` be its
ancestors from its root `A1` down to its parent `Ak`. Each `Aj` has an
**ancestor line**, an `ancestor` element with `Aj`'s address, drawn at
`M`'s scale and clipped to `M`. On `M`'s axis `Aj` starts at `ts = −(o(j+1)
+ … + o(k) + oM)`, the negated sum of the offsets from `Aj` down to `M`
(`oM` being `M`'s own offset in `Ak`, `o(j+1)` that of `A(j+1)` in `Aj`), and
ends at `te = ts + ` `Aj`'s `length`, combined as section 3.1 combines
values, when that length is a value; `λ` is `M`'s length, or its reach when
its length is `null` (section 3.4). `ts ≤ 0`, and `te ≥ λ` wherever every
length involved is a value, since a child lies within its parent. With `w`
the line's stroke width and `y` its ordinate:

- **On the left**, when `ts < 0` (compared exactly) the line **runs on**:
  it starts at `Xa = x0 − 4w` and ends in a double chevron pointing left,
  the inner one through `(Xa − w, y − 1.5w)`, `(Xa − 2.5w, y)` and `(Xa −
  w, y + 1.5w)`, the outer one the same `1.5w` further left, through `(Xa −
  2.5w, y − 1.5w)`, `(Xa − 4w, y)` and `(Xa − 2.5w, y + 1.5w)`, so its tip
  is at `x0 − 8w`. When `ts = 0` the line starts at `x0` with its circle.
- **On the right**, when `Aj`'s length or `M`'s length is `null`, or `te
  > λ`, the line runs on to `Xr = x0 + L' + 4w`, `L'` the drawn length
  of `M`'s frame (section 8.2; `L` without group elisions),
  and ends in a double chevron pointing right, mirrored: the inner one
  through `(Xr + w, y − 1.5w)`, `(Xr + 2.5w, y)` and `(Xr + w, y + 1.5w)`,
  the outer one `1.5w` further right, through `(Xr + 2.5w, y − 1.5w)`, `(Xr
  + 4w, y)` and `(Xr + 2.5w, y + 1.5w)`, its tip at `Xr + 4w`, `8w` past
  `x0 + L'` (section 6.7): where
  either end is not known, the drawing does not claim that the ancestor
  ends with the member. A running-on ancestor line has two chevrons on
  either side, also when its own length or `M`'s is `null`: the three
  chevrons of an open end (section 6.6) mark a line's own unknown length
  and are never drawn on an ancestor line. When `te =
  λ` the line ends at `x0 + L'` with `Aj`'s own end (section 6.6): the
  arrowhead, open arrowhead or circle of a top-level timeline, the diamond
  of a child. When `te < λ`, which a manifest allows only where a timeline
  between `Aj` and `M` has a length of `null`, the line ends at `x(te)`
  (section 3.2), inside the member's span, with `Aj`'s own end.
- **Named timestamps.** A named timestamp of `Aj` whose position on `M`'s
  axis, its `coordinate` plus `ts`, combined as section 3.1 combines
  values, is at least 0 and at most `λ`, compared exactly, is drawn on the
  ancestor line as on a timeline's line, by what its `display` lists
  (section 2), at `X`, `x` of that position (section 3.2). Its wedge lies
  on the line's **outer side**, the side away from the member's line
  (below), outside every band, a wedge of section 6.6 on that side with
  its tip on the line's edge (`y − w / 2` above the line, `y + w / 2`
  below it), turned by its `rotation`, so that, not rotated, its base lies
  13 further out. Its stack, its name, its ID and its coordinate in
  `Aj`'s unit (section 6.4, Markers), is placed by one first fit, the
  timestamps in canonical order, into tiers beyond the room of the wedges
  on the same side, as the markers band places its stacks (section 6.4,
  Markers), each stack as many lines high as it has labels: of a stack in
  tier `k`, label `i` lies on line `n = m1 + … + m(k − 1) + i`, `mq` the
  height of tier `q` in lines, which starts `w / 2 + 13 + 2 + (n − 1) ×
  h(9)` out from the ancestor line, the label's baseline beyond that start
  (section 6.6). That is its unturned place: a turned wedge carries its
  stack as section 6.6 does (Labels of named timestamps), with `c` 0, and
  the tiers and the band's room stay those of the unturned places. Its cross-section line crosses the whole
  of `M`'s card, cut by its gap (section 6.6, Cross-section lines). The
  defaults draw its wedge, its labels and its cross-section line at
  opacity 1 on the faded line, as for a timestamp named on `M` (section
  4). After
  `Aj`'s own timestamps come the secondary coordinates on `Aj` of the
  timestamps whose cross-section lines cross its line in `M`'s card
  (section 2), in the canonical order of their timestamps, each drawn so,
  by its wedge and its labels, where it is displayed (the defaults hide
  it, and fade it with the line where a rule shows it, section 4). A timestamp of `Aj` at a position outside `M`'s span is
  not drawn in `M`'s card; it is drawn where `Aj` is drawn whole, in an
  ancestor card (section 8.8) or a card of its own.
- **Nothing else** of `Aj` is drawn: no maps, regions, flow control,
  boundaries or other descendants, no mark of `M`'s start or end, and no
  named timestamp of another timeline but by the coordinates its lines
  cross on `Aj`. `M`'s start and end on `Aj` are the secondary
  coordinates there of `M`'s `origin` and `length` where `M` names them
  as groupstamps (section 2), as an editor does when a child joins a
  group: their lines cross the ancestor lines, and their wedges and
  coordinate labels, hidden and turned −45 by the defaults (section 4),
  are shown by a rule selecting `coordinates: secondary`, by their
  addresses or not. Its name is drawn in the name column on its row
  (section 6.6, names).

**Sides.** Each ancestor line lies on one side of the member's line: the
side opposite to where `Aj`'s own band order (section 6.4, completed
against its inherited order) puts its children band, below `M`'s line
when `children` comes before `line` in that order and above it when
`children` comes after `line`. `Aj`'s children band holds the way down to
`M`, so the member's card shows `Aj` on the side of `M` where `Aj`'s own
drawing has it, and in the same order as the ancestor card does (section
8.8). In the default band order (section 4) every ancestor line lies below
the member. An ancestor line's outer side is up when it lies above `M`'s
line and down when it lies below it.

The ancestor lines of one side lie in that side's **ancestor band**, the
outermost band of the side, beyond the root's bands and outside every
band order; it is not an element and has no address. A member drawing
has an ancestor band on each side where a displayed ancestor line lies:
none, one or two. A band starts at the larger of `p0 / 2` and `S` beyond
the larger of the outer edge `E` of its side (section 6.4: `Ea` above,
`Eb` below, of the root's own bands) and half the stroke width `wm` of the
member's line, `wm` being 0 when that line is not displayed (section 6.5):
at `max(p0 / 2, max(E, wm / 2) + S)`, so that the band keeps the gap `S`
from the outermost band of its side and from the line's stroke, as a band
at level 1 or −1 does.
It holds one row per ancestor on its side, the deeper ancestor (the larger
`j`) nearer the member's line: of the ancestors on one side, the one
nearest `M` in the tree lies nearest and the one nearest the root
outermost. An ancestor line that is not
displayed has no row (section 2.4 states what it hides). Row `r` of a band,
counted outwards from the member's line, has the row pitch `qr` of its
name's font size (`p` of section 6.2), an inner half `ir = qr / 2`
towards the member's line and an outer half `or` on its line's outer side,
the larger of `qr / 2` and the reach of its wedges, `w / 2 + 13`, or `w /
2 + 13 + 2 + T × h(9)` (left to right) when the labels of its named
timestamps fill tiers of `T ≥ 1` lines together (9 standing for its
labels' largest font size), or `qr / 2` alone when no wedge or label of a
named timestamp is drawn on it. The line of row 1 lies at `c0 + i1` from
the member's line, `c0` the start of the band, and that of row `r + 1` at
the distance `Δr` beyond row `r`: `Δr = or + i(r + 1)`, except on the
side where the ancestor line of the root `R = A1` lies while an ancestor
card of `R` is drawn behind `M`'s frame (section 8.8), whether it is
aligned to `M` or to an earlier member below `R`, so in every member
card of that frame below `R`, where `Δr =
max(dr, or + i(r + 1))`, `dr` the distance between the lines of the two
rows' ancestors in `R`'s drawing laid out alone (section 8.8, step 1),
the larger of their ordinates less the smaller. For `dr`, `R`'s drawing
alone is laid out on the ancestor card's elided axis (section 8.9): on the
gaps carried into it, which draw no label but move what lies right of
them, and, as its mode chooses, on the pieces of its stored card elisions
or on the elisions it derives, so that it is the ancestor card's own
layout, and `dr` counts the label stacks of every elision the card draws
in its markers bands (section 6.4, Markers), stored and derived alike;
for a root drawn once behind a row (section 8.8, Drawn once) it is the
layout of its once card. The coordinates of the derived elisions depend
on the card's proportion, and the proportion on the height of `M`'s frame
(section 8.9), which it reads as laid out before any of its rows align on
a card behind, every `Δr` there `or + i(r + 1)`, so that `dr` depends on
nothing of `M`'s card as drawn.
So, in the card of the member the ancestor card is aligned to, which lies
aligned on `R`'s line (section 8.8), every ancestor row on that side lies
at exactly its height on the card behind (in a later member's card the
rows keep those distances from one another), with one exception: where
the wedges and labels of its own named timestamps need more room, that
row and the rows beyond it lie further out.
The
band is `i1 + Δ1 + … + Δ(C − 1) + oC` wide for `C` rows, summed in that
order, and its outer edge is `c0` plus that width.

### 8.4 Vertical

Every member drawing has its own height `Hm`, its content height `Hc` of
section 6.5 with its ancestor bands included in `Ea` and `Eb` and its card margin
`V` above and below; its card is `Hm` high, and the drawing's top is the
card's top. The card padding `K` is
horizontal only: above and below, the member drawing's own padding `P`
(section 6.5) lies inside the card. A card's shadow lies 2 to the
right of and 2 below the card.

A frame or card spanning `x = a` to `b` and `y = c` to `d` is written with
`x` `a`, `y` `c`, `width` `b − a` and `height` `d − c`, its right and bottom
edges being `b` and `d`: a card's `b` is the end of its span (section 8.2)
and its `d` its top plus `Hm`, a frame's `d` its top plus its height below.
A card's shadow is written at `x + 2` and `y + 2` with the card's `width`
and `height`, and its right and bottom edges are `b + 2` and `d + 2`.

- **A frame** is laid out from its top: the title's baseline lies at `top +
  Q + a(s)`, `s` the title's font size, so the title sits at the top of a
  slot `h(s)` high, unlike a row name, which is centred on its row. The
  frame's margin `Vf` (section 8.6) lies after the title's gap: the first
  card starts at `top + Q + h(s) + 4 + Vf` (at `top + Q + Vf` when the
  title is not displayed), and each further one the frame's spacing `Sf`
  below the previous one's bottom (section 8.6); the margin lies again
  after the last card, before the bottom padding `Q`. The frame is `Q +
  h(s) + 4 + Vf + Hm1 + Sf + Hm2 + … + Sf + Hmn + Vf + Q` high, summed in
  that order, without `h(s) + 4` when the title is not displayed, and
  without either `Vf` when it holds no card.
- **The block.** The manifest's title, when there is one, lies at the block's
  top left corner: drawn at `x = Xl + P`, with its baseline at `Yt + P +
  a(s)`, both in place coordinates (below), so in the block at `P` and `P +
  a(s)` wherever the block grows. Its slot, `h(s)` high, is the top border
  of the items: no item rises into it, and an item placed higher pushes it
  up with the block's top. Every frame and ungrouped card lies at its place
  (section 8.6).

Within a member drawing, the root's line lies at the drawing's top plus the
`y_root` of section 6.5, computed in that order; every other ordinate
follows from that line as section 3.3 states.

The block grows in every direction to hold its content, with the padding `P`
on every side. Every position is first computed in **place coordinates**,
measured from the place origin, as sections 6 and 8 write it (an item's
positions through its item coordinates and its place, section 8.6). In place
coordinates the content runs from `Xl`, the smaller of 0 and the smallest
left edge of any frame, card or displayed ancestor card (section 8.8)
minus `P`, to `Xr`, `P` plus the largest right edge of any of these, a
shadow included, or of the
manifest's displayed title, whose right edge is `Xl + P` plus its width;
and from `Yt`, the smaller of 0 and the smallest top of any of these
minus `Pt`, to `Yb`, `P` plus the larger of the largest bottom edge of any
of these, a shadow included, plus the block's margin `Vb`
(section 8.6), and of the manifest's displayed title, whose slot
ends at `Yt + P + h(s)` (`Xr = 2P + K` and `Yb = P` when the block holds none
of these). `Pt` is `P + h(s) + F + Vb` when the manifest's title is displayed,
`s` its font size, and `P + Vb` otherwise, so that an item never rises above
`F + Vb` below the title's slot. The block's margin so lies, as its padding
does, between the title's gap (or the top padding) and the highest item,
and between the lowest item and the bottom padding.
The content is `Wb = Xr − Xl` wide and `Hb = Yb − Yt` high, the sum with
`P` taken first: `Wb = (P + max(b + 2, …)) − Xl`, and `Hb` likewise. The place origin lies at
`(Ox, Oy) = (0 − Xl, 0 − Yt)` in the block, so an origin of 0 is `+0`; it is
`(0, 0)` unless an item reaches left of or above the padding. Each finished
position is then drawn in the block with `Ox` added to its x and `Oy` to its
y, the last sum of each: the manifest's title is drawn at `(Xl + P) + Ox`
with its baseline at `((Yt + P) + a(s)) + Oy`. A frame's or card's width and height are
taken in item coordinates (section 8.6); the block's `Wb` and `Hb` in place
coordinates, as above. A frame or card that is not displayed is not drawn but keeps
its place, since member drawings lie in it: the layout, `n`, `Wb` and `Hb`
are as when it is displayed, except that a hidden card's shadow is not
drawn and does not count. The
block is `W = max(Wb, width)` wide and `H = max(Hb, height)` high (`W = Wb`
when `width` is `null`, `H = Hb` when `height` is); the
background is a rectangle filling it with corner radius `rx`.

### 8.5 Descriptors

A manifest becomes element descriptors in this order: the background; the
manifest's title; then each displayed ancestor card in the order of
section 8.8, the descriptors of its member drawing and its gaps; then,
for each frame in drawing order, the frame, its
title, and for each of its members in display order, the member's card and
the descriptors of its member drawing; then, for each ungrouped root, its
card, the descriptors of its member drawing and its gaps. A card's gaps
(section 8.9), its own and those carried into it, follow its member
drawing, gap by gap from the left, each gap's descriptors in this order:
its rectangle where it is filled, its continuations, its ellipsis, then
its labels, name, ID and coordinate. A gap's rows, which its
continuations follow, are taken in their own order, which
is not that of their descriptors (section 7.2, maps before lines): first
the ancestor lines, from `A1` to `Ak` (section 8.3), then the lines of
the member drawing in the traversal order of their timelines (section
6.1), each line followed by the maps of its conversion maps band in the
order that band places them (section 6.4); a row is taken only where it
is drawn and crosses the gap (section 6.6, Elisions). The descriptors of a member
drawing follow section 7.2, with its ancestor lines, from `A1` to `Ak`,
each with its chevrons, just before its root; the wedges of the named
timestamps' coordinates on them, from `A1` to `Ak`, each ancestor's in
the order of its first fit (section 8.3), first among its wedges; their
names, from `A1` to `Ak`, first among its names; the labels of those
coordinates, from `A1` to `Ak`, each ancestor's in the same order, first
among its marker labels; and the cross-section lines of their
timelines' named timestamps, from `A1` to `Ak`, each ancestor's in
canonical order, first among its cross-section lines. After the last item
come the gaps of the frames' group elisions, frame by frame in drawing
order and in each frame from the left, each written as a card's gap is,
its rows taken card by card from the top; then the
groupstamps' lines, timestamp by timestamp in the order of `timestamps`
and frame by frame in the order of `groups`, each frame's lines from the
top down (section 6.6); then the alignment anchors and then their labels (section 8.7), so that they
lie over everything else. In an arranged block (section 8.6) the item
order, or for `horizontal` the row, takes the place of drawing order
throughout: the frames and the ungrouped roots' cards are written in
that one order, a frame or a card each where it stands in it, and the
gaps of the frames follow it too. In a block arranged `horizontal` the
ancestor cards written are its once cards (section 8.8, Drawn once), in
the order of their roots from the top, each followed by its gaps from
the left as a card's gaps are, a seam writing nothing; a line of the
member drawing cut by gaps is written as its pieces from the left, in the
line's place.
A title is a text descriptor of section 7.2, anchored at `start`;
its `content` and `max-width` apply as section 6.6 applies them to a row's
name.

### 8.6 Places

Every item of the block, a group's frame or an ungrouped root's card, lies at
a **place**: its left edge `x` and its top `y`, measured from the place
origin in canvas units, its graphical length `length`, its **scale**
`scale` (positive), its `spacing` (finite, ≥ 0), its `margin` (finite,
≥ 0), and its requested size `width` and `height` (positive, or left out for its
content's own size). `places` (section 1) states any of
these members for the item whose ID is its key, and a group's entry states
in its `cards`, under a member's ID `M`, the card of `M` in that group's
frame, `places[G].cards[M]`. A key naming no item, such as a member's ID
at the top of `places`, or a key of `cards` that is not a member of its
group, is not used, and so is any of a value's members that this section
gives no use for (a member's card uses only `width`, `height`,
`spacing` and `margin`, and an ungrouped root's card no `cards`). A member that is not stated takes its default:

- `length`: the placement's `length`;
- `scale`: 1;
- `spacing`: 8 for a frame, 4 for a card;
- `margin`: 0;
- `width` and `height`: none, the content's own size;
- `x`: `P`;
- `y`: for the first item in drawing order (section 8.5), `P + h(s) + F +
  Vb` below the manifest's title, `s` its font size and `Vb` the block's
  margin, or `P + Vb` when there is no title or it is not displayed; for
  every further item, the block's spacing
  below the largest bottom edge `d` of the items before it. That edge is
  the frame's or card's `d` of section 8.4, its place `y` plus `scale` times its
  height, summed in place coordinates before any shift; a card's shadow does not count, and
  an item that a `height` request makes higher ends at its requested
  bottom.

So with `places` empty the items lie one under the other, as an editor
first shows them.

**Arrangements.** An arrangement (section 1) takes the block's items in
its own **item order**: the items its `order` names, each at its first
mention, an ID that names no item passed over, and then every item it
leaves out, in drawing order (section 8.1). An arranged item takes no
`x` and no `y` from `places`, which keeps them for when the block is
not arranged; every other member of its place applies as above.

- `vertical`: every item lies at its default `x` and `y`, as above, the
  items taken in the item order instead of drawing order: the first at
  the first item's default `y`, each further one the block's spacing
  below the largest bottom edge of the items before it.
- `horizontal`: the items stand in one row, in the **row** of section
  8.8 (Drawn once), which keeps the item order wherever the stretches of
  the groups on their roots leave it free. The first item lies at `x =
  P`, each further one at the previous item's `x` plus its width plus
  the **row gap** `max(S, 48)`, `S` the block's spacing, summed in that
  order; an item's width is its drawn width, `scale` times its `b − a`
  (section 8.4), a card's shadow not counted. Their tops, and the once
  cards of the roots they hang on, are those of section 8.8; where no
  group hangs on a root every item's top is the first item's default
  `y`. When the rules of section 8.8 refuse the row, the block is drawn
  as `vertical`, in the item order, and the drawing states why.

An item is laid out by sections 8.2 and 8.4 with its own `length` as `L`,
in item coordinates, its left edge and top at 0, every sum written as those
sections write it. Its frame or card is wider when `width` asks for more:
for a frame, `Ri` is taken as the larger of its `Ri` and `width − K − Q`,
so its cards still end at one x inside it; for an ungrouped root's card,
as the larger of its `Ri` and `width − K − Q` when the block holds a frame
and `width − K` otherwise. It is higher when `height` asks for more: the
frame or card is the larger of its own height and `height` high, every card
and member drawing keeping its top. `width` and `height` are in item
coordinates, before the scale.

The **card spacing** `S` of a member drawing (sections 6.2 to 6.5 and
8.3) is its card's `spacing`: the entry `places[G].cards[M]` for a
member `M` drawn in the frame of group `G` (section 1), or the entry under
the ungrouped root's ID. A group's entry states its frame's
spacing `Sf`, the gap between its member cards (section 8.4); the
placement's `spacing` is the gap between the block's items at their default
`y`. The **card margin** `V` of a member drawing (section 6.5) is its
card's `margin`, from the same entry; a group's entry states its frame's
margin `Vf`, and the placement's `margin` is the block's margin `Vb`
(section 8.4). A container's margin is drawn inside its padding, above its
contents and below them (section 1), and changes no width. Each
container's spacing and margin space only its own contents: none
multiplies another, and a frame's padding `Q`, its title's slot, the block's
padding `P` and the card's padding `P` above and below do not change with
any of them.

A **member's card** may request a size, a spacing and a margin of its own:
the entry `places[G].cards[M]`, for the card of member `M` in the frame
of group `G`, states its `width` and `height`, in item coordinates, before
`G`'s scale, its `spacing` and its `margin`, and nothing else of it is used; the cards
of `M` in other groups' frames take their own entries. The card is then the larger of its own width and `width` wide,
spanning `Q` to `max(Ri + K, Q + width)`, and the larger of `Hm` and
`height` high; its member drawing keeps its place at the card's top left,
so the request adds room to its right and below. The frame holding it
grows with it: the frame spans `0` to the largest right edge of its cards
plus `Q`, and its height sums its cards' heights.

The item is then drawn at its place: every position of its elements, its
frame's or card's included, is the item-coordinate position `(px, py)`
taken to `(x + scale × px, y + scale × py)`, and every length of them, a
width or height, a radius (a frame's or card's corner radius `rx`
included), a stroke width, every dash of a dash array, a font size, a
text's `max-width` and the size of every marker, is multiplied by `scale`;
a frame's or card's `width` and `height` are `scale` times its
item-coordinate `b − a` and `d − c`; a card's shadow is written at its
card's written `x` and `y` plus `scale × 2`, with the card's `width` and
`height`, its right and bottom edges for the block being `x + scale × (b +
2)` and `y + scale × (d + 2)`; with
`scale` 1 that is `(x + px, y + py)` and every length unchanged. So an item's
scale scales everything in it, proportions kept, text included, about its
top left corner, as the block's scale `z` scales the block (section 1). Its
edges for the block (section 8.4) and for the default `y` above are its
drawn edges, after the scale.

The members of a group are never placed: they lie one under the other in
their frame, in the group's display order (section 8.1), and only that order
changes; their cards may only request a size, a spacing and a margin. The bands of every timeline likewise lie outwards from its own line
in its band order (section 6.4).

### 8.7 Alignment anchors

Every alignment anchor of a named MatchStamp (section 2) is placed
between the cross-section lines of its two timestamps, in the block's
coordinates, after every item is drawn at its place (section 8.6) with
`Ox` and `Oy` added (section 8.4). A timestamp has one **cross-section
segment** in every member drawing in a frame or card, an ancestor card's
excepted, that draws its timeline's line, or for
a segment without a line its segment line's line, or draws its timeline
as an ancestor line and the timestamp on it (section 8.3): the vertical segment
from `(X, yt)` to `(X, yb)` of section 6.6 as drawn in the block, from
the card's upper border to its lower border, its gap included. A
segment counts whether or not its cross-section line is displayed. An
anchor one of whose timestamps has no cross-section segment draws
nothing.

Between a segment `A` from `(Xa, a1)` to `(Xa, a2)` and a segment `B` from
`(Xb, b1)` to `(Xb, b2)`, `a1 ≤ a2` and `b1 ≤ b2`, the line is the
shortest one, with `lo = max(a1, b1)` and `hi = min(a2, b2)`:

- when `lo ≤ hi`, the two overlap vertically, as on cards side by side,
  and the line is horizontal at their middle `ym = (lo + hi) / 2`, from
  `(Xa, ym)` to `(Xb, ym)`;
- when `a2 < b1`, `A` lies above `B`, and the line runs from `(Xa, a2)`
  to `(Xb, b1)`;
- otherwise from `(Xa, a1)` to `(Xb, b2)`.

`A` is a segment of the first timestamp of the anchor's `timestamps` and
`B` of the second. When a timestamp has several segments, its timeline
being drawn in several cards, the line is the shortest over every pair of
one segment of each: the one whose `dx × dx + dy × dy` is smallest, `dx`
and `dy` the differences of its end points' coordinates, in binary64; of
equal ones, the first in the descriptor order of the first timestamp's
segments, then of the second's (section 8.5). A line of no length is not
drawn. The line is straight, crosses whatever cards lie between its ends,
takes no room and widens nothing.

The `alignment_anchor` element, with the address `{"id": A}` of its
anchor's ID `A`, is the `<line>` of section 7.2 from the first point to
the second. When its anchor's `display` lists `name`, the MatchStamp's
`name` is drawn as a `label` element with the address `{"id": A, "part":
["name"]}`, centred on the line's midpoint `(xm, ym)`, `xm = (x1 + x2) /
2` and `ym = (y1 + y2) / 2` in binary64, with its baseline at `ym + (a(s)
− d(s)) / 2`, `s` its font size, vertically centred as a row's name is
(section 6.6); it is placed so whether or not the line is displayed or
has a length, and it takes no room either.

The lines are written after the last item's descriptors, MatchStamp by
MatchStamp in the order of `matchstamps` and each MatchStamp's anchors in
the order of its `alignment_anchors`, and then their labels in the same
order (section 8.5).

### 8.8 Ancestor cards

A member that is a child timeline is drawn with the faded lines of its
ancestors (section 8.3). Its root may also be drawn whole, behind the
member's frame, in an **ancestor card**: an `ancestor_card` element with
the root's card address `{"id": R, "part": ["card"]}` (section 2.2),
belonging to the root `R`, drawn as a card is (section 7.2), with the
member drawing of `R` in it. Every ancestor between `R` and the member is
a row of that drawing at its true proportions, and `R`'s own line
continues the member's faded ancestor line of `R` beyond the frame's
borders. In the tree of section 2.1 the block holds the ancestor card and
the `timeline` element of `R` drawn in it, and the ancestor card holds
nothing, so nothing of its drawing lies inside an `ancestor` element and
none of it is faded. The defaults show every ancestor card (section 4);
a rule of a later layer hides them as it hides any element, all of them
with

```json
{"select": {"element": "ancestor_card"}, "set": {"display": "none"}}
```

and those of one root `R` with `"addresses": [{"id": "#R", "part":
["card"]}]` added to the selector.

**Which.** The groups are taken in drawing order (section 8.1), and the
members of each group `G` in its display order. Each member `M` that is a
child timeline gives one ancestor card of its root `R` (`A1` of section
8.3) behind `G`'s frame, aligned to `M`, unless an earlier member of `G`
lies below the same `R`: a root has at most one ancestor card behind a
frame, aligned to the first member below it in display order, and a later
member below it adds none, whether or not that card is drawn. A root with
members below it in the frames of several groups has one ancestor card
behind each of them, each laid out with its own frame's length and drawn
at its own frame's place and scale; several roots with members in one
frame have one ancestor card each. A root that is a member of another
group keeps its card in that group's frame too.

**When it is drawn.** An ancestor card is drawn when it is displayed
(section 2.4), the line of `R` in its member drawing (below) is displayed,
and the line it is aligned to is drawn in `M`'s card in `G`'s frame:
`R`'s ancestor line there, or `M`'s own line where that ancestor line is
not displayed. Otherwise nothing of it is drawn, it takes no room and the
block does not grow for it.

**Geometry.** Let `ts` be the start of `R` on `M`'s axis (section 8.3,
with `Aj = A1 = R`), `λ` `M`'s length, or its reach when its length is
`null`, and `λR` `R`'s length, or its reach when its length is `null`
(section 3.4); `te = ts + λR`, combined as section 3.1 combines values.
`us = ts / λ` and `ue = te / λ` are proportions formed as section 3.2
forms them. With `x0` the start of the member drawings of `G`'s frame and
`L` its graphical length (section 8.2), in item coordinates and binary64:

    xs = x0 + L × us
    xe = x0 + L × ue
    LA = xe − xs

1. **Alone.** `R` is laid out by sections 3 to 6, 8.2 and 8.4 as the one
   ungrouped root of a block that holds nothing else and has no title: at
   the graphical length `LA`, with the card spacing 4 and the card margin
   0 whatever `places` states, the name column at `n = K`, its gaps
   (section 8.9) on its elided axis (section 3.2), and its own
   `N`, `G'`, start `s0'` and right margin, so that its card spans `0` to
   `Ri' + K` and is `Hm` high, its top at 0. `R` is a root, so its drawing
   has no ancestor band. `yR` is the ordinate of `R`'s line in it.
2. **Placed.** `yA` is the ordinate, in `G`'s item coordinates, of `R`'s
   ancestor line in `M`'s card, or of `M`'s line where that ancestor line
   is not displayed. Every position `(px, py)` of the layout of 1, its
   card's included, becomes `(px + dx, py + dy)` with `dx = (xs + DL) −
   s0'` and `dy = yA − yR`, `DL` the sum of the shrinks of the gaps left
   of `M`'s span (section 8.9), summed from the left, and 0 without gaps,
   less `OL`. The card's axis has two **seams** (section 3.2), at the start
   `−ts` and at the end `−ts + λ` of `M`'s span on `R`: the first `OL =
   x0` wide, the room of `G`'s frame from its left edge, at 0 in item
   coordinates, to its member drawings, and the second `OR = Fw − (x0 +
   L')` wide, the room from the members' drawn end to the frame's right
   edge, `Fw` the width of the frame as drawn and `L'` its members' drawn
   length (section 8.9), in binary64. A position at either seam lies on
   the side of `M`'s span, so an element at the span's start or end lies
   under the frame. So `R`'s line starts at `xs + DL`, `M`'s span on it
   lies over `M`'s line, its gaps carried from the frame (section 8.9)
   over the frame's gaps, everything left of the span, the card's names
   included, lies left of the frame, everything right of it lies right of
   the frame, `OR` further right and `DG` further left with the frame's
   shared end, `R`'s line runs whole across both seams under the frame,
   and it lies at `yA`.
   The ancestor card is then drawn at `G`'s place and scale, as every
   element of the frame (section 8.6).
3. **No room.** No item's default `y` (section 8.6), no quantity of the
   block's one horizontal layout (section 8.2) and no size of `G`'s frame
   or cards counts it. The block grows to hold it as it holds a card: its
   left edge, top, right and bottom edges, its shadow included, count
   among the edges of section 8.4, so the block may grow to the left or
   upwards, moving the place origin within it while every item keeps its
   place.
4. **Order.** Ancestor cards are written before every frame and card,
   in the order of **Which** (section 8.5), so that every item and every
   alignment anchor lies over them, and a later ancestor card over an
   earlier one where they meet.
5. **Nothing else.** `places` states nothing of it: a key
   `places[G].cards[R]` names no member of `G` and is not used (section
   8.6). It gives no cross-section segment to an alignment anchor (section
   8.7), and no groupstamp line is drawn for it, since those lines span
   the member cards of a frame alone (section 6.6, Cross-section lines);
   the named timestamps of its drawing draw their own cross-section lines
   in it, across the whole ancestor card, as in every member drawing.

The fixture `group_parent_both` drawn with the defaults shows the root
`piece` (16 quarters) behind the frame of its child `middle` (8 quarters
at offset 4), so `us = −0.5` and `ue = 1.5` and `LA = 800` at the
length 400; its proportion is 1 (section 8.9), so it derives no elision,
and the card is written at `x` 8 and `y` 36.207, 1013.0391 wide
and 63.3789 high, `piece`'s line runs from 60.3354 to 1004.0391 at
`y` 85.1836, on the faded ancestor line of `piece`, which the default band
order puts below `middle`'s line in `middle`'s card, and the block grows
to the left, its place origin at `(252.3354, 0)`. In the card `middle`'s
row lies above `piece`'s line, at 51.207, 4 lower than `middle`'s own line
at 47.207: between `middle`'s markers band and the line of `piece`,
`middle`'s card holds the card spacing `S` and the inner half 7 of the
row of `piece`, and `piece`'s drawing only the start 7 of its children
band.
In `group_parents_mixed`, three roots lie behind one frame, each aligned
to the first of its members in the display order; `sonata` is drawn
whole, `session` and `page` with the gaps they derive (section 8.9).

**Drawn once.** In a block arranged `horizontal` (section 8.6) every
root that groups hang on is drawn once, behind the row of items, and
each group stands where its stretch lies on that root.

*Words.* A group **hangs on** a root `R` when it has an ancestor card of
`R` (Which, above): when one of its members lies below `R`, a child, a
grandchild or deeper. The member that card is aligned to, the group's
first member below `R` in its display order, is the group's **anchor**
on `R`, and the anchor's **stretch** runs on `R`'s axis from the
anchor's start (section 3.1) to its end (section 3.4), so that a member
of unknown length stretches to its drawn end. A member that is the root
itself anchors nothing; an ungrouped root's card hangs on nothing.

*The rules.*

1. The items stand side by side in one row, and each root that a group
   hangs on is drawn once behind them, the roots one under another.
2. Along every root, the stretches of the groups hanging on it follow
   the row from left to right without overlapping; touching is allowed.
3. In every group, the anchors lie in the same top-to-bottom order as
   their roots.

*The orders.* Rule 2 gives, for each root in canonical order (by ID) and
each two groups hanging on it, taken in the item order (section 8.6),
"`G` before `H`" when `G`'s stretch ends at or before the start of
`H`'s, and "`H` before `G`" when `H`'s ends at or before the start of
`G`'s, compared exactly: nothing when both hold (two stretches without
length at one position), and an **overlap** when neither does. Rule 3
gives, for each group in canonical order and each two of its anchors
next to each other in its display order, "the upper anchor's root above
the lower's". The **row** is the item order sorted by the first
relation: repeatedly the first item of the item order left that no item
left must precede. The **roots**, every root some group hangs on, are
sorted likewise by the second relation, starting from canonical order.
So the row keeps the item order wherever the stretches leave it free,
and roots no group orders lie in canonical order.

*Refusal.* When no row and no order of the roots satisfy rules 2 and 3
for all groups at once, `horizontal` is refused, and the first of these
names the conflict:

- **An overlap**, on the first root in canonical order where two
  stretches overlap, of the first such pair in the item order: its groups
  are the pair, its root that root, and its reason `"G" and "H" overlap
  on "R" (a–b)`, the stretch both cover, from the later start to the
  earlier end, written as an elision's coordinate label writes its
  elided coordinates (section 5.3): `"Theme A" and "Theme B" overlap on
  "Score" (8–16 ♩)`.
- **The row in a cycle**: of the items the sort leaves, every item that
  must precede none of the others still left is set aside, again and
  again until none is. From the first item of the item order still left,
  step along the first relation, each time to the item earliest in the
  item order among those still left, until an item repeats. The cycle so
  found, begun at its item earliest in the item order, gives the
  groups, the root of each step (of two roots giving one step, the
  earlier in canonical order) and the reason, for two groups `on "R" "G"
  comes first, on "S" "H"`, and for more `on "R" "G" comes before "H", on
  "S" "H" before "J", on "T" "J" before "G"`.
- **The roots in a cycle**, found and begun likewise among the roots in
  canonical order, every root that must lie above none of the others
  still left set aside first: the groups of its steps (of two groups
  giving one step, the earlier in canonical order), its roots and the
  reason `"G" holds "R" above "S", "H" holds "S" above "R"`.

Each group and root is named in a reason by its title or name (section
5.3), in double quotes. A refused arrangement is drawn as `vertical`
(section 8.6), and the drawing states the conflict (section 1); nothing
else refuses one.

*Vertically.* In place coordinates, with `S` the block's spacing: the
**once card** of a root `R` is its ancestor card behind the first group
of the row hanging on it, `G1`, aligned to `G1`'s anchor `M1`, laid out
alone as step 1 above lays it out, at that card's graphical length `LA`,
and drawn at `G1`'s scale `s1`; `yR` is the ordinate of `R`'s line in
that layout and `Hm` its height, so the card reaches `aR = s1 × yR`
above its line and `bR = s1 × (Hm − yR)` below it. For the anchor `M` of
a group `G` on `R`, `yM` is the ordinate in `G`'s item coordinates of
`R`'s ancestor line in `M`'s card, laid out as section 8.4 lays out the
frame, or of `M`'s line where that ancestor line is not displayed (the
`yA` of step 2 above).

1. **Lines.** The line of the first root lies at `y1 = 0`, and that of
   each further root `R'` at the largest of `(y + bR) + S + aR'`, `R`
   the root above it and `y` its line, so that the cards of two roots
   never overlap, and, for each group whose anchor `M'` on `R'` comes
   after an anchor `M` on a root `Q` in its display order, `M` the one
   just before `M'`, `yQ + sG × (yM' − yM)`, `yQ` the line of `Q` and
   `sG` the group's scale, so that the group can lie on both roots.
2. **Padding.** In each such group the card of each anchor `M'` after
   the first lies `δ = (yR' − yQ) / sG − (yM' − yM)` lower than section
   8.4 lays it, the gap above it grown by `δ`, `yR'` and `yQ` the lines
   of the two anchors' roots: every card after it moves with it, no card
   changes its height, and the frame is the sum of its `δ` higher. So
   every anchor lies on its root's line, up to the rounding of binary64.
3. **Tops.** A group hanging on roots has its top at `yR − sG × yM` of
   its first anchor `M`, on the root `R`, and a once card at `yR − aR`.
   The **row's top** `T0` is the smallest of these tops; every item that
   hangs on nothing has its top at `T0`. Then every ordinate moves by
   `Y − T0`, `Y` the first item's default `y` (section 8.6), so that the
   highest frame or once card lies where the first item would.
4. **Left.** Where a once card's left edge (below) lies left of `P`, the
   row is packed again from `x = P + δx` instead of `P`, `δx` that edge's
   distance from `P` for the leftmost such edge, and every abscissa below
   follows from the new places.

*The axis of a once card.* `R`'s line in its once card is drawn in
**runs**, each at the scale of one anchor's frame. The run of an anchor
`M` of a group `G`, at the place `(xG, yG)` with the scale `sG`, `M`
starting at `a` on `R`'s axis and `λ` its length, or its reach when its
length is `null`, gives a position `t` of `R`'s axis the x

    XM(t) = xG + sG × (x0 + (L × u − D))

with `u` the proportion of `t − a`, `M`'s own position, of `λ` (section
3.2), `x0` and `L` the start and the graphical length of `G`'s member
drawings and `D` the sum of the shrinks of the gaps of `G`'s frame with
`q ≤ u` (section 3.2): where `R`'s ancestor line in `M`'s card puts `t`,
continued to either side of `M`'s span. Between two anchors next to each
other along `R`, `A`, whose stretch ends at `b`, and `B`, whose stretch
starts at `a`, with `c` the middle of the room right of `A`'s frame, the
mean of that frame's right edge and the left edge of the next item of
the row, in binary64:

- `s` is the largest whole unit of `R`'s axis (section 8.9, Derived
  elisions, step 1) no less than `b` with `XA(s) ≤ c − 16`, or `b`
  where none is, and `e` the smallest whole unit no more than `a` with
  `XB(e) ≥ c + 16`, or `a` where none is;
- when `s < e`, a **gap** leaves out `R` from `s` to `e`: `R` lies on
  `A`'s run up to `s` and on `B`'s from `e`, and the gap is drawn from
  `XA(s)` to `XB(e)`, at least the standard gap of 32 wide;
- otherwise a **seam** (section 3.2) lies at `m = max(b, min(a, s))`:
  `R` lies on `A`'s run up to `m` and on `B`'s from `m`, the seam
  `XB(m) − XA(m)` wide. It leaves out nothing: it marks where the scale
  changes where the room holds no whole unit.

So every change of scale lies in a gap or at a seam. A gap is an elision
the card derives on `R` (section 8.9), with the address `{"id": R,
"part": ["elision"]}` (section 2.2) and the elided coordinates `s` and
`e`, drawn as every gap is (section 6.6), its `display` the card's
`elision-display`. A seam is none, and a row crossing it is drawn across
it whole (section 3.2). An element at `m` lies on `B`'s run when it
belongs to a timeline that starts at `m` (its line's start, its named
timestamps there with their wedges, labels and cross-section lines) or
is the start of a region or a jump target at `m`, and on `A`'s run
otherwise; a line ending at `m` ends there on `A`'s run, one starting
there starts on `B`'s.

Left of the first anchor's stretch `R` lies on that anchor's run and
right of the last one's on the last anchor's run, and there the card
draws the gaps its elision mode gives (section 8.9): left of the first
stretch those that `R`'s ancestor card behind the first anchor's group
draws left of its protected span, right of the last those that the one
behind the last anchor's group draws right of its own, with their
natural and drawn widths taken from those cards and multiplied by their
groups' scales; the proportion `r` of their derived elisions is the
least of the proportions of `R`'s ancestor cards behind every group
hanging on it (section 8.9), each as section 8.9 gives it. As in an ancestor card (step 2), a seam lies at the start of the
first stretch, `s1 × OL` wide with the `OL` of the first anchor's frame,
and one at the end of the last stretch, `sN × OR` wide with the `OR` of
the last anchor's frame, `N` the last anchor and `sN` its group's scale;
a position at either lies on its stretch's side. A position `t` left of
the first stretch in no gap lies at `XM(t) + s1 × (DL − OL)`, `DL` the
sum of the shrinks of those gaps that start at or after `t`, and one
right of the last stretch at `XN(t) − sN × (DR − OR)`, `DR` the sum of
those that end at or before `t`, each sum taken from the left. Between
the first stretch and the last the arrangement's gaps leave out what
they leave out whatever the mode, and stored card elisions lying there are kept and
not drawn; the gaps of each anchor's frame lie in its run, carried as
section 8.9 carries them.

*Drawing a once card.* The once card draws the layout of step 1 with
every ordinate `y` of it at `(yR − aR) + s1 × y`, and every abscissa by
the position it belongs to: an element at a position `t` of `R`'s axis,
or at an offset `o` from it (a wedge's corners, a label centred on it, a
mark at a line's end), lies at `X(t) + s1 × o`, `X` the run the position
lies on; a line or row crossing a gap is drawn in pieces (section 6.6,
Elisions), and one crossing a seam whole across it (section 3.2); the names, the chevrons and everything else of
the layout left of `R`'s start `s0'` keep their distance from it at
`X(start) + s1 × (x − s0')`, so the card's left edge lies at `X(start) −
s1 × s0'`; and the card's right edge lies at `X(end) + s1 × ((Ri' + K) −
xe')`, `xe'` the x of `R`'s end in the layout of step 1. Every length of
it, a stroke width, a font size, a mark, is `s1` times its length there.
The rows are those of step 1, as gaps never move a row (section 3.2).
The once card is the ancestor card of `R` behind `G1`; `R`'s ancestor
cards behind the other groups hanging on it draw nothing and take no
room. A once card that is not displayed draws nothing but keeps its
place in 1 to 4, so that hiding it moves nothing.

*Worked example.* The fixture `bundle_arranged_roots` arranged
`horizontal` in the order `page`, `group_3`, `group_1`, `group_2`
(`bundle__bundle_arranged_roots__horizontal`): the score `score` (48
quarters) holds the touching movements `exposition`, `development` and
`recapitulation` (16 quarters at 0, 16 and 32), the session `session`
(130.0 seconds) the takes `take_a` (30.0 at 0.0) and `take_b` (30.0 at
100.0); "Exposition" (`group_1`) lists `exposition` and `take_a`,
"Development" (`group_2`) `development` and the root `notes`,
"Recapitulation" (`group_3`) `recapitulation`, the root `annotations`
and `take_b`, and `page` is ungrouped. On `score` Exposition comes
before Development before Recapitulation, on `session` Exposition before
Recapitulation, and `page` hangs on nothing, so the row is `page`,
`group_1`, `group_2`, `group_3`, and `score` lies above `session`.
Every item is 567.39013671875 wide, so with the row gap 48 they lie at
`x` 8, 623.39013671875, 1238.7802734375 and 1854.17041015625.

- Vertically: `score`'s once card, laid out at `LA` = 1200, has its line
  at 82.953125 of 97.35546875, `session`'s, at `LA` = 1733.3333333333333,
  at 48.9765625 of 83.953125. The ancestor line of `score` lies at
  77.18359375 in each frame, that of `session` at 152.5625 in Exposition
  and 209.94140625 in Recapitulation, so `session`'s line lies at the
  largest of 71.37890625, 75.37890625 and 132.7578125, the last set by
  Recapitulation, and Exposition's card of `take_a` is padded by
  57.37890625. The tops are −77.18359375 for the three frames,
  −82.953125 and 83.78125 for the once cards; `T0` = −82.953125, and
  everything moves by 28.8046875 + 82.953125 = 111.7578125: the frames
  lie at 34.57421875, `page` at 28.8046875, `score`'s line at
  111.7578125 and `session`'s at 244.515625.
- Along `score`, 25 canvas units per quarter in each frame: between
  Exposition and Development `c` = 1214.7802734375, `s` = 17 and `e` =
  11, so a seam at 16, from 1150.7802734375 to 1366.17041015625;
  between Development and Recapitulation a seam at 32, from
  1766.17041015625 to 1981.560546875. `score`'s line, the one row
  crossing them, runs across each whole; the movements' lines and the
  timestamps at their starts lie on the right runs, those at their ends
  on the left ones.
- Along `session`, 400 / 30.0 canvas units per second: between Exposition
  and Recapitulation, through the room right of Exposition, `s` = 33.0
  (`XA(33.0)` = 1190.7802734375 ≤ 1198.7802734375) and `e` = 44.0
  (`XB(44.0)` = 1234.8938802083335 ≥ 1230.7802734375): a gap leaving out
  33.0 to 44.0, 44.113606770833485 wide, its ellipsis centred at x
  1212.8370768229167, and `session`'s line runs on behind
  Development to `take_b`.
- The once cards span 591.36669921875 to 2398.839599609375 (`score`,
  `s0'` = 159.41357421875) and 652.52734375 to 2398.560546875
  (`session`, `s0'` = 98.2529296875). The block is 2429.560546875 wide,
  the right edge of Recapitulation's frame plus `P`, and 289.4921875
  high, the bottom of `session`'s once card with its shadow plus `P`.

### 8.9 Elisions

**Where.** Elisions (section 2) are drawn where their timeline is drawn
whole. A **card elision**, one on a timeline that lies in no group, is
drawn in the cards that draw its root whole: the ungrouped root's card
and every ancestor card of that root (section 8.8); never in a member's
card, whose members convert linearly between their shared start and end
(README, "Groups and the `graphical` object"). A **group elision**, one
on a timeline that lies in a group, is drawn across the frame of each
group its timeline lies in, at one place in every member card of that
frame, and carried into the ancestor cards behind that frame (below); an
ancestor of a member lies in no group through it (section 2), so an
elision on the root of a member, or on an ancestor between, is a card
elision of that root. A root that is a member of one group and holds a
member of another lies wholly in the first, so all its elisions are
group elisions of that frame, and its ancestor cards behind other frames
have no card elision. An elision is drawn where its gap is displayed
(section 2.4); a group elision also only where its timeline's line is
drawn in the frame, as a groupstamp's lines across a frame are (section
6.6).

**Modes.** Which elisions a card draws is the card's **mode**, its
`elision-mode` (section 2.4), cascaded as every property is; every card
of a root `R`, its ungrouped card and its ancestor cards, carries the
address `{"id": R, "part": ["card"]}`, so one rule addressed to it sets
the mode of all of them, beside the `display` that hides them:

| `elision-mode` | What the card draws |
|---|---|
| `full` | no card elision, and no derived one |
| `proportional` | the elisions the card derives (Derived elisions, below), and no stored card elision |
| `custom` | the stored card elisions lying on `R` or on a descendant of `R`, and no derived one |
| `auto` (initial) | as `custom` where at least one stored card elision lies on `R` or a descendant, displayed or not, and as `proportional` otherwise |

Group elisions are never counted and never switched by a card's mode: an
ancestor card draws the gaps carried into it in every mode, so a group
elision neither turns `auto` into `custom` nor disappears under `full`;
a card that is not displayed draws nothing at all. An ungrouped root's
card has no protected span and derives nothing, so `proportional` draws
no gap there. `elision-proportion` and `elision-depths` act under
`proportional` alone, and `elision-display` is the `display` of every
elision the card derives (`none` an empty one), the order and repetition
of its words meaning nothing. A frame reads `elision-mode` for its group
elisions as an ungrouped root's card reads it for its own: `full` draws
none, neither across the frame nor carried, `auto` and `custom` draw
them, and `proportional` draws none; it reads none of the other three. So
the rules

```json
{"select": {"addresses": [{"id": "#clt_1", "part": ["card"]}]}, "set": {"elision-mode": "full"}}
{"select": {"addresses": [{"id": "#clt_1", "part": ["card"]}]}, "set": {"elision-mode": "proportional", "elision-proportion": 0.05, "elision-depths": "1", "elision-display": "ellipsis name coordinate"}}
{"select": {"addresses": [{"id": "#group_1"}]}, "set": {"elision-mode": "full"}}
```

draw the root `clt_1` whole in every card, its stored elisions kept and
not drawn; derive its elisions at the proportion 0.05 on its own row
alone, each drawing its ellipsis and its name and coordinate labels; and
draw the frame of `group_1` without its group elisions.

**Pieces.** A card elision's stretch on the root's axis runs from its
`start` to its `end`, each carried to the root as section 3.1 carries a
coordinate, and no further than the root's start and end (section 3.4).
In an ancestor card aligned to a member `M`, the **protected span**, `M`'s
span on the root's axis from `−ts` to `−ts + λ` (section 8.8), is never
elided by a card elision. The card elisions a card draws are taken in
canonical order (section 2), and each draws as its **pieces** what of its
stretch lies outside the protected span and outside every piece taken
before it: none, one or several stretches, each with the elision's
address, `name`, `width` and `display`. So an elision overlapping the
protected span is clipped to what lies outside it, drawn as up to two
pieces; of two elisions that overlap, the earlier is drawn whole and the
later clipped; a piece without length is not drawn; and nothing is
refused. A stored elision the card does not draw, its gap not displayed
or its timeline not drawn there (Where, above), has no pieces and takes
no stretch from the elisions after it. Each piece of a stored elision
is one gap of section 3.2 over the whole piece, its elided coordinates
the piece's ends on the elision's timeline's own axis.

**Widths.** A gap of a stored elision over `[a, b]` has the natural width
`n` of section 3.2 and the drawn width set by its elision's `width`
(section 2): when it is absent, the standard gap 32; for `{"ratio": q}`,
`q × n`; for `{"span": v}`, `L × uv`, `uv = v / λR` a proportion formed
as section 3.2 forms one and `λR` the root's length, or its reach when its
length is `null`; for `{"canvas": c}`, `c`; each in binary64, and `n`
instead when it is larger than `n`. `L` is the card's graphical length,
`LA` in an ancestor card (section 8.8), and a width is in the card's item
coordinates, so its item's `scale` scales it. Each piece of a clipped
elision takes its width so, as if it were the whole elision.

**Group elisions.** Let `M` be the member of a group `G` that is the
elision's timeline `T` or has it as a descendant, and `λ` `M`'s length,
or its reach when its length is `null` (section 3.4). The elision's
`start` and `end`, carried to `M`'s axis as section 3.1 carries a
coordinate to a root, become the proportions `p` and `q` of `λ` (section
3.2), each clipped to `[0, 1]`: the elision's **stretch in the frame**.
The frame's group elisions are taken in canonical order, and each draws
as its pieces what of its stretch lies outside every piece taken before
it, one the frame does not draw (Where, above) taking no stretch; each
piece is one gap of the frame's elided axis (section 3.2), with the
natural width `n = L × q − L × p` and the drawn width set by its
elision's `width` as above, `{"span": v}` giving `L × uv` with `uv = v /
λ`, and `{"canvas": c}` `c` in the frame's item coordinates, so the
frame's `scale` scales it; `n` instead when it is larger. One stored
`width` thus sets the gap of every member card at once, and a timeline
lying in two groups has a gap in each frame, each by that frame's `L`
and `scale`. The frame is drawn shorter by `DG`, the sum of the shrinks
of its gaps (section 8.2), its members' drawn length `L' = L − DG`. A
gap runs across the frame's member cards, from the top of the topmost to
the bottom of the bottommost (section 6.6); every row of every member
card that crosses it stops and resumes there, and the gap draws one
ellipsis, centred on the member cards together, with its label stack
once, below that ellipsis (section 6.6), its room taken in the markers
band of the elision's own timeline `T` in its card in that frame
(section 6.4, Markers) and nowhere else. Its labels show the piece's ends on `T`'s
own axis: the elision's `start` and `end` where the piece is its whole
stretch, neither clipped to `[0, 1]` nor cut by an earlier piece; on any
other piece both ends are read on `T` at the piece's proportions, `p ×
λ` and `q × λ` on `M`'s axis (where `λ` is exact, the piece's exact
proportions, defined under Carried gaps below, and the products exact;
where `λ` is a float, the doubles `p` and `q` and the products in
binary64), less `T`'s start on `M`'s axis, combined as section 3.1
combines values, and written as section 5.2 writes a coordinate. The
gap's elided coordinates on a member, or on a timeline its card draws,
are the positions at the proportions `p` and `q` of that member's drawn
length, each the exact product of the piece's exact proportion (Carried
gaps, below) and that length, a float length taken at its exact binary
value, read on the timeline and written in its number type as a
groupstamp's coordinates are (section 2). They have no value where a
groupstamp's coordinate would have none: on a member of unknown length,
and on every member when `M`'s length is unknown; where a member has
none, no timeline of its card has one. They are listed by an application
and never drawn: card by card in the display order of the frame's
members, in each card its member, then the other timelines of the
member's tree the card draws, in traversal order (section 6.1), then the
ancestors whose lines the card draws, from the member's parent up to its
root. A timeline other than the member is listed only where its span,
its ends included, holds both positions, as a row crossing the gap does
(section 6.6), an ancestor of unknown length having no end. The gap is a
place of the drawing, not a coordinate, so nothing of it is faded. A
position in a frame's gap has no x (section 3.2): a groupstamp's lines
and wedges at such a position are not drawn, and at a gap's edge they
are.

**Carried gaps.** The ancestor card of `R` behind `G`, aligned to `M`
(section 8.8), keeps `M`'s span on `R` over `M`'s line, so it draws the
frame's gaps inside its protected span: each gap of the frame over `[p,
q]` becomes a gap of the card over `R`'s stretch from `−ts + p × λ` to
`−ts + q × λ`, with the frame's natural width `n` and drawn width `g`,
taken and never recomputed, so that the card's gaps lie over the frame's,
up to the rounding of binary64. Here `p` and `q` are the piece's
**exact proportions**: the exact quotients of the elision's `start` and
`end`, carried to `M`'s axis, and `λ`, each clipped to `[0, 1]` (a float
taken at its exact binary value), not the doubles that place the frame's
gap; where an earlier piece cut the elision's stretch, the cut end is
the earlier piece's exact end there, so that the carried gaps meet
exactly where the frame's gaps meet. On an exact axis of `R` the stretch
is exact, `−ts`, `p × λ` and their sum computed exactly, and on a float
axis it is combined as section 3.1 combines values, each exact operand
converted to the nearest double; only its x is rounded (section 3.2). A carried gap is drawn where the frame draws its gap, by the
frame's mode and display and not by the card's cascade, in every mode of
`R`; it is a further drawing of the frame's gap, carries its elision's
address and takes the values cascaded for the frame's gap, ellipsis
included, and it draws one ellipsis, centred on the ancestor card, and
no label. Card
elisions and derived ones are clipped around the protected span, so they
never meet a carried gap, and everything right of `M`'s span lies `OR`
further right and `DG` further left with the frame's shared end (section
8.8, step 2). Rows
are untouched: the card's ordinates are those of section 8.8.

**Derived elisions.** An ancestor card of a root `R` aligned to a member
`M` derives elisions where its mode is `proportional` and its proportion
`r` (below) is less than 1. Let `A1 = R, …, Ak` be `M`'s ancestors, `Ak`
its parent (section 8.3). **Depth** `j` holds `Aj` and, for `j` ≥ 2,
every other child of `A(j − 1)` the card draws (a displayed child,
section 2.4; a segment without a line of its own counts when it is
displayed); depth 1 holds `R` alone. The **chosen depths** are those of
`elision-depths`: all of `1 … k` for `auto`, otherwise the depths it
lists that are at most `k`. From the deepest chosen depth up, and within
a depth in canonical order (section 6.1), each stretch of a timeline's
span (from its start to its end, sections 3.1 and 3.4) that lies outside
the protected span, outside the spans of the timelines of the deeper
chosen depths and outside every piece found before becomes one **piece**
lying on that timeline, its ends on that timeline's own axis. A stretch
no chosen depth covers stays at full scale. So with `auto` `M`'s parent
and its siblings take what they cover of `R`, what they leave uncovered
falls to the next depth up and `R` takes the rest, and with `"1"` alone
`R` is elided once on each side of the protected span, its pieces taken
from `R`'s own span and their gaps cutting every row of the card that
crosses them, its children's rows included (section 6.6).

Each piece is drawn as **its middle left out**: a piece over `[a, b]`
of its timeline's own axis, `[aR, bR]` on the root's axis, with the
natural width `n` (section 3.2, with `LA`), is drawn `W = r × n` wide as a
visible start, a gap and a visible end. With `h = (W − min(32, W)) / 2`
and `k = n / (b − a)`, the canvas units per unit of the timeline at full
scale, the difference formed as section 3.1 forms one and the division
in binary64,

1. its elided coordinates are `start`, the larger of `a` and `⌊a + h /
   k⌋`, and `end`, the smaller of `b` and `⌈b − h / k⌉`, each sum
   combined as section 3.1 combines values and rounded **outwards to a
   whole unit** of the timeline, an integer, which every number type
   holds exactly: `int` as the integer, `float` as the double equal to
   it and `fraction` as `[n, 1]`;
2. the visible ends keep their natural widths, `e1` from `aR` to `start`
   and `e2` from `end` to `bR`, each on the root's axis (section 3.2),
   both 0 where `start = a` and `end = b`;
3. the gap over `[start, end]` is drawn `g = W − e1 − e2` wide, in
   binary64 left to right, so that the piece stays `W` wide up to the
   rounding of binary64.

The gap is that of a **derived elision** lying on the piece's timeline,
with the address of section 2.2, no `name` and no ID, the `display` that
`elision-display` gives, and the elided coordinates `start` and `end`,
which its `coordinate` label shows and which an application stores as
they are where it makes the derived elisions stored ones. A piece whose
`start` and `end` are its own ends is a gap whole.

**The proportion** `r` of an ancestor card is the number its
`elision-proportion` states, or, for `auto`, the largest at which (a)
the gaps' pieces together are no wider than `M`'s drawn line and (b)
with the view (section 1) centred on the frame at the zoom `zb`, the
elided card lies within the view. With, in `G`'s item coordinates:

| Symbol | Meaning |
|---|---|
| `VW`, `VH` | the `width` and `height` of the placement's `view` (section 1) |
| `sG` | `G`'s `scale` (section 8.6) |
| `L`, `L'`, `x0` | `G`'s graphical length, its members' drawn length (section 8.2; `L` without group elisions) and the start of its member drawings |
| `Fw`, `Fh` | the width and the height of `G`'s frame (sections 8.2, 8.4 and 8.6, its requests included) as laid out before the ancestor rows of its member cards align on the cards behind them, every `Δr` of section 8.3 `or + i(r + 1)`: so `Fw` is its width as drawn, and `Fh` does not depend on the rows the ancestor card's own elisions move; its centre `c = Fw / 2` |
| `σ` | `K + N' + G'` of `R` laid out as section 8.8, step 1 lays it out but without any gap, and so without the label stacks of its elisions (section 6.4, Markers), which can change its rows and so its names: its name column and the gap after it, `N'` the width of its widest name and `G'` 8 where it draws a name and 0 otherwise (section 8.2) |
| `EL`, `ER` | the stretches of `R` left and right of `M`, on `M`'s axis: `EL = −ts` and `ER = te − λ` (section 8.8), and `E = EL + ER`, each combined as section 3.1 combines values |

the zoom at which the group's frame fills four fifths of the view, capped
at 4, is `zG = min(4, 0.8 × VW / (sG × Fw), 0.8 × VH / (sG × Fh))`, the
constant factor `0.8` formed first (section 3.3); `Z` is the double
nearest 5/7, the legibility floor: a row of the default pitch 14 drawn at
`Z` lies 10 from the next, the fixed part of its pitch (section 6.2); and
`zb = min(zG, Z)`, so that a frame whose `zG` is below `Z` is not zoomed
out further. At `zb` the view shows `B = 0.8 × VW / ((2 × zb) × sG)` on
either side of `c`; the card's line reaches `dl = c + σ` left of `c` and `dr = (Fw +
8) − c` right of it before its gaps, since its seams (section 8.8, step
2) put what lies outside `M`'s span outside the frame's edges, at 0 and
`Fw`, the name column `σ` left of the one and the card padding `K`, 8,
right of the other. Then

    r = min(1, λ / E × (L' / L), (B − dl) / (L × uL), (B − dr) / (L × uR))

with `uL = EL / λ` and `uR = ER / λ`; `λ / E`, `uL` and `uR` are
proportions formed as section 3.2 forms one, `λ / E × (L' / L)` is that
proportion times the binary64 quotient `L' / L`, and everything else is
binary64 in the order written. The term of (a) is left out when `E` is 0,
the left term when `EL` is 0 or `B ≤ dl`, and the right term when `ER`
is 0 or `B ≤ dr`: a side with nothing to elide, or on which the root
cannot lie within the view whatever its gaps, sets no bound. Where the
term of (a) is the minimum, the drawn widths of the pieces sum to `L'`,
up to the rounding of binary64, and the elided line is `2L'` long. A
stated proportion sets `r` whatever (b) gives, so the drawing then does
not depend on the view.

**Worked examples**, at the default view `1280 × 720` and the length 400,
so `0.8 × VW = 1024`, `0.8 × VH = 576`, `zb = Z = 0.7142857142857143` and
`B = 716.8` wherever `zG` exceeds `Z`, which it does in each:

- The fixture `group_elided_inside` (`auto`): the root `piece` of 64
  quarters, its movements `first` (32 at 0) and `second` (32 at 32), and
  the member `excerpt` of 8 at 8 in `first`, so `ts` = −8, `EL` = 8, `ER`
  = 48, `E` = 56 and `LA` = 3200, 50 canvas units per quarter. Depth 2
  holds `first` and `second` and gives the pieces `first` 0–8, `first`
  16–32 and `second` 0–32; depth 1 is left nothing. `r` =
  0.14285714285714285, set by (a): the frame, 543.70361328125 wide and
  171.5625 high, gives `zG` = 1.8833790598156273 and `c` =
  271.851806640625, and with `x0` = 103.70361328125 and `σ` =
  87.4248046875 (`N'` the width of the row name `First, Second`), `dl` =
  359.276611328125 and `dr` = 279.851806640625, so (b)'s terms are
  0.8938084716796874 on the left and 0.1820617472330729 on the right.
  The natural widths are 400, 800 and
  1600, `W` 57.14285714285714, 114.28571428571428 and
  228.57142857142856, and `h / k` 0.2514285714285714, 0.8228571428571427
  and 1.9657142857142855: the first two round outwards to their own ends,
  so each is a gap whole, 57.14285714285714 and 114.28571428571428 wide;
  the third leaves out `second` 1–31 (labelled `1–31 ♩`), keeping 50 of
  `second` at full scale on each side, its gap 128.57142857142856 wide.
  `DL` = 239.1535295758929, the shrink 342.8571428571429 of the one gap
  left of the frame less `OL` = 103.70361328125.
  The gaps over `first` cut the rows of `piece` and `first`, that over
  `second` the rows of `piece` and `second`, each gap with one ellipsis.
- The fixture `bundle_elided_layerit`, the card of the suite `clt_1`
  (1616 quarters) behind the frame of `clt_8` "Clair de Lune mm. 1–6"
  (27 at 0 in `clt_4` "Clair de Lune", 324 at 668): `x0` =
  182.8037109375, the block's start (`n + N + G' + 8w`, `N` the width
  134.8037109375 of `Passepied mm. 153–156`), `LA` = 23940.74074074074,
  `E` = 1589 and `r` = 0.016991818753933293, set by (a): the frame of
  `clt_8` is `x0 + L + 8w + K + Q` = 622.8037109375 wide, its right edge the
  outer chevron tip of `clt_1`'s ancestor line, and 171.5625 high, so `zG`
  = 1.6441777433512452 and `c` = 311.40185546875; `σ` = 175.8974609375,
  `N'` = 159.8974609375 being the width of the movements' row name cut to
  `Prelude, Menuet, Clair de L…` (section 6.6, Names), so `dl` =
  487.29931640625, `dr` = 319.40185546875 and (b)'s terms are
  0.023190563087691803 on the left and 0.029125271179000402 on the right.
  Depth 2 gives
  the pieces Prelude 0–356, Menuet 0–312, Clair de Lune 27–324 and
  Passepied 0–624, drawn `W` = 89.61611076148522, 78.53996224040277,
  74.7640025173065 and 157.07992448080557 wide. Their gaps leave out
  Prelude 1–355 (`h / k` = 1.944543738200126), Menuet 1–311, Clair de
  Lune 28–323 and Passepied 4–620 (`h / k` = 4.221447451227188), so each
  movement keeps its start and end at full scale: the visible ends are
  14.814814814814815 and 14.814814814814781 of Prelude,
  14.814814814814781 and 14.814814814813872 of Menuet,
  14.81481481481569 and 14.814814814813872 of Clair de Lune, and
  59.259259259259125 on either side of Passepied, the gaps
  59.986481131855626, 48.91033261077412, 45.13437288767693 and
  38.561405962287324 wide.
- The fixture `group_elided_members`: the frame of `group_1` (`L` 400)
  draws two group elisions. `elision_1` on the member `excerpt` (16
  quarters) from 2 to 8 has the stretch `p` = 0.125 to `q` = 0.5, the
  natural width 150 and the standard gap 32; `elision_2` on `phrase`, at
  12 in the member `voice` (24 quarters), from 2 to 6 is 14 to 18 on
  `voice`, `p` = 0.5833333333333334 to `q` = 0.75, the natural width
  66.66666666666666 and, with `{"ratio": 0.5}`, the gap
  33.33333333333333. `DG` = 151.33333333333331 and `L'` =
  248.66666666666669. Each gap cuts every row of the three cards that
  crosses it, the ancestor line of `piece` in the card of `excerpt`
  included, and the line of `sketch`, whose open end counts as its whole
  drawn length; the
  stack of `elision_1`, `Development` and `2–8 ♩`, takes its room in the
  markers band of `excerpt` and stands under the gap's ellipsis;
  `elision_2`, which states no `display`, draws its ellipsis and its name
  label `Phrase`, whose room the markers band of `phrase` takes. On `voice`
  the elided coordinates are 3 to 12 and 14 to 18, on `sketch`, of
  unknown length, none have a value. The groupstamp at 15 of `voice`
  lies in the second gap and is not drawn; that at 21 is drawn, faded
  over `sketch` (section 6.6). The ancestor card of `piece` (48
  quarters; `ts` = −16, `LA` = 1200, 25 canvas units per quarter) carries
  the gaps over `piece` 18 to 24 and 76/3 to 28 (`16 + 7/12 × 16` and `16
  + 3/4 × 16`, exact on its fraction axis), 32 and 33.33333333333333 wide
  of 150 and 66.66666666666666. Under `auto`
  it derives elisions at `r` = 0.5 × (248.66666666666669 / 400) =
  0.31083333333333335, set by (a), the frame being drawn 383.2599283854167
  wide (`DG` narrower) and 259.9921875 high: `zG` = 2.2154511854322547, `c`
  = 191.62996419270834, `x0` = 90.09326171875, `σ` = 58.09326171875, `dl`
  = 249.72322591145834 and `dr` = 199.62996419270834, so (b)'s terms are
  1.167691935221354 and 1.292925089518229. Depth 1 gives `piece` 0–16 and
  32–48, each of natural width 400, `W` = 124.33333333333334 and `h / k`
  = 1.846666666666667, so their gaps leave out `piece` 1–15 and 33–47,
  25 at full scale on either side and 74.33333333333334 wide; `DL` =
  185.57340494791663, their shrink 275.66666666666663 left of the frame
  less `OL` = 90.09326171875.
- Stored elisions, the fixture `bundle_elisions_stored`. In the ancestor
  card of `score` (64 quarters) aligned to its child `theme` (8 at 16;
  `LA` = 3200, the protected span 16 to 24), under `auto`, which reads
  `custom`: `elision_4` from 0 to 20 with `{"ratio": 0.5}` is clipped to
  0–16, natural width 800, drawn 400 wide; `elision_5` from 32 to 48 with
  `{"span": [4, 1]}` is drawn 3200 × 0.0625 = 200 wide of 800, its name
  `Development` its one label; `elision_6` from 40 to 56 with `{"canvas":
  30}` overlaps it, comes later in canonical order and is clipped to
  48–56, 30 wide of 400, a bare gap; `elision_1` lies on `coda`, whose
  line a rule hides, and is not drawn, the coda's stretch drawn at full
  scale. `elision_3` on the member root `recording` (10.0 seconds) from
  0.0 to 2.0 is a group elision: its stretch in the frame runs from 0.0
  to 0.2, its natural width 80 and its standard gap 32, so `DG` = 48 and
  `L'` = 352; it is carried into the ancestor card of `score` over 16
  to 88/5 (`16 + 1/5 × 8`, 1/5 the exact quotient of 2.0 and 10.0, exact
  on the score's fraction axis) and into that of `session` over 30.0 to
  35.1 (on its float axis), which draws it although the session's cards
  are `full`: a carried gap follows the frame, not the card's mode, and
  the rule hiding every elision `within` `session` matches no elision of
  `recording`. The session's own `elision_7` is not drawn, hidden by that
  rule and left out by `full` alike, and kept in the manifest. In the ungrouped card of `page` (1754 pixels, length 400),
  `elision_2` "Appendix" from 600 to 1754 has the natural width
  263.169897377423 and the standard gap 32, so the line is
  168.830102622577 long, and its labels `Appendix` and `600–1 754 px`
  stand under its ellipsis.
