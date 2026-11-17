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
   raises the first violation at the same path; `parse` is `parseJson`
   followed by `validate`. A checked value is typed as the lossless form:
   one test assigns it to `LosslessManifest` and, by a
   `@ts-expect-error` line, not to `Manifest`, and reads its lengths
   back as `9007199254740993n` and `JsonFloat(2)`.
2. `unknownKeys` and `unregisteredTerms` return, for every manifest, the
   lists Python's `unknown_keys` and `unregistered_terms` return, byte for
   byte once written by `dumps`.
3. `complete` and `minimal` give the values Python's functions give, from a
   `DEFAULTS` table equal to the schema's `default`s, as Python's is; their
   typed forms take and give the generated `LosslessManifest` and
   `CompleteManifest`.
4. `dumps` writes every value as the same bytes as Python's `dumps`.
5. The generated files are the generator's output, and the npm package
   ships the schema document, the drawing specification, the registry of
   identifier schemes and the licence.
6. The description functions (`linkFromUrls`, `withUri`, …) build the same
   links as Python's description model, through the same registry, and
   throw an `Error` with Python's message wherever Python raises
   `ValueError`.

## The fixtures

`fixtures.test.ts`: every manifest fixture (every `*.json` below
`fixtures/0.2.0/` except the drawings), read by `parseJson`, validates, has
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
`Address` accepting and refusing the Python suite's values; no node
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
exports the registry file's entries as `schemes`; the committed
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

`number-members.test.ts` derives every scalar and array member of a
conversion map that can hold a Number (by reference or as a branch of an
`anyOf`), and every scalar, array and
keyed-object member that holds a nested conversion map, from the schema's
conversion-map definitions. It asserts exact equality with the respelling's
two traversal tables, naming every missing or extra entry on failure, so a
schema addition cannot escape the canonical spelling.

- **Messages.** Every message but a schema violation's is the same text in
  both packages: an ID, a unit or an order entry in single quotes, as
  written (`'m' is not unique in the manifest, first at …`), a value as the
  standard writer spells it (`unsupported TimeToShare version "9.9.9"; this
  package reads 0.2.0 only`). A schema violation carries Ajv's message
  (`must match pattern …`, `must NOT have duplicate items …`).
