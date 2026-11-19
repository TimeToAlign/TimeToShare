/**
 * IDs in a manifest file and in memory.
 *
 * A manifest file writes every ID with a leading `#`: an element's own ID
 * (`"id": "#clt_1"`) as well as every reference to one (a group's members,
 * the keys of `graphical.order`, a named timestamp's timeline, an address's
 * `id`, a selector's `within`, a flow-control element's `target`, a measure
 * view's `measure_map`, a part slot's `represented_by`). In memory an ID is
 * bare: `clt_1`. Exactly one `#` is stripped, so the file text `##x` is the
 * bare ID `#x`.
 *
 * Two positions hold an ID or something else, and the `#` tells them apart:
 * the values of a group's entry in `graphical.order` are member IDs, while a
 * timeline's entry holds band words, which stay bare; and an identifier's
 * `scheme` is either the ID of a scheme of the manifest (`#opus`) or an
 * absolute URI, which is written as it is.
 *
 * `withFileIds` and `withBareIds` convert a whole manifest between the two
 * forms. Both are pure: they return a new value, keep unknown keys and the
 * order of every object's keys (an order key renamed in place keeps its
 * position) and leave every number as `loads` read it. Both are driven by
 * one table of the positions of IDs, `ID_POSITIONS`, by schema definition
 * and member, and one table of where each definition occurs, `CONTAINERS`.
 * Python's `timetoshare.ids` holds the same tables and gives the same values
 * and messages.
 */

import { clone, isJsonObject, type JsonObject, keysOf, objectFrom } from "./json/value.js";

/** The character that marks an ID in a manifest file. */
export const HASH = "#";

/**
 * How a member holds IDs: `id` the member is one ID; `ids` a list of IDs;
 * `order` an object keyed by IDs whose value, where the key names a group, is
 * a list of member IDs (a timeline's value holds band words); `scheme` an ID
 * or an absolute URI, the `#` telling them apart.
 */
export type IdShape = "id" | "ids" | "order" | "scheme";

/** Every member of a schema definition that holds IDs, and how it holds them. */
export const ID_POSITIONS: readonly (readonly [string, string, IdShape])[] = [
  ["Manifest", "id", "id"],
  ["Timeline", "id", "id"],
  ["Group", "id", "id"],
  ["Group", "members", "ids"],
  ["Graphical", "order", "order"],
  ["Timestamp", "id", "id"],
  ["Timestamp", "timeline", "id"],
  ["Address", "id", "id"],
  ["MeasureMap", "id", "id"],
  ["Region", "id", "id"],
  ["FlowControlElement", "id", "id"],
  ["FlowControlElement", "target", "id"],
  ["Selector", "within", "id"],
  ["MapBase", "id", "id"],
  ["MeasureView", "measure_map", "id"],
  ["PartSlot", "represented_by", "ids"],
  ["Scheme", "id", "id"],
  ["Identifier", "scheme", "scheme"],
];

/** How a member holds a definition: one object, a list, or an object's values. */
export type Holding = "one" | "list" | "values";

/** Every member through which a definition holds another that holds IDs. */
export const CONTAINERS: readonly (readonly [string, string, Holding, string])[] = [
  ["Manifest", "timelines", "list", "Timeline"],
  ["Manifest", "groups", "list", "Group"],
  ["Manifest", "measure_maps", "list", "MeasureMap"],
  ["Manifest", "schemes", "list", "Scheme"],
  ["Manifest", "links", "list", "Link"],
  ["Manifest", "graphical", "one", "Graphical"],
  ["Timeline", "children", "list", "Timeline"],
  ["Timeline", "conversion_maps", "list", "ConversionMap"],
  ["Timeline", "regions", "list", "Region"],
  ["Timeline", "flow_control", "list", "FlowControlElement"],
  ["Timeline", "links", "list", "Link"],
  ["Region", "links", "list", "Link"],
  ["Graphical", "rules", "list", "Rule"],
  ["Graphical", "timestamps", "list", "Timestamp"],
  ["Rule", "select", "one", "Selector"],
  ["Selector", "addresses", "list", "Address"],
  ["ChainMap", "maps", "list", "ConversionMap"],
  ["PiecewiseMap", "maps", "list", "ConversionMap"],
  ["CombinationMap", "maps", "values", "ConversionMap"],
  ["Link", "identifiers", "list", "Identifier"],
  ["Link", "parts", "list", "PartSlot"],
  ["Link", "part_of", "list", "PartOf"],
  ["PartSlot", "identifiers", "list", "Identifier"],
  ["PartOf", "identifiers", "list", "Identifier"],
];

