"""The addresses inside a package: its root file, the names of manifest files
and the one reading of a URL.

A package's URLs, a table entry's, a resource's, a registry row's
``location``, are URI references resolved against the document stating
them. This module holds that one reading, free of pyarrow, for the table
checks, the registry and the version step alike.
"""

from __future__ import annotations

from urllib.parse import unquote, urldefrag, urljoin

PACKAGE_FILE = "package.yaml"
"""The name of the file at a package's root listing its manifests and tables."""

MANIFEST_SUFFIXES = (".tts.yaml", ".tts.yml", ".tts.json")
"""The endings of a manifest file's name, by which a tool looking for
manifests in a tree finds them."""

_BASE = "file:///package/"
"""The address a package's root is resolved at: references resolve as URLs,
and a reference leaving the package lies outside this prefix."""


def package_path(reference: str, against: str = "") -> str | None:
    """The path from the package's root of ``reference`` written in the
    document at ``against`` (a path from the root; the root itself by
    default), or ``None`` where it leads outside the package: an absolute
    URI, a path above the root, a reference with a query. Percent-escapes
    are decoded, a fragment dropped, and a folder's path keeps its final
    ``/``."""
    address = urldefrag(urljoin(_BASE + against, reference)).url
    if not address.startswith(_BASE) or "?" in address:
        return None
    return unquote(address.removeprefix(_BASE)) or None


def is_manifest_name(path: str) -> bool:
    """Whether a file's path or name ends like a manifest file's
    (:data:`MANIFEST_SUFFIXES`)."""
    return path.endswith(MANIFEST_SUFFIXES)


def manifest_key(path: str) -> str:
    """A manifest file's path without its ending ``.tts.<ext>``: one key for a
    manifest whatever its serialization (``op106.tts.yaml`` and
    ``op106.tts.json`` give ``op106``); any other path unchanged."""
    for suffix in MANIFEST_SUFFIXES:
        if path.endswith(suffix):
            return path.removesuffix(suffix)
    return path
