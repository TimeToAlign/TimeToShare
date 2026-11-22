# 0003. Validate Python documents with jsonschema

Date: 2026-10-09

Amended 2026-11-22: a check compiled from the schema answers, before the
walk, whether `jsonschema` would find any error, so that a valid manifest
skips the walk; `jsonschema` remains the one source of every diagnostic.

## Context

The Python package must validate draft 2020-12 documents and return useful
locations for invalid values. Most documents it validates are valid, and on
a manifest of a few hundred kilobytes the `jsonschema` walk, which builds a
validator per node and resolves every reference on the way, takes seconds
to find that there is nothing to report.

## Considered options

- `jsonschema`.
- `fastjsonschema`.
- `check-jsonschema`.
- `jsonschema-rs`.
- Write the validator ourselves.

## Decision

Use `jsonschema` and `Draft202012Validator`. TimeToAlign maintainers benefit
from its public error paths and broad format support; its established project
reduces the bus factor. Primary sources: https://pypi.org/project/jsonschema/
and https://github.com/python-jsonschema/jsonschema/blob/main/COPYING.

`jsonschema` is the one source of every diagnostic: every code, path and
message the package reports for a schema violation comes from its walk. In
front of the walk, `timetoshare.validation.schema_check` compiles the
closed schema once into a check that answers one question only: would the
walk yield no error? Where it answers yes, the walk is skipped; where it
answers no, or declines to answer, the walk runs as it would without the
check. The check reports nothing itself and is no second validator: it
follows `jsonschema`'s own semantics keyword by keyword (its type checker,
its equality and uniqueness, `re.search` for patterns, the keys its
`unevaluatedProperties` counts).

Two things keep the check and the walk equal:

- the tests compare them (`python/tests/test_validator_parity.py`): on
  every fixture, rejection case and warning case, on large generated
  manifests, on seeded mutations of the fixtures and on cases built per
  schema definition, the check answers yes exactly where the walk yields
  nothing;
- the compiler refuses a schema it does not know: a keyword it does not
  compile, `format`, and every keyword that changes how a reference
  resolves (`$id` or `$schema` below the root, `$anchor`,
  `$dynamicAnchor`, `$vocabulary`) stop the compilation, so the schema
  cannot outgrow the check unnoticed.

## Consequences

`jsonschema` is a small runtime dependency with its documented transitive
dependencies and MIT licence. Replacing it later is isolated behind
`validate.py`; writing a validator ourselves would make schema conformance,
diagnostics, security updates and exit testing the maintainers'
responsibility, and the compiled check takes on none of these: it answers
for valid documents only, and an invalid one is reported by `jsonschema`.

The check is code the maintainers own. A schema change that uses a keyword
the compiler does not know (such as `patternProperties`,
`dependentSchemas`, `contains` or `format`) must extend the compiler first,
proven by the comparison above; until then the compilation fails, and with
it every validation. An upgrade of `jsonschema` that changes the semantics
of a compiled keyword shows in the same comparison.

## Review date

2027-10-09.
