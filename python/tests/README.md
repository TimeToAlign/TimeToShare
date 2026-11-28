# Test strategy for the `timetoshare` Python package

This suite proves the public contract of schema 0.2.0: one manifest shape,
described by one schema document, read by one validator. The package
supports this version only.

Every rule is proved by a document written inline in its test, never by
editing a fixture: the documents are the smallest that exercise the rule, so
a passing test cannot be a restatement of a fixture the implementation
produced. The shared rejection and warning cases (`fixtures/rejections/0.2.0/`
and `fixtures/warnings/0.2.0/`) are read by this suite and by the JavaScript
suite, so both validators are held to the same paths, the same messages
and the same lists; so are the cases of several problems
(`fixtures/precedence/0.2.0/`), which pin the one path rule.

## What the package promises

1. Every manifest is `{timetoshare, timelines, id?, name?, meta?, groups?,
   measure_maps?, graphical?, @context?, statements?, provenance?}`;
   `validate` accepts exactly the values the schema and the rules below
   accept, and raises the first violation with its code and
   path.
2. A value without the version marker is refused at the root, a value with
   another version raises `UnsupportedVersionError`.
3. Unknown keys are kept and listed by `unknown_keys`, and a valid manifest
   without `@context`, or describing a bundle without an ID, draws the
   warnings `manifest_warnings` lists; neither is ever refused.
4. `complete` and `minimal` convert between the complete and the minimal
   form, both pure, from one table of defaults that agrees with the schema.
5. `dumps` writes every JSON value, a manifest put in canonical order and its
   own-axis values respelled first, in canonical YAML, pretty JSON and RFC
   8785 JSON, the same bytes as the JavaScript package; `loads` reads every
   serialization and `serialization_of` names a text's.
   `file_form` infers how a manifest file writes its manifest and
   `dumps_file` writes a value back in that form, the same bytes as the
   JavaScript package's `fileForm` and `dumpsFile`.
6. Schema, fixture, font and catalogue accessors resolve package data
   independently of the working directory; the wheel and the sdist ship the
   schema document, the two specifications `docs/description.md` and
   `docs/drawing.md`, the catalogue with its schema and the licence.
7. `timetoshare.statements` reads and writes the property–value pairs of
   the bundle, its timelines and its regions with their provenance, and
   `timetoshare.catalogue` reads them in words through the catalogue of
   identifier systems, verbs and types, with the same values, the same
   errors and the same messages as the JavaScript package; an independent
   JSON-LD processor reads the statement fixtures to the expected RDF.
8. `manifest_step`, `tree_step` and `git_step` name the version step a
   change of a repository of manifests requires, with one finding per
   change, and the `timetoshare` command's two hooks write and check the
   commit type of a staged change (`commit_types`); `release_step` names the
   step of change a release from one version to the next allows,
   `release_allows` says it in words, and `timetoshare release-check`
   decides whether a dataset repository's `HEAD` is a release and refuses
   one that allows less than the change requires; `timetoshare validate`
   validates manifest files, and
   the repository's `.pre-commit-hooks.yaml` offers the three as
   pre-commit hooks.

## The schema document

`schema_path()` is `schema/0.2.0/timetoshare.schema.json`; `load_schema()`
parses it. The tests hold invariants of the document, never a transcript of
its definitions; the definitions' contents are proven by the fixtures and the
rejection cases that use them (`test_schema.py`):

- **One document, one root.** `$id` is
  `https://timetoalign.github.io/timetoshare/0.2.0/timetoshare.schema.json`,
  `$schema` the 2020-12 dialect, the root `$ref` is `#/$defs/Manifest`,
  and `schema/` holds exactly the directory `0.2.0` with exactly that file.
  Every `$ref` is local (`#/$defs/<name>`) and names a definition; no node
  carries `$anchor`.
- **The public definitions.** The definitions include the twenty-two
  public ones `Manifest`, `Timeline`, `Group`, `Graphical`,
  `ConversionMap`, `Coordinate`, `Number`, `Fraction`, `TimeUnit`,
  `NumberType`, `Id`, `MeasureMap`, `MeasureMapRow`, `Descriptor`,
  `Resource`, `Timestamp`, `MatchStamp`, `AlignmentAnchor`, `Context`,
  `Statements`, `StatementValue` and `ProvenanceEntry`, and the root's
  description, which tells a host what it may refer to, names exactly
  these, in this order.
- **The map types.** `ConversionMap` chooses between exactly the ten types
  `ChainMap`, `CombinationMap`, `ConstantMap`, `FloatingMeasureMap`,
  `LinearMap`, `MeasureBeatMap`, `MeasureNumberMap`, `MeasureRecordMap`,
  `PiecewiseMap` and `TableMap`, and `Selector.class` admits exactly the six
  timeline classes and these ten types, its first branch, or an `Iri`, its
  second. `Selector.facet` and an `Address`'s
  `facet` refer to `Facet`, exactly the five facets `markers`,
  `conversion_maps`, `children`, `regions` and `flow_control`, and the words
  of an `Address`'s `part` to `Part`, exactly `start`, `end`, `name`,
  `label`, `card`, `line`, `id`, `coordinate`, `elision`, `ellipsis`,
  `symbol`, `fork` and `leader`. The words of a
  `Timestamp`'s `display` are exactly `TIMESTAMP_DISPLAY`, `wedge`, `name`,
  `id`, `coordinate` and `cross_section` in that order, and those of an
  `Elision`'s `display` exactly `ELISION_DISPLAY`, `ellipsis`, `name`,
  `id`, `coordinate` and `continuation` in that order, so the canonical
  order the writers apply cannot drift from the words the schema admits.
  `ElementType` is exactly the twenty-six types `block`,
  `timeline`, `child`, `band`, `map`, `region`, `break`, `section_break`,
  `barline`, `jump`, `wedge`, `name`, `label`, `boundary`, `ancestor`, `frame`, `card`,
  `cross_section`, `alignment_anchor`, `ancestor_card`, `elision`,
  `ellipsis`, `symbol`, `fork`, `leader` and `chunk`. An `Elision`'s `name` is a non-empty string. Its `width` declares exactly `ratio` (a number, exclusive
  minimum 0, maximum 1), `span` (`NumberPositive`) and `canvas` (a number,
  exclusive minimum 0), and its `oneOf` is exactly the three subschemas
  requiring one of them each, so `{"ratio": 0.5}`, `{"span": [3, 2]}`
  and `{"canvas": 40}` pass and `{}` and two forms together are refused.
  `Selector.coordinates` is exactly the two words `primary` and
  `secondary`. The four
  measure views fix `source_unit` to `quarters` and `target_unit` to
  `floating_measures` (`FloatingMeasureMap`) or null (the other three).
- **The unit table.** `TimeUnit` is a string whose `oneOf` holds one
  `{const, description}` per unit and no `enum`. The consts, in order, are
  exactly the keys of `UNITS`, and each description begins
  `<Domain>, <modality>; default number type <t>.` with the domain, the
  modality and the default number type of that unit's row of `UNITS`, so
  the table the packages read cannot drift from the one the schema states;
  a unit whose name does not say what it measures (`css_pixels`,
  `user_units`) adds one sentence after it. `Timeline` states which number
  types a unit admits as one conditional: the units whose `number_types` in
  `UNITS` are `["int"]` are exactly the `enum` of its `if`, whose `then`
  sets `number_type` to the `const` `int`; its `else` exempts the one unit
  admitting all three (`number`, the `const` of the inner `if`) and gives
  every other unit the `enum` `["float", "fraction"]`, which is exactly
  the `number_types` of each of them. So third-party validators reading the
  schema alone refuse what the packages refuse.
- **Shared definitions.** A shape that repeats is defined once: `Name`
  (string or null, default null) and `Meta` (a free object, default `{}`)
  are referred to by every `name` of the manifest, a timeline, a group, a
  region, a flow-control element, a MeasureMap and a conversion map and by every
  `meta`, and no property repeats their shapes inline. `MapBase` declares
  `type`, `id`, `name`, `source_unit` and `target_unit` and requires all but
  `name`; `MeasureView` is an object whose `allOf` is exactly
  `[{"$ref": "#/$defs/MapBase"}]`, whose own `properties` are exactly
  `source_unit`, the constant `quarters`, and `measure_map`, and whose
  `required` is exactly `["measure_map"]`. Every conversion map is an
  object whose `allOf` is exactly `[{"$ref": "#/$defs/MeasureView"}]` for
  the four measure views and `[{"$ref": "#/$defs/MapBase"}]` for the six
  others, whose own `properties` declare of the bases' keys only `type`,
  its constant, and, on a measure view, `target_unit`, a constant, and
  whose `required` lists `type`, as a discriminated union needs, and none
  of the bases' other keys.
- **References are IDs, addresses are `Address`.** `Selector.within`,
  the `to` of a `JumpDestination`, the `jump` and `to` of a
  `DestinationReference`, a `FlowMap`'s `timeline`, a `VirtualTimeline`'s
  `map`, `timeline` and `through` and the `measure_map` of each of the four
  measure views refer to `Id`, the items of a `FlowMap`'s `chunks` to `Id`
  or `Gap`, the items of `Selector.addresses` to `Address`. `Id`, an
  ID written `#` followed by the ID, accepts `#score`, `#Bass Kick`,
  `#perf/take 2`, `#https://example.org/piece/score#exposition`, `#start`,
  `#regions_1`, `##x`, `# `, `##NOMATCH_SENTINEL` and `#chunk_sentinel`,
  and refuses `""`, `#`, `score`, `score#`, `#score` followed by a tab,
  `#score` followed by a newline, `#` followed by U+001F,
  `#NOMATCH_SENTINEL` and `#CHUNK_SENTINEL`; every address below writes its ID so. `Address` accepts `{}`,
  `{"part": ["name"]}`, `{"id": "#score"}`, `{"id": "#perf/take 2"}`,
  `{"id": "#score", "facet": "regions"}`, `{"id": "#score", "part":
  ["card"]}`, `{"id": "#score", "part": ["end", "label"]}`, `{"id":
  "#timestamp_1", "part": ["line"]}`, `{"id": "#timestamp_1", "part":
  ["label"]}`, `{"id": "#timestamp_1", "part": ["name"]}`, `{"id": "#timestamp_1", "part": ["id"]}` and `{"id":
  "#timestamp_1", "part": ["coordinate"]}`, and refuses
  the string `"score"`, `{"facet": "regions"}` (a facet needs an ID),
  `{"id": "#score", "facet": "regions", "part": ["label"]}` (a facet never
  stands with a part), `{"id": "#score", "part": []}`, `{"id": "#score",
  "part": ["wedge"]}` and `{"id": "#score", "facet": "regions_1"}`. It
  accepts `{"id": "#score", "root": "score"}`: an address is open like
  every object.
- **Open objects.** No node anywhere has `additionalProperties: false`
  or `unevaluatedProperties`, and no key anywhere in the document begins
  with `x-`: every object, `Address` included, is open by omission, with no
  custom keyword. Every object
  node with `properties` outside a branch declares, in its own `properties`
  or in those of the bases its `allOf` names, at any depth, every key its `oneOf`/`anyOf`
  branches and `if`/`then`/`else` arms declare, which is what lets
  `unknown_keys` name the unknown keys from the node alone. `meta` (on the
  manifest, a timeline, a region, a flow-control element, a group, a MeasureMap)
  refers to `Meta`; `Meta` is the one free object: `additionalProperties:
  true` and no `properties`.
- **Discriminated unions.** Exactly two nodes carry a `discriminator`, on
  `number_type` and on `type`; each tags every branch with a distinct
  required string constant.
- **Statements.** `statements` is a property of exactly `Manifest`,
  `Timeline` and `Region`, `provenance` of those and `ValueNode`, and
  `@context` of `Manifest` alone; no definition declares `links` or
  `schemes`, and `Link`, `PartSlot`, `PartOf`, `Assertion`, `Descriptor`,
  `Identifier`, `Scheme`, `Level`, `Term`, `Uri` and `UriReference` are
  gone. `ProvenanceEntry` is the bundled `ProvenanceRecord` (the root of
  `provenance.schema.json`) with `property` and `value`, both required;
  `ProvenanceRecord` declares exactly `basis`, `beliefs`, `date`, `match`,
  `method`, `note`, `service` and `stated_by` and requires none, `status`
  among none of them; `Belief` requires `actor`, `belief` and `date`, and
  its `belief`, the `method` words and `match` are exactly `BELIEFS`,
  `METHODS` and `MATCHES`; `Context`'s consts are
  exactly `FORMAT_CONTEXT`, its `required` and its term names the 35 terms
  in that order. `Iri` accepts `schema:MusicRecording`,
  `http://musicbrainz.org/work/x`, `urn:isbn:0451450523`,
  `mailto:a@example.org` and `wdt:P175`, and refuses `MusicRecording` (no
  prefix), `1http://x`, `http:` (nothing after the colon), `schema:a b`, a
  trailing newline, U+00A0 and U+FEFF; `IriReference` accepts `#clt_1`,
  `other.yaml#clt_1`, `wd:Q1` and `records/op106.json` and refuses `""`,
  `a b`, `_:b0` (a blank node) and `@id` (a keyword); `PrefixIri` accepts
  namespaces ending in `/` or `#` and refuses one ending otherwise, a
  trailing newline and a relative path; `PrefixName` accepts `schema`,
  `melodTerms`, `wd`, `a_b-1` and refuses `unit` (an element's key),
  `http`, `urn` (schemes the format reads as such), `1a`, `a:b`, `a.b` and
  `""`; `LanguageTag` accepts `en`, `de-CH`, `zh-Hant-TW` and refuses `""`,
  `en_GB`, a trailing newline and a subtag longer than eight letters. The
  white-space class the IRI definitions refuse with an unanchored `not` is
  `BLANK`, pinned against the schema.
- **Both libraries read every pattern alike.** A pattern ending in `$`
  lets a trailing newline through Python's `re.search` and not through
  JavaScript's `RegExp`, so a definition that needs to refuse control
  characters says so with an unanchored `not`, never with an anchored
  class: `Id` is a string of `minLength` 1 whose `not` refuses U+0000 to
  U+001F, and an entry of an `Order` has the same two keywords. The eight
  patterns that still end in `$`, `Paint`, `stroke-dasharray`,
  `elision-depths`, `elision-display`, `label-display`, a provenance
  entry's `date`, a resource's `media_type` and its integrity's `digest`,
  are exactly those the document holds, and each refuses a value it
  accepts (`none`, `4 2`, `1 2`, `ellipsis name`, `name id`, `2026-11-17`,
  `application/vnd.apache.parquet`, `00ff`) once a newline follows it; no
  ID has a pattern of its own (a named timestamp's, a resource's, a
  MatchStamp's and an anchor's are any `Id`); an `Order` refuses
  `["line\n"]`. The JavaScript suite
  asserts the same values, so the two validators cannot part on a
  trailing newline.
- **Defaults agree with the table.** For every kind of `DEFAULTS` the
  schema's corresponding definitions (`Manifest`, `Timeline`,
  `Region`, `FlowControlElement`, `JumpDestination`, `FlowMap`,
  `VirtualTimeline`, `MeasureMap`, `Group`, `Graphical`,
  `Timestamp`, `AlignmentAnchor`, `Elision`, every conversion map) declare `default` on exactly the keys
  of that kind's table, each equal to the table's value, and on no other
  key; a conversion map's kind is `conversion_map`, joined by `linear_map`
  for a `LinearMap` (`scalar` 1, `offset` 0) and by `table_map` for a
  `TableMap` (`kind` `linear`, `extrapolate` `none`); a flow-control
  element's kind is `flow_control_element`, a jump's destination's
  `jump_destination` (`determined` true, `reset` true, `label` null), a
  FlowMap's `flow_map` (`canonical` false, `name` null) and a virtual
  timeline's `virtual_timeline` (`name` null). A destination's
  `repeat_count` has no default, its absence meaning no limit, and the
  manifest's `flow_maps` and `virtual_timelines` have none either: they are
  never added. A key's default is
  stated on its property or on the definition the property refers to
  (`Name`, `Meta`), and a conversion map's keys include those of its bases,
  at any depth. `number_type`
  has no `default` (it depends on the unit). The JavaScript suite holds its
  table to the same schema, so the two tables are equal.

## The version marker

`validate` and `unknown_keys` read `timetoshare` first (`test_validate.py`):

- a value without it, a list and a string are refused at the root with
  exactly `not a TimeToShare manifest`, whatever else they hold (a value
  holding the version as `meta.schema_version` but no marker too);
- `"9.9.9"`, `"0.1.0"` (the version 0.2.0 replaces), `"0.1"` and the number
  `1` raise `UnsupportedVersionError` with `version` that value, the message for
  `"9.9.9"` exactly `unsupported TimeToShare version "9.9.9"; this package
  reads 0.2.0 only`; the marker is checked before the schema, so a value with
  another version and no `timelines` raises the same error;
- the smallest file `{"timetoshare": "0.2.0", "timelines": [{"id": "piece",
  "unit": "quarters", "length": [32, 1]}]}` and the empty manifest
  `{"timetoshare": "0.2.0", "timelines": []}` validate.

## The units

