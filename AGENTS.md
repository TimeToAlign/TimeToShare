# Contributor Rules

These rules apply to every contributor, human or automated.

## Repository layout

- `schema/`: the JSON Schema of the current version, one document
  `<version>/timetoshare.schema.json` describing the one manifest shape
  `{timetoshare, timelines, id?, name?, meta?, groups?, measure_maps?,
  schemes?, links?, graphical?}`; it is the format contract and source of
  truth.
- `docs/`: `drawing.md`, the specification of the style cascade, layout,
  the block of frames, cards and bands (the boxes) that draws every
  manifest, and SVG and TikZ writers; and `description.md`, the
  specification of the description layer (links, schemes, records,
  assertions, parts and absence, the registry of identifier schemes and
  validation). Both are part of the contract, and both packages ship
  them.
- `registry/`: `schemes.json`, the registry of identifier schemes that
  turns catalogue addresses into links, written in pretty JSON with
  `dumps`; both packages ship it and read it alike, and the validators
  never consult it.
- `fixtures/`: generated manifests under `fixtures/<version>/` in
  canonical YAML, each in the complete form beside its minimal twin (the
  subdirectories `groups/` and `bundles/` sort them by content only),
  hand-authored rejection cases under `fixtures/rejections/<version>/`,
  hand-authored warning cases under `fixtures/warnings/<version>/`,
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
  else is emitted); see `fixtures/README.md`.
- `fonts/`: DejaVu Sans 2.37 and Noto Music 2.004, their licences, and the
  one table of advance-width metrics used by the drawing.
- `python/`: the PyPI package, tests, lockfile, and build configuration.
- `js/`: the npm package, generated TypeScript types, tests, and lockfile.
- `scripts/`: fixture emission, font-metrics extraction, and the check
  that every version declaration agrees.
- `decisions/`: numbered MADR decision records.
- `.github/workflows/`: continuous integration and the release automation,
  which publishes both packages and the schema document on both sites.

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
  `scripts/emit_fixtures.py`; never hand-edit them. The script refuses to
  overwrite the fixtures of a version whose `v<version>` tag exists. Emit
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
  registry
  `registry/schemes.json` in pretty JSON with `dumps(…,
  serialization="json")`. Either way object keys are sorted by code point
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
  case, and warning cases under `fixtures/warnings/` by hand; the fixture
  script emits neither.
- Regenerate `js/src/generated/` after changing the schema or font metrics.
  The generated TypeScript files belong in this repository.
- Regenerate `fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json` with
  `scripts/extract_font_metrics.py`; do not calculate or edit its advances by
  hand.
- Support the current version only. Both packages validate the current
  schema version and refuse every other; there are no migrations. A version
  a later one replaces lives in the git history at its tag and in its
  released packages.

## Commands

Run these commands from the stated directory.

| Directory | Command | Purpose |
| --- | --- | --- |
| repository root | `python3 scripts/check_versions.py` | Check version declarations agree. |
| repository root | `python scripts/emit_fixtures.py --timetoalign-commit "$(git -C /path/to/timetoalign rev-parse --short HEAD)"` | Emit and round-trip the fixtures with an environment containing timetoalign. |
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
