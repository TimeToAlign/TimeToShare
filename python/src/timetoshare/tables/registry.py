"""The registry of a package: its index rows, resolving an ID, writing the index.

A package's registry is the table of the type ``Registry`` its
``package.yaml`` lists: one row per resolvable ID. An **event row** gives an
event's position on the axis of the root of its timeline's family, its
extraction and its locator; an **index row** names an element of a manifest,
a MatchClaim or an Extraction by its ``kind`` and its ``location``. Index
rows are derived: :func:`index_rows` builds them from the manifests, the
MatchClaim tables and the Extraction table, :func:`write_index` writes them
into the registry's index part, and :func:`stale_index` lists where the
index part disagrees with them, as the package check does. :func:`resolve`
finds every row of an ID, through a package or through one of its
manifests.

The registry is a file, or a folder of parts when its URL ends in ``/``:
``index.parquet`` holds the index rows, every other part the event rows of
one extraction. A ``location`` is a URI reference resolved against the
package root, the folder of ``package.yaml`` (a manifest alone: its folder).
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .._urls import PACKAGE_FILE, package_path
from ..ids import HASH, from_file_id, with_bare_ids
from ..serialization import loads
from ..validate import (
    SCHEMA_VERSION,
    SchemaValidationError,
    UnsupportedVersionError,
    validate,
)
from ..validation.diagnostics import entries_of
from .checks import TableError, _schema_problems, is_index
from .columns import ELEMENT_KINDS, REGISTRY_SCHEMA
from .package import (
    _INDEX_ROW,
    INDEX_PART,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    PackageProblem,
    _resolved_locations,
    _strings,
    index_rows_of,
    read_table,
    stale_problems,
    table_index_rows,
)

__all__ = [
    "INDEX_PART",
    "Resolution",
    "index_rows",
    "resolve",
    "stale_index",
    "write_index",
]


@dataclass(frozen=True)
class Resolution:
    """What an ID resolves to.

    Attributes:
        kind: The row's ``kind``: an event type, ``MatchClaim``,
            ``Extraction`` or the schema's name of a manifest element.
        location: The row's ``location``, a URI reference against the
            package root; ``None`` for an event only re-parsable from its
            extraction's source.
        manifest: The manifest the resolution belongs to, its path from the
            package root: the manifest resolved through, or, through the
            package, an element's own manifest; ``None`` otherwise.
        row: The registry row as a dictionary of its columns; ``None`` for
            an element of a manifest without a registry or one the index
            lacks.
    """

    kind: str
    location: str | None
    manifest: str | None
    row: dict[str, Any] | None


def _bare(id: str) -> str:
    """An ID as given: bare, or written ``#id``, of which one ``#`` is stripped."""
    return from_file_id(id) if id.startswith(HASH) else id


@dataclass(frozen=True)
class _Sources:
    """The index rows a package's sources give, and the paths from the root
    of the manifests and tables listed that could not be read."""

    rows: pa.Table
    unread: frozenset[str]


