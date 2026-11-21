import { describe, expect, it } from "vitest";
import {
  BELIEFS,
  candidates,
  compactIri,
  compactJson,
  defaultCatalogue,
  dumps,
  entries,
  expandIri,
  FORMAT_CONTEXT,
  JsonFloat,
  MATCHES,
  METHODS,
  manifestWarnings,
  NAMESPACE,
  pairs,
  SchemaValidationError,
  samePair,
  statementProblems,
  subjectPath,
  subjects,
  usedPrefixes,
  validate,
  withBelief,
  withCandidate,
  withContext,
  withoutPair,
  withPair,
  withReferencesRenamed,
} from "../src/index.js";
import type { JsonObject } from "../src/json/value.js";
import { CATALOGUE_TEST } from "./catalogue.js";
import { contextWith, m1, m2, RDF, SCHEMA, WIKIDATA } from "./statement-manifests.js";

const ROOT = ["timelines", 0] as const;
const EDITOR = "https://example.org/people/editor";
const TILIE = "https://example.org/agents/tilie";
const PIRES = { id: "wd:Q235650", label: "Maria João Pires" };
const STATED = { stated_by: [EDITOR], date: "2026-11-18", method: "manual" };

/** The error a call throws, as its message. */
function thrown(call: () => unknown): string {
  try {
    call();
  } catch (error) {
    if (error instanceof Error) return error.message;
    throw error;
  }
  throw new Error("nothing was thrown");
}

/** The root timeline of a manifest. */
const root = (value: JsonObject): JsonObject => (value.timelines as JsonObject[])[0] as JsonObject;

describe("the constants", () => {
  it("name the format's namespace, terms and words", () => {
    expect(NAMESPACE).toBe("https://timetoalign.github.io/timetoshare/ns#");
    expect(Object.keys(FORMAT_CONTEXT)).toHaveLength(32);
    expect(FORMAT_CONTEXT.statements).toBe("@nest");
    expect(FORMAT_CONTEXT.beliefs).toBe(`${NAMESPACE}belief`);
    expect(FORMAT_CONTEXT.actor).toEqual({ "@id": `${NAMESPACE}actor`, "@type": "@id" });
    expect(FORMAT_CONTEXT.belief).toBe(`${NAMESPACE}beliefValue`);
    for (const word of ["status", "confirmed", "proposed", "rejected"]) {
      expect(Object.hasOwn(FORMAT_CONTEXT, word)).toBe(false);
    }
    expect([...BELIEFS]).toEqual([true, false, "unlikely"]);
    expect([...METHODS]).toEqual(["manual", "reconciled", "imported", "inferred"]);
    expect([...MATCHES]).toEqual(["exact", "close", "broad", "narrow", "related"]);
  });
});

