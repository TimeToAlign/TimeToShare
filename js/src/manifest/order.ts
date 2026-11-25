/**
 * The canonical order of a TimeToShare manifest.
 *
 * Every array of a manifest whose order carries no meaning has one canonical
 * order: `timelines` by id; in every timeline, `children` by offset, then id,
 * `conversion_maps` by id, `regions` by start, then end, then id,
 * `flow_control` by coordinate, then id, and the `targets` of every jump by
 * place (the destination without a place first, then those with `by`, by
 * value, then those with `to`, by id); `groups` by id and every group's `members` by
 * code point; `measure_maps` by id; `resources`, `flow_maps` and
 * `virtual_timelines` by id, a FlowMap's `chunks` keeping their order, which
 * is the order they are played in; `graphical.timestamps`
 * by timeline, then coordinate, then id, and every timestamp's `display` in
 * the order of `TIMESTAMP_DISPLAY`; `graphical.matchstamps` by id, each one's
 * `alignment_anchors` by id, and every anchor's `display` in the order of
 * `ANCHOR_DISPLAY`; `graphical.elisions` by timeline, then start, then id,
 * and every elision's `display` in the order of `ELISION_DISPLAY`. Own-axis
 * values compare by exact numeric
 * value, strings by Unicode code point. A `graphical.order` array is a
 * display order and is never re-ordered, nor is any array of `statements`
 * or `provenance` (the values of a pair and the annotations keep the order
 * they are given in). Readers accept any order; every writer writes the
 * canonical one (`../serialization/write.ts`).
 */

import { clone, isJsonObject, type JsonObject } from "../json/value.js";
import { compareRationals, exactValue, type Rational, rational } from "../numbers/exact.js";
import { compareCodePoints, spell } from "../serialization/text.js";
import { respell } from "./spelling.js";

function member(entry: unknown, key: string): unknown {
  return isJsonObject(entry) ? entry[key] : undefined;
}

/** The words of a named timestamp's `display`, in canonical order. */
export const TIMESTAMP_DISPLAY = ["wedge", "name", "id", "coordinate", "cross_section"] as const;

/** The words of an alignment anchor's `display`, in canonical order. */
export const ANCHOR_DISPLAY = ["line", "name"] as const;

/** The words of an elision's `display`, in canonical order. */
export const ELISION_DISPLAY = ["ellipsis", "name", "id", "coordinate", "continuation"] as const;

/**
 * Order the words of a `display`: the known `words` canonically, then any
 * other string by code point, then any other value in its given order, so
 * ordering never fails. Python's `timetoshare.manifest` orders them alike.
 */
function byDisplay(words: readonly string[]): (a: unknown, b: unknown) => number {
  const rank = (word: unknown): number => {
    const index = (words as readonly unknown[]).indexOf(word);
    if (index >= 0) return index;
    return typeof word === "string" ? words.length : words.length + 1;
  };
  return (a, b) => {
    const difference = rank(a) - rank(b);
    if (difference !== 0) return difference;
    return typeof a === "string" && typeof b === "string" ? compareCodePoints(a, b) : 0;
  };
}

function orderDisplay(owner: unknown, words: readonly string[]): void {
  const display = member(owner, "display");
  if (Array.isArray(display)) display.sort(byDisplay(words));
}

/** Put every timestamp's, alignment anchor's and elision's `display` in canonical order, in place. */
export function orderDisplays(manifest: unknown): void {
  const graphical = member(manifest, "graphical");
  const timestamps = member(graphical, "timestamps");
  if (Array.isArray(timestamps)) {
    for (const timestamp of timestamps) orderDisplay(timestamp, TIMESTAMP_DISPLAY);
  }
  const matchstamps = member(graphical, "matchstamps");
  if (Array.isArray(matchstamps)) {
    for (const matchstamp of matchstamps) {
      const anchors = member(matchstamp, "alignment_anchors");
      if (!Array.isArray(anchors)) continue;
      for (const anchor of anchors) orderDisplay(anchor, ANCHOR_DISPLAY);
    }
  }
  const elisions = member(graphical, "elisions");
  if (Array.isArray(elisions)) {
    for (const elision of elisions) orderDisplay(elision, ELISION_DISPLAY);
  }
}

