"""The tables of a package: reading a table, and checking a package whole.

A package is a folder with ``package.yaml`` at its root, which lists the
package's manifests and its tables (:func:`timetoshare.validate_package`),
its registry among them. A table is a file, or a folder of files read as one
table when its URL ends in ``/``: its files are the names ending in
``.parquet`` directly inside it, none starting with ``.`` or ``_``
(:func:`table_files`). Files may hold the rows of several manifests; a
manifest finds its rows by the timelines its resources list, a row by its
ID (:func:`read_table`).

A file states in its metadata its type (``timetoshare:type``) and its format
version (``timetoshare:version``); a MatchClaim file may state a provenance
every row shares (``timetoshare:provenance``). Nothing else of a file's
metadata is read.
"""

from __future__ import annotations

import os
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from .._urls import PACKAGE_FILE, package_path
from ..ids import with_bare_ids
from ..serialization import loads
from ..validate import (
    SCHEMA_VERSION,
    SchemaValidationError,
    UnsupportedVersionError,
    data_root,
    validate,
    validate_package,
)
from ..validation.diagnostics import (
    ValidationCode,
    axes_by_id,
    entries_of,
    json_pointer,
    manifest_ids,
    number_type_of,
)
from .checks import (
    EVENT_TIMELINES,
    MATCH_CLAIM_TIMELINES,
    TableCode,
    TableError,
    TableProblem,
    _all,
    _array,
    _axis_admitted,
    _dense,
    _first_rows,
    _firsts,
    _held,
    _schema_problems,
    _shape,
    _shared_provenance,
    is_non_event,
    match_claim_problems,
    parse_problems,
    registry_problems,
)
from .columns import (
    ELEMENT_KINDS,
    MATCH_CLAIM_SCHEMA,
    PARSE_SCHEMA,
    PROVENANCE_METADATA_KEY,
    REGISTRY_SCHEMA,
)

__all__ = [
    "PACKAGE_FILE",
    "TYPE_METADATA_KEY",
    "VERSION_METADATA_KEY",
    "PackageCode",
    "PackageProblem",
    "package_fixture_path",
    "package_problems",
    "is_table_resource",
    "non_event_rows_of",
    "read_table",
    "stale_problems",
    "table_files",
    "table_non_event_rows",
]

TYPE_METADATA_KEY = "timetoshare:type"
"""The schema-metadata key holding a file's table type, such as ``Registry``."""

VERSION_METADATA_KEY = "timetoshare:version"
"""The schema-metadata key holding the format version of a file."""

PackageCode = Literal[
    "missing_file",
    "missing_registry",
    "duplicate_registry",
    "registry_not_a_file",
    "duplicate_table",
    "table_type",
    "column_type_mismatch",
    "version_mismatch",
    "unknown_table",
    "duplicate_id",
    "unknown_timeline",
    "unlisted_timeline",
    "claim_across_manifests",
    "axis_mismatch",
    "unknown_parse",
    "unknown_location",
    "missing_content",
    "unregistered_id",
    "stale_non_event_row",
    "foreign_table",
]
"""The codes of the package check's own rules. A package problem may also
carry the code of a manifest's validation (``timetoshare.ValidationCode``)
or of a table check (:data:`~timetoshare.tables.TableCode`); two package
rules use such codes as well: ``duplicate_url`` for a file two table entries
reach, ``schema_violation`` for a row whose timeline is null."""

ProblemCode = PackageCode | TableCode | ValidationCode
"""The code of a package problem: a package rule's, a table check's or a
manifest validation's."""

Path_ = tuple[str | int, ...]


@dataclass(frozen=True)
class PackageProblem:
    """One problem of a package: its code, the file it lies in (its path
    from the package's root, ``/``-separated: ``package.yaml``, a manifest,
    a table's file, or a table's folder for what its files share), the row
    of that file (``None`` for no single row), the path of the member at
    fault (a JSON path in ``package.yaml`` or a manifest, the column path of
    a table's row) and its message."""

    code: ProblemCode
    file: str
    row: int | None
    path: Path_
    message: str


def package_fixture_path(*parts: str) -> Path:
    """The path of a package fixture, or of a file in it: ``shared``, the
    package of two manifests sharing their registry and tables,
    ``acceptances/<case>`` or ``rejections/<case>``, each beside an
    ``expected.yaml``."""
    return data_root().joinpath("fixtures", "packages", SCHEMA_VERSION, *parts)


def table_files(path: str | os.PathLike[str]) -> list[Path]:
    """The files of a table: the file itself, or a folder's files.

    A folder's files are the names ending in ``.parquet`` directly inside
    it, not in its subfolders, none starting with ``.`` or ``_`` (a file
    being written, a ``_delta_log``), sorted by code point.

    Raises:
        FileNotFoundError: If ``path`` is neither a file nor a folder.
    """
    path = Path(path)
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"no table file or folder at '{path}'")
    return sorted(
        (
            child
            for child in path.iterdir()
            if child.name.endswith(".parquet")
            and not child.name.startswith((".", "_"))
            and child.is_file()
        ),
        key=lambda child: child.name,
    )


def _metadata(schema: pa.Schema, key: str) -> str | None:
    value = (schema.metadata or {}).get(key.encode())
    return None if value is None else value.decode("utf-8", "replace")


def _table_type(
    files: Sequence[Path], schemas: Sequence[pa.Schema], kind: str | None
) -> str:
    """The type of a table: what its files' metadata state, else ``kind``.

    Raises:
        TableError: If two files state two types, a file states another
            type than ``kind``, or neither a file nor ``kind`` states one
            (``table_type``).
    """
    stated: dict[str, str] = {}
    for file, schema in zip(files, schemas, strict=True):
        named = _metadata(schema, TYPE_METADATA_KEY)
        if named is not None:
            stated.setdefault(named, file.name)
    if len(stated) > 1:
        (first, at), (second, again) = list(stated.items())[:2]
        message = f"'{at}' holds the type {first} and '{again}' the type {second}"
    elif stated and kind is not None and kind not in stated:
        ((named, at),) = stated.items()
        message = f"'{at}' holds the type {named}, not {kind}"
    elif stated:
        return next(iter(stated))
    elif kind is None:
        message = f"the table names no type: no file states '{TYPE_METADATA_KEY}'"
    else:
        return kind
    raise TableError(TableProblem("table_type", None, (), message))


def _unified(files: Sequence[Path], schemas: Sequence[pa.Schema]) -> pa.Schema:
    """The schema the files are read as one table in: every column of every
    file, by name, in the order first met.

    Raises:
        TableError: If one column name has two types in two files
            (``column_type_mismatch``); nullability and the names of list
            items are not compared.
    """
    fields: dict[str, tuple[pa.Field, str]] = {}
    for file, schema in zip(files, schemas, strict=True):
        for field in schema:
            held = fields.get(field.name)
            if held is None:
                fields[field.name] = (field, file.name)
            elif _shape(held[0].type) != _shape(field.type):
                raise TableError(
                    TableProblem(
                        "column_type_mismatch",
                        None,
                        (field.name,),
                        f"the column '{field.name}' is {held[0].type} in "
                        f"'{held[1]}' and {field.type} in '{file.name}'",
                    )
                )
    return pa.schema([field for field, _ in fields.values()])


