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
under one shared path rule and list unknown keys and unregistered terms as
warnings, the complete and the minimal form of a manifest, a canonical
order, standard writers that produce the same bytes in Python and
TypeScript, a lossless JSON reader for TypeScript, generated TypeScript
types, and shared fixtures. It also specifies how a manifest is drawn and
how a manifest links its content to works, editions, recordings and
agents, with a registry of identifier schemes that turns catalogue
addresses into links; both packages ship both specifications and the
registry.

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
{"timetoshare": "0.2.0", "timelines": [{"id": "piece", "unit": "quarters", "length": [32, 1]}]}
```

| Member | Required | Holds |
| --- | --- | --- |
| `timetoshare` | yes | the version marker, `"0.2.0"` |
| `timelines` | yes | the root timelines, an array that may be empty |
| `id` | no | the manifest's ID |
| `name` | no | the manifest's displayed name |
| `meta` | no | an object of anything an application wants to record |
| `groups` | no | timeline groups whose members name timelines of the manifest |
| `measure_maps` | no | the MeasureMaps the conversion maps read, each with an ID; they belong to no timeline |
| `schemes` | no | the identifier schemes the manifest's links name by ID ([Describing a manifest](#describing-a-manifest)) |
| `links` | no | the links of the manifest as a whole to external entities ([Describing a manifest](#describing-a-manifest)) |
| `graphical` | no | the styling of the manifest's drawing, its groups' display orders and its timelines' band orders |
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
timelines from wherever they live. This version of the format holds no
events itself.

### The timeline

A timeline (`$defs/Timeline`) requires `id`, `unit` and `length`. Its
optional keys are `name`, `number_type`, `offset`, `locked`,
`is_segment_line`, `meta`, `children`, `conversion_maps`, `regions`,
`flow_control` and `links`.

- `unit` decides the timeline's domain (logical, physical or graphical)
  and modality (continuous or discrete), since each unit belongs to exactly
  one of the six combinations, and the default of its number type:

  | Unit | Domain | Modality | Default number type |
  | --- | --- | --- | --- |
  | `number`, `floating_measures` | logical | continuous | `float` |
  | `whole_notes`, `quarters` | logical | continuous | `fraction` |
  | `ticks` | logical | discrete | `int` |
  | `milliseconds`, `seconds`, `minutes` | physical | continuous | `float` |
  | `samples`, `frames` | physical | discrete | `int` |
  | `pixels` | graphical | discrete | `int` |
  | `meters`, `centimeters`, `millimeters`, `inches`, `points` | graphical | continuous | `float` |

  The domain and modality decide the timeline's class (`seconds` makes a
  `ContinuousPhysicalTimeline`), which a timeline never writes.
- `number_type` is `int`, `float` or `fraction`; absent, it is the unit's
  default number type above.
- `length` is the timeline's length on its own axis, or `null` when it is
  not known (section [Unknown length](#unknown-length)).
- `children` is an array of timelines, each carrying its `offset` on the
  parent's axis, written in offset order with ties by ID; a child shares
  its parent's `unit`, here `seconds`:

  ```json
  "children": [{"id": "perf", "offset": 4.0, "unit": "seconds", "length": 1503.2}]
  ```

  A child requires `offset`. The schema and both validators accept a
  negative offset, a child starting before its parent's 0; timetoalign and
  TimeLineEditor do not support it yet and refuse it (`A negative child
  offset is not supported yet: …`). Where its
  parent's length is known, a child starts at or before the parent's end
  and ends at or before it, locked or not: no child reaches past a known
  length. A root may carry an `offset` too, negative included:
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
  offset order to its length, all sharing its unit as every child does,
  and all with one `is_segment_line` value. Segments that are segment lines
  themselves make a nested segment line.
- `conversion_maps`, `regions`, `flow_control` and `links` hold the
  timeline's conversion maps ([Conversion maps and
  MeasureMaps](#conversion-maps-and-measuremaps)), regions (`{id, name?, start,
  end, meta?, links?}`), flow-control elements ([Flow control](#flow-control))
  and links to external entities ([Describing a
  manifest](#describing-a-manifest)).

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

The declared number type decides how a value is read, never its spelling,
and a reader coerces: `2.0` on an `int` axis is the integer 2, `2` on a
`float` axis the float 2.0, and `[1, 8.0]` the Fraction 1/8. A JSON round
trip that respells numbers therefore never invalidates a manifest. Writers
spell every value canonically: an int as a JSON integer, a float as
Python's `repr` spells it, Fraction members as JSON integers. What a value
cannot be read as stays refused: a number with a fractional part on an
`int` axis, an integer that no float equals exactly on a `float` axis, a
Fraction pair on an `int` or `float` axis and a bare number on a
`fraction` axis, each with the code `representation`; and a Fraction
member with a fractional part or a denominator below 1, which the schema
refuses. The schema types own-axis values as `Number`; both validators then
check the representation and report a mismatch such as
`length 32 of 'score' is an int on a fraction axis: write [32, 1]`, or, for
an integer no float holds exactly,
`length 9007199254740993 of 'take' is an int on a float axis: write a float`.
Every number of a manifest is finite: JSON spells no NaN or infinity, but a
value built in memory, or read by a lenient reader, may hold one, and both
validators refuse it at its path.

A conversion map's numbers and a MeasureMap row's lengths are numbers of
the same kind, each a JSON number or a Fraction pair. The self-describing
coordinate object `{unit, number_type, value}` (`$defs/Coordinate`) serves
a position outside such a container, as hosts exchange single positions;
inside a manifest every position lies on an axis its container declares.

### Defaults

Every key of this table is optional, and readers supply its default when it
is absent. Writers write the **complete form**: every key of the table,
its default included (`null`, `{}`, `[]`), except the keys whose default is
"absent", which are written only with a value. Asked for the **minimal
form**, they omit exactly the keys whose value is the default, equal to it
in JSON type and value: `repeat_count: 1.0` is a float, not the integer
default `1`, and stays. Either form
reads to the same objects, and each writes back to itself. `length` is
required in both forms.

| Object | Key: default |
| --- | --- |
| manifest | `id`: absent (without a `name` too, an anonymous bundle); `name`: `null`; `meta`: `{}`; `groups`, `measure_maps`, `schemes`, `links`: `[]`; `graphical`: absent |
| timeline | `name`: `null`; `number_type`: the unit's default (the unit table of [The timeline](#the-timeline)); `offset`: absent on a root, required on a child; `locked`: `false`; `is_segment_line`: `false`; `meta`: `{}`; `children`, `conversion_maps`, `regions`, `flow_control`, `links`: `[]` |
| region | `name`: `null`; `meta`: `{}`; `links`: `[]` |
| flow-control element (`flow_control_element`) | `name`, `label`: `null`; `meta`: `{}` |
| a `repeat_end` besides (`repeat_end`) | `repeat_count`: 1 |
| conversion map (`conversion_map`) | `name`: `null` |
| a `LinearMap` besides (`linear_map`) | `scalar`: 1; `offset`: 0 |
| a `TableMap` besides (`table_map`) | `kind`: `"linear"`; `extrapolate`: `"none"` |
| MeasureMap (`measure_map`) | `name`: `null`; `meta`: `{}` |
| group | `name`: `null`; `meta`: `{}` |
| graphical | `styles`: `{}`; `statements`: `[]`; `order`: `{}`; `timestamps`: `[]` |
| named timestamp (`timestamp`) | `display`: `["wedge", "name", "cross_section"]` |
| scheme | `name`, `criteria`: `null`; `uri`: `[]` |
| link | `uri`, `identifiers`, `records`, `parts`, `part_of`: `[]`; `label`, `assertion`, `parts_relation`: `null`; `parts_ordered`: `true` |
| record (`descriptor`) | `media_type`, `size`, `integrity`: `null` |
| assertion | `asserted_by`, `based_on`: `[]`; `asserted_on`, `method`, `service`, `match`, `status`: `null` |
| part slot (`part_slot`) | `uri`, `identifiers`, `represented_by`: `[]`; `label`, `absent`, `assertion`: `null` |
| `part_of` entry (`part_of`) | `uri`, `identifiers`: `[]`; `label`, `position`, `assertion`: `null` |

An identifier `{scheme, value}` has no default. A row marked "besides"
adds its keys to those of the general row it follows: a `repeat_end` has the keys of every flow-control element plus
`repeat_count`, which no other element carries, and a `LinearMap` or a
`TableMap` the keys of every conversion map plus its own, at any depth of
nesting. The names in
parentheses are the kinds of the packages' `DEFAULTS` table.
Python's `complete(value)` and npm's `complete(value)` return a copy of a
manifest in the complete form, and `minimal(value)` in both packages a copy
in the minimal form; both are pure and read the one table above.
timetoalign's `to_dict()` writes the complete form, and
`to_dict(minimal=True)` the minimal one.

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
is a child keeps its parent.

`graphical` is `{styles?, statements?, order?, timestamps?}`, at the
manifest's top level only, never on a timeline: a timeline holds time, and
what is graphical lies in this object. `styles` and `statements` style the
drawing ([Drawing a manifest](#drawing-a-manifest)). `timestamps` lists the
**named timestamps**, each `{id, timeline, coordinate, name, display?}`: a
position `coordinate` on the own axis of the timeline `timeline`, a root or
a descendant at any depth, a segment included, written as that timeline's
number type selects ([Values on a timeline's own axis](#values-on-a-timelines-own-axis)),
from its zero to its `length` (only from its zero when the length is
`null`), and named `name`, a non-empty string. Only that coordinate is
stored, never a map's value at it. `display` lists what the timestamp
draws, distinct words from `wedge` (its coordinate marker), `name`, `id`
and `coordinate` (its labels, stacked beyond the wedge in this order: its
name, its ID, its coordinate with its unit) and `cross_section` (a vertical
line across its timeline's line, children band and conversion maps band);
its order means nothing and writers write it in the order just given. A
timestamp draws by default its wedge, its name and its cross-section line
(the drawing specification, sections 2, 6.4 and 6.6). `order` maps the ID of a group
or of a timeline to the order of what it stacks, top to bottom, and
writers never reorder it:

- a group's ID to the **display order** of its members, a permutation of
  their IDs; a group without an entry is displayed in the order of
  `members`;
- a timeline's ID, of a root or a descendant, to its **band order**, a
  permutation of `line`, the timeline's own line, and of its five facets
  `markers`, `conversion_maps`, `children`, `regions` and `flow_control`,
  each drawn as a band: the bands before `line` lie above the line, the
  nearest last, and those after it below, the nearest first. A timeline
  without an entry follows its parent's band order, a member that is a
  child included, and a root without one the default
  `["children", "conversion_maps", "line", "markers", "regions",
  "flow_control"]`; changing a timeline's band order so changes that of
  every descendant without an entry of its own.

```json
"order": {"score": ["children", "markers", "line", "conversion_maps", "regions", "flow_control"]}
```

draws the coordinate markers of `score`, the wedges and labels of its named
timestamps, against its line above it, its children beyond them, and its
conversion maps against its line below it;
its descendants follow it, so their conversion maps lie below their lines
too. A manifest carries no MatchClaims.

### Unknown keys

Every object of the schema is open: the schema closes none and carries no
custom keyword, so a key an object does not declare is valid. Both
packages' validators find such keys themselves and report them as
**unknown keys**, except inside `meta`, the one free object. Unknown keys
are warnings, never errors, since a misspelt optional
key would otherwise silently become its default. Python's
`unknown_keys(value)` and npm's `unknownKeys(value)` return the same list of
`{path, key}` entries, the path locating the object that holds the key,
sorted by path and then by key; `validate` raises only on errors. timetoalign
and TimeLineEditor keep the unknown keys of a manifest they read and write
them back. A key that a host schema declares beside its `$ref` to a
TimeToShare definition is reported as unknown by these validators; the
host's own validator is unaffected.

### Identity

Every timeline, group, MeasureMap, conversion map, region,
flow-control element, named timestamp and scheme carries an `id`, which
identifies it, and so may the manifest. A `name`, where an element has
one, is what is displayed, and it may repeat. An ID is any non-empty string without control characters
(U+0000 to U+001F): `/`, spaces, colons and URIs are allowed. Every ID is
unique across the whole manifest: the manifest's own, and the IDs of every
timeline (root or descendant), group, MeasureMap, conversion map at any
depth of nesting, region, flow-control element, named timestamp and
scheme. A named timestamp's ID has one shape, `timestamp_` followed by a
positive integer without leading zeros. An ID is never parsed
and never composed with another. A reference is an ID: a jump origin's
`target` names a jump target of the same timeline, a measure view's
`measure_map` an entry of `measure_maps`, a group's `members` name
timelines of the manifest, a key of `graphical.order` a group or a
timeline, a named timestamp's `timeline` a timeline of the manifest, a
part slot's `represented_by` timelines and regions of the manifest, and an
identifier's `scheme` a scheme of the manifest unless it is an absolute
URI.

timetoalign and TimeLineEditor mint a speaking default `{prefix}_{N}` for
an element created without an ID, such as `clt_1` or `region_1`, `N` the
smallest positive integer whose ID the manifest does not hold; an ID that
is given is kept verbatim. An ID that is an
absolute URI identifies its element globally. A manifest published at a
stable location gives every local ID a global identity too: the
manifest's URI with the ID as its fragment, `<manifest location>#<id>`.

