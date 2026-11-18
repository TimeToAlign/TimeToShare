# 0014. Read YAML in TypeScript with yaml

Date: 2026-11-17

## Context

A manifest may be written in YAML. The package writes its canonical YAML
itself, because the format fixes that layout character for character, so
it needs a library for reading only. The reader must:

1. resolve plain scalars by the core schema of YAML 1.2.2 (§10.3.2):
   `no` and `2026-11-17` are strings, `1e-05` and `2.0` are floats, `2` is
   an integer;
2. keep integers exact at any size, as `bigint`, the way the package's
   lossless JSON reader does, and tell integer and float apart as the core
   schema resolves them, which in JavaScript, where `2` and `2.0` are the
   same `number`, needs each scalar's resolved kind;
3. read a float literal as the nearest double;
4. refuse, with the position of the offending node: malformed text and
   more than one document; a character outside YAML's printable set;
   duplicate keys; anchors, aliases and tags; a key that is not a string;
   a non-finite float
   (`.inf`, `.nan`, and a literal such as `1e309` that rounds to an
   infinity); a string holding an unpaired surrogate; collections nested
   deeper than 256 levels; of several faults, the first in document order;
5. construct no objects from the text (safe loading only);
6. throw an error with the offset, line and column for every refusal;
7. run on the Node versions of the package's `engines` (`>=22.18.0`) and
   import into an ES module, under a licence compatible with MIT.

The format guarantees that canonical YAML, and any YAML text using only
its constructs, is read to the same value by both packages. Beyond those
constructs a text is read as the package's parser reads it, after the
checks of requirement 4.

## Considered options

Each candidate was installed and run against the requirements on Node on
2026-11-17.

- **`yaml` 2.9.1** (Eemeli Aro). Parses to a document of nodes
  (`parseDocument`), keeps each node's `anchor`, `tag` and `range`, and
  reports errors and warnings with a `code` and a position. With
  `{schema: "core", intAsBigInt: true}` it resolves exactly by the core
  schema: `no`, `1_000`, `0b101`, `2026-11-17`, `=` and `<<` are strings;
  `2`, `0o17`, `017`, `0x1F` and a 30-digit integer are `bigint`; `2.0`,
  `1e-05` and `.5` are `number`.
- **`yaml` 3.0.0-2.** A prerelease of the next major line, ES modules only;
  not a release.
- **`js-yaml` 5.5.0** (MIT, 2026-10-15, depends on `argparse`). Parses to
  plain values only: `2` and `2.0` both give the number `2`, and
  `123456789012345678901234567890` gives `1.2345678901234568e+29`, so
  requirement 2 fails; with no node tree, aliases cannot be detected once
  loaded. OSV lists twelve advisories for the package, eight of them
  published in 2026, most about CPU exhaustion in merge keys and `!!omap`;
  none affects 5.5.0.
- **Write the parser here.** The parse and compose stages of `yaml` are
  about 3,900 lines of JavaScript; a reader restricted to the canonical
  layout would refuse the hand-edited YAML the format accepts.

## Decision

Use `yaml` 2.9.1. The YAML reader first refuses a character outside
YAML 1.2's printable set, then calls `parseDocument(text, {schema:
"core", intAsBigInt: true, uniqueKeys: true, keepSourceTokens: true})`,
then builds the value by
one walk over the node tree in document order (a key before its value, a
value's items before the next key), with an explicit stack, so a text
nested as deeply as `yaml` composes it never exhausts the call stack in
the walk; it never calls `toJS` and never resolves an alias. At each node
the walk checks, in this order, an alias, an anchor, a tag, a key being a
string, the depth, then the value, and it stops at the first fault. Every error and warning of the parser is a fault as well; the
reader refuses the one of them with the smallest `pos[0]`.

| Refusal | How |
| --- | --- |
| Characters outside the printable set | `yaml` reads them; YAML 1.2 allows only `c-printable` (tab, line feed, carriage return, U+0020 to U+007E, U+0085, U+00A0 to U+D7FF, U+E000 to U+FFFD, U+10000 to U+10FFFF), as PyYAML does. Before parsing, the reader refuses the first other code point, U+0001, U+007F or a lone surrogate among them, at its offset with PyYAML's message (`special characters are not allowed #x0001`), whatever fault comes before it, as PyYAML does. |
| Malformed text, more than one document, duplicate keys | Errors of the parser: a second document is `MULTIPLE_DOCS`, two equal keys (`a` and `"a"` alike) are `DUPLICATE_KEY` under `uniqueKeys`, a text nested too deeply for the call stack is `RESOURCE_EXHAUSTION`. |
| What the parser only warns about | Refused as well: an unknown tag (`!foo`) is the warning `TAG_RESOLVE_FAILED`, at the tag, where the walk would refuse it too. |
| Anchors, aliases and tags | The walk refuses a node, key or value, for which `isAlias(node)` holds, then one whose `anchor` is set, then one whose `tag` is set, whatever the tag names (`!!str 1` and `!` included); implicit resolution leaves `tag` unset. |
| Keys that are not strings | The walk refuses a pair whose `key` is not a scalar whose `value` is a string (`1:`, `null:`, `[1]:`). The option `stringKeys` stays unset, since it would turn `1:` into the key `"1"`. |
| The data model | With every tag refused, a scalar under the core schema is `null`, a boolean, a string, a `bigint` or a `number`, a collection a mapping or a sequence, so nothing else needs a check. |
| Non-finite floats | The walk refuses a scalar whose `value` is a `number` that is not `Number.isFinite`: `.inf`, `-.Inf` and `.nan`, which `yaml` resolves to `Infinity` and `NaN` with `tag` unset, and `1e309`, which `parseFloat` rounds to `Infinity`. |
| Unpaired surrogates | The walk refuses a string, key or value, holding a high surrogate not followed by a low one or a low surrogate not preceded by a high one, by the package's own test, which the writers share. `yaml` joins a high-surrogate escape followed by a low one into one character (`"\ud83d\ude00"` gives U+1F600) and leaves an unpaired one in the string (`"\ud800"`). |
| Nesting deeper than 256 levels | The walk knows the depth of each node from its stack (the root stands at depth 1) and refuses a mapping or a sequence at depth 257 at its first character, before it walks into it: the first collection at depth 257, in document order. |

