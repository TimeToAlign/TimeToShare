"""Identity, target, group-member and orchestration rules."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from itertools import chain
from typing import Any

from .containment import timeline_containment_problems
from .diagnostics import (
    SchemaValidationError,
    ValidationCode,
    _entries,
    _Path,
    json_pointer,
)
from .maps import MEASURE_VIEWS, timeline_map_problems, timeline_maps
from .order import order_problems
from .segments import timeline_segment_problems


def _element_ids(
    timeline: Mapping[str, Any], path: _Path
) -> Iterator[tuple[str, _Path]]:
    yield timeline["id"], (*path, "id")
    for member in ("conversion_maps", "regions"):
        for index, entry in enumerate(_entries(timeline, member)):
            yield entry["id"], (*path, member, index, "id")
    for index, entry in enumerate(_entries(timeline, "flow_control")):
        yield entry["id"], (*path, "flow_control", index, "id")
    for index, child in enumerate(_entries(timeline, "children")):
        yield from _element_ids(child, (*path, "children", index))


def _nested_map_ids(
    timeline: Mapping[str, Any], path: _Path
) -> Iterator[tuple[Any, _Path]]:
    for conversion_map, at in timeline_maps(timeline, path):
        if at[-2] == "maps":
            yield conversion_map["id"], (*at, "id")
    for index, child in enumerate(_entries(timeline, "children")):
        yield from _nested_map_ids(child, (*path, "children", index))


def _dangling_targets(
    timeline: Mapping[str, Any], path: _Path, measure_maps: set[str]
) -> Iterator[SchemaValidationError]:
    flow = _entries(timeline, "flow_control")
    targets = {entry["id"] for entry in flow if entry["type"] == "jump_to"}
    for index, entry in enumerate(flow):
        if "target" in entry and entry["target"] not in targets:
            yield SchemaValidationError(
                "dangling_target",
                (*path, "flow_control", index, "target"),
                f"'{entry['target']}' names no jump_to of this timeline",
            )
    for conversion_map, at in timeline_maps(timeline, path):
        reference = conversion_map.get("measure_map")
        if conversion_map["type"] in MEASURE_VIEWS and reference not in measure_maps:
            yield SchemaValidationError(
                "dangling_target",
                (*at, "measure_map"),
                f"'{reference}' names no MeasureMap of this manifest",
            )
    for index, child in enumerate(_entries(timeline, "children")):
        yield from _dangling_targets(child, (*path, "children", index), measure_maps)


def _duplicate(
    identifier: str,
    path: _Path,
    first: _Path,
    code: ValidationCode = "duplicate_id",
) -> SchemaValidationError:
    return SchemaValidationError(
        code,
        path,
        f"'{identifier}' is not unique in the manifest, first at {json_pointer(first)}",
    )


def _tree_ids(root: Mapping[str, Any], path: _Path) -> Iterator[tuple[str, _Path]]:
    """Yield every ID of a root's tree, the maps other maps hold after the rest."""
    yield from chain(_element_ids(root, path), _nested_map_ids(root, path))


def _root_problems(
    root: Mapping[str, Any], path: _Path, measure_maps: set[str]
) -> Iterator[SchemaValidationError]:
    first: dict[str, _Path] = {}
    for identifier, at in _tree_ids(root, path):
        if identifier in first:
            yield _duplicate(identifier, at, first[identifier])
        else:
            first[identifier] = at
    yield from _dangling_targets(root, path, measure_maps)
    yield from timeline_map_problems(root, path)
    yield from timeline_containment_problems(root, path)
    yield from timeline_segment_problems(root, path)


def _parents(roots: list[Mapping[str, Any]]) -> dict[str, str | None]:
    found: dict[str, str | None] = {}

    def visit(timeline: Mapping[str, Any], parent: str | None) -> None:
        found.setdefault(timeline["id"], parent)
        for child in _entries(timeline, "children"):
            visit(child, timeline["id"])

    for root in roots:
        visit(root, None)
    return found


def _ancestors(identifier: str, parents: Mapping[str, str | None]) -> list[str]:
    found: list[str] = []
    parent = parents.get(identifier)
    while parent is not None:
        found.append(parent)
        parent = parents.get(parent)
    return found


def _member_problems(
    group: Mapping[str, Any],
    path: _Path,
    parents: Mapping[str, str | None],
) -> Iterator[SchemaValidationError]:
    selected: dict[str, int] = {}
    earliest_descendant: dict[str, tuple[int, str]] = {}
    for index, member in enumerate(group["members"]):
        at = (*path, index)
        if member not in parents:
            yield SchemaValidationError(
                "group_member", at, f"'{member}' names no timeline of this manifest"
            )
            continue
        ancestors = _ancestors(member, parents)
        relation: tuple[int, str, str] | None = None
        for ancestor in ancestors:
            if ancestor in selected and (
                relation is None or selected[ancestor] < relation[0]
            ):
                relation = (selected[ancestor], ancestor, "lies inside")
        descendant = earliest_descendant.get(member)
        if descendant is not None and (relation is None or descendant[0] < relation[0]):
            relation = (*descendant, "contains")
        if relation is not None:
            _, other, word = relation
            yield SchemaValidationError(
                "group_member",
                at,
                f"member '{member}' {word} member '{other}' of the same group",
            )

        selected.setdefault(member, index)
        for ancestor in ancestors:
            earliest_descendant.setdefault(ancestor, (index, member))


def identity_problems(
    value: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield semantic violations in the established identity order."""
    roots = _entries(value, "timelines")
    groups = _entries(value, "groups")
    measure_maps = _entries(value, "measure_maps")
    measure_map_ids = {measure_map["id"] for measure_map in measure_maps}
    for index, root in enumerate(roots):
        yield from _root_problems(root, ("timelines", index), measure_map_ids)

    first: dict[str, _Path] = {}
    for index, root in enumerate(roots):
        seen: dict[str, _Path] = {}
        for identifier, path in _tree_ids(root, ("timelines", index)):
            if identifier in seen:
                continue
            seen[identifier] = path
            if identifier in first:
                yield _duplicate(identifier, path, first[identifier])
        for identifier, path in seen.items():
            first.setdefault(identifier, path)
    for key, entries in (("groups", groups), ("measure_maps", measure_maps)):
        for index, entry in enumerate(entries):
            path = (key, index, "id")
            if entry["id"] in first:
                yield _duplicate(entry["id"], path, first[entry["id"]])
            else:
                first[entry["id"]] = path
    manifest_id = value.get("id")
    if manifest_id in first:
        yield _duplicate(manifest_id, ("id",), first[manifest_id], "manifest_id")

    parents = _parents(roots)
    for index, group in enumerate(groups):
        yield from _member_problems(group, ("groups", index, "members"), parents)
    first_group: dict[str, int] = {}
    for index, group in enumerate(groups):
        first_group.setdefault(group["id"], index)
    yield from order_problems(value, parents, first_group)
