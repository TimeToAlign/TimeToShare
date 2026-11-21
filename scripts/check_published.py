#!/usr/bin/env python3
"""Assemble the published documents of a schema version and check their addresses.

A release serves, under ``https://timetoalign.github.io/timetoshare/<version>/``,
every file of ``schema/<version>/`` (the manifest schema, the provenance
schema, the column types of the tables) and the catalogue's schema
``catalogue/catalogue.schema.json``. The release workflow assembles both of
its sites with this script, so the tree checked here is the tree served.

The check fails when

* a document has no ``$id``, or one that is not the address it is served at,
* a ``$ref`` (or a type of ``tables.json`` naming its ``schema``) points to a
  document the tree does not hold, or its fragment to no member of it.

Usage::

    python scripts/check_published.py                    # the working tree
    python scripts/check_published.py --ref v0.2.0       # a commit or tag
    python scripts/check_published.py --ref v0.2.0 --out site   # into site/0.2.0/

Exit status 0 prints the published paths; 1 lists every problem. Standard
library only, so the workflows can run it before any environment is set up.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urldefrag, urljoin

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SITE = "https://timetoalign.github.io/timetoshare/"
"""The address every published document's ``$id`` lies under."""
CATALOGUE_SCHEMA = "catalogue/catalogue.schema.json"
TABLES_DOCUMENT = "tables.json"


def _git(*arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), *arguments],
        check=True,
        capture_output=True,
    ).stdout


def _names(ref: str | None, directory: str) -> list[str]:
    """The names of the files (or, for ``schema``, the directories) in ``directory``."""
    if ref is None:
        path = REPOSITORY_ROOT / directory
        return sorted(child.name for child in path.iterdir()) if path.is_dir() else []
    listed = _git("ls-tree", "--name-only", f"{ref}:{directory}").decode()
    return sorted(listed.split())


def _read(ref: str | None, path: str) -> bytes | None:
    if ref is None:
        file = REPOSITORY_ROOT / path
        return file.read_bytes() if file.is_file() else None
    try:
        return _git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None


def published(ref: str | None = None) -> dict[str, bytes]:
    """The published documents, by their path under :data:`SITE`.

    Read from the working tree, or from the commit ``ref`` names.
    """
    versions = _names(ref, "schema")
    if len(versions) != 1:
        raise SystemExit(f"expected one version under schema/, found {versions}")
    (version,) = versions
    files = {
        f"{version}/{name}": _read(ref, f"schema/{version}/{name}")
        for name in _names(ref, f"schema/{version}")
    }
    catalogue = _read(ref, CATALOGUE_SCHEMA)
    if catalogue is not None:
        files[f"{version}/{Path(CATALOGUE_SCHEMA).name}"] = catalogue
    return {path: content for path, content in files.items() if content is not None}


def _references(document: Any, name: str) -> Iterator[str]:
    """Every reference a document makes to a document or a member of one."""
    if name == TABLES_DOCUMENT:
        for declared in document.get("types", {}).values():
            if "schema" in declared:
                yield declared["schema"]
    stack = [document]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            reference = node.get("$ref")
            if isinstance(reference, str):
                yield reference
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)


def _member(document: Any, pointer: str) -> bool:
    """Whether the JSON pointer ``pointer`` names a member of ``document``."""
    node = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            return False
    return True


def problems(files: dict[str, bytes]) -> list[str]:
    """Every problem of the published tree ``files``."""
    documents = {
        path: json.loads(content)
        for path, content in files.items()
        if path.endswith(".json")
    }
    found = []
    for path, document in sorted(documents.items()):
        address = SITE + path
        identifier = document.get("$id")
        if identifier is None:
            found.append(f"{path}: no $id")
        elif identifier != address:
            found.append(f"{path}: its $id {identifier} is not its address {address}")
        base = identifier or address
        for reference in sorted(set(_references(document, Path(path).name))):
            target, fragment = urldefrag(urljoin(base, reference))
            if not target.startswith(SITE) or target[len(SITE) :] not in documents:
                found.append(f"{path}: {reference} names a document not published")
                continue
            pointer = unquote(fragment)
            if pointer.startswith("/") and not _member(
                documents[target[len(SITE) :]], pointer
            ):
                found.append(f"{path}: {reference} names no member")
    return found


def write(files: dict[str, bytes], out: Path) -> None:
    """Write the published tree under ``out``."""
    for path, content in files.items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ref", help="read the commit or tag REF, not the working tree"
    )
    parser.add_argument("--out", type=Path, help="write the tree under OUT/<version>/")
    arguments = parser.parse_args()
    files = published(arguments.ref)
    found = problems(files)
    if found:
        print("\n".join(found), file=sys.stderr)
        return 1
    if arguments.out is not None:
        write(files, arguments.out)
    print("\n".join(sorted(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
