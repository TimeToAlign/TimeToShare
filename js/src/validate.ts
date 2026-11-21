/**
 * The TimeToShare schema validator and its public diagnostics.
 *
 * A manifest is validated in its file form, every ID written `#` followed by
 * the ID: the schema check and the search for unknown keys read the value as
 * given. Every other check reads the manifest with bare IDs (`withBareIds`),
 * the finite rule, which runs first, included: their messages quote IDs bare
 * (`'clt_1'`) and the paths of the checks after the schema name the keys of
 * `graphical.order` bare too.
 */

import { Ajv2020, type ErrorObject, type ValidateFunction } from "ajv/dist/2020.js";
import { schema } from "./generated/schema.js";
import type { LosslessManifest } from "./generated/types.js";
import { FileIdError, lenientlyBareIds, withBareIds } from "./ids.js";
import { isJsonObject, type JsonObject, plain } from "./json/value.js";
import { loads } from "./serialization/read.js";
import { compareCodePoints, spell } from "./serialization/text.js";
import { subjects } from "./statements/statements.js";
import {
  comparePaths,
  duplicateProblem,
  jsonPointer,
  manifestIds,
  type PathSegment,
  SchemaValidationError,
  stringId,
  timestampsOf,
} from "./validate/diagnostics.js";
import { identityProblems as semanticProblems } from "./validate/identity.js";
import { finiteNumberProblems, representationProblems } from "./validate/representation.js";
import { type ManifestWarning, statementRuleProblems, warningsOf } from "./validate/statements.js";
import { matchstampProblems as matchstampRuleProblems } from "./validate/timestamps.js";

export type { JsonObject } from "./json/value.js";
export { childEnds } from "./validate/containment.js";
export {
  entries,
  jsonPointer,
  lengthOf,
  numberTypeOf,
  type PathSegment,
  SchemaValidationError,
  text,
  type ValidationCode,
} from "./validate/diagnostics.js";
export type { ManifestWarning, WarningCode } from "./validate/statements.js";

/** The schema version this package reads and writes, the only one it supports. */
export const SCHEMA_VERSION = "0.2.0";

/** Thrown when a manifest's version marker names a version other than `SCHEMA_VERSION`. */
export class UnsupportedVersionError extends Error {
  readonly version: unknown;

  constructor(version: unknown) {
    super(
      `unsupported TimeToShare version ${spell(version)}; this package reads ${SCHEMA_VERSION} only`,
    );
    this.name = "UnsupportedVersionError";
    this.version = version;
  }
}

/** A key the schema does not declare on the object at `path`. */
export interface UnknownKey {
  readonly path: readonly PathSegment[];
  readonly key: string;
}

const OPTIONS = {
  strict: false,
  allErrors: true,
  allowUnionTypes: true,
  discriminator: true,
} as const;

type Node = Readonly<Record<string, unknown>>;

const BRANCHES = new Set(["oneOf", "anyOf", "if", "then", "else"]);

/** The definitions some `allOf` refers to: shared bases, not objects. */
function allOfBases(node: unknown, found = new Set<string>()): Set<string> {
  if (Array.isArray(node)) {
    for (const item of node) allOfBases(item, found);
  } else if (typeof node === "object" && node !== null) {
    for (const entry of ((node as Node).allOf ?? []) as Node[]) {
      found.add((entry.$ref as string).slice("#/$defs/".length));
    }
    for (const value of Object.values(node)) allOfBases(value, found);
  }
  return found;
}

/** Copy `node` with every declared object outside a branch closed. */
function close(node: unknown, inside: boolean, bases: ReadonlySet<string>): unknown {
  if (Array.isArray(node)) return node.map((item) => close(item, inside, bases));
  if (typeof node !== "object" || node === null) return node;
  const closed: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(node)) {
    if (BRANCHES.has(key)) closed[key] = close(value, true, bases);
    else if (key === "$defs" || key === "properties") {
      closed[key] = Object.fromEntries(
        Object.entries(value as Node).map(([name, member]) => [
          name,
          key === "$defs" && bases.has(name) ? member : close(member, false, bases),
        ]),
      );
    } else if (["default", "const", "enum"].includes(key)) closed[key] = value;
    else closed[key] = close(value, inside, bases);
  }
  const object = node as Node;
  if (!inside && object.type === "object" && "properties" in object) {
    closed.unevaluatedProperties = false;
  }
  return closed;
}

/**
 * The schema with every object closed, the walk that finds unknown keys.
 *
 * The document keeps its objects open; this variant, built in memory only,
 * sets `unevaluatedProperties: false` on every object node with `properties`
 * outside a `oneOf`/`anyOf` branch or an `if`/`then`/`else` arm, except the
 * bases an `allOf` shares, so a key no definition declares fails where it
 * stands.
 */
