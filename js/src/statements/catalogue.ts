/**
 * The catalogue: identifier systems, verbs and types, shared data that tools
 * read to offer choices and to print statements in words. The validators
 * never consult it.
 *
 * - `prefixes` names the namespaces of every vocabulary the catalogue uses,
 *   and `aliases` the namespaces read as equal (`https://schema.org/` as
 *   `http://schema.org/`).
 * - An identifier system names its things: each with the template of its
 *   IRIs, the patterns of the URLs that address one, and whether its values
 *   ignore case.
 * - A verb ("performed by") gives, per system, the alternatives of a
 *   pattern: a fragment of a statements container whose slots take a value
 *   (`{id: "?"}` a thing, `"?"` a literal or class IRI, `"?role"` and the
 *   like a named literal). An alternative marked `inverse` is the verb's
 *   inverse reading ("has part" of "part of").
 * - A type ("video") gives its "is a" alternatives per system, the verbs
 *   usually stated of such a thing and its preferred lookup systems.
 *
 * The catalogue is one data file, `catalogue/catalogue.yaml`, shipped with
 * this package (as `@timetoalign/timetoshare/catalogue/catalogue.yaml`, and
 * bundled as `generated/catalogue.ts`) and with the Python package, which
 * reads it the same way (`timetoshare.catalogue`); its schema is
 * `catalogue/catalogue.schema.json`. A thing's URL pattern matches a whole
 * URL and captures the value in its one group; it is compiled as
 * `^(?:pattern)$` with the `u` flag and uses only the syntax Python's `re`
 * reads alike: no named group, no lookbehind, no inline flag.
 */

import { catalogue as shipped } from "../generated/catalogue.js";
import { clone, isJsonObject, type JsonObject } from "../json/value.js";
import { compareCodePoints } from "../serialization/text.js";
import type { PathSegment } from "../validate/diagnostics.js";
import {
  BLANK,
  expandIri,
  isAbsoluteReference,
  isFloat,
  isNode,
  isValueObject,
  type Pair,
  pairs,
  prefixOf,
} from "./statements.js";

/** One alternative of a verb's or a type's pattern in a system. */
export interface Alternative {
  /** A statements fragment: keys `type` or IRIs, every value a one-item list, slots for the value. */
  readonly pattern: JsonObject;
  /** Where the alternative applies: subjects of these types, values of these things. */
  readonly when?: { readonly subject?: readonly string[]; readonly value?: readonly string[] };
  /** Whether the pattern is the verb's inverse reading. */
  readonly inverse?: boolean;
  readonly note?: string;
}

/** A kind of thing an identifier system names, and the URLs that address one. */
export interface CatalogueThing {
  readonly id: string;
  readonly kind: string;
  readonly name: string;
  /** The template of the thing's IRIs, holding `{value}`, or null where it mints none. */
  readonly iri: string | null;
  /** The prefix the thing's IRIs are written with. */
  readonly prefix?: string;
  readonly scheme_uri: string | null;
  /** The LRMoo class of every such thing, or null where the address does not tell. */
  readonly lrmoo_class: string | null;
  /** Whether values are written in lower case: the letters `A` to `Z` are lowered. */
  readonly lowercase: boolean;
  /** Regular expressions, each matching a whole URL and capturing the value in its one group. */
  readonly patterns: readonly string[];
  readonly note?: string;
}

/** How a system's things are looked up. */
export interface Lookup {
  readonly route: "browser" | "server" | "cross_reference" | "database" | "none";
  readonly [key: string]: unknown;
}

/** An identifier system: its things, the prefixes of its vocabulary and its lookup. */
export interface CatalogueSystem {
  readonly id: string;
  readonly name: string;
  readonly prefixes: readonly string[];
  readonly things: readonly CatalogueThing[];
  readonly lookup: Lookup;
  readonly note?: string;
}

/** A verb: its label, and its pattern alternatives per system. */
export interface CatalogueVerb {
  readonly id: string;
  readonly label: string;
  readonly inverse_label?: string;
  readonly patterns: Readonly<Record<string, readonly Alternative[]>>;
}

/** A type of thing: its "is a" alternatives per system, its usual verbs, its lookup systems. */
export interface CatalogueType {
  readonly id: string;
  readonly label: string;
  readonly is_a: Readonly<Record<string, readonly Alternative[]>>;
  readonly verbs: readonly string[];
  readonly lookup: readonly string[];
}

