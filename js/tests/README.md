# Test strategy for the `@timetoalign/timetoshare` npm package

This suite proves the public contract of schema 0.2.0 in JavaScript: one
manifest shape, one schema document, one validator, the same answers as the
Python package. The rules and the reasoning that proves each one are stated
in the Python suite's README (`python/tests/README.md`); this suite asserts
the same cases with the same expected values, through inline documents
written in each test, and reads the same shared rejection and warning cases.
Where the two packages answer differently by design, this README says so.

## What the package promises

1. `validate` accepts exactly the manifests the Python package accepts and
   raises the first violation at the same path; `parse` is `loads`
   followed by `validate`. A checked value is typed as the lossless form:
   one test assigns it to `LosslessManifest` and, by a
   `@ts-expect-error` line, not to `Manifest`, and reads its lengths
   back as `9007199254740993n` and `JsonFloat(2)`.
2. `unknownKeys` and `manifestWarnings` return, for every manifest, the
   lists Python's `unknown_keys` and `manifest_warnings` return, byte for
   byte once written by `dumps`; `statementProblems` and
   `matchstampProblems` return the problems Python's `statement_problems`
   and `matchstamp_problems` return, with the same codes, paths and
   messages.
3. `complete` and `minimal` give the values Python's functions give, from a
   `DEFAULTS` table equal to the schema's `default`s, as Python's is; their
   typed forms take and give the generated `LosslessManifest` and
   `CompleteManifest`.
4. `dumps` writes every value in canonical YAML, pretty JSON and RFC 8785
   JSON as the README's "Serializations" specifies, the bytes of the shared
   hand-derived cases, which Python's `dumps` writes too; `loads` reads every
   serialization as "Reading" states. `fileForm` infers how a manifest
   file writes its manifest and `dumpsFile` writes a value back in that
   form, the same bytes as Python's `file_form` and `dumps_file`.
5. The generated files are the generator's output, and the npm package
   ships the schema document, the two specifications, the catalogue with
   its schema and the licence.
6. The statement functions (`withPair`, `withCandidate`, `withBelief`, `withContext`, …)
   and the catalogue functions (`readCatalogue`, `recognize`,
   `instantiate`, `verbOf`, `rectangles`) give the values Python's
   `timetoshare.statements` and `timetoshare.catalogue` give, and throw an
   `Error` with Python's message wherever Python raises `ValueError`.
7. A statement fixture read by a JSON-LD processor gives exactly the RDF
   dataset stored beside it, and no other manifest states anything.

## The fixtures

`fixtures.test.ts`: every manifest fixture (every `*.json` below
`fixtures/0.2.0/` except the drawings, found by its name in either
`.yaml` or `.json`), read by `loads`, validates, has
no unknown keys and no warnings (each states `@context`, and a bundle with
statements has an ID), and satisfies both round trips of `complete` and
`minimal`, as in the Python suite's "The fixture set".

## The schema document and the generated files

`schema.test.ts` checks invariants, not the tree's private shape, so a
refactor that keeps the accepted language stays green: the bundled `schema`
is the file; references are local and resolve; the public definitions exist and the root's description names exactly them; `ConversionMap` chooses between exactly the ten
map types, `Selector.class` admits the six timeline classes and the ten types, or an `Iri`,
`Facet`, `Part`, `ElementType`, the words of `Selector.coordinates`, the words of a `Timestamp`'s `display` (`TIMESTAMP_DISPLAY`) and of an `Elision`'s (`ELISION_DISPLAY`) are exactly the Python suite's lists, an `Elision`'s `width` declares the Python suite's three forms, one of them required by its `oneOf`, and accepts and refuses the Python suite's widths, and
each measure view fixes its target unit over
`MeasureView`, which fixes the source unit; the unit
table's consts are exactly the keys of
`UNITS` in order, each description naming that unit's domain, modality
and default number type, as in the Python suite; `Name`, `Meta` and `MapBase` are the
shared definitions every `name`, every `meta` and every conversion map
refers to (a measure view through `MeasureView`, whose `allOf` is
`MapBase`, as in the Python suite), the
references are `Id`s and `Selector.addresses` holds `Address`es, `Id` and
`Address` accepting and refusing the Python suite's values; the patterns
ending in `$` are exactly the Python suite's five, each refusing its value
followed by a newline, and an `Order` refusing a trailing newline too, so
Ajv and Python's `jsonschema` agree on every trailing newline; no node
carries `additionalProperties: false` or `unevaluatedProperties`, `Address`
included, and no key begins with `x-`; every object
declares, itself or in its `allOf` bases at any depth, what its branches declare; every
discriminated union tags each branch with a distinct required constant; the
`default`s, read through references and bases, are exactly `DEFAULTS`;
the statements' invariants: `statements` and `provenance` on exactly
`Manifest`, `Timeline` and `Region` (besides `Context`, which declares every
format term), without a default, `@context` on `Manifest` only, no `links`
and no `schemes` anywhere, a provenance entry the bundled `ProvenanceRecord`
(`provenance.schema.json`, beside the manifest schema, bundled by
`bundleSchemas`: the generated `schema` equals the bundle of the two files,
every reference local, a definition of both names refused) with `property`
and `value`, its keys exactly `basis`, `beliefs`, `date`, `match`, `method`,
`note`, `service` and `stated_by`, a belief's `belief`, the `match` and
`method` words equal to `BELIEFS`, `MATCHES` and `METHODS`, the white-space
class of `Iri`, `IriReference` and `PrefixIri` equal to `BLANK`; the
`Context` definition fixes, required and in order, exactly the terms of
`FORMAT_CONTEXT` with their values, and takes every other key as a prefix
(`PrefixIri`); and the values `Iri`, `IriReference`, `PrefixName`,
`PrefixIri` and `LanguageTag` accept and refuse (a compact IRI, an absolute
one, a URN; a bare word, an empty prefix or suffix, a leading digit, white
space and a trailing newline; a relative reference, never a blank node
`_:b0` or a keyword `@id`; a prefix name that is no element key and no URI
scheme; a namespace ending in `/` or `#`; a language tag of subtags up to
eight characters). The patterns ending in `$` are five. `bundleSchemas` leads every reference to the same place in the bundle as in its own document, each case on a small pair of schemas exactly as in the Python suite's "The bundle": from the provenance schema, `timetoshare.schema.json` gives `#`, `#` gives `#/$defs/ProvenanceRecord`, `provenance.schema.json#/$defs/P` gives `#/$defs/P` and `#/properties/a` gives `#/$defs/ProvenanceRecord/properties/a`, and so on for every case listed there; a reference to any other document is refused with the same message. `generated.test.ts`: a fresh generator run exports the committed
names, which are every definition, the complete form of exactly the
definitions holding a default, and `LosslessManifest`, and `catalogue.ts`
exports the catalogue file's value as `catalogue` (equal, as `compactJson`
texts, to the value `loads` reads from the file); the committed text is
`check:drift`'s oracle. The generation view turns a lone conditional (a
statement value is a value object where it holds `@value`, else a node)
into the union of its two arms, drops `not` and names the type an
`additionalProperties` reference stands for, so a value node, whose values
hold value nodes, is typed once. Statements marked `@ts-expect-error` (a
misspelt key, a missing `length` or child `offset`, a complete form missing
a defaulted key, a three-member Fraction) make a looser generation break
the typecheck gate. A complete flow-control element without `targets` and
`ends` compiles: neither is a key of every element nor has a default, so
the complete form keeps both optional. A complete
`MeasureRecordMap` carries `id`, `name`, `source_unit`, `target_unit` and
`measure_map`, the members of both its bases.

