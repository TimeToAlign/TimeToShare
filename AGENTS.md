# Contributor Rules

These rules apply to every contributor, human or automated.

## Repository layout

- `schema/`: the JSON Schema of the current version, the document
  `<version>/timetoshare.schema.json` describing the one manifest shape
  `{timetoshare, timelines, id?, name?, meta?, groups?, measure_maps?,
  resources?, flow_maps?, virtual_timelines?, "@context"?, statements?,
  provenance?, graphical?}`, and beside it
  `<version>/provenance.schema.json`, the provenance entry that
  statements, flow-control elements, FlowMaps and the MatchClaim table
  share, `<version>/tables.json`,
  the column types of the four table types of a package as data (the
  registry, the Extraction table, the MatchClaim table and the pre-parsed
  Projection table), and
  `<version>/package.schema.json`, the schema of a package's
  `package.yaml` `{timetoshare, manifests, tables, id?, name?, meta?}`;
  they are the format contract and source of truth.
- `docs/`: `drawing.md`, the specification of the style cascade, layout,
  the block of frames, cards and bands (the boxes) that draws every
  manifest, and SVG and TikZ writers; and `description.md`, the
  specification of statements (the subject, pairs and their values, the
  inline JSON-LD context, provenance and beliefs, the catalogue and
  validation). Both
  are part of the contract, and both packages ship them.
- `catalogue/`: `catalogue.yaml`, the catalogue of identifier systems,
  verbs and types that guides the writing of statements, and
  `catalogue.schema.json`, its JSON Schema; both packages ship the
  catalogue and read it alike, and the validators never consult it.
- `fixtures/`: generated manifests under `fixtures/<version>/` in
  canonical YAML, each in the complete form beside its minimal twin (the
  subdirectories `groups/`, `bundles/`, `statements/` and `flow/` sort
  them by content only), the expected flows of the manifests of flow
  control under `flow/` under
  `fixtures/flows/<version>/` (hand-authored, each beside the trace it was
  derived with), the expected RDF of the statement fixtures under
  `fixtures/rdf/<version>/` (canonical N-Quads, emitted), the table
  fixture under `fixtures/tables/<version>/` (a manifest naming its
  registry and its MatchClaim table, the Parquet files of the registry,
  the MatchClaim table and the pre-parsed Projection table, and the
  anchors and potential MatchStamps expected of them, emitted), the
  package fixtures under `fixtures/packages/<version>/` (`shared/`, two
  manifests sharing a registry, an Extraction table, a pre-parsed
  Projection table and a folder of MatchClaims, `acceptances/<case>/` and
  `rejections/<case>/`, each beside an `expected.yaml` of the rows read
  and the resolutions, or the problems the package check reports,
  emitted), the
  test vectors of minted IDs under `fixtures/ids/` (`minted_ids.json`,
  emitted, the values every tool that mints IDs checks its minter
  against), hand-authored rejection cases under `fixtures/rejections/<version>/`,
  hand-authored warning cases under `fixtures/warnings/<version>/`, the
  hand-authored acceptance table of own-axis values under
  `fixtures/acceptances/<version>/`, and the hand-authored cases of a
  manifest that breaks the schema twice under
  `fixtures/precedence/<version>/cases.yaml` (which problem is reported
  first; a case names a fixture and the members to set on it); every
  rejection and precedence case records the `message` of the two reference
  packages beside the `code` and `path` the format requires,
  hand-derived serialization cases under `fixtures/serializations/`
  (`cases/<name>/` with `canonical.yaml`, `pretty.json` and
  `rfc8785.json`, the last missing where that writer refuses the value;
  `readings/<name>.<ext>` beside `<name>.expected.yaml` and, optionally,
  `<name>.expected.rfc8785.json` (the RFC 8785 bytes of that value, no
  final line feed); `refusals/`;
  `refusals-writing/`; kept byte for byte by
  `fixtures/serializations/** -text` in `.gitattributes`), hand-written
  file-form cases under `fixtures/file_forms/` (`<name>.<ext>` beside the
  `<name>.expected.<ext>` written back in its inferred file form, kept
  byte for byte by `fixtures/file_forms/** -text`), and the
  drawings (`inputs.json`, in pretty JSON and naming the `.yaml`
  manifests, `figure.svg` and `figure.tex` per drawing; the hand-derived `figure.svg`
  files are listed with their arithmetic in `drawings/README.md`, everything
  else is emitted), and the hand-authored version cases under
  `fixtures/versions/` (`<case>/old/` and `<case>/new/`, two trees of
  manifests, and for the cases of tables the registry, the Extraction
  table and the pre-parsed Projection table they name, whose Parquet
  files are emitted, beside `expected.yaml`, the step and findings
  `tree_step` gives); see `fixtures/README.md`.
