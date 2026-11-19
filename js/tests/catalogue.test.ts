import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { Ajv2020 } from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import {
  type Catalogue,
  compactJson,
  defaultCatalogue,
  instantiate,
  loads,
  readCatalogue,
  recognize,
  rectangles,
  verbOf,
} from "../src/index.js";
import { type JsonObject, plain } from "../src/json/value.js";
import { CATALOGUE_TEST } from "./catalogue.js";
import { expectWrittenAsStored, repositoryRoot } from "./fixtures.js";
import { m2 } from "./statement-manifests.js";

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

/** The test catalogue changed by `change`, as a plain document. */
function changed(change: (document: JsonObject) => void): JsonObject {
  const document = structuredClone(CATALOGUE_TEST) as unknown as JsonObject;
  change(document);
  return document;
}

const systems = (document: JsonObject) => document.systems as JsonObject[];
const verbs = (document: JsonObject) => document.verbs as JsonObject[];
const types = (document: JsonObject) => document.types as JsonObject[];
const patternsOf = (document: JsonObject, verb: number) =>
  (verbs(document)[verb] as JsonObject).patterns as Record<string, JsonObject[]>;

describe("readCatalogue", () => {
  it("reads the test catalogue as it is", () => {
    expect(compactJson(readCatalogue(CATALOGUE_TEST))).toBe(compactJson(CATALOGUE_TEST));
  });

  it.each<[string, (document: JsonObject) => void, string]>([
    [
      "a system twice",
      (document) => systems(document).push(structuredClone(systems(document)[2] as JsonObject)),
      "the catalogue holds the system 'melody' twice",
    ],
    [
      "a thing twice",
      (document) => {
        const wikidata = (systems(document)[0] as JsonObject).things as JsonObject[];
        ((systems(document)[1] as JsonObject).things as JsonObject[]).push({ ...wikidata[0] });
      },
      "the catalogue holds the thing 'wikidata' twice",
    ],
    [
      "a verb twice",
      (document) => verbs(document).push({ ...(verbs(document)[1] as JsonObject) }),
      "the catalogue holds the verb 'same_as' twice",
    ],
    [
      "a type twice",
      (document) => types(document).push({ ...(types(document)[0] as JsonObject) }),
      "the catalogue holds the type 'video' twice",
    ],
    [
      "a system's prefix undeclared",
      (document) => ((systems(document)[2] as JsonObject).prefixes as string[]).push("mus"),
      "the catalogue uses the prefix 'mus' without declaring it",
    ],
    [
      "a thing's LRMoo class undeclared",
      (document) => {
        const things = (systems(document)[1] as JsonObject).things as JsonObject[];
        (things[0] as JsonObject).lrmoo_class = "lrmoo:F1_Work";
      },
      "the catalogue uses the prefix 'lrmoo' without declaring it",
    ],
    [
      "a pattern key undeclared",
      (document) =>
        patternsOf(document, 1).fallback?.push({ pattern: { "owl:sameAs": [{ id: "?" }] } }),
      "the catalogue uses the prefix 'owl' without declaring it",
    ],
    [
      "a pattern's constant thing undeclared",
      (document) =>
        patternsOf(document, 2).melody?.push({
          pattern: { "melod:hasContribution": [{ "melod:hasRole": [{ id: "terms:Performer" }] }] },
        }),
      "the catalogue uses the prefix 'terms' without declaring it",
    ],
    [
      "a system not held",
      (document) => {
        patternsOf(document, 2).viaf = [{ pattern: { "rel:prf": [{ id: "?" }] } }];
      },
      "the catalogue names the system 'viaf', which it does not hold",
    ],
    [
      "a lookup system not held",
      (document) => ((types(document)[0] as JsonObject).lookup as string[]).push("gnd"),
      "the catalogue names the system 'gnd', which it does not hold",
    ],
    [
      "a thing not held",
      (document) => {
        const [first] = patternsOf(document, 2).wikidata ?? [];
        (first as JsonObject).when = { value: ["isrc_code"] };
      },
      "the catalogue names the thing 'isrc_code', which no system holds",
    ],
    [
      "a verb not held",
      (document) => ((types(document)[0] as JsonObject).verbs as string[]).push("recorded_by"),
      "the catalogue names the verb 'recorded_by', which it does not hold",
    ],
    [
      "a type not held",
      (document) => {
        const [first] = patternsOf(document, 2).wikidata ?? [];
        (first as JsonObject).when = { subject: ["release"] };
      },
      "the catalogue names the type 'release', which it does not hold",
    ],
    [
      "a pattern outside the shared subset",
      (document) => {
        const things = (systems(document)[0] as JsonObject).things as JsonObject[];
        (things[0] as JsonObject).patterns = ["https://w/(?<value>Q[0-9]+)"];
      },
      "pattern 'https://w/(?<value>Q[0-9]+)' of thing 'wikidata' uses syntax outside the shared subset; only (?:, (?= and (?! may follow '(?'",
    ],
    [
      "a pattern that is no regular expression",
      (document) => {
        const things = (systems(document)[0] as JsonObject).things as JsonObject[];
        (things[0] as JsonObject).patterns = ["https://w/(Q[0-9]+"];
      },
      "pattern 'https://w/(Q[0-9]+' of thing 'wikidata' is no regular expression",
    ],
    [
      "a pattern of two groups",
      (document) => {
        const things = (systems(document)[0] as JsonObject).things as JsonObject[];
        (things[0] as JsonObject).patterns = ["https://(w)/(Q[0-9]+)"];
      },
      "pattern 'https://(w)/(Q[0-9]+)' of thing 'wikidata' has 2 capturing groups; it needs exactly one",
    ],
  ])("refuses %s", (_name, change, message) => {
    expect(thrown(() => readCatalogue(changed(change)))).toBe(message);
  });

  it("checks in its order: a repeat before a prefix before a name before a pattern", () => {
    const document = changed((value) => {
      verbs(value).push({ ...(verbs(value)[1] as JsonObject) });
      ((systems(value)[2] as JsonObject).prefixes as string[]).push("mus");
    });
    expect(thrown(() => readCatalogue(document))).toBe(
      "the catalogue holds the verb 'same_as' twice",
    );
    const named = changed((value) => {
      ((types(value)[0] as JsonObject).verbs as string[]).push("recorded_by");
      ((systems(value)[2] as JsonObject).prefixes as string[]).push("mus");
    });
    expect(thrown(() => readCatalogue(named))).toBe(
      "the catalogue uses the prefix 'mus' without declaring it",
    );
  });
});