def _with_shared_provenance(
    part: pa.Table, schema: pa.Schema, file: Path, offset: int
) -> pa.Table:
    """A MatchClaim file's rows with the provenance its metadata states for
    every row filled into their ``provenance``.

    Raises:
        TableError: If the file's provenance is no provenance entry, or a
            row states its own beside it (``invalid_provenance``; the row
            counted from ``offset``); if its ``provenance`` column is of
            another type than the declared one, which the shared provenance
            cannot be filled into (``schema_violation``).
    """
    if PROVENANCE_METADATA_KEY.encode() not in (schema.metadata or {}):
        return part
    cell, problem = _shared_provenance(
        pa.schema([], metadata=schema.metadata).empty_table()
    )
    if problem:
        message = f"{problem}, in '{file.name}'"
        raise TableError(
            TableProblem("invalid_provenance", None, ("provenance",), message)
        )
    if "provenance" not in part.column_names:
        return part
    index = part.schema.get_field_index("provenance")
    field = part.schema.field(index)
    declared = MATCH_CLAIM_SCHEMA.field("provenance").type
    if _shape(field.type) != _shape(declared):
        raise TableError(
            TableProblem(
                "schema_violation",
                None,
                ("provenance",),
                f"the column 'provenance' is {field.type}, not {declared}, in "
                f"'{file.name}'",
            )
        )
    # One array: a filter may leave a column of no chunks, on which
    # ``indices_nonzero`` crashes the process (pyarrow 25).
    stated = pc.indices_nonzero(pc.is_valid(part.column(index).combine_chunks()))
    if len(stated):
        raise TableError(
            TableProblem(
                "invalid_provenance",
                offset + stated[0].as_py(),
                ("provenance",),
                "the provenance is stated in the file's metadata and in the row",
            )
        )
    filled = pa.repeat(pa.scalar(cell, field.type), len(part))
    return part.set_column(index, field, filled)


def _timeline_columns(kind: str) -> tuple[str, ...]:
    """The columns naming a row's timelines in a table of ``kind``."""
    return MATCH_CLAIM_TIMELINES if kind == "MatchClaim" else EVENT_TIMELINES


def _rows_of(
    kind: str, timelines: Iterable[str] | None, ids: Iterable[str] | None = None
) -> ds.Expression | None:
    """The filter keeping the rows of ``timelines`` (an event row's own
    timeline, either timeline of a MatchClaim) and of ``ids``, both where
    both are given."""
    expression = None
    if timelines is not None:
        listed = pa.array(list(timelines), pa.string())
        columns = _timeline_columns(kind)
        expression = ds.field(columns[0]).isin(listed)
        for column in columns[1:]:
            expression = expression | ds.field(column).isin(listed)
    if ids is not None:
        kept = ds.field("id").isin(pa.array(list(ids), pa.string()))
        expression = kept if expression is None else expression & kept
    return expression


@dataclass(frozen=True)
class _Read:
    """A table read from its files, each part with its file and its length."""

    table: pa.Table
    lengths: list[int]


def _read(
    files: Sequence[Path],
    schemas: Sequence[pa.Schema],
    kind: str,
    timelines: Iterable[str] | None = None,
    columns: Sequence[str] | None = None,
    ids: Iterable[str] | None = None,
) -> _Read:
    """The files read as one table of ``kind``, file by file in order.

    The files' schemas are unified by name, a column a file lacks read as
    null, and no file reads as no row in the columns of a type the format
    declares; the filter of ``timelines`` and ``ids`` is pushed into the
    reader, and only ``columns`` (those the files hold) are read where
    given. A MatchClaim file's shared provenance is filled into its rows
    before the files are joined, unless only ``columns`` are read.
    """
    schema = _unified(files, schemas) if files else _DECLARED.get(kind, pa.schema([]))
    expression = _rows_of(kind, timelines, ids)
    needed = (*(_timeline_columns(kind) if timelines is not None else ()),)
    needed += ("id",) if ids is not None else ()
    for name in needed:
        if name not in schema.names:
            raise TableError(
                TableProblem(
                    "schema_violation",
                    None,
                    (name,),
                    f"the table has no column '{name}'",
                )
            )
    names = None
    if columns is not None:
        names = [name for name in columns if name in schema.names]
    dataset = ds.dataset([str(file) for file in files], schema=schema, format="parquet")
    parts: list[pa.Table] = []
    offset = 0
    for fragment, file, own in zip(
        dataset.get_fragments(), files, schemas, strict=True
    ):
        part = fragment.to_table(schema=schema, columns=names, filter=expression)
        if kind == "MatchClaim" and columns is None:
            part = _with_shared_provenance(part, own, file, offset)
        parts.append(part)
        offset += len(part)
    if parts:
        table = pa.concat_tables(parts)
    else:
        table = (
            schema.empty_table()
            if names is None
            else schema.empty_table().select(names)
        )
    return _Read(table, [len(part) for part in parts])


_DECLARED = {
    "Registry": REGISTRY_SCHEMA,
    "Parse": PARSE_SCHEMA,
    "MatchClaim": MATCH_CLAIM_SCHEMA,
}
"""The table types the format defines, with their declared columns."""


def read_table(
    path: str | os.PathLike[str],
    *,
    timelines: Iterable[str] | None = None,
    ids: Iterable[str] | None = None,
    columns: Sequence[str] | None = None,
    type: str | None = None,  # noqa: A002 - the word the format uses
) -> pa.Table:
    """Read a table, a file or a folder of files, as one Arrow table.

    The files of a folder are :func:`table_files`'; they are read through
    ``pyarrow.dataset``, their schemas unified by name, a column a file
    lacks read as null. ``timelines`` (bare IDs) keeps, in the reader, the
    rows of those timelines: a registry row whose ``timeline_id`` is listed,
    a MatchClaim's either of whose timelines is, so that a check sees a
    MatchClaim reaching outside them. ``ids`` (bare IDs) keeps, in the
    reader, the rows whose ``id`` is listed: a registry's rows of an ID, a
    pre-parsed table's content of some events; given both, a row is kept
    where both keep it. ``columns`` reads only those columns, of those the
    files hold, in their order; the filters may name others. A MatchClaim
    file's shared provenance (``timetoshare:provenance``) is filled into
    its own rows before the files are joined, unless ``columns`` are given.
    The order of the rows is the files' order, then each
    file's; readers never rely on it.

    The table's type is what its files state (``timetoshare:type``), else
    ``type``; where both are stated they agree. The table returned states
    its type alone in its metadata. An empty folder gives no rows, in the
    declared columns of a type the format declares (``Registry``,
    ``Parse``, ``MatchClaim``), in none for another
    type.

    Raises:
        FileNotFoundError: If ``path`` is neither a file nor a folder.
        TableError: If the files state two types, or another type than
            ``type``, or neither states one (``table_type``); if one column
            has two Arrow types in two files (``column_type_mismatch``); if
            ``timelines`` is given and the files lack a column naming a
            row's timeline, or ``ids`` is given and they lack ``id``
            (``schema_violation``); if a MatchClaim file's
            provenance is unreadable or a row states its own beside it
            (``invalid_provenance``); if a MatchClaim file stating a shared
            provenance has a ``provenance`` column of another type than the
            declared one (``schema_violation``).
    """
    files = table_files(path)
    schemas = [pq.read_schema(file) for file in files]
    kind = _table_type(files, schemas, type)
    if not files:
        table = _DECLARED.get(kind, pa.schema([])).empty_table()
        if columns is not None:
            table = table.select(
                [name for name in columns if name in table.column_names]
            )
    else:
        table = _read(files, schemas, kind, timelines, columns=columns, ids=ids).table
    return table.replace_schema_metadata({TYPE_METADATA_KEY: kind})


# The package check.

_PARQUET = "application/vnd.apache.parquet"
"""The media type of a Parquet file."""


def is_table_resource(resource: Mapping[str, Any]) -> bool:
    """Whether a resource of a manifest names a table.

    A resource names a table when its type is one the format declares
    (``Registry``, ``Parse``, ``MatchClaim``), its URL
    names a folder (ends in ``/``) or a Parquet file
    (ends in ``.parquet``), or its media type is Parquet's. Any other
    resource, a recording, an image or a score file, is carried with its
    manifest and names no table. This is the one rule of the format; a
    package lists a table entry for every table resource of its manifests.

    Args:
        resource: The resource as a manifest holds it: its ``type`` and
            ``url``, and its ``media_type`` where stated.

    Returns:
        ``True`` if the resource names a table.

    Examples:
        >>> is_table_resource({"type": "Note", "url": "Note.parquet"})
        True
        >>> is_table_resource({"type": "Audio", "url": "take.flac"})
        False
    """
    if resource["type"] in _DECLARED or resource.get("media_type") == _PARQUET:
        return True
    return urlsplit(resource["url"]).path.endswith(("/", ".parquet"))


@dataclass(frozen=True)
class _Manifest:
    """A manifest of the package: its path, as read, and with bare IDs."""

    file: str
    value: Mapping[str, Any]
    bare: Mapping[str, Any]