## The validator

`validate.test.ts`, `identity.test.ts` and `segment-lines.test.ts` prove the
rules of the Python README's sections "The version marker", "Reading by
the declared number type", "The rules and their codes" and "What proves the rules"
with the same inline documents, paths, codes and messages, in the same
order: every semantic rule by its smallest document with one problem, which
`validate` raises too, and one document breaking every step once, whose
problems and codes `identityProblems` lists in order and whose first problem
`validate` raises. The rules live in seven modules of the same names and
decomposition in both packages, so a rule changes in both or the shared
cases fail. The packages differ only where JavaScript must:

- **Messages.** Every message is the same text in both packages: an ID, a
  unit or an order entry in single quotes, as written (`'m' is not unique
  in the manifest, first at …`), a value as the writers spell it
  (`unsupported TimeToShare version "9.9.9"; this package reads 0.2.0
  only`). A schema violation is worded as Python's validator words it, not
  as Ajv does: the message `jsonschema` 4.26 gives the keyword, each value
  spelled as Python's `repr` spells the value Python reads (`None`,
  `True`, `2.0` for a `JsonFloat`, a string holding `'` and no `"` in
  double quotes), and the
  three shapes the Python README's "One path rule for both validators"
  words itself (`'furlongs' is not one of ['number', …]`, `the key
  'target' is not admitted here`, `'#a\tb' holds U+0009: …`). Ajv runs
  with `verbose` so each error carries its data and schemas; the message
  spells the value as read, its `JsonFloat`s and `bigint`s kept, so a
  value read through `plain` may be spelled otherwise (`2` for `2.0`).
- **Integral floats.** `loads` keeps `2.0` as a `JsonFloat`, so
  `length 2.0` on a fraction axis is "a float … write [2, 1]" as in Python;
  a number built in code as `2` is an int. A `JsonFloat` member of a
  Fraction pair is the integer it equals, as Python reads `8.0`; the Python
  README's manifest of respellable values validates, and `complete`,
  `minimal` and `canonicalOrder` give, compared as `compactJson` texts,
  what they give for its canonical twin, a `JsonFloat` member of an
  own-axis Fraction becoming a plain integer, a `JsonFloat` on an int axis
  a plain integer, an integer on a float axis a `JsonFloat`, while its
  conversion-map numbers and MeasureMap rows, which no number type governs,
  stay as written in both; `dumps` writes the twin's text. Rewritten floats are spelled as Python spells them (`write
  2.0`, `write 0.75`, `ends at 1.0`).
- **Integers beyond 2^53.** `loads` reads `9007199254740993` as a
  `bigint`, so on a float axis it is "an int … write a float";
  `9007199254740992n` and `10n ** 20n` are exactly floats and validate.
  `10n ** 400n` has no double (`Number` gives infinity), so containment
  and segment lines add it exactly, as Python adds an integer that
  `float` cannot convert, and both spell the end alike.
- **Non-finite numbers.** The readers refuse them and a `JsonFloat` cannot
  hold one, so only a number built in code reaches the finite rule; the
  tests build infinity, NaN and negative infinity as Python's do.

**The acceptance table** of the Python README ("Reading by the declared
number type") is run here row by row on the same file,
`fixtures/acceptances/0.2.0/numbers.yaml`, read by `loads`
(`validate.test.ts`, "the acceptance table"): the same fourteen rows
stated literally, each value the `offset` of the same root; a refused row
throws `SchemaValidationError` with the code `representation` at
`["timelines", 0, "offset"]`; an accepted row validates, `exactValue` of
what it states equals `exactValue` of `read` (both exported from the
package index, with `jsonInteger`), and `canonicalOrder` writes the offset
as `read`, compared as `dumps` texts. So `[1, 8.0]` (a `JsonFloat` member)
is 1/8 and `9007199254740993` (a `bigint`) is refused on a float axis, as
in Python.

**A selector's `coordinates`** (the Python README's "The graphical
object"): `{coordinates: "primary"}` and `{element: "wedge", coordinates:
"secondary"}` each validate and leave `unknownKeys` empty
(`validate.test.ts`), and the shared case `rule_select_coordinates_unknown`
refuses any other word at the selector's `coordinates` with the Python
suite's code, path and message.

## MatchStamps and resources

The Python README's section "MatchStamps and resources" is proved here with
the same values: the ID positions of MatchStamps, anchors and resources
and the IDs of `match_claims`, which keep their `#` (`ids.test.ts`); the
order by ID and `ANCHOR_DISPLAY` (`manifest.test.ts`, whose reversal walk
reverses `resources`, `matchstamps`, `alignment_anchors` and an anchor's
`display`); the defaults of a match timestamp and an anchor
(`defaults.test.ts`, and the `then` and `else` arms in `schema.test.ts`);
the eleven messages of its table and the one list of every problem
(`validate.test.ts`, "the MatchStamp and resource rules"); the MatchStamps
alone (`validate.test.ts`, "the MatchStamps alone"): `matchstampProblems`
gives, for each of the nine MatchStamp rejection cases, a first problem
equal in code, path and message to the one `validate` throws, nothing for
every fixture (`bundles/bundle_matchstamp_groupstamp` among them) and
every other rejection case (`groupstamp_match_without_group` among them), the schema's problem at a
match timestamp without `timeline`, and nothing for a manifest whose
ordinary timestamps include one that is no object.

## Elisions