/** The catalogue as read. */
export interface Catalogue {
  readonly prefixes: Readonly<Record<string, string>>;
  readonly aliases: Readonly<Record<string, string>>;
  readonly systems: readonly CatalogueSystem[];
  readonly verbs: readonly CatalogueVerb[];
  readonly types: readonly CatalogueType[];
}

/** What a URL addresses: the system, the thing, the value and the thing's IRI or null. */
export interface Recognition {
  readonly system: string;
  readonly thing: string;
  readonly value: string;
  readonly iri: string | null;
}

/**
 * One verb about one thing: the pairs of a subject that state it, in file
 * order, in as many vocabularies as they use; the expanded IRIs of the
 * things they name, in first-seen order; and the first label among them.
 * A pair no verb reads stands alone with `verb` null.
 */
export interface Rectangle {
  readonly verb: string | null;
  readonly inverse: boolean;
  readonly pairs: readonly Pair[];
  readonly things: readonly string[];
  readonly label: string | null;
}

const OUTSIDE_SUBSET = /\(\?[^:=!]/u;
const BLANK_PATTERN = new RegExp(BLANK, "u");
const SAME_AS = ["http://schema.org/sameAs", "http://www.w3.org/2002/07/owl#sameAs"];

/** Whether a template string is a slot: `?` or a named `?name`. */
function isSlot(value: unknown): value is string {
  return typeof value === "string" && value.startsWith("?");
}

/** The strings of a pattern a prefix may be needed for: keys, `type` items, `id`s. */
function* patternIris(value: unknown): Generator<string> {
  if (Array.isArray(value)) {
    for (const item of value) yield* patternIris(item);
    return;
  }
  if (!isJsonObject(value)) return;
  for (const [key, member] of Object.entries(value)) {
    if (key === "id") {
      if (typeof member === "string" && !isSlot(member)) yield member;
    } else if (key === "type") {
      for (const item of Array.isArray(member) ? member : []) {
        if (typeof item === "string" && !isSlot(item)) yield item;
      }
    } else {
      yield key;
      yield* patternIris(member);
    }
  }
}

function* alternativesOf(
  patterns: Readonly<Record<string, readonly Alternative[]>>,
): Generator<[string, Alternative]> {
  for (const [system, alternatives] of Object.entries(patterns)) {
    for (const alternative of alternatives) yield [system, alternative];
  }
}

function checkedPatterns(thing: CatalogueThing): void {
  for (const pattern of thing.patterns) {
    const where = `pattern '${pattern}' of thing '${thing.id}'`;
    if (OUTSIDE_SUBSET.test(pattern)) {
      throw new Error(
        `${where} uses syntax outside the shared subset; only (?:, (?= and (?! may follow '(?'`,
      );
    }
    let groups: number;
    try {
      groups = (new RegExp(`(?:${pattern})|`, "u").exec("")?.length ?? 1) - 1;
    } catch {
      throw new Error(`${where} is no regular expression`);
    }
    if (groups !== 1) {
      throw new Error(`${where} has ${groups} capturing groups; it needs exactly one`);
    }
  }
}

/**
 * Read a catalogue document and check its cross-references, in this order:
 * no system, thing, verb or type twice; every prefix used declared (the
 * prefixes of the systems' vocabularies, a thing's `prefix` and LRMoo class,
 * every pattern key, `type` item and `id`); every system, thing, verb and
 * type named held; every thing's URL patterns usable. Its shape is not
 * checked here: the shipped file is checked against its schema by the tests.
 * Python's `read_catalogue` raises the same messages.
 *
 * @throws {Error} at the first problem.
 */
export function readCatalogue(document: unknown): Catalogue {
  const catalogue = clone(document) as Catalogue;
  const things = catalogue.systems.flatMap((system) => system.things);
  const twice = (kind: string, ids: readonly string[]): void => {
    const seen = new Set<string>();
    for (const id of ids) {
      if (seen.has(id)) throw new Error(`the catalogue holds the ${kind} '${id}' twice`);
      seen.add(id);
    }
  };
  twice(
    "system",
    catalogue.systems.map((system) => system.id),
  );
  twice(
    "thing",
    things.map((thing) => thing.id),
  );
  twice(
    "verb",
    catalogue.verbs.map((verb) => verb.id),
  );
  twice(
    "type",
    catalogue.types.map((type) => type.id),
  );

  const declared = (prefix: string): void => {
    if (!Object.hasOwn(catalogue.prefixes, prefix)) {
      throw new Error(`the catalogue uses the prefix '${prefix}' without declaring it`);
    }
  };
  const iri = (text: string): void => {
    const prefix = prefixOf(text);
    if (prefix !== null) declared(prefix);
  };
  for (const system of catalogue.systems) {
    for (const prefix of system.prefixes) declared(prefix);
    for (const thing of system.things) {
      if (thing.prefix !== undefined) declared(thing.prefix);
      if (thing.lrmoo_class !== null) iri(thing.lrmoo_class);
    }
  }
  const alternatives = [
    ...catalogue.verbs.flatMap((verb) => [...alternativesOf(verb.patterns)]),
    ...catalogue.types.flatMap((type) => [...alternativesOf(type.is_a)]),
  ];
  for (const [, alternative] of alternatives) {
    for (const text of patternIris(alternative.pattern)) iri(text);
  }

  const systems = new Set(catalogue.systems.map((system) => system.id));
  const thingIds = new Set(things.map((thing) => thing.id));
  const verbs = new Set(catalogue.verbs.map((verb) => verb.id));
  const types = new Set(catalogue.types.map((type) => type.id));
  const named = (ids: Iterable<string>, held: ReadonlySet<string>, what: string): void => {
    for (const id of ids) if (!held.has(id)) throw new Error(what.replace("{}", id));
  };
  named(
    [...alternatives.map(([system]) => system), ...catalogue.types.flatMap((type) => type.lookup)],
    systems,
    "the catalogue names the system '{}', which it does not hold",
  );
  named(
    alternatives.flatMap(([, alternative]) => alternative.when?.value ?? []),
    thingIds,
    "the catalogue names the thing '{}', which no system holds",
  );
  named(
    catalogue.types.flatMap((type) => type.verbs),
    verbs,
    "the catalogue names the verb '{}', which it does not hold",
  );
  named(
    alternatives.flatMap(([, alternative]) => alternative.when?.subject ?? []),
    types,
    "the catalogue names the type '{}', which it does not hold",
  );
  for (const thing of things) checkedPatterns(thing);
  return catalogue;
}

let DEFAULT: Catalogue | undefined;

/** The catalogue of the shipped file `catalogue/catalogue.yaml`. */
export function defaultCatalogue(): Catalogue {
  DEFAULT ??= readCatalogue(shipped);
  return DEFAULT;
}

const HEX_PAIR = /^[0-9A-Fa-f]{2}$/u;
const UTF8 = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });
const CAPITALS = /[A-Z]/gu;
const SCHEME_NAME = /^[A-Za-z][A-Za-z0-9+.-]*:./u;

