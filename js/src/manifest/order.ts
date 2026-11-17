/**
 * The canonical order and the standard writer of a TimeToShare manifest.
 *
 * Every array of a manifest whose order carries no meaning has one canonical
 * order: `timelines` by id; in every timeline, `children` by offset, then id,
 * `conversion_maps` by id, `regions` by start, then end, then id,
 * `flow_control` by coordinate, then id; `groups` by id and every group's `members` by
 * code point; `measure_maps` and `schemes` by id; `graphical.timestamps` by timeline, then
 * coordinate, then id, and every timestamp's `display` in the order of
 * `TIMESTAMP_DISPLAY`. Own-axis values compare by exact numeric
 * value, strings by Unicode code point. A `graphical.order` array is a
 * display order and is never re-ordered, nor are the `links` of the
 * manifest, a timeline or a region (a display order), a link's `uri` (the
 * first preferred) and `parts` (the order of its reading), or any other
 * array of a link. Readers accept any order; `dumps` writes the canonical
 * one, every object's keys sorted by code point, two-space indentation and a
 * final newline, the same bytes as Python's `timetoshare.dumps`.
 */

import { clone, isJsonObject, type JsonObject } from "../json/value.js";
import { compareCodePoints, emit } from "../json/write.js";
import { compareExact } from "../numbers/exact.js";
import { respell } from "./spelling.js";

function text(member: unknown): string {
  if (typeof member !== "string") throw new TypeError(`not a string: ${String(member)}`);
  return member;
}

/** Order by the first comparison that does not tie. */
function by<T>(...comparisons: ((left: T, right: T) => number)[]) {
  return (left: T, right: T): number => {
    for (const compare of comparisons) {
      const result = compare(left, right);
      if (result !== 0) return result;
    }
    return 0;
  };
}

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

const byId = (a: unknown, b: unknown): number =>
  compareCodePoints(text(member(a, "id")), text(member(b, "id")));

const at =
  (key: string) =>
  (a: unknown, b: unknown): number =>
    compareExact(member(a, key), member(b, key));

/** Order the arrays of one timeline and of its descendants, in place. */
function orderTimeline(timeline: JsonObject): void {
  if (Array.isArray(timeline.children)) {
    for (const child of timeline.children) if (isJsonObject(child)) orderTimeline(child);
    timeline.children.sort(by(at("offset"), byId));
  }
  if (Array.isArray(timeline.conversion_maps)) timeline.conversion_maps.sort(byId);
  if (Array.isArray(timeline.regions)) timeline.regions.sort(by(at("start"), at("end"), byId));
  if (Array.isArray(timeline.flow_control)) {
    timeline.flow_control.sort(by(at("coordinate"), byId));
  }
}

/**
 * Return a deep copy of `value`, its manifest in canonical order and spelling.
 *
 * A value with a top-level `timelines` array is a manifest: every timeline in
 * it is ordered at every depth and the array itself by id, its `groups` are
 * ordered by id, each with its `members` by code point, its `measure_maps`
 * and its `schemes` by id and its `graphical.timestamps` by timeline, then coordinate, then id,
 * each with its `display` in canonical order. Every value it reads by a number type is spelled as
 * that type selects (`./spelling.ts`).
 * Object keys are left as they are (`dumps` sorts them), and any other JSON
 * value is copied unchanged. Python's `timetoshare.canonical_order` gives
 * the same value.
 *
 * @throws {TypeError} if a collection holds an entry whose ordering members are missing or of the wrong type.
 */
export function canonicalOrder<T>(value: T): T {
  const result = clone(value);
  const timelines = member(result, "timelines");
  if (!Array.isArray(timelines)) return result;
  respell(result);
  for (const timeline of timelines) if (isJsonObject(timeline)) orderTimeline(timeline);
  timelines.sort(byId);
  const groups = member(result, "groups");
  if (Array.isArray(groups)) {
    for (const group of groups) {
      const members = member(group, "members");
      if (Array.isArray(members)) {
        members.sort((a: unknown, b: unknown) => compareCodePoints(text(a), text(b)));
      }
    }
    groups.sort(byId);
  }
  for (const key of ["measure_maps", "schemes"]) {
    const entries = member(result, key);
    if (Array.isArray(entries)) entries.sort(byId);
  }
  const timestamps = member(member(result, "graphical"), "timestamps");
  if (Array.isArray(timestamps)) {
    const byTimeline = (a: unknown, b: unknown): number =>
      compareCodePoints(text(member(a, "timeline")), text(member(b, "timeline")));
    timestamps.sort(by(byTimeline, at("coordinate"), byId));
  }
  orderDisplays(result);
  return result;
}

/**
 * Return the standard text of a TimeToShare manifest, or of any JSON value.
 *
 * The value is put in `canonicalOrder`, then written with the keys of every
 * object sorted by code point, two-space indentation and a final newline,
 * characters unescaped, every float spelled as Python's `repr` spells it (a
 * plain number with a fractional part, a `JsonFloat`) and every integer
 * without a decimal point (a plain integral number, a `bigint`). Python's
 * `timetoshare.dumps` writes the same bytes.
 *
 * @throws {RangeError} for a non-finite number or a string with a lone surrogate.
 * @throws {TypeError} for a value that is not JSON, or a collection that cannot be put in canonical order.
 */
export function dumps(value: unknown): string {
  return `${emit(canonicalOrder(value), "  ", true, "")}\n`;
}