describe("expandIri", () => {
  const context = contextWith({ ...SCHEMA, ...WIKIDATA });
  it.each([
    ["type", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"],
    ["label", "http://www.w3.org/2000/01/rdf-schema#label"],
    ["stated_by", "http://www.w3.org/ns/prov#wasAttributedTo"],
    ["beliefs", `${NAMESPACE}belief`],
    ["actor", `${NAMESPACE}actor`],
    ["wdt:P175", "http://www.wikidata.org/prop/direct/P175"],
    ["http://schema.org/name", "http://schema.org/name"],
    ["urn:isbn:0451450523", "urn:isbn:0451450523"],
    ["mailto:a@example.org", "mailto:a@example.org"],
    ["wdtt:P175", null],
    ["MusicRecording", null],
    ["id", null],
    ["provenance", null],
  ])("reads %j as %j", (text, expected) => {
    expect(expandIri(context, text)).toBe(expected);
  });

  it("reads no format term as a prefix", () => {
    expect(expandIri({ ...context, label: "http://example.org/" }, "label:x")).toBeNull();
  });
});

describe("subjectPath", () => {
  it("addresses the bundle, a root, a child and a region by their IDs as written", () => {
    const value = m1();
    expect(subjectPath(value, null)).toEqual([]);
    expect(subjectPath(value, "#cpt_1")).toEqual(["timelines", 0]);
    expect(subjectPath(value, "#cpt_2")).toEqual(["timelines", 0, "children", 0]);
    expect(subjectPath(value, "#region_1")).toEqual(["timelines", 0, "regions", 0]);
    expect(thrown(() => subjectPath(value, "cpt_1"))).toBe(
      "no timeline or region of the manifest has the ID 'cpt_1'",
    );
  });
});

describe("subjects", () => {
  it("walks the manifest, then each root's timeline, its regions and its children", () => {
    const manifest: JsonObject = {
      timetoshare: "0.2.0",
      timelines: [
        {
          id: "a",
          regions: [{ id: "a1" }, 7, { id: "a2" }],
          children: [{ id: "b", regions: [{ id: "b1" }], children: [{ id: "c" }] }, { id: "d" }],
        },
        { id: "e" },
      ],
      groups: [{ id: "g", members: ["a", "e"] }],
    };
    const walked = [...subjects(manifest)];
    expect(walked.map(({ path, kind, element }) => [path, kind, element.id ?? null])).toEqual([
      [[], "manifest", null],
      [["timelines", 0], "timeline", "a"],
      [["timelines", 0, "regions", 0], "region", "a1"],
      [["timelines", 0, "regions", 2], "region", "a2"],
      [["timelines", 0, "children", 0], "timeline", "b"],
      [["timelines", 0, "children", 0, "regions", 0], "region", "b1"],
      [["timelines", 0, "children", 0, "children", 0], "timeline", "c"],
      [["timelines", 0, "children", 1], "timeline", "d"],
      [["timelines", 1], "timeline", "e"],
    ]);
    expect(walked[0]?.element).toBe(manifest);
    expect([...subjects([manifest])]).toEqual([]);
  });
});

describe("stating and removing pairs", () => {
  it("states a pair with its entry", () => {
    const value = withPair(m1(), ROOT, "wdt:P175", PIRES, { provenance: STATED });
    expect(root(value).statements).toEqual({ "wdt:P175": [PIRES] });
    expect(root(value).provenance).toEqual([
      {
        date: "2026-11-18",
        method: "manual",
        property: "wdt:P175",
        stated_by: [EDITOR],
        value: { id: "wd:Q235650" },
      },
    ]);
    expect(pairs(value, ROOT)).toEqual([["wdt:P175", PIRES]]);
    expect(entries(value, ROOT)).toHaveLength(1);
    expect(candidates(value, ROOT)).toEqual([]);
    validate(value);
  });

  it("refuses the same pair again, by the same thing written in full too", () => {
    const value = withPair(m1(), ROOT, "wdt:P175", PIRES, { provenance: STATED });
    expect(thrown(() => withPair(value, ROOT, "wdt:P175", PIRES))).toBe(
      "'wdt:P175' already has this value",
    );
    const full = { id: "http://www.wikidata.org/entity/Q235650" };
    expect(thrown(() => withPair(value, ROOT, "wdt:P175", full))).toBe(
      "'wdt:P175' already has this value",
    );
  });

  it("states a type, written rdf:type in its entry", () => {
    const value = withPair(m1(), ROOT, "type", "schema:VideoObject", { provenance: STATED });
    expect(root(value).statements).toEqual({ type: ["schema:VideoObject"] });
    expect(root(value).provenance).toEqual([
      { ...STATED, property: "rdf:type", value: { id: "schema:VideoObject" } },
    ]);
  });

  it("removes both pairs with their entries, and with them every emptied key", () => {
    let value = withPair(m1(), ROOT, "wdt:P175", PIRES, { provenance: STATED });
    value = withPair(value, ROOT, "type", "schema:VideoObject", { provenance: STATED });
    value = withoutPair(value, ROOT, "wdt:P175", { id: "wd:Q235650" });
    expect(root(value).statements).toEqual({ type: ["schema:VideoObject"] });
    value = withoutPair(value, ROOT, "type", "schema:VideoObject");
    expect(Object.keys(root(value))).toEqual(Object.keys(root(m1())));
    expect(dumps(value)).toBe(dumps(m1()));
    expect(thrown(() => withoutPair(value, ROOT, "type", "schema:VideoObject"))).toBe(
      "'type' does not have this value",
    );
  });

  it("states a pair on a value node, whose pairs are its own keys", () => {
    const value = withPair(m1(), ROOT, "wdt:P175", PIRES);
    const node = [...ROOT, "statements", "wdt:P175", 0];
    const viaf = { id: "http://viaf.org/viaf/113931950" };
    const sameAs = withPair(value, node, "schema:sameAs", viaf);
    expect(pairs(sameAs, node)).toEqual([["schema:sameAs", viaf]]);
    expect(root(sameAs).statements).toEqual({
      "wdt:P175": [{ ...PIRES, "schema:sameAs": [viaf] }],
    });
    expect(compactJson(withoutPair(sameAs, node, "schema:sameAs", viaf))).toBe(compactJson(value));
  });

  it("leaves its arguments as they were", () => {
    const value = m1();
    const before = compactJson(value);
    const node = { ...PIRES };
    withPair(value, ROOT, "wdt:P175", node, { provenance: STATED });
    expect(compactJson(value)).toBe(before);
    expect(node).toEqual(PIRES);
  });
});

describe("candidates and beliefs", () => {
  const WORK = { id: "wd:Q29117946" };
  const candidate = () =>
    withCandidate(m1(), ROOT, "wdt:P2550", WORK, {
      stated_by: [TILIE],
      date: "2026-11-18",
      method: "inferred",
      basis: ["#cpt_2"],
    });
  const PROPOSED = {
    property: "wdt:P2550",
    value: WORK,
    stated_by: [TILIE],
    date: "2026-11-18",
    method: "inferred",
    basis: ["#cpt_2"],
  };

  it("hold a candidate without stating it", () => {
    const value = candidate();
    expect(Object.hasOwn(root(value), "statements")).toBe(false);
    expect(root(value).provenance).toEqual([PROPOSED]);
    expect(candidates(value, ROOT)).toEqual([PROPOSED]);
    validate(value);
  });

  it("replace a candidate in place, keeping its beliefs", () => {
    const doubted = withBelief(candidate(), ROOT, "wdt:P2550", WORK, {
      actor: EDITOR,
      belief: "unlikely",
      date: "2026-11-19",
      note: "n",
    });
    const again = withCandidate(doubted, ROOT, "wdt:P2550", WORK, {
      stated_by: [EDITOR],
      date: "2026-11-19",
      method: "manual",
    });
    expect(root(again).provenance).toEqual([
      {
        property: "wdt:P2550",
        value: WORK,
        stated_by: [EDITOR],
        date: "2026-11-19",
        method: "manual",
        beliefs: [{ actor: EDITOR, belief: "unlikely", date: "2026-11-19", note: "n" }],
      },
    ]);
  });

  it("state a candidate by a person, who believes it true, and keep it against a false belief", () => {
    const labelled = { ...WORK, label: "Clair de lune" };
    const stated = withPair(candidate(), ROOT, "wdt:P2550", labelled, {
      actor: EDITOR,
      date: "2026-11-20",
    });
    expect(root(stated).statements).toEqual({ "wdt:P2550": [labelled] });
    expect(root(stated).provenance).toEqual([
      { ...PROPOSED, beliefs: [{ actor: EDITOR, belief: true, date: "2026-11-20" }] },
    ]);
    expect(candidates(stated, ROOT)).toEqual([]);
    validate(stated);
    const disbelieved = withBelief(stated, ROOT, "wdt:P2550", WORK, {
      actor: TILIE,
      belief: false,
      date: "2026-11-21",
    });
    const changed = withBelief(disbelieved, ROOT, "wdt:P2550", WORK, {
      actor: EDITOR,
      belief: false,
      date: "2026-11-22",
    });
    expect(root(changed).statements).toEqual({ "wdt:P2550": [labelled] });
    expect((root(changed).provenance as JsonObject[])[0]?.beliefs).toEqual([
      { actor: EDITOR, belief: false, date: "2026-11-22" },
      { actor: TILIE, belief: false, date: "2026-11-21" },
    ]);
    validate(changed);
    expect(withoutPair(changed, ROOT, "wdt:P2550", WORK)).toEqual(m1());
  });

  it("offer a candidate to every actor but one who believes it false", () => {
    const believed = withBelief(candidate(), ROOT, "wdt:P2550", WORK, {
      actor: EDITOR,
      belief: false,
      date: "2026-11-19",
    });
    const [held] = entries(believed, ROOT);
    expect(candidates(believed, ROOT)).toEqual([held]);
    expect(candidates(believed, ROOT, EDITOR)).toEqual([]);
    expect(candidates(believed, ROOT, TILIE)).toEqual([held]);
  });

  it("record a belief in a pair never stated with an entry of its own", () => {
    const value = withBelief(m1(), [...ROOT, "regions", 0], "type", "schema:MusicVideoObject", {
      actor: EDITOR,
      belief: false,
      date: "2026-11-18",
    });
    expect((root(value).regions as JsonObject[])[0]?.provenance).toEqual([
      {
        property: "rdf:type",
        value: { id: "schema:MusicVideoObject" },
        beliefs: [{ actor: EDITOR, belief: false, date: "2026-11-18" }],
      },
    ]);
  });

  it("refuse what does not hold", () => {
    const stated = withPair(m1(), ROOT, "wdt:P2550", WORK);
    const options = { stated_by: [EDITOR], date: "2026-11-18", method: "manual" };
    expect(thrown(() => withCandidate(stated, ROOT, "wdt:P2550", WORK, options))).toBe(
      "'wdt:P2550' already has this value; a stated pair is no candidate",
    );
    expect(thrown(() => withPair(m1(), ROOT, "wdt:P2550", WORK, { actor: EDITOR }))).toBe(
      "a belief needs a date",
    );
    for (const belief of [1, 0, "likely", null]) {
      const given = { actor: EDITOR, belief: belief as never, date: "2026-11-18" };
      expect(thrown(() => withBelief(m1(), ROOT, "type", "schema:Thing", given))).toBe(
        `${belief === "likely" ? '"likely"' : String(belief)} is no belief: write true, false or 'unlikely'`,
      );
    }
    expect(thrown(() => withPair(m1(), ROOT, "performer", "x"))).toBe(
      "'performer' is no property: write 'type', a compact IRI or an absolute IRI",
    );
    expect(thrown(() => withPair(m1(), ["timelines", 3], "wdt:P175", WORK))).toBe(
      "#/timelines/3 addresses no element and no value node",
    );
    expect(thrown(() => withPair(m1(), ["timelines"], "wdt:P175", WORK))).toBe(
      "#/timelines addresses no element and no value node",
    );
    const container = ["timelines", 0, "statements"];
    expect(thrown(() => pairs(stated, container))).toBe(
      "#/timelines/0/statements addresses no element and no value node",
    );
    expect(thrown(() => withPair(stated, container, "wdt:P175", WORK))).toBe(
      "#/timelines/0/statements addresses no element and no value node",
    );
    const nested = m1();
    root(nested).statements = {
      "schema:p": [
        {
          id: "wd:Q1",
          "schema:sameAs": [{ id: "wd:Q2" }],
          provenance: [{ property: "schema:sameAs", value: { id: "wd:Q2" } }],
        },
      ],
    };
    const throughProvenance = [...ROOT, "statements", "schema:p", 0, "provenance", 0, "value"];
    expect(thrown(() => pairs(nested, throughProvenance))).toBe(
      "#/timelines/0/statements/schema:p/0/provenance/0/value addresses no element and no value node",
    );
    expect(pairs(nested, [...ROOT, "statements", "schema:p", 0])).toEqual([
      ["schema:sameAs", { id: "wd:Q2" }],
    ]);
    expect(
      thrown(() =>
        withCandidate(m1(), ROOT, "wdt:P2550", WORK, { ...options, date: "2026-02-30" }),
      ),
    ).toBe("'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD");
  });
});

describe("samePair", () => {
  const context = contextWith({ ...SCHEMA, ...WIKIDATA, ...RDF });
  it.each([
    [
      ["wdt:P175", { id: "wd:Q1" }],
      ["http://www.wikidata.org/prop/direct/P175", { id: "http://www.wikidata.org/entity/Q1" }],
    ],
    [
      ["type", "schema:Book"],
      ["rdf:type", { id: "http://schema.org/Book" }],
    ],
    [
      ["wdt:P175", { id: "wd:Q1", label: "A" }],
      ["wdt:P175", { id: "wd:Q1" }],
    ],
    [
      ["schema:author", { label: "A", "schema:name": ["A"] }],
      ["schema:author", { "schema:name": ["A"], label: "A" }],
    ],
    [
      ["schema:name", { "@value": "x", "@type": "schema:Text" }],
      ["schema:name", { "@value": "x", "@type": "http://schema.org/Text" }],
    ],
    [
      ["schema:position", { list: [1, 2] }],
      ["schema:position", { list: [1, 2] }],
    ],
    [
      ["dcterms:source", { id: "#cpt_1" }],
      ["dcterms:source", { id: "#cpt_1" }],
    ],
  ])("holds for %j and %j", (left, right) => {
    expect(samePair(context, left as [string, unknown], right as [string, unknown])).toBe(true);
  });

  it.each([
    [
      ["schema:position", true],
      ["schema:position", 1],
    ],
    [
      ["schema:position", 1],
      ["schema:position", "1"],
    ],
    [
      ["schema:position", 1],
      ["schema:position", new JsonFloat(1)],
    ],
    [
      ["schema:name", { "@value": "x", "@language": "en" }],
      ["schema:name", { "@value": "x", "@language": "de" }],
    ],
    [
      ["schema:position", { list: [1, 2] }],
      ["schema:position", { list: [2, 1] }],
    ],
    [
      ["wdt:P175", { id: "wd:Q1" }],
      ["wdt:P86", { id: "wd:Q1" }],
    ],
    [
      ["schema:author", { label: "A" }],
      ["schema:author", { label: "B" }],
    ],
    [
      ["type", "schema:X"],
      ["rdf:type", "schema:X"],
    ],
    [
      ["rdf:type", "schema:X"],
      ["type", "schema:X"],
    ],
  ])("fails for %j and %j", (left, right) => {
    expect(samePair(context, left as [string, unknown], right as [string, unknown])).toBe(false);
  });
});

describe("the context of a manifest", () => {
  it("lists the prefixes M2 uses and rebuilds its context from the catalogue's", () => {
    const value = m2();
    expect(usedPrefixes(value)).toEqual([
      "dcterms",
      "gnd",
      "melod",
      "rel",
      "schema",
      "viaf",
      "wd",
      "wdt",
      "xsd",
    ]);
    const { "@context": context, ...rest } = value;
    const rebuilt = withContext(rest, CATALOGUE_TEST.prefixes);
    expect(dumps(rebuilt["@context"])).toBe(dumps(context));
    expect(dumps(withContext(value, {}))).toBe(dumps(value));
  });

  it("drops an unused prefix and states only the terms of a manifest without statements", () => {
    const value = withContext(
      { timetoshare: "0.2.0", timelines: [], "@context": { unused: "http://example.org/" } },
      {},
    );
    expect(dumps(value["@context"])).toBe(dumps(FORMAT_CONTEXT));
  });

  it("refuses a prefix declared nowhere", () => {
    const own = withContext(m2(), { ...CATALOGUE_TEST.prefixes, wd: "http://example.org/" });
    expect((own["@context"] as JsonObject).wd).toBe("http://www.wikidata.org/entity/");
    const { "@context": _, ...rest } = m2();
    expect(thrown(() => withContext(rest, { schema: "http://schema.org/" }))).toBe(
      "the prefix 'dcterms' is declared neither in the manifest's @context nor in the given prefixes",
    );
  });

  it("finds M2 valid and without warnings", () => {
    validate(m2());
    expect(manifestWarnings(m2())).toEqual([]);
  });
});

/** The base manifest of the shared rejection cases, with members of its root added. */
function based(
  rootMembers: JsonObject = {},
  members: JsonObject = {},
  prefixes: JsonObject = {},
): JsonObject {
  return {
    "@context": contextWith({ ...SCHEMA, ...WIKIDATA, ...(prefixes as Record<string, string>) }),
    timetoshare: "0.2.0",
    timelines: [{ id: "#clt_1", unit: "quarters", length: [8, 1], ...rootMembers }],
    ...members,
  };
}

/** The code, path and message `validate` raises. */
function refusal(value: unknown): [string, readonly (string | number)[], string] {
  try {
    validate(value);
  } catch (error) {
    if (!(error instanceof SchemaValidationError)) throw error;
    return [error.code, error.path, error.detail];
  }
  throw new Error("value was accepted");
}

const COMPOSITION = { type: ["schema:MusicComposition"] };
const entry = (property: string, value: unknown, rest: JsonObject = {}) => ({
  property,
  value,
  ...rest,
});

describe("the statement rules", () => {
  it.each<[string, JsonObject, string, (string | number)[], string]>([
    [
      "statements without a context",
      (() => {
        const { "@context": _, ...value } = based({ statements: COMPOSITION });
        return value;
      })(),
      "context",
      ["timelines", 0, "statements"],
      "statements and provenance need the manifest's @context",
    ],
    [
      "an undeclared prefix of a key",
      based({ statements: { "wdtt:P175": [{ id: "wd:Q84148" }] } }),
      "iri",
      ["timelines", 0, "statements", "wdtt:P175"],
      "'wdtt:P175': the prefix 'wdtt' is not declared in @context",
    ],
    [
      "an undeclared prefix of a thing",
      based({ statements: { "wdt:P175": [{ id: "wdd:Q84148" }] } }),
      "iri",
      ["timelines", 0, "statements", "wdt:P175", 0, "id"],
      "'wdd:Q84148': the prefix 'wdd' is not declared in @context",
    ],
    [
      "an undeclared prefix of a class",
      based({ statements: { type: ["schemaa:MusicRecording"] } }),
      "iri",
      ["timelines", 0, "statements", "type", 0],
      "'schemaa:MusicRecording': the prefix 'schemaa' is not declared in @context",
    ],
    [
      "a property no IRI",
      based({ statements: { performer: ["x"] } }),
      "schema",
      ["timelines", 0, "statements"],
      "",
    ],
    [
      "a value object with a language and a type",
      based(
        {
          statements: {
            "schema:name": [{ "@value": "Op. 106", "@language": "en", "@type": "xsd:string" }],
          },
        },
        {},
        { xsd: "http://www.w3.org/2001/XMLSchema#" },
      ),
      "schema",
      ["timelines", 0, "statements", "schema:name", 0],
      "",
    ],
    [
      "a value node without keys",
      based({ statements: { "schema:sameAs": [{}] } }),
      "schema",
      ["timelines", 0, "statements", "schema:sameAs", 0],
      "",
    ],
    [
      "a value node naming a blank node",
      based({ statements: { "schema:sameAs": [{ id: "_:b0" }] } }),
      "schema",
      ["timelines", 0, "statements", "schema:sameAs", 0, "id"],
      "",
    ],
    [
      "a null in ordered values",
      based({ statements: { "schema:hasPart": [{ list: [{ id: "wd:Q1" }, null] }] } }),
      "schema",
      ["timelines", 0, "statements", "schema:hasPart", 0, "list", 1],
      "",
    ],
    [
      "an integral float",
      based({ statements: { "schema:position": [new JsonFloat(1)] } }),
      "representation",
      ["timelines", 0, "statements", "schema:position", 0],
      "a statement value is an integer or a string, never a float: 1.0",
    ],
    [
      "an impossible date",
      based(
        {
          statements: COMPOSITION,
          provenance: [
            entry(
              "rdf:type",
              { id: "schema:MusicComposition" },
              {
                date: "2026-02-30",
              },
            ),
          ],
        },
        {},
        RDF,
      ),
      "calendar_date",
      ["timelines", 0, "provenance", 0, "date"],
      "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD",
    ],
    [
      "a pair annotated twice",
      based({
        statements: { "wdt:P86": [{ id: "wd:Q255" }] },
        provenance: [entry("wdt:P86", { id: "wd:Q255" }), entry("wdt:P86", { id: "wd:Q255" })],
      }),
      "provenance_duplicate",
      ["timelines", 0, "provenance", 1],
      "the entry repeats the pair of entry 0",
    ],
    [
      "an actor holding two beliefs in one entry",
      based({
        statements: { "wdt:P86": [{ id: "wd:Q255" }] },
        provenance: [
          entry(
            "wdt:P86",
            { id: "wd:Q255" },
            {
              beliefs: [
                { actor: "wd:Q1", belief: true, date: "2026-11-18" },
                { actor: "#clt_1", belief: "unlikely", date: "2026-11-18" },
                { actor: "http://www.wikidata.org/entity/Q1", belief: false, date: "2026-11-19" },
              ],
            },
          ),
        ],
      }),
      "belief_actor",
      ["timelines", 0, "provenance", 0, "beliefs", 2, "actor"],
      "'http://www.wikidata.org/entity/Q1' already holds belief 0 of this entry; an actor holds one belief",
    ],
    [
      "a belief of an element that is not there",
      based({
        provenance: [
          entry(
            "wdt:P86",
            { id: "wd:Q255" },
            {
              beliefs: [{ actor: "#cpt_9", belief: false, date: "2026-11-18" }],
            },
          ),
        ],
      }),
      "dangling_target",
      ["timelines", 0, "provenance", 0, "beliefs", 0, "actor"],
      "'#cpt_9' names no element of this manifest",
    ],
    [
      "an element that is not there",
      based(
        { statements: { "dcterms:source": [{ id: "#cpt_9" }] } },
        {},
        { dcterms: "http://purl.org/dc/terms/" },
      ),
      "dangling_target",
      ["timelines", 0, "statements", "dcterms:source", 0, "id"],
      "'#cpt_9' names no element of this manifest",
    ],
    [
      "an element with a label",
      (() => {
        const value = based(
          { statements: { "dcterms:source": [{ id: "#clt_2", label: "Score" }] } },
          {},
          { dcterms: "http://purl.org/dc/terms/" },
        );
        (value.timelines as JsonObject[]).push({ id: "#clt_2", unit: "quarters", length: [4, 1] });
        return value;
      })(),
      "element_value",
      ["timelines", 0, "statements", "dcterms:source", 0],
      "'#clt_2' names an element; a value naming an element holds its id alone",
    ],
    [
      "a subject ID no IRI fragment",
      (() => {
        const value = based({ statements: { type: ["schema:MusicRecording"] } });
        root(value).id = "#Bass Kick";
        return value;
      })(),
      "iri",
      ["timelines", 0, "id"],
      "the ID 'Bass Kick' of an element with statements is no IRI fragment",
    ],
    [
      "a term on a timeline",
      based({ label: "Score" }),
      "reserved_key",
      ["timelines", 0, "label"],
      "'label' is reserved on a timeline",
    ],
    [
      "an IRI on a region",
      based({
        regions: [{ id: "#region_1", start: [0, 1], end: [4, 1], "schema:name": ["Intro"] }],
      }),
      "reserved_key",
      ["timelines", 0, "regions", 0, "schema:name"],
      "'schema:name' is reserved on a region",
    ],
    [
      "statements on a group",
      based(
        {},
        {
          groups: [
            { id: "#group_1", members: ["#clt_1"], statements: { type: ["schema:MusicGroup"] } },
          ],
        },
      ),
      "reserved_key",
      ["groups", 0, "statements"],
      "'statements' is reserved on a group",
    ],
    [
      "a prefix on the manifest",
      based({}, { schema: "x" }),
      "reserved_key",
      ["schema"],
      "'schema' is reserved on the manifest",
    ],
    [
      "a context on a timeline",
      based({ "@context": {} }),
      "reserved_key",
      ["timelines", 0, "@context"],
      "'@context' is reserved on a timeline",
    ],
    [
      "children on a region",
      based({ regions: [{ id: "#region_1", start: [0, 1], end: [4, 1], children: [] }] }),
      "reserved_key",
      ["timelines", 0, "regions", 0, "children"],
      "'children' is reserved on a region",
    ],
  ])("refuse %s", (_name, value, code, path, message) => {
    const [found, at, detail] = refusal(value);
    // A schema violation carries Ajv's message, which only its code and path pin.
    expect([found, at, code === "schema" ? "" : detail]).toEqual([code, path, message]);
  });

  it("accept an ID with every character of a fragment", () => {
    const value = based({ statements: COMPOSITION });
    root(value).id = "#a-._~!$&'()*+,;=:@/?%41é";
    validate(value);
    root(value).id = "#a%4";
    expect(refusal(value)[0]).toBe("iri");
  });

  it("list every problem of the statements in rule order", () => {
    const value = based(
      {
        label: "Score",
        statements: {
          "dcterms:source": [{ id: "#cpt_9" }, { id: "#clt_2", label: "x" }],
          "schema:position": [new JsonFloat(2)],
          type: ["schema:MusicComposition"],
          "wdtt:P1": ["x"],
        },
        provenance: [
          entry("rdf:type", { id: "schema:MusicComposition" }, { date: "2026-02-30" }),
          entry("rdf:type", { id: "schema:MusicComposition" }),
          entry(
            "wdt:P86",
            { id: "wd:Q255" },
            {
              beliefs: [
                { actor: "#clt_2", belief: true, date: "2026-11-18" },
                { actor: "#clt_2", belief: false, date: "2026-11-19" },
              ],
            },
          ),
        ],
      },
      {},
      { ...RDF, dcterms: "http://purl.org/dc/terms/" },
    );
    (value.timelines as JsonObject[]).push({ id: "#clt_2", unit: "quarters", length: [4, 1] });
    const at = ["timelines", 0];
    expect(
      statementProblems(value).map((problem) => [problem.code, problem.path, problem.detail]),
    ).toEqual([
      ["reserved_key", [...at, "label"], "'label' is reserved on a timeline"],
      [
        "dangling_target",
        [...at, "statements", "dcterms:source", 0, "id"],
        "'#cpt_9' names no element of this manifest",
      ],
      [
        "element_value",
        [...at, "statements", "dcterms:source", 1],
        "'#clt_2' names an element; a value naming an element holds its id alone",
      ],
      [
        "representation",
        [...at, "statements", "schema:position", 0],
        "a statement value is an integer or a string, never a float: 2.0",
      ],
      [
        "iri",
        [...at, "statements", "wdtt:P1"],
        "'wdtt:P1': the prefix 'wdtt' is not declared in @context",
      ],
      [
        "calendar_date",
        [...at, "provenance", 0, "date"],
        "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD",
      ],
      ["provenance_duplicate", [...at, "provenance", 1], "the entry repeats the pair of entry 0"],
      [
        "belief_actor",
        [...at, "provenance", 2, "beliefs", 1, "actor"],
        "'#clt_2' already holds belief 0 of this entry; an actor holds one belief",
      ],
    ]);
    expect(refusal(value)).toEqual([
      "reserved_key",
      [...at, "label"],
      "'label' is reserved on a timeline",
    ]);
  });

  it("check the members' schema before the rules, each member's first problem", () => {
    const value = based({ label: "Score", statements: {}, provenance: [] });
    expect(statementProblems(value).map((problem) => [problem.code, problem.path])).toEqual([
      ["schema", ["timelines", 0, "provenance"]],
      ["schema", ["timelines", 0, "statements"]],
    ]);
    const context = based();
    (context["@context"] as JsonObject).statements = "@set";
    expect(statementProblems(context).map((problem) => [problem.code, problem.path])).toEqual([
      ["schema", ["@context", "statements"]],
    ]);
  });

  it("list a context problem for every key that needs one", () => {
    const { "@context": _, ...value } = based(
      { statements: COMPOSITION },
      { provenance: [entry("wdt:P86", { id: "wd:Q255" })] },
    );
    const problems = statementProblems(value).filter((problem) => problem.code === "context");
    expect(problems.map((problem) => problem.path)).toEqual([
      ["provenance"],
      ["timelines", 0, "statements"],
    ]);
  });
});

describe("the warnings", () => {
  it("warn of a manifest without a context", () => {
    const { "@context": _, ...value } = based();
    expect(manifestWarnings(value)).toEqual([
      { code: "context_absent", path: [], message: "the manifest has no @context" },
    ]);
  });

  it("warn of a bundle with statements but no ID", () => {
    expect(manifestWarnings(based({}, { statements: COMPOSITION }))).toEqual([
      {
        code: "bundle_blank",
        path: ["statements"],
        message: "the manifest has statements but no ID; its subject is a blank node",
      },
    ]);
    const proposal = { provenance: [entry("wdt:P86", { id: "wd:Q255" })] };
    expect(manifestWarnings(based({}, proposal)).map((warning) => warning.path)).toEqual([
      ["provenance"],
    ]);
    expect(manifestWarnings(based({}, { id: "#op106", ...proposal }))).toEqual([]);
  });
});

describe("references to elements", () => {
  const RECORD = "https://example.org/record";

  /** M1 naming an element by `reference` at every reference position once. */
  function referring(reference: string): JsonObject {
    const value = m1();
    const context = value["@context"] as JsonObject;
    context.dcterms = "http://purl.org/dc/terms/";
    context.rdfs = "http://www.w3.org/2000/01/rdf-schema#";
    value.statements = { "rdfs:seeAlso": [{ id: reference }, { id: "other.yaml#cpt_2" }] };
    const timeline = root(value);
    timeline.statements = { "dcterms:source": [{ id: reference }], type: ["schema:VideoObject"] };
    timeline.provenance = [
      {
        property: "dcterms:source",
        value: { id: reference },
        basis: [reference, RECORD],
      },
      {
        property: "rdf:type",
        value: { id: "schema:VideoObject" },
        basis: [reference],
        service: reference,
      },
      { property: "dcterms:isPartOf", value: { id: reference } },
    ];
    return value;
  }

  /** M1 whose region names an element in nodes, ordered values and `stated_by`. */
  function nesting(reference: string): JsonObject {
    const value = m1();
    const region = (root(value).regions as JsonObject[])[0] as JsonObject;
    region.statements = {
      "schema:about": [
        { "schema:mentions": [{ id: reference }] },
        { label: "Intro", "schema:mentions": [{ id: reference }] },
      ],
      "schema:hasPart": [
        { list: [{ id: reference }, { id: reference }] },
        { list: [{ id: reference }, { id: "wd:Q1" }] },
      ],
    };
    region.provenance = [
      {
        property: "schema:about",
        value: { id: "wd:Q2" },
        stated_by: [reference, EDITOR],
      },
      {
        property: "schema:about",
        value: { id: "wd:Q3" },
        stated_by: [reference],
      },
    ];
    return value;
  }

  it("renames every reference to a renamed element", () => {
    for (const build of [referring, nesting]) {
      const given = build("#cpt_2");
      const kept = structuredClone(given);
      expect(withReferencesRenamed(given, { cpt_2: "cpt_3" })).toEqual(build("#cpt_3"));
      expect(given).toEqual(kept);
    }
  });

  it("drops every reference to a dropped element", () => {
    const given = referring("#cpt_2");
    const kept = structuredClone(given);
    const result = withReferencesRenamed(given, { cpt_2: null });
    const expected = referring("#cpt_2");
    expected.statements = { "rdfs:seeAlso": [{ id: "other.yaml#cpt_2" }] };
    root(expected).statements = { type: ["schema:VideoObject"] };
    root(expected).provenance = [{ property: "rdf:type", value: { id: "schema:VideoObject" } }];
    expect(result).toEqual(expected);
    expect(Object.hasOwn(result, "provenance")).toBe(false);
    expect(given).toEqual(kept);
  });

  it("renames and drops the actors of beliefs", () => {
    const held = { belief: true, date: "2026-11-18" };
    const given = m1();
    root(given).provenance = [
      {
        property: "wdt:P86",
        value: { id: "wd:Q255" },
        beliefs: [
          { actor: "#cpt_2", ...held },
          { actor: EDITOR, ...held },
        ],
      },
      { property: "wdt:P175", value: { id: "wd:Q1" }, beliefs: [{ actor: "#cpt_2", ...held }] },
    ];
    const renamed = root(withReferencesRenamed(given, { cpt_2: "cpt_3" }))
      .provenance as JsonObject[];
    expect(
      ((renamed[0] as JsonObject).beliefs as JsonObject[]).map((belief) => belief.actor),
    ).toEqual(["#cpt_3", EDITOR]);
    expect(renamed[1]?.beliefs).toEqual([{ actor: "#cpt_3", ...held }]);
    expect(root(withReferencesRenamed(given, { cpt_2: null })).provenance).toEqual([
      { property: "wdt:P86", value: { id: "wd:Q255" }, beliefs: [{ actor: EDITOR, ...held }] },
      { property: "wdt:P175", value: { id: "wd:Q1" } },
    ]);
  });

  it("drops nodes and ordered values left empty", () => {
    const result = withReferencesRenamed(nesting("#cpt_2"), { cpt_2: null });
    const region = (root(result).regions as JsonObject[])[0] as JsonObject;
    expect(region.statements).toEqual({
      "schema:about": [{ label: "Intro" }],
      "schema:hasPart": [{ list: [{ id: "wd:Q1" }] }],
    });
    expect(region.provenance).toEqual([
      { property: "schema:about", value: { id: "wd:Q2" }, stated_by: [EDITOR] },
      { property: "schema:about", value: { id: "wd:Q3" } },
    ]);
  });

  it("changes nothing for an ID nothing names", () => {
    for (const build of [referring, nesting]) {
      expect(withReferencesRenamed(build("#cpt_2"), { cpt_9: "x" })).toEqual(build("#cpt_2"));
    }
  });

  it("renames each reference once", () => {
    const result = withReferencesRenamed(referring("#cpt_1"), { cpt_1: "cpt_2", cpt_2: "cpt_3" });
    expect(result).toEqual(referring("#cpt_2"));
  });
});

describe("compact IRIs", () => {
  const MUSICBRAINZ_WORK = "http://musicbrainz.org/work/8d331505-4d88-39ae-81c7-bec5da77af96";
  const CASES: readonly (readonly [string, string])[] = [
    ["http://www.wikidata.org/entity/Q235650", "wd:Q235650"],
    ["http://www.wikidata.org/prop/direct/P175", "wdt:P175"],
    ["https://schema.org/name", "https://schema.org/name"],
    ["http://d-nb.info/gnd/11862119X", "http://d-nb.info/gnd/11862119X"],
    ["https://d-nb.info/gnd/119018934", "gnd:119018934"],
    ["https://lod.academy/melod/vocab/ontology#Work", "melod:Work"],
    ["http://www.wikidata.org/entity/", "http://www.wikidata.org/entity/"],
    ["urn:uuid:works/1", "urn:uuid:works/1"],
    [MUSICBRAINZ_WORK, MUSICBRAINZ_WORK],
  ];

  it.each(CASES)("compacts %s by the catalogue's prefixes", (iri, compact) => {
    expect(compactIri(defaultCatalogue().prefixes, iri)).toBe(compact);
  });

  it("reads an alias before compacting", () => {
    const { prefixes, aliases } = defaultCatalogue();
    expect(compactIri(prefixes, "https://schema.org/name", aliases)).toBe("schema:name");
    expect(compactIri(prefixes, "https://example.org/x/y", aliases)).toBe(
      "https://example.org/x/y",
    );
  });

  it("takes the longest namespace and the smaller name of a tie", () => {
    const prefixes = { ex: "http://a.example/", exs: "http://a.example/sub/", a: "http://b/" };
    expect(compactIri(prefixes, "http://a.example/sub/x")).toBe("exs:x");
    expect(compactIri(prefixes, "http://a.example/x.1_-")).toBe("ex:x.1_-");
    expect(compactIri({ z: "http://b/", b: "http://b/", é: "http://b/" }, "http://b/x")).toBe(
      "b:x",
    );
    for (const rest of ["a/b", "a:b", ".a", "-a", "a b", "a\n"]) {
      expect(compactIri(prefixes, `http://b/${rest}`)).toBe(`http://b/${rest}`);
    }
  });
});
