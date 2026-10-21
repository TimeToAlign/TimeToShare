# 0010. One manifest shape in one schema document

Date: 2026-10-15

## Context

A manifest holds one timeline, a group of timelines, or several groups
beside ungrouped timelines. A schema could describe these as three file
kinds (a timeline file, a group file and a bundle file) in four documents:
one per kind and a shared `core`, referring to each other by relative
`$ref`. That design has four costs:

- A host that embeds a TimeToShare value in a file of its own and refers to
  our schema has to register every document; `core` cannot be resolved
  otherwise, in Python (jsonschema 4.26) or in JavaScript (Ajv 8.20).
- An editor changes the kind of a file whenever it names a timeline, extracts
  one from a bundle or merges two files, rewriting the root and every
  address.
- Styling (`graphical`) and identity need a rule per kind: a group file's
  display order is an array, a bundle's an object; a timeline file addresses
  every element by its bare id, the other kinds by `<root>/<id>`.
- A version recorded inside `meta` (`meta.schema_version`) keeps `meta`
  from being free.

Every real embedder also needs more than one timeline: a media axis with its
quarters axis, a score with its performances, a conversion map with the
sibling it targets.

## Considered options

- Three kinds in four documents.
- A single timeline object as a file of its own beside a bundle file holding
  several (two shapes).
- One document whose root is a `oneOf` of a bare timeline and a manifest of
  several (one document, two root forms).
- One shape: every manifest is `{timetoshare, timelines, id?, name?, meta?,
  groups?, measure_maps?, graphical?}`, in one document.
- One shape with references between manifests (`timelines` items that point
  into other files).

## Decision

Every TimeToShare manifest has one shape, described by one document per
version, `schema/<version>/timetoshare.schema.json`, whose root is `{"$ref":
"#/$defs/Manifest"}`. A single timeline is a manifest of one root, a group
a manifest with one group, and a manifest with an `id` or a `name` is named.
There is no file kind.

- **The version marker** is the top-level member `"timetoshare": "0.1.0"`
  (a `const`), read before anything else: a value without it is no
  TimeToShare manifest, a value with another version is refused with
  `UnsupportedVersionError`. `meta` is free. `$schema` is a known optional
  string for editors and is never read.
- **Public definitions.** `Manifest`, `Timeline`, `Group`, `Graphical`,
  `ConversionMap`, `Coordinate`, `Number`, `Fraction`, `TimeUnit`,
  `NumberType`, `Id`, `MeasureMap` and `MeasureMapRow` may be referred to by a host as
  `#/$defs/<name>`; within 0.1.x they change only by addition. A host may
  embed a whole manifest, marker included, or a bare `Timeline` and record the
  version itself. The document uses no `$anchor`: json-schema-to-typescript
  cannot follow one.
- **Open objects, unknown keys found in code.** Every object is open by
  omission: no object carries `additionalProperties: false` or
  `unevaluatedProperties: false`, and the document carries no custom
  keyword and no `x-` key, so every standard validator accepts an
  undeclared key and the document hides no signal that only our validators
  read. The root description states the policy. Our validators find
  undeclared keys in code: each builds in memory a copy of the document
  that closes every object definition with `type: object` and `properties`
  (never a `oneOf`/`anyOf` branch or an `if`/`then`/`else` arm, nor a base
  that an `allOf` shares) with `unevaluatedProperties: false`, walks the
  manifest with it, and reports each key that copy refuses through
  `unknownKeys` / `unknown_keys` as a warning, never as an error, so a
  misspelt optional key is visible rather than silently taken for its
  default. The one free object, `Meta`, says `additionalProperties: true`,
  and its keys are never reported.
- **Defaults.** Every key with a default declares it with `default`, and a
  reader supplies it; `complete` and `minimal` convert between the form that
  writes every such key and the form that leaves out those equal to their
  default.
- **Types.** The TypeScript types are generated from the one document with
  the generator's `additionalProperties: false`, so a misspelt key is a
  compile error while `meta` stays free; conditionals are left out of the
  view the generator reads.

The schema keeps only the current version; there are no migrations. A
version a later one replaces lives in the git history at its tag and in its
released packages.

## Rejected options

- **Three kinds in four documents**: the costs listed under Context.
- **Two shapes** (a timeline file and a bundle file): a timeline file holds
  one axis, but every embedder needs two or more; naming, extracting and
  merging still change the shape and rewrite addresses.
- **A two-form root (`oneOf`)**: a validator reports an unknown key or any
  other mistake as one opaque `oneOf` error over both forms (Ajv also
  reports a misleading missing `timelines`), and the walk that finds unknown
  keys cannot tell which form an object belongs to; both forms would be
  frozen at 1.0.
- **References between manifests now**: validation would become
  asynchronous, browsers cannot portably resolve a relative path, and the
  semantics of a reference would be frozen with the format. Ids are
  fragment-shaped already (`op35.json#region_1`), so a reference form
  can join `timelines` in a later 0.x version; it must be decided before 1.0.

## Consequences

Every reader has one shape and one address rule; naming, extracting and
merging are edits of one structure. A host registers one document. A key a
host declares beside a `$ref` into this document is reported as unknown by our
validators, not by the host's own. Our validators resolve no reference between
documents, so the Python package declares no direct `referencing`
dependency; `jsonschema` brings it in. The fixtures
of a version are one set of manifests; their subdirectories sort them by
content only. Moving to references later adds an item form to `timelines`, not
a document.

## Review date

2027-10-15.
