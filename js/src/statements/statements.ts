/**
 * Statements: property–value pairs about the things a manifest's elements
 * stand for, and their provenance.
 *
 * The manifest, every timeline at any depth and every region may carry
 * `statements`, an object whose keys are `type` ("is a") or property IRIs
 * and whose values are non-empty lists of values, and `provenance`, a list
 * of annotations, each naming one pair of its element with who stated it,
 * when, how, on what basis and its status. A `confirmed` entry annotates a
 * stated pair; a `proposed` or `rejected` one names a pair that is never
 * stated. A value node holds its own pairs directly, as property-IRI keys,
 * and its own `provenance`.
 *
 * A subject is addressed by its path in the manifest: `[]` the manifest,
 * a path ending in `"timelines"`, `"children"` or `"regions"` and an index an
 * element, a path passing through `statements` a value node. Every function
 * is pure: it returns a new value and leaves its arguments as they are. The
 * IRIs of statements and provenance read alike in a manifest's file form and
 * in memory, so every function takes either form. Python's
 * `timetoshare.statements` holds the same functions with the same messages.
 */

import { clone, isJsonFloat, isJsonObject, type JsonObject } from "../json/value.js";
import { compareCodePoints } from "../serialization/text.js";
import { jsonPointer, entries as listed, type PathSegment } from "../validate/diagnostics.js";

/** The namespace of the format's own terms: `method`, `service`, `match`, `status` and their words. */
export const NAMESPACE = "https://timetoalign.github.io/timetoshare/ns#";

const RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";

/** The IRI of "is a", the property `type` stands for. */
export const RDF_TYPE = `${RDF}type`;

/**
 * The format's terms of the inline JSON-LD context, each as the schema's
 * `Context` fixes it. A manifest's `@context` holds exactly these and the
 * prefixes its statements and provenance use.
 */
export const FORMAT_CONTEXT = Object.freeze({
  "@version": 1.1,
  id: "@id",
  type: "@type",
  statements: "@nest",
  list: "@list",
  timelines: "@included",
  children: "@included",
  regions: "@included",
  groups: "@included",
  label: "http://www.w3.org/2000/01/rdf-schema#label",
  provenance: Object.freeze({ "@reverse": `${RDF}subject` }),
  property: Object.freeze({ "@id": `${RDF}predicate`, "@type": "@vocab" }),
  value: `${RDF}object`,
  stated_by: Object.freeze({ "@id": "http://www.w3.org/ns/prov#wasAttributedTo", "@type": "@id" }),
  date: Object.freeze({
    "@id": "http://purl.org/dc/terms/date",
    "@type": "http://www.w3.org/2001/XMLSchema#date",
  }),
  method: Object.freeze({ "@id": `${NAMESPACE}method`, "@type": "@vocab" }),
  service: Object.freeze({ "@id": `${NAMESPACE}service`, "@type": "@id" }),
  basis: Object.freeze({ "@id": "http://www.w3.org/ns/prov#hadPrimarySource", "@type": "@id" }),
  match: Object.freeze({ "@id": `${NAMESPACE}match`, "@type": "@vocab" }),
  note: "http://www.w3.org/2000/01/rdf-schema#comment",
  status: Object.freeze({ "@id": `${NAMESPACE}status`, "@type": "@vocab" }),
  manual: `${NAMESPACE}Manual`,
  reconciled: `${NAMESPACE}Reconciled`,
  imported: `${NAMESPACE}Imported`,
  inferred: `${NAMESPACE}Inferred`,
  confirmed: `${NAMESPACE}Confirmed`,
  proposed: `${NAMESPACE}Proposed`,
  rejected: `${NAMESPACE}Rejected`,
  exact: "http://www.w3.org/2004/02/skos/core#exactMatch",
  close: "http://www.w3.org/2004/02/skos/core#closeMatch",
  broad: "http://www.w3.org/2004/02/skos/core#broadMatch",
  narrow: "http://www.w3.org/2004/02/skos/core#narrowMatch",
  related: "http://www.w3.org/2004/02/skos/core#relatedMatch",
});

/** The statuses of a provenance entry, in the schema's order. */
export const STATUSES = ["confirmed", "proposed", "rejected"] as const;

/** The words of a provenance entry's `method`, in the schema's order; any other method is an IRI. */
export const METHODS = ["manual", "reconciled", "imported", "inferred"] as const;

/** The words of a provenance entry's `match`, in the schema's order. */
export const MATCHES = ["exact", "close", "broad", "narrow", "related"] as const;

/** A provenance entry's status. */
export type Status = (typeof STATUSES)[number];

/**
 * White space and control characters, which no IRI holds: the class the
 * schema's `Iri`, `IriReference` and `PrefixIri` refuse, written out because
 * Python's `\s` and JavaScript's `\s` differ.
 */
export const BLANK =
  "[\\u0000-\\u0020\\u007f-\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff]";

const BLANK_PATTERN = new RegExp(BLANK, "u");
const IRI_SHAPE = /^[A-Za-z][A-Za-z0-9_+.-]*:./u;
const SCHEME_NAME = /^[A-Za-z][A-Za-z0-9_+.-]*:/u;

/** The URI schemes a compact IRI may use without a declared prefix. */
export const URI_SCHEMES: readonly string[] = ["info", "mailto", "tag", "urn"];

/** A subject's path in the manifest: `[]` the manifest, else an element or a value node. */
export type Subject = readonly PathSegment[];