@dataclass
class _Entry:
    """A table entry of ``package.yaml`` whose files could be read."""

    index: int
    kind: str
    url: str
    files: list[Path]
    names: list[str]
    schemas: list[pa.Schema]


class _Problems:
    """The problems found, in the order they are added."""

    def __init__(self) -> None:
        self.found: list[PackageProblem] = []

    def add(
        self, code: ProblemCode, file: str, row: int | None, path: Path_, message: str
    ) -> None:
        self.found.append(PackageProblem(code, file, row, path, message))


def _axis(timeline: Mapping[str, Any]) -> tuple[str | None, str | None]:
    try:
        return timeline.get("unit"), number_type_of(timeline)
    except (KeyError, TypeError):
        return timeline.get("unit"), None


def _arange(length: int) -> pa.Array:
    return pa.array(range(length), pa.int64())


def _version_text(version: Any) -> str:
    return repr(version) if isinstance(version, str) else str(version)


def package_problems(path: str | os.PathLike[str]) -> list[PackageProblem]:
    """Every problem of a package, ``path`` its ``package.yaml``.

    First ``package.yaml`` itself (:func:`timetoshare.validate_package`; a
    problem there ends the check, another version being
    ``version_mismatch``), then its registry: no table of the type
    ``Registry`` (``missing_registry``, at ``tables``) or a second one
    (``duplicate_registry``), at the later entry's ``type``; only the first
    is read. Of every other type a package lists at most one local table,
    an entry whose URL is a relative reference inside the package (a file or
    a folder), and any number of external ones, whose URL is an absolute
    URI, which the check does not follow; a second local one is
    ``duplicate_table``, at its ``type``. A relative URL leading outside
    the package is neither, and names no table (``missing_file``). A
    Registry entry whose URL names a folder (ends in
    ``/``) is no registry: the registry is one Parquet file
    (``registry_not_a_file``, at the entry's ``url``; nothing at the URL is
    read). Then, manifest by manifest as listed, a file that
    is missing (``missing_file``) or that is no valid manifest (its
    validation's code and path; another version ``version_mismatch``).
    Then, table by table and file by file, a file or folder that is missing
    (``missing_file``), a file an earlier entry of the same type reaches
    already, a file entry inside a listed folder for instance
    (``duplicate_url``, at the later entry's ``url``; the later entry reads
    its other files only), a file stating another type (``table_type``) or
    another version (``version_mismatch``) than its entry and the package,
    a column of two Arrow types in two files (``column_type_mismatch``, at
    the folder; its rows are not read), and a table of another type than
    ``Registry``, ``Parse`` and ``MatchClaim`` whose files hold no
    ``id`` column of strings, a carried table of audio features for instance
    (``foreign_table``, at the table; its rows are not read, and no location
    or resource naming it is checked against its rows). Then the rules the manifests and
    the rows keep together, each over every row in the order of the
    entries, their files and their rows:

    - ``registry_not_a_file``: a manifest's ``Registry`` resource whose URL
      names a folder, at its ``url``;
    - ``unknown_table``: a manifest's table resource whose URL names no
      table entry of the resource's type, or leads outside the package
      (:func:`is_table_resource`); any other resource, a recording, an
      image or a score file, is carried and not checked against the tables;
    - ``duplicate_id``: in the registry, an event, MatchClaim or Parse
      ID held twice among all of these rows, a manifest element's ID twice
      at one ``location``; an event ID twice among the rows of the
      pre-parsed tables, every type and file; a MatchClaim ID twice among
      the MatchClaims; each at the later row;
    - ``schema_violation``, then ``unknown_timeline``: an event row's
      timeline, and a MatchClaim's either, column by column, that is null
      (``'timeline_id' is null``) or that no manifest holds;
    - ``unlisted_timeline``: an event row's timeline that no manifest's
      ``Registry`` resource naming the registry lists, a MatchClaim's that
      no manifest's ``MatchClaim`` resource naming its table lists;
    - ``axis_mismatch``: an event row whose unit and number type are not
      its timeline's in a manifest holding it, once per distinct axis;
    - ``unknown_parse``: an event row's ``parse_id`` or
      ``vanished_in`` naming no row of the Parse table;
    - ``unknown_location``: an event row's ``location``, a relative
      reference, naming no table entry of the row's kind; a ``location``
      that is an absolute URI names a resource outside the package and is
      not checked;
    - ``missing_content``: an event row whose location's table holds no row
      of its ID;
    - ``unregistered_id``: a row of a pre-parsed table whose ID has no
      event row of the table's type;
    - ``stale_non_event_row``: a non-event row of the registry that no
      manifest element, MatchClaim or parse gives at its location (an
      extra row), or whose ``kind`` or ``timeline_id`` differs from what
      they give, in the registry's order; then each non-event row they give
      that the registry lacks, by location and ID (a missing row). A
      manifest or table that could not be read gives no row and has none
      compared;
    - ``claim_across_manifests``: a MatchClaim whose two timelines no one
      manifest holds.

    These read the identifying columns of each table, column by column, the
    registry's from the one reading of it whole its table check uses. Last,
    the table checks: of the registry (:func:`registry_problems`, given the
    timelines of every manifest as those a Projection's ``projection_of``
    may name, so that one naming a timeline no manifest holds is
    ``unknown_timeline``; its ``axis_mismatch``, a matter of the manifests,
    is the package rule's), the Parse table (:func:`parse_problems`), each
    once and whole;
    then, manifest by manifest, of each MatchClaim table its resources name,
    in the order they first name it, over the rows of the timelines those
    resources list (:func:`match_claim_problems`): each row's manifests are
    found once and the rows ordered by manifest, so each manifest is checked
    on its own rows alone. Each problem is placed in its file and row; a
    problem a package rule already reports at the same file, row and column
    with the same code, or an ``unknown_timeline`` on a MatchClaim reaching
    another manifest, is not repeated.

    Raises:
        FileNotFoundError: If ``path`` is no file.
        ValueError: If ``package.yaml`` or a manifest is no readable text
            in a serialization of the format.
    """
    path = Path(path)
    root = path.parent
    problems = _Problems()
    value = loads(path.read_text(encoding="utf-8"))
    try:
        validate_package(value)
    except UnsupportedVersionError as error:
        problems.add(
            "version_mismatch", PACKAGE_FILE, None, ("timetoshare",), str(error)
        )
        return problems.found
    except SchemaValidationError as error:
        problems.add(error.code, PACKAGE_FILE, None, error.path, error.message)
        return problems.found
    _one_table_per_type(value, problems)
    version = value["timetoshare"]
    manifests, unread = _manifests(root, value, problems)
    entries = _entries(root, value, version, problems)
    listed = {
        (url, entry["type"])
        for entry in value["tables"]
        if (url := package_path(entry["url"], "")) is not None
    }
    _Check(listed, manifests, unread, entries, problems).run()
    return problems.found


def _is_external(url: str) -> bool:
    """Whether a URL of the package is an absolute URI, naming a resource
    outside the package that the check does not follow."""
    return bool(urlsplit(url).scheme)


def _one_table_per_type(value: Mapping[str, Any], problems: _Problems) -> None:
    """``missing_registry`` and ``duplicate_registry`` over every Registry
    entry; ``duplicate_table`` over the local entries of every other type."""
    by_type: dict[str, list[int]] = {}
    for index, entry in enumerate(value["tables"]):
        kind = entry["type"]
        if kind == "Registry" or (
            not _is_external(entry["url"])
            and package_path(entry["url"], "") is not None
        ):
            by_type.setdefault(kind, []).append(index)
    if "Registry" not in by_type:
        problems.add(
            "missing_registry",
            PACKAGE_FILE,
            None,
            ("tables",),
            "the package lists no table of the type Registry",
        )
    for kind, indices in by_type.items():
        registry = kind == "Registry"
        for later in indices[1:]:
            problems.add(
                "duplicate_registry" if registry else "duplicate_table",
                PACKAGE_FILE,
                None,
                ("tables", later, "type"),
                f"the package lists a second {'' if registry else 'local '}table "
                f"of the type {kind}, first at "
                f"{json_pointer(('tables', indices[0], 'type'))}",
            )


