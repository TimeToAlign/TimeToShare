/**
 * The TimeToShare schema validator and its public diagnostics.
 *
 * A manifest is validated in its file form, every ID written `#` followed by
 * the ID: the schema check and the search for unknown keys read the value as
 * given. Every other check reads the manifest with bare IDs (`withBareIds`),
 * the finite rule, which runs first, included: their messages quote IDs bare
 * (`'clt_1'`) and the paths of the checks after the schema name the keys of
 * `graphical.order` bare too. The rules run in one order: the version
 * marker, the finite rule, the earlier form of flow control
 * (`./validate/flow.ts`), the schema, the representation of own-axis values,
 * the identity rules, then the statement rules.
 */

import { Ajv2020, type ErrorObject, type ValidateFunction } from "ajv/dist/2020.js";
import { packageSchema, schema } from "./generated/schema.js";
import type { LosslessManifest } from "./generated/types.js";
import { FileIdError, lenientlyBareIds, withBareIds } from "./ids.js";
import { isJsonObject, type JsonObject, plain } from "./json/value.js";
import { loads } from "./serialization/read.js";
import { compareCodePoints, spell } from "./serialization/text.js";
import { subjects } from "./statements/statements.js";
import {
  comparePaths,
  duplicateProblem,
  entries,
  jsonPointer,
  manifestIds,
  type PathSegment,
  SchemaValidationError,
  stringId,
  text,
  timestampsOf,
} from "./validate/diagnostics.js";
import { earlierFormProblems, flowWarnings } from "./validate/flow.js";
import { identityProblems as semanticProblems } from "./validate/identity.js";
import { finiteNumberProblems, representationProblems } from "./validate/representation.js";
import { pythonSearch, schemaRefusal, toPath } from "./validate/schemaMessages.js";
import { type ManifestWarning, statementRuleProblems, warningsOf } from "./validate/statements.js";
import {
  folderProblems,
  matchstampProblems as matchstampRuleProblems,
} from "./validate/timestamps.js";

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
  code: { regExp: pythonSearch },
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
  if (
    !inside &&
    object.type === "object" &&
    "properties" in object &&
    !("additionalProperties" in object)
  ) {
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
 * bases an `allOf` shares and the maps keyed by data, whose
 * `additionalProperties` admits every key (the `@context`, statements and
 * value nodes), so a key no definition declares fails where it stands.
 * Closing a map keyed by data would find no key of its own, only its keys
 * again wherever a value below it fails.
 */
function closedSchema(document: Node): Node {
  return close(document, false, allOfBases(document)) as Node;
}

/** The options of the checks whose errors are reported: each error carries its data and schemas. */
const REPORTING = { ...OPTIONS, verbose: true } as const;

const check = new Ajv2020(REPORTING).compile(schema);
const closed = closedSchema(schema);
const marking = new Ajv2020(REPORTING).compile(closed);
const partChecks = new Map<string, ValidateFunction>();
const branchChecks = new WeakMap<object, ValidateFunction>();

/** Whether `data` passes `branch`, a schema of the document, as the document checks it. */
function passes(branch: unknown, data: unknown): boolean {
  if (typeof branch === "boolean") return branch;
  if (typeof branch !== "object" || branch === null) return false;
  let compiled = branchChecks.get(branch);
  if (compiled === undefined) {
    const definitions = (schema as Node).$defs;
    compiled = new Ajv2020(OPTIONS).compile({ $defs: definitions, ...(branch as Node) });
    branchChecks.set(branch, compiled);
  }
  return compiled(data);
}

/** The definition a local `$ref` (`#/$defs/Name`) names in `root`. */
function definitionOf(root: Node, reference: unknown): unknown {
  if (typeof reference !== "string" || !reference.startsWith("#/$defs/")) return undefined;
  return (root.$defs as Node)[reference.slice("#/$defs/".length)];
}

/**
 * The closed schemas the walk applies at `path` of `instance` through the
 * branches the value takes there: a `oneOf`/`anyOf` branch only where the
 * document's branch passes the value, the `then` or the `else` arm as the
 * document's `if` decides. The closed variant and the document are walked
 * side by side, the variant being the document with keys added.
 */
function takenAt(path: readonly PathSegment[], instance: unknown): Set<object> {
  let level: [unknown, unknown][] = [[closed, schema]];
  let data = instance;
  for (let depth = 0; ; depth += 1) {
    const step = path[depth];
    const taken = new Set<object>();
    const next: [unknown, unknown][] = [];
    const visit = (variant: unknown, document: unknown): void => {
      if (!isJsonObject(variant) || !isJsonObject(document) || taken.has(variant)) return;
      taken.add(variant);
      for (const [key, member] of Object.entries(variant)) {
        const original = document[key];
        if (key === "$ref") {
          visit(definitionOf(closed, member), definitionOf(schema as Node, member));
        } else if (key === "allOf" || key === "anyOf" || key === "oneOf") {
          (member as unknown[]).forEach((branch, index) => {
            const counterpart = (original as unknown[])[index];
            if (key === "allOf" || passes(counterpart, data)) visit(branch, counterpart);
          });
        } else if (key === "if") {
          const arm = passes(original, data) ? "then" : "else";
          visit(variant[arm], document[arm]);
        } else if (key === "properties" && typeof step === "string") {
          if (Object.hasOwn(member as Node, step)) {
            next.push([(member as Node)[step], (original as Node)[step]]);
          }
        } else if (key === "additionalProperties" && typeof step === "string") {
          if (!Object.hasOwn((variant.properties ?? {}) as Node, step))
            next.push([member, original]);
        } else if (key === "prefixItems" && typeof step === "number") {
          const items = member as unknown[];
          if (step < items.length) next.push([items[step], (original as unknown[])[step]]);
        } else if (key === "items" && typeof step === "number") {
          const prefix = Array.isArray(variant.prefixItems) ? variant.prefixItems.length : 0;
          if (step >= prefix) next.push([member, original]);
        }
      }
    };
    for (const [variant, document] of level) visit(variant, document);
    if (step === undefined) return taken;
    level = next;
    data = (data as Record<string | number, unknown>)[step];
  }
}

/**
 * The unknown keys the closed variant's errors name: a key is listed where
 * the closed object refusing it is applied on a branch the value takes,
 * never from a `oneOf`/`anyOf` branch the document refuses the value, as
 * Python lists only the keys of branches that fail for undeclared keys alone.
 */
function keysOf(errors: readonly ErrorObject[], instance: unknown): UnknownKey[] {
  const found: UnknownKey[] = [];
  const takenByPath = new Map<string, Set<object>>();
  for (const error of errors) {
    if (error.keyword !== "unevaluatedProperties") continue;
    const path = toPath(error.instancePath, instance);
    let taken = takenByPath.get(error.instancePath);
    if (taken === undefined) {
      taken = takenAt(path, instance);
      takenByPath.set(error.instancePath, taken);
    }
    if (!taken.has(error.parentSchema as object)) continue;
    found.push({ path, key: String(error.params.unevaluatedProperty) });
  }
  return found;
}

/** The refusal of a value the schema check failed, as Python chooses and words it. */
function refusalOf(
  checked: ValidateFunction,
  instance: unknown,
  original: unknown,
): { path: PathSegment[]; message: string } | undefined {
  return schemaRefusal(checked.errors ?? [], instance, original, checked.schema, passes);
}

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
    compiled = new Ajv2020(REPORTING).compile({ $defs: definitions, ...declared });
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
  if (checkPart(instance)) return undefined;
  const refusal = refusalOf(checkPart, instance, value);
  if (refusal === undefined) return undefined;
  return new SchemaValidationError("schema", [...path, ...refusal.path], refusal.message);
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

  const earlier = first(earlierFormProblems(value));
  if (earlier !== undefined) throw earlier;

  const instance = plain(value);
  let found: UnknownKey[] = [];
  if (!marking(instance)) {
    // The closed variant refuses undeclared keys; the document decides validity.
    if (!check(instance)) reject(instance, value);
    found = keysOf(marking.errors ?? [], instance);
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
  const warnings: ManifestWarning[] = [...warningsOf(bare), ...flowWarnings(bare)];
  warnings.sort((a, b) => comparePaths(a.path, b.path) || compareCodePoints(a.code, b.code));
  return { keys, warnings };
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
 * `context_absent` (no `@context`), `bundle_blank` (statements or
 * provenance on a manifest without ID, whose subject is a blank node),
 * `manifestation_unknown` (a manifestation the format does not define for its
 * flow-control element or destination) and `convention_unknown` (a FlowMap's
 * convention that is none of the format's).
 * Validates `value` as `validate` does. Python's `manifest_warnings` returns
 * the same list.
 */
export function manifestWarnings(value: unknown): ManifestWarning[] {
  return run(value).warnings;
}

function reject(instance: unknown, original: unknown): never {
  const refusal = refusalOf(check, instance, original);
  if (refusal === undefined) {
    throw new SchemaValidationError("schema", [], "value is invalid");
  }
  throw new SchemaValidationError("schema", refusal.path, refusal.message);
}

const packageCheck = new Ajv2020(REPORTING).compile(packageSchema);
const packageBranchChecks = new WeakMap<object, ValidateFunction>();

/** Whether `data` passes `branch`, a schema of the package schema, as that schema checks it. */
function passesPackage(branch: unknown, data: unknown): boolean {
  if (typeof branch === "boolean") return branch;
  if (typeof branch !== "object" || branch === null) return false;
  let compiled = packageBranchChecks.get(branch);
  if (compiled === undefined) {
    const definitions = (packageSchema as Node).$defs;
    compiled = new Ajv2020(OPTIONS).compile({ $defs: definitions, ...(branch as Node) });
    packageBranchChecks.set(branch, compiled);
  }
  return compiled(data);
}

/**
 * Check the value of a `package.yaml` and throw its first problem, as
 * Python's `validate_package` does. The version marker first: a value
 * without `timetoshare` is no package (`not_a_package`), another version
 * throws `UnsupportedVersionError`. Then the package schema, its problem
 * chosen by the one path rule (`schema`). Then, entry by entry, the
 * manifests and then the tables: a manifest listed again under the same
 * `url`, and a table listed again under the same `url` and `type`
 * (`duplicate_url`, at the later entry's `url`; URLs compared as written),
 * and a folder, a `url` ending in `/`, with a `size` or an `integrity`
 * (`folder_descriptor`, at that member, `size` first). What the manifests and the tables hold is the
 * Python package's package check.
 */
export function validatePackage(value: unknown): void {
  if (!isJsonObject(value) || !Object.hasOwn(value, "timetoshare")) {
    throw new SchemaValidationError("not_a_package", [], "not a TimeToShare package");
  }
  if (value.timetoshare !== SCHEMA_VERSION) throw new UnsupportedVersionError(value.timetoshare);
  const instance = plain(value);
  if (!packageCheck(instance)) {
    const refusal = schemaRefusal(
      packageCheck.errors ?? [],
      instance,
      value,
      packageCheck.schema,
      passesPackage,
    );
    if (refusal === undefined) throw new SchemaValidationError("schema", [], "value is invalid");
    throw new SchemaValidationError("schema", refusal.path, refusal.message);
  }
  const listed = new Map<string, number>();
  for (const [index, entry] of entries(value, "manifests").entries()) {
    const path = ["manifests", index];
    const url = text(entry, "url");
    const earlier = listed.get(url);
    if (earlier !== undefined) {
      throw new SchemaValidationError(
        "duplicate_url",
        [...path, "url"],
        `the manifest '${url}' is listed twice, first at ${jsonPointer(["manifests", earlier, "url"])}`,
      );
    }
    listed.set(url, index);
    const folder = first(folderProblems(entry, path));
    if (folder !== undefined) throw folder;
  }
  const tables = new Map<string, number>();
  for (const [index, entry] of entries(value, "tables").entries()) {
    const path = ["tables", index];
    const url = text(entry, "url");
    const type = text(entry, "type");
    const key = JSON.stringify([url, type]);
    const earlier = tables.get(key);
    if (earlier !== undefined) {
      throw new SchemaValidationError(
        "duplicate_url",
        [...path, "url"],
        `the table '${url}' of the type ${type} is listed twice, first at ${jsonPointer(["tables", earlier, "url"])}`,
      );
    }
    tables.set(key, index);
    const folder = first(folderProblems(entry, path));
    if (folder !== undefined) throw folder;
  }
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
