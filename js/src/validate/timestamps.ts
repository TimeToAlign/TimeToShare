/**
 * Named-timestamp, MatchStamp and resource rules: the timeline a timestamp
 * names and its coordinate; the alignment anchors of the named MatchStamps
 * and their match timestamps; the timelines and types of the resources.
 * Python's `timetoshare.validation.timestamps` checks the same rules with
 * the same messages.
 */

import { isJsonObject, type JsonObject } from "../json/value.js";
import { compareExact, exact } from "../numbers/exact.js";
import { spell } from "../serialization/text.js";
import {
  entries,
  lengthOf,
  matchstampsOf,
  type PathSegment,
  SchemaValidationError,
  stringId,
  text,
  timelinesById,
  timestampsOf,
} from "./diagnostics.js";

/**
 * Yield timestamps off the manifest's timelines or outside their extent.
 *
 * A timestamp names a timeline of the manifest, at any depth, and its
 * coordinate lies between 0 and that timeline's length, or at or after 0
 * where the length is not known.
 */
export function* timestampProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const timelines = timelinesById(manifest);
  for (const [index, timestamp] of timestampsOf(manifest).entries()) {
    const path = ["graphical", "timestamps", index];
    const id = text(timestamp, "timeline");
    const timeline = timelines.get(id);
    if (timeline === undefined) {
      yield new SchemaValidationError(
        "timestamp_timeline",
        [...path, "timeline"],
        `'${id}' names no timeline of this manifest`,
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

/** The resource types a manifest names at most once. */
export const ONE_RESOURCE_TYPES = ["MatchClaim", "Projection"] as const;

/**
 * Yield the problems of the resources.
 *
 * Resource by resource, each ID of its `timelines` names a timeline of the
 * manifest, at any depth, and no earlier resource has its type where that
 * type is `MatchClaim` or `Projection`.
 */
export function* resourceProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const timelines = timelinesById(manifest);
  const first = new Map<string, string>();
  for (const [index, resource] of entries(manifest, "resources").entries()) {
    const path = ["resources", index];
    for (const [number, id] of (resource.timelines as string[]).entries()) {
      if (!timelines.has(id)) {
        yield new SchemaValidationError(
          "resource_timeline",
          [...path, "timelines", number],
          `'${id}' names no timeline of this manifest`,
        );
      }
    }
    const kind = text(resource, "type");
    if (!(ONE_RESOURCE_TYPES as readonly string[]).includes(kind)) continue;
    const earlier = first.get(kind);
    if (earlier !== undefined) {
      yield new SchemaValidationError(
        "resource_type",
        [...path, "type"],
        `a manifest names at most one resource of the type ${kind}; '${earlier}' is one`,
      );
    } else first.set(kind, text(resource, "id"));
  }
}
