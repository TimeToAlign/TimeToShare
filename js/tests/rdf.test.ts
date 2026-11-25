import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import jsonld from "jsonld";
import { describe, expect, it } from "vitest";
import {
  ATOMIC_SECTION,
  expandIri,
  isJsonObject,
  loads,
  NAMESPACE,
  SCHEMA_VERSION,
  samePair,
} from "../src/index.js";
import { type JsonObject, plain } from "../src/json/value.js";
import { fixtureFiles, fixtureText, repositoryRoot } from "./fixtures.js";

/** The statement fixtures, each beside its minimal twin. */
const STATEMENT_FIXTURES = ["djset_segment", "layerit_recording", "nielsen_record", "op106_work"];

const RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
const RDFS = "http://www.w3.org/2000/01/rdf-schema#";
const PROV = "http://www.w3.org/ns/prov#";

/** The predicates of the annotations, besides the statements' own. */
const ANNOTATION_PREDICATES = [
  `${RDF}type`,
  `${RDFS}label`,
  `${RDF}subject`,
  `${RDF}predicate`,
  `${RDF}object`,
  `${PROV}wasAttributedTo`,
  "http://purl.org/dc/terms/date",
  `${PROV}hadPrimarySource`,
  `${RDFS}comment`,
  `${NAMESPACE}method`,
  `${NAMESPACE}service`,
  `${NAMESPACE}match`,
  `${NAMESPACE}beliefs`,
  `${NAMESPACE}actor`,
  `${NAMESPACE}belief`,
];

const SCHEMES = ["http:", "https:", "urn:", "tag:", "mailto:", "info:"];

/** A document loader that refuses every fetch: the inline context is all there is. */
async function refuse(url: string): Promise<never> {
  throw new Error(`no document is fetched, ${url} neither`);
}

/** The base IRI of a fixture: its file name under an address of its own. */
function baseOf(path: string): string {
  const name =
    path
      .split("/")
      .at(-1)
      ?.replace(/\.minimal$/u, "") ?? path;
  return `https://example.org/manifests/${name}.yaml`;
}

/** The canonical N-Quads of a fixture's dataset. */
async function canonical(path: string): Promise<string> {
  return jsonld.canonize(plain(loads(fixtureText(path))), {
    base: baseOf(path),
    safe: false,
    documentLoader: refuse,
    format: "application/n-quads",
    canonizeOptions: { algorithm: "RDFC-1.0" },
  });
}

const TERM = /<[^>]*>|_:\S+|"(?:[^"\\]|\\.)*"(?:@[A-Za-z0-9-]+|\^\^<[^>]*>)?/gu;

/** The quads of N-Quads text, each as its terms written. */
function quadsOf(text: string): string[][] {
  return text
    .split("\n")
    .filter((line) => line !== "")
    .map((line) => [...line.matchAll(TERM)].map((match) => match[0]));
}

/** Every IRI a quad writes, a literal's datatype included. */
function irisOf(quad: readonly string[]): string[] {
  return quad.flatMap((term) =>
    [...term.matchAll(/<([^>]*)>/gu)].map((match) => match[1] as string),
  );
}

/** The subjects that may carry statements: the manifest, its timelines at any depth, its regions. */
function* subjectElements(manifest: JsonObject): Generator<JsonObject> {
  yield manifest;
  const visit = function* (timeline: JsonObject): Generator<JsonObject> {
    yield timeline;
    for (const region of (timeline.regions ?? []) as JsonObject[]) yield region;
    for (const child of (timeline.children ?? []) as JsonObject[]) yield* visit(child);
  };
  for (const root of (manifest.timelines ?? []) as JsonObject[]) yield* visit(root);
}

const OWN_KEYS = new Set(["id", "label", "provenance", "type"]);

/**
 * Every subject of a manifest with statements or provenance, value nodes
 * included, each with its pairs' container: an element's `statements`, a
 * node's own keys.
 */
function* subjectsOf(manifest: JsonObject): Generator<[JsonObject, JsonObject]> {
  const nodes = function* (value: unknown): Generator<[JsonObject, JsonObject]> {
    if (Array.isArray(value)) {
      for (const item of value) yield* nodes(item);
    } else if (isJsonObject(value) && !("@value" in value)) {
      if ("list" in value) {
        yield* nodes(value.list);
        return;
      }
      yield [value, value];
      for (const [key, member] of Object.entries(value)) {
        if (key === "provenance") {
          for (const entry of member as JsonObject[]) yield* nodes(entry.value);
        } else if (!OWN_KEYS.has(key)) yield* nodes(member);
      }
    }
  };
  for (const element of subjectElements(manifest)) {
    const container = (element.statements ?? {}) as JsonObject;
    yield [element, container];
    for (const [key, values] of Object.entries(container)) if (key !== "type") yield* nodes(values);
    for (const entry of (element.provenance ?? []) as JsonObject[]) yield* nodes(entry.value);
  }
}

/** The IRI a subject stands for, or null for a blank node. */
function iriOf(context: unknown, subject: JsonObject, base: string): string | null {
  if (typeof subject.id !== "string") return null;
  return /^[A-Za-z][A-Za-z0-9+.-]*:/u.test(subject.id)
    ? (expandIri(context, subject.id) ?? subject.id)
    : new URL(subject.id, base).href;
}