/**
 * Percent-decode a value as Python's `urllib.parse.unquote` does with strict
 * UTF-8: within each run of ASCII characters a `%` followed by two hexadecimal
 * digits is a byte and any other character its own byte, and the run's bytes
 * are decoded as UTF-8; a run that is not UTF-8 gives `null`.
 */
function percentDecoded(text: string): string | null {
  let result = "";
  let index = 0;
  while (index < text.length) {
    if (text.charCodeAt(index) > 0x7f) {
      result += text[index];
      index += 1;
      continue;
    }
    let end = index;
    while (end < text.length && text.charCodeAt(end) <= 0x7f) end += 1;
    const bytes: number[] = [];
    for (let at = index; at < end; ) {
      const pair = text.slice(at + 1, at + 3);
      if (text[at] === "%" && at + 3 <= end && HEX_PAIR.test(pair)) {
        bytes.push(Number.parseInt(pair, 16));
        at += 3;
      } else {
        bytes.push(text.charCodeAt(at));
        at += 1;
      }
    }
    try {
      result += UTF8.decode(Uint8Array.from(bytes));
    } catch {
      return null;
    }
    index = end;
  }
  return result;
}

/**
 * Return what `url` addresses, or null: the first thing, system by system in
 * catalogue order, one of whose patterns matches the whole URL. The captured
 * value is written as the thing writes it (lowered where `lowercase`); a
 * thing with an IRI template gives the IRI with the value substituted as
 * written, one without gives a value percent-decoded as UTF-8 with
 * underscores for spaces and no IRI. A URL that is no absolute URI is never
 * recognised, nor one whose value is not percent-encoded UTF-8. Python's
 * `recognize` gives the same.
 */
