/**
 * The lossless JSON reader. It reads any JSON text without losing a
 * number's written kind or an object's key order (see `../json/value.ts`),
 * and refuses, with a `JsonSyntaxError` naming where, a text that is not one
 * JSON value, a key that repeats in its object and a lone surrogate in a
 * string or a key, whether it stands as itself or is written as an escape.
 */

import { type Json, JsonFloat, type JsonNumber, type Lossless, objectFrom } from "../json/value.js";
import { JsonSyntaxError, positionOf } from "./errors.js";
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
 * Read a JSON text, from its first character, as `loads` reads it.
 *
 * @throws {JsonSyntaxError} if the text is not one JSON value, a key repeats
 * in its object, or a string or key holds a lone surrogate.
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

  const string = (): string => {
    const start = index;
    index++;
    let result = "";
    let high = -1;
    for (;;) {
      if (index >= text.length) fail("unterminated string");
      const at = index;
      let unit = text.charCodeAt(index);
      if (unit === 0x22) break;
      if (unit < 0x20) fail("malformed string", start);
      if (unit === 0x5c) {
        const escaped = text[index + 1] as string;
        if (escaped === "u") {
          const digits = text.slice(index + 2, index + 6);
          if (!/^[0-9A-Fa-f]{4}$/.test(digits)) fail("malformed string", start);
          unit = Number.parseInt(digits, 16);
          index += 6;
        } else {
          const character = ESCAPES[escaped];
          if (character === undefined) fail("malformed string", start);
          unit = (character as string).charCodeAt(0);
          index += 2;
        }
      } else {
        index++;
      }
      if (high >= 0) {
        if (!isLow(unit)) fail("lone surrogate", high);
        high = -1;
      } else if (isHigh(unit)) {
        high = at;
      } else if (isLow(unit)) {
        fail("lone surrogate", at);
      }
      result += String.fromCharCode(unit);
    }
    if (high >= 0) fail("lone surrogate", high);
    index++;
    return result;
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

  const value = (): unknown => {
    space();
    const character = text[index];
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
        entries.push([key, value()]);
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
        items.push(value());
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

  const result = value();
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
 * in its object, or a string or key holds a lone surrogate.
 * @throws {RangeError} if a float rounds to an infinity.
 */
export function parseJson(text: string): Lossless<Json> {
  return readJson(removeByteOrderMark(text));
}
