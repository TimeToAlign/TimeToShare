# 0014. Read YAML in TypeScript with yaml

Date: 2026-11-17

## Context

A manifest may be written in YAML 1.2. The package writes its canonical
YAML itself, because the format fixes that layout character for character,
so it needs a library for reading only. The reader accepts any valid YAML 1.2
in any style people write by hand (block and flow collections, plain,
single-quoted and double-quoted scalars, block scalars, comments) and must:

1. resolve plain scalars by the core schema, the recommended default of
   YAML 1.2.2 (§10.3.2): `no` and `2026-11-17` are strings, `1e-05` and
   `2.0` are floats, `2` is an integer;
2. keep integers exact at any size, as `bigint`, the way the package's
   lossless JSON reader does;
3. tell integer and float apart as the core schema resolves them, which in
   JavaScript, where `2` and `2.0` are the same `number`, needs each
   scalar's resolved kind or its source text;
4. read a float literal as the nearest double, underflow to zero and
   subnormals included, and refuse one that rounds to an infinity
   (`1e309`); `1.7976931348623158e308` is the largest double;
5. refuse anchors and aliases, explicit tags (the non-specific `!`
   included), a text that holds no document, more than one document,
   every directive other than `%YAML 1.2`, duplicate keys, keys that are
   not strings, an implicit key whose span from its first character up
   to, not including, its `:` exceeds 1024 characters, counted in code
   points (YAML 1.2 sets this limit, productions [154] and [155], for the
   implicit keys of block mappings and of single pairs in flow sequences;
   the format extends it to the keys of flow mappings, production [144],
   which YAML leaves unlimited), and `.nan` and the infinities;
6. read a surrogate pair written as two `\u` escapes as one character, and
   refuse a lone surrogate, whether written as itself or through an
   escape;
7. refuse every character written as itself, in a scalar or a comment,
   outside YAML's printable set, U+0085, U+2028 and U+2029, and every
   U+FEFF but the one of requirement 8, as the Python package must; the
   escapes stay allowed;
8. remove exactly one U+FEFF (byte order mark) at position 0;
9. construct no objects from the text (safe loading only);
10. throw an error with the offset, line and column for malformed text and
    for every refusal;
11. ignore comments;
12. run on the Node versions of the package's `engines` (`>=22.18.0`) and
   import into an ES module, under a licence compatible with MIT.

## Considered options

Each candidate was installed and run against the requirements on Node on
2026-11-17.

- **`yaml` 2.9.1** (Eemeli Aro). Parses to a document of nodes
  (`parseDocument`), keeps each scalar's `source` text, `anchor`, `tag` and
  `range`, and reports errors with a `code` and a line and column. With
  `{schema: "core", intAsBigInt: true}` it resolves exactly by the core
  schema: `no`, `1_000`, `0b101`, `2026-11-17`, `=` and `<<` are strings;
  `2`, `0o17`, `0x1F` and a 30-digit integer are `bigint`; `2.0`, `1e-05`
  and `.5` are `number`. A `%YAML 1.1` directive does not change the
  resolution under `schema: "core"`.
- **`yaml` 3.0.0-2.** A prerelease of the next major line, ES modules only;
  not a release.
- **`js-yaml` 5.5.0** (MIT, 2026-10-15, depends on `argparse`). Parses to
  plain values only: `2` and `2.0` both give the number `2`, and
  `123456789012345678901234567890` gives `1.2345678901234568e+29`, so
  requirements 2 and 3 fail; with no node tree, aliases and tags cannot be
  detected once loaded. Its `CORE_SCHEMA` resolves the other core scalars
  correctly. OSV lists twelve advisories for the package, eight of them
  published in 2026, most about CPU exhaustion in merge keys and `!!omap`;
  none affects 5.5.0.