/** N-Quads' writing of a string literal. */
function literal(text: string): string {
  const escaped = text
    .replaceAll("\\", "\\\\")
    .replaceAll('"', '\\"')
    .replaceAll("\n", "\\n")
    .replaceAll("\r", "\\r");
  return `"${escaped}"`;
}

describe("the statement fixtures", () => {
  it("are the four of the specification, each with its expected N-Quads", () => {
    const found = fixtureFiles()
      .filter((path) => path.startsWith("statements/") && !path.endsWith(".minimal"))
      .map((path) => path.slice("statements/".length));
    expect(found).toEqual(STATEMENT_FIXTURES);
  });

  const cases = STATEMENT_FIXTURES.flatMap((name) => [
    [name, `statements/${name}`],
    [name, `statements/${name}.minimal`],
  ]);

  it.each(cases)(
    "%s: %s gives its dataset, and only what its statements say",
    async (name, path) => {
      const manifest = loads(fixtureText(path)) as JsonObject;
      const context = manifest["@context"] as JsonObject;
      const base = baseOf(path);
      const text = await canonical(path);
      const expected = readFileSync(
        resolve(repositoryRoot, "fixtures", "rdf", SCHEMA_VERSION, `${name}.nq`),
        "utf8",
      );
      expect(text).toBe(expected);

      const quads = quadsOf(text);
      const prefixes = Object.keys(context).filter((key) => typeof context[key] === "string");
      for (const iri of quads.flatMap(irisOf)) {
        expect(
          prefixes.some((prefix) => iri.startsWith(`${prefix}:`)),
          iri,
        ).toBe(false);
        expect(
          SCHEMES.some((scheme) => iri.startsWith(scheme)),
          iri,
        ).toBe(true);
      }

      const subjects = [...subjectsOf(manifest)];
      const keys = subjects.flatMap(([, container]) =>
        Object.keys(container)
          .filter((key) => !OWN_KEYS.has(key))
          .map((key) => expandIri(context, key)),
      );
      const predicates = new Set([...keys, ...ANNOTATION_PREDICATES]);
      for (const quad of quads)
        expect(predicates.has(quad[1]?.slice(1, -1) ?? ""), quad[1]).toBe(true);

      const triples = new Set(quads.map((quad) => quad.slice(0, 3).join(" ")));
      let annotations = 0;
      for (const [subject, container] of subjects) {
        const entries = (subject.provenance ?? []) as JsonObject[];
        annotations += entries.length;
        const iri = iriOf(context, subject, base);
        const stated = Object.entries(container)
          .filter(([key]) => key === "type" || !OWN_KEYS.has(key))
          .flatMap(([key, values]) =>
            Array.isArray(values) ? values.map((item) => [key, item] as const) : [],
          );
        for (const entry of entries) {
          const pair = [String(entry.property), entry.value] as const;
          if (iri === null || stated.some((held) => samePair(context, held, pair))) continue;
          const property = expandIri(context, String(entry.property));
          const value = entry.value;
          const object =
            typeof value === "string"
              ? literal(value)
              : isJsonObject(value) && typeof value.id === "string"
                ? `<${iriOf(context, value, base)}>`
                : null;
          if (object === null) continue;
          expect(triples.has(`<${iri}> <${property}> ${object}`), `${iri} ${property}`).toBe(false);
        }
      }
      const reified = new Set(
        quads.filter((quad) => quad[1] === `<${RDF}subject>`).map((quad) => quad[0]),
      );
      expect(reified.size).toBe(annotations);
    },
  );
});

/** The flow fixture whose regions state that they are atomic sections, and its twin. */
const ATOMIC_SECTIONS = ["flow/sonata_exposition", "flow/sonata_exposition.minimal"];

describe("the atomic sections", () => {
  it.each(ATOMIC_SECTIONS)("of %s are typed in the format's namespace", async (path) => {
    const type = `${RDF}type`;
    const rdf = RDF;
    const regions = [1, 2, 3].map((number) => `<${baseOf(path)}#region_${number}>`);
    const quads = quadsOf(await canonical(path));
    const named = quads.filter((quad) => (quad[0] as string).startsWith("<"));
    expect(named.map((quad) => quad.join(" ")).sort()).toEqual(
      regions.map((region) => `${region} <${type}> <${ATOMIC_SECTION}>`).sort(),
    );
    const reified = quads.filter((quad) => !(quad[0] as string).startsWith("<"));
    expect([quads.length, reified.length]).toEqual([15, 12]);
    expect(new Set(reified.map((quad) => quad[0])).size).toBe(3);
    expect(reified.map((quad) => `${quad[1]} ${quad[2]}`).sort()).toEqual(
      regions
        .flatMap((region) => [
          `<${rdf}subject> ${region}`,
          `<${rdf}predicate> <${type}>`,
          `<${rdf}object> <${ATOMIC_SECTION}>`,
          `<${NAMESPACE}method> <${NAMESPACE}Inferred>`,
        ])
        .sort(),
    );
  });
});

describe("every other fixture", () => {
  const others = fixtureFiles().filter(
    (path) => !path.startsWith("statements/") && !ATOMIC_SECTIONS.includes(path),
  );
  it.each(others)("%s states nothing", async (path) => {
    expect(await canonical(path)).toBe("");
  });
});
