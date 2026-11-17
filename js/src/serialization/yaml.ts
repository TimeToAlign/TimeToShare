/**
 * The YAML reader. The `yaml` library parses the text under the YAML 1.2
 * core schema, integers as `bigint`s, and refuses a repeated key; one walk
 * over its node tree then refuses what lies outside the format's data model
 * and builds the lossless value: an integer exact (a `bigint` beyond the safe
 * range), a float a float (a `JsonFloat` where it is integral), an object's
 * keys in their written order. Every refusal is a `YamlSyntaxError` at the
 * offending node.
 */

import { isAlias, isMap, isScalar, isSeq, type Node, parseDocument } from "yaml";
import { type Json, JsonFloat, type Lossless, objectFrom } from "../json/value.js";
import { YamlSyntaxError } from "./errors.js";
import { removeByteOrderMark } from "./json.js";
import { hasLoneSurrogate } from "./text.js";

const SAFE = BigInt(Number.MAX_SAFE_INTEGER);

/**
 * Read a YAML text, from its first character, as `loads` reads it. An empty
 * text, or one of comments only, reads as `null`.
 *
 * @throws {YamlSyntaxError} for a text the parser refuses (more than one
 * document, an unknown tag and a repeated key among them), an anchor or an
 * alias, a key that is not a string, a value outside the JSON data model, a
 * float that is not finite (`.inf`, `.nan` and a literal that rounds to an
 * infinity) and a string or key with a lone surrogate.
 */
export function readYaml(text: string): Lossless<Json> {
  const document = parseDocument(text, { schema: "core", intAsBigInt: true, uniqueKeys: true });
  const problem = document.errors[0] ?? document.warnings[0];
  if (problem !== undefined) {
    throw new YamlSyntaxError(
      `${problem.code}: ${reasonOf(problem.message)}`,
      text,
      problem.pos[0],
    );
  }

  const fail = (reason: string, node: { range?: unknown } | null | undefined): never => {
    const range = node?.range;
    const offset = Array.isArray(range) && typeof range[0] === "number" ? range[0] : 0;
    throw new YamlSyntaxError(reason, text, offset);
  };

  const string = (value: string, node: Node): string =>
    hasLoneSurrogate(value) ? fail("a string holds a lone surrogate", node) : value;

  const walk = (node: unknown, parent: Node | null): unknown => {
    if (node === null || node === undefined) return null;
    if (isAlias(node)) return fail("an alias", node);
    if (!isMap(node) && !isSeq(node) && !isScalar(node)) {
      return fail("a value outside the JSON data model", parent);
    }
    if (node.anchor !== undefined) return fail("an anchor", node);
    if ((isMap(node) || isSeq(node)) && !COLLECTION_TAGS.has(node.tag)) {
      return fail("a value outside the JSON data model", node);
    }
    if (isMap(node)) {
      const entries: [string, unknown][] = [];
      for (const pair of node.items) {
        const key = pair.key;
        if (isAlias(key)) return fail("an alias", key);
        if (!isScalar(key) || typeof key.value !== "string") {
          return fail(
            "a key that is not a string",
            isMap(key) || isSeq(key) || isScalar(key) ? key : node,
          );
        }
        if (key.anchor !== undefined) return fail("an anchor", key);
        entries.push([string(key.value, key), walk(pair.value, node)]);
      }
      return objectFrom(entries);
    }
    if (isSeq(node)) return node.items.map((item) => walk(item, node));
    const { value } = node;
    if (value === null || typeof value === "boolean") return value;
    if (typeof value === "string") return string(value, node);
    if (typeof value === "bigint") return value >= -SAFE && value <= SAFE ? Number(value) : value;
    if (typeof value === "number") {
      if (!Number.isFinite(value)) return fail(`the float ${node.source} is not finite`, node);
      return Number.isInteger(value) ? new JsonFloat(value) : value;
    }
    return fail("a value outside the JSON data model", node);
  };

  return walk(document.contents, null) as Lossless<Json>;
}

/** The tags a mapping or a sequence of the JSON data model may carry: none, or the plain ones. */
const COLLECTION_TAGS = new Set([undefined, "tag:yaml.org,2002:map", "tag:yaml.org,2002:seq"]);

/** The first line of a parser's message, without the position it names. */
function reasonOf(message: string): string {
  return (message.split("\n", 1)[0] as string).replace(/ at line \d+, column \d+:?$/, "");
}

/**
 * Read a text as YAML, whatever its first character, after removing one
 * U+FEFF at position 0, without losing a number or the order of a key.
 *
 * @throws {YamlSyntaxError} for a text the reading rules refuse.
 */
export function parseYaml(text: string): Lossless<Json> {
  return readYaml(removeByteOrderMark(text));
}