/** One pair of a subject: its property as written and one value. */
export type Pair = readonly [property: string, value: unknown];

const DATE = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/u;
const DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

/**
 * Why `text` is no date written `YYYY-MM-DD` that the Gregorian calendar has,
 * or null where it is one. The calendar's years run from 1 to 9999, its months
 * from 1 to 12, and February has 29 days in a year divisible by 4 and not by
 * 100, or by 400. Python's `ValueError` carries the same message.
 */
export function calendarDateProblem(text: string): string | null {
  const [, year, month, day] = DATE.exec(text) ?? [];
  if (year !== undefined && month !== undefined && day !== undefined) {
    const [y, m, d] = [Number(year), Number(month), Number(day)];
    const leap = (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
    const days = m === 2 && leap ? 29 : DAYS[m - 1];
    if (y >= 1 && days !== undefined && d >= 1 && d <= days) return null;
  }
  return `'${text}' is no Gregorian calendar date written YYYY-MM-DD`;
}

/** Whether `text` has the shape of a compact or absolute IRI (the schema's `Iri`). */
export function isIri(text: string): boolean {
  return IRI_SHAPE.test(text) && !BLANK_PATTERN.test(text);
}

/** Whether a reference is an IRI rather than a relative reference: it begins with a scheme name and `:`. */
export function isAbsoluteReference(text: string): boolean {
  return SCHEME_NAME.test(text);
}

/** The namespace `context` declares for a prefix, or null: a key that is no format term. */
export function declaredPrefix(context: unknown, prefix: string): string | null {
  if (!isJsonObject(context) || Object.hasOwn(FORMAT_CONTEXT, prefix)) return null;
  const namespace = Object.hasOwn(context, prefix) ? context[prefix] : undefined;
  return typeof namespace === "string" ? namespace : null;
}

/**
 * The IRI `text` stands for under `context` (a manifest's `@context`, or any
 * object of prefixes), or null. `type` is `rdf:type`; another format term is
 * the IRI it maps to; `p:rest` is itself where `rest` begins with `//`, the
 * prefix's namespace followed by `rest` where `context` declares `p`, and
 * itself where `p` is `info`, `mailto`, `tag` or `urn`; anything else is
 * null.
 */
export function expandIri(context: unknown, text: string): string | null {
  if (text === "type") return RDF_TYPE;
  if (Object.hasOwn(FORMAT_CONTEXT, text)) {
    const term = (FORMAT_CONTEXT as Readonly<Record<string, unknown>>)[text];
    if (typeof term === "string") return term.startsWith("@") ? null : term;
    const id = isJsonObject(term) ? term["@id"] : undefined;
    return typeof id === "string" ? id : null;
  }
  const colon = text.indexOf(":");
  if (colon < 0) return null;
  const prefix = text.slice(0, colon);
  const rest = text.slice(colon + 1);
  if (rest.startsWith("//")) return text;
  const namespace = declaredPrefix(context, prefix);
  if (namespace !== null) return namespace + rest;
  return URI_SCHEMES.includes(prefix) ? text : null;
}

/**
 * The prefix a compact IRI needs declared, or null: none for a text without
 * `:`, for `p://…` and for the four URI schemes.
 */
export function prefixOf(text: string): string | null {
  const colon = text.indexOf(":");
  if (colon < 0) return null;
  const prefix = text.slice(0, colon);
  if (text.slice(colon + 1).startsWith("//") || URI_SCHEMES.includes(prefix)) return null;
  return prefix;
}

/** An element that may carry statements, with its path and what it is. */
export interface SubjectElement {
  readonly element: JsonObject;
  readonly path: readonly PathSegment[];
  readonly kind: "manifest" | "timeline" | "region";
}

function* timelineSubjects(
  timeline: unknown,
  path: readonly PathSegment[],
): Generator<SubjectElement> {
  if (!isJsonObject(timeline)) return;
  yield { element: timeline, path, kind: "timeline" };
  for (const [index, region] of listed(timeline, "regions").entries()) {
    if (isJsonObject(region))
      yield { element: region, path: [...path, "regions", index], kind: "region" };
  }
  for (const [index, child] of listed(timeline, "children").entries()) {
    yield* timelineSubjects(child, [...path, "children", index]);
  }
}

/**
 * Every element that may carry statements, in subject order: the manifest,
 * then root by root the timeline, its regions in array order and its
 * children, depth first. Any value is read; what is no object is passed over.
 */
export function* subjectElements(manifest: unknown): Generator<SubjectElement> {
  if (!isJsonObject(manifest)) return;
  yield { element: manifest, path: [], kind: "manifest" };
  for (const [index, root] of listed(manifest, "timelines").entries()) {
    yield* timelineSubjects(root, ["timelines", index]);
  }
}

/** Whether a value is a value object: a literal with `@value`. */
export function isValueObject(value: unknown): value is JsonObject {
  return isJsonObject(value) && Object.hasOwn(value, "@value");
}

/** Whether a value is a list of ordered values, `{list: [...]}`. */
export function isOrderedValues(value: unknown): value is JsonObject {
  return isJsonObject(value) && Object.hasOwn(value, "list");
}

/** Whether a value is a node: an object that is neither a value object nor ordered values. */
export function isNode(value: unknown): value is JsonObject {
  return isJsonObject(value) && !isValueObject(value) && !isOrderedValues(value);
}

/** Whether a value is a float: a `JsonFloat` or a number that is no integer. */
export function isFloat(value: unknown): boolean {
  return isJsonFloat(value) || (typeof value === "number" && !Number.isInteger(value));
}

/** The keys of a node that are not its pairs. */
const NODE_KEYS = new Set(["id", "label", "provenance"]);

/**
 * What the walk of a subject meets, in the order the validator checks it:
 * an IRI, a reference (an IRI or a relative reference), a date, a float, a
 * node naming an element that holds more than its `id`, and, after a
 * subject's own positions and its provenance's, the subject itself, whose
 * entries are then matched against its pairs.
 */
export type Visit =
  | {
      readonly kind: "iri" | "reference" | "date";
      readonly text: string;
      readonly path: PathSegment[];
    }
  | { readonly kind: "float"; readonly value: unknown; readonly path: PathSegment[] }
  | { readonly kind: "element"; readonly id: string; readonly path: PathSegment[] }
  | {
      readonly kind: "subject";
      readonly owner: JsonObject;
      readonly node: boolean;
      readonly path: PathSegment[];
    };

function* visitIris(
  items: unknown,
  path: readonly PathSegment[],
  kind: "iri" | "reference",
): Generator<Visit> {
  if (!Array.isArray(items)) return;
  for (const [index, item] of items.entries()) {
    if (typeof item === "string") yield { kind, text: item, path: [...path, index] };
  }
}

/** Visit one value of a pair. */
export function* visitValue(value: unknown, path: readonly PathSegment[]): Generator<Visit> {
  if (isFloat(value)) {
    yield { kind: "float", value, path: [...path] };
    return;
  }
  if (isValueObject(value)) {
    const type = value["@type"];
    if (typeof type === "string") yield { kind: "iri", text: type, path: [...path, "@type"] };
    return;
  }
  if (isOrderedValues(value)) {
    const items = value.list;
    if (Array.isArray(items)) {
      for (const [index, item] of items.entries())
        yield* visitValue(item, [...path, "list", index]);
    }
    return;
  }
  if (!isJsonObject(value)) return;
  const id = value.id;
  if (typeof id === "string") {
    yield { kind: "reference", text: id, path: [...path, "id"] };
    if (id.startsWith("#") && Object.keys(value).length > 1) {
      yield { kind: "element", id, path: [...path] };
    }
  }
  yield* visitSubject(value, path, true);
}

/** The pairs' container of a subject: an element's `statements`, a node's own keys. */
function containerOf(owner: JsonObject, node: boolean): [JsonObject | null, PathSegment[]] {
  if (node) return [owner, []];
  const container = owner.statements;
  return [isJsonObject(container) ? container : null, ["statements"]];
}

/** The property keys of a container in code-point order; a node's `id`, `label`, `provenance` excluded. */
function propertyKeys(container: JsonObject, node: boolean): string[] {
  return Object.keys(container)
    .filter((key) => !(node && NODE_KEYS.has(key)))
    .sort(compareCodePoints);
}

/**
 * Visit a subject: its container's keys in code-point order (each `type`
 * item an IRI; any other key an IRI, then each of its values), then each
 * provenance entry's keys in code-point order (`basis` references, `date`,
 * `method` an IRI unless one of the four words, `property` an IRI, `service`
 * a reference, `stated_by` references, `value` a value), then the subject.
 */
export function* visitSubject(
  owner: JsonObject,
  path: readonly PathSegment[],
  node: boolean,
): Generator<Visit> {
  const [container, at] = containerOf(owner, node);
  if (container !== null) {
    const base = [...path, ...at];
    for (const key of propertyKeys(container, node)) {
      if (key === "type") {
        yield* visitIris(container.type, [...base, "type"], "iri");
        continue;
      }
      yield { kind: "iri", text: key, path: [...base, key] };
      const values = container[key];
      if (!Array.isArray(values)) continue;
      for (const [index, value] of values.entries())
        yield* visitValue(value, [...base, key, index]);
    }
  }
  for (const [index, entry] of listed(owner, "provenance").entries()) {
    if (!isJsonObject(entry)) continue;
    const at = [...path, "provenance", index];
    for (const key of Object.keys(entry).sort(compareCodePoints)) {
      const member = entry[key];
      if (key === "basis" || key === "stated_by")
        yield* visitIris(member, [...at, key], "reference");
      else if (key === "date" && typeof member === "string") {
        yield { kind: "date", text: member, path: [...at, key] };
      } else if (key === "method" && typeof member === "string") {
        if (!(METHODS as readonly string[]).includes(member)) {
          yield { kind: "iri", text: member, path: [...at, key] };
        }
      } else if (key === "property" && typeof member === "string") {
        yield { kind: "iri", text: member, path: [...at, key] };
      } else if (key === "service" && typeof member === "string") {
        yield { kind: "reference", text: member, path: [...at, key] };
      } else if (key === "value") yield* visitValue(member, [...at, key]);
    }
  }
  yield { kind: "subject", owner, node, path: [...path] };
}

/** Every position of every subject's statements and provenance, in subject order. */
export function* visitManifest(manifest: unknown): Generator<Visit> {
  for (const { element, path } of subjectElements(manifest))
    yield* visitSubject(element, path, false);
}

/**
 * The names of the prefixes a manifest's statements and provenance use,
 * sorted: the `p` of every `p:rest` at an IRI position of every subject
 * (`rest` not beginning with `//`, `p` none of `info`, `mailto`, `tag` and
 * `urn`; a relative reference and a method word use none). Python's
 * `used_prefixes` gives the same list.
 */
export function usedPrefixes(manifest: unknown): string[] {
  const found = new Set<string>();
  for (const visit of visitManifest(manifest)) {
    if (visit.kind !== "iri" && visit.kind !== "reference") continue;
    if (visit.kind === "reference" && !isAbsoluteReference(visit.text)) continue;
    const prefix = prefixOf(visit.text);
    if (prefix !== null) found.add(prefix);
  }
  return [...found].sort(compareCodePoints);
}

/**
 * The manifest with its `@context` made from the format's terms and the
 * prefixes its statements and provenance use, each prefix's namespace taken
 * from the manifest's own `@context` where it declares it, else from
 * `prefixes`. A prefix no statement uses is dropped. The context replaces the
 * manifest's in place, or is added last.
 *
 * @throws {Error} if a prefix is declared in neither.
 */
export function withContext<T>(manifest: T, prefixes: Readonly<Record<string, string>>): T {
  const result: unknown = clone(manifest);
  if (!isJsonObject(result)) return result as T;
  const own = result["@context"];
  const context: JsonObject = clone({ ...FORMAT_CONTEXT });
  for (const prefix of usedPrefixes(result)) {
    const namespace =
      declaredPrefix(own, prefix) ??
      (Object.hasOwn(prefixes, prefix) ? (prefixes[prefix] ?? null) : null);
    if (namespace === null) {
      throw new Error(
        `the prefix '${prefix}' is declared neither in the manifest's @context nor in the given prefixes`,
      );
    }
    context[prefix] = namespace;
  }
  result["@context"] = context;
  return result as T;
}

const LOCAL_NAME = /^[A-Za-z0-9_][A-Za-z0-9_.-]*$/u;

/** The number of code points of a text, as Python's `len` counts them. */
function codePoints(text: string): number {
  return [...text].length;
}

/**
 * `iri` written `name:rest` with one of `prefixes`, or as given. Where a
 * namespace of `aliases` (the first in its order) begins `iri`, it is first
 * replaced by the namespace it is read as. Among the prefixes whose
 * namespace begins the IRI so read and leaves a rest of letters, digits,
 * `_`, `.` and `-` that does not begin with `.` or `-`, the longest
 * namespace (in code points) wins, a tie going to the code-point-smaller
 * name. Without such a prefix the IRI is returned as given, no alias
 * applied. Python's `compact_iri` gives the same texts.
 */
export function compactIri(
  prefixes: Readonly<Record<string, string>>,
  iri: string,
  aliases: Readonly<Record<string, string>> = {},
): string {
  let read = iri;
  for (const [namespace, target] of Object.entries(aliases)) {
    if (iri.startsWith(namespace)) {
      read = target + iri.slice(namespace.length);
      break;
    }
  }
  let best: readonly [name: string, namespace: string] | null = null;
  for (const [name, namespace] of Object.entries(prefixes)) {
    if (!read.startsWith(namespace) || !LOCAL_NAME.test(read.slice(namespace.length))) continue;
    if (
      best === null ||
      codePoints(namespace) > codePoints(best[1]) ||
      (codePoints(namespace) === codePoints(best[1]) && compareCodePoints(name, best[0]) < 0)
    ) {
      best = [name, namespace];
    }
  }
  return best === null ? iri : `${best[0]}:${read.slice(best[1].length)}`;
}

/** Renames and drops the references to elements in one copy of a manifest. */
class References {
  readonly #renamed: ReadonlyMap<string, string | null>;

  constructor(renamed: Readonly<Record<string, string | null>>) {
    this.#renamed = new Map(
      Object.entries(renamed).map(([old, renewed]) => [
        `#${old}`,
        renewed === null ? null : `#${renewed}`,
      ]),
    );
  }

  dropped(text: unknown): boolean {
    return typeof text === "string" && this.#renamed.get(text) === null;
  }

  /** A reference renamed; any other value as it is. */
  text(text: unknown): unknown {
    if (typeof text !== "string") return text;
    return this.#renamed.get(text) ?? text;
  }

  /** The values of a list kept, each renamed. */
  values(items: readonly unknown[]): unknown[] {
    return items.filter((value) => this.value(value));
  }

  /** Rename the references of a value in place; whether it is kept. */
  value(value: unknown): boolean {
    if (isOrderedValues(value)) {
      const items = value.list;
      if (!Array.isArray(items)) return true;
      const kept = this.values(items);
      value.list = kept;
      return kept.length > 0;
    }
    if (!isNode(value)) return true;
    if (this.dropped(value.id)) return false;
    if (Object.hasOwn(value, "id")) value.id = this.text(value.id);
    this.subject(value, true);
    return Object.keys(value).length > 0;
  }

  /** Rename the references of a subject's pairs and entries in place. */
  subject(owner: JsonObject, node: boolean): void {
    const [container] = containerOf(owner, node);
    if (container !== null) {
      for (const key of Object.keys(container)) {
        if (key === "type" || (node && NODE_KEYS.has(key))) continue;
        const values = container[key];
        if (!Array.isArray(values)) continue;
        const kept = this.values(values);
        if (kept.length === 0) delete container[key];
        else container[key] = kept;
      }
      if (!node && Object.keys(container).length === 0) delete owner.statements;
    }
    const list = owner.provenance;
    if (Array.isArray(list)) {
      const kept = list.filter((entry) => !isJsonObject(entry) || this.entry(entry));
      if (kept.length === 0) delete owner.provenance;
      else owner.provenance = kept;
    }
  }

  /** Rename the references of an entry in place; whether it is kept. */
  entry(entry: JsonObject): boolean {
    if (Object.hasOwn(entry, "value") && !this.value(entry.value)) return false;
    for (const key of ["basis", "stated_by"]) {
      const items = entry[key];
      if (!Array.isArray(items)) continue;
      const kept = items.filter((item) => !this.dropped(item)).map((item) => this.text(item));
      if (kept.length === 0) delete entry[key];
      else entry[key] = kept;
    }
    if (this.dropped(entry.service)) delete entry.service;
    else if (Object.hasOwn(entry, "service")) {
      entry.service = this.text(entry.service);
    }
    return true;
  }
}

