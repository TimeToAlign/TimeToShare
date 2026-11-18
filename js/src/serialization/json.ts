/**
 * The lossless JSON reader. It reads any JSON text without losing a
 * number's written kind or an object's key order (see `../json/value.ts`),
 * and refuses, with a `JsonSyntaxError` naming where, a text that is not one
 * JSON value, a key that repeats in its object and a lone surrogate in a
 * string or a key, whether it stands as itself or is written as an escape;
 * a surrogate escape pairs only with an escape, so an escaped high surrogate
 * before a low one standing as itself is two lone surrogates, as in Python.
 * A text holding several faults is refused for the first in document order,
 * at the token that offends.
 */

import { type Json, JsonFloat, type JsonNumber, type Lossless, objectFrom } from "../json/value.js";
import { DEPTH_LIMIT, JsonSyntaxError, positionOf, TOO_DEEP } from "./errors.js";
import { compactJson } from "./text.js";

/** The text without one U+FEFF, a byte order mark, at position 0. */
export function removeByteOrderMark(text: string): string {
  return text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
}

const NUMBER = /-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/y;
const SAFE = BigInt(Number.MAX_SAFE_INTEGER);
const WHITESPACE = " \t\n\r";
const ESCAPES: Readonly<Record<string, string>> = {
  '"': '"',
  "\\": "\\",
  "/": "/",
  b: "\b",
  f: "\f",
  n: "\n",
  r: "\r",
  t: "\t",
};

/**
 * Whether a text is one JSON scalar under the grammar of RFC 8259, white
 * space around it allowed: a string, a number, `true`, `false` or `null`.
 */