function closedSchema(document: Node): Node {
  return close(document, false, allOfBases(document)) as Node;
}

const check = new Ajv2020(OPTIONS).compile(schema);
const marking = new Ajv2020(OPTIONS).compile(closedSchema(schema));
const partChecks = new Map<string, ValidateFunction>();

/**
 * The check of one definition, or of one member of it, as the whole document
 * checks it.
 */
function partCheck(definition: string, member?: string): ValidateFunction {
  const key = member === undefined ? definition : `${definition}.${member}`;
  let compiled = partChecks.get(key);
  if (compiled === undefined) {
    const definitions = (schema as Node).$defs as Readonly<Record<string, Node>>;
    const owner = definitions[definition] as Node;
    const declared =
      member === undefined
        ? { $ref: `#/$defs/${definition}` }
        : (owner.properties as Readonly<Record<string, Node>>)[member];
    compiled = new Ajv2020(OPTIONS).compile({ $defs: definitions, ...declared });
    partChecks.set(key, compiled);
  }
  return compiled;
}

/** The first schema problem of `value` against one part of the schema, at `path`. */
function partProblem(
  value: unknown,
  path: readonly PathSegment[],
  definition: string,
  member?: string,
): SchemaValidationError | undefined {
  const instance = plain(value);
  const checkPart = partCheck(definition, member);
  const error = checkPart(instance) ? undefined : select(checkPart.errors ?? []);
  if (error === undefined) return undefined;
  const at = [...path, ...toPath(error.instancePath, instance)];
  return new SchemaValidationError("schema", at, error.message ?? error.keyword);
}

/** Convert an Ajv instance path to segments, typing array indices as numbers. */
function toPath(instancePath: string, value: unknown): PathSegment[] {
  if (instancePath === "") return [];
  const path: PathSegment[] = [];
  let cursor: unknown = value;
  for (const raw of instancePath.slice(1).split("/")) {
    const key = raw.replace(/~1/g, "/").replace(/~0/g, "~");
    if (Array.isArray(cursor)) {
      const index = Number(key);
      path.push(index);
      cursor = cursor[index];
    } else {
      path.push(key);
      cursor = isJsonObject(cursor) ? cursor[key] : undefined;
    }
  }
  return path;
}

/** Pick the deepest diagnostic leaf, with the first reported leaf winning ties. */
function select(errors: readonly ErrorObject[]): ErrorObject | undefined {
  let best: ErrorObject | undefined;
  let bestDepth = -1;
  for (const error of errors) {
    const depth = error.instancePath === "" ? 0 : error.instancePath.split("/").length - 1;
    if (depth > bestDepth) {
      best = error;
      bestDepth = depth;
    }
  }
  return best;
}

function first(problems: Iterable<SchemaValidationError>): SchemaValidationError | undefined {
  return problems[Symbol.iterator]().next().value;
}

/** What a valid manifest is warned of: its unknown keys and its warnings. */
interface Warnings {
  readonly keys: UnknownKey[];
  readonly warnings: ManifestWarning[];
}

/** Check a value through every rule and return its unknown keys and warnings. */
function run(value: unknown): Warnings {
  if (!isJsonObject(value) || !Object.hasOwn(value, "timetoshare")) {
    throw new SchemaValidationError("not_a_manifest", [], "not a TimeToShare manifest");
  }
  if (value.timetoshare !== SCHEMA_VERSION) throw new UnsupportedVersionError(value.timetoshare);

  const finite = first(finiteNumberProblems(lenientlyBareIds(value)));
  if (finite !== undefined) throw finite;

  const instance = plain(value);
  const found: UnknownKey[] = [];
  if (!marking(instance)) {
    // The closed variant refuses undeclared keys; the document decides validity.
    if (!check(instance)) reject(check.errors ?? [], instance);
    for (const error of marking.errors ?? []) {
      if (error.keyword !== "unevaluatedProperties") continue;
      found.push({
        path: toPath(error.instancePath, instance),
        key: String(error.params.unevaluatedProperty),
      });
    }
  }

  const bare = bareManifest(value);
  const representation = first(representationProblems(bare));
  if (representation !== undefined) throw representation;
  const semantic = first(semanticProblems(bare));
  if (semantic !== undefined) throw semantic;
  const statement = first(statementRuleProblems(bare));
  if (statement !== undefined) throw statement;

  const unique = new Map(found.map((entry) => [`${jsonPointer(entry.path)} ${entry.key}`, entry]));
  const keys = [...unique.values()].sort(
    (a, b) => comparePaths(a.path, b.path) || compareCodePoints(a.key, b.key),
  );
  return { keys, warnings: warningsOf(bare) };
}

