/**
 * The description layer: links from a manifest's elements to external entities.
 *
 * A link is a typed relation from the element holding it (the manifest, a
 * timeline or a region) to an external entity at a stated level; it never
 * claims that the element is the entity, and one link is one attributed
 * reading (the schema's `Link`). The functions here build links from the URLs
 * of catalogue pages through the registry of known schemes (`./registry.ts`)
 * and change them copy-on-write. A link is a plain object of the generated
 * types: every function takes a link in either form and returns a new link in
 * the complete form, built from the table of defaults as `complete` builds a
 * manifest's links; `minimal` of a manifest holding it gives the minimal form.
 * Python's `timetoshare.description` offers the same operations as methods,
 * with the same values, and raises `ValueError` with the same message wherever
 * a function here throws an `Error`.
 */

import { completeDescription } from "../defaults.js";
import type {
  Assertion,
  CompleteAssertion,
  CompleteLink,
  CompletePartSlot,
  Descriptor,
  Identifier,
  Level,
  Link,
  PartOf,
  PartSlot,
} from "../generated/types.js";
import type { Lossless } from "../json/value.js";
import {
  defaultRegistry,
  isAbsoluteUri,
  LEVELS,
  recognize,
  type SchemeRegistry,
} from "./registry.js";

export { LEVELS };

/** The registered words of a link's `relation`; another bare word reads as an unspecified relation. */
export const RELATIONS = ["pertains_to"] as const;

/** The registered words of an assertion's `method`; another bare word reads as no method stated. */
export const METHODS = ["manual", "reconciled", "imported", "inferred"] as const;

/**
 * The registered words of a `parts_relation`, on a link and on `part_of`;
 * another bare word reads as an unspecified structural relation.
 */
export const PARTS_RELATIONS = ["has_part", "aggregates", "incorporates"] as const;

/** The registered words of a part slot's `absent`; another bare word reads as `not_represented`. */
export const ABSENCE_REASONS = [
  "not_represented",
  "lost",
  "unfinished",
  "unknown",
  "not_recorded",
] as const;

/** The words of an assertion's `match`, a closed vocabulary. */
export const MATCHES = ["exact", "close", "broad", "narrow", "related"] as const;

/** The words of an assertion's `status`, a closed vocabulary. */
export const STATUSES = ["confirmed", "unconfirmed", "rejected"] as const;

const DATE = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/;
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

/** What `linkFromUrls` takes besides the URLs; each member as Python's keyword of its name. */
export interface LinkOptions {
  /** The level; no level a URL is recognised at may contradict it. */
  readonly level?: string;
  /** The relation; `pertains_to` where absent, required at the level `agent`. */
  readonly relation?: string;
  /** Identifiers after those from URLs: a record of scheme to value, or `Identifier`s. */
  readonly identifiers?: Readonly<Record<string, string>> | readonly Identifier[];
  readonly label?: string | null;
  readonly assertion?: Assertion | null;
  /** The registry the URLs are read through, the default registry where absent. */
  readonly registry?: SchemeRegistry;
}

/** What `partSlotFromUrl` takes besides the URL. */
export interface PartSlotOptions {
  readonly absent?: string | null;
  readonly representedBy?: readonly string[];
  readonly label?: string | null;
  readonly assertion?: Assertion | null;
  readonly registry?: SchemeRegistry;
}

/** What `withParts` takes besides the parts relation and the slots. */
export interface PartsOptions {
  /** Whether the order of the slots is the linked entity's own; true where absent. */
  readonly ordered?: boolean;
  readonly registry?: SchemeRegistry;
}

function identifierKey(identifier: Identifier): string {
  return `${identifier.scheme}\u0000${identifier.value}`;
}

/** The entries without repetitions, each kept where it first occurs. */
function unique<T>(entries: readonly T[], key: (entry: T) => string): T[] {
  const seen = new Set<string>();
  return entries.filter((entry) => {
    const name = key(entry);
    if (seen.has(name)) return false;
    seen.add(name);
    return true;
  });
}

const same = (text: string): string => text;

function quoted(texts: readonly string[]): string {
  return texts.map((text) => `'${text}'`).join(", ");
}

interface Normalised {
  readonly uris: string[];
  readonly identifiers: Identifier[];
  /** Each recognised level with the URL it was recognised from. */
  readonly levels: [Level, string][];
}

/**
 * Read URLs through the registry: their URIs, identifiers and levels. An
 * absolute URI the registry does not recognise is kept as it is.
 *
 * @throws {Error} if a URL is neither recognised nor an absolute URI.
 */
function normalised(urls: readonly string[], registry: SchemeRegistry | undefined): Normalised {
  const known = registry ?? defaultRegistry();
  const uris: string[] = [];
  const identifiers: Identifier[] = [];
  const levels: [Level, string][] = [];
  for (const url of urls) {
    const recognition = recognize(url, known);
    if (recognition === null) {
      if (!isAbsoluteUri(url)) throw new Error(`'${url}' is no absolute URI`);
      uris.push(url);
      continue;
    }
    if (recognition.uri !== null) uris.push(recognition.uri);
    else if (recognition.identifier !== null) identifiers.push(recognition.identifier);
    if (recognition.level !== null) levels.push([recognition.level, url]);
  }
  return {
    uris: unique(uris, same),
    identifiers: unique(identifiers, identifierKey),
    levels,
  };
}