The drawing addresses its elements by **address objects** `{id?, facet?,
part?}` built from these IDs and compared as whole objects, never by
strings composed from them; the band drawing the regions facet of a
timeline `T`, for instance, is `{"id": T, "facet": "regions"}`. The
drawing specification, section 2.2, gives every form.

The JSON Schema cannot express that IDs are unique, nor that a reference
names an element, nor that a map converts from its timeline's unit or its
holder's, nor that a map's arrays agree, nor that a member names a timeline
of the manifest, nor that no member of a group lies inside another, nor
that a child lies within its parent's known length, nor that a segment
line's segments are contiguous and alike, nor that a named timestamp lies
on a timeline of the manifest and within it, nor that an assertion's date
names a day of the calendar, nor the representation of own-axis values,
so both validators check them after the schema. Each
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
| A group ID, a MeasureMap ID, a named timestamp's ID or a scheme ID repeats an earlier ID of the manifest | `duplicate_id` | the group's, the MeasureMap's, the timestamp's or the scheme's `id` | `'<id>' is not unique in the manifest, first at <pointer>` |
| The manifest's ID repeats another ID of the manifest | `manifest_id` | `id` | `'<id>' is not unique in the manifest, first at <pointer>`, the pointer naming the first occurrence of that ID |
| A member names no timeline of the manifest | `group_member` | the member | `'<id>' names no timeline of this manifest` |
| A member lies inside an earlier member of its group, or contains one | `group_member` | the later member | `member '<id>' lies inside member '<earlier id>' of the same group` (`… contains member …`) |
| A key of `graphical.order` names no group and no timeline | `order_key` | the key | `'<key>' names no group or timeline of this manifest` |
| An entry of a display order is not a member of its group | `display_order` | the entry | `'<id>' is not a member of group '<group id>'` |
| A member of a group is missing from its display order | `display_order` | the order | `member '<id>' of group '<group id>' is missing` |
| An entry of a band order is neither `line` nor a facet | `band_order` | the entry | `'<entry>' is not 'line' or a facet, in the band order of '<id>'` |
| A facet, or `line`, is missing from its band order | `band_order` | the order | `'<entry>' is missing from the band order of '<id>'` |
| A named timestamp's `timeline` names no timeline of the manifest | `timestamp_timeline` | the `timeline` | `'<id>' names no timeline of this manifest` |
| A named timestamp's `coordinate` lies before 0, or beyond its timeline's known length | `timestamp_coordinate` | the `coordinate` | `coordinate <value> of '<id>' lies before the start of its timeline '<id>'` (`… is beyond the length <length> of its timeline '<id>'`) |
| An assertion's `asserted_on` names no day of the Gregorian calendar, whose years run from 1 to 9999 | `calendar_date` | the `asserted_on` | `'<date>' is no Gregorian calendar date written YYYY-MM-DD` |
| An identifier's `scheme` names no scheme of the manifest and is no absolute URI | `dangling_target` | the `scheme` | `'<scheme>' names no scheme of this manifest and is no absolute URI` |
| A part slot's `represented_by` entry names no timeline (at any depth) or region of the manifest | `dangling_target` | the entry | `'<id>' names no timeline or region of this manifest` |

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
segments are visited in canonical order and compared by exact value. Across the manifest, the problems come in this
order: each root's own problems, roots in array order; then the IDs
repeated across roots (root by root, each ID of its tree in identity order,
the IDs of the maps other maps hold last), the group IDs, the MeasureMap
IDs, the named timestamps' IDs, the scheme IDs, the manifest's ID; members
(member by member: dangling, nested); the entries of `graphical.order` in
code-point order of their keys: an order's strangers first, in its order,
then its missing entries, in the order of the group's `members` or of the
default band order; then the named timestamps, in array order; and last
the dates and references of links, link by link, each link's assertion's
date and identifiers before those of its part slots and its `part_of`
entries (the description specification, section 8). A timestamp's
coordinate is an own-axis value of its timeline, so its representation is
checked as every such value is (`representation`, at its `coordinate`); a
timestamp naming no timeline is checked for its timeline alone. `<pointer>`
is a JSON pointer in URI fragment form, such as `#/timelines/0/id`, as Python's
`json_pointer(path)` and npm's `jsonPointer(path)` render a path. Both
packages write the messages above alike, an ID verbatim in single quotes
and every value spelled as the standard writer spells it (`720`,
`[19, 2]`, `75.0`). A child's end, its offset plus its length, or for a
segment of unknown length its successor's offset, is compared exactly and
spelled as its parent's number type writes it, or as a `[numerator,
denominator]` pair where that type cannot write it exactly. A repeated
entry within one display or band order or within one group's `members` is
refused by the schema.

### The schema document

Version 0.2.0 is one document, `schema/0.2.0/timetoshare.schema.json`,
with the identifier
`https://timetoalign.github.io/timetoshare/0.2.0/timetoshare.schema.json`,
so the document lies below `schema/` at the path of its identifier. Every
released version's document is served at its identifier and, by this
repository's own GitHub Pages site, at
`https://timetoalign.github.io/TimeToShare/0.2.0/timetoshare.schema.json`
(its version in place of `0.2.0`); the release workflow publishes both. Its
root is
`{"$ref": "#/$defs/Manifest"}`. These definitions are public and may be
embedded by a host schema; within 0.2.x they change only by addition:

`Manifest`, `Timeline`, `Group`, `Graphical`, `ConversionMap`,
`Coordinate`, `Number`, `Fraction`, `TimeUnit`, `NumberType`, `Id`,
`MeasureMap`, `MeasureMapRow`, `Link` and `Scheme`.

A host refers to the document, or to one definition as
`timetoshare.schema.json#/$defs/<Name>`, never through an `$anchor`. It
embeds either a whole manifest, version marker included, or a bare
`Timeline`, in which case the host records the TimeToShare version itself.

The schema is the source of truth for timetoalign and TimeLineEditor.
timetoalign's hand-written serialization is tested for schema conformance and
fixture round trips. TypeScript types are generated in this repository from
the one document.

## Describing a manifest

The manifest, every timeline at any depth and every region may carry
`links`, the manifest's **description layer**: typed relations to the
external entities their content is about, a work, an expression, a
manifestation or an item in the sense of the IFLA Library Reference
Model, or an agent. A link never states that its element is the entity.
It states that the element pertains to the entity, or in which role an
agent stands to it, and names the entity by URIs and by identifiers
`{scheme, value}`. It may point to records about the entity, carry an
assertion of who stated it, when and how, and list the entity's parts in
order, each represented by timelines and regions of the manifest or absent
for a stated reason. Readings that differ, such as two editions that
order the movements of a work differently, are separate links. A scheme
without a URI of its own, such as a composer's opus numbers, is declared
in the manifest's `schemes` and named by its ID:

```json
"schemes": [
  {"id": "mb_beethoven_opus", "name": "Works of Ludwig van Beethoven by opus number", "uri": ["https://musicbrainz.org/series/004f17aa-0f46-4fec-b939-c5dfc849e5c6"]}
],
"links": [
  {
    "relation": "pertains_to",
    "level": "work",
    "uri": ["http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284", "http://www.wikidata.org/entity/Q146730"],
    "identifiers": [{"scheme": "mb_beethoven_opus", "value": "op. 106"}],
    "label": "Piano Sonata No. 29 in B♭ major, Op. 106"
  }
]
```

The **registry of identifier schemes**, `registry/schemes.json`, lists
well-known schemes (MusicBrainz works, recordings and releases, Wikidata,
VIAF, GND, IMSLP and DOI) with the addresses each recognises. Python's
`Link.from_urls` and npm's `linkFromUrls` turn addresses copied from those
sites into links: `https://musicbrainz.org/work/…` gives the entity URI
`http://musicbrainz.org/work/…` at the level `work`, and an IMSLP page an
identifier in the scheme of IMSLP IDs. Each fact is stored once: an
identifier given in a scheme whose registry entry mints entity URIs, such
as a MusicBrainz work ID, is stored as its entity URI. The validators
never consult the registry.

