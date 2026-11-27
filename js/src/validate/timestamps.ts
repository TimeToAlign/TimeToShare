/**
 * Named-timestamp, elision, MatchStamp and resource rules: the timeline a
 * timestamp names, its coordinate and whether it may be a groupstamp; the
 * timeline an elision names and its stretch; the alignment anchors of the
 * named MatchStamps and their match timestamps; the timelines, types and
 * folders of the resources.
 * Python's `timetoshare.validation.timestamps` checks the same rules with
 * the same messages.
 */

import { isJsonObject, type JsonObject } from "../json/value.js";
import { compareExact, exact } from "../numbers/exact.js";
import { spell } from "../serialization/text.js";
import {
  axesById,
  elisionsOf,
  entries,
  lengthOf,
  matchstampsOf,
  type PathSegment,
  SchemaValidationError,
  stringId,
  text,
  timestampsOf,
} from "./diagnostics.js";

/**
 * The IDs of the timelines lying in a group, at any depth: a timeline lies
 * in a group when it or one of its ancestors is listed in the group's
 * `members`, since a member's descendants are drawn inside the member's
 * card in the group's frame. An ancestor of a member lies in no group
 * through it. A virtual timeline lies in the groups it is a member of.
 */
function groupedTimelines(manifest: JsonObject): Set<string> {
  const members = new Set(
    entries(manifest, "groups").flatMap((group) =>
      Array.isArray(group.members)
        ? group.members.filter((member) => typeof member === "string")
        : [],
    ),
  );
  const grouped = new Set<string>();
  const visit = (timeline: JsonObject, inside: boolean): void => {
    const id = text(timeline, "id");
    const within = inside || members.has(id);
    if (within) grouped.add(id);
    for (const child of entries(timeline, "children")) visit(child, within);
  };
  for (const root of entries(manifest, "timelines")) visit(root, false);
  for (const entry of entries(manifest, "virtual_timelines")) {
    if (members.has(text(entry, "id"))) grouped.add(text(entry, "id"));
  }
  return grouped;
}

/**
 * Yield timestamps off the manifest's timelines, outside their extent or groupless.
 *
 * A timestamp names a timeline of the manifest, at any depth, or a virtual
 * timeline, and its coordinate lies between 0 and that timeline's length,
 * or at or after 0 where the length is not known. A groupstamp (`groupstamp: true`), a match
 * timestamp included, lies in a group (`groupedTimelines`).
 */
export function* timestampProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const timelines = axesById(manifest);
  const grouped = groupedTimelines(manifest);
  for (const [index, timestamp] of timestampsOf(manifest).entries()) {
    const path = ["graphical", "timestamps", index];
    const id = text(timestamp, "timeline");
    const timeline = timelines.get(id);
    if (timeline === undefined) {
      yield new SchemaValidationError(
        "timestamp_timeline",
        [...path, "timeline"],
        `'${id}' names no timeline or virtual timeline of this manifest`,
      );
      continue;
    }
    const { coordinate } = timestamp;
    const length = lengthOf(timeline);
    const where = `coordinate ${spell(coordinate)} of '${text(timestamp, "id")}'`;
    if (compareExact(coordinate, 0) < 0) {
      yield new SchemaValidationError(
        "timestamp_coordinate",
        [...path, "coordinate"],
        `${where} lies before the start of its timeline '${id}'`,
      );
    } else if (length !== null && compareExact(coordinate, length) > 0) {
      yield new SchemaValidationError(
        "timestamp_coordinate",
        [...path, "coordinate"],
        `${where} is beyond the length ${spell(length)} of its timeline '${id}'`,
      );
    }
    if (timestamp.groupstamp === true && !grouped.has(id)) {
      yield new SchemaValidationError(
        "groupstamp",
        [...path, "groupstamp"],
        `'${text(timestamp, "id")}' is a groupstamp, but its timeline '${id}' is a member of no group and lies in none`,
      );
    }
  }
}

