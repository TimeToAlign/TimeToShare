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
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

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
    extraction_problems,
    match_claim_problems,
    projection_problems,
    registry_problems,
)
from .columns import (
    EXTRACTION_SCHEMA,
    INDEX_KINDS,
    MATCH_CLAIM_SCHEMA,
    PROJECTION_SCHEMA,
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
    "read_table",
    "table_files",
]

PACKAGE_FILE = "package.yaml"
"""The name of the file at a package's root listing its manifests and tables."""

TYPE_METADATA_KEY = "timetoshare:type"
"""The schema-metadata key holding a file's table type, such as ``Projection``."""

VERSION_METADATA_KEY = "timetoshare:version"
"""The schema-metadata key holding the format version of a file."""

PackageCode = Literal[
    "missing_file",
    "missing_registry",
    "duplicate_registry",
    "duplicate_extraction",
    "table_type",
    "column_type_mismatch",
    "version_mismatch",
    "unknown_table",
    "duplicate_id",
    "unknown_timeline",
    "unlisted_timeline",
    "claim_across_manifests",
    "axis_mismatch",
    "unknown_extraction",
    "unknown_location",
    "missing_content",
    "unregistered_id",
    "stale_index",
]
"""The codes of the package check's own rules. A package problem may also
carry the code of a manifest's validation (``timetoshare.ValidationCode``)
or of a table check (:data:`~timetoshare.tables.TableCode`); two package
rules use such codes as well: ``duplicate_url`` for a file two table entries
reach, ``schema_violation`` for a row whose timeline is null,
``invalid_projection_of`` for a Projection standing for an event of its own
timeline."""

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
    declares; the filter of ``timelines`` and ``ids`` is pushed into the reader.
    A MatchClaim file's shared provenance is filled into its rows before the
    files are joined, unless only ``columns`` are read.
    """
    schema = _unified(files, schemas) if files else _DECLARED.get(kind, pa.schema([]))
    if columns is not None:
        schema = pa.schema(
            [schema.field(name) for name in columns if name in schema.names]
        )
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
    dataset = ds.dataset([str(file) for file in files], schema=schema, format="parquet")
    parts: list[pa.Table] = []
    offset = 0
    for fragment, file, own in zip(
        dataset.get_fragments(), files, schemas, strict=True
    ):
        part = fragment.to_table(schema=schema, filter=expression)
        if kind == "MatchClaim" and columns is None:
            part = _with_shared_provenance(part, own, file, offset)
        parts.append(part)
        offset += len(part)
    table = pa.concat_tables(parts) if parts else schema.empty_table()
    return _Read(table, [len(part) for part in parts])


_DECLARED = {
    "Registry": REGISTRY_SCHEMA,
    "Extraction": EXTRACTION_SCHEMA,
    "Projection": PROJECTION_SCHEMA,
    "MatchClaim": MATCH_CLAIM_SCHEMA,
}
"""The table types the format defines, with their declared columns."""


def read_table(
    path: str | os.PathLike[str],
    *,
    timelines: Iterable[str] | None = None,
    ids: Iterable[str] | None = None,
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
    where both keep it. A MatchClaim file's shared provenance
    (``timetoshare:provenance``) is filled into its own rows before the
    files are joined. The order of the rows is the files' order, then each
    file's; readers never rely on it.

    The table's type is what its files state (``timetoshare:type``), else
    ``type``; where both are stated they agree. The table returned states
    its type alone in its metadata. An empty folder gives no rows, in the
    declared columns of a type the format declares (``Registry``,
    ``Extraction``, ``Projection``, ``MatchClaim``), in none for another
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
    else:
        table = _read(files, schemas, kind, timelines, ids=ids).table
    return table.replace_schema_metadata({TYPE_METADATA_KEY: kind})


# The package check.

_BASE = "file:///package/"
"""The address a package's root is resolved at: references resolve as URLs,
and a reference leaving the package lies outside this prefix."""


_PARQUET = "application/vnd.apache.parquet"
"""The media type of a Parquet file."""


def is_table_resource(resource: Mapping[str, Any]) -> bool:
    """Whether a resource of a manifest names a table.

    A resource names a table when its type is one the format declares
    (``Registry``, ``Extraction``, ``Projection``, ``MatchClaim``), its URL
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


