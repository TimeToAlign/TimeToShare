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
4. refuse anchors and aliases, explicit tags (the non-specific `!`
   included), more than one document, duplicate keys, keys that are not
   strings, `.nan` and the infinities, and floats beyond a double;
5. construct no objects from the text (safe loading only);
6. report the line and column of malformed text;
7. ignore comments;
8. run on the Node versions of the package's `engines` (`>=22.18.0`) and
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

Use `yaml` 2.9.1. The package calls
`parseDocument(text, {schema: "core", intAsBigInt: true, uniqueKeys: true,
lineCounter})` and builds the manifest value by walking the node tree
itself; it never calls `toJS` and never resolves an alias. The walk keeps
an explicit stack or a depth bound, so a deeply nested text cannot exhaust
the call stack. Each requirement is met as follows:

| Requirement | How |
| --- | --- |
| Core schema | By option: `schema: "core"`. |
| Exact integers | By option: `intAsBigInt: true` makes every integer a `bigint`. |
| Integer and float told apart | By option: with `intAsBigInt`, a scalar whose `value` is a `bigint` is an integer and one whose `value` is a `number` a float; `source` keeps the text. |
| Anchors and aliases | By the walk: refused at a node for which `isAlias(node)` holds or whose `anchor` is set. |
| Explicit tags | By the walk: refused at a node whose `tag` is set; implicit resolution leaves `tag` unset, while `!foo`, `!!str`, `!!binary` and `!` set it. |
| One document | By the parser: a second document is the error `MULTIPLE_DOCS`. |
| Duplicate keys | By option: `uniqueKeys: true` reports `DUPLICATE_KEY`; `a` and `"a"` collide. |
| Keys that are not strings | By the walk: refused unless `pair.key` is a scalar whose `value` is a string. The option `stringKeys` stays unset, since it would turn `1:` into the key `"1"` instead of refusing it. |
| `.nan`, infinities, floats beyond a double | By the walk: refused when a `number` value is not `Number.isFinite`; `source` tells `.inf` from `1e400` for the message. |
| Safe loading | The walk builds plain values only, with `Object.fromEntries`, so `__proto__` is an ordinary own key; the library constructs no class instance from a tag. |
| Positions | `document.errors[i].linePos[0]` gives `{line, col}` counted from one, with the error's `code`; a refusal by the walk reports `lineCounter.linePos(node.range[0])` (`LineCounter`). |
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
The walk owns the format's refusals, which are its own rules in any case;
the grammar and the core-schema resolution stay in the library. The exit
cost is the YAML reader module of the package. The release of `yaml` 3.0
needs a review: its Node range excludes Node 23, which the package's
`engines` admit.

## Review date

2027-11-17, or when `yaml` 3.0 is released.
