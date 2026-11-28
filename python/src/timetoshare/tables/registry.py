"""The registry of a package: its non-event rows, resolving an ID, writing it.

A package's registry is the table of the type ``Registry`` its
``package.yaml`` lists: one Parquet file, one row per resolvable ID. An
**event row** gives an event's position on the axis of the root of its
timeline's family, its parse and its locator; a **non-event row** names
an element of a manifest, a MatchClaim or a Parse by its ``kind`` and
its ``location``. The non-event rows are the rows whose ``kind`` is one of
:data:`~timetoshare.tables.NON_EVENT_KINDS`, a filter on the one file. They
are derived: :func:`non_event_rows` builds them from the manifests, the
MatchClaim tables and the Parse table, :func:`write_non_event_rows`
rewrites them inside the registry file, and :func:`stale_non_event_rows`
lists where the file disagrees with them, as the package check does.
:func:`write_registry` writes a registry file in the order of the format.
:func:`resolve` finds every row of an ID, through a package or through one
of its manifests.

A ``location`` is a URI reference resolved against the package root, the
folder of ``package.yaml`` (a manifest alone: its folder).
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from fractions import Fraction
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
from .checks import TableError, _schema_problems, is_non_event
from .columns import ELEMENT_KINDS, NUMBER_TYPE, REGISTRY_SCHEMA
from .package import (
    _NON_EVENT_ROW,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    PackageProblem,
    _resolved_locations,
    _strings,
    non_event_rows_of,
    read_table,
    stale_problems,
    table_non_event_rows,
)

__all__ = [
    "Resolution",
    "non_event_rows",
    "resolve",
    "stale_non_event_rows",
    "write_non_event_rows",
    "write_registry",
]


@dataclass(frozen=True)
class Resolution:
    """What an ID resolves to.

    Attributes:
        kind: The row's ``kind``: an event type, ``MatchClaim``,
            ``Parse`` or the schema's name of a manifest element.
        location: The row's ``location``, a URI reference against the
            package root; ``None`` for an event whose content lies nowhere
            but its registry row (a Projection, any kind whose events hold
            nothing but their IDs) or is only re-parsable from its parse's
            source file.
        manifest: The manifest the resolution belongs to, its path from the
            package root: the manifest resolved through, or, through the
            package, an element's own manifest; ``None`` otherwise.
        row: The registry row as a dictionary of its columns; ``None`` for
            an element of a manifest without a registry or one the registry
            lacks.
    """

    kind: str
    location: str | None
    manifest: str | None
    row: dict[str, Any] | None


def _not_a_file(url: str) -> ValueError:
    return ValueError(
        f"the registry '{url}' names a folder; a registry is one Parquet file"
    )


def _bare(id: str) -> str:
    """An ID as given: bare, or written ``#id``, of which one ``#`` is stripped."""
    return from_file_id(id) if id.startswith(HASH) else id


@dataclass(frozen=True)
class _Sources:
    """The non-event rows a package's sources give, and the paths from the root
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
                the type ``Registry``, or the one names a folder.
        """
        urls = self.urls("tables", "Registry")
        if len(urls) != 1:
            many = "no table" if not urls else f"{len(urls)} tables"
            raise ValueError(f"{PACKAGE_FILE} lists {many} of the type Registry")
        if urls[0].endswith("/"):
            raise _not_a_file(urls[0])
        return urls[0]

    def sources(self) -> _Sources:
        """The non-event rows of the valid manifests (each at its URL as
        ``package.yaml`` lists it) and of the MatchClaim and Parse
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
            parts.append(non_event_rows_of(with_bare_ids(manifest), url))
        for kind in ("MatchClaim", "Parse"):
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
                parts.append(table_non_event_rows(_strings(table, "id"), kind, url))
        rows = pa.concat_tables(parts) if parts else _NON_EVENT_ROW.empty_table()
        rows = rows.sort_by([("location", "ascending"), ("id", "ascending")])
        return _Sources(rows, frozenset(unread))

    def registry_file(self) -> tuple[Path, str]:
        """The registry file: its path, and its path from the package root."""
        url = self.registry()
        path = package_path(url)
        if path is None:
            raise ValueError(f"the registry '{url}' lies outside the package")
        return self.root / path, path


def _as_registry(table: pa.Table) -> pa.Table:
    """Non-event rows in the registry's columns and order, every other column null."""
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