/**
 * The manifest with the references to renamed elements renamed or dropped.
 * The keys and values of `renamed` are bare IDs. A reference is the text
 * `"#" + old` exactly (`other.yaml#old` names an element of another manifest
 * and is none) where statements name things: a node's `id`, a provenance
 * entry's `basis` and `stated_by` items and its `service`, in the statements
 * and provenance of the manifest, of every timeline at any depth and of every
 * region, and of every node within them, a node in an entry's `value`
 * included. Where `renamed[old]` is an ID, each reference becomes
 * `"#" + renamed[old]`. Where it is null, a value that is a node naming the
 * element leaves its list, an entry whose `value` names it leaves
 * `provenance`, a `basis` or `stated_by` item naming it leaves its list and a
 * `service` naming it is deleted; then every list of values, container,
 * `basis`, `stated_by` and `provenance` left empty is deleted, as are a node
 * without `id` and ordered values left without anything. Each reference is
 * renamed once: with `{a: "b", b: "c"}`, `#a` becomes `#b` and `#b` becomes
 * `#c`. The elements' own IDs are never read, so either ID form is taken.
 * Python's `with_references_renamed` gives the same values.
 */
export function withReferencesRenamed<T>(
  manifest: T,
  renamed: Readonly<Record<string, string | null>>,
): T {
  const references = new References(renamed);
  const result = clone(manifest);
  for (const { element } of subjectElements(result)) {
    references.subject(element, false);
  }
  return result;
}

