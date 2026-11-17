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
2. `unknownKeys` and `unregisteredTerms` return, for every manifest, the
   lists Python's `unknown_keys` and `unregistered_terms` return, byte for
   byte once written by `dumps`; `descriptionProblems` returns the problems
   Python's `description_problems` returns, with the same codes and paths
   and, but for a schema violation's, the same messages.
3. `complete` and `minimal` give the values Python's functions give, from a
   `DEFAULTS` table equal to the schema's `default`s, as Python's is; their
   typed forms take and give the generated `LosslessManifest` and
   `CompleteManifest`.
4. `dumps` writes every value in canonical YAML, pretty JSON and RFC 8785
   JSON as the README's "Serializations" specifies, the bytes of the shared
   hand-derived cases, which Python's `dumps` writes too; `loads` reads every
   serialization as "Reading" states.
5. The generated files are the generator's output, and the npm package
   ships the schema document, the drawing specification, the registry of
   identifier schemes and the licence.
6. The description functions (`linkFromUrls`, `withUri`, …) build the same
   links as Python's description model, through the same registry, and
   throw an `Error` with Python's message wherever Python raises
   `ValueError`.

## The fixtures

`fixtures.test.ts`: every manifest fixture (every `*.json` below
`fixtures/0.2.0/` except the drawings, found by its name in either
`.yaml` or `.json`), read by `loads`, validates, has
no unknown keys, and satisfies both round trips of `complete` and `minimal`,
as in the Python suite's "The fixture set".

## The schema document and the generated files

`schema.test.ts` checks invariants, not the tree's private shape, so a
refactor that keeps the accepted language stays green: the bundled `schema`
is the file; references are local and resolve; the public definitions exist and the root's description names exactly them; `ConversionMap` chooses between exactly the ten
map types, `Selector.class` names the six timeline classes and the ten types,
`Facet`, `Part`, `ElementType` and the words of a `Timestamp`'s `display` (`TIMESTAMP_DISPLAY`) are exactly the Python suite's lists, and
each measure view fixes its target unit over
`MeasureView`, which fixes the source unit; the unit
table's consts are exactly the keys of
`UNIT_NUMBER_TYPES` in order, each description naming that unit's default
number type, as in the Python suite; `Name`, `Meta` and `MapBase` are the
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
the description layer's invariants of the Python README ("The schema
document", "The description layer": `links` on exactly `Manifest`,
`Timeline` and `Region`, `schemes` on `Manifest`, the closed vocabularies
equal to `LEVELS`, `MATCHES` and `STATUSES`, no `position` on a slot and no
`name` on a link, the values `Uri`, `Term` and `UriReference` accept and
refuse, the white-space class pinned against the registry's). `generated.test.ts`: a fresh generator run exports the committed
names, which are every definition, the complete form of exactly the
definitions holding a default, and `LosslessManifest`, and `registry.ts`
exports the registry file's entries as `schemes` (equal, as `compactJson`
texts, to the value `loads` reads from the file, which holds byte for
byte the pretty JSON `dumps` writes for that value); the committed
text is `check:drift`'s oracle. Statements marked `@ts-expect-error` (a
misspelt key, a missing `length` or child `offset`, a complete form missing
a defaulted key, a three-member Fraction) make a looser generation break
the typecheck gate. A complete flow-control element without `repeat_count`
compiles: the schema states the repeat count's default in the `then` arm
for a `repeat_end`, not on the shared property, and the generator removes
the arms, so the complete form keeps it optional. A complete
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

- **Messages.** Every message but a schema violation's is the same text in
  both packages: an ID, a unit or an order entry in single quotes, as
  written (`'m' is not unique in the manifest, first at …`), a value as the
  writers spell it (`unsupported TimeToShare version "9.9.9"; this
  package reads 0.2.0 only`). A schema violation carries Ajv's message
  (`must match pattern …`, `must NOT have duplicate items …`).
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
- **Non-finite numbers.** The readers refuse them and a `JsonFloat` cannot
  hold one, so only a number built in code reaches the finite rule; the
  tests build infinity, NaN and negative infinity as Python's do.

