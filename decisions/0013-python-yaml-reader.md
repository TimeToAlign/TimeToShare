# 0013. Read YAML in Python with PyYAML

Date: 2026-11-17

## Context

A manifest may be written in YAML. The package writes its canonical YAML
itself, because the format fixes that layout character for character, so
it needs a library for reading only. The reader must:

1. resolve plain scalars by the core schema of YAML 1.2.2 (§10.3.2):
   `no` and `2026-11-17` are strings, `1e-05` and `2.0` are floats, `2` is
   an integer;
2. keep integers exact at any size, and read a float literal as the
   nearest double;
3. refuse, with the line and column of the offending node: malformed text
   and more than one document; a character outside YAML's printable set;
   duplicate keys; anchors, aliases and tags; a key that is not a string;
   a non-finite float (`.inf`, `.nan`, and a literal such as `1e309` that
   rounds to an infinity); a string holding an unpaired surrogate;
   collections nested deeper than 256 levels; of several faults, the first
   in document order;
4. construct no objects from the text (safe loading only);
5. raise `ValueError` for every refusal;
6. run on every Python the package supports (`requires-python >= 3.11`),
   under a licence compatible with MIT.

The format guarantees that canonical YAML, and any YAML text using only
its constructs, is read to the same value by both packages. Beyond those
constructs a text is read as the package's parser reads it, after the
checks of requirement 3.

PyYAML describes itself as "a complete YAML 1.1 parser"
(https://pypi.org/project/PyYAML/). Its `SafeLoader` resolves plain
scalars by YAML 1.1: `k: no` gives `False`, `k: 1e-5` the string `"1e-5"`
(a 1.1 float needs a decimal point), `k: 017` the octal 15, `k: 1_000`
the integer 1000 and `k: 2026-11-17` a `datetime.date`; of two equal keys
it keeps the last silently. The grammar of 1.1 and 1.2 agrees on every
construct canonical YAML uses; PyYAML's resolution of plain scalars and
its handling of duplicate keys do not suit the format.

## Considered options

Each candidate was installed in a clean environment on Python 3.11 and run
against the requirements on 2026-11-17.

- **PyYAML 6.0.3 as it is.** Fails requirement 1 (`no`, `1e-5`, `017`,
  `1_000`, dates) and keeps duplicate keys silently.
- **PyYAML 6.0.3's parser events with the core-schema table.** The
  reader takes the events of PyYAML's documented low-level API, resolves
  plain scalars by the core schema itself and makes the checks of
  requirement 3 in one pass over the events (see Decision). Meets every
  requirement.
- **ruamel.yaml 0.19.1.** YAML 1.2 by declaration, but its resolver is not
  the core schema even with `version=(1, 2)`: `2026-11-17` gives a
  `datetime.date`, `1_000` and `0b101` integers, and `=` and `<<` are
  refused as unknown tags. It has one maintainer and stays at 0.x, whose
  minor releases remove API (0.18 turned the module-level `load` and
  `parse` into errors), and its project description warns that PEP 625
  may force a change of the project name.
- **Write the parser here.** A YAML parser is several thousand lines
  (PyYAML's pure-Python reader, scanner, parser and composer, with their
  tokens, events and errors, are about 2,600); a reader restricted to the canonical layout would refuse the
  hand-edited YAML the format accepts.

## Decision

Use PyYAML's documented low-level API and nothing beyond it:
`yaml.parse(text, Loader=yaml.SafeLoader)`, the event classes with their
attributes (`anchor`, `tag`, `implicit`, `value`, `style`,
`start_mark.line`, `start_mark.column`, `start_mark.index`) and
`yaml.MarkedYAMLError` with its marks, whose `problem_mark` the
documentation's own example of error handling reads
(https://pyyaml.org/wiki/PyYAMLDocumentation, "The yaml package", "Mark",
"YAMLError", "Events"). No PyYAML class is subclassed, no resolver or
constructor registered, no node built, no internal method or module used,
so a PyYAML release that keeps its documented interface keeps the reader
working. The format's core-schema table is the reader's own.

The loader named is the pure-Python `yaml.SafeLoader`, never
`yaml.CSafeLoader`, so that the value a text reads to never depends on
whether PyYAML was built with libyaml. The two read differently: libyaml
refuses every `\u` escape of a surrogate, so `CSafeLoader` refuses
`"\ud83d\ude00"`, which `SafeLoader` reads as two surrogates that the
reader joins into U+1F600; and `CSafeLoader` reads a tab after `key:` or
inside a plain scalar (`a:\t1`, `k: a\tb`), which `SafeLoader` refuses.
Manifests are small, so the speed of the C loader does not matter.

**Characters first.** Before parsing, the reader looks for the first
character outside YAML 1.2's `c-printable` (tab, line feed, carriage
return, U+0020 to U+007E, U+0085, U+00A0 to U+D7FF, U+E000 to U+FFFD,
U+10000 to U+10FFFF; a lone surrogate is outside) with one regular
expression and refuses it where it stands (`special characters are not
allowed #x0001`), whatever fault comes before it in the text. PyYAML
checks the same set, for the whole text, before it parses anything.