- **Integral floats.** `parseJson` keeps `2.0` as a `JsonFloat`, so
  `length 2.0` on a fraction axis is "a float … write [2, 1]" as in Python;
  a number built in code as `2` is an int. A `JsonFloat` member of a
  Fraction pair is the integer it equals, as Python reads `8.0`; the Python
  README's manifest of respellable values, read by `parseJson`, validates,
  and `complete`, `minimal` and `canonicalOrder` give, compared as
  `compactJson` texts, what they give for its canonical twin, a `JsonFloat`
  member becoming a plain integer, a `JsonFloat` on an int axis a plain
  integer, an integer on a float axis a `JsonFloat`; `dumps` writes the
  twin's text. Rewritten floats are spelled as Python spells them (`write
  2.0`, `write 0.75`, `ends at 1.0`).
- **Integers beyond 2^53.** `parseJson` reads `9007199254740993` as a
  `bigint`, so on a float axis it is "an int … write a float";
  `9007199254740992n` and `10n ** 20n` are exactly floats and validate.
- **Non-finite numbers.** `parseJson` refuses them and a `JsonFloat` cannot
  hold one, so only a number built in code reaches the finite rule; the
  tests build infinity, NaN and negative infinity as Python's do.

## Shared rejection cases

Each of the 125 cases (`validate.test.ts`), read by `parseJson`, is written
as the standard writer writes it and raises `SchemaValidationError` with its
stored path and code through `validate` on the parsed value, through
`validate` on the value as `JSON.parse` reads it, and through `parse` of its
compact text; `version_unknown` raises `UnsupportedVersionError`. Each case
is read through one reader, the mirror of Python's `rejection_case`, which
puts the infinity or NaN a `finite_number` case names at its path; such a
case has one reading, the reader's value, since JSON text cannot carry it,
and a test pins the two values in place. One `JSON.parse` reading is exempt:
`float_axis_int_not_exact`, since `9007199254740993` becomes
`9007199254740992`, exactly a float; the test asserts that this lossy
reading validates. The set of names and the eighteen codes are stated
literally, and the fifteen cases whose messages the Python suite pins carry
the same messages here (`identity.test.ts`, `description.test.ts`).

The path rule is the Python README's ("One path rule for both validators");
Ajv applies a discriminated `oneOf` to the candidate its tag selects through
its `discriminator` option. The shared cases pin the paths.

## Unknown keys

`unknown-keys.test.ts`: every shared warning case validates, holds exactly
`manifest`, `unknown_keys` and `unregistered_terms`, its text is the
standard writer's, `dumps(unknownKeys(manifest))` equals
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
is the default only in type and value: `repeat_count: new JsonFloat(1)` (read
from `1.0`) is not the default `1` and stays in the minimal form; the round
trips compare `dumps` texts, which tell `1.0` from `1`. No result shares
an object with `DEFAULTS`. The typed forms' oracle is the fixtures: each
minimal twin (70, one per fixture) completes to its fixture's text, keeps it in canonical order,
and strips back to its own; a literal `CompleteManifest` compiles, and
keys whose default is absent (`id`, `graphical`, a root's `offset`) stay
optional.

## The description layer

`registry.test.ts` and `description.test.ts` assert the Python README's
sections "The description layer", "Links" and "Unregistered terms" with the
same documents, the same values and the same messages: the eight shipped
entries in order, the recognition table and the URL forms, the one rule per
scheme, `withSchemes` and its refusals, the work bundle of Op. 106 in both
forms (built with `linkFromUrls`, `partSlotFromUrl` and `withParts`, read
back through `parse` to the same complete link), the two readings, every
error, normalisation, copy-on-write and `assertionFor`. The packages differ
only where JavaScript must:

- **Plain objects.** A link is a plain object of the generated types, not a
  class: every function takes a link in either form and returns a new link
  in the complete form (`CompleteLink`), built through the defaults table
  as `complete` builds a manifest's; `minimal` of a manifest holding it
  gives the minimal form. Unknown keys are kept because nothing is rebuilt,
  so the Python README's unknown keys are proved on what `withLabel` and
  `withParts` return. An assertion's date is the string `2026-11-17`.
- **Patterns.** A registry pattern is compiled as `^(?:pattern)$` with the
  `u` flag, which matches what Python's `re.fullmatch` matches for every
  URL the registry reads (the URL holds no white space or control
  character, the one place the two engines read `.` and `$` differently).
  Percent-decoding mirrors Python's `unquote` with strict UTF-8: a `%`
  followed by two hexadecimal digits is a byte, any other `%` is kept, and
  a byte sequence that is not UTF-8 refuses the URL; a leading byte-order
  mark is kept, as Python keeps it.

## The canonical order and the standard writer

`manifest.test.ts` asserts the Python README's sections "The canonical
order" and "The standard writer" with the same documents and expected id
sequences, including own-axis values as bare ints, floats, `JsonFloat`s and
pairs mixed, and adds:

- **Both writers, from any order.** Every fixture, rejection and warning
  case, with the keys of every object reversed and, in the fixtures, the
  items of every array the canonical order sorts (`timelines`, `groups`,
  `members`, `measure_maps`, `children`, `conversion_maps`, `regions`,
  `flow_control`, `graphical.timestamps` and every timestamp's `display`), is written by this `dumps` and by Python's `dumps`
  (loaded by `python3` from its path) to the same bytes, equal to the file.
- **Python's `repr` itself.** 2000 doubles from a fixed pseudo-random
  sequence are spelled exactly as `python3` spells them with `repr`.
- **The shared number corpus** gives the one literal expected text.
- **Refusals.** NaN, infinity and lone surrogates are refused as a
  `RangeError`, `undefined` as a `TypeError`, a collection that cannot be
  ordered as a `TypeError`.

## Lossless reading in JavaScript

`parseJson` reads any JSON text into the smallest representation that loses
nothing: a safe integer and a float with a fractional part are plain numbers,
an integer beyond `Number.MAX_SAFE_INTEGER` a `bigint`, an integral float
(`2.0`, `1e+16`, `-0.0`) a frozen `JsonFloat`; `-0` is the integer 0, as in
Python; objects keep the written order of their keys, array-index keys
included, which `compactJson` honours. The tests pin each case (`0.5`,
`2.0`, `123456789012345678`, `-0`, `-0.0`, `1E5`), key order surviving a
round trip, and `1e400` refused as a `RangeError`. Malformed text is refused
as a `JsonSyntaxError`, a `SyntaxError`, whose offset, line and column name
where the text breaks; eleven texts, each breaking in a different way and
place (an empty text, a stray comma, an unterminated string, a missing
comma on line 3), pin the message and the three numbers. `compactJson` is a
fixpoint for every value nested in every fixture and equals Python's
`json.dumps(value, separators=(",", ":"), ensure_ascii=False)` for every
fixture, rejection and warning case. `JsonFloat` is told apart by
`instanceof` or `isJsonFloat`, and `isJsonObject` is false for it.

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
- `dumps(fontMetrics)` reproduces the metrics file
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
