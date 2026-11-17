/**
 * The validator's diagnostics and the small readers every rule module shares:
 * the error a rule raises with its code and path, the JSON pointer of a path,
 * and the readers of a schema-checked object's members. A leaf module: it
 * imports no rule module and no validator, so the rule modules and
 * `validate.ts` both import it without a cycle.
 */

import type { NumberType, TimeUnit } from "../generated/types.js";
import { isJsonObject, type JsonObject } from "../json/value.js";
import { compareCodePoints } from "../json/write.js";

/** One step of a path into a value: an object key or an array index. */
export type PathSegment = string | number;

/** A stable machine-readable schema or semantic rule identifier. */
export type ValidationCode =
  | "not_a_manifest"
  | "schema"
  | "representation"
  | "duplicate_id"
  | "dangling_target"
  | "conversion_map"
  | "child_unit"
  | "child_offset"
  | "child_end"
  | "segment_line"
  | "group_member"
  | "manifest_id"
  | "order_key"
  | "display_order"
  | "band_order"
  | "timestamp_timeline"
  | "timestamp_coordinate"
  | "finite_number";

/** Order paths segment by segment: indices by number, keys by code point, prefixes first. */
export function comparePaths(left: readonly PathSegment[], right: readonly PathSegment[]): number {
  for (let index = 0; index < Math.min(left.length, right.length); index += 1) {
    const a = left[index] as PathSegment;
    const b = right[index] as PathSegment;
    if (a === b) continue;
    if (typeof a === "number" && typeof b === "number") return a < b ? -1 : 1;
    return compareCodePoints(String(a), String(b));
  }
  return left.length - right.length;
}

/** Render a path as a JSON pointer in URI fragment form (`#` for the root). */
export function jsonPointer(path: readonly PathSegment[]): string {
  const segments = path.map((segment) => String(segment).replace(/~/g, "~0").replace(/\//g, "~1"));
  return `#${segments.map((segment) => `/${segment}`).join("")}`;
}

/** Thrown when a value violates the schema or a semantic rule. */
export class SchemaValidationError extends Error {
  readonly code: ValidationCode;
  readonly path: readonly PathSegment[];
  readonly detail: string;

  constructor(code: ValidationCode, path: readonly PathSegment[], detail: string) {
    super(`${jsonPointer(path)}: ${detail}`);
    this.name = "SchemaValidationError";
    this.code = code;
    this.path = path;
    this.detail = detail;
  }
}

/** The objects of an array member, or none where it is absent. */
export function entries(owner: unknown, key: string): JsonObject[] {
  const value = isJsonObject(owner) ? owner[key] : undefined;
  return Array.isArray(value) ? (value as JsonObject[]) : [];
}

/** A string member of an object the schema has already checked. */
export function text(owner: JsonObject, key: string): string {
  return owner[key] as string;
}

/**
 * Every timeline of a manifest, at any depth, by ID; of a repeated ID the
 * first timeline in document order is kept.
 */
export function timelinesById(manifest: unknown): Map<string, JsonObject> {
  const found = new Map<string, JsonObject>();
  const visit = (timeline: JsonObject): void => {
    const id = text(timeline, "id");
    if (!found.has(id)) found.set(id, timeline);
    for (const child of entries(timeline, "children")) visit(child);
  };
  for (const root of entries(manifest, "timelines")) visit(root);
  return found;
}

/** The named timestamps of a manifest's `graphical` object, or none. */
export function timestampsOf(manifest: unknown): JsonObject[] {
  return entries(isJsonObject(manifest) ? manifest.graphical : undefined, "timestamps");
}

/** A timeline's length, or `null` where it is not known. */
export function lengthOf(timeline: JsonObject): unknown {
  return timeline.length ?? null;
}

/** The default number type of each unit. */
export const UNIT_NUMBER_TYPES: Readonly<Record<TimeUnit, NumberType>> = {
  number: "float",
  floating_measures: "float",
  whole_notes: "fraction",
  quarters: "fraction",
  ticks: "int",
  milliseconds: "float",
  seconds: "float",
  minutes: "float",
  samples: "int",
  frames: "int",
  pixels: "int",
  meters: "float",
  centimeters: "float",
  millimeters: "float",
  inches: "float",
  points: "float",
};

/** The number type of a timeline's axis: its own, or its unit's default. */
export function numberTypeOf(timeline: { unit: TimeUnit; number_type?: NumberType }): NumberType {
  return timeline.number_type ?? UNIT_NUMBER_TYPES[timeline.unit];
}
