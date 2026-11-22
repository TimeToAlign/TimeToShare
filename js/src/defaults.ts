/**
 * The defaults of a TimeToShare manifest: the complete and the minimal form.
 *
 * Every key with a default may be left out of a manifest, and a reader
 * supplies the default. The complete form writes every such key, its default
 * included; the minimal form leaves out exactly the keys whose value is the
 * default. Either form reads to the same manifest, and each converts to the
 * other. A key whose default is "absent" (a manifest's `id` and `graphical`,
 * a root's `offset`) is never added and never removed. Unknown keys pass
 * through untouched.
 */

import type { CompleteManifest, LosslessManifest, NumberType } from "./generated/types.js";
import { clone, isJsonObject, JsonFloat, type JsonObject } from "./json/value.js";
import { orderDisplays } from "./manifest/order.js";
import { respell } from "./manifest/spelling.js";
import { isUnit, UNITS } from "./manifest/units.js";
import { exactValue, sameRational } from "./numbers/exact.js";

/**
 * The default of every key that has one, by the kind of object holding it.
 * A timeline's `number_type` defaults to its unit's default number type,
 * which the unit table `UNITS` states. Every conversion map has the keys of
 * `conversion_map`; a `LinearMap` adds those of `linear_map` and a `TableMap`
 * those of `table_map`. Every flow-control element has the keys of
 * `flow_control_element`, and one whose manifestation is `repeat_end` adds
 * those of `repeat_end`, as no other element carries a repeat count. Every named timestamp of
 * `graphical.timestamps` has the keys of `timestamp`, a match timestamp
 * (`matchstamp: true`) those of `match_timestamp` instead, and every
 * alignment anchor of a named MatchStamp those of `alignment_anchor`, and every
 * elision of `graphical.elisions` those of `elision` (its `width` has none). A
 * resource has no defaults. `@context`,
 * `statements` and `provenance` have no default and are never added or
 * removed. Python's
 * `timetoshare.defaults` holds the same table, and the schema declares each value as the key's `default`.
 */
export const DEFAULTS = {
  manifest: { name: null, meta: {}, groups: [], measure_maps: [], resources: [] },
  timeline: {
    name: null,
    locked: false,
    is_segment_line: false,
    meta: {},
    children: [],
    conversion_maps: [],
    regions: [],
    flow_control: [],
  },
  region: { name: null, meta: {} },
  flow_control_element: { name: null, label: null, meta: {} },
  repeat_end: { repeat_count: 1 },
  conversion_map: { name: null },
  linear_map: { scalar: 1, offset: 0 },
  table_map: { kind: "linear", extrapolate: "none" },
  measure_map: { name: null, meta: {} },
  group: { name: null, meta: {} },
  graphical: {
    styles: {},
    rules: [],
    order: {},
    timestamps: [],
    matchstamps: [],
    elisions: [],
  },
  timestamp: { display: ["wedge", "name", "cross_section"], matchstamp: false, groupstamp: false },
  match_timestamp: { display: ["cross_section"], groupstamp: false },
  alignment_anchor: { display: ["line"] },
  elision: { display: ["strip", "name", "coordinate"] },
} as const;

type Kind = keyof typeof DEFAULTS;

/** The kind of the defaults a conversion map type adds to those of every map. */
const MAP_KINDS: Readonly<Record<string, Kind>> = {
  LinearMap: "linear_map",
  TableMap: "table_map",
};

/** A pass over one object of a manifest: complete it, or strip its defaults. */
type Pass = (owner: JsonObject, kind: Kind) => void;

function objects(owner: JsonObject, key: string): JsonObject[] {
  const value = owner[key];
  return Array.isArray(value) ? value.filter(isJsonObject) : [];
}

/** Apply a pass to a conversion map and to the maps it holds. */
function visitMap(map: JsonObject, pass: Pass): void {
  pass(map, "conversion_map");
  const { type } = map;
  if (typeof type === "string" && Object.hasOwn(MAP_KINDS, type)) {
    pass(map, MAP_KINDS[type] as Kind);
  }
  const maps = map.maps;
  const nested = Array.isArray(maps) ? maps : isJsonObject(maps) ? Object.values(maps) : [];
  for (const entry of nested) if (isJsonObject(entry)) visitMap(entry, pass);
}

/** Apply a pass to a timeline and to everything it holds. */
function visitTimeline(timeline: JsonObject, pass: Pass): void {
  pass(timeline, "timeline");
  for (const child of objects(timeline, "children")) visitTimeline(child, pass);
  for (const map of objects(timeline, "conversion_maps")) visitMap(map, pass);
  for (const region of objects(timeline, "regions")) pass(region, "region");
  for (const entry of objects(timeline, "flow_control")) {
    pass(entry, "flow_control_element");
    if (entry.manifestation === "repeat_end") pass(entry, "repeat_end");
  }
}

