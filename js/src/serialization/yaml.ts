/**
 * The YAML reader. The `yaml` library parses the text under the YAML 1.2
 * core schema, integers as `bigint`s, and refuses a repeated key; one walk
 * over its node tree then refuses what lies outside the format's data model
 * and builds the lossless value: an integer exact (a `bigint` beyond the safe
 * range), a float a float (a `JsonFloat` where it is integral), an object's
 * keys in their written order. Every refusal is a `YamlSyntaxError` at the
 * offending token: an anchor at its `&`, every other fault of a node at the
 * node's first character, its tag where it has one. A character outside
 * YAML's printable set, which `yaml` reads, is refused where it stands.
 *
 * The first fault in document order is the one refused: the walk checks
 * each node as it reaches it, a key before its value (its anchor and its
 * tag in the order they are written, a key being a string, its depth, then
 * its value), and the first fault the walk finds is refused unless a
 * problem of the parser lies at or before it.
 * A text whose value would be deeper than 256 is refused at the first
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
  isSeq,
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
const SPECIAL = /[^\t\n\r\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD\u{10000}-\u{10FFFF}]/u;

/**
 * Read a YAML text, from its first character, as `loads` reads it. An empty
 * text, or one of comments only, reads as `null`.
 *
 * @throws {YamlSyntaxError} at the first fault in document order: a character
 * outside YAML's printable set, a problem of the parser (more than one
 * document, an unknown tag and a repeated key among them), collections nested deeper than 256 levels (never outranked by
 * the problem that the parser's stack ran out), an anchor or an alias, a key
 * that is not a string, a value outside the JSON data model, a float that is
 * not finite (`.inf`, `.nan` and a literal that rounds to an infinity) and a
 * string or key with a lone surrogate.
 */