/**
 * The path of the subject an element ID names: `[]` for `null`, the bundle;
 * else the timeline (at any depth) or region whose `id` equals `elementId`
 * as written in this manifest (`#clt_1` in the file form, `clt_1` bare).
 *
 * @throws {Error} if no timeline or region has the ID.
 */
export function subjectPath(manifest: unknown, elementId: string | null): PathSegment[] {
  if (elementId === null) return [];
  for (const { element, path, kind } of subjectElements(manifest)) {
    if (kind !== "manifest" && element.id === elementId) return [...path];
  }
  throw new Error(`no timeline or region of the manifest has the ID '${elementId}'`);
}

/** The value at one step of a path, or undefined where the step leads nowhere. */
function stepInto(value: unknown, step: PathSegment): unknown {
  if (Array.isArray(value)) {
    return typeof step === "number" && Number.isInteger(step) && step >= 0 && step < value.length
      ? value[step]
      : undefined;
  }
  return isJsonObject(value) && typeof step === "string" && Object.hasOwn(value, step)
    ? value[step]
    : undefined;
}

/**
 * The element a subject's path begins with and the length of that prefix:
 * `timelines` then `children` or `regions` steps, each followed by an index,
 * a region ending the walk.
 */
function elementAt(manifest: unknown, subject: Subject): [unknown, number] {
  let target: unknown = manifest;
  let position = 0;
  let expected: readonly PathSegment[] = ["timelines"];
  while (position + 1 < subject.length && expected.includes(subject[position] as PathSegment)) {
    const key = subject[position] as string;
    const list = isJsonObject(target) ? target[key] : undefined;
    target = Array.isArray(list) ? stepInto(list, subject[position + 1] as PathSegment) : undefined;
    if (target === undefined) return [undefined, position];
    position += 2;
    if (key === "regions") break;
    expected = ["children", "regions"];
  }
  return [target, position];
}

