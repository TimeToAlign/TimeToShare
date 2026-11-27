"""The tables of a package: reading a table, and checking a package whole.

A package is a folder with ``package.yaml`` at its root, which lists the
package's manifests and its tables (:func:`timetoshare.validate_package`).
A table is a file, or a folder of files read as one table when its URL ends
in ``/``: its files are the names ending in ``.parquet`` directly inside it,
none starting with ``.`` or ``_`` (:func:`table_files`). Files may hold the
rows of several manifests; a manifest finds its rows by the timelines its
resources list (:func:`read_table`).

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
    number_type_of,
)
from .checks import (
    EVENT_TIMELINES,
    MATCH_CLAIM_TIMELINES,
    TableCode,
    TableError,
    TableProblem,
    _array,
    _axis_admitted,
    _first_rows,
    _held,
    _shape,
    _shared_provenance,
    match_claim_problems,
    projection_problems,
)
from .columns import (
    MATCH_CLAIM_SCHEMA,
    PROJECTION_SCHEMA,
    PROVENANCE_METADATA_KEY,
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
    "table_type",
    "column_type_mismatch",
    "version_mismatch",
    "duplicate_timeline",
    "unknown_table",
    "duplicate_id",
    "unknown_timeline",
    "unlisted_timeline",
    "claim_across_manifests",
    "axis_mismatch",
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
    package of two manifests sharing their tables, or ``rejections/<case>``,
    each beside an ``expected.yaml``."""
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


def _rows_of(kind: str, timelines: Iterable[str] | None) -> ds.Expression | None:
    """The filter keeping the rows of ``timelines``: an event's own timeline,
    either timeline of a MatchClaim."""
    if timelines is None:
        return None
    listed = pa.array(list(timelines), pa.string())
    columns = _timeline_columns(kind)
    expression = ds.field(columns[0]).isin(listed)
    for column in columns[1:]:
        expression = expression | ds.field(column).isin(listed)
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
) -> _Read:
    """The files read as one table of ``kind``, file by file in order.

    The files' schemas are unified by name, a column a file lacks read as
    null; the filter of ``timelines`` is pushed into the reader. A
    MatchClaim file's shared provenance is filled into its rows before the
    files are joined, unless only ``columns`` are read.
    """
    schema = _unified(files, schemas)
    if columns is not None:
        schema = pa.schema(
            [schema.field(name) for name in columns if name in schema.names]
        )
    expression = _rows_of(kind, timelines)
    for name in _timeline_columns(kind) if expression is not None else ():
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


_DECLARED = {"MatchClaim": MATCH_CLAIM_SCHEMA, "Projection": PROJECTION_SCHEMA}
"""The table types the format defines, with their declared columns."""


def read_table(
    path: str | os.PathLike[str],
    *,
    timelines: Iterable[str] | None = None,
    type: str | None = None,  # noqa: A002 - the word the format uses
) -> pa.Table:
    """Read a table, a file or a folder of files, as one Arrow table.

    The files of a folder are :func:`table_files`'; they are read through
    ``pyarrow.dataset``, their schemas unified by name, a column a file
    lacks read as null. ``timelines`` (bare IDs) keeps, in the reader, the
    rows of those timelines: an event's whose ``timeline_id`` is listed, a
    MatchClaim's either of whose timelines is, so that a check sees a
    MatchClaim reaching outside them. A MatchClaim file's shared provenance
    (``timetoshare:provenance``) is filled into its own rows before the
    files are joined. The order of the rows is the files' order, then each
    file's; readers never rely on it.

    The table's type is what its files state (``timetoshare:type``), else
    ``type``; where both are stated they agree. The table returned states
    its type alone in its metadata. An empty folder gives no rows, in the
    declared columns of a MatchClaim or Projections table, in none for
    another type.

    Raises:
        FileNotFoundError: If ``path`` is neither a file nor a folder.
        TableError: If the files state two types, or another type than
            ``type``, or neither states one (``table_type``); if one column
            has two Arrow types in two files (``column_type_mismatch``); if
            ``timelines`` is given and the files lack a column naming a
            row's timeline (``schema_violation``); if a MatchClaim file's
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
        table = _read(files, schemas, kind, timelines).table
    return table.replace_schema_metadata({TYPE_METADATA_KEY: kind})


# The package check.

_BASE = "file:///package/"
"""The address a package's root is resolved at: references resolve as URLs,
and a reference leaving the package lies outside this prefix."""


_PARQUET = "application/vnd.apache.parquet"
"""The media type of a Parquet file."""


def is_table_resource(resource: Mapping[str, Any]) -> bool:
    """Whether a resource of a manifest names a table.

    A resource names a table when its type is ``MatchClaim`` or
    ``Projection``, its URL names a folder (ends in ``/``) or a Parquet file
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


