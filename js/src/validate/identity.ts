import type { JsonObject } from "../json/value.js";
import { type Rational, rational } from "../numbers/exact.js";
import { timelineContainmentProblems } from "./containment.js";
import {
  duplicateProblem,
  entries,
  manifestIds,
  type PathSegment,
  SchemaValidationError,
  text,
  treeIds,
} from "./diagnostics.js";
import {
  childStart,
  flowMapProblems,
  flowRuleProblems,
  type JumpPositions,
  timelineFlowProblems,
} from "./flow.js";
import { MEASURE_VIEWS, timelineMapProblems, timelineMaps } from "./maps.js";
import { orderProblems } from "./order.js";
import { timelineSegmentProblems } from "./segments.js";
import {
  elisionProblems,
  matchstampProblems,
  resourceProblems,
  timestampProblems,
} from "./timestamps.js";

function* danglingTargets(
  timeline: JsonObject,
  path: readonly PathSegment[],
  measureMaps: ReadonlySet<string>,
  start: Rational,
  jumpsAt: JumpPositions,
): Generator<SchemaValidationError> {
  yield* timelineFlowProblems(timeline, path, start, jumpsAt);
  for (const [map, at] of timelineMaps(timeline, path)) {
    const reference = map.measure_map;
    if (MEASURE_VIEWS.has(text(map, "type")) && !measureMaps.has(reference as string)) {
      yield new SchemaValidationError(
        "dangling_target",
        [...at, "measure_map"],
        `'${reference}' names no MeasureMap of this manifest`,
      );
    }
  }
  for (const [index, child] of entries(timeline, "children").entries()) {
    yield* danglingTargets(
      child,
      [...path, "children", index],
      measureMaps,
      childStart(start, child),
      jumpsAt,
    );
  }
}

function* rootProblems(
  root: JsonObject,
  path: readonly PathSegment[],
  measureMaps: ReadonlySet<string>,
): Generator<SchemaValidationError> {
  const first = new Map<string, PathSegment[]>();
  for (const [id, at] of treeIds(root, path)) {
    const earlier = first.get(id);
    if (earlier === undefined) first.set(id, at);
    else yield duplicateProblem(id, at, earlier);
  }
  yield* danglingTargets(root, path, measureMaps, rational(0n, 1n), []);
  yield* timelineMapProblems(root, path);
  yield* timelineContainmentProblems(root, path);
  yield* timelineSegmentProblems(root, path);
}

/** Parent ids for every timeline; the first occurrence of a repeated id wins. */
function parentsOf(roots: readonly JsonObject[]): Map<string, string | null> {
  const parents = new Map<string, string | null>();
  const visit = (timeline: JsonObject, parent: string | null): void => {
    const id = text(timeline, "id");
    if (!parents.has(id)) parents.set(id, parent);
    for (const child of entries(timeline, "children")) visit(child, id);
  };
  for (const root of roots) visit(root, null);
  return parents;
}

function ancestorsOf(id: string, parents: ReadonlyMap<string, string | null>): string[] {
  const ancestors: string[] = [];
  let parent = parents.get(id) ?? null;
  while (parent !== null) {
    ancestors.push(parent);
    parent = parents.get(parent) ?? null;
  }
  return ancestors;
}

/**
 * Yield a group's members that name nothing, then those inside or around an
 * earlier member. A virtual timeline lies inside no timeline and contains
 * none.
 */
