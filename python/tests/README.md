# Test strategy for the `timetoshare` Python package

This suite proves the public contract of schema 0.2.0: one manifest shape,
described by one schema document, read by one validator. The package
supports this version only.

Every rule is proved by a document written inline in its test, never by
editing a fixture: the documents are the smallest that exercise the rule, so
a passing test cannot be a restatement of a fixture the implementation
produced. The shared rejection and warning cases (`fixtures/rejections/0.2.0/`
and `fixtures/warnings/0.2.0/`) are read by this suite and by the JavaScript
suite, so both validators are held to the same paths and the same lists.

## What the package promises

1. Every manifest is `{timetoshare, timelines, id?, name?, meta?, groups?,
   measure_maps?, schemes?, links?, graphical?}`; `validate` accepts exactly the values the schema and the
   rules below accept, and raises the first violation with its code and
   path.
2. A value without the version marker is refused at the root, a value with
   another version raises `UnsupportedVersionError`.
3. Unknown keys are kept and listed by `unknown_keys`, and bare words outside
   a registered vocabulary are kept and listed by `unregistered_terms`;
   neither is ever refused.
4. `complete` and `minimal` convert between the complete and the minimal
   form, both pure, from one table of defaults that agrees with the schema.
5. `dumps` writes every JSON value, a manifest put in canonical order and its
   own-axis values respelled first, in canonical YAML, pretty JSON and RFC
   8785 JSON, the same bytes as the JavaScript package; `loads` reads every
   serialization and `serialization_of` names a text's.
6. Schema, fixture, font and registry accessors resolve package data
   independently of the working directory; the wheel and the sdist ship the
   schema document, `docs/drawing.md`, the registry of identifier schemes and
   the licence.
7. The description model (`timetoshare.description`) builds links from URLs
   through the registry of identifier schemes (`timetoshare.registry`), and
   writes and reads them in both forms, with the same values, the same
   errors and the same messages as the JavaScript package.

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
- **The public definitions.** The definitions include the fifteen public
  ones `Manifest`, `Timeline`, `Group`, `Graphical`, `ConversionMap`,
  `Coordinate`, `Number`, `Fraction`, `TimeUnit`, `NumberType`, `Id`,
  `MeasureMap`, `MeasureMapRow`, `Link` and `Scheme`, and the root's
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
  `ElementType` is exactly the sixteen types `block`,
  `timeline`, `child`, `band`, `map`, `region`, `flow_marker`, `jump_from`,
  `wedge`, `name`, `label`, `boundary`, `ancestor`, `frame`, `card` and
  `cross_section`. The four
  measure views fix `source_unit` to `quarters` and `target_unit` to
  `floating_measures` (`FloatingMeasureMap`) or null (the other three).
- **The unit table.** `TimeUnit` is a string whose `oneOf` holds one
  `{const, description}` per unit and no `enum`. The consts, in order, are
  exactly the keys of `UNIT_NUMBER_TYPES`, and each description is
  `<Domain>, <modality>; default number type <t>.` with `t` that unit's
  value in the table, so the default number types the validators read
  cannot drift from the ones the schema states.
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
  refer to `Id`, the items of `Selector.addresses` to `Address`. `Id`
  accepts `score`, `Bass Kick`, `perf/take 2`,
  `https://example.org/piece/score#exposition`, `start` and `regions_1`,
  and refuses `""`, `score` followed by a tab and `score` followed by a
  newline. `Address` accepts `{}`,
  `{"part": ["name"]}`, `{"id": "score"}`, `{"id": "perf/take 2"}`,
  `{"id": "score", "facet": "regions"}`, `{"id": "score", "part":
  ["card"]}`, `{"id": "score", "part": ["end", "label"]}`, `{"id":
  "timestamp_1", "part": ["line"]}`, `{"id": "timestamp_1", "part":
  ["label"]}`, `{"id": "timestamp_1", "part": ["name"]}`, `{"id": "timestamp_1", "part": ["id"]}` and `{"id":
  "timestamp_1", "part": ["coordinate"]}`, and refuses
  the string `"score"`, `{"facet": "regions"}` (a facet needs an ID),
  `{"id": "score", "facet": "regions", "part": ["label"]}` (a facet never
  stands with a part), `{"id": "score", "part": []}`, `{"id": "score",
  "part": ["wedge"]}` and `{"id": "score", "facet": "regions_1"}`. It
  accepts `{"id": "score", "root": "score"}`: an address is open like
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
- **The description layer.** `links` is a property of exactly the
  definitions `Manifest`, `Timeline` and `Region`, and `schemes` of
  `Manifest` alone, so no group, map, MeasureMap, flow-control element or
  timestamp carries links. `Level` is exactly `work`, `expression`,
  `manifestation`, `item` and `agent`, `Assertion.match` exactly `exact`,
  `close`, `broad`, `narrow`, `related` and null, `Assertion.status` exactly
  `confirmed`, `unconfirmed`, `rejected` and null; the package's `LEVELS`,
  `MATCHES` and `STATUSES` equal them, so the model cannot drift from the
  closed vocabularies. A `PartSlot` declares no `position` (its place in
  `parts` is its position) and a `Link` declares `label` and no `name`,
  `same_as` or `equivalent`. `Uri` accepts `http://musicbrainz.org/work/x`,
  `urn:isbn:0451450523` and `mailto:a@example.org`, and refuses
  `musicbrainz.org/work/x` (no scheme), `1http://x` (a scheme begins with a
  letter), `http:` (nothing after the colon), `http://a b`, `http://a\n` (a
  trailing newline, which a pattern ending in `$` lets through Python's
  `re.search`; the definitions therefore refuse white space with a separate
  unanchored `not`, which both libraries read alike), `http://a b` and
  `http://a﻿`. `Term` accepts `pertains_to`, `marcrel:cmp` and
  `http://id.loc.gov/vocabulary/relators/cmp`, and refuses `""`,
  `has part` and `has_part\n`; `UriReference` accepts `records/op106.json`
  and refuses `""` and `a b`. The white-space class of those definitions is
  the one the registry uses to refuse a URL before matching it, pinned
  against the schema.
