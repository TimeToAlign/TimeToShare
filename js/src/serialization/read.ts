/**
 * The one reader of every serialization. After one U+FEFF at position 0 is
 * removed, a text is read as JSON when its first character other than a
 * space, a tab, a line feed or a carriage return is `{` or `[`, or when it is
 * a JSON text, and as YAML otherwise.
 */

import type { Json, Lossless } from "../json/value.js";
import { readJson, readsAsJson, removeByteOrderMark } from "./json.js";
import { dumps, type Serialization } from "./write.js";
import { readYaml } from "./yaml.js";

/**
 * Read a text in any serialization, JSON or YAML, after removing one U+FEFF
 * at position 0, without losing a number or key order and without
 * validating.
 *
 * @throws {JsonSyntaxError} for a text read as JSON that the reading rules refuse.
 * @throws {YamlSyntaxError} for a text read as YAML that the reading rules refuse.
 * @throws {RangeError} for a finite float literal that rounds to an infinity.
 */
export function loads(text: string): Lossless<Json> {
  const body = removeByteOrderMark(text);
  return readsAsJson(body) ? readJson(body) : readYaml(body);
}

/**
 * Name a text's serialization without validating it: `"jcs"` when it is
 * read as JSON and is byte for byte the RFC 8785 JSON of its value, `"json"`
 * for every other text read as JSON (one that cannot be read, one whose value
 * the RFC 8785 writer refuses, and one after a byte order mark included), and
 * `"yaml"` for every other text. Never throws.
 */
export function serializationOf(text: string): Serialization {
  const body = removeByteOrderMark(text);
  if (!readsAsJson(body)) return "yaml";
  if (body !== text) return "json";
  try {
    return dumps(readJson(body), { serialization: "jcs" }) === body ? "jcs" : "json";
  } catch {
    return "json";
  }
}
