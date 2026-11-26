import type { NumberType, TimeUnit } from "../generated/types.js";
import { isJsonObject, JsonFloat, type JsonObject } from "../json/value.js";
import { exact, exactNumber, jsonInteger, type Rational } from "../numbers/exact.js";
import { spell } from "../serialization/text.js";
import {
  axesById,
  elisionsOf,
  entries,
  jsonPointer,
  numberTypeOf,
  type PathSegment,
  SchemaValidationError,
  text,
  timelinesById,
  timestampsOf,
} from "./diagnostics.js";

const ARTICLES: Readonly<Record<NumberType, string>> = {
  int: "an int",
  float: "a float",
  fraction: "a fraction",
};

function writtenAs(value: unknown): NumberType {
  if (Array.isArray(value)) return "fraction";
  return typeof value === "bigint" || (typeof value === "number" && Number.isInteger(value))
    ? "int"
    : "float";
}

function represents(value: unknown, numberType: NumberType): boolean {
  if (numberType === "fraction") return Array.isArray(value);
  if (Array.isArray(value)) return false;
  if (numberType === "float")
    return writtenAs(value) !== "int" || rewritten(value, "float") !== null;
  return jsonInteger(value) !== null;
}

/** Spell an exact rewriting in an axis number type, or return `null`. */
export function rewritten(value: unknown, numberType: NumberType): string | null {
  const exactValue = exact(value);
  if (numberType === "fraction") {
    return `[${exactValue.numerator}, ${exactValue.denominator}]`;
  }
  if (numberType === "int") {
    return exactValue.denominator === 1n ? String(exactValue.numerator) : null;
  }
  const double = Number(exactValue.numerator) / Number(exactValue.denominator);
  if (!Number.isFinite(double)) return null;
  const back = exactNumber(double) as Rational;
  if (back.numerator !== exactValue.numerator || back.denominator !== exactValue.denominator) {
    return null;
  }
  return spell(Number.isInteger(double) ? new JsonFloat(double) : double);
}

/** The representation problem of `owner[key]`, if any, naming the element `of` (by default the owner's `id`). */
function* representationProblem(
  key: string,
  owner: JsonObject,
  path: readonly PathSegment[],
  numberType: NumberType,
  of: string = text(owner, "id"),
): Generator<SchemaValidationError> {
  const value = owner[key];
  if (value === undefined || value === null || represents(value, numberType)) return;
  const fix = rewritten(value, numberType) ?? ARTICLES[numberType];
  yield new SchemaValidationError(
    "representation",
    [...path, key],
    `${key} ${spell(value)} of '${of}' is ${ARTICLES[writtenAs(value)]} on ${ARTICLES[numberType]} axis: write ${fix}`,
  );
}

function* timelineRepresentation(
  timeline: JsonObject,
  path: readonly PathSegment[],
  offsetType: NumberType | null,
): Generator<SchemaValidationError> {
  const own = numberTypeOf(timeline as { unit: TimeUnit; number_type?: NumberType });
  yield* representationProblem("offset", timeline, path, offsetType ?? own);
  yield* representationProblem("length", timeline, path, own);
  for (const [index, region] of entries(timeline, "regions").entries()) {
    for (const key of ["start", "end"]) {
      yield* representationProblem(key, region, [...path, "regions", index], own);
    }
  }
  for (const [index, entry] of entries(timeline, "flow_control").entries()) {
    const at = [...path, "flow_control", index];
    const id = text(entry, "id");
    yield* representationProblem("coordinate", entry, at, own);
    const after = isJsonObject(entry.ends) ? entry.ends.after : undefined;
    if (isJsonObject(after)) {
      yield* representationProblem("by", after, [...at, "ends", "after"], own, id);
    }
    for (const [number, destination] of entries(entry, "targets").entries()) {
      const here = [...at, "targets", number];
      yield* representationProblem("by", destination, here, own, id);
      if (isJsonObject(destination.after)) {
        yield* representationProblem("by", destination.after, [...here, "after"], own, id);
      }
    }
  }
  for (const [index, child] of entries(timeline, "children").entries()) {
    yield* timelineRepresentation(child, [...path, "children", index], own);
  }
}

