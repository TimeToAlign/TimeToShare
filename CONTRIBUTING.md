# Contributing

TimeToShare! is schema-first. The current schema, 0.1.0, is the contract; the Python and
TypeScript packages validate it, and timetoalign emits its fixtures.

## Schema changes

A version's schema is one document,
`schema/<version>/timetoshare.schema.json`, with the `$id`
`https://timetoalign.github.io/timetoshare/<version>/timetoshare.schema.json`;
the same file is also served at
`https://timetoalign.github.io/TimeToShare/<version>/timetoshare.schema.json`
by this repository's own GitHub Pages site. An unreleased version is changed in place; a released one is never altered.
A new version replaces the current one in `schema/`: the repository and both
packages hold the current version only, with no migrations, and a replaced
version lives in the git history at its tag, in its released packages and
on the project site. Update the
version declarations in both packages, add shared rejection and warning
cases, regenerate `js/src/generated/` with `pnpm generate`, and re-emit the
fixtures through timetoalign.

The manifests under `fixtures/<version>/` and its `groups/` and `bundles/`
subdirectories are generated artifacts, each in the complete form beside
its minimal twin. Use an environment containing the timetoalign revision
represented by the schema:

```bash
python scripts/emit_fixtures.py --timetoalign-commit "$(git -C /path/to/timetoalign rev-parse --short HEAD)"
```

Do not edit a fixture by hand. The script refuses to write into the
fixtures of a version whose `v<version>` tag exists. Rejection cases under
`fixtures/rejections/` and warning cases under `fixtures/warnings/` are
authored by hand.

## The drawing specification

`docs/drawing.md` specifies the `graphical` object, arithmetic, default
styles, font, layout, SVG and TikZ writers, and the block that draws every
manifest with its frames, cards, bands and ancestor lines. A drawing is derived and has no
schema or exchanged JSON form. The specification pins the drawing. A rule a reader could not reproduce from the
specification alone is a defect of the specification.

The drawing uses `fonts/DejaVuSans.ttf` from DejaVu Sans 2.37.
`fonts/LICENSE` contains its licence, and
`fonts/dejavu-sans-2.37.metrics.json` contains the advance widths used to
measure text. Regenerate the metrics from `python/` with:

```bash
uv run python ../scripts/extract_font_metrics.py
```

Python exposes the font through `font_path()` and `font_metrics()`. The npm
package exports `fontMetrics` and the
`@timetoalign/timetoshare/fonts/*` subpath.

## Dependencies and decisions

Add a dependency only with a numbered MADR in `decisions/`. The record must
assess writing the component here and its long-term maintenance cost, name the
audited version, and set a review date. Do not add speculative dependencies or
options.

Package manifests declare compatible version ranges because published
packages resolve in consumers' environments. The lockfiles,
`python/uv.lock` and `js/pnpm-lock.yaml`, pin exact versions. An audited
dependency release must have been available for at least 14 days before it is
added.

## Tests

Tests are README-first. Update the relevant `python/tests/README.md` or
`js/tests/README.md` to state the proof required, then write tests with exact
expected values.

Run the complete local checks:

```bash
cd python
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv build
```

```bash
cd js
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm generate
pnpm build
```

From the repository root:

```bash
python3 scripts/check_versions.py
```

## Known limitations

- The validator tests do not pin the JSON implementation's maximum
  safe-integer boundary in either implementation.
- Python and TypeScript rejection paths are independently compared with
  expected values, but no test compares both implementations' paths for the
  same generated invalid manifests.

## Release

Releases are made by
[release-please](https://github.com/googleapis/release-please) and
`.github/workflows/release.yml`. Write commit messages in the
[Conventional Commits](https://www.conventionalcommits.org/) form;
release-please builds `CHANGELOG.md` from them.

A TimeToShare version is a schema version, so release-please does not compute
it from the commits. The commit that adds a schema version updates every
declaration (`python/pyproject.toml`, `js/package.json`, `SCHEMA_VERSION`
in `python/src/timetoshare/validate.py` and `js/src/validate.ts`, and the
self entry in `python/uv.lock`), holds the document
`schema/X.Y.Z/timetoshare.schema.json`, a non-empty `fixtures/X.Y.Z/`
with its `drawings/`, and the rejection and warning cases, and passes
`python3 scripts/check_versions.py`. The commit carries the footer:

```text
Release-As: X.Y.Z
```

On every push to `main`, release-please opens or updates a release pull
request with that version and its changelog entry. Merging the pull request
tags `vX.Y.Z` and creates the GitHub release. The release job fails when the
version differs from the declarations, and the publish job checks the tag
again before publishing. It then runs the Python and JavaScript checks, builds
both packages, and publishes them through OIDC trusted publishing. Do not
push version tags by hand. When publishing fails part-way, run the Release
workflow by hand from the Actions tab with the release tag (`v0.1.0`) as its
input: it publishes that release again, skipping every file a registry
already holds, and serves its schema again.

The workflow then publishes the schema document of every released tag at
two addresses. The pages job deploys this repository's own site,
`https://timetoalign.github.io/TimeToShare/`, which holds
`<version>/timetoshare.schema.json`. A second job pushes the same file to
`timetoshare/<version>/timetoshare.schema.json` in the organisation's site
repository, `TimeToAlign/timetoalign.github.io`, where it is served at its
`$id`, `https://timetoalign.github.io/timetoshare/<version>/timetoshare.schema.json`.
GitHub Pages paths are case-sensitive, so the two addresses are two
copies of one file.

The workflow needs the repository to be public (npm provenance and the
public schema site require it), GitHub Actions to be allowed to create pull
requests in this repository, GitHub Pages enabled with GitHub Actions as its
source before the first release pull request is merged, the secret
`ORG_SITE_DEPLOY_KEY`, the private half of a deploy key with write access
to `TimeToAlign/timetoalign.github.io`, and a trusted publisher on each
registry:

| Registry | Project or package | GitHub owner | Repository | Workflow file | Environment |
| --- | --- | --- | --- | --- | --- |
| PyPI | `timetoshare` | `TimeToAlign` | `TimeToShare` | `release.yml` | `release` |
| npm | `@timetoalign/timetoshare` | `TimeToAlign` | `TimeToShare` | `release.yml` | `release` |

npm configures a trusted publisher only for a package that exists; the
package exists since 0.1.0, and its trusted publisher allows `npm publish`
only. No registry token is stored.
