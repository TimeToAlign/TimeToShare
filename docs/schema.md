# Schema

The schema of version {{ schema_version }} is four documents in
`schema/{{ schema_version }}/`, the contract the two packages validate
(README, [The schema document](overview.md#the-schema-document)):

- {{ manifest_schema }}: the manifest, a JSON Schema 2020-12 document
  describing the one manifest shape;
- {{ provenance_schema }}: the provenance entry that statements,
  flow-control elements, FlowMaps and the MatchClaim table share;
- {{ tables_schema }}: the column types of the package's three table
  types (the registry, the Parse table and the MatchClaim table), as data;
- {{ package_schema }}: the `package.yaml` of a package, which lists its
  manifests and the tables they share (README,
  [Packages](overview.md#packages)).

The catalogue of identifier systems, verbs and types that guides the
writing of statements ([Describing a manifest](description.md), section
10) is {download}`catalogue.yaml <../catalogue/catalogue.yaml>`, and its
JSON Schema is {download}`catalogue.schema.json
<../catalogue/catalogue.schema.json>`.

The files linked here are the documents of this version of the site. A
release also serves each document at its `$id`,
`https://timetoalign.github.io/timetoshare/<version>/<file>`.