def _timeline_paths(manifest: Mapping[str, Any]) -> dict[str, Path_]:
    """The path of the ``id`` of every timeline, at any depth, and of every
    virtual timeline of a manifest, the first of a repeated ID kept."""
    found: dict[str, Path_] = {}

    def visit(timeline: Mapping[str, Any], path: Path_) -> None:
        found.setdefault(timeline["id"], (*path, "id"))
        for index, child in enumerate(entries_of(timeline, "children")):
            visit(child, (*path, "children", index))

    for index, root in enumerate(entries_of(manifest, "timelines")):
        visit(root, ("timelines", index))
    for index, entry in enumerate(entries_of(manifest, "virtual_timelines")):
        found.setdefault(entry["id"], ("virtual_timelines", index, "id"))
    return found


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
    ``version_mismatch``). Then, manifest by manifest as listed, a file
    that is missing (``missing_file``) or that is no valid manifest (its
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

    - ``duplicate_timeline``: a timeline ID, a virtual timeline's included,
      held by two manifests, at the later's;
    - ``unknown_table``: a manifest's table resource whose URL names no
      table entry of the resource's type, or leads outside the package; a
      table resource is one of the type ``MatchClaim`` or ``Projection``,
      or one whose URL names a folder (ends in ``/``) or a Parquet file
      (ends in ``.parquet``), or whose media type is
      ``application/vnd.apache.parquet``. Any other resource, a recording,
      an image or a score file, is carried and not checked against the
      tables;
    - ``duplicate_id``: an event ID held twice among all event rows of the
      package, every type and file, then a MatchClaim ID twice among the
      MatchClaims, at the later row;
    - ``schema_violation``, then ``unknown_timeline``: a row's timeline (a
      MatchClaim's either, column by column) that is null, worded as the
      table checks word it (``'timeline_id' is null``), or that no manifest
      holds;
    - ``unlisted_timeline``: a row's timeline that its manifest's resources
      of the row's type, naming the row's table, do not list;
    - ``claim_across_manifests``: a MatchClaim whose timelines lie in two
      manifests;
    - ``axis_mismatch``: an event row stating a unit and number type its
      timeline does not have in its manifest.

    These read the columns ``id``, ``timeline_id``, ``unit`` and
    ``number_type`` of the event tables and ``id``, ``timeline_a_id`` and
    ``timeline_b_id`` of the MatchClaim tables, column by column. Last,
    manifest by manifest, the table checks of each MatchClaim or Projections
    table its resources name, in the order they first name it, over the rows
    of the timelines those resources list (:func:`match_claim_problems`,
    :func:`projection_problems`): each row's manifests are found once and the
    rows ordered by manifest, so each manifest is checked on its own rows
    alone, and each problem is placed in its file and row;
    a problem a package rule already reports at the same file, row and
    column with the same code, or an ``unknown_timeline`` on a MatchClaim
    reaching another manifest, is not repeated.

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
    version = value["timetoshare"]
    manifests = _manifests(root, value, problems)
    entries = _entries(root, value, version, problems)
    listed = {
        (url, entry["type"])
        for entry in value["tables"]
        if (url := _resolved(entry["url"], "")) is not None
    }
    _Check(listed, manifests, entries, problems).run()
    return problems.found


def _manifests(
    root: Path, value: Mapping[str, Any], problems: _Problems
) -> list[_Manifest]:
    """The manifests ``package.yaml`` lists that are valid, in its order."""
    found = []
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
            continue
        except SchemaValidationError as error:
            problems.add(error.code, file, None, error.path, error.message)
            continue
        found.append(_Manifest(file, manifest, with_bare_ids(manifest)))
    return found


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


_EVENT_COLUMNS = ("id", "timeline_id", "unit", "number_type")
_CLAIM_COLUMNS = ("id", "timeline_a_id", "timeline_b_id")
_CHECKED = {"MatchClaim": match_claim_problems, "Projection": projection_problems}


class _Check:
    """The package rules over the rows of every table, and the table checks."""

    def __init__(
        self,
        listed: set[tuple[str, str]],
        manifests: list[_Manifest],
        entries: list[_Entry],
        problems: _Problems,
    ) -> None:
        self.listed = listed
        self.manifests = manifests
        self.entries = entries
        self.problems = problems
        self.names = [name for entry in entries for name in entry.names]
        self.first_file = []
        count = 0
        for entry in entries:
            self.first_file.append(count)
            count += len(entry.files)

    def run(self) -> None:
        self._timelines()
        self._resources()
        events = self._rows(claims=False)
        claims = self._rows(claims=True)
        self._duplicates(events, "event")
        self._duplicates(claims, "MatchClaim")
        self._unknown(events, ("timeline_id",))
        self._unknown(claims, MATCH_CLAIM_TIMELINES)
        self._unlisted(events, ("timeline_id",))
        self._unlisted(claims, MATCH_CLAIM_TIMELINES)
        self._across(claims)
        self._axes(events)
        self._table_checks()

    # The manifests.

    def _timelines(self) -> None:
        """The owner and the axis of every timeline; ``duplicate_timeline``."""
        owners: dict[str, int] = {}
        axes: dict[str, tuple[str | None, str | None]] = {}
        for index, manifest in enumerate(self.manifests):
            paths = _timeline_paths(manifest.bare)
            for identifier, timeline in axes_by_id(manifest.bare).items():
                held = owners.setdefault(identifier, index)
                if held != index:
                    self.problems.add(
                        "duplicate_timeline",
                        manifest.file,
                        None,
                        paths[identifier],
                        f"the timeline '{identifier}' is a timeline of "
                        f"'{self.manifests[held].file}' as well",
                    )
                else:
                    axes[identifier] = _axis(timeline)
        self.timeline_ids = pa.array(list(owners), pa.string())
        self.owner_of = pa.array(list(owners.values()), pa.int64())
        self.unit_of = pa.array([axes[key][0] for key in owners], pa.string())
        self.number_type_of = pa.array([axes[key][1] for key in owners], pa.string())

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

    def _rows(self, *, claims: bool) -> pa.Table:
        """The identifying columns of every row of the event tables, or of
        the MatchClaim tables, with the table entry, the file (an index of
        :attr:`names`) and the row in the file of each."""
        columns = _CLAIM_COLUMNS if claims else _EVENT_COLUMNS
        timelines = MATCH_CLAIM_TIMELINES if claims else EVENT_TIMELINES
        parts = []
        for number, entry in enumerate(self.entries):
            if (entry.kind == "MatchClaim") != claims:
                continue
            read = _read(entry.files, entry.schemas, entry.kind, columns=columns)
            table = read.table
            files, rows = _origins(self.first_file[number], read.lengths)
            parts.append(
                pa.table(
                    {
                        **{name: _strings(table, name) for name in columns},
                        **{
                            _READ + name: pa.repeat(
                                pa.scalar(_is_strings(table, name)), len(table)
                            )
                            for name in timelines
                        },
                        "entry": pa.repeat(
                            pa.scalar(entry.index, pa.int64()), len(table)
                        ),
                        "file": files,
                        "row": rows,
                    }
                )
            )
        if not parts:
            return pa.table(
                {
                    **{name: pa.array([], pa.string()) for name in columns},
                    **{_READ + name: pa.array([], pa.bool_()) for name in timelines},
                    "entry": _arange(0),
                    "file": _arange(0),
                    "row": _arange(0),
                }
            )
        return pa.concat_tables(parts)

    def _add_rows(
        self,
        code: ProblemCode,
        rows: pa.Table,
        mask: pa.Array,
        column: str,
        message: Any,
    ) -> None:
        """Add a problem at each row ``mask`` flags, worded by ``message``
        from the row read in Python."""
        flagged = rows.filter(_held(mask)).to_pylist()
        for row in flagged:
            self.problems.add(
                code, self.names[row["file"]], row["row"], (column,), message(row)
            )

    def _owners(self, timelines: pa.Array) -> pa.Array:
        """The manifest holding each timeline, null where none does."""
        return self.owner_of.take(pc.index_in(timelines, value_set=self.timeline_ids))

    def _duplicates(self, rows: pa.Table, what: str) -> None:
        ids = _array(rows, "id")
        first = _first_rows(ids, ids)
        again = _held(pc.not_equal(first, _arange(len(ids))))
        again = pc.and_(again, pc.is_valid(ids))
        located = rows.append_column("first", first)

        def message(row: Mapping[str, Any]) -> str:
            held = located.slice(row["first"], 1).to_pylist()[0]
            return (
                f"the {what} ID '{row['id']}' is given twice, first in "
                f"'{self.names[held['file']]}' at row {held['row']}"
            )

        self._add_rows("duplicate_id", located, again, "id", message)

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

    def _across(self, claims: pa.Table) -> None:
        a = self._owners(_array(claims, "timeline_a_id"))
        b = self._owners(_array(claims, "timeline_b_id"))
        placed = claims.append_column("owner_a", a).append_column("owner_b", b)
        across = pc.not_equal(a, b)

        def message(row: Mapping[str, Any]) -> str:
            return (
                f"the MatchClaim joins the timeline '{row['timeline_a_id']}' of "
                f"'{self.manifests[row['owner_a']].file}' and the timeline "
                f"'{row['timeline_b_id']}' of '{self.manifests[row['owner_b']].file}'"
            )

        self._add_rows(
            "claim_across_manifests", placed, across, "timeline_b_id", message
        )
        self.across = {
            (row["file"], row["row"])
            for row in placed.filter(_held(across)).to_pylist()
        }

    def _axes(self, events: pa.Table) -> None:
        timelines = _array(events, "timeline_id")
        found = pc.index_in(timelines, value_set=self.timeline_ids)
        unit = self.unit_of.take(found)
        number_type = self.number_type_of.take(found)
        row_unit = _array(events, "unit")
        row_type = _array(events, "number_type")
        admitted = _axis_admitted(row_unit, row_type)
        held = pc.and_(pc.is_valid(found), admitted)
        unit_differs = _held(pc.not_equal(row_unit, unit))
        differs = pc.or_(unit_differs, _held(pc.not_equal(row_type, number_type)))
        placed = events.append_column("expected_unit", unit).append_column(
            "expected_number_type", number_type
        )
        for column, mask in (
            ("unit", pc.and_(held, unit_differs)),
            ("number_type", pc.and_(pc.and_(held, differs), pc.invert(unit_differs))),
        ):
            self._add_rows(
                "axis_mismatch",
                placed,
                mask,
                column,
                lambda row: (
                    f"a coordinate in {row['unit']} ({row['number_type']}) on the "
                    f"timeline '{row['timeline_id']}' in {row['expected_unit']} "
                    f"({row['expected_number_type']})"
                ),
            )

    # The table checks.

    def _table_checks(self) -> None:
        """The table checks of each MatchClaim or Projections table, once per
        manifest whose resources name it, over that manifest's rows alone:
        each row's manifests are found once, by its timelines' listings, and
        the rows ordered by manifest, so that every manifest is checked on
        its own run of rows."""
        package = {
            (problem.code, problem.file, problem.row, problem.path)
            for problem in self.problems.found
        }
        across = {(self.names[file], row) for file, row in self.across}
        full: dict[int, _Full | None] = {}
        reported: set[PackageProblem] = set(self.problems.found)
        for number, manifest in enumerate(self.manifests):
            checked_entries: set[int] = set()
            for index in range(len(entries_of(manifest.bare, "resources"))):
                entry = self.resolved.get((number, index))
                if (
                    entry is None
                    or entry.kind not in _CHECKED
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
                checked = _CHECKED[entry.kind](read.table.take(taken), manifest.value)
                for problem in checked:
                    if problem.row is None:
                        file, row = entry.url, None
                    else:
                        at = taken[problem.row].as_py()
                        file = self.names[read.files[at].as_py()]
                        row = read.rows[at].as_py()
                    if (problem.code, file, row, problem.column) in package:
                        continue
                    if problem.code == "unknown_timeline" and (file, row) in across:
                        continue
                    placed = PackageProblem(
                        problem.code, file, row, problem.column, problem.message
                    )
                    if placed not in reported:
                        reported.add(placed)
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

    def _full(self, entry: _Entry) -> _Full | None:
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
        return _Full(read.table, files, rows, self._runs(entry, read.table))


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