describe("recognize", () => {
  it("names the system, the thing, the value and the IRI", () => {
    expect(recognize(CATALOGUE_TEST, "https://www.wikidata.org/wiki/Q235650")).toEqual({
      system: "wikidata",
      thing: "wikidata",
      value: "Q235650",
      iri: "http://www.wikidata.org/entity/Q235650",
    });
    expect(
      recognize(
        CATALOGUE_TEST,
        "https://musicbrainz.org/work/8D331505-4D88-39AE-81C7-BEC5DA77AF96",
      ),
    ).toEqual({
      system: "musicbrainz",
      thing: "musicbrainz_work",
      value: "8d331505-4d88-39ae-81c7-bec5da77af96",
      iri: "http://musicbrainz.org/work/8d331505-4d88-39ae-81c7-bec5da77af96",
    });
    expect(recognize(CATALOGUE_TEST, "not a url")).toBeNull();
    expect(recognize(CATALOGUE_TEST, "https://example.org/Q1")).toBeNull();
  });

  it("decodes the value of a thing without IRI", () => {
    const document = changed((value) => {
      const things = (systems(value)[3] as JsonObject).things as JsonObject[];
      things.push({
        id: "imslp",
        kind: "work",
        name: "IMSLP work page",
        iri: null,
        scheme_uri: "http://www.wikidata.org/entity/P839",
        lrmoo_class: null,
        lowercase: false,
        patterns: ["https?://imslp\\.org/wiki/([^?#/]+)"],
      });
    });
    expect(
      recognize(
        readCatalogue(document),
        "https://imslp.org/wiki/Clair%20de%20lune%20(Debussy%2C_Claude)",
      ),
    ).toEqual({
      system: "fallback",
      thing: "imslp",
      value: "Clair_de_lune_(Debussy,_Claude)",
      iri: null,
    });
  });
});