- `fonts/`: DejaVu Sans 2.37 and Noto Music 2.004, their licences, and the
  one table of advance-width metrics used by the drawing.
- `python/`: the PyPI package, tests, lockfile, and build configuration.
- `js/`: the npm package, generated TypeScript types, tests, and lockfile.
- `scripts/`: fixture emission (`emit_fixtures.py`, `emit_rdf.py`
  for the expected RDF of the statement fixtures, `emit_tables.py` for
  the table fixture, `emit_packages.py` for the package fixtures,
  `emit_versions.py` for the Parquet files of the version cases of
  tables, and `emit_id_vectors.py`, the reference
  implementation of the ID minter, for the vectors under `fixtures/ids/`),
  `convert_flow_control.py`, which rewrites manifest
  files whose flow control is written in the earlier form, font-metrics
  extraction, the check that every version declaration agrees, and
  `check_published.py`, which assembles the documents a release publishes
  and checks their `$id`s and references.
- `decisions/`: numbered MADR decision records.
- `.pre-commit-hooks.yaml`: the pre-commit hooks a dataset repository
  installs from this repository (the commit type, its check,
  `timetoshare validate` and `timetoshare registry --check`, which checks
  the registry's non-event rows against the manifests), and `setup.py`, an empty distribution at the
  root that exists only so that pre-commit's `pip install .` succeeds; each
  hook installs the package from `./python`.
- `.github/workflows/`: continuous integration and the release automation,
  which publishes both packages and, on both sites, every document of the
  schema version and the catalogue's schema; and
  `dataset-release-check.yml`, the reusable workflow a dataset repository's
  release workflow calls before release-please tags.

## Rules

- Work schema-first: change the versioned schema, then both packages, then
  fixtures.
- Add a numbered MADR in `decisions/` before adding a dependency. It must
  compare the dependency with writing the component here, record long-term
  maintenance cost, name the audited version, and include a review date.
- Do not add speculative options or dependencies.
- Package manifests declare compatible dependency ranges for published
  consumers. Lockfiles pin exact audited versions. A dependency may enter only
  after its selected release has been available for at least 14 days.
- Write tests README-first: update the relevant `tests/README.md` with what
  proves the behavior, then implement tests with exact expected values.
- Emit the manifests under `fixtures/<version>/` only through
  `scripts/emit_fixtures.py`, and their expected RDF under
  `fixtures/rdf/<version>/` only through `scripts/emit_rdf.py` after
  them, and the table fixture under `fixtures/tables/<version>/` only
  through `scripts/emit_tables.py`, whose expected anchors and MatchStamps
  are literal data written in the script, the package fixtures under
  `fixtures/packages/<version>/` only through `scripts/emit_packages.py`,
  whose rows, manifests, rows read and problems expected are literal data
  written in the script, the Parquet files of the version cases of tables
  under `fixtures/versions/` only through `scripts/emit_versions.py`,
  whose rows are literal data written in the script (their YAML files and
  `expected.yaml` are written by hand, their non-event parts by
  `write_non_event_rows`), and the vectors under
  `fixtures/ids/` only through `scripts/emit_id_vectors.py`; never
  hand-edit any of them.
  The manifests of flow control under `fixtures/<version>/flow/` are
  emitted like every other; only their expected flows under
  `fixtures/flows/<version>/` are derived by hand. The
  five scripts `emit_fixtures.py`, `emit_rdf.py`, `emit_tables.py`,
  `emit_packages.py` and `emit_versions.py` refuse to overwrite the files
  of a version whose `v<version>` tag exists. Emit
  the drawings under `fixtures/<version>/drawings/` only through
  TimeLineEditor's `emit-drawings` script, which never rewrites the
  hand-derived figures but compares them with its own output.
- `docs/drawing.md` pins the drawing. There is no drawing schema, and a drawing's JSON form is internal to
  an implementation. A rule a reader could not reproduce from the
  specification alone is a defect of the specification. This repository never
  depends on TimeLineEditor in code or packages; only the emitted drawing
  figures are produced by TimeLineEditor's writers (its `emit-drawings`
  script, writing into a TimeToShare checkout).