def _resolved(reference: str, against: str) -> str | None:
    """The path from the package's root of ``reference`` written in the
    document at ``against`` (a path from the root), or ``None`` where it
    leads outside the package; a folder's keeps its final ``/``."""
    address = urldefrag(urljoin(_BASE + against, reference)).url
    if not address.startswith(_BASE) or "?" in address:
        return None
    resolved = unquote(address.removeprefix(_BASE))
    return resolved or None


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
    ``Registry`` (``missing_registry``, at ``tables``), a second one
    (``duplicate_registry``) or a second table of the type ``Extraction``
    (``duplicate_extraction``), each at the later entry's ``type``; only the
    first of each is read. Then, manifest by manifest as listed, a file that
    is missing (``missing_file``) or that is no valid manifest (its
    validation's code and path; another version ``version_mismatch``).
    Then, table by table and file by file, a file or folder that is missing
    (``missing_file``), a file an earlier entry of the same type reaches
    already, a file entry inside a listed folder for instance
    (``duplicate_url``, at the later entry's ``url``; the later entry reads
    its other files only), a file stating another type (``table_type``) or
    another version (``version_mismatch``) than its entry and the package,
    and a column of two Arrow types in two files (``column_type_mismatch``,
    at the folder; its rows are not read). Then the rules the manifests and
    the rows keep together, each over every row in the order of the
    entries, their files and their rows:

    - ``unknown_table``: a manifest's table resource whose URL names no
      table entry of the resource's type, or leads outside the package
      (:func:`is_table_resource`); any other resource, a recording, an
      image or a score file, is carried and not checked against the tables;
    - ``duplicate_id``: in the registry, an event, MatchClaim or Extraction
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
    - ``unknown_extraction``: an event row's ``extraction_id`` or
      ``vanished_in`` naming no row of the Extraction table;
    - ``unknown_location``: an event row's ``location`` naming no table
      entry of the row's kind;
    - ``missing_content``: an event row whose location's table holds no row
      of its ID;
    - ``unregistered_id``: a row of a pre-parsed table whose ID has no
      event row of the table's type;
    - ``invalid_projection_of``, then ``unknown_timeline``: a pre-parsed
      Projection standing for an event of its own registry row's timeline,
      or of a timeline no manifest holds;
    - ``stale_index``: an index row of the registry that no manifest
      element, MatchClaim or extraction gives at its location (an extra
      row), or whose ``kind``, ``timeline_id`` or ``name`` differs from
      what they give, in the registry's order; then each index row they
      give that the registry lacks, by location and ID (a missing row). A
      manifest or table that could not be read gives no row and has none
      compared;
    - ``claim_across_manifests``: a MatchClaim whose two timelines no one
      manifest holds.

    These read the identifying columns of each table, column by column. Last,
    the table checks: of the registry (:func:`registry_problems`; its
    ``axis_mismatch``, a matter of the manifests, is the package rule's), the
    Extraction table (:func:`extraction_problems`) and each pre-parsed
    Projection table (:func:`projection_problems`), each once and whole;
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
    _registry_entries(value, problems)
    version = value["timetoshare"]
    manifests, unread = _manifests(root, value, problems)
    entries = _entries(root, value, version, problems)
    listed = {
        (url, entry["type"])
        for entry in value["tables"]
        if (url := _resolved(entry["url"], "")) is not None
    }
    _Check(listed, manifests, unread, entries, problems).run()
    return problems.found


def _registry_entries(value: Mapping[str, Any], problems: _Problems) -> None:
    """``missing_registry``, ``duplicate_registry``, ``duplicate_extraction``."""
    by_type: dict[str, list[int]] = {"Registry": [], "Extraction": []}
    for index, entry in enumerate(value["tables"]):
        if entry["type"] in by_type:
            by_type[entry["type"]].append(index)
    if not by_type["Registry"]:
        problems.add(
            "missing_registry",
            PACKAGE_FILE,
            None,
            ("tables",),
            "the package lists no table of the type Registry",
        )
    for kind, code in (
        ("Registry", "duplicate_registry"),
        ("Extraction", "duplicate_extraction"),
    ):
        indices = by_type[kind]
        for later in indices[1:]:
            problems.add(
                code,
                PACKAGE_FILE,
                None,
                ("tables", later, "type"),
                f"the package lists a second table of the type {kind}, first at "
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
        file = _resolved(entry["url"], "")
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


def _entries(
    root: Path, value: Mapping[str, Any], version: str, problems: _Problems
) -> list[_Entry]:
    """The table entries whose files could be read as one table; a file an
    earlier entry of its type reaches already is left to that entry."""
    found = []
    reached: dict[tuple[str, str], int] = {}
    for index, entry in enumerate(value["tables"]):
        url = _resolved(entry["url"], "")
        folder = entry["url"].endswith("/")
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
        found.append(_Entry(index, kind, url, files, names, schemas))
    return found


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
    "name",
    "extraction_id",
    "locator",
    "vanished_in",
)
_CLAIM_COLUMNS = ("id", "timeline_a_id", "timeline_b_id")
_COMPARED = ("kind", "timeline_id", "name")
"""The columns of an index row compared with what the manifests give."""

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

_INDEX = pa.array(INDEX_KINDS, pa.string())
_ONE_PER_PACKAGE = pa.array(["MatchClaim", "Extraction"], pa.string())
"""The index kinds whose IDs are held once among the event rows as well."""
_SEPARATOR = pa.scalar("\x00")
_EMPTY_TEXT = pa.scalar("")


def _any_of(*masks: pa.Array) -> pa.Array:
    result = masks[0]
    for mask in masks[1:]:
        result = pc.or_(result, mask)
    return result


_WHOLE = {
    "Registry": registry_problems,
    "Extraction": extraction_problems,
    "Projection": projection_problems,
}
"""The table checks run once over a whole table."""
_TABLE_KINDS = ("Registry", "Extraction", "MatchClaim")
"""The types of the tables that hold no event's content."""


def _at_path(value: Any, path: Path_) -> Any:
    for step in path:
        value = value[step]
    return value


def _index_rows_of(manifest: Mapping[str, Any], location: str) -> list[dict[str, Any]]:
    """The index rows a valid manifest (IDs bare) gives, at ``location``:
    one per element holding an ID, in the order of
    :func:`~timetoshare.validation.diagnostics.manifest_ids`."""
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
        name = element.get("name")
        rows.append(
            {
                "id": identifier,
                "kind": kind,
                "location": location,
                "timeline_id": timeline,
                "name": name if isinstance(name, str) else None,
            }
        )
    return rows


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
            if kind in ("MatchClaim", "Extraction") and (url, kind) not in read
        }
        self.registry = next(
            (entry for entry in entries if entry.kind == "Registry"), None
        )
        self.extraction = next(
            (entry for entry in entries if entry.kind == "Extraction"), None
        )

    def run(self) -> None:
        self._timelines()
        self._resources()
        registry = self._registry_rows()
        events = registry.filter(pc.invert(_held(pc.is_in(registry["kind"], _INDEX))))
        contents = self._rows(_content=True)
        claims = self._rows(_content=False)
        extractions = self._column_rows(self.extraction, "id")
        self._registry_duplicates(registry)
        self._duplicates(contents, "event ID")
        self._duplicates(claims, "MatchClaim ID")
        self._unknown(events, ("timeline_id",))
        self._unlisted(events, ("timeline_id",))
        self._axes(events)
        self._extractions(events, extractions)
        located = self._locations(events)
        self._content(events, located, contents)
        self._projections()
        self._stale(registry, claims, extractions)
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
        """Each table resource's table entry; ``unknown_table``; the
        listings. A resource naming no table is passed over."""
        by_url = {(entry.url, entry.kind): entry for entry in self.entries}
        self.resolved: dict[tuple[int, int], _Entry] = {}
        listing_entry: list[int] = []
        listing_timeline: list[str] = []
        listing_manifest: list[int] = []
        for number, manifest in enumerate(self.manifests):
            for index, resource in enumerate(entries_of(manifest.bare, "resources")):
                if not is_table_resource(resource):
                    continue
                url = _resolved(resource["url"], manifest.file)
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
        table = read.table
        files, rows = _origins(self.first_file[number], read.lengths)
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
        which its table check reports."""
        columns = _REGISTRY_COLUMNS
        entry = self.registry
        if entry is not None:
            schema = _unified(entry.files, entry.schemas)
            if not _schema_problems(schema.empty_table(), REGISTRY_SCHEMA):
                number = self.entries.index(entry)
                return self._framed(number, entry, columns, EVENT_TIMELINES)
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
        """The registry's IDs: an event, MatchClaim or Extraction ID once
        among these rows, a manifest element's once per location."""
        kinds = _array(registry, "kind")
        element = _held(
            pc.and_(
                pc.is_in(kinds, value_set=_INDEX),
                pc.invert(pc.is_in(kinds, value_set=_ONE_PER_PACKAGE)),
            )
        )
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

    def _extractions(self, events: pa.Table, extractions: pa.Table) -> None:
        """An event row's ``extraction_id`` or ``vanished_in`` naming no
        extraction."""
        known = _array(extractions, "id")
        for column in ("extraction_id", "vanished_in"):
            values = _array(events, column)
            unknown = pc.and_(
                pc.is_valid(values), pc.invert(pc.is_in(values, value_set=known))
            )
            self._add_rows(
                "unknown_extraction",
                events,
                unknown,
                column,
                lambda row, column=column: (
                    f"no extraction of the package has the ID '{row[column]}'"
                ),
            )

    def _locations(self, events: pa.Table) -> pa.Table:
        """Each event row with a location, resolved against the package's
        root, and the entry it names (null where none of its kind does);
        ``unknown_location``."""
        locations = _array(events, "location")
        kinds = _array(events, "kind")
        codes = _dense(pc.binary_join_element_wise(locations, kinds, _SEPARATOR))
        firsts = _firsts(codes)
        by_url = {(entry.url, entry.kind): entry.index for entry in self.entries}
        resolved: list[str | None] = []
        entry_of: list[int | None] = []
        named: list[bool] = []
        for location, kind in zip(
            locations.take(firsts).to_pylist(),
            kinds.take(firsts).to_pylist(),
            strict=True,
        ):
            url = None if location is None else _resolved(location, "")
            resolved.append(url)
            entry_of.append(by_url.get((url, kind)) if url is not None else None)
            named.append(location is None or (url, kind) in self.listed)
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
        self.events = events
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

    def _projections(self) -> None:
        """A pre-parsed Projection standing for an event of its registry
        row's own timeline (``invalid_projection_of``), or of a timeline no
        manifest holds (``unknown_timeline``)."""
        if self.registry is None:
            return
        events = self.events.select(["kind", "id", "timeline_id"])
        events = events.filter(pc.equal(events["kind"], pa.scalar("Projection")))
        for number, entry in enumerate(self.entries):
            if entry.kind != "Projection":
                continue
            try:
                read = _read(entry.files, entry.schemas, entry.kind)
            except TableError:
                continue
            table = read.table
            if _schema_problems(table.schema.empty_table(), PROJECTION_SCHEMA):
                continue
            files, rows = _origins(self.first_file[number], read.lengths)
            source = _array(table, "projection_of")
            frame = pa.table(
                {
                    "id": _strings(table, "id"),
                    "source": pc.struct_field(source, "timeline_id"),
                    "file": files,
                    "row": rows,
                    "order": _arange(len(table)),
                }
            )
            joined = frame.join(
                events.select(["id", "timeline_id"]), keys="id", join_type="left outer"
            ).sort_by("order")
            own = _held(pc.equal(joined["source"], joined["timeline_id"]))
            self._add_rows(
                "invalid_projection_of",
                joined,
                own,
                ("projection_of", "timeline_id"),
                lambda row: (
                    "a Projection stands for an event of another timeline than "
                    f"'{row['timeline_id']}'"
                ),
            )
            sources = _array(joined, "source")
            unknown = pc.and_(
                _held(pc.not_equal(sources, pa.scalar(""))),
                pc.is_null(self._owners(sources)),
            )
            self._add_rows(
                "unknown_timeline",
                joined,
                unknown,
                ("projection_of", "timeline_id"),
                lambda row: (
                    f"no manifest of the package has the timeline '{row['source']}'"
                ),
            )

    def _expected_index(self, claims: pa.Table, extractions: pa.Table) -> pa.Table:
        """The index rows the manifests, the MatchClaim tables and the
        Extraction table give: ``id``, ``resolved`` (the location),
        ``expected_kind``, ``expected_timeline_id``, ``expected_name`` and
        their ``position``."""
        rows: list[dict[str, Any]] = []
        for manifest in self.manifests:
            rows.extend(_index_rows_of(manifest.bare, manifest.file))
        strings = pa.schema(
            [
                pa.field(name, pa.string())
                for name in ("id", "kind", "location", "timeline_id", "name")
            ]
        )
        parts = [pa.Table.from_pylist(rows, schema=strings)]
        urls = pa.array([entry.url for entry in self.entries], pa.string())
        numbers = pa.array([entry.index for entry in self.entries], pa.int64())
        for table, kind in ((claims, "MatchClaim"), (extractions, "Extraction")):
            table = table.filter(pc.is_valid(_array(table, "id")))
            locations = urls.take(
                pc.index_in(_array(table, "entry"), value_set=numbers)
            )
            parts.append(
                pa.table(
                    {
                        "id": _array(table, "id"),
                        "kind": pa.repeat(pa.scalar(kind), len(table)),
                        "location": locations,
                        "timeline_id": pa.nulls(len(table), pa.string()),
                        "name": pa.nulls(len(table), pa.string()),
                    },
                    schema=strings,
                )
            )
        expected = pa.concat_tables(parts)
        return pa.table(
            {
                "id": _array(expected, "id"),
                "resolved": _array(expected, "location"),
                "expected_kind": _array(expected, "kind"),
                "expected_timeline_id": _array(expected, "timeline_id"),
                "expected_name": _array(expected, "name"),
                "position": _arange(len(expected)),
            }
        )

    def _stale(
        self, registry: pa.Table, claims: pa.Table, extractions: pa.Table
    ) -> None:
        """The registry's index rows against what the manifests, the
        MatchClaim tables and the Extraction table give (``stale_index``): the
        index rows of the index part (``index.parquet`` of a folder, else
        the file), an extra row (a location and ID given again among them
        included) or a differing one in the part's order, then each missing
        row by location and ID. Rows at a location that could not be read
        are not compared."""
        entry = self.registry
        if entry is None:
            return
        expected = self._expected_index(claims, extractions)
        at = f"{entry.url}index.parquet" if entry.url.endswith("/") else entry.url
        index = registry.filter(_held(pc.is_in(registry["kind"], _INDEX)))
        if at in self.names:
            part = pa.array([self.names.index(at)], pa.int64())
            index = index.filter(pc.is_in(index["file"], value_set=part))
        else:
            index = index.slice(0, 0)
        index = index.append_column("order", _arange(len(index)))
        locations = _array(index, "location")
        codes = _dense(locations)
        resolved = pa.array(
            [
                None if value is None else _resolved(value, "")
                for value in locations.take(_firsts(codes)).to_pylist()
            ],
            pa.string(),
        ).take(codes)
        index = index.append_column("resolved", resolved)
        unread = pa.array(sorted(self.unread), pa.string())
        index = index.filter(pc.invert(_held(pc.is_in(resolved, value_set=unread))))
        actual = index.select(
            ["order", "id", "resolved", *_COMPARED, "file", "row", "location"]
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
        joined = actual.join(
            unique, keys=["id", "resolved"], join_type="left outer"
        ).sort_by("order")
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
        flagged = flagged.filter(_any_of(extra, *differs.values()))
        for row in flagged.to_pylist():
            file = self.names[row["file"]]
            if row["extra"]:
                self.problems.add(
                    "stale_index",
                    file,
                    row["row"],
                    ("id",),
                    f"the index holds the ID '{row['id']}' at '{row['location']}', "
                    "which no manifest or table holds there",
                )
                continue
            for column in _COMPARED:
                if row[f"differs_{column}"]:
                    self.problems.add(
                        "stale_index",
                        file,
                        row["row"],
                        (column,),
                        f"the index row of the ID '{row['id']}' at "
                        f"'{row['location']}' has the {column} {row[column]!r}, "
                        f"not {row[f'expected_{column}']!r}",
                    )
        missing = expected.join(
            actual.select(["id", "resolved"]),
            keys=["id", "resolved"],
            join_type="left anti",
        ).sort_by([("resolved", "ascending"), ("id", "ascending")])
        for row in missing.to_pylist():
            self.problems.add(
                "stale_index",
                at,
                None,
                ("id",),
                f"the index lacks the ID '{row['id']}' at '{row['resolved']}'",
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
        the package rule, which compares each manifest's axis), the
        Extraction table's and each pre-parsed Projection table's, once and
        whole, in the order of the entries; then each MatchClaim table's,
        once per manifest whose resources name it, over that manifest's rows
        alone: each row's manifests are found once, by its timelines'
        listings, and the rows ordered by manifest, so that every manifest is
        checked on its own run of rows."""
        self.package = {
            (problem.code, problem.file, problem.row, problem.path)
            for problem in self.problems.found
        }
        self.reported: set[PackageProblem] = set(self.problems.found)
        for entry in self.entries:
            whole = _WHOLE.get(entry.kind)
            if whole is None or (
                entry.kind in ("Registry", "Extraction")
                and entry not in (self.registry, self.extraction)
            ):
                continue
            read = self._full(entry, runs=False)
            if read is None:
                continue
            everything = _arange(len(read.table))
            checked = [
                problem
                for problem in whole(read.table)
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