/**
 * The object a subject's path addresses, and whether it is a value node: an
 * element's path, or an element's path through its `statements` to a node
 * held in a list (never through a `provenance`, never the container itself).
 */
function resolve(manifest: unknown, subject: Subject): { owner: JsonObject; node: boolean } {
  const missing = new Error(`${jsonPointer(subject)} addresses no element and no value node`);
  const [element, position] = elementAt(manifest, subject);
  if (!isJsonObject(element)) throw missing;
  if (position === subject.length) return { owner: element, node: false };
  const rest = subject.slice(position);
  if (rest[0] !== "statements" || rest.includes("provenance") || typeof rest.at(-1) !== "number") {
    throw missing;
  }
  let value: unknown = element;
  for (const step of rest) value = stepInto(value, step);
  if (!isNode(value)) throw missing;
  return { owner: value, node: true };
}

/** The `@context` of a manifest, or null. */
function contextOf(manifest: unknown): unknown {
  return isJsonObject(manifest) ? (manifest["@context"] ?? null) : null;
}

/** The IRI a property stands for, or the text where it expands to none; `rdf:type` is always "is a". */
function propertyIri(context: unknown, property: string): string {
  return expandIri(context, property) ?? (property === "rdf:type" ? RDF_TYPE : property);
}

/** The IRI a reference stands for: an IRI expanded, a relative reference as written. */
function referenceIri(context: unknown, text: string): string {
  return isAbsoluteReference(text) ? (expandIri(context, text) ?? text) : text;
}

