"""The registry of a package: its index rows, resolving an ID, writing the index.

A package's registry is the table of the type ``Registry`` its
``package.yaml`` lists: one row per resolvable ID. An **event row** gives an
event's position on the axis of the root of its timeline's family, its
extraction and its locator; an **index row** names an element of a manifest,
a MatchClaim or an Extraction by its ``kind`` and its ``location``. Index
rows are derived: :func:`index_rows` builds them from the manifests, the
MatchClaim tables and the Extraction table, :func:`write_index` writes them
into the registry's index part, and :func:`stale_index` lists where the
index part disagrees with them. :func:`resolve` finds every row of an ID,
through a package or through one of its manifests.

The registry is a file, or a folder of parts when its URL ends in ``/``:
``index.parquet`` holds the index rows, every other part the event rows of
one extraction. A ``location`` is a URI reference resolved against the
package root, the folder of ``package.yaml`` (a manifest alone: its folder).
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urldefrag, urljoin

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ..ids import HASH, from_file_id, with_bare_ids
from ..serialization import loads
from ..validate import (
    SCHEMA_VERSION,
    SchemaValidationError,
    UnsupportedVersionError,
    validate,
)
from ..validation.diagnostics import entries_of, manifest_ids
from .columns import NUMBER_TYPE
from .package import (
    PACKAGE_FILE,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    PackageProblem,
    read_table,
    table_files,
)

__all__ = [
    "ELEMENT_KINDS",
    "INDEX_KINDS",
    "INDEX_PART",
    "REGISTRY_SCHEMA",
    "Resolution",
    "index_rows",
    "resolve",
    "stale_index",
    "write_index",
]

REGISTRY_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("kind", pa.string()),
        pa.field("location", pa.string()),
        pa.field("timeline_id", pa.string()),
        pa.field("unit", pa.string()),
        pa.field("number_type", pa.string()),
        pa.field("start", NUMBER_TYPE),
        pa.field("duration", NUMBER_TYPE),
        pa.field("name", pa.string()),
        pa.field("extraction_id", pa.string()),
        pa.field("locator", pa.string()),
        pa.field("vanished_in", pa.string()),
    ]
)
"""The registry's columns, in order."""

ELEMENT_KINDS = (
    "Manifest",
    "Timeline",
    "VirtualTimeline",
    "Group",
    "MeasureMap",
    "ConversionMap",
    "Region",
    "FlowControlElement",
    "Resource",
    "FlowMap",
    "Timestamp",
    "MatchStamp",
    "AlignmentAnchor",
    "Elision",
)
"""The kinds of the index rows of manifest elements: the schema's names."""

INDEX_KINDS = frozenset({*ELEMENT_KINDS, "MatchClaim", "Extraction"})
"""The kinds of index rows; a row of any other kind is an event row."""

INDEX_PART = "index.parquet"
"""The part of a registry folder holding the index rows."""

_KINDS = {
    "timelines": "Timeline",
    "children": "Timeline",
    "conversion_maps": "ConversionMap",
    "maps": "ConversionMap",
    "regions": "Region",
    "flow_control": "FlowControlElement",
    "groups": "Group",
    "measure_maps": "MeasureMap",
    "timestamps": "Timestamp",
    "elisions": "Elision",
    "matchstamps": "MatchStamp",
    "alignment_anchors": "AlignmentAnchor",
    "resources": "Resource",
    "flow_maps": "FlowMap",
    "virtual_timelines": "VirtualTimeline",
}
"""The kind of an element by the member that lists it."""

_ON_TIMELINE = ("Region", "FlowControlElement")
"""The kinds whose index row names the timeline holding them."""

_NAMING_TIMELINE = ("Timestamp", "Elision")
"""The kinds whose index row names the timeline of their ``timeline``."""

_COMPARED = ("kind", "timeline_id", "name")
"""The columns of an index row that its sources give; every other is null."""

_BASE = "file:///package/"


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


def _from_root(reference: str, against: str = "") -> str | None:
    """The path from the package root of ``reference`` written in the
    document at ``against``; ``None`` where it leads outside the package. A
    folder's path keeps its final ``/``."""
    address = urldefrag(urljoin(_BASE + against, reference)).url
    if not address.startswith(_BASE) or "?" in address:
        return None
    return unquote(address.removeprefix(_BASE)) or None