describe("verbOf", () => {
  const context = m2()["@context"];
  const contributor = (role: string) => ({
    type: ["schema:OrganizationRole"],
    "schema:contributor": [{ id: "wd:Q84148" }],
    "schema:roleName": [role],
  });
  it.each<[string, unknown, [string, boolean] | null]>([
    ["rel:prf", { id: "viaf:113931950" }, ["performed_by", false]],
    ["schema:contributor", contributor("conductor"), ["conducted_by", false]],
    ["schema:contributor", contributor("pianist"), ["performed_by", false]],
    ["dcterms:hasPart", { id: "#clt_6" }, ["part_of", true]],
    ["dcterms:created", { "@value": "2025-12-05", "@type": "xsd:date" }, null],
    ["type", "schema:VideoObject", ["is_a", false]],
    [
      "https://schema.org/sameAs",
      { id: "https://www.youtube.com/watch?v=Ch2mrPm1JnM" },
      ["same_as", false],
    ],
    ["wdt:P175", "Maria João Pires", null],
  ])("reads %s %j as %j", (property, value, expected) => {
    expect(verbOf(CATALOGUE_TEST, context, property, value)).toEqual(expected);
  });
});

describe("instantiate", () => {
  it("fills a pattern's slots", () => {
    expect(
      instantiate(CATALOGUE_TEST, "performed_by", "wikidata", "wd:Q235650", {
        label: "Maria João Pires",
      }),
    ).toEqual([["wdt:P175", { id: "wd:Q235650", label: "Maria João Pires" }]]);
    expect(
      instantiate(CATALOGUE_TEST, "performed_by", "musicbrainz", "wd:Q235650", {
        slots: { role: "piano" },
      }),
    ).toEqual([
      [
        "schema:contributor",
        {
          type: ["schema:OrganizationRole"],
          "schema:contributor": [{ id: "wd:Q235650" }],
          "schema:roleName": ["piano"],
        },
      ],
    ]);
    expect(instantiate(CATALOGUE_TEST, "is_a", "fallback", "schema:VideoObject")).toEqual([
      ["type", "schema:VideoObject"],
    ]);
    expect(
      instantiate(CATALOGUE_TEST, "part_of", "fallback", "#clt_6", { alternative: 1 }),
    ).toEqual([["dcterms:hasPart", { id: "#clt_6" }]]);
  });

  it.each<[string, string, number, string]>([
    ["recorded_by", "wikidata", 0, "the catalogue has no verb 'recorded_by'"],
    ["performed_by", "gnd", 0, "the verb 'performed_by' has no pattern in 'gnd'"],
    ["part_of", "fallback", 2, "the verb 'part_of' has 2 patterns in 'fallback'"],
    [
      "performed_by",
      "musicbrainz",
      0,
      "the pattern of 'performed_by' in 'musicbrainz' needs a value for '?role'",
    ],
  ])("refuses %s in %s (alternative %i)", (verb, system, alternative, message) => {
    expect(thrown(() => instantiate(CATALOGUE_TEST, verb, system, "wd:Q1", { alternative }))).toBe(
      message,
    );
  });
});