@dataclass(frozen=True)
class _Package:
    """A package's ``package.yaml`` as read, with its root."""

    root: Path
    value: Mapping[str, Any]

    @classmethod
    def at(cls, root: str | os.PathLike[str]) -> _Package:
        root = Path(root)
        file = root / PACKAGE_FILE
        if not file.is_file():
            raise FileNotFoundError(f"no {PACKAGE_FILE} lies in '{root}'")
        return cls(root, loads(file.read_text(encoding="utf-8")))

    def urls(self, member: str, kind: str | None = None) -> list[str]:
        """The URLs of the entries of ``manifests`` or ``tables`` as
        written, of the type ``kind`` where given."""
        return [
            entry["url"]
            for entry in entries_of(self.value, member)
            if isinstance(entry, Mapping)
            and isinstance(entry.get("url"), str)
            and (kind is None or entry.get("type") == kind)
        ]

    def registry(self) -> str:
        """The URL of the one Registry entry.

        Raises:
            ValueError: If ``package.yaml`` lists no table or two tables of
                the type ``Registry``.
        """
        urls = self.urls("tables", "Registry")
        if len(urls) != 1:
            many = "no table" if not urls else f"{len(urls)} tables"
            raise ValueError(f"{PACKAGE_FILE} lists {many} of the type Registry")
        return urls[0]

    def sources(self) -> _Sources:
        """The index rows of the valid manifests (each at its URL as
        ``package.yaml`` lists it) and of the MatchClaim and Extraction
        tables (at their entries' URLs), and what could not be read: a
        missing or invalid manifest, a missing or unreadable table."""
        parts = []
        unread: set[str] = set()
        for url in self.urls("manifests"):
            path = package_path(url)
            if path is None or not (self.root / path).is_file():
                unread.update([path] if path is not None else [])
                continue
            manifest = loads((self.root / path).read_text(encoding="utf-8"))
            try:
                validate(manifest)
            except (SchemaValidationError, UnsupportedVersionError):
                unread.add(path)
                continue
            parts.append(index_rows_of(with_bare_ids(manifest), url))
        for kind in ("MatchClaim", "Extraction"):
            for url in self.urls("tables", kind):
                path = package_path(url)
                if path is None or not (self.root / path).exists():
                    unread.update([path] if path is not None else [])
                    continue
                try:
                    table = read_table(self.root / path, type=kind, columns=["id"])
                except TableError:
                    unread.add(path)
                    continue
                parts.append(table_index_rows(_strings(table, "id"), kind, url))
        rows = pa.concat_tables(parts) if parts else _INDEX_ROW.empty_table()
        rows = rows.sort_by([("location", "ascending"), ("id", "ascending")])
        return _Sources(rows, frozenset(unread))

    def index_part(self) -> tuple[Path, str]:
        """The index part of the registry: its path, and its path from the
        package root."""
        url = self.registry()
        path = package_path(url)
        if path is None:
            raise ValueError(f"the registry '{url}' lies outside the package")
        if url.endswith("/"):
            path += INDEX_PART
        return self.root / path, path


def _as_registry(table: pa.Table) -> pa.Table:
    """Index rows in the registry's columns and order, every other column null."""
    return pa.table(
        {
            field.name: (
                table.column(field.name).cast(field.type)
                if field.name in table.column_names
                else pa.nulls(len(table), field.type)
            )
            for field in REGISTRY_SCHEMA
        },
        schema=REGISTRY_SCHEMA,
    )


def index_rows(package_root: str | os.PathLike[str]) -> pa.Table:
    """The index rows of a package, as its manifests and tables give them.

    One row per element with an ID of each valid manifest ``package.yaml``
    lists (``kind`` the schema's name of the element, ``location`` the
    manifest's URL as ``package.yaml`` lists it, ``timeline_id`` the timeline
    holding a region or a flow-control element and the ``timeline`` of a
    named timestamp or an elision, ``name`` the element's name), one per
    row of each MatchClaim table and of the Extraction table (``location``
    the table entry's URL); built by
    :func:`~timetoshare.tables.package.index_rows_of` and
    :func:`~timetoshare.tables.package.table_index_rows`, as the package
    check builds them. Every other column is null. The rows are sorted by
    ``location``, then ``id``, by code point.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
    """
    return _as_registry(_Package.at(package_root).sources().rows)


# The index part.


def _held_rows(part: Path) -> pa.Table | None:
    """The rows of an index part as written; ``None`` for no part."""
    if not part.is_file():
        return None
    return read_table(part, type="Registry")


