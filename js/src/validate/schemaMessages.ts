/**
 * The refusal the schema check reports, chosen and worded as Python's
 * validator chooses and words it.
 *
 * Ajv reports every error of a value in a flat list; this module reads from
 * it the leaves Python's `jsonschema` walk reports, picks one by the one
 * path rule (the deepest leaf, then the path that comes first element by
 * element, then the first the walk reports) and words it as `jsonschema`
 * 4.26 does, with the values spelled as Python's `repr` spells them, and
 * with the three shapes Python's `worded` rewords: the constants a
 * `oneOf`/`anyOf` admits, a key no value is admitted at, and the part of a
 * string a `not` of patterns or words refuses. Ajv must run with
 * `verbose: true`, so each error carries its data and schemas, and with
 * `pythonSearch` as its pattern engine, so a pattern refuses what Python's
 * refuses.
 */

import type { ErrorObject } from "ajv/dist/2020.js";
import { CHUNK_SENTINEL, HASH, NOMATCH_SENTINEL } from "../ids.js";
import { isJsonFloat, isJsonObject, keysOf } from "../json/value.js";
import { floatText } from "../serialization/text.js";
import { comparePaths, type PathSegment } from "./diagnostics.js";

/** The refusal a schema check reports: where, and in which words. */
export interface SchemaRefusal {
  readonly path: PathSegment[];
  readonly message: string;
}

/** Whether `data` passes `schema`, a schema of the document, as the document checks it. */
export type BranchCheck = (schema: unknown, data: unknown) => boolean;

type Node = Readonly<Record<string, unknown>>;

const NOT_PRINTABLE = /^[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Cn}\p{Zl}\p{Zp}\p{Zs}]$/u;

function hex(codePoint: number, width: number): string {
  return codePoint.toString(16).padStart(width, "0");
}

/** Whether Python's `str.isprintable` holds for one code point. */
function printable(character: string): boolean {
  return character === " " || !NOT_PRINTABLE.test(character);
}

/** A string as Python's `repr` spells it. */
function stringRepr(value: string): string {
  const quote = value.includes("'") && !value.includes('"') ? '"' : "'";
  let spelled = quote;
  for (const character of value) {
    const codePoint = character.codePointAt(0) as number;
    if (character === quote || character === "\\") spelled += `\\${character}`;
    else if (character === "\t") spelled += "\\t";
    else if (character === "\n") spelled += "\\n";
    else if (character === "\r") spelled += "\\r";
    else if (codePoint < 0x20 || codePoint === 0x7f) spelled += `\\x${hex(codePoint, 2)}`;
    else if (codePoint < 0x7f || printable(character)) spelled += character;
    else if (codePoint <= 0xff) spelled += `\\x${hex(codePoint, 2)}`;
    else if (codePoint <= 0xffff) spelled += `\\u${hex(codePoint, 4)}`;
    else spelled += `\\U${hex(codePoint, 8)}`;
  }
  return spelled + quote;
}

/** A float as Python's `repr` spells it: the shared spelling, a lone mantissa digit bare. */
function floatRepr(value: number): string {
  return floatText(value).replace(/^(-?\d)\.0e/, "$1e");
}

/**
 * A JSON value as Python's `repr` spells the value Python reads: `None`,
 * `True`, `False`, integers in digits, floats as `repr` spells them, strings
 * quoted as `repr` quotes them, lists and dicts in their written order.
 */
export function pythonRepr(value: unknown): string {
  if (value === null || value === undefined) return "None";
  if (value === true) return "True";
  if (value === false) return "False";
  if (typeof value === "bigint") return value.toString();
  if (isJsonFloat(value)) return floatRepr(value.value);
  if (typeof value === "number") {
    return Number.isInteger(value) ? BigInt(value).toString() : floatRepr(value);
  }
  if (typeof value === "string") return stringRepr(value);
  if (Array.isArray(value)) return `[${value.map(pythonRepr).join(", ")}]`;
  if (isJsonObject(value)) {
    const members = keysOf(value).map((key) => `${stringRepr(key)}: ${pythonRepr(value[key])}`);
    return `{${members.join(", ")}}`;
  }
  return String(value);
}

/**
 * The pattern keyword's search as Python's `re.search` runs it: a `$`
 * matches at the end of the string and also before a line feed that ends
 * it. The schema guards every pattern ending in `$` with a `not` of control
 * characters or a `maxLength`, so a value ending in a line feed is refused
 * either way; this engine makes the leaves that refuse it Python's.
 */
export const pythonSearch = Object.assign(
  (pattern: string, flags: string): { test(text: string): boolean; toString(): string } => {
    const expression = new RegExp(pattern, flags);
    const anchored = pattern.includes("$");
    return {
      test: (text) =>
        expression.test(text) ||
        (anchored && text.endsWith("\n") && expression.test(text.slice(0, -1))),
      toString: () => `${expression}`,
    };
  },
  { code: "pythonSearch" },
);