def _manifests(
    root: Path, value: Mapping[str, Any], problems: _Problems
) -> tuple[list[_Manifest], set[str]]:
    """The manifests ``package.yaml`` lists that are valid, in its order, and
    the paths of those listed that could not be read as one."""
    found = []
    unread: set[str] = set()
    for index, entry in enumerate(value["manifests"]):
        file = package_path(entry["url"], "")
        if file is None or not (root / file).is_file():
            problems.add(
                "missing_file",
                PACKAGE_FILE,
                None,
                ("manifests", index, "url"),
                f"no manifest lies at '{entry['url']}' in the package",
            )
            if file is not None:
                unread.add(file)
            continue
        manifest = loads((root / file).read_text(encoding="utf-8"))
        try:
            validate(manifest)
        except UnsupportedVersionError as error:
            problems.add(
                "version_mismatch",
                file,
                None,
                ("timetoshare",),
                f"the manifest declares the version {_version_text(error.version)}, "
                f"the package {value['timetoshare']!r}",
            )
            unread.add(file)
            continue
        except SchemaValidationError as error:
            problems.add(error.code, file, None, error.path, error.message)
            unread.add(file)
            continue
        found.append(_Manifest(file, manifest, with_bare_ids(manifest)))
    return found, unread


_NOT_A_FILE = "the registry '{url}' names a folder; a registry is one Parquet file"
"""The message of ``registry_not_a_file``."""


def _entries(
    root: Path, value: Mapping[str, Any], version: str, problems: _Problems
) -> list[_Entry]:
    """The table entries whose files could be read as one table; a file an
    earlier entry of its type reaches already is left to that entry, a
    Registry entry naming a folder (``registry_not_a_file``) and a table of
    events without an ``id`` column of strings (``foreign_table``) are
    reported and not read, an external entry of another type than
    ``Registry`` is not followed."""
    found = []
    reached: dict[tuple[str, str], int] = {}
    for index, entry in enumerate(value["tables"]):
        url = package_path(entry["url"], "")
        folder = entry["url"].endswith("/")
        if folder and entry["type"] == "Registry":
            problems.add(
                "registry_not_a_file",
                PACKAGE_FILE,
                None,
                ("tables", index, "url"),
                _NOT_A_FILE.format(url=entry["url"]),
            )
            continue
        if entry["type"] != "Registry" and _is_external(entry["url"]):
            continue
        target = None if url is None else root / url
        if target is None or not (target.is_dir() if folder else target.is_file()):
            problems.add(
                "missing_file",
                PACKAGE_FILE,
                None,
                ("tables", index, "url"),
                f"no {'folder' if folder else 'file'} lies at '{entry['url']}' in the "
                "package",
            )
            continue
        assert url is not None
        kind = entry["type"]
        files: list[Path] = []
        names: list[str] = []
        for file in table_files(target):
            name = f"{url}{file.name}" if folder else url
            earlier = reached.setdefault((kind, name), index)
            if earlier != index:
                problems.add(
                    "duplicate_url",
                    PACKAGE_FILE,
                    None,
                    ("tables", index, "url"),
                    f"the file '{name}' is read by the table "
                    f"'{value['tables'][earlier]['url']}' already",
                )
                continue
            files.append(file)
            names.append(name)
        if not files and not folder:
            continue
        schemas = [pq.read_schema(file) for file in files]
        for name, schema in zip(names, schemas, strict=True):
            stated = _metadata(schema, TYPE_METADATA_KEY)
            if stated is not None and stated != kind:
                problems.add(
                    "table_type",
                    name,
                    None,
                    (),
                    f"the file holds the type {stated}, its table the type {kind}",
                )
            declared = _metadata(schema, VERSION_METADATA_KEY)
            if declared is not None and declared != version:
                problems.add(
                    "version_mismatch",
                    name,
                    None,
                    (),
                    f"the file declares the version {declared!r}, the package "
                    f"{version!r}",
                )
        try:
            _unified(files, schemas)
        except TableError as error:
            found_problem = error.problem
            problems.add(
                found_problem.code,
                url,
                None,
                found_problem.column,
                found_problem.message,
            )
            continue
        if kind not in _TABLE_KINDS and not all(
            _holds_ids(schema) for schema in schemas
        ):
            problems.add(
                "foreign_table",
                url,
                None,
                (),
                f"the table '{entry['url']}' of type '{kind}' has no 'id' column: a "
                "package's tables hold the registry, the Parse table, "
                "MatchClaim tables and pre-parsed tables of events keyed by 'id'",
            )
            continue
        found.append(_Entry(index, kind, url, files, names, schemas))
    return found


def _holds_ids(schema: pa.Schema) -> bool:
    """Whether a file's columns hold an ``id`` column of strings."""
    index = schema.get_field_index("id")
    return index >= 0 and pa.types.is_string(schema.field(index).type)


@dataclass(frozen=True)
class _Full:
    """An entry's rows read whole: each row's file (an index of the check's
    file names) and row in the file, and each manifest's run of rows."""

    table: pa.Table
    files: pa.Array
    rows: pa.Array
    runs: dict[int, pa.Array]


_REGISTRY_COLUMNS = (
    "id",
    "kind",
    "location",
    "timeline_id",
    "unit",
    "number_type",
    "parse_id",
    "locator",
    "vanished_in",
)
_CLAIM_COLUMNS = ("id", "timeline_a_id", "timeline_b_id")
_COMPARED = ("kind", "timeline_id")
"""The columns of a non-event row compared with what the manifests give."""