/**
 * The manifest with bare IDs; an ID the schema cannot see unwritten is
 * refused. The schema types every position but one: a group's entry in
 * `graphical.order` holds member IDs where a timeline's holds band words.
 */
function bareManifest(value: JsonObject): JsonObject {
  try {
    return withBareIds(value);
  } catch (error) {
    if (error instanceof FileIdError) {
      throw new SchemaValidationError("schema", [...error.path], error.message);
    }
    throw error;
  }
}

/**
 * Check that `value` is a TimeToShare manifest. A checked value is typed as
 * the lossless form `loads` returns: its numbers may be `bigint`s and
 * `JsonFloat`s, and a Fraction is a pair of them.
 */
export function validate(value: unknown): asserts value is LosslessManifest {
  run(value);
}

/** Return the sorted unknown keys of a valid manifest. */
export function unknownKeys(value: unknown): UnknownKey[] {
  return run(value).keys;
}

/**
 * Return the warnings of a valid manifest, sorted by path, then code:
 * `context_absent` (no `@context`) and `bundle_blank` (statements or
 * provenance on a manifest without ID, whose subject is a blank node).
 * Validates `value` as `validate` does. Python's `manifest_warnings` returns
 * the same list.
 */
export function manifestWarnings(value: unknown): ManifestWarning[] {
  return run(value).warnings;
}

function reject(errors: readonly ErrorObject[], instance: unknown): never {
  const error = select(errors);
  if (error === undefined) {
    throw new SchemaValidationError("schema", [], "value is invalid");
  }
  throw new SchemaValidationError(
    "schema",
    toPath(error.instancePath, instance),
    error.message ?? error.keyword,
  );
}

/**
 * Read a manifest in any serialization with `loads` and validate it: a
 * manifest read without losing a number or key order.
 */
export function parse(text: string): LosslessManifest {
  const value = loads(text);
  validate(value);
  return value;
}

/** One member of a subject the partial check reads: its definition, key, value, path and owner. */
interface StatementMember {
  readonly definition: "Manifest" | "Timeline" | "Region";
  readonly member: "@context" | "provenance" | "statements";
  readonly value: unknown;
  readonly path: readonly PathSegment[];
  readonly owner: string | null;
}

const DEFINITIONS = { manifest: "Manifest", timeline: "Timeline", region: "Region" } as const;

/**
 * The members of `value` the partial check reads: the manifest's
 * `@context`, then subject by subject (the manifest, then root by root the
 * timeline, its regions and its children, depth first) its `provenance` and
 * its `statements`, each with the ID of the element holding it.
 */
function* statementMembers(value: JsonObject): Generator<StatementMember> {
  const owner = typeof value.id === "string" ? value.id : null;
  if (Object.hasOwn(value, "@context")) {
    yield {
      definition: "Manifest",
      member: "@context",
      value: value["@context"],
      path: ["@context"],
      owner,
    };
  }
  for (const { element, path, kind } of subjects(value)) {
    for (const member of ["provenance", "statements"] as const) {
      if (!Object.hasOwn(element, member)) continue;
      yield {
        definition: DEFINITIONS[kind],
        member,
        value: element[member],
        path: [...path, member],
        owner: typeof element.id === "string" ? element.id : null,
      };
    }
  }
}

/**
 * Return the problems of the statements of `value` alone, as Python's
 * `statement_problems` does. First, member by member, the manifest's
 * `@context` and every `provenance` and `statements` member (subject order:
 * the manifest, then root by root the timeline, its regions and its
 * children, depth first; on one element `provenance` first), each checked as
 * `validate` checks it, its first problem at its path: a number that is not
 * finite (`finite_number`), else the schema's definition of the member
 * (`schema`), reported by the one path rule. Where no member has a problem,
 * every problem of the statement rules follows, not only the first:
 * `context`, `reserved_key`, then the walk of every subject (`iri`,
 * `dangling_target`, `calendar_date`, `representation`, `element_value`,
 * `provenance_duplicate`, `belief_actor`).
 *
 * Nothing outside the statements is refused but a reserved key, and the
 * version marker is not read: a library that reads only part of a manifest
 * checks its statements with this function. The messages are those of
 * `validate`. `value` is in the file form; the rules read its IDs bare, an
 * ID written without `#` as it stands.
 */
export function statementProblems(value: LosslessManifest | JsonObject): SchemaValidationError[] {
  if (!isJsonObject(value)) return [];
  const bare = lenientlyBareIds(value);
  const problems: SchemaValidationError[] = [];
  for (const { definition, member, value: given, path, owner } of statementMembers(bare)) {
    const finite = first(finiteNumberProblems(given, path, owner, member));
    if (finite !== undefined) {
      problems.push(finite);
      continue;
    }
    const schemaProblem = partProblem(given, path, definition, member);
    if (schemaProblem !== undefined) problems.push(schemaProblem);
  }
  if (problems.length > 0) return problems;
  return [...statementRuleProblems(bare)];
}

