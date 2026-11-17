/**
 * The registry of well-known identifier schemes, which turns URLs into links.
 *
 * A URL a user copies from a catalogue's web page is rarely the form a link
 * keeps: the registry recognises the URL of each scheme it knows and gives
 * either the entity URI the scheme mints, written as Wikidata's formatter URI
 * for RDF resources states it where the scheme's Wikidata property has one,
 * or, for a scheme that mints none, an identifier `{scheme: <scheme URI>,
 * value}`. Never both.
 *
 * The registry is one data file, `registry/schemes.json`, shipped with this
 * package (as `@timetoalign/timetoshare/registry/schemes.json`, and bundled
 * as `generated/registry.ts`) and with the Python package, which reads it the
 * same way (`timetoshare.registry`). A pattern matches a whole URL and
 * captures the value in its one group; it is compiled as `^(?:pattern)$` with
 * the `u` flag and uses only the syntax Python's `re` reads alike: no named
 * group, no lookbehind, no inline flag. A URL holding white space or a
 * control character is no absolute URI and is never recognised. The value
 * captured for an entity URI is substituted as written; the value of an
 * identifier is percent-decoded as UTF-8 and written with underscores for
 * spaces, as a wiki writes a page name.
 */

import { schemes as shipped } from "../generated/registry.js";
import type { Identifier, Level } from "../generated/types.js";

/** The levels of a link, the closed vocabulary of the schema's `Level`. */
export const LEVELS = ["work", "expression", "manifestation", "item", "agent"] as const;

/**
 * White space and control characters, which no URI or term holds: the class
 * the schema's `Term`, `Uri` and `UriReference` refuse, written out because
 * Python's `\s` and JavaScript's `\s` differ.
 */
export const BLANK =
  "[\\u0000-\\u0020\\u007f-\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff]";

const BLANK_PATTERN = new RegExp(BLANK, "u");
const SCHEME_NAME = /^[A-Za-z][A-Za-z0-9+.-]*:./u;
const OUTSIDE_SUBSET = /\(\?[^:=!]/u;

/**
 * Whether `text` is an absolute URI as the schema's `Uri` reads one: a scheme
 * name (a letter, then letters, digits, `+`, `.` or `-`), a colon and at least
 * one more character, without white space or a control character.
 */
export function isAbsoluteUri(text: string): boolean {
  return SCHEME_NAME.test(text) && !BLANK_PATTERN.test(text);
}

/** One entry of the registry: a scheme and the URLs it recognises. */
export interface KnownScheme {
  /** The entry's ID, unique within a registry. */
  readonly id: string;
  /** The scheme's name, as Wikidata labels its property. */
  readonly name: string;
  /** The URI of the scheme, the `scheme` of the identifiers it gives. */
  readonly uri: string;
  /** The level of every entity of the scheme, or null where the address does not tell. */
  readonly level: Level | null;
  /** The template of the scheme's entity URIs, holding `{value}`, or null where it mints none. */
  readonly entity_uri: string | null;
  /** Regular expressions, each matching a whole URL and capturing the value in its one group. */
  readonly patterns: readonly string[];
}

/** What the registry recognises in a URL; exactly one of `uri` and `identifier` is set. */
export interface Recognition {
  /** The entry that recognised the URL. */
  readonly scheme: KnownScheme;
  /** The value the entry's pattern captured, decoded for an identifier. */
  readonly value: string;
  /** The level of the entity, or null where the scheme does not tell. */
  readonly level: Level | null;
  /** The entity URI, or null. */
  readonly uri: string | null;
  /** The identifier, or null. */
  readonly identifier: Identifier | null;
}

/**
 * An ordered, read-only set of known schemes; a URL is recognised by the
 * first entry, in this order, one of whose patterns matches it.
 */
export interface SchemeRegistry {
  readonly schemes: readonly KnownScheme[];
}

function compiled(pattern: string): RegExp {
  return new RegExp(`^(?:${pattern})$`, "u");
}

/**
 * Check one entry as Python's `KnownScheme` does.
 *
 * @throws {Error} if a pattern is no regular expression, has not exactly one
 * capturing group or uses syntax outside the shared subset, if the level is
 * no level, or if the template holds no `{value}`.
 */
function checked(entry: KnownScheme): KnownScheme {
  if (entry.level !== null && !(LEVELS as readonly string[]).includes(entry.level)) {
    throw new Error(`scheme '${entry.id}' has the level '${entry.level}', which is no level`);
  }
  if (entry.entity_uri !== null && !entry.entity_uri.includes("{value}")) {
    throw new Error(
      `the entity URI template '${entry.entity_uri}' of scheme '${entry.id}' holds no {value}`,
    );
  }
  for (const pattern of entry.patterns) {
    const where = `pattern '${pattern}' of scheme '${entry.id}'`;
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
  return Object.freeze({ ...entry, patterns: Object.freeze([...entry.patterns]) });
}

/**
 * Return a new registry extended by `entries`: an entry whose ID the registry
 * holds replaces that entry in place, any other is appended. The given
 * registry is left as it is.
 *
 * @throws {Error} for an entry `KnownScheme` refuses, with Python's message.
 */
export function withSchemes(
  registry: SchemeRegistry,
  entries: readonly KnownScheme[],
): SchemeRegistry {
  const schemes = [...registry.schemes];
  for (const entry of entries) {
    const scheme = checked(entry);
    const index = schemes.findIndex((known) => known.id === scheme.id);
    if (index >= 0) schemes[index] = scheme;
    else schemes.push(scheme);
  }
  return Object.freeze({ schemes: Object.freeze(schemes) });
}

const DEFAULT_REGISTRY = withSchemes({ schemes: [] }, shipped);

/** The registry of the shipped file `registry/schemes.json`; it cannot be changed, only extended. */
export function defaultRegistry(): SchemeRegistry {
  return DEFAULT_REGISTRY;
}

const HEX_PAIR = /^[0-9A-Fa-f]{2}$/u;
const UTF8 = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });

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
 * Return what the registry recognises in `url`, or null. A URL that is no
 * absolute URI is never recognised, and neither is one whose identifier is not
 * percent-encoded UTF-8. Python's `SchemeRegistry.recognize` gives the same.
 */
export function recognize(
  url: string,
  registry: SchemeRegistry = defaultRegistry(),
): Recognition | null {
  if (!isAbsoluteUri(url)) return null;
  for (const scheme of registry.schemes) {
    for (const pattern of scheme.patterns) {
      const captured = compiled(pattern).exec(url)?.[1];
      if (captured === undefined) continue;
      if (scheme.entity_uri !== null) {
        return {
          scheme,
          value: captured,
          level: scheme.level,
          uri: scheme.entity_uri.split("{value}").join(captured),
          identifier: null,
        };
      }
      const decoded = percentDecoded(captured);
      if (decoded === null) return null;
      const value = decoded.replaceAll(" ", "_");
      return {
        scheme,
        value,
        level: scheme.level,
        uri: null,
        identifier: { scheme: scheme.uri, value },
      };
    }
  }
  return null;
}