/** Apply a pass to every object of a manifest that has defaults, outermost first. */
function visitManifest(manifest: unknown, pass: Pass): void {
  if (!isJsonObject(manifest)) return;
  pass(manifest, "manifest");
  for (const timeline of objects(manifest, "timelines")) visitTimeline(timeline, pass);
  for (const group of objects(manifest, "groups")) pass(group, "group");
  for (const measureMap of objects(manifest, "measure_maps")) pass(measureMap, "measure_map");
  const { graphical } = manifest;
  if (!isJsonObject(graphical)) return;
  pass(graphical, "graphical");
  for (const timestamp of objects(graphical, "timestamps")) {
    pass(timestamp, timestamp.matchstamp === true ? "match_timestamp" : "timestamp");
  }
  for (const matchstamp of objects(graphical, "matchstamps")) {
    for (const anchor of objects(matchstamp, "alignment_anchors")) pass(anchor, "alignment_anchor");
  }
  for (const elision of objects(graphical, "elisions")) pass(elision, "elision");
}

/** The default number type of a timeline, or `undefined` where its unit is none. */
function defaultNumberType(timeline: JsonObject): NumberType | undefined {
  return isUnit(timeline.unit) ? UNITS[timeline.unit].numberType : undefined;
}

const completeOne: Pass = (owner, kind) => {
  for (const [key, value] of Object.entries(DEFAULTS[kind])) {
    if (!Object.hasOwn(owner, key)) owner[key] = clone(value as unknown);
  }
  if (kind === "timeline" && !Object.hasOwn(owner, "number_type")) {
    const numberType = defaultNumberType(owner);
    if (numberType !== undefined) owner.number_type = numberType;
  }
};

/**
 * Whether two JSON values are equal in value: numbers by exact value (an
 * integer, a float and a Fraction pair of equal value are equal), arrays
 * when their items are, objects when their members are, anything else only
 * to itself.
 */
function same(left: unknown, right: unknown): boolean {
  const a = exactValue(left);
  const b = exactValue(right);
  if (a !== null && b !== null) return sameRational(a, b);
  if (Array.isArray(left) || Array.isArray(right)) {
    return (
      Array.isArray(left) &&
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((item, index) => same(item, right[index]))
    );
  }
  if (isJsonObject(left) || isJsonObject(right)) {
    if (!isJsonObject(left) || !isJsonObject(right)) return false;
    const keys = Object.keys(left);
    return (
      keys.length === Object.keys(right).length &&
      keys.every((key) => Object.hasOwn(right, key) && same(left[key], right[key]))
    );
  }
  return left === right && !(left instanceof JsonFloat);
}

const stripOne: Pass = (owner, kind) => {
  for (const [key, value] of Object.entries(DEFAULTS[kind])) {
    if (Object.hasOwn(owner, key) && same(owner[key], value)) delete owner[key];
  }
  if (kind === "timeline" && Object.hasOwn(owner, "number_type")) {
    if (owner.number_type === defaultNumberType(owner)) delete owner.number_type;
  }
};

/**
 * Return a copy of a manifest in the complete form: every key with a default
 * that is absent is added with its default, at every depth (a timeline's
 * `number_type` is its unit's default). Keys whose default is "absent" are
 * never added, present keys keep their values, spelled as their number type
 * selects (as `canonicalOrder` spells them), the `display` of a named
 * timestamp, an alignment anchor and an elision in canonical order, and unknown keys pass through.
 * Any other value is copied, its manifest-shaped parts completed, so a
 * `graphical` object alone completes as `complete({ graphical }).graphical`.
 * Python's `timetoshare.complete` gives the same value.
 */
export function complete(value: LosslessManifest): CompleteManifest;
export function complete<T>(value: T): T;
export function complete(value: unknown): unknown {
  const result = clone(value);
  respell(result);
  orderDisplays(result);
  visitManifest(result, completeOne);
  return result;
}

/**
 * Return a copy of a manifest in the minimal form: the complete form without
 * every key whose value equals its default in value, after own-axis values
 * are respelled and each `display` put in canonical order (`repeat_count:
 * 1.0` and a `LinearMap`'s `scalar: [1, 1]` are left out like `1`).
 * `minimal(complete(x))` equals `minimal(x)` and
 * `complete(minimal(x))` equals `complete(x)`. Python's
 * `timetoshare.minimal` gives the same value.
 */
export function minimal(value: LosslessManifest): LosslessManifest;
export function minimal<T>(value: T): T;
export function minimal(value: unknown): unknown {
  const result = complete(value);
  visitManifest(result, stripOne);
  return result;
}
