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
   serialization as "Reading" states. `fileForm` infers how a manifest
   file writes its manifest and `dumpsFile` writes a value back in that
   form, the same bytes as Python's `file_form` and `dumps_file`.
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
  `10n ** 400n` has no double (`Number` gives infinity), so containment
  and segment lines add it exactly, as Python adds an integer that
  `float` cannot convert, and both spell the end alike.
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

## The units

`validate.test.ts` proves the Python README's section "The units" with
the same roots: `css_pixels` and `user_units` validate with every number
type exactly where `points` does, and `px` and `uu` are refused with the
code `schema` at `["timelines", 0, "unit"]`. `defaults.ts` completes a
timeline's `number_type` for exactly the keys of `UNIT_NUMBER_TYPES`, its
one list of units, so the default number type of both new units is
`float` in `defaults.test.ts` as in the Python suite.

## Defaults

`defaults.test.ts` asserts the Python README's section "Defaults: the
complete and the minimal form" with the same documents and values. A value
equals its default in value: `repeat_count: new JsonFloat(1)` (read from
`1.0`), a `LinearMap`'s `scalar: [1, 1]` and `offset: new JsonFloat(-0)` are
left out as the defaults `1` and `0` are, and the complete form of what
remains states the defaults; the round trips compare `dumps` texts, which
tell `1.0` from `1`. No result shares
an object with `DEFAULTS`. The typed forms' oracle is the fixtures: each
minimal twin (73, one per fixture) completes to the canonical YAML of its
fixture, keeps it in canonical order,
and strips back to its own; a literal `CompleteManifest` compiles, and
keys whose default is absent (`id`, `graphical`, a root's `offset`) stay
optional.

## The description layer

`registry.test.ts` and `description.test.ts` assert the Python README's
sections "The description layer", "Links", "The description layer alone"
and "Unregistered terms" with the same documents, the same values and the
same messages: the nine shipped entries in order with their `lowercase`,
the recognition table (the MusicBrainz ID in capitals among it) and the URL
forms (every IMSLP page that is no work page refused, plainly and with
`%3A`, and the two work pages beginning with such a word recognised), the
addresses of a YouTube video (one entity URI, the ID's case kept, the
legacy `/v/` with `&` straight after the ID and on `youtube-nocookie.com`
recognised, the embedded playlist `videoseries` and a channel's embedded
live stream `live_stream` refused), the one rule per scheme,
`withSchemes`, its reading of an entry without
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
the Python suite, and every fixture round-trips.

## Manifest files

`fileForm(text)` gives a `FileForm`, `{ minimal, styling, serialization }`,
and `dumpsFile(value, form)` writes a value back in it, as Python's
`file_form` and `dumps_file` do (`src/files.ts`). The form is minimal when
`minimal(value)` and `value` write the same canonical YAML, the equality
of the fixtures' twin law: a key stated at its default, recognized by
exact value, makes a text not minimal, and the order canonical order sorts
does not count. What proves them (`files.test.ts`):

- **Every fixture comes back byte for byte.** For every fixture and every
  minimal twin (bundles and groups included), its value and its value
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
  same text Python's test pins.
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