/** Convert an Ajv instance path to segments, typing array indices as numbers. */
export function toPath(instancePath: string, value: unknown): PathSegment[] {
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

/** The value at `path` in `value`, or `undefined` where the path leads nowhere. */
function at(value: unknown, path: readonly PathSegment[]): unknown {
  let cursor = value;
  for (const segment of path) {
    if (Array.isArray(cursor) && typeof segment === "number") cursor = cursor[segment];
    else if (isJsonObject(cursor) && typeof segment === "string") cursor = cursor[segment];
    else return undefined;
  }
  return cursor;
}

/** The constants a `oneOf`/`anyOf` of `const` branches admits, or `null`. */
function constants(error: ErrorObject): unknown[] | null {
  if (error.keyword !== "oneOf" && error.keyword !== "anyOf") return null;
  const branches = error.schema;
  if (!Array.isArray(branches)) return null;
  if (!branches.every((branch) => isJsonObject(branch) && Object.hasOwn(branch, "const"))) {
    return null;
  }
  return branches.map((branch) => (branch as Node).const);
}

/**
 * The errors Python's walk reports as leaves, in Ajv's order: a `oneOf` or
 * `anyOf` of constants stands for its branches; a failed `oneOf`, `anyOf`,
 * `if` or `propertyNames` stands for nothing, its branches' errors being
 * the leaves, but a `oneOf` that more than one branch passes is one; a
 * discriminator whose tag names no branch is the `oneOf` failing whole.
 */
function leaves(errors: readonly ErrorObject[]): ErrorObject[] {
  const folded = errors
    .filter((error) => constants(error) !== null)
    .map((error) => ({ instancePath: error.instancePath, prefix: `${error.schemaPath}/` }));
  return errors.filter((error) => {
    if (
      folded.some(
        (fold) =>
          error.instancePath === fold.instancePath && error.schemaPath.startsWith(fold.prefix),
      )
    ) {
      return false;
    }
    switch (error.keyword) {
      case "if":
      case "propertyNames":
        return false;
      case "oneOf":
        return constants(error) !== null || error.params.passingSchemas != null;
      case "anyOf":
        return constants(error) !== null;
      default:
        return true;
    }
  });
}

/** The definition a local `$ref` (`#/$defs/Name`) names in `root`. */
function referenced(root: unknown, reference: unknown): unknown {
  if (typeof reference !== "string" || !reference.startsWith("#/$defs/")) return undefined;
  const definitions = isJsonObject(root) ? root.$defs : undefined;
  return isJsonObject(definitions) ? definitions[reference.slice("#/$defs/".length)] : undefined;
}

/**
 * The schemas the walk applies at `path` of a value, numbered in the
 * order Python's `jsonschema` visits them: an object's keywords in the
 * order the document writes them, `$ref`, `allOf`, `anyOf`, `oneOf` and
 * `if` (its `then` and `else`) in place, the branches in order, then the
 * schemas `properties`, `additionalProperties`, `prefixItems` and `items`
 * hand the next step of the path, and at the path itself the schema of
 * `propertyNames`, whose errors lie at the object.
 */
function appliedAt(root: unknown, path: readonly PathSegment[]): Map<object, number> {
  let level: unknown[] = [root];
  for (let depth = 0; ; depth += 1) {
    const step = path[depth];
    const order = new Map<object, number>();
    const next: unknown[] = [];
    const visit = (node: unknown): void => {
      // A schema applied twice at one place reports its errors where it was first applied.
      if (!isJsonObject(node) || order.has(node)) return;
      order.set(node, order.size);
      for (const [key, member] of Object.entries(node)) {
        if (key === "$ref") visit(referenced(root, member));
        else if (key === "allOf" || key === "anyOf" || key === "oneOf") {
          if (Array.isArray(member)) member.forEach(visit);
        } else if (key === "if") {
          visit(node.then);
          visit(node.else);
        } else if (key === "propertyNames") {
          if (step === undefined) visit(member);
        } else if (key === "properties" && typeof step === "string") {
          if (isJsonObject(member) && Object.hasOwn(member, step)) next.push(member[step]);
        } else if (key === "additionalProperties" && typeof step === "string") {
          const declared = node.properties;
          if (!isJsonObject(declared) || !Object.hasOwn(declared, step)) next.push(member);
        } else if (key === "prefixItems" && typeof step === "number") {
          if (Array.isArray(member) && step < member.length) next.push(member[step]);
        } else if (key === "items" && typeof step === "number") {
          const prefix = Array.isArray(node.prefixItems) ? node.prefixItems.length : 0;
          if (step >= prefix) next.push(member);
        }
      }
    };
    level.forEach(visit);
    if (step === undefined) return order;
    level = next;
  }
}

/**
 * Of the leaves at one path, the one the walk reports first: the one whose
 * schema it applies first, and of one schema's keywords the one the
 * document writes first; Ajv's order decides the rest.
 */
function firstReported(
  root: unknown,
  path: readonly PathSegment[],
  found: readonly ErrorObject[],
): ErrorObject {
  const applied = appliedAt(root, path);
  const rank = (error: ErrorObject): [number, number] => {
    const parent = error.parentSchema;
    if (!isJsonObject(parent)) return [Number.POSITIVE_INFINITY, 0];
    return [
      applied.get(parent) ?? Number.POSITIVE_INFINITY,
      Object.keys(parent).indexOf(error.keyword),
    ];
  };
  let best = found[0] as ErrorObject;
  let [node, keyword] = rank(best);
  for (const error of found.slice(1)) {
    const [n, k] = rank(error);
    if (n < node || (n === node && k < keyword)) [best, node, keyword] = [error, n, k];
  }
  return best;
}

/** The patterns a `not` refuses, with how a value meets each and what is not admitted. */
const REFUSED_PATTERNS: ReadonlyMap<string, readonly [string, string]> = new Map([
  ["[\\u0000-\\u001f]", ["holds", "no control character (U+0000 to U+001F) is admitted here"]],
  [
    "[\\u0000-\\u0020\\u007f-\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff]",
    ["holds", "no whitespace and no control character is admitted here"],
  ],
  ["^_:", ["begins with", "no blank node identifier is admitted here"]],
  ["^@", ["begins with", "no keyword is admitted here"]],
  ["[^A-Za-z0-9-]", ["holds", "only A-Z, a-z, 0-9 and '-' are admitted here"]],
  ["[^A-Za-z0-9_-]", ["holds", "only A-Z, a-z, 0-9, '_' and '-' are admitted here"]],
]);

/**
 * Why a word a `not` lists is refused, where it is no reserved ID: the one
 * other such list is the prefix names'.
 */
const REFUSED_WORDS =
  "it names a key of the manifest's elements or a URI scheme the format reads as such";

/** The IDs no element takes, as a file writes them: the words of the `not` of `Id`. */
const RESERVED_IDS: ReadonlySet<string> = new Set(
  [NOMATCH_SENTINEL, CHUNK_SENTINEL].map((sentinel) => HASH + sentinel),
);

/** The first character of `text`: itself where printable, else its code point. */
function character(text: string): string {
  const first = String.fromCodePoint(text.codePointAt(0) as number);
  if (printable(first) && first !== " ") return stringRepr(first);
  return `U+${(first.codePointAt(0) as number).toString(16).toUpperCase().padStart(4, "0")}`;
}

/** The message of a string a `not` of patterns or words refuses, or `null`. */
function notAdmitted(error: ErrorObject, value: unknown): string | null {
  const refused = error.schema;
  if (error.keyword !== "not" || typeof value !== "string" || !isJsonObject(refused)) return null;
  const branches = Array.isArray(refused.anyOf) ? refused.anyOf : [refused];
  for (const branch of branches) {
    if (!isJsonObject(branch)) return null;
    const keys = Object.keys(branch);
    if (keys.length === 1 && keys[0] === "enum") {
      if ((branch.enum as unknown[]).includes(value)) {
        if (RESERVED_IDS.has(value)) {
          return `${stringRepr(value.slice(HASH.length))} is reserved for a sentinel`;
        }
        return `${stringRepr(value)} is not admitted here: ${REFUSED_WORDS}`;
      }
      continue;
    }
    if (keys.length !== 1 || keys[0] !== "pattern") return null;
    const pattern = branch.pattern as string;
    const found = new RegExp(pattern, "u").exec(value);
    if (found === null) continue;
    const words = REFUSED_PATTERNS.get(pattern);
    if (words === undefined) return null;
    const [verb, what] = words;
    const part = verb === "holds" ? character(found[0]) : stringRepr(found[0]);
    return `${stringRepr(value)} ${verb} ${part}: ${what}`;
  }
  return null;
}

function bounded(value: unknown, limit: unknown, one: number, at: string, other: string): string {
  return `${pythonRepr(value)} ${limit === one ? at : other}`;
}

/** The message `jsonschema` 4.26 gives an error, `value` the instance it reports. */
function walkMessage(error: ErrorObject, value: unknown, check: BranchCheck): string {
  const schema = error.schema;
  const shown = pythonRepr(value);
  switch (error.keyword) {
    case "type": {
      const types = Array.isArray(schema) ? schema : [schema];
      return `${shown} is not of type ${types.map(pythonRepr).join(", ")}`;
    }
    case "enum":
      return `${shown} is not one of ${pythonRepr(schema)}`;
    case "const":
      return `${pythonRepr(schema)} was expected`;
    case "pattern":
      return `${shown} does not match ${pythonRepr(schema)}`;
    case "minimum":
      return `${shown} is less than the minimum of ${pythonRepr(schema)}`;
    case "maximum":
      return `${shown} is greater than the maximum of ${pythonRepr(schema)}`;
    case "exclusiveMinimum":
      return `${shown} is less than or equal to the minimum of ${pythonRepr(schema)}`;
    case "exclusiveMaximum":
      return `${shown} is greater than or equal to the maximum of ${pythonRepr(schema)}`;
    case "minItems":
    case "minLength":
      return bounded(value, schema, 1, "should be non-empty", "is too short");
    case "maxItems":
    case "maxLength":
      return bounded(value, schema, 0, "is expected to be empty", "is too long");
    case "minProperties":
      return bounded(value, schema, 1, "should be non-empty", "does not have enough properties");
    case "maxProperties":
      return bounded(value, schema, 0, "is expected to be empty", "has too many properties");
    case "uniqueItems":
      return `${shown} has non-unique elements`;
    case "required":
      return `${pythonRepr(error.params.missingProperty)} is a required property`;
    case "dependentRequired":
      return `${pythonRepr(error.params.missingProperty)} is a dependency of ${pythonRepr(error.params.property)}`;
    case "items": {
      const items = Array.isArray(value) ? value : [];
      const parent = error.parentSchema as Node;
      const prefix = Array.isArray(parent.prefixItems) ? parent.prefixItems.length : 0;
      const extra = items.length - prefix;
      const rest = extra === 1 ? items[prefix] : items.slice(prefix);
      const item = prefix === 1 ? "item" : "items";
      return `Expected at most ${prefix} ${item} but found ${extra} extra: ${pythonRepr(rest)}`;
    }
    case "not":
      return `${shown} should not be valid under ${pythonRepr(schema)}`;
    case "false schema":
      return `False schema does not allow ${shown}`;
    case "oneOf": {
      const passing = error.params.passingSchemas as readonly number[] | null;
      if (passing == null || !Array.isArray(schema)) {
        return `${shown} is not valid under any of the given schemas`;
      }
      const first = passing[0] as number;
      const more = schema.filter((branch, index) => index > first && check(branch, error.data));
      const valid = [...more, schema[first]];
      return `${shown} is valid under each of ${valid.map(pythonRepr).join(", ")}`;
    }
    case "anyOf":
    case "discriminator":
      return `${shown} is not valid under any of the given schemas`;
    default:
      return error.message ?? error.keyword;
  }
}

/** Whether a schema refuses every value: `not: {}`, `not: true` or `false`. */
function refusesAll(error: ErrorObject): boolean {
  if (error.keyword === "false schema") return true;
  const schema = error.schema;
  return (
    error.keyword === "not" &&
    (schema === true || (isJsonObject(schema) && Object.keys(schema).length === 0))
  );
}

/** The message of a selected leaf, worded as Python's `worded` words it. */
function worded(
  error: ErrorObject,
  path: readonly PathSegment[],
  value: unknown,
  check: BranchCheck,
): string {
  const admitted = constants(error);
  if (admitted !== null) return `${pythonRepr(value)} is not one of ${pythonRepr(admitted)}`;
  const last = path[path.length - 1];
  if (refusesAll(error) && typeof last === "string") {
    return `the key ${stringRepr(last)} is not admitted here`;
  }
  return notAdmitted(error, value) ?? walkMessage(error, value, check);
}

/**
 * The refusal of a value the schema check failed: the leaf the one path rule
 * selects among `errors`, at its path, worded as Python words it. `instance`
 * is the value Ajv checked, `original` the same value as read (its
 * `JsonFloat`s and `bigint`s kept), whose members the message spells, and
 * `root` the schema Ajv compiled, whose schemas the errors name.
 */
export function schemaRefusal(
  errors: readonly ErrorObject[],
  instance: unknown,
  original: unknown,
  root: unknown,
  check: BranchCheck,
): SchemaRefusal | undefined {
  let best: { error: ErrorObject; path: PathSegment[] }[] = [];
  for (const error of leaves(errors)) {
    const path = toPath(error.instancePath, instance);
    const held = best[0]?.path;
    const order = held === undefined ? -1 : held.length - path.length || comparePaths(path, held);
    if (order < 0) best = [{ error, path }];
    else if (order === 0) best.push({ error, path });
  }
  const first = best[0];
  if (first === undefined) return undefined;
  const error = firstReported(
    root,
    first.path,
    best.map((leaf) => leaf.error),
  );
  // A string is the same read and checked; it is a key where `propertyNames` checked it.
  const value =
    typeof error.data === "string" ? error.data : (at(original, first.path) ?? error.data);
  return { path: first.path, message: worded(error, first.path, value, check) };
}