export function readYaml(text: string): Lossless<Json> {
  const special = SPECIAL.exec(text);
  if (special !== null) {
    // A fault before the character is found in the text before it, read
    // with a printable character in its place, which ends no token.
    try {
      readYaml(`${text.slice(0, special.index)}\uFFFD`);
    } catch (error) {
      if (error instanceof YamlSyntaxError && error.offset < special.index) throw error;
    }
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

/**
 * Build the lossless value of a composed tree, refusing its first fault in
 * document order with a `YamlSyntaxError`.
 */
function walk(contents: unknown, text: string): Lossless<Json> {
  const fail = (reason: string, offset: number): never => {
    throw new YamlSyntaxError(reason, text, offset);
  };

  let written: WrittenProps | undefined;
  /** Where a node's anchor and tag are written; the node has one or both. */
  const propsOf = (node: Node): Props => {
    written ??= writtenProps(text);
    const token = node.srcToken;
    const found = token && written.before.get(`${token.type}@${token.offset}`);
    if (found !== undefined) return found;
    // An empty node has no token: its anchor and tag are the last written before it.
    const start = (node.range as [number, number, number])[0];
    let index = written.all.length - 1;
    while ((written.all[index] as Props).start >= start) index--;
    return written.all[index] as Props;
  };
  /** The first character of a node: its anchor or tag where it has one. */
  const startOf = (node: Node): number =>
    node.anchor === undefined && node.tag === undefined
      ? (node.range as [number, number, number])[0]
      : propsOf(node).start;

  const string = (value: string, node: Node): string =>
    hasLoneSurrogate(value) ? fail("a string holds a lone surrogate", startOf(node)) : value;

  /** Refuse a node whose tag names no value of the JSON data model. */
  const checkTag = (node: YAMLMap | YAMLSeq | Scalar): void => {
    const outside = isScalar(node)
      ? !(
          node.value === null ||
          ["boolean", "string", "bigint", "number"].includes(typeof node.value)
        )
      : !COLLECTION_TAGS.has(node.tag);
    if (outside) fail("a value outside the JSON data model", startOf(node));
  };

  /** Refuse a node's anchor and tag, in the order they are written. */
  const checkProps = (node: YAMLMap | YAMLSeq | Scalar): void => {
    if (node.anchor !== undefined) {
      const props = propsOf(node);
      if (props.tag !== undefined && props.tag < (props.anchor as number)) checkTag(node);
      fail("an anchor", props.anchor as number);
    }
    checkTag(node);
  };

  const scalar = (node: Scalar): unknown => {
    const { value } = node;
    if (value === null || typeof value === "boolean") return value;
    if (typeof value === "string") return string(value, node);
    if (typeof value === "bigint") return value >= -SAFE && value <= SAFE ? Number(value) : value;
    const number = value as number;
    if (!Number.isFinite(number)) {
      return fail(`the float ${node.source} is not finite`, startOf(node));
    }
    return Number.isInteger(number) ? new JsonFloat(number) : number;
  };

  /**
   * A node's value where it is a scalar, else a frame to fill with its
   * items; `depth` is the depth the node stands at, 1 for the root.
   */
  const visit = (node: unknown, parent: Node | null, depth: number): { value: unknown } | Frame => {
    if (node === null || node === undefined) return { value: null };
    if (isAlias(node)) return fail("an alias", (node.range as [number, number, number])[0]);
    if (!isMap(node) && !isSeq(node) && !isScalar(node)) {
      return fail("a value outside the JSON data model", parent ? startOf(parent) : 0);
    }
    checkProps(node);
    if (isScalar(node)) return { value: scalar(node) };
    if (depth > DEPTH_LIMIT) return fail(TOO_DEEP, startOf(node));
    return { node, keys: [], values: [] };
  };

  const keyOf = (pair: Pair, map: YAMLMap): string => {
    const { key } = pair;
    if (isAlias(key)) return fail("an alias", (key.range as [number, number, number])[0]);
    const node = isMap(key) || isSeq(key) || isScalar(key) ? key : undefined;
    if (node !== undefined) checkProps(node);
    if (!isScalar(key) || typeof key.value !== "string") {
      return fail("a key that is not a string", startOf(node ?? map));
    }
    return string(key.value, key);
  };

  // The walk keeps its own stack, so a text nested as deeply as `yaml`
  // composes it is read without exhausting the call stack. It visits the
  // nodes in document order, a key before its value, and a value's items
  // before the next key, so the first refusal is the first in the text.
  const root = visit(contents, null, 1);
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
    const visited = visit(item, node, stack.length + 1);
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

/** The tags a mapping or a sequence of the JSON data model may carry: none, or the plain ones. */
const COLLECTION_TAGS = new Set([undefined, "tag:yaml.org,2002:map", "tag:yaml.org,2002:seq"]);

/** Where the anchor and the tag of a node are written, as offsets; the first of them is `start`. */
interface Props {
  readonly start: number;
  readonly anchor: number | undefined;
  readonly tag: number | undefined;
}

/**
 * Every anchor and tag of a text: by the type and offset of the token they
 * are written before, and all of them in the order they are written.
 */
interface WrittenProps {
  readonly before: ReadonlyMap<string, Props>;
  readonly all: readonly Props[];
}

/**
 * The anchors and tags of a text, from its concrete syntax tree, which
 * `yaml` keeps in the tokens before a node, not on the node: in a
 * document's start for its root, in an item's start for its key (or for its
 * value where it has no key) and in an item's separator for its value. A
 * block mapping's token and its first key's stand at the same offset, so a
 * token is named by its type and its offset.
 */
function writtenProps(text: string): WrittenProps {
  const before = new Map<string, Props>();
  const all: Props[] = [];
  const add = (
    tokens: readonly CST.SourceToken[] | undefined,
    target: CST.Token | null | undefined,
  ) => {
    let anchor: number | undefined;
    let tag: number | undefined;
    for (const token of tokens ?? []) {
      if (token.type === "anchor") anchor ??= token.offset;
      else if (token.type === "tag") tag ??= token.offset;
    }
    if (anchor === undefined && tag === undefined) return;
    const props = { start: Math.min(anchor ?? Infinity, tag ?? Infinity), anchor, tag };
    all.push(props);
    if (target) before.set(`${target.type}@${target.offset}`, props);
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
  return { before, all: all.sort((left, right) => left.start - right.start) };
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
