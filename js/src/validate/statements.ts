/**
 * Statement rules: what the schema cannot check of `statements`,
 * `provenance` and `@context`. Three rules, each over the subjects in subject
 * order (the manifest, then root by root the timeline, its regions and its
 * children, depth first):
 *
 * 1. `context`: a manifest without `@context` carries no `statements` and no
 *    `provenance` anywhere.
 * 2. `reserved_key`: no element (the subjects, then the groups) holds a key
 *    JSON-LD would read: a keyword, a key holding `:`, a format term other
 *    than the element's own, or a prefix of the context.
 * 3. The walk of every subject carrying statements or provenance: its ID an
 *    IRI fragment (`iri`); every IRI's prefix declared (`iri`); every `#`
 *    reference naming an element (`dangling_target`); every date a calendar
 *    date (`calendar_date`); no float (`representation`); a node naming an
 *    element holding its `id` alone (`element_value`); every `confirmed`
 *    entry matching a pair and no `proposed` or `rejected` one
 *    (`provenance_match`); one entry per pair (`provenance_duplicate`).
 *
 * The rules read the manifest with bare IDs; the IRIs of statements and
 * provenance are the same in both forms. The validators never consult the
 * catalogue. Python's `timetoshare.validation.statements` holds the same
 * rules with the same messages.
 */

import { isJsonObject, type JsonObject } from "../json/value.js";
import { compareCodePoints, spell } from "../serialization/text.js";
import {
  BLANK,
  calendarDateProblem,
  declaredPrefix,
  FORMAT_CONTEXT,
  isAbsoluteReference,
  type Pair,
  pairsOf,
  samePair,
  subjectElements,
  URI_SCHEMES,
  visitSubject,
} from "../statements/statements.js";
import {
  comparePaths,
  entries,
  manifestIds,
  type PathSegment,
  SchemaValidationError,
} from "./diagnostics.js";

/** The names of the format's terms. */
const TERMS: readonly string[] = Object.keys(FORMAT_CONTEXT);

/** The terms an element may hold as its own keys, by kind. */
const OWN_TERMS: Readonly<Record<ElementKind, readonly string[]>> = {
  manifest: ["id", "timelines", "groups", "statements", "provenance"],
  timeline: ["id", "children", "regions", "statements", "provenance"],
  region: ["id", "statements", "provenance"],
  group: ["id"],
};

type ElementKind = "manifest" | "timeline" | "region" | "group";

const ELEMENT_WORDS: Readonly<Record<ElementKind, string>> = {
  manifest: "the manifest",
  timeline: "a timeline",
  region: "a region",
  group: "a group",
};

/** The keys that carry statements, in the order the rules read them on one element. */
const CARRIERS = ["provenance", "statements"] as const;

const BLANK_PATTERN = new RegExp(BLANK, "u");
const FRAGMENT_CHARACTER = /^[A-Za-z0-9\-._~!$&'()*+,;=:@/?]$/u;
const HEX = /^[0-9A-Fa-f]{2}$/u;

/**
 * Whether an ID may stand as the fragment of an IRI: every code point an
 * unreserved or sub-delimiting character, `:`, `@`, `/`, `?` or one at
 * U+0080 or above, `%` only before two hexadecimal digits, and no white space
 * or control character.
 */
export function isFragment(id: string): boolean {
  if (BLANK_PATTERN.test(id)) return false;
  const characters = [...id];
  return characters.every((character, index) => {
    if ((character.codePointAt(0) ?? 0) >= 0x80) return true;
    if (character === "%") return HEX.test(characters.slice(index + 1, index + 3).join(""));
    return FRAGMENT_CHARACTER.test(character);
  });
}

/** Whether an element carries statements or provenance. */
function carries(element: JsonObject): boolean {
  return CARRIERS.some((key) => Object.hasOwn(element, key));
}

/**
 * Yield a `context` problem for every `statements` and `provenance` key, in
 * subject order (on one element `provenance` first), of a manifest without
 * `@context`.
 */
export function* contextProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  if (Object.hasOwn(manifest, "@context")) return;
  for (const { element, path } of subjectElements(manifest)) {
    for (const key of CARRIERS) {
      if (Object.hasOwn(element, key)) {
        yield new SchemaValidationError(
          "context",
          [...path, key],
          "statements and provenance need the manifest's @context",
        );
      }
    }
  }
}

/** Whether `key` is reserved on an element of `kind` under the given prefixes. */
function reserved(key: string, kind: ElementKind, prefixes: ReadonlySet<string>): boolean {
  if (key.startsWith("@")) return !(kind === "manifest" && key === "@context");
  if (key.includes(":")) return true;
  if (TERMS.includes(key) && !OWN_TERMS[kind].includes(key)) return true;
  return prefixes.has(key);
}

/**
 * Yield every reserved key: the subjects in subject order, then the groups,
 * each element's keys in code-point order.
 */
export function* reservedKeyProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const context = manifest["@context"];
  const prefixes = new Set(
    isJsonObject(context) ? Object.keys(context).filter((key) => !TERMS.includes(key)) : [],
  );
  const elements: { element: JsonObject; path: readonly PathSegment[]; kind: ElementKind }[] = [
    ...subjectElements(manifest),
  ];
  for (const [index, group] of entries(manifest, "groups").entries()) {
    if (isJsonObject(group))
      elements.push({ element: group, path: ["groups", index], kind: "group" });
  }
  for (const { element, path, kind } of elements) {
    for (const key of Object.keys(element).sort(compareCodePoints)) {
      if (reserved(key, kind, prefixes)) {
        yield new SchemaValidationError(
          "reserved_key",
          [...path, key],
          `'${key}' is reserved on ${ELEMENT_WORDS[kind]}`,
        );
      }
    }
  }
}

