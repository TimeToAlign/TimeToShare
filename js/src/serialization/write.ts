/**
 * The writer of the three serializations: canonical YAML, pretty JSON and
 * RFC 8785 JSON, each specified to the byte by the README's
 * "Serializations". A manifest, a value whose `timelines` member is an
 * array, is put in canonical order and its own-axis values respelled before
 * it is written; every other value keeps the order of its arrays and the
 * kind of its numbers. The keys of every object are sorted, by code point in
 * canonical YAML and pretty JSON and by UTF-16 code unit in RFC 8785 JSON.
 */

import { isJsonObject, JsonFloat } from "../json/value.js";
import { canonicalOrder } from "../manifest/order.js";
import { DEPTH_LIMIT } from "./errors.js";
import {
  checkKey,
  compact,
  compareCodePoints,
  compareCodeUnits,
  isScalar,
  jcsNumber,
  jsonString,
  numberText,
  numericOf,
  yamlString,
} from "./text.js";

/** The name of a serialization: canonical YAML, pretty JSON or RFC 8785 JSON. */
export type Serialization = "yaml" | "json" | "jcs";

/** Every serialization's name: canonical YAML, pretty JSON and RFC 8785 JSON. */
export const SERIALIZATIONS: readonly Serialization[] = ["yaml", "json", "jcs"];

/** Whether a value names a serialization, one of `SERIALIZATIONS`. */
export function isSerialization(value: unknown): value is Serialization {
  return (SERIALIZATIONS as readonly unknown[]).includes(value);
}

type JsonRecord = Record<string, unknown>;

/**
 * Check that a value is JSON throughout: `null`, a boolean, a finite number
 * (`number`, `bigint` or `JsonFloat`), a string, an array or a plain object,
 * every string and key free of lone surrogates and every key within the key
 * limit.
 */
function check(value: unknown): void {
  if (value === null || typeof value === "boolean" || typeof value === "bigint") return;
  if (value instanceof JsonFloat) return;
  if (typeof value === "string") {
    jsonString(value);
    return;
  }
  if (typeof value === "number") {
    numericOf(value);
    return;
  }
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index++) check(value[index]);
    return;
  }
  if (typeof value === "object") {
    const prototype = Object.getPrototypeOf(value);
    if (prototype === Object.prototype || prototype === null) {
      for (const [key, member] of Object.entries(value)) {
        checkKey(key);
        check(member);
      }
      return;
    }
  }
  throw new TypeError(`not a JSON value: ${String(value)}`);
}