export function recognize(catalogue: Catalogue, url: string): Recognition | null {
  if (!SCHEME_NAME.test(url) || BLANK_PATTERN.test(url)) return null;
  for (const system of catalogue.systems) {
    for (const thing of system.things) {
      for (const pattern of thing.patterns) {
        const captured = new RegExp(`^(?:${pattern})$`, "u").exec(url)?.[1];
        if (captured === undefined) continue;
        const written = (value: string): string =>
          thing.lowercase ? value.replace(CAPITALS, (letter) => letter.toLowerCase()) : value;
        if (thing.iri !== null) {
          const value = written(captured);
          return {
            system: system.id,
            thing: thing.id,
            value,
            iri: thing.iri.split("{value}").join(value),
          };
        }
        const decoded = percentDecoded(captured);
        if (decoded === null) return null;
        return {
          system: system.id,
          thing: thing.id,
          value: written(decoded.replaceAll(" ", "_")),
          iri: null,
        };
      }
    }
  }
  return null;
}

/** What `instantiate` takes besides the verb, the system and the value. */
export interface InstantiateOptions {
  /** The index of the alternative in the system, 0 by default. */
  readonly alternative?: number;
  /** The label every thing slot is given. */
  readonly label?: string;
  /** The values of the named slots, by name without `?`. */
  readonly slots?: Readonly<Record<string, unknown>>;
}

/**
 * The pairs that state `verb` in `system` with `value`: the alternative's
 * pattern with `{id: "?"}` as `{id: value}` (and `label` after it where
 * given), `"?"` as `value` and `"?name"` as `slots[name]`; its keys in
 * code-point order, each `type` item a pair `["type", iri]`.
 *
 * @throws {Error} if the catalogue has no such verb, no or not that many
 * alternatives in the system, or a named slot has no value.
 */
export function instantiate(
  catalogue: Catalogue,
  verb: string,
  system: string,
  value: unknown,
  options: InstantiateOptions = {},
): Pair[] {
  const found = catalogue.verbs.find((candidate) => candidate.id === verb);
  if (found === undefined) throw new Error(`the catalogue has no verb '${verb}'`);
  const alternatives = Object.hasOwn(found.patterns, system) ? (found.patterns[system] ?? []) : [];
  if (alternatives.length === 0) {
    throw new Error(`the verb '${verb}' has no pattern in '${system}'`);
  }
  const index = options.alternative ?? 0;
  const alternative = alternatives[index];
  if (alternative === undefined) {
    throw new Error(`the verb '${verb}' has ${alternatives.length} patterns in '${system}'`);
  }
  const fill = (template: unknown): unknown => {
    if (Array.isArray(template)) return template.map(fill);
    if (isSlot(template)) {
      if (template === "?") return clone(value);
      const name = template.slice(1);
      const slots = options.slots ?? {};
      if (!Object.hasOwn(slots, name)) {
        throw new Error(`the pattern of '${verb}' in '${system}' needs a value for '?${name}'`);
      }
      return clone(slots[name]);
    }
    if (!isJsonObject(template)) return template;
    const filled: JsonObject = {};
    for (const [key, member] of Object.entries(template)) {
      filled[key] = fill(member);
      if (key === "id" && member === "?" && options.label !== undefined) {
        filled.label = options.label;
      }
    }
    return filled;
  };
  const pattern = fill(alternative.pattern) as JsonObject;
  const result: Pair[] = [];
  for (const key of Object.keys(pattern).sort(compareCodePoints)) {
    const values = pattern[key];
    for (const item of Array.isArray(values) ? values : []) result.push([key, item]);
  }
  return result;
}

/** The keys of a node that hold no pairs, and its `type`, which the reading takes apart. */
const NOT_PAIRED = new Set(["id", "label", "provenance", "type"]);

