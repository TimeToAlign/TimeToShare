# 0013. Read YAML in Python with ruamel.yaml's event stream

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
2. keep integers exact at any size;
3. read a float literal as the nearest double, underflow to zero and
   subnormals included, and refuse one that rounds to an infinity
   (`1e309`); `1.7976931348623158e308` is the largest double;
4. refuse anchors and aliases, explicit tags (the non-specific `!`
   included), a text that holds no document, more than one document,
   every directive other than `%YAML 1.2`, duplicate keys, keys that are
   not strings, an implicit key whose span from its first character to
   its `:` exceeds 1024 characters (YAML's own limit, counted in code
   points), and `.nan` and the infinities;
5. read a surrogate pair written as two `\u` escapes as one character, and
   refuse a lone surrogate, whether written as itself or through an
   escape;
6. refuse every character written as itself, in a scalar or a comment,
   outside YAML's printable set, U+0085, U+2028 and U+2029, and every
   U+FEFF but the one of requirement 7; the escapes stay allowed;
7. remove exactly one U+FEFF (byte order mark) at position 0;
8. construct no objects from the text (safe loading only);
9. raise `ValueError` with the line and column for malformed text and for
   every refusal, whatever the library raises;
10. ignore comments;
11. run on every Python the package supports (`requires-python >= 3.11`)
   as pure Python or with wheels for all major platforms, under a licence
   compatible with MIT.

