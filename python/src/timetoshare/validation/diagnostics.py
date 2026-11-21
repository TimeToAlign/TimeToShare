"""The validator's diagnostics and the small readers every rule module shares.

The error a rule raises with its code and path, the JSON pointer of a path,
the readers of a schema-checked object's members, and the walks of the IDs
of a root's tree and of the whole manifest, which read any value. A leaf
module: it imports no rule module and no validator, so the rule modules and
``timetoshare.validate`` both import it without a cycle.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator, Mapping
from typing import Any, Literal, TypeAlias, TypedDict, TypeVar

from ..manifest import UNIT_NUMBER_TYPES as UNIT_NUMBER_TYPES

_Path = tuple[str | int, ...]
ValidationCode: TypeAlias = Literal[
    "not_a_manifest",
    "schema",
    "representation",
    "duplicate_id",
    "dangling_target",
    "conversion_map",
    "child_unit",
    "child_offset",
    "child_end",
    "segment_line",
    "group_member",
    "manifest_id",
    "order_key",
    "display_order",
    "band_order",
    "timestamp_timeline",
    "timestamp_coordinate",
    "groupstamp",
    "match_timestamp",
    "alignment_anchor",
    "matchstamp",
    "resource_timeline",
    "resource_type",
    "calendar_date",
    "finite_number",
    "context",
    "reserved_key",
    "iri",
    "element_value",
    "provenance_duplicate",
    "belief_actor",
]

WarningCode: TypeAlias = Literal["context_absent", "bundle_blank"]
"""The codes of the warnings a valid manifest may draw."""


class ManifestWarning(TypedDict):
    """A warning about a valid manifest: its code, its path and its message."""

    code: WarningCode
    path: list[str | int]
    message: str


_Member = TypeVar("_Member", bound=Hashable)


def connected_sets(pairs: Iterable[tuple[_Member, _Member]]) -> dict[_Member, _Member]:
    """Map every member of the pairs to the representative of its connected set.

    Two members share a representative exactly when a chain of pairs joins
    them (union-find with path halving). The MatchStamp rule counts the sets
    a named MatchStamp's anchors form; the table types group the unique
    anchors of a MatchClaim table into potential MatchStamps by it.
    """
    parent: dict[_Member, _Member] = {}

    def find(member: _Member) -> _Member:
        parent.setdefault(member, member)
        while parent[member] != member:
            parent[member] = parent[parent[member]]
            member = parent[member]
        return member

    for left, right in pairs:
        parent[find(left)] = find(right)
    return {member: find(member) for member in list(parent)}


def json_pointer(path: Iterable[str | int]) -> str:
    """Render a path as a JSON pointer in URI fragment form (``#`` for the root)."""
    segments = [str(segment).replace("~", "~0").replace("/", "~1") for segment in path]
    return "#" + "".join(f"/{segment}" for segment in segments)


class SchemaValidationError(ValueError):
    """Raised when a value violates the schema or a semantic rule."""

    def __init__(self, code: ValidationCode, path: _Path, message: str) -> None:
        self.code = code
        self.path = path
        self.message = message
        super().__init__(f"{json_pointer(path)}: {message}")


def duplicate_problem(
    identifier: str,
    path: _Path,
    first: _Path,
    code: ValidationCode = "duplicate_id",
) -> SchemaValidationError:
    """The problem of an ID at ``path`` that the manifest holds first at ``first``."""
    return SchemaValidationError(
        code,
        path,
        f"'{identifier}' is not unique in the manifest, first at {json_pointer(first)}",
    )


def _entries(owner: Any, key: str) -> list[Any]:
    value = owner.get(key) if isinstance(owner, Mapping) else None
    return value if isinstance(value, list) else []


def string_id(element: Any) -> str | None:
    """Return an element's ``id`` where it is an object holding a string ``id``."""
    identifier = element.get("id") if isinstance(element, Mapping) else None
    return identifier if isinstance(identifier, str) else None


def _element_ids(timeline: Any, path: _Path) -> Iterator[tuple[str, _Path]]:
    identifier = string_id(timeline)
    if identifier is not None:
        yield identifier, (*path, "id")
    for member in ("conversion_maps", "regions", "flow_control"):
        for index, entry in enumerate(_entries(timeline, member)):
            identifier = string_id(entry)
            if identifier is not None:
                yield identifier, (*path, member, index, "id")
    for index, child in enumerate(_entries(timeline, "children")):
        yield from _element_ids(child, (*path, "children", index))


def _held_ids(conversion_map: Any, path: _Path) -> Iterator[tuple[str, _Path]]:
    maps = conversion_map.get("maps") if isinstance(conversion_map, Mapping) else None
    if isinstance(maps, list):
        held = list(enumerate(maps))
    elif isinstance(maps, Mapping):
        held = [(name, maps[name]) for name in sorted(maps)]
    else:
        return
    for key, entry in held:
        at = (*path, "maps", key)
        identifier = string_id(entry)
        if identifier is not None:
            yield identifier, (*at, "id")
        yield from _held_ids(entry, at)


def _nested_map_ids(timeline: Any, path: _Path) -> Iterator[tuple[str, _Path]]:
    for index, entry in enumerate(_entries(timeline, "conversion_maps")):
        yield from _held_ids(entry, (*path, "conversion_maps", index))
    for index, child in enumerate(_entries(timeline, "children")):
        yield from _nested_map_ids(child, (*path, "children", index))


def tree_ids(root: Any, path: _Path) -> Iterator[tuple[str, _Path]]:
    """Yield every ID of a root's tree with its path, in the order of the rules.

    The timelines depth first, each with its conversion maps', regions' and
    flow-control elements' IDs before its children's; then the IDs of the
    maps other maps hold, timeline by timeline in the same order, each held
    map before those it holds, a ``CombinationMap``'s outputs by name in
    code-point order. An element that is no object or holds no string ``id``
    is passed over, so the walk reads any value.
    """
    yield from _element_ids(root, path)
    yield from _nested_map_ids(root, path)


def listed_ids(manifest: Any) -> Iterator[tuple[str, _Path]]:
    """Yield the IDs of the elements a manifest lists outside its timelines.

    The groups, the MeasureMaps, the named timestamps, the named
    MatchStamps, each followed by its alignment anchors, and the resources,
    in that order, each with its path. An entry that is no object or holds
    no string ``id`` is passed over, so the walk reads any value.
    """
    for key, entries in (
        (("groups",), _entries(manifest, "groups")),
        (("measure_maps",), _entries(manifest, "measure_maps")),
        (("graphical", "timestamps"), timestamps_of(manifest)),
    ):
        for index, entry in enumerate(entries):
            identifier = string_id(entry)
            if identifier is not None:
                yield identifier, (*key, index, "id")
    for index, matchstamp in enumerate(matchstamps_of(manifest)):
        at = ("graphical", "matchstamps", index)
        identifier = string_id(matchstamp)
        if identifier is not None:
            yield identifier, (*at, "id")
        for number, anchor in enumerate(_entries(matchstamp, "alignment_anchors")):
            identifier = string_id(anchor)
            if identifier is not None:
                yield identifier, (*at, "alignment_anchors", number, "id")
    for index, resource in enumerate(_entries(manifest, "resources")):
        identifier = string_id(resource)
        if identifier is not None:
            yield identifier, ("resources", index, "id")


def manifest_ids(manifest: Any) -> Iterator[tuple[str, _Path]]:
    """Yield every ID of a manifest with its path, in the order of the rules.

    Each root's tree (``tree_ids``), then the listed elements
    (``listed_ids``), then the manifest's own ``id``. The walk reads any
    value.
    """
    for index, root in enumerate(_entries(manifest, "timelines")):
        yield from tree_ids(root, ("timelines", index))
    yield from listed_ids(manifest)
    identifier = string_id(manifest)
    if identifier is not None:
        yield identifier, ("id",)


def timelines_by_id(manifest: Any) -> dict[str, Mapping[str, Any]]:
    """Return every timeline of a manifest, at any depth, by ID.

    Of a repeated ID the first timeline in document order is kept.
    """
    found: dict[str, Mapping[str, Any]] = {}

    def visit(timeline: Mapping[str, Any]) -> None:
        found.setdefault(timeline["id"], timeline)
        for child in _entries(timeline, "children"):
            visit(child)

    for root in _entries(manifest, "timelines"):
        visit(root)
    return found


def timestamps_of(manifest: Any) -> list[Any]:
    """Return the named timestamps of a manifest's ``graphical`` object, or none."""
    graphical = manifest.get("graphical") if isinstance(manifest, Mapping) else None
    return _entries(graphical, "timestamps")


def matchstamps_of(manifest: Any) -> list[Any]:
    """Return the named MatchStamps of a manifest's ``graphical`` object, or none."""
    graphical = manifest.get("graphical") if isinstance(manifest, Mapping) else None
    return _entries(graphical, "matchstamps")


def number_type_of(timeline: Mapping[str, Any]) -> str:
    """Return the number type of a timeline's axis: its own, or its unit's default."""
    return timeline.get("number_type") or UNIT_NUMBER_TYPES[timeline["unit"]]