- Write every fixture, rejection case and warning case in canonical YAML
  with `dumps` of either package; a rejection or warning case about JSON
  text itself would be written in JSON, and none is at present. Write the
  catalogue `catalogue/catalogue.yaml` in canonical YAML with `dumps`,
  without comments (a note goes in a `note` field). In every such file
  object keys are sorted by code point
  at every depth, arrays are in canonical order, and floats are spelled as
  the README's "Serializations" specifies. Never keep a fixed list of
  key orders; key order is sorted order, and `canonical_order` covers only
  the order of array elements. In JavaScript, read files with `loads`,
  `parse`, `parseYaml` or `parseJson`, never `JSON.parse`, and write them with
  `dumps`, never `JSON.stringify`; the native methods lose the distinction
  between `2.0` and `2`, integers beyond 2^53, and the order of
  array-index keys.
- Derive the serialization cases under `fixtures/serializations/` by hand
  from the README's "Serializations", never with `dumps`, which they test.
  Both packages reproduce every text byte for byte. A case the README does
  not determine is a defect of the README.
- Author rejection cases under `fixtures/rejections/` by hand, one rule per
  case, warning cases under `fixtures/warnings/`, the acceptance table
  under `fixtures/acceptances/` and the cases of several problems under
  `fixtures/precedence/` by hand; the fixture script emits none of them.
- Regenerate `js/src/generated/` after changing the schema or font metrics.
  The generated TypeScript files belong in this repository.
- Regenerate `fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json` with
  `scripts/extract_font_metrics.py`; do not calculate or edit its advances by
  hand.
- Support the current version only. Both packages validate the current
  schema version and refuse every other; there are no migrations. The
  converter of flow control written in the earlier form,
  `scripts/convert_flow_control.py`, is therefore a script of this
  repository and no package code. A version
  a later one replaces lives in the git history at its tag and in its
  released packages.

## Commands

Run these commands from the stated directory.

| Directory | Command | Purpose |
| --- | --- | --- |
| repository root | `python3 scripts/check_versions.py` | Check version declarations agree. |
| repository root | `python3 scripts/check_published.py` | Check the `$id`s and references of the documents a release publishes. |
| repository root | `python scripts/emit_fixtures.py --timetoalign-commit "$(git -C /path/to/timetoalign rev-parse --short HEAD)"` | Emit and round-trip the fixtures with an environment containing timetoalign. |
| `python/` | `uv run python ../scripts/emit_rdf.py` | Write the expected RDF of the statement fixtures. |
| `python/` | `uv run python ../scripts/emit_tables.py` | Write the table fixture (needs pyarrow, a development dependency). |
| `python/` | `uv run python ../scripts/emit_packages.py` | Write the package fixtures (needs pyarrow, a development dependency). |
| `python/` | `uv run python ../scripts/emit_versions.py` | Write the Parquet files of the version cases of tables (needs pyarrow, a development dependency). |
| repository root | `python3 scripts/emit_id_vectors.py` | Write the test vectors of minted IDs (standard library only). |
| `python/` | `uv sync` | Synchronize Python dependencies. |
| `python/` | `uv run ruff check .` | Run Python lint checks. |
| `python/` | `uv run ruff format --check .` | Check Python formatting. |
| `python/` | `uv run pytest -q` | Run Python tests. |
| `python/` | `uv run python ../scripts/extract_font_metrics.py` | Regenerate the metrics table of the two bundled fonts. |
| `python/` | `uv build` | Build Python distributions. |
| `js/` | `pnpm install --frozen-lockfile` | Install locked JavaScript dependencies. |
| `js/` | `pnpm lint` | Run JavaScript lint checks. |
| `js/` | `pnpm typecheck` | Check TypeScript types. |
| `js/` | `pnpm test` | Run JavaScript tests. |
| `js/` | `pnpm generate` | Regenerate schema- and font-derived TypeScript files. |
| `js/` | `pnpm build` | Copy assets and build the npm package. |
