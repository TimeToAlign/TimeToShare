/**
 * Description rules: what a link's references name, and its unregistered
 * terms. The schema checks the shape of every link; two references reach
 * beyond the link and are checked here, link by link: an identifier's `scheme`
 * names a scheme of the manifest or is an absolute URI, and a part slot's
 * `represented_by` names a timeline (at any depth) or a region of the
 * manifest. The open vocabularies are never refused: a bare term outside the
 * words registered for its key is listed as a warning. Python's
 * `timetoshare.validation.description` holds the same rules.
 */

import { ABSENCE_REASONS, METHODS, PARTS_RELATIONS, RELATIONS } from "../description/link.js";
import { isAbsoluteUri } from "../description/registry.js";
import { isJsonObject, type JsonObject } from "../json/value.js";
import {
  comparePaths,
  entries,
  type PathSegment,
  SchemaValidationError,
  text,
} from "./diagnostics.js";

/** A bare term outside the words registered for its key, at `path`. */
export interface UnregisteredTerm {
  readonly path: readonly PathSegment[];
  readonly term: string;
}

type Found = [JsonObject, PathSegment[]];

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
  const visit = (timeline: JsonObject): void => {
    found.add(text(timeline, "id"));
    for (const region of entries(timeline, "regions")) found.add(text(region, "id"));
    for (const child of entries(timeline, "children")) visit(child);
  };
  for (const root of entries(manifest, "timelines")) visit(root);
  return found;
}

function* schemeProblems(
  owner: JsonObject,
  path: readonly PathSegment[],
  schemes: ReadonlySet<string>,
): Generator<SchemaValidationError> {
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
 * Yield the references of links that name nothing, link by link: within a
 * link its identifiers' schemes, then each part slot's identifiers' schemes
 * and its `represented_by` entries, then each `part_of` entry's identifiers'
 * schemes.
 */
export function* descriptionProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const schemes = new Set(entries(manifest, "schemes").map((scheme) => text(scheme, "id")));
  const targets = targetsOf(manifest);
  for (const [link, path] of linksOf(manifest)) {
    yield* schemeProblems(link, path, schemes);
    for (const [index, slot] of entries(link, "parts").entries()) {
      const at = [...path, "parts", index];
      yield* schemeProblems(slot, at, schemes);
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
      yield* schemeProblems(entry, [...path, "part_of", index], schemes);
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