/**
 * Yield elisions off the manifest's timelines or outside their extent.
 *
 * An elision names a timeline of the manifest, at any depth, or a virtual
 * timeline, and its `start` lies before its `end`, both between 0 and that
 * timeline's length, or at or after 0 where the length is not known.
 * Elisions may overlap; no overlap is a problem.
 */
export function* elisionProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const timelines = axesById(manifest);
  for (const [index, elision] of elisionsOf(manifest).entries()) {
    const path = ["graphical", "elisions", index];
    const id = text(elision, "timeline");
    const timeline = timelines.get(id);
    if (timeline === undefined) {
      yield new SchemaValidationError(
        "elision_timeline",
        [...path, "timeline"],
        `'${id}' names no timeline or virtual timeline of this manifest`,
      );
      continue;
    }
    const { start, end } = elision;
    const name = text(elision, "id");
    if (compareExact(start, 0) < 0) {
      yield new SchemaValidationError(
        "elision_stretch",
        [...path, "start"],
        `start ${spell(start)} of '${name}' lies before the start of its timeline '${id}'`,
      );
    }
    const length = lengthOf(timeline);
    if (length !== null && compareExact(end, length) > 0) {
      yield new SchemaValidationError(
        "elision_stretch",
        [...path, "end"],
        `end ${spell(end)} of '${name}' is beyond the length ${spell(length)} of its timeline '${id}'`,
      );
    }
    if (compareExact(start, end) >= 0) {
      yield new SchemaValidationError(
        "elision_stretch",
        [...path, "end"],
        `end ${spell(end)} of '${name}' does not lie after its start ${spell(start)}`,
      );
    }
  }
}

/** The number of connected sets the pairs join their members into. */
function connectedSets(pairs: readonly (readonly [string, string])[]): number {
  const parent = new Map<string, string>();
  const find = (member: string): string => {
    if (!parent.has(member)) parent.set(member, member);
    let root = member;
    while (parent.get(root) !== root) root = parent.get(root) as string;
    parent.set(member, root);
    return root;
  };
  for (const [left, right] of pairs) parent.set(find(left), find(right));
  return new Set([...parent.keys()].map(find)).size;
}

/**
 * Yield the problems of the named MatchStamps and their match timestamps.
 *
 * MatchStamp by MatchStamp, each alignment anchor names two match
 * timestamps of the manifest (`matchstamp: true`) lying on two timelines,
 * and the anchors are one connected set; then, timestamp by timestamp, a
 * match timestamp shares its coordinate with no earlier match timestamp and
 * some MatchStamp names it. A named timestamp that is no object or holds
 * no string ID is passed over, so the rules read a manifest whose ordinary
 * timestamps no schema has checked.
 */