/** What an entry is ordered by: strings by code point, coordinates by exact value. */
type SortKey = string | Rational;

function compareKeys(left: readonly SortKey[], right: readonly SortKey[]): number {
  for (const [index, a] of left.entries()) {
    const b = right[index] as SortKey;
    const result =
      typeof a === "string"
        ? compareCodePoints(a, b as string)
        : compareRationals(a, b as Rational);
    if (result !== 0) return result;
  }
  return 0;
}

/** A member an entry is ordered by, as a string. */
function text(entry: JsonObject, key: string, where: string): string {
  const value = entry[key];
  if (typeof value === "string") return value;
  throw new TypeError(
    `${where} cannot be put in canonical order: its ${key} ${spell(value)} is not a string`,
  );
}

/** A member an entry is ordered by, as a coordinate: a number or a Fraction pair. */
function coordinate(entry: JsonObject, key: string, where: string): Rational {
  const value = exactValue(entry[key]);
  if (value !== null) return value;
  throw new TypeError(
    `${where} cannot be put in canonical order: its ${key} ${spell(entry[key])} is no number or Fraction pair`,
  );
}

/**
 * Sort an array of objects, in place and stably, by the keys `keyOf` gives
 * each entry; entries that tie keep their given order.
 *
 * @throws {TypeError} if an entry is not an object or lacks a member it is
 * ordered by, or holds it in a wrong type.
 */
function sortBy(
  entries: unknown[],
  where: string,
  keyOf: (entry: JsonObject, where: string) => SortKey[],
): void {
  const keyed = entries.map((entry, index) => {
    const at = `${where}[${index}]`;
    if (!isJsonObject(entry)) {
      throw new TypeError(`${at} cannot be put in canonical order: it is not an object`);
    }
    return { entry, key: keyOf(entry, at) };
  });
  keyed.sort((left, right) => compareKeys(left.key, right.key));
  for (const [index, { entry }] of keyed.entries()) entries[index] = entry;
}

const byId = (entry: JsonObject, where: string): SortKey[] => [text(entry, "id", where)];

const ZERO = rational(0n, 1n);

/** Order a jump's destinations: without a place, then by `by`, then by `to`. */
function byPlace(destination: JsonObject, where: string): SortKey[] {
  if (Object.hasOwn(destination, "by")) return ["1", coordinate(destination, "by", where), ""];
  if (Object.hasOwn(destination, "to")) return ["2", ZERO, text(destination, "to", where)];
  return ["0", ZERO, ""];
}

/** Order the arrays of one timeline and of its descendants, in place. */
function orderTimeline(timeline: JsonObject, where: string): void {
  const { children, conversion_maps: maps, regions, flow_control: flow } = timeline;
  if (Array.isArray(children)) {
    sortBy(children, `${where}.children`, (child, at) => [
      coordinate(child, "offset", at),
      text(child, "id", at),
    ]);
    for (const [index, child] of children.entries()) {
      orderTimeline(child as JsonObject, `${where}.children[${index}]`);
    }
  }
  if (Array.isArray(maps)) sortBy(maps, `${where}.conversion_maps`, byId);
  if (Array.isArray(regions)) {
    sortBy(regions, `${where}.regions`, (region, at) => [
      coordinate(region, "start", at),
      coordinate(region, "end", at),
      text(region, "id", at),
    ]);
  }
  if (Array.isArray(flow)) {
    for (const [index, entry] of flow.entries()) {
      const targets = member(entry, "targets");
      if (Array.isArray(targets)) {
        sortBy(targets, `${where}.flow_control[${index}].targets`, byPlace);
      }
    }
    sortBy(flow, `${where}.flow_control`, (entry, at) => [
      coordinate(entry, "coordinate", at),
      text(entry, "id", at),
    ]);
  }
}

