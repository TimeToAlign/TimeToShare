"""Identity, target, group-member and orchestration rules."""

from __future__ import annotations

from collections.abc import Collection, Iterator, Mapping
from fractions import Fraction
from typing import Any

from ..manifest import exact
from .containment import timeline_containment_problems
from .diagnostics import (
    InstancePath,
    SchemaValidationError,
    duplicate_problem,
    entries_of,
    listed_ids,
    tree_ids,
)
from .flow import (
    JumpPositions,
    flow_map_problems,
    flow_rule_problems,
    timeline_flow_problems,
)
from .maps import MEASURE_VIEWS, timeline_map_problems, timeline_maps
from .order import order_problems
from .segments import timeline_segment_problems
from .timestamps import (
    elision_problems,
    matchstamp_problems,
    resource_problems,
    timestamp_problems,
)


def _dangling_targets(
    timeline: Mapping[str, Any],
    path: InstancePath,
    measure_maps: set[str],
    start: Fraction,
    jumps_at: JumpPositions,
) -> Iterator[SchemaValidationError]:
    yield from timeline_flow_problems(timeline, path, start, jumps_at)
    for conversion_map, at in timeline_maps(timeline, path):
        reference = conversion_map.get("measure_map")
        if conversion_map["type"] in MEASURE_VIEWS and reference not in measure_maps:
            yield SchemaValidationError(
                "dangling_target",
                (*at, "measure_map"),
                f"'{reference}' names no MeasureMap of this manifest",
            )
    for index, child in enumerate(entries_of(timeline, "children")):
        yield from _dangling_targets(
            child,
            (*path, "children", index),
            measure_maps,
            start + exact(child["offset"]),
            jumps_at,
        )


def _root_problems(
    root: Mapping[str, Any], path: InstancePath, measure_maps: set[str]
) -> Iterator[SchemaValidationError]:
    first: dict[str, InstancePath] = {}
    for identifier, at in tree_ids(root, path):
        if identifier in first:
            yield duplicate_problem(identifier, at, first[identifier])
        else:
            first[identifier] = at
    yield from _dangling_targets(root, path, measure_maps, Fraction(0), {})
    yield from timeline_map_problems(root, path)
    yield from timeline_containment_problems(root, path)
    yield from timeline_segment_problems(root, path)


def _parents(roots: list[Mapping[str, Any]]) -> dict[str, str | None]:
    found: dict[str, str | None] = {}

    def visit(timeline: Mapping[str, Any], parent: str | None) -> None:
        """Record a timeline's parent unless its ID is taken, then its children's."""
        found.setdefault(timeline["id"], parent)
        for child in entries_of(timeline, "children"):
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
    path: InstancePath,
    parents: Mapping[str, str | None],
    virtual: Collection[str],
) -> Iterator[SchemaValidationError]:
    """Yield a group's members that name nothing, then those inside or around
    an earlier member. A virtual timeline lies inside no timeline and
    contains none."""
    selected: dict[str, int] = {}
    earliest_descendant: dict[str, tuple[int, str]] = {}
    for index, member in enumerate(group["members"]):
        at = (*path, index)
        if member not in parents:
            if member in virtual:
                continue
            yield SchemaValidationError(
                "group_member",
                at,
                f"'{member}' names no timeline or virtual timeline of this manifest",
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
    """Yield semantic violations in the established identity order.

    Root by root: duplicates, flow control and dangling targets (timeline by
    timeline, each before its children), conversion maps, containment and
    segment lines; then the IDs unique across the manifest (the roots'
    trees, the group IDs, the MeasureMap IDs, the named timestamps' IDs, the
    elisions' IDs, the named MatchStamps' IDs each followed by its alignment
    anchors' IDs, the resources', the FlowMaps' and the virtual timelines'
    IDs, and last the manifest ID); then group members, graphical orders,
    named timestamps, elisions, named MatchStamps, resources, FlowMaps,
    virtual timelines and the property ``flow``.
    """
    roots = entries_of(value, "timelines")
    groups = entries_of(value, "groups")
    measure_maps = entries_of(value, "measure_maps")
    measure_map_ids = {measure_map["id"] for measure_map in measure_maps}
    for index, root in enumerate(roots):
        yield from _root_problems(root, ("timelines", index), measure_map_ids)

    first: dict[str, InstancePath] = {}
    for index, root in enumerate(roots):
        seen: dict[str, InstancePath] = {}
        for identifier, path in tree_ids(root, ("timelines", index)):
            if identifier in seen:
                continue
            seen[identifier] = path
            if identifier in first:
                yield duplicate_problem(identifier, path, first[identifier])
        for identifier, path in seen.items():
            first.setdefault(identifier, path)
    for identifier, path in listed_ids(value):
        if identifier in first:
            yield duplicate_problem(identifier, path, first[identifier])
        else:
            first[identifier] = path
    manifest_id = value.get("id")
    if manifest_id in first:
        yield duplicate_problem(manifest_id, ("id",), first[manifest_id], "manifest_id")

    parents = _parents(roots)
    virtual = {entry["id"] for entry in entries_of(value, "virtual_timelines")}
    for index, group in enumerate(groups):
        yield from _member_problems(
            group, ("groups", index, "members"), parents, virtual
        )
    first_group: dict[str, int] = {}
    for index, group in enumerate(groups):
        first_group.setdefault(group["id"], index)
    yield from order_problems(value, parents, virtual, first_group)
    yield from timestamp_problems(value)
    yield from elision_problems(value)
    yield from matchstamp_problems(value)
    yield from resource_problems(value)
    yield from flow_map_problems(value)
    yield from flow_rule_problems(value)