/** The conversion-map types built on `MeasureView`; every other one on `MapBase`. */
export const MEASURE_VIEWS: readonly string[] = [
  "FloatingMeasureMap",
  "MeasureBeatMap",
  "MeasureNumberMap",
  "MeasureRecordMap",
];

const POSITIONS = new Map<string, Map<string, IdShape>>();
for (const [definition, member, shape] of ID_POSITIONS) {
  const members = POSITIONS.get(definition) ?? new Map<string, IdShape>();
  members.set(member, shape);
  POSITIONS.set(definition, members);
}
const HELD = new Map<string, Map<string, readonly [Holding, string]>>();
for (const [definition, member, holding, child] of CONTAINERS) {
  const members = HELD.get(definition) ?? new Map<string, readonly [Holding, string]>();
  members.set(member, [holding, child]);
  HELD.set(definition, members);
}

type Path = readonly (string | number)[];

/** Thrown for a text that is not an ID in the file form; `path` says where it stands. */
export class FileIdError extends RangeError {
  readonly path: Path;

  constructor(message: string, path: Path = []) {
    super(message);
    this.name = "FileIdError";
    this.path = path;
  }
}

/** The file form of a bare ID: `#` followed by the ID. */
export function toFileId(id: string): string {
  if (typeof id !== "string") throw new TypeError(`an ID is a string, not ${typeof id}`);
  return HASH + id;
}

function bare(text: string, path: Path): string {
  if (typeof text !== "string") throw new TypeError(`an ID is a string, not ${typeof text}`);
  if (!text.startsWith(HASH)) {
    throw new FileIdError(`'${text}' is not written as an ID: it does not start with '#'`, path);
  }
  if (text.length === 1) {
    throw new FileIdError("'#' is not written as an ID: nothing follows the '#'", path);
  }
  return text.slice(1);
}

/**
 * The bare ID that a file's `#id` text writes. Exactly one leading `#` is
 * stripped: `#x` is `x` and `##x` is `#x`.
 *
 * @throws {FileIdError} a `RangeError`, if the text does not start with `#`
 * or nothing follows it.
 */
export function fromFileId(text: string): string {
  return bare(text, []);
}

/** The bare ID of a text in the file form; any other text as it is. */
function leniently(text: string): string {
  return text.startsWith(HASH) && text.length > 1 ? text.slice(1) : text;
}

/**
 * The definitions whose members `value`, held as `definition`, carries: a
 * conversion map is its type's definition and that definition's bases; every
 * other value is its definition alone.
 */
export function definitionsOf(definition: string, value: JsonObject): readonly string[] {
  if (definition !== "ConversionMap") return [definition];
  const kind = value.type;
  if (typeof kind === "string" && MEASURE_VIEWS.includes(kind)) {
    return [kind, "MeasureView", "MapBase"];
  }
  return [typeof kind === "string" ? kind : "", "MapBase"];
}

/** One conversion of a whole manifest, to the file form or to the bare form. */
class Converter {
  readonly #toFile: boolean;
  readonly #strict: boolean;
  readonly #groups: ReadonlySet<string>;
  readonly #schemes: ReadonlySet<string>;

  constructor(manifest: JsonObject, toFile: boolean, strict = true) {
    this.#toFile = toFile;
    this.#strict = strict;
    this.#groups = this.#ids(manifest, "groups");
    this.#schemes = this.#ids(manifest, "schemes");
  }

  /** The bare IDs of a top-level list, read leniently: a check comes later. */
  #ids(manifest: JsonObject, member: string): ReadonlySet<string> {
    const found = new Set<string>();
    const entries = manifest[member];
    if (!Array.isArray(entries)) return found;
    for (const entry of entries) {
      if (!isJsonObject(entry) || typeof entry.id !== "string") continue;
      const text = entry.id;
      if (this.#toFile) found.add(text);
      else if (text.startsWith(HASH) && text.length > 1) found.add(text.slice(1));
    }
    return found;
  }