**One pass over the events.** The reader builds the value as the events
arrive, every open collection on a stack of its own rather than by
recursion, and checks each node when its event arrives, a key before its
value:

| Check | Refusal |
| --- | --- |
| `AliasEvent` | an alias, never expanded |
| `anchor` set | an anchor |
| `tag` set, whatever it names (`!!str`, `!!float`, `!local`, `!`) | a tag; `!!str 1` too, so no value of the format is written with a tag |
| a key that is not a plain or quoted scalar resolving to a string | a key that is not a string (`1:`, `null:`, `.inf:`, `[1]:`) |
| a key already in its mapping | a repeated key; `a` and `"a"` are the same key, and a merge key (`<<`) is an ordinary key, never merged |
| a collection opening while 256 are open | the first collection at depth 257, in document order |
| a float `.inf`, `.nan` (any spelling) or rounding to an infinity (`1e309`) | a float that is not finite |
| a string or key holding an unpaired surrogate | a lone surrogate |
| a second `DocumentStartEvent` | more than one document |

The anchor, the tag and every other check are placed at the event's
`start_mark`, which PyYAML puts at the node's first property where it has
one, and a node holding both an anchor and a tag is refused for the one
written first, the character at `start_mark.index` (`&` or `!`); an empty
key's `start_mark` is right after its `?`. **Resolution**: a plain scalar
(`style` is `None`) is resolved by the core schema of YAML 1.2.2
(§10.3.2), each pattern anchored with `\Z`, in this order; every quoted or
block scalar is a string:

| Kind | Pattern | Value |
| --- | --- | --- |
| null | `null\|Null\|NULL\|~\|` (the empty scalar included) | `None` |
| bool | `true\|True\|TRUE\|false\|False\|FALSE` | `True` for the first three |
| int | `[-+]?[0-9]+`, `0o[0-7]+`, `0x[0-9a-fA-F]+` | base 10, `0o` base 8, `0x` base 16, exact |
| float | `[-+]?(\.[0-9]+\|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?`, `[-+]?\.(inf\|Inf\|INF)`, `\.(nan\|NaN\|NAN)` | `float(text)`, the non-finite ones refused |
| string | every other plain scalar | the text |

`float(text)` rounds to the nearest double (`1.7976931348623158e308`
gives the largest double, `1e-400` gives `0.0`, `-1e-400` gives `-0.0`).
A string passes through `s.encode("utf-16-le",
"surrogatepass").decode("utf-16-le")`, which joins a high surrogate
followed by a low one into one character (`"\ud83d\ude00"` gives
U+1F600) and refuses an unpaired one (`"\ud800"`, `"\udc00\ud800"`).

The pass stops at the first fault, so of several faults the first in
document order is refused, the character check excepted, and except that a
syntax error the parser meets reading one token ahead (a scalar may turn
out to be a key) may be refused before a fault of the token just before
it: `- &a "\q"` is refused at the bad escape (1, 8), where the TypeScript
reader names the anchor (1, 3); an error of the parser (`ScannerError`,
`ParserError`, both a `MarkedYAMLError`) is raised where the parser meets
it. Every refusal is a `ValueError` naming the line and column, counted
from one, from the event's `start_mark` or the error's `problem_mark`
(else `context_mark`); PyYAML's marks count code points, so a character
above U+FFFF counts once. An empty text, one of comments only and `---`
alone read as null. A text nested 100,000 deep is refused at its 257th
collection, never by Python's recursion limit, since neither the parser
nor the pass recurses.

Verified on 2026-11-18 with PyYAML 6.0.3 on Python 3.13: `k: no` →
`"no"`, `k: 1e-5` → `1e-05`, `k: 0o17` → `15`, `k: 017` → `17`,
`k: 010` → `10`, `k: 1_000` → `"1_000"`,
`k: 2026-11-17` → `"2026-11-17"`, `k: 0b101` → `"0b101"`, `k: =` → `"="`,
`<<: 1` → `{"<<": 1}`, `k: 2.0` → `2.0`, a 30-digit integer exact; and
refused: `.inf`, `.nan`, `1e309`, `a: 1` with `"a": 2`, `1: x`,
`a: &x 1`, `a: *x`, `!!timestamp`, `!!set`, `!!omap`, `!foo`, `!!str 1`,
`!`, `!!python/name:os.system`, `"\ud800"`, U+0001, two documents.