/** An array, or an object whose prototype is `Object.prototype` or `null`. */
function isCollection(value: unknown): value is unknown[] | JsonRecord {
  if (Array.isArray(value)) return true;
  if (value === null || typeof value !== "object") return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

/**
 * Refuse a value nested deeper than `DEPTH_LIMIT`, walking no deeper than
 * it, so an array or object that holds itself is refused the same way.
 */
function checkDepth(value: unknown): void {
  const pending: [unknown, number][] = [[value, 1]];
  for (let next = pending.pop(); next !== undefined; next = pending.pop()) {
    const [item, depth] = next;
    if (!isCollection(item)) continue;
    if (depth > DEPTH_LIMIT) {
      throw new RangeError(`a value nested deeper than ${DEPTH_LIMIT} levels cannot be written`);
    }
    for (const member of Array.isArray(item) ? item : Object.values(item)) {
      pending.push([member, depth + 1]);
    }
  }
}

const sortedKeys = (object: JsonRecord): string[] => Object.keys(object).sort(compareCodePoints);

/** A non-empty array whose items are all scalars. */
function isScalarSequence(value: unknown): value is unknown[] {
  return Array.isArray(value) && value.length > 0 && value.every(isScalar);
}

function yamlScalar(value: unknown): string {
  if (typeof value === "string") return yamlString(value);
  const numeric = numericOf(value);
  return numeric === null ? String(value) : numberText(numeric);
}

/** The text of a value that stands on its key's or item's line, or `undefined`. */
function yamlInline(value: unknown): string | undefined {
  if (isScalar(value)) return yamlScalar(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    return value.every(isScalar) ? `[${value.map(yamlScalar).join(", ")}]` : undefined;
  }
  return Object.keys(value as JsonRecord).length === 0 ? "{}" : undefined;
}

/** Write an object with members, or a block sequence, at `column`. */
function yamlBlock(value: unknown, column: number, lines: string[]): void {
  const pad = " ".repeat(column);
  const entries: [string, unknown][] = Array.isArray(value)
    ? value.map((item) => [`${pad}-`, item])
    : sortedKeys(value as JsonRecord).map((key) => [
        `${pad}${yamlString(key)}:`,
        (value as JsonRecord)[key],
      ]);
  for (const [lead, item] of entries) {
    const inline = yamlInline(item);
    if (inline === undefined) {
      lines.push(lead);
      yamlBlock(item, column + 2, lines);
    } else {
      lines.push(`${lead} ${inline}`);
    }
  }
}

function yaml(value: unknown): string {
  const inline = Array.isArray(value) && value.length > 0 ? undefined : yamlInline(value);
  if (inline !== undefined) return `${inline}\n`;
  const lines: string[] = [];
  yamlBlock(value, 0, lines);
  return `${lines.join("\n")}\n`;
}

function jsonScalar(value: unknown): string {
  if (typeof value === "string") return jsonString(value);
  const numeric = numericOf(value);
  return numeric === null ? String(value) : numberText(numeric);
}

/** The pretty JSON of a value whose first line stands at `column`. */
function pretty(value: unknown, column: number): string {
  if (isScalar(value)) return jsonScalar(value);
  const pad = " ".repeat(column);
  const inner = " ".repeat(column + 2);
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    if (isScalarSequence(value)) return `[${value.map(jsonScalar).join(", ")}]`;
    const items = value.map((item) => `${inner}${pretty(item, column + 2)}`);
    return `[\n${items.join(",\n")}\n${pad}]`;
  }
  const object = value as JsonRecord;
  const keys = sortedKeys(object);
  if (keys.length === 0) return "{}";
  const members = keys.map(
    (key) => `${inner}${jsonString(key)}: ${pretty(object[key], column + 2)}`,
  );
  return `{\n${members.join(",\n")}\n${pad}}`;
}

/** Options of `dumps`. */
export interface DumpsOptions {
  /** The serialization to write: `"yaml"` (the default), `"json"` or `"jcs"`. */
  readonly serialization?: Serialization;
}

/**
 * Return the text of a manifest, or of any JSON value, in canonical YAML
 * (`"yaml"`, the default), pretty JSON (`"json"`) or RFC 8785 JSON
 * (`"jcs"`), as Python's `dumps` writes it. A value whose `timelines` member
 * is an array is a manifest: it is put in canonical order and its own-axis
 * values respelled first. `dumps` writes the form it is given.
 *
 * Numbers are read as `loads` reads them: a `bigint` and an integral plain
 * `number` are integers (an integral plain number is the integer of its
 * exact value, so `-0` is 0), a `JsonFloat` and a plain number with a
 * fractional part are floats.
 *
 * @throws {RangeError} for a value the serialization refuses: a value
 * nested deeper than 256 levels (checked first), a NaN or an infinity, a
 * string or key with a lone surrogate, a key whose canonical
 * YAML form is longer than 1024 UTF-16 code units, and in `"jcs"` an integer
 * beyond ±(2^53 − 1) or an integral float of magnitude from 2^53 up to but
 * excluding 10^21; and for an unknown serialization.
 * @throws {TypeError} for a manifest that cannot be put in canonical order,
 * and for a value that is not JSON.
 */
export function dumps(value: unknown, options: DumpsOptions = {}): string {
  const serialization = options.serialization ?? "yaml";
  if (!isSerialization(serialization)) {
    throw new RangeError(`unknown serialization ${jsonString(String(serialization))}`);
  }
  checkDepth(value);
  check(value);
  const written =
    isJsonObject(value) && Array.isArray(value.timelines) ? canonicalOrder(value) : value;
  if (serialization === "yaml") return yaml(written);
  if (serialization === "json") return `${pretty(written, 0)}\n`;
  return compact(written, (object) => Object.keys(object).sort(compareCodeUnits), jcsNumber);
}
