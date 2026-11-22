# 0003. Validate Python documents with jsonschema behind a jsonschema-rs gate

Date: 2026-10-09

Amended 2026-11-22: `jsonschema-rs` answers, before the `jsonschema` walk,
whether a document is valid, so that a valid manifest, one with unknown
keys included, skips the walk; `jsonschema` remains the one source of every
diagnostic. This replaces a check compiled from the schema by the package
itself.

## Context

The Python package must validate draft 2020-12 documents and return useful
locations for invalid values. Most documents it validates are valid, and on
a manifest of a few hundred kilobytes the `jsonschema` walk, which builds a
validator per node and resolves every reference on the way, takes seconds
to find that there is nothing to report. Unknown keys are found against an
in-memory copy of the schema that closes every object, so a manifest with
one unknown key fails that copy and, without a faster answer, is walked
whole.

## Considered options

- `jsonschema` alone.
- `jsonschema` behind a check the package compiles from the schema itself.
- `jsonschema` behind `jsonschema-rs`.
- `fastjsonschema`.
- `check-jsonschema`.
- Write the validator ourselves.

## Decision

Use `jsonschema` and `Draft202012Validator` for every diagnostic, and
`jsonschema-rs` (`Draft202012Validator`) as a gate in front of it.

`jsonschema` is the one source of every diagnostic: every code, path and
message the package reports for a schema violation comes from its walk.
Its public error paths and established project keep the messages stable
for the two packages' shared rejection cases. Primary sources:
https://pypi.org/project/jsonschema/ and
https://github.com/python-jsonschema/jsonschema/blob/main/COPYING.

Every schema node the package checks (the closed document, `Timestamp`,
and each member that `statement_problems` and `matchstamp_problems` check
alone) is compiled by both libraries from the very same schema. The gate
answers only for plain JSON data whose every float is finite (exact `dict`,
`list`, `str`, `int`, `float`, `bool`, `None`): `jsonschema-rs` reads a
tuple as an array and `NaN` as `null`, and refuses a key that is no string.
Where it finds no error, or only errors that an undeclared key alone causes
(from which it lists the unknown keys), the walk is skipped; where it finds
any other error, raises, or is not asked, the walk runs and reports. The
gate reports nothing itself and is no second source of diagnostics.

Why `jsonschema-rs`: it implements the whole of draft 2020-12 (it is listed
compliant by Bowtie), so every keyword the schema may use later costs no
code here, only a rerun of the comparison below; it answers a valid
300-timeline manifest in about 1 ms and the whole validation takes about
18 ms (26 ms with the former compiled check, about 900 ms with
`jsonschema` alone), and it lists unknown keys in milliseconds where the
walk took about one second per 300 timelines. The compiled check it
replaces was about 700 lines the maintainers owned, and every new keyword
had to be compiled and proven before the schema could use it.

Audited version: `jsonschema-rs` 0.60.3 (2026-10-27; MIT; abi3 wheels for
CPython 3.10 and later on Linux glibc and musl, macOS and Windows, x86 and
ARM, no pure-Python fallback: elsewhere the sdist needs a Rust toolchain;
one principal maintainer, frequent 0.x releases). Primary sources:
https://pypi.org/project/jsonschema-rs/ and
https://github.com/Stranger6667/jsonschema. Against the walk of the same
schema it gave no false acceptance on 1,368 plain JSON inputs (every
fixture, rejection and warning case, large manifests, 480 seeded mutations
and 514 per-definition cases) and refused all 92 rejection cases the
schema refuses. Its known differences are harmless to the gate: a
`pattern` ending in `$` does not match before a final line feed (as in
ECMA 262, unlike Python's `re`), so it refuses where the walk accepts and
the walk decides; non-finite floats and non-JSON Python values never reach
it.

Two things keep the gate and the walk equal:

- the tests compare them (`python/tests/test_validator_parity.py`): on
  every fixture, rejection case and warning case, on large generated
  manifests, on seeded mutations of the fixtures and on cases built per
  schema definition, the gate answers "valid" exactly where the walk finds
  nothing to report, lists exactly the walk's unknown keys, and the
  outcome of every entry point equals the outcome with the gate removed;
- the dependency is pinned to one minor version (`>=0.60.3,<0.61` in the
  package, the exact version in `uv.lock`). Each minor bump reruns that
  comparison and an audit of the library's answers against the walk
  before the lockfile moves.

## Consequences

`jsonschema` stays a small runtime dependency with its documented
transitive dependencies and MIT licence. `jsonschema-rs` adds a compiled
wheel of about 6 MB (15 MB installed) and no transitive dependency; a
platform without a wheel needs Rust to install the package. Every consumer
of the Python package inherits it.

A release of `jsonschema-rs` that changes an answer shows in the
comparison; until the comparison passes, the lockfile keeps the audited
version. Should the library be abandoned, removing the gate changes no
outcome, only the time (the walk then runs on every document); writing a
validator ourselves would make schema conformance, diagnostics, security
updates and exit testing the maintainers' responsibility.

## Review date

2027-10-09.
