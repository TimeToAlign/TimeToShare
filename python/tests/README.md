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
   schema document, `docs/drawing.md`, the catalogue with its schema and
   the licence.
7. `timetoshare.statements` reads and writes the property–value pairs of
   the bundle, its timelines and its regions with their provenance, and
   `timetoshare.catalogue` reads them in words through the catalogue of
   identifier systems, verbs and types, with the same values, the same
   errors and the same messages as the JavaScript package; an independent
   JSON-LD processor reads the statement fixtures to the expected RDF.

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
- **The public definitions.** The definitions include the seventeen public
  ones `Manifest`, `Timeline`, `Group`, `Graphical`, `ConversionMap`,
  `Coordinate`, `Number`, `Fraction`, `TimeUnit`, `NumberType`, `Id`,
  `MeasureMap`, `MeasureMapRow`, `Context`, `Statements`, `StatementValue`
  and `ProvenanceEntry`, and the root's
  description, which tells a host what it may refer to, names exactly
  these, in this order.
- **The map types.** `ConversionMap` chooses between exactly the ten types
  `ChainMap`, `CombinationMap`, `ConstantMap`, `FloatingMeasureMap`,
  `LinearMap`, `MeasureBeatMap`, `MeasureNumberMap`, `MeasureRecordMap`,
  `PiecewiseMap` and `TableMap`, and `Selector.class` names exactly the six
  timeline classes and these ten types. `Selector.facet` and an `Address`'s
  `facet` refer to `Facet`, exactly the five facets `markers`,
  `conversion_maps`, `children`, `regions` and `flow_control`, and the words
  of an `Address`'s `part` to `Part`, exactly `start`, `end`, `name`,
  `label`, `card`, `line`, `id` and `coordinate`. The words of a
  `Timestamp`'s `display` are exactly `TIMESTAMP_DISPLAY`, `wedge`, `name`,
  `id`, `coordinate` and `cross_section` in that order, so the canonical
  order the writers apply cannot drift from the words the schema admits.
  `ElementType` is exactly the eighteen types `block`,
  `timeline`, `child`, `band`, `map`, `region`, `flow_marker`, `jump_from`,
  `wedge`, `name`, `label`, `boundary`, `ancestor`, `frame`, `card`,
  `cross_section`, `alignment_anchor` and `ancestor_card`.
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
  `FlowControlElement.target` and the `measure_map` of each of the four measure views
  refer to `Id`, the items of `Selector.addresses` to `Address`. `Id`, an
  ID written `#` followed by the ID, accepts `#score`, `#Bass Kick`,
  `#perf/take 2`, `#https://example.org/piece/score#exposition`, `#start`,
  `#regions_1`, `##x` and `# `, and refuses `""`, `#`, `score`, `score#`,
  `#score` followed by a tab, `#score` followed by a newline and `#`
  followed by U+001F; every address below writes its ID so. `Address` accepts `{}`,
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
  U+001F, and an entry of an `Order` has the same two keywords. The five
  patterns that still end in `$`, `Paint`, `stroke-dasharray`, a
  provenance entry's `date`, a resource's `media_type` and its
  integrity's `digest`, are exactly those the document holds, and each
  refuses a value it accepts (`none`, `4 2`, `2026-11-17`,
  `application/vnd.apache.parquet`, `00ff`) once a newline follows it; no
  ID has a pattern of its own (a named timestamp's, a resource's, a
  MatchStamp's and an anchor's are any `Id`); an `Order` refuses
  `["line\n"]`. The JavaScript suite
  asserts the same values, so the two validators cannot part on a
  trailing newline.