function isLevel(text: string): text is Level {
  return (LEVELS as readonly string[]).includes(text);
}

function checkedLevel(level: string): Level {
  if (!isLevel(level)) throw new Error(`'${level}' is no level`);
  return level;
}

/**
 * The level of a link: the stated one, else the one the URLs tell, else null.
 *
 * @throws {Error} if the stated level is no level or contradicts a recognised
 * one, or if the URLs tell two levels.
 */
function levelOf(stated: string | undefined, recognised: readonly [Level, string][]): Level | null {
  if (stated !== undefined) {
    const level = checkedLevel(stated);
    for (const [found, url] of recognised) {
      if (found !== level) {
        throw new Error(
          `the level '${level}' contradicts '${url}', recognised at the level '${found}'`,
        );
      }
    }
    return level;
  }
  const [first, ...rest] = recognised;
  if (first === undefined) return null;
  for (const [found, url] of rest) {
    if (found !== first[0]) {
      throw new Error(
        `'${url}' is recognised at the level '${found}', '${first[1]}' at '${first[0]}'`,
      );
    }
  }
  return first[0];
}

/**
 * Check an assertion's date as Python reads it.
 *
 * @throws {Error} if its `asserted_on` is no date of the calendar written
 * `YYYY-MM-DD`.
 */
function checkedAssertion(assertion: CompleteAssertion | null): CompleteAssertion | null {
  const date = assertion?.asserted_on ?? null;
  const problem = date === null ? null : calendarDateProblem(date);
  if (problem !== null) throw new Error(problem);
  return assertion;
}

/**
 * Check the dates of a link's assertions as Python reads them, the link's
 * own, then its slots' and its `part_of` entries', and then the link as
 * Python's `Link` checks one on construction.
 *
 * @throws {Error} if an assertion's date is no date, the level is no level,
 * an agent link uses `pertains_to`, or parts lack a `parts_relation`.
 */
function checkedLink(link: CompleteLink): CompleteLink {
  checkedAssertion(link.assertion);
  for (const entry of [...link.parts, ...link.part_of]) checkedAssertion(entry.assertion);
  checkedLevel(link.level);
  if (link.level === "agent" && link.relation === "pertains_to") {
    throw new Error("an agent link never uses the relation 'pertains_to'");
  }
  if (link.parts.length > 0 && link.parts_relation === null) {
    throw new Error("a link with parts states its parts_relation");
  }
  return link;
}

/**
 * Check a part slot as Python's `PartSlot` checks one on construction, and
 * the date of its assertion as Python reads it.
 *
 * @throws {Error} if the slot is both represented and absent, or neither, or
 * its assertion's date is no date.
 */
function checkedSlot(slot: CompletePartSlot): CompletePartSlot {
  checkedAssertion(slot.assertion);
  if (slot.represented_by.length > 0 && slot.absent !== null) {
    throw new Error("a part slot is represented or absent, not both");
  }
  if (slot.represented_by.length === 0 && slot.absent === null) {
    throw new Error("a part slot is represented by an element or absent");
  }
  return slot;
}

function givenIdentifiers(identifiers: LinkOptions["identifiers"]): Identifier[] {
  if (identifiers === undefined) return [];
  if (Array.isArray(identifiers)) return [...identifiers];
  return Object.entries(identifiers).map(([scheme, value]) => ({ scheme, value }));
}

/**
 * Build a link from the URLs of an entity, read through the registry, as
 * Python's `Link.from_urls`. Each URL gives its entity URI, which joins `uri`,
 * or its identifier, which joins `identifiers`; an absolute URI the registry
 * does not recognise joins `uri` as it is; repetitions collapse into the
 * first. The identifiers from URLs come first, then the given ones. The level
 * is the given one, which no recognised level may contradict, else the one
 * level the URLs tell. The relation is `pertains_to` unless the level is
 * `agent`, which needs the agent's role.
 *
 * @throws {Error} if no URL is given, a URL is neither recognised nor an
 * absolute URI, the level is no level, contradicts a recognised one or is
 * told by no URL, the URLs tell two levels, or an agent link names no
 * relation.
 */
export function linkFromUrls(urls: readonly string[], options: LinkOptions = {}): CompleteLink {
  if (urls.length === 0) throw new Error("a link from URLs needs one URL at least");
  const { uris, identifiers, levels } = normalised(urls, options.registry);
  const level = levelOf(options.level, levels);
  if (level === null) {
    throw new Error(`no level is recognised from ${quoted(urls)}; state the level`);
  }
  let relation = options.relation;
  if (relation === undefined) {
    if (level === "agent") throw new Error("an agent link states its relation, the agent's role");
    relation = "pertains_to";
  }
  const link: Lossless<Link> = {
    relation,
    level,
    uri: uris,
    identifiers: unique([...identifiers, ...givenIdentifiers(options.identifiers)], identifierKey),
    label: options.label ?? null,
    assertion: options.assertion ?? null,
  };
  return checkedLink(completeDescription(link, "link"));
}