- **Both libraries read every pattern alike.** A pattern ending in `$`
  lets a trailing newline through Python's `re.search` and not through
  JavaScript's `RegExp`, so a definition that needs to refuse control
  characters says so with an unanchored `not`, never with an anchored
  class: `Id` is a string of `minLength` 1 whose `not` refuses U+0000 to
  U+001F, and an entry of an `Order` has the same two keywords. The five
  patterns that still end in `$`, a named timestamp's `id`, `Paint`,
  `stroke-dasharray`, `asserted_on` and a record's `integrity`, are
  exactly those the document holds, and each refuses a value it accepts
  (`timestamp_1`, `none`, `4 2`, `2026-11-17`, `sha256-AAAA`) once a
  newline follows it, through `Id`'s `not`, a `not` of its own or its
  `maxLength`; an `Order` refuses `["line\n"]`. The JavaScript suite
  asserts the same values, so the two validators cannot part on a
  trailing newline.
- **Defaults agree with the table.** For every kind of `DEFAULTS` the
  schema's corresponding definitions (`Manifest`, `Timeline`,
  `Region`, `FlowControlElement`, `MeasureMap`, `Group`, `Graphical`,
  `Scheme`, `Link`, `PartSlot`, `PartOf`, `Assertion`, `Descriptor`, every
  conversion map) declare `default` on exactly the keys
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
  holds exactly `manifest`, `unknown_keys` and `unregistered_terms`;
  `validate` accepts the manifest, `unknown_keys` returns exactly its
  `unknown_keys` list and `unregistered_terms` exactly its
  `unregistered_terms` list (empty in the thirteen cases of unknown keys,
  empty `unknown_keys` in the four cases of terms); the JavaScript suite
  asserts the same lists. `several_depths` holds unknown keys on the
  manifest, a timeline, a child, a region, a flow marker, a jump origin, a
  jump target, a conversion map and the map nested in it, a MeasureMap and
  one of its rows, a group, the `graphical` object, a statement, a selector
  and a declaration (sixteen entries). The other cases are keys the format does
  not declare that a writer might plausibly add: a timeline `class`,
  a manifest `support_policy`, a group's `order`, `arrangement` in
  `graphical`, a selector's `kind` and `ids` (a list of string
  addresses), a declaration's `colour` and
  `show-projections`, a MeasureMap row's `tempo` and `offset`, a
  `CombinationMap`'s `names`, and an address's `root`
  (`address_unknown_member`: the address equals no element's address and
  matches nothing, and its key is reported like any other).
- **An undeclared key of a declaration and of a style.** `side`: a manifest whose statement
  sets `{"fill": "#000000", "side": "above"}` on maps and whose style
  `below` is `{"side": "below"}` validates, and `unknown_keys` lists exactly
  `{"path": ["graphical", "statements", 0, "set"], "key": "side"}` and
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
- **One walk.** The keys come from the schema walk `validate` runs. It
  walks an in-memory variant of the document that closes every object the
  document leaves open (`unevaluatedProperties: false` on each object node
  with `properties` outside a branch, except the base an `allOf` shares), and
  a failure that only an undeclared key causes is a key to list, not a
  violation. Listing them walks the manifest with the schema once, as a
  counting validator proves.

## Defaults: the complete and the minimal form

`DEFAULTS` is the one table (`test_defaults.py`). What proves `complete` and
`minimal`:

- **Literal forms.** The smallest file completes to the literal complete
  manifest (`name` null, `meta` `{}`, `groups`, `measure_maps`, `schemes`
  and `links` `[]`, and
  on the timeline `name` null, `number_type` `fraction`, `locked` false,
  `is_segment_line` false, `meta` `{}`, `children`, `conversion_maps`,
  `regions`, `flow_control` and `links` `[]`), and that minimizes back to the
  smallest file. A manifest holding a scheme, and a link (on the manifest, a
  timeline and a region) with a record, an assertion, a part slot with an
  assertion of its own and a `part_of` entry, gains exactly the keys of
  `scheme`, `link`, `descriptor`, `assertion`, `part_slot` and `part_of`
  (every array `[]`, `parts_ordered` true, every other key null), and its
  minimal form is the literal input. A region (gaining `links` too), a flow-control element (a `repeat_end` gains
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
  (`float`) and whole_notes (`fraction`).
- **Never added, never removed.** `id`, `graphical` and a root's `offset`
  are absent from the completion of a manifest without them; a present
  `graphical: {}` completes to its four keys (`styles`, `statements`,
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
table, root by root for the first six (a root's duplicates, then its
targets, then its conversion maps, then child by child, each followed by its
own children, the containment rules, then its segment lines), the rest over
the whole manifest. A timeline's maps are read in array order, each before
the maps it holds, a `CombinationMap`'s by output name in code-point order,
and a map's source unit before its arrays.
`identity_problems` returns every semantic problem in that order; `validate`
stops at the first. A message names an element by its ID in single quotes,
as written (a unit and an order entry too), so every message but a schema
violation's is the same text in both packages.

| Code | Rule | Reported at | Message |
| --- | --- | --- | --- |
| `not_a_manifest` | an object holding `timetoshare` | the root | `not a TimeToShare manifest` |
| `finite_number` | every number finite | the leaf | `length of 'take' is not a finite number`, or `#/graphical/styles/s/opacity is not a finite number` with no ID above it |
| `schema` | the schema document | the path rule below | the schema library's |
| `representation` | own-axis values in the axis's number type | the value | `length 32 of 'score' is an int on a fraction axis: write [32, 1]` |
| `duplicate_id` | IDs unique within a root's tree, the maps a `ChainMap`, `PiecewiseMap` or `CombinationMap` holds included after the tree's other IDs | the later ID | `'m' is not unique in the manifest, first at #/…` |
| `dangling_target` | a jump origin's `target` names a jump target of its timeline; then, map by map, a measure view's `measure_map` names an entry of `measure_maps` | the target, the `measure_map` | `'there' names no jump_to of this timeline`, `'ghost' names no MeasureMap of this manifest` |
| `conversion_map` | a non-null `source_unit` of a map attached to a timeline is the timeline's unit, and that of every map a `PiecewiseMap` or `CombinationMap` holds, and of a `ChainMap`'s first map, is its holder's non-null `source_unit`; a `TableMap`'s x and y values of equal length, its x values strictly increasing; a `PiecewiseMap`'s maps one fewer than its breaks, its breaks strictly increasing | the `source_unit`, the `y_values`, the value, the `maps`, the break | `MeasureRecordMap 'bars' has source unit 'quarters', its timeline 'score' has 'ticks'`, `LinearMap 'scale' has source unit 'ticks', its ChainMap 'chain' has 'quarters'`, `TableMap 'tempo' has 3 x values and 2 y values`, `x value [0, 1] of TableMap 'tempo' does not exceed the one before it`, `PiecewiseMap 'sections' has 1 map for 3 breaks; it needs 2 maps`, `break [4, 1] of PiecewiseMap 'sections' does not exceed the one before it` |
| `child_unit` | a child has its parent's unit | its `unit` | `child 'take' has unit 'seconds', its parent 'score' has 'quarters'` |
| `child_offset` | a child starts within the parent's known length | its `offset` | `offset 75.0 of 'take' is beyond the length 60.0 of its parent 'recording'` |
| `child_end` | else, it ends within it | its `length` | `child 'coda' ends at [12, 1], beyond the length [10, 1] of its parent 'score'` |
| `segment_line` | segments contiguous from 0 to the length, one flag | the segment's flag or offset, the line's `length` | `segment 'b' of segment line 'line' does not start where the one before it ends` |
| `duplicate_id` | every ID unique across the manifest: each root's tree, in the order above, against the earlier roots' (an ID repeated inside one root counts once), then each group ID, then each MeasureMap ID, then each named timestamp's ID, then each scheme's ID, against every ID before it | the later ID | as above |
| `manifest_id` | the manifest ID is no other ID of the manifest | `id` | `'g2' is not unique in the manifest, first at #/groups/1/id` |
| `group_member` | a member names a timeline and neither contains nor lies inside another member of its group | the member | `'ghost' names no timeline of this manifest`, `member 'b' lies inside member 'a' of the same group` |
| `order_key` | a `graphical.order` key names a group or a timeline | the key | `'g9' names no group or timeline of this manifest` |
| `display_order` | a group's order permutes its members | the entry, then the order | `'x' is not a member of group 'g'`, `member 'b' of group 'g' is missing` |
| `band_order` | a timeline's order permutes `line` and the five facets | the entry, then the order | `'annotations' is not 'line' or a facet, in the band order of 'score'`, `'flow_control' is missing from the band order of 'score'` |
| `timestamp_timeline` | a named timestamp's `timeline` names a timeline of the manifest, at any depth | its `timeline` | `'ghost' names no timeline of this manifest` |
| `timestamp_coordinate` | its `coordinate` lies from 0 to its timeline's length, from 0 on where the length is null | its `coordinate` | `coordinate [9, 1] of 'timestamp_1' is beyond the length [8, 1] of its timeline 'score'`, `coordinate [-1, 1] of 'timestamp_1' lies before the start of its timeline 'score'` |
| `calendar_date` | link by link, with the row below: an assertion's `asserted_on` names a day of the Gregorian calendar from 0001-01-01 to 9999-12-31 | the `asserted_on` | `'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD` |
| `dangling_target` | link by link, an identifier's `scheme` names a scheme of the manifest or is an absolute URI, and a part slot's `represented_by` entry names a timeline (any depth) or a region of the manifest | the `scheme`, the entry | `'opus' names no scheme of this manifest and is no absolute URI`, `'ghost' names no timeline or region of this manifest` |

The keys of `graphical.order` are read in code-point order, each order's
strangers before its missing entries, missing members in the order of
`members`, missing bands in the default band order (`children`,
`conversion_maps`, `line`, `markers`, `regions`, `flow_control`).
A key naming a group and a timeline never reaches `validate` (the duplicate
ID comes first); `identity_problems` reads it as the group's. The named
timestamps are read after the orders, in array order, and the links last:
the manifest's, then root by root each timeline's own, its regions' in array
order and its children's, depth first; within a link its assertion's
`asserted_on`, then its `identifiers`, then each part slot's `asserted_on`,
`identifiers` and `represented_by`, then each `part_of` entry's
`asserted_on` and `identifiers`. The schema checks that a date is written
`YYYY-MM-DD`; `calendar_date` checks that the calendar has it, as the
description model does when it reads an assertion, so a manifest
`validate` accepts is one the model reads. The Gregorian calendar counts
months 1 to 12 and the days of each month, February having 29 in a year
divisible by 4 and not by 100, or by 400; its years run from 1 (the first
year of Python's `datetime.date`), so `0000-01-01` is refused too. What
proves it (`test_description.py`): `2024-02-29`, `2000-02-29`,
`0001-01-01` and `9999-12-31` validate, and `2026-02-30`, `2023-02-29`,
`2100-02-29`, `2026-11-31`, `2026-13-01`, `2026-00-10`, `2026-11-00` and
`0000-01-01` are each one `calendar_date` problem with the message above;
a manifest holding one in the assertion of a link, of its slot and of its
`part_of` entry, its slot also represented by `ghost` and its identifier
naming `opus`, lists its problems in the order stated. The coordinate of a
timestamp on a timeline of the manifest is an own-axis value of that
timeline and is checked with the `representation` rule (`coordinate 3 of 'timestamp_1' is
an int on a fraction axis: write [3, 1]`, at its `coordinate`); a timestamp
naming no timeline is checked for its timeline alone.

## What proves the rules

**The shared rejection cases are the oracle the two packages share.** Each of
the 129 cases of `fixtures/rejections/0.2.0/` breaks one rule and stores the
path and the code (`test_validate.py`); `validate` raises
`SchemaValidationError` with exactly both, and the codes of the cases are
exactly the nineteen of the table, so every code is reached by a case both
suites read. `version_unknown` raises `UnsupportedVersionError` and stores
`["timetoshare"]` and the code `null`. Every case is read through the
package's one reader, `rejection_case`, which every consumer uses too; it
puts the infinity or NaN a `finite_number` case names at the stored path.
Three tests pin the reader: `nan_offset` and `infinite_length` hold the
value in place and are reported at their path with the exact message, a
case without one (`id_empty`) reads as written, and an unknown name is
refused with `ValueError`. Each case's text is the
standard writer's, and the set of names is stated literally, so a case cannot
disappear unnoticed. Sixteen cases pin their message too (`test_identity.py`
and `test_description.py`):
`child_unit_differs`, `child_offset_beyond_parent`, `child_end_beyond_parent`,
`region_id_duplicate_across_roots`, `band_order_unknown_entry`,
`band_order_missing_band`, `band_order_old_form`, `order_unknown_group`,
`timestamp_timeline_unknown`, `timestamp_coordinate_beyond_length`,
`timestamp_coordinate_negative`, `timestamp_id_is_timeline_id`,
`description_slot_represented_by_unresolved`,
`description_identifier_scheme_unresolved`,
`description_scheme_id_duplicate` and
`description_asserted_on_impossible_date`. The nineteen cases named
`description_*` break one rule each of a manifest whose one root `score`
(8 quarters) holds the region `intro` and whose one link, at the level `work`, reads two
parts; every case is in the complete form, so its slots state both
`represented_by` and `absent` and its paths are those of the complete form:
a link without `relation` or without `level` (`schema` at the link), with
the level `score` (`schema` at `level`), at the level `agent` with the
relation `pertains_to` (`schema` at the link, the definition's `not`), a
slot represented by `score` and absent as `lost` (`schema` at its `absent`,
the `then` arm), a slot with `represented_by` empty and `absent` null
(`schema` at its `absent`, the `else` arm), a slot represented by `ghost`
(`dangling_target` at `represented_by/0`), an identifier of the scheme
`opus` that no scheme declares (`dangling_target` at its `scheme`), a
scheme whose ID is `score` (`duplicate_id` at `schemes/0/id`, first at the
timeline's), parts with `parts_relation` null (`schema` at
`parts_relation`), empty parts with `parts_relation` `has_part`
(`description_parts_relation_without_parts`, `schema` at
`parts_relation`, the link's `else` arm) and with `parts_ordered` false
(`description_parts_ordered_without_parts`, `schema` at `parts_ordered`,
the same arm), a `part_of` entry without `parts_relation` (`schema` at
the entry), an assertion with `match` `equivalent` and with `status`
`approved` (`schema` at the member), `asserted_on` `17 November 2026`
(`schema` at the member) and `2026-02-30` (`calendar_date` at the
member), a `uri` entry `musicbrainz.org/work/x` (`schema`
at the entry) and a record without `url` (`schema` at the record).
`id_control_character_trailing_newline` names its one root `score`
followed by a newline and is refused at that `id` (`schema`), the case on
which an anchored pattern would part the two validators. The five
cases of named timestamps break one rule each of the manifest `score` (8
quarters) with the child `verse` (4 at 2): a timestamp on `ghost`
(`timestamp_timeline` at its `timeline`), at `[5, 1]` on `verse`
(`timestamp_coordinate`, beyond the child's own length 4, though within
its parent), at `[-1, 1]` on `score` (`timestamp_coordinate`), with the ID
`timestamp_1` of a timeline (`duplicate_id` at the timestamp's `id`, first
at the timeline's), and with the ID `timestamp_01` (`schema` at its `id`).
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
  segment of unknown length, its successor's offset; values compare exactly
  and the end is spelled in the parent's number type, a fraction pair where
  that type has no exact spelling: `0.2` at `0.1` in `0.3` seconds ends at
  `[10808639105689191, 36028797018963968]`, `0.5` at `0.5` in `0.75` at
  `1.0`, `240` ticks at `480` in `480` at `720`, a quarters child declared
  `float`, `2.5` at `[7, 1]` in `[8, 1]`, at `[19, 2]`; `0.25` at `0.5` in
  `0.75` and `[2, 1]` at `[8, 1]` in `[10, 1]` end at the length and pass.
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
  and 0 are contiguous); exact comparison (`0.1 + 0.2` does not meet `0.3`,
  `0.5 + 0.25` meets `0.75`); a segment of unknown length ends where its
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
  of the default); each stranger (`annotations`, `region`, `score`,
  `score/regions_1`, `Regions`) is one problem at its entry, a missing facet
  one at the order, an empty order its six missing entries in the default
  band order. An order keyed by a region's ID is one `order_key`.
- **Named timestamps.** Timestamps on a root, on a child and on a segment,
  at 0 and at the length, and at any coordinate from 0 on a timeline of
  unknown length pass, as do a timestamp on the second of two roots and two
  timestamps of one name at one coordinate. A timestamp ID equal to a
  timeline's (a timeline may be named `timestamp_1`), a group's or another
  timestamp's is one `duplicate_id` at the timestamp's `id`, and the
  manifest ID equal to a timestamp's one `manifest_id`. A coordinate on a
  float axis is compared exactly (`60.5` beyond `60.0`), as is a fraction
  (`[17, 2]` beyond `[8, 1]`, `[16, 2]` not). The schema refuses an ID
  `timestamp_0`, `timestamp_01` or `clt_1`, an empty `name`, a `name`
  null and a timestamp without `coordinate`, each at that member (the
  missing member at the timestamp). `display` passes as `[]`, as `["id"]`,
  as all five in canonical order and as all five reversed (the order
  carries no meaning); the schema refuses `"wedge"` (not an array) at
  `display`, `["wedge", "Wedge"]` at `display/1` (words are exact),
  `["line"]` at `display/0` (a part word, not a display word), `[1]` at
  `display/0`, and `["name", "name"]` at `display` (`uniqueItems`).
- **Links** (`test_description.py`). A slot represented by a root, a child,
  a segment and a region passes; one represented by `ghost`, by a group's ID
  or by a MeasureMap's ID (neither a timeline nor a region) is one
  `dangling_target` at that entry. An identifier whose scheme is a scheme's
  ID or an absolute URI passes, and one whose scheme is `opus` is one
  `dangling_target` at its `scheme`, wherever the identifier stands: on the
  link, on a part slot, on a `part_of` entry, and on links of the
  manifest, a root, a child and a region, each reported at its own path. A
  scheme's ID equal to a timeline's, a region's or another scheme's is one
  `duplicate_id` at the later `schemes/<i>/id`, and the manifest's ID equal
  to a scheme's one `manifest_id`. Of a link breaking two rules,
  `identity_problems` lists its identifier's problem before its slot's.
  The schema's own rules: a slot both represented and absent is refused at
  its `absent`, a slot that is neither at its `absent` in the complete form
  and at the slot in the minimal form; a link at the level `agent` with the
  relation `pertains_to` at the link, the same link with the relation
  `marcrel:cmp` passes; parts with `parts_relation` null or absent are
  refused at `parts_relation` or at the link, and empty parts with neither
  pass. The other side of the same rule: a `parts_relation` `has_part`
  with `parts` empty or absent is refused at `parts_relation`, and
  `parts_ordered` false with `parts` empty or absent at `parts_ordered`,
  while `parts_ordered` false beside one slot under `has_part` passes. A
  scheme's `criteria` is a URI reference: `criteria/opus-numbers.html` and
  `https://example.org/criteria` pass, `""` and `criteria/opus numbers` are
  refused at `schemes/0/criteria`.
- **The description layer alone** (`test_description.py`).
  `description_problems` returns the problems of the description layer of
  any manifest and nothing else, so a reader of part of a manifest checks
  its links without knowing which parts the rules read. Its oracle is the
  shared set: each of the nineteen `description_*` rejection cases gives
  exactly one problem, the case's path and code (and, for the four cases
  whose message is pinned above, that message), and each of the other 110
  cases (the `version_unknown` case and the case that is no manifest
  among them) and every fixture gives none. Every document of the rules
  of links above gives the list `identity_problems` gives, as each breaks
  description rules only. A manifest whose other parts break every kind of
  rule (the version `9.9.9`, two roots `a`, the unit `beats`, a child of
  another unit beyond its parent's length, a region that is no object, a
  group naming `ghost`, `graphical` that is no object) and whose links
  are sound gives none: its one slot represented by the region `r`
  passes, and a scheme `a` is one `duplicate_id` at `schemes/0/id`, first
  at `#/timelines/0/id`, followed by the manifest ID `g` equal to the
  scheme `g` (`manifest_id` at `id`, first at `#/schemes/1/id`) and then by
  the identifier naming `q` (`dangling_target`): the scheme rules come
  before the links' as in `identity_problems`. The arrays are checked one
  by one, each giving its first problem at its own path, in the order
  `schemes`, the manifest's `links`, then root by root each timeline's,
  its regions' and its children's: in one manifest, `schemes` holding a
  scheme without `id` (`schema` at `schemes/0`), the manifest's `links`
  being `"none"` (`schema` at `links`), the root's link without `level`
  (`schema` at `timelines/0/links/0`), its region `r`'s link with the
  level `score` (`schema` at `timelines/0/regions/0/links/0/level`) and
  the child `verse`'s link with a record of size infinity (`finite_number`
  at `timelines/0/children/0/links/0/records/0/size`, `size of 'verse' is
  not a finite number`, built in code) are five problems in that order; a
  sound link of the same manifest whose identifier names `q` adds none,
  because the reference rules read a schema-checked layer and run only
  where no array has a problem. A schema problem's message is the schema
  library's, as for `validate`.