function* memberProblems(
  group: JsonObject,
  path: readonly PathSegment[],
  parents: ReadonlyMap<string, string | null>,
  virtual: ReadonlySet<string>,
): Generator<SchemaValidationError> {
  const selected = new Map<string, number>();
  const earliestDescendant = new Map<string, { index: number; member: string }>();
  for (const [index, member] of (group.members as string[]).entries()) {
    const at = [...path, index];
    if (!parents.has(member)) {
      if (virtual.has(member)) continue;
      yield new SchemaValidationError(
        "group_member",
        at,
        `'${member}' names no timeline or virtual timeline of this manifest`,
      );
      continue;
    }
    const ancestors = ancestorsOf(member, parents);
    let relation: { index: number; member: string; word: "lies inside" | "contains" } | null = null;
    for (const ancestor of ancestors) {
      const selectedIndex = selected.get(ancestor);
      if (selectedIndex !== undefined && (relation === null || selectedIndex < relation.index)) {
        relation = { index: selectedIndex, member: ancestor, word: "lies inside" };
      }
    }
    const descendant = earliestDescendant.get(member);
    if (descendant !== undefined && (relation === null || descendant.index < relation.index)) {
      relation = { ...descendant, word: "contains" };
    }
    if (relation !== null) {
      yield new SchemaValidationError(
        "group_member",
        at,
        `member '${member}' ${relation.word} member '${relation.member}' of the same group`,
      );
    }

    if (!selected.has(member)) selected.set(member, index);
    for (const ancestor of ancestors) {
      if (!earliestDescendant.has(ancestor)) {
        earliestDescendant.set(ancestor, { index, member });
      }
    }
  }
}

/**
 * Yield semantic problems in the public identity order.
 *
 * Root by root: duplicates, flow control and dangling targets (timeline by
 * timeline, each before its children), conversion maps, containment and
 * segment lines; then the IDs unique across the manifest (the roots' trees,
 * the group IDs, the MeasureMap IDs, the named timestamps' IDs, the elisions'
 * IDs, the named MatchStamps' IDs each followed by its alignment anchors'
 * IDs, the resources', the FlowMaps' and the virtual timelines' IDs, and
 * last the manifest ID); then group members, graphical orders, named
 * timestamps, elisions, named MatchStamps, resources, FlowMaps, virtual
 * timelines and the property `flow`.
 */
export function* identityProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const roots = entries(manifest, "timelines");
  const groups = entries(manifest, "groups");
  const measureMaps = entries(manifest, "measure_maps");
  const measureMapIds = new Set(measureMaps.map((measureMap) => text(measureMap, "id")));
  for (const [index, root] of roots.entries()) {
    yield* rootProblems(root, ["timelines", index], measureMapIds);
  }

  // A root's repeated IDs were reported with the root; across roots each ID
  // counts from its first root, and the manifest's own ID is checked last.
  const first = new Map<string, PathSegment[]>();
  let seen = new Map<string, PathSegment[]>();
  let current: number | null = null;
  for (const [id, path, root] of manifestIds(manifest)) {
    if (root !== current) {
      for (const [earlierId, at] of seen) if (!first.has(earlierId)) first.set(earlierId, at);
      seen = new Map();
      current = root;
    }
    const earlier = first.get(id);
    if (root !== null) {
      if (seen.has(id)) continue;
      seen.set(id, path);
      if (earlier !== undefined) yield duplicateProblem(id, path, earlier);
    } else if (path.length === 1) {
      if (earlier !== undefined) yield duplicateProblem(id, path, earlier, "manifest_id");
    } else if (earlier === undefined) first.set(id, path);
    else yield duplicateProblem(id, path, earlier);
  }

  const parents = parentsOf(roots);
  const virtual = new Set(entries(manifest, "virtual_timelines").map((entry) => text(entry, "id")));
  for (const [index, group] of groups.entries()) {
    yield* memberProblems(group, ["groups", index, "members"], parents, virtual);
  }
  const firstGroup = new Map<string, number>();
  for (const [index, group] of groups.entries()) {
    const id = text(group, "id");
    if (!firstGroup.has(id)) firstGroup.set(id, index);
  }
  yield* orderProblems(manifest, parents, virtual, firstGroup);
  yield* timestampProblems(manifest);
  yield* elisionProblems(manifest);
  yield* matchstampProblems(manifest);
  yield* resourceProblems(manifest);
  yield* flowMapProblems(manifest);
  yield* flowRuleProblems(manifest);
}