/**
 * Yield own-axis representation violations in manifest order: the timelines
 * first (a flow-control element's coordinate, then the `by` of its `ends` and
 * of each destination and its `after`), then the coordinate of every named
 * timestamp on a timeline of the manifest or a virtual timeline, then the `start`, `end` and width
 * `span` of every elision on one, then the gaps of every FlowMap of one, each
 * read as that timeline's number type, then the `length` of every virtual
 * timeline, read as its own.
 */
export function* representationProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  for (const [index, root] of entries(manifest, "timelines").entries()) {
    yield* timelineRepresentation(root, ["timelines", index], null);
  }
  const timelines = timelinesById(manifest);
  const axes = axesById(manifest);
  for (const [index, timestamp] of timestampsOf(manifest).entries()) {
    const timeline = axes.get(text(timestamp, "timeline"));
    if (timeline === undefined) continue;
    yield* representationProblem(
      "coordinate",
      timestamp,
      ["graphical", "timestamps", index],
      numberTypeOf(timeline as { unit: TimeUnit; number_type?: NumberType }),
    );
  }
  for (const [index, elision] of elisionsOf(manifest).entries()) {
    const timeline = timelines.get(text(elision, "timeline"));
    if (timeline === undefined) continue;
    const path = ["graphical", "elisions", index];
    const numberType = numberTypeOf(timeline as { unit: TimeUnit; number_type?: NumberType });
    for (const key of ["start", "end"]) {
      yield* representationProblem(key, elision, path, numberType);
    }
    const { width } = elision;
    if (isJsonObject(width)) {
      yield* representationProblem(
        "span",
        width,
        [...path, "width"],
        numberType,
        text(elision, "id"),
      );
    }
  }
  for (const [index, flowMap] of entries(manifest, "flow_maps").entries()) {
    const timeline = timelines.get(text(flowMap, "timeline"));
    if (timeline === undefined) continue;
    const numberType = numberTypeOf(timeline as { unit: TimeUnit; number_type?: NumberType });
    for (const [number, chunk] of (flowMap.chunks as unknown[]).entries()) {
      if (!isJsonObject(chunk)) continue;
      yield* representationProblem(
        "gap",
        chunk,
        ["flow_maps", index, "chunks", number],
        numberType,
        text(flowMap, "id"),
      );
    }
  }
  for (const [index, virtual] of entries(manifest, "virtual_timelines").entries()) {
    yield* representationProblem(
      "length",
      virtual,
      ["virtual_timelines", index],
      virtual.number_type as NumberType,
    );
  }
}

/**
 * Yield non-finite numeric leaves before any value is adapted for Ajv.
 *
 * Only a plain number can be one: a `JsonFloat` refuses a non-finite value
 * when constructed. A leaf is named by its key and the id of the nearest
 * object above it that has one, or else by its JSON pointer.
 */
export function* finiteNumberProblems(
  value: unknown,
  path: readonly PathSegment[] = [],
  ownerId: string | null = null,
  ownerKey: string | null = null,
): Generator<SchemaValidationError> {
  if (typeof value === "number" && !Number.isFinite(value)) {
    const detail =
      ownerId !== null && ownerKey !== null
        ? `${ownerKey} of '${ownerId}' is not a finite number`
        : `${jsonPointer(path)} is not a finite number`;
    yield new SchemaValidationError("finite_number", path, detail);
    return;
  }
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      yield* finiteNumberProblems(item, [...path, index], ownerId, ownerKey);
    }
    return;
  }
  if (!isJsonObject(value)) return;
  const id = typeof value.id === "string" ? value.id : ownerId;
  for (const [key, item] of Object.entries(value)) {
    yield* finiteNumberProblems(item, [...path, key], id, key);
  }
}