The Python README's section "Elisions" is proved here with the same values:
the schema's words, `name`, width forms, element types and part words,
and the values the four elision properties of `Declaration` admit and
refuse (`schema.test.ts`); the defaults (`defaults.test.ts`, `elisions:
[]` and an elision's `display`, its `name` and `width` never added); the order by timeline,
start and ID, the `display` order and the respelling of `start`, `end`
and `span` (`manifest.test.ts`); the ID positions (`ids.test.ts`, the
manifest naming every position holds the elision `elision_1` on `verse`);
the fifteen shared cases with their messages (`validate.test.ts`, "the shared
rejection cases"); and the inline documents of the rules, the overlapping
elisions accepted without a warning, the number-type readings and the
shared ID scope (`identity.test.ts`), each with the Python suite's code,
path and message.

## Groupstamps

The Python README's section "Groupstamps" is proved here with the same
values: `groupstamp` defaulting to `false` on both kinds of timestamp
(`defaults.test.ts`, and the `then` arm in `schema.test.ts`); the four
`groupstamp` cases with their messages (a root in no group, a child whose
ancestors are in no group, the parent of a member, and a match timestamp
on a timeline in no group, `groupstamp_match_without_group`, which
`matchstampProblems` passes over like the other three;
`validate.test.ts`, `identity.test.ts`); the one list of every problem,
the groupstamp match timestamp in no group first (`validate.test.ts`);
and the four groupstamp fixtures, `groups/group_groupstamp`,
`groups/group_groupstamp_child_member` (a member's child, accepted),
`bundles/bundle_groupstamp_shared_member` (a member of two groups) and
`bundles/bundle_matchstamp_groupstamp` (a match timestamp on a member of
two groups), each valid in both forms (`fixtures.test.ts`), the last with
no problem from `matchstampProblems` either.

## Flow

`flow.test.ts` asserts the Python README's section "Flow" with the same
documents, paths and messages, the converter aside, which is a Python script
and is tested there: the schema of the five roles, of a destination and its
conditions, of FlowMaps and virtual timelines, and the words of the open
vocabularies in its descriptions; the earlier form refused before the
schema with the converter named; rejected elements left out of the rules;
coordinates and places on a timeline of unknown length, at the ends of the
axis and on a float axis (a place is the double sum); an `after` naming one
destination by its place; the chunks, the canonical flag and the IDs of
FlowMaps and virtual timelines, their order and respelling; a virtual
timeline held to its map under `virtual_timeline`, with the same documents:
a ring reported at each of its members and nowhere else, a FlowMap applied
within the tree of its own root unless `through` is stated, the length the
sum of chunks and gaps compared by value, spelled as an integer on an
integer axis, and the six cases where no sum is read; the warnings of
a manifestation and a convention outside the vocabularies, sorted by path
and then code; the provenance of a flow-control element and of a FlowMap
under the entry rules; and the agreement of every expected flow under
`fixtures/flows/0.2.0/` with its manifest, the boundaries of the atomic
sections computed in the test, `never_played` once for each stretch the
default flow leaves out, at its start, and each FlowMap of
`sonata_exposition` with its one provenance entry `{method: inferred}`. The shared rejection and warning cases pin
every rule's code, path and message for both packages; the canonical order
of a jump's destinations lies in `manifest.test.ts`, the ID positions in
`ids.test.ts`, the defaults in `defaults.test.ts` and `schema.test.ts`.

The defaults block of section 4 of `docs/drawing.md`, three styles and 43
rules, among them one for each of the element types `jump`, `break`,
`section_break`, `barline`, `symbol`, `bracket` and `leader`, and one
selecting the atomic sections by the `class` `tts:AtomicSection`,
validates as the `graphical` object of the smallest manifest
(`validate.test.ts`). So do the selectors of the three element types
`symbol`, `bracket` and `leader`, addresses with the parts `symbol`,
`bracket` and `leader`, a `class` written as a compact and as a full IRI,
and `label-display` set to `none`, `label` and `name id label`, while a
`class` that is neither a class word nor an IRI (`tts AtomicSection`) is
refused at the selector's `class` (`validate.test.ts`).

## Shared rejection cases

Each of the 247 cases (`validate.test.ts`), found by its name whatever
its extension and read by `loads`, is stored as the writers write it,
byte for byte (a canonical YAML text is `dumps`'s bytes, a JSON text the
bytes of `dumps` in pretty JSON) and raises
`SchemaValidationError` with its stored path and code through `validate`
on the read value, through `validate` on the value as `JSON.parse` would
read it (`plain`: every `JsonFloat` and `bigint` a plain number), and
through `parse` of its compact text, and with its stored message through
`validate` on the read value and through `parse`, the message the Python
suite holds its validator to, so both packages give every case one
message; `version_unknown` raises `UnsupportedVersionError` with its
stored message. Each case is read through one reader, the mirror
of Python's `rejection_case`, which puts the infinity or NaN a
`finite_number` case names at its path; such a case has one reading, the
reader's value, since no text carries it, and a test pins the two values in
place. Two plain readings are exempt: `float_axis_int_not_exact`, since
`9007199254740993` becomes `9007199254740992`, exactly a float, and
`statement_value_integral_float`, since the statement value `1.0` becomes
the integer `1`; the test asserts that these lossy readings validate. The set of names and the codes of the cases are stated
literally, and the cases whose messages the Python suite pins carry the same
messages here (`identity.test.ts`, `statements.test.ts`).

A MeasureMap row's `volta` is one pass or several, kept as written (the
Python README's "What proves the rules" describes the five cases
`measure_map_row_volta_*` and their one manifest). The acceptance
(`validate.test.ts`) puts `1`, `[1]`, `[1, 3]` and `[3, 1]` in the third
row of that manifest: each validates, and the row reads back with that
very value, an integer an integer and a list a list in its order, from
`minimal`, `complete`, `canonicalOrder` and from `loads` of the text
`dumps` writes in each of the three serializations. The generated type
admits both forms (`types.test.ts`): a `MeasureMapRow` takes `volta: 2`
and `volta: [1, 3]`, and neither an empty list nor a string.

The path rule is the Python README's ("One path rule for both
validators"): the deepest leaf, then the path that comes first element by
element (`comparePaths`), then the first the walk reports. Ajv reports
its errors in an order of its own, so the validator reads from them the
leaves Python's walk reports (a `oneOf` or `anyOf` of constants is one, a
failed `oneOf`, `anyOf`, `if` or `propertyNames` none, its branches' errors
being the leaves, a discriminator naming no branch the `oneOf` failing
whole) and orders the leaves at one path as the walk visits them: the
schemas applied there in the order the document writes their keywords,
`$ref`, `allOf`, `anyOf`, `oneOf` and `if` in place, then a schema's
keywords in its own order. Ajv applies a discriminated `oneOf` to the
candidate its tag selects through its `discriminator` option, which the
schema's `ConversionMap` and `Coordinate` read only on an object, each
typing itself `object` (Ajv's discriminator would otherwise accept a map
`0` and throw on a map `null`). The shared cases pin the paths and the
messages; the cases of several problems (`fixtures/precedence/0.2.0/`)
pin the order, each built from its fixture by the members it sets, with
the code, path and message both packages report.

## Unknown keys

`unknown-keys.test.ts`: every shared warning case validates, holds exactly
`manifest`, `unknown_keys` and `warnings`, its text is stored
as the writers write it, `dumps(unknownKeys(manifest))` equals
`dumps(case.unknown_keys)` and `dumps(manifestWarnings(manifest))` equals
`dumps(case.warnings)`; the five cases of warnings (`context_absent`,
`bundle_blank_statements`, `bundle_blank_provenance`,
`manifestation_unknown`, `convention_unknown`) are among them;
`several_depths` lists its sixteen entries in the
stated order; keys inside `meta`, `styles`,
`graphical.order` and unknown values are not reported; the sort (keys by
code point, `ﬀ` before `😀`, indices by number, `timelines[2]` before
`timelines[10]`); an invalid value raises before any key is listed. The
validator walks the value with the in-memory closed variant of the Python
README ("One walk"); only where the variant refuses it does it walk the
document itself, which decides validity, and then reads each key from the
variant's `unevaluatedProperties` errors. A discriminated `oneOf` evaluates
only the candidate its tag selects, so a key is never reported from a
candidate the value does not match (the nested conversion map of
`several_depths` proves it). The variant leaves the maps keyed by data open
(`@context`, statements and value nodes, whose `additionalProperties`
admits every key), and a key refused inside a `oneOf`/`anyOf` branch the
document refuses the value (a statement value read as a `list` object, say)
is not listed: only a branch that fails for undeclared keys alone counts,
as in Python. Two inputs prove it, each with the list Python's
`unknown_keys` returns for it (the first is also a Python test):
`nielsen_record` with the key `x` added to the first provenance entry of
`statements.schema:about[0]` lists exactly `x` at
`["statements", "schema:about", 0, "provenance", 0]`, never the keys of the
value node that holds it; and the same fixture whose `@context` declares one more prefix
`ex` (`http://example.org/`), with a pair `ex:extra` on that value node whose
value node states `ex:part` and a provenance entry for it carrying `zz`, and
an `x` on the manifest, lists exactly `x` at `[]` and `zz` at
`["statements", "schema:about", 0, "ex:extra", 0, "provenance", 0]`: the
prefix, the pairs and the value nodes' own keys are declared by their maps.
A third input is also a Python test: the bare manifest with `provenance:
[{property, value, beliefs: [{actor, belief, date, x: 1}]}]` lists exactly
`x` at `["provenance", 0, "beliefs", 0]`, never the keys the provenance
record declares on the entry (`beliefs`), though the key below fails the
record the entry is `allOf`.
No test runs the two languages side by side; the lists are literal. The keys belong to one run, so a refused
manifest's keys never appear in the next run's list (`validate.test.ts`).

## The units

`validate.test.ts` proves the Python README's section "The units" with
the same roots: `css_pixels` and `user_units` validate with `float` and
`fraction` exactly where `points` does, all three refuse `int`, and `px` and `uu` are refused with the
code `schema` at `["timelines", 0, "unit"]`. `defaults.ts` completes a
timeline's `number_type` for exactly the keys of `UNITS`, its
one list of units, so the default number type of both new units is
`float` in `defaults.test.ts` as in the Python suite.

Which number types a unit admits is the Python README's paragraph of that
name, proved with the same values: `UNITS` (exported from the package
index) stated literally row by row in `schema.test.ts`, its consts the
schema's `TimeUnit` in order and the schema's `Timeline` conditional
matching its admitted number types, the `Coordinate` conditional equal to
it, and the same seven single coordinates checked against `Coordinate`
alone, refused at the same paths by the same keywords (Ajv's report of the
`if` that chose the branch set aside); the three shared cases
`timeline_ticks_float`, `timeline_seconds_int` and `timeline_quarters_int`;
and in `validate.test.ts` every unit with every number type, at a root and
at a child, valid exactly where the row admits it, else `schema` at the
`number_type`.

The property bounds of a declaration are the Python README's: a wedge's
`rotation` of −45, −180 and 180 validates, and so does the integral float
`45.0` (`new JsonFloat(45)`), which is the integer 45 however it is spelled;
181, −180.5 and `"45"` are refused at the property.

## Defaults

`defaults.test.ts` asserts the Python README's section "Defaults: the
complete and the minimal form" with the same documents and values. A value
equals its default in value: a `LinearMap`'s `scalar: [1, 1]` and `offset:
new JsonFloat(-0)` are left out as the defaults `1` and `0` are, and the complete form of what
remains states the defaults; the round trips compare `dumps` texts, which
tell `1.0` from `1`. No result shares
an object with `DEFAULTS`. The typed forms' oracle is the fixtures: each
minimal twin (103, one per fixture) completes to the canonical YAML of its
fixture, keeps it in canonical order,
and strips back to its own; a literal `CompleteManifest` compiles, and
keys whose default is absent (`id`, `graphical`, a root's `offset`) stay
optional.

## Statements and provenance

`statements.test.ts` asserts the Python README's sections on statements with
the same documents, values and messages. The belief filter's states are
`BELIEF_STATES` (`true`, `undecided`, `unlikely`, `false`) and
`DEFAULT_BELIEFS` the first three; `checkBeliefFilter` returns the states of
a collection, in any order, empty included, and refuses a single string, a
value that is no iterable collection (`null`, `undefined`, a plain object
and a `Map`, which stands for Python's mapping and is spelled as the object of its entries)
and a collection naming an unknown word, a member that is no string
included, with the Python package's messages, byte for byte (a member that
is no string spelled unquoted: `true is no belief state: …`). Its oracles are the
two manifests of the specification, read from YAML text by `loads` in the
file form:

- **M1**: `@context` the format's terms with `schema`, `wd` and `wdt`; `id`
  `#rec`; one root `#cpt_1` in seconds of unknown length with a region
  `#region_1` and a child `#cpt_2`. `subjectPath` gives `[]` for `null` and
  the paths of the root, the child and the region for their IDs as written;
  a bare ID names nothing (Python's message). A performer stated with
  provenance writes exactly the stated pair and one entry whose
  value is the thing's `id` alone; the same pair again, and the same thing
  by its full IRI, are refused as "already has this value", which proves
  that pairs compare by expanded IRI. A type stated with provenance writes
  `type` and an entry `rdf:type` / `{id}`. Removing both leaves neither
  `statements` nor `provenance`: emptied lists, containers and annotations
  go. A candidate, a person's statement and beliefs walk one pair, with
  the values of the Python README ("Writing pairs"): `withCandidate`
  leaves `statements` as they were and is the one candidate; again, it
  replaces the entry in place and keeps its beliefs; `withPair` with
  `actor` and `date` states the value with its label, keeps the entry and
  records the person's belief `"true"`; `withBelief` of two actors `"false"`
  leaves the pair stated, the editor's replaced in place; `withoutPair`
  gives M1 back; `candidates` offers a candidate the editor believes
  `"false"` to every actor but the editor; a belief in a pair never stated
  creates the entry. Every function leaves its arguments as they were.
- **M2**: the two timelines of the LayerIt recording, a score encoding and
  a video, with the vocabulary of every kind of value (a datatyped
  literal, nodes with labels and `schema:sameAs`, several classes, a full
  IRI). `usedPrefixes` lists the nine prefixes, and `withContext` of M2
  without its `@context`, given the test catalogue's prefixes, rebuilds
  exactly M2's `@context`; a prefix declared nowhere is refused with
  Python's message.

Every error message of the statement functions is asserted once: a
property that is no IRI, a pair stated twice, a pair missing, a stated pair
as a candidate, an actor without a date, a belief none of the three
(`1`, `0`, `"likely"`, `null`, spelled as JSON spells them), a path
addressing nothing, an impossible date. A path addresses an element, or a node held in a list
under an element's `statements`: the path of the container itself and a
path through a node's `provenance` (to an entry's node `value`, which
exists) are refused with the same message, while the node holding that
`provenance` is read. `samePair` is proved by pairs that are equal (a
compact and a full IRI, `type` and `rdf:type` with `{id}`, a node with a
label and one without, blank nodes with keys in another order) and unequal
(`true` and `1`, `1` and `"1"`, value objects of other languages, lists in
another order, and `type` against `rdf:type` with the same string in either
order: only the key `type` reads a string as the thing `{id}`, so an
entry's literal class is no class); `expandIri` by each of its branches.

The statement rules are proved by inline documents built on the base
manifest of the shared rejection cases (the terms with `schema`, `wd` and
`wdt`, one root `#clt_1` in quarters): each code by its smallest document,
raised by `validate` with Python's path and message, and the schema's
refusals of a value at the value's own path (a value object with both a
language and a type, an empty node, a blank-node `id`, a `null` in ordered
values), which the conditional between value object and node makes
deterministic; `statementProblems`
lists every problem of one document breaking each rule once, in rule order,
and checks the members' schema first (a schema problem hides the rules);
`manifestWarnings` gives `context_absent` and `bundle_blank` at their paths,
sorted, and nothing for a manifest with a context and an ID. M2 itself
validates and has no warnings. An entry may match a stated pair or none;
`belief_actor` refuses an actor's second belief in one entry, actors
compared as their expanded IRIs (`wd:Q1`, then
`http://www.wikidata.org/entity/Q1`), and a belief's `actor` is a
reference the rule `dangling_target` reads. The actors of beliefs are
renamed and dropped with their element by `withReferencesRenamed`.

`subjects` walks the subjects in subject order, proved by the Python
README's manifest ("The subjects in subject order"): the same `(path,
kind, id)` sequence, each element yielded as the object it is, and nothing
for a value that is no object.

`withReferencesRenamed` and `compactIri` are proved by the Python README's
values ("References to elements renamed and dropped", "Compact IRIs"): M1
with each reference position holding `#cpt_2` once, renamed to `#cpt_3`
(the whole result equal to the document built by hand, the other
manifest's `other.yaml#cpt_2` unchanged), dropped (the root keeps its type
and that pair's entry without `basis` and `service`, the bundle keeps the
other manifest's reference and no `provenance`) and renamed where nothing
names the ID (equal to the input); and `compactIri` over the shipped
catalogue's prefixes and aliases (`defaultCatalogue`) for the nine IRIs of
the specification, plus the longest-namespace rule, the code-point tie and
a rest outside the compact form. Both functions leave their arguments as
they were.

## The catalogue

`catalogue.test.ts` reads the test catalogue of the specification, held
inline in `tests/catalogue.ts` (`CATALOGUE_TEST`: ten prefixes, the
schema.org alias, the systems `wikidata`, `musicbrainz`, `melody`,
`fallback`, the verbs `is_a`, `same_as`, `performed_by`, `conducted_by`,
`version_or_edition_of`, `part_of`, one type `video`), and asserts the
specification's values: `recognize` of a Wikidata page, of a MusicBrainz
work in capitals (value and IRI lowered) and of a text that is no URL;
`verbOf` of a relator, of a contributor node with the role `conductor` and
with `pianist` (most constants win), of `dcterms:hasPart` (the inverse
reading), of `dcterms:created` (none), of a type and of a full
`https://schema.org/` key (the alias); `instantiate` with a label, with a
role slot, without it (refused) and of a type; `rectangles` of both
timelines of M2, with their verbs, pairs, things and labels.

Five readings are pinned beside them, each with a value that the other
reading would answer differently:

- `verbOf` of `rdf:type` with `schema:X`, under M2's context with `rdf`
  declared, is `is_a`: a property is read by its IRI, and the pattern key
  `type` is `rdf:type`.
- A slot matches no ordered values: `type` with `{list: [schema:X]}` is
  read by no verb, nor is a contributor node whose role is `{list:
  [piano]}`.
- A template key's items are matched against every value under a key of
  the same IRI, and the best match counts once: with a verb
  `accompanied_by` appended whose role template lists `accompanist` and
  `conductor`, a contributor (type `schema:OrganizationRole`) with the roles
  `conductor` and `accompanist` ties `conducted_by` at two constants and
  the earlier verb wins, `conducted_by`; with the role `accompanist` alone
  it is `accompanied_by`, whose two items need not both be present.
- Two pairs of one verb read the same way join where both value nodes
  carry a string `label` and the labels are equal, though they name no
  common thing: on M1's root, `schema:exampleOfWork` `{id: <the
  MusicBrainz work>, label: Clair de Lune}` and `wdt:P629` `{id:
  wd:Q29117946, label: Clair de Lune}` are exactly the empty `is_a` and one
  `version_or_edition_of` with both pairs in that order, its things the
  MusicBrainz and the Wikidata IRI, label `Clair de Lune`. Labels compare
  as strings, exactly (`Clair de lune` on the second gives two
  `version_or_edition_of` rectangles), and only within one verb (`rel:prf`
  `{id: wd:Q1, label: X}` and `wdt:P629` `{id: wd:Q2, label: X}` stay
  `performed_by` and `version_or_edition_of`).
- The things of a node without `id` are the `id`s under its `schema:sameAs`
  (and `owl:sameAs`): on a subject stating `rel:prf` `{id: viaf:113931950}`
  and a MusicBrainz contributor node without `id` whose `schema:sameAs` is
  that VIAF ID, both pairs are `performed_by` and share the thing, so they
  form one rectangle with the one thing `http://viaf.org/viaf/113931950`. Every