export function* matchstampProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const timestamps = new Map<string, JsonObject>();
  for (const timestamp of timestampsOf(manifest)) {
    const id = stringId(timestamp);
    if (id !== null && !timestamps.has(id)) timestamps.set(id, timestamp);
  }
  const named = new Set<string>();
  for (const [index, matchstamp] of matchstampsOf(manifest).entries()) {
    const path: PathSegment[] = ["graphical", "matchstamps", index, "alignment_anchors"];
    const pairs: [string, string][] = [];
    for (const [number, anchor] of entries(matchstamp, "alignment_anchors").entries()) {
      const at = [...path, number, "timestamps"];
      const ends = anchor.timestamps as string[];
      for (const end of ends) named.add(end);
      pairs.push([ends[0] as string, ends[1] as string]);
      const found: JsonObject[] = [];
      for (const [position, id] of ends.entries()) {
        const timestamp = timestamps.get(id);
        if (timestamp === undefined) {
          yield new SchemaValidationError(
            "alignment_anchor",
            [...at, position],
            `'${id}' names no timestamp of this manifest`,
          );
        } else if (timestamp.matchstamp !== true) {
          yield new SchemaValidationError(
            "alignment_anchor",
            [...at, position],
            `'${id}' is no match timestamp`,
          );
        } else found.push(timestamp);
      }
      const [left, right] = found;
      if (left !== undefined && right !== undefined && left.timeline === right.timeline) {
        yield new SchemaValidationError(
          "alignment_anchor",
          [...at, 1],
          `the timestamps of '${text(anchor, "id")}' both lie on the timeline '${text(left, "timeline")}'`,
        );
      }
    }
    if (connectedSets(pairs) > 1) {
      yield new SchemaValidationError(
        "matchstamp",
        path,
        `the alignment anchors of '${text(matchstamp, "id")}' are not one connected set`,
      );
    }
  }
  const first = new Map<string, string>();
  for (const [index, timestamp] of timestampsOf(manifest).entries()) {
    if (!isJsonObject(timestamp) || timestamp.matchstamp !== true) continue;
    const path = ["graphical", "timestamps", index];
    const id = text(timestamp, "id");
    const value = exact(timestamp.coordinate);
    const key = JSON.stringify([
      text(timestamp, "timeline"),
      String(value.numerator),
      String(value.denominator),
    ]);
    const earlier = first.get(key);
    if (earlier !== undefined) {
      yield new SchemaValidationError(
        "match_timestamp",
        path,
        `'${id}' lies on the coordinate of the match timestamp '${earlier}'`,
      );
    } else first.set(key, id);
    if (!named.has(id)) {
      yield new SchemaValidationError(
        "match_timestamp",
        path,
        `the match timestamp '${id}' belongs to no MatchStamp`,
      );
    }
  }
}

/** The members of a descriptor that state a file's bytes, which a folder has not. */
export const FOLDER_FILE_KEYS = ["size", "integrity"] as const;

/**
 * Yield the problem of a descriptor naming a folder (a `url` ending in `/`)
 * with a `size` or an `integrity`: the first of the two it states, at that
 * member.
 */
export function* folderProblems(
  descriptor: JsonObject,
  path: readonly PathSegment[],
): Generator<SchemaValidationError> {
  const url = descriptor.url;
  if (typeof url !== "string" || !url.endsWith("/")) return;
  for (const key of FOLDER_FILE_KEYS) {
    if (Object.hasOwn(descriptor, key)) {
      yield new SchemaValidationError(
        "folder_descriptor",
        [...path, key],
        `'${url}' names a folder, which has no ${key}`,
      );
      return;
    }
  }
}

/**
 * Yield the problems of the resources.
 *
 * Resource by resource, each ID of its `timelines` names a timeline of the
 * manifest, at any depth, or a virtual timeline, and no earlier resource of
 * its type lists it; then a folder has no `size` and no `integrity`.
 */
export function* resourceProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const timelines = axesById(manifest);
  const first = new Map<string, Map<string, string>>();
  for (const [index, resource] of entries(manifest, "resources").entries()) {
    const path = ["resources", index];
    const kind = text(resource, "type");
    const id = text(resource, "id");
    let listed = first.get(kind);
    if (listed === undefined) {
      listed = new Map();
      first.set(kind, listed);
    }
    for (const [number, timeline] of (resource.timelines as string[]).entries()) {
      const at = [...path, "timelines", number];
      if (!timelines.has(timeline)) {
        yield new SchemaValidationError(
          "resource_timeline",
          at,
          `'${timeline}' names no timeline or virtual timeline of this manifest`,
        );
      }
      const earlier = listed.get(timeline);
      if (earlier === undefined) listed.set(timeline, id);
      else if (earlier !== id) {
        yield new SchemaValidationError(
          "resource_type",
          at,
          `'${timeline}' is listed by the resource '${earlier}' of the type ${kind} already`,
        );
      }
    }
    yield* folderProblems(resource, path);
  }
}
