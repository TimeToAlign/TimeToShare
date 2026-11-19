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
import { FileIdError, lenientlyBareIds, memberWithBareIds, withBareIds } from "./ids.js";
import { isJsonObject, type JsonObject, plain } from "./json/value.js";
import { loads } from "./serialization/read.js";
import { compareCodePoints, spell } from "./serialization/text.js";
import {
  descriptionArrays,
  linkProblems,
  schemeProblems,
  type UnregisteredTerm,
  unregisteredTermsOf,
} from "./validate/description.js";
import {
  comparePaths,
  jsonPointer,
  type PathSegment,
  SchemaValidationError,
} from "./validate/diagnostics.js";
import { identityProblems as semanticProblems } from "./validate/identity.js";
import { finiteNumberProblems, representationProblems } from "./validate/representation.js";

export type { JsonObject } from "./json/value.js";
export { childEnds } from "./validate/containment.js";
export type { UnregisteredTerm } from "./validate/description.js";
export {
  entries,
  jsonPointer,
  lengthOf,
  numberTypeOf,
  type PathSegment,
  SchemaValidationError,
  text,
  UNIT_NUMBER_TYPES,
  type ValidationCode,
} from "./validate/diagnostics.js";

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
const memberChecks = new Map<string, ValidateFunction>();

/** The check of one member of a definition, as the whole document checks it. */
function memberCheck(definition: string, member: string): ValidateFunction {
  const key = `${definition}.${member}`;
  let compiled = memberChecks.get(key);
  if (compiled === undefined) {
    const definitions = (schema as Node).$defs as Readonly<Record<string, Node>>;
    const owner = definitions[definition] as Node;
    const declared = (owner.properties as Readonly<Record<string, Node>>)[member];
    compiled = new Ajv2020(OPTIONS).compile({ $defs: definitions, ...declared });
    memberChecks.set(key, compiled);
  }
  return compiled;
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

/** What a valid manifest is warned of: its unknown keys and its unregistered terms. */
interface Warnings {
  readonly keys: UnknownKey[];
  readonly terms: UnregisteredTerm[];
}

/** Check a value through every rule and return its unknown keys and unregistered terms. */
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

  const unique = new Map(found.map((entry) => [`${jsonPointer(entry.path)} ${entry.key}`, entry]));
  const keys = [...unique.values()].sort(
    (a, b) => comparePaths(a.path, b.path) || compareCodePoints(a.key, b.key),
  );
  return { keys, terms: unregisteredTermsOf(bare) };
}

/**
 * The manifest with bare IDs; an ID the schema cannot see unwritten is
 * refused. The schema types every position but two: a group's entry in
 * `graphical.order` holds member IDs where a timeline's holds band words, and
 * an identifier's `scheme` written without `#` is a URI unless it names a
 * scheme of the manifest.
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
 * Return the bare terms of a valid manifest outside their registered words.
 * Validates `value` as `validate` does, then lists every term of an open
 * vocabulary (a link's `relation` and `parts_relation`, an assertion's
 * `method`, a part slot's `absent`, a `part_of` entry's `parts_relation`)
 * that holds no colon and is not registered for its key, sorted by path. Such
 * a term is kept and read as its key's fallback; it is never refused.
 * Python's `unregistered_terms` returns the same list.
 */
export function unregisteredTerms(value: unknown): UnregisteredTerm[] {
  return run(value).terms;
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

/**
 * Return the problems of the description layer of `value` alone, as Python's
 * `description_problems` does. First, array by array, the manifest's `schemes`
 * and every `links` array (the manifest's, then root by root each timeline's,
 * its regions' and its children's, depth first) checked as `validate` checks
 * them, each array's first problem at its path: a number that is not finite
 * (`finite_number`), else the schema's `#/$defs/Scheme` or `#/$defs/Link`
 * (`schema`), reported by the one path rule, else an ID the schema cannot
 * see unwritten (`schema`, as `validate` refuses it: an identifier's
 * `scheme` written without `#` that names a scheme of the manifest). Where
 * no array has a problem,
 * the reference rules follow over the whole manifest, in the order of
 * `identityProblems`: each scheme ID unique across every ID of the manifest
 * (`duplicate_id`), the manifest ID that is a scheme's (`manifest_id`), then
 * link by link the dates (`calendar_date`) and references
 * (`dangling_target`) of links.
 *
 * Nothing outside the description layer is refused, and the version marker
 * is not read: a manifest whose timelines break other rules but whose links
 * and schemes are sound has no problem here. A library that reads only part
 * of a manifest checks its description layer with this function. The
 * messages are those of `validate`. `value` is in the file form; every ID of
 * the description layer must be written so, the reference rules read the
 * IDs bare, and an ID outside the description layer written without `#` is
 * read as it stands.
 */
export function descriptionProblems(value: LosslessManifest | JsonObject): SchemaValidationError[] {
  if (!isJsonObject(value)) return [];
  const problems: SchemaValidationError[] = [];
  const bare = lenientlyBareIds(value);
  const plainArrays = [...descriptionArrays(bare)];
  for (const [index, { definition, member, value: array, path }] of [
    ...descriptionArrays(value),
  ].entries()) {
    const owner = plainArrays[index]?.owner ?? null;
    const finite = first(finiteNumberProblems(plainArrays[index]?.value, path, owner, member));
    if (finite !== undefined) {
      problems.push(finite);
      continue;
    }
    const instance = plain(array);
    const checkMember = memberCheck(definition, member);
    const error = checkMember(instance) ? undefined : select(checkMember.errors ?? []);
    if (error !== undefined) {
      const at = [...path, ...toPath(error.instancePath, instance)];
      problems.push(new SchemaValidationError("schema", at, error.message ?? error.keyword));
      continue;
    }
    try {
      memberWithBareIds(value, definition, member, path);
    } catch (refused) {
      if (!(refused instanceof FileIdError)) throw refused;
      problems.push(new SchemaValidationError("schema", [...refused.path], refused.message));
    }
  }
  if (problems.length > 0) return problems;
  // Every ID of the description layer is now known to be in the file form;
  // the reference rules compare it with IDs outside the layer, which are read
  // leniently so that this function refuses nothing outside it.
  return [...schemeProblems(bare), ...linkProblems(bare)];
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