**The first fault.** Of several faults the reader refuses the first in
document order, once the characters are checked. The walk meets its own faults in that order and stops at
the first; the parser reports its errors and warnings in lists of their
own, ordered by kind rather than by place, so the reader takes the one
with the smallest `pos[0]`. A fault of the walk is refused unless that
problem of the parser lies at or before its offset, and a problem of the
parser alone is refused where the walk finds none. One problem never
outranks the walk: `RESOURCE_EXHAUSTION`, which `yaml` reports where its
stack ran out composing collections hundreds of levels deeper than 257 and
where it stops composing. The tree it leaves still holds the collection at
depth 257, which the walk reaches first, so a text nested 100,000 deep is
refused at the same place as one nested 257 deep.

Numbers stay lossless by the scalar's resolved kind: a `value` that is a
`bigint` is an integer, one that is a `number` a float.

Every refusal throws `YamlSyntaxError`, a subclass of `SyntaxError` with
the fields of `JsonSyntaxError` (`offset`, in UTF-16 code units from zero;
`line` and `column` counted from one, the column in code points, so that
a character above U+FFFF counts once, as in PyYAML's marks), from an
offset: for an error or warning of the parser its `pos[0]`, with its
`code` in the message; for a refusal of the walk the offending token.
An alias is refused at its `*`, an anchor or a tag at the node's first
property, whichever is written first, every other fault of a node at its
`range[0]`. A node keeps no position of its properties: they are tokens
of the concrete syntax tree written before the node (in a document's
start for the root, in an item's start for its key, or its value where it
has no key, and in an item's separator for its value). Where a node has
one, the reader parses the text again with `yaml`'s `Parser` and takes
the first there, naming the node's token by its type and its `offset`
(kept by `keepSourceTokens`), since a block mapping and its first key
share an offset; an empty node, which has no token, takes the last
written before its `range[0]`. The package computes the line and column
from the offset itself, with the same function as for `JsonSyntaxError`
(a line ends at each line feed), so no `LineCounter` is passed. The walk builds plain
values only, defining each key as an own property in its written order,
so `__proto__` is an ordinary own key. An empty text, or one of comments
only, reads as null; `---` alone too. Comments are kept on the nodes and
ignored by the walk. The emitter is not used.

Verified on 2026-11-18 with `yaml` 2.9.1 on Node 22.23: `!foo 1` gives the
warning `TAG_RESOLVE_FAILED`; `.inf` resolves to the `number` `Infinity`
with `tag` unset; `&x` sets `anchor` and `*x` is a node for which
`isAlias` holds; the values listed under `yaml` 2.9.1 above, the
refusals of the table, and `%YAML 1.1` before a document leaving the
resolution unchanged.

- **Fit.** `yaml` is the only candidate that resolves the core schema
  exactly, keeps integers exact and exposes each node's kind, anchor, tag
  and position. In the YAML test-suite matrix it passes 307 of 308 valid
  and 92 of 94 invalid cases in the event comparison
  (https://matrix.yaml.info/, test data of 2022-01-17, processor versions
  not stated).
- **Maintenance.** Eemeli Aro is the single maintainer on npm; his
  library has been published under the name since 1.0 in 2018 (97 of the
  name's 105 versions; the earlier 0.x versions of 2011 are another
  author's unrelated package). The 2.x line had four releases in 2026:
  2.8.3 (2026-03-21), 2.8.4 (2026-05-02), 2.9.0 (2026-05-11) and 2.9.1
  (2026-09-11); a 3.0 line is in prerelease, ES modules only, for Node
  `^20.19 || ^22.12 || >=24`. The bus factor is one; the 2.x line is
  mature and the package's exposure is one call and the node predicates.
- **Writing it ourselves.** Owning a YAML grammar and its edge cases is out
  of proportion to reading manifests.
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

Primary sources: https://yaml.org/spec/1.2.2/ (§10.3.2, Core Schema
tag resolution), https://registry.npmjs.org/yaml,
https://github.com/eemeli/yaml, https://eemeli.org/yaml/,
https://github.com/eemeli/yaml/blob/main/LICENSE,
https://registry.npmjs.org/js-yaml, https://github.com/nodeca/js-yaml,
https://matrix.yaml.info/,
https://github.com/advisories/GHSA-48c2-rrv3-qjmp,
https://github.com/advisories/GHSA-f9xv-q969-pqx4,
https://osv.dev/ (queried through its API).

## Consequences

The package adds one runtime dependency with no transitive dependencies.
The grammar and the core-schema resolution stay in the library; the walk
owns the format's refusals, which are its own rules in any case. Beyond
the constructs of canonical YAML a text is read as `yaml` reads it, which
follows YAML 1.2 more closely than PyYAML does, so the two packages may
differ there; such a difference is not a defect of the format. The exit
cost is the YAML reader module. The release of `yaml` 3.0 needs a review:
its Node range excludes Node 23, which the package's `engines` admit.

## Review date

2027-11-17, or when `yaml` 3.0 is released.