def _write(table: pa.Table, target: Path) -> None:
    """Write a registry file atomically: a name starting with ``.`` beside it,
    then renamed over it."""
    metadata = {
        **(table.schema.metadata or {}),
        TYPE_METADATA_KEY.encode(): b"Registry",
        VERSION_METADATA_KEY.encode(): SCHEMA_VERSION.encode(),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}")
    try:
        pq.write_table(table.replace_schema_metadata(metadata), temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _at_unread(table: pa.Table, unread: Iterable[str]) -> pa.Array:
    """Where a row's ``location`` resolves to a manifest or table that could
    not be read."""
    paths = _resolved_locations(_strings(table, "location"))
    gone = pa.array(sorted(unread), pa.string())
    return pc.fill_null(pc.is_in(paths, value_set=gone), False)


def write_index(package_root: str | os.PathLike[str]) -> Path:
    """Write the registry's index part from the package's sources.

    For a registry folder the part is ``index.parquet`` in it, the other
    parts untouched; for a single file the file itself. The part holds the
    index rows of :func:`index_rows`, and, sorted in among them, the index
    rows it held at a manifest or table that could not be read, which
    cannot be rebuilt and are kept as they were; then the rows that are no
    index rows, as they were, so that no event row is lost. The file is
    written under a name starting with ``.`` and renamed over the part, and
    states the type ``Registry`` and the format version in its metadata.

    Returns:
        The path of the part written.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
        ValueError: If ``package.yaml`` lists no table, or two tables, of the
            type ``Registry``, or the registry lies outside the package.
    """
    package = _Package.at(package_root)
    part, _ = package.index_part()
    sources = package.sources()
    rows = _as_registry(sources.rows)
    held = _held_rows(part)
    if held is not None:
        held = held.replace_schema_metadata(None)
        index = is_index(_strings(held, "kind"))
        indexed = held.filter(index)
        kept = indexed.filter(_at_unread(indexed, sources.unread))
        if len(kept):
            rows = pa.concat_tables([rows, kept], promote_options="default").sort_by(
                [("location", "ascending"), ("id", "ascending")]
            )
        events = held.filter(pc.invert(index))
        if len(events):
            rows = pa.concat_tables([rows, events], promote_options="default")
    _write(rows, part)
    return part


def stale_index(package_root: str | os.PathLike[str]) -> list[PackageProblem]:
    """Where the registry's index part disagrees with the package's sources.

    The index rows of the part are compared with :func:`index_rows` by
    :func:`~timetoshare.tables.package.stale_problems`, the comparison the
    package check makes, so that this list is the package check's
    ``stale_index`` problems: rows matched by ``id`` and ``location``
    resolved against the package root, ``kind``, ``timeline_id`` and
    ``name`` compared, rows at a manifest or table that could not be read
    not compared. A missing index part lacks every row; a part whose columns
    are not the registry's has none compared, its table check's to report.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
        ValueError: If ``package.yaml`` lists no table, or two tables, of the
            type ``Registry``, or the registry lies outside the package.
    """
    package = _Package.at(package_root)
    part, file = package.index_part()
    sources = package.sources()
    held = _held_rows(part)
    if held is None or _schema_problems(held.schema.empty_table(), REGISTRY_SCHEMA):
        held = REGISTRY_SCHEMA.empty_table()
    rows = pc.indices_nonzero(is_index(_strings(held, "kind")))
    index = pa.table(
        {
            **{name: _strings(held, name).take(rows) for name in _INDEX_ROW.names},
            "row": rows.cast(pa.int64()),
        }
    )
    return stale_problems(index, sources.rows, file, sources.unread)


# Resolving.


def _resolution(row: dict[str, Any], manifest: str | None) -> Resolution:
    return Resolution(row["kind"], row["location"], manifest, row)


def _package_root_of(manifest: Path) -> tuple[Path, str]:
    """The root of the package a manifest file lies in, and the manifest's
    URL from it as ``package.yaml`` lists it: the nearest folder above it
    whose ``package.yaml`` lists it, else its own folder."""
    resolved = manifest.resolve()
    for folder in resolved.parents:
        if not (folder / PACKAGE_FILE).is_file():
            continue
        for url in _Package.at(folder).urls("manifests"):
            path = package_path(url)
            if path is not None and (folder / path).resolve() == resolved:
                return folder, url
    return resolved.parent, resolved.name


def _rows_with(root: Path, paths: Iterable[str], id: str) -> pa.Table:
    """The rows of the ID in each registry, a path from the root, read once
    each, the filter pushed into the reader."""
    found = [
        read_table(root / path, type="Registry", ids=[id])
        for path in dict.fromkeys(paths)
    ]
    if not found:
        return REGISTRY_SCHEMA.empty_table()
    return pa.concat_tables(found, promote_options="default")


def _names_extraction(
    root: Path, paths: Iterable[str], id: str, listed: pa.Array
) -> bool:
    """Whether an event row of the ``listed`` timelines in one of the
    registries names the extraction ``id``: the rows of those timelines read
    in their ``extraction_id`` alone, the timeline filter pushed into the
    reader."""
    for path in dict.fromkeys(paths):
        rows = read_table(
            root / path,
            type="Registry",
            timelines=listed.to_pylist(),
            columns=["extraction_id"],
        )
        if pc.any(pc.equal(_strings(rows, "extraction_id"), id)).as_py():
            return True
    return False


def _through_package(root: Path, id: str) -> list[Resolution]:
    path = package_path(_Package.at(root).registry())
    found = []
    for row in _rows_with(root, [] if path is None else [path], id).to_pylist():
        own = row["location"] if row["kind"] in ELEMENT_KINDS else None
        found.append(_resolution(row, own))
    return found


def _through_manifest(file: Path, id: str) -> list[Resolution]:
    root, location = _package_root_of(file)
    manifest = with_bare_ids(loads(file.read_text(encoding="utf-8")))
    at = package_path(location) or location
    resources = [
        resource
        for resource in entries_of(manifest, "resources")
        if isinstance(resource, Mapping)
    ]

    def paths(kind: str) -> list[str]:
        return [
            path
            for resource in resources
            if resource.get("type") == kind
            and (path := package_path(resource["url"], at)) is not None
        ]

    registries = paths("Registry")
    with_id = _rows_with(root, registries, id)
    resolved = _resolved_locations(_strings(with_id, "location"))
    kinds = _strings(with_id, "kind")
    found: list[Resolution] = []
    elements = index_rows_of(manifest, location)
    for element in elements.filter(pc.equal(elements["id"], id)).to_pylist():
        index = with_id.filter(
            pc.fill_null(
                pc.and_(pc.equal(resolved, at), pc.equal(kinds, element["kind"])), False
            )
        ).to_pylist()
        found.append(
            Resolution(element["kind"], location, location, index[0] if index else None)
        )
    listed = pa.array(
        sorted(
            {
                timeline
                for resource in resources
                if resource.get("type") == "Registry"
                for timeline in entries_of(resource, "timelines")
                if isinstance(timeline, str)
            }
        ),
        pa.string(),
    )
    event = pc.invert(is_index(kinds))
    events = pc.and_(
        event, pc.fill_null(pc.is_in(_strings(with_id, "timeline_id"), listed), False)
    )
    tables = pa.array(sorted(set(paths("MatchClaim"))), pa.string())
    claims = pc.and_(
        pc.equal(kinds, "MatchClaim"),
        pc.fill_null(pc.is_in(resolved, value_set=tables), False),
    )
    extraction = pc.equal(kinds, "Extraction")
    if pc.any(extraction).as_py() and not _names_extraction(
        root, registries, id, listed
    ):
        extraction = pc.and_(extraction, pa.scalar(False))
    for mask in (events, claims, extraction):
        for row in with_id.filter(pc.fill_null(mask, False)).to_pylist():
            found.append(_resolution(row, location))
    return found


def resolve(path: str | os.PathLike[str], id: str) -> list[Resolution]:
    """Every resolution of an ID, through a package or one of its manifests.

    Through a package root (a folder holding ``package.yaml``): every row of
    its registry with the ID, an element's with its manifest. Through a
    manifest file: the element of the manifest with the ID first (with its
    index row, or ``None`` without a registry or where the index lacks it),
    then the rows of its Registry resources' registries that belong to it:
    an event row on a timeline those resources list, a MatchClaim row of a
    table its MatchClaim resources name, an Extraction row one of its event
    rows names; each with the manifest. The ID is bare; a written ``#id``
    is read as the bare ID, one ``#`` stripped. Each registry is read with
    the filter of the ID pushed into the reader (``read_table(ids=...)``);
    an Extraction row found through a manifest is checked against the
    ``extraction_id`` of the event rows of the timelines listed, read with
    the timeline filter pushed in.

    Returns:
        The resolutions; an empty list where nothing holds the ID.

    Raises:
        FileNotFoundError: If ``path`` is neither a package root nor a file.
        ValueError: If a package root's ``package.yaml`` lists no table, or
            two tables, of the type ``Registry``.
    """
    bare = _bare(id)
    path = Path(path)
    if path.is_dir():
        return _through_package(path, bare)
    if not path.is_file():
        raise FileNotFoundError(f"no package or manifest lies at '{path}'")
    return _through_manifest(path, bare)
