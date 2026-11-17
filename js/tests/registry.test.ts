import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  defaultRegistry,
  dumps,
  type Identifier,
  type KnownScheme,
  type Level,
  parseJson,
  recognize,
  type SchemeEntry,
  withSchemes,
} from "../src/index.js";
import { repositoryRoot } from "./fixtures.js";

const WIKIDATA = "http://www.wikidata.org/entity/";
const IMSLP = `${WIKIDATA}P839`;
const OP_106 = "Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)";
const MB_WORK = "4a622b0d-b0c0-405e-b49e-05b70c108284";

const ENTRIES: [string, string, Level | null, string | null, boolean][] = [
  ["musicbrainz_work", `${WIKIDATA}P435`, "work", "http://musicbrainz.org/work/{value}", true],
  [
    "musicbrainz_recording",
    `${WIKIDATA}P4404`,
    "expression",
    "http://musicbrainz.org/recording/{value}",
    true,
  ],
  [
    "musicbrainz_release",
    `${WIKIDATA}P5813`,
    "manifestation",
    "http://musicbrainz.org/release/{value}",
    true,
  ],
  [
    "wikidata",
    "http://id.loc.gov/vocabulary/identifiers/wikidata",
    null,
    "http://www.wikidata.org/entity/{value}",
    false,
  ],
  ["viaf", `${WIKIDATA}P214`, null, "http://viaf.org/viaf/{value}", false],
  ["gnd", `${WIKIDATA}P227`, null, "https://d-nb.info/gnd/{value}", false],
  ["imslp", IMSLP, "work", null, false],
  ["doi", `${WIKIDATA}P356`, null, "https://doi.org/{value}", false],
];

const RECOGNISED: [string, string | null, Identifier | null, Level | null][] = [
  [
    `https://musicbrainz.org/work/${MB_WORK}`,
    `http://musicbrainz.org/work/${MB_WORK}`,
    null,
    "work",
  ],
  [
    "http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980/",
    "http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980",
    null,
    "work",
  ],
  [
    "https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c",
    "http://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c",
    null,
    "manifestation",
  ],
  ["https://www.wikidata.org/wiki/Q146730", "http://www.wikidata.org/entity/Q146730", null, null],
  ["https://viaf.org/viaf/186299955", "http://viaf.org/viaf/186299955", null, null],
  [`https://imslp.org/wiki/${OP_106}`, null, { scheme: IMSLP, value: OP_106 }, "work"],
  [
    "https://imslp.org/wiki/Piano_Sonata_No.29%2C_Op.106_%28Beethoven%2C_Ludwig_van%29",
    null,
    { scheme: IMSLP, value: OP_106 },
    "work",
  ],
  ["https://doi.org/10.5281/zenodo.7473560", "https://doi.org/10.5281/zenodo.7473560", null, null],
  [
    `https://musicbrainz.org/work/${MB_WORK.toUpperCase()}`,
    `http://musicbrainz.org/work/${MB_WORK}`,
    null,
    "work",
  ],
];

const FORMS: [string, string][] = [
  [`http://www.musicbrainz.org/work/${MB_WORK}?tab=details#top`, "musicbrainz_work"],
  [`https://musicbrainz.org/work/${MB_WORK.toUpperCase()}/`, "musicbrainz_work"],
  ["https://musicbrainz.org/work/4a622B0D-b0c0-405E-b49e-05B70C108284", "musicbrainz_work"],
  [
    "https://musicbrainz.org/recording/5F1A7C3E-2B4D-4E6F-8A9B-0C1D2E3F4A5B",
    "musicbrainz_recording",
  ],
  ["https://musicbrainz.org/release/814C53FD-0732-4819-9753-4578F5AB992C", "musicbrainz_release"],
  [
    "https://musicbrainz.org/recording/5f1a7c3e-2b4d-4e6f-8a9b-0c1d2e3f4a5b",
    "musicbrainz_recording",
  ],
  ["https://m.wikidata.org/wiki/Q146730", "wikidata"],
  ["http://www.wikidata.org/entity/Q146730", "wikidata"],
  ["https://www.wikidata.org/wiki/Q146730#P435", "wikidata"],
  ["https://viaf.org/en/viaf/186299955", "viaf"],
  ["https://www.viaf.org/viaf/186299955/", "viaf"],
  ["https://d-nb.info/gnd/118508288", "gnd"],
  ["https://dx.doi.org/10.5281/zenodo.7473560", "doi"],
  [`https://www.imslp.org/wiki/${OP_106}?action=history`, "imslp"],
];

