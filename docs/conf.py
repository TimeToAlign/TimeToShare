"""Sphinx configuration of the TimeToShare! documentation site.

``building.md`` gives the command. Before Sphinx reads a page, this file
writes the pages generated from other sources, all ignored by git: one page
per decision record (``decisions/``) and the TypeScript API (``api-ts/``),
which TypeDoc writes as Markdown from ``js/src/index.ts``.
"""

from __future__ import annotations

import subprocess
from importlib.metadata import metadata
from pathlib import Path

from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.ext.napoleon import Config as NapoleonConfig
from sphinx.ext.napoleon.docstring import GoogleDocstring
from sphinx.transforms.post_transforms import SphinxPostTransform

import timetoshare

_DOCS = Path(__file__).resolve().parent
_ROOT = _DOCS.parent

# -- Project -----------------------------------------------------------------

_METADATA = metadata("timetoshare")
_REPOSITORY = next(
    url.split(", ", 1)[1]
    for url in _METADATA.get_all("Project-URL", [])
    if url.startswith("Repository, ")
)

project = _METADATA["Name"]
release = _METADATA["Version"]
version = release
copyright = "2026 Time to Align!"

# -- General -----------------------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]
nitpicky = True
nitpick_ignore = [
    # Type aliases of the validator's diagnostics, written in signatures but
    # not documented on their own.
    ("py:class", "InstancePath"),
    ("py:class", "ValidationCode"),
    # `check_belief_filter` names `spell` of `timetoshare.serialization`
    # without its module.
    ("py:func", "spell"),
]
nitpick_ignore_regex = [
    # Private helpers named in signatures or docstrings are not part of the
    # documented API.
    (r"py:.*", r"(.+\.)?_\w+"),
]

# -- Markdown ----------------------------------------------------------------

myst_enable_extensions = ["colon_fence", "substitution"]
# The README, the specifications and the decision records link to their own
# headings in GitHub's form (`#the-timeline`); MyST derives the same slugs.
myst_heading_anchors = 6

# The schema page names the documents of the schema version the package
# validates, so that no page spells a version.
_SCHEMA = f"../schema/{timetoshare.SCHEMA_VERSION}"
myst_substitutions = {
    "schema_version": timetoshare.SCHEMA_VERSION,
    "manifest_schema": (
        f"{{download}}`timetoshare.schema.json <{_SCHEMA}/timetoshare.schema.json>`"
    ),
    "provenance_schema": (
        f"{{download}}`provenance.schema.json <{_SCHEMA}/provenance.schema.json>`"
    ),
    "tables_schema": f"{{download}}`tables.json <{_SCHEMA}/tables.json>`",
}

# -- Design decisions --------------------------------------------------------

# One page per record, each including the record itself, so that a new record
# needs no page of its own.
_DECISIONS = _DOCS / "decisions"
_DECISIONS.mkdir(exist_ok=True)
for _stale in _DECISIONS.glob("*.md"):
    _stale.unlink()
for _record in sorted((_ROOT / "decisions").glob("*.md")):
    (_DECISIONS / _record.name).write_text(
        f"```{{include}} ../../decisions/{_record.name}\n```\n", encoding="utf-8"
    )

# -- Python API --------------------------------------------------------------

autosummary_generate = True
autodoc_default_options = {"members": True, "show-inheritance": True}
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pyarrow": ("https://arrow.apache.org/docs/", None),
}

# Docstrings are Google style, read by napoleon. The docstring of a constant
# or a type alias is prose, and napoleon would read the words before its
# first colon as a type, so those are left as written.
_NAPOLEON = NapoleonConfig(napoleon_numpy_docstring=False)


def _google_docstring(app, what, name, obj, options, lines) -> None:
    if what in ("data", "attribute"):
        return
    lines[:] = GoogleDocstring(lines, _NAPOLEON, app, what, name, obj, options).lines()


def _skip_tuple_field(app, what, name, obj, skip, options) -> bool | None:
    # A NamedTuple's fields are described in its "Attributes" section; the
    # accessors Python generates for them only say "Alias for field number N".
    if (getattr(obj, "__doc__", None) or "").startswith("Alias for field number"):
        return True
    return None


def _package_name(app, env, node, contnode):
    """Resolve ``timetoshare.X`` to the module that defines the re-exported X."""
    if node.get("refdomain") != "py":
        return None
    domain = env.get_domain("py")
    target = node["reftarget"]
    for package in ("timetoshare.tables", "timetoshare"):
        name = target.removeprefix(package + ".")
        if name == target or "." in name:
            continue
        homes = [
            full
            for full in domain.objects
            if full.startswith(package + ".") and full.endswith("." + name)
        ]
        if len(homes) == 1:
            return domain.resolve_xref(
                env,
                node["refdoc"],
                app.builder,
                node["reftype"],
                homes[0],
                node,
                contnode,
            )
    return None


# -- TypeScript API ----------------------------------------------------------

_TYPEDOC = _ROOT / "js" / "node_modules" / "typedoc" / "bin" / "typedoc"
if not _TYPEDOC.is_file():
    raise RuntimeError(
        "TypeDoc is missing: run `pnpm install --frozen-lockfile` in js/ first"
    )
subprocess.run(
    ["node", str(_TYPEDOC), "--options", "typedoc.json", "--logLevel", "Error"],
    cwd=_DOCS,
    check=True,
)


class _RepositoryLinks(SphinxPostTransform):
    """Point a link to a repository file the site does not hold at GitHub.

    The README links to `fixtures/README.md`, which is no page of the site.
    """

    default_priority = 8  # before MyST resolves its links

    def run(self, **kwargs) -> None:
        for node in list(self.document.findall(addnodes.pending_xref)):
            if node["reftype"] != "myst" or node.get("refdomain"):
                continue
            target = node["reftarget"]
            if not (_ROOT / target.split("#", 1)[0]).is_file():
                continue
            node.replace_self(
                nodes.reference(
                    "", "", *node.children, refuri=f"{_REPOSITORY}/blob/main/{target}"
                )
            )


# -- HTML --------------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_title = f"{project} {release}"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": _REPOSITORY,
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        }
    ],
    "header_links_before_dropdown": 9,
    "show_toc_level": 2,
}
html_show_sourcelink = False


def setup(app: Sphinx) -> None:
    app.connect("autodoc-process-docstring", _google_docstring)
    app.connect("autodoc-skip-member", _skip_tuple_field)
    app.connect("missing-reference", _package_name)
    app.add_post_transform(_RepositoryLinks)
