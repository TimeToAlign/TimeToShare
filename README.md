# TimeToShare!

TimeToShare! is an exchange format for the structures of musical
timelines: their axes, extents, nesting, groups, conversion maps, regions,
flow control and MeasureMaps, without their events. Music-research
software trades these structures in it like a currency. The format
expresses the TimeToAlign! model
([TISMIR](https://doi.org/10.5334/tismir.296)); the Python library
[timetoalign](https://github.com/timetoalign/timetoalign) is one
implementation of it, and emits the shared fixtures, but does not define
the format. This repository holds the format as a JSON Schema, with
validation packages for Python and TypeScript.

**Status: alpha.** The repository holds one schema version, 0.2.0, the
current version, as one JSON Schema document describing one manifest shape.
It provides validators for Python and TypeScript that locate a violation
under one shared path rule and list unknown keys and warnings, the
complete and the minimal form of a manifest, a canonical
order, generated TypeScript types, shared fixtures, and three
serializations: canonical YAML, which every reader reads and every writer
writes, and two optional JSON forms, pretty JSON and RFC 8785 JSON. Both
packages write each serialization to the same bytes and read each without
losing what it holds; the JSON Schema validates the value a
text holds, whatever its serialization. It defines the tables a manifest
names beside it, the MatchClaim table and the Projections table, which
the Python package checks, and how MatchClaims give alignment anchors and
MatchStamps. It also specifies how a manifest
is drawn and how its elements are described by property–value statements
in published vocabularies, which make a manifest a YAML-LD document, with
a catalogue of identifier systems, verbs and types that guides their
writing; both packages ship both specifications and the catalogue.

## Containers

A manifest nests its content in four containers, and its drawing draws
each of them as a container of its own:

| Semantic: the manifest | Graphical: the drawing |
| --- | --- |
| bundle, the manifest itself | block |
| group | frame |
| timeline | card |
| facet | band |

The bundle holds timelines and groups; a group has timelines as its
members; every timeline, root or child, has five facets: `markers` (its
coordinate markers), `conversion_maps`, `children`, `regions` and
`flow_control`. The drawing of a manifest is one block. Each group is
drawn as a frame in the block, each group member and each ungrouped root
as a card, and each facet of a timeline as a band at the timeline's line.
An ungrouped root's card lies in the block directly; a member has one card
in the frame of each group that has it as a member. A child timeline
belongs to its parent's `children` facet and is drawn as a line in its
parent's children band, never in a card of its own unless a group has it
as a member. The four graphical containers are **boxes**, containers drawn
as rectangles with rounded corners; "box" is the generic word for any of
them.

Manifest content and addresses take the semantic words; the drawing's
containers take the graphical ones.

## The manifest

Every TimeToShare manifest has one shape and is an alignment bundle,
whatever it holds: one timeline, several, a group of timelines, or several
groups beside ungrouped timelines. The smallest manifest is

```json
{"timetoshare": "0.2.0", "timelines": [{"id": "#piece", "unit": "quarters", "length": [32, 1]}]}
```

| Member | Required | Holds |
| --- | --- | --- |
| `timetoshare` | yes | the version marker, `"0.2.0"` |
| `timelines` | yes | the root timelines, an array that may be empty |
| `id` | no | the manifest's ID, written `#` followed by the ID ([Identity](#identity)) |
| `name` | no | the manifest's displayed name |
| `meta` | no | an object of anything an application wants to record |
| `groups` | no | timeline groups whose members name timelines of the manifest |
| `measure_maps` | no | the MeasureMaps the conversion maps read, each with an ID; they belong to no timeline |
| `resources` | no | the files beside the manifest that hold data for its timelines, such as the MatchClaim table ([Resources](#resources)) |
| `@context` | no | the inline JSON-LD context: the format's terms and the prefixes the statements use; required where any element carries `statements` or `provenance`, and warned of where absent (`context_absent`) ([Describing a manifest](#describing-a-manifest)) |
| `statements` | no | property–value pairs about the manifest as a whole, among them the work it is about under `schema:about` ([Describing a manifest](#describing-a-manifest)) |
| `provenance` | no | the annotations of those pairs, how each was made and who believes it, and candidate pairs, which are never stated ([Provenance and beliefs](#provenance-and-beliefs)) |
| `graphical` | no | the styling of the manifest's drawing, its groups' display orders, its timelines' band orders, its named timestamps, its named MatchStamps and its elisions |
| `$schema` | no | a string naming the schema, for editors; never read |

A single timeline is a bundle of one root, and a group is a bundle of one
group. A manifest with an `id` or a `name` is a named bundle; one with
neither is an anonymous bundle. `id` and `name` are independent: either may
stand without the other.

**The version marker.** Both validators read `timetoshare` first. A value
without it is refused at the root as `not a TimeToShare manifest`; a value
declaring any other version raises `UnsupportedVersionError` with the
message `unsupported TimeToShare version "0.1.0"; this package reads 0.2.0
only`, the version spelled as JSON, byte for byte the same in both
packages.

A manifest describes timelines and all their descendants, not their
events. No manifest says where or how often an application places it.
Events refer to a manifest rather than the other way round: an event's
coordinates name the ID of the timeline they lie on. A manifest can
therefore be published once at a stable location, and any number of event
collections, in any serialization format or database, can point to its
timelines from wherever they live. A manifest holds no event and names
no event's ID; it names the tables of its package that hold events and
MatchClaims for its timelines, in `resources` ([Resources and
tables](#resources-and-tables)).

### The timeline

A timeline (`$defs/Timeline`) requires `id`, `unit` and `length`. Its
optional keys are `name`, `number_type`, `offset`, `locked`,
`is_segment_line`, `meta`, `children`, `conversion_maps`, `regions`,
`flow_control`, `statements` and `provenance`.

- `unit` decides the timeline's domain (logical, physical or graphical)
  and modality (continuous or discrete), since each unit belongs to exactly
  one of the six combinations, the default of its number type, and the
  number types it admits:

  | Unit | Domain | Modality | Default number type | Admits |
  | --- | --- | --- | --- | --- |
  | `number` | logical | continuous | `float` | `int`, `float`, `fraction` |
  | `floating_measures` | logical | continuous | `float` | `float`, `fraction` |
  | `whole_notes`, `quarters` | logical | continuous | `fraction` | `float`, `fraction` |
  | `ticks` | logical | discrete | `int` | `int` |
  | `milliseconds`, `seconds`, `minutes` | physical | continuous | `float` | `float`, `fraction` |
  | `samples`, `frames` | physical | discrete | `int` | `int` |
  | `pixels` | graphical | discrete | `int` | `int` |
  | `meters`, `centimeters`, `millimeters`, `inches`, `points`, `css_pixels`, `user_units` | graphical | continuous | `float` | `float`, `fraction` |

  Both packages hold this table as `UNITS`, keyed by unit, each row a
  `UnitEntry` of the unit's domain, modality, default number type and
  admitted number types (Python `number_type` and `number_types`, npm
  `numberType` and `numberTypes`).

  `pixels` counts the pixels of a raster image. `css_pixels` is the CSS
  pixel, 1/96 inch, the unit of an SVG's outermost viewport, and is
  continuous. `user_units` is a document's own coordinate system, such as
  the space of an SVG `viewBox`; only that document knows its size, so it
  is related to another unit only through a conversion map of the timeline
  that measures in it.

  The domain and modality decide the timeline's class (`seconds` makes a
  `ContinuousPhysicalTimeline`), which a timeline never writes.
- `number_type` is `int`, `float` or `fraction`, one its unit admits: a
  discrete unit `int` alone, a continuous unit `float` or `fraction`, and
  `number` any of the three; the schema refuses any other (`ticks` with
  `float`, `seconds` with `int`). Absent, it is the unit's default number
  type above.
- `length` is the timeline's length on its own axis, or `null` when it is
  not known (section [Unknown length](#unknown-length)).
- `children` is an array of timelines, each carrying its `offset` on the
  parent's axis, written in offset order with ties by ID; a child shares
  its parent's `unit`, here `seconds`:

  ```json
  "children": [{"id": "#perf", "offset": 4.0, "unit": "seconds", "length": 1503.2}]
  ```

  A child requires `offset`. The schema and both validators accept a
  negative offset, a child starting before its parent's 0; timetoalign and
  TimeLineEditor do not support it yet and refuse it (`A negative child
  offset is not supported yet: …`). Where its
  parent's length is known, a child starts at or before the parent's end
  and ends at or before it, locked or not: no child reaches past a known
  length. A child's **end** is its offset plus its length, both known.
  Where the parent's number type and the child's are both `float`, it is
  the sum of the two doubles in IEEE 754 binary64 arithmetic, rounding to
  nearest, ties to even, as a reader adding the two JSON numbers finds it;
  wherever either number type is `int` or `fraction`, and where a value
  has no double (a Fraction pair, an integer beyond the range of doubles)
  or the double sum overflows, it is the exact sum. The end is then
  compared with the parent's length by exact value. So a child of length
  855.5289364103584 at offset 76.70371459980326 ends at the length
  932.2326510101616 of its `float` parent, though the exact sum of the two
  doubles lies 3/2^46 beyond it, and a child of length 0.2 at offset 0.1
  ends at 0.30000000000000004, beyond a `float` parent of length 0.3. A
  root may carry an `offset` too, negative included:
  it places the root's origin on its unit's absolute axis, such as a
  recording whose origin is a moment in UNIX time. A root without `offset`
  has none.
- `locked` states whether the timeline's length is fixed; it defaults to
  `false` on every timeline. A child writes it like every other timeline,
  and may be unlocked as a root may. A locked timeline's length may still
  be unknown. An unlocked child's length may change only within its
  parent's known length; a parent's length never follows a child's.
  A segment is never locked, since its segment line's lock governs it:
  writers write `false` for a segment, and timetoalign and TimeLineEditor
  read a segment's `locked` as `false` whatever it states. A segment line
  that is a child, a segment or a group member is the exception, locked by
  default when it is built. That default belongs to construction, not to the table of
  [Defaults](#defaults), so writers write its `true` explicitly, in the
  minimal form as well. timetoalign and TimeLineEditor do not support
  lifting it yet.
- `is_segment_line` marks a **segment line**, a timeline containing only
  contiguous segments: its children are its segments, contiguous from 0 in
  offset order to its length, each starting where the one before it ends
  (a child's end, as above), all sharing its unit as every child does,
  and all with one `is_segment_line` value. Segments that are segment lines
  themselves make a nested segment line.
- `conversion_maps`, `regions` and `flow_control` hold the timeline's
  conversion maps ([Conversion maps and
  MeasureMaps](#conversion-maps-and-measuremaps)), regions (`{id, name?, start,
  end, meta?, statements?, provenance?}`) and flow-control elements ([Flow
  control](#flow-control)); `statements` and `provenance` hold pairs about
  the thing the timeline is the axis of, such as a recording or an edition,
  and their annotations ([Describing a manifest](#describing-a-manifest)).

### Conversion maps and MeasureMaps

A conversion map is a function from a position on its timeline's axis to a
value, discriminated by its `type`. Every map carries `type`, `id`, `name`,
`source_unit` and `target_unit`, a unit being null where that side is not
a time axis. A map is an abstract type, independent of any number type: each
of its numbers is an int, a float or a Fraction pair, whatever the
implementation computes in. Its domain and modality, which the drawing
styles it by, are those of its `target_unit`. There are ten types:

| Type | Maps x to | Own keys |
| --- | --- | --- |
| `LinearMap` | `scalar` · x + `offset` | `scalar` (default 1), `offset` (default 0) |
| `TableMap` | an interpolation between anchor pairs | `x_values`, `y_values` (equal length, at least two, x strictly increasing); `kind` `linear` (default) or `previous`; `extrapolate` `none` (default), `constant` or `linear` |
| `ConstantMap` | one value for every x | `value`, a number or a string |
| `PiecewiseMap` | the value of the map of the interval `[breaks[i], breaks[i+1])` holding x | `breaks` (strictly increasing), `maps` (one fewer than `breaks`) |
| `ChainMap` | the value of its maps applied in turn, the first first | `maps` (at least one) |
| `CombinationMap` | several named outputs, each one map's value | `maps`, an object from output name to map |
| `MeasureRecordMap` | the row of the measure holding x | `measure_map` |
| `MeasureNumberMap` | that row's `number` | `measure_map` |
| `FloatingMeasureMap` | floating measures | `measure_map` |
| `MeasureBeatMap` | the measure number and the beat | `measure_map` |

Scaling, shifting and every conversion between two units of fixed ratio
(quarters to ticks at a resolution, samples to seconds at a sample rate)
are linear maps. The last four are the **measure views**: each reads the
MeasureMap its `measure_map` names, from `quarters` (its constant
`source_unit`) to `floating_measures` (`FloatingMeasureMap`) or to null
(the other three, whose outputs are not positions on a time axis).

A map attached to a timeline converts from the timeline's axis: its
`source_unit`, where not null, is the timeline's unit. A map that another
map holds reads its holder's input: every map of a `PiecewiseMap` or a
`CombinationMap`, and the first map of a `ChainMap`, has its holder's
`source_unit` wherever both are stated. A timeline in ticks or
`whole_notes` therefore reaches a measure view through a `ChainMap` whose
first map is a `LinearMap` to quarters. The schema states the exact
reading of every type.

`measure_maps` holds the manifest's MeasureMaps, each `{id, name?, meta?,
rows}`. A MeasureMap belongs to no timeline and is not drawn; its
positions are quarters by definition, so it fits every timeline. `rows` is
the [Measure Map standard](https://github.com/measure-map/specification)'s
compressed row array, at least one row: an entry equal to the preceding
entry's default successor is omitted. A row is the standard's Measure plus
two extensions: the integer `volta`, and `offset_within_measure`, where the
row begins inside its nominal measure in quarter notes. Lengths are
strictly positive and `qstamp` is non-negative; exact Fraction pairs are
permitted wherever the standard uses JSON numbers. A measure view's
`measure_map` must name an entry of `measure_maps`, which both validators
check after the schema.

### Flow control

A timeline's `flow_control` is one array of elements `{id, type,
manifestation, coordinate, target?, repeat_count?, name?, label?, meta?}`,
each at a `coordinate` on the timeline's own axis. Its `type` decides the
manifestations it may take and whether it carries a `target`:

| `type` | Manifestations | `target` |
| --- | --- | --- |
| `jump_from`, a jump origin | `repeat_end`, `da_capo`, `da_capo_al_fine`, `da_capo_al_coda`, `dal_segno`, `dal_segno_al_fine`, `dal_segno_al_coda`, `to_coda` | the ID of a `jump_to` of the same timeline; required on the `dal_segno` manifestations and `to_coda`, optional on the `da_capo` manifestations and `repeat_end`, whose jump without one goes to the timeline's start |
| `jump_to`, a jump target | `repeat_start`, `segno`, `coda` | none |
| `flow_marker`, a flow marker | `fine`, `section_break`, `double_barline`, `final_barline` | none |

Only a `repeat_end` carries `repeat_count`, an integer of at least 1. When
a jump origin acts follows from its manifestation: a `repeat_end` on its
first `repeat_count` passes, a `to_coda` only after a `da_capo_al_coda` or
a `dal_segno_al_coda`, every other jump origin always.

### Values on a timeline's own axis

A coordinate on its timeline's own axis is written as its value alone:
`length`, a child's `offset` (on the parent's axis), a root's `offset`,
region `start` and `end`, and the `coordinate` of every flow-control
element. The value is represented as the axis's number type selects, that
is `number_type`, or the unit's default when it is absent: a JSON integer
for `int`, a JSON number for `float`, and a `[numerator, denominator]` pair
of integers with a strictly positive denominator for `fraction`, mirroring
BOPP. A child's `offset` takes the parent's number type.

The number type fixes the form of a value; the spelling within the form
is free. An `int` takes a JSON number without a fractional part, a `float`
a JSON number (an integer only where a double equals it), and a
`fraction` a `[numerator, denominator]` pair, and a reader reads every
spelling within the form as the value it states: `480.0` on an `int` axis
is the integer 480, `2` on a `float` axis the float 2.0, and a pair in
any terms, its members integers or integral floats, the Fraction it
equals (`[2, 4]` and `[4, 8.0]` are 1/2, `[-3, 6]` is −1/2). A value in
another form is refused with the code `representation`, even where its
value could be read: a Fraction pair on an `int` axis (`[480, 1]`) or a
`float` axis (`[25, 2]`), a bare number on a `fraction` axis (`12`,
`12.0`), a number with a fractional part on an `int` axis (`2.5`), and an
integer that no double equals on a `float` axis (`9007199254740993`). A
Fraction member with a fractional part or a denominator below 1 is
refused by the schema. The acceptance table
`fixtures/acceptances/0.2.0/numbers.yaml` states these readings and
refusals as rows that every reader runs ([fixture
guide](fixtures/README.md#acceptance-cases)). A round trip that respells
numbers, such as one through RFC 8785 JSON, therefore never invalidates a
manifest. Writers respell every own-axis value of a manifest
as its number type selects ([Shared spelling](#shared-spelling)): an
integral float on an `int` axis as an integer (`2.0` as `2`), an integer
on a `float` axis as a float (`2` as `2.0`), and a Fraction pair reduced
to lowest terms with a positive denominator, its members integers
(`[4, 8.0]` as `[1, 2]`). A value its number type cannot take, any of
those refused above, and every value on an axis whose `unit` or
`number_type` is unknown, is written as given; a `unit` that is missing,
not a string or a string not in the unit table, and a `number_type` that
is not a string, `null`
included, count as unknown, while a missing `number_type` is the unit's
default. A child's own-axis values are respelled by the child's own
`unit` and `number_type` even under a parent whose axis is unknown; the
child's `offset`, on the parent's axis, is then written as given. The schema
types own-axis values as `Number`; both validators then
check the representation and report a mismatch such as
`length 32 of 'score' is an int on a fraction axis: write [32, 1]`, or, for
an integer no float holds exactly,
`length 9007199254740993 of 'take' is an int on a float axis: write a float`.
Every number of a manifest is finite: JSON spells no NaN or infinity, but a
value built in memory, or read by a lenient reader, may hold one, and both
validators refuse it at its path.

A conversion map's numbers and a MeasureMap row's lengths are numbers of
the same kind, each a JSON number or a Fraction pair. Writers write the
numbers of conversion maps and of MeasureMap rows as given, neither
respelled nor reduced. The self-describing
coordinate object `{unit, number_type, value}` (`$defs/Coordinate`), its
`number_type` one its `unit` admits, serves
a position outside such a container, as hosts exchange single positions;
inside a manifest every position lies on an axis its container declares.

### Defaults

Every key of this table is optional, and readers supply its default when it
is absent. A manifest is written in one of two forms. The **complete
form** holds every key of the table, its default included (`null`, `{}`,
`[]`), except the keys whose default is "absent", which are written only
with a value. The **minimal form** omits exactly the keys whose value
equals the default in value; applications write it unless asked for the
complete one ([Forms and defaults for
applications](#forms-and-defaults-for-applications)). Numbers compare by
exact value, each read as its key's declared type selects: an integer, a
float and a Fraction pair of equal value are equal, so `repeat_count: 1`
and `repeat_count: 1.0` are both omitted, and a `LinearMap`'s `scalar`
written `1`, `1.0` or `[1, 1]` equals its default 1 and is omitted alike;
arrays and objects are equal when their items and members are. Before a
value is compared with its default, in either form, the manifest's
own-axis values are respelled as their number type selects ([Values on a
timeline's own axis](#values-on-a-timelines-own-axis)) and the `display`
of each named timestamp, of each alignment anchor and of each elision is
put in canonical order, so a timestamp's `display` written
`[name, wedge, cross_section]` equals its default and is omitted. Either form reads to
the same objects, and each writes back to itself. `length` is required in
both forms.

| Object | Key: default |
| --- | --- |
| manifest | `id`: absent (without a `name` too, an anonymous bundle); `name`: `null`; `meta`: `{}`; `groups`, `measure_maps`, `resources`: `[]`; `graphical`: absent |
| resource | `media_type`, `size`, `integrity`: absent |
| timeline | `name`: `null`; `number_type`: the unit's default (the unit table of [The timeline](#the-timeline)); `offset`: absent on a root, required on a child; `locked`: `false`; `is_segment_line`: `false`; `meta`: `{}`; `children`, `conversion_maps`, `regions`, `flow_control`: `[]` |
| region | `name`: `null`; `meta`: `{}` |
| flow-control element (`flow_control_element`) | `name`, `label`: `null`; `meta`: `{}` |
| a `repeat_end` besides (`repeat_end`) | `repeat_count`: 1 |
| conversion map (`conversion_map`) | `name`: `null` |
| a `LinearMap` besides (`linear_map`) | `scalar`: 1; `offset`: 0 |
| a `TableMap` besides (`table_map`) | `kind`: `"linear"`; `extrapolate`: `"none"` |
| MeasureMap (`measure_map`) | `name`: `null`; `meta`: `{}` |
| group | `name`: `null`; `meta`: `{}` |
| graphical | `styles`: `{}`; `rules`: `[]`; `order`: `{}`; `timestamps`, `matchstamps`, `elisions`: `[]` |
| named timestamp (`timestamp`) | `matchstamp`, `groupstamp`: `false`; `display`: `["wedge", "name", "cross_section"]`, on a match timestamp `["cross_section"]` |
| alignment anchor (`alignment_anchor`) | `display`: `["line"]` |
| elision (`elision`) | `name`, `width`: absent (the timeline's name and the standard gap); `display`: `["ellipsis", "name"]` |

`@context`, `statements` and `provenance` have no default: neither form
adds or drops them, and both write them as given. A row marked "besides"
adds its keys to those of the general row it follows: a `repeat_end` has the keys of every flow-control element plus
`repeat_count`, which no other element carries, and a `LinearMap` or a
`TableMap` the keys of every conversion map plus its own, at any depth of
nesting. The names in
parentheses are the kinds of the packages' `DEFAULTS` table.
Python's `complete(value)` and npm's `complete(value)` return a copy of a
manifest in the complete form, and `minimal(value)` in both packages a copy
in the minimal form; both are pure, read the one table above, and
respell own-axis values and put each `display` in canonical order before
comparing a value with its default.
timetoalign's `to_dict()` writes the minimal form, and
`to_dict(minimal=False)` the complete one.

### Unknown length

`length: null` means that the length is not known, on any timeline: a root,
a child, a segment, a locked timeline or a group member. It is a fact
stated by the manifest, never inferred and never a violation; content
added to such a timeline leaves its length unknown. A rule that needs an
end applies where the end is known and is skipped where it is not. Segment
lines are checked between known values: a segment of unknown length ends
where the next segment starts, and the last segment of a segment line
whose length is known ends at that length. The segments of a segment line
of known length keep ending at its length: a segment's length changes only
where its neighbours allow, never moving the line's end. The
[drawing specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/drawing.md)
scales a timeline of unknown length to its reach, the farthest coordinate
its content reaches, and ends its line in three chevrons.

### Groups and the `graphical` object

A group is `{id, name?, meta?, members}`. `members` are the distinct IDs of
the member timelines, each naming a timeline of the manifest: a root or any
descendant. Members share the same graphical start and end: every
member's 0 coincides with every other member's 0 and every member's end
with every other member's end, and positions in between convert linearly.
When only part of a timeline takes part, the member is a child of that
timeline, placed at its exact offset; a member is never placed partially.
A timeline may be a member of several groups, and no member of a group
lies inside another member of the same group, since a timeline and its
descendant in one group would give two answers for one position; a child
may belong to one group while its root belongs to another or to none. The
roots that no group names, and that contain no member, are ungrouped. A
manifest holding a group always holds its members' roots, so a member that
is a child keeps its parent. An editor that makes a child timeline a
member of a group may name its zero and its known length as groupstamps
(below), so that their lines cross the frame and the member's ancestor
lines; the format requires nothing of the kind.

`graphical` is `{styles?, rules?, order?, timestamps?, matchstamps?,
elisions?}`, at the manifest's top level only, never on a timeline: a
timeline holds time, and what is graphical lies in this object. `styles`
and `rules` style the drawing ([Drawing a manifest](#drawing-a-manifest));
`matchstamps` lists the named MatchStamps ([Named
MatchStamps](#named-matchstamps)); `elisions` lists the elisions (below).
`timestamps` lists the **named timestamps**, each `{id, timeline,
coordinate, name, display?, matchstamp?, groupstamp?}`: a
position `coordinate` on the own axis of the timeline `timeline`, a root or
a descendant at any depth, a segment included, written as that timeline's
number type selects and respelled by writers as every own-axis value is
([Values on a timeline's own axis](#values-on-a-timelines-own-axis)),
from its zero to its `length` (only from its zero when the length is
`null`), and named `name`, a non-empty string, which only a match
timestamp, one with `matchstamp: true`, may leave out ([Named
MatchStamps](#named-matchstamps)). A timestamp whose
`timeline` names no timeline of the manifest, or more than one (their IDs
repeating), has its coordinate written as given. Only that coordinate is
stored, never a map's value at it. `display` lists what the timestamp
draws, distinct words from `wedge` (its coordinate marker), `name`, `id`
and `coordinate` (its labels, stacked at the wedge's thick end in this
order: its name, its ID, its coordinate with its unit) and `cross_section`
(a vertical line across each card its timeline is drawn in, as a line or
as the faded line of an ancestor, from border to border, with a gap where
its wedge and labels stand); its order means nothing and writers write it
in the order just given. A timestamp draws by default its wedge, its name
and its cross-section line, a match timestamp its cross-section line alone
(the drawing specification, sections 2, 6.4 and 6.6). A timestamp's
**coordinates** are what its line crosses in a card: every timeline and
conversion map drawn there at its position. Its **primary coordinate** is
its `coordinate` on its `timeline`, which its wedge and labels mark,
whether that timeline is a root, a child or an ancestor drawn as a faded
line; the others are its **secondary coordinates**, drawn on a timeline
as wedges and labels too but hidden by default, their wedges turned −45°
and their coordinate labels written in their timeline's number type;
an application listing the coordinates lists them all and highlights the
primary one. A **groupstamp**, a timestamp
with `groupstamp: true` (default `false`), lies on a timeline that lies in
a group: the timeline or one of its ancestors is listed in the group's
`members` (an ancestor of a member lies in no group through it). In the
frame of each group its timeline lies in, its cross-section line extends
across the frame, from the upper border of the topmost member card to the
lower border of the bottommost, as one vertical line at the timestamp's
position, which marks the same proportion of every member's drawn length.
The members' coordinates at that line are derived from the group and
never stored; they are secondary coordinates of the timestamp. Only a
known length gives one a value, since one member's length is never
carried to another: the line still crosses a member of unknown length, up
to its reach, but gives that member, and every timeline its card draws, a
coordinate without a value, and a groupstamp on a member of unknown
length, or on a timeline inside one, gives none on the other members.
The drawing shows such a coordinate as undefined, its piece of the line
and its wedge at the opacity of an ancestor line and without a coordinate
label, and an application listing the coordinates lists it without a
value. The line is
drawn in the style of the timestamp's own line, has no settings of its
own, and leaves out the member's card, which the timestamp's own line
crosses; the timestamp's own wedge is not turned (the drawing
specification, section 6.6). A match timestamp may be a
groupstamp too. Both validators refuse a groupstamp whose timeline lies in
no group. `order` maps the
ID of a group or of a timeline to the order of what it stacks, top to bottom, and
writers never reorder it:

- a group's ID to the **display order** of its members, a permutation of
  their IDs; a group without an entry is displayed in the order of
  `members`;
- a timeline's ID, of a root or a descendant, to its **band order**:
  `line`, the timeline's own line, and any of its five facets `markers`,
  `conversion_maps`, `children`, `regions` and `flow_control`, each drawn
  as a band, each at most once: the bands before `line` lie above the
  line, the nearest last, and those after it below, the nearest first. A
  timeline without an entry follows its parent's band order, a member
  that is a child included, and a root without one the default
  `["children", "conversion_maps", "line", "markers", "regions",
  "flow_control"]`; changing a timeline's band order so changes that of
  every descendant without an entry of its own. An entry that leaves a
  facet out is completed against the order the timeline would follow
  without it: the listed entries keep their order, and each facet left
  out keeps the side of `line` it has there and lies beyond the listed
  entries on that side, in that order's sequence (the drawing
  specification, section 6.4): for a root, `["markers", "line"]` stands
  for `["children", "conversion_maps", "markers", "line", "regions",
  "flow_control"]`, which a child without an entry follows.

```json
"order": {"#score": ["children", "markers", "line", "conversion_maps", "regions", "flow_control"]}
```

draws the coordinate markers of `score`, the wedges and labels of its named
timestamps, against its line above it, its children beyond them, and its
conversion maps against its line below it;
its descendants follow it, so their conversion maps lie below their lines
too. A manifest holds no MatchClaim: MatchClaims lie in the MatchClaim
table beside it ([The MatchClaim table](#the-matchclaim-table)), and
`graphical` holds only the MatchStamps someone named from them, so that
the manifest draws without the table.

`elisions` lists the **elisions**, each `{id, timeline, start, end,
name?, width?, display?}`: a stretch of the timeline `timeline` left out
of the drawing. Every row drawn across the stretch stops where the
stretch starts and resumes where it ends, at full scale on either side,
and a narrow **gap** lies between, holding one **ellipsis** (`•••`),
centred in it, and below it the elision's name. The elision **lies on** its timeline, a root or a
descendant at any depth, a segment included: `timeline` has the meaning
and the validation of a named timestamp's `timeline`, and `start < end`,
its **elided coordinates**, are values on that timeline's own axis, from
its zero to its `length` (and only from its zero when the length is
`null`), written as its number type selects and respelled by writers as
every own-axis value is ([Values on a timeline's own
axis](#values-on-a-timelines-own-axis)). An elision moves with its
timeline when the timeline's offset changes. Nothing refers to an elision
but an address in a rule, and no timeline lists its elisions: an elision
leaves out what lies on its stretch by position, so a child added there
later is elided without an edit. `name`, a non-empty string, is its name;
without one its name label shows the name of its timeline. `width` is the
gap's drawn width, exactly one of `{"ratio": q}` (`q` times the
stretch's width at full scale, `0 < q ≤ 1`), `{"span": v}` (as wide as
`v` units of its timeline at full scale) and `{"canvas": c}` (`c` canvas
units); absent, the gap takes the standard width of 32 canvas units. A
gap is never wider than its stretch at full scale. `display` lists what
the elision draws besides its gap, distinct words from `ellipsis` (its
ellipsis), `name`, `id` and `coordinate` (its three labels, stacked as a
named timestamp's under the ellipsis, a stack that would touch a
neighbouring gap's standing below it) and `continuation` (grey
continuations of the rows across the gap), by default `["ellipsis",
"name"]`; an empty array draws a bare gap.

An elision on a timeline that lies in a group, as a groupstamp's
timeline does, is drawn across that group's frame, at one place in every
member card, the frame drawn shorter by its gaps, and carried into the
ancestor cards behind the frame; every other elision is drawn wherever
its root is drawn whole outside a frame: in an ungrouped root's card and
in the ancestor cards behind the frames of the groups holding a member
below it. Which of these a root's cards draw is a styling property of
those cards, `elision-mode` in a rule addressed to `{"id": "#R", "part":
["card"]}`: `full` draws none, `custom` the stored ones, `proportional`
elisions the drawing derives around the member in each ancestor card, and
`auto`, the initial value, the stored ones where the root has any, else
the derived ones. A derived elision leaves out the middle of a timeline's
stretch outside the member, rounded outwards to whole units of its axis,
so that each stretch keeps its start and its end at full scale; all of a
card's derived elisions share one proportion, which `elision-proportion`
states or the drawing computes from the screen it draws for, and lie on
the rows `elision-depths` chooses, drawing what `elision-display` lists.
A frame reads `elision-mode` too, `full` drawing its group's elisions
whole. Two elisions may overlap, and an elision may overlap the member's
span: neither is refused, the earlier in canonical order is drawn whole,
the later clipped, and the member's span is never elided in the card
behind its frame but by the frame's own elisions. The rule `{"select":
{"addresses": [{"id": "#score", "part": ["card"]}]}, "set":
{"elision-mode": "full"}}` draws the root `score` whole, its stored
elisions kept (the drawing specification, sections 2, 2.4, 3.2, 6.6 and
8.9).

### Unknown keys

Every object of the schema is open but `@context`, a `statements`
container and the values within it, whose keys JSON-LD reads: the schema
closes no other object and carries no custom keyword, so a key such an
object does not declare is valid. Both packages' validators find such
keys themselves and report them as **unknown keys**, except inside `meta`,
the one free object. They are reported as warnings, which refuse nothing,
since a misspelt optional key would otherwise silently become its
default. A key that a JSON-LD processor would read is refused on the manifest, a
timeline, a region and a group, as the code `reserved_key` states: a key
beginning with `@` (`@context` on the manifest excepted), a key holding a
colon, a term of the format's context the element does not use, such as
`label`, and the name of a prefix of the manifest's context
([Describing a manifest](#describing-a-manifest)). Python's
`unknown_keys(value)` and npm's `unknownKeys(value)` return the same list of
`{path, key}` entries, the path locating the object that holds the key,
sorted by path and then by key; `validate` raises only on errors. timetoalign
and TimeLineEditor keep the unknown keys of a manifest they read and write
them back. A key that a host schema declares beside its `$ref` to a
TimeToShare definition is reported as unknown by these validators; the
host's own validator is unaffected. A table is closed where a manifest is
open: the MatchClaim table refuses a key its provenance does not declare
([Checking the tables](#checking-the-tables)).

### Identity

Every timeline, group, MeasureMap, conversion map, region,
flow-control element, resource, named timestamp, named MatchStamp,
alignment anchor and elision carries an `id`, which identifies it, and so
may the manifest. A `name`, where an element has
one, is what is displayed, and it may repeat. An ID is any non-empty string without control characters
(U+0000 to U+001F): `/`, spaces, colons and URIs are allowed. Every ID is
unique across the whole manifest: the manifest's own, and the IDs of every
timeline (root or descendant), group, MeasureMap, conversion map at any
depth of nesting, region, flow-control element, resource, named
timestamp, named MatchStamp, alignment anchor and elision. An ID is never parsed
and never composed with another. A reference is an ID, written in a file
as an ID is ([Written in a file](#written-in-a-file)): a jump origin's
`target` names a jump target of the same timeline, a measure view's
`measure_map` an entry of `measure_maps`, a group's `members` name
timelines of the manifest, a key of `graphical.order` a group or a
timeline, a named timestamp's `timeline` a timeline of the manifest, an
elision's `timeline` a timeline of the manifest, a resource's `timelines`
timelines of the manifest, and an alignment anchor's `timestamps` named
timestamps. A MatchStamp's `match_claims`
are no references: they name the package's own MatchClaims in the
MatchClaim table, whose IDs are not the manifest's ([Named
MatchStamps](#named-matchstamps)).
An IRI reference of the statements or their provenance that begins with
`#`, such as the `id` of a value, names an element of any kind
([Describing a manifest](#describing-a-manifest)).

timetoalign and TimeLineEditor mint a speaking default `{prefix}_{N}` for
an element created without an ID, such as `clt_1` or `region_1`, never one
the manifest holds; an ID that is given is kept verbatim. An ID that is an
absolute URI identifies its element globally. A manifest published at a
stable location gives every local ID a global identity too: the
manifest's URI with the ID as its fragment, `<manifest location>#<id>`,
which is what the written form of the ID resolves to.

#### Written in a file

In a manifest file every ID and every reference to an ID is written `#`
followed by the ID: `"id": "#clt_1"`, `"members": ["#clt_1", "#clt_2"]`.
Exactly one leading `#` is stripped to get the ID, so `##x` is the ID `#x`.
The `#` stands on the manifest's own `id` and on the IDs of timelines at any
depth, groups, MeasureMaps, conversion maps (nested ones included), regions,
flow-control elements, resources, named timestamps (`#timestamp_1`),
named MatchStamps, alignment anchors and elisions; and on the
references: a group's `members`, the keys of `graphical.order` and the
member IDs of a group's entry, a named timestamp's `timeline`, an
elision's `timeline`, a resource's `timelines`, an alignment anchor's `timestamps`, an address's
`id`, a selector's `within`, a flow-control element's `target` and a
measure view's `measure_map`. The IDs of MatchClaims in a MatchStamp's
`match_claims` are written bare (`claim_27`), as their table holds them.
Inside `statements` and `provenance` a value
naming an element, `{"id": "#cpt_1"}`, is an IRI reference, written and
held alike, which no reader or writer rewrites. The reason is the
reading of a manifest as YAML-LD or JSON-LD, which takes `#clt_1` as a
reference relative to the manifest's own address and resolves it to
`<manifest location>#clt_1`; a bare ID would resolve to the wrong address,
and an ID with a space would be dropped.

The schema states the written form: an ID without its `#` and a reference
without its `#` are refused, with the code `schema`. Every check after the
schema, the identity rules and the messages that report them, works on the
bare IDs and quotes them bare (`'clt_1'`). Inside timetoalign and TiLiE IDs
are bare too: their readers strip the `#` and their writers add it, through
the helpers of both packages, Python's `timetoshare.ids.to_file_id`,
`from_file_id`, `with_file_ids` and `with_bare_ids`, and npm's `toFileId`,
`fromFileId`, `withFileIds` and `withBareIds`. TiLiE's workspace file keeps
bare IDs, and the `data-id` attributes of a drawing's SVG are bare.

The drawing addresses its elements by **address objects** `{id?, facet?,
part?}` built from these IDs and compared as whole objects, never by
strings composed from them; the band drawing the regions facet of a
timeline `T`, for instance, is `{"id": T, "facet": "regions"}`, its `id`
written `#T` in a file. The
drawing specification, section 2.2, gives every form.

The JSON Schema cannot express that IDs are unique, nor that a reference
names an element, nor that a map converts from its timeline's unit or its
holder's, nor that a map's arrays agree, nor that a member names a timeline
of the manifest, nor that no member of a group lies inside another, nor
that a child lies within its parent's known length, nor that a segment
line's segments are contiguous and alike, nor that a named timestamp lies
on a timeline of the manifest and within it, nor that a groupstamp lies
in a group, nor that an elision lies on a timeline of the manifest and
within it, nor that a resource's
timelines are timelines of the manifest, nor the rules of named
MatchStamps ([Named MatchStamps](#named-matchstamps)), nor the representation of
own-axis values, so both validators check them after the schema. Each
finding is one problem, located by a path into the manifest and named by a
stable code:

| Rule | Code | Location | Message |
| --- | --- | --- | --- |
| An ID repeats an earlier ID of its root's tree | `duplicate_id` | the later occurrence | `'<id>' is not unique in the manifest, first at <pointer>` |
| A jump origin's `target` names no jump target of its timeline | `dangling_target` | the `target` | `'<target>' names no jump_to of this timeline` |
| A measure view's `measure_map` names no entry of `measure_maps` | `dangling_target` | the `measure_map` | `'<id>' names no MeasureMap of this manifest` |
| A map's non-null `source_unit` is not its timeline's unit, or, for a map a `PiecewiseMap` or `CombinationMap` holds or a `ChainMap`'s first map, not its holder's non-null `source_unit` | `conversion_map` | the `source_unit` | `<type> '<id>' has source unit '<unit>', its timeline '<id>' has '<unit>'` (`… its <holder type> '<id>' has '<unit>'`) |
| A `TableMap`'s `x_values` and `y_values` differ in length | `conversion_map` | the `y_values` | `TableMap '<id>' has <n> x values and <m> y values` |
| An x value of a `TableMap`, or a break of a `PiecewiseMap`, does not exceed the one before it | `conversion_map` | the value | `x value <value> of TableMap '<id>' does not exceed the one before it` (`break <value> of PiecewiseMap …`) |
| A `PiecewiseMap` does not have one map fewer than breaks | `conversion_map` | the `maps` | `PiecewiseMap '<id>' has <n> maps for <m> breaks; it needs <m − 1> maps` |
| A child's `unit` is not its parent's | `child_unit` | the child's `unit` | `child '<id>' has unit '<unit>', its parent '<id>' has '<unit>'` |
| A child's `offset` lies beyond its parent's known length | `child_offset` | the child's `offset` | `offset <offset> of '<id>' is beyond the length <length> of its parent '<id>'` |
| A child ends beyond its parent's known length, its own end known | `child_end` | the child's `length` | `child '<id>' ends at <end>, beyond the length <length> of its parent '<id>'` |
| A segment's `is_segment_line` differs from the first segment's | `segment_line` | the segment's `is_segment_line`, or the segment when it leaves the key out | `segment '<id>' of segment line '<id>' differs from segment '<first id>' in is_segment_line` |
| A segment does not start where the one before it ends, or the first at 0 | `segment_line` | the segment's `offset` | `segment '<id>' of segment line '<id>' does not start where the one before it ends` (`… does not start at 0`) |
| The last segment does not end at the segment line's length, both known | `segment_line` | the segment line's `length` | `the segments of segment line '<id>' do not end at its length` |
| An ID of a root's tree repeats an ID of an earlier root's tree | `duplicate_id` | the later occurrence | `'<id>' is not unique in the manifest, first at <pointer>` |
| A group ID, a MeasureMap ID, a named timestamp's ID, an elision's ID, a named MatchStamp's ID, an alignment anchor's ID or a resource's ID repeats an earlier ID of the manifest | `duplicate_id` | that element's `id` | `'<id>' is not unique in the manifest, first at <pointer>` |
| The manifest's ID repeats another ID of the manifest | `manifest_id` | `id` | `'<id>' is not unique in the manifest, first at <pointer>`, the pointer naming the first occurrence of that ID |
| A member names no timeline of the manifest | `group_member` | the member | `'<id>' names no timeline of this manifest` |
| A member lies inside an earlier member of its group, or contains one | `group_member` | the later member | `member '<id>' lies inside member '<earlier id>' of the same group` (`… contains member …`) |
| A key of `graphical.order` names no group and no timeline | `order_key` | the key | `'<key>' names no group or timeline of this manifest` |
| An entry of a display order is not a member of its group | `display_order` | the entry | `'<id>' is not a member of group '<group id>'` |
| A member of a group is missing from its display order | `display_order` | the order | `member '<id>' of group '<group id>' is missing` |
| An entry of a band order is neither `line` nor a facet | `band_order` | the entry | `'<entry>' is not 'line' or a facet, in the band order of '<id>'` |
| `line` is missing from a band order | `band_order` | the order | `'line' is missing from the band order of '<id>'` |
| A named timestamp's `timeline` names no timeline of the manifest | `timestamp_timeline` | the `timeline` | `'<id>' names no timeline of this manifest` |
| A named timestamp's `coordinate` lies before 0, or beyond its timeline's known length | `timestamp_coordinate` | the `coordinate` | `coordinate <value> of '<id>' lies before the start of its timeline '<id>'` (`… is beyond the length <length> of its timeline '<id>'`) |
| A groupstamp lies on a timeline that lies in no group (neither it nor any of its ancestors is a member) | `groupstamp` | its `groupstamp` | `'<id>' is a groupstamp, but its timeline '<timeline id>' is a member of no group and lies in none` |
| An elision's `timeline` names no timeline of the manifest | `elision_timeline` | the `timeline` | `'<id>' names no timeline of this manifest` |
| An elision's `start` lies before 0 | `elision_stretch` | the `start` | `start <value> of '<id>' lies before the start of its timeline '<timeline id>'` |
| An elision's `end` lies beyond its timeline's known length | `elision_stretch` | the `end` | `end <value> of '<id>' is beyond the length <length> of its timeline '<timeline id>'` |
| An elision's `end` does not lie after its `start` | `elision_stretch` | the `end` | `end <value> of '<id>' does not lie after its start <value>` |
| An entry of an alignment anchor's `timestamps` names no named timestamp | `alignment_anchor` | the entry | `'<id>' names no timestamp of this manifest` |
| An entry of an alignment anchor's `timestamps` names a timestamp that is no match timestamp | `alignment_anchor` | the entry | `'<id>' is no match timestamp` |
| The two match timestamps of an alignment anchor lie on one timeline | `alignment_anchor` | the anchor's second entry of `timestamps` | `the timestamps of '<anchor id>' both lie on the timeline '<timeline id>'` |
| The alignment anchors of a named MatchStamp are not one connected set of timestamps | `matchstamp` | its `alignment_anchors` | `the alignment anchors of '<id>' are not one connected set` |
| A match timestamp lies on the coordinate of an earlier match timestamp of its timeline, compared by exact value | `match_timestamp` | the later timestamp | `'<id>' lies on the coordinate of the match timestamp '<earlier id>'` |
| No named MatchStamp's anchor names a match timestamp | `match_timestamp` | the timestamp | `the match timestamp '<id>' belongs to no MatchStamp` |
| An entry of a resource's `timelines` names no timeline of the manifest | `resource_timeline` | the entry | `'<id>' names no timeline of this manifest` |
| A resource has the type `MatchClaim` or `Projection` of an earlier resource | `resource_type` | the later resource's `type` | `a manifest names at most one resource of the type <type>; '<earlier id>' is one` |

Within one root's tree, IDs are visited in identity order (a timeline,
then its conversion maps, regions and flow-control elements, then its
children in array order), and after them the IDs of the maps a
`ChainMap`, `PiecewiseMap` or `CombinationMap` holds, timeline by timeline
in the same order, each map before the maps it holds; duplicates come first, then dangling targets
(timeline by timeline, its jump origins' targets before its measure views),
then the conversion-map rules (a timeline's maps in array order, each
before the maps it holds, the outputs of a `CombinationMap` in code-point
order of their names, then its children's), then children off their
parent's axis (child by child, each followed by its
own children: its unit, then an offset beyond its parent's known length
or else an end beyond it), then segment lines, whose
segments are visited in canonical order and each segment's end, a
child's end ([The timeline](#the-timeline)), is compared by exact value
with the next segment's offset and the last one's with the line's length. Across the manifest, the problems come in this
order: each root's own problems, roots in array order; then the IDs
repeated across roots (root by root, each ID of its tree in identity order,
the IDs of the maps other maps hold last), the group IDs, the MeasureMap
IDs, the named timestamps' IDs, the elisions' IDs, the named MatchStamps'
IDs, each followed by its anchors' IDs, the resources' IDs, the
manifest's ID; members
(member by member: dangling, nested); the entries of `graphical.order` in
code-point order of their keys: an order's strangers first, in its order,
then what it misses, a display order's members in the order of the group's
`members` and a band order's `line`; then the named timestamps, in array order, each its
timeline, its coordinate, then whether it may be a groupstamp; then the
elisions, in array order, each its timeline, then its start, its end
against the timeline's length and its end against its start; then the
named MatchStamps in array order, each anchor in turn (its two
timestamps in order, then whether they lie on one timeline) before
whether the MatchStamp's anchors connect, followed by the match
timestamps in array order, for each a
coordinate shared with an earlier one, then belonging to no MatchStamp; and last the resources, in array order, each its
`timelines` in order before its `type`. A repeated anchor ID is a
`duplicate_id` wherever the earlier ID stands, and a repeated ID within
one MatchStamp's `match_claims` is refused by the schema. The
rules of statements and their provenance follow the identity rules
(the description specification, section 12). A timestamp's
coordinate is an own-axis value of its timeline, so its representation is
checked as every such value is (`representation`, at its `coordinate`); a
timestamp naming no timeline is checked for its timeline alone. An
elision's `start` and `end`, and the `span` of its `width`, are own-axis
values of its timeline too, checked and respelled so, and an elision
naming no timeline is checked for its timeline alone. `<pointer>`
is a JSON pointer in URI fragment form, such as `#/timelines/0/id`, as Python's
`json_pointer(path)` and npm's `jsonPointer(path)` render a path. Both
packages write the messages above alike, a bare ID verbatim in single quotes
and every value spelled as canonical YAML and pretty JSON spell it
(`720`, `[19, 2]`, `75.0`). A child's end ([The timeline](#the-timeline)), or for a
segment of unknown length its successor's offset, is compared by exact
value and spelled as its parent's number type writes it, or as a `[numerator,
denominator]` pair where that type cannot write it exactly. A repeated
entry within one display or band order or within one group's `members` is
refused by the schema.

### The schema document

Version 0.2.0 is three documents in `schema/0.2.0/`: the manifest
document `timetoshare.schema.json`, with the identifier
`https://timetoalign.github.io/timetoshare/0.2.0/timetoshare.schema.json`,
so the document lies below `schema/` at the path of its identifier; beside
it the provenance document `provenance.schema.json`, which defines the one
provenance entry that the manifest's statements and the MatchClaim
table's rows share ([Provenance and beliefs](#provenance-and-beliefs)),
and to which the manifest document refers for every `provenance` entry;
and `tables.json`, the column types of the two tables as data ([Resources
and tables](#resources-and-tables)). Every released version's documents,
and with them the catalogue's schema `catalogue/catalogue.schema.json` as
`<version>/catalogue.schema.json`, are served at their identifiers and,
by this repository's own GitHub Pages site, at
`https://timetoalign.github.io/TimeToShare/0.2.0/timetoshare.schema.json`
(its version in place of `0.2.0`, its file name in place of
`timetoshare.schema.json`). The release workflow publishes every one of
them on both sites, assembled by `scripts/check_published.py`, which
refuses a document whose `$id` is not the address it is served at and a
reference to a document or member that is not served. The
manifest document's root is
`{"$ref": "#/$defs/Manifest"}`. These definitions are public and may be
embedded by a host schema; within 0.2.x they change only by addition:

`Manifest`, `Timeline`, `Group`, `Graphical`, `ConversionMap`,
`Coordinate`, `Number`, `Fraction`, `TimeUnit`, `NumberType`, `Id`,
`MeasureMap`, `MeasureMapRow`, `Resource`, `Timestamp`, `MatchStamp`,
`AlignmentAnchor`, `Context`, `Statements`, `StatementValue` and
`ProvenanceEntry`.

The provenance document is public as a whole: its root is the one
provenance entry. A host refers to either document, or to one definition
of the manifest document as
`timetoshare.schema.json#/$defs/<Name>`, never through an `$anchor`. It
embeds either a whole manifest, version marker included, or a bare
`Timeline`, in which case the host records the TimeToShare version itself.

The schema is the source of truth for timetoalign and TimeLineEditor.
timetoalign's hand-written serialization is tested for schema conformance and
fixture round trips. TypeScript types are generated in this repository from
the manifest and provenance documents.

## Resources and tables

A manifest holds the structure of its timelines; what lies on them, their
events and the MatchClaims that relate them, lies in tables beside it,
which the manifest names. A manifest and the files it names make a
**package**. The manifest draws and validates without them.

### Resources

```yaml
resources:
  - id: "#resource_1"
    type: MatchClaim
    timelines: ["#clt_6", "#dpt_1"]
    url: match_claims.parquet
  - id: "#resource_2"
    type: Projection
    timelines: ["#dpt_1"]
    url: projections.parquet
```

`resources` lists the files the manifest names, each one descriptor:

| Key | Required | Holds |
| --- | --- | --- |
| `id` | yes | the resource's ID ([Identity](#identity)) |
| `type` | yes | what its rows are: `MatchClaim` for the MatchClaim table, `Projection` for the Projections table, or the type of the events it holds |
| `timelines` | yes | the IDs of the timelines it holds data for, each a timeline of the manifest |
| `url` | yes | its location, relative to the manifest's own, so that a bare file name lies beside the manifest |
| `media_type` | no | its media type |
| `size` | no | its size in bytes |
| `integrity` | no | the digest of its raw bytes, `{algorithm, digest}`: `algorithm` the hash function as the PREMIS vocabulary of cryptographic hash functions names it, one of `MD5`, `SHA-1`, `SHA-256`, `SHA-384` and `SHA-512`, and `digest` the digest in lower-case hexadecimal |

At most one resource has the type `MatchClaim`, and at most one the type
`Projection`. A table of events is named by the same entry, its `type`
the type of its events; the Projections table is the one such table this
version defines. Parquet is the form in which packages read and write
these tables. `schema/0.2.0/tables.json` publishes the column types of
both tables as data ([The schema document](#the-schema-document)), each
table with its `status`: the MatchClaim table is `stable`; the
Projections table, like every event type a resource names, is
`experimental` and may change in any version.

### The MatchClaim table

A **MatchClaim** connects two events of two timelines: a synchronous
MatchClaim states that they happen at the same time, a conceptual one
relates them without stating a time, and a NOMATCH states that an event
has no counterpart on the other timeline. MatchClaims are data, not
structure, and a manifest holds none. They live in one table per package,
the **MatchClaim table**, named by the resource of type `MatchClaim`, and
it is the one place they live. A MatchClaim table belongs to one
manifest, and a MatchClaim is addressed by its ID alone. It holds one row per MatchClaim and one
column per property of a MatchClaim, each of the Arrow type given; a
column whose Null is "never" holds a value in every row:

| Column | Arrow type | Null | Holds |
| --- | --- | --- | --- |
| `timeline_a_id`, `timeline_b_id` | string | never | the IDs of its two timelines, two different timelines, each a timeline of the manifest |
| `start_anchor`, `end_anchor` | anchor | allowed | the alignment anchors the two events give, of their starts and, for intervals, of their ends; null where the MatchClaim gives none |
| `is_synchronous` | bool | never | `true` for a synchronous MatchClaim; `false` for a conceptual one, which states no temporal equivalence, and for a NOMATCH |
| `provenance` | provenance | allowed | how the MatchClaim was made and who believes it ([Provenance and beliefs](#provenance-and-beliefs)); null where the row states none |
| `certainty` | float64 | allowed | how certain the MatchClaim is, from 0 to 1, both included; null where none is stated |
| `event_a_id`, `event_b_id` | string | allowed | the IDs of its two events, one on each timeline. A synchronous or a conceptual MatchClaim names an event on each side, a Projection where the timeline holds no event of its own ([The Projections table](#the-projections-table)); null is the NOMATCH sentinel alone, on the side without a counterpart, and is never an event |
| `event_a_name`, `event_b_name` | string | allowed | the name of each event, where it is known |
| `id` | string | never | the MatchClaim's ID, never changed once given (below) |

The columns may stand in any order, and a table may hold further
columns, which are kept and never checked. A provenance that every row shares is stated once, as JSON
under the key `timetoshare:provenance` of the file's schema metadata; the
`provenance` of every row is then null, and a row stating its own is
refused.

The table uses three struct types:

- a **coordinate cell**: `struct<numerator: int64, denominator: int64,
  value: double, unit: string, number_type: string>` (below);
- an **anchor**: `struct<coordinate_a: coordinate cell, coordinate_b:
  coordinate cell>`, `coordinate_a` on the row's `timeline_a_id` and
  `coordinate_b` on its `timeline_b_id`, so that an anchor names no
  timeline of its own;
- a **provenance**: the members of the provenance entry in the order of
  `provenance.schema.json`, `stated_by` (list of string), `date`,
  `method`, `service` (strings), `basis` (list of string), `match`,
  `note` (strings) and `beliefs` (list of `struct<actor: string, belief:
  string, date: string, note: string>`). A null member is a key the entry
  leaves out, and the struct holds no other member.

A column's type is compared by its shape: the members of a struct by name
and in the order given, the items of a list by their type whatever name
the list gives them, and a field's nullable flag is not read; which
columns may hold a null is the Null of the tables here, checked row by
row.

A **coordinate cell** holds its number in three members, filled as its
`number_type` selects and never mirrored, beside the `unit` and
`number_type` of its timeline's axis: an `int` is its `numerator` alone,
a `fraction` its `numerator` and its `denominator`, a `float` its
`value` alone, and every other member is null. A float is never written
as a fraction, nor a fraction as a float. Every cell that is not null
states a `unit` of the format's units and a `number_type` of `int`,
`float` and `fraction` that the unit admits ([The timeline](#the-timeline));
its `value` is finite, its integers are 64-bit,
and a fraction has a `denominator` of at least 1, so that exact ratios
survive Parquet. A fraction in any terms is accepted and read as its
value: `(2, 4, null)` is the value 1/2, equal to `(1, 2, null)` wherever
cells are compared.

Every coordinate lies on its timeline's own axis, in that timeline's unit
and number type: a position given in a unit the timeline converts to is
converted when its event is added, never kept in the other unit, so that
one position never appears as two coordinates. Checked against a
manifest, a cell in another unit or number type than its timeline's is
refused. A table checked alone knows no timeline's axis and refuses only
the coordinates of one timeline in two units or number types.

Each row obeys these rules ([Checking the tables](#checking-the-tables)
gives their codes and messages):

- Its two timelines differ, and it names at least one event.
- A row with one event is a NOMATCH, which is not synchronous and has no
  anchors.
- A synchronous row with an event on each side has a `start_anchor`; a
  conceptual row, not synchronous with an event on each side, has no
  anchors. An `end_anchor` comes only with a `start_anchor`.
- Both coordinates of an anchor are cells, never null.
- A stated `certainty` lies in [0, 1].
- The ID and an event ID are non-empty strings without control
  characters (U+0000 to U+001F), as every ID of the format
  ([Identity](#identity)); an ID is given once in the table.
- The provenance is a provenance entry ([Provenance and
  beliefs](#provenance-and-beliefs)): valid against
  `provenance.schema.json`, without a key the entry or a belief does not
  declare, its dates days of the Gregorian calendar, each actor holding
  one belief, actors compared as the IRIs they stand for under the
  manifest's `@context`.

A NOMATCH or a conceptual MatchClaim has no anchors and is a row like any
other.

**IDs and succession.** A MatchClaim is never deleted, and its ID never
changes. A MatchClaim found wrong is invalidated by a belief `false`
([Provenance and beliefs](#provenance-and-beliefs)); a correction is
another MatchClaim under a new ID. Joining the tables of two packages
that hold one ID gives a table the check refuses (`duplicate_id`).
Whoever writes a table over an existing one keeps the **succession
rule**: every MatchClaim of the old table, by its ID, is in
the new one with the same value in every column of the table's type but
`provenance`, which alone may differ; coordinates compare by unit, number
type and exact value, and the further columns of a table are not
compared. The Python
package checks the rule for an old and a new table,
`timetoshare.tables.check_succession(old, new)` raising the first breach
and `succession_problems(old, new)` listing them ([Python](#python)). A reader refuses no table
for its history: it reads the table it is given.

### The Projections table

A **Projection** is an event that stands on a timeline for an event not
held there. It is an event type of its own, and a package holds one table
of them, the **Projections table**, named by the resource of type
`Projection`:

| Column | Arrow type | Null | Holds |
| --- | --- | --- | --- |
| `id` | string | never | the event's ID: an ID its source gives is kept, and one is minted as `projection_N` otherwise. An event's ID is unique in the package: the table holds an ID once, whichever timelines its rows lie on |
| `timeline_id` | string | never | the timeline the Projection is an event of, a timeline of the manifest |
| `unit`, `number_type` | string | never | the unit and the number type of its `start` and `duration`, stated once for both: those of the timeline's own axis |
| `start` | number | never | its position on that timeline's own axis |
| `duration` | number | allowed | its duration on the same axis, never negative; null for an instant |
| `projection_of` | `struct<timeline_id: string, event_id: string>` | allowed | the event it stands for, an object and never a joined string: both members given, the timeline another than the Projection's own; null where no such event is known |

A **number** is `struct<numerator: int64, denominator: int64, value:
double>`, a coordinate cell without its `unit` and `number_type`: its
members are filled as the row's `number_type` selects, as a coordinate
cell's are. As in the MatchClaim table, the columns may stand in any
order, further columns are kept and never checked, and the rows of one
timeline lie in one unit and one number type, its own where a manifest
is given.

A Projection repeats nothing else of its source. One mechanism serves
every side of a MatchClaim that has no event of its own:

- **The other side has an event.** The Projection names it in
  `projection_of`: score notes aligned to a recording whose alignment
  gives onsets only are projected onto the recording's axis as instants.
- **Both sides are stated as coordinates**, as a beat grid or the spine
  of IEEE 1599 states them: a Projection on each side, `projection_of`
  null. The source states positions, and nothing beyond them is invented.
- **The source names an event the package does not hold**, such as a
  note a performance inserts: a Projection under the source's ID,
  `projection_of` null. In a NOMATCH the other side stays the sentinel,
  which is never an event.

### Provenance and beliefs

One provenance entry, defined by `provenance.schema.json`, annotates both
a pair of the statements ([Describing a
manifest](#describing-a-manifest)) and a MatchClaim, in its `provenance`
column. It records two things:

- **How the item was made**, its paradata: `stated_by`, `date`,
  `method`, `service`, `basis`, `match` and `note`.
- **Who believes it**: `beliefs`, a list of `{actor, belief, date,
  note?}`: `actor` the IRI of the person or organisation holding the
  belief, `belief` one of the three strings `"true"`, `"false"` and
  `"unlikely"` (never a JSON boolean, so that the manifest and a table's
  `provenance` column hold one type), `date` the day it was stated,
  `YYYY-MM-DD`, and `note` a note in words. An actor holds at most one
  belief per item, a later belief replacing the earlier one, and one
  actor's belief leaves every other actor's standing.

Nothing in the format derives a truth value from the beliefs, and nobody
imposes one: each belief is its actor's. A person who states a pair or a
MatchClaim through an editor or a package function is recorded with the
belief `true`; a loader or a service records how the item was made and
holds no belief. Believing an item `false` records that belief and
nothing more: it never removes a stated pair or a MatchClaim, and
removing a pair is an edit of its own. The entry of a pair adds the pair it is about,
`property` and `value`; a MatchClaim's entry holds the other keys alone.

**The belief filter** selects, for one actor, the items whose state for
that actor is one of the states it is given. An item has one of four
**states** for an actor: the actor's belief, `true`, `unlikely` or
`false`, or `undecided` where the actor holds no belief on it. The filter
keeps any set of these four states, by default every state but `false`;
without an actor nothing is filtered. A MatchClaim that
the filter leaves out gives no anchor. The description specification,
section 9, states the entry, its reading as RDF and what it tells apart
among statements.

Both packages hold the four states, in the order `true`, `undecided`,
`unlikely`, `false`, as `BELIEF_STATES`, and the three kept by default as
`DEFAULT_BELIEFS`. Python's `check_belief_filter(beliefs)` and npm's
`checkBeliefFilter(beliefs)` check a filter and return the set of states
it keeps; both refuse, Python with a `ValueError` and npm with an
`Error`, alike:

- a single string: `the belief filter takes a collection of states, not
  the string 'true': write ['true']`;
- a value that is no collection, a mapping or a plain object included:
  `the belief filter takes a collection of states, not <value>`;
- a member that is no state: `'maybe' is no belief state: write 'true',
  'undecided', 'unlikely' or 'false'`, naming the first such member by
  code point of its spelling, a string quoted and any other member
  unquoted (`1 is no belief state: …`).

A table has no base IRI against which a reference could be resolved: the
IRI references of a row's provenance are read as written. The belief
filter compares a table's actors with the believer as the IRIs they stand
for under the manifest's `@context`, as it compares them among
statements, so that a compact and an absolute IRI of one actor name the
same actor; an actor that expands to nothing (a compact IRI whose prefix
the context does not declare) compares as written. Where a row holds
beliefs of the believer under two spellings, which the check refuses only
under the manifest's context, its state is the most critical of them:
`false`, then `unlikely`, then `true`.

### Checking the tables

The Python package checks both tables in `timetoshare.tables`
([Python](#python)); the npm package reads no tables.
`match_claim_problems(table, manifest=None)` and
`projection_problems(table, manifest=None)` list every problem of a table;
given a manifest (as read from its file, IDs written `#`), they also
refuse a timeline the manifest does not hold and a cell off its
timeline's axis. Each problem is a `TableProblem` of a `code`, a `row`
(its index from 0, or `None` for the whole table), a `column` (a tuple
path such as `("start_anchor", "coordinate_a")`, written
`start_anchor.coordinate_a` below) and a `message`. A table missing a
column of its type, or holding one of another type, is
reported for those alone, column by column in the type's order; next, a
table holding a null where its type allows none is reported for those
alone, row by row. Otherwise the table's own problems come first, then
row by row, each row's ID before the rules below in their
order, its provenance last. Every check reports a cell's first problem
only. `check_match_claims(table, manifest=None)` and
`check_projections(table, manifest=None)` raise the first problem as a
`TableError`, a `ValueError` whose `problem` is that `TableProblem`.

The MatchClaim table:

| Rule | Code | Column | Message |
| --- | --- | --- | --- |
| A column of the type is missing, or of another type | `schema_violation` | the column, row `None` | `the table has no column '<name>'`, `the column '<name>' is <type>, not <type>` |
| `timeline_a_id`, `timeline_b_id`, `is_synchronous` or `id` is null | `schema_violation` | the column | `'<name>' is null` |
| An ID is empty or holds a control character | `invalid_id` | `id` | `the ID is empty`, `the ID '<id>' holds a control character` |
| An ID repeats the ID of an earlier row | `duplicate_id` | `id` | `the ID '<id>' is given twice` |
| The file's provenance is no JSON text, no object or no provenance entry | `invalid_provenance` | `provenance`, row `None` | `the file's provenance is no JSON text`, `the file's provenance is no object`, `the file's provenance <pointer>: <problem>` |
| A timeline names no timeline of the manifest | `unknown_timeline` | `timeline_a_id`, `timeline_b_id` | `the manifest has no timeline '<id>'` |
| Both timelines are one | `claim_timelines` | `timeline_b_id` | `both sides are '<id>'` |
| An event ID is empty or holds a control character | `invalid_id` | `event_a_id`, `event_b_id` | `the event ID is empty`, `the event ID '<id>' holds a control character` |
| The row names no event | `claim_events` | `event_a_id` | `the MatchClaim names no event` |
| A NOMATCH is synchronous | `claim_anchors` | `is_synchronous` | `a NOMATCH MatchClaim is not synchronous` |
| A NOMATCH that is not synchronous has an anchor | `claim_anchors` | `start_anchor`, else `end_anchor` | `a NOMATCH MatchClaim has no anchors` |
| A synchronous row with an event on each side has no start anchor | `claim_anchors` | `start_anchor` | `a synchronous MatchClaim has a start anchor` |
| A conceptual row has an anchor | `claim_anchors` | `start_anchor`, else `end_anchor` | `a conceptual MatchClaim has no anchors` |
| An end anchor has no start anchor | `claim_anchors` | `end_anchor` | `an end anchor needs a start anchor` |
| A coordinate of an anchor (the start anchor's before the end anchor's, `coordinate_a` before `coordinate_b`) is null or malformed | `invalid_coordinate` | the cell, such as `start_anchor.coordinate_b` | a cell's message (below) |
| Such a coordinate lies off its timeline's axis | `axis_mismatch` | the cell | an axis message (below) |
| `certainty` lies outside [0, 1] | `invalid_certainty` | `certainty` | `the certainty <value> lies outside [0, 1]` |
| A row states a provenance where the file states one | `invalid_provenance` | `provenance` | `the provenance is stated in the file's metadata and in the row` |
| A row's provenance is no provenance entry | `invalid_provenance` | `provenance` | `the provenance <pointer>: <problem>` |

The Projections table:

| Rule | Code | Column | Message |
| --- | --- | --- | --- |
| A column of the type is missing or of another type | `schema_violation` | the column, row `None` | as in the MatchClaim table |
| `id`, `timeline_id`, `unit`, `number_type` or `start` is null | `schema_violation` | the column | `'<name>' is null` |
| An ID is empty or holds a control character | `invalid_id` | `id` | as in the MatchClaim table |
| An ID repeats the ID of an earlier row | `duplicate_id` | `id` | as in the MatchClaim table |
| `timeline_id` names no timeline of the manifest | `unknown_timeline` | `timeline_id` | `the manifest has no timeline '<id>'` |
| `unit` is none of the format's units, or `number_type` none of `int`, `float` and `fraction` or one the unit does not admit | `invalid_coordinate` | `unit`, else `number_type` | `'<unit>' is no unit`, `'<number type>' is no number type`, `'<unit>' admits no number type '<number type>'` |
| The row's unit and number type are not those of its timeline in the manifest, or of an earlier row on its timeline | `axis_mismatch` | `unit` where the units differ, else `number_type` | an axis message (below) |
| `start`, then `duration`, is malformed | `invalid_coordinate` | the number | a number's message (below) |
| A well-formed `duration` is negative | `invalid_duration` | `duration` | `the duration is negative` |
| A member of `projection_of` is null or empty | `invalid_projection_of` | `projection_of.timeline_id`, `projection_of.event_id` | `the projected event has no timeline_id`, `the projected event has no event_id` |
| `projection_of` names the Projection's own timeline | `invalid_projection_of` | `projection_of.timeline_id` | `a Projection stands for an event of another timeline than '<id>'` |
| `projection_of` names no timeline of the manifest | `unknown_timeline` | `projection_of.timeline_id` | `the manifest has no timeline '<id>'` |

A cell's message names the first of: an anchor's coordinate that is null
(`the coordinate is null`); a null `unit`, then a null `number_type`
(`the coordinate has no unit`, `the coordinate has no number_type`); a
unit that is none of the format's (`'<unit>' is no unit`); a number type
other than `int`, `float` and `fraction` (`'<number type>' is no number
type`); a number type its unit does not admit (`'<unit>' admits no number
type '<number type>'`), so that a table checked alone refuses it too; then
the problem of its number. A number's message calls a
cell and a Projection's `start` the coordinate and a Projection's
`duration` the duration, and names the first of: a member its number type
fills that is null, in the order `numerator`, `denominator`, `value` (`a
float coordinate has no value`, `a fraction duration has no
denominator`); a member it leaves null that holds a value (`an int
coordinate holds its numerator alone, not a denominator`, `a fraction
coordinate holds its numerator and denominator alone, not a value`); a
value that is not finite (`the coordinate's value <value> is not
finite`); a denominator below 1 (`the coordinate's denominator
<denominator> is below 1`). An axis
message is `a coordinate in <unit> (<number type>) on the timeline '<id>' in <unit>
(<number type>)` against a manifest, and `the timeline '<id>' has
coordinates in <unit> (<number type>) and in <unit> (<number type>)` at
the later of two cells, or Projections, of one timeline in a table, the
first axis met before the second. A cell on a timeline the manifest does not hold is
not compared.

In a provenance message, `<pointer>` locates the member at fault as a
JSON pointer into the entry in URI fragment form (`#` for the entry,
`#/beliefs/1/actor`), and `<problem>` names the first of: the entry's
first problem against `provenance.schema.json`, worded as `validate`
words a `schema` refusal (`'maybe' is not one of ['true', 'false',
'unlikely']`); a key the entry or a belief does not declare (`'<key>'
is no key of a provenance entry`, `… of a belief`); a date that is no
day of the Gregorian calendar (`'<date>' is no Gregorian calendar date
written YYYY-MM-DD`); an actor holding a second belief (`'<actor>'
already holds belief <index> of this entry; an actor holds one belief`,
the index that of its earlier belief), actors compared as the IRIs they
stand for under the manifest's `@context` where a manifest is given, an
actor that expands to nothing as written.

**Unknown keys.** The `provenance` column holds the members of the entry
alone, so a row cannot state a key the entry does not declare, and the
file's provenance stating one is refused (`invalid_provenance`). In a
manifest, the same key in a `provenance` entry is an unknown key,
reported as a warning that refuses nothing ([Unknown
keys](#unknown-keys)): the one provenance entry is open in a manifest
and closed in a table.

`succession_problems(old, new)` lists every breach of the succession rule
([The MatchClaim table](#the-matchclaim-table)), both tables checked
before, the old table's MatchClaims in its row order, for each its
columns in the type's order; `check_succession` raises the first.

| Rule | Code | Column | Message |
| --- | --- | --- | --- |
| A MatchClaim of the old table is missing from the new one | `succession_missing` | `id`, row `None` | `the MatchClaim '<id>' is missing` |
| A MatchClaim of the old table has another value in a column but `provenance` | `succession_changed` | that column, the row in the new table | `the MatchClaim '<id>' changed its '<column>'` |

## MatchStamps

### From MatchClaims to anchors

An **alignment anchor** is a pair of coordinates of two timelines, each
on its timeline's own axis.

- A synchronous MatchClaim gives the anchor of its `start_anchor` and, if
  it has one, of its `end_anchor`. A MatchClaim with both is an **interval
  MatchClaim**, and its two anchors bound a **matched span** on each timeline.
  A NOMATCH or a conceptual MatchClaim gives none, and so does one the
  belief filter leaves out.
- Two anchors are the same when both their coordinates are equal,
  compared by exact value on the two timelines' axes; the **unique
  anchors** are the anchors without repeats.
- A **potential MatchStamp** is one connected set of coordinates under the
  unique anchors: the coordinates that a chain of anchors joins, with the
  MatchClaims behind them. It holds only what MatchClaims state, never a
  position that a group, a parent or an interpolation would add, and it is
  derived from the current table, never stored.

For example, a recording aligned to a score by 58 note onsets, each
projected onto the recording's samples as an instant, gives 58
MatchClaims and 58 Projections; the notes of a chord share their onset, so
the MatchClaims give 31 unique anchors, which join 62 coordinates into 31
potential MatchStamps of two coordinates each.

Python's reference derivation, `alignment_anchors` and
`potential_matchstamps`, names the MatchClaims behind each anchor and
each potential MatchStamp by their IDs.

### Named MatchStamps

A MatchStamp someone names is stored in the manifest's `graphical`
object, so that it draws without the table:

```yaml
graphical:
  timestamps:
    - id: "#timestamp_3"
      timeline: "#clt_6"
      coordinate: [27, 2]
      matchstamp: true
    - id: "#timestamp_4"
      timeline: "#dpt_1"
      coordinate: 850176
      matchstamp: true
  matchstamps:
    - id: "#matchstamp_1"
      name: "Bar 4, downbeat"
      alignment_anchors:
        - id: "#anchor_1"
          timestamps: ["#timestamp_3", "#timestamp_4"]
          display: [line, name]
      match_claims: [claim_27, claim_28]
```

- **Match timestamp**: a named timestamp with `matchstamp: true`, at most
  one per coordinate and shared by every MatchStamp touching it. Its
  `name` is optional, its `display` defaults to `["cross_section"]`, and
  every word of an ordinary timestamp's `display` works on it.
- **Named MatchStamp**: `{id, name, alignment_anchors, match_claims}`.
  Each alignment anchor has an ID, names its two match timestamps in
  `timestamps`, and carries `display`, distinct words from `line` and
  `name`, by default `["line"]`: `line` draws the anchor's line, `name`
  the MatchStamp's name at the line's middle. An editor naming a
  MatchStamp turns `name` on for the middle anchor in screen order. The
  timestamps of a MatchStamp are those its anchors name.
- `match_claims` records the IDs of the MatchClaims behind the MatchStamp
  when it was named or last updated, MatchClaims of the manifest's own
  table. The manifest is valid whatever the
  table says: comparing a named MatchStamp with the current table is an
  editor's work. A MatchStamp, unlike a MatchClaim, may be changed and
  removed.

Both validators refuse an anchor naming a timestamp that does not exist
or is no match timestamp, and an anchor naming two timestamps of one
timeline (`alignment_anchor`); a MatchStamp whose anchors do not form one
connected set of timestamps (`matchstamp`); two match timestamps at one
coordinate of one timeline, and a match timestamp that no MatchStamp
names (`match_timestamp`); an anchor ID that repeats any ID of the
manifest (`duplicate_id`, as every ID); and a MatchClaim ID repeated
within one MatchStamp's `match_claims` or an anchor's `display` word
other than `line` and `name` (`schema`). The table of
[Identity](#identity) gives each rule's location and message. The drawing specification
draws a match timestamp's line as every cross-section line and an anchor
as the shortest line between its two timestamps' lines (sections 6.6 and
8.7); its SVG and TikZ writers draw the named MatchStamps as stored, and
never the potential MatchStamps an editor shows from the table.

## Describing a manifest

The manifest, every timeline at any depth and every region may state what
it stands for. A manifest bundles the manifestations of one or more
expressions of one work: the manifest stands for the bundle and names
that work, which it never packages, by `schema:about`; a timeline stands
for the manifestation it is the time axis of, such as an edition, an
encoding, a recording file or a video; and a region for the stretch of
that manifestation it marks. Works and expressions occur only as values,
named by the bundle and by the timelines that manifest them. The
elements state all this in `statements`, property–value pairs
whose properties and things are IRIs of published vocabularies (Wikidata,
schema.org as MusicBrainz writes it, the GND ontology, LRMoo and MeLODy,
the MARC relators and others), with a list `provenance` beside them recording who
stated a pair, when, how and on what basis, and who believes it
([Provenance and beliefs](#provenance-and-beliefs)); a candidate, a pair
held in `provenance` alone, is never stated. The inline `@context` makes the manifest a YAML-LD document
that any JSON-LD 1.1 processor reads as RDF without fetching anything.

The **catalogue**, `catalogue/catalogue.yaml`, lists identifier systems
with the addresses each recognises and the vocabulary its linked data
uses, verbs such as "performed by" with the properties that state each in
each system, and types of thing with their usual verbs. Tools read it to
offer properties and to print pairs in words; the validators never
consult it, and no manifest names a verb. The [description
specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/description.md)
states the subject, the bibliographic class of each thing a manifest
holds, pairs, values naming elements, the context, provenance, the
catalogue, the functions that edit statements, and their validation with
its codes. Both packages contain the specification, the wheel as
`timetoshare/docs/description.md` and the npm package as
`@timetoalign/timetoshare/docs/description.md`, and the catalogue as
`catalogue/catalogue.yaml` beside it.

## Drawing a manifest

The optional `graphical` object of a manifest contains named declarations
in `styles` and an ordered list of `rules`:

```json
"graphical": {
  "styles": {
    "highlight": {"stroke": "#7F00FF", "fill": "#7F00FF"}
  },
  "rules": [
    {"select": {"element": "label"}, "set": {"fill": "#404040"}},
    {"select": {"element": "wedge", "within": "#performance"}, "set": "highlight"}
  ]
}
```

Each rule has a selector in `select` and either a declaration or a style
name in `set`. Rule order matters. The complete selectors, presentation
properties, cascade, defaults, element addresses, layout, and writer profiles
are defined by the
[drawing specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/drawing.md).

Every manifest is drawn as one block ([Containers](#containers)), opened
by its title: its `name`, or its `id` when it has no name; an anonymous
bundle has none. Each group is a frame; each ungrouped root lies in a card
of its own, and each member in one card in the frame of each group that
has it as a member; a member that is a child timeline is drawn with the
faded lines of its ancestors and, unless a rule hides it, with its
root's **ancestor card** behind its group's frame, the root drawn whole
at the proportions of its own axis, its line continuing the faded one.
The element types are the containers `block`, `frame`, `card`,
`ancestor_card` (shown by default) and `band` (a band draws one of a timeline's five
facets and lies above or below its line as the timeline's band order
places it; a band that is not displayed hides everything it holds, and by
default the regions and flow control bands are hidden on every timeline
but the one a card holds), and the content `timeline`, `child`,
`boundary` (a segment's start on its segment line), `ancestor`, `map`,
`region`, `flow_marker` (a flow marker), `jump_from` (a jump origin, drawn
as an arc to its target or to the start; a jump target draws nothing),
`wedge` (a coordinate marker), `cross_section` (a named timestamp's
cross-section line), `alignment_anchor` (the line of an alignment anchor
of a named MatchStamp, drawn last, across the cards between its two
timestamps), `elision` (the gap of an elision, over the stretch it
leaves out), `ellipsis` (an elision's ellipsis, one centred in each
drawing of its gap), `name` and `label` (every other text, a named
timestamp's name, a MatchStamp's name and an elision's three labels among
them). Besides `element`, a selector may name `addresses` (address
objects, each matched as a whole object), `domain`, `modality`, `class`
(the class a timeline's unit decides, such as
`ContinuousPhysicalTimeline` for `seconds`, or a conversion map's type),
`facet` (the bands drawing that facet), `within` (a timeline and its
descendants), `inside` (an element type that holds the element at any
depth) and `coordinates` (`"primary"` or `"secondary"`: the wedges and
labels of the named timestamps' primary coordinates, or of their secondary
ones; no other element). The defaults hide the secondary ones, so the rule
`{"select": {"element": "wedge", "coordinates": "secondary"}, "set":
{"display": "inline"}}` shows their wedges. The property `shadow` colours a card's offset shadow, and
`rotation` turns a wedge about its tip, in whole degrees from −180 to 180.
Four properties of a card, an ancestor card and, for the first, a frame
choose its elisions (the elisions paragraph of [Groups and the `graphical`
object](#groups-and-the-graphical-object)): `elision-mode` (`auto`,
`full`, `proportional`, `custom`), `elision-proportion` (`auto` or a
number from above 0 to 1), `elision-depths` (`auto` or positive integers
separated by single spaces, the root's depth 1) and `elision-display`
(`none` or words of an elision's `display` separated by single spaces);
the schema alone checks their values, and none has a default in the
`DEFAULTS` table: their initial values are the drawing specification's.
The group fixture `group_styled` frames its group in violet, fills the
group's title violet, and gives every card in a frame a light violet
shadow:

```json
"graphical": {
  "order": {"#group_1": ["#score", "#page", "#performance"]},
  "rules": [
    {"select": {"element": "frame"}, "set": "frame-highlight"},
    {"select": {"element": "name", "addresses": [{"id": "#group_1", "part": ["name"]}]}, "set": {"fill": "#7F00FF"}},
    {"select": {"element": "card", "inside": "frame"}, "set": {"rx": 2, "shadow": "#C4B5FD"}}
  ],
  "styles": {
    "frame-highlight": {"stroke": "#7F00FF"}
  }
}
```

A rule may name a style missing from the `styles` of its `graphical`
object. Python's `complete_styles(graphical)` and npm's
`completeStyles(graphical)` return a copied `graphical` object with every such
name added as an empty declaration, together with the sorted missing names.
Python issues one `MissingStyleWarning` and npm one `console.warn` call, each
naming all missing styles. The completed `graphical` object is valid, and a rule that names one of those empty declarations sets nothing.

A drawing is derived and is not exchanged as JSON. The drawing specification
pins the drawing, and both packages contain it: the wheel as
`timetoshare/docs/drawing.md`, the npm package as
`@timetoalign/timetoshare/docs/drawing.md`.

Every text is measured and drawn with the bundled DejaVu Sans 2.37 release
file, `fonts/DejaVuSans.ttf`; every code point it does not map and Noto
Music does, such as the whole note of a label in whole notes, is drawn with the bundled Noto
Music 2.004 release file, `fonts/NotoMusic-Regular.ttf`.
`fonts/DejaVuSans-LICENSE` and `fonts/NotoMusic-LICENSE` contain their
licences, and `fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json`
contains the advance-width metrics of both, in one table.
Python names the files in `FONT_FILES` and exposes them through
`font_paths()`, and the metrics through `font_metrics()`. The npm package
exports `FONT_FILES` and `fontMetrics` and exposes the files through the
`@timetoalign/timetoshare/fonts/*` subpath. Run
`scripts/extract_font_metrics.py` to regenerate the metrics from the fonts.

## Canonical order

Readers accept a manifest's collections in any order. Writers emit one
canonical order, so equal manifests have equal text. The keys of every
object, at every depth, are sorted by Unicode code point. The arrays whose
order keys cannot express are put in this order:

- `timelines`, `groups` and `measure_maps` by ID, and every group's
  `members` by code point;
- in every timeline, `children` by offset, then ID;
- `conversion_maps` by ID;
- `regions` by start, then end, then ID;
- `flow_control` by coordinate, then ID;
- `resources` by ID;
- `graphical.timestamps` by `timeline` (code point), then coordinate,
  then ID, and every timestamp's `display` in the order `wedge`, `name`,
  `id`, `coordinate`, `cross_section`, followed by any other strings by
  code point and then by any other values in their given order;
- `graphical.matchstamps` by ID, every MatchStamp's `alignment_anchors`
  by ID, and every anchor's `display` in the order `line`, `name`,
  followed by other values as a timestamp's are;
- `graphical.elisions` by `timeline` (code point), then start, then ID,
  and every elision's `display` in the order `ellipsis`, `name`, `id`,
  `coordinate`, `continuation`, followed by other values as a timestamp's
  are.

Coordinates compare by exact numeric value, never by spelling. Strings
compare by Unicode code point. IDs are unique across a valid manifest, so
no two entries tie; entries that tie on every member they are ordered by,
as entries of equal ID do, keep their given order. A writer refuses a
manifest that cannot be put in this order (Python raises `ValueError`,
TypeScript `TypeError`): one in which an entry of an ordered array of
objects is not an object, lacks a member it is ordered by, or holds that
member in a wrong type, such as an ID or a `timeline` that is not a
string, or a coordinate that is neither a number nor a Fraction pair (two
integers, an integral float counting as the integer it equals, the
denominator at least 1); and one in which an entry of a group's `members`
is not a string. A `display` is put in order whatever it holds, and a
member that should hold an ordered array but holds no array, such as
`children: "x"`, has nothing to order and is written as given. No other
array is reordered: `graphical` rules, display orders,
conversion-map payloads, MeasureMap rows, the values of every pair of
`statements`, and every `provenance` keep their order.

## Serializations

A manifest is a value, and it is exchanged as text in one of three
serializations, each specified here to the byte:

| Serialization | Name | Status |
| --- | --- | --- |
| canonical YAML | `"yaml"` | required: every reader reads it, every writer writes it |
| pretty JSON | `"json"` | optional, recommended over RFC 8785 JSON for its readability and its number kinds |
| RFC 8785 JSON | `"jcs"` | optional, for digests and signatures |

Manifests are kept in repositories and changed by reviewed pull requests,
so each serialization gives equal manifests equal text, and a diff of two
versions of a manifest shows what changed. Each package writes
all three with `dumps` and reads all three with `loads`, and the two
packages write the same bytes for the same value. `dumps` writes the form it is given: pass a manifest through
`complete` or `minimal` first to choose its form ([Defaults](#defaults)).

### The data model

A manifest is a JSON value: an object, an array, a string, an integer, a
float, `true`, `false` or `null`. Integer and float are distinct kinds:
`2` and `2.0` are two values of equal numeric value. An integer is exact at
any size; a float is a finite IEEE 754 double. An object's keys are
distinct strings, and an object has no order of its own; an array is
ordered. Every serialization carries this model whole, except that RFC 8785
JSON loses the distinction between integer and float. In Python the kinds
are `dict`, `list`, `str`, `int`, `float`, `bool` and `None`; in
TypeScript a number is a `JsonNumber` ([TypeScript](#typescript)).

### Shared spelling

These rules hold in canonical YAML and pretty JSON. In RFC 8785 JSON the
rules on strings and on the order of arrays hold too, while numbers and
the order of keys follow its own rules and it has no lines ([RFC 8785
JSON](#rfc-8785-json)).

**Integers** are written in decimal digits, preceded by `-` when negative,
never with `+` or a leading zero: `0`, `480`, `-3`, `9007199254740993`.

**Floats** are written by the following algorithm. It gives what Python's
`repr` gives for a float, with a fractional digit added to a mantissa in
exponent form that lacks one (`repr` writes `1e-05`, the algorithm
`1.0e-05`), and is stated so that it can be implemented without Python.

1. A NaN or an infinity is refused. Zero is written `0.0` and negative zero
   `-0.0`. A negative float is written `-` followed by its magnitude,
   spelled by steps 2 to 4.
2. Find the shortest string of decimal digits d1 d2 … dn, d1 not 0, with an
   integer k such that the decimal d1.d2…dn × 10^k reads back as the float:
   the double nearest to it, of two equally near the one with an even
   significand, is the float. Where several strings of that length read
   back as the float, take the one nearest to the float's exact value, and
   of two equally near the one whose last digit is even. ECMAScript's
   Number::toString finds strings of the same length and, as ECMAScript
   recommends and engines do, chooses the same digits.
3. If −4 ≤ k ≤ 15, write fixed notation with at least one fractional
   digit. For k ≥ 0: the digits d1 … d(k+1) as the integer part, padded on
   the right with zeros when n < k + 1, then `.`, then the remaining digits
   d(k+2) … dn, or `0` when none remain. For k < 0: `0.`, then −k − 1
   zeros, then d1 … dn.
4. Otherwise write d1, then `.`, then d2 … dn, or `0` when n = 1, then
   `e`, the sign of k (`+` or `-`) and the magnitude of k in at least two
   digits. The mantissa so always has a fractional digit.

So 2.0 is written `2.0`, 123.25 `123.25`, 0.1 `0.1`, 0.0001 `0.0001`,
0.00001 `1.0e-05`, −2.5 × 10^−7 `-2.5e-07`, 10^15 `1000000000000000.0`,
10^16 `1.0e+16`, 1.5 × 10^16 `1.5e+16`, the smallest double above zero
`5.0e-324` and the largest double `1.7976931348623157e+308`.

**Depth.** A scalar has depth 0; an object or an array has depth 1 plus
the greatest depth of its members, an empty one depth 1. A writer refuses a
value deeper than 256 in every serialization, so that every value that can
be written can be read ([Reading](#reading)).

**Strings and keys** are Unicode text, written in UTF-8. A string or key
holding a lone surrogate, a code point from U+D800 to U+DFFF that is not
part of a pair, cannot be written in UTF-8 and is refused. Each
serialization names the characters it escapes; every other character is
written as itself. A key whose canonical YAML form, its quotes and escapes
included, is longer than 1024 UTF-16 code units (a character above U+FFFF
counting two) is refused by every writer, in every serialization. YAML 1.2
limits the implicit keys of block mappings, from their first character to
their `:`, to 1024 characters, which parsers count in code points or in
UTF-16 code units; so every manifest that can be written can be written in
canonical YAML and read by every YAML parser.

**Order.** The keys of every object, at every depth, are sorted by Unicode
code point. When the value written is an object whose `timelines` member
is an array, whether or not it holds `timetoshare`, it is a manifest: its
arrays are put in [canonical order](#canonical-order) and its own-axis
values respelled as their number type selects ([Values on a timeline's
own axis](#values-on-a-timelines-own-axis)) before it is written. Every
other array keeps its order. Only the value written is so taken as a
manifest: a value that is not a manifest, such as an application's file
that embeds manifests, keeps the order of all its arrays and the kind of
all its numbers, and of a manifest it embeds only the keys are sorted.
A top-level `timelines` member that is an array is so reserved for
manifests: a value such as `{"timelines": ["b", "a"]}` is taken as a
manifest, cannot be put in canonical order, and cannot be written.

**Scalar sequences.** A scalar is `null`, `true`, `false`, a number or a
string. A non-empty array whose items are all scalars is a **scalar
sequence**, written on one line as `[`, its items separated by `, ` (a
comma and one space), and `]`, however long the line. Every other
non-empty array, one holding an empty array or an empty object included,
is written one item per line. An empty array is written `[]` and an empty
object `{}`. A Fraction pair is so written `[19, 2]`, and a named
timestamp's `display` `[wedge, coordinate]` in canonical YAML and
`["wedge", "coordinate"]` in pretty JSON.

### Canonical YAML

Canonical YAML is YAML 1.2 under its core schema, written in one layout:

- The text is one document, without a `%` directive, `---` or `...`,
  anchors, aliases, explicit tags or comments. It is UTF-8 without a byte
  order mark, every line ends in a line feed (LF), no line ends in a space,
  and the text ends in exactly one line feed.
- Columns count characters from 0 at the start of a line. Indentation is
  two spaces: a member or an item at column c places the content nested in
  it, where that content goes on the following lines, at column c + 2.
- An object with members is written one member per line, as its key, `:`
  and then
  - a scalar, `{}`, `[]` or a scalar sequence, after one space on the same
    line;
  - an object with members, or a non-empty array that is not a scalar
    sequence, on the following lines at column c + 2, c being the key's
    column.
- A non-empty array that is not a scalar sequence is a **block sequence**,
  written one item per line, each item as `-` at the column c of the
  sequence and then
  - a scalar, `{}`, `[]` or a scalar sequence, after one space on the same
    line;
  - an object with members, or a block sequence: nothing, the `-` standing
    alone on its line with no space after it, and the object's members or
    the sequence's items on the following lines at column c + 2.
- At the top level, an object with members starts at column 0, and so
  does a non-empty array, written as a block sequence even when it is a
  scalar sequence, since a text that begins with `[` is read as JSON
  ([Reading](#reading)); a scalar, `{}` or `[]` stands alone on the one
  line.
- `null`, `true` and `false` are written so; integers and floats as in
  [Shared spelling](#shared-spelling).
- A string, a value or a key, is written **plain**, as itself, when it is
  not empty, matches `^[A-Za-z_][A-Za-z0-9_./-]*$`, and its lower-case
  form is none of `null`, `true`, `false`, `yes`, `no`, `on`, `off`, `y`
  and `n` (the last six guard readers still on YAML 1.1). Every other
  string is written **double-quoted**, between `"` and `"`, escaping `"` as
  `\"`, `\` as `\\`, U+0008 as `\b`, U+0009 as `\t`, U+000A as `\n`, U+000C
  as `\f` and U+000D as `\r`, and every other character of U+0000 to
  U+001F, U+007F to U+009F, U+2028, U+2029, U+FEFF, U+FFFE and U+FFFF as
  `\u` and its four hexadecimal digits in lower case (`\u001b`); every
  other character is written as itself. A string is never folded or broken
  across lines.

So `score`, `take_1`, `quarters` and `has_part` are plain, while `"0.2.0"`,
`"Sonata in B♭"`, `"#score"`, `"https://example.org/"`, `"$schema"`, `"No"` and `""`
are quoted. The value `{"a": [[1, 2], [{"b": null}], {"c": {"d": "x y"}}],
"e": {}}` is written

```yaml
a:
  - [1, 2]
  -
    -
      b: null
  -
    c:
      d: "x y"
e: {}
```

Every canonical YAML text reads to the same value under a YAML 1.1 parser
as under a YAML 1.2 parser: a YAML 1.1 float needs a `.`, which every
written float has, and the plain strings exclude YAML 1.1's further
booleans. A text written by hand is read as [Reading](#reading) states.

### Pretty JSON

Pretty JSON is JSON ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259))
laid out as follows:

- An object with members is written `{`, then its members one per line,
  each as its key, `: ` (a colon and one space) and its value, then `}` on
  a line of its own. The members stand at column c + 2 and the `}` at
  column c, c being the indentation of the line on which the `{` stands.
  Every member but the last is followed by `,` at the end of its last
  line. A value that is an object or array opens on its member's line.
- A non-empty array that is not a scalar sequence is written likewise with
  `[` and `]`, its items one per line in place of members, each item that
  is an object or array opening on its own line.
- A scalar sequence is written `[a, b]`, an empty array `[]` and an empty
  object `{}`, each on the line of the key or item that holds it.
- `null`, `true` and `false` are written so; integers and floats as in
  [Shared spelling](#shared-spelling).
- Every string, a value or a key, is double-quoted, escaping `"` as `\"`,
  `\` as `\\`, U+0008 as `\b`, U+0009 as `\t`, U+000A as `\n`, U+000C as
  `\f` and U+000D as `\r`, and every other character of U+0000 to U+001F
  as `\u` and its four hexadecimal digits in lower case (`\u001b`); every
  other character is written as itself.
- The top-level value starts at column 0. The text is UTF-8 without a byte
  order mark, every line ends in a line feed, no line ends in a space, and
  the text ends in exactly one line feed.

Canonical YAML keeps every change to its own lines. No member or item
shares a line with another, and an object or block sequence held in an
item begins on the line after its `-`, so adding, removing or changing a
member of an object, or an item of a block sequence, adds, removes or
changes that member's or item's lines and no other. A scalar sequence is
one line, and so are `{}` and `[]`: adding the first member or item to an
empty object or array, or removing the last, changes the line of its key
(or its `-`). An array that
switches between scalar sequence and block sequence, as when an object is
added to an array of strings, rewrites that array's own lines, the line of
its key or its `-` included; no line outside the array changes. Pretty
JSON keeps every change to its own lines too, except for the comma that separates
members and items: adding or removing the last member of an object, or
the last item of an array, also changes the line before it, which gains or
loses its `,`.

### RFC 8785 JSON

RFC 8785 JSON is the JSON Canonicalization Scheme of
[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) exactly, applied to the
value after canonical order and respelling: equal manifests give equal
bytes, so a digest
or a signature of the text is meaningful.

- There is no whitespace between tokens, and no final line feed: the text
  ends with its last `}`, `]` or scalar.
- The keys of every object are sorted by their UTF-16 code units, which
  differs from code-point order only between a character above U+FFFF and
  one from U+E000 to U+FFFF at the same position.
- Strings are escaped as in pretty JSON, which is RFC 8785's escaping.
- An integer from −(2^53 − 1) to 2^53 − 1 is written in decimal digits as
  in [Shared spelling](#shared-spelling). An integer outside that range is
  refused by the writer, since RFC 8785 numbers are doubles.
- A float is written as ECMAScript's Number::toString writes it. Zero of
  either sign is `0`, and a negative float is `-` followed by its
  magnitude. With d1 … dn and k as in step 2 of the float algorithm: if
  n − 1 ≤ k ≤ 20, the digits followed by k − n + 1 zeros (`2`,
  `1700000000`); if 0 ≤ k < n − 1, d1 … d(k+1), `.` and the remaining
  digits (`1503.25`); if −6 ≤ k ≤ −1, `0.`, −k − 1 zeros and the digits
  (`0.00001`); otherwise d1, then `.` and d2 … dn when n > 1, then `e`,
  the sign of k (`+` or `-`) and the magnitude of k without leading zeros
  (`1e+21`, `1e-7`, `1.5e-10`).
- An integral float of magnitude from 2^53 up to but excluding 10^21 is
  refused by the writer: it would be written in digits alone, which read
  back as an integer outside the range above.

A float written without `.` or exponent, an integral float of magnitude
below 2^53 or a zero, is read back as an integer. On a timeline's own
axis the declared number type restores the float ([Values on a timeline's
own axis](#values-on-a-timelines-own-axis)), though not the sign of a
negative zero; everywhere else, in conversion maps, MeasureMap rows,
`graphical`, `meta` and unknown keys, the distinction between integer and
float is lost.

### One manifest in three serializations

This manifest is valid and in the minimal form. It holds a Fraction
(`length` of `score`), floats (`length` and `offset` of `take_1`), an
integer (`pages`), plain and quoted strings, an empty array (`errata`), a
nested object (`meta`) and an array of objects (`timelines`). In canonical
YAML, 265 bytes:

```yaml
meta:
  source:
    edition: Urtext
    errata: []
    pages: 12
name: "Sonata in B♭"
timelines:
  -
    id: "#score"
    length: [32, 1]
    unit: quarters
  -
    id: "#take_1"
    length: 1503.25
    offset: 1700000000.0
    unit: seconds
timetoshare: "0.2.0"
```

In pretty JSON, 382 bytes:

```json
{
  "meta": {
    "source": {
      "edition": "Urtext",
      "errata": [],
      "pages": 12
    }
  },
  "name": "Sonata in B♭",
  "timelines": [
    {
      "id": "#score",
      "length": [32, 1],
      "unit": "quarters"
    },
    {
      "id": "#take_1",
      "length": 1503.25,
      "offset": 1700000000.0,
      "unit": "seconds"
    }
  ],
  "timetoshare": "0.2.0"
}
```

In RFC 8785 JSON, 244 bytes, one line ending in `}` without a line feed:

```json
{"meta":{"source":{"edition":"Urtext","errata":[],"pages":12}},"name":"Sonata in B♭","timelines":[{"id":"#score","length":[32,1],"unit":"quarters"},{"id":"#take_1","length":1503.25,"offset":1700000000,"unit":"seconds"}],"timetoshare":"0.2.0"}
```

The first two texts end in a line feed and count `♭` (U+266D) as its three
bytes in UTF-8. RFC 8785 JSON writes the `offset` 1700000000.0 as
`1700000000`, which reads back as an integer; `seconds` declares the
number type `float`, which restores 1700000000.0.

The manifest holds no float that is written in exponent form. Two such
floats, 0.00005 and 10^21, are written `5.0e-05` and `1.0e+21` in
canonical YAML and pretty JSON, and `0.00005` and `1e+21` in RFC 8785
JSON.

### Reading

Both packages read every serialization with one reader, which takes text,
not bytes: decoding a file, as UTF-8, is the caller's.

- One U+FEFF, a byte order mark, at position 0 of a text is removed
  before the text is read, in every serialization and by every reading
  function; writers never write one. The text is then read as JSON when
  its first character other than a space, a tab, a line feed or a carriage
  return is `{` or `[`, or when it is a JSON text, one value under the
  grammar of RFC 8259; every other text is read as YAML. A YAML text in
  flow style from its first character, such as `{a: 1}`, is therefore
  read as JSON and refused unless it is JSON, while a YAML mapping whose
  first key is quoted, such as `"a": 1`, is not a JSON text and is read as
  YAML. A scalar standing alone that is a JSON text, such as `480` or
  `"x y"`, is read as JSON. The canonical YAML texts that are JSON texts
  too, `{}`, `[]`, and a number, `null`, `true`, `false` or a
  double-quoted string standing alone, read as JSON to the value they hold
  as YAML.
- JSON is read in any layout by the lossless reader. A number written
  without `.`, `e` or `E` is an integer, exact at any size (`-0` is the
  integer 0); every other number is a float, read as the double nearest to
  the decimal written, of two equally near the one with an even
  significand (IEEE 754 rounding to nearest), and keeping its sign:
  `-0.0` and `-1e-400` are read as −0.0, `1e-400` as 0.0, and
  `1.7976931348623158e308` as the largest double. Refused besides are a
  text that is not one JSON value, `NaN`, `Infinity`, `-Infinity`, and a
  float that rounds to an infinity, its magnitude 2^1024 − 2^970 or more
  (`1e309`, `1.7976931348623159e308`).
- YAML is read by a conforming YAML parser in safe mode, which builds
  plain data and runs no code, under the YAML 1.2 core schema. A quoted or
  block scalar is a string; a plain scalar is null, a boolean, an integer,
  a float or a string as the core schema resolves it, an integer being
  exact at any size. Comments are ignored, and an empty text, or one of
  blank lines and comments only, is read as null. Refused besides are
  - a character outside YAML 1.2's printable set (`c-printable`), such as
    U+0001, U+007F or a lone surrogate;
  - every text the parser refuses, more than one document among them;
  - anchors, aliases and tags, whatever the tag (`!!str 1`, `!!binary`,
    `!local`, `!`);
  - a key that is not a string, such as `1`, `null`, `true` or a
    collection;
  - a float that is not finite: `.nan`, the infinities, and a literal that
    rounds to an infinity, such as `1e309`.
- In every serialization, JSON and YAML alike, refused are
  - a key that repeats in its object, keys being compared after their
    escapes are read (`{"a": 1, "a": 2}` is refused); both packages
    refuse it in JSON too, where RFC 8259 leaves it open;
  - a lone surrogate in a string or a key, a code point from U+D800 to
    U+DFFF that is not part of a pair, whether it stands in the text as
    itself, as only a text held in memory can hold it, or is written
    through an escape such as `\ud800`. An escape of a high surrogate
    directly followed by an escape of a low surrogate, such as
    `\ud83d\ude00`, is one character, here U+1F600, in YAML as in JSON;
  - a value deeper than 256 ([Shared spelling](#shared-spelling));
    manifests are far shallower.

Every reader refuses the texts these rules refuse and reads every other
JSON text, and every other YAML text that uses only the constructs of
canonical YAML, to the same value, as every conforming YAML 1.1 or 1.2
parser reads such YAML. These constructs are block mappings and block
sequences at any consistent indentation, one-line flow sequences of
scalars, `{}` and `[]`, plain scalars that canonical YAML would write
plain, numbers, booleans and null as canonical YAML spells them,
double-quoted strings with the escapes canonical YAML writes, comments and
blank lines, a blank line holding nothing but spaces. Canonical YAML holds
no literal tab, since it escapes every tab in a string, so a text with a
tab anywhere, such as a line of a tab alone or a tab before a comment,
lies outside these constructs. Beyond these constructs a text is read as
the package's parser reads it, and a difference between two parsers there
is not a defect of the format. Tools write canonical YAML.

Both packages refuse a text holding several faults at the first of them in
the order of the text, as their shared refusals in
`fixtures/serializations/` test; other readers are recommended to do the
same. Two exceptions follow from how YAML is read. A character outside
YAML's printable set is refused before the text is parsed: the first one
in a YAML text is refused where it stands, so it outranks any fault before
it, such as a repeated key. And a YAML parser reads one token ahead, since
a scalar may turn out to be a key, so a syntax error it meets while
reading ahead may be named before a fault of the token just before it, as
in `- &a "\q"`, an anchor followed by an invalid escape; only there may the
two packages name different faults. The depth limit is one fault among
them, ranked by the start of the first collection at depth 257: a fault
before that start is refused in its stead, and a fault after it is never
reached. A fault is reported at its offending token: a fault of a node at
its first character; a node with properties, an anchor, a tag or both, at
its first property, which the error names, whichever is written first
(`&a !!str x` at `&a`, `!!str &a x` at `!!str`); an alias at its `*`; an
escaped lone surrogate at its escape; a number that rounds to an infinity
at that number. Lines and columns are counted from 1, columns in code
points, JSON and YAML alike.

Python's `serialization_of(text)` and npm's `serializationOf(text)` name a
text's serialization without validating it, by the same choice between
JSON and YAML: `"jcs"` when the text is read as JSON and is byte for byte
the RFC 8785 JSON of its value; `"json"` for every other text read as
JSON, including one that cannot be read, one whose value the RFC 8785
writer refuses, and RFC 8785 JSON after a byte order mark, which RFC 8785
JSON never begins with; `"yaml"` for every other text. They never raise.

A text that a writer wrote, read and written again in the same
serialization, gives the same bytes, in either package and across the two.
Canonical YAML and pretty JSON keep every number kind; RFC 8785 JSON gives
its own bytes back although its integral floats are read as integers,
since it writes an integer and the float of equal value alike.

### Comments

Comments are not part of a manifest. Readers ignore them and writers never
write them, so a manifest read and written by a tool loses the comments of
its YAML text. A note about a manifest belongs in its `meta`, or in the
history of the repository that keeps it.

### Forms and defaults for applications

An application that writes manifests writes the minimal form
([Defaults](#defaults)) unless it is asked for the complete one, in
canonical YAML unless it is asked for another serialization. A manifest
read from a file is written back in the file's **file form**: its form,
its styling and its serialization, which the format defines and both
packages infer from the file's text:

- the form is minimal when no key at its default is present, that is when
  `minimal(value)` and the value read are written as the same canonical
  YAML, and complete otherwise. Defaults are recognised by exact value
  (`repeat_count: 1.0` is the default `1`, so a text stating it is not
  minimal); otherwise canonical YAML tells an integer from a float of
  equal value, and it ignores the order canonical order sorts;
- the manifest is styled when it holds the top-level `graphical` key;
- the serialization is the one the text is read in, as `serialization_of`
  names it.

A value is written back in a file form by dropping its `graphical` key
when the form is not styled, then putting it in the minimal or the
complete form, then writing it in that serialization. A text in the
minimal or the complete form and in canonical YAML, pretty JSON or RFC
8785 JSON so comes back byte for byte when it is read and written back
unchanged; a text in no canonical layout, such as
YAML written by hand, comes back in the canonical layout of its
serialization; and a text neither minimal nor complete comes back
complete. Python's `file_form(text)` and npm's `fileForm(text)` return a
text's `FileForm`, and Python's `dumps_file(value, form)` and npm's
`dumpsFile(value, form)` write a value in it.

## Install

```bash
pip install timetoshare
pip install "timetoshare[tables]"  # with the table types, timetoshare.tables
```

```bash
pnpm add @timetoalign/timetoshare
# or
npm install @timetoalign/timetoshare
```

## Usage

### Python

Python validation raises `SchemaValidationError` with the `code` of the
rule broken, a tuple `path` to the offending value and a `message`. Read a
manifest in any serialization with `loads`, and write it with `dumps`, or
with `dumps_file`, here back in the file form it came in:

```python
from timetoshare import (
    SchemaValidationError,
    dumps_file,
    file_form,
    fixture_paths,
    loads,
    validate,
)

text = fixture_paths()[0].read_text(encoding="utf-8")  # canonical YAML
value = loads(text)
try:
    validate(value)
except SchemaValidationError as error:
    print(error.code, error.path)
else:
    assert dumps_file(value, file_form(text)) == text
```

- `validate(value)` reads the version marker first, then checks the value
  against the schema, the representation of its own-axis values, the
  identity rules and the rules of statements, and raises
  `SchemaValidationError` at the first problem.
  A value without `timetoshare` is refused at the root; a value declaring
  another version raises `UnsupportedVersionError`. Unknown
  keys never fail it.
- `loads(text)` reads a text, a `str`, in any serialization, JSON or YAML,
  as [Reading](#reading) states, after removing one U+FEFF at position 0:
  integers stay exact at any size and floats stay floats. It reads YAML
  through PyYAML's event API (`yaml.parse`) over its pure-Python parser
  and resolves plain scalars by the YAML 1.2 core schema itself, so no
  PyYAML loader, resolver or constructor takes part; it never uses the C
  parser, so that reading does not depend on whether libyaml is
  installed. A text the reading rules refuse, and every error of the YAML
  parser, raises `ValueError` with the line and column of the fault
  ([Reading](#reading)). It does not validate.
- `unknown_keys(value)` returns the unknown keys of a manifest as a list of
  `{path, key}` entries, sorted by path and then by key.
- `manifest_warnings(value)` validates a manifest and returns its
  warnings, `context_absent` and `bundle_blank`, as `{code, path,
  message}` entries sorted by path and then by code.
- `statement_problems(value)` returns the problems of a manifest's
  statements alone as a list of `SchemaValidationError`s, empty where they
  are sound, and refuses nothing outside them (the description
  specification, section 12).
- `matchstamp_problems(value)` returns the problems of a manifest's named
  MatchStamps and match timestamps alone, as `validate` reports them, as a
  list of `SchemaValidationError`s: each match timestamp and then
  `graphical.matchstamps`, each one's first problem at its path, a number
  that is not finite (`finite_number`), else the schema (`schema`); where
  none has one, every further problem, an ID of a MatchStamp or an
  alignment anchor the manifest holds twice (`duplicate_id`, or
  `manifest_id` where the manifest's own ID repeats one) and the rules of
  [Named MatchStamps](#named-matchstamps). It reads nothing else of
  `graphical`, for a library that keeps the styles, the rules and the
  ordinary timestamps unread: a timestamp that is no object or holds no
  string ID is passed over.
- `pairs`, `entries`, `candidates`, `with_pair`, `without_pair`,
  `with_candidate` and `with_belief` read and edit the pairs and
  provenance of a subject, which `subject_path` finds by its ID:
  `with_pair(…, actor=, date=)` records the person stating a pair with
  the belief `true`, `with_candidate` adds a candidate, `with_belief`
  records an actor's belief without changing what is stated, and
  `candidates(…, actor=)` leaves out what that actor believes `false`;
  `subjects` walks every element that may carry statements with its path
  and kind, the manifest first, then root by root the timeline, its
  regions and its children, depth first; `with_context` writes the manifest's `@context`, the format's terms in
  `FORMAT_CONTEXT` and the prefixes the statements use; `same_pair`,
  `expand_iri` and `used_prefixes` serve them (the description
  specification, section 11). `BELIEFS` holds the three words of a
  belief, `("true", "false", "unlikely")`, `BELIEF_STATES` the four states
  of the belief filter and `DEFAULT_BELIEFS` the three it keeps by
  default, and `check_belief_filter(beliefs)` checks a filter ([Provenance
  and beliefs](#provenance-and-beliefs)). They live in
  `timetoshare.statements`, and the package exports them.
- `load_catalogue()` returns the shipped catalogue and
  `read_catalogue(document)` reads another; `recognize`, `instantiate`,
  `verb_of` and `rectangles` read an address, a verb, a pair and a
  subject's pairs through it (the description specification, section 10).
  They live in `timetoshare.catalogue`.
- `complete(value)` and `minimal(value)` return a copy of a manifest in the
  complete or the minimal form; the input is not changed.
- `dumps(value, serialization="yaml")` returns the text of a manifest, or
  of any JSON value, in canonical YAML (`"yaml"`), pretty JSON (`"json"`)
  or RFC 8785 JSON (`"jcs"`) ([Serializations](#serializations)), a
  manifest put in canonical order and its own-axis values respelled first.
  It writes the form it is given. It raises `ValueError` for a value the
  serialization refuses: a NaN or an infinity, a string or key with a lone
  surrogate, a key whose canonical YAML form is longer than 1024 UTF-16
  code units, and in `"jcs"` an integer beyond ±(2^53 − 1) or an integral
  float of magnitude from 2^53 up to but excluding 10^21; `ValueError`
  for a manifest that cannot be put in [canonical
  order](#canonical-order); `ValueError` for a value deeper than 256
  ([Reading](#reading)), so that every value that can be written can be
  read; `ValueError` for an unknown `serialization`; and `TypeError` for a
  value that is not JSON.
- `serialization_of(text)` returns `"yaml"`, `"json"` or `"jcs"`, the
  serialization of a text ([Reading](#reading)).
- `file_form(text)` returns the `FileForm` of a manifest's text, a frozen
  dataclass of `minimal`, `styling` and `serialization`, and
  `dumps_file(value, form)` writes a manifest back in it ([Forms and
  defaults for applications](#forms-and-defaults-for-applications));
  `dumps_file(loads(text), file_form(text))` gives back every text a
  writer wrote. `SERIALIZATIONS` is `("yaml", "json", "jcs")`.
- `canonical_order(value)` returns a deep copy with the manifest's arrays in
  canonical order.
- `TIMESTAMP_DISPLAY` holds the words of a named timestamp's `display`,
  `("wedge", "name", "id", "coordinate", "cross_section")`, in canonical
  order, and `ANCHOR_DISPLAY` those of an alignment anchor's `display`,
  `("line", "name")`.
- `identity_problems(value)` returns every violation of the identity rules in
  a schema-valid manifest, in the order described above; `validate` raises
  the first.
- `to_file_id(id)` writes an ID as it stands in a file, with a leading `#`,
  and `from_file_id(value)` strips one leading `#`; `with_file_ids(manifest)`
  returns a copy of a manifest whose every ID and reference is written
  `#`-first, and `with_bare_ids(manifest)` the copy with every one bare
  ([Written in a file](#written-in-a-file)). They live in `timetoshare.ids`.
- `complete_styles(graphical)` returns `(completed, missing)` and warns with
  `MissingStyleWarning` when `missing` is non-empty.
- `SCHEMA_VERSION` is `"0.2.0"`, the one version the package reads, and
  `UNITS` the unit table ([The timeline](#the-timeline)).
- `schema_path()` returns the path of the manifest document and
  `provenance_schema_path()` that of the provenance document beside it;
  `load_schema()` returns the manifest document with the provenance
  document bundled into it, so that every reference is local.
- `timetoshare.tables`, which needs the extra `tables`
  (`pip install "timetoshare[tables]"`, which installs pyarrow), reads
  the two tables as Arrow tables ([Resources and
  tables](#resources-and-tables)). `tables_path()` returns the path of
  `tables.json` (`TABLES_DOCUMENT`), from which `MATCH_CLAIM_SCHEMA` and
  `PROJECTION_SCHEMA` declare their columns, `MATCH_CLAIM_REQUIRED` and
  `PROJECTION_REQUIRED` name the columns that hold no null, and
  `NUMBER_TYPE`, `COORDINATE_TYPE`, `ANCHOR_TYPE`, `PROJECTION_OF_TYPE`
  and `PROVENANCE_TYPE` declare the struct types; `NUMBER_KEYS` holds a
  number's members and `NUMBER_MEMBERS` the members each number type
  fills; `number_cell(value, number_type)` writes a number's
  members, raising `ValueError` for a value its number type does not
  hold (a float where an exact number belongs, a float that is not
  finite, a Fraction on a `float` axis or an integer no double holds
  there, a Fraction that is no integer on an `int` axis, an exact number
  beyond 64-bit integers), and `coordinate_value(cell, number_type=None)`
  reads its exact value back; `match_claim_problems(table,
  manifest=None)` and `projection_problems(table, manifest=None)` list
  every problem of a table, the table's own first, then row by row, each a
  `TableProblem` (`code`, `row`, `column`, `message`), checked against the
  manifest's timelines where one is given, and `check_match_claims` and
  `check_projections` raise the first as a `TableError` ([Checking the
  tables](#checking-the-tables) gives every rule);
  `check_succession` and `succession_problems` check the succession rule;
  `row_provenance(table)` gives each row's provenance, its own or the
  file's. `alignment_anchors`, `potential_matchstamps` and
  `believed_rows` derive the unique anchors and the potential MatchStamps
  of a MatchClaim table under the belief filter ([From MatchClaims to
  anchors](#from-matchclaims-to-anchors)), a reference derivation for
  conformance; each takes a `believer`, the `beliefs` it keeps (by
  default `DEFAULT_BELIEFS`) and the `context` under which actors
  expand. `fixture_path(name)` returns a file of the table fixture
  ([Fixtures](#fixtures)).
- `fixture_paths()` returns the bundled accepted fixtures,
  `rejection_paths()` the bundled rejection cases and `warning_paths()` the
  bundled warning cases; they live in the module `timetoshare.fixtures`, and
  the package exports them. `rejection_case(path)` reads one rejection case as a
  `RejectionCase` (`manifest`, `path`, `code`, `error`, `reason`), with the
  non-finite number a finite-rule case names put in place.
  `rdf_expectation(path)` returns the path of the canonical N-Quads
  expected of a statement fixture or its minimal twin.
- `FONT_FILES` names the bundled TrueType files, DejaVu Sans first and Noto
  Music second; `font_paths()` returns their paths in that order, and
  `font_metrics()` returns the merged advance-width metrics of both.

### TypeScript

`JSON.parse` cannot preserve every distinction in the format: it reads `2.0`
as the integer `2`, rounds integers beyond 2^53, and changes the enumeration
order of array-index keys. Use the package's readers, which read every
serialization without losing either:

```ts
import {
  dumpsFile,
  fileForm,
  parse,
  SchemaValidationError,
} from "@timetoalign/timetoshare";

const text = `timelines:
  -
    id: "#piece"
    length: [32, 1]
    unit: quarters
timetoshare: "0.2.0"
`;

function rewrite(text: string): string {
  try {
    return dumpsFile(parse(text), fileForm(text));
  } catch (error) {
    if (error instanceof SchemaValidationError) {
      console.error(error.code, error.path);
    }
    throw error;
  }
}

rewrite(text) === text; // true: the text is canonical YAML
```

- `loads(text)` reads a text in any serialization, JSON or YAML, as
  [Reading](#reading) states, after removing one U+FEFF at position 0,
  without losing a number or key order and without validating. It reads
  YAML with the `yaml` package under its core schema.
- `parse(text)` is `loads(text)` followed by `validate`: it reads a
  manifest in any serialization, validates it and returns it as a
  `LosslessManifest`.
- `parseJson(text)` reads a text as JSON and `parseYaml(text)` as YAML,
  whatever its first character, each as [Reading](#reading) states for
  its language, after removing one U+FEFF at position 0 as `loads` and
  `parse` do, without losing a number or key order and without
  validating.
- For a text the reading rules refuse, the readers throw
  `JsonSyntaxError` when it is read as JSON, a `SyntaxError` with the
  `offset` (in UTF-16 code units, counted from 0), `line` and `column`
  (counted from 1, the column in code points) of the fault, and
  `YamlSyntaxError` for every refusal
  of a text read as YAML, a `SyntaxError` with the same three fields. A
  JSON number that rounds to an infinity, such as `1e309`, throws a
  `RangeError`. `dumps` throws a `RangeError` for a value deeper than 256,
  so that every value that can be written can be read.
- `validate(value)` asserts that an unknown value is a
  `LosslessManifest` (its numbers may be bigints and `JsonFloat`s),
  checking it as Python's `validate` does; its `SchemaValidationError` carries the same
  `code` (typed `ValidationCode`), a `path` and a `detail`.
- `unknownKeys(value)` returns the same list as Python's `unknown_keys`,
  and `manifestWarnings(value)` the same list as Python's
  `manifest_warnings`.
- `statementProblems(value)` returns the problems of the statements
  alone, as Python's `statement_problems` does, with the same codes,
  paths and messages, a `schema` problem's included.
- `matchstampProblems(value)` returns the problems of the named
  MatchStamps and match timestamps alone, as Python's
  `matchstamp_problems` does, with the same codes, paths and messages, a
  `schema` problem's included.
- `pairs`, `entries`, `candidates`, `withPair`, `withoutPair`,
  `withCandidate`, `withBelief`, `subjectPath`, `subjects`,
  `withContext`, `samePair`, `expandIri` and `usedPrefixes` do what Python's functions of
  `timetoshare.statements` do, with the same messages, their keyword
  arguments in an options object (`withPair(manifest, subject, property,
  value, { actor, date })`); `BELIEFS` holds the same three words,
  `BELIEF_STATES` and `DEFAULT_BELIEFS` the same states, typed
  `BeliefState`, and `checkBeliefFilter` checks a filter as
  `check_belief_filter` does;
  `defaultCatalogue()`, `readCatalogue`, `recognize`, `instantiate`,
  `verbOf` and `rectangles` what those of `timetoshare.catalogue` do.
- `complete(value)` and `minimal(value)` return the complete and the minimal
  form, as Python's functions do, keeping every number and key order
  `loads` read. The typed forms say which form a value is in:
  `completeManifest(value: LosslessManifest): CompleteManifest`,
  `minimalManifest(value): LosslessManifest` and
  `canonicalManifest(value)`, which returns its argument's type in canonical
  order.
- `dumps(value, { serialization })` writes a manifest, or any JSON value,
  as Python's `dumps` does, in `"yaml"` (the default), `"json"` or `"jcs"`
  ([Serializations](#serializations)). It throws a `RangeError` for a
  value the serialization refuses (a NaN or an infinity, a string or key
  with a lone surrogate, a key whose canonical YAML form is longer than
  1024 UTF-16 code units, and in `"jcs"` an integer beyond ±(2^53 − 1) or
  an integral float of magnitude from 2^53 up to but excluding 10^21) and
  for an unknown `serialization`, and a `TypeError` for a manifest that
  cannot be put in [canonical order](#canonical-order) and for a value
  that is not JSON.
- `serializationOf(text)` returns `"yaml"`, `"json"` or `"jcs"`, as
  Python's `serialization_of` does.
- `fileForm(text)` returns a text's `FileForm` (`minimal`, `styling`,
  `serialization`, all read-only) and `dumpsFile(value, form)` writes a
  manifest back in it, as Python's `file_form` and `dumps_file` do.
  `SERIALIZATIONS` is `["yaml", "json", "jcs"]`, and `isSerialization(value)`
  tells whether a value is one of them.
- `compactJson(value)` writes JSON without whitespace, every object's keys
  in their own order and numbers spelled as in [Shared
  spelling](#shared-spelling); it is a utility, not a serialization of the
  format. `compactSortedJson(value)` writes it likewise with every
  object's keys sorted by code point at every depth, so that two values
  `loads` reads alike give the same text.
- `canonicalOrder(value)` returns a deep copy with the manifest's arrays in
  canonical order.
- `TIMESTAMP_DISPLAY` holds the words of a named timestamp's `display`,
  `["wedge", "name", "id", "coordinate", "cross_section"]`, and
  `ANCHOR_DISPLAY` those of an alignment anchor's, `["line", "name"]`, in
  canonical order, as Python's constants do.
- `identityProblems(value)` returns the same identity problems as Python's
  `identity_problems`.
- `toFileId(id)`, `fromFileId(value)`, `withFileIds(manifest)` and
  `withBareIds(manifest)` do what Python's `to_file_id`, `from_file_id`,
  `with_file_ids` and `with_bare_ids` do.
- `completeStyles(graphical)` returns `{graphical: completed, missing}`,
  the copy keeping every number as `loads` read it (a `JsonFloat` stays
  one).
- `FONT_FILES` names the bundled TrueType files, as Python's constant does,
  and `fontMetrics` contains the merged advance-width metrics of both.
- `UNITS` holds the unit table as Python's does ([The
  timeline](#the-timeline)). `exactValue(value)` returns the exact value
  of a number as the format writes one, a JSON number or a `[numerator,
  denominator]` pair in any terms (its members integers or integral
  floats, its denominator at least 1), as a `Rational` of two bigints, or
  `null` for a value that is none; `jsonInteger(value)` returns the
  integer a JSON number states, an integral float included, or `null`.
- `SCHEMA_VERSION` is `"0.2.0"`, and `schema` holds the schema document.
  The generated types are generated from it, with the root type
  `Manifest` and one type per definition, such as `Timeline`, `Group`
  and `Graphical`. Beside each definition with defaults a complete form is
  generated, `CompleteManifest`, `CompleteTimeline`, `CompleteGroup`,
  `CompleteTimestamp` (whose `display` is required) and so on, in which every key with a default is required at every depth and
  every number is a `JsonNumber`; keys whose default is their absence (the
  manifest's `id` and `graphical`, a root's `offset`) stay optional.
  `LosslessManifest` is `Lossless<Manifest>`.

A number read by `loads`, `parseJson` or `parseYaml` is a `JsonNumber`:

| Number as written | `JsonNumber` |
| --- | --- |
| an integer within ±(2^53 − 1), such as `480` | a `number` |
| an integer beyond that range, such as `9007199254740993` | a `bigint` |
| a float with a fractional part, such as `0.5` | a `number` |
| an integral float, such as `2.0`, `1.0e+16`, or `-0.0` | a `JsonFloat` |

`Lossless<T>` replaces every `number` in `T` with `JsonNumber` and keeps
tuples, so a Fraction is `[JsonNumber, JsonNumber]`. An integral plain
`number` is the integer of its exact value: `-0` is the integer 0, and
`1e300` a 301-digit integer, which RFC 8785 JSON therefore refuses. A
float whose value is an integer must be passed as `new JsonFloat(2)`, not as `2`, if it is
to be written as a float. JavaScript code that writes manifests must use
`dumps`, not `JSON.stringify`.

## Versioning

The packages read the current version only. A value declaring any other
version raises `UnsupportedVersionError`, and neither package migrates a
value from one version to another. The repository holds the current
version only; a version a later one replaces lives in the git history at
its tag and in the packages released with it.

A TimeToShare release is a schema-version event: one `vX.Y.Z` tag publishes
both packages through trusted publishing and publishes the version's
documents at both their addresses ([The schema
document](#the-schema-document)); `scripts/check_published.py` checks those
addresses. `scripts/check_versions.py` checks that all
version declarations agree.

## Fixtures

The [fixture guide](fixtures/README.md) describes the generated manifests
and the drawings, the hand-authored rejection cases, the warning cases,
and the acceptance table of own-axis values
(`fixtures/acceptances/0.2.0/numbers.yaml`, [Values on a timeline's own
axis](#values-on-a-timelines-own-axis)).
Every accepted fixture is written in canonical YAML (`.yaml`), the complete
form beside its minimal twin (`.minimal.yaml`). The manifests are emitted
only by timetoalign through the catalogue of builders in
`scripts/fixtures/`, whose CLI is `scripts/emit_fixtures.py`. Do not edit
them by hand. The statement fixtures under `fixtures/0.2.0/statements/`
have their expected RDF under `fixtures/rdf/0.2.0/`, canonical N-Quads
that `scripts/emit_rdf.py` writes. The table fixture lies apart, under
`fixtures/tables/0.2.0/`: a manifest (`manifest.yaml`), its MatchClaim
table (`match_claims.parquet`), its Projections table
(`projections.parquet`) and the alignment anchors and potential
MatchStamps expected of the MatchClaim table (`expected.yaml`), every
value written by hand in `scripts/emit_tables.py`, which alone writes
them; the expected values are literal data, never computed by the
derivation they test. The rejection and warning cases are
written in canonical YAML too; a case about JSON text itself would be
written in JSON, and none is at present.

`fixtures/serializations/` holds the serialization cases, derived by hand
from [Serializations](#serializations), never written with `dumps`, which
they test:

| Path | Holds |
| --- | --- |
| `cases/<name>/canonical.yaml`, `cases/<name>/pretty.json`, `cases/<name>/rfc8785.json` | one value in each of the three serializations; a missing `rfc8785.json` means that the RFC 8785 writer refuses the value |
| `readings/<name>.<ext>` | a text that is not canonical and that every reader reads to the same value, `<ext>` being `yaml` or `json`: JSON in any layout, or YAML using only the constructs of canonical YAML ([Reading](#reading)); the readings are the files of `readings/` whose names end neither in `.expected.yaml` nor in `.expected.rfc8785.json` |
| `readings/<name>.expected.yaml` | the canonical YAML of the value that text is read as |
| `readings/<name>.expected.rfc8785.json` | optional; an expected output, read as RFC 8785 JSON (`serialization_of` gives `"jcs"`), not a reading: the RFC 8785 JSON written from the value that text is read as, with no final line feed; it exists for readings whose value is not yet in canonical spelling (for example an unreduced Fraction pair), since RFC 8785 JSON is written after canonical order and respelling |
| `refusals/<name>.<ext>` | a text that every reader refuses, by a refusal that the rules of [Reading](#reading) decide |
| `refusals-writing/<name>.<ext>` | a text every reader reads, whose value a writer refuses |

The cases include texts at depth 256, which every reader reads, texts at
depth 257, which every reader refuses, and a value of depth 257, which every
writer refuses ([Shared spelling](#shared-spelling)).

Both packages write every text of a case byte for byte, read every reading
to its expected value, write that value with `dumps(..., serialization="jcs")`
to the bytes of its `.expected.rfc8785.json` where one exists, refuse every
refused text, and refuse to write
each value of `refusals-writing/` in the serializations that
`fixtures/serializations/README.md` names for it. The bytes of these files, carriage
returns and final line feeds included, are significant, so
`.gitattributes` marks `fixtures/serializations/** -text` and git keeps
them as they are.

`fixtures/file_forms/` holds the file-form cases, written by hand from
[Forms and defaults for
applications](#forms-and-defaults-for-applications): each text
`<name>.<ext>` beside the `<name>.expected.<ext>` that `dumps_file`
writes back in its inferred file form. The texts cover a manifest
neither minimal nor complete, JSON on one line, canonical YAML with
carriage returns, and RFC 8785 JSON on a float axis whose integral floats
are written as integers, once minimal and once with a default stated;
[`fixtures/README.md`](fixtures/README.md) lists them. Both packages
infer the same form for each text and write the same bytes. Its bytes
are significant too (`fixtures/file_forms/** -text`).

## Development

Clone the repository, then run the package commands in their directories:

```bash
cd python
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv build
```

```bash
cd ../js
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm generate
pnpm build
```

To regenerate the metrics table of the two fonts, run this from `python/`:

```bash
uv run python ../scripts/extract_font_metrics.py
```

To re-emit the fixtures, use an interpreter containing the timetoalign
revision being represented:

```bash
python scripts/emit_fixtures.py --timetoalign-commit "$(git -C /path/to/timetoalign rev-parse --short HEAD)"
```

then write the expected RDF of the statement fixtures from `python/`:

```bash
uv run python ../scripts/emit_rdf.py
```

and the table fixture, also from `python/`:

```bash
uv run python ../scripts/emit_tables.py
```

Each of the three scripts refuses to overwrite the files of a version
whose `v<version>` tag exists.

From the repository root, check version declarations with:

```bash
python3 scripts/check_versions.py
```

and the documents a release publishes, with their `$id`s and references
([The schema document](#the-schema-document)), with:

```bash
python3 scripts/check_published.py
```

## Releasing

See the
[contribution guide](https://github.com/TimeToAlign/TimeToShare/blob/main/CONTRIBUTING.md)
for the required version updates, checks, tag, and trusted-publishing
configuration.

## License

[MIT](https://github.com/TimeToAlign/TimeToShare/blob/main/LICENSE).
The bundled fonts keep their own licences: `fonts/DejaVuSans-LICENSE`
(the Bitstream Vera and Arev font licences) and `fonts/NotoMusic-LICENSE`
(the SIL Open Font License 1.1).