def non_event_rows(package_root: str | os.PathLike[str]) -> pa.Table:
    """The non-event rows of a package, as its manifests and tables give them.

    One row per element with an ID of each valid manifest ``package.yaml``
    lists (``kind`` the schema's name of the element, ``location`` the
    manifest's URL as ``package.yaml`` lists it, ``timeline_id`` the timeline
    holding a region or a flow-control element and the ``timeline`` of a
    named timestamp or an elision), one per row of each MatchClaim table and
    of the Parse table (``location`` the table entry's URL); built by
    :func:`~timetoshare.tables.package.non_event_rows_of` and
    :func:`~timetoshare.tables.package.table_non_event_rows`, as the package
    check builds them. Every other column is null. The rows are sorted by
    ``location``, then ``id``, by code point.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
    """
    return _as_registry(_Package.at(package_root).sources().rows)


# Writing the registry.


def _held_rows(file: Path) -> pa.Table | None:
    """The rows of a registry file as written; ``None`` for no file."""
    if not file.is_file():
        return None
    return read_table(file, type="Registry")


def _start_values(starts: pa.Array) -> pa.Array:
    """A double per ``start``, equal for equal values and ordered as they are
    wherever two doubles differ: a float's value, an int's or a fraction's
    quotient as a double; null where the cell holds none of them."""
    numerator = pc.cast(pc.struct_field(starts, "numerator"), pa.float64(), safe=False)
    denominator = pc.cast(
        pc.struct_field(starts, "denominator"), pa.float64(), safe=False
    )
    quotient = pc.divide(numerator, pc.coalesce(denominator, pa.scalar(1.0)))
    return pc.coalesce(pc.struct_field(starts, "value"), quotient)


def _is_number(kind: pa.DataType) -> bool:
    """Whether a column holds numbers: a struct of the members of a number,
    of their types, whatever their nullability."""
    return pa.types.is_struct(kind) and [
        (field.name, field.type) for field in kind
    ] == [(field.name, field.type) for field in NUMBER_TYPE]


_NO_RANKS = pa.table(
    {"row": pa.array([], pa.int64()), "rank": pa.array([], pa.int64())}
)


def _exact_ranks(events: pa.Table, order: pa.Table) -> pa.Table:
    """The rank of the exact value of each event row's ``start`` among the
    rows of its timeline whose double (:func:`_start_values`) is the same,
    for the rows where two distinct values share one; the other rows have
    none. Only those rows are read in Python."""
    starts = events.column("start").combine_chunks()
    members = pa.table(
        {
            "timeline": order["timeline"],
            "double": order["double"],
            "numerator": pc.struct_field(starts, "numerator"),
            "denominator": pc.struct_field(starts, "denominator"),
            "value": pc.struct_field(starts, "value"),
            "row": order["row"],
        }
    )
    keys = ["timeline", "double"]
    spellings = members.group_by(
        [*keys, "numerator", "denominator", "value"]
    ).aggregate([])
    shared = spellings.group_by(keys).aggregate([([], "count_all")])
    shared = shared.filter(pc.greater(shared["count_all"], 1)).select(keys)
    if not len(shared):
        return _NO_RANKS
    ambiguous = members.join(shared, keys=keys, join_type="inner").to_pylist()
    groups: dict[tuple[Any, Any], list[tuple[Fraction, int]]] = {}
    for member in ambiguous:
        value = (
            Fraction(member["value"])
            if member["value"] is not None
            else Fraction(member["numerator"], member["denominator"] or 1)
        )
        groups.setdefault((member["timeline"], member["double"]), []).append(
            (value, member["row"])
        )
    ranked_rows: list[int] = []
    ranks: list[int] = []
    for group in groups.values():
        values = sorted({value for value, _ in group})
        for value, row in group:
            ranked_rows.append(row)
            ranks.append(values.index(value))
    return pa.table(
        {"row": pa.array(ranked_rows, pa.int64()), "rank": pa.array(ranks, pa.int64())}
    )


def _event_order(events: pa.Table) -> pa.Array:
    """The order of event rows: by ``timeline_id`` (code point), the exact
    value of ``start``, then ``id``. A ``start`` column that is no number,
    which the registry's table check reports, takes no part, nor does a
    column of another type than strings."""
    numbers = _is_number(events.schema.field("start").type)
    starts = events.column("start").combine_chunks()
    order = pa.table(
        {
            "timeline": _strings(events, "timeline_id"),
            "double": _start_values(starts)
            if numbers
            else pa.nulls(len(events), pa.float64()),
            "id": _strings(events, "id"),
            "row": pa.array(range(len(events)), pa.int64()),
        }
    )
    ranks = _exact_ranks(events, order) if numbers else _NO_RANKS
    if len(ranks):
        order = order.join(ranks, keys="row", join_type="left outer")
    else:
        order = order.append_column("rank", pa.nulls(len(order), pa.int64()))
    order = order.set_column(
        order.schema.get_field_index("rank"),
        "rank",
        pc.fill_null(order["rank"], 0),
    )
    order = order.sort_by(
        [
            ("timeline", "ascending"),
            ("double", "ascending"),
            ("rank", "ascending"),
            ("id", "ascending"),
        ]
    )
    return order["row"].combine_chunks()


