/**
 * Description rules: the dates and references of links, and their
 * unregistered terms. The schema checks the shape of every link; four rules
 * reach beyond it and are checked here: a scheme's ID is unique across every
 * ID of the manifest, and, link by link, an assertion's `asserted_on` names a
 * day of the Gregorian calendar, an identifier's `scheme` names a scheme of
 * the manifest or is an absolute URI, and a part slot's `represented_by`
 * names a timeline (at any depth) or a region of the manifest. The open
 * vocabularies are never refused: a bare term outside the words registered
 * for its key is listed as a warning. Python's
 * `timetoshare.validation.description` holds the same rules.
 *
 * The walks of this module read the description layer of any manifest: the
 * arrays it consists of (`descriptionArrays`) and the IDs its rules read
 * outside it are found whatever the rest of the manifest holds, so a reader of
 * part of a manifest can check its description layer alone.
 */

import {
  ABSENCE_REASONS,
  calendarDateProblem,
  METHODS,
  PARTS_RELATIONS,
  RELATIONS,
} from "../description/link.js";
import { isAbsoluteUri } from "../description/registry.js";
import { isJsonObject, type JsonObject } from "../json/value.js";
import {
  comparePaths,
  duplicateProblem,
  entries,
  type PathSegment,
  SchemaValidationError,
  stringId,
  text,
  timestampsOf,
  treeIds,
} from "./diagnostics.js";

/** A bare term outside the words registered for its key, at `path`. */
export interface UnregisteredTerm {
  readonly path: readonly PathSegment[];
  readonly term: string;
}

type Found = [JsonObject, PathSegment[]];

/**
 * An array of the description layer: the definition declaring it, its member,
 * its value, its path and the ID of the nearest element holding it, if any.
 */
export interface DescriptionArray {
  readonly definition: "Manifest" | "Timeline" | "Region";
  readonly member: "schemes" | "links";
  readonly value: unknown;
  readonly path: readonly PathSegment[];
  readonly owner: string | null;
}

/** The element's own ID where it holds a string one, else its holder's. */
function owned(element: unknown, owner: string | null): string | null {
  return stringId(element) ?? owner;
}

function* timelineArrays(
  timeline: unknown,
  path: readonly PathSegment[],
  holder: string | null,
): Generator<DescriptionArray> {
  if (!isJsonObject(timeline)) return;
  const owner = owned(timeline, holder);
  if (Object.hasOwn(timeline, "links")) {
    yield {
      definition: "Timeline",
      member: "links",
      value: timeline.links,
      path: [...path, "links"],
      owner,
    };
  }
  for (const [index, region] of entries(timeline, "regions").entries()) {
    if (isJsonObject(region) && Object.hasOwn(region, "links")) {
      yield {
        definition: "Region",
        member: "links",
        value: region.links,
        path: [...path, "regions", index, "links"],
        owner: owned(region, owner),
      };
    }
  }
  for (const [index, child] of entries(timeline, "children").entries()) {
    yield* timelineArrays(child, [...path, "children", index], owner);
  }
}

/**
 * Every array of the description layer that a manifest states: the
 * manifest's `schemes`, then its `links`, then root by root each timeline's
 * `links`, its regions' `links` in array order and its children's, depth
 * first, whatever their values; an element that is no object states none.
 * Each comes with the schema definition declaring it and the ID of the
 * nearest element holding it, as the finite rule names an owner.
 */
export function* descriptionArrays(manifest: unknown): Generator<DescriptionArray> {
  if (!isJsonObject(manifest)) return;
  const owner = stringId(manifest);
  for (const member of ["schemes", "links"] as const) {
    if (Object.hasOwn(manifest, member)) {
      yield { definition: "Manifest", member, value: manifest[member], path: [member], owner };
    }
  }
  for (const [index, root] of entries(manifest, "timelines").entries()) {
    yield* timelineArrays(root, ["timelines", index], owner);
  }
}

function* timelineLinks(timeline: JsonObject, path: readonly PathSegment[]): Generator<Found> {
  for (const [index, link] of entries(timeline, "links").entries()) {
    yield [link, [...path, "links", index]];
  }
  for (const [index, region] of entries(timeline, "regions").entries()) {
    for (const [number, link] of entries(region, "links").entries()) {
      yield [link, [...path, "regions", index, "links", number]];
    }
  }
  for (const [index, child] of entries(timeline, "children").entries()) {
    yield* timelineLinks(child, [...path, "children", index]);
  }
}

/**
 * Every link of a manifest with its path, in document order: the manifest's
 * own links, then root by root each timeline's links, its regions' links in
 * array order and its children's, depth first.
 */
export function* linksOf(manifest: JsonObject): Generator<Found> {
  for (const [index, link] of entries(manifest, "links").entries()) yield [link, ["links", index]];
  for (const [index, root] of entries(manifest, "timelines").entries()) {
    yield* timelineLinks(root, ["timelines", index]);
  }
}

/** The IDs a part slot may name: every timeline's, at any depth, and region's. */
function targetsOf(manifest: JsonObject): Set<string> {
  const found = new Set<string>();
  const add = (id: string | null): void => {
    if (id !== null) found.add(id);
  };
  const visit = (timeline: unknown): void => {
    add(stringId(timeline));
    for (const region of entries(timeline, "regions")) add(stringId(region));
    for (const child of entries(timeline, "children")) visit(child);
  };
  for (const root of entries(manifest, "timelines")) visit(root);
  return found;
}

/**
 * Yield the scheme IDs another ID of the manifest holds, as the identity rules
 * do: each scheme's ID against every ID before it in the order of the identity
 * rules (the roots' trees, the groups, the MeasureMaps, the named timestamps,
 * the earlier schemes), at the later `id`; then the manifest ID where it is a
 * scheme's ID. The schemes are taken as schema-checked; every other ID is read
 * wherever it is a string.
 */