- **Defaults agree with the table.** For every kind of `DEFAULTS` the
  schema's corresponding definitions (`Manifest`, `Timeline`,
  `Region`, `FlowControlElement`, `MeasureMap`, `Group`, `Graphical`,
  `Timestamp`, every conversion map) declare `default` on exactly the keys
  of that kind's table, each equal to the table's value, and on no other
  key; a conversion map's kind is `conversion_map`, joined by `linear_map`
  for a `LinearMap` (`scalar` 1, `offset` 0) and by `table_map` for a
  `TableMap` (`kind` `linear`, `extrapolate` `none`); a flow-control
  element's kind is `flow_control_element`, joined by `repeat_end`
  (`repeat_count` 1), which `complete` applies to a `repeat_end` only, since
  no other element may carry a repeat count: the schema states that one
  default in the `then` arm of the `if` that tests for a `repeat_end`, and
  not on the shared `repeat_count` property, so a reader that supplies
  every default it finds on a property never writes `repeat_count` to an
  element that must not carry it. A key's default is
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
`repeat_count`, a free value) keeps its spelling, and a value that has no
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
`end`, a flow-control element's `coordinate`) is a bare Number whose representation the axis's number type
selects: an int axis an integral JSON number, a float axis any JSON number
that a float equals exactly (an integer beyond 2^53 may have none), a
fraction axis a pair. The axis is the timeline's `number_type`, else its
unit's default (`int` for ticks, samples, frames, pixels; `fraction` for
quarters, whole_notes; `float` otherwise). A child's offset lies on its
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
- `start`, `end` and the `coordinate` of a flow marker, a jump origin and a
  jump target each reported at its own path with its holder's ID.

Accepted: `8` and `8.0` on an int axis (an integral number is an int),
`8`, `0.5`, `9007199254740992` (2^53) and `10**20` on a float axis (each
exactly a float), `[8, 1]` and `[8.0, 1]` on a fraction axis, `length:
null` anywhere, a root's negative offset in its own number type. The checks
visit a timeline's offset, length, regions and flow-control elements, then
its children in array order; the first problem is raised.

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
  empty `unknown_keys` in the three cases of warnings, `context_absent`,
  `bundle_blank_statements` and `bundle_blank_provenance`); the
  JavaScript suite asserts the same lists. `several_depths` holds unknown keys on the
  manifest, a timeline, a child, a region, a flow marker, a jump origin, a
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
  literal input. A region, a flow-control element (a `repeat_end` gains
  `repeat_count` 1 besides, no other element does), a group, a MeasureMap, a conversion map (and the maps nested in a
  `ChainMap`, a `CombinationMap` and a `PiecewiseMap`), a `LinearMap`, a
  `TableMap` and a `graphical` object each gain exactly their table's keys.
  A named timestamp without `display` gains `display: ["wedge", "name",
  "cross_section"]`, and nothing else; one stating `["cross_section",
  "wedge", "name"]` completes to `["wedge", "name", "cross_section"]` and
  minimizes without `display`, as the default in another order is still
  the default; one stating `["name", "wedge"]` completes to `["wedge",
  "name"]` and keeps it in the minimal form; one stating `[]` keeps `[]` in
  both forms.
  The unit default of `number_type` is stated for ticks (`int`), seconds
  (`float`), whole_notes (`fraction`), pixels (`int`), and the two
  vector-graphics units css_pixels and user_units (`float`).
- **Never added, never removed.** `id`, `graphical` and a root's `offset`
  are absent from the completion of a manifest without them; a present
  `graphical: {}` completes to its four keys (`styles`, `rules`,
  `order`, `timestamps`) and minimizes to `{}`; a
  child's `offset` stays in the minimal form.
- **Values that differ from the default stay.** `locked: true`,
  `number_type` `float` on quarters and a `repeat_end` with `repeat_count` 2
  survive `minimal`, the element keeping only its own non-default keys.