const JSON_SCALAR =
  // biome-ignore lint/suspicious/noControlCharactersInRegex: JSON strings exclude the C0 controls.
  /^[ \t\n\r]*(?:"(?:[^"\\\u0000-\u001f]|\\(?:["\\/bfnrt]|u[0-9A-Fa-f]{4}))*"|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)[ \t\n\r]*$/;

/**
 * Whether a text is read as JSON: its first character other than a space, a
 * tab, a line feed or a carriage return is `{` or `[`, or it is a JSON text.
 * A text whose first such character is neither is a JSON text only when it
 * is one scalar.
 */
export function readsAsJson(text: string): boolean {
  let index = 0;
  while (index < text.length && WHITESPACE.includes(text[index] as string)) index++;
  const first = text[index];
  return first === "{" || first === "[" || JSON_SCALAR.test(text);
}

const isHigh = (unit: number): boolean => unit >= 0xd800 && unit <= 0xdbff;
const isLow = (unit: number): boolean => unit >= 0xdc00 && unit <= 0xdfff;

/**
 * Read a JSON text, from its first character, as `loads` reads it. A
 * collection opening at depth 257 is refused at its `{` or `[`, before the
 * reader descends into it, so the reader's recursion never goes deeper than
 * 256 levels.
 *
 * @throws {JsonSyntaxError} if the text is not one JSON value, a key repeats
 * in its object, a string or key holds a lone surrogate, or collections nest
 * deeper than 256 levels.
 * @throws {RangeError} if a float rounds to an infinity.
 */
export function readJson(text: string): Lossless<Json> {
  let index = 0;

  const fail = (reason: string, at = index): never => {
    throw new JsonSyntaxError(reason, text, at);
  };
  const space = (): void => {
    while (index < text.length && WHITESPACE.includes(text[index] as string)) index++;
  };
  const expect = (token: string): void => {
    if (!text.startsWith(token, index)) fail(`expected "${token}"`);
    index += token.length;
  };

  /**
   * The string at `index`, its opening quote. A fault is refused where it
   * stands: an invalid escape at its backslash, a control character where
   * it is, an unterminated string at the end of the text. A high surrogate
   * pairs only with the low surrogate right after it, written the same way;
   * one that does not is lone where it stands, whatever follows it.
   */
  const string = (): string => {
    index++;
    let result = "";
    let high = -1;
    let highViaEscape = false;
    for (;;) {
      const at = index;
      let unit = text.charCodeAt(index);
      const viaEscape = unit === 0x5c;
      let length = 1;
      if (viaEscape) {
        const escaped = text[index + 1] as string;
        if (escaped === "u" && /^[0-9A-Fa-f]{4}$/.test(text.slice(index + 2, index + 6))) {
          unit = Number.parseInt(text.slice(index + 2, index + 6), 16);
          length = 6;
        } else {
          const character = ESCAPES[escaped];
          if (high >= 0) fail("lone surrogate", high);
          if (character === undefined) fail("malformed string");
          unit = (character as string).charCodeAt(0);
          length = 2;
        }
      }
      if (high >= 0) {
        // A surrogate written as an escape pairs only with an escape, and one
        // standing as itself only with one standing as itself, as in Python.
        if (!isLow(unit) || viaEscape !== highViaEscape) fail("lone surrogate", high);
        high = -1;
      } else if (index >= text.length) {
        fail("unterminated string");
      } else if (unit === 0x22 && !viaEscape) {
        index++;
        return result;
      } else if (unit < 0x20 && !viaEscape) {
        fail("malformed string");
      } else if (isHigh(unit)) {
        high = at;
        highViaEscape = viaEscape;
      } else if (isLow(unit)) {
        fail("lone surrogate");
      }
      index += length;
      result += String.fromCharCode(unit);
    }
  };

  const number = (source: string, at: number): JsonNumber => {
    if (/[.eE]/.test(source)) {
      const value = Number(source);
      if (!Number.isFinite(value)) {
        const { line, column } = positionOf(text, at);
        throw new RangeError(
          `${source} rounds to an infinity at line ${line}, column ${column} of the JSON text`,
        );
      }
      return Number.isInteger(value) ? new JsonFloat(value) : value;
    }
    const integer = BigInt(source);
    return integer >= -SAFE && integer <= SAFE ? Number(integer) : integer;
  };

  /** The value at `index`, inside `depth` open collections. */
  const value = (depth: number): unknown => {
    space();
    const character = text[index];
    if ((character === "{" || character === "[") && depth === DEPTH_LIMIT) fail(TOO_DEEP);
    if (character === "{") {
      index++;
      const entries: [string, unknown][] = [];
      const keys = new Set<string>();
      space();
      if (text[index] === "}") {
        index++;
        return objectFrom(entries);
      }
      for (;;) {
        space();
        if (text[index] !== '"') fail("expected a string key");
        const at = index;
        const key = string();
        if (keys.has(key)) fail(`duplicate key ${compactJson(key)}`, at);
        keys.add(key);
        space();
        expect(":");
        entries.push([key, value(depth + 1)]);
        space();
        if (text[index] === ",") {
          index++;
          continue;
        }
        expect("}");
        return objectFrom(entries);
      }
    }
    if (character === "[") {
      index++;
      const items: unknown[] = [];
      space();
      if (text[index] === "]") {
        index++;
        return items;
      }
      for (;;) {
        items.push(value(depth + 1));
        space();
        if (text[index] === ",") {
          index++;
          continue;
        }
        expect("]");
        return items;
      }
    }
    if (character === '"') return string();
    for (const [token, literal] of [
      ["true", true],
      ["false", false],
      ["null", null],
    ] as const) {
      if (text.startsWith(token, index)) {
        index += token.length;
        return literal;
      }
    }
    NUMBER.lastIndex = index;
    const match = NUMBER.exec(text);
    if (match === null) {
      return fail(character === undefined ? "unexpected end" : "unexpected character");
    }
    const at = index;
    index += match[0].length;
    return number(match[0], at);
  };

  const result = value(0);
  space();
  if (index !== text.length) fail("unexpected text after the JSON value");
  return result as Lossless<Json>;
}

/**
 * Read a text as JSON, whatever its first character, after removing one
 * U+FEFF at position 0, without losing a number or the order of a key.
 *
 * Integers keep their exact value (a `bigint` beyond the safe range), floats
 * stay floats (an integral float is a `JsonFloat`), and an object's keys keep
 * their written order even where JavaScript would list array-index keys
 * first. The text `-0` is the integer `0`.
 *
 * @throws {JsonSyntaxError} if the text is not one JSON value, a key repeats
 * in its object, a string or key holds a lone surrogate, or collections nest
 * deeper than 256 levels.
 * @throws {RangeError} if a float rounds to an infinity.
 */
export function parseJson(text: string): Lossless<Json> {
  return readJson(removeByteOrderMark(text));
}