/** Whether two JSON values are equal: numbers by kind and value, objects ignoring key order. */
function jsonEqual(left: unknown, right: unknown): boolean {
  if (isJsonFloat(left) || isJsonFloat(right)) {
    return isJsonFloat(left) && isJsonFloat(right) && Object.is(left.value, right.value);
  }
  if (typeof left === "bigint" || typeof right === "bigint") {
    return (
      (typeof left === "bigint" || Number.isInteger(left)) &&
      (typeof right === "bigint" || Number.isInteger(right)) &&
      BigInt(left as number | bigint) === BigInt(right as number | bigint)
    );
  }
  if (Array.isArray(left) || Array.isArray(right)) {
    return (
      Array.isArray(left) &&
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((item, index) => jsonEqual(item, right[index]))
    );
  }
  if (isJsonObject(left) || isJsonObject(right)) {
    if (!isJsonObject(left) || !isJsonObject(right)) return false;
    const keys = Object.keys(left);
    return (
      keys.length === Object.keys(right).length &&
      keys.every((key) => Object.hasOwn(right, key) && jsonEqual(left[key], right[key]))
    );
  }
  return left === right;
}

/** A node without its top-level `provenance`. */
function withoutProvenance(node: JsonObject): JsonObject {
  const { provenance: _, ...rest } = node;
  return rest;
}

function sameValue(context: unknown, left: unknown, right: unknown): boolean {
  if (isValueObject(left) || isValueObject(right)) {
    if (!isValueObject(left) || !isValueObject(right)) return false;
    const type = (value: JsonObject): unknown =>
      typeof value["@type"] === "string" ? referenceIri(context, value["@type"]) : value["@type"];
    return (
      left["@value"] === right["@value"] &&
      left["@language"] === right["@language"] &&
      type(left) === type(right)
    );
  }
  if (isOrderedValues(left) || isOrderedValues(right)) {
    if (!isOrderedValues(left) || !isOrderedValues(right)) return false;
    const [a, b] = [left.list, right.list];
    return (
      Array.isArray(a) &&
      Array.isArray(b) &&
      a.length === b.length &&
      a.every((item, index) => sameValue(context, item, b[index]))
    );
  }
  if (isJsonObject(left) || isJsonObject(right)) {
    if (!isJsonObject(left) || !isJsonObject(right)) return false;
    const [a, b] = [left.id, right.id];
    if (typeof a === "string" || typeof b === "string") {
      return (
        typeof a === "string" &&
        typeof b === "string" &&
        referenceIri(context, a) === referenceIri(context, b)
      );
    }
    return jsonEqual(withoutProvenance(left), withoutProvenance(right));
  }
  return jsonEqual(left, right);
}

/** A pair's value, a `type` item T read as the thing `{id: T}`; only the key `type` reads so. */
function asThing([property, value]: Pair): unknown {
  return property === "type" && typeof value === "string" ? { id: value } : value;
}

/**
 * Whether two pairs are the same pair under `context`: their properties
 * expand to the same IRI (`type` is `rdf:type`) and their values are equal.
 * Literals are equal with the same JSON type (`true` is not `1`); value
 * objects after expanding `@type`; a node with `id` equals any node with the
 * same expanded `id`, its other keys ignored, and a `type` item T counts as
 * `{id: T}`; nodes without `id` equal as JSON once their top-level
 * `provenance` is dropped; lists item by item. A relative reference compares
 * as written.
 */
export function samePair(context: unknown, left: Pair, right: Pair): boolean {
  if (propertyIri(context, left[0]) !== propertyIri(context, right[0])) return false;
  return sameValue(context, asThing(left), asThing(right));
}

/** The pairs of a subject's container, keys in code-point order, values in list order. */
export function pairsOf(owner: JsonObject, node: boolean): Pair[] {
  const [container] = containerOf(owner, node);
  if (container === null) return [];
  const found: Pair[] = [];
  for (const key of propertyKeys(container, node)) {
    const values = container[key];
    if (!Array.isArray(values)) continue;
    for (const value of values) found.push([key, value]);
  }
  return found;
}

/**
 * The pairs of a subject: its container's keys in code-point order, each key's
 * values in list order, each `type` item a pair `["type", iri]`; a node's
 * pairs are its own IRI keys and `type`.
 *
 * @throws {Error} if the path addresses no element and no value node.
 */
export function pairs(manifest: unknown, subject: Subject): Pair[] {
  const { owner, node } = resolve(manifest, subject);
  return pairsOf(owner, node).map(([key, value]) => [key, clone(value)] as const);
}

/**
 * The provenance entries of a subject, or those of one status.
 *
 * @throws {Error} if the path addresses no element and no value node.
 */
export function entries(manifest: unknown, subject: Subject, status?: Status): JsonObject[] {
  const { owner } = resolve(manifest, subject);
  return listed(owner, "provenance")
    .filter((entry) => status === undefined || entry.status === status)
    .map(clone);
}