cross-reference error of `readCatalogue` is raised in its order by a
catalogue holding that one fault. The shipped `catalogue/catalogue.yaml`
validates against `catalogue/catalogue.schema.json` (Ajv), passes
`readCatalogue`, is what `dumps` writes for its value, and is what
`defaultCatalogue` returns.

## RDF

`rdf.test.ts` reads each statement fixture under `fixtures/0.2.0/statements/`
and its minimal twin with jsonld.js (decision record 0016), handing it a
plain value (every `JsonFloat` and `bigint` a number), with base
`https://example.org/manifests/<name>.yaml`, `safe: false` (the format's own
keys are dropped by design) and a document loader that refuses every fetch,
so the inline context is all a processor reads. For both, it asserts:

1. the canonical N-Quads (RDFC-1.0) equal `fixtures/rdf/0.2.0/<name>.nq`
   byte for byte, the bytes Python's PyLD gives;
2. every other fixture under `fixtures/0.2.0/` (drawings excluded) gives the
   empty dataset: no element states anything by being written; the two
   exceptions are `flow/sonata_exposition` and `volta_run` with their
   twins, whose three and five regions state that they are atomic
   sections (`volta_run`'s `region_1` is none): the dataset is exactly,
   per such region, the triple typing it `AtomicSection` in the format's
   namespace and the reified statement of that pair with the method
   `Inferred`, five quads; the FlowMaps and their provenance add none,
   `flow_maps` being no term of the context;
3. no IRI of the dataset begins with `p:` for a prefix `p` of the fixture's
   context, and every IRI begins with `http:`, `https:`, `urn:`, `tag:`,
   `mailto:` or `info:`: every compact IRI was expanded;
4. every predicate is an expanded key of a statements container or node,
   `rdf:type`, `rdfs:label`, or one of the annotation's properties
   (`rdf:subject`, `rdf:predicate`, `rdf:object`, `prov:wasAttributedTo`,
   `dcterms:date`, `prov:hadPrimarySource`, `rdfs:comment` and the format's
   `method`, `service`, `match`, `beliefs`, `actor`, `belief`);
5. for every candidate (an entry whose pair its subject does not state)
   whose subject has an IRI and whose value is a thing or a plain literal,
   the triple subject–property–value is absent: a candidate is never
   asserted;
6. the distinct subjects of `rdf:subject` are as many as the provenance
   entries of the fixture: one reified statement per entry.

The statement fixtures and their `.nq` files are emitted by the fixture
scripts; until they exist, (1), (3) to (6) have no case and (2) runs over
the fixtures there are.

## The serializations

`serialization.test.ts` walks `fixtures/serializations/` as its README
states. A case or a reading added there is tested without a change here;
a refusal or a writer refusal is named in the test's table with what it
throws, and each table is checked against its directory, the files equal
to the table's keys, so a file added, removed or renamed on one side only
fails. No test is skipped:

- **Cases.** The directory holds 35 cases, the five manifest cases and
  the eight top-level JSON texts named below among them. The value V of
  each case is read from its
  `pretty.json`; `canonical.yaml` reads to V, kind for kind (an integer
  equals only an integer, a float only a float, `-0.0` differs from
  `0.0`); `dumps(V)` with each serialization gives the bytes of its file,
  and where `rfc8785.json` is missing `"jcs"` throws a `RangeError`;
  `rfc8785.json` reads to V with every float RFC 8785 spells without `.`
  or exponent as the integer of equal value; each text read and written
  again in its own serialization gives its own bytes; for each of the
  five manifest cases alone (`readme_manifest`,
  `manifest_canonical_order`, `manifest_order_by_value`,
  `manifest_ties_kept`, `manifest_display_order`) the value read from
  `rfc8785.json` is written as `canonical.yaml`; `serializationOf` names `canonical.yaml` `"json"` for
  the eight top-level JSON texts and `"yaml"` otherwise, `pretty.json`
  `"json"` and `rfc8785.json` `"jcs"`.
- **Readings.** Every reading has its `.expected.yaml`, and every
  expected text belongs to a reading. Every file of `readings/` but the
  expected ones reads to the
  value whose canonical YAML is its `.expected.yaml`, and, where present,
  whose RFC 8785 JSON is its `.expected.rfc8785.json`; each expected text
  gives its own bytes; `serializationOf` names a `.json` reading `"json"`, a
  `.yaml` one `"yaml"` and every expected RFC 8785 text `"jcs"`.
- **Refusals.** The table names each of the 88 files with the error it
  throws: a text read as YAML a `YamlSyntaxError`, through `loads` and
  `parseYaml`; a text read as JSON a `JsonSyntaxError`, through `loads`
  and `parseJson` (the three `flow_*` texts meant as YAML among them), a
  `RangeError` for the five whose float rounds to an infinity
  (`json_float_overflow*`, `json_top_level_float_overflow`).
  `serializationOf` names each `"yaml"` or `"json"` as it is read, never
  throwing.
- **Writer refusals.** The table names each of the 21 files with the
  serializations that refuse its value. Each file reads, and is named
  `"json"` or `"yaml"` by its extension; writing its value throws in each
  serialization the table names (a `RangeError`, or a `TypeError` for the
  `order_*` texts) and succeeds in the others.

The unit tests beside the walk pin what the cases leave to a package:

- **The JSON reader** (`manifest.test.ts`): `0.5`, `2.0`,
  `123456789012345678`, `-0`, `-0.0`, `1E5` read losslessly; key order
  survives, array-index keys included; eleven malformed texts, three
  repeated keys and nine lone surrogates (escaped, as themselves, in a
  key, reversed, followed by a letter, and a high surrogate and a low one
  of which one is escaped and the other stands as itself, which pair with
  neither, as in Python) pin the message, offset, line and column of each
  `JsonSyntaxError`; `[1e400]` throws a `RangeError` naming line 1, column
  2; a pair of surrogate escapes, and a pair standing as itself, is one
  character; one
  leading byte order mark is removed and a second refused at offset 0.
- **The YAML reader** (`serialization.test.ts`): the core schema (`0x1F`,
  `0o17`, a 30-digit integer, `2.0`, `-0.0`, `.5`, `no`, a date, `~`,
  `True`, `'12'`), key order, an empty or comment-only text as null, and
  twenty-two refusals with their message, offset, line and column: an
  anchor at its `&`, an alias, a repeated key, a collection and an integer
  as keys, an escaped lone surrogate at the string, a lone surrogate as
  itself and U+007F where they stand (outside YAML's printable set),
  `.inf`, `-.Inf`, `.nan`, `1e309`; every tag at the tag as `a tag`,
  whatever it names (`!!binary`, `!!timestamp`, `!!set`, `!!omap`,
  `!local`, `!!str 1`, the non-specific `!`, `!!float 1`, `!!str` on a
  sequence), never as the parser's `TAG_RESOLVE_FAILED` at the same
  place; and a second document.
- **The nesting limit** (`serialization.test.ts`): a scalar has depth 0,
  an object or array 1 more than its deepest member (an empty one 1). Both
  readers refuse a text whose value would be deeper than 256, at the first
  character of the first collection at depth 257, with the reason
  `collections nest deeper than 256 levels`: a `JsonSyntaxError` or a
  `YamlSyntaxError` whose offset (UTF-16 code units from 0), line and
  column are pinned, the same places Python names. The JSON reader counts
  the collections it opens and refuses before its recursion could go
  deeper; the YAML reader's walk knows each node's depth from its stack and
  refuses the first collection at depth 257 in document order, also where
  the parser stopped composing for want of stack, a problem that never
  outranks the walk, so a text nested 100,000 deep is refused where one
  nested 257 deep is. Pinned
  (offset, line, column): JSON `[` 257 times then `]` 257 times, and `[`
  100,000 times unclosed, at (256, 1, 257); `{"a":` 257 times, then `1`
  and `}` 257 times, at (1280, 1, 1281); YAML `- ` 257 times then `1`, and
  `- ` 100,000 times then `1`, at (512, 1, 513); 257 block sequences in
  canonical layout (`-` alone on a line, each two columns further, the
  last `- 1`) at (66304, 257, 513); 257 block mappings (`k:` on a line,
  each two columns further, the last `k: 1`) at (66560, 257, 513); `a: `
  then `[` 256 times and `]` 256 times at (258, 1, 259); `# x`, a line
  feed, then `{a: ` 257 times, `1` and `}` 257 times at (1028, 2, 1025);
  the shared refusals `json_depth_257.json` at (256, 1, 257) and
  `yaml_depth_257.yaml` at (16640, 128, 385). Every text nested 257 deep,
  made one level shallower, is read, to a value nested 256 deep. The writers throw the `RangeError` `a value nested
  deeper than 256 levels cannot be written` in every serialization for the
  array nested 257 deep (built in memory: no text a reader reads holds
  it), an object whose member holds an array 256 deep, the array nested
  257 deep around a NaN (the depth is checked first) and an array holding
  itself; the array nested 256 deep is written in every serialization and
  reads back equal, its canonical YAML `readings/json_depth_256.expected.yaml`
  and its RFC 8785 JSON `[` 256 times then `]` 256 times.
- **The first fault** (`serialization.test.ts`): a text holding several
  faults is refused for the first in document order, at the token that
  offends, the same place Python names, so a pinned place proves the
  order. The YAML walk stops at its first fault, and a problem of the
  parser (errors and warnings alike, the one with the smallest offset)
  is refused instead where it lies before that fault; at the same offset
  the walk's fault stands. A parser reads one token ahead, so a syntax
  error it meets there may be refused before a fault of the token just
  before it: `- &a "\q"` is refused by Python at the bad escape (1, 8)
  and here at the anchor (1, 3), so its test asserts only the
  `YamlSyntaxError`, and no shared refusal pins such a pair. Pinned as
  (error, line, column): in YAML, a repeated key at (2, 1), `!foo`,
  `!!map [1]` and the escape `\ud800` at (1, 4) and the key `1` at (1, 1),
  each before a flow sequence at depth 257, and that depth at (1, 259)
  before a repeated key or `!foo`; `!foo` before a repeated key at (1, 4)
  and a repeated key before `!foo` at (2, 1); a repeated key before a
  second document, and a second document before a repeated key in it, at
  (2, 1); an anchor and a tag at the node's first property and named by
  it, with message and offset: `a: &x !local 1` as `an anchor`, `a:
  !local &x 1` and `a: !!str &x 1` as `a tag`, all at (3, 1, 4); `.inf: 1` as a key that is not a string at (1, 1); `!!binary
  aGk=: 1` for the tag at (1, 1); a character outside YAML's printable
  set, which `yaml` reads, looked for before the text is parsed and
  refused where it stands with Python's message (`special characters are
  not allowed #x0001`), whatever fault comes before it: U+0001 ending a
  key that would repeat `a` at (1, 12), ending `1e99999` at (1, 15),
  before a repeated key at (1, 5), after a repeated key at (3, 5), after
  `!foo` at (2, 4). In JSON, `[1e999, }` and `[1e999] 2` as a `RangeError` at column
  2, `["\ud800", }` at 3, a repeated key before a missing key or extra
  data at 8, `1e999` as the value of a key that repeats later as a
  `RangeError` at 6, a lone surrogate before 300 unclosed `[` at 3, a
  collection at depth 257 before a repeated key at 257, and U+0001 in a
  string before `1e999` at 3. A JSON string is refused at the token that
  offends: an invalid escape (`\x` at 5, `\u12G4` at 3) at its
  backslash, a control character where it stands, an unterminated string
  at the end of the text; a high-surrogate escape not followed by a
  low-surrogate escape (an invalid escape, the end, a control character,
  an escaped quote or a low surrogate standing as itself follows) is lone
  at its own escape, column 3. Every shared refusal whose place the
  cases' README gives is refused there (`SHARED_PLACES`): the two depth texts; the six `json_lone_surrogate_*` texts, one of them
  (`json_lone_surrogate_before_syntax_error`) also among the fifteen
  `*_before_*` texts; `yaml_anchor` and `yaml_alias` at the `&`; the nine
  `yaml_tag_*` texts at the tag (`yaml_tag_before_anchor` also among the
  `*_before_*` texts); `yaml_special_character_in_key` at the character;
  and `yaml_key_empty_trailing_space` (`?`, a space, a line feed, `: 1`)
  right after the `?` at (1, 2), where `yaml` places the empty key after
  the space.
- **Columns count code points** (`serialization.test.ts`): `line` and
  `column` of a `JsonSyntaxError` and a `YamlSyntaxError`, and the line
  and column the message of a JSON `RangeError` names, count from 1, the
  column in code points, so a character above U+FFFF counts once, while
  `offset` stays a UTF-16 index from 0:
  the YAML anchor in `"😀": &x 1` at (6, 1, 6) and the escape `\ud800` in
  the JSON text `["😀", "\ud800"]` at (8, 1, 8), as Python names them (in
  UTF-16 code units the columns would be 7 and 9); `1e999` after `"😀"`
  in `["😀", 1e999]` as a `RangeError` at line 1, column 7; and the shared
  refusals `json_astral_before_duplicate_key` and
  `yaml_astral_before_infinity` at column 10 (11 in UTF-16 code units).
- **The choice** between JSON and YAML: leading white space, a JSON
  scalar, a quoted YAML scalar, a YAML escape, `-Infinity`, `{a: 1}`
  refused as JSON, `"a": 1` read as YAML, a JSON string holding U+2028; and
  `serializationOf` returning a name, never throwing, for unreadable texts
  (a lone surrogate, 100000 `[`, an unclosed object, `1e309`), `"jcs"` only
  for exact RFC 8785 bytes without a byte order mark.
- **Respelling** (`manifest.test.ts`): one manifest whose values lie on
  every kind of axis: an integral float on an `int` axis (`-0.0` as 0,
  `1.0e+20` as its 21 digits), integers on a `float` axis (2^53 + 1 kept,
  2^53 and `-0` as floats), Fractions reduced (`[6.0, 4]`, `[0, 5]`,
  `[2, 4]` on a child's offset) and `[3, -2]` kept, a bare number on a
  `fraction` axis kept, a child respelled by its own axis under an unknown
  unit while its offset stays, a missing unit, an unknown `number_type`
  and `number_type: null`; named timestamps on one timeline, on none and on
  two of equal ID; an integral plain number written as the integer of its
  exact value (`1e300` its 301 digits, which RFC 8785 refuses, `-0` as 0);
  an integer no double can hold (10^400) as a `length` and a region `end`
  on a `seconds` axis written as given in canonical YAML and pretty JSON,
  each text reading back to itself, and refused in RFC 8785 JSON.
- **Canonical order**: keys by code point in YAML and JSON and by UTF-16
  code unit in RFC 8785; roots, groups, members, measure maps,
  conversion maps, children, regions, flow control and named timestamps
  with the expected ID sequences, ties broken by ID and entries tying on
  every member kept in their order, values compared by exact value; a
  `display` holding anything ordered; a member holding no array written
  as given; display orders, rules and the values of a pair kept; a `TypeError` for
  an entry that is not an object, lacks a member or holds a wrong type,
  even alone in its array, and for a group member that is not a string.
- **Refusals of the writers**: a lone surrogate in a string or key, NaN and
  an infinity, keys over 1024 UTF-16 code units of their canonical YAML
  form (plain, quoted, above U+FFFF, nested) as a `RangeError` in every
  serialization, keys of exactly 1024 written; ±2^53, 2^64, the integral
  floats 2^53, −10^16 and 10^21 − 2^17 refused in `"jcs"` only, ±(2^53 − 1)
  and 10^21 written; `undefined`, a function, a symbol, a `Date` and a
  `Map` as a `TypeError`; an unknown serialization (`"toml"`, `"YAML"`,
  `""`) as the `RangeError` `unknown serialization "<name>"`.
- **Every stored file** (fixtures, rejection and warning cases) is written
  as stored, and its value with every key and every array the canonical
  order sorts reversed is written to the same text, or refused alike, in
  each serialization.
- **Python's `repr`.** 2000 doubles from a fixed pseudo-random sequence are
  spelled as Python spells them with `repr`, with `.0` added to a mantissa
  in exponent form that has no fractional digit. The expected spellings
  are stored in `python-repr.ts`, produced once by CPython from the same
  doubles (its comment states how), so the suite runs no other
  interpreter.

## IDs in a file

`ids.test.ts` proves `toFileId`, `fromFileId`, `withFileIds` and
`withBareIds` with the cases, values and messages of the Python suite's
"IDs in a file"; `FileIdError` is a `RangeError` here where Python's is a
`ValueError`. The manifest is the same, written as YAML text and read by
`loads`, so its numbers are the lossless form: `2.0` comes back as
`JsonFloat(2)`. Values are compared by `compactJson`, which keeps each
object's own key order, and one case more pins an order key that reads as an
array index (`#2` becomes `2` and stays after `b`), the order JavaScript
would otherwise change. The tables equal the schema's ID positions as in
the Python suite, and every fixture round-trips. The validators read the
file form as the Python suite's "IDs in a file" states, with its one
refusal the schema cannot type (a bare member ID in a group's order), and a
bare ID of any length refused by the `#` rule (Python's message `'s' does
not match '^#[\\s\\S]'`). The IRIs of statements are no IDs: `#verse` in a
region's statements stays `#verse` in both forms, `statementProblems` reads
an ID outside the statements as it stands, and an element named by a
statement resolves against the bare IDs. The inline documents write IDs
bare and reach the checks through the file-form helpers of
`tests/fixtures.ts` (`validate`, `unknownKeys`, `manifestWarnings`,
`identityProblems`, `statementProblems`), while the shared cases and the
fixtures, which are files, reach the package's functions as they are.

## Manifest files

`fileForm(text)` gives a `FileForm`, `{ minimal, styling, serialization }`,
and `dumpsFile(value, form)` writes a value back in it, as Python's
`file_form` and `dumps_file` do (`src/files.ts`). The form is minimal when
`minimal(value)` and `value` write the same canonical YAML, the equality
of the fixtures' twin law: a key stated at its default, recognized by
exact value, makes a text not minimal, and the order canonical order sorts
does not count. What proves them (`files.test.ts`):

- **Every fixture comes back byte for byte.** For every fixture and every
  minimal twin (206 files: bundles, the flow fixtures, groups and statements included), its value and its value
  without `graphical` are each written in all three serializations; every
  such text reads as `{ minimal: <is a twin>, styling: <holds graphical>,
  serialization: <the one it was written in> }`, and
  `dumpsFile(loads(text), fileForm(text))` gives the text byte for byte.
- **The cases of `fixtures/file_forms/`**, shared with Python and stated in
  its test README: each text not named `*.expected.*` reads to the form
  the test's table states (the table naming exactly the directory's
  texts) and is written back as the bytes of its `.expected` file:
  `neither.yaml` (neither minimal nor complete) as `minimal: false` and
  the complete form, `one_line.json` in the pretty JSON layout,
  `crlf.yaml` with line feeds alone, `jcs_minimal.json` (RFC 8785 JSON
  on a float axis, its integral floats written as integers) as
  `minimal: true` and its own bytes, `jcs_float_default.json` (the same
  with a LinearMap's default `offset` 0.0 stated as `0`) as
  `minimal: false` and the complete form. `jcs_minimal.json` written in
  canonical YAML gives the floats its declared number type selects, the
  same text Python's test pins after the `@context` block of `bare`'s
  twin.
- **The serialization names.** `SERIALIZATIONS` is `["yaml", "json",
  "jcs"]`; `isSerialization` is true for those three and false for
  `"YAML"`, `"toml"`, `""`, `null`, `undefined` and `1`.
- **The key-sorted compact writer.** `compactSortedJson` writes
  `{ b: 1, z: { y: 1, x: 2 }, "😀": null, "｡": true, a: [JsonFloat(2),
  0.5, 2n ** 60n, JsonFloat(1e21)] }` as
  `{"a":[2.0,0.5,1152921504606846976,1.0e+21],"b":1,"z":{"x":2,"y":1},"｡":true,"😀":null}`:
  keys by code point at every depth (U+FF61 before U+1F600, which UTF-16
  code units order the other way), no whitespace, a float spelled apart
  from an integer, an integer beyond 2^53 written; a manifest's arrays
  keep their order. `compactJson` writes the same value with its keys in
  their own order.

## Lossless reading in JavaScript

`loads` reads any text into the smallest representation that loses
nothing: a safe integer and a float with a fractional part are plain
numbers, an integer beyond `Number.MAX_SAFE_INTEGER` a `bigint`, an
integral float (`2.0`, `1e+16`, `-0.0`) a frozen `JsonFloat`; `-0` is the
integer 0, as in Python; objects keep the written order of their keys,
array-index keys included, which `compactJson` honours. `compactJson` is a
fixpoint for every value nested in every fixture and spells numbers as the
writers do (`2.0`, `1.0e-07`, `1.0e+16`, `-0.0`, and `-0` as `0`).
`JsonFloat` is told apart by `instanceof` or `isJsonFloat`, and
`isJsonObject` is false for it.

Every object these readers and the ID conversions build comes from one
helper, and three cases pin what it keeps, whatever way it sets keys: a
key `__proto__` read from JSON and from YAML is an own enumerable key
holding its value, the object's prototype still `Object.prototype`, and
it is written back in its place (`{"a":1,"__proto__":{"b":2},"c":3}`); a
key given twice keeps its first position and its last value; and
array-index keys given twice among other keys keep the order in which each
was first given, which `compactJson` writes.

`JSON.parse("9007199254740993")` gives `9007199254740992`, while `parseJson`
reads `9007199254740993n`; lengths of `9007199254740993n` and
`9223372036854775807n` on a ticks axis validate and are written and read
back as the same integer.

## Completing missing styles

`completeStyles` returns a new `graphical` object and never changes its
input; every distinct style name a rule names but `styles` lacks is
added as an empty declaration, `missing` lists them in code-point order (`ﬀ` before
`😀`), and with missing names it calls `console.warn` exactly once with the
text of Python's `MissingStyleWarning`, with none never. The copy keeps
every number as `loads` read it: a style's `stroke-width: 2.0` stays a
`JsonFloat` of value 2, `missing` is `["b"]`, the completed manifest
validates and `dumps` writes `stroke-width: 2.0`.

## The fonts

A drawing's text is drawn in DejaVu Sans 2.37 and every code point DejaVu
Sans does not map and Noto Music 2.004 does in Noto Music, and measured from
one table. The JavaScript tests cannot
read a TrueType file's tables (the Python tests prove the table against both
fonts with fontTools); they prove that the package ships the same files and
the same table:

- `FONT_FILES` is `["DejaVuSans.ttf", "NotoMusic-Regular.ttf"]`; each file
  under `fonts/` has the SHA-256 of its upstream release file
  (`7da195a7…48954`, `26c0a28d…0de816`), and its licence lies beside it,
  `DejaVuSans-LICENSE` (8816 bytes) and `NotoMusic-LICENSE` (4381 bytes);
  `package.json` exports `./fonts/*` and lists `fonts` in `files`.
- `fontMetrics` has exactly `advances`, `ascender`, `descender`, `fallback`
  and `units_per_em` with the values 1901, 483, 1229 and 2048 and 6467
  advances, DejaVu Sans's 5918 and 549 from Noto Music (`"9833"` 966,
  `"48"` 1303, `"32"` 651; `"119133"`, U+1D15D, 1053; `"119070"`, U+1D11E,
  1456; `"119135"`, U+1D15F, 819; `"118784"`, U+1D000, 973; `"119296"`,
  U+1D200, 1810).
- `dumps(fontMetrics, { serialization: "json" })` reproduces the metrics file
  `fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json`.

## Packaging

After `scripts/copy-assets.ts`, the package directory's `docs/` holds
exactly the two specifications `docs/description.md` and `docs/drawing.md`
(the rest of the repository's `docs/` is the documentation site's source
and build, which a package must not carry: the copy step leaves it out, and
`files` alone would not catch a copy step that brought it along), and
`npm pack --dry-run --json` lists exactly these two under `docs/` (so
`docs/conf.py` shipped fails),
exactly the three schema documents
`schema/0.2.0/provenance.schema.json`, `schema/0.2.0/tables.json` and
`schema/0.2.0/timetoshare.schema.json`,
`catalogue/catalogue.yaml` and `catalogue/catalogue.schema.json` (and
`package.json` exports `./catalogue/*`),
`LICENSE` and
exactly the five files of `fonts/` (both TrueType files, `DejaVuSans-LICENSE`,
`NotoMusic-LICENSE` and the metrics table
`dejavu-sans-2.37+noto-music-2.004.metrics.json`; the SIL Open Font License
requires its licence to travel with the font), each copy byte for byte the
repository's file, and `package.json` exports `./docs/*`. The packed
package is `@timetoalign/timetoshare` at the version `SCHEMA_VERSION` names,
as a package version is the schema version it reads. The test runs `npm`
through the platform's shell, one fixed command line, because on Windows
`npm` is the script `npm.cmd`, which Node starts only through a shell; so
the six tests run on every platform, Windows included, and none is
skipped.

## Hermeticity

Tests read the repository fixtures and the schema through shared helpers
(`fixtures.ts`). They use no network or shared mutable input. The packaging
test refreshes the package directory's ignored copies of the repository
assets, as `pnpm build` does, and runs `npm pack` without writing a tarball.