/** Build a link from one URL, as `linkFromUrls` does. */
export function linkFromUrl(url: string, options: LinkOptions = {}): CompleteLink {
  return linkFromUrls([url], options);
}

/**
 * Build a part slot from the URL of the part, read through the registry, as
 * Python's `PartSlot.from_url`.
 *
 * @throws {Error} if the URL is neither recognised nor an absolute URI, or the
 * slot is both represented and absent, or neither.
 */
export function partSlotFromUrl(url: string, options: PartSlotOptions = {}): CompletePartSlot {
  const { uris, identifiers } = normalised([url], options.registry);
  const slot: Lossless<PartSlot> = {
    uri: uris,
    identifiers,
    label: options.label ?? null,
    represented_by: [...(options.representedBy ?? [])],
    absent: options.absent ?? null,
    assertion: options.assertion ?? null,
  };
  return checkedSlot(completeDescription(slot, "part_slot"));
}

/**
 * Return the link with URLs appended, read as `linkFromUrls` reads them.
 *
 * @throws {Error} if a URL is neither recognised nor an absolute URI, or is
 * recognised at another level than the link's.
 */
export function withUri(
  link: Lossless<Link>,
  urls: readonly string[],
  options: { readonly registry?: SchemeRegistry } = {},
): CompleteLink {
  const base = completeDescription(link, "link");
  const { uris, identifiers, levels } = normalised(urls, options.registry);
  levelOf(base.level, levels);
  base.uri = unique([...base.uri, ...uris], same);
  base.identifiers = unique([...base.identifiers, ...identifiers], identifierKey);
  return checkedLink(base);
}

/** Return the link with the identifier appended, unless it holds it. */
export function withIdentifier(link: Lossless<Link>, scheme: string, value: string): CompleteLink {
  const base = completeDescription(link, "link");
  base.identifiers = unique([...base.identifiers, { scheme, value }], identifierKey);
  return checkedLink(base);
}

/** Return the link with a record appended. */
export function withRecord(link: Lossless<Link>, descriptor: Lossless<Descriptor>): CompleteLink {
  const base = completeDescription(link, "link");
  base.records = [...base.records, completeDescription(descriptor, "descriptor")];
  return checkedLink(base);
}

/** Return the link with its label replaced. */
export function withLabel(link: Lossless<Link>, label: string | null): CompleteLink {
  const base = completeDescription(link, "link");
  base.label = label;
  return checkedLink(base);
}

/** Return the link with its assertion replaced. */
export function withAssertion(link: Lossless<Link>, assertion: Assertion | null): CompleteLink {
  const base = completeDescription(link, "link");
  base.assertion = assertion === null ? null : completeDescription(assertion, "assertion");
  return checkedLink(base);
}

/**
 * Return the link with its reading's parts replaced by `slots`.
 *
 * @throws {Error} if a slot is both represented and absent, or neither, or if
 * a slot's URI is recognised at another level than the link's.
 */
export function withParts(
  link: Lossless<Link>,
  partsRelation: string,
  slots: readonly Lossless<PartSlot>[],
  options: PartsOptions = {},
): CompleteLink {
  const base = completeDescription(link, "link");
  const known = options.registry ?? defaultRegistry();
  const parts = slots.map((slot) => checkedSlot(completeDescription(slot, "part_slot")));
  for (const [index, slot] of parts.entries()) {
    for (const uri of slot.uri) {
      const level = recognize(uri, known)?.level ?? null;
      if (level !== null && level !== base.level) {
        throw new Error(
          `part slot ${index + 1} is recognised at the level '${level}', the link's level is '${base.level}'`,
        );
      }
    }
  }
  base.parts_relation = partsRelation;
  base.parts = parts;
  base.parts_ordered = options.ordered ?? true;
  return checkedLink(base);
}

/** Return the link with a `part_of` entry appended. */
export function withPartOf(link: Lossless<Link>, entry: Lossless<PartOf>): CompleteLink {
  const base = completeDescription(link, "link");
  base.part_of = [...base.part_of, completeDescription(entry, "part_of")];
  return checkedLink(base);
}

/**
 * Return the assertion of a slot or `part_of` entry of a link: its own, else
 * the link's.
 *
 * @throws {Error} if that assertion's date is no date of the calendar.
 */
export function assertionFor(
  link: Lossless<Link>,
  entry: Lossless<PartSlot> | Lossless<PartOf>,
): CompleteAssertion | null {
  const assertion = entry.assertion ?? link.assertion ?? null;
  return checkedAssertion(assertion === null ? null : completeDescription(assertion, "assertion"));
}
