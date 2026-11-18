/**
 * The spelling of scalars that every serialization shares: integers in
 * decimal digits, floats by the README's float algorithm (the digits of
 * ECMAScript's `Number::toString`, laid out as Python's `repr` lays them out,
 * a mantissa in exponent form always with a fractional digit), strings
 * double-quoted in JSON and plain or double-quoted in canonical YAML. RFC
 * 8785 JSON spells numbers its own way (`jcsNumber`). `compactJson` and
 * `spell` are the utilities built on the shared spelling.
 */

import { isJsonObject, JsonFloat, keysOf } from "../json/value.js";

/** Compare strings by Unicode code point, not by UTF-16 code unit. */
export function compareCodePoints(left: string, right: string): number {
  let i = 0;
  let j = 0;
  while (i < left.length && j < right.length) {
    const a = left.codePointAt(i) as number;
    const b = right.codePointAt(j) as number;
    if (a !== b) return a < b ? -1 : 1;
    i += a > 0xffff ? 2 : 1;
    j += b > 0xffff ? 2 : 1;
  }
  if (i < left.length) return 1;
  return j < right.length ? -1 : 0;
}

/** Compare strings by UTF-16 code unit, as RFC 8785 sorts keys. */
export function compareCodeUnits(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

const LONE_SURROGATE = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;

/** Whether a string holds a code point from U+D800 to U+DFFF that is not part of a pair. */
export function hasLoneSurrogate(value: string): boolean {
  return LONE_SURROGATE.test(value);
}

/**
 * A number as the serializations tell it apart: an integer, exact at any
 * size, or a finite float. A `bigint` and an integral plain `number` are
 * integers (`-0` is the integer 0); a `JsonFloat` and a plain number with a
 * fractional part are floats.
 */
export type Numeric = { readonly integer: bigint } | { readonly float: number };

/** The kind and value of a JSON number, or `null` for any other value. */
export function numericOf(value: unknown): Numeric | null {
  if (typeof value === "bigint") return { integer: value };
  if (value instanceof JsonFloat) return { float: value.value };
  if (typeof value !== "number") return null;
  if (!Number.isFinite(value)) throw new RangeError(`${value} is not a JSON number`);
  return Number.isInteger(value) ? { integer: BigInt(value) } : { float: value };
}

/**
 * The shortest decimal digits d1 … dn (d1 not 0, no trailing zero) and the
 * exponent k with d1.d2…dn × 10^k reading back as the positive finite
 * double `value`, as ECMAScript's `Number::toString` chooses them.
 */
function digitsOf(value: number): [string, number] {
  const [mantissa = "", exponent = "0"] = String(value).split("e");
  const [whole = "", fraction = ""] = mantissa.split(".");
  let digits = whole + fraction;
  let k = whole.length - 1 + Number(exponent);
  const leading = (digits.match(/^0*/) as RegExpMatchArray)[0].length;
  digits = digits.slice(leading).replace(/0+$/, "");
  k -= leading;
  return [digits, k];
}

/**
 * Spell a finite float by the shared algorithm: fixed notation with at
 * least one fractional digit for −4 ≤ k ≤ 15, else a mantissa with a
 * fractional digit and an exponent of at least two digits (`1.0e-05`).
 *
 * @throws {RangeError} for a NaN or an infinity.
 */
export function floatText(value: number): string {
  if (!Number.isFinite(value)) throw new RangeError(`${value} is not a JSON number`);
  if (value === 0) return Object.is(value, -0) ? "-0.0" : "0.0";
  const sign = value < 0 ? "-" : "";
  const [digits, k] = digitsOf(Math.abs(value));
  if (k >= -4 && k <= 15) {
    if (k < 0) return `${sign}0.${"0".repeat(-k - 1)}${digits}`;
    const whole = digits.slice(0, k + 1).padEnd(k + 1, "0");
    return `${sign}${whole}.${digits.slice(k + 1) || "0"}`;
  }
  const magnitude = String(Math.abs(k)).padStart(2, "0");
  return `${sign}${digits[0]}.${digits.slice(1) || "0"}e${k < 0 ? "-" : "+"}${magnitude}`;
}

/** Spell a number as canonical YAML and pretty JSON spell it. */
export function numberText(numeric: Numeric): string {
  return "integer" in numeric ? numeric.integer.toString() : floatText(numeric.float);
}

const SAFE = 2n ** 53n - 1n;

/**
 * Spell a number as RFC 8785 JSON spells it: an integer within ±(2^53 − 1)
 * in decimal digits, a float as ECMAScript's `Number::toString` does.
 *
 * @throws {RangeError} for an integer beyond ±(2^53 − 1), and for an integral
 * float of magnitude from 2^53 up to but excluding 10^21, which RFC 8785 JSON
 * would spell as such an integer.
 */
export function jcsNumber(numeric: Numeric): string {
  if ("integer" in numeric) {
    const { integer } = numeric;
    if (integer > SAFE || integer < -SAFE) {
      throw new RangeError(`RFC 8785 JSON cannot hold the integer ${integer}`);
    }
    return integer.toString();
  }
  const { float } = numeric;
  const magnitude = Math.abs(float);
  if (Number.isInteger(float) && magnitude >= 2 ** 53 && magnitude < 1e21) {
    throw new RangeError(`RFC 8785 JSON cannot hold the integral float ${floatText(float)}`);
  }
  return String(float);
}

const SHORT_ESCAPES: ReadonlyMap<number, string> = new Map([
  [0x22, '\\"'],
  [0x5c, "\\\\"],
  [0x08, "\\b"],
  [0x09, "\\t"],
  [0x0a, "\\n"],
  [0x0c, "\\f"],
  [0x0d, "\\r"],
]);

/** Double-quote a string, escaping each code unit `escaped` names as `\u` and four digits. */
function quote(value: string, escaped: (unit: number) => boolean): string {
  if (hasLoneSurrogate(value)) {
    throw new RangeError("a string holds a lone surrogate, which UTF-8 cannot hold");
  }
  let result = '"';
  let start = 0;
  for (let index = 0; index < value.length; index++) {
    const unit = value.charCodeAt(index);
    const short = SHORT_ESCAPES.get(unit);
    if (short === undefined && !escaped(unit)) continue;
    result += value.slice(start, index);
    result += short ?? `\\u${unit.toString(16).padStart(4, "0")}`;
    start = index + 1;
  }
  return `${result}${value.slice(start)}"`;
}

const jsonEscaped = (unit: number): boolean => unit < 0x20;

const yamlEscaped = (unit: number): boolean =>
  unit < 0x20 ||
  (unit >= 0x7f && unit <= 0x9f) ||
  unit === 0x2028 ||
  unit === 0x2029 ||
  unit === 0xfeff ||
  unit === 0xfffe ||
  unit === 0xffff;

/**
 * A string as JSON writes it, pretty or RFC 8785: double-quoted, `"`, `\`
 * and the C0 controls escaped, every other character as itself.
 *
 * @throws {RangeError} for a string with a lone surrogate.
 */
export function jsonString(value: string): string {
  return quote(value, jsonEscaped);
}

const PLAIN = /^[A-Za-z_][A-Za-z0-9_./-]*$/;
const RESERVED = new Set(["null", "true", "false", "yes", "no", "on", "off", "y", "n"]);

/**
 * A string as canonical YAML writes it: plain where it matches the plain
 * rule and is no reserved word in any case, else double-quoted with the
 * escapes of JSON and every character YAML readers refuse as itself (U+007F
 * to U+009F, U+2028, U+2029, U+FEFF, U+FFFE, U+FFFF) escaped too.
 *
 * @throws {RangeError} for a string with a lone surrogate.
 */
export function yamlString(value: string): string {
  return PLAIN.test(value) && !RESERVED.has(value.toLowerCase())
    ? value
    : quote(value, yamlEscaped);
}

/** The longest key, in UTF-16 code units of its canonical YAML form, that a writer writes. */
export const KEY_LIMIT = 1024;

/**
 * Check a key for every serialization: its canonical YAML form, quotes and
 * escapes included, is at most `KEY_LIMIT` UTF-16 code units long.
 *
 * @throws {RangeError} for a longer key, or one with a lone surrogate.
 */
export function checkKey(key: string): void {
  const length = yamlString(key).length;
  if (length > KEY_LIMIT) {
    throw new RangeError(
      `a key whose canonical YAML form is ${length} UTF-16 code units long exceeds ${KEY_LIMIT}`,
    );
  }
}

/** Whether a value is a scalar: `null`, a boolean, a number or a string. */
export function isScalar(value: unknown): boolean {
  return (
    value === null ||
    typeof value === "boolean" ||
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "bigint" ||
    value instanceof JsonFloat
  );
}

/**
 * Write a value as JSON without whitespace, every object's keys in the
 * order `keys` gives, every number as `spellNumber` spells it.
 *
 * @throws {RangeError} for a non-finite number or a string with a lone surrogate.
 * @throws {TypeError} for a value that is not JSON.
 */
export function compact(
  value: unknown,
  keys: (object: Record<string, unknown>) => string[],
  spellNumber: (numeric: Numeric) => string,
): string {
  if (value === null || typeof value === "boolean") return String(value);
  if (typeof value === "string") return jsonString(value);
  const numeric = numericOf(value);
  if (numeric !== null) return spellNumber(numeric);
  if (Array.isArray(value)) {
    return `[${value.map((item) => compact(item, keys, spellNumber)).join(",")}]`;
  }
  if (isJsonObject(value)) {
    const members = keys(value).map(
      (key) => `${jsonString(key)}:${compact(value[key], keys, spellNumber)}`,
    );
    return `{${members.join(",")}}`;
  }
  throw new TypeError(`not a JSON value: ${String(value)}`);
}

/**
 * The compact JSON text of a value: no whitespace, every object's keys in
 * their own order (the written order for a value read by `loads`), numbers
 * spelled as canonical YAML and pretty JSON spell them, strings as JSON
 * writes them. A utility, not a serialization of the format: `loads` reads
 * it back to an equal value.
 *
 * @throws {RangeError} for a non-finite number or a string with a lone surrogate.
 * @throws {TypeError} for a value that is not JSON.
 */
export function compactJson(value: unknown): string {
  return compact(value, keysOf, numberText);
}

/**
 * The compact JSON text of a value with every object's keys sorted by code
 * point at every depth: no whitespace, numbers spelled as canonical YAML and
 * pretty JSON spell them (an integer apart from a float, `2` apart from
 * `2.0`), strings as JSON writes them. Arrays keep their order, a manifest's
 * included, and an integer beyond 2^53 is written, as RFC 8785 JSON would
 * not. Two values that `loads` reads alike, whatever the order of their
 * keys, give the same text.
 *
 * @throws {RangeError} for a non-finite number or a string with a lone surrogate.
 * @throws {TypeError} for a value that is not JSON.
 */
export function compactSortedJson(value: unknown): string {
  return compact(value, (object) => Object.keys(object).sort(compareCodePoints), numberText);
}

/**
 * Spell a value as a message quotes it: a number as the writers spell it, an
 * array as its items separated by `, ` within brackets (`[32, 1]`), anything
 * else as compact JSON. Python spells numbers and arrays the same way.
 */
export function spell(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(spell).join(", ")}]`;
  if (value === undefined) return "undefined";
  try {
    return compactJson(value);
  } catch {
    return String(value);
  }
}