/**
 * Return every semantic violation in the long-established identity order.
 * `value` is in the file form; the rules read its IDs bare.
 *
 * @throws {SchemaValidationError} if an ID is not written in the file form.
 */
export function identityProblems(value: LosslessManifest | JsonObject): SchemaValidationError[] {
  return [...semanticProblems(bareManifest(value))];
}

const MATCHSTAMPS: readonly PathSegment[] = ["graphical", "matchstamps"];

/** Each match timestamp (`matchstamp: true`) of `value` with its path. */
function* matchTimestamps(value: JsonObject): Generator<[PathSegment[], JsonObject]> {
  for (const [index, timestamp] of timestampsOf(value).entries()) {
    if (isJsonObject(timestamp) && timestamp.matchstamp === true) {
      yield [["graphical", "timestamps", index], timestamp];
    }
  }
}

/**
 * The repeated IDs a named MatchStamp or an alignment anchor holds. IDs are
 * compared as `validate` compares them (each root's tree, an ID repeated
 * within one tree counted once, then the listed elements, then the
 * manifest's ID); a repetition is reported where `validate` reports it when
 * the ID at it or its first occurrence belongs to a MatchStamp.
 */
function* matchstampIdProblems(bare: JsonObject): Generator<SchemaValidationError> {
  const concerned = (...paths: (readonly PathSegment[])[]): boolean =>
    paths.some((path) => MATCHSTAMPS.every((key, index) => path[index] === key));
  const first = new Map<string, PathSegment[]>();
  for (const [id, path, root] of manifestIds(bare)) {
    const earlier = first.get(id);
    if (root !== null) {
      if (earlier === undefined) first.set(id, path);
    } else if (path.length === 1) {
      if (earlier !== undefined && concerned(earlier)) {
        yield duplicateProblem(id, path, earlier, "manifest_id");
      }
    } else if (earlier === undefined) first.set(id, path);
    else if (concerned(path, earlier)) yield duplicateProblem(id, path, earlier);
  }
}

/**
 * Return the problems of the named MatchStamps and their match timestamps
 * alone, as Python's `matchstamp_problems` does. First, each match
 * timestamp (a named timestamp with `matchstamp: true`) and then
 * `graphical.matchstamps`, each checked as `validate` checks it, its first
 * problem at its path: a number that is not finite (`finite_number`), else
 * the schema (`schema`), reported by the one path rule. Where none has a
 * problem, every problem beyond the schema follows, not only the first: an
 * ID of a MatchStamp or an alignment anchor that the manifest holds twice
 * (`duplicate_id`, or `manifest_id` where the manifest's ID repeats one),
 * then the rules of the MatchStamps and their match timestamps
 * (`alignment_anchor`, `matchstamp`, `groupstamp`, `match_timestamp`), in
 * `identityProblems`' order.
 *
 * Nothing else is refused: an ordinary timestamp, the styles and rules, the
 * timelines and the statements are not read beyond what the MatchStamps
 * name. A library that keeps the rest of `graphical` unread checks its
 * MatchStamps with this function. The messages are those of `validate`.
 * `value` is in the file form; the rules read its IDs bare, an ID written
 * without `#` as it stands.
 */
export function matchstampProblems(value: LosslessManifest | JsonObject): SchemaValidationError[] {
  if (!isJsonObject(value)) return [];
  const flagged = [...matchTimestamps(value)];
  const graphical = value.graphical;
  const stated = isJsonObject(graphical) && Object.hasOwn(graphical, "matchstamps");
  if (flagged.length === 0 && !stated) return [];
  const bare = lenientlyBareIds(value);
  const owner = stringId(bare);
  const read = [...matchTimestamps(bare)];
  const problems: SchemaValidationError[] = [];
  for (const [index, [path, timestamp]] of flagged.entries()) {
    const finite = first(finiteNumberProblems(read[index]?.[1], path, owner));
    const problem = finite ?? partProblem(timestamp, path, "Timestamp");
    if (problem !== undefined) problems.push(problem);
  }
  if (stated) {
    const content = (bare.graphical as JsonObject).matchstamps;
    const finite = first(finiteNumberProblems(content, MATCHSTAMPS, owner, "matchstamps"));
    const problem =
      finite ?? partProblem(graphical.matchstamps, MATCHSTAMPS, "Graphical", "matchstamps");
    if (problem !== undefined) problems.push(problem);
  }
  if (problems.length > 0) return problems;
  return [...matchstampIdProblems(bare), ...matchstampRuleProblems(bare)];
}