def _in_order(table: pa.Table) -> pa.Table:
    """A registry's rows in the order of the format: the non-event rows by
    ``location``, then ``id``; then the event rows (:func:`_event_order`)."""
    non_event = is_non_event(_strings(table, "kind"))
    non_events = table.filter(non_event).sort_by(
        [("location", "ascending"), ("id", "ascending")]
    )
    events = table.filter(pc.invert(non_event))
    events = events.take(_event_order(events))
    return pa.concat_tables([non_events, events])


def write_registry(rows: pa.Table, path: str | os.PathLike[str]) -> Path:
    """Write a registry file: every row, in the order of the format.

    The non-event rows come first, sorted by ``location``, then ``id``; then
    the event rows, sorted by ``timeline_id``, the exact value of ``start``
    (``2/4`` and ``1/2`` are one value), then ``id``; strings by code point,
    nulls last. Readers never rely on the order. Every value is written as
    given, a further column included; a column of the registry the table
    lacks is written null. The file states the type ``Registry`` and the
    format version in its metadata, beside the table's own, and is written
    under a name starting with ``.`` beside ``path``, then renamed over it.

    Args:
        rows: The registry's rows, every one, non-event and event rows alike.
        path: The registry file.

    Returns:
        The path written.
    """
    target = Path(path)
    table = _in_order(_with_registry_columns(rows))
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
    return target


def _with_registry_columns(table: pa.Table) -> pa.Table:
    """A table with every column of the registry, those it lacks null, in the
    registry's order, then its further columns."""
    for field in REGISTRY_SCHEMA:
        if field.name not in table.column_names:
            table = table.append_column(field, pa.nulls(len(table), field.type))
    further = [name for name in table.column_names if name not in REGISTRY_SCHEMA.names]
    return table.select([*REGISTRY_SCHEMA.names, *further])


def _at_unread(table: pa.Table, unread: Iterable[str]) -> pa.Array:
    """Where a row's ``location`` resolves to a manifest or table that could
    not be read."""
    paths = _resolved_locations(_strings(table, "location"))
    gone = pa.array(sorted(unread), pa.string())
    return pc.fill_null(pc.is_in(paths, value_set=gone), False)


def write_non_event_rows(package_root: str | os.PathLike[str]) -> Path:
    """Rewrite the non-event rows inside the registry file from the
    package's sources.

    The file then holds the non-event rows of :func:`non_event_rows`, with
    the non-event rows it held at a manifest or table that could not be read,
    which cannot be rebuilt and are kept as they were; and every row it held
    that is no non-event row, each with its values unchanged, so that no
    event row is lost. It is written whole by :func:`write_registry`, in the
    order of the format; a missing file is written with the non-event rows
    alone.

    Returns:
        The path of the registry file.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
        ValueError: If ``package.yaml`` lists no table, or two tables, of the
            type ``Registry``, or the registry names a folder or lies outside
            the package.
    """
    package = _Package.at(package_root)
    file, _ = package.registry_file()
    sources = package.sources()
    parts = [_as_registry(sources.rows)]
    held = _held_rows(file)
    if held is not None:
        held = held.replace_schema_metadata(None)
        non_event = is_non_event(_strings(held, "kind"))
        non_events = held.filter(non_event)
        parts.append(non_events.filter(_at_unread(non_events, sources.unread)))
        parts.append(held.filter(pc.invert(non_event)))
    rows = pa.concat_tables(parts, promote_options="default")
    return write_registry(rows, file)


