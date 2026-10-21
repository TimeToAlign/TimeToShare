import type { JsonObject } from "../json/value.js";
import { timelineContainmentProblems } from "./containment.js";
import {
  entries,
  jsonPointer,
  type PathSegment,
  SchemaValidationError,
  text,
} from "./diagnostics.js";
import { MEASURE_VIEWS, timelineMapProblems, timelineMaps } from "./maps.js";
import { orderProblems } from "./order.js";
import { timelineSegmentProblems } from "./segments.js";

function* elementIds(
  timeline: JsonObject,
  path: readonly PathSegment[],
): Generator<[string, PathSegment[]]> {
  yield [text(timeline, "id"), [...path, "id"]];
  for (const member of ["conversion_maps", "regions"]) {
    for (const [index, entry] of entries(timeline, member).entries()) {
      yield [text(entry, "id"), [...path, member, index, "id"]];
    }
  }
  for (const [index, entry] of entries(timeline, "flow_control").entries()) {
    yield [text(entry, "id"), [...path, "flow_control", index, "id"]];
  }
  for (const [index, child] of entries(timeline, "children").entries()) {
    yield* elementIds(child, [...path, "children", index]);
  }
}

function* nestedMapIds(
  timeline: JsonObject,
  path: readonly PathSegment[],
): Generator<[string, PathSegment[]]> {
  for (const [map, at] of timelineMaps(timeline, path)) {
    if (at[at.length - 2] === "maps") yield [text(map, "id"), [...at, "id"]];
  }
  for (const [index, child] of entries(timeline, "children").entries()) {
    yield* nestedMapIds(child, [...path, "children", index]);
  }
}

function* danglingTargets(
  timeline: JsonObject,
  path: readonly PathSegment[],
  measureMaps: ReadonlySet<string>,
): Generator<SchemaValidationError> {
  const flow = entries(timeline, "flow_control");
  const targets = new Set(
    flow.filter((entry) => entry.type === "jump_to").map((entry) => entry.id),
  );
  for (const [index, entry] of flow.entries()) {
    if (Object.hasOwn(entry, "target") && !targets.has(entry.target)) {
      yield new SchemaValidationError(
        "dangling_target",
        [...path, "flow_control", index, "target"],
        `'${entry.target}' names no jump_to of this timeline`,
      );
    }
  }
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
    yield* danglingTargets(child, [...path, "children", index], measureMaps);
  }
}

function duplicate(
  id: string,
  path: readonly PathSegment[],
  first: readonly PathSegment[],
  code: "duplicate_id" | "manifest_id" = "duplicate_id",
): SchemaValidationError {
  return new SchemaValidationError(
    code,
    path,
    `'${id}' is not unique in the manifest, first at ${jsonPointer(first)}`,
  );
}

/** Every ID of a root's tree, the maps other maps hold after the rest. */
function* treeIds(
  root: JsonObject,
  path: readonly PathSegment[],
): Generator<[string, PathSegment[]]> {
  yield* elementIds(root, path);
  yield* nestedMapIds(root, path);
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
    else yield duplicate(id, at, earlier);
  }
  yield* danglingTargets(root, path, measureMaps);
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

function* memberProblems(
  group: JsonObject,
  path: readonly PathSegment[],
  parents: ReadonlyMap<string, string | null>,
): Generator<SchemaValidationError> {
  const selected = new Map<string, number>();
  const earliestDescendant = new Map<string, { index: number; member: string }>();
  for (const [index, member] of (group.members as string[]).entries()) {
    const at = [...path, index];
    if (!parents.has(member)) {
      yield new SchemaValidationError(
        "group_member",
        at,
        `'${member}' names no timeline of this manifest`,
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
 * Root by root: duplicates, dangling targets, conversion maps, containment
 * and segment lines; then the IDs unique across the manifest (the roots'
 * trees, the group IDs, the MeasureMap IDs, the manifest ID), group members,
 * and graphical orders.
 */
export function* identityProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const roots = entries(manifest, "timelines");
  const groups = entries(manifest, "groups");
  const measureMaps = entries(manifest, "measure_maps");
  const measureMapIds = new Set(measureMaps.map((measureMap) => text(measureMap, "id")));
  for (const [index, root] of roots.entries()) {
    yield* rootProblems(root, ["timelines", index], measureMapIds);
  }

  const first = new Map<string, PathSegment[]>();
  for (const [index, root] of roots.entries()) {
    const seen = new Map<string, PathSegment[]>();
    for (const [id, path] of treeIds(root, ["timelines", index])) {
      if (seen.has(id)) continue;
      seen.set(id, path);
      const earlier = first.get(id);
      if (earlier !== undefined) yield duplicate(id, path, earlier);
    }
    for (const [id, path] of seen) if (!first.has(id)) first.set(id, path);
  }
  for (const key of ["groups", "measure_maps"]) {
    for (const [index, entry] of entries(manifest, key).entries()) {
      const id = text(entry, "id");
      const path = [key, index, "id"];
      const earlier = first.get(id);
      if (earlier === undefined) first.set(id, path);
      else yield duplicate(id, path, earlier);
    }
  }
  if (typeof manifest.id === "string") {
    const earlier = first.get(manifest.id);
    if (earlier !== undefined) yield duplicate(manifest.id, ["id"], earlier, "manifest_id");
  }

  const parents = parentsOf(roots);
  for (const [index, group] of groups.entries()) {
    yield* memberProblems(group, ["groups", index, "members"], parents);
  }
  const firstGroup = new Map<string, number>();
  for (const [index, group] of groups.entries()) {
    const id = text(group, "id");
    if (!firstGroup.has(id)) firstGroup.set(id, index);
  }
  yield* orderProblems(manifest, parents, firstGroup);
}