- **Fit.** The standard parser of the Python ecosystem reads every
  construct of canonical YAML as YAML 1.2 does once plain scalars are
  resolved by the core schema; the format's own rules are that table and
  one pass over the parser's events.
- **Maintenance.** PyYAML is developed under the YAML project's
  organisation on GitHub (https://github.com/yaml/pyyaml), which also
  hosts libyaml; Kirill Simonov wrote it, and its recent releases and
  most commits since 2021 are by Matt Davis, with Ingy döt Net among the
  committers. Releases are rare and
  mostly follow new Python versions: 6.0 (2021-10-13), 6.0.1
  (2023-07-17), 6.0.2 (2024-08-06), 6.0.3 (2025-09-25, adding Python 3.14
  and Windows on Arm). The main branch, at 7.0.0.dev0, had its last commit
  on 2026-10-07. PyYAML was downloaded about 1.2 billion times in the
  month before this record (https://pypistats.org/packages/pyyaml). The
  package's exposure is `yaml.parse`, the event classes and
  `MarkedYAMLError`, all documented.
- **Writing it ourselves.** Owning a YAML grammar and its edge cases is out
  of proportion to reading manifests.
- **Audited version.** PyYAML 6.0.3, uploaded to PyPI on 2025-09-25, 418
  days before this record, so the 14-day rule holds. Licence MIT.
  `requires-python >= 3.8`; no runtime dependencies. Wheels for CPython
  3.8 to 3.14 and the free-threaded 3.14t, on Windows (x86-64 and, from
  3.12, Arm64), macOS (x86-64 and Arm64), manylinux (x86-64, AArch64,
  s390x) and musllinux (x86-64, AArch64), bundle the C extension, which
  the reader does not use; the source distribution builds without it
  when libyaml is missing. OSV
  lists four advisories, CVE-2017-18342, CVE-2019-20477, CVE-2020-1747
  and CVE-2020-14343, all about arbitrary code execution through the
  full or unsafe loaders and all fixed by 5.4 (queried 2026-11-17). A fix
  for exponential expansion through merge keys and aliases
  (https://github.com/yaml/pyyaml/pull/937, merged 2026-06-17) is not yet
  released; the reader is not exposed to it, since it refuses aliases as
  their events arrive and never merges.
- **Range.** `pyproject.toml` declares `PyYAML>=6.0.3,<7`; the lockfile
  pins 6.0.3. The next major release is excluded until reviewed.

Primary sources: https://yaml.org/spec/1.2.2/ (§10.3.2, Core Schema
tag resolution), https://pypi.org/project/PyYAML/6.0.3/,
https://github.com/yaml/pyyaml, https://pyyaml.org/wiki/PyYAMLDocumentation,
https://yaml.org/type/bool.html, https://yaml.org/type/float.html,
https://pypi.org/project/ruamel.yaml/0.19.1/,
https://pypistats.org/api/packages/pyyaml/recent,
https://osv.dev/ (queried through its API).

## Consequences

The package adds one runtime dependency with no transitive dependencies.
It owns the core-schema table and the checks, which are small and fixed
by the specification and the format.

Beyond the constructs of canonical YAML, `SafeLoader` reads by YAML
1.1's grammar. Found in 6.0.3: it refuses a tab after `key:` or inside a
plain scalar (`a:\t1`, `k: a\tb`) and a line holding only a tab (`a: 1`,
a line of one tab, `b: 2` raises `ScannerError` at the tab), all of
which YAML 1.2 reads; and it takes U+0085, U+2028 and U+2029 written as
themselves for line breaks. Canonical YAML writes none of these: it
escapes the tab and those three characters. Such a text is read as
`SafeLoader` reads it, and a difference there is not a defect of the
format. Within those constructs, the package's tests check that PyYAML's
unmodified `yaml.safe_load` reads every canonical YAML fixture to the
value the reader gives.

`CSafeLoader` is ruled out for one more reason: with libyaml's composer,
a sequence nested 3,000 deep ended the Python 3.11 process on Windows
without an exception, where `SafeLoader`'s composer raises
`RecursionError`. The reader composes no tree and so is exposed to
neither.

The exit cost is the reader module. The review revisits the choice if
PyYAML releases a YAML 1.2 loader of its own, or a major version.

## Review date

2027-11-17, or when PyYAML 7 is released.