Besides the shape of every link, the schema states two rules of parts: a
link whose `parts` is not empty states its `parts_relation`, and a link
without parts states no `parts_relation` and keeps `parts_ordered` true.
Both are refused with the code `schema`, the second at the
`parts_relation` or the `parts_ordered` it breaks. The dates and
references of links are checked after the schema, with the identity rules
([Identity](#identity)). Python's `description_problems(value)` and npm's
`descriptionProblems(value)` check the description layer alone, its
schemes and links against the schema and then these rules, and refuse
nothing outside it, so a library reading only part of a manifest checks
the layer without restating which parts of the manifest the rules read.
Words of the layer's open vocabularies that are not registered
are kept and listed as warnings by `unregistered_terms(value)` and
`unregisteredTerms(value)`, never refused. The
[description specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/description.md)
defines links, schemes, the registry, records, assertions, part readings,
wholes and absence, states what is refused and what is warned, works
through the bundle of Op. 106, and maps every term to Dublin Core,
schema.org, SKOS, PROV, the Web Annotation vocabulary, PREMIS and LRMoo.
Both packages contain the specification, the wheel as
`timetoshare/docs/description.md` and the npm package as
`@timetoalign/timetoshare/docs/description.md`, and the registry as
`registry/schemes.json` beside it.

## Drawing a manifest

The optional `graphical` object of a manifest contains named declarations
in `styles` and an ordered list of `statements`:

```json
"graphical": {
  "styles": {
    "highlight": {"stroke": "#7F00FF", "fill": "#7F00FF"}
  },
  "statements": [
    {"select": {"element": "label"}, "set": {"fill": "#404040"}},
    {"select": {"element": "wedge", "within": "performance"}, "set": "highlight"}
  ]
}
```

Each statement has a selector in `select` and either a declaration or a style
name in `set`. Statement order matters. The complete selectors, presentation
properties, cascade, defaults, element addresses, layout, and writer profiles
are defined by the
[drawing specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/drawing.md).

Every manifest is drawn as one block ([Containers](#containers)), opened
by its title: its `name`, or its `id` when it has no name; an anonymous
bundle has none. Each group is a frame; each ungrouped root lies in a card
of its own, and each member in one card in the frame of each group that
has it as a member; a member that is a child timeline is drawn with the
faded lines of its ancestors. The element types are the containers
`block`, `frame`, `card` and `band` (a band draws one of a timeline's five
facets and lies above or below its line as the timeline's band order
places it; a band that is not displayed hides everything it holds, and by
default the regions and flow control bands are hidden on every timeline
but the one a card holds), and the content `timeline`, `child`,
`boundary` (a segment's start on its segment line), `ancestor`, `map`,
`region`, `flow_marker` (a flow marker), `jump_from` (a jump origin, drawn
as an arc to its target or to the start; a jump target draws nothing),
`wedge` (a coordinate marker), `cross_section` (a named timestamp's
cross-section line), `name` and `label` (every other text, a named
timestamp's name among them). Besides `element`, a selector may name `addresses` (address
objects, each matched as a whole object), `domain`, `modality`, `class`
(the class a timeline's unit decides, such as
`ContinuousPhysicalTimeline` for `seconds`, or a conversion map's type),
`facet` (the bands drawing that facet), `within` (a timeline and its
descendants) and `inside` (an element type that holds the element at any
depth). The property `shadow` colours a card's offset shadow. The group
fixture `group_styled` frames its group in violet, fills the group's title
violet, and gives every card in a frame a light violet shadow:

```json
"graphical": {
  "order": {"group_1": ["score", "page", "performance"]},
  "statements": [
    {"select": {"element": "frame"}, "set": "frame-highlight"},
    {"select": {"element": "name", "addresses": [{"id": "group_1", "part": ["name"]}]}, "set": {"fill": "#7F00FF"}},
    {"select": {"element": "card", "inside": "frame"}, "set": {"rx": 2, "shadow": "#C4B5FD"}}
  ],
  "styles": {
    "frame-highlight": {"stroke": "#7F00FF"}
  }
}
```

A statement may name a style missing from the `styles` of its `graphical`
object. Python's `complete_styles(graphical)` and npm's
`completeStyles(graphical)` return a copied `graphical` object with every such
name added as an empty declaration, together with the sorted missing names.
Python issues one `MissingStyleWarning` and npm one `console.warn` call, each
naming all missing styles. The completed `graphical` object is valid, and a statement that names one of those empty declarations sets nothing.

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

- `timelines`, `groups`, `measure_maps` and `schemes` by ID, and every
  group's `members` by code point;
- in every timeline, `children` by offset, then ID;
- `conversion_maps` by ID;
- `regions` by start, then end, then ID;
- `flow_control` by coordinate, then ID;
- `graphical.timestamps` by `timeline` (code point), then coordinate,
  then ID, and every timestamp's `display` in the order `wedge`, `name`,
  `id`, `coordinate`, `cross_section`.

IDs are unique across the manifest, so no two entries tie. Coordinates
compare by exact numeric value, never by JSON spelling. Strings compare by
Unicode code point. No other array is reordered: `graphical` statements,
display orders, conversion-map payloads, MeasureMap rows, the links of the
manifest, a timeline or a region, and every array of a link keep their
order.

## The standard writer

Each package has one writer, `dumps`. It puts a manifest in canonical
order, sorts the keys of every object by code point, and writes UTF-8 text
with two-space indentation and a final newline. It writes any other JSON
value, such as an application's file embedding manifests, under the same
rules. It writes the form it is given: pass a manifest through `complete`
or `minimal` first to choose its form. Every
character is unescaped except `"`, `\`, and control characters U+0000 to
U+001F. A float remains a float and is spelled as Python's `repr` spells it
(`2.0`, `0.0001`, `1e-05`, `1e+16`, `-0.0`); an integer never has a decimal
point or exponent. A NaN, an infinity, or a string containing a lone surrogate
is refused. The fixtures use this writer.

## Install

```bash
pip install timetoshare
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
manifest with `loads` and write it with `dumps`:

```python
from timetoshare import SchemaValidationError, dumps, fixture_paths, loads, validate

value = loads(fixture_paths()[0].read_text(encoding="utf-8"))
try:
    validate(value)
except SchemaValidationError as error:
    print(error.code, error.path)
else:
    text = dumps(value)
```

- `validate(value)` reads the version marker first, then checks the value
  against the schema, the representation of its own-axis values and the
  identity rules, and raises `SchemaValidationError` at the first problem.
  A value without `timetoshare` is refused at the root; a value declaring
  another version raises `UnsupportedVersionError`. Unknown
  keys never fail it.
- `loads(text)` reads JSON text as the TypeScript package's `parseJson`
  does: integers stay exact at any size and floats stay floats, and `NaN`,
  `Infinity` and a float beyond a double are refused with `ValueError`.
- `unknown_keys(value)` returns the unknown keys of a manifest as a list of
  `{path, key}` entries, sorted by path and then by key.
- `unregistered_terms(value)` returns the unregistered terms of a
  manifest's links as `{path, term}` entries, sorted by path
  ([Describing a manifest](#describing-a-manifest)).
- `description_problems(value)` returns the problems of a manifest's
  description layer alone as a list of `SchemaValidationError`s, empty
  where its schemes and links are sound, and refuses nothing outside the
  layer (the description specification, section 8).
- `Link`, `PartSlot`, `PartOf`, `Assertion`, `Descriptor`, `Identifier` and
  `Scheme` model the description layer; `Link.from_urls` and
  `PartSlot.from_url` build links and part slots through the registry that
  `default_registry()` returns.
- `complete(value)` and `minimal(value)` return a copy of a manifest in the
  complete or the minimal form; the input is not changed.
- `dumps(value)` returns the standard text of a manifest or any JSON value.
- `canonical_order(value)` returns a deep copy with the manifest's arrays in
  canonical order. `canonical_json(value)` returns compact JSON with object
  keys sorted by code point.
- `TIMESTAMP_DISPLAY` holds the words of a named timestamp's `display`,
  `("wedge", "name", "id", "coordinate", "cross_section")`, in canonical
  order.
- `identity_problems(value)` returns every violation of the identity rules in
  a schema-valid manifest, in the order described above; `validate` raises
  the first.
- `complete_styles(graphical)` returns `(completed, missing)` and warns with
  `MissingStyleWarning` when `missing` is non-empty.
- `SCHEMA_VERSION` is `"0.2.0"`, the one version the package reads.
- `schema_path()` and `load_schema()` return the schema document.
- `fixture_paths()` returns the bundled accepted fixtures,
  `rejection_paths()` the bundled rejection cases and `warning_paths()` the
  bundled warning cases; they live in the module `timetoshare.fixtures`, and
  the package exports them. `rejection_case(path)` reads one rejection case as a
  `RejectionCase` (`manifest`, `path`, `code`, `error`, `reason`), with the
  non-finite number a finite-rule case names put in place.
- `FONT_FILES` names the bundled TrueType files, DejaVu Sans first and Noto
  Music second; `font_paths()` returns their paths in that order, and
  `font_metrics()` returns the merged advance-width metrics of both.

### TypeScript

`JSON.parse` cannot preserve every distinction in the format: it reads `2.0`
as the integer `2`, rounds integers beyond 2^53, and changes the enumeration
order of array-index keys. Use the package's lossless reader:

```ts
import {
  dumps,
  parse,
  SchemaValidationError,
} from "@timetoalign/timetoshare";

function load(text: string): string {
  try {
    return dumps(parse(text));
  } catch (error) {
    if (error instanceof SchemaValidationError) {
      console.error(error.code, error.path);
    }
    throw error;
  }
}
```

- `parse(text)` reads and validates a manifest without losing a number or
  key order, and returns it as a `LosslessManifest`. `parseJson(text)`
  reads any JSON text without validating it, and throws `JsonSyntaxError`,
  a `SyntaxError` with the `offset` (in UTF-16 code units), `line` and
  `column` (from 1) of the fault.
- `validate(value)` asserts that an unknown value is a
  `LosslessManifest` (its numbers may be bigints and `JsonFloat`s),
  checking it as Python's `validate` does; its `SchemaValidationError` carries the same
  `code` (typed `ValidationCode`), a `path` and a `detail`.
- `unknownKeys(value)` returns the same list as Python's `unknown_keys`,
  and `unregisteredTerms(value)` the same list as Python's
  `unregistered_terms`.
- `descriptionProblems(value)` returns the problems of the description
  layer alone, as Python's `description_problems` does, with the same
  codes and paths; a `schema` problem carries the TypeScript schema
  validator's own message.
- `linkFromUrls`, `partSlotFromUrl`, `withParts` and the other `with…`
  functions build links as plain objects of the generated types, as
  Python's description model does; `defaultRegistry()`, `recognize` and
  `withSchemes` read and extend the registry.
- `complete(value)` and `minimal(value)` return the complete and the minimal
  form, as Python's functions do, keeping every number and key order
  `parseJson` read. The typed forms say which form a value is in:
  `completeManifest(value: LosslessManifest): CompleteManifest`,
  `minimalManifest(value): LosslessManifest` and
  `canonicalManifest(value)`, which returns its argument's type in canonical
  order.
- `dumps(value)` is the standard writer. `compactJson(value)` writes without
  whitespace, and `canonicalJson(value)` also sorts object keys by code point.
- `canonicalOrder(value)` returns a deep copy with the manifest's arrays in
  canonical order.
- `TIMESTAMP_DISPLAY` holds the words of a named timestamp's `display`,
  `["wedge", "name", "id", "coordinate", "cross_section"]`, in canonical
  order, as Python's constant does.
- `identityProblems(value)` returns the same identity problems as Python's
  `identity_problems`.
- `completeStyles(graphical)` returns `{graphical: completed, missing}`.
- `FONT_FILES` names the bundled TrueType files, as Python's constant does,
  and `fontMetrics` contains the merged advance-width metrics of both.
- `SCHEMA_VERSION` is `"0.2.0"`, and `schema` holds the schema document.
  The generated types are generated from it, with the root type
  `Manifest` and one type per definition, such as `Timeline`, `Group`
  and `Graphical`. Beside each definition with defaults a complete form is
  generated, `CompleteManifest`, `CompleteTimeline`, `CompleteGroup`,
  `CompleteTimestamp` (whose `display` is required) and so on, in which every key with a default is required at every depth and
  every number is a `JsonNumber`; keys whose default is their absence (the
  manifest's `id` and `graphical`, a root's `offset`) stay optional.
  `LosslessManifest` is `Lossless<Manifest>`.

A number read by `parseJson` is a `JsonNumber`:

| JSON text | `JsonNumber` |
| --- | --- |
| an integer within ±(2^53 − 1), such as `480` | a `number` |
| an integer beyond that range, such as `9007199254740993` | a `bigint` |
| a float with a fractional part, such as `0.5` | a `number` |
| an integral float, such as `2.0`, `1e+16`, or `-0.0` | a `JsonFloat` |

`Lossless<T>` replaces every `number` in `T` with `JsonNumber` and keeps
tuples, so a Fraction is `[JsonNumber, JsonNumber]`. A float whose
value is an integer must be passed as `new JsonFloat(2)`, not as `2`, if it is
to be written as a float. JavaScript code that writes files must use
`dumps` or `compactJson`, not `JSON.stringify`.

## Versioning

The packages read the current version only. A value declaring any other
version raises `UnsupportedVersionError`, and neither package migrates a
value from one version to another. The repository holds the current
version only; a version a later one replaces lives in the git history at
its tag and in the packages released with it.

A TimeToShare release is a schema-version event: one `vX.Y.Z` tag publishes
both packages through trusted publishing and publishes the version's
schema document at both its URLs ([The schema
document](#the-schema-document)). `scripts/check_versions.py` checks that all
version declarations agree.

## Fixtures

The [fixture guide](fixtures/README.md) describes the generated manifests
and the drawings, the hand-authored rejection cases, and the warning cases.
Every accepted fixture is written in the complete form beside its minimal
twin. The manifests are emitted only by timetoalign through the catalogue of
builders in `scripts/fixtures/`, whose CLI is `scripts/emit_fixtures.py`. Do
not edit them by hand.

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

From the repository root, check version declarations with:

```bash
python3 scripts/check_versions.py
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
