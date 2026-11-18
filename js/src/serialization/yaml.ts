/**
 * The YAML reader. A character outside YAML 1.2's printable set, which `yaml`
 * reads, is refused first, where it stands. The `yaml` library then parses
 * the text under the YAML 1.2 core schema, integers as `bigint`s, and refuses
 * a repeated key; one walk over its node tree refuses what lies outside the
 * format and builds the lossless value: an integer exact (a `bigint` beyond
 * the safe range), a float a float (a `JsonFloat` where it is integral), an
 * object's keys in their written order. Every refusal is a `YamlSyntaxError`
 * at the offending token: an alias at its `*`, an anchor or a tag at the
 * node's first property, every other fault of a node at its first character.
 *
 * The first fault in document order is the one refused: the walk checks
 * each node as it reaches it, a key before its value (an alias, an anchor, a
 * tag, a key being a string, its depth, then its value), and the first fault
 * the walk finds is refused unless a problem of the parser lies at or before
 * it. A text whose value would be deeper than 256 is refused at the first
 * collection at depth 257. The parser composes collections recursively and,
 * where its stack runs out, reports it and stops composing; that happens
 * hundreds of levels deeper than 257, so the composed tree still holds the
 * collection the refusal names, and that report never outranks a fault the
 * walk finds.
 */

import {
  type CST,
  isAlias,
  isMap,
  isScalar,
  type Node,
  type Pair,
  Parser,
  parseDocument,
  type Scalar,
  type YAMLError,
  type YAMLMap,
  type YAMLSeq,
} from "yaml";
import { type Json, JsonFloat, type Lossless, objectFrom } from "../json/value.js";
import { DEPTH_LIMIT, TOO_DEEP, YamlSyntaxError } from "./errors.js";
import { removeByteOrderMark } from "./json.js";
import { hasLoneSurrogate } from "./text.js";

const SAFE = BigInt(Number.MAX_SAFE_INTEGER);

/** A character outside YAML 1.2's printable set (`c-printable`), a lone surrogate among them. */
const SPECIAL = /[^\t\n\r\x20-\x7E\x85\xA0-퟿-�\u{10000}-\u{10FFFF}]/u;

/**
 * Read a YAML text, from its first character, as `loads` reads it. An empty
 * text, or one of comments only, reads as `null`.
 *
 * @throws {YamlSyntaxError} at a character outside YAML's printable set,
 * before anything else, else at the first fault in document order: a problem
 * of the parser (more than one document, an unknown tag and a repeated key
 * among them), collections nested deeper than 256 levels (never outranked by
 * the problem that the parser's stack ran out), an alias, an anchor, a tag, a
 * key that is not a string, a float that is not finite (`.inf`, `.nan` and a
 * literal that rounds to an infinity) and a string or key with a lone
 * surrogate.
 */
export function readYaml(text: string): Lossless<Json> {
  const special = SPECIAL.exec(text);
  if (special !== null) {
    const code = (special[0].codePointAt(0) as number).toString(16).padStart(4, "0");
    throw new YamlSyntaxError(`special characters are not allowed #x${code}`, text, special.index);
  }
  const document = parseDocument(text, {
    schema: "core",
    intAsBigInt: true,
    uniqueKeys: true,
    keepSourceTokens: true,
  });
  let problem: YAMLError | undefined;
  for (const found of [...document.errors, ...document.warnings]) {
    if (problem === undefined || found.pos[0] < problem.pos[0]) problem = found;
  }
  const parserError = (): YamlSyntaxError | undefined =>
    problem &&
    new YamlSyntaxError(`${problem.code}: ${reasonOf(problem.message)}`, text, problem.pos[0]);

  let value: Lossless<Json>;
  try {
    value = walk(document.contents, text);
  } catch (error) {
    if (
      error instanceof YamlSyntaxError &&
      problem !== undefined &&
      problem.code !== "RESOURCE_EXHAUSTION" &&
      problem.pos[0] <= error.offset
    ) {
      throw parserError();
    }
    throw error;
  }
  const refused = parserError();
  if (refused !== undefined) throw refused;
  return value;
}

/** A node of the format's data model: a mapping, a sequence or a scalar. */
type DataNode = YAMLMap | YAMLSeq | Scalar;

/**
 * Build the lossless value of a composed tree, refusing its first fault in
 * document order with a `YamlSyntaxError`.
 */
