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
3. refuse anchors and aliases, explicit tags (the non-specific `!`
   included), more than one document, duplicate keys, keys that are not
   strings, `.nan` and the infinities, and floats beyond a double;
4. construct no objects from the text (safe loading only);
5. report the line and column of malformed text;
6. ignore comments;
7. run on every Python the package supports (`requires-python >= 3.11`)
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

The package creates `YAML(typ="safe", pure=True)` and iterates
`parse(text)`. Its own builder turns the events into the manifest value
with an explicit stack, so nesting depth is bounded by memory, not by
Python's recursion limit. Each requirement is met as follows:

| Requirement | How |
| --- | --- |
| Core schema | A plain scalar (`event.style is None`) is resolved by the package against the patterns of YAML 1.2.2 §10.3.2; a quoted scalar or block scalar (`style` one of `'`, `"`, `\|`, `>`) is a string; an empty plain scalar is null. |
| Exact integers | `int` on the matched text in base 10, 8 (`0o`) or 16 (`0x`). |
| Integer and float told apart | By which core pattern matched; `2.0` is a float, `2` an integer. |
| Anchors and aliases | Refused at an event whose `anchor` is not `None`, and at every `AliasEvent`; an alias is never expanded. |
| Explicit tags | Refused at an event whose `tag` is not `None`: `!foo`, `!!str` and the non-specific `!` alike. |
| One document | Refused at a second `DocumentStartEvent`. |
| Duplicate keys | Refused while building a mapping; keys are strings, so `a` and `"a"` are the same key. |
| Keys that are not strings | Refused when a key is a mapping or sequence, or a plain scalar that resolves to null, a boolean or a number. |
| `.nan` and infinities | Refused when the infinity or not-a-number pattern matches. |
| Floats beyond a double | Refused when `float(text)` is not finite (`1e400`). |
| Safe loading | Events construct nothing; no constructor runs. |
| Positions | A malformed text raises `ruamel.yaml.error.MarkedYAMLError` (`ScannerError`, `ParserError`) with `problem_mark.line` and `problem_mark.column`, counted from zero; a refusal by the package reports the event's `start_mark`. |
| Comments | Discarded by the scanner of the safe loader. |

The resolver and builder are small (nine patterns and one loop over
events); the grammar, the hard part, stays in the library.

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
comparison. A tab after `key:`, valid YAML 1.2, raises a `ScannerError` in
0.19.1. Some valid hand-written YAML is therefore refused with a position,
and a few rare constructs may be read differently from the specification;
the canonical layout and the common hand-written styles are unaffected.

The package owns the core-schema resolution, which is fixed by the
specification and small, and the refusals, which are the format's own rules
in any case. The exit cost is low: PyYAML's `yaml.parse` emits events of the
same classes and fields, so a replacement parser changes the call that
produces events and nothing else. The review revisits the choice if a fully
conformant parser, such as the libfyaml binding, has a stable release.

## Review date

2027-11-17.
