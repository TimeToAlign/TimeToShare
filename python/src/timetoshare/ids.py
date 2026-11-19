"""IDs in a manifest file and in memory.

A manifest file writes every ID with a leading ``#``: an element's own ID
(``"id": "#clt_1"``) as well as every reference to one (a group's members,
the keys of ``graphical.order``, a named timestamp's timeline, an address's
``id``, a selector's ``within``, a flow-control element's ``target``, a
measure view's ``measure_map``, a part slot's ``represented_by``). In
memory an ID is bare: ``clt_1``. Exactly one ``#`` is stripped, so the file
text ``##x`` is the bare ID ``#x``.

Two positions hold an ID or something else, and the ``#`` tells them apart:
the values of a group's entry in ``graphical.order`` are member IDs, while a
timeline's entry holds band words, which stay bare; and an identifier's
``scheme`` is either the ID of a scheme of the manifest (``#opus``) or an
absolute URI, which is written as it is.

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

Shape = Literal["id", "ids", "order", "scheme"]
"""How a member holds IDs.

``id`` the member is one ID; ``ids`` a list of IDs; ``order`` an object
keyed by IDs whose value, where the key names a group, is a list of member
IDs (a timeline's value holds band words); ``scheme`` an ID or an absolute
URI, the ``#`` telling them apart.
"""

ID_POSITIONS: tuple[tuple[str, str, Shape], ...] = (
    ("Manifest", "id", "id"),
    ("Timeline", "id", "id"),
    ("Group", "id", "id"),
    ("Group", "members", "ids"),
    ("Graphical", "order", "order"),
    ("Timestamp", "id", "id"),
    ("Timestamp", "timeline", "id"),
    ("Address", "id", "id"),
    ("MeasureMap", "id", "id"),
    ("Region", "id", "id"),
    ("FlowControlElement", "id", "id"),
    ("FlowControlElement", "target", "id"),
    ("Selector", "within", "id"),
    ("MapBase", "id", "id"),
    ("MeasureView", "measure_map", "id"),
    ("PartSlot", "represented_by", "ids"),
    ("Scheme", "id", "id"),
    ("Identifier", "scheme", "scheme"),
)
"""Every member of a schema definition that holds IDs, and how it holds them."""

Holding = Literal["one", "list", "values"]
"""How a member holds a definition: one object, a list, or an object's values."""

CONTAINERS: tuple[tuple[str, str, Holding, str], ...] = (
    ("Manifest", "timelines", "list", "Timeline"),
    ("Manifest", "groups", "list", "Group"),
    ("Manifest", "measure_maps", "list", "MeasureMap"),
    ("Manifest", "schemes", "list", "Scheme"),
    ("Manifest", "links", "list", "Link"),
    ("Manifest", "graphical", "one", "Graphical"),
    ("Timeline", "children", "list", "Timeline"),
    ("Timeline", "conversion_maps", "list", "ConversionMap"),
    ("Timeline", "regions", "list", "Region"),
    ("Timeline", "flow_control", "list", "FlowControlElement"),
    ("Timeline", "links", "list", "Link"),
    ("Region", "links", "list", "Link"),
    ("Graphical", "rules", "list", "Rule"),
    ("Graphical", "timestamps", "list", "Timestamp"),
    ("Rule", "select", "one", "Selector"),
    ("Selector", "addresses", "list", "Address"),
    ("ChainMap", "maps", "list", "ConversionMap"),
    ("PiecewiseMap", "maps", "list", "ConversionMap"),
    ("CombinationMap", "maps", "values", "ConversionMap"),
    ("Link", "identifiers", "list", "Identifier"),
    ("Link", "parts", "list", "PartSlot"),
    ("Link", "part_of", "list", "PartOf"),
    ("PartSlot", "identifiers", "list", "Identifier"),
    ("PartOf", "identifiers", "list", "Identifier"),
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
        self.schemes = self._ids(manifest, "schemes")

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
        if not isinstance(text, str):
            return copy.deepcopy(text)
        if self.to_file:
            return to_file_id(text)
        return _bare(text, path) if self.strict else _leniently_bare(text)

    def ids(self, value: Any, path: _Path) -> Any:
        if not isinstance(value, list):
            return copy.deepcopy(value)
        return [self.id(item, (*path, index)) for index, item in enumerate(value)]

    def scheme(self, text: Any, path: _Path) -> Any:
        if not isinstance(text, str):
            return copy.deepcopy(text)
        if self.to_file:
            return to_file_id(text) if text in self.schemes else text
        if text.startswith(HASH):
            return _bare(text, path) if self.strict else _leniently_bare(text)
        if text in self.schemes and self.strict:
            raise FileIdError(
                f"'{text}' names a scheme of this manifest, so it is written '#{text}'",
                path,
            )
        return text

    def order(self, value: Any, path: _Path) -> Any:
        if not isinstance(value, Mapping):
            return copy.deepcopy(value)
        result: dict[str, Any] = {}
        for key, entry in value.items():
            renamed = self.id(key, (*path, key))
            bare = key if self.to_file else renamed
            if bare in self.groups:
                result[renamed] = self.ids(entry, (*path, key))
            else:
                result[renamed] = copy.deepcopy(entry)
        return result

    def held(self, value: Any, definition: str, path: _Path) -> Any:
        if not isinstance(value, Mapping):
            return copy.deepcopy(value)
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
                result[key] = copy.deepcopy(member)
        return result

    def holding(self, value: Any, holding: Holding, child: str, path: _Path) -> Any:
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
        return copy.deepcopy(value)


def with_file_ids(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the manifest with every ID in the file form, ``#`` + the bare ID.

    An identifier's ``scheme`` gains the ``#`` where it names a scheme of
    the manifest, a value of ``graphical.order`` where its key names a group.
    """
    return _Converter(manifest, True).held(manifest, "Manifest", ())


def with_bare_ids(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the manifest with every ID bare, read from its file form ``#id``.

    An identifier's ``scheme`` without ``#`` is an absolute URI and stays as
    it is; a timeline's entry in ``graphical.order`` holds band words, which
    stay as they are.

    Raises:
        FileIdError: A ``ValueError``, with the ``path`` of the first text
            that is not an ID in the file form, or of an identifier's
            ``scheme`` written without ``#`` that names a scheme of the
            manifest.
    """
    return _Converter(manifest, False).held(manifest, "Manifest", ())


def leniently_bare_ids(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """``with_bare_ids`` that keeps every text not in the file form as it is.

    For a check of one part of a manifest, which must not refuse an ID
    outside that part.
    """
    return _Converter(manifest, False, strict=False).held(manifest, "Manifest", ())
