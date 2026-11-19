/**
 * The canonical order of a TimeToShare manifest.
 *
 * Every array of a manifest whose order carries no meaning has one canonical
 * order: `timelines` by id; in every timeline, `children` by offset, then id,
 * `conversion_maps` by id, `regions` by start, then end, then id,
 * `flow_control` by coordinate, then id; `groups` by id and every group's `members` by
 * code point; `measure_maps` by id; `graphical.timestamps` by timeline, then
 * coordinate, then id, and every timestamp's `display` in the order of
 * `TIMESTAMP_DISPLAY`. Own-axis values compare by exact numeric
 * value, strings by Unicode code point. A `graphical.order` array is a
 * display order and is never re-ordered, nor is any array of `statements`
 * or `provenance` (the values of a pair and the annotations keep the order
 * they are given in). Readers accept any order; every writer writes the
 * canonical one (`../serialization/write.ts`).
 */

import { clone, isJsonObject, type JsonObject } from "../json/value.js";
import { compareRationals, exactValue, type Rational } from "../numbers/exact.js";
import { compareCodePoints, spell } from "../serialization/text.js";
import { respell } from "./spelling.js";

function member(entry: unknown, key: string): unknown {
  return isJsonObject(entry) ? entry[key] : undefined;
}

/** The words of a named timestamp's `display`, in canonical order. */
export const TIMESTAMP_DISPLAY = ["wedge", "name", "id", "coordinate", "cross_section"] as const;

/** A `display` word's rank: its canonical index, then any other string, then any other value. */
function displayRank(word: unknown): number {
  const index = (TIMESTAMP_DISPLAY as readonly unknown[]).indexOf(word);
  if (index >= 0) return index;
  return typeof word === "string" ? TIMESTAMP_DISPLAY.length : TIMESTAMP_DISPLAY.length + 1;
}

/**
 * Order the words of `display`: the known ones canonically, then any other
 * string by code point, then any other value in its given order, so ordering
 * never fails. Python's `timetoshare.manifest` orders them alike.
 */
function byDisplay(a: unknown, b: unknown): number {
  const difference = displayRank(a) - displayRank(b);
  if (difference !== 0) return difference;
  return typeof a === "string" && typeof b === "string" ? compareCodePoints(a, b) : 0;
}

/** Put the `display` of every named timestamp in canonical order, in place. */
export function orderDisplays(manifest: unknown): void {
  const timestamps = member(member(manifest, "graphical"), "timestamps");
  if (!Array.isArray(timestamps)) return;
  for (const timestamp of timestamps) {
    const display = member(timestamp, "display");
    if (Array.isArray(display)) display.sort(byDisplay);
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
 * by id and its `graphical.timestamps` by timeline, then
 * coordinate, then id, each with its `display` in canonical order. Entries
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
  orderDisplays(result);
  return result;
}