_KIND_OF = {
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
"""The kind of a manifest element by the member holding it."""

_ELEMENTS = pa.array(ELEMENT_KINDS, pa.string())
_SEPARATOR = pa.scalar("\x00")
_EMPTY_TEXT = pa.scalar("")


def _any_of(*masks: pa.Array) -> pa.Array:
    result = masks[0]
    for mask in masks[1:]:
        result = pc.or_(result, mask)
    return result


_WHOLE = {
    "Registry": registry_problems,
    "Parse": parse_problems,
}
"""The table checks run once over a whole table."""
_TABLE_KINDS = ("Registry", "Parse", "MatchClaim")
"""The types of the tables that hold no event's content."""


def _at_path(value: Any, path: Path_) -> Any:
    for step in path:
        value = value[step]
    return value


_NON_EVENT_ROW = pa.schema(
    [pa.field(name, pa.string()) for name in ("id", "kind", "location", "timeline_id")]
)
"""The columns of a non-event row its sources give, as
:func:`non_event_rows_of` builds them; every other column of a non-event row
is null."""


def non_event_rows_of(manifest: Mapping[str, Any], location: str) -> pa.Table:
    """The non-event rows a valid manifest (IDs bare) gives, at ``location``.

    One row per element holding an ID, in the order of
    :func:`~timetoshare.validation.diagnostics.manifest_ids`: ``id``,
    ``kind`` (the schema's name of the element's definition), ``location``,
    ``timeline_id`` (the timeline holding a region or a flow-control
    element, the ``timeline`` of a named timestamp or an elision, else
    null), all strings; the element's name is its manifest's alone."""
    rows = []
    for identifier, path in manifest_ids(manifest):
        element = _at_path(manifest, path[:-1])
        kind = "Manifest" if path == ("id",) else _KIND_OF[path[-3]]
        timeline = None
        if kind in ("Region", "FlowControlElement"):
            timeline = _at_path(manifest, path[:-3])["id"]
        elif kind in ("Timestamp", "Elision"):
            held = element.get("timeline")
            timeline = held if isinstance(held, str) else None
        rows.append(
            {
                "id": identifier,
                "kind": kind,
                "location": location,
                "timeline_id": timeline,
            }
        )
    return pa.Table.from_pylist(rows, schema=_NON_EVENT_ROW)


def table_non_event_rows(
    ids: pa.Array, kind: str, location: str | pa.Array
) -> pa.Table:
    """The non-event rows of the MatchClaims or the parses of a table:
    one per non-null ID of ``ids``, of ``kind`` (``MatchClaim`` or
    ``Parse``), at ``location``, the table entry's URL, one for all
    or one per ID; in the columns of :func:`non_event_rows_of`."""
    kept = pc.is_valid(ids)
    ids = ids.filter(kept)
    if isinstance(location, str):
        locations = pa.repeat(pa.scalar(location, pa.string()), len(ids))
    else:
        locations = location.filter(kept)
    return pa.table(
        {
            "id": ids.cast(pa.string()),
            "kind": pa.repeat(pa.scalar(kind, pa.string()), len(ids)),
            "location": locations.cast(pa.string()),
            "timeline_id": pa.nulls(len(ids), pa.string()),
        },
        schema=_NON_EVENT_ROW,
    )


def _resolved_locations(locations: pa.Array) -> pa.Array:
    """Each location's path from the package root (:func:`package_path`),
    resolved once per distinct location; null where it leads outside."""
    codes = _dense(locations)
    paths = [
        None if value is None else package_path(value)
        for value in locations.take(_firsts(codes)).to_pylist()
    ]
    return pa.array(paths, pa.string()).take(codes)


def stale_problems(
    held: pa.Table, expected: pa.Table, file: str, unread: Collection[str]
) -> list[PackageProblem]:
    """Where the non-event rows held disagree with the non-event rows expected
    (``stale_non_event_row``), one problem per row.

    ``held`` is the non-event part's non-event rows in its order, with their
    ``row`` in the part (int64) beside the columns of
    :func:`non_event_rows_of`; ``expected`` the non-event rows the sources give;
    ``file`` the non-event part's path from the package root; ``unread`` the
    paths from the root of the manifests and tables that could not be read,
    whose rows are not compared. Rows are matched by ``id`` and by
    ``location`` resolved against the package root, so that
    ``./bach.tts.yaml`` and ``bach.tts.yaml`` are one location;
    ``kind`` and ``timeline_id`` are compared. First the held
    rows in their order, an extra one (nothing expected there, or a
    location and ID held again; path ``["id"]``) or a differing one (path
    its first differing column), then each expected row the part lacks, by
    resolved location and ID (row ``None``, path ``["id"]``)."""
    held = held.append_column("order", _arange(len(held)))
    held = held.append_column("resolved", _resolved_locations(_array(held, "location")))
    gone = pa.array(sorted(unread), pa.string())
    held = held.filter(pc.invert(_held(pc.is_in(held["resolved"], value_set=gone))))
    expected = pa.table(
        {
            "id": _array(expected, "id"),
            "resolved": _resolved_locations(_array(expected, "location")),
            **{f"expected_{name}": _array(expected, name) for name in _COMPARED},
            "position": _arange(len(expected)),
        }
    )
    unique = expected.group_by(["id", "resolved"], use_threads=False).aggregate(
        [
            ("position", "min"),
            *((f"expected_{name}", "first") for name in _COMPARED),
        ]
    )
    unique = unique.rename_columns(
        [
            name.removesuffix("_min").removesuffix("_first")
            for name in unique.column_names
        ]
    )
    joined = held.join(unique, keys=["id", "resolved"], join_type="left outer").sort_by(
        "order"
    )
    keys = _dense(
        pc.binary_join_element_wise(
            _array(joined, "id"),
            pc.coalesce(_array(joined, "resolved"), _EMPTY_TEXT),
            _SEPARATOR,
        )
    )
    again = pc.invert(pc.is_in(_arange(len(joined)), value_set=_firsts(keys)))
    extra = pc.or_(pc.is_null(joined["position"]), again)
    differs = {
        name: pc.and_(
            pc.invert(extra),
            _differ(_array(joined, name), _array(joined, f"expected_{name}")),
        )
        for name in _COMPARED
    }
    flagged = joined.append_column("extra", extra)
    for name, mask in differs.items():
        flagged = flagged.append_column(f"differs_{name}", mask)
    # Only the rows found stale are read in Python, to word their problems.
    flagged = flagged.filter(_any_of(extra, *differs.values()))
    problems = []
    for row in flagged.to_pylist():
        if row["extra"]:
            problems.append(
                PackageProblem(
                    "stale_non_event_row",
                    file,
                    row["row"],
                    ("id",),
                    f"the registry holds the non-event row of the ID '{row['id']}' "
                    f"at '{row['location']}', which no manifest or table holds there",
                )
            )
            continue
        column = next(name for name in _COMPARED if row[f"differs_{name}"])
        problems.append(
            PackageProblem(
                "stale_non_event_row",
                file,
                row["row"],
                (column,),
                f"the non-event row of the ID '{row['id']}' at '{row['location']}' "
                f"has the {column} {row[column]!r}, not {row[f'expected_{column}']!r}",
            )
        )
    missing = unique.join(
        held.select(["id", "resolved"]), keys=["id", "resolved"], join_type="left anti"
    )
    missing = missing.filter(pc.is_valid(missing["id"])).sort_by(
        [("resolved", "ascending"), ("id", "ascending")]
    )
    for row in missing.select(["id", "resolved"]).to_pylist():
        problems.append(
            PackageProblem(
                "stale_non_event_row",
                file,
                None,
                ("id",),
                f"the registry lacks the non-event row of the ID '{row['id']}' at "
                f"'{row['resolved']}'",
            )
        )
    return problems


def _differ(old: pa.Array, new: pa.Array) -> pa.Array:
    """Where two string columns differ, a null equal to a null alone."""
    return pc.or_(
        pc.xor(pc.is_null(old), pc.is_null(new)), _held(pc.not_equal(old, new))
    )


class _Check:
    """The package rules over the rows of every table, and the table checks."""

    def __init__(
        self,
        listed: set[tuple[str, str]],
        manifests: list[_Manifest],
        unread: set[str],
        entries: list[_Entry],
        problems: _Problems,
    ) -> None:
        self.listed = listed
        self.manifests = manifests
        self.unread = set(unread)
        self.entries = entries
        self.problems = problems
        self.names = [name for entry in entries for name in entry.names]
        self.first_file = []
        count = 0
        for entry in entries:
            self.first_file.append(count)
            count += len(entry.files)
        read = {(entry.url, entry.kind) for entry in entries}
        self.unread |= {
            url
            for url, kind in listed
            if kind in ("MatchClaim", "Parse") and (url, kind) not in read
        }
        self.registry = next(
            (entry for entry in entries if entry.kind == "Registry"), None
        )
        self.parse = next((entry for entry in entries if entry.kind == "Parse"), None)

    def run(self) -> None:
        self._timelines()
        self._resources()
        registry = self._registry_rows()
        events = registry.filter(pc.invert(is_non_event(registry["kind"])))
        contents = self._rows(_content=True)
        claims = self._rows(_content=False)
        parses = self._column_rows(self.parse, "id")
        self._registry_duplicates(registry)
        self._duplicates(contents, "event ID")
        self._duplicates(claims, "MatchClaim ID")
        self._unknown(events, ("timeline_id",))
        self._unlisted(events, ("timeline_id",))
        self._axes(events)
        self._parses(events, parses)
        located = self._locations(events)
        self._content(events, located, contents)
        self._stale(registry, claims, parses)
        self._unknown(claims, MATCH_CLAIM_TIMELINES)
        self._unlisted(claims, MATCH_CLAIM_TIMELINES)
        self._across(claims)
        self._table_checks()

    # The manifests.

    def _timelines(self) -> None:
        """Every timeline each manifest holds, with its axis there; a
        timeline ID may be held by several manifests, which share its event
        rows."""
        timelines: list[str] = []
        manifests: list[int] = []
        units: list[str | None] = []
        number_types: list[str | None] = []
        for index, manifest in enumerate(self.manifests):
            for identifier, timeline in axes_by_id(manifest.bare).items():
                unit, number_type = _axis(timeline)
                timelines.append(identifier)
                manifests.append(index)
                units.append(unit if isinstance(unit, str) else None)
                number_types.append(number_type)
        self.held = pa.table(
            {
                "timeline": pa.array(timelines, pa.string()),
                "manifest": pa.array(manifests, pa.int64()),
                "unit": pa.array(units, pa.string()),
                "number_type": pa.array(number_types, pa.string()),
            }
        )
        firsts = _first_rows(
            self.held["timeline"].combine_chunks(),
            self.held["timeline"].combine_chunks(),
        )
        kept = pc.equal(firsts, _arange(len(self.held)))
        first = self.held.filter(kept)
        self.timeline_ids = first["timeline"].combine_chunks()
        self.owner_of = first["manifest"].combine_chunks()

    def _resources(self) -> None:
        """Each table resource's table entry; ``registry_not_a_file`` for a
        Registry resource naming a folder; ``unknown_table``; the listings. A
        resource naming no table is passed over."""
        by_url = {(entry.url, entry.kind): entry for entry in self.entries}
        self.resolved: dict[tuple[int, int], _Entry] = {}
        listing_entry: list[int] = []
        listing_timeline: list[str] = []
        listing_manifest: list[int] = []
        for number, manifest in enumerate(self.manifests):
            for index, resource in enumerate(entries_of(manifest.bare, "resources")):
                if not is_table_resource(resource):
                    continue
                if resource["type"] == "Registry" and resource["url"].endswith("/"):
                    self.problems.add(
                        "registry_not_a_file",
                        manifest.file,
                        None,
                        ("resources", index, "url"),
                        _NOT_A_FILE.format(url=resource["url"]),
                    )
                    continue
                url = package_path(resource["url"], manifest.file)
                named = None if url is None else (url, resource["type"])
                entry = None if named is None else by_url.get(named)
                if entry is None:
                    if named is None or named not in self.listed:
                        self.problems.add(
                            "unknown_table",
                            manifest.file,
                            None,
                            ("resources", index, "url"),
                            f"the resource '{resource['id']}' names "
                            f"'{resource['url']}', which is no table of the type "
                            f"{resource['type']} in the package",
                        )
                    continue
                self.resolved[(number, index)] = entry
                for timeline in resource["timelines"]:
                    listing_entry.append(entry.index)
                    listing_timeline.append(timeline)
                    listing_manifest.append(number)
        self.listings = pa.table(
            {
                "entry": pa.array(listing_entry, pa.int64()),
                "timeline": pa.array(listing_timeline, pa.string()),
                "manifest": pa.array(listing_manifest, pa.int64()),
            }
        )

    # The rows.

    def _framed(
        self,
        number: int,
        entry: _Entry,
        columns: Sequence[str],
        timelines: Sequence[str],
    ) -> pa.Table:
        """An entry's ``columns`` as strings, with whether its table holds
        each of ``timelines`` as strings, its entry, file and row."""
        read = _read(entry.files, entry.schemas, entry.kind, columns=columns)
        files, rows = _origins(self.first_file[number], read.lengths)
        return self._frame(entry, read.table, files, rows, columns, timelines)

    def _frame(
        self,
        entry: _Entry,
        table: pa.Table,
        files: pa.Array,
        rows: pa.Array,
        columns: Sequence[str],
        timelines: Sequence[str],
    ) -> pa.Table:
        """The ``columns`` of an entry's rows read as strings, with the
        :meth:`_framed` columns beside them."""
        return pa.table(
            {
                **{name: _strings(table, name) for name in columns},
                **{
                    _READ + name: pa.repeat(
                        pa.scalar(_is_strings(table, name)), len(table)
                    )
                    for name in timelines
                },
                "entry": pa.repeat(pa.scalar(entry.index, pa.int64()), len(table)),
                "kind_of_entry": pa.repeat(pa.scalar(entry.kind), len(table)),
                "file": files,
                "row": rows,
            }
        )

    def _empty(self, columns: Sequence[str], timelines: Sequence[str]) -> pa.Table:
        return pa.table(
            {
                **{name: pa.array([], pa.string()) for name in columns},
                **{_READ + name: pa.array([], pa.bool_()) for name in timelines},
                "entry": _arange(0),
                "kind_of_entry": pa.array([], pa.string()),
                "file": _arange(0),
                "row": _arange(0),
            }
        )

    def _rows(self, *, _content: bool) -> pa.Table:
        """The identifying columns of every row of the pre-parsed tables
        (``id``), or of the MatchClaim tables (``id`` and both timelines),
        with the table entry, the file (an index of :attr:`names`) and the
        row in the file of each."""
        columns = ("id",) if _content else _CLAIM_COLUMNS
        timelines = () if _content else MATCH_CLAIM_TIMELINES
        parts = [
            self._framed(number, entry, columns, timelines)
            for number, entry in enumerate(self.entries)
            if (
                entry.kind not in _TABLE_KINDS
                if _content
                else entry.kind == "MatchClaim"
            )
        ]
        return pa.concat_tables(parts) if parts else self._empty(columns, timelines)

    def _registry_rows(self) -> pa.Table:
        """The registry's identifying columns, none where its shape is broken,
        which its table check reports. The registry is read whole once
        (:attr:`whole_registry`), for these columns and its table check."""
        columns = _REGISTRY_COLUMNS
        entry = self.registry
        self.whole_registry = None if entry is None else self._full(entry, runs=False)
        read = self.whole_registry
        if entry is not None and read is not None:
            if not _schema_problems(read.table.schema.empty_table(), REGISTRY_SCHEMA):
                return self._frame(
                    entry, read.table, read.files, read.rows, columns, EVENT_TIMELINES
                )
        return self._empty(columns, EVENT_TIMELINES)

    def _column_rows(self, entry: _Entry | None, column: str) -> pa.Table:
        if entry is None:
            return self._empty((column,), ())
        return self._framed(self.entries.index(entry), entry, (column,), ())

    def _add_rows(
        self,
        code: ProblemCode,
        rows: pa.Table,
        mask: pa.Array,
        column: str | Path_,
        message: Any,
    ) -> None:
        """Add a problem at each row ``mask`` flags, worded by ``message``
        from the row read in Python."""
        path = (column,) if isinstance(column, str) else column
        flagged = rows.filter(_held(mask)).to_pylist()
        for row in flagged:
            self.problems.add(
                code, self.names[row["file"]], row["row"], path, message(row)
            )

    def _owners(self, timelines: pa.Array) -> pa.Array:
        """The first manifest holding each timeline, null where none does."""
        return self.owner_of.take(pc.index_in(timelines, value_set=self.timeline_ids))

    def _duplicates(
        self,
        rows: pa.Table,
        what: str,
        among: pa.Array | None = None,
        keys: pa.Array | None = None,
        where: bool = False,
    ) -> None:
        """An ID given again, at the later row; among the rows ``among``
        flags, by ``keys`` where given (else the IDs)."""
        if among is not None:
            rows = rows.filter(among)
            keys = None if keys is None else keys.filter(among)
        ids = _array(rows, "id")
        keys = ids if keys is None else keys
        first = _first_rows(keys, keys)
        again = _held(pc.not_equal(first, _arange(len(ids))))
        again = pc.and_(again, pc.is_valid(keys))
        located = rows.append_column("first", first)

        def message(row: Mapping[str, Any]) -> str:
            held = located.slice(row["first"], 1).to_pylist()[0]
            at = f" at '{row['location']}'" if where else ""
            return (
                f"the {what} '{row['id']}' is given twice{at}, first in "
                f"'{self.names[held['file']]}' at row {held['row']}"
            )

        self._add_rows("duplicate_id", located, again, "id", message)

    def _registry_duplicates(self, registry: pa.Table) -> None:
        """The registry's IDs: an event, MatchClaim or Parse ID once
        among these rows, a manifest element's once per location."""
        kinds = _array(registry, "kind")
        element = _held(pc.is_in(kinds, value_set=_ELEMENTS))
        stated = pc.is_valid(kinds)
        self._duplicates(registry, "ID", pc.and_(stated, pc.invert(element)))
        keys = pc.binary_join_element_wise(
            _array(registry, "location"), _array(registry, "id"), _SEPARATOR
        )
        self._duplicates(registry, "ID", element, keys, where=True)

    def _unknown(self, rows: pa.Table, columns: tuple[str, ...]) -> None:
        """A null timeline (``schema_violation``, as the table checks word
        it), then a timeline no manifest holds (``unknown_timeline``), column
        by column; a column a table lacks, or holds no strings in, is its
        table check's to report."""
        for column in columns:
            timelines = _array(rows, column)
            null = pc.and_(pc.is_null(timelines), _array(rows, _READ + column))
            self._add_rows(
                "schema_violation",
                rows,
                null,
                column,
                lambda row, column=column: f"'{column}' is null",
            )
            unknown = pc.and_(
                pc.is_valid(timelines), pc.is_null(self._owners(timelines))
            )
            self._add_rows(
                "unknown_timeline",
                rows,
                unknown,
                column,
                lambda row, column=column: (
                    f"no manifest of the package has the timeline '{row[column]}'"
                ),
            )

    def _unlisted(self, rows: pa.Table, columns: tuple[str, ...]) -> None:
        """A row's timeline that no resource naming its table lists, in any
        manifest; worded with the first manifest holding the timeline."""
        kinds = {entry.index: entry.kind for entry in self.entries}
        for column in columns:
            timelines = _array(rows, column)
            owners = self._owners(timelines)
            placed = rows.append_column("owner", owners).append_column(
                "order", _arange(len(rows))
            )
            held = placed.filter(pc.is_valid(owners))
            keys = held.select(["entry", column]).rename_columns(["entry", "timeline"])
            keys = keys.append_column("order", held.column("order"))
            missing = keys.join(
                self.listings.select(["entry", "timeline"]),
                keys=["entry", "timeline"],
                join_type="left anti",
            )
            mask = pc.is_in(_arange(len(rows)), value_set=missing.column("order"))

            def message(row: Mapping[str, Any], column: str = column) -> str:
                manifest = self.manifests[row["owner"]].file
                return (
                    f"the timeline '{row[column]}' of '{manifest}' is listed by no "
                    f"resource of the type {kinds[row['entry']]} naming this table"
                )

            self._add_rows("unlisted_timeline", placed, mask, column, message)

    def _axes(self, events: pa.Table) -> None:
        """Each event row against its timeline's axis in every manifest
        holding it; one problem per distinct axis it is not on."""
        placed = events.append_column("order", _arange(len(events)))
        row_unit = _array(placed, "unit")
        row_type = _array(placed, "number_type")
        admitted = _axis_admitted(row_unit, row_type)
        candidates = placed.filter(
            pc.and_(admitted, pc.is_valid(_array(placed, "timeline_id")))
        )
        pairs = candidates.select(["order", "timeline_id", "unit", "number_type"]).join(
            self.held.rename_columns(
                ["timeline_id", "manifest", "expected_unit", "expected_number_type"]
            ),
            keys="timeline_id",
            join_type="inner",
        )
        unit_differs = _differ(_array(pairs, "unit"), _array(pairs, "expected_unit"))
        type_differs = _differ(
            _array(pairs, "number_type"), _array(pairs, "expected_number_type")
        )
        flagged = pairs.filter(pc.or_(unit_differs, type_differs)).append_column(
            "column",
            pc.if_else(
                unit_differs.filter(pc.or_(unit_differs, type_differs)),
                pa.scalar("unit"),
                pa.scalar("number_type"),
            ),
        )
        flagged = flagged.sort_by([("order", "ascending"), ("manifest", "ascending")])
        orders = flagged["order"].combine_chunks()
        rows = dict(
            zip(
                orders.to_pylist(),
                placed.take(orders).to_pylist(),
                strict=True,
            )
        )
        seen: set[tuple[int, str, str]] = set()
        for found in flagged.to_pylist():
            row = rows[found["order"]]
            message = (
                f"a coordinate in {row['unit']} ({row['number_type']}) on the "
                f"timeline '{row['timeline_id']}' in {found['expected_unit']} "
                f"({found['expected_number_type']})"
            )
            key = (found["order"], found["column"], message)
            if key in seen:
                continue
            seen.add(key)
            self.problems.add(
                "axis_mismatch",
                self.names[row["file"]],
                row["row"],
                (found["column"],),
                message,
            )

    def _parses(self, events: pa.Table, parses: pa.Table) -> None:
        """An event row's ``parse_id`` or ``vanished_in`` naming no
        parse."""
        known = _array(parses, "id")
        for column in ("parse_id", "vanished_in"):
            values = _array(events, column)
            unknown = pc.and_(
                pc.is_valid(values), pc.invert(pc.is_in(values, value_set=known))
            )
            self._add_rows(
                "unknown_parse",
                events,
                unknown,
                column,
                lambda row, column=column: (
                    f"no parse of the package has the ID '{row[column]}'"
                ),
            )

    def _locations(self, events: pa.Table) -> pa.Table:
        """Each event row with a location, resolved against the package's
        root, and the entry it names (null where none of its kind does, and
        for an absolute URI, which names a resource outside the package and
        is not checked); ``unknown_location``."""
        locations = _array(events, "location")
        kinds = _array(events, "kind")
        codes = _dense(pc.binary_join_element_wise(locations, kinds, _SEPARATOR))
        firsts = _firsts(codes)
        by_url = {(entry.url, entry.kind): entry.index for entry in self.entries}
        entry_of: list[int | None] = []
        named: list[bool] = []
        for location, kind in zip(
            locations.take(firsts).to_pylist(),
            kinds.take(firsts).to_pylist(),
            strict=True,
        ):
            # An absolute URI names a resource outside the package, unchecked.
            outside = location is not None and _is_external(location)
            url = None if location is None or outside else package_path(location)
            entry_of.append(by_url.get((url, kind)) if url is not None else None)
            named.append(location is None or outside or (url, kind) in self.listed)
        placed = events.append_column(
            "entry_named", pa.array(entry_of, pa.int64()).take(codes)
        ).append_column("order", _arange(len(events)))
        self._add_rows(
            "unknown_location",
            placed,
            pc.invert(pa.array(named, pa.bool_()).take(codes)),
            "location",
            lambda row: (
                f"the location '{row['location']}' names no table of the type "
                f"{row['kind']} in the package"
            ),
        )
        return placed

    def _content(self, events: pa.Table, located: pa.Table, contents: pa.Table) -> None:
        """``missing_content``, then ``unregistered_id``."""
        named = located.filter(pc.is_valid(located["entry_named"]))
        keys = named.select(["entry_named", "id", "order"]).rename_columns(
            ["entry", "id", "order"]
        )
        missing = keys.join(
            contents.select(["entry", "id"]),
            keys=["entry", "id"],
            join_type="left anti",
        )
        mask = pc.is_in(
            _arange(len(located)), value_set=missing["order"].combine_chunks()
        )
        self._add_rows(
            "missing_content",
            located,
            mask,
            "location",
            lambda row: (
                f"the table '{row['location']}' holds no row of the ID '{row['id']}'"
            ),
        )
        if self.registry is None:
            return
        placed = contents.append_column("order", _arange(len(contents)))
        registered = events.select(["kind", "id"]).rename_columns(
            ["kind_of_entry", "id"]
        )
        unregistered = placed.select(["kind_of_entry", "id", "order"]).join(
            registered, keys=["kind_of_entry", "id"], join_type="left anti"
        )
        mask = pc.and_(
            pc.is_in(
                _arange(len(placed)), value_set=unregistered["order"].combine_chunks()
            ),
            pc.is_valid(_array(placed, "id")),
        )
        self._add_rows(
            "unregistered_id",
            placed,
            mask,
            "id",
            lambda row: (
                f"no event row of the type {row['kind_of_entry']} in the registry "
                f"has the ID '{row['id']}'"
            ),
        )

    def _expected_non_event_rows(self, claims: pa.Table, parses: pa.Table) -> pa.Table:
        """The non-event rows the manifests, the MatchClaim tables and the
        Parse table give, each manifest's at its path from the root,
        each table's at its entry's URL."""
        parts = [
            non_event_rows_of(manifest.bare, manifest.file)
            for manifest in self.manifests
        ]
        urls = pa.array([entry.url for entry in self.entries], pa.string())
        numbers = pa.array([entry.index for entry in self.entries], pa.int64())
        for table, kind in ((claims, "MatchClaim"), (parses, "Parse")):
            locations = urls.take(
                pc.index_in(_array(table, "entry"), value_set=numbers)
            )
            parts.append(table_non_event_rows(_array(table, "id"), kind, locations))
        return pa.concat_tables(parts) if parts else _NON_EVENT_ROW.empty_table()

    def _stale(self, registry: pa.Table, claims: pa.Table, parses: pa.Table) -> None:
        """The registry's non-event rows against the rows the sources give
        (:func:`stale_problems`); rows at a manifest or table that could not
        be read are not compared."""
        entry = self.registry
        if entry is None:
            return
        non_events = registry.filter(is_non_event(registry["kind"]))
        held = non_events.select([*_NON_EVENT_ROW.names, "row"])
        expected = self._expected_non_event_rows(claims, parses)
        self.problems.found.extend(
            stale_problems(held, expected, entry.url, self.unread)
        )

    def _across(self, claims: pa.Table) -> None:
        """A MatchClaim whose two timelines are held, but by no one manifest."""
        a = _array(claims, "timeline_a_id")
        b = _array(claims, "timeline_b_id")
        order = _arange(len(claims))
        held = self.held.select(["timeline", "manifest"])
        sides = [
            pa.table({"order": order, "timeline": side}).join(
                held, keys="timeline", join_type="inner"
            )
            for side in (a, b)
        ]
        shared = (
            sides[0]
            .select(["order", "manifest"])
            .join(
                sides[1].select(["order", "manifest"]),
                keys=["order", "manifest"],
                join_type="inner",
            )
        )
        across = _all(
            pc.is_valid(self._owners(a)),
            pc.is_valid(self._owners(b)),
            pc.invert(pc.is_in(order, value_set=shared["order"].combine_chunks())),
        )

        def message(row: Mapping[str, Any]) -> str:
            return (
                "no manifest of the package holds both the timeline "
                f"'{row['timeline_a_id']}' and the timeline '{row['timeline_b_id']}'"
            )

        self._add_rows(
            "claim_across_manifests", claims, across, "timeline_b_id", message
        )
        self.across = {
            (row["file"], row["row"]) for row in claims.filter(across).to_pylist()
        }

    # The table checks.

    def _table_checks(self) -> None:
        """The table checks: the registry's (its ``axis_mismatch`` left to
        the package rule, which compares each manifest's axis; a Projection's
        projected timeline checked against the timelines of every manifest)
        and the Parse table's, once and whole, in the order of the entries;
        then each MatchClaim table's, once per manifest whose resources name
        it, over that manifest's rows alone: each row's manifests are found
        once, by its timelines' listings, and the rows ordered by manifest,
        so that every manifest is checked on its own run of rows."""
        self.package = {
            (problem.code, problem.file, problem.row, problem.path)
            for problem in self.problems.found
        }
        self.reported: set[PackageProblem] = set(self.problems.found)
        for entry in self.entries:
            whole = _WHOLE.get(entry.kind)
            if whole is None or (
                entry.kind in ("Registry", "Parse")
                and entry not in (self.registry, self.parse)
            ):
                continue
            if entry is self.registry:
                read = self.whole_registry
            else:
                read = self._full(entry, runs=False)
            if read is None:
                continue
            everything = _arange(len(read.table))
            options: dict[str, Any] = {}
            if entry is self.registry:
                options["projected_timelines"] = self.timeline_ids.to_pylist()
            checked = [
                problem
                for problem in whole(read.table, **options)
                if not (entry.kind == "Registry" and problem.code == "axis_mismatch")
            ]
            self._place(entry, read, everything, checked)
        full: dict[int, _Full | None] = {}
        for number, manifest in enumerate(self.manifests):
            checked_entries: set[int] = set()
            for index in range(len(entries_of(manifest.bare, "resources"))):
                entry = self.resolved.get((number, index))
                if (
                    entry is None
                    or entry.kind != "MatchClaim"
                    or entry.index in checked_entries
                ):
                    continue
                checked_entries.add(entry.index)
                if entry.index not in full:
                    full[entry.index] = self._full(entry)
                read = full[entry.index]
                if read is None:
                    continue
                taken = read.runs.get(number, _arange(0))
                checked = match_claim_problems(read.table.take(taken), manifest.value)
                self._place(entry, read, taken, checked)

    def _place(
        self,
        entry: _Entry,
        read: _Full,
        taken: pa.Array,
        checked: Iterable[TableProblem],
    ) -> None:
        """Put each problem of a table check in its file and row, unless a
        package rule reports it already."""
        across = {(self.names[file], row) for file, row in self.across}
        for problem in checked:
            if problem.row is None:
                file, row = entry.url, None
            else:
                at = taken[problem.row].as_py()
                file = self.names[read.files[at].as_py()]
                row = read.rows[at].as_py()
            if (problem.code, file, row, problem.column) in self.package:
                continue
            if problem.code == "unknown_timeline" and (file, row) in across:
                continue
            placed = PackageProblem(
                problem.code, file, row, problem.column, problem.message
            )
            if placed not in self.reported:
                self.reported.add(placed)
                self.problems.found.append(placed)

    def _runs(self, entry: _Entry, table: pa.Table) -> dict[int, pa.Array]:
        """The rows of an entry's table each manifest checks, by manifest: a
        row whose timeline (a MatchClaim's either) a resource of the manifest
        naming the entry lists, in the table's order. One hash join per
        timeline column and one sort over the rows found."""
        listed = self.listings.filter(
            pc.equal(self.listings.column("entry"), entry.index)
        ).select(["timeline", "manifest"])
        pairs = [
            pa.table({"timeline": _strings(table, column), "row": _arange(len(table))})
            .join(listed, keys="timeline", join_type="inner")
            .select(["manifest", "row"])
            for column in _timeline_columns(entry.kind)
        ]
        owned = (
            pa.concat_tables(pairs)
            .group_by(["manifest", "row"])
            .aggregate([])
            .sort_by([("manifest", "ascending"), ("row", "ascending")])
        )
        rows = owned.column("row").combine_chunks()
        runs: dict[int, pa.Array] = {}
        offset = 0
        for count in pc.value_counts(owned.column("manifest")).to_pylist():
            runs[count["values"]] = rows.slice(offset, count["counts"])
            offset += count["counts"]
        return runs

    def _full(self, entry: _Entry, *, runs: bool = True) -> _Full | None:
        """Every column of an entry's rows, with each row's file (an index of
        :attr:`names`), its row in the file, and the rows each manifest
        checks (:meth:`_runs`); ``None`` where they cannot be read as one
        table, the problem added."""
        first = self.first_file[self.entries.index(entry)]
        try:
            read = _read(entry.files, entry.schemas, entry.kind)
        except TableError as error:
            problem = error.problem
            file, row = entry.url, problem.row
            if row is not None:
                for name, file_schema_rows in zip(
                    entry.names, _file_rows(entry), strict=True
                ):
                    if row < file_schema_rows:
                        file = name
                        break
                    row -= file_schema_rows
            self.problems.add(problem.code, file, row, problem.column, problem.message)
            return None
        files, rows = _origins(first, read.lengths)
        found = self._runs(entry, read.table) if runs else {}
        return _Full(read.table, files, rows, found)


_READ = "read:"
"""The prefix of the column telling whether a row's table holds the timeline
column after it as strings."""


def _is_strings(table: pa.Table, name: str) -> bool:
    return name in table.column_names and pa.types.is_string(
        table.schema.field(name).type
    )


def _strings(table: pa.Table, name: str) -> pa.Array:
    """A column of strings, as the package rules read it: null where the
    table lacks it or holds no strings in it, which its table check
    reports."""
    if _is_strings(table, name):
        return table.column(name).combine_chunks()
    return pa.nulls(len(table), pa.string())


def _origins(first: int, lengths: Sequence[int]) -> tuple[pa.Array, pa.Array]:
    """Each row's file, numbered from ``first``, and its row in the file, for
    files of ``lengths`` rows read one after another."""
    files = [
        pa.repeat(pa.scalar(first + offset, pa.int64()), length)
        for offset, length in enumerate(lengths)
    ]
    rows = [_arange(length) for length in lengths]
    return (
        pa.concat_arrays(files) if files else _arange(0),
        pa.concat_arrays(rows) if rows else _arange(0),
    )


def _file_rows(entry: _Entry) -> list[int]:
    """The number of rows of each file of an entry, from the files' footers."""
    return [pq.ParquetFile(file).metadata.num_rows for file in entry.files]