/** What `withPair` writes into the confirmed entry: an entry's keys but its pair and status. */
export interface PairProvenance {
  readonly stated_by?: readonly string[];
  readonly date?: string;
  readonly method?: string;
  readonly service?: string;
  readonly basis?: readonly string[];
  readonly match?: (typeof MATCHES)[number];
  readonly note?: string;
}

/** What `withProposal` takes besides the pair. */
export interface ProposalOptions {
  readonly stated_by: readonly string[];
  readonly date: string;
  readonly method: string;
  readonly service?: string;
  readonly basis?: readonly string[];
  readonly match?: (typeof MATCHES)[number];
  readonly note?: string;
}

/** What `withConfirmation` and `withRejection` take besides the pair. */
export interface DecisionOptions {
  readonly stated_by: readonly string[];
  readonly date: string;
}

function checkedProperty(property: string): void {
  if (property !== "type" && !isIri(property)) {
    throw new Error(`'${property}' is no property: write 'type', a compact IRI or an absolute IRI`);
  }
}

function checkedDate(date: unknown): void {
  if (typeof date !== "string") return;
  const problem = calendarDateProblem(date);
  if (problem !== null) throw new Error(problem);
}

/** The property an entry writes for a pair: `type` as `rdf:type`. */
function entryProperty(property: string): string {
  return property === "type" ? "rdf:type" : property;
}

/** The value an entry writes for a pair: a thing by its `id` alone, a type as `{id}`. */
function entryValue(property: string, value: unknown): unknown {
  if (property === "type") return { id: value };
  if (isNode(value) && typeof value.id === "string") return { id: value.id };
  return clone(value);
}

/** The values' list of a property in a container, created last where absent. */
function valuesOf(container: JsonObject, property: string): unknown[] {
  const values = container[property];
  if (Array.isArray(values)) return values;
  const created: unknown[] = [];
  container[property] = created;
  return created;
}

/** The container of a subject, created last where an element has none. */
function containerFor(owner: JsonObject, node: boolean): JsonObject {
  const [container] = containerOf(owner, node);
  if (container !== null) return container;
  const created: JsonObject = {};
  owner.statements = created;
  return created;
}

/** The provenance list of a subject, created last where absent. */
function provenanceOf(owner: JsonObject): unknown[] {
  return valuesOf(owner, "provenance");
}

/** Whether a subject states the pair. */
function states(context: unknown, owner: JsonObject, node: boolean, pair: Pair): boolean {
  return pairsOf(owner, node).some((stated) => samePair(context, stated, pair));
}

function entryPair(entry: JsonObject): Pair {
  return [String(entry.property), entry.value];
}

/** The index of the first entry of the pair whose status is one of `statuses`, or -1. */
function entryIndex(
  context: unknown,
  owner: JsonObject,
  pair: Pair,
  statuses: readonly string[],
): number {
  const list = owner.provenance;
  if (!Array.isArray(list)) return -1;
  return list.findIndex(
    (entry) =>
      isJsonObject(entry) &&
      statuses.includes(String(entry.status)) &&
      samePair(context, entryPair(entry), pair),
  );
}

/** Remove a subject's values and entries a test picks, and every list and container left empty. */
function prune(
  owner: JsonObject,
  node: boolean,
  value: (pair: Pair) => boolean,
  entry: (entry: JsonObject) => boolean,
): void {
  const [container] = containerOf(owner, node);
  if (container !== null) {
    for (const key of propertyKeys(container, node)) {
      const values = container[key];
      if (!Array.isArray(values)) continue;
      const kept = values.filter((item) => !value([key, item]));
      if (kept.length === 0) delete container[key];
      else container[key] = kept;
    }
    if (!node && Object.keys(container).length === 0) delete owner.statements;
  }
  const list = owner.provenance;
  if (Array.isArray(list)) {
    const kept = list.filter((item) => !(isJsonObject(item) && entry(item)));
    if (kept.length === 0) delete owner.provenance;
    else owner.provenance = kept;
  }
}

/** Append a pair's value to a subject's container. */
function stated(owner: JsonObject, node: boolean, property: string, value: unknown): void {
  valuesOf(containerFor(owner, node), property).push(clone(value));
}

/**
 * Return the manifest with the pair stated on the subject: the value appended
 * to the property's list (`type` takes a class IRI), a `proposed` or
 * `rejected` entry of the pair removed. Given `provenance` (an entry's keys
 * but `property`, `value` and `status`), a `confirmed` entry of the pair is
 * appended: its property `rdf:type` for `type`, its value `{id}` for a node
 * with `id` or a type, else the value.
 *
 * @throws {Error} if the property is none, the subject has the pair, the
 * entry's date is no calendar date, or the path addresses no subject.
 */
export function withPair<T>(
  manifest: T,
  subject: Subject,
  property: string,
  value: unknown,
  options: { readonly provenance?: PairProvenance } = {},
): T {
  checkedProperty(property);
  checkedDate(options.provenance?.date);
  const result = clone(manifest);
  const { owner, node } = resolve(result, subject);
  const context = contextOf(result);
  const pair: Pair = [property, value];
  if (states(context, owner, node, pair)) throw new Error(`'${property}' already has this value`);
  stated(owner, node, property, value);
  prune(
    owner,
    node,
    () => false,
    (entry) =>
      (entry.status === "proposed" || entry.status === "rejected") &&
      samePair(context, entryPair(entry), pair),
  );
  if (options.provenance !== undefined) {
    const { property: _p, value: _v, status: _s, ...given } = options.provenance as JsonObject;
    provenanceOf(owner).push({
      ...clone(given),
      property: entryProperty(property),
      value: entryValue(property, value),
      status: "confirmed",
    });
  }
  return result;
}

