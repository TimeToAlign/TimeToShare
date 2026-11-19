# 0016. Test the RDF of statements in TypeScript with jsonld.js

Date: 2026-11-19

## Context

A manifest carrying `statements` is a YAML-LD document: its inline
`@context` maps the format's terms, and every pair and annotation reads as
RDF. Whether the context does what the format says can only be proved by a
JSON-LD processor reading the statement fixtures: the triples a fixture
states, that a proposed or rejected pair is never stated, that every compact
IRI is expanded and that a manifest without statements states nothing. Both
packages assert this against the same expected files, the canonical N-Quads
(RDFC-1.0) of each statement fixture, so the processor must:

1. implement JSON-LD 1.1 to RDF, including `@nest`, `@included`, `@reverse`,
   `@list`, `@type: @vocab` and value objects, as the format's context uses
   them;
2. canonicalize the dataset with RDFC-1.0 and write it as N-Quads, byte for
   byte what PyLD writes for the Python package;
3. take a base IRI, drop keys that expand to nothing without an error
   (the format's own keys, such as `unit` and `length`, are dropped by
   design) and accept a document loader that refuses every fetch;
4. run on the Node versions of the package's `engines` (`>=22.18.0`) and
   import into an ES module, under a licence compatible with MIT.

The processor is a test oracle only: no published code imports it, so it is
a development dependency.

## Considered options

- **`jsonld` 9.0.0** (jsonld.js, Digital Bazaar). The reference
  implementation by editors of the JSON-LD 1.1 specifications; `canonize`
  with `canonizeOptions: {algorithm: "RDFC-1.0"}` gives canonical N-Quads
  through `rdf-canonize` 5.0.0, by the same maintainers. Options `base`,
  `safe: false` and `documentLoader` meet requirement 3. Run on 2026-11-19
  against a statement manifest: annotations as reified statements, element
  IDs as fragments of the base, no triple for a proposed pair.
- **`jsonld-streaming-parser` 5.0.2** (Comunica) with `rdf-canonize`. A
  streaming JSON-LD to RDF/JS parser; canonicalization and N-Quads writing
  would be assembled from two more packages, and its results are not the
  reference implementation's.
- **Write it ourselves.** A JSON-LD 1.1 expansion and RDF conversion with
  the context features above, plus RDFC-1.0, is several thousand lines and
  a standard's worth of edge cases; as a test oracle it would prove only
  that it agrees with itself.

## Decision

Use `jsonld` 9.0.0 as a development dependency in `js/tests/rdf.test.ts`,
with the ambient declaration `js/tests/jsonld.d.ts` for the one function
the tests call (`canonize`); the package ships no type declarations. The
tests hand it a plain value (every `JsonFloat` and `bigint` a number, which
statements never hold beyond integers), the base
`https://example.org/manifests/<name>.yaml`, `safe: false` and a loader
that throws for every URL.

- **Fit.** jsonld.js passes the W3C JSON-LD 1.1 test suite's toRdf tests
  (its own test runner runs them) and is the processor PyLD was ported
  from, so the two packages compare the output of sibling implementations
  of one algorithm; both read the statement fixtures to the same canonical
  N-Quads.
- **Maintenance.** Published by Digital Bazaar since 2011, five maintainers
  on npm; 8.3.3 on 2024-12-21, 9.0.0 on 2025-11-21. Its dependencies:
  `rdf-canonize` 5.0.0 (2025-11-20), `canonicalize` 2.1.0 (2025-03-18),
  `lru-cache` 6.0.0 (2020-07-11) and `@digitalbazaar/http-client` 4.4.0 (2026-08-06),
  which brings `ky` 1.14.3 (2026-01-25) and `undici` 6.29.1 (2026-10-15) for
  fetching, which the tests never do. OSV lists no advisory for any of these
  versions (queried 2026-11-19); `undici` has many advisories, every one
  fixed at or before 6.29.1 for the 6.x line.
- **Audited version.** `jsonld` 9.0.0, published to npm on 2025-11-21,
  far beyond 14 days before this record. Licence BSD-3-Clause; 2.1 MB
  unpacked; `engines` `node >= 18`. Node resolves its CommonJS build, whose
  default export an ES module imports.
- **Range.** `package.json` declares `jsonld` `9.0.0` among the
  `devDependencies`, pinned like the other development tools; the lockfile
  pins it and every transitive version.

Primary sources: https://www.w3.org/TR/json-ld11-api/,
https://www.w3.org/TR/rdf-canon/, https://github.com/digitalbazaar/jsonld.js,
https://github.com/digitalbazaar/rdf-canonize,
https://registry.npmjs.org/jsonld,
https://github.com/rubensworks/jsonld-streaming-parser.js,
https://osv.dev/ (queried through its API).

## Consequences

The npm package gains no runtime dependency. The RDF test compares bytes
with the expected N-Quads the Python package's processor writes, so a
difference between jsonld.js and PyLD on a fixture fails one of the two
suites and has to be decided in the fixture or the format, not in a test.
The exit cost is one test file and its declaration.

## Review date

2027-11-19, or when jsonld.js 10 is released.
