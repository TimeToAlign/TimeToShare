# TimeToShare!

TimeToShare! is an exchange format for the structures of musical
timelines: their axes, extents, nesting, groups, conversion maps, regions,
flow control, MeasureMaps, FlowMaps and virtual timelines, without their
events. Music-research
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
the Python package reads and checks; the package, a folder whose
`package.yaml` lists manifests and the tables they share, which both
packages validate and the Python package checks whole; and how
MatchClaims give alignment anchors and MatchStamps. It also specifies how a manifest
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
| `flow_maps` | no | the FlowMaps, each one order in which stretches of one root timeline are played ([FlowMaps and virtual timelines](#flowmaps-and-virtual-timelines)) |
| `virtual_timelines` | no | the virtual timelines, each the statement that a map was applied to a timeline ([FlowMaps and virtual timelines](#flowmaps-and-virtual-timelines)) |
| `@context` | no | the inline JSON-LD context: the format's terms and the prefixes the statements use; required where the manifest, a timeline or a region carries `statements` or `provenance`, and where any provenance entry uses a prefix, and warned of where absent (`context_absent`) ([Describing a manifest](#describing-a-manifest)) |
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
  end, meta?, statements?, provenance?}`, among them its atomic sections,
  [FlowMaps and virtual timelines](#flowmaps-and-virtual-timelines)) and
  flow-control elements ([Flow control](#flow-control)); `statements` and
  `provenance` hold pairs about
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
two extensions: `volta`, the pass a volta bracket is played in, an
integer from 1, or a non-empty list of distinct such passes where the
bracket stands for several (a bracket printed "1, 3" is `[1, 3]`), kept as
written (no reader turns `1` into `[1]` or `[1]` into `1`), and `offset_within_measure`, where
the row begins inside its nominal measure in quarter notes. Lengths are
strictly positive and `qstamp` is non-negative; exact Fraction pairs are
permitted wherever the standard uses JSON numbers. A measure view's
`measure_map` must name an entry of `measure_maps`, which both validators
check after the schema.

### Flow control

A timeline's `flow_control` is one array of **flow-control elements**,
each at a `coordinate` on the timeline's own axis, from 0 to the
timeline's length where that is known. Every element is `{id, role,
coordinate, name?, label?, meta?, provenance?}` with the keys its `role`
admits, and `role` names one of five kinds:

| `role` | The element | When the flow plays up to it | Its own keys | Manifestations |
| --- | --- | --- | --- | --- |
| `jump` | a Jump, where the flow may leave for another place | a destination that holds is taken; where none holds, the flow goes on | `targets`, its destinations, one or more, required | none: each destination has its own |
| `jump_target` | a JumpTarget, a place a destination names | nothing | `manifestation` | `repeat_start`, `segno`, `coda`, `volta`, `ossia` |
| `break` | a Break, where the flow never goes on | a destination that holds of the Jump at the same coordinate is taken; otherwise the flow ends there | `manifestation`, `ends` | `fine`, `volta` |
| `section_break` | a SectionBreak, the end of a section, a movement included | the flow goes on | `manifestation` | none is defined |
| `barline` | a Barline, a marked position | nothing | `manifestation` | `double_barline`, `final_barline` |

An element acts when the flow plays up to its coordinate, never when a
destination lands on it. Flow control holds across descendants: a root
and all its descendants have at most one Jump at one position on the
root's axis, each element's coordinate carried to the root by adding the
offsets of its ancestors exactly, a float as its exact binary value, so a
Jump of a child never shares its place with a Jump of the root or of
another descendant; several signs at one
place, such as a repeat end and a dal segno on one barline, are
destinations of that one Jump. `manifestation` says how an
element or a destination is notated, a word of an open vocabulary: a word
the format does not define for its role is valid and kept, and both
validators report it as the warning `manifestation_unknown`. The
manifestation never decides the flow. `label` is the text an element is
drawn with, or `null`; on a Jump it labels the Jump once, never each of
its arcs.

**Destinations.** A Jump's `targets` are its destinations
(`$defs/JumpDestination`), which carry no order and in which every key is
optional:

| Key | Holds |
| --- | --- |
| `to` | the place as an element: the ID of a JumpTarget of the same timeline, of a region of it (its start), of a child timeline of it (the child's start on this axis) or of the timeline itself (its start) |
| `by` | the place as a signed distance from the Jump's coordinate, in the axis's number type |
| `passes` | the passes on which the destination holds, the n-th arrival of the flow at the Jump being pass n: a list of distinct positive integers, or `{from: n}` for pass n and every later one |
| `repeat_count` | how many times the destination is taken at most, an integer of at least 1; absent, there is no limit |
| `after` | `{jump, to?, by?}`, a destination of another Jump of the timeline, named by that Jump's ID and the destination's place: this destination holds once that one has been taken, and the condition is used up when this one is taken, as a To Coda holds after its dal segno al coda |
| `determined` | `false` for a choice nobody can check, such as an ossia, which a reader computing a flow never takes; default `true` |
| `reset` | whether taking the destination, where it lies before its Jump, restores what lies in the stretch gone back over (below); default `true` |
| `manifestation` | `repeat_end`, `da_capo`, `da_capo_al_fine`, `da_capo_al_coda`, `dal_segno`, `dal_segno_al_fine`, `dal_segno_al_coda`, `to_coda`, `volta` or `ossia`, an open vocabulary as above |
| `label` | the text the destination's arc is drawn with, or `null`: an arc without one has no label, never the destination's `manifestation`, which the drawing shows as a symbol, nor the Jump's `label` |

A destination's place is `to`, `by` or neither, never both, and lies from
0 to the timeline's length. A destination without a place lands at the
nearest section break, not rejected, before its Jump on the axis of the
timeline played, among those of that timeline and of all its descendants,
but never before the start of the timeline stating the Jump, which counts
as a section boundary for it: where no such section break lies from that
start up to the Jump, the destination lands at that start. `by` 0 is going
on and no jump: it is
written where the source prints it, as the numbers of a first volta
bracket, and is never taken. The destinations of one Jump lie at distinct
places, no two with the same `to`, the same `by` (compared by value) or
both without a place, so that an `after` names one by its place: with
`to` or `by` as that destination writes it, or with neither for the
destination without a place, or for the one destination of a Jump that has
no other.

A destination holds when every condition it states (`passes`,
`repeat_count`, `after`, `determined`) holds; one stating none is taken
every time the flow plays up to its Jump, so a repeat end, a da capo and a
dal segno state `repeat_count: 1`. Beyond the highest pass any destination
of a Jump names in a list, the destination naming that pass holds, as the
last volta bracket does after a da capo without repeats. Where several
destinations of a Jump hold at once, one with `by` 0 never competes; of
the others, one lying before the Jump that restores (`reset`) is taken
first, then one lying before the Jump that does not, then one lying
ahead, the nearest of its kind in each case; two of one kind holding
together are ambiguous. So a repeat end and a dal segno on one barline
play the repeat first and the dal segno after it.

Taking a destination that lies before its Jump, with `reset` at its
default, restores every Jump and Break lying wholly inside the stretch
gone back over, that is whose coordinate and places all lie from the
destination's place up to, but not at, the Jump's coordinate: their
passes, the times their destinations were taken and their `after`
conditions start again, as a repeat plays an inner repeat again.
`reset: false` on a da capo or a dal segno states that the repeats are
not played again (senza repetizione).

**Breaks, voltas and sections.** A Break without `ends` always ends the
flow. One with `ends`, `{passes?, after?}`, at least one of the two
stated and both holding where both are, ends it only while that condition
holds: `passes` counts the arrivals of the flow at the Break and means
exactly the arrivals listed, or with `from` that arrival and every later
one (what holds beyond the highest pass holds for a Jump's destinations
only, never for a Break), and `after` names a destination as a
destination's `after` does. A Fine is a Break of
the manifestation `fine` whose `ends.after` names the destination of the
da capo al fine or dal segno al fine. Volta brackets are written with
three kinds of element: one Jump at the end of the measure before the
brackets, with one destination per bracket, the first `by` 0 and every
other `to` a JumpTarget at its bracket's start, each with the bracket's
printed numbers as `passes`; a Break (`volta`) between adjacent brackets;
and the repeat sign of a bracket, a destination of the Jump at the
bracket's end. A bracket is left only by a Jump at its end whose
destination holds. The repeat sign that closes a bracket other than the
first is written with `reset: false`: with the default it would restore
the Jump before the brackets wherever all that Jump's places lie before
the sign, and the later passes would never be reached. A section break
ends a section, a movement included: no atomic section spans it, a
destination without a place may land at it (above), and
a flow that has ended at a Break begins again at the
nearest section break at or after that Break, where one lies before the
timeline's end.

**Provenance and rejection.** A flow-control element may carry
`provenance`, a non-empty list of entries of `provenance.schema.json`
([Provenance and beliefs](#provenance-and-beliefs)) that name no pair:
each is about the element itself, how it was made (`method` `imported` by
a loader, `manual` where a person added it, `inferred`) and who believes
it. A repair adds elements and rejects elements; it never deletes or
changes one. An element that some actor believes `false` is **rejected**:
a reader computing a flow leaves it out, and the validators apply the
rules of flow control to the elements not rejected, so a rejected Jump and
its replacement may share a coordinate, and a `to` or an `after` naming a
rejected element names nothing: the validators report it as they report a
`to` or an `after` naming no element (`dangling_target`), and a drawing
draws no arc to it. A drawing may take a reading of its own, an actor's
beliefs filtered by belief state, and then reads its unread elements as
rejected ([drawing
specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/drawing.md),
section 1). Such provenance needs the `@context` only
where it uses a prefix; JSON-LD reads none of it, since `flow_control` is
no term of the context.

**The earlier form.** A flow-control element written with the key `type`
(`jump_from`, `jump_to` or `flow_marker`), with one of those words as its
`role`, or with `target` and no `role`, is refused before the schema with
the code `flow_control_form` at the element: `flow-control element
'<id>' is written in the earlier form of flow control (type, target):
convert the manifest with scripts/convert_flow_control.py`. That script,
which lives in this repository and not in the packages, rewrites such
manifest files in place, each in the form and serialization it was read
in:

```bash
python scripts/convert_flow_control.py score.yaml other.json
python scripts/convert_flow_control.py --check score.yaml   # report only
```

The script reads one of the three words under `role` as it reads it
under `type`. A `jump_to` becomes a `jump_target`, its manifestation
kept; a `flow_marker` a `break` (`fine`, whose `ends.after` names the
destination of the timeline's one jump al fine), a `section_break`
(without a manifestation) or a `barline` (`double_barline`,
`final_barline`); a `jump_from` a `jump` with one destination, `to` its
`target` and its manifestation, a repeat end's `repeat_count` (1 where it
stated none), `repeat_count: 1` and `reset: false` on every da capo and
dal segno, and on a `to_coda` an `after` naming the destination of the
timeline's one jump al coda. A repeat end and every da capo form without
a `target` went to the timeline's start: their destination is `to` the
timeline's own ID, written as that ID is written in the file, never a
destination without a place, which would land at the nearest section
break before the Jump. Two `jump_from` at one coordinate become one Jump
holding both destinations, under the ID that comes first by code point;
the other element's label moves to its destination, the kept element's
label is copied to its own destination where that has none, every
address naming the other ID names the kept one, and the other element's
`name` and `meta` are dropped. A drawing rule selecting the element type
`jump_from` selects `jump`, and one selecting `flow_marker` becomes three
rules, for `break`, `section_break` and `barline`.

The script never guesses. It reports, and leaves the file as it was: an
element holding a `target` and none of the three words; one stating two
different words under `type` and `role`; one mixing the earlier form with
`targets` or `ends`; a `jump_from` without a `target` that is neither a
repeat end nor a da capo, or that lies on a timeline without an ID; a
`jump_from` at the coordinate of a Jump not of the earlier form; a
`flow_marker` whose manifestation names no role; a Fine or a To Coda on a
timeline with none or several of the jumps it waits for; a merge that
would give one Jump two destinations at one place, such as a repeat end
and a da capo without targets on one barline, both going to the
timeline's start; and an element without a coordinate it can read. Every
manifest the validators refuse with `flow_control_form` is either
converted or refused, never left as needing nothing. Its exit status is 0
when every file is converted or needs nothing and 1 when one is refused;
it needs the `timetoshare` package.

### FlowMaps and virtual timelines

A **FlowMap** is one order in which stretches of one root timeline are
played: a concrete flow, where flow control states what a source affords.
It needs no flow control: a reading, an order of movements or a set list
is a FlowMap written by hand. The manifest's `flow_maps` hold them, each
`{id, timeline, chunks, convention?, canonical?, name?, provenance?}`:

- `timeline` is the ID of one root timeline;
- `chunks` are the stretches in the order they are played, which no writer
  reorders: each the ID of an element giving an interval inside that
  root's tree (a region of the root or of a descendant, a child timeline at
  any depth, or a virtual timeline that comes from a timeline of that
  tree), or a gap `{gap: <length>}`, a strictly positive stretch that
  nothing of the timeline fills, in the root's number type; an element may
  occur any number of times;
- `convention` names which flow of the timeline's flow control the FlowMap
  states: `default`, every repeat and leap played as written; `single`,
  each stretch played once, without going back; `printed`, the atomic
  sections in the order of the axis. The vocabulary is open: another word
  is valid and kept, and both validators report it as the warning
  `convention_unknown`. A FlowMap that follows none, such as one written by
  hand, has no `convention`;
- `canonical: true` marks the canonical FlowMap of its timeline, at most
  one;
- `provenance` records how the FlowMap was made and who believes it, in
  the entries a flow-control element carries: a FlowMap computed from the
  flow control of its timeline, which states the `convention` it follows,
  carries an entry of method `inferred`, as the atomic sections it plays
  do, and one written by hand an entry of method `manual`; no reading of
  its beliefs is fixed.

**Atomic sections.** The flow of a timeline runs over its **atomic
sections**, the intervals between consecutive boundaries of its flow
control: 0, the timeline's length, the coordinates of its Jumps,
JumpTargets, Breaks and SectionBreaks, and the places of all its
destinations but those with `by` 0, of the elements not rejected; a
barline is no boundary. They are lettered A, B, … in the order of the
axis, and a timeline without flow control has none. A manifest states them
as regions of the timeline whose `type` statement is the class
`https://timetoalign.github.io/timetoshare/ns#AtomicSection`, written as a
compact IRI under a prefix the `@context` declares for the format's
namespace (`tts:AtomicSection`), each with its letter as `name` and a
provenance entry of method `inferred` for that pair. Both packages export
the class as `ATOMIC_SECTION`. The FlowMaps computed from flow control
list these regions as their chunks, and each carries its own provenance
entry of method `inferred`.

**Virtual timelines.** The manifest's `virtual_timelines` hold `{id, map,
timeline, unit, number_type, length, through?, name?}`, each the
statement that the map `map`, a FlowMap or a conversion map of the
manifest, was applied to `timeline`, a timeline of the manifest at any
depth or another virtual timeline, giving a timeline with its own ID of
which nothing else is written: it holds no children, flow control or
offset. Positions on it and on the timeline it comes from convert through
the map in both directions. Its `unit`, `number_type` (one the unit
admits, as for a timeline) and `length` (in that number type) are always
stated, so that a reader evaluating no map can still use its axis. A
FlowMap applied to its timeline gives a virtual timeline whose axis starts
at 0 with the first chunk and is as long as its chunks and gaps together.
`through` names the group or conversion map that carries the map to
`timeline` where the map's own elements do not lie on that timeline; the
validators do not resolve it.

Both validators hold a virtual timeline to the map it applies, under the
code `virtual_timeline`. Virtual timeline by virtual timeline, it comes
from a timeline of the manifest: none comes from itself through others,
which is reported at each virtual timeline of such a ring, never at one
that only leads into it. Where `map` is a FlowMap and no `through` is
stated, the timeline it comes from, followed through virtual timelines to
a timeline of the manifest, lies in the tree of the FlowMap's root
timeline; and there its `length` is the sum of the FlowMap's chunks and
gaps, compared by exact value where every chunk has a known length on an
axis of the virtual timeline's unit and number type: a region on the axis
of its timeline, a child timeline and a virtual timeline on their own, a
gap on the axis of the FlowMap's root. A `float` axis is never compared,
since a sum of doubles depends on the order of its additions, and no
length is compared where a chunk lies on another axis or has no known
length. Where `through` is stated, neither
the tree nor the length is read; a conversion map as `map` is read for
neither.

A virtual timeline takes part in alignment as a timeline does: a group may
name it as a member, so that it shares the frame with the recordings that
follow its flow ([Groups and the `graphical`
object](#groups-and-the-graphical-object)); a named timestamp, a
groupstamp where it is a member, may lie on it; a resource and the
MatchClaim table may name it; `graphical.order` may hold its band
order; and an elision may lie on it, on its own axis. A FlowMap is drawn
as the axis it plays: on the card of a virtual timeline, which
the drawing places where its placement holds the virtual timeline's ID,
and on the card of a root switched to it by the property `flow`, which a
rule addressed to the root's cards sets to the ID of one of its FlowMaps
or of a virtual timeline applying one to it. Its line is a segment line
of its **chunks**, one per entry, laid end to end and each named above
the line by its source, with a boundary at each start; a run of one
chunk repeated is drawn once with `× n`, and a gap is a grey stretch of
the line in the line's own stroke, labelled with its length and drawn at
least 32 wide on a card of its own. On a virtual timeline's card each
chunk is a window onto its source, the stretch of the written timeline
it plays: it can show what the source holds there, its children,
regions, named timestamps, flow control and conversion maps, at every
position where it is played, each band turned on for all chunks at once
and hidden by default, so that a new virtual timeline's card shows its
line, its chunks and its own named timestamps alone. What a chunk shows
belongs to its source and keeps the source's address; the virtual
timeline still holds nothing, and showing writes nothing to it. A switched card keeps the
bands it displays: it draws every element of its tree, its flow control
and conversion maps included, at each position where it is played; in a
frame, the switch of one member carries every member
through the group, and the switches of two members, which both
validators warn of as `flow_conflict` at the group's `members`, leave the
frame as written (the drawing specification, section 8.10).

**Computing a flow.** A timeline is **played** with its own elements and
those of all its descendants, each at its coordinate plus the offsets of
the ancestors between it and the timeline played (flow control holds
across descendants, above); the runs and the findings lie on the axis of
the timeline played. Each convention reads the elements so gathered that
are not rejected and the played timeline's length, never a
manifestation. The `default` flow starts at 0 and plays up to the nearest coordinate ahead that holds a Jump
or a Break, or up to the length; each such stretch is one **run**. There
the Jump counts one more pass, and a destination that holds is taken, by
the order above, the flow going on from its place. Where none is taken,
each Break there counts one more arrival, and where one of them holds,
the flow ends, or begins again at the nearest section break at or after
it, where one lies before the length. Otherwise the flow goes on; at the
length it ends. The `single` flow goes through once: no destination lying
before its Jump is taken and no `after` holds, and each Jump is arrived at
on pass 1 plus the sum of the `repeat_count`s of the restoring
destinations of other Jumps whose stretch gone back over contains its
coordinate, so that a volta Jump inside a repeat taken once enters the
second bracket. The `printed` flow is the atomic sections in the order of
the axis. A reader computing a flow reports **findings**, each at a
coordinate, which refuse nothing: `flow_ends_at_break` where the flow
ends at a Break that has no `ends`, lies before the length and shares its
coordinate with no section break, unless a Break with `ends` holds at that
coordinate; `never_played` once for each stretch of the axis from 0 to
the length that no run covers, at its start and with its end, however
many atomic sections the stretch holds; `endless_loop` where the flow comes
back to a place with every count and condition as it was there before;
`ambiguous_targets` where two destinations of one kind hold together;
and `undetermined_target` where the flow passes a Jump holding a
destination of `determined: false`. The `single` flow reports what its
walk finds alike; a stretch it never plays that the `default` flow plays
is reported `never_played` with the **cause** `single_playback`, since
going through once left it out, and divided where the `default` flow
begins or ends playing it; every other finding has no cause. The
`printed` flow plays the whole axis and finds nothing. The expected flows of the flow
fixtures ([fixture guide](fixtures/README.md#flow-fixtures-and-expected-flows))
state the runs, the atomic sections and the findings of each.

**An example.** The fixture `fixtures/0.2.0/flow/sonata_exposition.yaml`
is an exposition of 24 quarters whose repeat is left by two volta
brackets, the first from 12 to 16, the second from 16 on. Its minimal
twin, without its `@context`, which declares the prefix `tts` beside the
format's terms:

```yaml
flow_maps:
  -
    chunks: ["#region_3gr351kj2rne4", "#region_1sds8frdr4gcb"]
    convention: single
    id: "#flow_1a6b8chz5jxvf"
    provenance:
      -
        method: inferred
    timeline: "#score"
  -
    chunks: ["#region_3gr351kj2rne4", "#region_34nspphwkjsxm", "#region_3gr351kj2rne4", "#region_1sds8frdr4gcb"]
    convention: default
    id: "#flow_1ehd6m4iqaqeb"
    provenance:
      -
        method: inferred
    timeline: "#score"
  -
    chunks: ["#region_3gr351kj2rne4", "#region_34nspphwkjsxm", "#region_1sds8frdr4gcb"]
    convention: printed
    id: "#flow_2dbu5af0gros4"
    provenance:
      -
        method: inferred
    timeline: "#score"
name: "Sonata exposition"
timelines:
  -
    flow_control:
      -
        coordinate: [12, 1]
        id: "#jump_1"
        role: jump
        targets:
          -
            by: [0, 1]
            manifestation: volta
            passes: [1]
          -
            manifestation: volta
            passes: [2]
            to: "#jump_target_1"
      -
        coordinate: [16, 1]
        id: "#break_1"
        manifestation: volta
        role: break
      -
        coordinate: [16, 1]
        id: "#jump_2"
        role: jump
        targets:
          -
            manifestation: repeat_end
            repeat_count: 1
      -
        coordinate: [16, 1]
        id: "#jump_target_1"
        manifestation: volta
        role: jump_target
    id: "#score"
    length: [24, 1]
    name: Score
    regions:
      -
        end: [12, 1]
        id: "#region_3gr351kj2rne4"
        name: A
        provenance:
          -
            method: inferred
            property: "rdf:type"
            value:
              id: "tts:AtomicSection"
        start: [0, 1]
        statements:
          type: ["tts:AtomicSection"]
      -
        end: [16, 1]
        id: "#region_34nspphwkjsxm"
        name: B
        provenance:
          -
            method: inferred
            property: "rdf:type"
            value:
              id: "tts:AtomicSection"
        start: [12, 1]
        statements:
          type: ["tts:AtomicSection"]
      -
        end: [24, 1]
        id: "#region_1sds8frdr4gcb"
        name: C
        provenance:
          -
            method: inferred
            property: "rdf:type"
            value:
              id: "tts:AtomicSection"
        start: [16, 1]
        statements:
          type: ["tts:AtomicSection"]
    unit: quarters
timetoshare: "0.2.0"
virtual_timelines:
  -
    id: "#virtual_1"
    length: [36, 1]
    map: "#flow_1ehd6m4iqaqeb"
    name: "Score, as played"
    number_type: fraction
    timeline: "#score"
    unit: quarters
```

`jump_1`, at the end of the measure before the brackets, holds the two
brackets' destinations: on pass 1 `by` 0, going on into the first bracket;
on pass 2 to `jump_target_1`, the start of the second bracket at 16. At 16
lie the Break `break_1` between the brackets, the Jump `jump_2`, the first
bracket's repeat sign, whose one destination has no place and so lands at
the timeline's start, no section break lying before it, and the
JumpTarget `jump_target_1`. The boundaries 0, 12, 16 and 24 give the
atomic sections A from 0 to 12, B from 12 to 16 and C from 16 to 24, the
regions named A, B and C. Their IDs, and those of the FlowMaps, are
minted, so the FlowMaps are listed in the order of their IDs.

The `default` flow plays A up to 12, where `jump_1` on pass 1 goes on, and
B up to 16, where `jump_2` is taken back to 0. That restores nothing:
`jump_1` has a place at 16, outside the stretch from 0 up to 16, and keeps
its pass, and `break_1` lies at 16. The flow plays A again, `jump_1` on
pass 2 takes it to 16, and it plays C up to the length: A B A C, the
chunks of the `default` FlowMap, with no finding. The `single` flow arrives at
`jump_1` on pass 1 + 1, since the repeat end restores, is taken once and
goes back over 12: A C, the `single` FlowMap. The `printed` flow is A B C,
the `printed` FlowMap. The three FlowMaps are computed from the flow control, so
each carries a provenance entry of method `inferred`. `virtual_1` is
the `default` FlowMap applied to `score`, and is 12 + 4 + 12 + 8 = 36 quarters
long, the length both validators compare with the sum of its chunks. The expected flows
`fixtures/flows/0.2.0/sonata_exposition.yaml` state these runs and
sections.

### Values on a timeline's own axis

A coordinate on its timeline's own axis is written as its value alone:
`length`, a child's `offset` (on the parent's axis), a root's `offset`,
region `start` and `end`, the `coordinate` of every flow-control
element, the `by` of every destination and of every `after`, and the
gaps of every FlowMap of a root; a virtual timeline's `length` lies on the
virtual timeline's own axis, and is read and written by its own
`number_type` alike. The value is represented as the axis's number type selects, that
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
float and a Fraction pair of equal value are equal, so a `LinearMap`'s
`scalar` written `1`, `1.0` or `[1, 1]` equals its default 1 and is
omitted;
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
| manifest | `id`: absent (without a `name` too, an anonymous bundle); `name`: `null`; `meta`: `{}`; `groups`, `measure_maps`, `resources`: `[]`; `flow_maps`, `virtual_timelines`, `graphical`: absent |
| resource | `media_type`, `size`, `integrity`: absent |
| timeline | `name`: `null`; `number_type`: the unit's default (the unit table of [The timeline](#the-timeline)); `offset`: absent on a root, required on a child; `locked`: `false`; `is_segment_line`: `false`; `meta`: `{}`; `children`, `conversion_maps`, `regions`, `flow_control`: `[]` |
| region | `name`: `null`; `meta`: `{}` |
| flow-control element (`flow_control_element`) | `name`, `label`: `null`; `meta`: `{}` |
| destination of a jump (`jump_destination`) | `determined`: `true`; `reset`: `true`; `label`: `null`; `repeat_count`: absent (no limit) |
| FlowMap (`flow_map`) | `canonical`: `false`; `name`: `null`; `convention`: absent |
| virtual timeline (`virtual_timeline`) | `name`: `null`; `through`: absent |
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
adds its keys to those of the general row it follows: a `LinearMap` or a
`TableMap` has the keys of every conversion map plus its own, at any depth
of nesting. The names in
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
the member timelines, each naming a timeline of the manifest, a root or any
descendant, or a virtual timeline ([FlowMaps and virtual
timelines](#flowmaps-and-virtual-timelines)), which lies inside no other
member and contains none. Members share the same graphical start and end: every
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
a descendant at any depth, a segment included, or a virtual timeline, written as that timeline's
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
`members` (an ancestor of a member lies in no group through it), or the
virtual timeline is. In the
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
- a timeline's ID, of a root, a descendant or a virtual timeline, to its **band order**:
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
descendant at any depth, a segment included, or a virtual timeline:
`timeline` has the meaning and the validation of a named timestamp's
`timeline`, and `start < end`,
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
["card"]}`: `custom`, the initial value, draws the stored ones, `full`
none, `proportional` elisions the drawing derives around the member in
each ancestor card, and `auto` the stored ones where the root has any,
else the derived ones. A root that two or more groups hang on, drawn
once behind them where they stand side by side, is cut between the
groups and shortly beyond the outer ones whatever its mode. A derived elision leaves out the middle of a timeline's
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
flow-control element, resource, FlowMap, virtual timeline, named
timestamp, named MatchStamp, alignment anchor and elision carries an `id`,
which identifies it, and so may the manifest. A `name`, where an element has
one, is what is displayed, and it may repeat. An ID is any non-empty string without control characters
(U+0000 to U+001F): `/`, spaces, colons and URIs are allowed. Every ID is
unique across the whole manifest: the manifest's own, and the IDs of every
timeline (root or descendant), group, MeasureMap, conversion map at any
depth of nesting, region, flow-control element, resource, FlowMap,
virtual timeline, named timestamp, named MatchStamp, alignment anchor and
elision. Two strings are reserved for the sentinels of the MatchClaim
table, `NOMATCH_SENTINEL` and `CHUNK_SENTINEL` ([The MatchClaim
table](#the-matchclaim-table)): no element, event or Projection takes
either as its ID. The manifest validators refuse either as an element's
ID (code `schema`, at that `id`: `'CHUNK_SENTINEL' is reserved for a
sentinel`), and the checks of the tables refuse them as a MatchClaim's
or a Projection's `id` and as the event a Projection stands for
([Checking the tables](#checking-the-tables)). An ID is never parsed
and never composed with another. A reference is an ID, written in a file
as an ID is ([Written in a file](#written-in-a-file)): a destination's
`to` names a jump target, a region or a child of the same timeline or the
timeline itself, an `after`'s `jump` another jump of the same timeline
and its `to` the place of one of that jump's destinations, a FlowMap's
`timeline` a root timeline and the IDs among its `chunks` regions, child
timelines and virtual timelines inside that root's tree, a virtual
timeline's `map` a FlowMap or a conversion map, its `timeline` a timeline
or another virtual timeline and its `through` a group or a conversion map
(which no validator resolves), a measure view's
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

An ID that is given is kept verbatim. A tool that mints an ID for an
element created without one writes the element's type prefix, `_` and 13
random base-36 characters (`0` to `9`, `a` to `z`), such as
`region_3kq9x0m2ztb7a`, seeded so that it can mint the same IDs again
([fixture guide](fixtures/README.md#minted-id-vectors)). A minted ID is
opaque like any other: the format requires nothing of it beyond the
character rule above, and no reader parses its prefix or its characters.
An ID that is an
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
flow-control elements, resources, FlowMaps, virtual timelines, named
timestamps (`#timestamp_1`), named MatchStamps, alignment anchors and
elisions; and on the references: a group's `members`, the keys of
`graphical.order` and the member IDs of a group's entry, a named
timestamp's `timeline`, an elision's `timeline`, a resource's
`timelines`, an alignment anchor's `timestamps`, an address's `id`, a
selector's `within`, the `to` of a jump's destination, the `jump` and
`to` of an `after`, a FlowMap's `timeline` and the IDs among its
`chunks`, a virtual timeline's `map`, `timeline` and `through`, and a
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
holder's, nor that a map's arrays agree, nor that a member names a timeline or a virtual timeline
of the manifest, nor that no member of a group lies inside another, nor
that a child lies within its parent's known length, nor that a segment
line's segments are contiguous and alike, nor that a named timestamp lies
on a timeline or a virtual timeline of the manifest and within it, nor that a groupstamp lies
in a group, nor that an elision lies on a timeline or a virtual timeline
of the manifest and within it, nor that a resource's
timelines are timelines or virtual timelines of the manifest, nor that a
timeline is listed by at most one resource of each type, nor that a
folder has no `size` and no `integrity`, nor the rules of named
MatchStamps ([Named MatchStamps](#named-matchstamps)), nor the rules of
flow control, FlowMaps and virtual timelines ([Flow
control](#flow-control)), nor the use of the property `flow` ([Drawing a
manifest](#drawing-a-manifest)), nor the representation of
own-axis values, so both validators check them after the schema. Each
finding is one problem, located by a path into the manifest and named by a
stable code:

| Rule | Code | Location | Message |
| --- | --- | --- | --- |
| An ID repeats an earlier ID of its root's tree | `duplicate_id` | the later occurrence | `'<id>' is not unique in the manifest, first at <pointer>` |
| A flow-control element's `coordinate` lies before 0, or beyond its timeline's known length | `flow_coordinate` | the `coordinate` | `coordinate <value> of '<id>' is not on '<timeline id>': it lies outside 0 to the length <length>` (`… it lies before 0` where the length is unknown) |
| The `jump` of an `after` names no jump of the timeline, a rejected one, or the jump holding the destination | `dangling_target` | the `jump` | `'<id>' names no jump of this timeline` (`'<id>' is the jump holding this destination; after names a destination of another jump`) |
| The `to` or `by` of an `after` names no destination of that jump | `dangling_target` | the `to` or the `by` | `jump '<id>' has no destination to '<to>'` (`… by <value>`) |
| An `after` without `to` and `by` names a jump of several destinations, none without a place | `dangling_target` | the `after` | `jump '<id>' has <n> destinations and none without a place; after names one by its to or by` |
| A jump lies at the position of an earlier jump of its root's tree on the root's axis, its coordinate plus the offsets of its ancestors, summed exactly (a float as its exact binary value) and compared by exact value, in document order, a timeline's elements before its children's | `jump_repeated` | the later jump | `'<id>' is a second jump at coordinate <value> of '<timeline id>', after '<earlier id>': several signs at one place are destinations of one jump` (`… after '<earlier id>' of '<earlier timeline id>' at the same position on their root's axis: …` where the two lie on different timelines) |
| A destination has the place of an earlier destination of its jump, `by` compared by exact value | `jump_destination` | the later destination | `destination <n> of '<id>' has the place of destination <m>, to '<to>'` (`… by <value>`, `… without a place`) |
| A destination's `to` names no jump target, region or child of its timeline, nor the timeline, or names a rejected jump target | `dangling_target` | the `to` | `'<to>' names no jump target, region or child of this timeline, nor the timeline itself` |
| The place a destination's `by` reaches lies before 0, or beyond its timeline's known length | `flow_coordinate` | the `by` | `by <value> from coordinate <value> of '<id>' is not on '<timeline id>': it lies outside 0 to the length <length>` (`… it lies before 0`) |
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
| A group ID, a MeasureMap ID, a named timestamp's ID, an elision's ID, a named MatchStamp's ID, an alignment anchor's ID, a resource's ID, a FlowMap's ID or a virtual timeline's ID repeats an earlier ID of the manifest | `duplicate_id` | that element's `id` | `'<id>' is not unique in the manifest, first at <pointer>` |
| The manifest's ID repeats another ID of the manifest | `manifest_id` | `id` | `'<id>' is not unique in the manifest, first at <pointer>`, the pointer naming the first occurrence of that ID |
| A member names no timeline and no virtual timeline of the manifest | `group_member` | the member | `'<id>' names no timeline or virtual timeline of this manifest` |
| A member lies inside an earlier member of its group, or contains one | `group_member` | the later member | `member '<id>' lies inside member '<earlier id>' of the same group` (`… contains member …`) |
| A key of `graphical.order` names no group, no timeline and no virtual timeline | `order_key` | the key | `'<key>' names no group, timeline or virtual timeline of this manifest` |
| An entry of a display order is not a member of its group | `display_order` | the entry | `'<id>' is not a member of group '<group id>'` |
| A member of a group is missing from its display order | `display_order` | the order | `member '<id>' of group '<group id>' is missing` |
| An entry of a band order is neither `line` nor a facet | `band_order` | the entry | `'<entry>' is not 'line' or a facet, in the band order of '<id>'` |
| `line` is missing from a band order | `band_order` | the order | `'line' is missing from the band order of '<id>'` |
| A named timestamp's `timeline` names no timeline and no virtual timeline of the manifest | `timestamp_timeline` | the `timeline` | `'<id>' names no timeline or virtual timeline of this manifest` |
| A named timestamp's `coordinate` lies before 0, or beyond its timeline's known length | `timestamp_coordinate` | the `coordinate` | `coordinate <value> of '<id>' lies before the start of its timeline '<id>'` (`… is beyond the length <length> of its timeline '<id>'`) |
| A groupstamp lies on a timeline that lies in no group (neither it nor any of its ancestors is a member), or on a virtual timeline that is no member | `groupstamp` | its `groupstamp` | `'<id>' is a groupstamp, but its timeline '<timeline id>' is a member of no group and lies in none` |
| An elision's `timeline` names no timeline and no virtual timeline of the manifest | `elision_timeline` | the `timeline` | `'<id>' names no timeline or virtual timeline of this manifest` |
| An elision's `start` lies before 0 | `elision_stretch` | the `start` | `start <value> of '<id>' lies before the start of its timeline '<timeline id>'` |
| An elision's `end` lies beyond its timeline's known length | `elision_stretch` | the `end` | `end <value> of '<id>' is beyond the length <length> of its timeline '<timeline id>'` |
| An elision's `end` does not lie after its `start` | `elision_stretch` | the `end` | `end <value> of '<id>' does not lie after its start <value>` |
| An entry of an alignment anchor's `timestamps` names no named timestamp | `alignment_anchor` | the entry | `'<id>' names no timestamp of this manifest` |
| An entry of an alignment anchor's `timestamps` names a timestamp that is no match timestamp | `alignment_anchor` | the entry | `'<id>' is no match timestamp` |
| The two match timestamps of an alignment anchor lie on one timeline | `alignment_anchor` | the anchor's second entry of `timestamps` | `the timestamps of '<anchor id>' both lie on the timeline '<timeline id>'` |
| The alignment anchors of a named MatchStamp are not one connected set of timestamps | `matchstamp` | its `alignment_anchors` | `the alignment anchors of '<id>' are not one connected set` |
| A match timestamp lies on the coordinate of an earlier match timestamp of its timeline, compared by exact value | `match_timestamp` | the later timestamp | `'<id>' lies on the coordinate of the match timestamp '<earlier id>'` |
| No named MatchStamp's anchor names a match timestamp | `match_timestamp` | the timestamp | `the match timestamp '<id>' belongs to no MatchStamp` |
| An entry of a resource's `timelines` names no timeline and no virtual timeline of the manifest | `resource_timeline` | the entry | `'<id>' names no timeline or virtual timeline of this manifest` |
| An entry of a resource's `timelines` names a timeline that an earlier resource of the same type lists, for every type | `resource_type` | the entry | `'<id>' is listed by the resource '<earlier id>' of the type <type> already` |
| A resource whose `url` ends in `/`, naming a folder, has a `size` or an `integrity` | `folder_descriptor` | that member, `size` before `integrity` | `'<url>' names a folder, which has no size` (`… which has no integrity`) |
| A FlowMap's `timeline` names a child timeline, or no timeline | `flow_map_timeline` | the `timeline` | `'<id>' is a child timeline; a FlowMap names a root timeline` (`'<id>' names no root timeline of this manifest`) |
| An ID among a FlowMap's `chunks` names no region, child timeline or virtual timeline inside the tree of its root | `flow_map_chunk` | the chunk | `'<id>' names no region, child timeline or virtual timeline in the tree of '<timeline id>'` |
| A FlowMap is canonical after an earlier canonical FlowMap of its timeline | `flow_map_canonical` | its `canonical` | `'<id>' is a second canonical FlowMap of '<timeline id>', after '<earlier id>'` |
| A virtual timeline's `map` names no FlowMap and no conversion map | `dangling_target` | the `map` | `'<id>' names no FlowMap or conversion map of this manifest` |
| A virtual timeline's `timeline` names no timeline and no other virtual timeline, or the virtual timeline itself | `dangling_target` | the `timeline` | `'<id>' names no timeline and no other virtual timeline of this manifest` |
| A virtual timeline comes from itself through other virtual timelines, reported at each virtual timeline of the ring | `virtual_timeline` | the `timeline` | `'<id>' comes from itself through '<id>', '<id>': a virtual timeline comes, virtual timeline by virtual timeline, from a timeline of this manifest` |
| A virtual timeline without `through` applies a FlowMap of another root than the one its `timeline` comes from | `virtual_timeline` | the `map` | `'<map id>' is a FlowMap of '<root id>', and '<timeline>' comes from the tree of '<root id>': without through, a virtual timeline applies a FlowMap within the tree of the FlowMap's root timeline` |
| A virtual timeline without `through` applies a FlowMap of its own root, and its `length` is not the sum of the FlowMap's chunks and gaps, every chunk of a known length on its axis, the axis not `float` | `virtual_timeline` | the `length` | `length <value> of '<id>' is not the sum of the chunks and gaps of '<map id>', <sum>` |
| A style of `graphical.styles` sets `flow` | `flow_rule` | the style's `flow` | `style '<name>' sets flow; only a rule addressed to the cards of a timeline sets it` |
| A rule setting `flow` selects by anything but `addresses`, or by an address that is not `{id, part: ["card"]}` | `flow_rule` | the rule's `select` | `a rule setting flow selects the cards of timelines by their addresses alone, each {id, part: [card]}` |
| A rule's `flow` names no FlowMap and no virtual timeline | `flow_rule` | the rule's `set.flow` | `'<id>' names no FlowMap or virtual timeline of this manifest` |
| A rule's `flow` names a FlowMap of another timeline than one whose cards it selects, reported once per such address | `flow_rule` | the rule's `set.flow` | `'<id>' is a FlowMap of '<its timeline>', not of '<timeline id>'` |
| A rule's `flow` names a virtual timeline that does not apply a FlowMap of a timeline whose cards it selects to that timeline without `through`, reported once per such address | `flow_rule` | the rule's `set.flow` | `'<id>' does not apply a FlowMap of '<timeline id>' to '<timeline id>' without through` |

Within one root's tree, IDs are visited in identity order (a timeline,
then its conversion maps, regions and flow-control elements, then its
children in array order), and after them the IDs of the maps a
`ChainMap`, `PiecewiseMap` or `CombinationMap` holds, timeline by timeline
in the same order, each map before the maps it holds; duplicates come first, then flow control
and dangling targets, timeline by timeline, each before its children: its
flow-control elements in array order, a rejected one passed over (each its
`coordinate`, the `after` of a break's `ends`, and for a jump a second
jump at its coordinate, then destination by destination a repeated place,
its `to`, its `by` and its `after`), then its measure views;
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
FlowMaps' IDs, the virtual timelines' IDs, the manifest's ID; members
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
coordinate shared with an earlier one, then belonging to no MatchStamp; then the resources, in array order, each its
`timelines` in order, for each entry first whether it names a timeline,
then whether an earlier resource of its type lists it, and last a
folder's `size` or `integrity`; then the FlowMaps, in array
order, each its `timeline`, then its chunks in order (none where the
`timeline` names no root), then whether it is a second canonical FlowMap;
then the virtual timelines, in array order, each its `map`, then its
`timeline`, then the ring it lies in, then the FlowMap of another root,
else its length; and last the property `flow`: the styles setting it, in
code-point order of their names, then rule by rule in array order the
rule's `select`, then its value, address by address. Before the schema, both validators refuse flow control written
in the earlier form (`flow_control_form`, [Flow control](#flow-control)),
root by root, each timeline's elements before its children's. A repeated anchor ID is a
`duplicate_id` wherever the earlier ID stands, and a repeated ID within
one MatchStamp's `match_claims` is refused by the schema. The
rules of statements and their provenance follow the identity rules
(the description specification, section 12). A timestamp's
coordinate is an own-axis value of its timeline, so its representation is
checked as every such value is (`representation`, at its `coordinate`); a
timestamp naming no timeline is checked for its timeline alone. An
elision's `start` and `end`, and the `span` of its `width`, are own-axis
values of its timeline too, checked and respelled so, and an elision
naming no timeline is checked for its timeline alone. The `by` of a
destination and of an `after`, and a FlowMap's gaps on its timeline's
axis, are own-axis values as well, and a virtual timeline's `length` one
on its own axis: the representation rule reads the timelines (each
flow-control element's `coordinate`, then the `by` of its `ends.after`
and of each destination and its `after`), then the timestamps, the
elisions, the FlowMaps' gaps and last the virtual timelines' lengths. `<pointer>`
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

Version 0.2.0 is four documents in `schema/0.2.0/`: the manifest
document `timetoshare.schema.json`, with the identifier
`https://timetoalign.github.io/timetoshare/0.2.0/timetoshare.schema.json`,
so the document lies below `schema/` at the path of its identifier; beside
it the provenance document `provenance.schema.json`, which defines the one
provenance entry that the manifest's statements, its flow-control
elements and FlowMaps and the MatchClaim table's rows share ([Provenance
and beliefs](#provenance-and-beliefs)),
and to which the manifest document refers for every `provenance` entry;
`tables.json`, the column types of the two tables as data ([Resources
and tables](#resources-and-tables)); and the package document
`package.schema.json`, the schema of a package's `package.yaml`
([Packages](#packages)), which refers to the manifest document for
`Descriptor`, `IriReference`, `Name` and `Meta`. Every released version's documents,
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
`MeasureMap`, `MeasureMapRow`, `Descriptor`, `Resource`, `Timestamp`, `MatchStamp`,
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
which the manifest names. Manifests and the files they name make a
**package**: a folder whose `package.yaml` lists them, so that several
manifests may share their tables ([Packages](#packages)), or a manifest
alone with the files beside it, a package of one manifest. The manifest
draws and validates without them.

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
| `timelines` | yes | the IDs of the timelines it holds data for, each a timeline or a virtual timeline of the manifest |
| `url` | yes | its location, relative to the manifest's own, so that a bare file name lies beside the manifest: a file, or a folder of files when it ends in `/` |
| `media_type` | no | its media type, or that of each file of a folder |
| `size` | no | its size in bytes; a file's only |
| `integrity` | no | the digest of its raw bytes, `{algorithm, digest}`: `algorithm` the hash function as the PREMIS vocabulary of cryptographic hash functions names it, one of `MD5`, `SHA-1`, `SHA-256`, `SHA-384` and `SHA-512`, and `digest` the digest in lower-case hexadecimal; a file's only |

`url`, `media_type`, `size` and `integrity` are the members of a
**descriptor**, the schema's `Descriptor`, which also names each manifest
and each table of a package's `package.yaml`. A manifest may name several
resources of one type, for rows kept in different files, but a timeline
is listed by at most one resource of each type (`resource_type`,
[Identity](#identity)). A **folder**, a `url` ending in `/`, is read as
one table: its files are the names ending in `.parquet` directly inside
it, not in its subfolders, none starting with `.` or `_` (a file being
written, a `_delta_log`); their schemas are unified by column name, a
column a file lacks reading as null, and one column of two Arrow types in
two files is refused. A folder has no `size` and no `integrity`
(`folder_descriptor`). A file or a folder may hold the rows of other
manifests' timelines, as the files a package's manifests share do: a
reader of the manifest keeps, for each resource, the rows of the
timelines it lists, an event's by its `timeline_id` and a MatchClaim's by
either of its timelines, and passes over the others
([Packages](#packages)). A table of events is named by the same entry, its `type`
the type of its events; the Projections table is the one such table this
version defines. Parquet is the form in which packages read and write
these tables. `schema/0.2.0/tables.json` publishes the column types of
both tables as data ([The schema document](#the-schema-document)), each
table with its `status`: the MatchClaim table is `stable`; the
Projections table, like every event type a resource names, is
`experimental` and may change in any version.

### The MatchClaim table

A **MatchClaim** connects two timelines. A synchronous MatchClaim states
that two sides happen at the same time, each side an event or the sentinel
**CHUNK**: a coordinate on a timeline that holds no event for it, stated
by the MatchClaim's anchors alone. A conceptual MatchClaim relates two
events without stating a time, and a NOMATCH states that an event has no
counterpart on the other timeline, the side without one being the
sentinel **NOMATCH**. CHUNK, like NOMATCH, is a sentinel and never an
event; each is written in the side's event ID column as its reserved
string, `CHUNK_SENTINEL` and `NOMATCH_SENTINEL`, and an event ID column
is never null. The sentinel CHUNK of a MatchClaim side is unrelated to
the chunks of a FlowMap, the stretches in the order they are played
([FlowMaps and virtual timelines](#flowmaps-and-virtual-timelines)). MatchClaims are data, not
structure, and a manifest holds none. They live in the **MatchClaim
table**, a file or a folder of files that a manifest names by its
resources of type `MatchClaim`, and it is the one place they live. Every
MatchClaim belongs to one manifest, the one holding both its timelines,
and a MatchClaim is addressed by its ID alone, which the package holds
once. It holds one row per MatchClaim and one
column per property of a MatchClaim, each of the Arrow type given; a
column whose Null is "never" holds a value in every row:

| Column | Arrow type | Null | Holds |
| --- | --- | --- | --- |
| `timeline_a_id`, `timeline_b_id` | string | never | the IDs of its two timelines, two different timelines, each a timeline of the manifest |
| `start_anchor`, `end_anchor` | anchor | allowed | the alignment anchors the two sides give, of their starts and, for intervals, of their ends; null where the MatchClaim gives none |
| `is_synchronous` | bool | never | `true` for a synchronous MatchClaim; `false` for a conceptual one, which states no temporal equivalence, and for a NOMATCH |
| `provenance` | provenance | allowed | how the MatchClaim was made and who believes it ([Provenance and beliefs](#provenance-and-beliefs)); null where the row states none |
| `certainty` | float64 | allowed | how certain the MatchClaim is, from 0 to 1, both included; null where none is stated |
| `event_a_id`, `event_b_id` | string | never | each side's event, one on each timeline: an event's ID, a Projection's where the timeline holds no event of its own ([The Projections table](#the-projections-table)), or a sentinel's reserved string, never an event: `CHUNK_SENTINEL`, the side of a synchronous MatchClaim whose coordinate the anchors state, or `NOMATCH_SENTINEL`, the side without a counterpart of a NOMATCH |
| `event_a_name`, `event_b_name` | string | allowed | the name of each event, where it is known; on a CHUNK side the name of the position it states, where it is known; null on a NOMATCH side, which has no name |
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

- Its two timelines differ.
- Its kind follows from `is_synchronous` and its two sides, each an
  event or a sentinel:

  | `is_synchronous` | Side A / side B | Kind | Anchors |
  | --- | --- | --- | --- |
  | `true` | event / event | synchronous MatchClaim between two events | a `start_anchor`, an `end_anchor` optional |
  | `true` | event / CHUNK, CHUNK / event | synchronous, CHUNK on one side | the same |
  | `true` | CHUNK / CHUNK | synchronous, CHUNK on both sides | the same |
  | `false` | event / event | conceptual | none |
  | `false` | event / NOMATCH, NOMATCH / event | NOMATCH | none |

  Every other row is refused: CHUNK stands only on a synchronous
  MatchClaim, NOMATCH only on one that is not synchronous, and never on
  both sides.
- A NOMATCH side has no name: its `event_a_name` or `event_b_name` is
  null. A CHUNK side may carry one, the name of the position it states.
- An `end_anchor` comes only with a `start_anchor`.
- Both coordinates of an anchor are cells, never null.
- A stated `certainty` lies in [0, 1].
- The ID and an event ID are non-empty strings without control
  characters (U+0000 to U+001F), as every ID of the format
  ([Identity](#identity)); an ID is given once in the table. The ID is
  no reserved string: `NOMATCH_SENTINEL` and `CHUNK_SENTINEL` stand in an
  event ID column for the sentinels alone.
- The provenance is a provenance entry ([Provenance and
  beliefs](#provenance-and-beliefs)): valid against
  `provenance.schema.json`, without a key the entry or a belief does not
  declare, its dates days of the Gregorian calendar, each actor holding
  one belief, actors compared as the IRIs they stand for under the
  manifest's `@context`.

A NOMATCH or a conceptual MatchClaim has no anchors and is a row like any
other. A CHUNK side's coordinate is the anchors' coordinate on that side:
its start in `start_anchor` and, for an interval, its end in
`end_anchor`.

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
held there. It is an event type of its own, held in the **Projections
table**, a file or a folder of files that a manifest names by its
resources of type `Projection`:

| Column | Arrow type | Null | Holds |
| --- | --- | --- | --- |
| `id` | string | never | the event's ID: an ID its source gives is kept, and one is minted otherwise, `projection_` and 13 random base-36 characters ([Identity](#identity)), never a sentinel's reserved string. An event's ID is unique in the package: the table holds an ID once, whichever timelines its rows lie on, and the package check refuses an ID held twice among all the event rows of a package, of every type and file ([Packages](#packages)) |
| `timeline_id` | string | never | the timeline the Projection is an event of, a timeline of the manifest |
| `unit`, `number_type` | string | never | the unit and the number type of its `start` and `duration`, stated once for both: those of the timeline's own axis |
| `start` | number | never | its position on that timeline's own axis |
| `duration` | number | allowed | its duration on the same axis, never negative; null for an instant |
| `projection_of` | `struct<timeline_id: string, event_id: string>` | allowed | the event it stands for, an object and never a joined string: both members given, the timeline another than the Projection's own, the event never a sentinel's reserved string; null where no such event is known |

A **number** is `struct<numerator: int64, denominator: int64, value:
double>`, a coordinate cell without its `unit` and `number_type`: its
members are filled as the row's `number_type` selects, as a coordinate
cell's are. As in the MatchClaim table, the columns may stand in any
order, further columns are kept and never checked, and the rows of one
timeline lie in one unit and one number type, its own where a manifest
is given.

A Projection repeats nothing else of its source. A side of a MatchClaim
that has no event of its own is a Projection or the sentinel CHUNK:

- **The other side has an event.** The Projection names it in
  `projection_of`: score notes aligned to a recording whose alignment
  gives onsets only are projected onto the recording's axis as instants.
- **The source names an event the package does not hold**, such as a
  note a performance inserts: a Projection under the source's ID,
  `projection_of` null. In a NOMATCH the other side stays the sentinel
  `NOMATCH_SENTINEL`, which is never an event.
- **A NOMATCH is stated from a position**: a Projection, `projection_of`
  null, since a NOMATCH has no anchor that could hold the coordinate.
- **A conceptual MatchClaim relates two positions**: a Projection on
  each side, since a conceptual MatchClaim has no anchors either.
- **A synchronous MatchClaim states a position on both sides**, naming no
  event: it is CHUNK on both sides, `CHUNK_SENTINEL` in both event ID
  columns, and adds no Projection. A Listen Here!
  export, a grid of positions aligning recordings of one piece to each
  other, states its alignment so, and so does a beat grid aligned to a
  recording. The anchors hold the positions, and nothing beyond them is
  invented.

### Provenance and beliefs

One provenance entry, defined by `provenance.schema.json`, annotates a
pair of the statements ([Describing a
manifest](#describing-a-manifest)), a flow-control element or a FlowMap
([Flow control](#flow-control)), and a MatchClaim, in its `provenance`
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
imposes one: each belief is its actor's. One reading alone is fixed, for
flow control: a flow-control element that some actor believes `false` is
rejected and left out when a flow is computed ([Flow
control](#flow-control)). A person who states a pair or a
MatchClaim through an editor or a package function is recorded with the
belief `true`; a loader or a service records how the item was made and
holds no belief. Believing an item `false` records that belief and
nothing more: it never removes a stated pair or a MatchClaim, and
removing a pair is an edit of its own. The entry of a pair adds the pair it is about,
`property` and `value`; the entry of a flow-control element, of a FlowMap
and of a MatchClaim holds the other keys alone.

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
timeline's axis. Given a manifest, every row is the manifest's, a row of
another manifest's timelines included: a file the manifests of a package
share is read filtered first, by `read_table` with the timelines a
resource lists ([Packages](#packages)), and then checked. Each problem is a `TableProblem` of a `code`, a `row`
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
| `timeline_a_id`, `timeline_b_id`, `is_synchronous`, `event_a_id`, `event_b_id` or `id` is null | `schema_violation` | the column | `'<name>' is null` |
| An ID is empty or holds a control character | `invalid_id` | `id` | `the ID is empty`, `the ID '<id>' holds a control character` |
| An ID is a reserved string, `NOMATCH_SENTINEL` or `CHUNK_SENTINEL` (in an event ID column such a string is its sentinel) | `invalid_id` | `id` | `'<string>' is reserved for a sentinel` |
| An ID repeats the ID of an earlier row | `duplicate_id` | `id` | `the ID '<id>' is given twice` |
| The file's provenance is no JSON text, no object or no provenance entry | `invalid_provenance` | `provenance`, row `None` | `the file's provenance is no JSON text`, `the file's provenance is no object`, `the file's provenance <pointer>: <problem>` |
| A timeline names no timeline and no virtual timeline of the manifest | `unknown_timeline` | `timeline_a_id`, `timeline_b_id` | `the manifest has no timeline '<id>'` |
| Both timelines are one | `claim_timelines` | `timeline_b_id` | `both sides are '<id>'` |
| An event ID that is not a reserved string is empty or holds a control character | `invalid_id` | `event_a_id`, `event_b_id` | `the event ID is empty`, `the event ID '<id>' holds a control character` |
| `CHUNK_SENTINEL` on a row that is not synchronous | `claim_events` | the side's `event_a_id` or `event_b_id`, A before B | `CHUNK_SENTINEL stands only on a synchronous MatchClaim` |
| `NOMATCH_SENTINEL` on a synchronous row | `claim_events` | the side's `event_a_id` or `event_b_id`, A before B | `NOMATCH_SENTINEL stands only on a MatchClaim that is not synchronous` |
| `NOMATCH_SENTINEL` on both sides | `claim_events` | `event_b_id` | `a NOMATCH MatchClaim names an event on its other side` |
| A NOMATCH side has a name | `claim_events` | the side's `event_a_name` or `event_b_name` | `a NOMATCH side has no name` |
| A NOMATCH has an anchor | `claim_anchors` | `start_anchor`, else `end_anchor` | `a NOMATCH MatchClaim has no anchors` |
| A synchronous row has no start anchor | `claim_anchors` | `start_anchor` | `a synchronous MatchClaim has a start anchor` |
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
| An ID is a reserved string | `invalid_id` | `id` | as in the MatchClaim table |
| An ID repeats the ID of an earlier row | `duplicate_id` | `id` | as in the MatchClaim table |
| `timeline_id` names no timeline and no virtual timeline of the manifest | `unknown_timeline` | `timeline_id` | `the manifest has no timeline '<id>'` |
| `unit` is none of the format's units, or `number_type` none of `int`, `float` and `fraction` or one the unit does not admit | `invalid_coordinate` | `unit`, else `number_type` | `'<unit>' is no unit`, `'<number type>' is no number type`, `'<unit>' admits no number type '<number type>'` |
| The row's unit and number type are not those of its timeline in the manifest, or of an earlier row on its timeline | `axis_mismatch` | `unit` where the units differ, else `number_type` | an axis message (below) |
| `start`, then `duration`, is malformed | `invalid_coordinate` | the number | a number's message (below) |
| A well-formed `duration` is negative | `invalid_duration` | `duration` | `the duration is negative` |
| A member of `projection_of` is null or empty | `invalid_projection_of` | `projection_of.timeline_id`, `projection_of.event_id` | `the projected event has no timeline_id`, `the projected event has no event_id` |
| `projection_of.event_id` is a reserved string, `NOMATCH_SENTINEL` or `CHUNK_SENTINEL` | `invalid_projection_of` | `projection_of.event_id` | `'<string>' is reserved for a sentinel` |
| `projection_of` names the Projection's own timeline | `invalid_projection_of` | `projection_of.timeline_id` | `a Projection stands for an event of another timeline than '<id>'` |
| `projection_of` names no timeline and no virtual timeline of the manifest | `unknown_timeline` | `projection_of.timeline_id` | `the manifest has no timeline '<id>'` |

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

### Packages

A **package** is a folder of manifests and the tables their resources
name, with a file `package.yaml` at its root listing them:

```yaml
manifests:
  -
    media_type: application/yaml
    url: bach/manifest.yaml
  -
    media_type: application/yaml
    url: handel/manifest.yaml
name: "Two manifests sharing their tables"
tables:
  -
    media_type: application/vnd.apache.parquet
    type: MatchClaim
    url: tables/MatchClaim/
  -
    media_type: application/vnd.apache.parquet
    type: Projection
    url: tables/Projection/
timetoshare: "0.2.0"
```

Its schema is the package document, `schema/0.2.0/package.schema.json`
([The schema document](#the-schema-document)), and every object in it is
open:

| Key | Required | Holds |
| --- | --- | --- |
| `timetoshare` | yes | the version of the package, `"0.2.0"`, which every manifest and every table file of it declares |
| `id` | no | the package's IRI where it is published, such as its repository or its DOI |
| `name`, `meta` | no | its name and free-form metadata, as a manifest's |
| `manifests` | yes | the manifests, each once, each a descriptor ([Resources](#resources)): its `url`, and optionally its `media_type`, `size` and `integrity` |
| `tables` | yes, possibly empty | the tables, each a descriptor with the `type` of its rows, as a resource states it; a type may have several entries, for rows kept in different files |

- **URLs** are resolved against the address of the document stating
  them: an entry of `package.yaml` against the package's root, a
  resource against its manifest. A URL leading outside the package names
  nothing in it. A `url` ending in `/` names a folder, read as one table
  ([Resources](#resources)); a folder has no `size` and no `integrity`.
- **The manifests are listed one by one**, never by a pattern.
- **Each manifest's resources name the files and folders it reads**,
  with the timelines whose rows it keeps, so that the manifests and
  `package.yaml` name the same files, and nothing in a table file names a
  manifest. A **table resource** is one whose `type` is `MatchClaim` or
  `Projection`, whose `url` names a folder (ends in `/`) or a Parquet file
  (ends in `.parquet`), or whose `media_type` is
  `application/vnd.apache.parquet`; only a table resource names a table
  entry, and it names one exactly, by the same resolved URL and the same
  type: a resource naming one file of a folder entry names no entry. Any
  other resource, a recording, an image or a score file, is carried with
  its manifest and not checked against `tables`.
- **A file's metadata** states its type (`timetoshare:type`, such as
  `Projection`) and its format version (`timetoshare:version`); a
  MatchClaim file may state the provenance its rows share
  (`timetoshare:provenance`, [The MatchClaim
  table](#the-matchclaim-table)). Nothing else of a file's metadata is
  read.
- **A manifest alone**, its resources naming files beside it, without a
  `package.yaml`, stays valid unchanged: it is a package of one manifest.
  Checked against that manifest, a row of a timeline the manifest does
  not hold is refused (`unknown_timeline`, [Checking the
  tables](#checking-the-tables)). Manifests that share a file are listed
  by a `package.yaml`, which the package check reads.

**Validating `package.yaml`.** Python's `validate_package(value)` and
npm's `validatePackage(value)` check the value of a `package.yaml` alike
and raise the first problem as a `SchemaValidationError`. A value without
`timetoshare` is `not_a_package` at the root (`not a TimeToShare
package`), and one declaring another version raises
`UnsupportedVersionError`, as a manifest does. Then the package schema,
its problem chosen by the one path rule (`schema`); then, entry by entry,
the manifests and then the tables:

| Rule | Code | Path | Message |
| --- | --- | --- | --- |
| A manifest is listed again under the same `url` | `duplicate_url` | the later entry's `url` | `the manifest '<url>' is listed twice, first at <pointer>` |
| A table is listed again under the same `url` and `type` | `duplicate_url` | the later entry's `url` | `the table '<url>' of the type <type> is listed twice, first at <pointer>` |
| An entry whose `url` ends in `/`, naming a folder, has a `size` or an `integrity` | `folder_descriptor` | that member, `size` before `integrity` | `'<url>' names a folder, which has no size` (`… which has no integrity`) |

URLs are compared as written, and one `url` under two types is valid.
Python's `package_schema_path()` returns the path of the package document,
and `load_package_schema()` returns it with the definitions it reaches in
the manifest document bundled into it, so that every reference is local;
the npm package validates against the same bundle.

**Reading a manifest's rows.** Python's
`timetoshare.tables.read_table(path, *, timelines=None, type=None)` reads
a table, a file or a folder of files, as one Arrow table through
`pyarrow.dataset`; `table_files(path)` lists a folder's files, sorted by
code point. Given `timelines`, bare IDs, the reader keeps the rows of
those timelines: an event's whose `timeline_id` is listed, a
MatchClaim's either of whose timelines is, so that a check against the
manifest sees a MatchClaim reaching outside it. A manifest's rows of one
resource are therefore `read_table` of the resource's URL with its
`timelines`, which the table checks against the manifest then pass. A
MatchClaim file's shared provenance is filled into the `provenance` cell
of each of its own rows before the files are joined, so that no reader of
a folder loses it. The table's type is what its files state, else
`type`; where both are stated they agree, and the table returned states
its type alone in its metadata. An empty folder gives no rows, in the
declared columns of a MatchClaim or Projections table and in none for
another type. The rows come in the files' order, then each file's;
readers never rely on it, and an unsorted file is read. `read_table`
raises `FileNotFoundError` for a path that is neither a file nor a
folder, and a `TableError` for:

| Refusal | Code | Column | Message |
| --- | --- | --- | --- |
| Two files state two types | `table_type` | none | `'<file>' holds the type <type> and '<file>' the type <type>` |
| A file states another type than `type` | `table_type` | none | `'<file>' holds the type <type>, not <type>` |
| No file states a type and no `type` is given | `table_type` | none | `the table names no type: no file states 'timetoshare:type'` |
| One column has two Arrow types in two files, nullability and the names of list items not compared | `column_type_mismatch` | the column | `the column '<name>' is <type> in '<file>' and <type> in '<file>'` |
| `timelines` is given and the files lack a column naming a row's timeline | `schema_violation` | that column | `the table has no column '<name>'` |
| A MatchClaim file's provenance is no provenance entry | `invalid_provenance` | `provenance` | the file's provenance message ([Checking the tables](#checking-the-tables)), followed by `, in '<file>'` |
| A MatchClaim row states its own provenance beside the file's | `invalid_provenance` | `provenance`, at its row in the table read | `the provenance is stated in the file's metadata and in the row` |
| A MatchClaim file states a shared provenance and its `provenance` column is of another type than the declared one, so that the provenance cannot be filled in | `schema_violation` | `provenance` | `the column 'provenance' is <type>, not <type>, in '<file>'` |

**The package check.** Python's
`timetoshare.tables.package_problems(path)`, `path` a package's
`package.yaml` (`PACKAGE_FILE`), lists every problem of a package. Each is
a `PackageProblem` of a `code`, a `file` (its path from the package's
root, `/`-separated: `package.yaml`, a manifest, a table's file, or a
table's folder for what its files share), a `row` of that file (`None`
for no single row), a `path` (a JSON path in `package.yaml` or a
manifest, the column path of a table's row) and a `message`.
`PackageCode` names the codes of its own rules; a problem may also carry
a manifest validation's code or a table check's. It raises
`FileNotFoundError` where `path` is no file and `ValueError` where
`package.yaml` or a manifest is no readable text. It checks, in this
order:

1. `package.yaml` itself, by `validate_package`; a problem there ends the
   check, another version being reported as `version_mismatch`.
2. Manifest by manifest, as listed: a missing manifest, and a manifest
   that is not valid, with its validation's code and path.
3. Table by table and file by file: a missing file or folder, a file an
   earlier entry of the same type reaches already, such as a file entry
   inside a listed folder (the later entry reads its other files only, so
   that no row is read twice), a file of another type or version, and a
   column of two Arrow types (whose rows are then not read).
4. The rules the manifests and the rows keep together, rule by rule as
   the table below lists them, each over the event rows and then the
   MatchClaim rows, in the order of the entries, their files and their
   rows. They read the columns `id`, `timeline_id`, `unit` and
   `number_type` of the event tables and `id`, `timeline_a_id` and
   `timeline_b_id` of the MatchClaim tables.
5. Manifest by manifest, the table checks of each MatchClaim or
   Projections table its resources name, in the order they first name it,
   over the rows of the timelines those resources list, each problem
   placed in its file and row ([Checking the
   tables](#checking-the-tables)). A problem a package rule already
   reports at the same file, row and column with the same code, or an
   `unknown_timeline` on a MatchClaim reaching another manifest, is not
   repeated.

| Rule | Code | File, path | Message |
| --- | --- | --- | --- |
| A manifest `package.yaml` lists is missing | `missing_file` | `package.yaml`, the entry's `url` | `no manifest lies at '<url>' in the package` |
| A manifest declares another version than the package | `version_mismatch` | the manifest, `timetoshare` | `the manifest declares the version '<version>', the package '<version>'` |
| A table's file or folder is missing | `missing_file` | `package.yaml`, the entry's `url` | `no file lies at '<url>' in the package` (`no folder lies at …`) |
| A file an earlier table entry of the same type reaches | `duplicate_url` | `package.yaml`, the later entry's `url` | `the file '<file>' is read by the table '<earlier url>' already` |
| A file states another type than its entry | `table_type` | the file, `[]` | `the file holds the type <type>, its table the type <type>` |
| A file declares another version than the package | `version_mismatch` | the file, `[]` | `the file declares the version '<version>', the package '<version>'` |
| One column has two Arrow types in two files | `column_type_mismatch` | the folder, the column | `the column '<name>' is <type> in '<file>' and <type> in '<file>'` |
| A timeline ID, a virtual timeline's included, is held by two manifests | `duplicate_timeline` | the later manifest, the timeline's `id` | `the timeline '<id>' is a timeline of '<manifest>' as well` |
| A table resource's URL names no table entry of its type, or leads outside the package | `unknown_table` | the manifest, the resource's `url` | `the resource '<id>' names '<url>', which is no table of the type <type> in the package` |
| An event ID is held twice among all the event rows of the package, of every type and file; then a MatchClaim ID twice among its MatchClaims | `duplicate_id` | the later row's file and row, `id` | `the event ID '<id>' is given twice, first in '<file>' at row <row>` (`the MatchClaim ID …`) |
| A row's timeline (a MatchClaim's either, column by column) is null, where the file holds the column as strings | `schema_violation` | the row, the column | `'<column>' is null` |
| A row's timeline is held by no manifest | `unknown_timeline` | the row, the column | `no manifest of the package has the timeline '<id>'` |
| A row's timeline is listed by none of its manifest's resources of the row's type naming the row's table | `unlisted_timeline` | the row, the column | `the timeline '<id>' of '<manifest>' is listed by no resource of the type <type> naming this table` |
| A MatchClaim's two timelines lie in two manifests | `claim_across_manifests` | the row, `timeline_b_id` | `the MatchClaim joins the timeline '<id>' of '<manifest>' and the timeline '<id>' of '<manifest>'` |
| An event row states a unit and a number type the format admits that are not its timeline's in its manifest | `axis_mismatch` | the row, `unit` where the units differ, else `number_type` | `a coordinate in <unit> (<number type>) on the timeline '<id>' in <unit> (<number type>)` |

`fixtures/packages/0.2.0/` holds the package fixtures: `shared/`, two
manifests sharing a folder of Projections and a folder of MatchClaims,
beside an `expected.yaml` naming the rows each resource reads,
`acceptances/<case>/`, the shared package with one change each that the
package check accepts, such as a manifest naming a recording, and
`rejections/<case>/`, the shared package broken by one change each,
beside the problems the package check reports
([Fixtures](#fixtures)); Python's `package_fixture_path(*parts)` gives
their paths.

## MatchStamps

### From MatchClaims to anchors

An **alignment anchor** is a pair of coordinates of two timelines, each
on its timeline's own axis.

- A synchronous MatchClaim gives the anchor of its `start_anchor` and, if
  it has one, of its `end_anchor`, whatever its sides are: a side naming
  an event gives that event's coordinate, a CHUNK side its coordinate and
  no event. A MatchClaim with both anchors is an **interval
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
places it; a band that is not displayed hides everything it holds; a
root's flow control band draws the flow control of its whole tree, and no
other timeline draws one), and the content `timeline`, `child`,
`boundary` (a segment's start on its segment line, or a chunk's),
`chunk` (the segment of a FlowMap's line that one entry plays, drawing
nothing of its own and on a virtual timeline holding the bands of its
window onto its source), `ancestor`, `map`,
`region` (the atomic sections hidden by default, through the selector
`class` naming `tts:AtomicSection`), `break`, `section_break` and
`barline` (each a vertical line at its coordinate), `jump` (one arc per
destination whose place is not `by` 0, from the jump's coordinate to
that place, labelled with its destination's `label`, none for a
destination of manifestation `volta`, and none to a place a `to` names
where the element named is rejected; hidden by default; a rejected
element, or under a reading an unread one, is drawn faded), `symbol` (the music-font glyph of an
element's manifestation, such as 𝄆 for a repeat start), `fork` (a
jump's volta destinations as a stem splitting into one arrow per
destination, each with its passes), `leader` (the thin line joining a label
moved to a further tier to its element),
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
`ContinuousPhysicalTimeline` for `seconds`, a conversion map's type, or
the IRI of a class a region's `type` statement names),
`facet` (the bands drawing that facet), `within` (a timeline and its
descendants, or a virtual timeline and what its chunks' windows show),
`inside` (an element type that holds the element at any
depth) and `coordinates` (`"primary"` or `"secondary"`: the wedges and
labels of the named timestamps' primary coordinates, or of their secondary
ones; no other element). The defaults hide the secondary ones, so the rule
`{"select": {"element": "wedge", "coordinates": "secondary"}, "set":
{"display": "inline"}}` shows their wedges. The property `shadow` colours a card's offset shadow,
`rotation` turns a wedge about its tip, in whole degrees from −180 to 180,
`label-display` chooses the labels of a flow-control element (`none`
or words from `name`, `id` and `label`; `name label` unless a rule says
otherwise, so that naming an element shows its name), and `flow` draws a
card in one of its timeline's FlowMaps (`{"select": {"addresses":
[{"id": "#score", "part": ["card"]}]}, "set": {"flow": "#flow_map_1"}}`;
only a rule of the manifest's own `rules` selecting cards by their
addresses sets it, never a style, and both validators refuse any other use
as `flow_rule`). A placed virtual timeline is drawn in a card of its own,
its chunks as braces in its regions band, each addressed `{"id": "#V",
"facet": "regions", "part": [k]}` with its index `k` in `chunks`, and the
tick at a chunk's start as a `boundary` (the drawing specification,
section 8.10).
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
- `flow_control` by coordinate, then ID, and every jump's `targets` by
  place: the destination without a place first, then those with `by`, by
  value, then those with `to`, by ID;
- `resources`, `flow_maps` and `virtual_timelines` by ID;
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
array is reordered: a FlowMap's `chunks`, which are in the order they
are played, `graphical` rules, display orders,
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
  (a `LinearMap`'s `scalar: 1.0` is the default `1`, so a text stating it is not
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
  warnings, `context_absent`, `bundle_blank`, `manifestation_unknown`,
  `convention_unknown` and `flow_conflict`, as `{code, path, message}` entries sorted by
  path, compared element by element with an index before a key, and then
  by code.
- `statement_problems(value)` returns the problems of a manifest's
  statements alone, with the provenance of the flow-control elements and
  FlowMaps, as a list of `SchemaValidationError`s, empty where they are
  sound, and refuses nothing outside them (the description specification,
  section 12).
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
  `validate_package(value)` checks the value of a package's
  `package.yaml`, `package_schema_path()` returns the path of the package
  document and `load_package_schema()` that document with the
  definitions it reaches bundled into it ([Packages](#packages)).
- `timetoshare.tables`, which needs the extra `tables`
  (`pip install "timetoshare[tables]"`, which installs pyarrow), reads
  the two tables as Arrow tables ([Resources and
  tables](#resources-and-tables)). `tables_path()` returns the path of
  `tables.json` (`TABLES_DOCUMENT`), from which `MATCH_CLAIM_SCHEMA` and
  `PROJECTION_SCHEMA` declare their columns, `MATCH_CLAIM_REQUIRED` and
  `PROJECTION_REQUIRED` name the columns that hold no null,
  `NOMATCH_SENTINEL` and `CHUNK_SENTINEL` hold the reserved strings of
  the two sentinels ([The MatchClaim table](#the-matchclaim-table)), and
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
  file's. `read_table(path, *, timelines=None, type=None)` reads a table,
  a file or a folder of files (`table_files(path)`), keeping the rows of
  the timelines given, and `package_problems(path)` checks a package
  whole, each problem a `PackageProblem` (`code`, `file`, `row`, `path`,
  `message`) of a `PackageCode`, a `TableCode` or a validation code
  ([Packages](#packages)); `PACKAGE_FILE` is `"package.yaml"`, and
  `TYPE_METADATA_KEY` and `VERSION_METADATA_KEY` are the metadata keys
  `"timetoshare:type"` and `"timetoshare:version"`. `alignment_anchors`, `potential_matchstamps` and
  `believed_rows` derive the unique anchors and the potential MatchStamps
  of a MatchClaim table under the belief filter ([From MatchClaims to
  anchors](#from-matchclaims-to-anchors)), a reference derivation for
  conformance; each takes a `believer`, the `beliefs` it keeps (by
  default `DEFAULT_BELIEFS`) and the `context` under which actors
  expand. `fixture_path(name)` returns a file of the table fixture and
  `package_fixture_path(*parts)` a package fixture or a file in it
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
  `validatePackage(value)` checks the value of a `package.yaml` as
  Python's `validate_package` does, with the same codes, paths and
  messages ([Packages](#packages)).
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

### Versions of a dataset

The marker `timetoshare` says how to read a file; nothing in a manifest
says which state of its data it is. A dataset keeps its manifests and the
tables they name in one git repository, and that repository's release tags
(`v2.1.0`) version all of them together: a citation of an element pins
its state by the tagged URL or the DOI of the release. One repository
holds one dataset; where several share one, their tags carry a prefix
(`mtd/v2.0.0`). A tag is never moved or deleted.

A release compares the tree of the last tag with the new one, every
manifest and every table, by value in the complete form and canonical
order, elements matched by their IDs at any depth:

| Change | Step |
| --- | --- |
| removing anything with an ID (a timeline, a child, a group, a MeasureMap, a conversion map, a region, a flow-control element, a FlowMap, a virtual timeline, a resource, a named timestamp, a named MatchStamp, an alignment anchor), a group member, a statement pair, a prefix of `@context`, a row of a table, a manifest file | major |
| changing an ID (a removal and an addition) | major |
| adding any of these | minor |
| editing what an element states (a unit, a number type, a length, an offset, a map's numbers, a coordinate, a FlowMap's chunks, a statement's value, a prefix's IRI), corrections included | minor |
| a belief, a rejection included | patch |
| a `name`, `meta`, styling in `graphical` (a named timestamp's `display` included), an elision added, edited or removed, a resource's `url` for the same bytes (its `integrity` equal) | patch |
| another form or serialization of the same value, comments | none |
| giving an ID to an element of another type, or again after its element was removed | refused |

Numbers compare by exact value wherever the format reads a number, as
[Defaults](#defaults) states: an integer, a float and a Fraction pair of
equal value are one value (`2`, `2.0`, `[2, 1]` and `[4, 2]`), so a
conversion map's numbers and a MeasureMap row's lengths written in
another spelling are no change, while `0.1` and `[1, 10]` differ. `meta`
and the literals of `statements` and `provenance` compare as written. A
file that is a manifest in one state and cannot be read in the other is
reported as undetermined, never as a removal.

A major version promises that every cited ID still exists, not that every
coordinate keeps its meaning.

The `timetoshare` command of the Python package prints the step of a
change and one line per finding (`--json` for the whole report): between
two directories, between two git references of the repository `--repo`
(default `.`), or between a reference and the changes staged for the next
commit, when the second argument is left out; OLD `-` is the empty tree,
the state before a first release. From git it reads only the
manifests (the files ending `.yaml`, `.yml` or `.json`) and the table files
their resources name, never the rest of the tree; a table file is read
through the filters git's attributes name for its path, so a table kept by
Git LFS is compared as the table where git-lfs is installed. It exits 2
when a change is refused. Comparing the rows of a MatchClaim or Projections table needs
the `tables` extra; without it, and for tables of any other type, a changed
table is reported as undetermined.

Two states alone cannot show an ID given again after a release in between
removed its element. `--history` (git references only) also reads every tag
reachable from NEW (or `HEAD`) and from OLD, and OLD itself, in the order
of the history, and refuses (`reused_id`) every ID of NEW that one of them
held for an element of another type, or for an element that a later one of
them no longer holds. The release check below runs it from the last tag
to `HEAD`; the hooks below compare two states only.

```console
$ timetoshare step v2.1.0 HEAD
step: major
scope: op106
major	removed	op106.yaml	#clt_3	Timeline #clt_3 removed
```

In Python, `manifest_step(old, new)` compares two manifests,
`tree_step(old_root, new_root)` two directories and `git_step(old_ref,
new_ref, repo, history=False)` two references (`new_ref=None`: the staged
changes); the last two return a `StepReport` with the `step`, the
`findings` (each a `Finding` with `kind`, `step`, `path`, `id` and
`detail`), the flags `refused` and `undetermined`, and the `scope`, where
every finding lies: the manifest file's name without extension, or for a
file named `manifest.<ext>` its folder's name (`bpsd/op106/manifest.yaml`
gives `op106`); where the findings lie in several manifest files, the top
folder that holds them all (`bpsd`), or none.

The release tool [release-please](https://github.com/googleapis/release-please)
computes the version from Conventional Commits: a `feat` commit makes a
minor step, a commit whose header carries `!` a major one, and every other
commit a patch. A dataset repository therefore writes these types, the
scope naming the manifest or the part of the dataset (`op106`, `bpsd`):

| Type | Instead of | Step | Changelog section | For |
| --- | --- | --- | --- | --- |
| `feat` (release-please reads `feature` alike) | `feat`; `fix` for a correction | minor | Added or changed | adding or editing data, corrections included: `feat(op106): add the BPSD recordings` |
| `remove` with `!` | `feat!` | major | Removed, and the IDs under the breaking changes | removing anything, changing an ID, with the footer `BREAKING CHANGE: removes #clt_3, #region_7`; any other type with `!` or with that footer also makes a major release, and the hook refuses it for a removal |
| `belief` | `fix` | patch | Beliefs | recording a belief |
| `label` | `chore` | patch | Names | a `name` |
| `graphic` | `style` | patch | Drawing | `graphical`: styling rules, orders, display words, elisions |
| `meta` | `chore` | patch | Application data | `meta` |
| `move` | `refactor` | patch | Moved | a resource's `url` changed for the same bytes |
| `docs` | `docs` | patch | Documentation | prose |
| `fix` | `fix` | patch | Scripts | the repository's own scripts or loaders |
| `chore`, `build`, `ci`, `refactor`, `test`, `style` | the same | none (hidden) | — | everything else about the repository's code |

A commit touching data and code takes the type of its data. Moving a
manifest file changes its address and is a removal.

Two git hooks keep the types honest. `timetoshare hook prepare-commit-msg`
writes the type only for the two large steps: `feat` for an addition or an
edit, and `remove` with `!` and the `BREAKING CHANGE` footer for a removal,
with the scope where every change lies in one manifest or directory. It
writes them before the subject given with `-m` or before the editor opens,
so that `git commit -m "add the BPSD recordings"` commits `feat(op106): add
the BPSD recordings`. For a patch (a belief, a `name`, `graphical`, `meta`,
a moved resource) it writes no type and only suggests one, `Suggested
type "belief(op106):", since this commit records beliefs only`, because
the choice between `belief`, `docs` or `fix` is the author's. A commit mixing
kinds of change (additions, edits, removals, beliefs, names, drawing,
application data, moves) gets a hint, `This commit mixes 2 kinds of change
(1 added, 1 belief); one kind of change per commit keeps the history and
the changelog clear.`, also when the message already has a type; nothing
counting the smaller changes is written into the message. A message whose
first line already reads as a header (`type(scope): `, whatever the type)
keeps it and gets no suggestion. Where the message is edited, the
suggestion and the hint are comment lines, which git removes; where it
comes from `-m` or `-F` (`git commit -m x -e` included, where they are
printed before the editor opens), or where `git config commit.cleanup` is
`whitespace`, `verbatim` or `scissors`, with which git keeps comment
lines, they are printed on standard error and the message stays as given
(a `--cleanup=` option on the command line does not reach the hook). The
hook leaves merges, amends, squashes and commits without a change of the
data alone. `timetoshare hook commit-msg` refuses a message whose type
gives a lower step than an addition, an edit or a removal requires, or
that has no type at all for such a change (the first hook was skipped), a
removal written with any type but `remove` with `!` (`feat!` and `remove`
without `!` included), a header without a subject
(closing the editor on the written `feat(op106): `) and an ID given to an
element of another type. For a patch, a missing type or a type without a
step (`chore`) is only a warning naming the suggested type, and the commit
goes through. It also warns where a data type or a `!` gives a higher step,
where `remove` without `!` or a `BREAKING CHANGE` footer stands on a
commit that removes nothing,
and where the footer misses a removed ID; the check hook is `verbose`, so
pre-commit shows these warnings when the message is accepted. Both read
comment lines by git's `core.commentChar` (`#` where it is `auto`). For
`git commit --amend` with the editor or `--no-edit`, the first hook records
the amended commit in `timetoshare-amend-base` in the git directory, and
the second compares the amended commit's parent (the empty tree for a first
commit) with the index; `git commit --amend -m` tells the hooks no amend
and is compared with `HEAD`.

This repository is a pre-commit hook repository: its
`.pre-commit-hooks.yaml` offers both hooks and a third,
`timetoshare-validate`, which runs `timetoshare validate` on every staged
`.yaml`, `.yml` and `.json` file. pre-commit installs them by running `pip
install .` in its clone of this repository; the root `setup.py` is an empty
distribution, and each hook installs the package from `./python` of the
same clone. A dataset repository's `.pre-commit-config.yaml`:

```yaml
default_install_hook_types: [pre-commit, prepare-commit-msg, commit-msg]
repos:
  - repo: https://github.com/TimeToAlign/TimeToShare
    rev: <tag or commit>
    hooks:
      - id: timetoshare-commit-type
      - id: timetoshare-commit-check
      - id: timetoshare-validate
```

and, once per clone, `pre-commit install --hook-type pre-commit
--hook-type prepare-commit-msg --hook-type commit-msg`. `rev:` is a tag or
a commit, never a branch: pre-commit keeps the environment of a `rev` and
never reinstalls it.

`timetoshare validate [PATH ...]` validates the files named, or, without
arguments, every `.yaml`, `.yml` and `.json` file under the current
directory outside `.git`, and prints one line per problem, `<path>: <code>
at <JSON pointer>: <message>`, a warning's code preceded by `warning: `. A
file is a manifest when `loads` reads it as an object holding
`timetoshare`; other files are skipped. A manifest is refused for its first
violation, with the code `validate` raises it with, or
`unsupported_version` at `#/timetoshare` for another version. A file
`loads` cannot read is refused as `unreadable` only when its text names the
format at the top: a YAML line starting with the key `timetoshare:`, or,
in a text starting with `{`, the key of the JSON object; every other such
file is skipped (a workflow file using YAML anchors, a YAML file of several
documents, an `mkdocs.yml` with `!!python/name:` tags). The command exits 1
when a file is refused, else 0, warnings included; the hook is `verbose`,
so pre-commit shows the warnings of an accepted manifest too.

```console
$ timetoshare validate op106.yaml notes.yaml
op106.yaml: duplicate_id at #/timelines/1/id: 'score' is not unique in the manifest, first at #/timelines/0/id
```

release-please's configuration of a dataset repository names the
sections and makes a dataset's drafts `0.y.z` releases:
`bump-minor-pre-major` turns a removal into a minor step and
`bump-patch-for-minor-pre-major` an addition into a patch below 1.0.0, so
a removal raises `y`; `1.0.0` is set by a person with a `Release-As: 1.0.0`
footer. `initial-version` with a `.release-please-manifest.json` holding
`{".": "0.0.0"}` makes the first release `0.1.0`, a draft like every
`0.y.z`, and tells the release check below that nothing is released yet;
`include-component-in-tag` keeps the tags `v<version>`, the tags the
release check reads.

```json
{
  "packages": {
    ".": {
      "release-type": "simple",
      "changelog-path": "CHANGELOG.md",
      "initial-version": "0.1.0",
      "include-component-in-tag": false,
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": true,
      "changelog-sections": [
        {"type": "feat", "section": "Added or changed"},
        {"type": "remove", "section": "Removed"},
        {"type": "belief", "section": "Beliefs"},
        {"type": "label", "section": "Names"},
        {"type": "graphic", "section": "Drawing"},
        {"type": "meta", "section": "Application data"},
        {"type": "move", "section": "Moved"},
        {"type": "docs", "section": "Documentation"},
        {"type": "fix", "section": "Scripts"},
        {"type": "chore", "hidden": true},
        {"type": "build", "hidden": true},
        {"type": "ci", "hidden": true},
        {"type": "refactor", "hidden": true},
        {"type": "test", "hidden": true},
        {"type": "style", "hidden": true}
      ]
    }
  }
}
```

The hooks are the gate where people commit to the default branch without
pull requests; a commit made without them is caught by the reusable
workflow `.github/workflows/dataset-release-check.yml` of this repository,
which a dataset's release workflow runs before release-please. It checks
the repository out with its history, its tags and its Git LFS files and
runs `timetoshare release-check`. A push is a release when the version in
`.release-please-manifest.json` is not `0.0.0` and has no tag `v<version>`
yet: the push that merges a release pull request, before release-please
tags it. The check then compares the latest version tag reachable from
`HEAD` (`git describe --tags --abbrev=0 --match 'v[0-9]*'`; the empty tree
where there is none) with `HEAD`, with `--history`, and fails when an ID is
given again, when a change is undetermined (a table that cannot be
compared, a manifest that no longer reads), or when the release from the
tag's version (`0.0.0` without a tag) to the new one allows a lower step
than the data requires (from 1.0.0 on, the first number that rises names
the step of change a release allows; below 1.0.0 the middle number allows
a major step and the last a minor one, as the configuration above makes
release-please count); the remedy is a commit whose type says what the
data does, or a `Release-As:` footer. On every other push it reports the
same comparison, undetermined changes included, and never fails. Either
way the findings and the verdict also go to the job summary (`--summary
"$GITHUB_STEP_SUMMARY"`):

```console
$ timetoshare release-check
the data from v0.1.0 to HEAD
step: major
scope: op106
release: 0.1.0 to 0.1.1 allows changes up to minor
major	removed	bpsd/op106/manifest.yaml	#clt_3	Timeline #clt_3 removed
fails: a release from 0.1.0 to 0.1.1 allows changes up to minor; the change requires major
```

It exits 2 when a release fails, 1 when the version cannot be read (or, at
a release, is lower than the last tag's), else 0. The workflow's input
`timetoshare-ref` names the TimeToShare tag or commit whose package runs
the check, the one the workflow is taken from:

```yaml
name: Release
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  check:
    uses: TimeToAlign/TimeToShare/.github/workflows/dataset-release-check.yml@<tag or commit>
    with:
      timetoshare-ref: <the same tag or commit>
  release-please:
    needs: check
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - uses: googleapis/release-please-action@v5
        with:
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
```

Until a TimeToShare release carries these hooks, the release check and
schema 0.2.0, a dataset pins one commit of `main` in three places, all
the same commit: the pre-commit `rev:`, the workflow's `@<ref>` and its
`timetoshare-ref`. `pre-commit autoupdate` must not be used until then: it
moves `rev:` to the latest tag, which has none of them.

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
them by hand. The ten manifests of flow control under
`fixtures/0.2.0/flow/` are emitted the same way, and
`fixtures/flows/0.2.0/` holds the expected flows of the nine that hold
flow control, each derived by hand beside the trace it was derived with
([fixture guide](fixtures/README.md#flow-fixtures-and-expected-flows)). The statement fixtures under `fixtures/0.2.0/statements/`
have their expected RDF under `fixtures/rdf/0.2.0/`, canonical N-Quads
that `scripts/emit_rdf.py` writes. The table fixture lies apart, under
`fixtures/tables/0.2.0/`: a manifest (`manifest.yaml`), its MatchClaim
table (`match_claims.parquet`), its Projections table
(`projections.parquet`) and the alignment anchors and potential
MatchStamps expected of the MatchClaim table (`expected.yaml`), every
value written by hand in `scripts/emit_tables.py`, which alone writes
them; the expected values are literal data, never computed by the
derivation they test. The package fixtures lie under
`fixtures/packages/0.2.0/` ([Packages](#packages)): `shared/`, a package
of two manifests sharing a folder of Projections and a folder of
MatchClaims, `acceptances/<case>/`, the shared package changed and still
accepted, and `rejections/<case>/`, the shared package breaking one
rule each, every package beside an `expected.yaml` of literal data, the rows read or the
problems reported, written by `scripts/emit_packages.py`, which alone
writes them ([fixture guide](fixtures/README.md#the-package-fixtures)).
The rejection and warning cases are
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

and the package fixtures, also from `python/`:

```bash
uv run python ../scripts/emit_packages.py
```

Each of the four scripts refuses to overwrite the files of a version
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
