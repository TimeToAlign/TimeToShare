# 0017. Read and check the table types with pyarrow, as an optional extra

Date: 2026-11-21

## Context

A TimeToShare package keeps two tables beside its manifest: the MatchClaim
table (`match_claims.parquet`) and the Projections table
(`projections.parquet`). The format fixes their columns, the coordinate
cell, the provenance column and the rules a table must keep, and the
Python package offers `timetoshare.tables` to declare those columns, check
a table (alone or against its manifest), check the succession rule between
a table and the one written over it, and derive the AlignmentAnchors and
potential MatchStamps of a MatchClaim table for conformance.

That module must read Apache Parquet, the only form the tables take, and
hold the columns as Apache Arrow types: nested structs (the coordinate
cell, the anchor, the provenance entry with its list of beliefs), lists and
nullable columns, plus the file's schema metadata, which holds a provenance
shared by every row. The manifest validators need none of this, and most
users of the package read manifests alone.

## Considered options

- **pyarrow 25.0.0** (Apache Arrow). The reference implementation of Arrow
  and Parquet for Python: `pyarrow.Table`, `pyarrow.parquet.read_table` and
  `write_table`, struct and list types, schema metadata. The table form the
  library timetoalign writes is built with it already (`pyarrow>=14.0,<26`),
  so the tables a library user writes and the ones this package checks are
  read by the same implementation.
- **polars or pandas.** Both read Parquet, but through Arrow (polars through
  its own Arrow implementation, pandas through pyarrow or fastparquet); their
  data frames flatten or reinterpret nested structs and nulls, which the
  checks must see exactly as written. Each is a larger dependency than the
  one it would hide.
- **fastparquet.** Reads Parquet into pandas; nested types are partly
  supported and the column types are pandas', not Arrow's, so the
  declared schema could not be compared with a file's.
- **Write it here.** A Parquet reader (Thrift metadata, the encodings,
  the compression codecs, the Dremel nesting of definition and repetition
  levels) is several thousand lines and would have to agree with every
  writer the format's users have; out of proportion for a conformance
  module.

## Decision

Add pyarrow as the optional extra `tables` of the Python package,
`tables = ["pyarrow>=25.0.0,<26"]`, so `pip install "timetoshare[tables]"`
installs it and `pip install timetoshare` does not; pin it exactly in the
`dev` dependency group (`pyarrow==25.0.0`), where the tests of
`timetoshare.tables` run with it. `timetoshare.tables` imports pyarrow at
import time and, without it, raises an `ImportError` naming the extra; no
other module imports it. The JavaScript package has no table module.

- **Fit.** One implementation for the writers (timetoalign) and the
  checks; Arrow's types express the columns exactly as the format states
  them, nested and nullable, and the checks compare a file's schema by name
  and shape with the declared one.
- **Maintenance.** pyarrow is developed by the Apache Arrow project
  (https://github.com/apache/arrow) and releases a major version about every
  three months; the range admits the 25.x series, and a new major version is
  admitted only after a review of this record. The exposure is the table
  and schema types, `Table.from_pylist`, `to_pylist`, `select`,
  `replace_schema_metadata` and the Parquet reader and writer.
- **Writing it ourselves.** Out of proportion (see above).
- **Audited version.** pyarrow 25.0.0, uploaded to PyPI on 2026-07-10, 134
  days before this record; licence Apache-2.0; requires Python 3.10 or
  later and declares no runtime dependency; wheels for CPython 3.11 to
  3.14 on Linux, macOS and Windows. OSV lists no advisory for it (queried
  2026-11-21).
- **Range.** The extra declares `>=25.0.0,<26`; the `dev` group pins
  `==25.0.0` and `uv.lock` records it. Nothing is added to the package's
  `dependencies`.

Primary sources: https://arrow.apache.org/docs/python/,
https://parquet.apache.org/docs/, https://pypi.org/project/pyarrow/25.0.0/,
https://osv.dev/ (queried through its API).

## Consequences

Installing the extra adds one large binary package (about 50 MB unpacked on
Linux) and nothing else. The tests of the table types skip themselves where
pyarrow is absent, as the font extraction's do without fontTools. The exit
cost is the `timetoshare.tables` package, its two test files and the
fixture script `scripts/emit_tables.py`.

## Review date

2027-11-21, or when pyarrow 26 is released.
