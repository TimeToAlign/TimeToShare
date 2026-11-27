"""The addresses inside a package: its root file and the one reading of a URL.

A package's URLs, a table entry's, a resource's, a registry row's
``location``, are URI references resolved against the document stating
them. This module holds that one reading, free of pyarrow, for the table
checks, the registry and the version step alike.
"""

from __future__ import annotations

from urllib.parse import unquote, urldefrag, urljoin

PACKAGE_FILE = "package.yaml"
"""The name of the file at a package's root listing its manifests and tables."""

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