- **Unregistered terms** (`test_description.py`). `unregistered_terms`
  validates the manifest, then lists every bare term of an open vocabulary
  that is not registered for its key, as `{"path": [...], "term": ...}`
  sorted by path as unknown keys are. Every registered word of every key
  (`pertains_to`; `manual`, `reconciled`, `imported`, `inferred`;
  `has_part`, `aggregates`, `incorporates`; `not_represented`, `lost`,
  `unfinished`, `unknown`, `not_recorded`) and every extension term
  (`marcrel:cmp`, `http://id.loc.gov/vocabulary/relators/cmp`, a PREMIS URI)
  lists nothing; a word registered for another key is listed (`has_part` as
  a `relation`, `lost` as a `method`). The keys read are a link's
  `relation` and `parts_relation`, every assertion's `method` (the link's,
  a slot's and a `part_of` entry's), a slot's `absent` and a `part_of`
  entry's `parts_relation`; one manifest holding an unregistered word in
  each of these places, on links of the manifest, a timeline and a region,
  lists them in path order. An invalid manifest raises before any term is
  listed. The four shared warning cases each hold one such word: a relation
  `about`, a method `guessed`, a parts relation `contains` and an absence
  reason `destroyed`.

**One document breaks every step once** (`test_every_step_in_order` and its
JavaScript twin): `identity_problems` returns exactly the stated problems, in
the stated order, with the stated codes, and `validate` raises the first.

