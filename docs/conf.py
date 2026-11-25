"""Sphinx configuration of the TimeToShare! documentation site.

``building.md`` gives the command. When a build starts, before Sphinx reads a
page, this file writes the pages generated from other sources, all ignored by
git: one page per decision record (``decisions/``) and the TypeScript API
(``api-ts/``), which TypeDoc writes as Markdown from ``js/src/index.ts``.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from importlib.metadata import metadata
from pathlib import Path, PurePosixPath

from docutils.nodes import Element
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.ext.napoleon import Config as NapoleonConfig
from sphinx.ext.napoleon.docstring import GoogleDocstring

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
nitpick_ignore_regex = [
    # The type variable of `connected_sets`, written in its signature, is not
    # part of the documented API.
    ("py:class", r"(.+\.)?_Member"),
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


def _write_decision_pages() -> None:
    """One page per decision record, each including the record itself.

    A new record needs no page of its own.
    """
    folder = _DOCS / "decisions"
    folder.mkdir(exist_ok=True)
    for stale in folder.glob("*.md"):
        stale.unlink()
    for record in sorted((_ROOT / "decisions").glob("*.md")):
        (folder / record.name).write_text(
            f"```{{include}} ../../decisions/{record.name}\n```\n", encoding="utf-8"
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


def _resolve_in_module(
    app: Sphinx, env: BuildEnvironment, node: pending_xref, contnode: Element
) -> Element | None:
    """Resolve a Python name the way its module does.

    A docstring or a signature names an object as its module imports it
    (``InstancePath``), and a page names it as the package re-exports it
    (``timetoshare.UNITS``); the object is documented in the module
    that defines it, under its full name, which is looked up here. A type
    alias names no module of its own, so the documented names are searched for
    the one that is the same object.
    """
    if node.get("refdomain") != "py":
        return None
    module = sys.modules.get(node.get("py:module") or "")
    target = node["reftarget"]
    parts = target.split(".")
    for end in range(len(parts) - 1, 0, -1):
        if ".".join(parts[:end]) in sys.modules:
            module = sys.modules[".".join(parts[:end])]
            target = ".".join(parts[end:])
            break
    head, _, rest = target.partition(".")
    if module is None or not hasattr(module, head):
        return None
    found = getattr(module, head)
    domain = env.get_domain("py")
    homes = []
    for full in domain.objects:
        home, _, name = full.rpartition(".")
        if (
            name == head
            and home != module.__name__
            and home in sys.modules
            and vars(sys.modules[home]).get(head) is found
        ):
            homes.append(full)
    if len(homes) != 1:
        return None
    return domain.resolve_xref(
        env,
        node["refdoc"],
        app.builder,
        node["reftype"],
        ".".join(part for part in (homes[0], rest) if part),
        node,
        contnode,
    )


# -- TypeScript API ----------------------------------------------------------


def _write_typescript_api() -> None:
    """Write the TypeScript API as Markdown into ``api-ts/`` with TypeDoc.

    A warning of TypeDoc fails the build (``treatWarningsAsErrors``).
    """
    typedoc = _ROOT / "js" / "node_modules" / "typedoc" / "bin" / "typedoc"
    if not typedoc.is_file():
        raise RuntimeError(
            "TypeDoc is missing: run `pnpm install --frozen-lockfile` in js/ first"
        )
    subprocess.run(
        ["node", str(typedoc), "--options", "typedoc.json"], cwd=_DOCS, check=True
    )


def _generate(app: Sphinx) -> None:
    _write_decision_pages()
    _write_typescript_api()


# -- Links of included files -------------------------------------------------

#: Repository files that are pages of this site, by their page name.
_SITE_PAGES = {
    "README.md": "overview",
    "CHANGELOG.md": "changelog",
    "CONTRIBUTING.md": "contributing",
}

_LINK = re.compile(r"\]\((?P<target>[^)\s]+)(?P<title>\s+\"[^\"]*\")?\)")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _page_of(path: PurePosixPath) -> str | None:
    """The page of this site that shows the repository file ``path``, if any."""
    if str(path) in _SITE_PAGES:
        return _SITE_PAGES[str(path)]
    if path.suffix == ".md" and len(path.parts) == 2:
        if path.parts[0] == "docs" and (_DOCS / path.name).is_file():
            return path.stem
        if path.parts[0] == "decisions":
            return f"decisions/{path.stem}"
    return None


def _rewrite_links(text: str, source: Path, page_folder: PurePosixPath) -> str:
    """Point the links of an included repository file at this site or at GitHub.

    A link relative to ``source``, or a link to the repository's own file on
    GitHub (as the README writes them, for the package registries), goes to
    the page that shows the file, written relative to ``page_folder``; a link
    to another file of the repository goes to GitHub. A link out of the
    repository is left as written, for the strict build to report.
    """
    on_github = f"{_REPOSITORY}/blob/main/"

    def replace(match: re.Match[str]) -> str:
        target = match["target"]
        path, hash_, anchor = target.partition("#")
        if path.startswith(on_github):
            absolute = _ROOT / path.removeprefix(on_github)
        elif not path or _SCHEME.match(path):
            return match[0]
        else:
            absolute = Path(os.path.normpath(source.parent / path))
        if not absolute.is_relative_to(_ROOT):
            return match[0]
        relative = PurePosixPath(absolute.relative_to(_ROOT).as_posix())
        page = _page_of(relative)
        if page is not None:
            new = PurePosixPath(os.path.relpath(f"{page}.md", page_folder)).as_posix()
        elif path.startswith(on_github):
            return match[0]
        else:
            kind = "tree" if absolute.is_dir() else "blob"
            new = f"{_REPOSITORY}/{kind}/main/{relative}"
        return f"]({new}{hash_}{anchor}{match['title'] or ''})"

    return _LINK.sub(replace, text)


def _read_included(
    app: Sphinx, relative_path: Path, parent_docname: str, content: list[str]
) -> None:
    """Point the links of an included repository file at the site."""
    source = Path(os.path.normpath(_DOCS / relative_path))
    if source.is_relative_to(_ROOT):
        folder = PurePosixPath(parent_docname).parent
        content[0] = _rewrite_links(content[0], source, folder)


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
    app.connect("builder-inited", _generate, priority=100)
    app.connect("autodoc-process-docstring", _google_docstring)
    app.connect("autodoc-skip-member", _skip_tuple_field)
    app.connect("missing-reference", _resolve_in_module)
    app.connect("include-read", _read_included)