def stale_non_event_rows(
    package_root: str | os.PathLike[str],
) -> list[PackageProblem]:
    """Where the registry file's non-event rows disagree with the package's
    sources.

    The non-event rows of the file are compared with :func:`non_event_rows`
    by :func:`~timetoshare.tables.package.stale_problems`, the comparison the
    package check makes, so that this list is the package check's
    ``stale_non_event_row`` problems, each in the registry file (its path
    from the package root) at its row there: rows matched by ``id`` and
    ``location`` resolved against the package root, ``kind`` and
    ``timeline_id`` compared, rows at a manifest or table that could not be
    read not compared. A missing file lacks every row; a file whose columns
    are not the registry's has none compared, its table check's to report.

    Raises:
        FileNotFoundError: If ``package_root`` holds no ``package.yaml``.
        ValueError: If ``package.yaml`` lists no table, or two tables, of the
            type ``Registry``, or the registry names a folder or lies outside
            the package.
    """
    package = _Package.at(package_root)
    file, at = package.registry_file()
    sources = package.sources()
    held = _held_rows(file)
    if held is None or _schema_problems(held.schema.empty_table(), REGISTRY_SCHEMA):
        held = REGISTRY_SCHEMA.empty_table()
    rows = pc.indices_nonzero(is_non_event(_strings(held, "kind")))
    non_events = pa.table(
        {
            **{name: _strings(held, name).take(rows) for name in _NON_EVENT_ROW.names},
            "row": rows.cast(pa.int64()),
        }
    )
    return stale_problems(non_events, sources.rows, at, sources.unread)


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


def _names_parse(root: Path, paths: Iterable[str], id: str, listed: pa.Array) -> bool:
    """Whether an event row of the ``listed`` timelines in one of the
    registries names the parse ``id``: the rows of those timelines read
    in their ``parse_id`` alone, the timeline filter pushed into the
    reader."""
    for path in dict.fromkeys(paths):
        rows = read_table(
            root / path,
            type="Registry",
            timelines=listed.to_pylist(),
            columns=["parse_id"],
        )
        if pc.any(pc.equal(_strings(rows, "parse_id"), id)).as_py():
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

    for resource in resources:
        if resource.get("type") == "Registry" and str(resource["url"]).endswith("/"):
            raise _not_a_file(resource["url"])
    registries = paths("Registry")
    with_id = _rows_with(root, registries, id)
    resolved = _resolved_locations(_strings(with_id, "location"))
    kinds = _strings(with_id, "kind")
    found: list[Resolution] = []
    elements = non_event_rows_of(manifest, location)
    for element in elements.filter(pc.equal(elements["id"], id)).to_pylist():
        held = with_id.filter(
            pc.fill_null(
                pc.and_(pc.equal(resolved, at), pc.equal(kinds, element["kind"])), False
            )
        ).to_pylist()
        found.append(
            Resolution(element["kind"], location, location, held[0] if held else None)
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
    event = pc.invert(is_non_event(kinds))
    events = pc.and_(
        event, pc.fill_null(pc.is_in(_strings(with_id, "timeline_id"), listed), False)
    )
    tables = pa.array(sorted(set(paths("MatchClaim"))), pa.string())
    claims = pc.and_(
        pc.equal(kinds, "MatchClaim"),
        pc.fill_null(pc.is_in(resolved, value_set=tables), False),
    )
    parse = pc.equal(kinds, "Parse")
    if pc.any(parse).as_py() and not _names_parse(root, registries, id, listed):
        parse = pc.and_(parse, pa.scalar(False))
    for mask in (events, claims, parse):
        for row in with_id.filter(pc.fill_null(mask, False)).to_pylist():
            found.append(_resolution(row, location))
    return found


def resolve(path: str | os.PathLike[str], id: str) -> list[Resolution]:
    """Every resolution of an ID, through a package or one of its manifests.

    Through a package root (a folder holding ``package.yaml``): every row of
    its registry with the ID, an element's with its manifest. Through a
    manifest file: the element of the manifest with the ID first (with its
    non-event row, or ``None`` without a registry or where the registry
    lacks it),
    then the rows of its Registry resources' registries that belong to it:
    an event row on a timeline those resources list, a MatchClaim row of a
    table its MatchClaim resources name, a Parse row one of its event
    rows names; each with the manifest. The ID is bare; a written ``#id``
    is read as the bare ID, one ``#`` stripped. Each registry is read with
    the filter of the ID pushed into the reader (``read_table(ids=...)``);
    a Parse row found through a manifest is checked against the
    ``parse_id`` of the event rows of the timelines listed, read with
    the timeline filter pushed in.

    Returns:
        The resolutions; an empty list where nothing holds the ID.

    Raises:
        FileNotFoundError: If ``path`` is neither a package root nor a file.
        ValueError: If a package root's ``package.yaml`` lists no table, or
            two tables, of the type ``Registry``, or a registry the package or
            the manifest names is a folder.
    """
    bare = _bare(id)
    path = Path(path)
    if path.is_dir():
        return _through_package(path, bare)
    if not path.is_file():
        raise FileNotFoundError(f"no package or manifest lies at '{path}'")
    return _through_manifest(path, bare)