**The finite rule runs before everything else.** Infinity as a length, NaN
in a fraction pair of a region and negative infinity in a style, each in a
manifest whose repeated root also breaks the identity rules, raise
`finite_number` at the leaf with the message of the table.

## The description layer

A link describes its element by pointing to an external entity; the model
writes links, reads them back and builds them from URLs. What proves it
(`test_description.py`, `test_registry.py`):

- **The registry is the shipped file.** `registry/schemes.json` is written
  in pretty JSON by `dumps(…, serialization="json")`, and the default registry holds exactly its nine entries, in
  this order, each with its scheme URI, level, entity URI template and
  `lowercase`:
  `musicbrainz_work` (`http://www.wikidata.org/entity/P435`, `work`,
  `http://musicbrainz.org/work/{value}`, true), `musicbrainz_recording`
  (`P4404`, `expression`, `http://musicbrainz.org/recording/{value}`,
  true), `musicbrainz_release` (`P5813`, `manifestation`,
  `http://musicbrainz.org/release/{value}`, true), `wikidata`
  (`http://id.loc.gov/vocabulary/identifiers/wikidata`, null,
  `http://www.wikidata.org/entity/{value}`, false), `viaf` (`P214`, null,
  `http://viaf.org/viaf/{value}`, false), `gnd` (`P227`, null,
  `https://d-nb.info/gnd/{value}`, false), `imslp` (`P839`, `work`, null,
  false), `doi` (`P356`, null, `https://doi.org/{value}`, false) and
  `youtube_video` (`P1651`, `item`,
  `https://www.youtube.com/watch?v={value}`, false). An entity URI template
  is Wikidata's formatter URI for RDF resources (P1921) where one exists,
  unless the issuer prescribes the canonical form, as the DOI Foundation
  does with `https://doi.org/`; YouTube has no such formatter, so its
  template is the watch page, the first formatter URL (P1630) Wikidata
  states for P1651. Every entry is written with
  all seven keys, so the file reads back to the entries it was written from.
  Every pattern has exactly one capturing group and no syntax that Python's
  `re` and JavaScript's `RegExp` read differently (no named group, no
  lookbehind, no inline flag).
- **One rule per scheme.** A scheme with an entity URI template yields an
  entity URI and never an identifier; one without yields an identifier
  `{scheme: <scheme URI>, value}` and never a URI.
- **The recognition table** (the same table in the JavaScript suite):
  `https://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284` is the
  URI `http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284` at
  the level `work`; `http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980/`
  is `http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980`,
  `work`; `https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c`
  is `http://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c`,
  `manifestation`; `https://www.wikidata.org/wiki/Q146730` is
  `http://www.wikidata.org/entity/Q146730`, no level;
  `https://viaf.org/viaf/186299955` is `http://viaf.org/viaf/186299955`, no
  level; `https://imslp.org/wiki/Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)`
  and its percent-encoded form
  `https://imslp.org/wiki/Piano_Sonata_No.29%2C_Op.106_%28Beethoven%2C_Ludwig_van%29`
  are the identifier `{scheme: "http://www.wikidata.org/entity/P839", value:
  "Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)"}` at the level
  `work`; `https://doi.org/10.5281/zenodo.7473560` is
  `https://doi.org/10.5281/zenodo.7473560`, no level;
  `https://musicbrainz.org/work/4A622B0D-B0C0-405E-B49E-05B70C108284`, the
  same work's ID in capitals, is
  `http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284`,
  `work`, its value `4a622b0d-b0c0-405e-b49e-05b70c108284`;
  `https://www.youtube.com/watch?v=Ch2mrPm1JnM` is
  `https://www.youtube.com/watch?v=Ch2mrPm1JnM` at the level `item`; and
  `https://imslp.org/wiki/Special:ReverseLookup/534071` and
  `https://example.org/anything` are not recognised.