/**
 * Return the manifest without the pair on the subject: the value and its
 * `confirmed` entry removed; a list, a container or a `provenance` left
 * empty is removed.
 *
 * @throws {Error} if the subject does not have the pair, or the path
 * addresses no subject.
 */
export function withoutPair<T>(manifest: T, subject: Subject, property: string, value: unknown): T {
  checkedProperty(property);
  const result = clone(manifest);
  const { owner, node } = resolve(result, subject);
  const context = contextOf(result);
  const pair: Pair = [property, value];
  if (!states(context, owner, node, pair)) {
    throw new Error(`'${property}' does not have this value`);
  }
  prune(
    owner,
    node,
    (stated) => samePair(context, stated, pair),
    (entry) => entry.status === "confirmed" && samePair(context, entryPair(entry), pair),
  );
  return result;
}

/** Write an entry of the pair in place of the subject's first, else append it. */
function placed(context: unknown, owner: JsonObject, pair: Pair, entry: JsonObject): void {
  const index = entryIndex(context, owner, pair, STATUSES);
  const list = provenanceOf(owner);
  if (index >= 0) list[index] = entry;
  else list.push(entry);
}

/**
 * Return the manifest with the pair proposed for the subject: a `proposed`
 * entry, replacing another entry of the pair in place, else appended; the
 * statements are left as they are.
 *
 * @throws {Error} if the property is none, the subject has the pair, the
 * date is no calendar date, or the path addresses no subject.
 */
export function withProposal<T>(
  manifest: T,
  subject: Subject,
  property: string,
  value: unknown,
  options: ProposalOptions,
): T {
  checkedProperty(property);
  checkedDate(options.date);
  const result = clone(manifest);
  const { owner, node } = resolve(result, subject);
  const context = contextOf(result);
  const pair: Pair = [property, value];
  if (states(context, owner, node, pair)) {
    throw new Error(`'${property}' already has this value; a stated pair is not proposed`);
  }
  const entry: JsonObject = {
    property: entryProperty(property),
    value: entryValue(property, value),
    status: "proposed",
    stated_by: [...options.stated_by],
    date: options.date,
    method: options.method,
  };
  if (options.service !== undefined) entry.service = options.service;
  if (options.basis !== undefined && options.basis.length > 0) entry.basis = [...options.basis];
  if (options.match !== undefined) entry.match = options.match;
  if (options.note !== undefined) entry.note = options.note;
  placed(context, owner, pair, entry);
  return result;
}

/**
 * Return the manifest with a proposed or rejected pair confirmed: the value
 * as given (its label included) appended to the property's list, the entry
 * `confirmed` in place, its `stated_by` and `date` replaced and its other
 * keys kept.
 *
 * @throws {Error} if the subject has no proposed or rejected entry of the
 * pair, already has the pair, the date is no calendar date, or the path
 * addresses no subject.
 */
export function withConfirmation<T>(
  manifest: T,
  subject: Subject,
  property: string,
  value: unknown,
  options: DecisionOptions,
): T {
  checkedProperty(property);
  checkedDate(options.date);
  const result = clone(manifest);
  const { owner, node } = resolve(result, subject);
  const context = contextOf(result);
  const pair: Pair = [property, value];
  const index = entryIndex(context, owner, pair, ["proposed", "rejected"]);
  if (index < 0) throw new Error(`no proposal or rejection of this value of '${property}'`);
  if (states(context, owner, node, pair)) throw new Error(`'${property}' already has this value`);
  stated(owner, node, property, value);
  const entry = provenanceOf(owner)[index] as JsonObject;
  entry.status = "confirmed";
  entry.stated_by = [...options.stated_by];
  entry.date = options.date;
  return result;
}

/**
 * Return the manifest with the pair rejected for the subject: a stated pair
 * removed, and the pair's entry (appended where it has none) `rejected` with
 * the given `stated_by`, `date` and, where given, `note`; its other keys,
 * `method` among them, are kept.
 *
 * @throws {Error} if the property is none, the date is no calendar date, or
 * the path addresses no subject.
 */
export function withRejection<T>(
  manifest: T,
  subject: Subject,
  property: string,
  value: unknown,
  options: DecisionOptions & { readonly note?: string },
): T {
  checkedProperty(property);
  checkedDate(options.date);
  const result = clone(manifest);
  const { owner, node } = resolve(result, subject);
  const context = contextOf(result);
  const pair: Pair = [property, value];
  const index = entryIndex(context, owner, pair, STATUSES);
  const entry: JsonObject =
    index >= 0
      ? (provenanceOf(owner)[index] as JsonObject)
      : { property: entryProperty(property), value: entryValue(property, value) };
  entry.status = "rejected";
  entry.stated_by = [...options.stated_by];
  entry.date = options.date;
  if (options.note !== undefined) entry.note = options.note;
  if (index < 0) provenanceOf(owner).push(entry);
  prune(
    owner,
    node,
    (stated) => samePair(context, stated, pair),
    () => false,
  );
  return result;
}
