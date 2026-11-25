# Building these docs

The site is built with Sphinx from `docs/`. It needs the Python package
with its `docs` dependency group (Sphinx, the PyData theme and MyST) and
the JavaScript package's development dependencies (TypeDoc and its
Markdown plugin, which write the TypeScript API from `js/src/index.ts`
before Sphinx reads the pages). From the repository root:

```bash
(cd js && pnpm install --frozen-lockfile)
cd python
uv sync --group docs
uv run --no-sync sphinx-build -W --keep-going -n -d ../docs/_build/doctrees ../docs ../docs/_build/html
```

The pages land in `docs/_build/html`; open `index.html`. Every link
between pages is relative, so the folder can be served from any path.
The pages generated during the build (`docs/api/generated/`,
`docs/api-ts/` and `docs/decisions/`) and the output are ignored by git.
The build fetches the inventories of the Python and pyarrow documentation
to link the names they define, so it needs the network.