export function* schemeProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const first = new Map<string, PathSegment[]>();
  const note = (id: string | null, path: PathSegment[]): void => {
    if (id !== null && !first.has(id)) first.set(id, path);
  };
  for (const [index, root] of entries(manifest, "timelines").entries()) {
    for (const [id, path] of treeIds(root, ["timelines", index])) note(id, path);
  }
  const keyed: [PathSegment[], JsonObject[]][] = [
    [["groups"], entries(manifest, "groups")],
    [["measure_maps"], entries(manifest, "measure_maps")],
    [["graphical", "timestamps"], timestampsOf(manifest)],
  ];
  for (const [key, list] of keyed) {
    for (const [index, entry] of list.entries()) note(stringId(entry), [...key, index, "id"]);
  }
  const schemes = new Set<string>();
  for (const [index, scheme] of entries(manifest, "schemes").entries()) {
    const id = text(scheme, "id");
    const path = ["schemes", index, "id"];
    schemes.add(id);
    const earlier = first.get(id);
    if (earlier === undefined) first.set(id, path);
    else yield duplicateProblem(id, path, earlier);
  }
  const manifestId = stringId(manifest);
  if (manifestId !== null && schemes.has(manifestId)) {
    yield duplicateProblem(manifestId, ["id"], first.get(manifestId) ?? [], "manifest_id");
  }
}

function* dateProblems(
  owner: JsonObject,
  path: readonly PathSegment[],
): Generator<SchemaValidationError> {
  const { assertion } = owner;
  const date = isJsonObject(assertion) ? assertion.asserted_on : null;
  const problem = typeof date === "string" ? calendarDateProblem(date) : null;
  if (problem !== null) {
    yield new SchemaValidationError(
      "calendar_date",
      [...path, "assertion", "asserted_on"],
      problem,
    );
  }
}

/** The date of an owner's assertion, then its identifiers' schemes. */
function* ownerProblems(
  owner: JsonObject,
  path: readonly PathSegment[],
  schemes: ReadonlySet<string>,
): Generator<SchemaValidationError> {
  yield* dateProblems(owner, path);
  for (const [index, identifier] of entries(owner, "identifiers").entries()) {
    const scheme = text(identifier, "scheme");
    if (!schemes.has(scheme) && !isAbsoluteUri(scheme)) {
      yield new SchemaValidationError(
        "dangling_target",
        [...path, "identifiers", index, "scheme"],
        `'${scheme}' names no scheme of this manifest and is no absolute URI`,
      );
    }
  }
}

/**
 * Yield the impossible dates and dangling references of links, link by link:
 * within a link its assertion's date and its identifiers' schemes, then each
 * part slot's assertion's date, identifiers' schemes and `represented_by`
 * entries, then each `part_of` entry's assertion's date and identifiers'
 * schemes. The links and schemes are taken as schema-checked; the timelines
 * and regions a slot may name are read wherever their `id` is a string.
 */
export function* linkProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const schemes = new Set(entries(manifest, "schemes").map((scheme) => text(scheme, "id")));
  const targets = targetsOf(manifest);
  for (const [link, path] of linksOf(manifest)) {
    yield* ownerProblems(link, path, schemes);
    for (const [index, slot] of entries(link, "parts").entries()) {
      const at = [...path, "parts", index];
      yield* ownerProblems(slot, at, schemes);
      const represented = Array.isArray(slot.represented_by) ? slot.represented_by : [];
      for (const [number, target] of (represented as string[]).entries()) {
        if (!targets.has(target)) {
          yield new SchemaValidationError(
            "dangling_target",
            [...at, "represented_by", number],
            `'${target}' names no timeline or region of this manifest`,
          );
        }
      }
    }
    for (const [index, entry] of entries(link, "part_of").entries()) {
      yield* ownerProblems(entry, [...path, "part_of", index], schemes);
    }
  }
}

function* term(
  owner: JsonObject,
  key: string,
  words: readonly string[],
  path: readonly PathSegment[],
): Generator<UnregisteredTerm> {
  const value = owner[key];
  if (typeof value === "string" && !value.includes(":") && !words.includes(value)) {
    yield { path: [...path, key], term: value };
  }
}

function* method(owner: JsonObject, path: readonly PathSegment[]): Generator<UnregisteredTerm> {
  const { assertion } = owner;
  if (isJsonObject(assertion)) yield* term(assertion, "method", METHODS, [...path, "assertion"]);
}

/**
 * Return every bare term outside the words registered for its key, sorted by
 * path. A term holding a colon is an extension term and never listed. The
 * keys read are a link's `relation` and `parts_relation`, every assertion's
 * `method`, a part slot's `absent` and a `part_of` entry's `parts_relation`.
 * The manifest is taken as valid.
 */
export function unregisteredTermsOf(manifest: JsonObject): UnregisteredTerm[] {
  const found: UnregisteredTerm[] = [];
  for (const [link, path] of linksOf(manifest)) {
    found.push(...term(link, "relation", RELATIONS, path));
    found.push(...method(link, path));
    found.push(...term(link, "parts_relation", PARTS_RELATIONS, path));
    for (const [index, slot] of entries(link, "parts").entries()) {
      const at = [...path, "parts", index];
      found.push(...term(slot, "absent", ABSENCE_REASONS, at));
      found.push(...method(slot, at));
    }
    for (const [index, entry] of entries(link, "part_of").entries()) {
      const at = [...path, "part_of", index];
      found.push(...term(entry, "parts_relation", PARTS_RELATIONS, at));
      found.push(...method(entry, at));
    }
  }
  return found.sort((a, b) => comparePaths(a.path, b.path));
}