def _bare(id: str) -> str:
    """An ID as given: bare, or written ``#id``, of which one ``#`` is stripped."""
    return from_file_id(id) if id.startswith(HASH) else id


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

    def entries(self, kind: str) -> list[Mapping[str, Any]]:
        return [
            entry
            for entry in entries_of(self.value, "tables")
            if isinstance(entry, Mapping) and entry.get("type") == kind
        ]

    def registry(self) -> Mapping[str, Any]:
        """The one Registry entry.

        Raises:
            ValueError: If ``package.yaml`` lists no table or two tables of
                the type ``Registry``.
        """
        entries = self.entries("Registry")
        if len(entries) != 1:
            many = "no table" if not entries else f"{len(entries)} tables"
            raise ValueError(f"{PACKAGE_FILE} lists {many} of the type Registry")
        return entries[0]

    def manifests(self) -> Iterator[tuple[str, Mapping[str, Any]]]:
        """The valid manifests, each by its URL as ``package.yaml`` lists it
        and with bare IDs; a missing or invalid one is the package check's."""
        for entry in entries_of(self.value, "manifests"):
            url = entry.get("url") if isinstance(entry, Mapping) else None
            file = None if not isinstance(url, str) else _from_root(url)
            if file is None or not (self.root / file).is_file():
                continue
            manifest = loads((self.root / file).read_text(encoding="utf-8"))
            try:
                validate(manifest)
            except (SchemaValidationError, UnsupportedVersionError):
                continue
            yield url, with_bare_ids(manifest)


def _element_rows(location: str, manifest: Mapping[str, Any]) -> dict[str, list]:
    """The index rows of a manifest's elements, as columns."""
    columns: dict[str, list] = {"id": [], "kind": [], "timeline_id": [], "name": []}
    for identifier, path in manifest_ids(manifest):
        kind = "Manifest" if path == ("id",) else _KINDS[str(path[-3])]
        element: Any = manifest
        for step in path[:-1]:
            element = element[step]
        timeline = None
        if kind in _ON_TIMELINE:
            holder: Any = manifest
            for step in path[:-3]:
                holder = holder[step]
            timeline = holder.get("id")
        elif kind in _NAMING_TIMELINE:
            timeline = element.get("timeline")
        name = element.get("name")
        columns["id"].append(identifier)
        columns["kind"].append(kind)
        columns["timeline_id"].append(timeline if isinstance(timeline, str) else None)
        columns["name"].append(name if isinstance(name, str) else None)
    columns["location"] = [location] * len(columns["id"])
    return columns


def _ids_of(package: _Package, kind: str) -> Iterator[tuple[str, pa.Array]]:
    """The IDs of every table entry of ``kind``, by the entry's URL."""
    for entry in package.entries(kind):
        url = entry.get("url")
        path = None if not isinstance(url, str) else _from_root(url)
        if path is None or not (package.root / path).exists():
            continue
        arrays = [
            pq.read_table(file, columns=["id"]).column("id").combine_chunks()
            for file in table_files(package.root / path)
        ]
        yield url, (pa.concat_arrays(arrays) if arrays else pa.array([], pa.string()))


def _column(values: Any, kind: pa.DataType, length: int) -> pa.Array:
    if values is None:
        return pa.nulls(length, kind)
    if isinstance(values, pa.Array):
        return values.cast(kind)
    return pa.array(values, kind)