- **Numbers compare by value.** `repeat_count: 1.0`, a `LinearMap`'s
  `scalar` `1.0` and `[1, 1]` and its `offset` `0.0` and `[0, 3]` equal
  their defaults 1 and 0 and are left out by `minimal`; `repeat_count: 2.0`
  and `scalar` `[1, 2]` stay; `false` is not the number 0 and `0` is not
  `null`. A named timestamp's `display` given `["name", "wedge",
  "cross_section"]` and a child's `offset` `[4, 8]` on quarters are compared
  after canonical order and respelling, so the `display` is left out and the
  offset written `[1, 2]`.
- **Unknown keys pass through** both functions, at every depth, untouched.
- **`length` survives** both, `null` included.
- **The round trips.** For each of these documents (a `repeat_end` with
  `repeat_count: 1.0` among them) and for every fixture,
  `minimal(complete(x)) == minimal(x)`, `complete(minimal(x)) == complete(x)`
  and both results validate; both functions return new objects and leave
  their input unchanged. The first equality compares the canonical YAML
  texts, which tell `1.0` from `1`; the second compares the RFC 8785 JSON
  texts, which compare numbers by value, since `minimal` leaves out a
  `repeat_count: 1.0` that `complete` then restores as `1`.

## The rules and their codes

`validate` checks in this order and raises the first violation as a
`SchemaValidationError` carrying `code`, `path` and `message`: the version
marker; `finite_number`; the schema, in one walk that also collects the
unknown keys; `representation`; then the semantic rules in the order of the
table, the statement rules last, root by root for the first six (a root's duplicates, then its
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
| `dangling_target` | a jump origin's `target` names a jump target of its timeline; then, map by map, a measure view's `measure_map` names an entry of `measure_maps` | the target, the `measure_map` | `'there' names no jump_to of this timeline`, `'ghost' names no MeasureMap of this manifest` |
| `conversion_map` | a non-null `source_unit` of a map attached to a timeline is the timeline's unit, and that of every map a `PiecewiseMap` or `CombinationMap` holds, and of a `ChainMap`'s first map, is its holder's non-null `source_unit`; a `TableMap`'s x and y values of equal length, its x values strictly increasing; a `PiecewiseMap`'s maps one fewer than its breaks, its breaks strictly increasing | the `source_unit`, the `y_values`, the value, the `maps`, the break | `MeasureRecordMap 'bars' has source unit 'quarters', its timeline 'score' has 'ticks'`, `LinearMap 'scale' has source unit 'ticks', its ChainMap 'chain' has 'quarters'`, `TableMap 'tempo' has 3 x values and 2 y values`, `x value [0, 1] of TableMap 'tempo' does not exceed the one before it`, `PiecewiseMap 'sections' has 1 map for 3 breaks; it needs 2 maps`, `break [4, 1] of PiecewiseMap 'sections' does not exceed the one before it` |
| `child_unit` | a child has its parent's unit | its `unit` | `child 'take' has unit 'seconds', its parent 'score' has 'quarters'` |
| `child_offset` | a child starts within the parent's known length | its `offset` | `offset 75.0 of 'take' is beyond the length 60.0 of its parent 'recording'` |
| `child_end` | else, it ends within it | its `length` | `child 'coda' ends at [12, 1], beyond the length [10, 1] of its parent 'score'` |
| `segment_line` | segments contiguous from 0 to the length, one flag | the segment's flag or offset, the line's `length` | `segment 'b' of segment line 'line' does not start where the one before it ends` |
| `duplicate_id` | every ID unique across the manifest: each root's tree, in the order above, against the earlier roots' (an ID repeated inside one root counts once), then each group ID, then each MeasureMap ID, then each named timestamp's ID, against every ID before it | the later ID | as above |
| `manifest_id` | the manifest ID is no other ID of the manifest | `id` | `'g2' is not unique in the manifest, first at #/groups/1/id` |
| `group_member` | a member names a timeline and neither contains nor lies inside another member of its group | the member | `'ghost' names no timeline of this manifest`, `member 'b' lies inside member 'a' of the same group` |
| `order_key` | a `graphical.order` key names a group or a timeline | the key | `'g9' names no group or timeline of this manifest` |
| `display_order` | a group's order permutes its members | the entry, then the order | `'x' is not a member of group 'g'`, `member 'b' of group 'g' is missing` |
| `band_order` | a timeline's order lists `line` and any of the five facets | the entry, then the order | `'annotations' is not 'line' or a facet, in the band order of 'score'`, `'line' is missing from the band order of 'score'` |
| `timestamp_timeline` | a named timestamp's `timeline` names a timeline of the manifest, at any depth | its `timeline` | `'ghost' names no timeline of this manifest` |
| `timestamp_coordinate` | its `coordinate` lies from 0 to its timeline's length, from 0 on where the length is null | its `coordinate` | `coordinate [9, 1] of 'timestamp_1' is beyond the length [8, 1] of its timeline 'score'`, `coordinate [-1, 1] of 'timestamp_1' lies before the start of its timeline 'score'` |
| `context` | a manifest whose manifest, timeline or region carries `statements` or `provenance` holds `@context` | the first such key in subject order, `provenance` before `statements` | `statements and provenance need the manifest's @context` |
| `reserved_key` | no key of the manifest, a timeline, a region or a group begins with `@` (but the manifest's `@context`), holds a `:`, is a term of the context the element may not use or names a prefix of `@context` | the key | `'label' is reserved on a timeline` |
| `iri` | subject by subject: the ID of an element with statements is an IRI fragment; every compact IRI names a prefix of `@context`, unless it is `//`-absolute or of the schemes `info`, `mailto`, `tag`, `urn` | the `id`, the key or value | `the ID 'Bass Kick' of an element with statements is no IRI fragment`, `'wdtt:P175': the prefix 'wdtt' is not declared in @context` |
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
alone.

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
the 179 cases of `fixtures/rejections/0.2.0/` breaks one rule and stores the
path, the code and the message (`test_validate.py`); `validate` raises
`SchemaValidationError` with exactly all three, and the JavaScript suite
holds its validator to the same three, so the two packages refuse every
case at one path with one code and one message. The codes of the cases are
exactly the thirty of the table, so every code is reached by a case both
suites read. `version_unknown` raises `UnsupportedVersionError` and stores
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
disappear unnoticed. Twenty-two cases pin their message too (`test_identity.py`
and `test_statements.py`):
`child_unit_differs`, `child_offset_beyond_parent`, `child_end_beyond_parent`,
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
of a case states its `display`.

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
- **No reserved IDs.** The part words of an address (`start`, `end`,
  `name`, `label`, `card`), names shaped like a band (`regions_1`,
  `flow_control_907`) and IDs holding
  a slash, a space, a colon or a `#` (`perf/take 2`,
  `https://example.org/piece/score#exposition`) are accepted as the ID of a
  timeline, a map, a map held by a `ChainMap`, by a `PiecewiseMap` and by a
  `CombinationMap`, a region, a flow marker, a jump origin, a jump target,
  a group, a MeasureMap and the manifest: `identity_problems` finds nothing
  and `validate` accepts each manifest.
- **Containment.** A child's end is its offset plus its length, or, for a
  segment of unknown length, its successor's offset. Where the parent's
  axis and the child's are both `float`, the offset and the length are
  added as doubles, as a reader adds the JSON numbers it reads, and that
  sum is compared with the parent's length; wherever either axis is `int`
  or `fraction`, the values are added and compared exactly. The end is
  spelled in the parent's number type, a fraction pair where that type has
  no exact spelling: `0.2` at `0.1` in `0.3` seconds ends at
  `0.30000000000000004`, their double sum, `0.5` at `0.5` in `0.75` at
  `1.0`, `240` ticks at `480` in `480` at `720`, a quarters child declared
  `float`, `2.5` at `[7, 1]` in `[8, 1]`, at `[19, 2]`, and a seconds child
  declared `fraction`, `[1, 3]` at `0.5` in `0.75`, at `[5, 6]`; `0.25` at
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
  containment: where the line's axis and the segment's are both `float`,
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
  and at the line's length, and so are they on the `float` line where `b`
  alone is declared `fraction`, its length the pair: one problem, at `c`'s
  offset. Where a segment's offset and length have no
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
- **Flow control.** The schema ties each element type to its
  manifestations, its `target` and its `repeat_count`: the three `da_capo`
  manifestations and a `repeat_end` without a target validate
  (`test_validate.py`), a `dal_segno` without one is refused at the element; a jump origin whose target names a flow marker, or a jump target
  of its child, is one `dangling_target` at that `target`, naming the target
  (`'fine' names no jump_to of this timeline`).
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
  none. An order keyed by a region's ID is one `order_key`.
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
| `resource_timeline` | `resource_timeline_unknown` | `'take_3' names no timeline of this manifest` |
| `resource_type` | `resource_match_claim_twice` | `a manifest names at most one resource of the type MatchClaim; 'resource_1' is one` |
| `resource_type` | `resource_projection_twice` | `a manifest names at most one resource of the type Projection; 'resource_2' is one` |

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

Every other fixture under `fixtures/0.2.0/` yields the empty dataset, both
forms: a manifest without statements says nothing in RDF. `rdf_expectation`
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
measure view's `source_unit` other than `quarters` the unit, a `target` on a
jump target or a `repeat_count` on a `to_coda` the member, a `dal_segno`
without a `target` the element.

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
   `the key 'repeat_count' is not admitted here`.
3. A `not` refusing a pattern, or any of several patterns and words, names
   the value, the part of it the refused branch finds (the first branch
   that finds one) and what is not admitted, in the words of the schema's
   description where it has them: a character is named as itself where it
   is printable and no whitespace, else by its code point. `'#a\tb' holds
   U+0009: no control character (U+0000 to U+001F) is admitted here` for an
   ID (and for every other string the schema closes against control
   characters: an order entry, a paint, a dash array, a media type, a
   digest); `'match claims.parquet' holds U+0020: no whitespace and no
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
of a flow-control element (`repeat_count` on a `dal_segno` and on a
`da_capo`, `target` and `repeat_count` on a jump target or a flow marker);
and the eleven `not` places (an ID, an order entry, a paint, a dash array,
a resource's media type and its digest, an IRI, an IRI reference with each
of its three branches, a prefix's IRI, a language tag, a prefix name with
each of its two branches), each message stated literally, at the path the
walk reports.

## The canonical order

Every array whose order carries no meaning has one order: `timelines` by ID;
in every timeline `children` by offset then ID, `conversion_maps` by ID,
`regions` by start, end, ID, `flow_control` by coordinate then ID; `groups`
by ID and `members` by code point; `measure_maps` by ID;
`graphical.timestamps` by timeline (code point), then coordinate, then ID.
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
  the README's name for every file, and never raises. Values are compared
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
  jump_to and the jump_from targeting it, a group, a MeasureMap, a
  timeline's and a group's `graphical.order` entry, a rule with an address
  and `within`, a named timestamp), plus the unknown key `extra: score` on
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

## Manifest files

`file_form(text)` gives a `FileForm`: whether the manifest is `minimal`,
whether it holds its `styling` (the top-level `graphical` key) and its
`serialization` (`serialization_of`). `dumps_file(value, form)` drops a
top-level `graphical` unless `form.styling`, writes the minimal form if
`form.minimal`, else the complete form, and writes it in
`form.serialization`. They live in `timetoshare.files`. The form is
minimal when `minimal(value)` and `value` write the same canonical YAML,
the equality the twin law of the fixtures uses: a key stated at its
default, recognized by exact value (`repeat_count: 1.0` is the default
`1`), makes a text not minimal, and the order canonical order sorts does
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
written by hand (`test_fixtures.py`). For every fixture: `validate` accepts
it, `unknown_keys` and `manifest_warnings` list nothing (every fixture
states the format's `@context`), `dumps` reproduces it, and the two round
trips of `complete` and `minimal` hold. The folders are `.`, `bundles`,
`groups` and `statements`, 172 files (`test_files.py`); the four statement
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
- **Flow-control IDs by type.** Across the complete fixtures, every
  flow-control element whose ID has the generated form `<prefix>_<N>`
  carries its own `type` as the prefix: exactly `flow_marker_1` (three
  elements), `jump_from_1` to `jump_from_4` (six, two, one and one) and
  `jump_to_1` to `jump_to_3` (three, two and one). Every other flow-control
  ID is one a builder names (`fine`, `da-capo`, `da_capo_al_fine`,
  `dal_segno`, `repeat`, `segno`). A prefix taken from another type (a flow
  marker `break_1`, a jump target `marker_1`, a jump origin `jump_1`) fails
  the test.

## The graphical object

`docs/drawing.md` section 4's defaults block (three styles, 35 rules),
read from the file, validates as the `graphical` of the smallest file; the
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
  code point added.** Independently of the extraction script, the test
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

`timetoshare.tables` (the extra `tables`, pyarrow) holds the two table
types a package keeps beside its manifest: the MatchClaim table
(`match_claims.parquet`) and the Projections table (`projections.parquet`).
The tests (`test_tables.py`, `test_tables_anchors.py`) need pyarrow, a
development dependency; without it they are skipped, as the font
extraction's are without fontTools. What proves them:

- **The columns are the declared ones.** `MATCH_CLAIM_COLUMNS` names, in
  this order, `timeline_a_id`, `timeline_b_id`, `start_anchor`,
  `end_anchor`, `is_synchronous`, `provenance`, `certainty`,
  `event_a_id`, `event_a_name`, `event_b_id`, `event_b_name`, `id`;
  `PROJECTION_COLUMNS` `id`, `timeline_id`, `unit`, `number_type`,
  `start`, `duration`, `projection_of`. A number is the struct `numerator`,
  `denominator` (int64), `value` (float64), the type of a Projection's
  `start` and `duration`; a coordinate cell is a number followed by `unit`
  and `number_type` (strings); an anchor the struct `coordinate_a`,
  `coordinate_b`, its timelines the
  row's `timeline_a_id` and `timeline_b_id` (an anchor cell holding the
  timeline IDs as well is another type, `schema_violation`);
  `projection_of` the struct `timeline_id`, `event_id`. The
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
  (`tables_path()`) is the one source of both schemas: its `types` declare
  `number`, `coordinate`, `anchor` and `projection_of` as Arrow structs of
  named members and `provenance` as the struct read from the provenance
  schema it names; its `tables` give each table a `status` and its
  `columns` in order, each a `name`, a `type` (one of the four type names
  `string`, `bool`, `int64` and `float64`, Arrow's utf8, bool, int64 and
  double, or a type of `types`) and whether it is `nullable`. The test
  reads the file and
  pins it: its `$id` is
  `https://timetoalign.github.io/timetoshare/0.2.0/tables.json`, its
  sections are exactly `types` and `tables`, the MatchClaim table is
  `stable` and the Projections table `experimental`, the `coordinate`'s
  members are the `number`'s followed by `unit` and `number_type`, and
  `provenance` names `provenance.schema.json`, a file beside it.
  `MATCH_CLAIM_SCHEMA` equals, field by field, a literal list of its
  twelve columns with their Arrow types written out in the test
  (`timeline_a_id` string, …, the anchors the struct of two coordinate
  structs, `provenance` the struct of the eight members, `certainty`
  double, …, `id` string), and `PROJECTION_SCHEMA` its seven; every Arrow
  field is nullable, so a writer need declare nothing, and the columns the
  file marks `nullable: false` are exactly those a null is refused in
  (`timeline_a_id`, `timeline_b_id`, `is_synchronous`, `id`; `id`,
  `timeline_id`, `unit`, `number_type`, `start`), each proved below, and
  `MATCH_CLAIM_REQUIRED` and `PROJECTION_REQUIRED` are these tuples. Every
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
  `number_type` or from the one given for a Projection's number, and
  reads nothing from a member its number type leaves null.
- **Each rule refuses its smallest counterexample and nothing else.** A
  valid table of a few rows is built inline; each rule is proved by
  changing one cell (or one column type) and asserting the exact list of
  problems `(code, row, column)` and the message of the first, which
  `check_match_claims`, `check_projections` and `check_succession` raise
  as `TableError`. The valid table itself yields no problem, with and
  without its manifest. The rules: a missing column or a column of
  another type (`schema_violation`; a Parquet round trip, which renames
  list items, changes nothing; a column the type does not declare is
  kept, as an unknown key is); a null in `id`, a timeline or
  `is_synchronous` (`schema_violation`); an empty ID or one with a control character
  (`invalid_id`); an ID twice in a table (`duplicate_id`, at its second
  row: `the ID 'claim_1' is given twice`, `the ID 'projection_1' is given
  twice`), a Projection's ID as much on two timelines as on one, since a
  Projection's ID is unique in the package as every event's; a `scope`
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
  the member); a row naming no event
  (`claim_events`); both timelines the same (`claim_timelines`); NOMATCH (one event null) that is
  synchronous or has an anchor, a conceptual row (two events, not
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
  (`axis_mismatch`); a Projection whose `projection_of` lacks a member or
  names its own timeline (`invalid_projection_of`), whose row's `unit` or
  `number_type` is null (`schema_violation`) or unknown
  (`invalid_coordinate` at that column), whose row's number type its unit
  does not admit (`'samples' admits no number type 'fraction'`,
  `invalid_coordinate` at `number_type`), whose `start` or `duration`
  breaks the number rule of the row's number type (`invalid_coordinate`
  at that column), whose `duration` is negative (`invalid_duration`), two
  Projections of one timeline whose rows state two units
  (`axis_mismatch` at `unit`) or two number types its unit admits
  (seconds as float and as fraction, at `number_type`),
  and a `projection_of` column holding a joined string
  (`schema_violation`).
