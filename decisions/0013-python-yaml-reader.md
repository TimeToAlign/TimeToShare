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
   and more than one document; duplicate keys; anchors and aliases; a key
   that is not a string; a value outside the JSON data model; a non-finite
   float (`.inf`, `.nan`, and a literal such as `1e309` that rounds to an
   infinity); a string holding an unpaired surrogate;
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
- **PyYAML 6.0.3 with the core-schema resolvers.** A loader subclass
  replaces the 1.1 implicit resolvers by the core schema's through
  PyYAML's resolver API and adds the checks of requirement 3 in its
  composer and constructor (see Decision). Meets every requirement.
- **ruamel.yaml 0.19.1.** YAML 1.2 by declaration, but its resolver is not
  the core schema even with `version=(1, 2)`: `2026-11-17` gives a
  `datetime.date`, `1_000` and `0b101` integers, and `=` and `<<` are
  refused as unknown tags. It takes U+0085, U+2028 and U+2029 for line
  breaks, as YAML 1.1 did, and so misreads silently a text that holds them
  as themselves (`k: a`U+0085`b` gives `"a b"`). It has one maintainer and
  stays at 0.x, whose minor releases remove API (0.18 turned the
  module-level `load` and `parse` into errors), and its project description
  warns that PEP 625 may force a change of the project name.
- **Write the parser here.** A YAML parser is several thousand lines
  (PyYAML's pure-Python reader, scanner, parser and composer, with their
  tokens, events and errors, are about 2,600); a reader restricted to the canonical layout would refuse the
  hand-edited YAML the format accepts.

## Decision

Use PyYAML. The reader is a loader subclass of the pure-Python
`yaml.SafeLoader` only, never of `yaml.CSafeLoader`, so that the value a
text reads to never depends on whether PyYAML was built with libyaml.
The two loaders read differently: libyaml refuses every `\u` escape of a
surrogate, so `CSafeLoader` refuses `"\ud83d\ude00"`, which `SafeLoader`
reads as two surrogates that the check below joins into U+1F600; and
`CSafeLoader` reads a tab after `key:` or inside a plain scalar
(`a:\t1`, `k: a\tb`), which `SafeLoader` refuses. Manifests are small,
so the speed of the C loader does not matter.

**Resolution.** The subclass sets `yaml_implicit_resolvers = {}` and
registers with `add_implicit_resolver` the patterns of the core schema
(YAML 1.2.2 §10.3.2), each anchored with `\Z`, integers before floats:

| Tag | Pattern | First characters |
| --- | --- | --- |
| `null` | `null\|Null\|NULL\|~\|` (the empty scalar included) | `~ n N` and the empty string |
| `bool` | `true\|True\|TRUE\|false\|False\|FALSE` | `t T f F` |
| `int` | `[-+]?[0-9]+` | `- + 0`–`9` |
| `int` | `0o[0-7]+` | `0` |
| `int` | `0x[0-9a-fA-F]+` | `0` |
| `float` | `[-+]?(\.[0-9]+\|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?` | `- + .` `0`–`9` |
| `float` | `[-+]?(\.inf\|\.Inf\|\.INF)` | `- + .` |
| `float` | `\.nan\|\.NaN\|\.NAN` | `.` |

Every other plain scalar is a string. The loader needs its own
constructor of `int` as well, since PyYAML's follows YAML 1.1: it reads a
leading `0` as octal (`010` as 8, where the core schema reads 10), `0b`
as binary and `_` as a separator, and fails on `0o17`. The new one reads
`0o` in base 8, `0x` in base 16 and every other integer in base 10,
exactly. The
constructors of `null`, `bool`, `float` and `str` stay; `float(text)`
rounds a core float to the nearest double (`1.7976931348623158e308` gives
the largest double, `1e-400` gives `0.0`, `-1e-400` gives `-0.0`).

**Checks.**