def _as_table(columns: Mapping[str, Sequence[Any] | pa.Array], length: int) -> pa.Table:
    return pa.table(
        {
            field.name: _column(columns.get(field.name), field.type, length)
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
    the table entry's URL). Every other column is null. The rows are sorted
    by ``location``, then ``id``, by code point.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
    """
    package = _Package.at(package_root)
    parts = []
    for location, manifest in package.manifests():
        columns = _element_rows(location, manifest)
        parts.append(_as_table(columns, len(columns["id"])))
    for kind in ("MatchClaim", "Extraction"):
        for url, ids in _ids_of(package, kind):
            length = len(ids)
            columns = {
                "id": ids,
                "kind": pa.repeat(pa.scalar(kind, pa.string()), length),
                "location": pa.repeat(pa.scalar(url, pa.string()), length),
            }
            parts.append(_as_table(columns, length))
    table = pa.concat_tables(parts) if parts else REGISTRY_SCHEMA.empty_table()
    return table.sort_by([("location", "ascending"), ("id", "ascending")])


# The index part.


def _index_part(package: _Package) -> tuple[Path, str]:
    """The index part of a package's registry: its path, and its path from
    the package root."""
    url = package.registry()["url"]
    path = _from_root(url)
    if path is None:
        raise ValueError(f"the registry '{url}' lies outside the package")
    if url.endswith("/"):
        path += INDEX_PART
    return package.root / path, path


def _held_rows(part: Path) -> pa.Table | None:
    """The rows of an index part as written; ``None`` for no part."""
    if not part.is_file():
        return None
    return read_table(part, type="Registry")


def _kinds(table: pa.Table) -> pa.Array:
    if "kind" not in table.column_names:
        return pa.nulls(len(table), pa.string())
    return table.column("kind").combine_chunks()


def _is_index(table: pa.Table) -> pa.Array:
    """Whether each row is an index row; a null kind is no index row."""
    value_set = pa.array(sorted(INDEX_KINDS), pa.string())
    return pc.fill_null(pc.is_in(_kinds(table), value_set=value_set), False)


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


def write_index(package_root: str | os.PathLike[str]) -> Path:
    """Write the registry's index part from the package's sources.

    For a registry folder the part is ``index.parquet`` in it, the other
    parts untouched; for a single file the file itself. The rows of the part
    that are no index rows are kept after the index rows, as they were, so
    that no event row is lost. The file is written under a name starting
    with ``.`` and renamed over the part, and states the type ``Registry``
    and the format version in its metadata.

    Returns:
        The path of the part written.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
        ValueError: If ``package.yaml`` lists no table, or two tables, of the
            type ``Registry``, or the registry lies outside the package.
    """
    package = _Package.at(package_root)
    part, _ = _index_part(package)
    rows = index_rows(package_root)
    held = _held_rows(part)
    if held is not None:
        kept = held.filter(pc.invert(_is_index(held)))
        if len(kept):
            rows = pa.concat_tables(
                [rows, kept.replace_schema_metadata(None)], promote_options="default"
            )
    _write(rows, part)
    return part


def _strings(table: pa.Table, name: str) -> pa.Array:
    if name not in table.column_names:
        return pa.nulls(len(table), pa.string())
    return table.column(name).combine_chunks().cast(pa.string())


def stale_index(package_root: str | os.PathLike[str]) -> list[PackageProblem]:
    """Where the registry's index part disagrees with the package's sources.

    Rows are matched by ``location`` and ``id``; ``kind``, ``timeline_id``
    and ``name`` are compared. One problem per row, code ``stale_index``,
    file the index part, in this order: the part's rows in their order, an
    extra row (no source holds the ID there, or a repeated row; path
    ``["id"]``) or a differing one (path its first differing column), then
    the missing rows by ``location`` and ``id`` (row ``None``, path
    ``["id"]``). A missing index part lacks every row.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
        ValueError: If ``package.yaml`` lists no table, or two tables, of the
            type ``Registry``, or the registry lies outside the package.
    """
    package = _Package.at(package_root)
    part, file = _index_part(package)
    expected = index_rows(package_root)
    held = _held_rows(part)
    if held is None:
        held = REGISTRY_SCHEMA.empty_table()
    index = pc.indices_nonzero(_is_index(held))
    actual = pa.table(
        {
            "row": index,
            **{name: _strings(held, name).take(index) for name in ("id", "location")},
            **{
                "actual_" + name: _strings(held, name).take(index) for name in _COMPARED
            },
        }
    )
    sources = pa.table(
        {
            "id": expected.column("id"),
            "location": expected.column("location"),
            "order": pa.array(range(len(expected)), pa.int64()),
            **{"expected_" + name: expected.column(name) for name in _COMPARED},
        }
    )
    first = actual.group_by(["location", "id"], use_threads=False).aggregate(
        [("row", "min")]
    )
    joined = actual.join(first, keys=["location", "id"], join_type="left outer").join(
        sources, keys=["location", "id"], join_type="left outer"
    )
    joined = joined.sort_by("row")
    extra = pc.fill_null(
        pc.or_kleene(
            pc.not_equal(joined.column("row_min"), joined.column("row")),
            pc.is_null(joined.column("order")),
        ),
        True,
    )
    remaining = pc.invert(extra)
    for name in _COMPARED:
        held_column = joined.column("actual_" + name)
        given_column = joined.column("expected_" + name)
        differs = pc.or_(
            pc.xor(pc.is_valid(held_column), pc.is_valid(given_column)),
            pc.fill_null(pc.not_equal(held_column, given_column), False),
        )
        remaining = pc.and_(remaining, pc.invert(differs))
    # Only the rows found stale are read in Python, to word their problems.
    flagged = joined.filter(pc.invert(remaining))
    problems: list[PackageProblem] = []
    for row in flagged.to_pylist():
        repeated = row["row_min"] != row["row"]
        if repeated or row["order"] is None:
            problems.append(
                PackageProblem(
                    "stale_index",
                    file,
                    row["row"],
                    ("id",),
                    f"the index holds the ID '{row['id']}' at '{row['location']}', "
                    "which no manifest or table holds there",
                )
            )
            continue
        for name in _COMPARED:
            held_value, given = row["actual_" + name], row["expected_" + name]
            if held_value != given:
                problems.append(
                    PackageProblem(
                        "stale_index",
                        file,
                        row["row"],
                        (name,),
                        f"the index row of the ID '{row['id']}' at "
                        f"'{row['location']}' has the {name} {held_value!r}, not "
                        f"{given!r}",
                    )
                )
                break
    missing = sources.join(
        first, keys=["location", "id"], join_type="left anti"
    ).sort_by("order")
    for row in missing.select(["id", "location"]).to_pylist():
        problems.append(
            PackageProblem(
                "stale_index",
                file,
                None,
                ("id",),
                f"the index lacks the ID '{row['id']}' at '{row['location']}'",
            )
        )
    return problems


# Resolving.


def _rows_with(registry: pa.Table, id: str) -> pa.Table:
    return registry.filter(pc.equal(_strings(registry, "id"), id))


def _registry_files(
    root: Path, references: Sequence[tuple[str, str]]
) -> list[tuple[str, pa.Table]]:
    """Each registry read, by its path from the package root; a registry
    named twice is read once."""
    read: dict[str, pa.Table] = {}
    for reference, against in references:
        path = _from_root(reference, against)
        if path is None or path in read:
            continue
        read[path] = read_table(root / path, type="Registry")
    return list(read.items())


def _resolution(row: dict[str, Any], manifest: str | None) -> Resolution:
    return Resolution(row["kind"], row["location"], manifest, row)


def _package_root_of(manifest: Path) -> tuple[Path, str]:
    """The root of the package a manifest file lies in, and the manifest's
    URL from it as ``package.yaml`` lists it: the nearest folder above it
    whose ``package.yaml`` lists it, else its own folder."""
    resolved = manifest.resolve()
    for folder in resolved.parents:
        file = folder / PACKAGE_FILE
        if not file.is_file():
            continue
        value = loads(file.read_text(encoding="utf-8"))
        for entry in entries_of(value, "manifests"):
            url = entry.get("url") if isinstance(entry, Mapping) else None
            path = None if not isinstance(url, str) else _from_root(url)
            if path is not None and (folder / path).resolve() == resolved:
                return folder, url
    return resolved.parent, resolved.name


def _through_package(root: Path, id: str) -> list[Resolution]:
    package = _Package.at(root)
    found = []
    for _, registry in _registry_files(root, [(package.registry()["url"], "")]):
        for row in _rows_with(registry, id).to_pylist():
            own = row["location"] if row["kind"] in ELEMENT_KINDS else None
            found.append(_resolution(row, own))
    return found


def _through_manifest(file: Path, id: str) -> list[Resolution]:
    root, location = _package_root_of(file)
    manifest = with_bare_ids(loads(file.read_text(encoding="utf-8")))
    at = _from_root(location) or location
    resources = [
        resource
        for resource in entries_of(manifest, "resources")
        if isinstance(resource, Mapping)
    ]
    registries = _registry_files(
        root,
        [(r["url"], at) for r in resources if r.get("type") == "Registry"],
    )
    rows = (
        pa.concat_tables(
            [registry for _, registry in registries], promote_options="default"
        )
        if registries
        else REGISTRY_SCHEMA.empty_table()
    )
    with_id = _rows_with(rows, id)
    found: list[Resolution] = []
    for _, path in manifest_ids(manifest):
        identifier: Any = manifest
        for step in path:
            identifier = identifier[step]
        if identifier != id:
            continue
        kind = "Manifest" if path == ("id",) else _KINDS[str(path[-3])]
        index = with_id.filter(
            pc.and_(
                pc.equal(_strings(with_id, "location"), location),
                pc.equal(_strings(with_id, "kind"), kind),
            )
        ).to_pylist()
        found.append(Resolution(kind, location, location, index[0] if index else None))
    listed = sorted(
        {
            timeline
            for resource in resources
            if resource.get("type") == "Registry"
            for timeline in entries_of(resource, "timelines")
            if isinstance(timeline, str)
        }
    )
    timelines = pa.array(listed, pa.string())
    kinds = _kinds(with_id)
    events = pc.and_(
        pc.invert(_is_index(with_id)),
        pc.fill_null(pc.is_in(_strings(with_id, "timeline_id"), timelines), False),
    )
    tables = sorted(
        {
            path
            for resource in resources
            if resource.get("type") == "MatchClaim"
            and (path := _from_root(resource["url"], at)) is not None
        }
    )
    claim_locations = [
        held
        for held in pc.unique(_strings(with_id, "location")).to_pylist()
        if held is not None and _from_root(held) in tables
    ]
    claims = pc.and_(
        pc.equal(kinds, "MatchClaim"),
        pc.fill_null(
            pc.is_in(
                _strings(with_id, "location"),
                pa.array(claim_locations, pa.string()),
            ),
            False,
        ),
    )
    named = pc.and_(
        pc.invert(_is_index(rows)),
        pc.and_(
            pc.equal(_strings(rows, "extraction_id"), id),
            pc.fill_null(pc.is_in(_strings(rows, "timeline_id"), timelines), False),
        ),
    )
    extraction = pc.and_(
        pc.equal(kinds, "Extraction"), pa.scalar(bool(pc.any(named).as_py()))
    )
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
    is read as the bare ID, one ``#`` stripped.

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
