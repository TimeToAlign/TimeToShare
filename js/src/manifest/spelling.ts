/**
 * The respelling of a manifest's own-axis values. The declared number type
 * decides how a value is read, never its spelling, and writers respell every
 * own-axis value as its axis's number type selects: an integral float on an
 * `int` axis as the integer of its exact value, an integer on a `float` axis
 * as the float that equals it exactly, a Fraction pair on a `fraction` axis
 * reduced to lowest terms with integer members. A value its number type
 * cannot take, and every value on an axis whose `unit` or `number_type` is
 * unknown, is written as given. `complete`, `minimal` and `canonicalOrder`
 * respell what they return; Python's `timetoshare` respells the same values.
 */

import type { NumberType } from "../generated/types.js";
import { isJsonObject, JsonFloat, type JsonObject } from "../json/value.js";
import { exactValue, jsonInteger } from "../numbers/exact.js";
import { isUnit, UNITS } from "./units.js";

/** A number type, or `null` for an axis whose unit or number type is unknown. */
type Axis = NumberType | null;

const SAFE = BigInt(Number.MAX_SAFE_INTEGER);

/** An integer as a reader gives it: a `number` within the safe range, else a `bigint`. */
function integer(value: bigint): number | bigint {
  return value >= -SAFE && value <= SAFE ? Number(value) : value;
}

/** An own-axis value spelled as `axis` selects, or as given where it cannot take it. */
function onAxis(value: unknown, axis: Axis): unknown {
  if (axis === "int") {
    const whole = jsonInteger(value);
    return whole === null || Array.isArray(value) ? value : integer(whole);
  }
  if (axis === "float") {
    if (typeof value !== "bigint" && !(typeof value === "number" && Number.isInteger(value))) {
      return value;
    }
    const whole = BigInt(value);
    const double = Number(whole);
    // An integer beyond the largest double, such as 10^400, rounds to an infinity.
    if (!Number.isFinite(double)) return value;
    return BigInt(double) === whole ? new JsonFloat(double === 0 ? 0 : double) : value;
  }
  if (axis === "fraction" && Array.isArray(value)) {
    const reduced = exactValue(value);
    return reduced === null ? value : [integer(reduced.numerator), integer(reduced.denominator)];
  }
  return value;
}

/**
 * The axis of a timeline: unknown where `unit` is missing, no string or no
 * unit, or `number_type` is present but no number type; else `number_type`,
 * or the unit's default where it is missing.
 */
function axisOf(timeline: JsonObject): Axis {
  const { unit, number_type: numberType } = timeline;
  if (!isUnit(unit)) return null;
  if (numberType === undefined) return UNITS[unit].numberType;
  return numberType === "int" || numberType === "float" || numberType === "fraction"
    ? numberType
    : null;
}

function objects(value: unknown): JsonObject[] {
  return Array.isArray(value) ? value.filter(isJsonObject) : [];
}

function respellMembers(owner: JsonObject, keys: readonly string[], axis: Axis): void {
  for (const key of keys) {
    if (Object.hasOwn(owner, key)) owner[key] = onAxis(owner[key], axis);
  }
}

/** Respell the `by` of the `after` a destination or an `ends` holds. */
function respellCondition(holder: unknown, axis: Axis): void {
  const after = isJsonObject(holder) ? holder.after : undefined;
  if (isJsonObject(after)) respellMembers(after, ["by"], axis);
}

/** Respell a timeline and its descendants; `offsetAxis` is its parent's axis, `undefined` for a root. */
function respellTimeline(timeline: JsonObject, offsetAxis: Axis | undefined): void {
  const own = axisOf(timeline);
  respellMembers(timeline, ["offset"], offsetAxis === undefined ? own : offsetAxis);
  respellMembers(timeline, ["length"], own);
  for (const region of objects(timeline.regions)) respellMembers(region, ["start", "end"], own);
  for (const entry of objects(timeline.flow_control)) {
    respellMembers(entry, ["coordinate"], own);
    respellCondition(entry.ends, own);
    for (const destination of objects(entry.targets)) {
      respellMembers(destination, ["by"], own);
      respellCondition(destination, own);
    }
  }
  for (const child of objects(timeline.children)) respellTimeline(child, own);
}

/**
 * Respell every own-axis value of a manifest as its number type selects, in
 * place: a timeline's `length`, a root's `offset` on its own axis, a child's
 * `offset` on its parent's, region `start` and `end`, flow-control
 * `coordinate`s and the `by` of every destination and of every `after`, every
 * named timestamp's `coordinate`, every elision's `start`, `end` and width
 * `span` and every gap of a FlowMap, on the axis of the one timeline its
 * `timeline` names (as given where it names none or several), and a virtual
 * timeline's `length` on the virtual timeline's own axis. Anything else is left as it is, so any value may be given.
 */
export function respell(manifest: unknown): void {
  if (!isJsonObject(manifest)) return;
  for (const timeline of objects(manifest.timelines)) respellTimeline(timeline, undefined);
  const axes = new Map<string, Axis[]>();
  const visit = (timeline: JsonObject): void => {
    const { id } = timeline;
    if (typeof id === "string") axes.set(id, [...(axes.get(id) ?? []), axisOf(timeline)]);
    for (const child of objects(timeline.children)) visit(child);
  };
  for (const timeline of objects(manifest.timelines)) visit(timeline);
  const axisNamed = (timeline: unknown): Axis | undefined => {
    const found = typeof timeline === "string" ? axes.get(timeline) : undefined;
    return found?.length === 1 ? found[0] : undefined;
  };
  const { graphical } = manifest;
  for (const timestamp of objects(isJsonObject(graphical) ? graphical.timestamps : undefined)) {
    const axis = axisNamed(timestamp.timeline);
    if (axis !== undefined) respellMembers(timestamp, ["coordinate"], axis);
  }
  for (const elision of objects(isJsonObject(graphical) ? graphical.elisions : undefined)) {
    const axis = axisNamed(elision.timeline);
    if (axis === undefined) continue;
    respellMembers(elision, ["start", "end"], axis);
    if (isJsonObject(elision.width)) respellMembers(elision.width, ["span"], axis);
  }
  for (const flowMap of objects(manifest.flow_maps)) {
    const axis = axisNamed(flowMap.timeline);
    if (axis === undefined) continue;
    for (const chunk of objects(flowMap.chunks)) respellMembers(chunk, ["gap"], axis);
  }
  for (const virtual of objects(manifest.virtual_timelines)) {
    respellMembers(virtual, ["length"], axisOf(virtual));
  }
}