The units are the consts of the schema's `TimeUnit`, and nothing else.
The two vector-graphics units, `css_pixels` (the CSS pixel) and
`user_units` (a document's own coordinate system), prove that a unit of
the table is read like its neighbours (`test_validate.py`): a root of
each, with the length `600.5` and `number_type` `float`, `[1201, 2]` and
`fraction`, or `600` and `int`, validates exactly where the same root in
`points`, the other continuous graphical unit, validates (the first two;
`int` is refused for all three, a continuous unit admitting no `int`).
Neither has an abbreviation: a root in `px` or in `uu` is refused with the
code `schema` at `["timelines", 0, "unit"]`, as the shared case
`timeline_unit_unknown` refuses `beats`, so a short spelling can never be
read as the discrete `pixels`.

`ordinals`, the logical unit of positions in an ordered structure of units
of length 1 subdivided exactly, is read like `quarters`, the other
continuous logical unit whose default number type is `fraction`
(`test_validate.py`): a root of each, with the length `[7, 3]` and
`number_type` `fraction`, `2.5` and `float`, or `3` and `int`, validates
exactly where the same root in `quarters` validates (the first two; `int`
is refused for both, `ordinals` being continuous). Its default number type
is `fraction` (`test_defaults.py`).

**Which number types a unit admits.** `UNITS` (exported as
`timetoshare.UNITS`, the one table of the package, which every module
reading a unit's default number type reads) gives every unit its domain, modality, default number type
and admitted number types: `ticks`, `samples`, `frames` and `pixels` admit
`("int",)`, `number` admits `("int", "float", "fraction")`, every other
unit `("float", "fraction")`. `test_schema.py` states the table literally,
row by row, and the JavaScript suite states the same rows. A
`number_type` the unit does not admit is a `schema` problem at the
timeline's `number_type`, at any depth. What proves it: the shared cases
`timeline_ticks_float` (ticks declared `float`, length `480.0`),
`timeline_seconds_int` (seconds declared `int`, length `10`) and
`timeline_quarters_int` (quarters declared `int`, length `8`), each refused
at `["timelines", 0, "number_type"]`; and inline (`test_validate.py`), for
every unit and every number type, a root whose `length` is the number
type's spelling of 2 (`2`, `2.0`, `[2, 1]`) validates exactly where the
unit's row admits that number type and is otherwise refused at its
`number_type`, and the same for a child of such a root (refused at
`["timelines", 0, "children", 0, "number_type"]`). A unit's default
number type is always one it admits, and `number` with `int` validates.
The schema's `Coordinate`, the self-describing `{unit, number_type,
value}` a host exchanges outside a manifest, carries the same rule:
`test_schema.py` requires its `if`, `then` and `else` to equal the
`Timeline`'s, and checks single coordinates against the definition alone.
`{unit: ticks, number_type: float, value: 1.5}` is refused at
`number_type` by the keyword `then/properties/number_type/const`;
`{unit: seconds, number_type: int, value: 10}` and `{unit: quarters,
number_type: int, value: 8}` at `number_type` by
`else/else/properties/number_type/enum`; each is the one error found, and
`{ticks, int, 480}`, `{seconds, float, 1.5}`, `{quarters, fraction, [1,
2]}` and `{number, int, 2}` validate. The JavaScript suite checks the
same coordinates with Ajv and finds the same paths and keywords; both
packages word a `schema` problem alike ([One path rule for both
validators](#one-path-rule-for-both-validators)).

## Reading by the declared number type

The declared number type decides how a value is read, never its lexical
form: a number written with a zero fractional part is the integer it equals
wherever an integer is read. A Fraction member written `8.0` is 8, wherever
a Fraction occurs (own-axis values, conversion-map Numbers at any depth of
nesting, MeasureMap rows); `2.0` on an int axis is 2; `2` on a float axis
is 2.0. So a JSON round trip that respells numbers (`JSON.parse` and
`JSON.stringify` turn `8.0` into `8`) never invalidates a manifest. What
proves it (`test_validate.py`): one inline manifest (`respellable()` in
`conftest.py`) validates, leaves `unknown_keys` empty and is unchanged by
`validate`. In quarters it holds the length `[32, 1.0]`, a child offset
`[8.0, 1]`, a region from `[0, 1.0]` to `[1.0, 2]`, a jump target at `[2.0, 1]`, a
TableMap x value `[1.0, 2]` nested in a ChainMap, a LinearMap offset
`[0, 1.0]` and, in the manifest's MeasureMap, a row with `qstamp`
`[0, 1.0]` and `actual_length` `[4.0, 1]`; in ticks a length `480.0` with a child offset
`240.0`; in seconds a length `60` and a region starting at `0`. It also holds
numbers whose place declares no number type: the LinearMap scalar `1.0`,
the TableMap y values `0.0` and `0.5` and the row's `nominal_length` `4.0`.

Still refused, each by a shared rejection case: a non-integral value on an
int axis (`length_float_on_int_axis`, `480.5` in ticks, `representation`
at the length), a non-integral Fraction member (`length_fraction_member_not_integral`,
`[12, 1.5]`, `schema` at the member), a denominator below 1
(`length_zero_denominator`), a Fraction on an int axis
(`length_fraction_on_int_axis`) or on a float axis
(`child_offset_fraction_on_float_axis`), and a bare number on a fraction
axis (`length_int_on_fraction_axis`, `region_start_float_on_fraction_axis`).

**One acceptance table: the number type fixes the form, the spelling within
the form is free.** `fixtures/acceptances/0.2.0/numbers.yaml` holds the
rows every reader of an own-axis value runs, each `{number_type, value}`
with either `read`, the value read written as its number type spells it
(the canonical spelling), or `refused: representation`. The rows, in
order: fraction `[2, 4]` → `[1, 2]`, `[1, 8.0]` → `[1, 8]`, `[4, 8.0]` →
`[1, 2]`, `[-3, 6]` → `[-1, 2]`; int `480` → `480`, `480.0` → `480`;
float `2` → `2.0`, `0.1` → `0.1`; refused: int `[480, 1]` and `2.5`,
fraction `12` and `12.0`, float `[25, 2]` and `9007199254740993`. A
Fraction member with a fractional part stays the `schema` refusal of
`length_fraction_member_not_integral` and is no row. What proves it
(`test_validate.py`): the rows are stated literally (number type and
value), so a row cannot disappear unnoticed; each row's value is the
`offset` of one root (`ticks` for int, `seconds` for float, `quarters` for
fraction, the unit's own number type declared, `length` null), an
own-axis value that may be negative; a refused row raises
`SchemaValidationError` with the code `representation` at
`["timelines", 0, "offset"]`; an accepted row validates, the exact value
of what it states equals the exact value of `read`, and `canonical_order`
writes the offset as `read` (compared as `dumps` texts, so `2.0` is told
from `2`).

**Readers coerce, writers respell own-axis values.** `complete` (so
`minimal` too) and `canonical_order` (so `dumps` too) respell every own-axis
value as its number type selects: on an int axis an integral float as the
integer it equals, on a float axis an integer as the float that equals it
exactly, on a fraction axis a pair reduced to lowest terms with integer
members. `loads` and `validate` change nothing. Every other number (a
conversion map's Numbers and pairs, a MeasureMap row's values, a
destination's `repeat_count`, a free value) keeps its spelling, and a value that has no
exact respelling (an integer beyond 2^53 on a float axis, which `validate`
refuses) is left as written. What proves it (`test_manifest.py`): for that
manifest, `complete`, `minimal` and `canonical_order` each give, compared as
pretty JSON texts of the value wrapped in an array (a wrapped value is no
manifest, so its texts tell `8.0` from `8`), exactly what they give for its
literal twin `respelled()`, written canonically (`[32, 1]`, `[8, 1]`, `[0,
1]`, `[1, 2]`, `[2, 1]`, `480`, `240`, `60.0`, `0.0`, while the TableMap's
`[1.0, 2]`, the LinearMap's `[0, 1.0]` and `1.0`, the y values `0.0` and
`0.5` and the row's `[0, 1.0]`, `[4.0, 1]` and `4.0` are kept); `dumps`
writes the twin's text; the twin is its own canonical order and spelling;
and the input is unchanged. Each of the three equalities fails when the
respelling is left out. A seconds length `9007199254740993` stays that
integer.

An own-axis value (a timeline's `length` and `offset`, a region's `start` and
`end`, a flow-control element's `coordinate`, the `by` of a jump's destination and of an `after`, a gap of a FlowMap of the timeline, and a virtual timeline's `length` on its own axis) is a bare Number whose representation the axis's number type
selects: an int axis an integral JSON number, a float axis any JSON number
that a float equals exactly (an integer beyond 2^53 may have none), a
fraction axis a pair. The axis is the timeline's `number_type`, else its
unit's default (`int` for ticks, samples, frames, pixels; `fraction` for
quarters, whole_notes, ordinals; `float` otherwise). A child's offset lies on its
parent's axis, a root's on its own. A mismatch is reported after the schema,
at the value, as `<key> <value> of '<id>' is <found> on <axis> axis: write
<value rewritten>`, the ID that of the object holding the key, the value
rewritten where an exact rewriting exists, else the number type named. What
proves it, one inline document per line, message stated literally:

- `length 32 of 'score' is an int on a fraction axis: write [32, 1]`;
- `length 0.5 of 'score' is a float on a fraction axis: write [1, 2]`;
- `length 0.1 of 'score' is a float on a fraction axis: write
  [3602879701896397, 36028797018963968]` (the exact value of the double);
- `length [3, 4] of 'take' is a fraction on a float axis: write 0.75`;
- `length [1, 3] of 'take' is a fraction on a float axis: write a float`;
- `length [480, 1] of 'midi' is a fraction on an int axis: write 480`;
- `length 0.5 of 'midi' is a float on an int axis: write an int`;
- `length [1, 2] of 'midi' is a fraction on an int axis: write an int`;
- `length 9007199254740993 of 'take' is an int on a float axis: write a
  float` (2^53 + 1 lies between two floats, so no float rewrites it);
- on a seconds axis declared `fraction`, `length 2.0` is `a float on a
  fraction axis: write [2, 1]`, and on quarters declared `float` a length
  `[2, 1]` is `write 2.0`;
- `offset [1, 2] of 'take' is a fraction on a float axis: write 0.5` for a
  child in seconds of a root in seconds, and a child in quarters of a root in
  seconds with offset `[1, 2]` is reported the same way (the parent's axis),
  while its own length `[4, 1]` is fine; a root's own `offset 3` in quarters
  is `write [3, 1]`;
- `start`, `end` and the `coordinate` of a break, a jump and a jump target
  each reported at its own path with its holder's ID; the `by` of a
  destination, a FlowMap's gap and a virtual timeline's `length` likewise,
  by the shared rejection cases (section "Flow").

Accepted: `8` and `8.0` on an int axis (an integral number is an int),
`8`, `0.5`, `9007199254740992` (2^53) and `10**20` on a float axis (each
exactly a float), `[8, 1]` and `[8.0, 1]` on a fraction axis, `length:
null` anywhere, a root's negative offset in its own number type. The checks
visit a timeline's offset, length, regions and flow-control elements (each
element's coordinate, then the `by` of its `ends` and of each destination
and its `after`), then its children in array order; after the timelines
come the named timestamps, the elisions, the gaps of the FlowMaps and the
lengths of the virtual timelines; the first problem is raised.

## Open objects and unknown keys

`unknown_keys(value)` validates the value and returns every key the schema
does not declare on the object holding it, as `{"path": [...], "key": ...}`,
sorted by path (segment by segment, indices by number, keys by code point,
an object before its descendants) and then by key (`test_unknown_keys.py`):

- **The shared warning cases.** Every case of `fixtures/warnings/0.2.0/`
  holds exactly `manifest`, `unknown_keys` and `warnings`; `validate`
  accepts the manifest, `unknown_keys` returns exactly its `unknown_keys`
  list and `manifest_warnings` exactly its `warnings` list (empty in the
  thirteen cases of unknown keys, which state the format's `@context`;
  empty `unknown_keys` in the six cases of warnings, `context_absent`,
  `bundle_blank_statements`, `bundle_blank_provenance`,
  `manifestation_unknown`, `convention_unknown` and `flow_conflict`); the
  JavaScript suite asserts the same lists. `several_depths` holds unknown keys on the
  manifest, a timeline, a child, a region, a break, a jump, a
  jump target, a conversion map and the map nested in it, a MeasureMap and
  one of its rows, a group, the `graphical` object, a rule, a selector
  and a declaration (sixteen entries). The other cases are keys the format does
  not declare that a writer might plausibly add: a timeline `class`,
  a manifest `support_policy`, a group's `order`, `arrangement` in
  `graphical`, a selector's `kind` and `ids` (a list of string
  addresses), a declaration's `colour` and
  `show-projections`, a MeasureMap row's `tempo` and `offset`, a
  `CombinationMap`'s `names`, and an address's `root`
  (`address_unknown_member`: the address equals no element's address and
  matches nothing, and its key is reported like any other).
- **An undeclared key of a declaration and of a style.** `side`: a manifest whose rule
  sets `{"fill": "#000000", "side": "above"}` on maps and whose style
  `below` is `{"side": "below"}` validates, and `unknown_keys` lists exactly
  `{"path": ["graphical", "rules", 0, "set"], "key": "side"}` and
  `{"path": ["graphical", "styles", "below"], "key": "side"}`.
- **A base of a base.** A measure view's base is `MeasureView`, whose own
  base is `MapBase`: a `MeasureNumberMap` carrying the unknown key
  `colour` lists exactly `{"path": ["timelines", 0, "conversion_maps",
  0], "key": "colour"}`, its `id`, `name` and units counting as declared.
- **What is not reported.** Keys inside `meta` (a free object), keys inside the value of an unknown key, keys of `styles` and of
  `graphical.order` (maps keyed by data), and a known key whose value is
  its default: a manifest with none of these and a key in each lists
  nothing.
- **Sorting.** Keys `zz`, `aa`, `ﬀ`, `😀` on one object come out `aa`, `zz`,
  `ﬀ`, `😀`; an unknown key on `timelines[10]` follows one on
  `timelines[2]`; the manifest's own keys come first.
- **An invalid value** raises the error `validate` raises, before any key
  is listed.
- **One reading.** The keys come from the schema reading `validate` runs.
  It reads an in-memory variant of the document that closes every object
  the document leaves open (`unevaluatedProperties: false` on each object
  node with `properties` outside a branch, except the base an `allOf`
  shares and the maps keyed by data whose `additionalProperties` admits
  every key: the `@context`, statements and value nodes), and a failure
  that only an undeclared key causes is a key to list, not a violation.
  An unknown key inside a statement's value node is listed alone, never
  the statement's or the value node's own keys beside it. A valid manifest's keys are listed by the schema
  gate without the `jsonschema` walk, as a counting validator proves (see
  "The schema gate"); an invalid one is walked once.

## Defaults: the complete and the minimal form

`DEFAULTS` is the one table (`test_defaults.py`). What proves `complete` and
`minimal`:

- **Literal forms.** The smallest file completes to the literal complete
  manifest (`name` null, `meta` `{}`, `groups` and `measure_maps` `[]`,
  and on the timeline `name` null, `number_type` `fraction`, `locked`
  false, `is_segment_line` false, `meta` `{}`, `children`,
  `conversion_maps`, `regions` and `flow_control` `[]`), and that minimizes
  back to the smallest file. `@context`, `statements` and `provenance`
  have no default: a manifest stating all three on itself, its root and a
  region keeps each exactly in both forms, and its minimal form is the
  literal input. A region, a flow-control element (each destination of a
  jump gains `determined`, `reset` and `label`, a stated `determined: false`,
  `reset: false` and label kept, and never a `repeat_count`), a FlowMap, a
  virtual timeline, a group, a MeasureMap, a conversion map (and the maps nested in a
  `ChainMap`, a `CombinationMap` and a `PiecewiseMap`), a `LinearMap`, a
  `TableMap` and a `graphical` object each gain exactly their table's keys.
  A named timestamp without `display` gains `display: ["wedge", "name",
  "cross_section"]`, and nothing else; one stating `["cross_section",
  "wedge", "name"]` completes to `["wedge", "name", "cross_section"]` and
  minimizes without `display`, as the default in another order is still
  the default; one stating `["name", "wedge"]` completes to `["wedge",
  "name"]` and keeps it in the minimal form; one stating `[]` keeps `[]` in
  both forms. An elision without `display` gains `display: ["ellipsis",
  "name"]` and nothing else, its `name` and `width` neither added nor
  completed; one stating `["name", "ellipsis"]` completes to `["ellipsis",
  "name"]` and minimizes without `display`, the default in another order;
  one stating `["ellipsis"]`, the former default, is a stated value and
  keeps it in both forms; one stating
  `["continuation", "name", "ellipsis"]` completes to `["ellipsis", "name",
  "continuation"]` and keeps it in the minimal form; one stating `[]`
  keeps `[]` in both forms; its `width` `{"ratio": 1}` stays in both forms,
  as no width has a default.
  The unit default of `number_type` is stated for ticks (`int`), seconds
  (`float`), whole_notes (`fraction`), ordinals (`fraction`), pixels
  (`int`), and the two vector-graphics units css_pixels and user_units
  (`float`).
- **Never added, never removed.** `id`, `graphical` and a root's `offset`
  are absent from the completion of a manifest without them; a present
  `graphical: {}` completes to its six keys (`styles`, `rules`,
  `order`, `timestamps`, `matchstamps`, `elisions`, each empty) and
  minimizes to `{}`; a
  child's `offset` stays in the minimal form.
- **Values that differ from the default stay.** `locked: true`,
  `number_type` `float` on quarters, a destination with `repeat_count` 1,
  `determined: false`, `reset: false` and a label, and a FlowMap with
  `canonical: true` survive `minimal`, each keeping only its own
  non-default keys; a destination stating the three defaults keeps none of
  them, an empty `virtual_timelines` stays, and a `by` written `-1` on a
  float axis is written `-1.0`.
- **Numbers compare by value.** A `LinearMap`'s
  `scalar` `1.0` and `[1, 1]` and its `offset` `0.0` and `[0, 3]` equal
  their defaults 1 and 0 and are left out by `minimal`;
  `scalar` `[1, 2]` stays; `false` is not the number 0 and `0` is not
  `null`. A named timestamp's `display` given `["name", "wedge",
  "cross_section"]` and a child's `offset` `[4, 8]` on quarters are compared
  after canonical order and respelling, so the `display` is left out and the
  offset written `[1, 2]`.
- **Unknown keys pass through** both functions, at every depth, untouched.
- **`length` survives** both, `null` included.
- **The round trips.** For each of these documents (a destination with
  `repeat_count: 1.0` and `reset: true` among them) and for every fixture,
  `minimal(complete(x)) == minimal(x)`, `complete(minimal(x)) == complete(x)`
  and both results validate; both functions return new objects and leave
  their input unchanged. The first equality compares the canonical YAML
  texts, which tell `1.0` from `1`; the second compares the RFC 8785 JSON
  texts, which compare numbers by value, since `minimal` leaves out a
  `scalar: 1.0` that `complete` then restores as `1`.

## The rules and their codes

`validate` checks in this order and raises the first violation as a
`SchemaValidationError` carrying `code`, `path` and `message`: the version
marker; `finite_number`; `flow_control_form`; the schema, in one walk that
also collects the unknown keys; `representation`; then the semantic rules in
the order of the table, the statement rules last, root by root for the first six (a root's duplicates, then
timeline by timeline, each before its children, its flow control and its
targets, then its conversion maps, then child by child, each followed by its
own children, the containment rules, then its segment lines), the rest over
the whole manifest. A timeline's maps are read in array order, each before
the maps it holds, a `CombinationMap`'s by output name in code-point order,
and a map's source unit before its arrays.
`identity_problems` returns every semantic problem in that order; `validate`
stops at the first. A message names an element by its ID in single quotes,
as written (a unit and an order entry too), so every message is the same
text in both packages, a schema violation's included: the JavaScript
package words it as this package does.

| Code | Rule | Reported at | Message |
| --- | --- | --- | --- |
| `not_a_manifest` | an object holding `timetoshare` | the root | `not a TimeToShare manifest` |
| `finite_number` | every number finite | the leaf | `length of 'take' is not a finite number`, or `#/graphical/styles/s/opacity is not a finite number` with no ID above it |
| `schema` | the schema document | the path rule below | the schema library's, but for the three shapes worded below |
| `representation` | own-axis values in the axis's number type | the value | `length 32 of 'score' is an int on a fraction axis: write [32, 1]` |
| `duplicate_id` | IDs unique within a root's tree, the maps a `ChainMap`, `PiecewiseMap` or `CombinationMap` holds included after the tree's other IDs | the later ID | `'m' is not unique in the manifest, first at #/…` |
| `flow_control_form` | before the schema: no flow-control element is written in the earlier form (`type` with `jump_from`, `jump_to` or `flow_marker`, a `role` that is one of those words, or `target` without `role`) | the element | `flow-control element 'old' is written in the earlier form of flow control (type, target): convert the manifest with scripts/convert_flow_control.py` |
| `flow_coordinate`, `jump_repeated`, `jump_destination`, `dangling_target` | per timeline, over the elements not rejected, in document order (section "Flow"): a coordinate from 0 to the known length; one jump at a position on the root's axis, over the root's whole tree; distinct places of a jump's destinations; a `to` naming a jump target or region of the timeline, a child of it or the timeline; a place reached by `by` from 0 to the known length; an `after` naming one destination of another jump of the timeline | the `coordinate`, the jump, the destination, the `to`, the `by`, the `after` or its member | `coordinate [17, 1] of 'jump_2' is not on 'score': it lies outside 0 to the length [16, 1]`, `'jump_3' is a second jump at coordinate [16, 1] of 'score', after 'jump_2': several signs at one place are destinations of one jump`, `destination 1 of 'jump_1' has the place of destination 0, to 'jump_target_1'`, `'break_1' names no jump target, region or child of this timeline, nor the timeline itself`, `jump 'jump_2' has no destination to 'jump_target_1'` |
| `dangling_target` | then, map by map, a measure view's `measure_map` names an entry of `measure_maps` | the `measure_map` | `'ghost' names no MeasureMap of this manifest` |
| `conversion_map` | a non-null `source_unit` of a map attached to a timeline is the timeline's unit, and that of every map a `PiecewiseMap` or `CombinationMap` holds, and of a `ChainMap`'s first map, is its holder's non-null `source_unit`; a `TableMap`'s x and y values of equal length, its x values strictly increasing; a `PiecewiseMap`'s maps one fewer than its breaks, its breaks strictly increasing | the `source_unit`, the `y_values`, the value, the `maps`, the break | `MeasureRecordMap 'bars' has source unit 'quarters', its timeline 'score' has 'ticks'`, `LinearMap 'scale' has source unit 'ticks', its ChainMap 'chain' has 'quarters'`, `TableMap 'tempo' has 3 x values and 2 y values`, `x value [0, 1] of TableMap 'tempo' does not exceed the one before it`, `PiecewiseMap 'sections' has 1 map for 3 breaks; it needs 2 maps`, `break [4, 1] of PiecewiseMap 'sections' does not exceed the one before it` |
| `child_unit` | a child has its parent's unit | its `unit` | `child 'take' has unit 'seconds', its parent 'score' has 'quarters'` |
| `child_number_type` | then, a child has its parent's number type, each the declared one or its unit's default | its `number_type`, its `unit` where it declares none | `child 'verse' has the number type 'float', its parent 'score' has 'fraction'` |
| `child_offset` | a child starts within the parent's known length | its `offset` | `offset 75.0 of 'take' is beyond the length 60.0 of its parent 'recording'` |
| `child_end` | else, it ends within it | its `length` | `child 'coda' ends at [12, 1], beyond the length [10, 1] of its parent 'score'` |
| `segment_line` | segments contiguous from 0 to the length, one flag | the segment's flag or offset, the line's `length` | `segment 'b' of segment line 'line' does not start where the one before it ends` |
| `duplicate_id` | every ID unique across the manifest: each root's tree, in the order above, against the earlier roots' (an ID repeated inside one root counts once), then each group ID, then each MeasureMap ID, then each named timestamp's ID, then each elision's ID, then each MatchStamp's and its anchors', each resource's, each FlowMap's and each virtual timeline's, against every ID before it | the later ID | as above |
| `manifest_id` | the manifest ID is no other ID of the manifest | `id` | `'g2' is not unique in the manifest, first at #/groups/1/id` |
| `group_member` | a member names a timeline or a virtual timeline, and neither contains nor lies inside another member of its group (a virtual timeline does neither) | the member | `'ghost' names no timeline or virtual timeline of this manifest`, `member 'b' lies inside member 'a' of the same group` |
| `order_key` | a `graphical.order` key names a group, a timeline or a virtual timeline | the key | `'g9' names no group, timeline or virtual timeline of this manifest` |
| `display_order` | a group's order permutes its members | the entry, then the order | `'x' is not a member of group 'g'`, `member 'b' of group 'g' is missing` |
| `band_order` | a timeline's order lists `line` and any of the five facets | the entry, then the order | `'annotations' is not 'line' or a facet, in the band order of 'score'`, `'line' is missing from the band order of 'score'` |
| `timestamp_timeline` | a named timestamp's `timeline` names a timeline of the manifest, at any depth, or a virtual timeline | its `timeline` | `'ghost' names no timeline or virtual timeline of this manifest` |
| `timestamp_coordinate` | its `coordinate` lies from 0 to its timeline's length, from 0 on where the length is null | its `coordinate` | `coordinate [9, 1] of 'timestamp_1' is beyond the length [8, 1] of its timeline 'score'`, `coordinate [-1, 1] of 'timestamp_1' lies before the start of its timeline 'score'` |
| `elision_timeline` | an elision's `timeline` names a timeline of the manifest, at any depth, or a virtual timeline | its `timeline` | `'ghost' names no timeline or virtual timeline of this manifest` |
| `elision_stretch` | its `start` lies at or after 0, its `end` at or before its timeline's length where the length is known, and its `start` before its `end`; each elision checked in that order | its `start`, its `end`, its `end` | `start [-1, 1] of 'elision_1' lies before the start of its timeline 'score'`, `end [5, 1] of 'elision_1' is beyond the length [4, 1] of its timeline 'verse'`, `end [3, 1] of 'elision_1' does not lie after its start [3, 1]` |
| `flow_map_timeline`, `flow_map_chunk`, `flow_map_canonical` | after the MatchStamps and resources (section "MatchStamps and resources"), FlowMap by FlowMap: its `timeline` names a root; each ID among its chunks a region, a child or a virtual timeline inside that root's tree; at most one FlowMap of a timeline is canonical | its `timeline`, the chunk, its `canonical` | `'coda' is a child timeline; a FlowMap names a root timeline`, `'jump_target_1' names no region, child timeline or virtual timeline in the tree of 'score'`, `'flow_map_2' is a second canonical FlowMap of 'score', after 'flow_map_1'` |
| `dangling_target`, `virtual_timeline` | then virtual timeline by virtual timeline: its `map` names a FlowMap or a conversion map, its `timeline` a timeline or another virtual timeline, never itself (`dangling_target`); it comes from no ring of virtual timelines, reported at each member of the ring; without `through`, a FlowMap it applies is one of the root its timeline comes from, else its `length` is the sum of the FlowMap's chunks and gaps, compared where every chunk has a known length on its axis and the axis is not `float` (`virtual_timeline`) | its `map`, its `timeline`, its `timeline`, its `map`, its `length` | `'virtual_1' comes from itself through 'virtual_2': a virtual timeline comes, virtual timeline by virtual timeline, from a timeline of this manifest`, `'flow_map_1' is a FlowMap of 'score', and 'sketch' comes from the tree of 'sketch': without through, a virtual timeline applies a FlowMap within the tree of the FlowMap's root timeline`, `length [30, 1] of 'virtual_1' is not the sum of the chunks and gaps of 'flow_map_1', [22, 1]` |
| `flow_rule` | last, the property `flow`: no style of `graphical.styles` sets it (style by style, in code-point order of their names); then rule by rule a rule setting it selects by `addresses` alone, each `{id, part: [card]}`, and its value names a FlowMap or a virtual timeline, and, address by address, a FlowMap of that timeline or a virtual timeline applying one to that timeline without `through` | the style's `flow`, the rule's `select`, its `set.flow` | `style 'switched' sets flow; only a rule addressed to the cards of a timeline sets it`, `a rule setting flow selects the cards of timelines by their addresses alone, each {id, part: [card]}`, `'region_1' names no FlowMap or virtual timeline of this manifest`, `'flow_map_1' is a FlowMap of 'score', not of 'recording'`, `'virtual_2' does not apply a FlowMap of 'score' to 'score' without through` |
| `context` | a manifest whose manifest, timeline or region carries `statements` or `provenance` holds `@context` | the first such key in subject order, `provenance` before `statements` | `statements and provenance need the manifest's @context` |
| `reserved_key` | no key of the manifest, a timeline, a region or a group begins with `@` (but the manifest's `@context`), holds a `:`, is a term of the context the element may not use or names a prefix of `@context` | the key | `'label' is reserved on a timeline` |
| `iri` | subject by subject: the ID of an element with statements is an IRI fragment; every compact IRI names a prefix of `@context`, unless it is `//`-absolute or of the schemes `info`, `mailto`, `tag`, `urn`; last, after the provenance of the elements, rule by rule, a selector's `class` written as a compact IRI does too, its prefix `tts` excepted (`iri_prefix_undeclared_selector_class`) | the `id`, the key or value, the `class` | `the ID 'Bass Kick' of an element with statements is no IRI fragment`, `'wdtt:P175': the prefix 'wdtt' is not declared in @context` |
| `dangling_target` | with the row above: a reference `#x` in a node's `id`, an entry's `basis`, `stated_by` or `service` names an ID of the manifest, of any kind | the reference | `'#cpt_9' names no element of this manifest` |
| `element_value` | a node naming an element holds its `id` alone | the node | `'#clt_2' names an element; a value naming an element holds its id alone` |
| `representation` | with the rows above: a statement value is no float (an integral one passes the schema) | the value | `a statement value is an integer or a string, never a float: 1.0` |
| `calendar_date` | with the rows above: an entry's `date` names a day of the Gregorian calendar from 0001-01-01 to 9999-12-31 | the `date` | `'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD` |
| `belief_actor` | an actor holds at most one belief in an entry, actors compared as their expanded IRIs | the later belief's `actor` | `'http://www.wikidata.org/entity/Q1' already holds belief 0 of this entry; an actor holds one belief` |
| `provenance_duplicate` | no entry repeats the pair of an earlier entry of its subject | the entry | `the entry repeats the pair of entry 0` |

The keys of `graphical.order` are read in code-point order, each order's
strangers before its missing entries, missing members in the order of
`members`; a band order may leave out any facet, but not `line`.
A key naming a group and a timeline never reaches `validate` (the duplicate
ID comes first); `identity_problems` reads it as the group's. The named
timestamps are read after the orders, in array order. The coordinate of a
timestamp on a timeline of the manifest is an own-axis value of that
timeline and is checked with the `representation` rule (`coordinate 3 of
'timestamp_1' is an int on a fraction axis: write [3, 1]`, at its
`coordinate`); a timestamp naming no timeline is checked for its timeline
alone. The elisions are read after the named timestamps, in array order;
an elision's `start`, `end` and width `span` are own-axis values of its
timeline, checked with the `representation` rule after the timestamps'
coordinates (`span 2 of 'elision_1' is an int on a fraction axis: write
[2, 1]`, at `width/span`).

The statement rules read the manifest with bare IDs and its statements as
written (they are the same in both forms). Subject order is the manifest,
then root by root the timeline, its regions in array order and its
children, depth first; the reserved keys add the groups after the
subjects, each element's keys in code-point order. Within a subject the
rules follow its container's keys in code-point order (each `type` item an
IRI; any other key an IRI, then each of its values: a value object's
`@type`, an ordered list's items, a node's `id`, then whether it names an
element, then the node's own pairs and provenance as a subject's), then
its provenance entries, each entry's keys in code-point order (`basis`,
`date`, `method` unless one of the four words, `property`, `service`,
`stated_by`, `value`, and `beliefs`: each belief's `actor` a reference and
its `date` a date), then each entry again for `belief_actor` and
`provenance_duplicate`; an entry may match a stated pair or none. The schema checks that a date is written
`YYYY-MM-DD`; `calendar_date` checks that the calendar has it. The
Gregorian calendar counts months 1 to 12 and the days of each month,
February having 29 in a year divisible by 4 and not by 100, or by 400; its
years run from 1 (the first year of Python's `datetime.date`), so
`0000-01-01` is refused too. What proves it (`test_statements.py`):
`2024-02-29`, `2000-02-29`, `0001-01-01` and `9999-12-31` validate, and
`2026-02-30`, `2023-02-29`, `2100-02-29`, `2026-11-31`, `2026-13-01`,
`2026-00-10`, `2026-11-00` and `0000-01-01` are each one `calendar_date`
problem with the message above. Pairs match as `same_pair` says (the
section "Statements").

## What proves the rules

**The shared rejection cases are the oracle the two packages share.** Each of
the 258 cases of `fixtures/rejections/0.2.0/` breaks one rule and stores the
path, the code and the message (`test_validate.py`); `validate` raises
`SchemaValidationError` with exactly all three, and the JavaScript suite
holds its validator to the same three, so the two packages refuse every
case at one path with one code and one message. The codes of the cases are
exactly the forty-one of `ValidationCode`, the thirty-five of the table and
the six of the sections "MatchStamps and resources" and "Groupstamps"
(`groupstamp`, `alignment_anchor`, `matchstamp`, `match_timestamp`,
`resource_timeline`, `resource_type`), so every code is reached by a case
both suites read. `version_unknown` raises `UnsupportedVersionError` and stores
`["timetoshare"]`, the code `null` and the error's message. Three cases
refuse a conversion map that is no object, which the schema types as an
object beside its discriminated `oneOf`: `conversion_map_not_object` (`0`),
`conversion_map_null` (`null`) and `combination_map_member_not_object` (a
`CombinationMap` output `9`), each at the value with `… is not of type
'object'`. Every case is read through the
package's one reader, `rejection_case`, which every consumer uses too; it
puts the infinity or NaN a `finite_number` case names at the stored path.
Three tests pin the reader: `nan_offset` and `infinite_length` hold the
value in place and are reported at their path with the exact message, a
case without one (`id_empty`) reads as written, and an unknown name is
refused with `ValueError`. Each case's text is the
standard writer's, and the set of names is stated literally, so a case cannot
disappear unnoticed. Twenty-three cases pin their message too (`test_identity.py`
and `test_statements.py`):
`child_unit_differs`, `child_number_type_differs`,
`child_offset_beyond_parent`, `child_end_beyond_parent`,
`region_id_duplicate_across_roots`, `band_order_unknown_entry`,
`band_order_missing_line`, `band_order_old_form`, `order_unknown_group`,
`timestamp_timeline_unknown`, `timestamp_coordinate_beyond_length`,
`timestamp_coordinate_negative`, `timestamp_id_is_timeline_id`,
`context_absent_with_statements`, `reserved_key_term_on_timeline`,
`subject_id_not_fragment`, `iri_prefix_undeclared_key`,
`element_value_dangling`, `element_value_with_label`,
`provenance_date_impossible`, `provenance_repeated`,
`belief_actor_repeated` and `belief_date_impossible`; ten MatchStamp and
resource cases pin theirs in `test_validate.py` (the table "MatchStamps
and resources" below). The 44 statement
cases break one rule each of the manifest `B`: the format's `@context`
with `schema`, `wd` and `wdt` (others as a case needs), and one root
`clt_1` (8 quarters), its `statements` and `provenance` as the case says,
in the complete form: the context absent beside statements or the
bundle's provenance (`context`), a term altered or missing, a prefix that
is no namespace or an element's key (`schema` at the term, at
`@context`), an undeclared prefix in a key, a node's `id`, a `type` item
and an entry's `basis` (`iri`), a bare word as a `type`, a key, an entry's
`property` and a keyword as a key, empty statements, values and
provenance, repeated values, a float, `null` in the values and in an
ordered list, a value object with both a language and a datatype, an
empty node, a blank-node `id`, an entry with an unknown method, match,
a belief none of the three and a date not written `YYYY-MM-DD` (`schema`
at the member, the value or the container), an integral float
(`representation`), an impossible date of an entry and of a belief
(`calendar_date`), an actor holding two beliefs in one entry
(`belief_actor`), a repeated
entry (`provenance_duplicate`), a reference to no element
(`dangling_target`), a node naming an element with a label
(`element_value`), a subject whose ID is no IRI fragment (`iri`), and a
reserved key: a term on a timeline, an IRI on a region, `statements` on a
group, a prefix on the manifest, `@context` on a timeline, `children` on a
region (`reserved_key`).
`id_control_character_trailing_newline` names its one root `score`
followed by a newline and is refused at that `id` (`schema`), the case on
which an anchored pattern would part the two validators. The four
cases of named timestamps break one rule each of the manifest `score` (8
quarters) with the child `verse` (4 at 2): a timestamp on `ghost`
(`timestamp_timeline` at its `timeline`), at `[5, 1]` on `verse`
(`timestamp_coordinate`, beyond the child's own length 4, though within
its parent), at `[-1, 1]` on `score` (`timestamp_coordinate`), with the ID
`timestamp_1` of a timeline (`duplicate_id` at the timestamp's `id`, first
at the timeline's).
Two more break the schema's `display` of a timestamp on `score`:
`timestamp_display_unknown` states `["wedge", "flag"]` (`schema` at
`display/1`, the word outside the enum) and `timestamp_display_repeated`
states `["wedge", "name", "name"]` (`schema` at `display`, the duplicate
breaking `uniqueItems`), each `display` in canonical order, so ordering it
moves nothing. Every case is written in the complete form, so a timestamp
of a case states its `display`. The six cases of elisions are written so
too, on the same manifest, each with one elision `elision_1` on `verse`
from `[1, 1]` to `[3, 1]` but for what it breaks (section "Elisions").

**A MeasureMap row's `volta` is one pass or several, kept as written.** The
schema admits a positive integer or a non-empty list of distinct positive
integers. What would prove it wrong: a list refused, an integer and the
list of that one integer told apart nowhere, or a writer that sorts,
unwraps or wraps the value. The five cases `measure_map_row_volta_*` break
one rule each of one manifest in the complete form: a MeasureMap of four
4/4 rows, the third under a bracket for the passes `[1, 3]` and the fourth
under one for `[2]`, and one root `score` of 16 quarters. Each states
another `volta` in the third row: `[]` (`schema` at the `volta`, `[] should
be non-empty`), `[1, 1]` (at the `volta`, `[1, 1] has non-unique
elements`), `0` (at the `volta`, `0 is less than the minimum of 1`),
`[1, -3]` (at member 1, `-3 is less than the minimum of 1`) and `[1, 2.5]`
(at member 1, `2.5 is not of type 'integer'`). The acceptance
(`test_validate.py`) puts `1`, `[1]`, `[1, 3]` and `[3, 1]` at that place
of the same manifest: each validates, and the row reads back with that
very value (an integer stays an integer, a list a list in its order, the
fourth row's `[2]` beside it) from `minimal`, `complete`,
`canonical_order` and from `loads` of the text `dumps` writes in each
of the three serializations. No function of the package expands or
compresses rows, so these are all the readers and writers a row passes.

**Each semantic rule has the smallest inline document with exactly one
problem** (`test_identity.py`, `test_segment_lines.py`), whose path and
message are stated literally, and `validate` raises that same problem. The
documents that bound each rule from the other side:

- **One scope.** Every ID is unique across the manifest. Inside one root a
  timeline ID repeated is reported once, at the later. Nested map IDs count
  after the tree's other IDs: two maps `l` held by one `ChainMap`, a map
  `l` held by a `PiecewiseMap` beside a region `l`, and a map `cmap_1` held
  by the `CombinationMap` `cmap_1` are each one `duplicate_id` at the
  nested `id`. Across roots, a jump target `m` in two roots, a region
  `perf` beside a child timeline `perf` of another root, and a map `l` held
  by a `ChainMap` in two roots are each one `duplicate_id` at the later
  root's ID, naming the first. A group ID equal to any ID of a root's tree (a region's
  included) and a MeasureMap ID equal to a group ID are one `duplicate_id`
  at the group's or MeasureMap's `id`, and a manifest ID equal to a
  region's one `manifest_id`.
- **No reserved word.** The part words of an address (`start`, `end`,
  `name`, `label`, `card`), names shaped like a band (`regions_1`,
  `flow_control_907`) and IDs holding
  a slash, a space, a colon or a `#` (`perf/take 2`,
  `https://example.org/piece/score#exposition`) are accepted as the ID of a
  timeline, a map, a map held by a `ChainMap`, by a `PiecewiseMap` and by a
  `CombinationMap`, a region, a break, a jump, a jump target,
  a group, a MeasureMap and the manifest: `identity_problems` finds nothing
  and `validate` accepts each manifest. So are `#NOMATCH_SENTINEL` (written
  `##NOMATCH_SENTINEL`) and `chunk_sentinel`, which only resemble the two
  strings below.
- **The sentinels' strings are no ID.** `NOMATCH_SENTINEL` and
  `CHUNK_SENTINEL`, the two strings a MatchClaim table writes for a
  sentinel in its event ID columns (`timetoshare.ids` names them), are
  refused as the ID of each element of the list above, written
  `#NOMATCH_SENTINEL` and `#CHUNK_SENTINEL`: `validate` raises the code
  `schema` at that element's `id`, `'NOMATCH_SENTINEL' is reserved for a
  sentinel` (the ID without its `#`), and `identity_problems` finds
  nothing, the rule being the schema's `Id`. The rejection case
  `id_chunk_sentinel` holds it for a timeline in both packages.
- **Containment.** A child has its parent's unit (`child_unit`), then its
  parent's number type (`child_number_type`), each the declared one or the
  unit's default: a seconds child declared `fraction` under a quarters
  root is `child_unit` alone; a ticks grandchild under a quarters child is
  `child_unit`, then `child_number_type` at its `unit`, since it declares
  no number type (`child 'b' has the number type 'int', its parent 'a' has
  'fraction'`); a quarters child declared `float` under a `fraction` root is
  `child_number_type` at its `number_type`. A child admits every number
  type its unit admits when its parent has it (the parent declares it, a
  test per unit and number type), and a number type its unit does not
  admit is the schema's, at the child. A child's end is its offset plus
  its length, or, for a segment of unknown length, its successor's offset.
  On a `float` axis the offset and the length are added as doubles, as a
  reader adds the JSON numbers it reads, and that sum is compared with the
  parent's length; on an `int` or `fraction` axis the values are added and
  compared exactly. The end is spelled in the parent's number type, a
  fraction pair where that type has no exact spelling: `0.2` at `0.1` in
  `0.3` seconds ends at `0.30000000000000004`, their double sum, `0.5` at
  `0.5` in `0.75` at `1.0`, `240` ticks at `480` in `480` at `720`, a
  quarters child of a quarters root both declared `float`, `2.5` at `7.0`
  in `8.0`, at `9.5`; a seconds child whose length is the Fraction pair
  `[1, 3]`, which no double equals, at `0.5` in `0.75` ends at `[5, 6]`,
  the exact sum (`identity_problems`; `validate` refuses the pair on a
  `float` axis first, as a representation problem); `0.25` at
  `0.5` in `0.75` and `[2, 1]` at `[8, 1]` in `[10, 1]` end at the length
  and pass. The double sum decides even where it differs from the exact
  one, as for three doubles whose exact sum exceeds the parent's length by
  3/2^46 while their double sum equals it: `855.5289364103584` points at
  `76.70371459980326` in `932.2326510101616` end at the length in double
  arithmetic and pass; one decimal step longer, `855.53` ends at
  `932.2337145998032` and is reported. The same three values written as
  the Fraction pairs that equal them on a `fraction` axis are added exactly
  and reported, ending at `[65600040932999587, 70368744177664]`. Where the
  two `float` values have no double sum, because it overflows or because
  one is an integer no double holds, they are added exactly and the end,
  which no double equals, is spelled as a Fraction pair: `1e308` at
  `1e308` in `1.7976931348623157e308`, the largest double, ends at
  `[2n, 1]`, n being the integer the double `1e308` equals, and is
  reported; `10^400` at `0.5` in `1.0` ends at `[2·10^400 + 1, 2]`, which
  `identity_problems` reports while `validate` refuses the integer on a
  `float` axis first, as a representation problem.
  An offset beyond the length is its child's one problem; a child of another
  unit gets only the unit problem, also between two continuous logical units
  (`number` under `quarters`); a parent of unknown length checks no
  containment. Unknown lengths pass wherever they stand: a root, a locked
  root, a child in a parent of known length and the reverse
  (`test_validate.py`). Negative offsets pass, on a root (`-1700000000.25` seconds,
  `[-3, 2]` quarters) and on a child (`-1.5`, `-0.0` seconds,
  `[-1, 1000000]`, `[-3, 2]` quarters, a grandchild at `[-1, 2]`), while a
  child at `[-3, 2]` of length `[40, 1]` in `[32, 1]` ends at `[77, 2]` and is
  reported. A grandchild is reported at its own path, naming its parent.
- **Segment lines.** Offset order decides, not array order (`b`, `a` at 3
  and 0 are contiguous). A segment ends where a child ends under
  containment: on a `float` axis (a segment has its line's number type),
  at the double sum of its offset and length, else at the exact sum
  (`0.1 + 0.2` seconds does not meet `0.3`, their double sum being
  `0.30000000000000004`; `0.5 + 0.25` meets `0.75` and `0.3 + 0.7` meets
  `1.0`). The double sum decides even where the exact one differs: on a
  `points` line of length `1000.0`, `a` of `76.70371459980326` at `0.0`,
  `b` of `855.5289364103584` at `76.70371459980326` and `c` of
  `67.7673489898384` at `932.2326510101616` pass, though `b` ends 3/2^46
  beyond `c`'s offset and `c` 1/2^46 short of the length in exact
  arithmetic (both sums are asserted in the test). A real gap is still
  refused: `b` at `76.70371459980328`, one double after `a`'s end, is one
  problem at its offset. The same values as the Fraction pairs that equal
  them on a `fraction` line are added exactly and refused at `c`'s offset
  and at the line's length; on the `float` line, `b`'s length written as
  the pair, which no double equals, is added exactly too: one problem, at
  `c`'s offset (`identity_problems`; `validate` refuses the pair on a
  `float` axis first). Where a segment's offset and length have no
  double sum, it ends at their exact sum: on a `points` line of unknown
  length, `b` of `1e308` at `1e308` after `a` of `1e308` at `0.0` ends
  beyond every double, so `c` at `1.7976931348623157e308` is one problem
  at its offset, while `b` of `1.0` at `10^400` after `a` of `10^400` at `0.0` meets
  `a`'s end and `identity_problems` finds nothing (`validate` refuses the
  integer as a representation problem). A segment of unknown length ends where its
  successor starts; the end check is skipped where the last segment's or the
  line's length is unknown, contiguity is not; a line without segments has
  one problem at a length of 8, none at 0 or null; a flag differing from the
  first segment's is reported at its `is_segment_line`, or at the segment
  where the key is absent; a descendant segment line is checked at its own
  path, a timeline whose `is_segment_line` is false never.
- **Conversion maps.** A `TableMap` with three x values and two y values is
  one problem at its `y_values`, with x values `[0, 1]`, `[2, 1]`, `2.0` one
  at the third (values compare exactly, `2.0` equals `[2, 1]`), and with
  `[0, 1]`, `0.5`, `[3, 4]` none; a `PiecewiseMap` with three breaks and one
  map is one problem at its `maps`, with breaks `[0, 1]`, `[8, 1]`, `[4, 1]`
  one at the third. A map nested in a `ChainMap`, a `PiecewiseMap` or a
  `CombinationMap` is checked at its own path (`…/maps/0`, `…/maps/beat`),
  the outputs `b` and `a` of a `CombinationMap` in the order `a`, `b`, and a
  map of a child at the child's path.
- **Source units.** A map converts from its timeline's axis, and a map
  another holds reads its holder's input. A `MeasureRecordMap` (source
  `quarters`) attached to a ticks timeline `score` is one problem at its
  `source_unit`, `MeasureRecordMap 'bars' has source unit 'quarters', its
  timeline 'score' has 'ticks'`, also on a child in ticks, at the child's
  path; the same view held second by a `ChainMap` from ticks whose first
  map is a `LinearMap` from ticks to quarters passes, as does a map whose
  `source_unit` is null and a map held by a holder whose `source_unit` is
  null. A `ChainMap` from quarters whose first map, the `LinearMap`
  `scale`, is from ticks is one problem at `…/maps/0/source_unit`,
  `LinearMap 'scale' has source unit 'ticks', its ChainMap 'chain' has
  'quarters'`; a measure view held by a `CombinationMap` from ticks is one
  at `…/maps/bar/source_unit`, and a `LinearMap` from seconds held by a
  `PiecewiseMap` from quarters one at `…/maps/0/source_unit`. Every
  emitted fixture passes (`test_fixtures.py`).
- **Flow control.** The schema ties each role to what it carries
  (section "Flow"): a destination needs no place and no condition
  (`test_validate.py`: a da capo, a dal segno and a repeat end without `to`,
  and a destination `{}`, validate without an unknown key or a flow
  warning). A destination's `to` naming a jump target, a region, a child
  of its timeline or the timeline itself passes; one naming a jump target
  of its child, a break, or a region of its child, and a child's
  destination naming a jump target of its parent, are each one
  `dangling_target` at that `to` (`test_identity.py`).
- **MeasureMaps.** A measure view naming `ghost` while `measure_maps` holds
  only `measures` is one problem at its `measure_map`, also when nested in a
  `CombinationMap`; a MeasureMap in a manifest of a timeline in seconds
  is no problem, as no unit constraint remains. A MeasureMap ID equal to
  a timeline ID, a group ID or an earlier MeasureMap ID is one
  `duplicate_id` at the later ID, and a manifest ID equal to a MeasureMap ID
  one `manifest_id`.
- **Groups and orders.** A child in one group with its root in another or in
  none, a group without members and members of unknown length pass. A
  timeline that is a member of two groups (`t` in `g1` beside `u` and in
  `g2` beside `v`) is no problem for `identity_problems` and validates. A
  member listed twice in one group (`a`, `a`) is the schema's rule, not an
  identity rule: `validate` refuses it at `members` (the shared case
  `group_members_repeated`). A band order passes at a root and at a descendant (for the child `b` the reverse
  of the default), and so does a subset holding `line`: `["markers",
  "line"]`, `["line", "flow_control"]`, `["line"]`, `["regions",
  "line"]` and the README's example without `flow_control`, each beside
  the child `b` stating `["line", "children"]`; each stranger (`annotations`, `region`, `score`,
  `score/regions_1`, `Regions`) is one problem at its entry, a missing
  `line` one at the order (`["markers", "regions"]`, and the empty order,
  `'line' is missing from the band order of 'score'`), and a missing facet
  none. An order keyed by a region's ID is one `order_key`. A virtual
  timeline is a member like a timeline: a group of `recording` and the
  virtual timeline `virtual_1` that applies a FlowMap of `score`, and one
  of `score` beside `virtual_1`, validate, and so does a band order keyed
  by `virtual_1`; a member naming the FlowMap `flow_map_1` or the unknown
  `virtual_2` is one `group_member` each (the shared cases
  `group_member_flow_map`, `group_member_virtual_unknown`). What would prove
  it wrong: a virtual member refused, a FlowMap's ID taken for a member, or
  a virtual member reported as lying inside the timeline it comes from.
- **Named timestamps.** Timestamps on a root, on a child and on a segment,
  at 0 and at the length, and at any coordinate from 0 on a timeline of
  unknown length pass, as do a timestamp on the second of two roots and two
  timestamps of one name at one coordinate. A timestamp ID equal to a
  timeline's (a timeline may be named `timestamp_1`), a group's or another
  timestamp's is one `duplicate_id` at the timestamp's `id`, and the
  manifest ID equal to a timestamp's one `manifest_id`. A coordinate on a
  float axis is compared exactly (`60.5` beyond `60.0`), as is a fraction
  (`[17, 2]` beyond `[8, 1]`, `[16, 2]` not). A timestamp's ID is any
  ID: `timestamp_3kq9x0m2ztb7a`, `Bar 2` and `timestamp_01` are accepted.
  A timestamp on a virtual timeline lies on its own axis: at 0 and at its
  length (`[24, 1]`) it passes, at `[25, 1]` it is `timestamp_coordinate`
  against that length; a groupstamp on a virtual timeline that is a member
  passes, on one that is none it is `groupstamp`; a resource naming a
  virtual timeline passes. An elision on a virtual timeline lies on its
  own axis as well: from `[1, 1]` to `[2, 1]` and from 0 to its length
  `[12, 1]` it passes, ending at `[25, 2]` it is `elision_stretch` at its
  `end` against that length (`end [25, 2] of 'elision_1' is beyond the
  length [12, 1] of its timeline 'virtual_1'`), and its `start` `1.0` is
  `representation` at its `start` (`write [1, 1]`); `canonical_order`
  respells an elision's `start` `[2, 4]` on it as `[1, 2]` and a named
  timestamp's `coordinate` `[12, 2]` on it as `[6, 1]`, as on any
  timeline. A test that still refused the elision, read its values on
  the axis of the timeline it comes from, or left them unspelled, fails.
  So is the ID of a resource, a MatchStamp and an alignment anchor: the
  MatchStamp fixture with its MatchStamps renamed `matchstamp_3kq9x0m2ztb7a`
  and `Take 2, downbeat`, its anchors `anchor_00000000000zz` and `Bar 2`,
  a match timestamp `score at bar 2`, and two resources `MatchClaims of
  both takes` and `resource_0a1b2c3d4e5f6`, has no identity problem, no
  MatchStamp problem (`matchstamp_problems`) and passes `validate`, so a
  pattern or another restriction put back on any of these IDs fails.
  The schema refuses an empty `name`, a `name` null and a timestamp
  without `coordinate`, each at that member (the
  missing member at the timestamp). `display` passes as `[]`, as `["id"]`,
  as all five in canonical order and as all five reversed (the order
  carries no meaning); the schema refuses `"wedge"` (not an array) at
  `display`, `["wedge", "Wedge"]` at `display/1` (words are exact),
  `["line"]` at `display/0` (a part word, not a display word), `[1]` at
  `display/0`, and `["name", "name"]` at `display` (`uniqueItems`).