- **Write the reader here.** A full YAML 1.2 reader is large: the parse and
  compose stages of `yaml` are about 3,900 lines of JavaScript. A reader
  restricted to the canonical layout would refuse the hand-edited YAML the
  format accepts.

## Decision

Use `yaml` 2.9.1. `loads(text)` reads any serialization without
validating, as the Python package's `loads` does: it removes one U+FEFF
at position 0, dispatches the rest to JSON or YAML by the rule of the
README's "Reading" and passes it to the internal JSON or YAML reader,
which removes nothing more; `parse` is `loads` followed by validation.
Only the exported `parseJson` and `parseYaml`, when called directly,
remove one leading U+FEFF themselves. The YAML reader first scans the
text (for the characters it refuses, see Characters, and for
directives), then calls `parseDocument(text, {schema: "core",
intAsBigInt: true, uniqueKeys: true, keepSourceTokens: true,
lineCounter})` and builds the value by walking the node tree itself; it
never calls `toJS` and never resolves an alias. The walk keeps an explicit
stack or a depth bound, so a deeply nested text cannot exhaust the call
stack. Each requirement is met as follows:

| Requirement | How |
| --- | --- |
| Core schema | By option: `schema: "core"`. |
| Exact integers | By option: `intAsBigInt: true` makes every integer a `bigint`. |
| Integer and float told apart | By option: with `intAsBigInt`, a scalar whose `value` is a `bigint` is an integer and one whose `value` is a `number` a float; `source` keeps the text. |
| Float range | By the library and the walk: the core schema's float is `parseFloat` of the text, which rounds to the nearest double (`1.7976931348623158e308` gives `Number.MAX_VALUE`, `1e-400` gives 0, `2.5e-324` gives `Number.MIN_VALUE`); the walk refuses a `number` that is not `Number.isFinite`, and throws `RangeError` when `source` is a finite literal that rounds to an infinity (`1e309`, `-1e309`, `1.7976931348623159e308`), as the JSON reader does. |
| `.nan` and infinities | By the walk, by the same test; when `source` is `.nan` or an infinity (`.inf`, `-.Inf` and the other core spellings) it throws `YamlSyntaxError`. |
| Anchors and aliases | By the walk: refused at a node for which `isAlias(node)` holds or whose `anchor` is set. |
| Explicit tags | By the walk: refused at a node whose `tag` is set; implicit resolution leaves `tag` unset, while `!foo`, `!!str`, `!!binary` and `!` set it. |
| No document | `contents` is `null` for an empty text or one of whitespace and comments only. `yaml` also reads `...` alone, a stream that holds no document, as a document holding null; the package tells it from `---` alone, a document holding null that is read, by `doc.directives.docStart`: without `---`, contents that are a scalar of empty range (`range[0] === range[1]`) mean no document. `''` has a range and is the empty string. |
| One document | By the parser: a second document is the error `MULTIPLE_DOCS`. |
| Directives | By the package's own scan, before parsing, as in Python: it reads the lines up to the first that is neither blank, a comment nor a directive (a line beginning with `%`), and refuses at its line every directive other than a single `%YAML 1.2`. The document does not suffice: `doc.directives.yaml` is `{explicit: true, version: "1.1"}` after `%YAML 1.1` and `doc.directives.tags` gains the handle of `%TAG !e! …`, but `%YAML 1.3` and a reserved directive (`%FOO bar`) are only warnings (`BAD_DIRECTIVE` in `doc.warnings`) that leave `version` at `"1.2"`, and `%TAG !! tag:yaml.org,2002:` leaves `tags` as it was. |
| Duplicate keys | By option: `uniqueKeys: true` reports `DUPLICATE_KEY`; `a` and `"a"` collide. |
| Keys that are not strings | By the walk: refused unless `pair.key` is a scalar whose `value` is a string. The option `stringKeys` stays unset, since it would turn `1:` into the key `"1"` instead of refusing it. |
| Implicit key over 1024 characters | By the walk, in place of the library. `yaml` measures the key from its first character up to, not including, its `:` (quotes, escapes and spaces before the `:` included) and reports `KEY_OVER_1024_CHARS` when that span exceeds 1024 UTF-16 code units, for keys of block mappings and of single pairs in flow sequences, where YAML 1.2 sets the limit; keys of flow mappings, which YAML leaves unlimited, it does not check (`{` `a`×2000 `: 1}` is read). The format extends the limit to them, and the walk applies it. The document is composed all the same. The package drops every `KEY_OVER_1024_CHARS` and recounts every implicit key of a block mapping, a flow-sequence pair and a flow mapping in code points, `[...text.slice(key.range[0], colon)].length`, with `colon` the first `:` at or after `key.range[1]`, and refuses the key when the count exceeds 1024. A key is explicit, and has no limit, when the syntax tree shows the `?` indicator: with `keepSourceTokens: true`, each pair keeps its item of the concrete syntax tree as `pair.srcToken`, and the pair is explicit when `pair.srcToken.start` holds a token of type `explicit-key-ind`, in block and flow collections alike, whatever separates the `?` from the key (a space, a tab, a comment or a line break). So `?` LF, two spaces, `a`×1100, LF, `: 1` is read, as ruamel.yaml reads it, and not counted as an implicit key. `a`×1024 `: 1` and 1024 characters outside the Basic Multilingual Plane (2048 code units) are read; `a`×1025 `: 1`, `a`×1024 ` : 1`, `{` `a`×1025 `: 1}` and `"` `a`×1023 `": 1` are refused, as in Python. |
| Surrogates | By the library and the walk: `yaml` joins a pair of `\u` escapes into one character (`"\ud83d\ude00"` gives U+1F600) and leaves an unpaired one in the string (`"\ud800"`, `"\U0000d800"`, `"\udc00\ud800"`); the walk refuses a string key or value for which `isWellFormed()` is false. `yaml` reads a lone surrogate written as itself as content, in a comment too; the package refuses it by `text.isWellFormed()` before parsing, as ruamel.yaml's reader does in Python. |
| Characters | By the package's scan before parsing: the first character written as itself, in a scalar or a comment, that lies outside YAML's printable set (C0 controls other than tab, LF and CR; U+007F to U+009F; U+FFFE; U+FFFF; surrogates) or is U+0085, U+2028, U+2029 or a U+FEFF other than the one removed at position 0 refuses the text at its position. A lone surrogate is found by `text.isWellFormed()`. `yaml` reads all of these as content, and U+0085, U+2028 and U+2029 as YAML 1.2 specifies; the format refuses the three all the same, which keeps the two packages reading the same texts, since ruamel.yaml would misread the three. YAML 1.2 reads U+FEFF as content in places, in a quoted or block scalar for one, and `yaml` reads it as content wherever it stands, in a plain scalar, a comment and a key too (a second leading U+FEFF becomes part of the first key), as ruamel.yaml does; the refusal of every other U+FEFF is a rule of the format, which both libraries read alike. The escapes `\N`, `\L` and `\P` give the characters. |
| Leading U+FEFF | One U+FEFF at position 0 is removed once: by `loads`, and so by `parse`, before dispatch, after which the internal JSON and YAML readers remove nothing more; or by `parseJson` or `parseYaml` when called directly. Any other U+FEFF in YAML is refused by the scan of the Characters row: in `﻿﻿a: 1` the second U+FEFF makes the text YAML by the dispatch rule, and the scan refuses it at position 0 of the remaining text, through `loads`, `parse` and `parseYaml` alike. |
| Safe loading | The walk builds plain values only, with `Object.fromEntries`, so `__proto__` is an ordinary own key; the library constructs no class instance from a tag. |
| Positions | `parseYaml` throws `YamlSyntaxError`, a new subclass of `SyntaxError` with the fields of `JsonSyntaxError` (`offset`, in UTF-16 code units from zero; `line` and `column` counted from one), for every error in `doc.errors` but `KEY_OVER_1024_CHARS` (`pos[0]` and `linePos[0]`, with the error's `code` in the message) and for every refusal by the walk (`node.range[0]` and `lineCounter.linePos`) or by a scan (the index it found); the one exception is a finite literal that rounds to an infinity, for which the walk throws `RangeError` with the same position in its message. |
| Comments | Kept on the nodes (`comment`, `commentBefore`) and ignored by the walk. |

The emitter is not used.

- **Fit.** `yaml` is the only candidate that resolves the core schema
  exactly, keeps integers exact and exposes each node's kind, source,
  anchor, tag and position. In the YAML test-suite matrix it passes 307 of
  308 valid and 92 of 94 invalid cases in the event comparison
  (https://matrix.yaml.info/, test data of 2022-01-17, processor versions
  not stated).
- **Maintenance.** Eemeli Aro is the single maintainer on npm; his
  library has been published under the name since 1.0 in 2018 (97 of the
  name's 105 versions; the earlier 0.x versions of 2011 are another
  author's unrelated package). The 2.x line had four
  releases in 2026: 2.8.3 (2026-03-21), 2.8.4 (2026-05-02), 2.9.0
  (2026-05-11) and 2.9.1 (2026-09-11); a 3.0 line is in prerelease, ES
  modules only, for Node `^20.19 || ^22.12 || >=24`. The bus factor is
  one; the 2.x line is mature and the package's exposure is one call and
  the node predicates.
- **Writing it ourselves.** Owning a YAML 1.2 grammar of several thousand
  lines and its edge cases is out of proportion to reading manifests.
- **Audited version.** `yaml` 2.9.1, published to npm on 2026-09-11, 67
  days before this record, so the 14-day rule holds. Licence ISC. No
  dependencies; 686,297 bytes unpacked; `engines` `node >= 14.6`. Node
  resolves the package's CommonJS build (`exports["."].node`), whose named
  exports an ES module imports (`import {parseDocument} from "yaml"`,
  checked on Node); other environments resolve its ES module build. OSV
  lists two advisories for the package, both fixed before 2.9.1:
  CVE-2023-2251 (fixed in 2.2.2) and CVE-2026-33532, unbounded recursion
  on deeply nested collections (fixed in 2.8.3); 2.9.1 reports 20,000
  nested flow sequences as the error `RESOURCE_EXHAUSTION`.
- **Range.** `package.json` declares `yaml` `^2.9.1`; the lockfile pins
  2.9.1.

Primary sources: https://yaml.org/spec/1.2.2/ (§10.3, Core Schema),
https://registry.npmjs.org/yaml, https://github.com/eemeli/yaml,
https://eemeli.org/yaml/, https://github.com/eemeli/yaml/blob/main/LICENSE,
https://registry.npmjs.org/js-yaml, https://github.com/nodeca/js-yaml,
https://matrix.yaml.info/,
https://github.com/advisories/GHSA-48c2-rrv3-qjmp,
https://github.com/advisories/GHSA-f9xv-q969-pqx4,
https://osv.dev/ (queried through its API).

## Consequences

The package adds one runtime dependency with no transitive dependencies.
The walk and the scans own the format's refusals, which are its own rules
in any case; the grammar and the core-schema resolution stay in the
library. Two of them correct the library where it departs from YAML 1.2:
the key limit, which `yaml` counts in UTF-16 code units, and a stream that
holds no document but `...`, which `yaml` reads as null. A third applies a
rule the format adds to YAML: the key limit for flow mappings, which
YAML 1.2 leaves unlimited and `yaml` accordingly does not check. The exit
cost is the YAML reader module of the package. The release of `yaml` 3.0
needs a review: its Node range excludes Node 23, which the package's
`engines` admit.

## Review date

2027-11-17, or when `yaml` 3.0 is released.