- **A fraction in any terms is its value.** No check asks a fraction
  cell for lowest terms: an unreduced fraction is read, and it is the
  same value as its reduced form wherever cells are compared. The
  MatchClaim table with `claim_2`'s start anchor written `(2, 2, null)`
  (the quarter 1) or `(0, 4, null)` has no problem, with and without its
  manifest, and `coordinate_value` reads the two cells as exactly `1` and
  `0`; so does the Projections table whose third row, moved to the
  quarters of `clt_1`, starts at `4/2` (read as `2`) or starts at `7/2`
  and lasts `2/4` (read as `1/2`). Its anchors are the reduced table's:
  `alignment_anchors` gives the table with `(2, 2, null)` exactly the
  anchors and MatchClaim IDs of the table with `(1, 1, null)`. A test
  that refuses one of these cells, or reads it as another value, fails.
- **Against a manifest.** Given a manifest (as read from its file), every
  timeline a cell or a row names exists (`unknown_timeline`) and every
  cell, every Projection's row, is in its timeline's own unit and number
  type (`axis_mismatch`): seconds on a samples timeline and a float on a
  fraction axis are refused, the same cells and rows without a manifest
  are not. A number type the unit does not admit is no question of the
  manifest: a MatchClaim's `samples` cell as `float` and a Projection's
  `samples` row as `float` are refused as `invalid_coordinate`, at the
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
  of an event, two Projections without a source joined by one claim, a
  NOMATCH row, a conceptual row, a row one actor believes false and another
  true, a row believed `unlikely` (kept by the default filter, dropped by
  the believed-true one, kept again by the unlikely-and-false one, which
  splits the chain it closes) and a child timeline whose coordinates never
  meet its parent's. Its Projections table holds each number type of the
  cell form: int instants and an int interval on the samples timeline, a
  float instant and a float interval on the seconds timeline, and a
  fraction interval (start 7/2, duration 1/2) on the child timeline in
  quarters, so every reader of the shared tables meets a fraction and a
  float duration. Without an actor the row believed false still gives
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
  for one actor, which partitions the fifteen rows, the default, and
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
- **The fixture files are the script's.** The two Parquet files read back
  equal to the tables the script builds, the manifest equal to the
  script's manifest of the files written, and both tables pass every
  check against that manifest. The manifest names the two tables in its
  `resources` (`resource_1`, `MatchClaim`, `match_claims.parquet`;
  `resource_2`, `Projection`, `projections.parquet`), each with the media
  type `application/vnd.apache.parquet`, the size of the file in bytes, its
  SHA-256 digest (both computed by the test from the file) and, in the
  manifest's order, exactly the timelines its table names. Each
  Projection a MatchClaim names stands on that side's timeline at the
  anchor's coordinate, its duration spanning to the end anchor; the
  fixture's eleven Projections are all named but the last two, the
  fraction interval and the float interval. The Projections table's rows
  lie sorted stably by `timeline_id`, each timeline's in the order the
  script lists them: `projection_10` on `clt_2`, `projection_7` and
  `projection_11` on `cpt_1`, then `projection_1` to `projection_6`,
  `projection_8` and `projection_9` on `dpt_1`, the order in which a
  writer holding the Projections per timeline writes them, so that such a
  writer's file can equal the fixture's byte for byte.