PyYAML, the most widely installed YAML library for Python, describes itself
as "a complete YAML 1.1 parser" (https://pypi.org/project/PyYAML/). Under
YAML 1.1, `no` is a boolean (https://yaml.org/type/bool.html) and a float
needs a decimal point (https://yaml.org/type/float.html), so
`yaml.safe_load("k: no")` gives `False` and `yaml.safe_load("k: 1e-05")`
the string `"1e-05"`; both contradict requirement 1.

## Considered options

Each candidate was installed in a clean environment on Python 3.11 and run
against the requirements on 2026-11-17.

- **ruamel.yaml 0.19.1.** Pure Python, YAML 1.2 by declaration. Its
  resolver is not the core schema, with or without `version=(1, 2)`: it
  reads `2026-11-17` as a `datetime.date`, `1_000` and `0b101` as
  integers, and refuses `=` and `<<` as unknown tags, where the core schema
  gives five strings. Its constructor expands aliases. Its event stream,
  `YAML(typ="safe", pure=True).parse(text)`, offers everything the
  requirements need: every event carries its `anchor`, `tag`, `style` and
  `start_mark`; an alias arrives as an `AliasEvent` and is never expanded;
  each document opens with a `DocumentStartEvent`; comments are discarded.
- **PyYAML 6.0.3.** YAML 1.1 (see Context). Its event stream has the same
  classes and fields as ruamel.yaml's and could carry a resolver of the
  package's own, but its scanner targets YAML 1.1 by declaration, and in
  the YAML test-suite matrix it passes fewer tests than ruamel.yaml (329
  against 345 of 402 in the event comparison).
- **strictyaml 1.7.3.** Vendors an old ruamel.yaml. It refuses flow style
  (`k: [1, 2]` raises `FlowMappingDisallowed`), which the canonical layout
  writes for every sequence of scalars, and reads every scalar as a string
  unless the caller supplies a schema (`2.0` and `2` both give a string).
  Depends on `python-dateutil`; last release 2023-03-10.
- **yaml-rs 0.1.6** (Rust, Unlicense, 2026-07-07). Returns values only, with
  no events or nodes: it expands aliases (`b: *x` gives the anchored value),
  drops explicit tags (`!foo 1` gives `"1"`) and reads dates and `1_000`
  as ruamel.yaml's resolver does, so neither aliases nor tags can be
  refused.
- **ryaml 0.5.1.** Wraps the Rust `serde-yaml` and states that it implements
  YAML 1.1.
- **The Python binding of libfyaml.** libfyaml passes the whole YAML test
  suite, but its binding exists only as release candidate 1.0.0rc2,
  uploaded 2026-11-11, with no stable release; it fails the 14-day rule and
  ships no musllinux wheels.
- **Write the reader here.** A full YAML 1.2 reader is large: ruamel.yaml's
  reader, scanner, parser, tokens, events and errors are about 4,500
  lines, and the parse and compose stages of the JavaScript `yaml` package
  about 3,900. A reader restricted to the canonical layout would refuse the
  hand-edited YAML the format accepts.

## Decision

Use ruamel.yaml as the parser only, through its event stream. The package
resolves every scalar and builds the value itself; ruamel.yaml's resolver,
constructors and emitter are not used.

Before parsing, the package drops a single leading U+FEFF and scans the
text twice: for the characters it refuses (see Characters) and for
directives. It then creates `YAML(typ="safe", pure=True)`
and iterates `parse(text)`. Its own builder turns the events into the
manifest value with an explicit stack, so nesting depth is bounded by
memory, not by Python's recursion limit. Each requirement is met as
follows:

| Requirement | How |
| --- | --- |
| Core schema | A plain scalar (`event.style is None`) is resolved by the package against the patterns of YAML 1.2.2 §10.3.2; a quoted scalar or block scalar (`style` one of `'`, `"`, `\|`, `>`) is a string; an empty plain scalar is null. |
| Exact integers | `int` on the matched text in base 10, 8 (`0o`) or 16 (`0x`). |
| Integer and float told apart | By which core pattern matched; `2.0` is a float, `2` an integer. |
| Float range | A float is `float(text)`, which rounds correctly to the nearest double: `1.7976931348623158e308` gives the largest double, `1e-400` gives `0.0`, `2.5e-324` the smallest subnormal. Refused when the result is not finite (`1e309`, `-1e309`, `1.7976931348623159e308`). |
| `.nan` and infinities | Refused when the infinity or not-a-number pattern matches. |
| Anchors and aliases | Refused at an event whose `anchor` is not `None`, and at every `AliasEvent`; an alias is never expanded. |
| Explicit tags | Refused at an event whose `tag` is not `None`: `!foo`, `!!str` and the non-specific `!` alike. |
| No document | Refused when the stream ends without a `DocumentStartEvent`: an empty text, or one of whitespace and comments only. `---` alone yields a `DocumentStartEvent` and an empty plain scalar, read as null. `...` alone, a stream that holds no document, raises `ParserError`. |
| One document | Refused at a second `DocumentStartEvent`. |
| Directives | By the package's own scan, before parsing: it reads the lines up to the first that is neither blank, a comment nor a directive (a line beginning with `%`), and refuses at its line every directive other than a single `%YAML 1.2`. The events do not suffice: `DocumentStartEvent.version` shows `(1, 1)` and `tags` a `%TAG` handle, but a reserved directive (`%FOO bar`) leaves no trace, and `%YAML 1.0` or `%YAML 1.3` raises a bare `AssertionError`. A directive before a later document meets the refusal of a second document, or that `AssertionError` (see Positions). |
| Duplicate keys | Refused while building a mapping; keys are strings, so `a` and `"a"` are the same key. |
| Keys that are not strings | Refused when a key is a mapping or sequence, or a plain scalar that resolves to null, a boolean or a number. |
| Implicit key over 1024 characters | By the scanner, for every implicit key: of a block mapping, of a pair in a flow sequence and of a flow mapping. ruamel.yaml drops a possible implicit key once its `:` lies more than 1024 characters after the key's first character, counted in code points over the text as written, so quotes, escapes and spaces before the `:` count; it then raises `ScannerError` ("mapping values are not allowed here") at the `:` in a block mapping, and `ParserError` in a flow sequence or a flow mapping. `a`×1024 `: 1`, `{` `a`×1024 `: 1}` and 1024 characters outside the Basic Multilingual Plane are read; `a`×1025 `: 1`, `a`×1024 ` : 1`, `{` `a`×1025 `: 1}` and `"` `a`×1023 `": 1` are refused; a double-quoted key of 511 escapes `\t` (a span of 1024) is read, one of 512 is refused. An explicit key (`? `) has no limit. The package needs no check of its own. |
| Surrogates | ruamel.yaml decodes `"\ud83d\ude00"` to two lone surrogates. The builder passes every string through `s.encode("utf-16-le", "surrogatepass").decode("utf-16-le")`, which joins a high surrogate followed by a low one into one character (U+1F600) and raises `UnicodeDecodeError` at an unpaired one (`"\ud800"`, `"\U0000d800"`, `"\udc00\ud800"`), refused at the event's `start_mark`. A lone surrogate written as itself is refused by ruamel.yaml's reader, as `ReaderError`, before any event, in a comment too. |
| Characters | The package scans the text before parsing and refuses, at its position, the first character written as itself, in a scalar or a comment, that lies outside YAML's printable set (C0 controls other than tab, LF and CR; U+007F to U+009F; U+FFFE; U+FFFF; surrogates) or is U+0085, U+2028, U+2029 or a U+FEFF other than the one removed at position 0. YAML 1.2 reads U+FEFF as content in places, in a quoted or block scalar for one, and ruamel.yaml reads it as content wherever it stands, in a plain scalar, a comment and a key too (a second leading U+FEFF becomes part of the first key); the format refuses it everywhere. YAML 1.2 reads U+0085, U+2028 and U+2029 as content, but ruamel.yaml takes each for a line break, as YAML 1.1 did, and misreads silently: in a plain or quoted scalar U+0085 folds to a space (`k: a`U+0085`b` gives `"a b"`), in a block scalar it ends the line. The escapes `\N`, `\L` and `\P` give the characters, as they should. |
| Leading U+FEFF | Exactly one U+FEFF at position 0 is removed by the package before dispatch. Any other U+FEFF is refused by the scan of the Characters row: a second leading one makes the text YAML by the dispatch rule, and the scan refuses it at position 0. |
| Safe loading | Events construct nothing; no constructor runs. |
| Positions | Every error ruamel.yaml raises is wrapped as `ValueError` with a position: `MarkedYAMLError` (`ScannerError`, `ParserError`) with `problem_mark.line` and `problem_mark.column`, counted from zero; `ReaderError` (a character YAML forbids, such as U+0001 or a lone surrogate), which is no `MarkedYAMLError` and carries `position`, the index in the text, turned into line and column by the package; and the `AssertionError` of `%YAML 1.0` and `%YAML 1.3`, which carries no mark and is reported at the end mark of the last event read. A refusal by the package reports the event's `start_mark`, or the index its scans found. |
| Comments | Discarded by the scanner of the safe loader. |

The resolver, the builder and the two scans are small (nine patterns, one
loop over events and two loops over characters and lines); the grammar,
the hard part, stays in the library.

- **Fit.** Of the candidates, ruamel.yaml is the only stable, pure-Python
  YAML 1.2 parser that exposes anchors, tags, styles and positions before
  any value is built. The value-level libraries (yaml-rs, strictyaml) lose
  exactly what the format must refuse.
- **Maintenance.** ruamel.yaml has one maintainer, Anthon van der Neut, who
  has published it since 2014 from a Mercurial repository on SourceForge.
  0.18 releases came every one to three months in 2023 to 2025; 0.19.0
  followed on 2025-12-31 and 0.19.1 on 2026-01-02, with none since. Minor
  releases of the 0.x line change the API: 0.18 turned the module-level
  functions (`load`, `parse` and others) into errors, and 0.19.0 broke
  installations through a new C-extension build that 0.19.1 made optional.
  The project description warns that PEP 625 may force a change of the
  project name. The bus factor is one. The package's exposure is small:
  one constructor call, `parse`, and the event classes.
- **Writing it ourselves.** Owning a YAML 1.2 grammar of several thousand
  lines and its edge cases is out of proportion to reading manifests.
- **Audited version.** ruamel.yaml 0.19.1, uploaded to PyPI on 2026-01-02
  (`ruamel_yaml-0.19.1-py3-none-any.whl`), 319 days before this record, so
  the 14-day rule holds. Licence MIT. `requires-python >= 3.9`. No runtime
  dependencies: the C extensions `ruamel.yaml.clib` and `ruamel.yaml.clibz`
  are optional extras (`oldlibyaml`, `libyaml`) that the package neither
  needs nor installs. OSV lists no advisory for ruamel.yaml (queried
  2026-11-17).
- **Range.** `pyproject.toml` declares `ruamel.yaml>=0.19.1,<0.20`, because
  minor releases of the 0.x line remove API; the lockfile pins 0.19.1.

Primary sources: https://yaml.org/spec/1.2.2/ (§10.3, Core Schema),
https://pypi.org/project/ruamel.yaml/0.19.1/,
https://yaml.dev/doc/ruamel.yaml,
https://sourceforge.net/p/ruamel-yaml/code/ci/default/tree/,
https://pypi.org/project/PyYAML/, https://yaml.org/type/bool.html,
https://yaml.org/type/float.html, https://pypi.org/project/strictyaml/,
https://pypi.org/project/yaml-rs/, https://pypi.org/project/ryaml/,
https://pypi.org/project/libfyaml/, https://matrix.yaml.info/,
https://osv.dev/ (queried through its API).

## Consequences

ruamel.yaml's parser is not fully conformant: in the YAML test-suite matrix
(https://matrix.yaml.info/, test data of 2022-01-17, processor versions not
stated) it passes 265 of 308 valid and 80 of 94 invalid cases in the event
comparison. The defects found in 0.19.1 are of two kinds, and the package
lets none of them misread a text.

Valid YAML 1.2 that ruamel.yaml refuses, with a position, as `ScannerError`
or `ParserError`: a tab where YAML allows separating white space, as after
`key:` (`a:\t1`, `a: \t1`), after `-` (`-\t1`, `- \t1`), before a comment
(`a: 1\t# c`, `a: 1 \t# c`) or on a line of its own; a tab inside a plain
scalar (`k: a\tb`), which YAML 1.2 reads as content; and an implicit key
of a flow mapping that spans lines (`{a\n b: 1}`). The package passes these
refusals on as `ValueError` with the position ruamel.yaml gives. They are
known defects of the dependency: the package's tests mark them as known
issues, so that a release of ruamel.yaml that reads them shows.

Valid YAML 1.2 that ruamel.yaml would read differently from the
specification, without an error: a literal U+0085 (see the table), and a
literal U+2028 or U+2029, which it also takes for a line break in some
places: `k: |\n  a`U+2028`\n` loses the final line feed, `k: 'a`U+2029` '`
the trailing space, and a plain or double-quoted scalar folded onto a line
that begins with U+2028 the space of the fold. The package refuses all
three characters by the scan of the table's Characters row, as a rule of
the format that the TypeScript reader applies too, so such a text is
refused with a position, never misread. The canonical layout and the common hand-written styles are
unaffected.

The package owns the core-schema resolution, which is fixed by the
specification and small, the refusals, which are the format's own rules
in any case, and the two scans, which read the text, not the library. The
exit cost is low: PyYAML's `yaml.parse` emits events of the same classes
and fields, so a replacement parser changes the call that produces events
and the errors it wraps, and nothing else. The review revisits the choice if a fully
conformant parser, such as the libfyaml binding, has a stable release.

## Review date

2027-11-17.
