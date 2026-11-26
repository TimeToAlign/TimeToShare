"""The checks of the MatchClaim table and the Projections table.

Each ``*_problems`` function lists every problem it finds, the table's own
first, then row by row; each ``check_*`` function raises the first as a
``TableError``. A table may hold columns its type does not declare; they are
kept and never checked.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any, Literal

import pyarrow as pa
import pyarrow.compute as pc
from jsonschema import Draft202012Validator

from ..ids import with_bare_ids
from ..manifest import UNITS
from ..statements import calendar_date, expand_iri
from ..validate import PROVENANCE_DEFINITION, load_schema, select, worded
from ..validation.diagnostics import axes_by_id, json_pointer, number_type_of
from .columns import (
    BELIEF_KEYS,
    COORDINATE_KEYS,
    MATCH_CLAIM_REQUIRED,
    MATCH_CLAIM_SCHEMA,
    NUMBER_KEYS,
    NUMBER_MEMBERS,
    PROJECTION_REQUIRED,
    PROJECTION_SCHEMA,
    PROVENANCE_KEYS,
    PROVENANCE_METADATA_KEY,
    coordinate_value,
)

__all__ = [
    "TableCode",
    "TableError",
    "TableProblem",
    "check_match_claims",
    "check_projections",
    "check_succession",
    "match_claim_problems",
    "projection_problems",
    "row_provenance",
    "succession_problems",
]

TableCode = Literal[
    "schema_violation",
    "invalid_id",
    "duplicate_id",
    "invalid_coordinate",
    "claim_events",
    "claim_timelines",
    "claim_anchors",
    "invalid_certainty",
    "invalid_provenance",
    "axis_mismatch",
    "unknown_timeline",
    "invalid_projection_of",
    "invalid_duration",
    "succession_missing",
    "succession_changed",
]

Column = tuple[str, ...]


@dataclass(frozen=True)
class TableProblem:
    """One problem of a table: its code, its row (``None`` for the whole
    table), the path of its column and its message."""

    code: TableCode
    row: int | None
    column: Column
    message: str


class TableError(ValueError):
    """A table breaks a rule; ``problem`` is the first problem found."""

    def __init__(self, problem: TableProblem) -> None:
        super().__init__(problem.message)
        self.problem = problem


_CONTROL = re.compile(r"[\x00-\x1f]")
"""A control character, in the syntax of Python's ``re`` and of RE2 (``pyarrow``)."""


def _shape(data_type: pa.DataType) -> Any:
    """A type's shape, blind to nullability and to the name of list items."""
    if pa.types.is_struct(data_type):
        return ("struct", tuple((f.name, _shape(f.type)) for f in data_type))
    if pa.types.is_list(data_type):
        return ("list", _shape(data_type.value_type))
    return str(data_type)


def _schema_problems(table: pa.Table, schema: pa.Schema) -> list[TableProblem]:
    problems = []
    for field in schema:
        if field.name not in table.column_names:
            problems.append(
                TableProblem(
                    "schema_violation",
                    None,
                    (field.name,),
                    f"the table has no column '{field.name}'",
                )
            )
        elif _shape(table.schema.field(field.name).type) != _shape(field.type):
            problems.append(
                TableProblem(
                    "schema_violation",
                    None,
                    (field.name,),
                    f"the column '{field.name}' is "
                    f"{table.schema.field(field.name).type}, not {field.type}",
                )
            )
    return problems


def _id_problem(value: Any, what: str) -> str | None:
    if value == "":
        return f"{what} is empty"
    if _CONTROL.search(value):
        return f"{what} {value!r} holds a control character"
    return None


def _axis_problem(unit: str, number_type: str) -> str | None:
    """Why a unit and a number type, both stated, are no axis, or ``None``.

    The unit is one of :data:`~timetoshare.UNITS`, the number type one of the
    three, and one the unit admits."""
    if unit not in UNITS:
        return f"'{unit}' is no unit"
    if number_type not in NUMBER_MEMBERS:
        return f"'{number_type}' is no number type"
    if number_type not in UNITS[unit].number_types:
        return f"'{unit}' admits no number type '{number_type}'"
    return None


def _number_problem(
    number: Mapping[str, Any], number_type: str, what: str
) -> str | None:
    """Why a non-null number is no number of ``number_type``, or ``None``.

    A number fills the members of its number type and leaves the others
    null (:data:`~timetoshare.tables.NUMBER_MEMBERS`); a float is finite, a
    fraction's denominator at least 1.
    """
    held = NUMBER_MEMBERS[number_type]
    kind = f"{'an' if number_type == 'int' else 'a'} {number_type} {what}"
    for key in held:
        if number[key] is None:
            return f"{kind} has no {key}"
    for key in NUMBER_KEYS:
        if key not in held and number[key] is not None:
            return f"{kind} holds its {' and '.join(held)} alone, not a {key}"
    if number_type == "float" and not math.isfinite(number["value"]):
        return f"the {what}'s value {number['value']} is not finite"
    if number_type == "fraction" and number["denominator"] < 1:
        return f"the {what}'s denominator {number['denominator']} is below 1"
    return None


@cache
def _provenance_validator() -> Draft202012Validator:
    """The validator of one provenance entry: the provenance schema's root."""
    definitions = load_schema()["$defs"]
    return Draft202012Validator(
        {"$defs": definitions, "$ref": f"#/$defs/{PROVENANCE_DEFINITION}"}
    )