/**
 * How a catalogue reads the pairs of one manifest: its own strings expanded
 * by its prefixes, the manifest's by the manifest's `@context`, both with the
 * catalogue's aliases applied.
 */
class Reading {
  readonly #catalogue: Catalogue;
  readonly #context: unknown;

  constructor(catalogue: Catalogue, context: unknown) {
    this.#catalogue = catalogue;
    this.#context = context;
  }

  aliased(iri: string): string {
    for (const [from, to] of Object.entries(this.#catalogue.aliases)) {
      if (iri.startsWith(from)) return to + iri.slice(from.length);
    }
    return iri;
  }

  /** An IRI of the catalogue (`type` is `rdf:type`). */
  own(text: string): string {
    return this.aliased(expandIri(this.#catalogue.prefixes, text) ?? text);
  }

  /** An IRI of the manifest (`type` is `rdf:type`). */
  held(text: string): string {
    return this.aliased(expandIri(this.#context, text) ?? text);
  }

  /** A node's `id` as its IRI; a relative reference as written. */
  reference(text: string): string {
    return isAbsoluteReference(text) ? this.held(text) : text;
  }

  constant(template: unknown, value: unknown): boolean {
    if (typeof template === "string" && typeof value === "string") {
      return (
        template === value ||
        (isAbsoluteReference(template) && this.own(template) === this.held(value))
      );
    }
    return template === value;
  }

  /**
   * The number of constants by which a template matches a value, or null. A
   * slot matches a literal or value object (never a node or ordered values);
   * a node template's `id` matches by IRI, each of its `type` items must be
   * among the value's (`"?"` wants any), and each other key is matched by
   * `member`.
   */
  matches(template: unknown, value: unknown): number | null {
    if (isSlot(template)) {
      const literal =
        typeof value === "string" ||
        typeof value === "boolean" ||
        typeof value === "bigint" ||
        (typeof value === "number" && Number.isInteger(value)) ||
        isFloat(value) ||
        isValueObject(value);
      return literal ? 0 : null;
    }
    if (!isJsonObject(template)) return this.constant(template, value) ? 1 : null;
    if (!isNode(value)) return null;
    let count = 0;
    for (const [key, member] of Object.entries(template)) {
      if (key === "id") {
        if (typeof value.id !== "string") return null;
        if (member !== "?") {
          if (typeof member !== "string" || this.own(member) !== this.reference(value.id)) {
            return null;
          }
          count += 1;
        }
      } else if (key === "type") {
        const held = (Array.isArray(value.type) ? value.type : [])
          .filter((item): item is string => typeof item === "string")
          .map((item) => this.held(item));
        for (const wanted of Array.isArray(member) ? member : []) {
          if (wanted === "?") {
            if (held.length === 0) return null;
          } else if (typeof wanted === "string" && held.includes(this.own(wanted))) {
            count += 1;
          } else {
            return null;
          }
        }
      } else {
        const found = this.member(key, member, value);
        if (found === null) return null;
        count += found;
      }
    }
    return count;
  }

  /**
   * How a node's values under a template key match the key's template: the
   * best count of any template item against any value of every key of the
   * node expanding to the same IRI, counted once; null when none matches.
   */
  member(key: string, templates: unknown, node: JsonObject): number | null {
    const iri = this.own(key);
    let best: number | null = null;
    for (const [held, values] of Object.entries(node)) {
      if (NOT_PAIRED.has(held) || this.held(held) !== iri || !Array.isArray(values)) continue;
      for (const value of values) {
        for (const template of Array.isArray(templates) ? templates : []) {
          const found = this.matches(template, value);
          if (found !== null && (best === null || found > best)) best = found;
        }
      }
    }
    return best;
  }

  verbOf(property: string, value: unknown): [verb: string, inverse: boolean] | null {
    const iri = this.held(property);
    let best: [string, boolean] | null = null;
    let most = -1;
    for (const verb of this.#catalogue.verbs) {
      for (const [, alternative] of alternativesOf(verb.patterns)) {
        for (const [key, templates] of Object.entries(alternative.pattern)) {
          if (this.own(key) !== iri || !Array.isArray(templates)) continue;
          for (const template of templates) {
            const found = this.matches(template, value);
            if (found !== null && found > most) {
              best = [verb.id, alternative.inverse === true];
              most = found;
            }
          }
        }
      }
    }
    return best;
  }

  /**
   * The IRIs of the things a pair names: a `type` pair's class; a node's `id`
   * where it has one, then the `id`s under its `schema:sameAs` and
   * `owl:sameAs`.
   */
  things([property, value]: Pair): string[] {
    if (property === "type" && typeof value === "string") return [this.held(value)];
    if (!isNode(value)) return [];
    const found = typeof value.id === "string" ? [this.reference(value.id)] : [];
    for (const [key, items] of Object.entries(value)) {
      if (NOT_PAIRED.has(key) || !SAME_AS.includes(this.held(key)) || !Array.isArray(items)) {
        continue;
      }
      for (const item of items) {
        if (isNode(item) && typeof item.id === "string") found.push(this.reference(item.id));
      }
    }
    return found;
  }
}

/**
 * The verb a pair states and whether it is the verb's inverse reading, or
 * null: among the alternatives whose key expands (aliases applied) to the
 * property's IRI (`type` and an expanded `rdf:type` alike) and whose template
 * matches the value, the one with most constants, ties to the first in
 * catalogue order. `context` is the manifest's `@context`.
 */
export function verbOf(
  catalogue: Catalogue,
  context: unknown,
  property: string,
  value: unknown,
): [verb: string, inverse: boolean] | null {
  return new Reading(catalogue, context).verbOf(property, value);
}

/**
 * The rectangles of a subject: its pairs, each read by `verbOf`, joined
 * where they state the same verb the same way and are both "is a", share a
 * thing, or carry equal string `label`s on both value nodes (transitively); a
 * pair no verb reads stands alone. The "is a" rectangle comes first, empty
 * where nothing is stated; then the others in the order of their first pair. A rectangle's pairs keep file order, its
 * things first-seen order, its label is the first node label among its
 * pairs.
 *
 * @throws {Error} if the path addresses no element and no value node.
 */
export function rectangles(
  catalogue: Catalogue,
  manifest: unknown,
  subject: readonly PathSegment[],
): Rectangle[] {
  const reading = new Reading(catalogue, isJsonObject(manifest) ? manifest["@context"] : undefined);
  const read = pairs(manifest, subject).map((pair) => ({
    pair,
    verb: reading.verbOf(pair[0], pair[1]),
    things: reading.things(pair),
    label: isNode(pair[1]) && typeof pair[1].label === "string" ? pair[1].label : null,
  }));
  const parent = read.map((_, index) => index);
  const root = (index: number): number => {
    let at = index;
    while (parent[at] !== at) at = parent[at] as number;
    return at;
  };
  for (const [i, left] of read.entries()) {
    for (const [j, right] of read.entries()) {
      if (j <= i || left.verb === null || right.verb === null) continue;
      if (left.verb[0] !== right.verb[0] || left.verb[1] !== right.verb[1]) continue;
      if (
        left.verb[0] === "is_a" ||
        left.things.some((thing) => right.things.includes(thing)) ||
        (left.label !== null && left.label === right.label)
      ) {
        parent[root(j)] = root(i);
      }
    }
  }
  const groups = new Map<number, number[]>();
  for (const index of read.keys()) {
    const key = root(index);
    groups.set(key, [...(groups.get(key) ?? []), index]);
  }
  const built = [...groups.values()].map((members): Rectangle => {
    const first = read[members[0] as number];
    const things: string[] = [];
    for (const index of members) {
      for (const thing of read[index]?.things ?? [])
        if (!things.includes(thing)) things.push(thing);
    }
    const label = members
      .map((index) => read[index]?.pair[1])
      .find((value) => isNode(value) && typeof value.label === "string") as JsonObject | undefined;
    return {
      verb: first?.verb?.[0] ?? null,
      inverse: first?.verb?.[1] ?? false,
      pairs: members.map((index) => read[index]?.pair as Pair),
      things,
      label: label === undefined ? null : (label.label as string),
    };
  });
  const isA = built.filter((rectangle) => rectangle.verb === "is_a" && !rectangle.inverse);
  const others = built.filter((rectangle) => !isA.includes(rectangle));
  const empty: Rectangle = { verb: "is_a", inverse: false, pairs: [], things: [], label: null };
  return [...(isA.length > 0 ? isA : [empty]), ...others];
}