describe("rectangles", () => {
  it("group the video's pairs by verb and thing, is a first", () => {
    const value = m2();
    const statements = ((value.timelines as JsonObject[])[1] as JsonObject)
      .statements as JsonObject;
    const [pires] = statements["wdt:P175"] as JsonObject[];
    expect(rectangles(CATALOGUE_TEST, value, ["timelines", 1])).toEqual([
      {
        verb: "is_a",
        inverse: false,
        pairs: [
          ["type", "schema:VideoObject"],
          ["type", "melod:Manifestation"],
          ["wdt:P31", { id: "wd:Q98069877" }],
        ],
        things: [
          "http://schema.org/VideoObject",
          "https://lod.academy/melod/vocab/ontology#Manifestation",
          "http://www.wikidata.org/entity/Q98069877",
        ],
        label: null,
      },
      {
        verb: "performed_by",
        inverse: false,
        pairs: [
          ["rel:prf", { id: "viaf:113931950" }],
          ["wdt:P175", pires],
        ],
        things: [
          "http://viaf.org/viaf/113931950",
          "http://www.wikidata.org/entity/Q235650",
          "https://d-nb.info/gnd/124927521",
        ],
        label: "Maria João Pires",
      },
      {
        verb: "same_as",
        inverse: false,
        pairs: [["schema:sameAs", { id: "https://www.youtube.com/watch?v=Ch2mrPm1JnM" }]],
        things: ["https://www.youtube.com/watch?v=Ch2mrPm1JnM"],
        label: null,
      },
    ]);
  });

  it("let a pair no verb reads stand alone", () => {
    const value = m2();
    const statements = ((value.timelines as JsonObject[])[0] as JsonObject)
      .statements as JsonObject;
    const work = "http://musicbrainz.org/work/8d331505-4d88-39ae-81c7-bec5da77af96";
    expect(rectangles(CATALOGUE_TEST, value, ["timelines", 0])).toEqual([
      {
        verb: "is_a",
        inverse: false,
        pairs: [
          ["type", "melod:Manifestation"],
          ["type", "schema:SheetMusic"],
        ],
        things: [
          "https://lod.academy/melod/vocab/ontology#Manifestation",
          "http://schema.org/SheetMusic",
        ],
        label: null,
      },
      {
        verb: null,
        inverse: false,
        pairs: [["dcterms:created", { "@value": "2025-12-05", "@type": "xsd:date" }]],
        things: [],
        label: null,
      },
      {
        verb: "version_or_edition_of",
        inverse: false,
        pairs: [
          ["schema:exampleOfWork", (statements["schema:exampleOfWork"] as JsonObject[])[0]],
          ["wdt:P629", (statements["wdt:P629"] as JsonObject[])[0]],
        ],
        things: [
          work,
          "http://www.wikidata.org/entity/Q29117946",
          "https://d-nb.info/gnd/300042558",
        ],
        label: "Clair de lune",
      },
    ]);
  });

  it("give an empty is a rectangle where nothing is stated", () => {
    expect(rectangles(CATALOGUE_TEST, m2(), [])).toEqual([
      { verb: "is_a", inverse: false, pairs: [], things: [], label: null },
    ]);
  });
});

describe("the shipped catalogue", () => {
  const directory = resolve(repositoryRoot, "catalogue");
  const text = () => readFileSync(resolve(directory, "catalogue.yaml"), "utf8");

  it("validates against its schema", () => {
    const schemaText = readFileSync(resolve(directory, "catalogue.schema.json"), "utf8");
    const check = new Ajv2020({ strict: false, allErrors: true }).compile(
      plain(loads(schemaText)) as JsonObject,
    );
    expect(check(plain(loads(text()))), JSON.stringify(check.errors)).toBe(true);
  });

  it("passes the cross-reference checks and is the default catalogue", () => {
    const read: Catalogue = readCatalogue(loads(text()));
    expect(compactJson(defaultCatalogue())).toBe(compactJson(read));
    expect(defaultCatalogue()).toBe(defaultCatalogue());
  });

  it("is written as the writers write it", () => {
    expectWrittenAsStored(text());
  });
});
