# 0015. Read the statement fixtures to RDF in the Python tests with PyLD

Date: 2026-11-19

## Context

A manifest carrying `statements` and `provenance` is a YAML-LD document:
its inline `@context` maps the statements to JSON-LD 1.1, so a JSON-LD
processor reads them as RDF triples and reads each provenance entry as an
RDF reification of one triple. The package itself never reads RDF; its
validators check the structure the format guarantees (declared prefixes,
references that resolve, entries that match pairs). Whether a valid
manifest really reads to the graph its authors meant can only be shown by a
processor that implements JSON-LD 1.1, independent of this package.

The Python test suite needs such a processor to assert, for each statement
fixture under `fixtures/0.2.0/statements/`, that:

1. its RDF, canonicalised by the RDF Dataset Canonicalization algorithm
   (RDFC-1.0, published as URDNA2015) and written as N-Quads, equals the
   expected file `fixtures/rdf/0.2.0/<name>.nq` byte for byte, the same bytes
   the JavaScript suite's processor gives;
2. no compact IRI leaks unexpanded, no key of the format gives a triple,
   no proposed or rejected pair is asserted, and each provenance entry
   gives one reified statement;
3. every fixture without statements yields the empty dataset;

and it must do so from the inline context alone, without fetching anything.
The processor is a development dependency: it is never installed with the
package and never runs in a user's program.

## Considered options

Each candidate was run against the four statement manifests (the Op. 106
work, a LayerIt recording, a DJ-set segment and a Carl Nielsen record, in
that order below) on 2026-11-18 and 2026-11-19, on Python 3.13.

- **PyLD 3.3.0** (Digital Bazaar). A JSON-LD 1.1 processor with
  `jsonld.to_rdf`, `jsonld.normalize` (URDNA2015) and N-Quads output, and a
  `documentLoader` option through which every fetch can be refused. Gives
  the same canonical graph as rdflib, jsonld.js 9 and python-yaml-ld on all
  four manifests (126, 115, 67 and 388 triples). Drops a key the context
  does not map silently, which is what the format relies on (its own keys
  stay out of the graph); it has no `safe` mode to turn that into an error,
  and needs none.
- **rdflib 7.6.** Parses JSON-LD into a graph and gives the same graph, but
  its canonical form (`rdflib.compare.to_canonical_graph`) is not RDFC-1.0
  and its N-Quads serialisation is not canonical, so the expected bytes
  could not be shared with the JavaScript suite; a comparison by graph
  isomorphism would be weaker than a comparison of bytes. It is also a much
  larger dependency (parsers, stores, SPARQL).
- **python-yaml-ld 1.1.22.** The one YAML-LD processor; it reads YAML
  itself and delegates to PyLD 2, so it adds a second YAML reader and an
  older processor to what PyLD gives. The package's own reader already
  turns a manifest into the JSON value a JSON-LD processor takes.
- **Write it here.** The JSON-LD 1.1 expansion and RDF algorithms (context
  processing, IRI expansion, `@nest`, `@reverse`, `@included`, `@list`,
  value objects, base resolution) and URDNA2015 are several thousand lines
  of specification each; a home-grown processor would test the manifests
  against our own reading of JSON-LD, which is what the test exists to
  avoid.

## Decision

Add PyLD 3.3.0 to the `dev` dependency group, pinned exactly
(`pyld==3.3.0`), and use only its documented functions `jsonld.to_rdf` and
`jsonld.normalize` with the options `base`
(`https://example.org/manifests/<name>.yaml`), `algorithm` (`URDNA2015`),
`format` (`application/n-quads`) and `documentLoader`, a function that
fails the test if it is ever called. The JavaScript suite uses jsonld.js
(decision 0016) and compares with the same files.

- **Fit.** PyLD and jsonld.js come from the same maintainers and implement
  the same specifications; both give the canonical N-Quads byte for byte
  (verified on the four manifests), so one expected file per fixture serves
  both suites.
- **Maintenance.** PyLD is maintained by Digital Bazaar, who edit the
  JSON-LD and RDF canonicalisation specifications, at
  https://github.com/digitalbazaar/pyld; 3.0.0 (2026-04-02), 3.1.0
  (2026-06-19), 3.2.0 (2026-08-17) and 3.3.0 (2026-09-02) followed 2.0.4
  (2024-02-16). The exposure is two functions and four options. A new
  release that changes canonical output would show as a difference in the
  expected bytes, which the JavaScript suite checks independently.
- **Writing it ourselves.** Out of proportion, and it would defeat the
  independence the test needs (see above).
- **Audited version.** PyLD 3.3.0, uploaded to PyPI on 2026-09-02, 78 days
  before this record; licence BSD-3-Clause; pure Python. Its runtime
  dependencies, locked as resolved on 2026-11-19 with no release younger
  than 14 days: lxml 6.1.3 (2026-09-02, BSD-3-Clause), cachetools 7.2.8
  (2026-10-31, MIT; 7.3.0 of 2026-11-05 was too recent) and frozendict
  2.5.1 (2026-10-30, LGPL-3.0-only, used by the tests only and never
  distributed with the package). OSV lists no advisory for any of the four
  versions (queried 2026-11-19).
- **Range.** The dependency group pins `pyld==3.3.0`; `uv.lock` pins the
  rest. Nothing is added to the package's `dependencies`.

Primary sources: https://www.w3.org/TR/json-ld11/,
https://www.w3.org/TR/json-ld11-api/, https://www.w3.org/TR/rdf-canon/,
https://www.w3.org/TR/yaml-ld/, https://pypi.org/project/PyLD/3.3.0/,
https://github.com/digitalbazaar/pyld, https://osv.dev/ (queried through
its API).

## Consequences

The development environment gains four packages, one with a C extension
(lxml, with wheels for every platform the suite runs on). The expected
N-Quads are written by the fixture script with the same processor and the
same options, and the tests read them back; a difference between PyLD and
jsonld.js would surface as a failure of one of the two suites. The exit
cost is `tests/test_rdf.py` and the script writing the expected files.

## Review date

2027-11-19, or when PyLD 4 is released.