  id(text: unknown, path: Path): unknown {
    if (typeof text !== "string") return clone(text);
    if (this.#toFile) return toFileId(text);
    return this.#strict ? bare(text, path) : leniently(text);
  }

  ids(value: unknown, path: Path): unknown {
    if (!Array.isArray(value)) return clone(value);
    return value.map((item, index) => this.id(item, [...path, index]));
  }

  scheme(text: unknown, path: Path): unknown {
    if (typeof text !== "string") return clone(text);
    if (this.#toFile) return this.#schemes.has(text) ? toFileId(text) : text;
    if (text.startsWith(HASH)) return this.#strict ? bare(text, path) : leniently(text);
    if (this.#strict && this.#schemes.has(text)) {
      throw new FileIdError(
        `'${text}' names a scheme of this manifest, so it is written '#${text}'`,
        path,
      );
    }
    return text;
  }

  order(value: unknown, path: Path): unknown {
    if (!isJsonObject(value)) return clone(value);
    return objectFrom(
      keysOf(value).map((key) => {
        const renamed = this.id(key, [...path, key]) as string;
        const owner = this.#toFile ? key : renamed;
        const entry = this.#groups.has(owner)
          ? this.ids(value[key], [...path, key])
          : clone(value[key]);
        return [renamed, entry] as const;
      }),
    );
  }

  held(value: unknown, definition: string, path: Path): unknown {
    if (!isJsonObject(value)) return clone(value);
    const shapes = new Map<string, IdShape>();
    const holds = new Map<string, readonly [Holding, string]>();
    for (const name of definitionsOf(definition, value)) {
      for (const [member, shape] of POSITIONS.get(name) ?? []) shapes.set(member, shape);
      for (const [member, held] of HELD.get(name) ?? []) holds.set(member, held);
    }
    return objectFrom(
      keysOf(value).map((key) => {
        const member = value[key];
        const at = [...path, key];
        const shape = shapes.get(key);
        if (shape !== undefined) return [key, this[shape](member, at)] as const;
        const held = holds.get(key);
        if (held !== undefined) return [key, this.holding(member, held[0], held[1], at)] as const;
        return [key, clone(member)] as const;
      }),
    );
  }

  holding(value: unknown, holding: Holding, child: string, path: Path): unknown {
    if (holding === "one") return this.held(value, child, path);
    if (holding === "list" && Array.isArray(value)) {
      return value.map((item, index) => this.held(item, child, [...path, index]));
    }
    if (holding === "values" && isJsonObject(value)) {
      return objectFrom(
        keysOf(value).map((key) => [key, this.held(value[key], child, [...path, key])] as const),
      );
    }
    return clone(value);
  }
}

/**
 * The manifest with every ID in the file form, `#` + the bare ID. An
 * identifier's `scheme` gains the `#` where it names a scheme of the
 * manifest, a value of `graphical.order` where its key names a group.
 */
export function withFileIds<T>(manifest: T): T {
  if (!isJsonObject(manifest)) return clone(manifest);
  return new Converter(manifest, true).held(manifest, "Manifest", []) as T;
}

/**
 * The manifest with every ID bare, read from its file form `#id`. An
 * identifier's `scheme` without `#` is an absolute URI and stays as it is; a
 * timeline's entry in `graphical.order` holds band words, which stay as they
 * are.
 *
 * @throws {FileIdError} a `RangeError` with the `path` of the first text
 * that is not an ID in the file form, or of an identifier's `scheme` written
 * without `#` that names a scheme of the manifest.
 */
export function withBareIds<T>(manifest: T): T {
  if (!isJsonObject(manifest)) return clone(manifest);
  return new Converter(manifest, false).held(manifest, "Manifest", []) as T;
}

/**
 * `withBareIds` that keeps every text not in the file form as it is: for a
 * check of one part of a manifest, which must not refuse an ID outside that
 * part.
 */
export function lenientlyBareIds<T>(manifest: T): T {
  if (!isJsonObject(manifest)) return clone(manifest);
  return new Converter(manifest, false, false).held(manifest, "Manifest", []) as T;
}