## Shared rejection cases

Each of the 129 cases (`validate.test.ts`), found by its name whatever
its extension and read by `loads`, is stored as the writers write it,
byte for byte (a canonical YAML text is `dumps`'s bytes, a JSON text the
bytes of `dumps` in pretty JSON) and raises
`SchemaValidationError` with its stored path and code through `validate`
on the read value, through `validate` on the value as `JSON.parse` would
read it (`plain`: every `JsonFloat` and `bigint` a plain number), and
through `parse` of its compact text; `version_unknown` raises
`UnsupportedVersionError`. Each case is read through one reader, the mirror
of Python's `rejection_case`, which puts the infinity or NaN a
`finite_number` case names at its path; such a case has one reading, the
reader's value, since no text carries it, and a test pins the two values in
place. One plain reading is exempt: `float_axis_int_not_exact`, since
`9007199254740993` becomes `9007199254740992`, exactly a float; the test
asserts that this lossy reading validates. The set of names and the nineteen codes are stated
literally, and the sixteen cases whose messages the Python suite pins carry
the same messages here (`identity.test.ts`, `description.test.ts`).

The path rule is the Python README's ("One path rule for both validators");
Ajv applies a discriminated `oneOf` to the candidate its tag selects through
its `discriminator` option. The shared cases pin the paths.

## Unknown keys

`unknown-keys.test.ts`: every shared warning case validates, holds exactly
`manifest`, `unknown_keys` and `unregistered_terms`, its text is stored
as the writers write it, `dumps(unknownKeys(manifest))` equals
`dumps(case.unknown_keys)` and `dumps(unregisteredTerms(manifest))` equals
`dumps(case.unregistered_terms)`; the cases of terms, and the other
documents of the Python README's "Unregistered terms", are asserted in
`description.test.ts`; `several_depths` lists its sixteen entries in the
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
`several_depths` proves it). The keys belong to one run, so a refused
manifest's keys never appear in the next run's list (`validate.test.ts`).

## Defaults