- **The URL forms a scheme accepts.** `http` and `https`, an optional
  `www.` (`m.` for Wikidata), Wikidata's `/wiki/` and `/entity/`, VIAF's
  language segment (`https://viaf.org/en/viaf/186299955`, the form Wikidata
  states as VIAF's formatter URL today), a trailing `/`, a query and a
  fragment all give the same URI, and so does a MusicBrainz ID in capitals
  or in mixed case, for a work, a recording (`5F1A7C3E-…` gives
  `http://musicbrainz.org/recording/5f1a7c3e-2b4d-4e6f-8a9b-0c1d2e3f4a5b`)
  and a release, since the MusicBrainz entries state `lowercase`. An IMSLP
  page that is no work page is not recognised: `Main_Page` (also with a
  trailing `/`, a query, or written `Main%20Page`) and a page of each
  namespace IMSLP's wiki declares, under its canonical and its local name
  and their aliases, and of `Module`: `Media:`, `Special:`, `Talk:`,
  `User:`, `User_talk:`, `IMSLP:`, `IMSLP_talk:`, `Project:`,
  `Project_talk:`, `File:`, `File_talk:`, `Image:`, `Image_talk:`,
  `MediaWiki:`, `MediaWiki_talk:`, `Template:`, `Template_talk:`, `Help:`,
  `Help_talk:`, `Category:`, `Category_talk:`, `Module:` and
  `Module_talk:`, each written plainly, with `%3A` or `%3a` for the colon,
  and the two-word ones with `%20` for the underscore. A work page whose
  name begins with such a word is recognised: `Main_Page_(Example)` and
  `Talk_Show_Suite_(Example,_Anna)` are identifiers of those values.
  Nor is a URL holding white space recognised, nor an IMSLP name whose
  percent-encoding is not UTF-8 (`%E2%80`); an IMSLP name written with
  spaces (`%20`) gives underscores. A captured value is substituted into
  the entity URI as written, lowered where the entry states `lowercase`
  (only the letters `A` to `Z`), and decoded only for an identifier.
- **The addresses of a YouTube video.** A video's ID is eleven letters,
  digits, `_` and `-`, and its case matters, so the entry does not state
  `lowercase`. Every address a video is shared at gives the one entity URI
  `https://www.youtube.com/watch?v=Ch2mrPm1JnM` and the value
  `Ch2mrPm1JnM` as written: `https://youtu.be/Ch2mrPm1JnM?t=42`,
  `https://m.youtube.com/watch?feature=share&v=Ch2mrPm1JnM` (`v` need not
  open the query), `https://www.youtube.com/embed/Ch2mrPm1JnM`,
  `http://youtube.com/watch?v=Ch2mrPm1JnM&t=42s#x`,
  `https://music.youtube.com/watch?v=Ch2mrPm1JnM`,
  `https://www.youtube.com/shorts/Ch2mrPm1JnM`,
  `https://youtube.com/live/Ch2mrPm1JnM?feature=share`,
  `https://www.youtube.com/watch?v=Ch2mrPm1JnM#t=1m`, the privacy-enhanced
  embed `https://www.youtube-nocookie.com/embed/Ch2mrPm1JnM` (also without
  `www.`) and the legacy `https://www.youtube.com/v/Ch2mrPm1JnM`, which
  was shared with its parameters joined straight to the ID by `&`
  (`https://www.youtube.com/v/Ch2mrPm1JnM&hl=en_US&fs=1`) and on the
  privacy-enhanced host too (`https://www.youtube-nocookie.com/v/Ch2mrPm1JnM`).
  An address that names no video is not recognised: a channel
  (`https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv`), a `v`
  shorter than eleven characters (`https://www.youtube.com/watch?v=short`),
  a playlist without `v` (`https://www.youtube.com/watch?list=PL123`), and
  the two embeds whose path segment is eleven characters long like an ID
  but names no video: the embedded playlist `videoseries`
  (`https://www.youtube.com/embed/videoseries?list=PL123`,
  `https://www.youtube-nocookie.com/embed/videoseries?list=PL123`) and a
  channel's live stream `live_stream`
  (`https://www.youtube.com/embed/live_stream?channel=UCabcdefghijklmnopqrstuv`,
  `https://www.youtube-nocookie.com/embed/live_stream?channel=UCabcdefghijklmnopqrstuv`).
- **A user extension.** `with_schemes` returns a new registry and leaves the
  default as it was; an entry whose ID the registry holds replaces it in
  place, any other is appended, and a URL is recognised by the first entry
  whose pattern matches it. An entry that leaves out `level`, `entity_uri`
  and `lowercase` is read as stating null, null and false, as the
  JavaScript package reads it: written back, it holds all seven keys, and
  `https://example.org/page/12` is the identifier `{scheme:
  "https://example.org/scheme", value: "12"}` without a level. An entry
  stating `lowercase` gives its values lowered: with `lowercase` true and
  the pattern `https://example\.org/page/([0-9A-Za-z]+)`,
  `https://example.org/page/AbC` is `https://example.org/entity/abc`. An
  entry is refused with `ValueError` for a
  pattern with no or two capturing groups (`pattern '…' of scheme 'x' has 0
  capturing groups; it needs exactly one`), one using `(?<`, `(?P` or an
  inline flag (`… uses syntax outside the shared subset; only (?:, (?= and
  (?! may follow '(?'`), one that is no regular expression, a level outside
  `LEVELS` (`scheme 'x' has the level 'score', which is no level`), an
  entity URI template without `{value}` and a `lowercase` that is no
  boolean, `"yes"` or null (`the lowercase of scheme 'x' is no boolean`).
- **The work bundle of Op. 106.** Built through the API from the URLs of
  its MusicBrainz work, its Wikidata item, its VIAF cluster and its IMSLP
  page, with `identifiers={"mb_beethoven_opus": "op. 106"}`, a label, an
  assertion (`asserted_by` `https://example.org/people/editor`,
  `asserted_on` 2026-11-17, `method` `manual`, `status` `confirmed`) and
  four `PartSlot.from_url` slots of its movements, each `not_represented`,
  under `has_part`, beside the scheme `mb_beethoven_opus` and in a manifest
  without timelines, its minimal form is exactly the stated manifest and
  its complete form the stated complete manifest, the flat (U+266D) and the
  dash (U+2013) kept; both validate, both list no unknown key and no
  unregistered term, `minimal` and `complete` map each to the other, and
  `Link.from_dict` and `Scheme.from_dict` read both forms back to objects
  equal to the built ones.
- **Two readings of one work** in one manifest, the movements in two orders
  with two assertions, validate and survive `dumps` and a read back in the
  order given; the canonical order moves neither the links, nor a link's
  `uri`, nor its `parts`, and sorts `schemes` by ID.
- **The errors of the model**, each with its message: a part slot both
  represented and absent (`a part slot is represented or absent, not
  both`) and neither (`a part slot is represented by an element or
  absent`); a URL that is neither recognised nor an absolute URI (`'x' is no
  absolute URI`); no URL (`a link from URLs needs one URL at least`); two
  URLs recognised at two levels (`'b' is recognised at the level
  'manifestation', 'a' at 'work'`); a level contradicting a recognised one
  (`the level 'expression' contradicts 'a', recognised at the level
  'work'`), from `from_urls` and from `with_uri`; no level at all (`no level
  is recognised from 'a', 'b'; state the level`); a level outside `LEVELS`
  (`'score' is no level`); an agent link without a relation (`an agent link
  states its relation, the agent's role`) or with `pertains_to` (`an agent
  link never uses the relation 'pertains_to'`); parts without a parts
  relation (`a link with parts states its parts_relation`); a parts
  relation without parts (`a link without parts states no
  parts_relation`), from the constructor and from `with_parts` given no
  slot; `parts_ordered` false without parts (`a link without parts keeps
  parts_ordered true`); `with_parts`
  given a slot recognised at another level (`part slot 2 is recognised at
  the level 'manifestation', the link's level is 'work'`); an identifier
  given in a scheme that mints entity URIs whose value is no value of the
  scheme (`'op. 106' is no value of the scheme 'MusicBrainz work ID'`, and
  `'x'` alike), from `from_urls` and from `with_identifier`; an entity URI
  from `with_identifier` at another level than the link's (`the level
  'expression' contradicts 'http://musicbrainz.org/work/4a622b0d-…',
  recognised at the level 'work'`); and an
  `asserted_on` the calendar lacks or not written `YYYY-MM-DD`, read by
  `Assertion.from_dict` (`2026-02-30`, `2100-02-29`, `0000-01-01`,
  `20261117` and `17 November 2026`, each `'<date>' is no Gregorian
  calendar date written YYYY-MM-DD`), given to the constructor
  `Assertion(asserted_on=…)` (the same five strings, and the integer
  `20261117` and the `datetime.datetime(2026, 11, 17)`, neither a
  `datetime.date`, as `'20261117'` and `'2026-11-17 00:00:00'`) or read by
  `Link.from_dict` in the
  assertion of a slot or of a `part_of` entry, the message of the
  validator's `calendar_date`. `Assertion.from_dict` and the constructor
  read `2024-02-29` as `datetime.date(2024, 2, 29)`, and the constructor
  keeps `datetime.date(2024, 2, 29)` as given.
- **Normalisation.** `from_urls` collapses URLs that normalise to one URI or
  one identifier, keeping the first, puts the identifiers from URLs before
  the given ones (a mapping or a list of `Identifier`), keeps an absolute
  URI the registry does not recognise verbatim, and takes `pertains_to` as
  the relation of every level but `agent`. `with_uri` normalises and
  appends the same way; `with_identifier`, `with_record` and `with_part_of`
  append, `with_label` and `with_assertion` replace, `with_parts` replaces
  the reading's parts; each returns a new link and leaves the old one
  equal to what it was. `assertion_for` gives an entry's own assertion, or
  else its link's.
- **Each fact stored once.** A given identifier whose scheme is the scheme
  URI of a registry entry that mints entity URIs is stored as that entity
  URI, read back through the registry as a URL of the scheme, never as an
  identifier beside it. `from_urls` of the Wikidata item with
  `identifiers={"http://www.wikidata.org/entity/P435":
  "4A622B0D-B0C0-405E-B49E-05B70C108284"}` has `uri`
  `("http://www.wikidata.org/entity/Q146730",
  "http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284")`, no
  identifier, and the level `work` the entity URI tells; `from_urls` of the
  MusicBrainz work's URL with the same identifier keeps the one URI; an
  identifier `{"http://www.wikidata.org/entity/P356":
  "10.5281/zenodo.7473560"}` becomes `https://doi.org/10.5281/zenodo.7473560`;
  identifiers of IMSLP (`P839`, a scheme that mints none) and of the
  manifest's scheme `mb_beethoven_opus` (no entry) stay identifiers.
  `with_identifier` of the P435 identifier, in capitals, appends the
  entity URI to a link without it and returns a link equal to one already
  holding it; through a registry extended by an entry `x` (scheme
  `https://example.org/scheme`, template `https://example.org/entity/{value}`,
  pattern `https://example\.org/entity/([0-9]+)`) the identifier
  `{"https://example.org/scheme": "12"}` becomes
  `https://example.org/entity/12`, while the default registry keeps it an
  identifier. The validators do not read the registry: an identifier in
  the scheme `P435` validates.
- **The case of a value.** `with_uri` of
  `https://musicbrainz.org/work/4A622B0D-B0C0-405E-B49E-05B70C108284` on a
  link holding the work's URI returns a link equal to it: one URI.
- **Unknown keys** on a scheme, a link, an identifier, a record, an
  assertion, a part slot and a `part_of` entry survive `from_dict` and
  `to_dict` in both forms, take no part in equality, and are each listed by
  `unknown_keys` at its object (eight entries, an assertion held by a slot
  included).
- **One mechanism for both forms.** `to_dict()`, by default, leaves out
  every key of the object's kind in `DEFAULTS` equal to its default and
  `to_dict(minimal=False)` writes every one of them, so `complete` of a
  minimal link equals its complete link and `minimal` of a complete one its
  minimal link.

## One path rule for both validators

Among the diagnostic leaves of every violation, a validator reports the one
with the deepest instance path, ties going to the first reported. A
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

## The canonical order

Every array whose order carries no meaning has one order: `timelines` by ID;
in every timeline `children` by offset then ID, `conversion_maps` by ID,
`regions` by start, end, ID, `flow_control` by coordinate then ID; `groups`
by ID and `members` by code point; `measure_maps` by ID; `schemes` by ID;
`graphical.timestamps` by timeline (code point), then coordinate, then ID.
The arrays of the description layer keep their order: `links` (a display
order), a link's `uri` (the first preferred) and `parts` (the reading's
order), and every other array of a link.
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
  empty value null, `True` a boolean; an integer of 2^70 stays exact;
  `!!str 1` is the string `"1"` and `!!float 2` the float 2.0; an empty text,
  one of comments only and one of blank lines read as null; `"😀"`
  is U+1F600. Refused, with exactly the stated message naming the line and
  column: a repeated key, an anchor, an alias, an integer key and a
  collection key, the tags `!!timestamp`, `!!binary`, `!!set` and `!!omap`,
  `.inf`, `1e309`, the escape `\ud800` and a second document.
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
  `yaml_depth_257.yaml` at line 128, column 385. A JSON text holding a
  repeated key before the 257th collection is refused for the key. Every
  text nested 257 deep, made one level shallower, is read, to a value nested
  256 deep.
  The writers refuse a value deeper than 256 with the `ValueError` `a value
  nested deeper than 256 levels cannot be written` in every serialization:
  the array nested 257 deep (built in memory: no text a reader reads holds
  it), an object whose member holds an array 256 deep, and the array nested
  257 deep around a NaN (the depth is checked before the numbers); a list
  holding itself is refused the same way. The array nested 256 deep is
  written in every serialization and reads back equal, its canonical YAML
  being `readings/json_depth_256.expected.yaml` and its RFC 8785 JSON `[`
  256 times then `]` 256 times.