**One document breaks every step once** (`test_every_step_in_order` and its
JavaScript twin): `identity_problems` returns exactly the stated problems, in
the stated order, with the stated codes, and `validate` raises the first.

**The finite rule runs before everything else.** Infinity as a length, NaN
in a fraction pair of a region and negative infinity in a style, each in a
manifest whose repeated root also breaks the identity rules, raise
`finite_number` at the leaf with the message of the table.

## MatchStamps and resources

A manifest names its files in `resources` and draws named MatchStamps from
`graphical.matchstamps`; the rules beyond the schema are checked after the
named timestamps, in `validation/timestamps.py`. What proves them:

- **IDs** (`test_ids.py`). A MatchStamp's and an anchor's `id`, an
  anchor's `timestamps` and a resource's `id` and `timelines` lose and
  regain their `#`; the IDs of `match_claims` (rows of a MatchClaim table)
  and a resource's `url` keep theirs (`#claim_2`, `#fragment.parquet`).
  Every ID of a MatchStamp, an anchor and a resource is unique across the
  manifest (`alignment_anchor_id_repeated`).
- **Order and defaults** (`test_manifest.py`, `test_defaults.py`).
  `resources` and `graphical.matchstamps` are ordered by ID, each
  MatchStamp's anchors by ID, and an anchor's `display` as
  `ANCHOR_DISPLAY` (`line`, `name`, then other words); `resources` and
  `matchstamps` default to `[]`; a match timestamp's `display` defaults to
  `["cross_section"]`, an ordinary one's stays `["wedge", "name",
  "cross_section"]`, so `minimal` strips each only against its own
  default; `matchstamp` defaults to `false`, so an ordinary timestamp
  completes to `matchstamp: false` and minimizes without it, while a match
  timestamp keeps `matchstamp: true` in both forms (every complete fixture
  with a named timestamp states it); `groupstamp` defaults to `false` for
  both kinds, so every timestamp completes to `groupstamp: false` and
  minimizes without it, and a groupstamp keeps `groupstamp: true` in both
  forms; an anchor's `display` defaults to `["line"]`; the schema states
  the match timestamp's defaults (`display`, `groupstamp`) in the `then`
  arm of `matchstamp: true` and requires `name` in the `else` arm
  (`test_schema.py`).
- **The rules** (`test_validate.py`). Each rejection case pins its message:

| Code | Case | Message |
| --- | --- | --- |
| `alignment_anchor` | `alignment_anchor_timestamp_unknown` | `'timestamp_99' names no timestamp of this manifest` |
| `alignment_anchor` | `alignment_anchor_timestamp_not_match` | `'timestamp_2' is no match timestamp` |
| `alignment_anchor` | `alignment_anchor_one_timeline` | `the timestamps of 'anchor_2' both lie on the timeline 'score'` |
| `groupstamp` | `groupstamp_match_without_group` | `'timestamp_1' is a groupstamp, but its timeline 'score' is a member of no group and lies in none` |
| `match_timestamp` | `match_timestamp_in_no_matchstamp` | `the match timestamp 'timestamp_11' belongs to no MatchStamp` |
| `match_timestamp` | `match_timestamp_coordinate_repeated` | `'timestamp_11' lies on the coordinate of the match timestamp 'timestamp_1'` |
| `matchstamp` | `matchstamp_not_connected` | `the alignment anchors of 'matchstamp_1' are not one connected set` |
| `duplicate_id` | `alignment_anchor_id_repeated` | `'anchor_1' is not unique in the manifest, first at #/graphical/matchstamps/0/alignment_anchors/0/id` |
| `resource_timeline` | `resource_timeline_unknown` | `'take_3' names no timeline or virtual timeline of this manifest` |
| `resource_type` | `resource_match_claim_twice` | `'score' is listed by the resource 'resource_1' of the type MatchClaim already` |
| `resource_type` | `resource_event_timeline_twice` | `'take_2' is listed by the resource 'resource_2' of the type Box already` |
| `folder_descriptor` | `resource_folder_size` | `'../tables/MatchClaim/' names a folder, which has no size` |

  A timeline is listed by at most one resource of each type, for every
  type, not only `MatchClaim`; several resources of one
  type are admitted. Each refusal is reported at the later resource's
  entry of `timelines` (`[resources, 1, timelines, 0]`), never at its
  `type`. What proves the rule admits what it should: the case
  `resource_match_claim_twice` with its second resource listing only
  `#take_2` validates, two MatchClaim resources over disjoint timelines;
  `resource_event_timeline_twice`, three `Box` resources of which the first
  two list `take_1` and `take_2`, validates without its third; and
  `resource_folder_size` validates without its `size`, a folder named
  alone, and is refused again (`folder_descriptor`, `… which has no
  integrity`, at `integrity`) with an `integrity` instead, while a file
  (`match_claims.parquet`) with a `size` and an `integrity` validates. A
  test that accepts a timeline listed twice by one type, or refuses one
  listed once by each of two types (a timeline listed by a `MatchClaim`
  and a `Box` resource), fails.

  `identity_problems` lists every problem in order: a match timestamp is a
  named timestamp first, so a groupstamp lying in no group is reported with
  the named timestamps, before the MatchStamps; then per MatchStamp its
  anchors (each timestamp, then the pair), then whether they connect; then
  each match timestamp, a shared coordinate before an unnamed one. One
  manifest proves it: `matchstamp_not_connected` (a bundle without groups)
  with its first anchor naming two ordinary timestamps and a groupstamp
  match timestamp added at the coordinate of `timestamp_11` gives exactly
  `groupstamp` at timestamp 10's `groupstamp`, two `alignment_anchor`
  problems, one `matchstamp`, `match_timestamp` at timestamps 1 and 4,
  then `match_timestamp` at timestamps 10 and 10.
- **The MatchStamps alone** (`test_validate.py`). `matchstamp_problems`,
  for a reader that keeps the rest of `graphical` unread, returns for each
  of the nine MatchStamp rejection cases a first problem equal, code, path
  and message, to the one `validate` raises: the schema of
  `graphical.matchstamps` (`alignment_anchor_display_unknown`,
  `matchstamp_claims_repeated`), an ID of a MatchStamp or an anchor
  repeated (`alignment_anchor_id_repeated`), then the rules. It returns
  nothing for every fixture (`bundles/bundle_matchstamp_groupstamp`
  among them) and for every other rejection case, the named-timestamp,
  groupstamp-without-group (`groupstamp_match_without_group` among them)
  and style cases among them, whose faults lie outside the MatchStamps; a match timestamp breaking the timestamp schema (no
  `timeline`) is reported by the schema at that timestamp, never raised
  as a `KeyError`. A number that is not finite is reported as `validate`
  reports it, code, path and message: an infinite coordinate of a match
  timestamp is "coordinate of 'timestamp_1' is not a finite number" (the
  ID bare, as the finite rule reads the manifest), an infinite entry
  appended to `match_claims` "match_claims of 'matchstamp_1' is not a
  finite number" at that entry, never the schema's message. A named
  timestamp that is no object is passed over (the rules read a manifest
  whose ordinary timestamps no schema checked). The TypeScript suite
  proves the same of `matchstampProblems` with the same values.
- **The bundle** (`test_schema.py`). `provenance.schema.json` lies beside
  the manifest schema with its own `$id`, defines `Belief` and
  `CalendarDate` and refers to the manifest schema's `Iri` and
  `IriReference`; `load_schema()` equals `bundle_schemas` of the two files,
  every reference local; a definition of both names is refused.
  Every reference leads to the same place in the bundle as in its own
  document, each case on a small pair of schemas: from the provenance schema,
  `timetoshare.schema.json` gives `#`, `timetoshare.schema.json#/$defs/A`
  gives `#/$defs/A`, `#` and `provenance.schema.json` give
  `#/$defs/ProvenanceRecord`, `#/$defs/P` and
  `provenance.schema.json#/$defs/P` give `#/$defs/P`, `#/properties/a` gives
  `#/$defs/ProvenanceRecord/properties/a`; from the manifest schema,
  `#/$defs/A` stays and `provenance.schema.json#/properties/a` gives
  `#/$defs/ProvenanceRecord/properties/a`. A reference to any other document,
  `https://example.org/other.json` in either schema, is refused with
  "reference 'https://example.org/other.json' leads outside the two schemas".

## Groupstamps

A named timestamp with `groupstamp: true` lies in a group: its timeline
or one of its ancestors is listed in the group's `members` (a member's
descendants are drawn inside the member's card in the group's frame); an
ancestor of a member lies in no group through it. Its line extends across
the frame of each group it lies in; the members' coordinates are derived,
never stored, so nothing beyond the flag is checked. What proves it:

- **Defaults** (`test_defaults.py`, `test_schema.py`). As stated under
  "MatchStamps and resources": `groupstamp` defaults to `false` on an
  ordinary and on a match timestamp, and the schema declares that default
  for both (the `then` arm repeats it, since the arm's defaults are the
  match timestamp's whole table).
- **The rules** (`test_validate.py`, `test_identity.py`). Code
  `groupstamp`, at the timestamp's `groupstamp` member. The boundary of
  "lies in a group" is pinned from both sides: accepted are a member
  (`groups/group_groupstamp`), a member shared by two groups
  (`bundles/bundle_groupstamp_shared_member`) and a member's child
  (`groups/group_groupstamp_child_member`, below); refused, each with
  `'<id>' is a groupstamp, but its timeline '<timeline>' is a member of
  no group and lies in none`, are a root in no group
  (`groupstamp_without_group`: the fixture `timestamps.yaml` with
  `timestamp_1` on `clt_1` made a groupstamp), a child whose ancestors
  are in no group (`groupstamp_child_without_group`: the same fixture
  with `timestamp_3` on the child `clt_2` made a groupstamp) and the
  parent of a member (`groupstamp_member_parent`: the fixture
  `groups/group_child_member.yaml`, whose member `second-half` is a child
  of `piece`, with a groupstamp `timestamp_5` added on `piece`). A fourth
  case, `groupstamp_match_without_group` (the fixture
  `bundles/bundle_matchstamps.yaml`, a bundle without groups, with its
  match timestamp `timestamp_1` on `score` made a groupstamp), gives the
  same message for `timestamp_1` and `score` at
  `["graphical", "timestamps", 1, "groupstamp"]`, so a match timestamp
  meets the membership rule as any named timestamp does; and a match
  timestamp that is a groupstamp on a member is accepted
  (`bundles/bundle_matchstamp_groupstamp`, below). The membership cases
  are a rule of the named timestamps, reported after the timeline and
  coordinate of the same timestamp, so `matchstamp_problems` returns
  nothing for any of them.
- **The fixtures** (`test_fixtures.py`). `groups/group_groupstamp.yaml`
  and its twin hold the group `group_1` ("Performance") of `score` (with
  a map to ticks) and `performance` (with a map to samples), so both
  members have a conversion maps band, and the groupstamp `timestamp_1`
  ("Bar 2", `[4, 1]` on `score`) beside the two members' origin and
  length timestamps (`timestamp_2` to `timestamp_5`); in the fixture
  every timestamp states `groupstamp` (`true` for `timestamp_1` alone), in
  the twin only `timestamp_1` does.
  `groups/group_groupstamp_child_member.yaml` holds the same group, the
  score without its map holding the child `second-half` (4 quarters at
  4), with the groupstamp `timestamp_1` ("Bar 4", `[2, 1]`) on the child,
  which is listed in no group's `members`.
  `bundles/bundle_groupstamp_shared_member.yaml` holds the bundle of
  `bundle_shared_member` (`t` a member of `g1` and of `g2`, no band) with
  the groupstamp `timestamp_1` ("Bar 2", `[4, 1]`) on `t`.
  `bundles/bundle_matchstamp_groupstamp.yaml` is
  `bundles/bundle_matchstamp_cards.yaml` (`score` a member of two groups)
  with its match timestamp `timestamp_1` (`[4, 1]` on `score`) a
  groupstamp: in the fixture it states `groupstamp: true` and
  `matchstamp: true`, in the twin both, every other timestamp neither
  `groupstamp` nor, unless a match timestamp, `matchstamp`. Every one of
  them and its twin passes `validate` and `identity_problems`, and
  `matchstamp_problems` finds nothing in either form.

## Flow

Flow control, FlowMaps and virtual timelines. The schema states the shapes;
`timetoshare.validation.flow` holds the rules beyond it; the shared cases
are the oracle of both packages; the flow fixtures and the expected flows
are data for any implementation that computes a flow, which this package
does not.

**What would prove it wrong.** A role carrying a member of another role; a
vocabulary closed by an `enum`, so that a word the format does not define
is refused; a rule reading a rejected element; a place compared by spelling;
a reference resolved outside its timeline or its root's tree; an expected
flow that does not follow from its manifest.

- **The schema** (`test_flow.py`). `FlowControlElement.role` is exactly
  `jump`, `jump_target`, `break`, `section_break` and `barline`; the element
  requires `id`, `role` and `coordinate` and declares exactly `id`, `role`,
  `coordinate`, `targets`, `manifestation`, `ends`, `name`, `label`, `meta`
  and `provenance`, none of the earlier `type`, `target` and
  `repeat_count`. `manifestation` and a FlowMap's `convention` are strings
  without an `enum`. A `JumpDestination` declares exactly `to`, `by`,
  `passes`, `repeat_count`, `after`, `determined`, `reset`, `manifestation`
  and `label`, requires none, and refuses `to` beside `by`; `Passes` is a
  non-empty list of distinct integers from 1, or `{from: n}` with n from 1;
  a `DestinationReference` requires `jump` and refuses `to` beside `by`; a
  `BreakCondition` is not empty and holds `passes` or `after`. The manifest
  declares `flow_maps` and `virtual_timelines`; a `FlowMap` requires `id`,
  `timeline` and `chunks`, a `Gap` its strictly positive `gap`, a
  `VirtualTimeline` `id`, `map`, `timeline`, `unit`, `number_type` and
  `length`, under the very `if`/`then`/`else` that ties a timeline's number
  type to its unit. `provenance` of a flow-control element and of a FlowMap
  is a non-empty list of provenance entries without a pair. The
  descriptions name every word of `MANIFESTATIONS` and `CONVENTIONS`, the
  tables the warnings read, and the region's description the class
  `ATOMIC_SECTION`, the format's namespace followed by `AtomicSection`.
- **The earlier form** (`test_flow.py`). An element with `type` `jump_from`,
  `jump_to` or `flow_marker` (also beside a `role`), with a `role` that is
  one of those words, or with `target` and no `role`, on a child, is
  refused with `flow_control_form` at the element, its message naming the
  ID and `scripts/convert_flow_control.py`, which exists; the rule comes
  before the schema (a manifest with an unknown unit too reports it) and
  names an element without an ID by its JSON pointer. A `type` beside a
  current `role` is an unknown key and nothing more.
- **Rejected elements** (`test_flow.py`). An element is rejected when an
  entry of its `provenance` holds a belief `false`; `unlikely`, another
  entry's method and no provenance do not reject. A rejected jump and its
  replacement at one coordinate validate, and without the rejection the
  second is `jump_repeated`. A rejected jump at a coordinate off the axis
  with two destinations at one place, both dangling, raises nothing, while a
  `to` naming a rejected jump target and an `after` naming a rejected jump
  are each `dangling_target`.
- **Coordinates and places** (`test_flow.py`, the shared cases). On a
  timeline of unknown length a coordinate and a place far out are accepted
  and a place before 0 refused with `it lies before 0`; the coordinates 0
  and the length and the places they reach are on the axis. On a float
  axis a place is the double sum of the two numbers: 0.1 and 0.2 reach
  0.30000000000000004, on a timeline of that length and off one of length
  0.3. A destination `to` an element and one `by` a distance landing at the
  same coordinate are two places.
- **After** (`test_flow.py`, the shared cases). A reference without a place
  names the one destination of a jump, or its one destination without a
  place; with `to` or `by` the destination of that place, `by` compared by
  value (`[-4, 2]` names `[-2, 1]`); a jump with two placed destinations
  and a reference without a place, a `by` or a `to` no destination has, a
  jump of a child and the destination's own jump are each
  `dangling_target`, at the `after` or at the member that fails.
- **FlowMaps and virtual timelines** (`test_flow.py`, the shared cases). A
  chunk is a region of the root or of a descendant, a child at any depth,
  or a virtual timeline that comes, through any number of virtual
  timelines, from a timeline of the root's tree; a region or a virtual
  timeline of another root, another root, the root itself, a FlowMap and an
  unknown ID are each `flow_map_chunk`; two virtual timelines naming each
  other come from no tree. A virtual timeline's `map` names a FlowMap or a
  conversion map at any depth, a map another map holds included, and its
  `timeline` never the virtual timeline itself (`dangling_target`). One
  FlowMap per timeline is canonical; a second is `flow_map_canonical`,
  FlowMaps of two timelines are not. A FlowMap's and a virtual timeline's
  ID count among the manifest's IDs, after the resources'.
- **Virtual timelines held to their map** (`test_flow.py`, the shared cases
  `virtual_timeline_cycle`, `virtual_timeline_map_other_root`,
  `virtual_timeline_length_not_the_sum`). What would prove it wrong: a ring
  reported at a virtual timeline that only leads into it, a FlowMap of
  another root accepted, a length compared by spelling or on an axis whose
  sum depends on the order of its additions. A ring of three virtual
  timelines is `virtual_timeline` at the `timeline` of each of the three,
  each naming the others in the order of its chain, while a fourth that
  comes from the ring and a chain from a timeline are not reported, and
  neither the FlowMap nor the length of a ring is read; once the ring is
  broken, all six validate. A FlowMap of `score` applied to the root, to
  its child and to a virtual timeline coming from the child validates;
  applied to another root, to a virtual timeline coming from it, or a
  FlowMap of that other root applied to `score`'s child, it is
  `virtual_timeline` at the `map`, the length (99) not read; with `through`
  all three validate, and a conversion map as `map` is never read. The
  length is the sum by exact value: a region of 2, a gap of 3/2, a child of
  4, the region again and a virtual timeline of 1/2 give 10, written
  `[10, 1]` or `[20, 2]` for the root, the child and a virtual timeline of
  the child alike. With the virtual timeline chunk restated as 1 (against
  its own FlowMap's gap of 1/2, refused with `[1, 2]`), the sum is read
  from its stated length and becomes `[21, 2]`: the three lengths `[19,
  2]`, `[20, 2]` and `[0, 1]` are each refused with it, the sum written in
  lowest terms; an empty FlowMap sums to `[0, 1]`. On a `samples` axis the sum
  is spelled as an integer (`length 60 of 'v' is not the sum of the chunks
  and gaps of 'f', 65`). The six cases where no sum is read, each with a
  length that is none: a `float` axis; a virtual timeline of another unit
  or number type than a chunk's axis; a gap on a root of another axis; a
  child of unknown length; a chunk naming nothing (its own
  `flow_map_chunk`); `through`.
- **Order and spelling** (`test_flow.py`, `test_manifest.py`,
  `test_ids.py`). `canonical_order` sorts FlowMaps and virtual timelines by
  ID, keeps each FlowMap's chunks in their order, repeated ones included,
  and sorts a jump's destinations given as two `to`, two `by` (one as
  `[-6, 2]`) and one without a place into: without a place, `[-3, 1]`,
  `[-2, 1]`, then the `to` by ID. A gap `[4, 2]` on a fraction axis is
  written `[2, 1]`, a virtual timeline's `length` `[16.0, 2]` on its own
  fraction axis `[8, 1]`, and on a float axis the `by` of a destination, of
  its `after` and of a break's `ends.after` written as integers are floats.
- **The property `flow`** (`test_flow.py`, the shared cases
  `flow_rule_*`). What proves it: the value a card is drawn in names an
  element the drawing can resolve for that card. A rule addressed to the
  cards of `score` setting `flow` to its FlowMap `flow_map_1`, or to the
  virtual timeline `virtual_1` that applies it to `score`, validates, the
  later of two such rules included. Each of these
  is one `flow_rule`: a style setting `flow` (at the style's `flow`,
  whatever rule names the style); a selector naming anything beside
  `addresses` (`element`, `within`), an address that is no card address
  (`{id}`, `{id, facet}`, `{id, part: [name]}`), each at the rule's
  `select`; a value naming a region, a timeline or nothing; a FlowMap of
  another timeline; a virtual timeline applying a FlowMap of another
  timeline, applying the right FlowMap to another timeline, applying it
  `through` a group, or applying a conversion map, each at the rule's
  `set.flow`, one problem per address that does not fit. A rule whose
  `set` names a style or sets other properties is not read. What would
  prove it wrong: a flow accepted on a card of a timeline its FlowMap does
  not play, or a problem reported for a rule that sets no `flow`.
- **Warnings** (`test_flow.py`, `test_unknown_keys.py`). Every word of the
  tables on the role or destination it belongs to, a section break without
  a manifestation, the three conventions and a FlowMap without one draw no
  warning; a word on another role (`fine` on a barline, `segno` on a break,
  `repeat_end` on a jump target, `segno` on a destination) is
  `manifestation_unknown` at the `manifestation`, with the role in the
  message, and any manifestation on a section break is, since none is
  defined. `convention_unknown` lies at a FlowMap's `convention`. Warnings
  are sorted by path, an index before a key, then by code. The shared
  cases `manifestation_unknown` (three warnings) and `convention_unknown`
  pin the messages for both packages. `flow_conflict` lies at a group's
  `members` where rules set `flow` on the cards of two or more of its
  members, naming them in the order of `members` with the flows the
  cascade gives them (the later rule for a card wins); one member switched,
  or two switched members in two groups, draw none; the shared case
  `flow_conflict` pins its message.
- **Provenance about an element** (`test_flow.py`). An entry of a
  flow-control element or a FlowMap names no pair. Beyond the schema its
  date is a calendar day, its compact IRIs name declared prefixes, its `#`
  references name elements and an actor holds one belief: each of the four
  is reported once on the element and once on the FlowMap, by
  `statement_problems` at both and by `validate` at the first. Such an
  entry needs no `@context` where it uses no prefix, and `used_prefixes`
  and `with_context` count the prefixes it uses.
- **The converter** (`test_convert_flow_control.py`), which lives in
  `scripts/` because the packages read one form only. `convert` leaves its
  input unchanged and its result validates. Each earlier type becomes its
  role with the members stated literally: a jump target; a jump with one
  destination (`to` its target, its manifestation, a repeat end's count or
  1, `repeat_count: 1` and `reset: false` on a da capo and a dal segno); a
  `fine` as a break whose `ends.after` names the timeline's one jump al
  fine; a section break without a manifestation; the two barlines. A
  `to_coda` waits for the one jump al coda. An earlier jump without a
  target went to the timeline's start: behind a section break at 8, a
  repeat end and the three da capo forms each become a destination `to`
  the timeline (`score`, or `#score` where the file writes its IDs so),
  the result validates and no destination lacks `to`, since one without a
  place would land at 8. Two earlier jumps at one coordinate become one
  under the ID first by code point, each destination with its element's
  label, the reference of a Fine naming the place where the jump has two
  destinations, an address naming the dropped ID rewritten, and the merge
  reported with the name and meta it drops. Raising `ConversionRefused`, a
  `ValueError`, with each sentence stated literally: a Fine or a To Coda
  with none or two of the jumps it waits for; a merge of two destinations
  at one place (a repeat end and a da capo without targets on one
  barline); a `flow_marker` of an unknown manifestation; a jump without a
  target that is a dal segno, of an unknown manifestation or of none; an
  element with a `target` and no type or a type none of the three words; a
  word of the earlier form beside `targets` or `ends`; two different words
  under `type` and `role`. A word under `role` converts as under `type`,
  to the same result. The converter and the validators hold one predicate:
  for each of sixteen elements, `earlier_form_problems` of the validators
  and `needs_conversion` agree, the command line prints `nothing to
  convert` exactly where the validators find nothing, and otherwise
  converts (the validators then finding no earlier form) or prints
  `refused: …` and leaves the file unchanged. A rule selecting `jump_from` selects `jump`,
  one selecting `flow_marker` becomes three in its place. A manifest
  without the earlier form comes back equal, its text byte for byte. The
  command line converts a pretty-JSON minimal file in place into pretty
  JSON in the minimal form, reports `would be converted` under `--check`
  without writing, `nothing to convert` the second time, and leaves a
  refused file as it was with exit status 1.
- **The flow fixtures** (`test_flow.py`, `test_fixtures.py`,
  `test_rdf.py`). Ten manifests under `fixtures/0.2.0/flow/`, each with its
  twin, pass every law of the fixture set. Each holds what its name says,
  stated literally from the minimal twin: two destinations of one jump
  (`repeat_end_and_dal_segno`), passes `[1, 3]` and `[2]` before two
  brackets, the repeat sign closing the second written `reset: false` and
  a Fine between the brackets ending the flow after it (`volta_passes`), a
  destination `determined: false` to a child timeline beside `by` 0
  (`ossia`), an `after` on a To Coda and on a
  Fine, a section break without a manifestation and a destination without
  a place behind it (`sections`), a loop of 127 on a seconds axis without a
  manifestation, a FlowMap by hand over two children and a gap with manual
  provenance and no convention, and an imported barline, a rejected
  imported jump and two elements added by hand, the two jumps at one
  coordinate (`repairs`). `sonata_exposition` holds three regions typed
  `tts:AtomicSection` with an `inferred` entry each, the FlowMaps of the
  three conventions, `default`, `single` and `printed` once each, each with
  the one provenance entry `{method: inferred}`, and one virtual timeline;
  read as RDF it says exactly that each region is an `AtomicSection` of the
  format's namespace and that the pair was inferred, fifteen quads;
  `volta_run` says so of its five atomic sections, the regions named "A"
  to "E", twenty-five quads, and nothing of its `region_1`
  ("Exposition"), which is none; `virtual_cards`, `switched_card` and the
  groups `virtual_member` and `switched_frame`, which hold one root
  `allegro` built alike, say so of its three sections `section_a`,
  `section_b` and `section_c` ("A", "B" and "C"), fifteen quads each;
  every other fixture outside `statements/` says nothing. The library
  mints the IDs of the regions and FlowMaps it computes, so the tests find
  the atomic sections by their names and the FlowMaps by their
  conventions, never by a minted ID, and do not rely on the order by ID
  of the FlowMaps. `virtual_cards` holds
  the three computed FlowMaps under the IDs `default`, `single` and
  `printed`, the FlowMap `by_hand` with a run of four entries and a gap,
  and three virtual timelines; `switched_card` holds the same `timelines`,
  FlowMaps and virtual timelines and a rule setting the property `flow` of
  `allegro`'s card to `default`. Numbered flow-control IDs name their role,
  without exception, and so do the IDs a loader mints (the role, `_` and
  13 base-36 characters, in `corpus_score_ms3`); the numbered ones are
  counted exactly, the minted ones are random and left out of the count,
  and every other ID is one of the given names listed.
- **The expected flows** (`test_flow.py`). `fixtures/flows/0.2.0/` holds
  one file per flow fixture with flow control, ten in all, in canonical
  YAML (`switched_card`, whose `timelines` are those of `virtual_cards`
  (`test_flow.py` compares them), stands on the file of `virtual_cards`), each beside the trace it was derived by hand with (`<name>.md`):
  `manifest` (a path under `fixtures/0.2.0/` without extension),
  `timeline` (a bare ID), `atomic_sections` (`name`, `start`, `end`) and
  `conventions`, whose `default`, `single` and `printed` each hold
  `runs`, `sections` and `findings`. A run is a
  pair of start and end, the end not played, in the spelling of the
  timeline's number type; `sections` lists the atomic sections the runs
  cover; a finding is a `kind` and a `coordinate`, a `never_played` one
  also the `end` of its stretch, and a `cause` where it has one, whose only
  value is `single_playback`. This package computes no
  flow, so the test proves agreement, not the flows: the atomic sections
  are the intervals between the boundaries the schema states (computed in
  the test from the manifest, a rejected element left out, a barline no
  boundary, a destination without a place at the nearest section break
  before its jump), lettered from A; every run starts and ends on a
  boundary inside the axis and covers the sections listed; `printed` is the
  sections in order and finds nothing; under `default` and `single`
  `never_played` is reported exactly once for each stretch of adjacent
  sections the convention's flow leaves out, at its start and with its
  end, never once per
  section, a stretch of `single` divided where the sections the `default`
  flow plays begin or end: a piece the `default` flow plays has the cause
  `single_playback`, a piece it leaves out none, and no other finding has
  a cause; every kind is one of the five the format names. For `sonata_exposition` the manifest's regions are the
  atomic sections, each FlowMap lists the regions of its convention's
  sections, and the virtual timeline's length, 36 quarters, is the sum of
  the default runs; for `virtual_cards` likewise, the default and single
  virtual timelines being 4241/2 and 3241/2 quarters long, the sums of
  their runs.

Not proven here: that the expected flows are the flows the stated behaviour
gives. They are derived by hand; an implementation computing flows is run
against them.

## Elisions

An elision `{id, timeline, start, end, name?, width?, display?}` of
`graphical.elisions` lies on the timeline it names, at any depth, a
segment included, and leaves the stretch from `start` to `end` of that
timeline's own axis out of the drawing, a narrow gap in its place.
Nothing refers to an elision; its ID is unique across the manifest like
any other. Four presentation properties of a card's rule, `elision-mode`,
`elision-proportion`, `elision-depths` and `elision-display`, choose which
elisions a root's cards draw; the schema alone checks their values. What
proves it:

- **The schema** (`test_schema.py`, section "The schema document"): its
  `display` words, its three width forms and their `oneOf`, the element
  types `elision` and `ellipsis` and the part words `elision` and
  `ellipsis`; the `display` default `["ellipsis", "name"]` and `elisions: []`
  agree with `DEFAULTS`. The four properties of `Declaration`:
  `elision-mode` is exactly the enum `auto`, `full`, `proportional`,
  `custom`; `elision-proportion` admits `"auto"`, `0.25` and `1` and
  refuses `0`, `1.5` and `"half"`; `elision-depths` admits `"auto"`,
  `"1"`, `"1 2"` and `"2 1"` and refuses `""`, `"0"`, `"1,2"`, `"1  2"`
  and `"auto\n"`; `elision-display` admits `"none"`, `"ellipsis"` and
  `"coordinate name continuation"` and refuses `"strip"`, `"none name"`
  and `"name\n"`.
- **The rules** (`test_validate.py`, `test_identity.py`). Six shared
  cases break one rule each of the manifest `score` (8 quarters) with the
  child `verse` (4 at 2), the elision `elision_1` on `verse`:
  `elision_timeline_unknown` (on `ghost`, `elision_timeline` at its
  `timeline`), `elision_end_beyond_length` (to `[5, 1]`, `elision_stretch`
  at its `end`, beyond `verse`'s own length 4 though within its parent),
  `elision_start_not_before_end` (from `[3, 1]` to `[3, 1]`,
  `elision_stretch` at its `end`: an empty stretch),
  `elision_width_two_forms` (`{"canvas": 40, "ratio": 0.5}`, `schema` at
  `width`, valid under two branches of its `oneOf`),
  `elision_ratio_zero` (`{"ratio": 0}`, `schema` at `width/ratio`, the
  exclusive minimum) and `elision_id_is_timeline_id` (the ID `verse`,
  `duplicate_id` at the elision's `id`, first at the timeline's). Nine
  more break the schema at one value each, `schema` at that value:
  `elision_name_empty` (`name: ""`), `elision_display_strip` (the word
  `strip`, at `display/0`), and in a rule's `set`, `elision_mode_unknown`
  (`elided`), `elision_proportion_zero` (`0`), `elision_proportion_word`
  (`half`), `elision_depths_zero` (`"0 1"`), `elision_depths_comma`
  (`"1,2"`), `elision_display_unknown` (`"ellipsis strip"`) and
  `elision_display_none_with_word` (`"none name"`). Inline
  documents bound the rules from the other side: on `score` an elision
  from 0 to its length 8 passes; one from `[-1, 1]` is refused at its
  `start` before anything else of it; on a root of unknown length one from
  `[100, 1]` to `[200, 1]` passes and one from `[-1, 1]` does not; one
  from `[5, 1]` to `[2, 1]` is refused at its `end` with `end [2, 1] of
  'elision_1' does not lie after its start [5, 1]`; an elision on a
  segment passes; the ID of an elision equal to a named timestamp's is
  `duplicate_id` at the elision's `id`, first at the timestamp's, and the
  manifest ID equal to an elision's is `manifest_id`. The own-axis values
  are read as the timeline's number type: `start` `1.0` on quarters is
  `representation` at `start` (`write [1, 1]`), `span` `2` at
  `width/span` (`write [2, 1]`), and on seconds `start` `1` passes as the
  float it equals.
- **Overlaps are accepted** (`test_identity.py`). On `score` the
  elisions `[0, 1]`–`[4, 1]`, `[2, 1]`–`[6, 1]` (overlapping it), one on
  the child `verse` from `[0, 1]` to `[4, 1]` (lying inside both), and a
  fourth with exactly the first one's stretch and a canvas width, in a
  manifest holding the format's `@context`, validate, draw no warning
  (`manifest_warnings` is empty) and have no unknown keys.
- **The forms and the order** (`test_defaults.py`, `test_manifest.py`).
  The defaults as stated under "Defaults". `canonical_order` puts
  `graphical.elisions` by timeline (code point), then `start` by exact
  value, then ID: `elision_4` on `b` from `[1, 1]`, `elision_3` on `a`
  from `[2, 4]`, `elision_2` on `a` from `[1, 2]`, `elision_1` on `a` from
  `[3, 1]` and `elision_0` on `ghost` come out `elision_2`, `elision_3`
  (tied in value with it), `elision_1`, `elision_4`, `elision_0`; each
  `display` in the order of `ELISION_DISPLAY` (`["coordinate", "zeta",
  "ellipsis"]` as `["ellipsis", "coordinate", "zeta"]`); `start`, `end` and the
  width's `span` are respelled on the timeline's axis (`[2, 4]` and `[4,
  8]` as `[1, 2]`, `[6.0, 1]` as `[6, 1]`), and those of `elision_0`,
  naming no timeline, stay as given (`[4, 8]`, `2`); two elisions whose
  `start` is a string are refused (`cannot put elisions in canonical
  order`).
- **IDs in a file** (`test_ids.py`). The elision's `id` and `timeline` are
  ID positions, held through `graphical.elisions`; the tables stay the
  schema's.
- **The fixtures.** Every complete fixture holding a `graphical` object
  states `elisions`, `[]` but in three, every twin leaves out an empty
  list; `bundles/bundle_elisions_stored` holds seven elisions, one of each
  width form and on each kind of timeline the drawing treats apart, names
  and display words among them, the rule `elision-mode: full` on a
  root's cards and a rule hiding every elision within that root; `groups/group_elided_members` holds two elisions on
  timelines lying in its group, one on a member that is a child timeline
  and one on a member's child, without `width` and with a ratio width;
  `bundles/bundle_groupstamp_shared_member` holds one on a member of two
  groups; each passes every check of the fixture set.

## Statements

The bundle, every timeline and every region may state property–value pairs
about the thing it stands for (`statements`) and annotate them
(`provenance`); `timetoshare.statements` reads and writes them. Two
documents serve every test (`conftest.py`, the same in the JavaScript
suite), both in the file form, since the IRIs of statements are the same in
either form: **M1**, the recording `#rec` (context: the 35 terms and
`schema`, `wd`, `wdt`) with the root `#cpt_1` (seconds, length null), its
region `#region_1` (0.0 to 10.0) and its child `#cpt_2` (5.0 at 0.0),
stating nothing; and **M2**, the two described timelines `#clt_6` (a score
encoding: `dcterms:created` a typed literal, `schema:exampleOfWork` the
MusicBrainz work with its label, `type` `melod:Manifestation` and
`schema:SheetMusic`, `wdt:P629` the Wikidata item with its label and two
`schema:sameAs`) and `#cpt_1` (a video: `rel:prf` a VIAF cluster,
`schema:sameAs` its YouTube address, `type` `schema:VideoObject` and
`melod:Manifestation`, `wdt:P175` the performer with her label and two
`schema:sameAs`, `wdt:P31` `wd:Q98069877`), its context the terms and the
nine prefixes it uses. What proves the package (`test_statements.py`):

- **The format's context.** `FORMAT_CONTEXT` holds the 35 terms, no prefix,
  and equals the schema's `Context` consts (`test_schema.py`); `NAMESPACE`
  is `https://timetoalign.github.io/timetoshare/ns#`; `beliefs`, `actor`
  (an `@id`) and `belief` (an `@vocab`) are its `beliefs`, `actor` and
  `belief`, the words `true`, `false` and `unlikely` its `True`, `False`
  and `Unlikely`, and
  `status`, `confirmed`, `proposed` and `rejected` are no term; `BELIEFS`
  is `("true", "false", "unlikely")`, strings; `BELIEF_STATES`, the states
  of the belief filter, is `("true", "undecided", "unlikely", "false")` and
  `DEFAULT_BELIEFS` its first three; `check_belief_filter` returns the
  states of a collection, in any order, empty included, and refuses with
  a `ValueError`, never another exception, a single string (`the belief
  filter takes a collection of states, not the string 'true': write
  ['true']`), a value that is no collection (`the belief filter takes a
  collection of states, not null` for `None`, `not {"true":1}` for a
  mapping) and an unknown word, naming the first by code point of its
  spelling (`'not_false' is no belief state: write 'true', 'undecided',
  'unlikely' or 'false'` for `["true", "zzz", "not_false"]`); a string
  member is quoted, a member that is no string is spelled as messages
  spell values and not quoted, so the boolean reads `true is no belief
  state: …` and never as the word it is not, `1` as `1 is no belief
  state: …`, and an unhashable member such as `["true"]` as `["true"] is
  no belief state: …`; the JavaScript package's `checkBeliefFilter` gives
  the same messages for the same inputs (its `null` and `undefined` too);
  `METHODS`
  and `MATCHES` are the schema's enums in its order; `BLANK` is the class
  the schema's `Iri` refuses.
- **Expanding an IRI.** Under M2's context `type` is `rdf:type`'s IRI,
  `label` `rdfs:label`'s, `property` `rdf:predicate`'s, `beliefs`
  `NAMESPACE + "belief"` and `actor` `NAMESPACE + "actor"`; `statements`, `id` and `provenance` (keywords)
  expand to nothing; `wdt:P175` gives
  `http://www.wikidata.org/prop/direct/P175`; `http://schema.org/name`,
  `urn:isbn:1`, `tag:x`, `mailto:a@b`, `info:x` stay as written; `wdtt:P1`
  (undeclared), `MusicRecording` (no colon) and the context's term `label`
  used as a prefix (`label:x`) expand to nothing.
- **Used prefixes and the context.** `used_prefixes(M2)` is exactly
  `["dcterms", "gnd", "melod", "rel", "schema", "viaf", "wd", "wdt",
  "xsd"]`: keys, `type` items, node `id`s, node keys and a value object's
  `@type`. A provenance entry adds its `property`, a `method` that is an
  IRI (not one of the four words), `basis`, `stated_by` and `service` and
  its value's IRIs, at a value node's depth too; an absolute IRI, the four
  URI schemes and a relative reference (`#cpt_1`, `other.yaml#x`) add
  none. `with_context(M2 without @context, CATALOGUE_TEST.prefixes)` equals
  M2's `@context`: the catalogue's unused `melodTerms` is dropped. A
  prefix the manifest declares wins over the given one; a prefix declared
  nowhere raises `the prefix 'p' is declared neither in the manifest's
  @context nor in the given prefixes`; the argument is left unchanged.
- **Subjects by path.** `subject_path(M1, None) == ()`; `#cpt_1`,
  `#cpt_2` and `#region_1` give `("timelines", 0)`, `("timelines", 0,
  "children", 0)` and `("timelines", 0, "regions", 0)`; the bare `cpt_1`
  raises `no timeline or region of the manifest has the ID 'cpt_1'`. A
  path reaching nothing (`("timelines", 9)`), a group (`("groups", 0)`), a
  provenance entry's value, a value object, a literal, a key's list of
  values and the `statements` container itself (`("timelines", 1,
  "statements")`, which is the element's, never a value node) raises
  `#/timelines/9 addresses no element and no value node` (its own pointer).
  A node is addressed through `statements` down to its item in a list of
  values (`("timelines", 1, "statements", "wdt:P175", 0)`): its pairs are
  its `schema:sameAs` values, in list order.
- **Pairs and entries.** `pairs` of M2's `#cpt_1` lists `rel:prf`,
  `schema:sameAs`, `("type", "schema:VideoObject")`, `("type",
  "melod:Manifestation")`, `wdt:P175`, `wdt:P31` in that order (keys by
  code point, values in list order); `entries` lists a subject's entries in
  order; `candidates` those whose pair the subject does not state (a
  candidate of `wdt:P175` beside a stated `type`), and given an actor, those
  the actor does not believe `False`: after the editor's belief `False` the
  candidate is offered to `TILIE` and to no actor named, never to the
  editor.
- **The same pair** (`same_pair`). Properties compare expanded: `type` and
  `rdf:type` (which an entry writes for `type`, read so even where the
  context declares no `rdf`), `wdt:P175` and its full IRI. A node with an `id` equals any
  node with the same expanded `id`, its label and pairs ignored; a `type`
  item `T` equals `{id: T}`; `true` is not `1`, `"1"` is not `1`; value
  objects compare `@value`, `@language` and the expanded `@type`; nodes
  without `id` compare as JSON without their own `provenance`; ordered
  values item by item; `#cpt_1` compares as written, never resolved.
- **Writing pairs.** The values, exactly: `with_pair(M1,
  ("timelines", 0), "wdt:P175", {Pires}, provenance={stated_by, date,
  method})` states the node as given and appends the entry
  whose `value` is `{"id": "wd:Q235650"}`; the same pair again, or written
  with the full IRI, raises `'wdt:P175' already has this value`; a `type`
  pair stores the class in `type` and writes its entry `property:
  "rdf:type"`, `value: {"id": "schema:VideoObject"}`; `without_pair` of
  both leaves no `statements` and no `provenance` key; `without_pair` of a
  pair not stated raises `'wdt:P175' does not have this value`.
  `with_candidate(…, "wdt:P2550", {"id": "wd:Q29117946"}, …, basis=["#cpt_2"])`
  leaves the statements as they were and adds one entry (with `basis`,
  without `service`, `match`, `note`); a stated pair raises `'wdt:P2550'
  already has this value; a stated pair is no candidate`; a candidate
  again replaces the entry in place and keeps its `beliefs` (the
  editor's `unlikely` with its note). `with_pair(…, {Clair de lune with
  label}, actor=editor, date="2026-11-20")` states the value with its
  label, keeps the candidate's entry and records the editor's belief
  `"true"` on that date; no candidate is left. `with_belief` of `TILIE`
  `"false"`, then of the editor `"false"`, leaves the pair stated and replaces
  the editor's belief in place: `[editor "false" 2026-11-22, TILIE "false"
  2026-11-21]`; `without_pair` then gives M1 back. A belief in a pair
  never stated creates the entry `{property, value, beliefs}`; `actor`
  without `date` raises `a belief needs a date`, a belief `True`, `False`,
  `1`, `"likely"` or `None` raises `true is no belief: write 'true',
  'false' or 'unlikely'` (the value spelled as JSON spells it, so the
  booleans are told from the strings). A property `performer`
  raises `'performer' is no property: write 'type', a compact IRI or an
  absolute IRI`, a date `2026-02-30` the calendar message. A node's own
  pairs are written the same way at its path. Every function is pure: its
  argument is unchanged, deep-equal, after the call. Each result
  validates.
- **The subjects in subject order.** `subjects` walks every element that
  may carry statements: the manifest, then root by root the timeline, its
  regions in array order and its children, depth first. One manifest of
  two roots proves the order: `a` holding the regions `a1`, the number
  `7` and `a2` and the children `b` (holding the region `b1` and the
  child `c`) and `d`; then `e`. The walk gives exactly `(path, kind, id)`
  for the manifest `()`, `a` `("timelines", 0)`, `a1`
  `("timelines", 0, "regions", 0)`, `a2` `("timelines", 0, "regions", 2)`,
  `b` `("timelines", 0, "children", 0)`, `b1`, `c`
  `("timelines", 0, "children", 0, "children", 0)`, `d`
  `("timelines", 0, "children", 1)`, `e` `("timelines", 1)`: a region
  before the children, the number passed over with its index kept, and
  the groups no subject. A value that is no object yields nothing. The
  JavaScript package's `subjects` gives the same walk.
- **References to elements renamed and dropped.** A reference is the text
  `#` + ID at a reference position (a node's `id`, an entry's `basis` and
  `stated_by` items and its `service`) of any subject, a node at any depth
  of a container or inside an entry's `value` included. One document,
  built on M1 (its context plus `dcterms` and `rdfs`), holds each position
  once: on the root the pair `dcterms:source` `{"id": "#cpt_2"}` with an
  entry whose `basis` is `["#cpt_2",
  "https://example.org/record"]`, the pair `type` `schema:VideoObject`
  with an entry whose `basis` is `["#cpt_2"]` and whose
  `service` is `#cpt_2`, and a candidate `dcterms:isPartOf` `{"id":
  "#cpt_2"}`; on the bundle `rdfs:seeAlso` `[{"id": "#cpt_2"}, {"id":
  "other.yaml#cpt_2"}]`. Renaming `cpt_2` to `cpt_3` gives the document
  with every `#cpt_2` written `#cpt_3`, built by hand, and the reference
  to another manifest (`other.yaml#cpt_2`) left as it is, since only an
  exact `#` + ID is a reference. Dropping `cpt_2` gives, exactly, a root
  stating only `type: ["schema:VideoObject"]` with its one entry left
  without `basis` and `service`, and a bundle stating only the other
  manifest's reference and holding no `provenance`: a value naming the
  element leaves its list, an entry whose value names it leaves
  `provenance`, a `basis` item leaves its list, a `service` naming it is
  deleted, and every list, container and annotation emptied so is deleted;
  a node without `id` whose every pair named the element, and ordered
  values whose every item did, leave their list too, so no value is left
  empty. A second document proves the deeper positions: M1's region states
  `schema:about` a node without `id` holding only `schema:mentions` the
  reference beside one that also holds the label `Intro` (the first
  leaves, the second keeps its label), `schema:hasPart` ordered values of
  two references beside ordered values of a reference and `wd:Q1` (the
  first leave, the second keep `wd:Q1`), and two candidates whose
  `stated_by` hold the reference with and without the editor (the first
  keeps the editor, the second loses `stated_by`; `test_the_actors_of_beliefs_are_renamed_and_dropped`: a belief of `#cpt_2` is renamed with it, and dropped with it, an emptied `beliefs` going too); renamed, it is the same
  document written with `#cpt_3`. Each reference is renamed once:
  `{"cpt_1": "cpt_2", "cpt_2": "cpt_3"}` turns `#cpt_1` into `#cpt_2` and
  leaves it there.
  A rename of an ID nothing names (`cpt_9`) gives a document equal to the
  input. The argument is unchanged in every case.
- **Compact IRIs.** `compact_iri` is proved against the shipped
  catalogue's prefixes and aliases, the ones an editor compacts by: a
  Wikidata item and property take the prefix whose namespace begins them
  (`wd:Q235650`, `wdt:P175`; `wd`'s namespace does not begin a property's
  IRI); `https://schema.org/name` stays unchanged without aliases and
  becomes `schema:name` once the alias reads it as `http://schema.org/`; a
  GND identifier compacts under `https://` only, the namespace the
  catalogue declares (`gnd:119018934`), never under `http://`; a namespace
  ending in `#` compacts (`melod:Work`); and an IRI whose rest after the
  namespace is empty (`http://www.wikidata.org/entity/`), an IRI of no
  declared namespace (`urn:uuid:works/1`) and a MusicBrainz work, whose
  namespace the catalogue does not declare, stay as written. The longest
  namespace wins (a prefix of a nested namespace beats its parent's), a
  tie goes to the code-point-smaller name, and a rest with a character
  outside the compact form (`/`, `:`) leaves the IRI as written.
- **The statement rules.** Every rejection case of a statement rule is the
  shared oracle (`test_validate.py`); the inline documents add what the
  cases cannot show. The messages, exactly: `statements and provenance
  need the manifest's @context`; `'label' is reserved on a timeline` (and
  `the manifest`, `a region`, `a group`); `the ID 'Bass Kick' of an element
  with statements is no IRI fragment` (an ID with `%41` passes, one with
  `%4` or `a|b` does not, one with `é` passes); `'wdtt:P175': the prefix
  'wdtt' is not declared in @context`; `'#cpt_9' names no element of this
  manifest`; `'#clt_2' names an element; a value naming an element holds
  its id alone`; `a statement value is an integer or a string, never a
  float: 1.0`; `'2026-02-30' is no Gregorian calendar date written
  YYYY-MM-DD`; `'http://www.wikidata.org/entity/Q1' already holds belief 0
  of this entry; an actor holds one belief` (the actor `wd:Q1` written
  in full the second time; a belief of `#cpt_9` is `dangling_target`);
  `the entry repeats the pair of entry 0`. The
  reference rule reaches every kind of ID: an element value naming a
  group, a MeasureMap, a nested conversion map, a flow-control element, a
  named timestamp and the manifest itself passes. The four URI schemes and
  `//` IRIs need no prefix. Allowed keys stay allowed: `timelines`,
  `groups`, `statements`, `provenance` and `@context` on the manifest,
  `children`, `regions` on a timeline, `id` everywhere. A manifest without
  statements and without `@context` validates (only the warning). Order:
  one manifest breaking the context rule, a reserved key and a prefix lists
  them in that order through `statement_problems`, and `validate` raises
  the first.
- **Statements alone.** `statement_problems` (no manifest, no problem: a
  value that is no object gives none) checks `@context` and every
  `statements` and `provenance` member as `validate` does, each member's
  first problem at its path, then, where none has one, every problem of
  the statement rules. Its oracle is the shared set: each statement
  rejection case gives exactly one problem, the case's path and code, but
  the two cases without `@context`, whose first problem is the case's and
  whose others are the `iri` problems of their compact IRIs (no prefix is
  declared where no context is); every other case and every fixture gives
  none. A manifest whose other
  parts break every kind of rule (the version `9.9.9`, two roots `a`, the
  unit `beats`, a group naming `ghost`) and whose statements are sound
  gives none; three broken members (the context missing a term, a root's
  statements `{}`, a region's provenance entry with the date infinity, the
  last built in code) give three problems in subject order, the date's
  `finite_number` with the region's ID as owner.
- **Warnings.** `manifest_warnings` validates first, then lists
  `context_absent` (`the manifest has no @context`, at `[]`) for a manifest
  without `@context`, and `bundle_blank` (`the manifest has statements but
  no ID; its subject is a blank node`) at `["statements"]`, or at
  `["provenance"]` where only that is present, for a bundle without `id`;
  a manifest with `@context`, an `id` and statements has none. The shared
  warning cases hold `manifest`, `unknown_keys` and `warnings` and every
  one is asserted exactly (`test_unknown_keys.py`).

## The catalogue

`timetoshare.catalogue` reads the catalogue of identifier systems, verbs and
types; the validators never consult it. The test catalogue `CATALOGUE_TEST`
(`conftest.py`, the same in the JavaScript suite) holds ten prefixes, the
alias `https://schema.org/` → `http://schema.org/`, four systems
(`wikidata` with its thing, `musicbrainz` with `musicbrainz_work`,
`melody`, `fallback`), six verbs (`is_a` first, `same_as`, `performed_by`
in four systems, `conducted_by`, `version_or_edition_of`, `part_of` with an
inverse alternative) and the type `video`. What proves it
(`test_catalogue.py`):

- **The shipped file.** `catalogue/catalogue.yaml` is canonical YAML
  (`dumps(loads(text)) == text`), validates against
  `catalogue/catalogue.schema.json` (whose `$id` is
  `https://timetoalign.github.io/timetoshare/0.2.0/catalogue.schema.json`),
  and `load_catalogue()` reads it once (the same object twice); its first
  verb is `is_a`.
- **Reading.** `read_catalogue(CATALOGUE_TEST)` keeps every member as
  given. Each cross-reference rule raises its exact message, one broken
  copy each: a system, a thing, a verb and a type held twice; the prefix
  `nope` used by a system's `prefixes`, a thing's `prefix`, a thing's
  `lrmoo_class` and a pattern's key, `type` item and nested node `id`; the
  system, thing, verb and type named but not held (`when.value`,
  `when.subject`, a type's `verbs` and `lookup`, a verb's pattern system);
  a thing pattern with two capturing groups, with a named group and with
  an unbalanced parenthesis. Of a copy breaking two rules, the earlier
  rule's message is raised. Only a pattern's keys, `type` items and node
  `id`s are read as IRIs: a copy whose pattern holds the literal constant
  `"nope:bar"` as a value (`schema:roleName: ["nope:bar"]`) is read
  without a problem.
- **Recognising URLs.** `https://www.wikidata.org/wiki/Q235650` gives
  `("wikidata", "wikidata", "Q235650",
  "http://www.wikidata.org/entity/Q235650")`; the MusicBrainz work's URL in
  capitals gives the value and the IRI in lower case; `not a url`, a URL
  with a space and an unknown site give `None`. A thing without an IRI
  template gives its percent-decoded value with underscores and the IRI
  `None` (a copy with an IMSLP thing: `Piano%20Sonata` gives
  `Piano_Sonata`), and an undecodable value `None`.
- **Instantiating.** `performed_by` in `wikidata` of `wd:Q235650` with the
  label gives `[("wdt:P175", {"id": "wd:Q235650", "label": "Maria João
  Pires"})]`; in `musicbrainz` with `slots={"role": "piano"}` the
  contributor node with `"schema:roleName": ["piano"]` and its inner
  `{"id": …}`; without slots `the pattern of 'performed_by' in
  'musicbrainz' needs a value for '?role'`; `is_a` in `fallback` of
  `schema:VideoObject` gives `[("type", "schema:VideoObject")]`; `part_of`
  alternative 1 gives `dcterms:hasPart`, alternative 2 raises `the verb
  'part_of' has 2 patterns in 'fallback'`; an unknown verb `the catalogue
  has no verb 'x'`, a system without a pattern `the verb 'conducted_by' has
  no pattern in 'wikidata'`.
- **Reading a pair as a verb.** Under M2's context: `rel:prf` of
  `{id: viaf:113931950}` is `("performed_by", False)`; a
  `schema:contributor` node typed `schema:OrganizationRole` with the role
  `conductor` is `("conducted_by", False)` (two constants against one),
  with `pianist` `("performed_by", False)`; `dcterms:hasPart` is
  `("part_of", True)`; `dcterms:created` is `None`; `("type",
  "schema:VideoObject")` is `("is_a", False)`;
  `https://schema.org/sameAs` is `("same_as", False)` through the alias; a
  `rel:prf` literal (not a node) is `None`. Under M2's context with `rdf`
  declared, `("rdf:type", "schema:MusicRecording")` is `("is_a", False)`:
  the key `type` of a pattern and `rdf:type` expand alike. A slot `"?"`
  takes a literal, never an ordered value: `("type", {"list":
  ["schema:VideoObject"]})` is `None`, and so is a contributor node whose
  `schema:roleName` holds `{"list": ["pianist"]}` (the `?role` slot
  refuses it, the constant `conductor` is not it). A template's item
  matches where it matches any item of the value's list, and a key's best
  match counts once: in a copy whose verb `about_subject` (`{schema:about:
  [{schema:subjectOf: [{type: [schema:Thing]}]}]}`) precedes `about_named`
  (`{schema:about: [{type: [schema:Thing], schema:name: [A]}]}`), a node
  typed `schema:Thing` named `["B", "A"]` whose `schema:subjectOf` holds
  two nodes typed `schema:Thing` is `("about_named", False)`: two
  constants against one, where counting each matching item would tie and
  give the earlier verb.
- **Rectangles.** `rectangles(CATALOGUE_TEST, M2, ("timelines", 1))` is
  exactly: `is_a` with the two `type` pairs and `wdt:P31`, its things
  `http://schema.org/VideoObject`,
  `https://lod.academy/melod/vocab/ontology#Manifestation`,
  `http://www.wikidata.org/entity/Q98069877`, no label; `performed_by`
  with `rel:prf` and `wdt:P175` (joined by the VIAF cluster both name),
  its things the VIAF, Wikidata and GND IRIs in that order, label `Maria
  João Pires`; `same_as` with the YouTube address. `("timelines", 0)`
  gives `is_a` (the two types), the unread `dcterms:created` (verb `None`,
  no thing), then `version_or_edition_of` with `schema:exampleOfWork` and
  `wdt:P629` (joined by the MusicBrainz work), its things the MusicBrainz,
  Wikidata and GND IRIs, label `Clair de lune`. A subject stating nothing
  gives one empty `is_a` rectangle; two `rel:prf` values naming different
  things give two `performed_by` rectangles. A node without `id` still
  names the things under its `schema:sameAs` and `owl:sameAs`: a `rel:prf`
  node `{schema:sameAs: [{id: viaf:1}], owl:sameAs: [{id: wd:Q1}]}` (which
  no verb reads, since every pattern of `rel:prf` wants an `id`) is one
  rectangle of verb `None` whose things are
  `http://viaf.org/viaf/1` and `http://www.wikidata.org/entity/Q1`.
  Two pairs of one verb read the same way also join where both value
  nodes carry a string `label` and the labels are equal: on M1's root,
  `schema:exampleOfWork` `{id: <the MusicBrainz work>, label: Clair de
  Lune}` and `wdt:P629` `{id: wd:Q29117946, label: Clair de Lune}`, neither
  stating a `sameAs`, are exactly the empty `is_a` and one
  `version_or_edition_of` with both pairs in that order, its things the
  MusicBrainz and the Wikidata IRI, label `Clair de Lune`. Labels compare
  as strings, exactly: with `Clair de lune` on the second the two are two
  `version_or_edition_of` rectangles. An equal label under different verbs
  joins nothing: `rel:prf` `{id: wd:Q1, label: X}` and `wdt:P629` `{id:
  wd:Q2, label: X}` stay `performed_by` and `version_or_edition_of`, apart.
  Two nodes without a label join by no label (the two `rel:prf` values
  above).

## The RDF of the statements

The statement fixtures are YAML-LD documents; their RDF is computed by an
independent processor, PyLD (dev dependency, `decisions/0015`), with the
fixture's base `https://example.org/manifests/<name>.yaml`, the algorithm
`URDNA2015` (RDFC-1.0) and a document loader that refuses every fetch, so
the inline context is all that is read. What proves it (`test_rdf.py`), for
each statement fixture and its twin:

1. its canonical N-Quads equal `fixtures/rdf/0.2.0/<name>.nq`
   (`rdf_expectation`) byte for byte;
2. no IRI of the dataset begins with `p:` for a prefix `p` of the fixture's
   context, and every IRI begins with `http:`, `https:`, `urn:`, `tag:`,
   `mailto:` or `info:`: no compact IRI leaks unexpanded;
3. every predicate is the expanded key of a statements container or a
   node, `rdf:type`, `rdfs:label`, or one of the reification and
   provenance predicates (`rdf:subject`, `rdf:predicate`, `rdf:object`,
   `prov:wasAttributedTo`, `dcterms:date`, `prov:hadPrimarySource`,
   `rdfs:comment` and `NAMESPACE` + `method`, `service`, `match`,
   `beliefs`, `actor`, `belief`): no key of the format gives a triple;
4. for every candidate (an entry whose pair its subject does not state)
   whose subject has an IRI and
   whose value is a thing or a plain literal, the triple subject, property,
   value is absent: a pair that is not stated is asserted nowhere. So that
   the check cannot pass on nothing, the number of entries it checks is
   exact, in both forms: 2 of the DJ set's segment, 3 of the LayerIt
   recording, 2 of the Nielsen record, none of the Op. 106 work (which
   holds no such entry); the candidates it passes over, their value a node
   with more than an `id`, a value object or an ordered value, are 1, 0, 3
   and 0;
5. the number of distinct subjects of `rdf:subject` equals the number of
   provenance entries in the fixture: each entry is one reified statement.

Every other fixture under `fixtures/0.2.0/`, but the six whose regions
are atomic sections (`sonata_exposition`, `volta_run`, `virtual_cards`,
`switched_card`, `virtual_member`, `switched_frame`), yields the empty
dataset, both forms: a manifest without statements says nothing in RDF. `rdf_expectation`
maps a fixture and its twin to the same file.

## One path rule for both validators

Among the diagnostic leaves of every violation, a validator reports the one
with the deepest instance path; among leaves equally deep, the one whose
path comes first compared element by element (indices by number, keys by
code point); among leaves at one path, the first the walk reports, which
visits the schemas applied at a place in the order the document writes
their keywords. The order of the paths decides between two places, never
the order of a report, so the result does not depend on how the walk
iterates the members of an `additionalProperties` (`jsonschema` iterates a
set, whose order changes with `PYTHONHASHSEED`). A
discriminated `oneOf` contributes only the candidate whose tag `const` equals
the instance's tag value (resolved through `$ref`), and is itself the
reported error when no candidate carries that value. The shared rejections
pin it where it matters: a negative fraction length reports its numerator
(`length/0`), a zero denominator the denominator (`length/1`), a negative
`actual_length` the row member, a negative `qstamp` pair its numerator, an
unknown conversion-map type the map, a missing `x_values` the `TableMap`, a
measure view's `source_unit` other than `quarters` the unit, `targets` on a
jump target or `ends` on a barline the member, a jump without `targets`
the element.

The cases of several problems, `fixtures/precedence/0.2.0/cases.yaml`,
pin the rule where a manifest breaks it twice (`test_validate.py`). Each
names a fixture, the members it sets and the code, path and message
reported, which both packages give: two declarations refused at one depth
(`styles/alpha` before `styles/zeta`), two prefixes of `@context` (`aa`
before `zz`), a deeper refusal in a later root before a shallower one in
an earlier root, two members of one timeline (`is_segment_line` before
`locked`), two conversion maps that are no objects (index 1 before 3),
and one number type refused by the list of number types and by its
unit's list at one path (the list of number types, which the walk applies
first). Before the rule broke ties by path, the first two depended on the
hash seed and the fourth went to `locked`; the cases are run in three
interpreters started with `PYTHONHASHSEED` 1, 2 and 3, which report the
same.

Three shapes of the schema are worded by the package, so a refusal says
what to write; the path and the code stay the path rule's and `schema`.

1. A `oneOf` (or `anyOf`) whose every branch is a `const` is one leaf,
   never its branches, and its message lists the admitted constants in the
   schema's order as an `enum`'s does: `'furlongs' is not one of
   ['number', 'floating_measures', …, 'user_units']` at a timeline's `unit`.
2. A member whose schema admits no value (`not: {}` or `false`) reads
   `the key 'targets' is not admitted here`.
3. A `not` refusing a pattern, or any of several patterns and words, names
   the value, the part of it the refused branch finds (the first branch
   that finds one) and what is not admitted, in the words of the schema's
   description where it has them: a character is named as itself where it
   is printable and no whitespace, else by its code point. `'#a\tb' holds
   U+0009: no control character (U+0000 to U+001F) is admitted here` for an
   ID (and for every other string the schema closes against control
   characters: an order entry, a paint, a dash array, a media type, a
   digest); an ID that is one of the two words of its `not`, the
   sentinels' strings, reads `'NOMATCH_SENTINEL' is reserved for a
   sentinel` for `#NOMATCH_SENTINEL`; `'match claims.parquet' holds U+0020: no whitespace and no
   control character is admitted here` for an IRI or IRI reference, a
   prefix's IRI included; `'_:b0' begins with '_:': no blank node
   identifier is admitted here` and `'@id' begins with '@': no keyword is
   admitted here` for an IRI reference; `'en_GB' holds '_': only A-Z, a-z,
   0-9 and '-' are admitted here` for a language tag; for a prefix name
   `'my.wd' holds '.': only A-Z, a-z, 0-9, '_' and '-' are admitted here`
   and `'https' is not admitted here: it names a key of the manifest's
   elements or a URI scheme the format reads as such`. A prefix name is
   reached only as a key of `@context`, where the format's own terms are
   the first branch, so `validate` reports the term list there; the prefix
   name's two words are proven on the definition itself.

Every other error keeps the schema library's message, a `not` requiring
members included; the JavaScript package spells those messages as
`jsonschema` 4.26 does, each value as Python's `repr` spells it. `test_validate.py` proves it on every place of the
schema with one of the three shapes, and a census of the schema fails when
a place is added without a case: the time unit; the four forbidden members
of a flow-control element (`manifestation` and `ends` on a jump, `targets`
on every other role, `ends` on every role but a break, seven cases);
and the thirteen `not` places (an ID with each of its two branches, an order entry, a paint, a dash array,
the elision depths and display of a declaration, a resource's media type and its digest, an IRI, an IRI reference with each
of its three branches, a prefix's IRI, a language tag, a prefix name with
each of its two branches), each message stated literally, at the path the
walk reports.

## The canonical order

Every array whose order carries no meaning has one order: `timelines` by ID;
in every timeline `children` by offset then ID, `conversion_maps` by ID,
`regions` by start, end, ID, `flow_control` by coordinate then ID, a jump's
`targets` by place (the destination without a place, then `by` by value,
then `to` by ID); `groups`
by ID and `members` by code point; `measure_maps`, `flow_maps` and
`virtual_timelines` by ID, a FlowMap's `chunks` kept (section "Flow");
`graphical.timestamps` by timeline (code point), then coordinate, then ID;
`graphical.elisions` by timeline, then start, then ID (section "Elisions").
The arrays of statements keep their order: the values of a pair, an
ordered list's items and the entries of `provenance`.
Values compare exactly; strings by code point. The timestamps
`timestamp_4` on `b` at `[1, 1]`, `timestamp_3` and `timestamp_2` on `a` at
`[3, 2]` and `timestamp_1` on `a` at `[5, 1]` come out `timestamp_2`,
`timestamp_3`, `timestamp_1`, `timestamp_4`; a timestamp's `display` is
written in the order of `TIMESTAMP_DISPLAY` (`["cross_section",
"coordinate", "id", "name", "wedge"]` comes out `["wedge", "name", "id",
"coordinate", "cross_section"]`, a word the schema does not know after
them by code point, `["zeta", "alpha", "wedge"]` as `["wedge", "alpha",
"zeta"]`, any other value last in its given order, so ordering a refused
manifest never fails), and a timestamp's coordinate
is respelled on its timeline's axis (`[6.0, 1]` on quarters as `[6, 1]`,
`2` on seconds as `2.0`), while one naming no timeline keeps its spelling
(`2` stays `2`). What proves it
(`test_manifest.py`): an inline manifest with ties at every level, own-axis
values given as bare ints, floats and pairs mixed (`[5, 8]` before `[2, 1]`,
`0.625` equal to `[5, 8]` and tied by ID), IDs where code-point and UTF-16
order disagree (`ﬀ` before `😀`), yields the literally stated ID sequences
and validates; children `z` (1), `m` (1), `b` (`[5, 8]`), `a` (`[2, 3]`) come
out `b`, `a`, `m`, `z`; roots, groups, members and MeasureMaps (`mﬀ`,
`mb`, `ma` come out `ma`, `mb`, `mﬀ`) sorted while
`graphical.order` keeps its order; the input is unchanged; a value without a
`timelines` array is copied as it is; a member that is not a string and two
regions without `start` are refused (`cannot put … in canonical order`).

The respelling and the failures are pinned by inline values besides
(`test_serialization.py`): an unknown `unit` (`furlongs`), a missing one and
one that is not a string, and a `number_type` that is not one of the three
(`"decimal"`, `null`, `1`), each leave `length`, `offset`, a region and a
flow-control coordinate as given, while a known unit without `number_type`
takes its default (`2.0` on ticks written `2`); a child in quarters under a
root of unknown unit has its `length` `[4, 8]` written `[1, 2]` and its
`offset` `[4, 8]` as given; a child's `offset` follows its parent's number
type (`2` under seconds written `2.0` while the child is in ticks); a
timestamp naming a timeline twice or no timeline keeps its coordinate (`2`
on a float axis stays `2`). A writer refuses with `ValueError` (`cannot put
… in canonical order`) each of: an entry of `timelines` that is not an
object, a child without `offset`, a region whose `start` is a string, a
timeline whose `id` is an integer, a timestamp whose `timeline` is an
integer, a group member that is an integer, a coordinate `[1, 0]`, `[1, 2,
3]` and `true`; a NaN offset is refused as a non-finite number, checked
before any ordering; `{"timelines": ["b", "a"]}` is a manifest and refused;
a member that holds no array (`children: "x"`, `groups: "g"`) is written as
given. Entries that tie on every member they are ordered by keep their given
order (two timelines `t` given `second` then `first` by name come out
`second`, `first`).

## The serializations

`dumps(value, serialization)` writes canonical YAML (`"yaml"`, the
default), pretty JSON (`"json"`) and RFC 8785 JSON (`"jcs"`); `loads` reads
any text and `serialization_of` names a text's serialization. They live in
`timetoshare.serialization`. What proves them (`test_serialization.py`):

- **The shared cases.** Every file of `fixtures/serializations/` is walked
  as that directory's README states, read as bytes and decoded as UTF-8
  with a leading U+FEFF kept. For every case, `canonical.yaml` and
  `pretty.json` read to one value V, kind for kind, which is written byte
  for byte as `canonical.yaml`, `pretty.json` and `rfc8785.json`, and `dumps(V, "jcs")` raises `ValueError` where
  `rfc8785.json` is absent; `rfc8785.json` reads to V with every float
  whose RFC 8785 spelling has neither `.` nor an exponent replaced by the
  integer it equals; each text read and written again in its own
  serialization gives its own bytes; for the five manifest cases the value
  read from `rfc8785.json` is written as `canonical.yaml`. Every reading
  written in canonical YAML gives its `.expected.yaml`, and in RFC 8785
  JSON its `.expected.rfc8785.json` where one exists; every refusal raises
  `ValueError`; every writer refusal raises `ValueError` in exactly the
  serializations the directory's README names; `serialization_of` gives
  the README's name for every file, and never raises. No reading whose
  expected value is a manifest (an object with a `timelines` array)
  holds a child, at any depth, of another unit or number type than its
  parent's, each the declared one or the unit's default, a shape both
  validators refuse; `manifest_fraction_reduced` and
  `manifest_number_type_missing` are among them. Other rules a reading's
  manifest may break, since readings test the reading of a text, not a
  manifest's validity. Values are compared
  kind for kind (an integer equals only an integer, `-0.0` differs from
  `0.0`). No case is skipped.
- **The test's tables name exactly their files.** Each table the test keeps
  beside the cases equals, as a set, the files it describes, so a case
  added or removed without its entry fails: the writer refusals' table
  names every file of `refusals-writing/` and no other; the manifest cases
  are the cases whose value is an object with a `timelines` array; the
  cases whose canonical YAML is a JSON text are those the standard
  library's JSON reader reads; the refusals written as YAML and read as
  JSON are the `.yaml` refusals whose first character other than JSON
  whitespace is `{` or `[`. `serialization_of` of an `.expected.yaml` is
  `"json"` exactly where the standard library's JSON reader reads the text.
- **The YAML reader.** Plain scalars resolve by the core schema: `no` and
  `y` are strings, `2026-11-17`, `1:20`, `1_000` and `0b101` strings,
  `1e-05` a float, `2` an integer, `0x1F` 31, `0o17` 15, `010` 10, `~` and an
  empty value null, `True` a boolean; an integer of 2^70 stays exact; an
  empty text, one of comments only, one of blank lines and `---` alone read
  as null; `"😀"` is U+1F600. Refused, with exactly the stated message
  naming the line and column: a repeated key, an anchor, an alias, an
  integer key and a collection key; every tag, whatever it names, as `a
  tag is not read` at the tag: `!!timestamp`, `!!binary`, `!!set`,
  `!!omap`, `!!str 1` and `!!float 2` (whose values would be in the format),
  `!!str` and `!!int` on a sequence, the non-specific `!` and the local
  `!local`; `.inf`, `1e309`, the escape `\ud800`, U+007F and a lone
  surrogate written as itself (characters outside YAML's printable set)
  and a second document.
- **Canonical YAML is plain YAML.** Every canonical YAML text of the
  fixtures (every manifest under `fixtures/0.2.0/`, every case's
  `canonical.yaml` and every reading's `.expected.yaml`) is read by
  PyYAML's unmodified `yaml.safe_load`, a YAML 1.1 reader, to the value
  `loads` reads, kind for kind (an integer equals only an integer, a
  boolean only a boolean, `-0.0` differs from `0.0`). So a reader that
  knows nothing of the format's rules reads canonical YAML as the format
  does. The texts are found by walking those directories, so a fixture
  added there is checked without a change to the test.
- **The nesting limit.** A scalar has depth 0, an object or array 1 more
  than its deepest member (an empty one 1). Both readers refuse a text whose
  value would be deeper than 256 with the `ValueError` `collections nest
  deeper than 256 levels at line L, column C`, at the first character of the
  first collection at depth 257. The readers build collections without
  recursion and count them as they open, so the place is a property of the
  text alone: a text nested 100,000 deep is refused where one nested 257 deep
  is, never by Python's recursion limit. Pinned positions: JSON `[` 257
  times then `]` 257 times, and `[` 100,000 times unclosed, at line 1,
  column 257; `{"a":` 257 times, then `1` and `}` 257 times, at column
  1281; YAML `- ` 257 times then `1`, and `- ` 100,000 times then `1`, at
  line 1, column 513 (block sequences); 257 block sequences in canonical
  layout (`-` alone on a line, each two columns further, the last `- 1`)
  at line 257, column 513; 257 block mappings (`k:` on a line, each two
  columns further, the last `k: 1`) at line 257, column 513; `a: ` then `[`
  256 times and `]` 256 times (flow sequences in a block mapping) at line 1,
  column 259; `{a: ` 257 times, then `1` and `}` 257 times, read as YAML
  after a comment line, at line 2, column 1025 (flow mappings); and the
  shared refusals `json_depth_257.json` at line 1, column 257 and
  `yaml_depth_257.yaml` at line 128, column 385. Every text nested 257
  deep, made one level shallower, is read, to a value nested 256 deep.
  The writers refuse a value deeper than 256 with the `ValueError` `a value
  nested deeper than 256 levels cannot be written` in every serialization:
  the array nested 257 deep (built in memory: no text a reader reads holds
  it), an object whose member holds an array 256 deep, and the array nested
  257 deep around a NaN (the depth is checked before the numbers); a list
  holding itself is refused the same way. The array nested 256 deep is
  written in every serialization and reads back equal, its canonical YAML
  being `readings/json_depth_256.expected.yaml` and its RFC 8785 JSON `[`
  256 times then `]` 256 times.
- **The first fault.** A text holding several faults is refused for the
  first in document order, at the token that offends, by both readers; the
  place names the fault, so a test that pins it proves the order. The
  YAML reader first looks for a character outside YAML's printable set and
  refuses it where it stands, before the text is parsed; it then checks
  each node as the parser's event for it arrives, a key before its value
  (an alias, an anchor, a tag, a key being a string, a key not repeating,
  depth, value), and stops there, except that a parser reading one token
  ahead may meet a syntax error there first: `- &a "\q"` is refused here
  at the bad escape (1, 8) and by TypeScript at the anchor (1, 3), so its
  test asserts only the `ValueError`, and no shared refusal pins such a
  pair; an anchor or a tag is placed at the node's first property and
  named by it, an empty key right after its `?`, every other fault of a
  node at its first character; the
  JSON reader refuses where it stands when it meets a fault, the grammar's
  included. Pinned by message: in YAML, a repeated key, `!foo`, `!!map
  [1]`, the key `1` and the escape `\ud800` each before a flow sequence at
  depth 257 are refused for themselves, and that depth (line 1, column
  259) before a repeated key or `!foo`; `!foo` before a repeated key and a
  repeated key before `!foo`, each for the first; U+0001 after `!foo`,
  before a repeated key, after a repeated key, inside a key that would
  repeat (`x: {a: 1, a` U+0001 `: 2}`, column 12) and after a float too
  large (`x: [1, 1e99999` U+0001 `]`, column 15), each for the character;
  a repeated key before a second document for the key, and a second
  document before a repeated key in it for the document; `a: &x !local 1`
  for the anchor, `a: !local &x 1` and `a: !!str &x 1` for the tag, the
  property written first, all at column 4; `.inf: 1`
  for a key that is not a string, never for the infinity; `!!binary aGk=:
  1` for the tag before the key. In
  JSON, `[1e999, }` and `[1e999] 2` for the number at column 2,
  `["\ud800", }` for the surrogate at column 3, a repeated key before a
  missing key or extra data for the key, `1e999` as the value of a key
  that repeats later for the number, a lone surrogate before 300 unclosed
  `[` for the surrogate, a collection at depth 257 before a repeated key
  for the depth, and U+0001 in a string before `1e999` for the character.
  A JSON string is refused at the token that offends: an invalid escape
  (`\x`, `\u12G4`) at its backslash, a control character where it stands,
  an unterminated string at the end of the text; a high-surrogate escape
  not followed by a low-surrogate escape (an invalid escape, the end, a
  control character, an escaped quote or a low surrogate standing as
  itself follows) is lone at its own escape. Every shared refusal whose
  place the cases' README gives is refused there (the test's table of
  places): the two depth texts; the six `json_lone_surrogate_*` texts, one of them
  (`json_lone_surrogate_before_syntax_error`) also among the fifteen
  `*_before_*` texts; `yaml_anchor` and `yaml_alias` at the `&`; the nine
  `yaml_tag_*` texts at the tag (`yaml_tag_before_anchor` also among the
  `*_before_*` texts); `yaml_special_character_in_key` at the character;
  and `yaml_key_empty_trailing_space` (`?`, a space, a line feed, `: 1`)
  right after the `?` at (1, 2).
- **Columns count code points.** In both readers a character above U+FFFF
  counts once: the YAML anchor in `"😀": &x 1` is refused at column 6, and
  the escape `\ud800` in the JSON text `["😀", "\ud800"]` at column 8 (in
  UTF-16 code units they would be 7 and 9); among the shared refusals
  `json_astral_before_duplicate_key` and `yaml_astral_before_infinity` at
  column 10 (11 in UTF-16 code units).
- **The float spelling.** The README's examples: `2.0`, `123.25`, `0.1`,
  `0.0001`, `1.0e-05`, `-2.5e-07`, `1000000000000000.0`, `1.0e+16`,
  `1.5e+16`, `5.0e-324`, `1.7976931348623157e+308`, `-0.0`, `5.0e-05` and
  `1.0e+21`; in RFC 8785 JSON `2`, `1700000000`, `1503.25`, `0.00001`,
  `1e+21`, `1e-7`, `1.5e-10`, `0.00005` and `0` for both zeros.
- **The writers' refusals.** NaN, infinity and negative infinity, a lone
  surrogate in a string and in a key raise `ValueError` in every
  serialization; a key of 1024 UTF-16 code units in canonical YAML form
  (1024 plain letters; 1021 letters and a space, quoted; 511 tabs, each
  escaped `\t`, quoted; 511 characters above U+FFFF, quoted) is written, one
  of 1025 (1025 letters; 1022 letters and a space; 511 tabs and a letter;
  511 characters above U+FFFF and a letter) refused in every serialization,
  nested in an object as at the top level; in RFC 8785 JSON the integers ±2^53 and 2^64 and the
  integral floats 2^53, −10^16, 10^20 and 10^21 − 2^17 are refused,
  ±(2^53 − 1) and 10^21 written. A tuple, a set, a Fraction and an object
  with an integer key raise `TypeError`; an unknown serialization name
  raises `ValueError`.
- **The JSON reader.** `0.5`, `2.0`, `123456789012345678`, `-0` (the
  integer 0), `-0.0` (a negative float zero) and `1E5` (a float) keep their
  kinds, an integer beyond 64 bits stays exact; `[1,]`, `{1: 2}`, `[1] 2`,
  `{"a": NaN}`, `[-Infinity]` and `1e400` (a JSON text whose number rounds
  to an infinity) raise `ValueError`; `""`, `01`, `nul`, `NaN` and
  `-Infinity` are no JSON texts and open with neither `{` nor `[`, so they
  are read as YAML, to null, 1 and the strings `nul`, `NaN` and `-Infinity`; `{"a": 1, "a": 2}`, `["\ud800"]` and a string holding U+D800 as
  itself raise `ValueError` naming the line and column, the repeated key
  at its quote and the surrogate at its escape or where it stands. A single U+FEFF
  before a JSON text is removed; `serialization_of` gives `"json"` for `{}`
  after a U+FEFF, `"jcs"` for `{}`, `"yaml"` for `a: 1` and `"json"` for
  `{"a": "\ud800"}` and for `[1,` and never raises.
- **Every standard file.** The font metrics are reproduced byte for byte by
  `dumps(loads(text), serialization="json")`; the catalogue, every fixture,
  rejection case and warning case are written in canonical YAML by `dumps`.

## IDs in a file

A manifest file writes every ID as `#` followed by the ID; in memory an ID
is bare. `to_file_id` adds one `#`, `from_file_id` strips exactly one
(`##x` is the bare ID `#x`) and raises `FileIdError`, a `ValueError` with an
empty `path`, for a text without the leading `#` and for `#` alone; the
messages are pinned exactly (`test_ids.py`). `with_file_ids` and
`with_bare_ids` convert a whole manifest, driven by one table of ID positions
(`ID_POSITIONS`, by definition and member) and one table of where each
definition is held (`CONTAINERS`). What proves them:

- **Every position, nothing else.** One bare manifest names an ID at every
  position of the table once (the manifest's own, a root, a child, a
  `ChainMap` with a nested `LinearMap` and a nested measure view naming its
  MeasureMap, a `CombinationMap` holding a map by output name, a region, a
  jump target, a jump with a destination `to` it and one with an `after`
  naming a second jump and its `to`, a break whose `ends.after` names the
  first, a FlowMap with its timeline and three chunk IDs around a gap
  (kept as it is), a virtual timeline with its `map`, `timeline` and
  `through`, a group, a MeasureMap, a
  timeline's and a group's `graphical.order` entry, a rule with an address
  and `within`, a named timestamp, an elision), plus the unknown key `extra: score` on
  the root, a `meta` holding `id: untouched`, the bundle's statement
  naming `#score` and the region's statement naming `#verse` with its
  provenance's `basis` `#intro` and `other.yaml#score`; `with_file_ids`
  gives exactly the hand-written file form and `with_bare_ids` gives the
  bare manifest back. The unknown key, `meta`, the band words of the
  timeline's order entry, `@context` and every IRI of the statements and
  their provenance stay as written in both directions: a reference to an
  element is an IRI, the same in a file and in memory.
- **Order and numbers kept.** Keys keep their order at every level, an
  order key renamed in place included (`#score` before `#g`); a float `2.0`
  stays a float, an integer an integer. The JavaScript suite adds an order
  key that reads as an array index (`#2` → `2`), which JavaScript would
  otherwise move first.
- **Pure.** Changing the result leaves the input unchanged, and converting
  changes neither input.
- **Refusals where they stand.** `with_bare_ids` raises `FileIdError` with
  the exact path and message for a timeline ID without `#`, a group member
  without `#`, a member ID without `#` in a group's order entry, a
  and a timestamp's `timeline` that is `#` alone.
- **The tables are the schema's.** The rows of `ID_POSITIONS` are exactly
  the positions where the schema types a value as `#/$defs/Id`, each shape
  matching how: `id` the member itself, `ids` its items, `order` its property
  names. The `order` shape covers one
  more thing the schema cannot type: the values of a group's entry, which
  the schema types as `Order` because a timeline's entry holds band words.
  `CONTAINERS` is exactly the set of members through which a definition
  refers (by `$ref`, items or `additionalProperties`) to a definition that
  holds an ID position or reaches one (through its members, its `allOf`
  bases or its `oneOf` branches), and a conversion map carries the members
  of its type's definition and of every base up to `MapBase`, the measure
  views being exactly the map types whose `allOf` is `MeasureView`. A
  future schema ID cannot be missed.
- **The validators read the file form.** The schema types an ID as `#`
  followed by at least one character, so a timeline ID written bare
  (`id_without_hash`) and a group member written bare
  (`reference_without_hash`) are refused by the schema where they stand.
  The `#` rule is the one reported whatever the length: a timeline ID
  written `s` (`id_without_hash_short`), `score` or `#` alone is refused at
  `timelines/0/id` with the same schema message, `'s' does not match
  '^#[\\s\\S]'` for the first, never one about the length. The rule
  reads any character after the `#` alike in both languages, so the ID
  `#\u2028` (a line separator, no control character) validates.
  Where the schema cannot tell, `validate` refuses with code `schema`, the
  path and `FileIdError`'s message: a member written bare in a group's
  order entry; the same manifest with it written `#` validates.
  `statement_problems` gives none for the manifest whose bare member stands
  in the group's order entry, outside the statements, nor for one whose
  root's ID is written bare (read as it stands, so the bundle's statement
  naming `#score` resolves), and one `dangling_target` once the statement
  names `#ghost`. The
  schema check and the search for unknown keys report paths through
  `graphical.order` with the key as written (`#score`); every other check,
  the finite rule included, reads the bare IDs and quotes them bare, so
  every message of a shared case is the one it was before IDs were written
  `#`.
- **Inline documents.** The suite's inline documents write IDs bare, as in
  memory; the helpers of `conftest.py` (`validate`, `unknown_keys`,
  `manifest_warnings`, `identity_problems`) hand
  the checks their file form through `with_file_ids`, which the cases above
  prove. The shared rejection and warning cases and the fixtures are files
  and go to the package's functions as they are.
- **Every fixture round-trips.** For every fixture, `with_file_ids(
  with_bare_ids(fixture)) == fixture`: the fixtures are written in the file
  form and every ID in them converts.

## Minted ID vectors

The package mints no ID; it ships `fixtures/ids/minted_ids.json`, the test
vectors that tools minting IDs check their minters against
(`test_minted_ids.py`; the algorithm is stated in the file and in
`scripts/emit_id_vectors.py`, its reference implementation). The file is
read where a consumer reads it, at `data_root() / "fixtures" / "ids" /
"minted_ids.json"`, so the test fails if the package stops finding it.

- **The file is the script's output.** The test loads the script, builds the
  vectors in memory and renders them, and the text equals the file byte for
  byte: a hand edit of the file, or a change of the script left unemitted,
  fails.
- **`mix64` is SplitMix64's finalizer.** Independently of the file, the
  script's `mix64` reproduces the published SplitMix64 outputs of the seed
  1234567, whose generator steps its state by `0x9e3779b97f4a7c15` and
  returns the finalizer of the new state: 6457827717110365317,
  3203168211198807973, 9817491932198370423, 4593380528125082431,
  16408922859458223821. The script's own arithmetic therefore cannot be
  what the file is checked against alone. Each `{input, output}` pair of the
  file is inverted by the inverse of the finalizer written in the test
  (each xorshift undone, each product multiplied by its inverse modulo
  2^64), giving back the input, so the pairs are those of a bijection.
- **The content is what the file promises.** `mix64` holds the inputs 0, 1,
  2, 42, 2^63, 2^64 − 1 and 0x0123456789abcdef, in that order;
  `minters` the seeds 0, 1, 42, 81985529216486895, 18446744073709551615
  and −1, each at the lengths 13, 10 and 7 in that order, each with the
  prefixes `note`, `clt`, `note`, `claim`, `score:clt` and five IDs;
  `later_ids` the seed 42 at the three lengths, the prefix `note` and the
  counter 1000. Seeds, inputs and outputs are decimal strings; lengths and
  counters are integers.
- **Each ID decodes to its counter.** For every ID, the part before the
  last `_` is its prefix, and the suffix matches `^[0-9a-z]{L}$` with its
  entry's L (the whole ID `^.+_[0-9a-z]{L}$`); read in base 36, the suffix
  equals `mix64(mix64(seed mod 2^64) + k) mod 36^L`, computed with the
  script's `mix64` that the point above checks, k being the ID's place in
  its entry (1 to 5) or the entry's `counter`; this decoding checks the
  base-36 digits and the padding apart from the script's `base36`.
- **Pinned values.** So that the script and the file cannot change
  together unnoticed, the test also states three values literally: the
  output of `mix64` of 0 is 0, the first ID of the seed 42 at length 13 is
  `note_26vx31m84xkac`, and the ID at counter 1000 of the seed 42 at
  length 13 is `note_3cu6welhit32x`.
- **A seed is taken modulo 2^64.** The entries of the seed −1 hold the same
  IDs as those of 18446744073709551615 at each length.
- **The counter is shared by the prefixes.** In every entry of `minters`,
  the two `note` IDs (the first and the third) differ.

## Manifest files

`file_form(text)` gives a `FileForm`: whether the manifest is `minimal`,
whether it holds its `styling` (the top-level `graphical` key) and its
`serialization` (`serialization_of`). `dumps_file(value, form)` drops a
top-level `graphical` unless `form.styling`, writes the minimal form if
`form.minimal`, else the complete form, and writes it in
`form.serialization`. They live in `timetoshare.files`. The form is
minimal when `minimal(value)` and `value` write the same canonical YAML,
the equality the twin law of the fixtures uses: a key stated at its
default, recognized by exact value (a `LinearMap`'s `scalar: 1.0` is the
default `1`), makes a text not minimal, and the order canonical order sorts does
not count. What proves them (`test_files.py`):

- **Every fixture comes back byte for byte.** For every fixture and every
  minimal twin under `fixtures/0.2.0/` (bundles and groups included), its
  value V and V without `graphical` are each written in all three
  serializations; every such text T is read back as the form its name
  states, `FileForm(minimal=<is a twin>, styling=<"graphical" in T's value>,
  serialization=<the serialization T was written in>)`, and
  `dumps_file(loads(T), file_form(T))` gives T byte for byte. A fixture
  is written complete and a twin minimal, so a test of the form cannot be
  passed by a reader that guesses one form for every file.
- **The cases of `fixtures/file_forms/`.** Each text there that is not
  named `*.expected.*` is read to the exact form the test's table states,
  and written back with `dumps_file` gives the bytes of its
  `<name>.expected.<ext>`; the table names exactly the texts of the
  directory. The expected texts are written by hand from the fixtures,
  never by `dumps`: `neither.yaml` holds `bare`'s minimal twin with two of
  its defaults written (`groups: []` and the root's `locked: false`), so
  it is neither minimal nor complete and reads as `minimal=False`; it
  comes back as the complete form, `bare.yaml` itself. `one_line.json` is
  that twin without `graphical`, on one line with a space after each
  separator, so pretty JSON but no RFC 8785 JSON; it comes back in the
  layout of pretty JSON. `crlf.yaml` is the twin in canonical YAML with
  every line feed preceded by a carriage return; it comes back with line
  feeds alone, the twin's own bytes. Two RFC 8785 JSON texts pin what
  that serialization cannot express: it writes an integral float as an
  integer, so a timeline on a float axis (`seconds`, no `number_type`) whose
  `length` 8.0, root `offset` 0.0 and region `start` 0.0 are written `8`
  and `0` is read with integers there. `jcs_minimal.json` is minimal (a
  LinearMap with `scalar` 0.5 and its default `offset` left out); it reads
  as `minimal=True` and comes back as its own bytes, because a key is left
  out by `minimal` when its exact value equals the default, which RFC 8785
  JSON keeps, and the canonical YAML that compares the forms respells every
  own-axis value by the declared number type on both sides. Written in
  canonical YAML instead, its value gives `length: 8.0`, `offset: 0.0` and
  `start: 0.0` (the exact text is pinned in the test, after the
  `@context` block with which `bare`'s twin opens). Every text carries the
  format's `@context`, as every fixture does.
  `jcs_float_default.json` is the same manifest with the LinearMap's
  default `offset` stated (0.0, written `0`) and every other default left
  out: it reads as `minimal=False`, as a YAML text stating `offset: 0.0`
  would, and comes back as the complete form in RFC 8785 JSON.
- **The shape.** `FileForm` is frozen (assigning a field raises
  `FrozenInstanceError`) and equal by its three fields; `SERIALIZATIONS`
  is `("yaml", "json", "jcs")`. `FileForm`, `file_form`, `dumps_file` and
  `SERIALIZATIONS` are exported from the package root.

## The fixture set

The fixtures under `fixtures/0.2.0/` are emitted by timetoalign, never
written by hand, those under `flow/` and the flow control of every other
included (section "Flow"; `test_fixtures.py`). For every fixture: `validate` accepts
it, `unknown_keys` and `manifest_warnings` list nothing (every fixture
states the format's `@context`), `dumps` reproduces it, and the two round
trips of `complete` and `minimal` hold. The folders are `.`, `bundles`,
`flow`, `groups` and `statements`, 214 files (`test_files.py`); the four statement
fixtures `op106_work`, `layerit_recording`, `djset_segment` and
`nielsen_record` with their twins are read to RDF as the section "The RDF
of the statements" says. `fixture_paths()` lists every
`*.yaml` under `fixtures/0.2.0/` except the drawings. The styled fixtures
`styled__score.yaml` and `styled__performance.yaml` carry the literally
stated `graphical` objects (20 and 3 rules, and the score's band order
with its markers band above its line and its map below), the
score's elements addressed by `Address` objects (`{"id": "intro", "part":
["label"]}`, `{"id": "da-capo", "part": ["label"]}`, and the wedge
`{"id": "timestamp_2"}` and coordinate label `{"id": "timestamp_2", "part":
["coordinate"]}` of its timestamp `length`); the thirteen drawn items of the
score, the wedges and coordinate labels of its timestamps `origin` and
`length` among them, resolve, by the
cascade ranking of `docs/drawing.md`, to thirteen distinct colours, and no
rule hides anything but child `a`.

The case accessors `fixture_paths`, `rdf_expectation`, `rejection_paths`,
`rejection_case`, `RejectionCase` and `warning_paths` are defined in `timetoshare.fixtures`,
and the top level exports those same objects; `timetoshare.validate`
defines none of them, so each has one home.

Two properties of the emitted set are pinned because a hand-written document
cannot prove that the emitter produces them:

- **A timeline in several groups.** `bundles/bundle_shared_member.yaml` and
  its twin hold the groups `g1` with the members `t`, `u` and `g2` with `t`,
  `v`; besides passing the checks above, `identity_problems` finds nothing
  in either form, so a member shared between groups, as the emitter writes
  it, passes both the schema and the identity rules.
- **Free IDs.** `bundles/bundle_free_ids.yaml` holds the roots
  `https://example.org/piece/score` and `perf/take 2`, their regions
  `https://example.org/piece/score#exposition` and `take 2/intro`, one
  group holding both roots, and one rule selecting `{"id": "take
  2/intro"}`, each ID written as given, so the emitter keeps an ID holding
  a slash, a space, a colon or a `#` verbatim.
- **Named timestamps.** `timestamps.yaml` and its twin hold the three
  timestamps `timestamp_1` (`Downbeat`, `[3, 2]` on the root `clt_1`),
  `timestamp_2` (`Climax`, `[6, 1]` on `clt_1`) and `timestamp_3` (`Entry`,
  `[1, 1]` on the child `clt_2`), in that canonical order, and no
  rule. In the fixture `timestamp_1` states the default `display`
  `["wedge", "name", "cross_section"]`, `timestamp_2` `["wedge", "name"]`
  and `timestamp_3` all five words in canonical order; the twin leaves out
  only `timestamp_1`'s `display`; every timestamp of the fixture states
  `matchstamp: false` and `groupstamp: false`, the twin neither.
  `identity_problems` finds nothing in
  either form, so the emitter carries the named timestamps through the
  library with their `display` in the format's form.
- **Origin and length.** Every fixture that a drawing under `drawings/`
  draws, but `timestamps`, names the zero of each root it draws (each
  ungrouped root and each group member) `origin` and, where the root's
  length is known, its length `length`, each with the `display` `["wedge",
  "coordinate"]`, in canonical order with the smallest free
  `timestamp_<N>`. Three fixtures pin it with their exact timestamps, in
  both forms: `label_float_rounding` (`origin` `0.0` and `length`
  `312.48979591836735` on `take`, `timestamp_1` and `timestamp_2`),
  `bundles/bundle_ungrouped` (three roots, minted by root ID: `pages` 0
  and 5262, `recording` 0 and 441000, `score` `[0, 1]` and `[16, 1]`,
  `timestamp_1` to `timestamp_6`) and `groups/group_unknown_length` (the
  member `performance` of unknown length has `origin` `0.0` alone,
  `timestamp_1`, before `score`'s `[0, 1]` and `[12, 1]`, `timestamp_2`
  and `timestamp_3`). No corpus fixture carries a named timestamp.
- **A band order of a subset.** `map_band_order_subset.yaml` and its
  twin hold the timelines of `map` (the root `melody` holding `phrase`)
  with the one band order `{"melody": ["markers", "line"]}`, and pass
  `validate` and `identity_problems`, so the emitter carries a band order
  that leaves facets out.
- **Lines on a child member.** `groups/group_child_member_stamps.yaml`
  and its twin hold the group of `group_parent_both` (`group_1` listing
  `middle`, the child of `piece` at 4, and `recording`) with three
  timestamps besides `origin` and `length`: `timestamp_1` "Bar 2" at `[2,
  1]` on `middle` with the `display` `["cross_section"]`, and the match
  timestamps `timestamp_2` at `[4, 1]` on `middle` and `timestamp_3` at
  `5.0` on `recording`, neither named; the one MatchStamp `matchstamp_1`
  "Middle, bar 3" holds the anchor `anchor_1` from `timestamp_2` to
  `timestamp_3` with the `display` `["line", "name"]` and the MatchClaim
  `claim_1`; no timestamp is a groupstamp (the twin leaves out each
  member at its default: the match timestamps' `display`, `timestamp_1`'s
  `matchstamp: false`, every `groupstamp: false`). Both forms pass `validate`,
  `identity_problems` and `matchstamp_problems`, so the emitter carries
  named timestamps and a MatchStamp on a member that is a child.
- **A parent's band order with its children below.**
  `groups/group_grandchild_parent_on_top.yaml` and its twin hold the
  timelines and the group of `group_grandchild` (`score` holding
  `movement` at `[16, 1]`, which holds `theme` at `[8, 1]`; `group_1`
  listing `recording` and `theme`) with exactly two `graphical.order`
  entries: the display order `{"group_1": ["theme", "recording"]}` of
  `group_grandchild` and the band order `{"movement": ["line", "children",
  "conversion_maps", "markers", "regions", "flow_control"]}`, no entry
  for `score`. Both forms pass `validate` and `identity_problems`, so the
  emitter carries a band order on an ancestor of a member, the one case
  whose drawing puts an ancestor line on each side of the member.
- **Flow-control IDs by role.** Across the complete fixtures, every
  flow-control element whose ID has the generated form `<prefix>_<N>`
  carries its own `role` as the prefix: exactly `barline_1` (two),
  `barline_2` and `barline_3` (one each), `break_1` to `break_4` (nine,
  three, one and one), `jump_1` (sixteen), `jump_2` (nine), `jump_3`
  (three), `jump_4` to `jump_11` (one each), `jump_target_1` (eleven),
  `jump_target_2` (five), `jump_target_3` to `jump_target_8` (one each)
  and `section_break_1` (two). The IDs of the earlier form of flow control
  (`jump_from_N`, `jump_to_N`, `flow_marker_N`) occur nowhere. Every other flow-control ID is one a builder
  names (`fine`, `da-capo`, `da_capo_al_fine`, `dal_segno`, `repeat`,
  `segno`, and `volta_jump`, `volta_break`, `repeat_end` and
  `second_ending` of `allegro`). A prefix taken from another role (a jump `break_1`, a jump
  target `jump_1`) fails the test.

## The graphical object

`docs/drawing.md` section 4's defaults block (three styles, 44 rules,
among them one for each of the element types `jump`, `break`,
`section_break`, `barline`, `symbol`, `fork` and `leader`, and one
selecting the atomic sections by `{"element": "region", "class":
"tts:AtomicSection"}`), read from the file, validates as the
`graphical` of the smallest file. The flow drawing's vocabulary
validates in a rule of the smallest file and leaves `unknown_keys`
empty: the selectors `{"element": "symbol"}`, `{"element": "fork"}`
and `{"element": "leader"}`, the addresses `{"id": "score", "part":
["symbol"]}`, `["fork"]` and `["leader"]`, a `class` written as a
compact IRI (`tts:AtomicSection`) and as a full IRI
(`https://timetoalign.github.io/timetoshare/ns#AtomicSection`), and
`label-display` set to `none`, `label` and `name id label`; a `class`
that is neither a class word nor an IRI (`tts AtomicSection`) is refused
at the selector's `class`, and a `label-display` word other than `name`,
`id` and `label` at the property (the shared case
`rule_set_label_display_unknown`, the word `names`). The word
`bracket`, which `fork` replaced, is refused as an element type at the
selector's `element` and as a part at the address's `part`. The
rules naming `card`, `frame`, `inside: ancestor` and `shadow`
validate, and so do `{"element": "ancestor_card"}` and the rule that
addresses the ancestor cards of one root, `{"element": "ancestor_card", "addresses":
[{"id": "score", "part": ["card"]}]}`, each setting `display: none`; so do the band selectors, `{"element": "band"}`, `{"element":
"band", "facet": <facet>}` for each of the five facets `markers`,
`conversion_maps`, `children`, `regions` and `flow_control`,
`{"addresses": [{"id": "score", "facet": "regions"}]}` and `{"inside":
"band"}`, each setting `display: none`, while a facet as a `class`
(`regions`) is refused at the selector's `class`, the element type `group`
at its `element`, and an empty `addresses` at `addresses`. In the
manifest whose groups `g1` and `g2` share the member `t`, a selector
`{"addresses": [{"id": "t", "part": ["card"]}]}`, every card of `t`,
validates. A selector's `coordinates` chooses a stamp's primary or its
secondary coordinates: `{"coordinates": "primary"}` and `{"element":
"wedge", "coordinates": "secondary"}` each validate and leave
`unknown_keys` empty, and any other word is refused at the selector's
`coordinates` (`rule_select_coordinates_unknown`, the word `both`). The schema shapes each entry of an order as an ID: the empty
string is refused at the entry, and a repeated entry (`line`, `markers`,
`line`) at the order, before any identity rule is read; property
bounds accept `stroke-width` and `rx` 0, `opacity` 0 and 1, positive
`font-size` and `max-width`, both forms of `stroke-dasharray`, and a wedge's
`rotation` at −45, at both ends, −180 and 180, and written as an integral
float (`45.0`, the integer 45 however it is spelled), and reject a negative
width and radius, opacity outside [0, 1], zero font size and maximum width,
non-text content, malformed dash text, a `rotation` one degree beyond the
range (181), a fractional one (−180.5) and one written as text (`"45"`) at
the property path. A
timeline name holding control characters validates.

## Completing missing styles

`complete_styles` returns a new `graphical` object and never changes its input.
Every distinct style name named by a rule but absent from `styles` is
added as an empty declaration, and the returned missing names are sorted by
code point. With missing names it emits exactly one `MissingStyleWarning`
whose exact text names all of them; with none no warning. Tests pin an absent
`styles` member, duplicate references, code-point ordering (`ﬀ` before `😀`),
preservation of existing declarations and input independence.

## The fonts

A drawing's text is drawn in DejaVu Sans 2.37 and every code point DejaVu
Sans does not map and Noto Music 2.004 does in Noto Music, and measured from
one table. What proves the table:

- **Both files are the release files.** `FONT_FILES` is `("DejaVuSans.ttf",
  "NotoMusic-Regular.ttf")` and `font_paths()` names them in that order,
  each with the SHA-256 of its upstream release file
  (`7da195a74c55bef988d0d48f9508bd5d849425c1770dba5d7bfc6ce9ed848954`,
  `26c0a28d7c6f96c70f1401db23066c5ea0ee1cdf155c79bc01ad2efb040de816`), with
  `DejaVuSans-LICENSE` and `NotoMusic-LICENSE` beside them.
- **The stated values.** `font_metrics()` has exactly `advances`,
  `ascender`, `descender`, `fallback`, `units_per_em` with 2048, 1901, 483
  and 1229, and 6467 advances: DejaVu Sans's 5918 (`"9833"` 966, `"48"`
  1303, `"32"` 651) and 549 from Noto Music (`"119133"`, U+1D15D, 1053 from
  Noto Music's 514 of 1000; `"119070"`, U+1D11E, 1456 from 711;
  `"119135"`, U+1D15F, 819 from 400; `"118784"`, U+1D000, 973;
  `"119296"`, U+1D200, 1810).
- **Every DejaVu Sans value unchanged, every added value exact, no other
  code point added.** Independently of the parse script, the test
  reads both TrueType files with fontTools: the table's code points that
  DejaVu Sans maps carry exactly DejaVu Sans's advances, and the others are
  exactly the 549 code points from U+0020 up that Noto Music maps and DejaVu
  Sans does not (none below U+0020 is in the table: a drawing turns
  U+0000 to U+001F into spaces before measuring, so Noto Music's U+0000
  and U+000D are left out),
  each the nearest integer to Noto Music's advance times 2048 over its
  units per em, computed as an exact fraction (no added advance lies on a
  tie).
- **The file is the script's.** `dumps(…, serialization="json")` reproduces
  the metrics file; the
  extraction script reproduces it from the bundled fonts and refuses either
  font altered by one byte, naming the file and both digests; access works
  from any working directory.

## The table types

`timetoshare.tables` (the extra `tables`, pyarrow) holds the table types
a package keeps beside its manifests: the registry, one row per resolvable
ID (an event row per event, its position on its root's axis, a
Projection's naming the event it stands for in `projection_of`; a
non-event row per manifest element, MatchClaim and parse), the Parse
table and the MatchClaim table. A Projection holds nothing but its ID and
that event, so it has no pre-parsed table.
The tests (`test_tables.py`, `test_tables_anchors.py`) need pyarrow, a
development dependency; without it they are skipped, as the font
extraction's are without fontTools. What proves them:

- **The columns are the declared ones.** `MATCH_CLAIM_COLUMNS` names, in
  this order, `timeline_a_id`, `timeline_b_id`, `start_anchor`,
  `end_anchor`, `is_synchronous`, `provenance`, `certainty`,
  `event_a_id`, `event_a_name`, `event_b_id`, `event_b_name`, `id`;
  `REGISTRY_COLUMNS` `id`,
  `kind`, `location`, `timeline_id`, `unit`, `number_type`, `start`,
  `duration`, `parse_id`, `locator`, `vanished_in`, `projection_of` (no
  `name`: an element's name is its manifest's, an event's its pre-parsed
  table's);
  `PARSE_COLUMNS` `id`, `source`, `source_integrity` (the struct
  `algorithm`, `digest`, `INTEGRITY_TYPE`), `parser`, `parser_version`,
  `parameters`, `minter`, `id_length` (int64), `seed`, `date`; and
  `NON_EVENT_KINDS`, the kinds of a non-event row, the sixteen names `Manifest`,
  `Timeline`, `VirtualTimeline`, `Group`, `MeasureMap`, `ConversionMap`,
  `Region`, `FlowControlElement`, `Resource`, `FlowMap`, `Timestamp`,
  `MatchStamp`, `AlignmentAnchor`, `Elision` (each a definition of the
  manifest schema, which the test reads), `MatchClaim`, `Parse`. A
  number is the struct `numerator`, `denominator` (int64), `value`
  (float64), the type of an event row's `start` and `duration`; a
  coordinate cell is a number followed by `unit`
  and `number_type` (strings); an anchor the struct `coordinate_a`,
  `coordinate_b`, its timelines the
  row's `timeline_a_id` and `timeline_b_id` (an anchor cell holding the
  timeline IDs as well is another type, `schema_violation`);
  `projection_of` the struct `timeline_id`, `event_id`, the registry's
  last column. The
  provenance struct holds exactly `PROVENANCE_KEYS`, `stated_by`, `date`,
  `method`, `service`, `basis`, `match`, `note`, `beliefs`, and a belief
  exactly `BELIEF_KEYS`, `actor`, `belief`, `date`, `note`. Both key sets
  are read from `schema/0.2.0/provenance.schema.json` (its `properties`
  and its `Belief`'s), never declared a second time: the test reads the
  schema file itself and compares, and pins the lists, so a key added to
  the schema changes the struct and fails the test that names it. Each
  member's Arrow type follows from the schema: an array is a list (of the
  belief struct for `beliefs`, of strings otherwise), every other member a
  string; `belief` is one of `timetoshare.BELIEFS`, the strings `true`,
  `false`, `unlikely`, the schema's enum.
- **The column types are published as data.** `schema/0.2.0/tables.json`
  (`tables_path()`) is the one source of every table schema: its `types`
  declare `number`, `coordinate`, `anchor`, `projection_of` and
  `integrity` as Arrow structs of named members and `provenance` as the
  struct read from the provenance schema it names; its `tables` give each
  table a `status` and its `columns` in order, and the registry its
  `non_event_kinds`, each column a `name`, a `type` (one of the four type names
  `string`, `bool`, `int64` and `float64`, Arrow's utf8, bool, int64 and
  double, or a type of `types`) and whether it is `nullable`. The test
  reads the file and
  pins it: its `$id` is
  `https://timetoalign.github.io/timetoshare/0.2.0/tables.json`, its
  sections are exactly `types` and `tables`, the MatchClaim table is
  `stable` and the registry and the Parse table `experimental`, the
  three tables exactly `Registry`, `Parse` and `MatchClaim`, the members of each table entry are exactly
  `description`, `status` and `columns` (and `non_event_kinds` for the
  registry), the `coordinate`'s
  members are the `number`'s followed by `unit` and `number_type`, and
  `provenance` names `provenance.schema.json`, a file beside it.
  `MATCH_CLAIM_SCHEMA` equals, field by field, a literal list of its
  twelve columns with their Arrow types written out in the test
  (`timeline_a_id` string, …, the anchors the struct of two coordinate
  structs, `provenance` the struct of the eight members, `certainty`
  double, …, `id` string), `REGISTRY_SCHEMA`
  its twelve and `PARSE_SCHEMA` its ten; every Arrow field is
  nullable, so a writer need declare nothing, and the columns the file
  marks `nullable: false` are exactly those a null is refused in in every
  row (`timeline_a_id`, `timeline_b_id`, `is_synchronous`, `event_a_id`,
  `event_b_id`, `id`; `id`, `kind`; `id`, `parser`,
  `parser_version`, `minter`, `id_length`, `date`), each proved below, and
  `MATCH_CLAIM_REQUIRED`, `REGISTRY_REQUIRED` and
  `PARSE_REQUIRED` are these tuples; `REGISTRY_EVENT_REQUIRED`,
  `timeline_id`, `unit`, `number_type`, `start`, `parse_id`, are the
  columns an event row holds no null in. Every
  column and member type is one of the four names or a name of `types`,
  and the four are `pa.string()`, `pa.bool_()`, `pa.int64()` and
  `pa.float64()`, so a reader in another language needs no list beyond
  the description's. A
  column added to the file, a type changed or a status changed fails the
  test that names it.
- **A number holds its number type's members alone.** `NUMBER_MEMBERS`
  gives an `int` the `numerator`, a `fraction` the `numerator` and the
  `denominator`, a `float` the `value`; every other member is null, so no
  value is stated twice. `number_cell` writes 3 on an int axis as
  `(3, null, null)`, `Fraction(3, 6)` and the integer 2 on a fraction axis
  as `(1, 2, null)` and `(2, 1, null)`, 0.25 and the integer 2 on a float
  axis as `(null, null, 0.25)` and `(null, null, 2.0)`, and refuses a
  float on an int or fraction axis, a Fraction on a float axis, a
  non-integral Fraction or the boolean `true` on an int axis, a non-finite
  float, an integer no double holds exactly on a float axis (2^53 + 1,
  which a conversion would round, and 2^1024, beyond the doubles), an
  exact number whose members leave the 64-bit integers (2^70 on an int
  axis, 1/2^64 on a fraction axis) and an unknown number type, each with
  its exact message and always as a `ValueError`.
  `coordinate_value` reads each pattern back to the exact value (`3`,
  `1/2`, `1/4`, a float as its exact binary value), from the cell's own
  `number_type` or from the one given for an event row's number, and
  reads nothing from a member its number type leaves null.
- **Each rule refuses its smallest counterexample and nothing else.** A
  valid table of a few rows is built inline; each rule is proved by
  changing one cell (or one column type) and asserting the exact list of
  problems `(code, row, column)` and the message of the first, which
  `check_match_claims`, `check_registry`,
  `check_parses` and `check_succession` raise as `TableError`. The
  valid table itself yields no problem, with and
  without its manifest. The rules: a missing column or a column of
  another type (`schema_violation`; a Parquet round trip, which renames
  list items, changes nothing; a column the type does not declare is
  kept, as an unknown key is); a null in `id`, a timeline,
  `is_synchronous` or an event ID (`schema_violation`, `'event_b_id' is
  null`: a sentinel is a string, never a null); an empty ID or one with a
  control character, and an `id` that is one of the two reserved strings
  (`invalid_id`, `'NOMATCH_SENTINEL' is reserved for a sentinel`, in the
  MatchClaim table and the registry); an ID twice in a table
  (`duplicate_id`, at its second row: `the ID 'claim_1' is given twice`,
  `the ID 'projection_1' is given twice`), an event row's ID as much on two timelines as on one, since an
  event's ID is unique in the package; a `scope`
  column is one of the undeclared columns, kept and never checked: one of
  integers is no problem, and one of strings giving a repeated `claim_1`
  two values leaves it given twice; a
  coordinate cell with an unknown unit or number type, or with a number
  type its unit does not admit by `UNITS` (`'samples' admits no number
  type 'float'`, `'quarters' admits no number type 'int'`), without a member
  its number type fills (an int without `numerator`, a fraction without
  `denominator`, a float without `value`), with a member its number type
  leaves null (an int with a `denominator` or a `value`, a fraction with a
  `value`, a float with a `numerator`: the mirror a former cell carried is
  refused), a fraction's denominator below 1, a
  non-finite float, a cell without `unit` or `number_type` (`the
  coordinate has no unit`) (`invalid_coordinate`, with the message naming
  the member); both timelines the same (`claim_timelines`); a sentinel
  where it cannot stand (`claim_events`, see the sentinels below); a
  NOMATCH row with an anchor, a conceptual row (two events, not
  synchronous) with an anchor, a synchronous row without `start_anchor`,
  an `end_anchor` without a start (`claim_anchors`); a certainty outside
  [0, 1] (`invalid_certainty`); a provenance entry, a row's cell (a null
  member being an absent one) or the file's, that is no entry of the
  provenance schema, checked by the schema itself and its first problem
  chosen by the validators' one path rule, its message `<the provenance |
  the file's provenance> <JSON pointer into the entry>: <the schema's
  message>`: an empty `stated_by`, a repeated `basis`, a date not written
  `YYYY-MM-DD`, a `method` neither a word nor an IRI, a `match` word
  outside the schema's, a belief word outside `BELIEFS`, a belief without
  date or actor; then a key the schema does not declare (`'status' is no
  key of a provenance entry`, `'weight' is no key of a belief`); then a
  date of the entry or of a belief that is no Gregorian calendar day
  (`2026-02-30`, the manifest's message); then an actor holding two
  beliefs (`'<actor>' already holds belief 0 of this entry; an actor holds
  one belief`, the manifest's message), against a manifest also the actor
  written once compactly (`orcid:…`, under a `@context` declaring
  `orcid`) and once absolutely, which without the manifest, its context
  unknown, is no problem (`invalid_provenance`); the file's
  provenance that is no JSON text, no object, or whose members have the
  wrong type (`{"beliefs": "x"}`, `{"date": 5}`, `{"stated_by": 5}`) is
  reported, never raised; provenance stated both in the file's
  metadata (`timetoshare:provenance`) and in a row (`invalid_provenance`);
  one timeline's cells in two units or number types within a table
  (`axis_mismatch`). A Projection's registry row whose `projection_of`
  lacks a member (null or empty: `the projected event has no event_id`)
  or names a sentinel's string as its `event_id` (a Projection stands for
  an event, never for a sentinel: `'NOMATCH_SENTINEL' is reserved for a
  sentinel` at `projection_of.event_id`, after the missing members), or
  whose `projection_of` names the Projection's own timeline, which the
  row holds beside it (`a Projection stands for an event of another
  timeline than 'dpt_1'` at `projection_of.timeline_id`, after the
  sentinel), and a `projection_of` stated on a row of another kind, an
  event row's (`MidiNote`) or a non-event row's (`Timeline`): `'projection_of'
  is set on a row of the kind 'MidiNote'` at `projection_of`
  (`invalid_projection_of`), each the same with and without the
  manifest; a `projection_of` column holding a joined string
  (`schema_violation`); a Projection whose `projection_of` is null (a
  position a source states without an event of its own) is admitted. A
  Projection standing for an event of `clt_9`, a timeline the manifest
  lacks, is no problem without the manifest; against the manifest alone it
  is `unknown_timeline` at `projection_of.timeline_id` (`the manifest has
  no timeline 'clt_9'`); given the timelines of a package that holds
  `clt_9` (the manifest's and `clt_9`) it is admitted, since the projected
  event may lie in another manifest of the package sharing the Projection's
  timeline; given a package's timelines without `clt_9` it is
  `unknown_timeline` there again, worded for the package (`no manifest of
  the package has the timeline 'clt_9'`). Both halves are needed: the
  first proves a lone manifest refuses what no timeline of it holds, the
  second that a package's reader, filtering the shared registry for one
  manifest, does not refuse another manifest's event. A registry's event
  row (its `kind` none of `NON_EVENT_KINDS`) whose `timeline_id`, `unit`,
  `number_type`, `start` or `parse_id` is null, and a row whose `id`
  or `kind` is null (`schema_violation`, `'<column>' is null`, row by row,
  column by column in the table's order); a non-event row whose `location` is
  null, or which states a `unit`, `number_type`, `start`, `duration`,
  `parse_id`, `locator` or `vanished_in` (`schema_violation`, `a
  non-event row has no 'start'`; a `projection_of` there is the
  `invalid_projection_of` above); an event, MatchClaim or Parse row
  holding an ID another of these rows holds (`the ID 'projection_2' is
  given twice`: an event's ID and a MatchClaim's are held once together),
  an element's ID twice at one `location` (`the ID 'clt_1' is given twice
  at 'manifest.yaml'`), while the same element ID at two locations is no
  problem (`duplicate_id`); an empty or reserved ID (`invalid_id`); an
  event row whose `unit` or `number_type` is unknown or not admitted
  (`invalid_coordinate` at that column), whose `start` or `duration`
  breaks the number rule (`invalid_coordinate`), whose `duration` is
  negative (`invalid_duration`), two event rows of one timeline in two
  units (`axis_mismatch` at `unit`) or two number types (at
  `number_type`); a locator given twice within one parse
  (`duplicate_locator`, `the locator 'track 0, message 4' is given twice in
  the parse 'parse_1'`), while one locator in two parses,
  an event row without a location (re-parsable only, or of a kind such as
  `Projection` that has no pre-parsed table), another event kind
  (`MidiNote`) and a row with `vanished_in` stated are admitted; non-event rows
  are never checked against a manifest (a Region of another manifest on a
  timeline it lacks passes). A Parse row whose `id`, `parser`,
  `parser_version`, `minter`, `id_length` or `date` is null
  (`schema_violation`); an ID twice or reserved (`duplicate_id`,
  `invalid_id`); a `source` without `source_integrity` (`'source_integrity'
  is null where 'source' is given`) and an integrity without `digest`, one
  problem per row a bad cell stands in (each `schema_violation`). Nothing
  else of a row is refused, since a reader accepts what a writer may write
  and spelling a value canonically is the writer's duty: `parameters`
  that are no JSON text (`{merge_tracks: false}`), no object (`[480]`) or
  not in RFC 8785 JSON (`{"resolution": 480, "merge_tracks": false}`,
  spaced and unsorted), a `date` with the offset `+00:00`, without a zone
  or of no calendar day (`2026-02-30T00:00:00Z`), a fractional second
  (`21:31:05.250Z`), an `id_length` of 0, an integrity of an algorithm
  the manifest schema's `Descriptor` does not list (`SHA-3`) or with a
  digest in capitals (`00FF`), and a run without a source are each
  admitted, with no problem.
- **The sentinels are reserved strings, read by `is_synchronous`.** An
  event ID column holds an event's ID or one of the two strings
  `timetoshare.tables` exports, `NOMATCH_SENTINEL` and `CHUNK_SENTINEL`
  (the test pins both values). The rows the format admits are accepted,
  each built from the inline table by one change and checked with and
  without the manifest, with no problem: a synchronous instant and a
  synchronous interval with `CHUNK_SENTINEL` on side A, on side B, and on
  both sides; a CHUNK side with a name (the name of the stated position),
  on side A, and on both sides of an interval; a NOMATCH with
  `NOMATCH_SENTINEL` on side A as well as on side B. A CHUNK side's event ID is no ID to check (a sentinel never
  meets the ID rules), and an event ID that is no sentinel still does. Each
  refused row is the smallest counterexample, with its exact problems and
  first message, in the order of the rules: `CHUNK_SENTINEL` on a row that
  is not synchronous (`claim_events` at that side's `event_X_id`, side A
  before side B: `CHUNK_SENTINEL stands only on a synchronous MatchClaim`,
  once per side when both sides hold it); `NOMATCH_SENTINEL` on a
  synchronous row (`claim_events` at that side's event ID: `NOMATCH_SENTINEL
  stands only on a MatchClaim that is not synchronous`); `NOMATCH_SENTINEL`
  on both sides (`claim_events` at `event_b_id`: `a NOMATCH MatchClaim
  names an event on its other side`); a name on a NOMATCH side
  (`claim_events` at that side's `event_X_name`: `a NOMATCH side has no
  name`); then the anchor rules: a synchronous row with one or no
  event and no start anchor gives `a synchronous MatchClaim has a start
  anchor`, at `start_anchor`, as a row of two events does. The messages of
  the former null reading, `the MatchClaim names no event` and `a NOMATCH
  MatchClaim is not synchronous`, and of the former name rule, `a sentinel
  side has no name`, are never given: no case and no table
  the suites compare (fixtures, inline cases, seeded mutations, the larger
  table) yields any of them.
- **A fraction in any terms is its value.** No check asks a fraction
  cell for lowest terms: an unreduced fraction is read, and it is the
  same value as its reduced form wherever cells are compared. The
  MatchClaim table with `claim_2`'s start anchor written `(2, 2, null)`
  (the quarter 1) or `(0, 4, null)` has no problem, with and without its
  manifest, and `coordinate_value` reads the two cells as exactly `1` and
  `0`; so does the registry whose third event row, moved to the quarters
  of `clt_1`, starts at `4/2` (read as `2`) or starts at `7/2` and lasts
  `2/4` (read as `1/2`). Its anchors are the reduced table's:
  `alignment_anchors` gives the table with `(2, 2, null)` exactly the
  anchors and MatchClaim IDs of the table with `(1, 1, null)`. A test
  that refuses one of these cells, or reads it as another value, fails.
- **Given a manifest, every row is the manifest's.** A file may hold the
  rows of several manifests of a package. A manifest reads its rows by
  filtering first (`read_table` with the timelines its resource lists,
  a MatchClaim kept where either of its timelines is listed); the checks
  themselves pass no row over, so a lone manifest is a package of one.
  Each timeline a row names that the manifest does not hold is
  `unknown_timeline` at that row and column. What proves it
  (`test_tables.py`): the inline tables with three rows of foreign
  timelines (`dpt_8`, `dpt_9`), valid otherwise, inserted before, between
  and after their own rows give against the manifest exactly
  `unknown_timeline` at rows 0, 3 and 6, at `timeline_a_id` then
  `timeline_b_id` (`the manifest has no timeline 'dpt_8'`, then `'dpt_9'`),
  and for the registry's event rows at rows 0, 3 and 5, at `timeline_id`;
  without the manifest, no problem. An event row whose `timeline_id` is
  `ghost` (row 2) is `unknown_timeline` at `timeline_id` (`the manifest
  has no timeline 'ghost'`), and no problem without the manifest; a
  Projection standing for an event of `clt_9` is `unknown_timeline` at
  `projection_of.timeline_id` against the manifest, and admitted given
  timelines of the package that hold it (above). A MatchClaim with exactly one of its timelines in the manifest
  (row 4) is `unknown_timeline` at its other side alone (`the manifest has
  no timeline 'dpt_9'`). A null timeline names no timeline of the
  manifest: an event row whose `timeline_id` is null (row 1) and a
  MatchClaim whose two timelines are null (row 1) are `schema_violation`
  at each null column (`'timeline_id' is null`, `'timeline_a_id' is
  null`), with and without the manifest. The shared package fixture's rows, read with
  `read_table(..., timelines=)` for each resource, pass the checks against
  their manifest (`test_packages.py`). The comparison with the reference
  (`test_table_checks.py`) holds the rule on every mutated table.
- **Against a manifest.** Given a manifest (as read from its file), every
  timeline a cell or a row names exists, a virtual timeline of the
  manifest included (a claim on `virtual_1` passes against the manifest
  stating it and is `unknown_timeline` against one without it)
  (`unknown_timeline`), and every
  cell, every event row, is in its timeline's own unit and number
  type (`axis_mismatch`): seconds on a samples timeline and a float on a
  fraction axis are refused, the same cells and rows without a manifest
  are not. A number type the unit does not admit is no question of the
  manifest: a MatchClaim's `samples` cell as `float` and an event row's
  `samples` axis as `float` are refused as `invalid_coordinate`, at the
  cell and at `number_type`, with the same message with and without the
  manifest, and never also reported as `axis_mismatch`. A test where the
  manifest is needed to refuse such a pair fails.
- **The succession rule.** `check_succession(old, new)` accepts the same
  table, the table with rows appended and the table with every provenance
  changed (a belief added); it refuses a missing ID (`succession_missing`)
  and a change to any other column, an anchor moved, an event renamed, a
  timeline swapped (`succession_changed`, naming the column). A coordinate
  is compared by unit, number type and exact value, so the quarter 1
  written as `(1, 1, null)` and as `(2, 2, null)` is the same coordinate
  and a successor respelling it changes nothing; an anchor's coordinates
  are compared side by side, `coordinate_a` on the row's
  `timeline_a_id`. A MatchClaim is its ID
  alone: a column the type does not declare takes no part, so a successor
  adding a `scope` column, or changing its values, breaks nothing.
- **The derivation is checked against values written by hand.** The
  fixture's expected file (`expected.yaml`) is written in
  `scripts/emit_tables.py` as literal data, never computed by the
  derivation; for each of its cases, a `believer` and the `beliefs` the
  filter keeps (no believer, every state but `false`, the default; an
  actor's default; that actor's `true`; a second actor's `true`; the
  first actor's `undecided`, the rows the actor holds no belief in; the
  first actor's `unlikely` and `false` together; the first actor's `true`
  again, the believer written compactly as `orcid:0000-0002-1825-0097`
  while every row writes the actor absolutely) `alignment_anchors` (each
  anchor with the MatchClaims stating it) and `potential_matchstamps`
  equal the expected values exactly, as exact fractions, every case read
  under the fixture manifest's `@context`, which declares `orcid` as
  `https://orcid.org/`; the compact case keeps exactly what the absolute
  one does, and without that context it would keep nothing, so the
  shared file pins the comparison of actors as IRIs for every reader. The fixture covers an instant claim, an interval
  claim (two anchors), two MatchClaims stating one anchor in opposite
  orientations, a chain over three timelines, one coordinate in two
  anchors, an interval claim with an anchor inside its span, a Projection
  of an event, a
  NOMATCH row (`NOMATCH_SENTINEL` on its sample side), a conceptual row, a row one actor believes false and another
  true, a row believed `unlikely` (kept by the default filter, dropped by
  the believed-true one, kept again by the unlikely-and-false one, which
  splits the chain it closes) and a child timeline whose coordinates never
  meet its parent's; and the two kinds of CHUNK: `claim_11`, a synchronous
  MatchClaim with `CHUNK_SENTINEL` on both sides, its side A named
  `downbeat 3` (the fixture table is accepted, so a named CHUNK side is
  read; the test of the sentinels pins each sentinel side's name), whose
  anchor between the samples and the seconds timelines closes the set of
  `claim_13` as the
  two Projections without a source it replaced did, so its expected
  values are unchanged,
  and `claim_16`, an instant MatchClaim between `CHUNK_SENTINEL` on the
  seconds timeline and the note `claim_2` states at the quarter 1, whose
  anchor (quarter 1, second 1.0) sorts before `claim_2`'s and joins its
  set: the potential MatchStamp at the quarter 1 holds three coordinates
  and the MatchClaims `claim_16` and `claim_2` wherever the filter keeps
  both (no actor, the actor's default, the actor's `undecided`), so a
  reader that drops a CHUNK row's anchor, or reads a CHUNK side as an
  event, fails the literal values. `claim_17`, an instant MatchClaim
  between the note at the quarter 45/4 and its Projection `projection_12`
  at the second 11.25, gives one anchor and one potential MatchStamp of
  its own, kept wherever the filter keeps undecided rows. `claim_18` is a
  NOMATCH stated from `inserted_1`, a Projection on the samples timeline
  under the source's ID for a note the package does not hold
  (`projection_of` null), `NOMATCH_SENTINEL` on its quarters side; as a
  NOMATCH it states no anchor and leaves every expected value unchanged,
  so a reader that takes a Projection without a source for an anchor's
  coordinate fails the literal values. Its registry's
  event rows hold each number type of the cell form: int instants and an int
  interval on the samples timeline, a float instant (`projection_12`) and
  a float interval on the seconds timeline, and a fraction interval on the
  child timeline in quarters (at 7/2 on the child, which starts at the
  quarter 8: start 23/2 on its root, duration 1/2), so every reader of the
  shared tables meets a fraction, a float instant and a float duration. Without an actor the row believed false still gives
  its anchor.
- **The belief filter takes the four states.** The states and the check of
  a filter are the package's (`timetoshare.BELIEF_STATES`,
  `DEFAULT_BELIEFS`, `check_belief_filter`, proved under Statements);
  `DEFAULT_BELIEFS` is the default of `believed_rows`, `alignment_anchors`
  and `potential_matchstamps`, which raise its messages. A row's state for a believer is the believer's
  belief in it, or `undecided` where the believer holds none (a row
  without provenance included); the row is kept when that state is one
  the filter names. `believed_rows` keeps, per believer and collection of
  states, the rows listed in `test_tables_anchors.py`: every state alone
  for one actor, which partitions the eighteen rows, the default, and
  without a believer every row whatever the states. A single string
  raises `the belief filter takes a collection of states, not the string
  'true': write ['true']`; an unknown word raises `'not_false' is no
  belief state: write 'true', 'undecided', 'unlikely' or 'false'`; an
  empty collection keeps no row for a believer. Actors compare as the
  IRIs they stand for under the `context` given: the believer
  `orcid:0000-0002-1825-0097` under a context declaring `orcid` as
  `https://orcid.org/` keeps the rows of the absolute actor, and keeps
  none of its `true` rows without that context (it then compares as
  written). A row holding beliefs of one believer under two spellings,
  which only a check without the manifest lets pass, takes the most
  critical of them, `false` before `unlikely` before `true`: a row
  believed `true` by `orcid:0000-0002-1825-0097` and `false` by
  `https://orcid.org/0000-0002-1825-0097` is `false` for that believer
  under the context, whichever is written first, and kept by `["false"]`
  alone; `unlikely` beside `true` is `unlikely`; without the context the
  two spellings are two actors and the absolute believer reads its own
  belief alone.
- **The fixture files are the script's.** The three Parquet files
  (`match_claims.parquet`, `parses.parquet`, `registry.parquet`) read back
  equal to the tables the script builds, and the fixture's folder holds
  them, `expected.yaml` and `tables.tts.yaml` alone (no table of
  Projections);
  the manifest equal to the script's manifest of the files written, and
  every table passes its check against that manifest. The manifest names
  two tables in its `resources` (`resource_1`, `MatchClaim`,
  `match_claims.parquet`; `resource_2`, `Registry`, `registry.parquet`),
  each with the media type `application/vnd.apache.parquet`, the size of
  the file in bytes, its SHA-256 digest (both computed by the test from the
  file) and, in the manifest's order, exactly the timelines its rows name;
  the registry's rows name the Parse table. The registry holds 36 rows: its
  non-event rows (the eighteen MatchClaims at `match_claims.parquet`, the
  parse at `parses.parquet`, the four timelines and two resources at
  `tables.tts.yaml`) sorted by location and ID, then the eleven
  event rows, each a `Projection` of `parse_1` whose `location` is null
  and whose `projection_of` names the event it stands for, sorted by
  timeline, exact start and ID. Each Projection a MatchClaim names stands on that
  side's timeline at the anchor's coordinate, its registry start less the
  offset of its child timeline from the root, its duration spanning to the
  end anchor; the fixture's eleven Projections are all named but two, the
  fraction interval and the float interval; one, `inserted_1`, names no
  event (`projection_of` null) and is named by the NOMATCH `claim_18`, the
  only MatchClaim side naming a Projection without an anchor; and no
  Projection stands where a MatchClaim's side is `CHUNK_SENTINEL` (a CHUNK
  is no Projection). The Projections keep their numbers, `projection_6`
  and `projection_7` being no longer held.

## Packages

A package is a folder whose `package.yaml` lists its manifests and its
tables; a table is a file, or a folder of files read as one table
(`schema/0.2.0/package.schema.json`, `timetoshare.validate_package`,
`timetoshare.tables.read_table`, `timetoshare.tables.package_problems`).
What proves them (`test_packages.py`, needs pyarrow):

- **The package schema is published beside the manifest schema.** Its
  `$id` is `https://timetoalign.github.io/timetoshare/0.2.0/package.schema.json`;
  it requires exactly `timetoshare`, `manifests` and `tables`, declares
  `id`, `name` and `meta` beside them, and refers into the manifest
  schema for `Descriptor`, `IriReference`, `Name` and `Meta`.
  `load_package_schema()` equals `bundle_package_schema` of the file and
  `load_schema()`: every reference local, its definitions exactly
  `Table`, `Descriptor`, `Name`, `Meta` and `IriReference` in that order
  (its own, then the manifest bundle's it reaches, in the bundle's order),
  each reached definition the manifest bundle's own. A reference to
  another document (`https://example.org/other.json`) is refused with
  "reference 'https://example.org/other.json' leads to no definition of
  the manifest schema", and a package definition of a name it reaches in
  the manifest schema with "both schemas define 'Descriptor'".
- **One `Descriptor`.** The manifest schema's `Descriptor` declares exactly
  `url`, `media_type`, `size` and `integrity`, requiring `url`; `Resource`
  is that descriptor (its one `allOf`) with `id`, `type` and `timelines`,
  requiring those three, so a resource keeps its public shape, and the
  package's `Table` is the descriptor with `type`. Every fixture with
  resources still validates, so no resource lost or gained a member.
- **`validate_package`.** The shared package's `package.yaml` validates,
  and so does the smallest package, `{timetoshare: "0.2.0", manifests: [],
  tables: []}`. Each refusal is exact, code, path and message: a value
  without `timetoshare` (`not_a_package`, `[]`, `not a TimeToShare
  package`, also for a list); another version (`UnsupportedVersionError`,
  the manifest's message `unsupported TimeToShare version "0.1.0"; this
  package reads 0.2.0 only`); no `tables` (`schema`, `[]`, `'tables' is a
  required property`); a table without `type` (`schema`, `[tables, 0]`,
  `'type' is a required property`); a negative `size` (`schema`,
  `[manifests, 0, size]`, `-1 is less than the minimum of 0`); a manifest
  listed twice (`duplicate_url`, `[manifests, 1, url]`, `the manifest
  'a.yaml' is listed twice, first at #/manifests/0/url`); a table listed
  twice under one `url` and `type` (`duplicate_url`, `[tables, 1, url]`,
  `the table 'tables/Note/' of the type Note is listed twice,
  first at #/tables/0/url`), while one `url` under two types validates;
  a folder with a
  `size` (`folder_descriptor`, `[tables, 1, size]`, `'tables/Note/'
  names a folder, which has no size`), with an `integrity` alone (at
  `integrity`, `… which has no integrity`), a folder among the manifests
  with a `size` (at `[manifests, 0, size]`); a file with a `size` and an
  `integrity` validates. The JavaScript suite holds `validatePackage` to
  the same codes, paths and messages.
- **`read_table` reads a folder as one table.** For each resource of the
  two manifests of the shared package, `read_table` of the folder its URL
  names, given the resource's `timelines`, returns exactly the rows
  `expected.yaml` lists, compared as sorted IDs: Bach's MatchClaims
  `claim_1`, `claim_2`, `claim_5` (`claim_5` written in the other
  orientation, its first timeline Bach's performance), Handel's
  `claim_3`, `claim_4`; from the registry, Bach's event rows `note_1`
  to `note_4`, `projection_1`, `projection_2`, `projection_7`,
  `projection_9`, Handel's `note_5`, `note_6`, `note_7`, `projection_3`,
  `projection_4`, `projection_5`, `projection_6`, `projection_8` (the rows
  of its child `clt_3` among them), event rows alone, of the kinds `Note`
  and `Projection`, since a non-event row's timeline is null or not
  listed. Each table read states its type alone in its metadata
  (`timetoshare:type`), and passes the table check against its manifest. Every MatchClaim read holds
  the file's provenance in its `provenance` cell, `{method: imported,
  service: https://example.org/aligner, date: 2026-11-20}`, the other
  members null, so no reader of a folder loses the provenance a file
  shares. A MatchClaim with either timeline listed is kept: given
  `["dpt_1"]` alone, Bach's MatchClaims are still `claim_1`, `claim_2`,
  `claim_5`. Without `timelines` every row is read (five MatchClaims, seven
  pre-parsed notes, 33 registry rows), and given `[]` none. `ids`
  keeps the rows of those IDs: `resource_1`, `note_5`, `projection_5` and
  `ghost` give the two non-event rows of `resource_1` (Bach's and
  Handel's), the event row of `note_5` at `tables/Note/` and that of
  `projection_5`, whose location is null; given with `timelines`, a row is
  kept where both keep it; `[]` keeps none; a pre-parsed table read by
  `ids` gives the content of those events (`note_4`, MIDI pitch 64). Each resolution an `expected.yaml` lists
  (the shared package's and three acceptances') states a row the registry
  holds for that ID, its kind and location the row's, and through the
  package every row of the ID; and `resolve` of its path and ID returns
  exactly those resolutions, in the order listed (through a manifest the
  element first, then the registry rows in the registry's order), each
  `Resolution` equal to the entry's `kind`, `location`, `manifest` and
  `row`. `table_files` of the folder of notes
  is `part_a.parquet`, `part_b.parquet`; files named `.part_c.parquet`,
  `_part_d.parquet`, `notes.txt` and a subfolder `sub/` holding
  `part_e.parquet`, added in a copy, are passed over, and the copy reads
  the same rows. A single file is read as itself.
- **A filter keeping no row of a MatchClaim file reads no row.** The
  shared MatchClaim folder, whose file states a shared provenance, read
  for `clt_3`, Handel's child, which no MatchClaim names, gives zero rows
  in exactly the declared MatchClaim columns, the type alone in its
  metadata; a MatchClaim file stating a shared provenance and holding no
  row, read whole, gives zero rows as well. Both once crashed the process
  in pyarrow 25 (the filter left a column of no chunks, whose valid rows
  were searched), so each runs in a child Python process: a regression
  fails its test, with the child's exit status and error output, instead
  of ending the test run.
- **Reading refuses what cannot be one table.** Each refusal is a
  `TableError` with its exact problem: two files of a folder in which one
  column has two Arrow types (`column_type_mismatch`, column
  `velocity`, `the column 'velocity' is int64 in 'part_a.parquet' and
  string in 'part_b.parquet'`); a file stating another type than the
  `type` given (`table_type`, `'part_a.parquet' holds the type Note,
  not MatchClaim`), two files stating two types (`'part_a.parquet' holds
  the type Note and 'part_b.parquet' the type MatchClaim`), a file
  stating none without a `type` given (`the table names no type: no file
  states 'timetoshare:type'`); a MatchClaim row stating its own
  provenance beside the file's (`invalid_provenance`, row 0, `the
  provenance is stated in the file's metadata and in the row`); a
  MatchClaim file stating a shared provenance whose `provenance` column is
  of another type, strings, so that the provenance cannot be filled in
  (`schema_violation`, column `provenance`, `the column 'provenance' is
  string, not …, in 'part_a.parquet'`, the declared type as Arrow prints
  it), where a reader
  ignoring it would lose the provenance silently; `timelines` given for
  files without the column naming a row's timeline, a pre-parsed table
  among them (`schema_violation`, column `timeline_id`, `the table has no
  column 'timeline_id'`), and `ids` given for files without `id` (column
  `id`). A file stating no type is read under the `type` given, and a
  column a file lacks reads as null in its rows: the shared notes
  with a further column `velocity` in `part_a` alone read three nulls for
  `part_b`'s rows; an empty folder of a declared type reads as no row in
  its declared columns.
  A path that is neither a file nor a folder raises `FileNotFoundError`.
- **`package_problems`.** The shared package has none, and neither has
  each package under `fixtures/packages/0.2.0/acceptances/`, whose
  `expected.yaml` lists no problem: `recording_resource`, the shared
  package whose Bach manifest names a recording in the folder `bach/`
  (`Audio`, `bach/recording.flac`, `audio/flac`, for `dpt_1`), a resource naming no
  table, which `package.yaml` does not list and the check passes over
  (the registry holds its non-event row); `timeline_in_two_manifests`, Handel's
  manifest holding `dpt_1` too and listing it in its Registry resource:
  manifests sharing a timeline ID share its event rows, which pass the
  registry check against either manifest given the timelines of both as
  those a Projection may name, and the ID resolves through each; the
  Projections on `dpt_1` stand for Bach's notes on `clt_1`, so against
  Handel's manifest alone they are `unknown_timeline` (`the manifest has
  no timeline 'clt_1'`) and against Bach's they pass; `re_parsable_event`, an `Onset` event row without a
  location, its content only re-parsable from its parse's source;
  `external_location`, the event row of `note_1` whose `location`
  is the absolute URI `https://example.org/events/note_1`, its
  pre-parsed row removed: a location with a scheme names a resource
  outside the package, which the check does not follow (no
  `unknown_location`, no `missing_content`), while a relative location
  naming no table entry stays `unknown_location` (the rejection below);
  `external_table_entry`, the shared package whose `package.yaml` lists,
  after its four entries, an external `Note` entry
  `https://example.org/tables/notes.parquet`: an entry whose URL is an
  absolute URI names a table outside the package, which the check does
  not follow (no `missing_file`) and which is no second local table of
  its type (no `duplicate_table`); its `expected.yaml` states the rows
  each resource reads, the shared package's `read` unchanged, and
  `read_table` over each resource of the acceptance returns exactly those
  IDs, so the external entry adds no row and takes none away.
  Each package under
  `fixtures/packages/0.2.0/rejections/` breaks one rule, and
  `package_problems` of its `package.yaml` returns exactly the problems its
  `expected.yaml` lists, in order, each as `{code, file, row, path,
  message}`, and exactly these (file, row, path):

| Case | Code | File, row, path |
| --- | --- | --- |
| `row_of_no_manifest` | `unknown_timeline` | `registry.parquet`, 33, `[timeline_id]` |
| `claim_across_manifests` | `claim_across_manifests` | `tables/MatchClaim/part_a.parquet`, 2, `[timeline_b_id]` |
| `column_in_two_types` | `column_type_mismatch` | `tables/Note/`, null, `[velocity]` |
| `version_mismatch` | `version_mismatch` | `tables/Note/part_b.parquet`, null, `[]` |
| `resource_naming_no_table` | `unknown_table` | `bach.tts.yaml`, null, `[resources, 2, url]` |
| `folder_with_size` | `folder_descriptor` | `package.yaml`, null, `[tables, 3, size]` |
| `timeline_unlisted` | `unlisted_timeline` | `registry.parquet`, 24 and 25, `[timeline_id]` |
| `axis_mismatch` | `axis_mismatch` | `registry.parquet`, 29, `[unit]` |
| `file_of_another_type` | `table_type` | `tables/Note/part_b.parquet`, null, `[]` |
| `table_listed_twice` | `duplicate_url` | `package.yaml`, null, `[tables, 4, url]` |
| `file_in_a_listed_folder` | `duplicate_table`, then `duplicate_url` | `package.yaml`, null, `[tables, 4, type]`, then `[tables, 4, url]` |
| `registry_missing` | `missing_registry` | `package.yaml`, null, `[tables]` |
| `registry_listed_twice` | `duplicate_registry` | `package.yaml`, null, `[tables, 4, type]` |
| `parse_table_listed_twice` | `duplicate_table` | `package.yaml`, null, `[tables, 4, type]` |
| `event_table_listed_twice` | `duplicate_table` | `package.yaml`, null, `[tables, 4, type]` |
| `unknown_parse` | `unknown_parse` | `registry.parquet`, 30, `[parse_id]` |
| `vanished_in_an_unknown_parse` | `unknown_parse` | `registry.parquet`, 30, `[vanished_in]` |
| `unknown_location` | `unknown_location` | `registry.parquet`, 18, `[location]` |
| `missing_content` | `missing_content` | `registry.parquet`, 21, `[location]` |
| `unregistered_id` | `unregistered_id` | `tables/Note/part_b.parquet`, 3, `[id]` |
| `locator_twice` | `duplicate_locator` | `registry.parquet`, 29, `[locator]` |
| `registry_id_twice` | `duplicate_id` | `registry.parquet`, 33, `[id]` (an onset holds `claim_1`, a MatchClaim's ID at row 9) |
| `registry_folder` | `registry_not_a_file` | `package.yaml`, null, `[tables, 0, url]`; `bach.tts.yaml` and `handel.tts.yaml`, null, `[resources, 1, url]` |
| `non_event_row_with_a_position` | `schema_violation` | `registry.parquet`, 0, `[unit]`, `[number_type]`, `[start]` |
| `stale_non_event_row` | `stale_non_event_row` | `registry.parquet`, 0, `[kind]` (differing); 4, `[id]` (extra); null, `[id]` (missing) |
| `foreign_table` | `foreign_table` | `tables/features.parquet`, null, `[]` |
| `projection_of_its_own_timeline` | `invalid_projection_of` | `registry.parquet`, 26, `[projection_of, timeline_id]` (the registry's table check: `projection_1` on `dpt_1` stands for an event of `dpt_1`) |
| `projection_of_no_timeline` | `unknown_timeline` | `registry.parquet`, 29, `[projection_of, timeline_id]` (`projection_7` stands for an event of `clt_9`, which no manifest holds) |
| `projection_of_on_another_kind` | `invalid_projection_of` | `registry.parquet`, 17, `[projection_of]` (the note `note_1` states a `projection_of`) |

  The rows follow from the shared registry: 17 non-event rows (0 to 16:
  Bach's four elements, Handel's five, the five MatchClaims, the three
  parses), then its 16 event rows by timeline, start and ID: Bach's notes
  `note_1`, `note_2`, `note_4`, `note_3` on `clt_1` (17 to 20), Handel's
  `note_5`, `note_6`, `note_7` on `clt_2` (21 to 23), Handel's Projections
  `projection_5`, `projection_8` on `clt_3` (24, 25), Bach's
  `projection_1`, `projection_2`, `projection_9`, `projection_7` on
  `dpt_1` (26 to 29), Handel's `projection_3`, `projection_4`,
  `projection_6` on `dpt_2` (30 to 32); a row a case adds after the last
  is 33, `note_8` at the quarter 4 of `clt_1` is 21, and `note_9` appended
  to `part_b`, of three notes, is its row 3.

  Each list is exact, so a problem reported twice (by a package rule and
  again by a table check, as `axis_mismatch`, `duplicate_id` and the
  MatchClaim across two manifests would be) fails, as does one missed.
  The messages of the new rules are pinned in `test_packages.py`: `the
  package lists no table of the type Registry`, `the package lists a second
  table of the type Registry, first at #/tables/0/type`, the two of
  `duplicate_table`, `the package lists a second local table of the type
  Parse, first at #/tables/1/type` (`parse_table_listed_twice`, a second
  Parse table `old/parses.parquet`) and `the package lists a second local
  table of the type Note, first at #/tables/3/type`
  (`event_table_listed_twice`, a second local Note entry, the file
  `old/notes.parquet` of no row: a type has one local table, a file or a
  folder, whatever its files hold), `no manifest of
  the package holds both the timeline 'clt_1' and the timeline 'dpt_2'`,
  `no parse of the package has the ID 'parse_9'`, `the location
  'tables/Box/' names no table of the type Note in the package`,
  `the table 'tables/Note/' holds no row of the ID 'note_8'`,
  `no event row of the type Note in the registry has the ID 'note_9'`,
  `a Projection stands for an event of another timeline than 'dpt_1'`,
  `no manifest of the package has the timeline 'clt_9'`, `'projection_of'
  is set on a row of the kind 'Note'`, `the ID 'claim_1' is given twice,
  first in 'registry.parquet' at row 9`, the three of `registry_not_a_file`: `the
  registry 'registry/' names a folder; a registry is one Parquet file`
  three times (`package.yaml` and both manifests write the URL alike), and the three of
  `stale_non_event_row`: `the non-event row of the ID 'clt_1' at
  'bach.tts.yaml' has the kind 'VirtualTimeline', not 'Timeline'`,
  `the registry holds the non-event row of the ID 'region_9' at
  'bach.tts.yaml', which no manifest or table holds there`, `the
  registry lacks the non-event row of the ID 'group_1' at
  'handel.tts.yaml'`; and `foreign_table`'s, `the table
  'tables/features.parquet' of type 'Features' has no 'id' column: a
  package's tables hold the registry, the Parse table, MatchClaim
  tables and pre-parsed tables of events keyed by 'id'`. The case
  `foreign_table` carries, beside the shared package, a table entry of the
  type `Features` whose one file holds the column `x` (two floats) and no
  `id`: the check reports it, at the table, and goes on, so that it is
  its one problem (no crash, and no rule reads its rows). A case that
  adds a manifest element adds its non-event row as well, so that each case
  breaks its one rule; `registry_missing` drops the manifests' Registry
  resources with the registry, and no pre-parsed row is then compared.
  A Projection's `projection_of` is read from its registry row: the
  rules the row holds alone (its own timeline, another kind) are the
  registry's table check's, placed at the registry's row, the timeline no
  manifest of the package holds the package rule's. `table_listed_twice` is
  `validate_package`'s refusal (`the table 'tables/Note/' of the
  type Note is listed twice, first at #/tables/3/url`), which the
  JavaScript suite throws alike; `file_in_a_listed_folder` lists `part_b`
  of the folder of notes as a table of its own, a URL no validator
  can compare, and is the package check's: a second local Note table
  (`duplicate_table`, at its `type`, `the package lists a second local
  table of the type Note, first at #/tables/3/type`) whose one file the
  first reads already (`duplicate_url`, at its `url`, `the file
  'tables/Note/part_b.parquet' is read by the table
  'tables/Note/' already`), these two problems alone proving the file's rows
  are read once (read twice, each would be a `duplicate_id` of itself).
  Beside the fixtures, inline packages
  built in `tmp_path` prove what the fixtures leave out: a missing
  manifest (`missing_file`, `package.yaml`, `[manifests, 2, url]`, `no
  manifest lies at 'gone.yaml' in the package`), a missing folder
  (`missing_file`, `[tables, 4, url]`, `no folder lies at 'tables/Box/' in
  the package`), a table entry and a resource whose URLs lead outside the
  package (`missing_file` at the entry, then `unknown_table` at the
  resource, `the resource 'resource_3' names '../../outside/', which is no
  table of the type Box in the package`, then the missing non-event row of
  `resource_3`; a resource leaving the package names no table even where
  an entry leaves it too), the shared package with three external entries
  beside its local ones (two of the type `Note`, a file and a folder, one
  of the type `Parse`, all `https://example.org/...`) and a fourth `Note`
  entry `../elsewhere/notes.parquet` (exactly one problem: `missing_file`
  at `[tables, 7, url]`, `no file lies at '../elsewhere/notes.parquet' in
  the package`; no external entry is followed, none is a second local
  table, and an entry leaving the package is neither local nor external,
  so it is no `duplicate_table` either), a null timeline (`schema_violation` at the row
  and column, `'timeline_id' is null` for an event row of
  `parse_1.parquet`, `'timeline_a_id' is null` and `'timeline_b_id'
  is null` for a MatchClaim whose two timelines are null, each reported
  once although the registry's and the MatchClaim's table check word the
  same problem), a manifest of another version (`version_mismatch`, the
  manifest, `[timetoshare]`, `the manifest declares the version '0.1.0',
  the package '0.2.0'`), an invalid manifest (the validator's code and
  path, `resource_timeline` at `[resources, 0, timelines, 0]`, in that
  manifest's file; neither has its non-event rows compared), a MatchClaim ID
  twice in the folder of MatchClaims (`duplicate_id`, `the MatchClaim ID
  'claim_1' is given twice, first in 'tables/MatchClaim/part_a.parquet' at
  row 0`, once, though Bach's own check would report it too), and an
  event ID shared by a pre-parsed note and a pre-parsed row of
  another type (a `Box` file listing `note_1`, `duplicate_id` at the
  Box row, `the event ID 'note_1' is given twice, first in
  'tables/Note/part_a.parquet' at row 1`, then `unregistered_id`, no `Box`
  event row holding it): event IDs are unique across every type and file. A table whose files do not all hold
  an `id` column of strings is foreign whatever its type: a folder of
  `Box` files, one holding `id` and `label`, the other `label` alone, and
  a file of the type `Score` whose `id` is int64, are each exactly one
  `foreign_table` at the table (`tables/Box/`, `tables/scores.parquet`),
  in the order listed; the `Box` row with an ID in the first file is then
  no `unregistered_id`, since a foreign table's rows are read by no other
  rule.
  **Which resources name a table** is proved inline as well, every branch
  of the rule once: added to Bach's manifest in a copy of the shared
  package, a resource of the type `Image` at `score.png` without a media
  type, and one of the type `Text` at `notes.txt` with the media type
  `text/plain`, are carried, no problem; and each of four resources that
  `package.yaml` does not list is a table resource by one branch alone and
  is `unknown_table` at its `url`, in this order: `Recording` at
  `take.parquet` (its URL's `.parquet`), `Scan` at `scans/` (a folder),
  `Sheet` at `sheet.bin` with the media type
  `application/vnd.apache.parquet`, `Parse` at `more.arrow` without a
  media type (its type, one the format declares), each message `the resource '<id>' names '<url>',
  which is no table of the type <type> in the package`, then the missing
  non-event rows of the six resources added.
  The rule is public, `is_table_resource(resource)`, and answers each
  branch alone, without a package: `False` for the `Image` and the `Text`
  resource above, `True` for the `Recording`, the `Scan` and the `Sheet`
  above, for a `MatchClaim` at `claims.arrow`, a `Registry` at `registry.arrow` and a
  `Parse` at `runs.arrow` (their types; `Projection` is none of them, a
  Projection having no table) and for a `Note` at `Note.parquet?v=1#rows`
  (the URL's path is read, its query and fragment are not).
- **The package check reads columns, and checks each row once.** It finds
  its rules over the identifying columns of each table with
  `pyarrow.compute` and joins, reading Python values only at the rows it
  reports (and once per distinct location of the registry's rows). The
  registry and Parse checks run once over the
  whole table; the MatchClaim checks once per manifest and table, over
  that manifest's rows alone, found once for every row by its timelines'
  listings. A package whose registry holds its 17 non-event rows and
  20,000 event rows of the first parse
  over two manifests (`dpt_1` on the odd rows, `dpt_2` on the even), two
  of them sharing one ID, gives exactly one `duplicate_id`, and its table
  checks, recorded, are called exactly three times: the registry's (20,017
  rows, the non-event rows included, given the package's timelines `clt_1`,
  `dpt_1`, `clt_2`, `clt_3`, `dpt_2`, each once, in the order the
  manifests first hold them, as those a Projection may name), Bach's
  MatchClaims (3 rows), Handel's MatchClaims (2).
- **The fixture files are the script's.** `package.yaml` lists the
  registry file `registry.parquet`, the Parse file, the MatchClaim
  folder and the folder of notes `tables/Note/`; every file states its
  type and the version `0.2.0`, the MatchClaim file alone a shared
  provenance; the registry holds 33 rows, the non-event rows first, sorted
  by location and ID, timelines, resources, MatchClaims and parses, then
  the event rows, sorted by timeline, exact start and ID, those of the
  first parse with locators, those of the second and the third without;
  every note's row names `tables/Note/`, every Projection's has a null
  `location`, and a `projection_of` is stated on exactly the Projection
  rows; Handel's two rows on `clt_3` lie at 9/2 and 11/2, on the root's
  axis; the first parse's integrity is the SHA-256 digest of its source
  file `bach/alignment.csv`, which the package holds, the second and the
  third have no source.

## The table checks read columns, not rows

`match_claim_problems`, `registry_problems` and
`succession_problems` compute their rules over whole columns (`pyarrow.compute`); Python reads
only the cells a rule flags, to word their problems, one cell per
distinct provenance cell, which is checked against the provenance schema
once, and, against a manifest, the unit and number type of each timeline
a sound cell or an admitted event row lies on, once per timeline in the
order the rows first reach it. The change is meant to change no outcome,
only the time: the list of problems is the one the former reading row by
row gives, the same codes, rows, columns and messages in the same order,
for every table, and where the former reading raised, the same exception
with the same message. What proves it (`test_table_checks.py`):

- **The reference is the former implementation.** `table_checks_reference.py`
  holds the row-by-row checks as they were before the change, unchanged but
  for their imports and for the rules the format changed since, which it
  follows as the package must (the sentinels' reserved strings in the event
  ID columns, read by `is_synchronous`, a reserved string refused as an
  `id`, the package's message of an ID, and as a projected event's
  `event_id`, its message written in the reference; a `projection_of` set
  on a row of another kind, and one of the Projection's own timeline,
  each with its message written in the reference): the row loops (the axes
  of the timelines, the IDs, the nulls, each MatchClaim's rules, each
  registry row's, a Projection's `projection_of` among them, the
  succession rule) are its own, and the helpers the change left as they were (the
  schema shape check, the message of an ID, an axis or a number, the check
  of a provenance entry and of the file's) are imported from the package,
  so the comparison is of the rules, their order and the cells they read,
  while the wording is pinned by the exact messages of `test_tables.py`.
  The reserved-ID rule of an `id` takes its message from the package's
  ID function, so the comparison cannot fail on it alone: the inline exact
  cases of `test_tables.py` (`id_*_sentinel`, in the MatchClaim table and
  the registry) are what test it.
  It is no part of the package and nothing else reads it. Each comparison
  asserts that both implementations return equal lists of `TableProblem`
  (code, row, column and message, in order), or raise the same exception
  type with the same message, for the MatchClaim table without and with
  its manifest, and for the registry likewise. The registry's row loop
  reads an event row's axis and positions, the registry's nulls, its two
  scopes of IDs, its locators and a Projection's `projection_of` as the
  format states them, so the comparison proves the column rules equal to
  a reading row by row.
- **The fixture tables and every inline case.** The MatchClaim table and
  the registry of the table fixture,
  against their manifest and without; the inline tables of `test_tables.py`
  and every one of their rule cases (`CLAIM_CASES`, `PROVENANCE_CASES`,
  `PROJECTION_CASES`, on the registry, `REGISTRY_CASES`), so every code and every message
  the suite names is reached by both.
- **A manifest's timeline is read where a row reaches it.** The inline
  tables are checked against their manifest with one more timeline, `x`,
  that no row names, and against the manifest whose `dpt_1`, which the
  rows name, is that timeline instead; `x` is each of: the unit
  `furlongs`, no unit, the unit `5` (number type `int`), the number type
  `7` (unit `samples`), the unit null (number type `int`), the unit a
  list. Unnamed, none changes the outcome: both tables have no problem.
  Named, every one is an `axis_mismatch` at every cell or row on
  `dpt_1`. A unit that is missing or unknown, with no number type stated
  (`furlongs`, no unit), has no axis to compare with; the problem says so
  (`a coordinate in samples (int) on the timeline 'dpt_1', whose unit
  'furlongs' is unknown`, `..., which has no unit`). This case used to
  raise `KeyError` from the default number type's lookup, which made a
  server that checks a posted table without validating its manifest answer
  with an error instead of a problem; the reference was changed alike, so
  the comparison still proves identity. A list unit with a stated number
  type, `5`, `7` and null are worded with the value as Python prints it
  (`a coordinate in samples (int) on the timeline 'dpt_1' in None (int)`).
  A check that reads a timeline no row reaches, or compares a null unit as
  a column value (null equal to everything), fails here.
- **Seeded mutations.** 1,920 MatchClaim tables (160 per kind) and 1,000
  registries (100 per kind; the two provenance kinds do not apply to
  them), each drawn from its own stream
  `random.Random("20261122-tables-<kind>-<n>")` from a fixture table or an
  inline one (the inline MatchClaims also with a provenance in every row,
  against a manifest whose context declares `orcid`), checked against its
  manifest or, in about a third, without one, and changed once by its kind
  and up to twice by any row kind. The kinds: a
  null put in any column or any member of a cell (a coordinate's member, an
  anchor's coordinate, a provenance member, a belief, a projected event's
  member); any member set to a value of a pool written for its key (a
  registry row's `kind` an event type, a non-event kind, empty or null, its
  `location`, `parse_id`, `vanished_in`, `locator` and `projection_of`
  from small pools that repeat, a `projection_of` thus reaching rows of
  other kinds and the Projection's own timeline; IDs
  empty, holding a control character or a sentinel's string (in an `id`
  as well as in an event ID or a projected event's), certainties outside [0, 1] or not a
  number, anchors added or taken away, a flag flipped); an ID given again (a second row with another row's ID); a
  timeline ID replaced by an unknown one, by the other side's, or a cell's
  unit or number type replaced by another one, one that is no unit or
  number type, or one the unit does not admit, so that the first cell read
  on a timeline decides its axis in another row; a number's members filled
  for another number type, a denominator below 1, a non-finite or negative
  value; a bad provenance (an empty `stated_by`, a date that is no day, a
  word outside the schema's, an actor holding two beliefs written once
  compactly and once absolutely, a null belief) beside cells repeated
  across rows, so that one distinct cell stands for many rows; the file's
  provenance stated beside the rows' or malformed; the rows reordered, cut
  to none or to one, or a row repeated; the manifest given (never left out
  for this kind) with a bad timeline of the pool above added unnamed, or
  put in place of a timeline the rows name; the columns cut into chunks of
  random lengths; an undeclared column added dictionary-encoded, and a
  declared column dictionary-encoded (a `schema_violation`). Every kind is
  asserted to have yielded tables with problems and tables without, so no
  kind compares only the empty list.
- **The succession rule on pairs.** 700 pairs (70 per kind) of a table
  and a successor made by the row kinds above plus a row removed, a fraction
  respelled in other terms (`(1, 2)` as `(2, 4)`, the same coordinate), a
  float moved to the next double, an integer moved by one, a
  provenance changed, and a coordinate stated on one side alone (one
  table's cell null, the other's holding its number without a unit or a
  number type, or without both), the successor in chunks in about half:
  compared wherever both tables pass the checks, the rule's domain (at
  least 250 pairs, with breaches and without), and also wherever the
  reference returns at all on tables that do not, as long as both hold
  the declared column types; where the reference raises (a cell it cannot
  read: a null member, a denominator 0, a float that is not finite), the
  pair lies outside the domain and is not compared, and the column checks,
  which read only cells whose members differ, may answer there instead.
  Tables whose declared columns have another physical type on one side
  (`large_string` for `string`) are schema violations, outside the domain
  as well; neither the suite nor the column checks compare them. The
  smallest one-sided pair is also a case of its own: `claim_1`'s
  `start_anchor.coordinate_a` written `(1, 2, null)` without unit and
  number type in the old table and null in the new one is exactly one
  `succession_changed` at row 0, column `start_anchor`.
- **Text that is no UTF-8.** A string cell whose bytes are no UTF-8 cannot
  be read in Python, and the reference raises `UnicodeDecodeError` reading
  the table's declared columns, column by column in the type's order and
  row by row; so do the column checks, for the first such cell in the same
  order, with the same message: an invalid `id`, an invalid
  `start_anchor.coordinate_a.unit` and an invalid provenance actor in a
  MatchClaim table, an invalid `projection_of.event_id` of a Projection's
  registry row, an invalid `location` of a registry's non-event row, in the old and in
  the new table of a succession. The same bytes
  in a null slot of a string column, or in a member of a null struct, are
  never read and are no problem, by both.
- **Every flagged cell has its message.** Each rule exists twice, as a
  column mask and as the helper wording a flagged cell; a cell the mask
  flags and the helper finds sound would give a problem without a message,
  so the checks raise `AssertionError` (`no message for 'invalid_id' at row
  0`) instead, which a test proves by replacing the ID's message helper
  with one that finds every ID sound.
- **A larger table.** The 2,000-row MatchClaim table of `large_tables.py`
  (synchronous, interval, NOMATCH and conceptual rows over two timelines,
  and synchronous rows with `CHUNK_SENTINEL` on one side, instants and
  intervals, and on both sides),
  without and with a provenance in every row (84 distinct cells), has no
  problem by either implementation, and the same table changed thirty
  times by the row kinds, cut into chunks, has the same problems by both,
  and the same succession breaches where the reference reads it. Its
  manifest is checked also with the bad timelines above added, which no
  row names: no problem, by both. The same module builds the 250,000-row
  MatchClaim tables whose timings are measured outside the suite and never
  asserted.

The whole comparison runs in under a minute.

## Integer boundaries

Values whose integer length is `9007199254740993` (2^53 + 1) or
`9223372036854775807` (2^63 - 1) on a ticks axis validate and serialize back
to the same integer.

## The publication check

`scripts/check_published.py` assembles what a release serves under
`https://timetoalign.github.io/timetoshare/<version>/` and refuses a tree
whose addresses do not hold; both release jobs build their sites with it,
so a check that cannot fail would let a release publish documents whose
`$id` or `$ref` lead nowhere. `test_published.py` loads the script by its
path and proves both directions with `problems()`:

- The repository's tree is sound: `published()` holds exactly
  `0.2.0/catalogue.schema.json`, `0.2.0/package.schema.json`,
  `0.2.0/provenance.schema.json`,
  `0.2.0/tables.json` and `0.2.0/timetoshare.schema.json`, each byte for
  byte its file, and `problems(published())` is `[]`; a small hand-written
  tree (a document whose `$ref` names a member of another, a
  `tables.json` naming a schema served beside it) is sound as well.
- Each broken tree gives exactly its message, one per rule, each made
  from the sound small tree by one change: a `$ref` to a document not
  served (`0.2.0/a.json: c.json names a document not published`), an
  `$id` that is not the document's address (`0.2.0/a.json: its $id
  https://timetoalign.github.io/timetoshare/0.1.0/a.json is not its
  address https://timetoalign.github.io/timetoshare/0.2.0/a.json`,
  followed by `0.2.0/a.json: b.json#/$defs/Kept names a document not
  published`, since a reference is resolved against the `$id` the
  document claims, under which `b.json` is not served), a
  document without `$id` (`0.2.0/a.json: no $id`), a pointer naming no
  member (`0.2.0/a.json: b.json#/$defs/Missing names no member`) and a
  type of `tables.json` naming a schema not served
  (`0.2.0/tables.json: b.json names a document not published`).
- The real tree without `0.2.0/provenance.schema.json` gives the two
  messages of the two documents that refer to it, `tables.json` first.

A test that finds no problem in one of the broken trees fails, so the
check cannot become a check that passes everything.

## Packaging

The test builds the sdist and the wheel with `uv build` twice (the wheel
from the checkout, and from the sdist as the release does) and requires
`timetoshare/docs/description.md`, `timetoshare/docs/drawing.md`,
`timetoshare/schema/0.2.0/timetoshare.schema.json`,
`timetoshare/schema/0.2.0/package.schema.json`,
`timetoshare/schema/0.2.0/provenance.schema.json`,
`timetoshare/schema/0.2.0/tables.json`,
`timetoshare/catalogue/catalogue.yaml`,
`timetoshare/catalogue/catalogue.schema.json` and the five files of
`fonts/` in the wheel, the same under `src/timetoshare/` in the sdist, each
byte for byte the repository's file, and the root `LICENSE` in the wheel's
`.dist-info/licenses/` and at the sdist root. The five font files are both
TrueType files, both licences (`DejaVuSans-LICENSE`, `NotoMusic-LICENSE`;
the SIL Open Font License requires its licence to travel with the font) and
the metrics table `dejavu-sans-2.37+noto-music-2.004.metrics.json`, and the
font directory of each distribution holds exactly these, so a font shipped
without its licence fails. The `docs/` directory of each distribution holds
exactly the two specifications: the rest of the repository's `docs/` is the
documentation site's source and build (`conf.py`, generated pages, the
build output), which a package must not carry.

## Hermeticity

Tests obtain fixtures through package accessors, never relative paths. They
use no shared mutable input; the files a test writes lie in its own
temporary directory. Building the distributions needs `uv`, and the network
unless uv's cache already holds the build backend.

## The schema gate

`validate`, `unknown_keys`, `manifest_warnings`, `statement_problems` and
`matchstamp_problems` walk the value with `jsonschema` only where
`jsonschema-rs` does not find it valid. Every schema node the validator
checks (the closed document, `Timestamp`, and each member
`statement_problems` and `matchstamp_problems` check alone) has two
validators compiled from the very same schema: the walk, which builds every
diagnostic, and the gate. The gate is asked only where the value is plain
JSON data whose every float is finite (`plainly_finite`); there it answers
"valid" where it finds no error, or where every error it finds is one an
undeclared key alone causes (an `unevaluatedProperties` failure, or a
`oneOf`/`anyOf` one of whose branches fails by such failures alone), and
then lists the keys among them that the object holding them does not
declare, as the walk does. Where it finds any other error, raises, or is not
asked, the walk runs as it ran before. The finite rule's copy of the value
with bare IDs is skipped likewise where `plainly_finite` holds, and the ID
conversions copy JSON data without `copy.deepcopy`. The gate is meant to
change no outcome, only the time. Every outcome follows from four facts,
which the tests prove rather than compare transcripts
(`test_validator_parity.py`):

1. **The gate answers as the walk.** On plain JSON data whose every float
   is finite, the gate answers "valid" exactly where the one path rule
   (`select`) finds nothing among the walk's errors of the same schema, and
   where it answers "valid" the keys it lists are exactly those the walk's
   errors give. The diagnostics, codes, paths and messages come from the
   walk alone.
2. **The outcome is the walk's.** For every input, plain or not, the
   outcome of `validate` (the code, path and message it raises, else the
   unknown keys and the warnings), of `statement_problems` and of
   `matchstamp_problems` is the outcome with the gate removed, the walk
   running on every value.
3. **The finite rule is skipped only where it finds nothing.** Wherever
   `plainly_finite(value)` holds, the finite rule yields nothing on
   `leniently_bare_ids(value)`, the copy it would read.
4. **The copies are copies.** The ID conversions' copy of a value equals
   `copy.deepcopy` of it, has the same type at every node, and shares no
   list or dictionary with the input; `with_file_ids(with_bare_ids(value))`
   gives the manifest fixture back, sharing nothing with either.

Fact 2 covers what fact 1 leaves to the walk: `jsonschema-rs` reads a
tuple as an array, a dictionary subclass as a dictionary, `NaN` and the
infinities as `null`, and refuses non-string keys; none of these reaches
the gate.

The inputs, on each of which the four facts are asserted (fact 1 for the
closed document's root):

- every manifest fixture and minimal twin, every shared rejection case (the
  non-finite ones with their value in place), every shared warning case,
  and the two large manifests below;
- seeded mutations of the manifest fixtures, each drawn from its own stream
  `random.Random("20261123-<kind>-<n>")`, sixty of each of nine kinds: a key deleted from
  an object; a value replaced by one of another JSON type; an undeclared
  key added to an object; an element's ID given the ID of another element;
  a string replaced by another `const` or `enum` string of the schema (a
  renamed discriminator, a second matching `oneOf` branch); a key of one
  object copied into another; an item of an array repeated, or a pair of
  items equal as numbers but not under JSON Schema's equality appended to
  an array (`1` beside `True`,
  `1` beside `1.0`, `[1, 2]` beside `[1.0, 2]`, `{"a": 1}` beside
  `{"a": 1.0}`); a value replaced by a number that is not finite or lies
  beyond 2^53 (`NaN`, both infinities, `2**53 + 1`, `2**64`, `10**400`);
  and a value replaced by a Python value that is no JSON (`Fraction`,
  `Decimal`, a tuple, bytes, a complex number, `OrderedDict`,
  `defaultdict`, subclasses of `dict`, `list`, `str`, `int` and `float`, a
  dictionary whose `keys()` disagrees with its iteration, and keys that are
  integers, `None` or tuples). Every kind is asserted to yield both
  answers of the walk, valid and invalid manifests alike, and the kind
  adding an undeclared key a valid manifest with listed keys: the
  mutations of the kind are enumerated from the first, past the sixty
  where needed, up to the 3000th, and the first mutation giving each
  sought answer is found and the four facts asserted on it. So the
  assertion holds whatever the seed and the fixture set, as long as such a
  mutation is not rarer than about one in a few hundred (a repeated item
  or an appended pair is valid only in free data, such as an array in a
  `meta` object, or in an array taking repeats, such as `rules`);
- per definition, seeded: a sub-value of a manifest fixture is drawn, a
  definition of the schema whose walk accepts it is drawn, the sub-value
  is mutated by one of the operators above, and fact 1 is asserted for
  the gate and the walk of `{"$defs": ..., "$ref": "#/$defs/<definition>"}`.

Around the facts:

- **Keyword semantics.** A few small schemas pin what the gate must share
  with the walk where the package relies on it: `True` is neither `1` in
  `const`, `enum` and `uniqueItems` nor an integer, `1.0` is an integer,
  `unevaluatedProperties` counts the keys of the `oneOf` branch a value is
  valid under and not those of a failing one, and those of an `allOf`
  base and of an `if`/`then`/`else` arm. One difference is pinned as
  known: a `pattern` ending in `$` matches before a final line feed in
  Python's `re`, not in `jsonschema-rs` (which follows ECMA 262); the gate
  then refuses and the walk decides, so the outcome is the walk's.
- **An undeclared key below an `allOf` base.** A schema that fails gives
  no evaluated keys, so an undeclared key inside a value an `allOf` base
  holds (a key of a belief, inside a provenance entry, which is `allOf`
  the provenance record) fails the base, and both validators then report
  every key of the base on the closed object holding it as unevaluated
  too, besides the undeclared key where it stands; a small schema pins
  that both report them. Those keys are declared, so neither side lists
  them: the bare manifest with `provenance: [{property, value, beliefs:
  [{actor, belief, date, x: 1}]}]` lists the key `x` at
  `provenance/0/beliefs/0` and nothing else, through the gate (without one
  call to the walk) as through the walk.
- **Every entry point has its gate.** The root, `Timestamp`,
  `Graphical.matchstamps` and every member `statement_problems` checks
  (each subject's `provenance` and `statements`, the manifest's
  `@context`) have one, eight members in all.
- **The walk is skipped.** A valid manifest, the two large ones below
  included, validates without one call to the walk's validator (a counting
  validator), and so does a manifest with an undeclared key, whose key is
  listed; an invalid manifest calls it once.

The two large manifests are built in `large_manifests.py`: 500 root
timelines with 10,000 named timestamps (twenty per timeline), and 38 root
timelines each with a `LinearMap` and a `TableMap` whose `x_values` and
`y_values` hold 340 Fraction pairs, the shape of a DJ-software beat grid.
Their timings, and those of the largest fixture, are measured and
reported outside the suite, never asserted.

The gate's dependency is pinned to one minor version; a bump of it reruns
this file before the lockfile moves.

## Version steps and commit types

A dataset repository versions its manifests and tables by release tags; the
step a change requires (none, patch, minor, major, or refused) is the
format's rule table in the main README ("Versions of a dataset").
`test_version_step.py`, `test_commit_hooks.py` and `test_release_check.py`
prove it.

**The rule table, one case per rule.** `fixtures/versions/<case>/` holds
an `old/` and a `new/` tree of manifests and `expected.yaml` with the step,
the scope, the flags `refused` and `undetermined`, and the findings as
`{kind, step, id}` in report order (path, kind, ID), all written by hand:
each `new/` is one literal edit of the one base manifest in `old/` (a
quarters score with a child, three regions, a LinearMap, a flow-control
element, a statement and its provenance with a belief, two seconds takes,
a sketch, a group, a MeasureMap, a FlowMap and the virtual timeline
applying it, an audio resource with its digest, a rule, a named timestamp,
an elision, a named MatchStamp with two alignment anchors and their match
timestamps, and a prefix `ex` beside the default context), so a finding
the case does not name, or a missing one, fails the case. `tree_step(old,
new)` must give exactly `expected.yaml`. The cases cover every row of the
table: removals (major) of a root timeline, a child, a group, a MeasureMap,
a conversion map, a flow-control element, a FlowMap (with the virtual
timeline applying it), a virtual timeline, a resource, a named timestamp,
a named MatchStamp (with its anchors and match timestamps), an alignment
anchor (with its one match timestamp no other anchor names), a group
member, a statement pair and an `@context` prefix; additions (minor) of a
region, a member, a pair and a prefix; edits (minor) of a prefix's IRI, an
offset, a unit, a number type, a length, a LinearMap's scalar, a named
timestamp's coordinate, a FlowMap's chunks and a pair's value; patches of a
belief added and one changed by its actor, a `name`, a `graphical` rule,
an elision added, edited and removed, a named timestamp's `display`,
`meta` and a resource moved with equal integrity; an ID changed (a removal
and an addition), a manifest file removed and added, and an ID given to an
element of another type (refused). Four cases prove that nothing is a
change of the data: the minimal and the complete form of one manifest, its
YAML rewritten as JSON (`base.tts.yaml` to `base.tts.json`), the same text with
comment lines, and the numbers of the LinearMap and a MeasureMap row
respelled (`2.0` as `2`, `[1, 2]` as `[2, 4]`, `[3, 1]` as `3`). Every
manifest of the cases validates, which a test asserts file by file. Beyond
the table, the fixture manifests of `fixtures/0.2.0/` against their
minimal twins, and each against itself, give no finding, which proves that
comparison happens in the complete form and in canonical order on every
element type the format has.

**What the cases cannot hold.** Inline in the tests: a manifest declaring
another format version gives the one finding `unsupported_version`,
undetermined, and no other; the scope is the first directory when the
findings lie in two manifests of one directory and none when they lie in
two top-level manifests; one manifest file gives its name without
`.tts.<ext>` (`bpsd/op106.tts.yaml`, `bpsd/op106.tts.json` and the
top-level `op106.tts.yml` all `op106`, `op106.minimal.tts.yaml`
`op106.minimal`); two manifests under one top folder give the top folder
(`bpsd`), under two none; and the findings are sorted by path, kind and ID
whatever order the changes were made in. **Which files are manifests.**
`tree_step` takes as a manifest only a file named `<name>.tts.yaml`,
`.tts.yml` or `.tts.json`: beside `x.tts.yaml`, a `package.yaml` listing no
tables and a plain `notes.yaml`, both holding `timetoshare`, are neither
compared nor read, so removing both from the later tree, or making them
unreadable there, gives no finding, while the same removal of `x.tts.yaml`
gives `removed_manifest` (that a `.tts.json` rewrite of a `.tts.yaml` is
the same manifest is the case `yaml_to_json`). Numbers by value: the LinearMap's
`scalar` and `offset` written `2`/`[1, 2]`, `[2, 1]`/`[2, 4]` and
`[4, 2]`/`0.5` give no finding against `2.0`/`[1, 2]`; an offset `0.1`
against `[1, 10]` is `edited` (a float's exact binary value); a break's
`passes` `[1, 2]` against `[2, 4]` is `edited` (two integers where the
schema admits no Fraction pair stay two numbers); `meta` with `1` against
`1.0` is `meta`, patch (literals as written). A manifest whose new text no
longer parses gives `unreadable_manifest`, undetermined, never
`removed_manifest`, naming the later tree; the reverse names the earlier.

**Tables.** The table cases need Parquet files, which the fixture rules
let only `scripts/emit_tables.py` write into `fixtures/`, so the tests
write them into their temporary directory from the table fixture's
MatchClaim table (`fixtures/tables/0.2.0/match_claims.parquet`) beside a
manifest naming it: dropping the row `claim_18` gives `removed_row`, major,
ID `claim_18`; the reverse gives `added_row`, minor; a belief of
`claim_6` changed (its provenance otherwise unchanged) gives `belief`,
patch; its `event_a_name` changed gives `edited_row`, minor. Without
pyarrow (its import made to fail) and for a resource of another type whose
bytes differ, the change is `changed_table`, undetermined, and the step
does not rise.

**Git.** `git_step` against a temporary repository: the step between two
commits equals the step between their trees, the staged change is read
from the index (a change left unstaged is not seen), and `HEAD` in a
repository without commits is the empty tree, so a staged manifest is
`added_manifest`; a staged `notes.yaml` holding `timetoshare` gives no
finding. Only manifests and the files their resources name are
read: a repository holding a manifest marked `export-ignore`, the audio
file its resource names and an unrelated text file materialises exactly
the manifest and the audio file on both sides, and the changed audio is
`changed_table`, undetermined. The files a manifest names are found
however it is written: the same repository with the manifest as
`base.tts.json`, or in YAML with `resources` in flow style and the URL
double-quoted with an escape (`"take\x5f1.flac"`), materialises the same
two files and gives the same finding; for every manifest and
`package.yaml` of `fixtures/` (228 documents naming 420 files, both
counts exact, so a fixture added or dropped is seen), the files found
named are exactly those the `url`s of its resources or tables name as
`loads` reads it. Hostile YAML is read so that it names every file
`loads` would: a top-level key `"[]"` before `resources` (which `loads`
reads) names `a.flac`, as `loads` does; `resources: {"[]": {url: x}}`
names nothing, as `loads` does, and raises nothing; a tag, an anchor
with its alias, and a second document, each refused by `loads` (which
names nothing then), name the files their resources list (`a.flac`; the
alias adds none; both documents' `a.flac` and `b.flac`). A document that
is no YAML (an unclosed flow sequence) or no UTF-8, or names a URL that
cannot be parsed (`http://[x`), may name any file and is read as naming
an unknown set; in the repository with the failing filter of the hook
tests, such a manifest committed beside the base manifest makes staging
`README.md` alone reach the comparison. A table
file is read through the filters its path's attributes name, as a
checkout writes it, and once where both states hold it unchanged: a
filter storing the MatchClaim table as base64 text (`base64 -w0` to clean, `base64 -d` to
smudge, standing in for Git LFS's pointer) leaves a blob starting `UEFS`
(no Parquet file), and dropping `claim_18` from the staged table still
gives `removed_row`, major (read unfiltered, `changed_table`); a smudge
filter that counts its runs runs once for the table when only the manifest
naming it is staged, and twice when the table itself is. **History**: with tags `v1.0.0` (the sketch
held) and `v2.0.0` (removed), staging the sketch again gives `added`
without `history` and `added` plus `reused_id`, refused, with it, the
detail naming both tags; so does the commit of it. With `v1.0.0` (region
`region_1`), `v1.1.0` (without it) and `v2.0.0` (`region_1` a timeline),
`v1.1.0` to `v2.0.0` adds `reused_id` "was a Region in v1.0.0 and is now a
Timeline", while `v1.0.0` to `v1.1.0` is a plain removal. The command
exits 0 without `--history` and 2 with it, printing the refused line, and
refuses `--history` over two directories.

**Commit types.** The suggested header of every case's report is fixed
(`remove(base)!: `, `feat(base): `, `belief(base): `, `label(base): `,
`graphic(base): `, `meta(base): `, `move(base): `, none for no step), the
patch type of a mixed report follows the count and then the order belief,
label, graphic, meta, move, and the trailer is the `BREAKING CHANGE:
removes #sketch` footer of a removal alone (a removal with an addition
included: no line counts the smaller changes), empty otherwise. The hints
are held to their exact lines: a patch gives the line `Suggested type
"<header>", since this commit <does> only`, one wording per kind (beliefs,
names, the drawing, application data, resources moved), and `, among other
changes` instead of ` only` where patch kinds mix; a minor or a major step
gives no suggestion, and neither does a message that already has a type,
which keeps only the line counting the kinds of a mixed change. A report whose findings fall into more than one of the
kinds added, edited, removed, belief, label, graphic, meta and move adds
the line `This commit mixes <n> kinds of change (<count> <kind>, …); one
kind of change per commit keeps the history and the changelog clear.`, the
counts in that order (the ID changed: `1 added, 1 removed`); a refused or
undetermined finding is no kind of change. `check_message` is held to its
exact errors and warnings. Errors: an understated type where the change
requires a minor or a major step (`label` for an added region, `feat` for a
removal), a removal written `feat!`, `fix!`, `feature` or `remove` without
`!`, a header with an empty subject (with and without the space after the colon), a reused ID,
and a missing header where the change requires a minor or a major step.
Warnings, the commit passing: a missing header or a type without a step
(`chore`) on a patch-level change, each naming the change and the suggested
type (`suggested type: label(base):`); `feature` for an addition passes; an
overstated data type or `!` (`feat!` for an addition, `fix!` for no change
of the data), `remove` without `!` on a commit that removes nothing (a
changed name, no change of the data: that warning alone; an added region:
beside the error asking for `feat`), a `BREAKING CHANGE` footer on a
commit that removes nothing,
a footer missing a removed ID and an undetermined change. A correct message
gives neither, and merges, fixups, squashes, amends and reverts are not
checked. With the comment character `;`, lines starting with `;` and
everything below `;`'s scissors line are ignored and a line starting with
`#` is message text.

**The hooks.** Each runs in a temporary git repository with git's global
and system configuration switched off, once called as the command line
does and once installed as git hooks in `.git/hooks` and run by `git
commit`, which proves that the staged tree reaches the hook as git hands
it over and that git strips the hook's comment lines. The message and the
standard error are compared exactly. `prepare-commit-msg` writes a type
only for a minor or a major step: it turns `-m "add the second region"`
into `feat(base): add the second region` and writes `remove(base)!: ` and
the footer for a removal. For a patch it writes no type: with `-m` (source
`message`) the message stays as given and the suggestion goes to standard
error, prefixed `timetoshare: `; in an editor template (no source, or
`template`) the suggestion is a comment line, followed by a lone comment
character, before git's comment lines, with git's comment character (also
with `core.commentChar` `;`). The hint of a mixed change goes the same two
ways (the ID changed: the removal's header and footer in the message, the
hint on standard error or as a comment line), and the message never holds
a line counting the smaller changes. With `commit.cleanup` set to
`scissors` or `verbatim`, with which git keeps comment lines, an editor
template stays as it was and the suggestion goes to standard error;
through `git commit` with `scissors` and an editor writing a subject above
the template, the commit holds the subject alone and standard error the
suggestion. A message that already has a type (`label(base): x`,
`data(base): x`, `feat(base):` without a subject) on a mixed change stays
as it is and gets the mixed hint alone, on standard error with `-m` and as
a comment line in an editor template; the same message on a change of
names only gets nothing. Through `git commit`: `-m "add the
second region"` commits `feat(base): add the second region`; `-m "rename
the score"` on a changed name commits exactly that message, exit 0, the
suggestion and `commit-msg`'s warning on standard error; with an editor
that writes a subject above the template it was given, the template the
editor received starts with the suggestion's comment line, and the commit
holds the subject alone. The hooks leave the message untouched and print
nothing for an amend (source `commit`, given as an argument or by
pre-commit's `PRE_COMMIT_COMMIT_MSG_SOURCE`), a merge and a commit with
no change of the data.
**Only data is compared.** The hooks compare the two states only where a
staged path, before or after, is a manifest file, a `package.yaml` or a
file a manifest's resources or a `package.yaml`'s tables name. Proved by
behaviour, never by watching a function: a repository whose committed
`take_1.flac`, the file the base manifest's resource names, sits behind a
required smudge filter that fails (`filter.broken.smudge = false`) cannot
be compared at all, and every comparison there ends in `commit-msg`
exiting 1 with `timetoshare: the staged change cannot be read: `. Staging
`README.md`, `release-please-config.json` (a `.json` that is no
manifest) or `code/align.py` there leaves `-m "describe the dataset"`
untouched with nothing on standard error, and `commit-msg` passes `docs:
describe the dataset` with nothing on standard error; `remove: x` passes
with the one warning `remove names a removal; this commit removes
nothing`, and `docs:` alone fails with the empty-subject error, as on any
change of no data. Staging `take_1.flac` itself, or renaming
`base.tts.yaml` to `score.tts.yaml` (`git mv`, a rename `git diff -M`
pairs), reaches the comparison: exit 1 and that message. In a repository
of the base manifest the same rename is compared exactly: `docs: rename`
is refused as removing `base.tts.yaml` (`removed_manifest` with
`added_manifest`). A staged table that a manifest names is compared:
beside `claims.tts.yaml`, whose MatchClaim resource names
`match_claims.parquet` (the table fixture's rows), staging the table
without the row `claim_18` refuses `docs: x` as removing that row.
Amends are judged by the paths staged against the amended commit's
parent: in the repository with the failing filter, amending a commit that
only added `code/align.py` with another change to it commits silently,
while amending a commit that changed `take_1.flac` (made with
`--no-verify`) with a change to `code/align.py` alone still reaches the
comparison and is refused with that message. A commit taking paths
beyond the index is judged by the paths it takes (git hands the hooks
a temporary index): in the repository with the failing filter, `git
commit -a -m "docs: x"` over a change to the committed `code/align.py`
alone commits silently, and over a change to `take_1.flac` is refused
with that message; with a change to `take_1.flac` staged, `git commit
code/align.py -m "docs: x"` over another change to `code/align.py`
commits silently (and leaves `take_1.flac` staged), and `git commit
take_1.flac -m "docs: x"` is refused with that message. A message is
compared with `UNREAD` by its start (`startswith`): what follows is
git's own report of the failing filter, whose wording differs by git
version and platform. `commit-msg`
exits 0 for a message it accepts, 0 with the warning on standard error for
a patch-level change without a type, and 1 with the error on standard
error for an understated one, and `git commit` then makes no commit.
**Amend**: after a commit removing the sketch, `git commit --amend` whose
editor writes `label(base): x` is refused (the amended commit's parent, not
`HEAD`, is compared with the index), the commit stays and the recorded
file is gone; `--amend --no-edit` keeps the removal's message. Amending the
first commit compares with the empty tree: `docs: x` is refused as adding
the manifest. pre-commit's `PRE_COMMIT_COMMIT_MSG_SOURCE=commit` and
`PRE_COMMIT_COMMIT_OBJECT_NAME=HEAD` record `HEAD`'s commit in
`timetoshare-amend-base`; `commit-msg` then refuses `label` for the
removal and deletes the file, so the next check compares with `HEAD`
again.

**The release check.** `release_step(old, new)` is held to a table of
exact values: from 1.0.0 on the first number that rises names the step
(`1.2.3` to `2.0.0` major, to `1.3.0` minor, to `1.2.4` patch, `1.9.0` to
`1.10.0` minor, numbers compared as numbers); below 1.0.0, as release-please
reads a dataset repository's two pre-major settings, the middle number
allows a major step and the last a minor one (`0.3.0` to `0.4.0` major,
to `0.3.1` minor, `0.3.4` to `1.0.0` major); equal versions allow none.
`release_allows` says the step in words, held to exact values: `any
change` for a major step (`0.0.0` to `0.1.0`), `changes up to minor`
(`1.2.3` to `1.3.0`, `0.3.0` to `0.3.1`), `changes up to patch` (`1.2.3`
to `1.2.4`), `no change` for equal versions. A
lower version (`1.2.3` to `1.2.2`) and anything but three numbers without a
leading zero (`v1.0.0`, `1.0.0-rc.1`, `01.0.0`, `1.0`) are refused with
their exact messages. `release_problem` returns `None` where the release
allows at least the change's step (a major change in `0.3.0` to `0.4.0`,
no change in equal versions, a patch in `1.0.0` to `1.0.1`) and otherwise
the exact sentence naming both versions and both steps ("allows changes
up to minor; the change requires major" for `0.3.0` to `0.3.1` under a
removal, "allows no change; the change requires minor" for `1.0.0` to
`1.0.0` under an addition). OLD `-` is the empty tree:
against a repository's one commit holding the base manifest it gives the one finding `added_manifest`, minor, with and
without `--history`, and with a directory as NEW it is refused like any
mix of a directory and a reference.

**`timetoshare release-check`** (`test_release_check.py`). Each case is a
temporary repository whose commits hold one base manifest of the version
cases and a `.release-please-manifest.json` with the version `"."`; the
expected output is the exact text. `HEAD` is a release when that version
is not `0.0.0` and has no tag `v<version>`; the data compared runs from the
nearest tag matching `v[0-9]*` reachable from `HEAD` (other tags, `draft`
on `HEAD` itself, are passed over), or from the empty tree, to `HEAD`, with
the history of the tags. Without a tag at `0.0.0` it prints `no release:
the version 0.0.0 is no release`, the data from the empty tree, the step
and the finding `added_manifest`, and exits 0; at `0.1.0` without a tag it
is the first release, `release: 0.1.0 is the first release; it allows
any change` (from `0.0.0`), and `passes`. With `v0.1.0` tagged and the version `0.1.0`, a
later removal is reported (`is tagged v0.1.0`) and exits 0. At `0.1.1`
after `v0.1.0` a removal `fails` with `release_problem`'s sentence and
exits 2, while an added region `passes`, an addition taking the last
number below 1.0.0. Restoring the sketch at `0.2.1` after `v0.1.0` held it
and `v0.2.0` removed it fails as `a change is refused`. A table of the
type Note whose bytes change gives `changed_table`, undetermined: at a
release (`0.2.0` after `v0.1.0`) it `fails: a change is undetermined` and
exits 2 although the release allows any change; at the tagged `0.1.0`
it is reported and exits 0. `--summary FILE` appends to FILE `### Release
0.1.1: fails` (or `### No release`), a blank line and the printed lines in a
`text` code block. A missing `.release-please-manifest.json` and one
without `"."` exit 1 with their message on standard error, nothing on
standard output, and the summary `### Release check: error`; a version
below the last tag's (`0.1.9` after `v0.2.0`) exits 1 with
`release_step`'s message.

**`timetoshare validate`.** Every case is a file written in the test's
temporary directory, and each expected line is the exact text the command
prints, `<path>: <code> at <JSON pointer>: <message>`; the codes and
messages of the rules are the validator's, held by the rejection cases, so
these tests prove the command's choice of files and its reports, not the
rules. The base manifest of the version cases is accepted silently; a
manifest without `@context` prints its one warning (`warning:
context_absent at #: the manifest has no @context`) and exits 0. Each
refusal exits 1: a manifest without `timelines` (`schema at #`), one whose
second timeline repeats the first's ID (`duplicate_id at #/timelines/1/id`,
the validator's first violation only), one of the version 0.1.0
(`unsupported_version at #/timetoshare`), a manifest written with a YAML
anchor that `loads` refuses (`unreadable at #`, `loads`'s message), a text
no reader reads, and bytes that are not UTF-8, each with a line starting
`timetoshare:`. A text `loads` refuses is refused exactly when it names
the format at the top: in YAML a line starting with the key, quoted or not
(`"timetoshare": "0.2.0"` before a broken list), and a text starting with
`{` as JSON, an object holding the key (`timetoshare` twice, which `loads`
refuses) or, where it is no JSON, the key anywhere in it, quoted (a JSON
object left open) or not (a YAML flow mapping); a manifest followed by a
second YAML document is refused too. Files that are no manifests are
skipped without a line: an object without `timetoshare`, a JSON array, a
YAML file with an anchor, a YAML file of two documents, an `mkdocs.yml`
with a `!!python/name:` tag, a broken YAML file holding `timetoshare:` only
nested, a broken JSON text with the key `timetoshare_version`, and bytes
that are not UTF-8 without the key. A file named explicitly is read
whatever its name: every case above names files without `.tts.`
(`plain.yaml` gives its warning). Without arguments the command reads
every file named `<name>.tts.yaml`, `.tts.yml` or `.tts.json` under the
current directory, sorted, subdirectories included, skipping `.git` (a
refused manifest there prints nothing) and every other file: a refused
manifest written to `package.yaml`, `notes.yaml` or `base.json` there
prints nothing. It prints each path relative to that directory.

**The hooks of the repository.** `.pre-commit-hooks.yaml` at the
repository root is read and compared, hook by hook, with the hooks the
README's configuration names (the fourth, `timetoshare-registry`, is held
in "The registry" below): `timetoshare-commit-type`
(`prepare-commit-msg`), `timetoshare-commit-check` (`commit-msg`) and
`timetoshare-validate` (`pre-commit`, files `\.tts\.(ya?ml|json)$`, so
that `package.yaml` is not passed to it,
`verbose: true` so that warnings show; the two others not verbose), each
`language: python` with the one additional dependency `./python[tables]`;
every entry, with a file name appended, parses as a subcommand of the
command. pre-commit itself installing them from a clone needs the package
index, so no test here does it: CI's job "Pre-commit hooks" runs
`pre-commit try-repo . timetoshare-validate --files
fixtures/tables/0.2.0/tables.tts.yaml`, which installs the root distribution and
`./python` as a dataset repository's clone does and accepts that fixture;
the two commit hooks are checked by hand, `pre-commit try-repo <checkout>
<hook id> --hook-stage <stage>` in a git repository holding a manifest.


## The registry: non-event rows, resolving, the registry command and version steps

A package's registry holds one row per resolvable ID: the **event rows**
(an event's position on the axis of its timeline's root, its parse,
its locator) and the **non-event rows** of everything else with an ID (each
element of each manifest, each MatchClaim, each Parse), which are
derived and rebuilt from their sources. `timetoshare.tables.registry`
builds and checks the non-event rows and resolves an ID; `timetoshare registry`
rewrites or checks them; the version step compares the event rows, a
Projection's among them. `test_registry.py` proves the first three and
`test_version_step.py` the last; both need pyarrow. Each test builds its
package in its temporary directory: the manifests written with `dumps`,
`package.yaml`, and the Parquet files written directly in the columns the
format declares for the registry and the Parse table (literal rows in the
test, never through the module under
test), so a test cannot pass by agreeing with itself.

**The non-event rows.** The test package holds two manifests at its root,
`bach.tts.yaml` and `handel.tts.yaml`, both holding a timeline `shared` (the IDs of
elements repeat across manifests) and between them every kind of element:
the manifest's own ID, a root and a child timeline, a region and a
flow-control element on a timeline, a conversion map with a nested map, a
group, a MeasureMap, a resource of each kind, a FlowMap and a virtual
timeline, a named timestamp, an elision, a named MatchStamp with an
alignment anchor; a MatchClaim folder of two files and a Parse
table. `non_event_rows` gives exactly the literal table of the test, in the
registry's columns and order: one row per element (its `kind` the
schema's definition name, `location` its manifest's URL as `package.yaml`
lists it, `timeline_id` the holding timeline of a region or flow-control
element and the `timeline` of a named timestamp or elision, null for every
other kind; no name, which the manifest holds), one per MatchClaim
(`location` the MatchClaim entry's URL) and one per Parse (the
Parse entry's URL), every other column null, sorted by `location`
then `id` by code point. A manifest that does not validate gives no rows.

**Writing the non-event rows.** The registry is one file,
`registry.parquet`, holding three event rows (on `score`, `shared` and
`aria`, written in that order; the one on `shared`, the Projection
`proj_1`, has no `location` and names in its `projection_of` the note
`note_1` of `score`) and no non-event row.
`write_non_event_rows` returns that file's path and rewrites it to hold
exactly the rows of `non_event_rows` first, then the three event rows,
cell for cell, by timeline (`aria`, `score`, `shared`), with the file
metadata `timetoshare:type` `Registry` and `timetoshare:version` `0.2.0`;
no file starting with `.` is left beside it. A missing file is written with
the non-event rows alone. A file holding two event rows and a stale
non-event row afterwards holds the fresh non-event rows and the two event
rows. Event rows keep every value as written: a start written `2/4` stays
`(2, 4)`, a further column `velocity` of the file keeps its values, and
an event row of a kind the format does not know is kept: no rewrite drops
or alters a row it does not own. A package whose `package.yaml` lists no
Registry table is refused with `package.yaml lists no table of the type
Registry`; one whose Registry entry names a folder (`registry/`) with `the
registry 'registry/' names a folder; a registry is one Parquet file`, by
`write_non_event_rows`, `stale_non_event_rows` and `resolve` through the
package alike, and `resolve` through a manifest whose Registry resource
names a folder with the same message; the
command prints it after `timetoshare: ` and exits 1.

**The order of a registry file.** `write_registry` writes every row it is
given, the non-event rows first, by `location`, then `id`, then the event
rows by `timeline_id`, the exact value of `start` and `id`, strings by code
point. The proof is an input whose order is the reverse of the expected one
and whose starts a double cannot tell apart: on one fraction timeline the
starts `1/3` and `6004799503160661/18014398509481984` (the double nearest
1/3, read exactly, a smaller value), `2/4` and `1/2` (one value, so ordered
by ID), and on one int timeline `9007199254740993` and `9007199254740992`
(2^53 + 1 and 2^53, one double); the file holds the rows in exactly the
order the test lists by hand. A registry whose `start` column holds
strings, which its table check refuses, is still written whole, its event
rows by timeline and ID, every value kept. Writing the shared package fixture's rows
reversed gives back its file's rows in its order, and
`write_non_event_rows` over a copy of the shared package leaves its
registry's table equal to the fixture's, metadata included.

**Stale non-event rows.** `stale_non_event_rows` of a freshly written
package is empty. Then each difference gives one problem, code
`stale_non_event_row`, file the registry file (`registry.parquet`), held
to the exact message: a region added
to a manifest after the write (missing: row null, path `["id"]`, "the
registry lacks the non-event row of the ID 'region_9' at
'bach.tts.yaml'"), a group removed (extra: its row in the part, "the
registry holds the non-event row of the ID 'pair' at 'bach.tts.yaml',
which no manifest or table holds there"), a named timestamp moved to
another timeline (differing: row 17 of the file, path `["timeline_id"]`, "the
non-event row of the ID 'ts_1' at 'bach.tts.yaml' has the timeline_id
'score', not 'shared'"), the score timeline renamed in the same change (no
problem: the registry holds no names, so a rename leaves the rows fresh),
and a MatchClaim added to the MatchClaim folder (missing, at the MatchClaim
entry's URL). The problems are in this order: the file's non-event rows in
their order (extra or differing), then the missing rows by location and
ID. A registry holding event rows alone lacks every non-event row. Only `kind`
and `timeline_id` are compared: the other columns of a non-event row are
null by the format.

**One comparison of the non-event rows.** `stale_non_event_rows` and the
package check compare the non-event rows alike, by one function: over the shared package and
every acceptance and rejection under `fixtures/packages/0.2.0/` whose
`package.yaml` lists exactly one registry, a file, over a copy of `shared/` whose
Handel manifest is made invalid (a unit spelled `quarter`), and over a
copy whose `package.yaml` writes every URL with a leading `./`,
`stale_non_event_rows(root)` equals the `stale_non_event_row` problems of
`package_problems(root / "package.yaml")`, in order. The two copies give
none: locations are compared resolved against the package root, so
`./bach.tts.yaml` and `bach.tts.yaml` are one location, and an
invalid manifest's non-event rows are not compared. `write_non_event_rows` of the copy
with the invalid manifest keeps its non-event rows at `handel.tts.yaml`
cell for cell, since they cannot be rebuilt, and the copy is still not
stale.

**The names are public.** `timetoshare.tables` exports `Resolution`,
`resolve`, `non_event_rows`, `write_non_event_rows`, `stale_non_event_rows`
and `write_registry`,
each the object `timetoshare.tables.registry` holds, and
`ELEMENT_KINDS`, the non-event kinds but `MatchClaim` and `Parse`.

**Resolving reads filtered.** With the module's `read_table` wrapped to
record its calls, `resolve` of an event ID and a MatchClaim ID through
the package root, and of a Parse ID, a MatchClaim ID and an event ID
through a manifest, gives its usual answer and reads each registry with
`ids` of the one ID, a filter `read_table` pushes into the reader
(above, "Packages"); the Parse found through Bach's manifest adds one
read of the `parse_id` column alone with Bach's listed `timelines`,
whether an event row of the manifest names it. No registry is read whole.

**Resolving.** `resolve(path, id)` always returns a list. Through the
package root: an event ID gives its one registry row (`kind`, `location`,
the row as a dictionary, `manifest` null); the ID of the timeline
`shared`, held by both manifests, gives two resolutions, one per manifest,
each with its manifest; a MatchClaim's and a Parse's ID give their
non-event rows; an unknown ID gives `[]`. Through a manifest file: the
element with the ID first, with its non-event row, then the registry rows that
belong to the manifest: an event row whose timeline the manifest's
Registry resource lists (an event on a timeline it does not list is not
found through it), a MatchClaim row of a table its MatchClaim resources
name, a Parse row named by one of its event rows (a Parse only
the other manifest's events name is not found). Every resolution through
a manifest names that manifest. A written `#id` is read as the bare ID
(`#shared` and `shared` give the same list). A
manifest without a Registry resource resolves its own elements with the
row null and nothing else.

**The command and the hook.** `timetoshare registry PACKAGE` writes the
non-event rows into the registry file and prints `wrote registry.parquet`,
exit 0, the file then holding the non-event rows and the three event rows;
without PACKAGE it takes the current directory. `--check` on the
fresh package prints nothing and exits 0, writes nothing (the file's bytes
unchanged); after a region is added it prints one line per problem,
`<file>: row <row>: stale_non_event_row: <message>` (`<file>: stale_non_event_row:
<message>` for a missing row, which has none), and exits 1, still writing nothing. A folder without
`package.yaml` exits 1 with one line on standard error starting
`timetoshare:`. `.pre-commit-hooks.yaml` holds the hook
`timetoshare-registry`: entry `timetoshare registry --check`, stage
`pre-commit`, `pass_filenames: false`, `always_run: true`, the language
and dependency of the other hooks; its entry parses as the command.

**Version steps over the registry.** Hand-authored cases under
`fixtures/versions/`, each an `old/` and a `new/` package (`package.yaml`,
the manifest `score.tts.yaml` with the quarters timeline `score` and the
seconds timeline `take`, the registry `registry.parquet`, a Parse table;
the registry's event rows on `score` are the MIDI notes `note_1` and
`note_2` and the Projection `proj_1` of the onset `onset_1` of `take`,
which lies in the registry alone), the
`new/` one edit of the one `old/`:

| Case | Change | Findings |
| --- | --- | --- |
| `registry_row_removed` | the event `note_2` removed from the registry | `removed_row`, major |
| `registry_row_added` | an event `note_3` added | `added_row`, minor |
| `registry_projection_moved` | the start of the Projection `proj_1` moved | `edited_row`, minor |
| `registry_row_vanished` | `vanished_in` of `note_2` set | `vanished_row`, minor |
| `registry_non_event_rows_only` | the timeline `score` renamed, its non-event row rewritten | `label`, patch (the manifest's finding alone) |
| `projection_row_edited` | the `projection_of` of `proj_1` edited (`onset_2` for `onset_1`) | `edited_row`, minor |
| `projection_row_removed` | `proj_1` removed from the registry | `removed_row`, major |

Every finding lies at the manifest whose Registry resource lists the
row's timeline (`score.tts.yaml`, scope `score`). The cases' manifests
validate and their registries' non-event rows are not stale (`stale_non_event_rows`
empty). Their
other Parquet files are `scripts/emit_versions.py`'s: for each case the
script names (exactly the seven), each tree's event rows of the registry
(its rows whose kind is no non-event kind, in the file's order) and Parse
table equal, cell for cell and with their metadata, the tables the script
builds from its literal rows.
Inline: an event row whose timeline no manifest's Registry resource lists
lies at `package.yaml`; with two manifests listing one timeline, a removed
row is reported at both; a vanished row's detail names the parse
(`row note_2 of registry.parquet, vanished in the parse parse_2`); without
pyarrow a changed registry is `changed_table`, undetermined, at the
`package.yaml` listing it, and the step does not rise. `git_step` reads
the registry file from git and gives each case's `expected.yaml` for the
staged change of `registry_row_removed` and `projection_row_edited`.
The suggested commit type follows the step (`remove(score)!: ` for the
removed row, `feat(score): ` for an added, moved, vanished or edited one;
a vanished row counts as an edit) and no case gives a hint.