def _present(cell: Mapping[str, Any]) -> dict[str, Any]:
    """A row's provenance cell as the entry it holds: a null member is absent."""
    entry = {key: value for key, value in cell.items() if value is not None}
    if "beliefs" in entry:
        entry["beliefs"] = [
            {key: value for key, value in belief.items() if value is not None}
            if isinstance(belief, Mapping)
            else belief
            for belief in entry["beliefs"]
        ]
    return entry


def _provenance_problem(
    entry: Any, what: str, context: Mapping[str, Any] | None
) -> str | None:
    """Why a provenance entry is no entry of the provenance schema, or ``None``.

    The schema first, its problem chosen by the validators' one path rule;
    then a key the schema does not declare, of the entry or of a belief;
    then a date that is no day of the Gregorian calendar; then an actor
    holding a second belief, actors compared as the IRIs they stand for
    under ``context`` (the manifest's ``@context``), else as written.
    ``what`` names the entry in the message, and the member at fault follows
    as a JSON pointer into it.
    """
    error = select(_provenance_validator().iter_errors(entry))
    if error is not None:
        return f"{what} {json_pointer(error.absolute_path)}: {worded(error)}"
    beliefs = entry.get("beliefs", [])
    for keys, known, path, kind in (
        (entry, PROVENANCE_KEYS, (), "a provenance entry"),
        *(
            (belief, BELIEF_KEYS, ("beliefs", index), "a belief")
            for index, belief in enumerate(beliefs)
        ),
    ):
        unknown = sorted(set(keys) - set(known))
        if unknown:
            return f"{what} {json_pointer(path)}: '{unknown[0]}' is no key of {kind}"
    dates = [(("date",), entry["date"])] if "date" in entry else []
    dates.extend(
        (("beliefs", index, "date"), belief["date"])
        for index, belief in enumerate(beliefs)
    )
    for path, date in dates:
        try:
            calendar_date(date)
        except ValueError as problem:
            return f"{what} {json_pointer(path)}: {problem}"
    held: dict[str, int] = {}
    for index, belief in enumerate(beliefs):
        actor = expand_iri(context, belief["actor"]) or belief["actor"]
        if actor in held:
            return (
                f"{what} {json_pointer(('beliefs', index, 'actor'))}: "
                f"'{belief['actor']}' already holds belief {held[actor]} of this "
                "entry; an actor holds one belief"
            )
        held[actor] = index
    return None


