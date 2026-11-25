# 0018. Build the documentation site with Sphinx, the PyData theme, MyST and TypeDoc

Date: 2026-11-25

## Context

The repository documents the format in Markdown: the README, the two
specifications in `docs/`, the decision records, the changelog and the
contribution guide. The two packages document their API in their source:
Google-style docstrings in the Python package `timetoshare`, TSDoc
comments in the TypeScript package `@timetoalign/timetoshare`. A reader
needs all of it on one site, with the API rendered from the source, so
that it never drifts from the code, and with relative links only, so that
the same build can be served at one path per version.

The site must read the Markdown files where they are, without copying their
text; render both APIs; build locally with one command into
`docs/_build/html`; and follow the light or dark scheme of the reader's
system. The documentation sites of the other TimeToAlign! repositories move to
the same stack, so a reader moves between them without learning a new
layout.

## Considered options

- **Sphinx 9 with the PyData theme, MyST and TypeDoc.** Sphinx renders the
  Python API through `autodoc`, `autosummary`, `napoleon` (Google style),
  `intersphinx` and `viewcode`, all shipped with Sphinx. MyST parses
  Markdown, including GitHub-style heading anchors, and its `include`
  directive pulls a file from outside `docs/` into a page. The PyData theme
  gives the navigation bar, the light and dark schemes and a repository
  link. TypeDoc, with typedoc-plugin-markdown, writes the TypeScript API as
  Markdown, which MyST reads like any other page.
- **Sphinx with sphinx-js for the TypeScript API.** sphinx-js 5.0.3
  (pyodide, released 2026-03-30) runs TypeDoc 0.25 to 0.28 and renders
  TypeScript objects into Sphinx's JavaScript domain. It builds this code
  base, but it starts TypeDoc through `npx tsx@4.15.8`, a fixed release from
  2024 outside every lockfile: either `npx` downloads it at build time,
  outside the lockfile and the fourteen-day rule, or it becomes a development
  dependency, whose esbuild 0.21 install script pnpm refuses under this
  repository's settings, so `pnpm install --frozen-lockfile` fails. Its
  `js:automodule` directive cannot address a module in a subdirectory whose
  file name another subdirectory repeats (`statements/statements.ts`,
  `validate/statements.ts`), and it pins `cattrs<25.1`.
- **Doxygen.** It has no TypeScript support and does not render Python
  docstrings as written.
- **Quarto.** The TimeToAlign! repositories move their documentation
  sites off it, to one stack.
- **Zensical, or MkDocs with Material.** Zensical is young; Material for
  MkDocs is in maintenance mode.
- **Write it here.** A static-site generator that reads Markdown,
  introspects Python and parses TypeScript would be several thousand lines
  for a task these tools serve well.

## Decision

Build the site with Sphinx from `docs/`: `conf.py` and the pages that
include the files kept elsewhere (the README as the overview, the changelog,
the contribution guide; one page per decision record, written at build
time). `autosummary` writes one page per Python module at build time.
When a build starts, before Sphinx reads a page, `conf.py` runs TypeDoc with
typedoc-plugin-markdown over `js/src/index.ts`, the package's public entry,
and writes `docs/api-ts/index.md`; loading `conf.py` alone writes nothing.
The schema-derived declarations of `js/src/generated/` are left out, since
the schema page and the schema documents describe them; `typedoc.json`
names them, and two internal aliases a signature mentions (`Path`, the
array of `PathSegment`s of `FileIdError.path`, and `JsonObject`, the type
`isJsonObject` narrows to), as intentionally not exported. Every other
TypeDoc warning fails the build (`treatWarningsAsErrors`), as Sphinx's
`-W -n` does for the Python API. Generated pages and the output are ignored
by git. `docs/building.md` gives the command.

`docs/` is the site's source, and its build output lands in it. The
packages ship only the two specifications of `docs/` (`description.md` and
`drawing.md`): the npm package's `files` and `scripts/copy-assets.ts`, and
the Python package's build hook, name them file by file.