`defaults.test.ts` asserts the Python README's section "Defaults: the
complete and the minimal form" with the same documents and values. A value
equals its default in value: `repeat_count: new JsonFloat(1)` (read from
`1.0`), a `LinearMap`'s `scalar: [1, 1]` and `offset: new JsonFloat(-0)` are
left out as the defaults `1` and `0` are, and the complete form of what
remains states the defaults; the round trips compare `dumps` texts, which
tell `1.0` from `1`. No result shares
an object with `DEFAULTS`. The typed forms' oracle is the fixtures: each
minimal twin (72, one per fixture) completes to the canonical YAML of its
fixture, keeps it in canonical order,
and strips back to its own; a literal `CompleteManifest` compiles, and
keys whose default is absent (`id`, `graphical`, a root's `offset`) stay
optional.

## The description layer

`registry.test.ts` and `description.test.ts` assert the Python README's
sections "The description layer", "Links", "The description layer alone"
and "Unregistered terms" with the same documents, the same values and the
same messages: the eight shipped entries in order with their `lowercase`,
the recognition table (the MusicBrainz ID in capitals among it) and the URL
forms (every IMSLP page that is no work page refused, plainly and with
`%3A`, and the two work pages beginning with such a word recognised), the
one rule per scheme, `withSchemes`, its reading of an entry without
`level`, `entity_uri` and `lowercase` as null, null and false (the entry
Python reads alike) and its refusals, a `lowercase` that is no boolean
among them, the work bundle of Op. 106 in both forms (built with
`linkFromUrls`, `partSlotFromUrl` and `withParts`, read back through
`parse` to the same complete link), the two readings, every error, the two
rules of a link without parts among them, normalisation, each fact stored
once (`linkFromUrls` and `withIdentifier`, whose `registry` option is
Python's keyword), copy-on-write and `assertionFor`; and
`descriptionProblems` with the shared cases (each `description_*` case its
one problem, every other case and every fixture none), the manifest whose
other parts break every kind of rule, and the manifest whose five arrays
each break once. The packages differ only where JavaScript must:

- **Plain objects.** A link is a plain object of the generated types, not a
  class: every function takes a link in either form and returns a new link
  in the complete form (`CompleteLink`), built through the defaults table
  as `complete` builds a manifest's; `minimal` of a manifest holding it
  gives the minimal form. Unknown keys are kept because nothing is rebuilt,
  so the Python README's unknown keys are proved on what `withLabel` and
  `withParts` return. An assertion's date is the string `2026-11-17`.
- **Schema messages.** `descriptionProblems` reports a schema violation
  with Ajv's message, as `validate` does; its code and path are Python's.
- **Dates.** Python refuses a date the calendar lacks, or one not written
  `YYYY-MM-DD`, when it reads or constructs an assertion; a JavaScript
  assertion stays a plain object, so every function that takes or returns one refuses such a
  date with Python's message (`'2026-02-30' is no Gregorian calendar date
  written YYYY-MM-DD`): `linkFromUrls` and `partSlotFromUrl` given it in
  their `assertion`, `withAssertion`, `withParts` given it in a slot's,
  `withPartOf` given it in the entry's, `withLabel` given a link holding
  it, and `assertionFor` reading it; `17 November 2026`, `20261117`,
  `2100-02-29` and `0000-01-01` are refused alike, `2024-02-29` kept as
  written. The validator's `calendar_date` gives the Python README's
  verdicts and messages.
- **Patterns.** A registry pattern is compiled as `^(?:pattern)$` with the
  `u` flag, which matches what Python's `re.fullmatch` matches for every
  URL the registry reads (the URL holds no white space or control
  character, the one place the two engines read `.` and `$` differently).
  Percent-decoding mirrors Python's `unquote` with strict UTF-8: a `%`
  followed by two hexadecimal digits is a byte, any other `%` is kept, and
  a byte sequence that is not UTF-8 refuses the URL; a leading byte-order
  mark is kept, as Python keeps it.

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
- **Refusals.** The table names each of the 67 files with the error it
  throws: a text read as YAML a `YamlSyntaxError`, through `loads` and
  `parseYaml`; a text read as JSON a `JsonSyntaxError`, through `loads`
  and `parseJson` (the three `flow_*` texts meant as YAML among them), a
  `RangeError` for the four whose float rounds to an infinity
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
  `True`, `'12'`, `!!str 1`), key order, an empty or comment-only text as
  null, and seventeen refusals with their message, offset, line and column:
  an anchor, an alias, a repeated key, a collection and an integer as keys,
  a lone surrogate escaped and as itself, `.inf`, `-.Inf`, `.nan`, `1e309`,
  `!!binary`, `!!timestamp`, `!!set`, `!!omap`, an unknown tag and a second
  document.
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
  as given; display orders, statements and links kept; a `TypeError` for
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

`JSON.parse("9007199254740993")` gives `9007199254740992`, while `parseJson`
reads `9007199254740993n`; lengths of `9007199254740993n` and
`9223372036854775807n` on a ticks axis validate and are written and read
back as the same integer.

## Completing missing styles

`completeStyles` returns a new `graphical` object and never changes its
input; every distinct style name a statement names but `styles` lacks is
added as an empty declaration, `missing` lists them in code-point order (`ﬀ` before
`😀`), and with missing names it calls `console.warn` exactly once with the
text of Python's `MissingStyleWarning`, with none never.

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

After `scripts/copy-assets.ts`, `npm pack --dry-run --json` lists
`docs/drawing.md`, `schema/0.2.0/timetoshare.schema.json`,
`registry/schemes.json` (and `package.json` exports `./registry/*`),
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