| Refusal | Where |
| --- | --- |
| Malformed text, more than one document | PyYAML's scanner, parser and composer raise a `MarkedYAMLError` (`ScannerError`, `ParserError`, `ComposerError`). |
| Anchors and aliases | The composer's `compose_node` refuses an `AliasEvent` and any event whose `anchor` is set, before the node is built, so an alias is never expanded. |
| Duplicate keys | `construct_mapping` is replaced: it constructs the keys of the mapping node one by one and refuses a key it has already seen; `a` and `"a"` are the same key. It does not call `flatten_mapping`, so a merge key (`<<`) is never merged. |
| Keys that are not strings | The same `construct_mapping` refuses a key whose value is not a `str` (`1:`, `null:`, `[1]:`). |
| Values outside the JSON data model | `construct_object` refuses a node whose tag is not `str`, `int`, `float`, `bool`, `null`, `seq` or `map` of `tag:yaml.org,2002:`. This covers `!!timestamp`, `!!binary`, `!!set`, `!!omap`, `!!pairs`, `!!merge` and every unknown tag (`!foo`). `!!str 1` reads as `"1"`. |
| Non-finite floats | `construct_object` refuses a `float` that is not finite: `.inf`, `-.Inf`, `.nan`, `1e309`. |
| Unpaired surrogates | `construct_object` passes each string through `s.encode("utf-16-le", "surrogatepass").decode("utf-16-le")`, which joins a high surrogate followed by a low one into one character (`"\ud83d\ude00"` gives U+1F600) and refuses an unpaired one (`"\ud800"`, `"\udc00\ud800"`). |

Every refusal by the subclass raises `ConstructorError` with the offending
node's `start_mark`. The reader wraps every error as `ValueError` with the
line and column counted from one: a `MarkedYAMLError` from its
`problem_mark`; a `ReaderError` (a character YAML forbids, such as U+0001
or a lone surrogate written as itself) from its `position`, an index
into the text; and a `RecursionError`, raised when
collections nest deeper than Python's recursion limit allows (about 330
levels under the default limit), from the start mark of the node the
loader last began to compose or construct (the parser's own state may be
left mid-token by the error, so the next event cannot be asked for).
Columns count code points.
An empty text, or one of comments only, reads as null; `---` alone too.

Verified on 2026-11-17 with PyYAML 6.0.3 on Python 3.11: `k: no` →
`"no"`, `k: 1e-5` → `1e-05`, `k: 0o17` → `15`, `k: 017` → `17`,
`k: 010` → `10`, `k: 1_000` → `"1_000"`,
`k: 2026-11-17` → `"2026-11-17"`, `k: 0b101` → `"0b101"`, `k: =` → `"="`,
`<<: 1` → `{"<<": 1}`, `k: 2.0` → `2.0`, a 30-digit integer exact; and
refused: `.inf`, `.nan`, `1e309`, `a: 1` with `"a": 2`, `1: x`,
`a: &x 1`, `!!timestamp`, `!!set`, `!!omap`, `!foo`,
`!!python/name:os.system`, `"\ud800"`, two documents.

- **Fit.** The standard parser of the Python ecosystem reads every
  construct of canonical YAML as YAML 1.2 does once its resolver is the
  core schema; the format's own rules are a resolver table, one
  constructor and three overridden methods.
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
  package's exposure is one loader subclass on documented extension
  points.
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
  released; the reader is not exposed to it, since it refuses aliases in
  the composer and never merges.
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
It owns the core-schema resolver table, the integer constructor and the
checks, which are small and fixed by the specification and the format.

Beyond the constructs of canonical YAML, `SafeLoader` reads by YAML
1.1's grammar. Found in 6.0.3: it refuses a tab after `key:` or inside a
plain scalar (`a:\t1`, `k: a\tb`) and a line holding only a tab (`a: 1`,
a line of one tab, `b: 2` raises `ScannerError` at the tab), all of
which YAML 1.2 reads; and it takes U+0085, U+2028 and U+2029 written as
themselves for line breaks. Canonical YAML writes none of these: it
escapes the tab and those three characters. Such a text is read as
`SafeLoader` reads it, and a difference there is not a defect of the
format.

`CSafeLoader` is ruled out for one more reason: with libyaml's composer,
a sequence nested 3,000 deep ended the Python 3.11 process on Windows
without an exception, where `SafeLoader` raises `RecursionError`, which
the reader wraps.

The exit cost is the reader module. The review revisits the choice if
PyYAML releases a YAML 1.2 loader of its own, or a major version.

## Review date

2027-11-17, or when PyYAML 7 is released.