- **Fit.** One tool renders both APIs and every Markdown file; the
  TypeScript API lists exactly what the package's entry exports.
- **Maintenance.** Sphinx is developed by the sphinx-doc organisation
  (https://github.com/sphinx-doc/sphinx) with a release every few months;
  pydata-sphinx-theme by the PyData community
  (https://github.com/pydata/pydata-sphinx-theme); myst-parser by
  Executable Books (https://github.com/executablebooks/MyST-Parser);
  TypeDoc by its maintainers around Gerrit Birkeland
  (https://github.com/TypeStrong/typedoc); typedoc-plugin-markdown by
  Thomas Grey (https://github.com/typedoc2md/typedoc-plugin-markdown), one
  maintainer, whose releases follow TypeDoc's minor versions. The exposure
  is `conf.py`, `typedoc.json`, the module template and the page stubs.
- **Writing it ourselves.** Out of proportion (see above).
- **Audited versions.** Sphinx 9.0.4 (2025-12-04, BSD-2-Clause, Python
  3.11 and later: the one Sphinx release that runs on every Python the
  package supports, so the pages do not depend on the interpreter that
  builds them; 9.1 and 9.2 require Python 3.12 and 3.13),
  pydata-sphinx-theme 0.24.0 (2026-11-02, BSD-3-Clause, the newest release
  at least fourteen days old; it requires Sphinx 8.2 to 9), myst-parser
  5.1.0 (2026-05-13, MIT, requires Sphinx 8 to 9 and docutils below 0.23),
  TypeDoc 0.28.20 (2026-07-05, Apache-2.0, supports TypeScript 5.0 to 6.0),
  typedoc-plugin-markdown 4.14.1 (2026-10-19, MIT, requires TypeDoc 0.28).
  The documentation sites of the other TimeToAlign! repositories use the
  same Sphinx, theme and MyST, so that they look alike and can share one
  version menu. OSV lists no advisory for any of them, nor for docutils
  0.22.4 (queried 2026-11-25). The `docs` group adds 28 packages to
  `python/uv.lock`.
- **Pins and release age.** The Python package's `docs` dependency group
  pins `sphinx==9.0.4`, `pydata-sphinx-theme==0.24.0`, `myst-parser==5.1.0`
  and `pyarrow==25.0.0` (so that autodoc imports `timetoshare.tables`), as
  the `dev` group pins its tools; the group is never published. The
  release-age rule is written into `python/pyproject.toml` as
  `[tool.uv] exclude-newer = "2026-11-11T00:00:00Z"`, so `uv lock` resolves
  no release younger than fourteen days and the lockfile can be reproduced
  from the project file; the date moves forward when the lockfile is
  refreshed. Under it, babel 2.18.0, certifi 2026.10.23,
  charset-normalizer 3.5.2 and soupsieve 4.1 are locked below their newest
  release. The npm package's development dependencies pin `typedoc`
  0.28.20 and `typedoc-plugin-markdown` 4.14.1, recorded in
  `pnpm-lock.yaml`. Neither package's runtime dependencies change.

Primary sources: https://www.sphinx-doc.org/,
https://pydata-sphinx-theme.readthedocs.io/,
https://myst-parser.readthedocs.io/, https://typedoc.org/,
https://typedoc-plugin-markdown.org/, https://github.com/pyodide/sphinx-js,
https://osv.dev/ (queried through its API).

## Consequences

Building the site needs Node and the JavaScript package's development
dependencies besides the Python environment. The TypeScript API is
Markdown, not objects of Sphinx's JavaScript domain, so Python pages cannot
cross-reference TypeScript declarations; a declaration's signature names a
schema-derived type without a link. The build fetches the intersphinx
inventories of Python and pyarrow, so it needs the network. The exit cost
is `docs/conf.py`, `docs/typedoc.json`, the page stubs and the template,
the `docs` dependency group and two development dependencies.

## Review date

2027-11-25, or when Sphinx 10 or TypeDoc 0.29 is released.