- **Columns count code points.** In both readers a character above U+FFFF
  counts once: the YAML anchor in `"😀": &x 1` is refused at column 6, and
  the escape `\ud800` in the JSON text `["😀", "\ud800"]` at column 7 (in
  UTF-16 code units they would be 7 and 8).
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
  itself raise `ValueError` naming the line and column. A single U+FEFF
  before a JSON text is removed; `serialization_of` gives `"json"` for `{}`
  after a U+FEFF, `"jcs"` for `{}`, `"yaml"` for `a: 1` and `"json"` for
  `{"a": "\ud800"}` and for `[1,` and never raises.
- **Every standard file.** The registry and the font metrics are reproduced
  byte for byte by `dumps(loads(text), serialization="json")`; every fixture,
  rejection case and warning case written in canonical YAML by `dumps`.

## The fixture set

The fixtures under `fixtures/0.2.0/` are emitted by timetoalign, never
written by hand (`test_fixtures.py`). For every fixture: `validate` accepts
it, `unknown_keys` lists nothing, `dumps` reproduces it, and the two round
trips of `complete` and `minimal` hold. `fixture_paths()` lists every
`*.yaml` under `fixtures/0.2.0/` except the drawings. The styled fixtures
`styled__score.yaml` and `styled__performance.yaml` carry the literally
stated `graphical` objects (20 and 3 statements, and the score's band order
with its markers band above its line and its map below), the
score's elements addressed by `Address` objects (`{"id": "intro", "part":
["label"]}`, `{"id": "da-capo", "part": ["label"]}`, and the wedge
`{"id": "timestamp_2"}` and coordinate label `{"id": "timestamp_2", "part":
["coordinate"]}` of its timestamp `length`); the thirteen drawn items of the
score, the wedges and coordinate labels of its timestamps `origin` and
`length` among them, resolve, by the
cascade ranking of `docs/drawing.md`, to thirteen distinct colours, and no
statement hides anything but child `a`.

The case accessors `fixture_paths`, `rejection_paths`, `rejection_case`,
`RejectionCase` and `warning_paths` are defined in `timetoshare.fixtures`,
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
  group holding both roots, and one statement selecting `{"id": "take
  2/intro"}`, each ID written as given, so the emitter keeps an ID holding
  a slash, a space, a colon or a `#` verbatim.
- **Named timestamps.** `timestamps.yaml` and its twin hold the three
  timestamps `timestamp_1` (`Downbeat`, `[3, 2]` on the root `clt_1`),
  `timestamp_2` (`Climax`, `[6, 1]` on `clt_1`) and `timestamp_3` (`Entry`,
  `[1, 1]` on the child `clt_2`), in that canonical order, and no
  statement. In the fixture `timestamp_1` states the default `display`
  `["wedge", "name", "cross_section"]`, `timestamp_2` `["wedge", "name"]`
  and `timestamp_3` all five words in canonical order; the twin leaves out
  only `timestamp_1`'s `display`. `identity_problems` finds nothing in
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

`docs/drawing.md` section 4's defaults block (three styles, 30 statements),
read from the file, validates as the `graphical` of the smallest file; the
statements naming `card`, `frame`, `inside: ancestor` and `shadow`
validate; so do the band selectors, `{"element": "band"}`, `{"element":
"band", "facet": <facet>}` for each of the five facets `markers`,
`conversion_maps`, `children`, `regions` and `flow_control`,
`{"addresses": [{"id": "score", "facet": "regions"}]}` and `{"inside":
"band"}`, each setting `display: none`, while a facet as a `class`
(`regions`) is refused at the selector's `class`, the element type `group`
at its `element`, and an empty `addresses` at `addresses`. In the
manifest whose groups `g1` and `g2` share the member `t`, a selector
`{"addresses": [{"id": "t", "part": ["card"]}]}`, every card of `t`,
validates. The schema shapes each entry of an order as an ID: the empty
string is refused at the entry, and a repeated entry (`line`, `markers`,
`line`) at the order, before any identity rule is read; property
bounds accept `stroke-width` and `rx` 0, `opacity` 0 and 1, positive
`font-size` and `max-width`, both forms of `stroke-dasharray`, and reject a
negative width and radius, opacity outside [0, 1], zero font size and maximum
width, non-text content and malformed dash text at the property path. A
timeline name holding control characters validates.

## Completing missing styles

`complete_styles` returns a new `graphical` object and never changes its input.
Every distinct style name named by a statement but absent from `styles` is
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

## Integer boundaries

Values whose integer length is `9007199254740993` (2^53 + 1) or
`9223372036854775807` (2^63 - 1) on a ticks axis validate and serialize back
to the same integer.

## Packaging

The test builds the sdist and the wheel with `uv build` twice (the wheel
from the checkout, and from the sdist as the release does) and requires
`timetoshare/docs/drawing.md`,
`timetoshare/schema/0.2.0/timetoshare.schema.json`,
`timetoshare/registry/schemes.json` and the five files of
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
