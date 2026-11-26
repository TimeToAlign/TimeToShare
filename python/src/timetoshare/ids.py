"""IDs in a manifest file and in memory.

A manifest file writes every ID with a leading ``#``: an element's own ID
(``"id": "#clt_1"``) as well as every reference to one (a group's members,
the keys of ``graphical.order``, a named timestamp's timeline, an elision's
timeline, an alignment anchor's timestamps, a resource's timelines, an
address's ``id``, a selector's ``within``, a declaration's ``flow``, the ``to``
of a jump's destination,
the ``jump`` and ``to`` of an ``after``, a FlowMap's ``timeline`` and the IDs
among its ``chunks``, a virtual timeline's ``map``, ``timeline`` and
``through``, a measure view's ``measure_map``). The IDs of MatchClaims a
MatchStamp lists name rows of a MatchClaim table, not elements, and are no
ID position. In memory an ID is bare: ``clt_1``. Exactly one ``#`` is
stripped, so the file text ``##x`` is the bare ID ``#x``.

One position holds an ID or something else: the values of a group's entry
in ``graphical.order`` are member IDs, while a timeline's entry holds band
words, which stay bare. The IRIs of ``statements`` and ``provenance``, a
reference to an element (``{"id": "#clt_1"}``) among them, are no ID
position: they are written the same in a file and in memory.

``with_file_ids`` and ``with_bare_ids`` convert a whole manifest between the
two forms. Both are pure: they return a new value, keep unknown keys and
the order of every object's keys (an order key renamed in place keeps its
position) and leave every number as it is. Both are driven by one table of
the positions of IDs, ``ID_POSITIONS``, by schema definition and member, and
one table of where each definition occurs, ``CONTAINERS``.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any, Literal

HASH = "#"
"""The character that marks an ID in a manifest file."""

Shape = Literal["id", "ids", "order"]
"""How a member holds IDs.