/**
 * Return a deep copy of `value`, its manifest in canonical order and spelling.
 *
 * A value with a top-level `timelines` array is a manifest: its own-axis
 * values are respelled as their number type selects (`./spelling.ts`), every
 * timeline in it is ordered at every depth and the array itself by id, its
 * `groups` by id, each with its `members` by code point, its `measure_maps`
 * by id, its `resources`, `flow_maps` and `virtual_timelines` by id, its `graphical.timestamps` by timeline, then
 * coordinate, then id, each with its `display` in canonical order, and its
 * `graphical.matchstamps` by id, each with its `alignment_anchors` by id and
 * every anchor's `display` in canonical order, and its `graphical.elisions`
 * by timeline, then start, then id, each with its `display` in canonical
 * order. Entries
 * that tie keep their given order, and a member that should hold an ordered
 * array but holds no array is left as it is. Object keys are left as they
 * are (the writers sort them), and any other JSON value is copied unchanged.
 * Python's `timetoshare.canonical_order` gives the same value.
 *
 * @throws {TypeError} if an entry of an ordered array of objects is not an
 * object, lacks a member it is ordered by or holds it in a wrong type, or an
 * entry of a group's `members` is not a string.
 */
export function canonicalOrder<T>(value: T): T {
  const result = clone(value);
  if (!isJsonObject(result) || !Array.isArray(result.timelines)) return result;
  respell(result);
  const timelines = result.timelines;
  sortBy(timelines, "timelines", byId);
  for (const [index, timeline] of timelines.entries()) {
    orderTimeline(timeline as JsonObject, `timelines[${index}]`);
  }
  const groups = result.groups;
  if (Array.isArray(groups)) {
    sortBy(groups, "groups", byId);
    for (const [index, group] of groups.entries()) {
      const members = (group as JsonObject).members;
      if (!Array.isArray(members)) continue;
      for (const [position, entry] of members.entries()) {
        if (typeof entry !== "string") {
          throw new TypeError(
            `groups[${index}].members[${position}] cannot be put in canonical order: ${spell(entry)} is not a string`,
          );
        }
      }
      members.sort(compareCodePoints);
    }
  }
  const measureMaps = result.measure_maps;
  if (Array.isArray(measureMaps)) sortBy(measureMaps, "measure_maps", byId);
  const timestamps = member(result.graphical, "timestamps");
  if (Array.isArray(timestamps)) {
    sortBy(timestamps, "graphical.timestamps", (timestamp, at) => [
      text(timestamp, "timeline", at),
      coordinate(timestamp, "coordinate", at),
      text(timestamp, "id", at),
    ]);
  }
  for (const key of ["resources", "flow_maps", "virtual_timelines"]) {
    const listed = result[key];
    if (Array.isArray(listed)) sortBy(listed, key, byId);
  }
  const matchstamps = member(result.graphical, "matchstamps");
  if (Array.isArray(matchstamps)) {
    sortBy(matchstamps, "graphical.matchstamps", byId);
    for (const [index, matchstamp] of matchstamps.entries()) {
      const anchors = (matchstamp as JsonObject).alignment_anchors;
      if (Array.isArray(anchors)) {
        sortBy(anchors, `graphical.matchstamps[${index}].alignment_anchors`, byId);
      }
    }
  }
  const elisions = member(result.graphical, "elisions");
  if (Array.isArray(elisions)) {
    sortBy(elisions, "graphical.elisions", (elision, at) => [
      text(elision, "timeline", at),
      coordinate(elision, "start", at),
      text(elision, "id", at),
    ]);
  }
  orderDisplays(result);
  return result;
}