## The table checks read columns, not rows

`match_claim_problems`, `projection_problems` and `succession_problems`
compute their rules over whole columns (`pyarrow.compute`); Python reads
only the cells a rule flags, to word their problems, one cell per
distinct provenance cell, which is checked against the provenance schema
once, and, against a manifest, the unit and number type of each timeline
a sound cell or an admitted Projection lies on, once per timeline in the
order the rows first reach it. The change is meant to change no outcome,
only the time: the list of problems is the one the former reading row by
row gives, the same codes, rows, columns and messages in the same order,
for every table, and where the former reading raised, the same exception
with the same message. What proves it (`test_table_checks.py`):

- **The reference is the former implementation.** `table_checks_reference.py`
  holds the row-by-row checks as they were before the change, unchanged but
  for their imports: the row loops (the axes of the timelines, the IDs, the
  nulls, each MatchClaim's and each Projection's rules, the succession
  rule) are its own, and the helpers the change left as they were (the
  schema shape check, the message of an ID, an axis or a number, the check
  of a provenance entry and of the file's) are imported from the package,
  so the comparison is of the rules, their order and the cells they read,
  while the wording is pinned by the exact messages of `test_tables.py`.
  It is no part of the package and nothing else reads it. Each comparison
  asserts that both implementations return equal lists of `TableProblem`
  (code, row, column and message, in order), or raise the same exception
  type with the same message, for the MatchClaim table without and with
  its manifest, and for the Projections table likewise.
- **The fixture tables and every inline case.** The two Parquet files of
  the table fixture, against their manifest and without; the inline tables
  of `test_tables.py` and every one of their rule cases (`CLAIM_CASES`,
  `PROVENANCE_CASES`, `PROJECTION_CASES`), so every code and every message
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
  Projections tables (100 per kind; the two provenance kinds do not apply
  to them), each drawn from its own stream
  `random.Random("20261122-tables-<kind>-<n>")` from a fixture table or an
  inline one (the inline MatchClaims also with a provenance in every row,
  against a manifest whose context declares `orcid`), checked against its
  manifest or, in about a third, without one, and changed once by its kind
  and up to twice by any row kind. The kinds: a
  null put in any column or any member of a cell (a coordinate's member, an
  anchor's coordinate, a provenance member, a belief, a projected event's
  member); any member set to a value of a pool written for its key (IDs
  empty or holding a control character, certainties outside [0, 1] or not a
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
- **The succession rule on pairs.** 600 pairs (60 per kind) of a table
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
  MatchClaim table, an invalid `projection_of.event_id` in a Projections
  table, in the old and in the new table of a succession. The same bytes
  in a null slot of a string column, or in a member of a null struct, are
  never read and are no problem, by both.
- **Every flagged cell has its message.** Each rule exists twice, as a
  column mask and as the helper wording a flagged cell; a cell the mask
  flags and the helper finds sound would give a problem without a message,
  so the checks raise `AssertionError` (`no message for 'invalid_id' at row
  0`) instead, which a test proves by replacing the ID's message helper
  with one that finds every ID sound.
- **A larger table.** The 2,000-row MatchClaim table of `large_tables.py`
  (synchronous, interval, NOMATCH and conceptual rows over two timelines),
  without and with a provenance in every row (84 distinct cells), has no
  problem by either implementation, and the same table changed thirty
  times by the row kinds, cut into chunks, has the same problems by both,
  and the same succession breaches where the reference reads it. Its
  manifest is checked also with the bad timelines above added, which no
  row names: no problem, by both. The same module builds the 250,000-row
  tables whose timings are measured outside the suite and never asserted.

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
  `0.2.0/catalogue.schema.json`, `0.2.0/provenance.schema.json`,
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
`timetoshare/docs/drawing.md`,
`timetoshare/schema/0.2.0/timetoshare.schema.json`,
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
without its licence fails.

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
then lists those keys. Where it finds any other error, raises, or is not
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
  `random.Random("20261122-<kind>-<n>")`, of nine kinds: a key deleted from
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
  answers of the walk, valid and invalid manifests alike; the kind adding
  an undeclared key is asserted to yield valid manifests with listed keys;
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