function entry(members: Partial<KnownScheme> = {}): SchemeEntry {
  return {
    id: "x",
    name: "Example",
    uri: "https://example.org/scheme",
    level: null,
    entity_uri: "https://example.org/entity/{value}",
    patterns: ["https://example.org/page/([0-9]+)"],
    ...members,
  };
}

const NAMESPACES = [
  "Media",
  "Special",
  "Talk",
  "User",
  "User_talk",
  "IMSLP",
  "IMSLP_talk",
  "Project",
  "Project_talk",
  "File",
  "File_talk",
  "Image",
  "Image_talk",
  "MediaWiki",
  "MediaWiki_talk",
  "Template",
  "Template_talk",
  "Help",
  "Help_talk",
  "Category",
  "Category_talk",
  "Module",
  "Module_talk",
];
const NOT_WORK_PAGES = [
  "Main_Page",
  "Main_Page/",
  "Main_Page?action=history",
  "Main%20Page",
  ...NAMESPACES.flatMap((namespace) =>
    [...new Set(["_", namespace.includes("_") ? "%20" : "_"])].flatMap((space) =>
      [":", "%3A", "%3a"].map((colon) => `${namespace.replace("_", space)}${colon}Example`),
    ),
  ),
];

describe("the registry of identifier schemes", () => {
  it("is the shipped file", () => {
    const text = readFileSync(resolve(repositoryRoot, "registry", "schemes.json"), "utf8");
    expect(dumps(parseJson(text))).toBe(text);
    const { schemes } = defaultRegistry();
    expect(
      schemes.map((scheme) => [
        scheme.id,
        scheme.uri,
        scheme.level,
        scheme.entity_uri,
        scheme.lowercase,
      ]),
    ).toEqual(ENTRIES);
    expect(dumps(schemes)).toBe(text);
    expect(defaultRegistry()).toBe(defaultRegistry());
  });

  it("gives every pattern one group and shared syntax only", () => {
    for (const scheme of defaultRegistry().schemes) {
      expect(scheme.patterns.length).toBeGreaterThan(0);
      for (const pattern of scheme.patterns) {
        expect(new RegExp(`(?:${pattern})|`, "u").exec("")?.length).toBe(2);
        expect(/\(\?[^:=!]/u.test(pattern), pattern).toBe(false);
      }
    }
  });

  it.each(RECOGNISED)("recognises %s", (url, uri, identifier, level) => {
    const recognition = recognize(url);
    expect([recognition?.uri, recognition?.identifier, recognition?.level]).toEqual([
      uri,
      identifier,
      level,
    ]);
  });

  it("writes a MusicBrainz ID in capitals in lower case", () => {
    expect(recognize(`https://musicbrainz.org/work/${MB_WORK.toUpperCase()}`)?.value).toBe(MB_WORK);
  });

  it.each(FORMS)("reads the form %s", (url, scheme) => {
    expect(recognize(url)?.scheme.id).toBe(scheme);
  });

  it("gives one URI for every form", () => {
    const uri = (url: string) => recognize(url)?.uri;
    const of = (id: string) =>
      new Set(FORMS.filter(([, scheme]) => scheme === id).map(([url]) => uri(url)));
    expect(of("wikidata")).toEqual(new Set(["http://www.wikidata.org/entity/Q146730"]));
    expect(of("viaf")).toEqual(new Set(["http://viaf.org/viaf/186299955"]));
    expect(uri("https://d-nb.info/gnd/118508288")).toBe("https://d-nb.info/gnd/118508288");
    expect(of("musicbrainz_work")).toEqual(new Set([`http://musicbrainz.org/work/${MB_WORK}`]));
    expect(of("musicbrainz_recording")).toEqual(
      new Set(["http://musicbrainz.org/recording/5f1a7c3e-2b4d-4e6f-8a9b-0c1d2e3f4a5b"]),
    );
    expect(of("musicbrainz_release")).toEqual(
      new Set(["http://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c"]),
    );
  });

  it.each([
    "https://imslp.org/wiki/Special:ReverseLookup/534071",
    "https://example.org/anything",
    "https://imslp.org/wiki/File:PMLP01477-Beethoven_Op106.pdf",
    "https://imslp.org/wiki/Category:Beethoven,_Ludwig_van",
    "https://imslp.org/wiki/Help:Contents",
    "https://imslp.org/wiki/IMSLP:About",
    "https://imslp.org/wiki/Special%3AReverseLookup/534071",
    `https://musicbrainz.org/work/${MB_WORK} `,
    "https://imslp.org/wiki/Sonata%E2%80",
    `musicbrainz.org/work/${MB_WORK}`,
  ])("does not recognise %s", (url) => {
    expect(recognize(url)).toBeNull();
  });

  it.each(NOT_WORK_PAGES)("does not recognise the IMSLP page %s", (page) => {
    expect(recognize(`https://imslp.org/wiki/${page}`)).toBeNull();
  });

  it.each(["Main_Page_(Example)", "Talk_Show_Suite_(Example,_Anna)"])(
    "recognises the work page %s",
    (page) => {
      expect(recognize(`https://imslp.org/wiki/${page}`)?.identifier).toEqual({
        scheme: IMSLP,
        value: page,
      });
    },
  );

  it("decodes an identifier and writes its spaces as underscores", () => {
    const recognition = recognize("https://imslp.org/wiki/Piano%20Sonata%20No.29");
    expect(recognition?.identifier).toEqual({ scheme: IMSLP, value: "Piano_Sonata_No.29" });
    expect(recognition?.value).toBe("Piano_Sonata_No.29");
  });

  it("yields an entity URI or an identifier, never both", () => {
    const samples: Readonly<Record<string, string>> = {
      musicbrainz_work: `https://musicbrainz.org/work/${MB_WORK}`,
      musicbrainz_recording: `https://musicbrainz.org/recording/${MB_WORK}`,
      musicbrainz_release: `https://musicbrainz.org/release/${MB_WORK}`,
      wikidata: "https://www.wikidata.org/wiki/Q146730",
      viaf: "https://viaf.org/viaf/186299955",
      gnd: "https://d-nb.info/gnd/118508288",
      imslp: `https://imslp.org/wiki/${OP_106}`,
      doi: "https://doi.org/10.5281/zenodo.7473560",
    };
    for (const scheme of defaultRegistry().schemes) {
      const recognition = recognize(samples[scheme.id] as string);
      expect(recognition?.scheme).toBe(scheme);
      if (scheme.entity_uri === null) {
        expect(recognition?.uri).toBeNull();
        expect(recognition?.identifier).toEqual({ scheme: scheme.uri, value: recognition?.value });
      } else {
        expect(recognition?.identifier).toBeNull();
        expect(recognition?.uri).toBe(
          scheme.entity_uri.split("{value}").join(recognition?.value ?? ""),
        );
      }
    }
  });

  it("extends into a new registry", () => {
    const original = defaultRegistry();
    const extended = withSchemes(original, [entry(), entry({ id: "y" })]);
    expect(extended.schemes.slice(-2).map((scheme) => scheme.id)).toEqual(["x", "y"]);
    expect(original.schemes.length).toBe(8);
    expect(recognize("https://example.org/page/12")).toBeNull();
    const recognition = recognize("https://example.org/page/12", extended);
    expect([recognition?.scheme.id, recognition?.uri]).toEqual([
      "x",
      "https://example.org/entity/12",
    ]);
  });

  it("reads an entry without level, entity_uri and lowercase as Python does", () => {
    const given: SchemeEntry = {
      id: "x",
      name: "Example",
      uri: "https://example.org/scheme",
      patterns: ["https://example.org/page/([0-9]+)"],
    };
    const extended = withSchemes(defaultRegistry(), [given]);
    expect(dumps(extended.schemes.at(-1))).toBe(
      dumps({ ...given, level: null, entity_uri: null, lowercase: false }),
    );
    const recognition = recognize("https://example.org/page/12", extended);
    expect([recognition?.uri, recognition?.identifier, recognition?.level]).toEqual([
      null,
      { scheme: "https://example.org/scheme", value: "12" },
      null,
    ]);
  });

  it("lowers the values of an entry stating lowercase", () => {
    const extended = withSchemes(defaultRegistry(), [
      entry({ lowercase: true, patterns: ["https://example\\.org/page/([0-9A-Za-z]+)"] }),
    ]);
    const recognition = recognize("https://example.org/page/AbC", extended);
    expect([recognition?.value, recognition?.uri]).toEqual([
      "abc",
      "https://example.org/entity/abc",
    ]);
  });

  it("replaces the entry of an ID in place", () => {
    const replaced = withSchemes(defaultRegistry(), [
      entry({
        id: "doi",
        entity_uri: "http://dx.doi.org/{value}",
        patterns: ["https?://doi\\.org/(10\\.[0-9]+/[^?#]+)"],
      }),
    ]);
    expect(replaced.schemes.map((scheme) => scheme.id)).toEqual(ENTRIES.map(([id]) => id));
    expect(recognize("https://doi.org/10.5281/zenodo.7473560", replaced)?.uri).toBe(
      "http://dx.doi.org/10.5281/zenodo.7473560",
    );
  });

  it("recognises by the first matching entry", () => {
    const late = withSchemes(defaultRegistry(), [
      entry({ patterns: ["https://musicbrainz\\.org/work/([0-9a-f-]+)"] }),
    ]);
    expect(recognize(`https://musicbrainz.org/work/${MB_WORK}`, late)?.scheme.id).toBe(
      "musicbrainz_work",
    );
  });

  const subset = "uses syntax outside the shared subset; only (?:, (?= and (?! may follow '(?'";
  it.each<[Partial<KnownScheme>, string]>([
    [
      { patterns: ["https://example.org/x"] },
      "pattern 'https://example.org/x' of scheme 'x' has 0 capturing groups; it needs exactly one",
    ],
    [
      { patterns: ["https://example.org/(a)(b)"] },
      "pattern 'https://example.org/(a)(b)' of scheme 'x' has 2 capturing groups; it needs exactly one",
    ],
    [
      { patterns: ["https://example.org/(?P<v>a)"] },
      `pattern 'https://example.org/(?P<v>a)' of scheme 'x' ${subset}`,
    ],
    [
      { patterns: ["https://example.org/(?<v>a)"] },
      `pattern 'https://example.org/(?<v>a)' of scheme 'x' ${subset}`,
    ],
    [{ patterns: ["(?<=a)(b)"] }, `pattern '(?<=a)(b)' of scheme 'x' ${subset}`],
    [{ patterns: ["(?i)(b)"] }, `pattern '(?i)(b)' of scheme 'x' ${subset}`],
    [{ patterns: ["(b"] }, "pattern '(b' of scheme 'x' is no regular expression"],
    [{ level: "score" as Level }, "scheme 'x' has the level 'score', which is no level"],
    [
      { entity_uri: "https://example.org/entity/" },
      "the entity URI template 'https://example.org/entity/' of scheme 'x' holds no {value}",
    ],
    [{ lowercase: "yes" as unknown as boolean }, "the lowercase of scheme 'x' is no boolean"],
    [{ lowercase: null as unknown as boolean }, "the lowercase of scheme 'x' is no boolean"],
  ])("refuses the entry %o", (members, message) => {
    expect(() => withSchemes(defaultRegistry(), [entry(members)])).toThrow(new Error(message));
  });
});