/** The problem of an IRI whose prefix is not declared, or null. */
function iriProblem(
  context: unknown,
  text: string,
  path: readonly PathSegment[],
): SchemaValidationError | null {
  const colon = text.indexOf(":");
  const prefix = colon < 0 ? text : text.slice(0, colon);
  const rest = colon < 0 ? "" : text.slice(colon + 1);
  if (rest.startsWith("//") || declaredPrefix(context, prefix) !== null) return null;
  if (URI_SCHEMES.includes(prefix)) return null;
  return new SchemaValidationError(
    "iri",
    path,
    `'${text}': the prefix '${prefix}' is not declared in @context`,
  );
}

/** The problem of a reference: a `#` reference naming no element, or an IRI's prefix. */
function referenceProblem(
  context: unknown,
  ids: ReadonlySet<string>,
  text: string,
  path: readonly PathSegment[],
): SchemaValidationError | null {
  if (isAbsoluteReference(text)) return iriProblem(context, text, path);
  if (text.startsWith("#") && !ids.has(text.slice(1))) {
    return new SchemaValidationError(
      "dangling_target",
      path,
      `'${text}' names no element of this manifest`,
    );
  }
  return null;
}

/** The match and repeat problems of a subject's provenance entries, entry by entry. */
function* entryProblems(
  context: unknown,
  owner: JsonObject,
  node: boolean,
  path: readonly PathSegment[],
): Generator<SchemaValidationError> {
  const stated = pairsOf(owner, node);
  const seen: Pair[] = [];
  for (const [index, entry] of entries(owner, "provenance").entries()) {
    const at = [...path, "provenance", index];
    const pair: Pair = [String(entry.property), entry.value];
    const matched = stated.some((candidate) => samePair(context, candidate, pair));
    if (entry.status === "confirmed" && !matched) {
      yield new SchemaValidationError(
        "provenance_match",
        at,
        "no pair of this subject matches the entry; an entry that matches none is proposed or rejected",
      );
    } else if ((entry.status === "proposed" || entry.status === "rejected") && matched) {
      yield new SchemaValidationError(
        "provenance_match",
        at,
        `the pair is stated; a ${entry.status} pair is never stated`,
      );
    }
    const earlier = seen.findIndex((candidate) => samePair(context, candidate, pair));
    if (earlier >= 0) {
      yield new SchemaValidationError(
        "provenance_duplicate",
        at,
        `the entry repeats the pair of entry ${earlier}`,
      );
    }
    seen.push(pair);
  }
}

/**
 * Yield the problems of the walk of every subject carrying statements or
 * provenance, in subject order: its ID, then every position of its
 * statements and provenance, nested nodes where they stand, each subject's
 * entries matched after its positions.
 */
export function* subjectProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const context = manifest["@context"];
  const ids = new Set([...manifestIds(manifest)].map(([id]) => id));
  for (const { element, path } of subjectElements(manifest)) {
    if (!carries(element)) continue;
    const id = element.id;
    if (typeof id === "string" && !isFragment(id)) {
      yield new SchemaValidationError(
        "iri",
        [...path, "id"],
        `the ID '${id}' of an element with statements is no IRI fragment`,
      );
    }
    for (const visit of visitSubject(element, path, false)) {
      let problem: SchemaValidationError | null = null;
      switch (visit.kind) {
        case "iri":
          problem = iriProblem(context, visit.text, visit.path);
          break;
        case "reference":
          problem = referenceProblem(context, ids, visit.text, visit.path);
          break;
        case "date": {
          const message = calendarDateProblem(visit.text);
          if (message !== null)
            problem = new SchemaValidationError("calendar_date", visit.path, message);
          break;
        }
        case "float":
          problem = new SchemaValidationError(
            "representation",
            visit.path,
            `a statement value is an integer or a string, never a float: ${spell(visit.value)}`,
          );
          break;
        case "element":
          problem = new SchemaValidationError(
            "element_value",
            visit.path,
            `'${visit.id}' names an element; a value naming an element holds its id alone`,
          );
          break;
        case "subject":
          yield* entryProblems(context, visit.owner, visit.node, visit.path);
          break;
      }
      if (problem !== null) yield problem;
    }
  }
}

/** Every problem of the statement rules, rule by rule; the manifest has bare IDs. */
export function* statementRuleProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  yield* contextProblems(manifest);
  yield* reservedKeyProblems(manifest);
  yield* subjectProblems(manifest);
}

/** What a manifest is warned of, never refused for. */
export type WarningCode = "context_absent" | "bundle_blank";

/** One warning of a valid manifest. */
export interface ManifestWarning {
  readonly code: WarningCode;
  readonly path: readonly PathSegment[];
  readonly message: string;
}

/**
 * The warnings of a valid manifest, sorted by path, then code:
 * `context_absent` where it has no `@context`; `bundle_blank` where the
 * manifest has statements or provenance but no ID, at `statements` (or at
 * `provenance` where only that is present).
 */
export function warningsOf(manifest: JsonObject): ManifestWarning[] {
  const found: ManifestWarning[] = [];
  if (!Object.hasOwn(manifest, "@context")) {
    found.push({ code: "context_absent", path: [], message: "the manifest has no @context" });
  }
  if (carries(manifest) && !Object.hasOwn(manifest, "id")) {
    found.push({
      code: "bundle_blank",
      path: [Object.hasOwn(manifest, "statements") ? "statements" : "provenance"],
      message: "the manifest has statements but no ID; its subject is a blank node",
    });
  }
  return found.sort((a, b) => comparePaths(a.path, b.path) || compareCodePoints(a.code, b.code));
}