``id`` the member is one ID; ``ids`` a list of IDs, an item that is no
string (a FlowMap's gap) kept as it is; ``order`` an object
keyed by IDs whose value, where the key names a group, is a list of member
IDs (a timeline's value holds band words).
"""

ID_POSITIONS: tuple[tuple[str, str, Shape], ...] = (
    ("Manifest", "id", "id"),
    ("Timeline", "id", "id"),
    ("Group", "id", "id"),
    ("Group", "members", "ids"),
    ("Graphical", "order", "order"),
    ("Timestamp", "id", "id"),
    ("Timestamp", "timeline", "id"),
    ("Elision", "id", "id"),
    ("Elision", "timeline", "id"),
    ("MatchStamp", "id", "id"),
    ("AlignmentAnchor", "id", "id"),
    ("AlignmentAnchor", "timestamps", "ids"),
    ("Resource", "id", "id"),
    ("Resource", "timelines", "ids"),
    ("Address", "id", "id"),
    ("MeasureMap", "id", "id"),
    ("Region", "id", "id"),
    ("FlowControlElement", "id", "id"),
    ("JumpDestination", "to", "id"),
    ("DestinationReference", "jump", "id"),
    ("DestinationReference", "to", "id"),
    ("FlowMap", "id", "id"),
    ("FlowMap", "timeline", "id"),
    ("FlowMap", "chunks", "ids"),
    ("VirtualTimeline", "id", "id"),
    ("VirtualTimeline", "map", "id"),
    ("VirtualTimeline", "timeline", "id"),
    ("VirtualTimeline", "through", "id"),
    ("Selector", "within", "id"),
    ("Declaration", "flow", "id"),
    ("MapBase", "id", "id"),
    ("MeasureView", "measure_map", "id"),
)
"""Every member of a schema definition that holds IDs, and how it holds them."""

Holding = Literal["one", "list", "values"]
"""How a member holds a definition: one object, a list, or an object's values."""

CONTAINERS: tuple[tuple[str, str, Holding, str], ...] = (
    ("Manifest", "timelines", "list", "Timeline"),
    ("Manifest", "groups", "list", "Group"),
    ("Manifest", "measure_maps", "list", "MeasureMap"),
    ("Manifest", "resources", "list", "Resource"),
    ("Manifest", "graphical", "one", "Graphical"),
    ("Manifest", "flow_maps", "list", "FlowMap"),
    ("Manifest", "virtual_timelines", "list", "VirtualTimeline"),
    ("Timeline", "children", "list", "Timeline"),
    ("Timeline", "conversion_maps", "list", "ConversionMap"),
    ("Timeline", "regions", "list", "Region"),
    ("Timeline", "flow_control", "list", "FlowControlElement"),
    ("FlowControlElement", "targets", "list", "JumpDestination"),
    ("FlowControlElement", "ends", "one", "BreakCondition"),
    ("JumpDestination", "after", "one", "DestinationReference"),
    ("BreakCondition", "after", "one", "DestinationReference"),
    ("Graphical", "styles", "values", "Declaration"),
    ("Graphical", "rules", "list", "Rule"),
    ("Graphical", "timestamps", "list", "Timestamp"),
    ("Graphical", "elisions", "list", "Elision"),
    ("Graphical", "matchstamps", "list", "MatchStamp"),
    ("MatchStamp", "alignment_anchors", "list", "AlignmentAnchor"),
    ("Rule", "select", "one", "Selector"),
    ("Rule", "set", "one", "Declaration"),
    ("Selector", "addresses", "list", "Address"),
    ("ChainMap", "maps", "list", "ConversionMap"),
    ("PiecewiseMap", "maps", "list", "ConversionMap"),
    ("CombinationMap", "maps", "values", "ConversionMap"),
)
"""Every member through which a definition holds another that holds IDs."""

MEASURE_VIEWS: tuple[str, ...] = (
    "FloatingMeasureMap",
    "MeasureBeatMap",
    "MeasureNumberMap",
    "MeasureRecordMap",
)
"""The conversion-map types built on ``MeasureView``; every other one on ``MapBase``."""

_POSITIONS: dict[str, dict[str, Shape]] = {}
for _definition, _member, _shape in ID_POSITIONS:
    _POSITIONS.setdefault(_definition, {})[_member] = _shape
_HELD: dict[str, dict[str, tuple[Holding, str]]] = {}
for _definition, _member, _holding, _child in CONTAINERS:
    _HELD.setdefault(_definition, {})[_member] = (_holding, _child)

_Path = tuple[str | int, ...]


class FileIdError(ValueError):
    """Raised for a text that is not an ID in the file form.

    Attributes:
        path: Where the text stands in the manifest; empty for a lone text.
    """

    def __init__(self, message: str, path: _Path = ()) -> None:
        super().__init__(message)
        self.path = path


def to_file_id(id: str) -> str:
    """Return the file form of a bare ID: ``#`` followed by the ID."""
    if not isinstance(id, str):
        raise TypeError(f"an ID is a string, not {type(id).__name__}")
    return HASH + id


def from_file_id(text: str) -> str:
    """Return the bare ID that a file's ``#id`` text writes.

    Exactly one leading ``#`` is stripped: ``#x`` is ``x`` and ``##x`` is
    ``#x``.

    Raises:
        FileIdError: A ``ValueError``, if the text does not start with ``#``
            or nothing follows it.
    """
    return _bare(text, ())


def _bare(text: str, path: _Path) -> str:
    if not isinstance(text, str):
        raise TypeError(f"an ID is a string, not {type(text).__name__}")
    if not text.startswith(HASH):
        raise FileIdError(
            f"'{text}' is not written as an ID: it does not start with '#'", path
        )
    if len(text) == 1:
        raise FileIdError("'#' is not written as an ID: nothing follows the '#'", path)
    return text[1:]


def _leniently_bare(text: str) -> str:
    """The bare ID of a text in the file form; any other text as it is."""
    return text[1:] if text.startswith(HASH) and len(text) > 1 else text


_ATOMS = frozenset({str, int, float, bool, type(None)})


def _copied(value: Any) -> Any:
    """A copy of JSON data, quicker than ``copy.deepcopy``.

    Strings, numbers, booleans and ``None`` are kept (``deepcopy`` keeps them
    too); lists and dictionaries of exactly those types are rebuilt member by
    member, so one shared by two members is no longer shared in the copy and
    a cycle raises ``RecursionError``; any other value goes through
    ``copy.deepcopy``.
    """
    kind = type(value)
    if kind in _ATOMS:
        return value
    if kind is list:
        return [_copied(item) for item in value]
    if kind is dict:
        return {key: _copied(item) for key, item in value.items()}
    return copy.deepcopy(value)


def definitions_of(definition: str, value: Mapping[str, Any]) -> tuple[str, ...]:
    """The definitions whose members ``value``, held as ``definition``, carries.

    A conversion map is its type's definition and that definition's bases;
    every other value is its definition alone.
    """
    if definition != "ConversionMap":
        return (definition,)
    kind = value.get("type")
    if kind in MEASURE_VIEWS:
        return (kind, "MeasureView", "MapBase")
    return (kind if isinstance(kind, str) else "", "MapBase")


class _Converter:
    """One conversion of a whole manifest, to the file form or to the bare form."""

    def __init__(
        self, manifest: Mapping[str, Any], to_file: bool, strict: bool = True
    ) -> None:
        self.to_file = to_file
        self.strict = strict
        self.groups = self._ids(manifest, "groups")

    def _ids(self, manifest: Mapping[str, Any], member: str) -> frozenset[str]:
        """The bare IDs of a top-level list, read leniently: a check comes later."""
        entries = manifest.get(member)
        if not isinstance(entries, list):
            return frozenset()
        found = set()
        for entry in entries:
            if isinstance(entry, Mapping) and isinstance(entry.get("id"), str):
                text = entry["id"]
                if self.to_file:
                    found.add(text)
                elif text.startswith(HASH) and len(text) > 1:
                    found.add(text[1:])
        return frozenset(found)

    def id(self, text: Any, path: _Path) -> Any:
        """One ID converted; a value that is no string is copied as it is.

        Raises:
            FileIdError: In strict conversion to the bare form, if the text is
                not written as an ID.
        """
        if not isinstance(text, str):
            return _copied(text)
        if self.to_file:
            return to_file_id(text)
        return _bare(text, path) if self.strict else _leniently_bare(text)

    def ids(self, value: Any, path: _Path) -> Any:
        """A list of IDs converted item by item; a value that is no list is copied."""
        if not isinstance(value, list):
            return _copied(value)
        return [self.id(item, (*path, index)) for index, item in enumerate(value)]

    def order(self, value: Any, path: _Path) -> Any:
        """An object keyed by IDs converted, and the member IDs a group's key holds."""
        if not isinstance(value, Mapping):
            return _copied(value)
        result: dict[str, Any] = {}
        for key, entry in value.items():
            renamed = self.id(key, (*path, key))
            bare = key if self.to_file else renamed
            if bare in self.groups:
                result[renamed] = self.ids(entry, (*path, key))
            else:
                result[renamed] = _copied(entry)
        return result

    def held(self, value: Any, definition: str, path: _Path) -> Any:
        """A value held as ``definition`` converted, member by member."""
        if not isinstance(value, Mapping):
            return _copied(value)
        definitions = definitions_of(definition, value)
        shapes: dict[str, Shape] = {}
        holds: dict[str, tuple[Holding, str]] = {}
        for name in definitions:
            shapes.update(_POSITIONS.get(name, {}))
            holds.update(_HELD.get(name, {}))
        result: dict[str, Any] = {}
        for key, member in value.items():
            at = (*path, key)
            if key in shapes:
                result[key] = getattr(self, shapes[key])(member, at)
            elif key in holds:
                result[key] = self.holding(member, *holds[key], at)
            else:
                result[key] = _copied(member)
        return result

    def holding(self, value: Any, holding: Holding, child: str, path: _Path) -> Any:
        """A member converted that holds ``child`` as one object, a list or values."""
        if holding == "one":
            return self.held(value, child, path)
        if holding == "list" and isinstance(value, list):
            return [
                self.held(item, child, (*path, index))
                for index, item in enumerate(value)
            ]
        if holding == "values" and isinstance(value, Mapping):
            return {
                key: self.held(item, child, (*path, key)) for key, item in value.items()
            }
        return _copied(value)


def with_file_ids(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the manifest with every ID in the file form, ``#`` + the bare ID.

    A value of ``graphical.order`` gains the ``#`` where its key names a
    group.
    """
    return _Converter(manifest, True).held(manifest, "Manifest", ())


def with_bare_ids(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the manifest with every ID bare, read from its file form ``#id``.

    A timeline's entry in ``graphical.order`` holds band words, which stay
    as they are.

    Raises:
        FileIdError: A ``ValueError``, with the ``path`` of the first text
            that is not an ID in the file form.
    """
    return _Converter(manifest, False).held(manifest, "Manifest", ())


def leniently_bare_ids(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """``with_bare_ids`` that keeps every text not in the file form as it is.

    For a check of one part of a manifest, which must not refuse an ID
    outside that part.
    """
    return _Converter(manifest, False, strict=False).held(manifest, "Manifest", ())
