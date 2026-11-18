/**
 * The YAML reader. The `yaml` library parses the text under the YAML 1.2
 * core schema, integers as `bigint`s, and refuses a repeated key; one walk
 * over its node tree then refuses what lies outside the format's data model
 * and builds the lossless value: an integer exact (a `bigint` beyond the safe
 * range), a float a float (a `JsonFloat` where it is integral), an object's
 * keys in their written order. Every refusal is a `YamlSyntaxError` at the
 * offending node.
 *
 * A text whose value would be deeper than 256 is refused at the first
 * collection at depth 257 in document order. The parser composes collections
 * recursively and, where its stack runs out, reports it and stops composing;
 * that happens hundreds of levels deeper than 257, so the composed tree still
 * holds the collection the refusal names, and the place depends on the text
 * alone.
 */

import {
  isAlias,
  isMap,
  isScalar,
  isSeq,
  type Node,
  type Pair,
  parseDocument,
  type Scalar,
  type YAMLMap,
  type YAMLSeq,
} from "yaml";
import { type Json, JsonFloat, type Lossless, objectFrom } from "../json/value.js";
import { DEPTH_LIMIT, TOO_DEEP, YamlSyntaxError } from "./errors.js";
import { removeByteOrderMark } from "./json.js";
import { hasLoneSurrogate } from "./text.js";

const SAFE = BigInt(Number.MAX_SAFE_INTEGER);

/**
 * Read a YAML text, from its first character, as `loads` reads it. An empty
 * text, or one of comments only, reads as `null`.
 *
 * @throws {YamlSyntaxError} for a text the parser refuses (more than one
 * document, an unknown tag and a repeated key among them), collections
 * nested deeper than 256 levels (before a problem of the parser at a later
 * place, and before the problem that its stack ran out), an anchor or an
 * alias, a key that is not a string, a value outside the JSON data model, a
 * float that is not finite (`.inf`, `.nan` and a literal that rounds to an
 * infinity) and a string or key with a lone surrogate.
 */
export function readYaml(text: string): Lossless<Json> {
  const document = parseDocument(text, { schema: "core", intAsBigInt: true, uniqueKeys: true });
  const problem = document.errors[0] ?? document.warnings[0];
  const deep = tooDeep(document.contents);
  if (
    deep !== undefined &&
    (problem === undefined || problem.code === "RESOURCE_EXHAUSTION" || problem.pos[0] >= deep)
  ) {
    throw new YamlSyntaxError(TOO_DEEP, text, deep);
  }
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

  const scalar = (node: Scalar): unknown => {
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

  /** A node's value where it is a scalar, else a frame to fill with its items. */
  const visit = (node: unknown, parent: Node | null): { value: unknown } | Frame => {
    if (node === null || node === undefined) return { value: null };
    if (isAlias(node)) return fail("an alias", node);
    if (!isMap(node) && !isSeq(node) && !isScalar(node)) {
      return fail("a value outside the JSON data model", parent);
    }
    if (node.anchor !== undefined) return fail("an anchor", node);
    if (isScalar(node)) return { value: scalar(node) };
    if (!COLLECTION_TAGS.has(node.tag)) return fail("a value outside the JSON data model", node);
    return { node, keys: [], values: [] };
  };

  const keyOf = (pair: Pair, map: YAMLMap): string => {
    const { key } = pair;
    if (isAlias(key)) return fail("an alias", key);
    if (!isScalar(key) || typeof key.value !== "string") {
      return fail(
        "a key that is not a string",
        isMap(key) || isSeq(key) || isScalar(key) ? key : map,
      );
    }
    if (key.anchor !== undefined) return fail("an anchor", key);
    return string(key.value, key);
  };

  // The walk keeps its own stack, so a text nested as deeply as `yaml`
  // composes it is read without exhausting the call stack. It visits the
  // nodes in document order, a key before its value, and a value's items
  // before the next key, so the first refusal is the first in the text.
  const root = visit(document.contents, null);
  if (!("node" in root)) return root.value as Lossless<Json>;
  const stack: Frame[] = [root];
  for (;;) {
    const frame = stack.at(-1) as Frame;
    const { node, keys, values } = frame;
    const index = values.length;
    if (index === node.items.length) {
      stack.pop();
      const value = isMap(node)
        ? objectFrom(keys.map((name, at) => [name, values[at]] as const))
        : values;
      const holder = stack.at(-1);
      if (holder === undefined) return value as Lossless<Json>;
      holder.values.push(value);
      continue;
    }
    let item: unknown;
    if (isMap(node)) {
      const pair = node.items[index] as Pair;
      keys.push(keyOf(pair, node));
      item = pair.value;
    } else {
      item = node.items[index];
    }
    const visited = visit(item, node);
    if ("node" in visited) stack.push(visited);
    else values.push(visited.value);
  }
}

/**
 * The offset of the first collection at depth 257, in document order, a key
 * before its value; `undefined` where there is none, or where an anchor or an
 * alias comes first, which the walk refuses. The walk keeps its own stack and
 * goes no deeper than 257.
 */
function tooDeep(root: unknown): number | undefined {
  const pending: [unknown, number][] = [[root, 1]];
  for (let next = pending.pop(); next !== undefined; next = pending.pop()) {
    const [node, depth] = next;
    if (isAlias(node)) return undefined;
    if (!isMap(node) && !isSeq(node)) {
      if (isScalar(node) && node.anchor !== undefined) return undefined;
      continue;
    }
    if (node.anchor !== undefined) return undefined;
    if (depth > DEPTH_LIMIT) return node.range?.[0] ?? 0;
    const members: unknown[] = isMap(node)
      ? node.items.flatMap((pair) => [pair.key, pair.value])
      : node.items;
    for (let index = members.length - 1; index >= 0; index--) {
      pending.push([members[index], depth + 1]);
    }
  }
  return undefined;
}

/** A mapping or a sequence being read: the keys and values of its items read so far. */
interface Frame {
  readonly node: YAMLMap | YAMLSeq;
  readonly keys: string[];
  readonly values: unknown[];
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