def _shared_provenance(
    table: pa.Table, context: Mapping[str, Any] | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """The provenance the file's metadata states for every row, and a problem.

    The entry is checked as a row's is, and returned with every member,
    an absent one ``None``, as a row's cell holds it.
    """
    metadata = table.schema.metadata or {}
    text = metadata.get(PROVENANCE_METADATA_KEY.encode())
    if text is None:
        return None, None
    try:
        entry = json.loads(text)
    except ValueError:
        return None, "the file's provenance is no JSON text"
    if not isinstance(entry, dict):
        return None, "the file's provenance is no object"
    problem = _provenance_problem(entry, "the file's provenance", context)
    if problem:
        return None, problem
    cell = {key: entry.get(key) for key in PROVENANCE_KEYS}
    if cell["beliefs"] is not None:
        cell["beliefs"] = [
            {key: belief.get(key) for key in BELIEF_KEYS} for belief in cell["beliefs"]
        ]
    return cell, None


def row_provenance(table: pa.Table) -> list[dict[str, Any] | None]:
    """The provenance of every row of a checked MatchClaim table: its own, or
    the file's where the row states none."""
    shared, _ = _shared_provenance(table)
    return [
        cell if cell is not None else shared
        for cell in table.column("provenance").to_pylist()
    ]


# The rules are computed over whole columns. Python reads only the cells a
# rule flags, to word their problems, and one cell per distinct provenance
# cell, to check it against the provenance schema; every problem is then put
# where a reading row by row lists it (``_Found``). A Python value handed to
# pyarrow.compute is converted on every call, which costs more than the call
# on a small table, so the constants below are converted once.

_FALSE = pa.scalar(False)
_ZERO = pa.scalar(0, pa.int64())
_ONE = pa.scalar(1, pa.int64())
_ZERO32 = pa.scalar(0, pa.int32())
_EMPTY = pa.scalar("")
_COMMA = pa.scalar(",")
_NO_ROW = pa.scalar(None, pa.int64())
_ENCODE = pc.DictionaryEncodeOptions(null_encoding="encode")
_KINDS = {kind: pa.scalar(kind) for kind in NUMBER_MEMBERS}
_ADMITTING = {
    kind: pa.array(
        [name for name, entry in UNITS.items() if kind in entry.number_types],
        pa.string(),
    )
    for kind in NUMBER_MEMBERS
}
"""The units admitting each number type."""


def _array(table: pa.Table, name: str) -> pa.Array:
    """A column as one array, however many chunks the table holds it in."""
    return table.column(name).combine_chunks()


def _utf8(values: pa.Array) -> bool:
    """Whether every string the values hold where they are stated is UTF-8:
    a member under a null struct, an item of a null list and a null string
    are not read."""
    kind = values.type
    if pa.types.is_struct(kind):
        return all(_utf8(member) for member in values.flatten())
    if pa.types.is_list(kind):
        return _utf8(values.flatten())
    if pa.types.is_string(kind):
        try:
            values.validate(full=True)
        except pa.ArrowInvalid:
            return False
    return True


def _readable(table: pa.Table, names: list[str]) -> None:
    """Raise, as reading the columns in Python raises, where a string they
    state is no UTF-8: the first such string in the order of the columns,
    then of their rows, is read, which raises ``UnicodeDecodeError``."""
    for name in names:
        column = table.column(name)
        if not all(_utf8(chunk) for chunk in column.chunks):
            column.to_pylist()


def _held(mask: pa.Array) -> pa.Array:
    """A mask with every null read as false."""
    return pc.coalesce(mask, _FALSE)


def _all(*masks: pa.Array) -> pa.Array:
    """Where every mask (none of them null) holds."""
    result = masks[0]
    for mask in masks[1:]:
        result = pc.and_(result, mask)
    return result


def _any(*masks: pa.Array) -> pa.Array:
    """Where some mask (none of them null) holds."""
    result = masks[0]
    for mask in masks[1:]:
        result = pc.or_(result, mask)
    return result


def _not(mask: pa.Array) -> pa.Array:
    return pc.invert(mask)


def _int(value: int) -> pa.Scalar:
    """An integer as an Arrow scalar, without converting a Python scalar."""
    return pa.array([value], pa.int64())[0]


def _member(values: pa.Array, name: str) -> pa.Array:
    """A member of a struct array, null where the struct is."""
    return values.flatten()[values.type.get_field_index(name)]


def _indices(mask: pa.Array) -> pa.Array:
    """The rows where a mask holds, in order."""
    return pc.indices_nonzero(_held(mask)).cast(pa.int64())


def _rows(mask: pa.Array) -> list[int]:
    return pc.indices_nonzero(_held(mask)).to_pylist()


def _at(values: pa.Array, rows: list[int]) -> list[Any]:
    """The values at some rows, as Python values."""
    if not rows:
        return []
    return values.take(pa.array(rows, pa.int64())).to_pylist()


def _dense(values: pa.Array) -> pa.Array:
    """The values numbered from 0 in the order they first occur, null one of them."""
    return pc.dictionary_encode(values, options=_ENCODE).indices.cast(pa.int64())


def _firsts(codes: pa.Array) -> pa.Array:
    """For each code of :func:`_dense`, the row it first occurs in: codes are
    numbered in that order, so the ``k``-th row where a code exceeds every
    code before it is where code ``k`` first occurs."""
    if len(codes) == 0:
        return codes
    before = pa.concat_arrays(
        [pa.array([-1], pa.int64()), pc.cumulative_max(codes)[:-1]]
    )
    return _indices(pc.greater(codes, before))


def _first_rows(keys: pa.Array, lookup: pa.Array) -> pa.Array:
    """For each value of ``lookup``, the first row of ``keys`` holding it
    (null matching null), else null."""
    codes = _dense(pa.concat_arrays([keys, lookup]))
    rows = _firsts(codes).take(codes[len(keys) :])
    return pc.if_else(pc.less(rows, _int(len(keys))), rows, _NO_ROW)


class _Found:
    """The problems found, listed as a reading row by row lists them.

    Each problem is added with the row it is read at (``-1`` for the
    table's own) and the place of its rule in the reading of a row; the
    list is ordered by row, then place, then the order of adding.
    """

    def __init__(self) -> None:
        self._found: list[tuple[int, int, int, TableProblem]] = []

    def add(self, row: int, place: int, problem: TableProblem) -> None:
        """Add a problem read at ``row`` by the rule at ``place``.

        Raises:
            AssertionError: If the problem has no message.
        """
        if problem.message is None:
            # A rule's mask flagged a cell its message helper finds sound.
            raise AssertionError(f"no message for '{problem.code}' at row {row}")
        self._found.append((row, place, len(self._found), problem))

    def problems(self) -> list[TableProblem]:
        """The problems added, by row, then place, then the order of adding."""
        return [found[3] for found in sorted(self._found, key=lambda f: f[:3])]


def _null_problems(table: pa.Table, required: tuple[str, ...]) -> list[TableProblem]:
    found = _Found()
    for place, key in enumerate(required):
        for row in _rows(pc.is_null(_array(table, key))):
            found.add(
                row,
                place,
                TableProblem("schema_violation", row, (key,), f"'{key}' is null"),
            )
    return found.problems()


def _malformed(values: pa.Array) -> pa.Array:
    """Where a string is an ID :func:`_id_problem` refuses: empty, or holding
    a control character."""
    return _held(
        pc.or_(
            pc.equal(values, _EMPTY),
            pc.match_substring_regex(values, _CONTROL.pattern),
        )
    )


def _id_problems(found: _Found, ids: pa.Array) -> None:
    """Each ID valid, and given once in the table.

    A MatchClaim is addressed by its ID alone; a Projection's ID is unique
    in the package, as every event's, so two timelines never share one.
    """
    malformed = _malformed(ids)
    rows = _rows(malformed)
    for row, value in zip(rows, _at(ids, rows), strict=True):
        found.add(
            row,
            0,
            TableProblem("invalid_id", row, ("id",), _id_problem(value, "the ID")),
        )
    first = _first_rows(ids, ids)
    again = _held(pc.not_equal(first, pa.array(range(len(ids)), pa.int64())))
    rows = _rows(_all(again, _not(malformed), pc.is_valid(ids)))
    for row, value in zip(rows, _at(ids, rows), strict=True):
        found.add(
            row,
            0,
            TableProblem(
                "duplicate_id", row, ("id",), f"the ID '{value}' is given twice"
            ),
        )


class _Manifest:
    """A manifest's timelines and virtual timelines by ID. A timeline's axis
    is read only where a sound cell or an admitted row lies on it, so a
    timeline no checked cell names is never read."""

    def __init__(self, manifest: Mapping[str, Any]) -> None:
        self.timelines = axes_by_id(with_bare_ids(manifest))
        self.ids = pa.array(
            [key for key in self.timelines if isinstance(key, str)], pa.string()
        )

    def unknown(self, timelines: pa.Array) -> pa.Array:
        """Where a timeline ID names no timeline of the manifest."""
        return _not(pc.is_in(timelines, value_set=self.ids))

    def axis(self, timeline_id: str) -> tuple[Any, Any] | None:
        """The unit and number type of a timeline as the manifest states
        them, whatever their type, or ``None`` where it has no such timeline.
        A timeline whose unit is missing or unknown and which states no
        number type has no axis: its number type is ``None``."""
        timeline = self.timelines.get(timeline_id)
        if timeline is None:
            return None
        unit = timeline.get("unit")
        try:
            return (unit, number_type_of(timeline))
        except (KeyError, TypeError):
            return (unit, None)


def _unknown_problems(
    found: _Found,
    manifest: _Manifest,
    timelines: pa.Array,
    place: int,
    column: Column,
    mask: pa.Array | None = None,
) -> None:
    unknown = manifest.unknown(timelines)
    rows = _rows(unknown if mask is None else _all(mask, unknown))
    for row, value in zip(rows, _at(timelines, rows), strict=True):
        found.add(
            row,
            place,
            TableProblem(
                "unknown_timeline",
                row,
                column,
                f"the manifest has no timeline '{value}'",
            ),
        )


def _axis_admitted(unit: pa.Array, number_type: pa.Array) -> pa.Array:
    """Where a unit and a number type make an axis (:func:`_axis_problem`)."""
    return _any(
        *(
            _all(
                _held(pc.equal(number_type, _KINDS[kind])),
                pc.is_in(unit, value_set=_ADMITTING[kind]),
            )
            for kind in NUMBER_MEMBERS
        )
    )


def _number_held(number: pa.Array, number_type: pa.Array) -> pa.Array:
    """Where a non-null number is a number of its number type
    (:func:`_number_problem`): the members of the type filled, the others
    null, a float finite, a fraction's denominator at least 1."""
    filled = {key: pc.is_valid(_member(number, key)) for key in NUMBER_KEYS}
    bounded = {
        "float": _held(pc.is_finite(_member(number, "value"))),
        "fraction": _held(pc.greater_equal(_member(number, "denominator"), _ONE)),
    }
    return _any(
        *(
            _all(
                _held(pc.equal(number_type, _KINDS[kind])),
                *(
                    filled[key] if key in held else _not(filled[key])
                    for key in NUMBER_KEYS
                ),
                *([bounded[kind]] if kind in bounded else []),
            )
            for kind, held in NUMBER_MEMBERS.items()
        )
    )


def _mismatched(cells: pa.Table, manifest: _Manifest | None) -> list[dict[str, Any]]:
    """The cells whose axis is not the axis of their timeline's cells.

    ``cells`` holds one row per cell stating an axis: its ``order`` of
    reading, its ``timeline``, ``unit`` and ``number_type`` (both strings,
    the cell being sound), and whatever its caller words a problem with. A
    timeline's cells have the axis of the manifest's timeline where a
    manifest is given (a timeline it lacks checks none), else the axis of
    the first cell read on the timeline. Each mismatched cell is returned
    with that axis added, as ``expected_unit`` and ``expected_number_type``.

    The manifest's axes are read in Python, one per timeline in the order
    the timelines are first read, as a reading row by row reads them: a
    unit or number type that is no string (null included) matches no cell.
    """
    cells = cells.sort_by("order")
    timelines = _array(cells, "timeline")
    codes = _dense(timelines)
    firsts = _firsts(codes)
    if manifest is not None:
        axes = [manifest.axis(key) for key in timelines.take(firsts).to_pylist()]
    else:
        axes = list(
            zip(
                _array(cells, "unit").take(firsts).to_pylist(),
                _array(cells, "number_type").take(firsts).to_pylist(),
                strict=True,
            )
        )
    plain = [
        axis is not None and all(isinstance(part, str) for part in axis)
        for axis in axes
    ]
    checked = pa.array([axis is not None for axis in axes], pa.bool_()).take(codes)
    strange = pa.array(
        [axis is not None and not ok for axis, ok in zip(axes, plain, strict=True)],
        pa.bool_(),
    ).take(codes)
    unit, number_type = (
        pa.array(
            [axis[part] if ok else None for axis, ok in zip(axes, plain, strict=True)],
            pa.string(),
        ).take(codes)
        for part in (0, 1)
    )
    differs = _all(
        checked,
        _any(
            strange,
            _held(pc.not_equal(_array(cells, "unit"), unit)),
            _held(pc.not_equal(_array(cells, "number_type"), number_type)),
        ),
    )
    mismatched = cells.append_column("code", codes).filter(differs).to_pylist()
    for cell in mismatched:
        cell["expected_unit"], cell["expected_number_type"] = axes[cell.pop("code")]
    return mismatched


def _mismatch(cell: Mapping[str, Any], manifest: bool) -> str:
    axis = f"{cell['unit']} ({cell['number_type']})"
    expected = f"{cell['expected_unit']} ({cell['expected_number_type']})"
    if manifest and cell["expected_number_type"] is None:
        unit = cell["expected_unit"]
        return f"a coordinate in {axis} on the timeline '{cell['timeline']}', " + (
            "which has no unit" if unit is None else f"whose unit {unit!r} is unknown"
        )
    if manifest:
        return (
            f"a coordinate in {axis} on the timeline '{cell['timeline']}' in {expected}"
        )
    return (
        f"the timeline '{cell['timeline']}' has coordinates in {expected} and in {axis}"
    )


def _cell_problem(cell: Mapping[str, Any] | None) -> str | None:
    """Why an anchor's coordinate cell, which states its own axis, is no
    coordinate."""
    if cell is None:
        return "the coordinate is null"
    for key in ("unit", "number_type"):
        if cell[key] is None:
            return f"the coordinate has no {key}"
    return _axis_problem(cell["unit"], cell["number_type"]) or _number_problem(
        cell, cell["number_type"], "coordinate"
    )


_CELLS = tuple(
    (name, f"coordinate_{side}")
    for name in ("start_anchor", "end_anchor")
    for side in ("a", "b")
)
"""The coordinate cells of a MatchClaim, in the order a row is read."""


def _claim_problems(found: _Found, table: pa.Table, manifest: _Manifest | None) -> None:
    """The rules of a MatchClaim's timelines, events, anchors, cells and
    certainty, at the places 1 to 12 of a row."""
    sides = {
        "a": _array(table, "timeline_a_id"),
        "b": _array(table, "timeline_b_id"),
    }
    if manifest is not None:
        for place, side in ((1, "a"), (2, "b")):
            _unknown_problems(
                found,
                manifest,
                sides[side],
                place,
                (f"timeline_{side}_id",),
            )
    rows = _rows(pc.equal(sides["a"], sides["b"]))
    for row, value in zip(rows, _at(sides["a"], rows), strict=True):
        found.add(
            row,
            3,
            TableProblem(
                "claim_timelines", row, ("timeline_b_id",), f"both sides are '{value}'"
            ),
        )
    for place, key in ((4, "event_a_id"), (5, "event_b_id")):
        events = _array(table, key)
        rows = _rows(_malformed(events))
        for row, value in zip(rows, _at(events, rows), strict=True):
            found.add(
                row,
                place,
                TableProblem(
                    "invalid_id", row, (key,), _id_problem(value, "the event ID")
                ),
            )
    _anchor_problems(found, table)
    _cell_problems(found, table, sides, manifest)
    certainty = _array(table, "certainty")
    inside = _all(
        _held(pc.greater_equal(certainty, _ZERO)),
        _held(pc.less_equal(certainty, _ONE)),
    )
    rows = _rows(_all(pc.is_valid(certainty), _not(inside)))
    for row, value in zip(rows, _at(certainty, rows), strict=True):
        found.add(
            row,
            12,
            TableProblem(
                "invalid_certainty",
                row,
                ("certainty",),
                f"the certainty {value} lies outside [0, 1]",
            ),
        )


def _anchor_problems(found: _Found, table: pa.Table) -> None:
    """Which anchors a MatchClaim has, by its events and whether it is
    synchronous: one problem at most at place 6, and an end anchor without
    a start at place 7."""
    without_a = pc.is_null(_array(table, "event_a_id"))
    without_b = pc.is_null(_array(table, "event_b_id"))
    synchronous = _array(table, "is_synchronous")
    start = pc.is_valid(_array(table, "start_anchor"))
    end = pc.is_valid(_array(table, "end_anchor"))
    anchored = _any(start, end)
    nomatch = pc.xor(without_a, without_b)
    both = _all(_not(without_a), _not(without_b))
    rules: tuple[tuple[TableCode, pa.Array, str | None, str], ...] = (
        (
            "claim_events",
            _all(without_a, without_b),
            "event_a_id",
            "the MatchClaim names no event",
        ),
        (
            "claim_anchors",
            _all(nomatch, synchronous),
            "is_synchronous",
            "a NOMATCH MatchClaim is not synchronous",
        ),
        (
            "claim_anchors",
            _all(nomatch, _not(synchronous), anchored),
            None,
            "a NOMATCH MatchClaim has no anchors",
        ),
        (
            "claim_anchors",
            _all(both, synchronous, _not(start)),
            "start_anchor",
            "a synchronous MatchClaim has a start anchor",
        ),
        (
            "claim_anchors",
            _all(both, _not(synchronous), anchored),
            None,
            "a conceptual MatchClaim has no anchors",
        ),
        (
            "claim_anchors",
            _all(end, _not(start)),
            "end_anchor",
            "an end anchor needs a start anchor",
        ),
    )
    for place, (code, mask, key, message) in enumerate(rules):
        rows = _rows(mask)
        for row, starts in zip(rows, _at(start, rows), strict=True):
            column = key or ("start_anchor" if starts else "end_anchor")
            found.add(
                row, 6 if place < 5 else 7, TableProblem(code, row, (column,), message)
            )


def _cell_problems(
    found: _Found,
    table: pa.Table,
    sides: Mapping[str, pa.Array],
    manifest: _Manifest | None,
) -> None:
    """The coordinate cells of the anchors a row has, at places 8 to 11: a
    cell that is no coordinate, else one off its timeline's axis."""
    axes = []
    for place, (name, member) in enumerate(_CELLS):
        anchor = _array(table, name)
        cell = _member(anchor, member)
        unit = _member(cell, "unit")
        number_type = _member(cell, "number_type")
        present = pc.is_valid(anchor)
        sound = _all(
            pc.is_valid(cell),
            _axis_admitted(unit, number_type),
            _number_held(cell, number_type),
        )
        rows = _rows(_all(present, _not(sound)))
        for row, value in zip(rows, _at(cell, rows), strict=True):
            found.add(
                row,
                8 + place,
                TableProblem(
                    "invalid_coordinate", row, (name, member), _cell_problem(value)
                ),
            )
        rows_sound = _indices(_all(present, sound))
        axes.append(
            pa.table(
                {
                    "order": pc.add(
                        pc.multiply(rows_sound, _int(len(_CELLS))), _int(place)
                    ),
                    "row": rows_sound,
                    "timeline": sides[member[-1]].take(rows_sound),
                    "unit": unit.take(rows_sound),
                    "number_type": number_type.take(rows_sound),
                }
            )
        )
    for cell in _mismatched(pa.concat_tables(axes), manifest):
        row, place = divmod(cell["order"], len(_CELLS))
        found.add(
            row,
            8 + place,
            TableProblem(
                "axis_mismatch",
                row,
                _CELLS[place],
                _mismatch(cell, manifest is not None),
            ),
        )


def _codes(values: pa.Array) -> pa.Array:
    """A code per value, two codes equal exactly where the two values read
    in Python (``to_pylist``) are equal; for strings, booleans, integers and
    the lists and structs of them."""
    kind = values.type
    if pa.types.is_struct(kind):
        return _combined(
            [
                pc.cast(pc.is_valid(values), pa.int64()),
                *(_codes(member) for member in values.flatten()),
            ]
        )
    if pa.types.is_list(kind):
        lengths = pc.coalesce(pc.list_value_length(values), _ZERO32)
        offsets = pa.concat_arrays(
            [pa.array([0], pa.int32()), pc.cumulative_sum(lengths).cast(pa.int32())]
        )
        items = pc.cast(_codes(pc.list_flatten(values)), pa.string())
        joined = pc.binary_join(pa.ListArray.from_arrays(offsets, items), _COMMA)
        return _combined([pc.cast(pc.is_valid(values), pa.int64()), _dense(joined)])
    if (
        pa.types.is_string(kind)
        or pa.types.is_boolean(kind)
        or pa.types.is_integer(kind)
    ):
        return _dense(values)
    raise TypeError(f"no codes for values of the type {kind}")


def _combined(parts: list[pa.Array]) -> pa.Array:
    """One code per row for the tuple of the rows' codes, numbered from 0."""
    code = parts[0]
    for part in parts[1:]:
        width = (pc.max(part).as_py() or 0) + 1
        code = _dense(pc.add_checked(pc.multiply_checked(code, _int(width)), part))
    return code


def _row_provenance_problems(
    found: _Found,
    cells: pa.Array,
    shared: bool,
    context: Mapping[str, Any] | None,
) -> None:
    """The provenance of each row, at place 13: none beside the file's, and
    each a provenance entry; each distinct cell is checked once."""
    present = pc.is_valid(cells)
    if shared:
        for row in _rows(present):
            found.add(
                row,
                13,
                TableProblem(
                    "invalid_provenance",
                    row,
                    ("provenance",),
                    "the provenance is stated in the file's metadata and in the row",
                ),
            )
        return
    codes = _codes(cells)
    stated = _indices(present)
    first = _firsts(_dense(codes.take(stated)))
    distinct = stated.take(first).to_pylist()
    failing = {}
    for code, cell in zip(_at(codes, distinct), _at(cells, distinct), strict=True):
        problem = _provenance_problem(_present(cell), "the provenance", context)
        if problem:
            failing[code] = problem
    if not failing:
        return
    rows = _rows(
        _all(present, pc.is_in(codes, value_set=pa.array(list(failing), pa.int64())))
    )
    for row, code in zip(rows, _at(codes, rows), strict=True):
        found.add(
            row,
            13,
            TableProblem("invalid_provenance", row, ("provenance",), failing[code]),
        )


def match_claim_problems(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> list[TableProblem]:
    """Every problem of a MatchClaim table, checked against a manifest (as
    read from its file, IDs written ``#``) where one is given.

    A MatchClaim's ID is unique in the table, which belongs to one manifest. An
    actor holds one belief in a row; against a manifest, actors are compared
    as the IRIs they stand for under its ``@context``, so a compact and an
    absolute IRI of one actor are one actor, else as written."""
    problems = _schema_problems(table, MATCH_CLAIM_SCHEMA)
    if problems:
        return problems
    _readable(table, MATCH_CLAIM_SCHEMA.names)
    problems = _null_problems(table, MATCH_CLAIM_REQUIRED)
    if problems:
        return problems
    found = _Found()
    _id_problems(found, _array(table, "id"))
    shared = PROVENANCE_METADATA_KEY.encode() in (table.schema.metadata or {})
    context = None if manifest is None else manifest.get("@context")
    _, problem = _shared_provenance(table, context)
    if problem:
        found.add(
            -1, 0, TableProblem("invalid_provenance", None, ("provenance",), problem)
        )
    _claim_problems(found, table, None if manifest is None else _Manifest(manifest))
    _row_provenance_problems(found, _array(table, "provenance"), shared, context)
    return found.problems()


def projection_problems(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> list[TableProblem]:
    """Every problem of a Projections table, checked against a manifest (as
    read from its file, IDs written ``#``) where one is given.

    A Projection's ID is unique in the package, as every event's: two
    timelines never both hold ``projection_1``."""
    problems = _schema_problems(table, PROJECTION_SCHEMA)
    if problems:
        return problems
    _readable(table, PROJECTION_SCHEMA.names)
    problems = _null_problems(table, PROJECTION_REQUIRED)
    if problems:
        return problems
    found = _Found()
    _id_problems(found, _array(table, "id"))
    axes = None if manifest is None else _Manifest(manifest)
    timelines = _array(table, "timeline_id")
    if axes is not None:
        _unknown_problems(found, axes, timelines, 1, ("timeline_id",))
    _projection_numbers(found, table, timelines, axes)
    _projected_events(found, table, timelines, axes)
    return found.problems()


def _projection_numbers(
    found: _Found, table: pa.Table, timelines: pa.Array, manifest: _Manifest | None
) -> None:
    """The problems of a Projection's axis (place 2), ``start`` (3) and
    ``duration`` (4): its row states the unit and the number type of both,
    never null here; a row without an axis has no numbers checked."""
    unit, number_type = _array(table, "unit"), _array(table, "number_type")
    admitted = _axis_admitted(unit, number_type)
    rows = _rows(_not(admitted))
    for row, row_unit, row_type in zip(
        rows, _at(unit, rows), _at(number_type, rows), strict=True
    ):
        column = "unit" if row_unit not in UNITS else "number_type"
        found.add(
            row,
            2,
            TableProblem(
                "invalid_coordinate",
                row,
                (column,),
                _axis_problem(row_unit, row_type),
            ),
        )
    stated = _indices(admitted)
    axes = pa.table(
        {
            "order": stated,
            "row": stated,
            "timeline": timelines.take(stated),
            "unit": unit.take(stated),
            "number_type": number_type.take(stated),
        }
    )
    for cell in _mismatched(axes, manifest):
        column = "unit" if cell["expected_unit"] != cell["unit"] else "number_type"
        found.add(
            cell["row"],
            2,
            TableProblem(
                "axis_mismatch",
                cell["row"],
                (column,),
                _mismatch(cell, manifest is not None),
            ),
        )
    for place, key, what in ((3, "start", "coordinate"), (4, "duration", "duration")):
        number = _array(table, key)
        checked = _all(admitted, pc.is_valid(number))
        held = _number_held(number, number_type)
        rows = _rows(_all(checked, _not(held)))
        for row, value, row_type in zip(
            rows, _at(number, rows), _at(number_type, rows), strict=True
        ):
            found.add(
                row,
                place,
                TableProblem(
                    "invalid_coordinate",
                    row,
                    (key,),
                    _number_problem(value, row_type, what),
                ),
            )
        if key == "duration":
            # A number holds its numerator or its value, never both.
            negative = _any(
                _held(pc.less(_member(number, "numerator"), _ZERO)),
                _held(pc.less(_member(number, "value"), _ZERO)),
            )
            for row in _rows(_all(checked, held, negative)):
                found.add(
                    row,
                    place,
                    TableProblem(
                        "invalid_duration", row, (key,), "the duration is negative"
                    ),
                )


def _projected_events(
    found: _Found, table: pa.Table, timelines: pa.Array, manifest: _Manifest | None
) -> None:
    """The event a Projection stands for: both members given (places 5 and
    6), on another timeline than the Projection's, one the manifest has (7)."""
    source = _array(table, "projection_of")
    present = pc.is_valid(source)
    members = {key: _member(source, key) for key in ("timeline_id", "event_id")}
    for place, (key, member) in enumerate(members.items(), 5):
        missing = _any(pc.is_null(member), _held(pc.equal(member, _EMPTY)))
        for row in _rows(_all(present, missing)):
            found.add(
                row,
                place,
                TableProblem(
                    "invalid_projection_of",
                    row,
                    ("projection_of", key),
                    f"the projected event has no {key}",
                ),
            )
    source_timeline = members["timeline_id"]
    same = _all(present, _held(pc.equal(source_timeline, timelines)))
    rows = _rows(same)
    for row, value in zip(rows, _at(timelines, rows), strict=True):
        found.add(
            row,
            7,
            TableProblem(
                "invalid_projection_of",
                row,
                ("projection_of", "timeline_id"),
                f"a Projection stands for an event of another timeline than '{value}'",
            ),
        )
    if manifest is not None:
        named = _all(present, _not(same), _held(pc.not_equal(source_timeline, _EMPTY)))
        _unknown_problems(
            found,
            manifest,
            source_timeline,
            7,
            ("projection_of", "timeline_id"),
            named,
        )


def _differs(old: pa.Array, new: pa.Array) -> pa.Array:
    """Where two columns of one type hold different values, compared as the
    succession rule compares them: a coordinate cell by its unit, its number
    type and its exact value, a struct member by member, null equal to null
    alone."""
    nulls = pc.xor(pc.is_null(old), pc.is_null(new))
    kind = old.type
    if pa.types.is_struct(kind):
        both = _all(pc.is_valid(old), pc.is_valid(new))
        if {field.name for field in kind} == set(COORDINATE_KEYS):
            inner = _coordinates_differ(old, new)
        else:
            inner = _any(
                _not(both),
                *(
                    _differs(before, after)
                    for before, after in zip(old.flatten(), new.flatten(), strict=True)
                ),
            )
        return _any(nulls, _all(both, inner))
    if pa.types.is_nested(kind):
        raise TypeError(f"no comparison of values of the type {kind}")
    return _any(nulls, _held(pc.not_equal(old, new)))


def _coordinates_differ(old: pa.Array, new: pa.Array) -> pa.Array:
    """Where two coordinate cells, both stated, differ in unit, number type
    or exact value; a fraction whose members differ is compared exactly."""

    def member(cells: pa.Array, key: str) -> pa.Array:
        """A member of the coordinate cells, null where the cell is."""
        return _member(cells, key)

    unit = _differs(member(old, "unit"), member(new, "unit"))
    number_type = _differs(member(old, "number_type"), member(new, "number_type"))
    raw = {key: _differs(member(old, key), member(new, key)) for key in NUMBER_KEYS}
    kind = member(old, "number_type")
    is_int = _held(pc.equal(kind, _KINDS["int"]))
    is_float = _held(pc.equal(kind, _KINDS["float"]))
    axis = _any(unit, number_type)
    respelled = _all(
        pc.is_valid(old),
        pc.is_valid(new),
        _not(axis),
        _not(is_int),
        _not(is_float),
        _any(raw["numerator"], raw["denominator"]),
    )
    rows = _rows(respelled)
    unequal = [
        row
        for row, before, after in zip(rows, _at(old, rows), _at(new, rows), strict=True)
        if coordinate_value(before) != coordinate_value(after)
    ]
    exact = pc.is_in(
        pa.array(range(len(old)), pa.int64()),
        value_set=pa.array(unequal, pa.int64()),
    )
    return _any(
        axis,
        _all(is_int, raw["numerator"]),
        _all(is_float, raw["value"]),
        exact,
    )


def succession_problems(old: pa.Table, new: pa.Table) -> list[TableProblem]:
    """Every breach of the succession rule by ``new`` written over ``old``.

    Both are checked MatchClaim tables. A MatchClaim is its ID alone; a column
    the type does not declare takes no part. Every MatchClaim of ``old`` is
    in ``new``, and its row has the same value in every column but
    ``provenance``; a coordinate is the same when its unit, number type and
    exact value are, so ``2/4`` and ``1/2`` are one coordinate. The rows of
    ``new`` are reported by their index in ``new``.
    """
    _readable(new, MATCH_CLAIM_SCHEMA.names)
    _readable(old, MATCH_CLAIM_SCHEMA.names)
    columns = [name for name in MATCH_CLAIM_SCHEMA.names if name != "provenance"]
    old_ids = _array(old, "id")
    successors = _first_rows(_array(new, "id"), old_ids)
    found = _Found()
    rows = _rows(pc.is_null(successors))
    for row, value in zip(rows, _at(old_ids, rows), strict=True):
        found.add(
            row,
            0,
            TableProblem(
                "succession_missing",
                None,
                ("id",),
                f"the MatchClaim '{value}' is missing",
            ),
        )
    kept = _indices(pc.is_valid(successors))
    later = successors.take(kept)
    for place, column in enumerate(columns, 1):
        differs = _indices(
            _differs(_array(old, column).take(kept), _array(new, column).take(later))
        )
        for row, successor, value in zip(
            kept.take(differs).to_pylist(),
            later.take(differs).to_pylist(),
            old_ids.take(kept.take(differs)).to_pylist(),
            strict=True,
        ):
            found.add(
                row,
                place,
                TableProblem(
                    "succession_changed",
                    successor,
                    (column,),
                    f"the MatchClaim '{value}' changed its '{column}'",
                ),
            )
    return found.problems()


def _first(problems: list[TableProblem]) -> None:
    if problems:
        raise TableError(problems[0])


def check_match_claims(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> None:
    """Raise ``TableError`` for the first problem of a MatchClaim table."""
    _first(match_claim_problems(table, manifest))


def check_projections(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> None:
    """Raise ``TableError`` for the first problem of a Projections table."""
    _first(projection_problems(table, manifest))


def check_succession(old: pa.Table, new: pa.Table) -> None:
    """Raise ``TableError`` for the first breach of the succession rule."""
    _first(succession_problems(old, new))