function walk(contents: unknown, text: string): Lossless<Json> {
  const fail = (reason: string, offset: number): never => {
    throw new YamlSyntaxError(reason, text, offset);
  };
  const startOf = (node: Node): number => (node.range as [number, number, number])[0];

  let written: WrittenProps | undefined;
  /** Where a node's first property, its anchor or its tag, is written; the node has one. */
  const propsOf = (node: Node): number => {
    written ??= writtenProps(text);
    const token = node.srcToken;
    const found = token && written.before.get(`${token.type}@${token.offset}`);
    if (found !== undefined) return found;
    // An empty node has no token: its properties are the last written before it.
    let index = written.all.length - 1;
    while ((written.all[index] as number) >= startOf(node)) index--;
    return written.all[index] as number;
  };

  /** Refuse a node holding an anchor or a tag, at its first property. */
  const checkProps = (node: DataNode): void => {
    if (node.anchor !== undefined) fail("an anchor", propsOf(node));
    if (node.tag !== undefined) fail("a tag", propsOf(node));
  };

  const string = (value: string, node: Node): string =>
    hasLoneSurrogate(value) ? fail("a string holds a lone surrogate", startOf(node)) : value;

  // Under the core schema a scalar without a tag is null, a boolean, a
  // string, an integer (a `bigint`) or a float (a `number`).
  const scalar = (node: Scalar): unknown => {
    const value = node.value as null | boolean | string | bigint | number;
    if (typeof value === "string") return string(value, node);
    if (typeof value === "bigint") return value >= -SAFE && value <= SAFE ? Number(value) : value;
    if (typeof value !== "number") return value;
    if (!Number.isFinite(value))
      return fail(`the float ${node.source} is not finite`, startOf(node));
    return Number.isInteger(value) ? new JsonFloat(value) : value;
  };

  /**
   * A node's value where it is a scalar, else a frame to fill with its
   * items; `depth` is the depth the node stands at, 1 for the root.
   */
  const visit = (item: unknown, depth: number): { value: unknown } | Frame => {
    if (item === null || item === undefined) return { value: null };
    if (isAlias(item)) return fail("an alias", startOf(item));
    const node = item as DataNode;
    checkProps(node);
    if (isScalar(node)) return { value: scalar(node) };
    if (depth > DEPTH_LIMIT) return fail(TOO_DEEP, startOf(node));
    return { node, keys: [], values: [] };
  };

  const keyOf = (pair: Pair, map: YAMLMap): string => {
    const key = pair.key as DataNode | null;
    if (isAlias(key)) return fail("an alias", startOf(key));
    if (key !== null) checkProps(key);
    if (!isScalar(key) || typeof key.value !== "string") {
      return fail("a key that is not a string", startOf(key ?? map));
    }
    return string(key.value, key);
  };

  // The walk keeps its own stack, so a text nested as deeply as `yaml`
  // composes it is read without exhausting the call stack. It visits the
  // nodes in document order, a key before its value, and a value's items
  // before the next key, so the first refusal is the first in the text.
  const root = visit(contents, 1);
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
    const visited = visit(item, stack.length + 1);
    if ("node" in visited) stack.push(visited);
    else values.push(visited.value);
  }
}

/** A mapping or a sequence being read: the keys and values of its items read so far. */
interface Frame {
  readonly node: YAMLMap | YAMLSeq;
  readonly keys: string[];
  readonly values: unknown[];
}

/**
 * Where the first property of each node holding one is written, as an
 * offset: by the type and offset of the token the properties stand before,
 * and all of them in the order they are written.
 */
interface WrittenProps {
  readonly before: ReadonlyMap<string, number>;
  readonly all: readonly number[];
}

/**
 * The properties of a text, from its concrete syntax tree, which `yaml`
 * keeps in the tokens before a node, not on the node: in a document's start
 * for its root, in an item's start for its key (or for its value where it
 * has no key) and in an item's separator for its value. A block mapping's
 * token and its first key's stand at the same offset, so a token is named by
 * its type and its offset.
 */
function writtenProps(text: string): WrittenProps {
  const before = new Map<string, number>();
  const all: number[] = [];
  const add = (
    tokens: readonly CST.SourceToken[] | undefined,
    target: CST.Token | null | undefined,
  ) => {
    const first = tokens?.find((token) => token.type === "anchor" || token.type === "tag");
    if (first === undefined) return;
    all.push(first.offset);
    if (target) before.set(`${target.type}@${target.offset}`, first.offset);
  };
  const stack: CST.Token[] = [...new Parser().parse(text)];
  for (let token = stack.pop(); token !== undefined; token = stack.pop()) {
    if (token.type === "document") {
      add(token.start, token.value);
      if (token.value) stack.push(token.value);
    } else if (
      token.type === "block-map" ||
      token.type === "block-seq" ||
      token.type === "flow-collection"
    ) {
      for (const item of token.items as CST.CollectionItem[]) {
        if (item.sep) {
          add(item.start, item.key);
          add(item.sep, item.value);
        } else {
          add(item.start, item.value ?? item.key);
        }
        if (item.key) stack.push(item.key);
        if (item.value) stack.push(item.value);
      }
    }
  }
  return { before, all: all.sort((left, right) => left - right) };
}

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
