import { describe, expect, it } from "vitest";
import { completeDescription, DEFAULTS, type DescriptionKind } from "../src/defaults.js";
import {
  ABSENCE_REASONS,
  type Assertion,
  assertionFor,
  type CompleteLink,
  type CompletePartSlot,
  canonicalOrder,
  complete,
  completeManifest,
  defaultRegistry,
  descriptionProblems,
  dumps,
  identityProblems,
  LEVELS,
  type Link,
  linkFromUrl,
  linkFromUrls,
  loads,
  METHODS,
  minimal,
  PARTS_RELATIONS,
  type PathSegment,
  parse,
  partSlotFromUrl,
  RELATIONS,
  SchemaValidationError,
  UnsupportedVersionError,
  unknownKeys,
  unregisteredTerms,
  validate,
  withAssertion,
  withIdentifier,
  withLabel,
  withPartOf,
  withParts,
  withRecord,
  withSchemes,
  withUri,
} from "../src/index.js";
import type { JsonObject, Lossless } from "../src/json/value.js";
import {
  fixtureFiles,
  fixtureText,
  group,
  manifest,
  rejectionCase,
  rejectionFileNames,
  timeline,
} from "./fixtures.js";

const MB = "http://musicbrainz.org/work/";
const MB_WORK = "4a622b0d-b0c0-405e-b49e-05b70c108284";
const P435 = "http://www.wikidata.org/entity/P435";
const IMSLP = "http://www.wikidata.org/entity/P839";
const OP_106 = "Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)";
const NAME = "Beethoven, Piano Sonata No. 29, Op. 106";
const LABEL = "Piano Sonata No. 29 in B♭ major, Op. 106";
const SERIES = "https://musicbrainz.org/series/004f17aa-0f46-4fec-b939-c5dfc849e5c6";
const SCHEME_NAME = "Works of Ludwig van Beethoven by opus number";
const RELEASE = "https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c";
const MOVEMENTS: [string, string][] = [
  ["80cbaf7b-a1da-3fc5-b650-6eb72a803980", "I. Allegro"],
  ["7813c9cf-6054-3ef3-b9ed-8ae4690581c9", "II. Scherzo. Assai vivace"],
  ["7d110747-f011-41d4-9ce5-a1fad9abed2f", "III. Adagio sostenuto"],
  ["cfa82cd6-bcb5-39dd-9beb-c98e275c7c84", "IV. Introduzione. Largo – Allegro risoluto"],
];
const URLS = [
  "https://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284",
  "https://www.wikidata.org/wiki/Q146730",
  "https://viaf.org/viaf/186299955",
  `https://imslp.org/wiki/${OP_106}`,
] as const;
const EDITOR: Assertion = {
  asserted_by: ["https://example.org/people/editor"],
  asserted_on: "2026-11-17",
  method: "manual",
  status: "confirmed",
};

const LINK_URIS = [
  `${MB}4a622b0d-b0c0-405e-b49e-05b70c108284`,
  "http://www.wikidata.org/entity/Q146730",
  "http://viaf.org/viaf/186299955",
];
const LINK_IDENTIFIERS = [
  { scheme: IMSLP, value: OP_106 },
  { scheme: "mb_beethoven_opus", value: "op. 106" },
];

const MINIMAL = {
  timetoshare: "0.2.0",
  name: NAME,
  timelines: [],
  schemes: [{ id: "mb_beethoven_opus", name: SCHEME_NAME, uri: [SERIES] }],
  links: [
    {
      relation: "pertains_to",
      level: "work",
      label: LABEL,
      uri: LINK_URIS,
      identifiers: LINK_IDENTIFIERS,
      parts_relation: "has_part",
      parts: MOVEMENTS.map(([mbid, label]) => ({
        uri: [`${MB}${mbid}`],
        label,
        absent: "not_represented",
      })),
      assertion: EDITOR,
    },
  ],
};

const COMPLETE = {
  timetoshare: "0.2.0",
  name: NAME,
  meta: {},
  groups: [],
  measure_maps: [],
  timelines: [],
  schemes: [{ id: "mb_beethoven_opus", name: SCHEME_NAME, uri: [SERIES], criteria: null }],
  links: [
    {
      relation: "pertains_to",
      level: "work",
      uri: LINK_URIS,
      identifiers: LINK_IDENTIFIERS,
      records: [],
      label: LABEL,
      assertion: { ...EDITOR, service: null, based_on: [], match: null },
      parts_relation: "has_part",
      parts: MOVEMENTS.map(([mbid, label]) => ({
        uri: [`${MB}${mbid}`],
        identifiers: [],
        label,
        represented_by: [],
        absent: "not_represented",
        assertion: null,
      })),
      parts_ordered: true,
      part_of: [],
    },
  ],
};

function slots(order: readonly number[]): CompletePartSlot[] {
  return order.map((index) => {
    const [mbid, label] = MOVEMENTS[index] as [string, string];
    return partSlotFromUrl(`https://musicbrainz.org/work/${mbid}`, {
      label,
      absent: "not_represented",
    });
  });
}

const SCHEME = { id: "mb_beethoven_opus", name: SCHEME_NAME, uri: [SERIES] };

function op106(): CompleteLink {
  const link = linkFromUrls(URLS, {
    identifiers: { mb_beethoven_opus: "op. 106" },
    label: LABEL,
    assertion: EDITOR,
  });
  return withParts(link, "has_part", slots([0, 1, 2, 3]));
}

function bundle(...links: CompleteLink[]): JsonObject {
  return { timetoshare: "0.2.0", name: NAME, timelines: [], schemes: [SCHEME], links };
}

describe("the work bundle of Op. 106", () => {
  it("is built in both forms", () => {
    const link = op106();
    expect(dumps(minimal(bundle(link)))).toBe(dumps(MINIMAL));
    expect(link).toEqual(COMPLETE.links[0]);
    expect(dumps(complete(bundle(link)))).toBe(dumps(COMPLETE));
    expect(dumps(complete(MINIMAL))).toBe(dumps(COMPLETE));
    expect(dumps(minimal(COMPLETE))).toBe(dumps(MINIMAL));
    for (const form of [MINIMAL, COMPLETE]) {
      const read = parse(dumps(form, { serialization: "json" }));
      expect(unknownKeys(read)).toEqual([]);
      expect(unregisteredTerms(read)).toEqual([]);
      expect(completeManifest(read).links[0]).toEqual(link);
      expect(completeManifest(read).schemes[0]).toEqual(COMPLETE.schemes[0]);
    }
    expect(dumps(MINIMAL)).toContain("♭");
    expect(dumps(MINIMAL)).toContain("–");
  });

  it("holds two readings in their order", () => {
    const first = op106();
    const second = withAssertion(withParts(first, "has_part", slots([0, 2, 1, 3])), {
      asserted_by: ["https://example.org/people/second-editor"],
      asserted_on: "2026-11-18",
      method: "imported",
      based_on: ["https://example.org/editions/london-1819"],
      status: "unconfirmed",
    });
    const value = bundle(first, second);
    validate(value);
    const read = completeManifest(parse(dumps(value, { serialization: "json" })));
    expect(read.links).toEqual([first, second]);
    expect(read.links.map((link) => link.parts.map((slot) => slot.label))).toEqual(
      [
        [0, 1, 2, 3],
        [0, 2, 1, 3],
      ].map((order) => order.map((index) => (MOVEMENTS[index] as [string, string])[1])),
    );
    expect((canonicalOrder(value) as JsonObject).links).toEqual(value.links);
  });

  it("sorts schemes and keeps every array of a link in the canonical order", () => {
    const link = {
      relation: "pertains_to",
      level: "work",
      uri: ["https://example.org/z", "https://example.org/a"],
      parts_relation: "has_part",
      parts: [
        { absent: "lost", label: "z" },
        { absent: "lost", label: "a" },
      ],
    };
    const value = manifest(
      [timeline("score", "quarters", [8, 1], { links: [link, { ...link, level: "expression" }] })],
      { schemes: [{ id: "zz" }, { id: "aa" }], links: [link, { ...link, relation: "about" }] },
    );
    const ordered = canonicalOrder(value);
    expect((ordered.schemes as JsonObject[]).map((scheme) => scheme.id)).toEqual(["aa", "zz"]);
    expect(ordered.links).toEqual(value.links);
    expect(((ordered.timelines as JsonObject[])[0] as JsonObject).links).toEqual(
      ((value.timelines as JsonObject[])[0] as JsonObject).links,
    );
  });
});

const work = (options = {}) => linkFromUrls([URLS[0]], options);
const noDate = (date: string) => `'${date}' is no Gregorian calendar date written YYYY-MM-DD`;

describe("the errors of the model", () => {
  const releaseSlot = () => partSlotFromUrl(RELEASE, { absent: "lost" });
  it.each<[string, () => unknown, string]>([
    [
      "both",
      () => partSlotFromUrl(`${MB}x`, { representedBy: ["intro"], absent: "lost" }),
      "a part slot is represented or absent, not both",
    ],
    [
      "neither",
      () => partSlotFromUrl(`${MB}x`, { label: "I." }),
      "a part slot is represented by an element or absent",
    ],
    [
      "a slot in withParts",
      () => withParts(work(), "has_part", [{ label: "I." }]),
      "a part slot is represented by an element or absent",
    ],
    [
      "no URI",
      () => linkFromUrls(["musicbrainz.org/work/x"]),
      "'musicbrainz.org/work/x' is no absolute URI",
    ],
    [
      "no URI for a slot",
      () => partSlotFromUrl("not a url", { absent: "lost" }),
      "'not a url' is no absolute URI",
    ],
    ["no URL", () => linkFromUrls([]), "a link from URLs needs one URL at least"],
    [
      "two levels",
      () => linkFromUrls([URLS[0], RELEASE]),
      `'${RELEASE}' is recognised at the level 'manifestation', '${URLS[0]}' at 'work'`,
    ],
    [
      "a contradicted level",
      () => linkFromUrls([URLS[0]], { level: "expression" }),
      `the level 'expression' contradicts '${URLS[0]}', recognised at the level 'work'`,
    ],
    [
      "a contradicting URI",
      () => withUri(work(), [RELEASE]),
      `the level 'work' contradicts '${RELEASE}', recognised at the level 'manifestation'`,
    ],
    [
      "no level",
      () => linkFromUrls([URLS[1], URLS[2]]),
      `no level is recognised from '${URLS[1]}', '${URLS[2]}'; state the level`,
    ],
    ["an unknown level", () => linkFromUrls([URLS[1]], { level: "score" }), "'score' is no level"],
    [
      "an unknown level of a link",
      () => withLabel({ relation: "pertains_to", level: "score" as "work" }, null),
      "'score' is no level",
    ],
    [
      "an agent without a relation",
      () => linkFromUrls(["https://example.org/people/composer"], { level: "agent" }),
      "an agent link states its relation, the agent's role",
    ],
    [
      "an agent with pertains_to",
      () =>
        linkFromUrls(["https://example.org/people/composer"], {
          level: "agent",
          relation: "pertains_to",
        }),
      "an agent link never uses the relation 'pertains_to'",
    ],
    [
      "parts without a relation",
      () =>
        withLabel({ relation: "pertains_to", level: "work", parts: [{ absent: "lost" }] }, null),
      "a link with parts states its parts_relation",
    ],
    [
      "a parts relation without parts",
      () => withLabel({ relation: "pertains_to", level: "work", parts_relation: "has_part" }, null),
      "a link without parts states no parts_relation",
    ],
    [
      "withParts given no slot",
      () => withParts(work(), "has_part", []),
      "a link without parts states no parts_relation",
    ],
    [
      "unordered parts without parts",
      () => withLabel({ relation: "pertains_to", level: "work", parts_ordered: false }, null),
      "a link without parts keeps parts_ordered true",
    ],
    ...["op. 106", "x"].map((value): [string, () => unknown, string] => [
      `the identifier ${value}`,
      () => linkFromUrls([URLS[1]], { identifiers: { [P435]: value } }),
      `'${value}' is no value of the scheme 'MusicBrainz work ID'`,
    ]),
    [
      "an identifier given to withIdentifier",
      () => withIdentifier(work(), P435, "op. 106"),
      "'op. 106' is no value of the scheme 'MusicBrainz work ID'",
    ],
    [
      "an identifier of another level",
      () => withIdentifier(linkFromUrls([URLS[1]], { level: "expression" }), P435, MB_WORK),
      `the level 'expression' contradicts '${MB}${MB_WORK}', recognised at the level 'work'`,
    ],
    [
      "a slot of another level",
      () => withParts(work(), "has_part", [...slots([0]), releaseSlot()]),
      "part slot 2 is recognised at the level 'manifestation', the link's level is 'work'",
    ],
    ...["2026-02-30", "2100-02-29", "0000-01-01", "20261117", "17 November 2026"].map(
      (date): [string, () => unknown, string] => [
        `the date ${date}`,
        () => linkFromUrls([URLS[0]], { assertion: { asserted_on: date } }),
        noDate(date),
      ],
    ),
    [
      "an impossible date of a slot",
      () => partSlotFromUrl(`${MB}x`, { absent: "lost", assertion: { asserted_on: "2026-11-31" } }),
      noDate("2026-11-31"),
    ],
    [
      "an impossible date given to withAssertion",
      () => withAssertion(work(), { asserted_on: "2026-02-30" }),
      noDate("2026-02-30"),
    ],
    [
      "an impossible date of a slot given to withParts",
      () =>
        withParts(work(), "has_part", [
          { absent: "lost", assertion: { asserted_on: "2026-11-31" } },
        ]),
      noDate("2026-11-31"),
    ],
    [
      "an impossible date of a part_of entry",
      () =>
        withPartOf(work(), {
          parts_relation: "has_part",
          assertion: { asserted_on: "2026-13-01" },
        }),
      noDate("2026-13-01"),
    ],
    [
      "an impossible date of a link given to withLabel",
      () =>
        withLabel(
          { relation: "pertains_to", level: "work", assertion: { asserted_on: "2026-02-30" } },
          null,
        ),
      noDate("2026-02-30"),
    ],
    [
      "an impossible date read by assertionFor",
      () =>
        assertionFor(
          { relation: "pertains_to", level: "work" },
          { absent: "lost", assertion: { asserted_on: "2026-02-30" } },
        ),
      noDate("2026-02-30"),
    ],
  ])("throws for %s", (_name, build, message) => {
    expect(build).toThrow(new Error(message));
  });

  it("keeps a day of the calendar as written", () => {
    const leap = work({ assertion: { asserted_on: "2024-02-29" } });
    expect(leap.assertion?.asserted_on).toBe("2024-02-29");
  });
});

describe("normalisation and copy-on-write", () => {
  it("collapses URLs into their first normal form", () => {
    const link = linkFromUrls(
      [
        URLS[0],
        `${MB}4a622b0d-b0c0-405e-b49e-05b70c108284/`,
        URLS[3],
        "https://imslp.org/wiki/Piano_Sonata_No.29%2C_Op.106_%28Beethoven%2C_Ludwig_van%29",
        "https://example.org/anything",
      ],
      {
        identifiers: [
          { scheme: "mb_beethoven_opus", value: "op. 106" },
          { scheme: IMSLP, value: OP_106 },
        ],
      },
    );
    expect(link.uri).toEqual([
      `${MB}4a622b0d-b0c0-405e-b49e-05b70c108284`,
      "https://example.org/anything",
    ]);
    expect(link.identifiers).toEqual([
      { scheme: IMSLP, value: OP_106 },
      { scheme: "mb_beethoven_opus", value: "op. 106" },
    ]);
    expect([link.relation, link.level]).toEqual(["pertains_to", "work"]);
    const agent = linkFromUrl("https://example.org/people/composer", {
      level: "agent",
      relation: "marcrel:cmp",
    });
    expect([agent.relation, agent.level, agent.uri]).toEqual([
      "marcrel:cmp",
      "agent",
      ["https://example.org/people/composer"],
    ]);
  });

  it("gives a new link for every change", () => {
    const base = work({ label: "Op. 106" });
    const before = dumps(base);
    const extended = withUri(base, [
      "https://www.wikidata.org/wiki/Q146730",
      "http://www.wikidata.org/entity/Q146730",
      URLS[0],
      URLS[3],
    ]);
    expect(extended.uri).toEqual([
      `${MB}4a622b0d-b0c0-405e-b49e-05b70c108284`,
      "http://www.wikidata.org/entity/Q146730",
    ]);
    expect(extended.identifiers).toEqual([{ scheme: IMSLP, value: OP_106 }]);
    const identified = withIdentifier(extended, "mb_beethoven_opus", "op. 106");
    expect(withIdentifier(identified, "mb_beethoven_opus", "op. 106")).toEqual(identified);
    const record = { url: "https://example.org/records/op106.json", size: 812 };
    const recorded = withRecord(withRecord(identified, record), record);
    const completed = { media_type: null, integrity: null, ...record };
    expect(recorded.records).toEqual([completed, completed]);
    expect(withLabel(recorded, "Hammerklavier").label).toBe("Hammerklavier");
    expect(withAssertion(recorded, EDITOR).assertion).toEqual(
      completeDescription(EDITOR, "assertion"),
    );
    const first = withParts(base, "has_part", slots([0, 1]), { ordered: false });
    const second = withParts(first, "has_part", slots([2]));
    expect([first.parts.length, first.parts_ordered]).toEqual([2, false]);
    expect([second.parts, second.parts_ordered]).toEqual([slots([2]), true]);
    const whole = {
      parts_relation: "has_part",
      label: "The thirty-two piano sonatas",
      position: 29,
    };
    const wholes = withPartOf(withPartOf(base, whole), whole).part_of;
    expect(wholes).toEqual([
      completeDescription(whole, "part_of"),
      completeDescription(whole, "part_of"),
    ]);
    expect(dumps(base)).toBe(before);
  });

  it("stores an identifier of a scheme minting URIs as its URI", () => {
    const upper = MB_WORK.toUpperCase();
    const link = linkFromUrls([URLS[1]], { identifiers: { [P435]: upper } });
    expect([link.uri, link.identifiers, link.level]).toEqual([
      ["http://www.wikidata.org/entity/Q146730", `${MB}${MB_WORK}`],
      [],
      "work",
    ]);
    expect(linkFromUrls([URLS[0]], { identifiers: [{ scheme: P435, value: upper }] }).uri).toEqual([
      `${MB}${MB_WORK}`,
    ]);
    const doi = linkFromUrls([URLS[1]], {
      level: "work",
      identifiers: {
        "http://www.wikidata.org/entity/P356": "10.5281/zenodo.7473560",
        [IMSLP]: OP_106,
        mb_beethoven_opus: "op. 106",
      },
    });
    expect(doi.uri).toEqual([
      "http://www.wikidata.org/entity/Q146730",
      "https://doi.org/10.5281/zenodo.7473560",
    ]);
    expect(doi.identifiers).toEqual([
      { scheme: IMSLP, value: OP_106 },
      { scheme: "mb_beethoven_opus", value: "op. 106" },
    ]);
    const bare = linkFromUrls([URLS[1]], { level: "work" });
    expect(withIdentifier(bare, P435, upper).uri).toEqual([
      "http://www.wikidata.org/entity/Q146730",
      `${MB}${MB_WORK}`,
    ]);
    const held = work();
    expect(withIdentifier(held, P435, upper)).toEqual(held);
    const extended = withSchemes(defaultRegistry(), [
      {
        id: "x",
        name: "Example",
        uri: "https://example.org/scheme",
        entity_uri: "https://example.org/entity/{value}",
        patterns: ["https://example\\.org/entity/([0-9]+)"],
      },
    ]);
    const example = linkFromUrls(["https://example.org/anything"], { level: "work" });
    expect(
      withIdentifier(example, "https://example.org/scheme", "12", { registry: extended }).uri,
    ).toEqual(["https://example.org/anything", "https://example.org/entity/12"]);
    expect(withIdentifier(example, "https://example.org/scheme", "12").identifiers).toEqual([
      { scheme: "https://example.org/scheme", value: "12" },
    ]);
    validate(
      manifest([timeline("score")], {
        links: [
          { relation: "pertains_to", level: "work", identifiers: [{ scheme: P435, value: "106" }] },
        ],
      }),
    );
  });

  it("gives one URI for a value in capitals", () => {
    const held = work();
    expect(withUri(held, [`https://musicbrainz.org/work/${MB_WORK.toUpperCase()}`])).toEqual(held);
    expect(held.uri).toEqual([`${MB}${MB_WORK}`]);
  });

  it("gives an entry its link's assertion unless it states one", () => {
    const own: Assertion = { method: "reconciled", service: "https://example.org/reconcile" };
    const slot = { represented_by: ["intro"] };
    const stated = { represented_by: ["intro"], assertion: own };
    const whole = { parts_relation: "has_part" };
    const link = withParts(work({ assertion: EDITOR }), "has_part", [slot, stated]);
    expect([slot, stated, whole].map((entry) => assertionFor(link, entry))).toEqual([
      completeDescription(EDITOR, "assertion"),
      completeDescription(own, "assertion"),
      completeDescription(EDITOR, "assertion"),
    ]);
    expect(assertionFor(work(), slot)).toBeNull();
  });
});

describe("forms and unknown keys", () => {
  const samples: Record<DescriptionKind, JsonObject> = {
    scheme: { id: "opus" },
    link: { relation: "pertains_to", level: "work" },
    descriptor: { url: "records/op106.json" },
    assertion: {},
    part_slot: { absent: "lost" },
    part_of: { parts_relation: "has_part" },
  };

  /** A manifest holding the sample of a kind at its place, and the path to it. */
  function holding(
    kind: DescriptionKind,
    value: JsonObject,
  ): [JsonObject, (form: JsonObject) => unknown] {
    const link = (members: JsonObject) => ({ relation: "pertains_to", level: "work", ...members });
    const at = (form: JsonObject) => (form.links as JsonObject[])[0] as JsonObject;
    switch (kind) {
      case "scheme":
        return [manifest([], { schemes: [value] }), (form) => (form.schemes as JsonObject[])[0]];
      case "link":
        return [manifest([], { links: [value] }), at];
      case "descriptor":
        return [
          manifest([], { links: [link({ records: [value] })] }),
          (form) => (at(form).records as JsonObject[])[0],
        ];
      case "assertion":
        return [
          manifest([], { links: [link({ assertion: value })] }),
          (form) => at(form).assertion,
        ];
      case "part_slot":
        return [
          manifest([], { links: [link({ parts_relation: "has_part", parts: [value] })] }),
          (form) => (at(form).parts as JsonObject[])[0],
        ];
      case "part_of":
        return [
          manifest([], { links: [link({ part_of: [value] })] }),
          (form) => (at(form).part_of as JsonObject[])[0],
        ];
    }
  }

  it.each(Object.keys(samples) as DescriptionKind[])(
    "takes both forms of %s from the defaults table",
    (kind) => {
      const sample = samples[kind];
      const [value, place] = holding(kind, sample);
      expect(place(complete(value) as JsonObject)).toEqual({ ...DEFAULTS[kind], ...sample });
      expect(place(minimal(complete(value)) as JsonObject)).toEqual(sample);
    },
  );

  it("gives identifiers no defaults", () => {
    const value = manifest([], {
      links: [
        { relation: "pertains_to", level: "work", identifiers: [{ scheme: "opus", value: "106" }] },
      ],
    });
    expect(((complete(value).links as JsonObject[])[0] as JsonObject).identifiers).toEqual([
      { scheme: "opus", value: "106" },
    ]);
  });

  it("keeps unknown keys on every object", () => {
    const noted = (value: JsonObject, note: string): JsonObject => ({ ...value, "x-note": note });
    const assertion = noted({ method: "manual" }, "assertion");
    const data = noted(
      {
        relation: "pertains_to",
        level: "work",
        identifiers: [noted({ scheme: "opus", value: "106" }, "identifier")],
        records: [noted({ url: "records/op106.json" }, "record")],
        assertion,
        parts_relation: "has_part",
        parts: [noted({ absent: "lost", assertion }, "slot")],
        part_of: [noted({ parts_relation: "has_part" }, "whole")],
      },
      "link",
    );
    const changed: JsonObject = withLabel(data as Lossless<Link>, null);
    const minimalForm = (
      minimal(manifest([], { links: [changed] })).links as JsonObject[]
    )[0] as JsonObject;
    for (const written of [changed, minimalForm]) {
      expect(written["x-note"]).toBe("link");
      expect(((written.identifiers as JsonObject[])[0] as JsonObject)["x-note"]).toBe("identifier");
      expect(((written.records as JsonObject[])[0] as JsonObject)["x-note"]).toBe("record");
      expect((written.assertion as JsonObject)["x-note"]).toBe("assertion");
      const slot = (written.parts as JsonObject[])[0] as JsonObject;
      expect(slot["x-note"]).toBe("slot");
      expect((slot.assertion as JsonObject)["x-note"]).toBe("assertion");
      expect(((written.part_of as JsonObject[])[0] as JsonObject)["x-note"]).toBe("whole");
    }
    expect(minimalForm).toEqual(data);
    expect(
      unknownKeys(manifest([], { schemes: [noted({ id: "opus" }, "scheme")], links: [data] })),
    ).toEqual(
      [
        ["links", 0],
        ["links", 0, "assertion"],
        ["links", 0, "identifiers", 0],
        ["links", 0, "part_of", 0],
        ["links", 0, "parts", 0],
        ["links", 0, "parts", 0, "assertion"],
        ["links", 0, "records", 0],
        ["schemes", 0],
      ].map((path) => ({ path, key: "x-note" })),
    );
    const scheme = noted({ id: "opus" }, "scheme");
    const schemes = minimal(manifest([], { schemes: [scheme] })).schemes;
    expect(schemes).toEqual([{ id: "opus", "x-note": "scheme" }]);
  });
});

const link = (members: JsonObject = {}): JsonObject => ({
  relation: "pertains_to",
  level: "work",
  ...members,
});

const slotLink = (...targets: string[]): JsonObject =>
  link({
    parts_relation: "has_part",
    parts: targets.map((target) => ({ represented_by: [target] })),
  });

function listed(
  found: readonly SchemaValidationError[],
): [readonly PathSegment[], string, string][] {
  return found.map((problem) => [problem.path, problem.code, problem.detail]);
}

/** The problems of a document breaking description rules only, both ways. */
function problems(value: JsonObject): [readonly PathSegment[], string, string][] {
  const found = listed(identityProblems(value));
  expect(listed(descriptionProblems(value))).toEqual(found);
  return found;
}

function segmented(): JsonObject {
  return timeline("score", "quarters", [16, 1], {
    is_segment_line: true,
    children: [
      timeline("a", "quarters", [8, 1], { offset: [0, 1] }),
      timeline("b", "quarters", [8, 1], {
        offset: [8, 1],
        children: [timeline("b1", "quarters", [8, 1], { offset: [0, 1] })],
      }),
    ],
    regions: [{ id: "intro", start: [0, 1], end: [4, 1] }],
  });
}

const opus = (scheme: string) => [{ scheme, value: "106" }];

describe("the rules of links", () => {
  it("lets a slot be represented by timelines and regions", () => {
    const value = manifest([segmented()], { links: [slotLink("score", "a", "b1", "intro")] });
    validate(value);
    expect(problems(value)).toEqual([]);
  });

  it.each(["ghost", "g", "bars"])("refuses a slot represented by %s", (target) => {
    const rows = [{ count: 1, qstamp: [0, 1], actual_length: [4, 1] }];
    const value = manifest([segmented()], {
      groups: [group("g", ["score"])],
      measure_maps: [{ id: "bars", rows }],
      links: [slotLink("intro", target)],
    });
    const problem: [PathSegment[], string, string] = [
      ["links", 0, "parts", 1, "represented_by", 0],
      "dangling_target",
      `'${target}' names no timeline or region of this manifest`,
    ];
    expect(problems(value)).toEqual([problem]);
    try {
      validate(value);
      expect.unreachable();
    } catch (error) {
      expect([
        (error as SchemaValidationError).path,
        (error as SchemaValidationError).code,
      ]).toEqual(problem.slice(0, 2));
    }
  });

  it("lets an identifier name a scheme or an absolute URI", () => {
    const accepted = manifest([timeline("score")], {
      schemes: [{ id: "opus" }],
      links: [link({ identifiers: [...opus("opus"), ...opus(IMSLP)] })],
    });
    validate(accepted);
    expect(problems(accepted)).toEqual([]);
    const message = "'opus' names no scheme of this manifest and is no absolute URI";
    const value = manifest(
      [
        timeline("score", "quarters", [8, 1], {
          links: [link({ identifiers: opus("opus") })],
          regions: [
            {
              id: "intro",
              start: [0, 1],
              end: [4, 1],
              links: [link({ identifiers: opus("opus") })],
            },
          ],
          children: [
            timeline("verse", "quarters", [8, 1], {
              offset: [0, 1],
              links: [link({ identifiers: opus("opus") })],
            }),
          ],
        }),
      ],
      {
        links: [
          link({
            identifiers: opus("opus"),
            parts_relation: "has_part",
            parts: [{ absent: "lost", identifiers: opus("opus") }],
            part_of: [{ parts_relation: "has_part", identifiers: opus("opus") }],
          }),
        ],
      },
    );
    const root = ["timelines", 0];
    expect(problems(value)).toEqual(
      [
        ["links", 0, "identifiers", 0, "scheme"],
        ["links", 0, "parts", 0, "identifiers", 0, "scheme"],
        ["links", 0, "part_of", 0, "identifiers", 0, "scheme"],
        [...root, "links", 0, "identifiers", 0, "scheme"],
        [...root, "regions", 0, "links", 0, "identifiers", 0, "scheme"],
        [...root, "children", 0, "links", 0, "identifiers", 0, "scheme"],
      ].map((path) => [path, "dangling_target", message]),
    );
  });

  it.each<[JsonObject[], PathSegment[], string]>([
    [[{ id: "score" }], ["schemes", 0, "id"], "#/timelines/0/id"],
    [[{ id: "intro" }], ["schemes", 0, "id"], "#/timelines/0/regions/0/id"],
    [[{ id: "opus" }, { id: "opus" }], ["schemes", 1, "id"], "#/schemes/0/id"],
  ])("keeps the scheme IDs %o unique", (schemes, path, first) => {
    const value = manifest(
      [
        timeline("score", "quarters", [8, 1], {
          regions: [{ id: "intro", start: [0, 1], end: [4, 1] }],
        }),
      ],
      { schemes },
    );
    const id = (schemes.at(-1) as JsonObject).id;
    expect(problems(value)).toEqual([
      [path, "duplicate_id", `'${id}' is not unique in the manifest, first at ${first}`],
    ]);
  });

  it("keeps the manifest ID apart from a scheme's", () => {
    const value = manifest([timeline("score")], { id: "opus", schemes: [{ id: "opus" }] });
    expect(problems(value)).toEqual([
      [["id"], "manifest_id", "'opus' is not unique in the manifest, first at #/schemes/0/id"],
    ]);
  });

  it("reads a link's identifier before its slot", () => {
    const value = manifest([timeline("score")], {
      links: [{ ...slotLink("ghost"), identifiers: opus("opus") }],
    });
    expect(problems(value).map(([path]) => path)).toEqual([
      ["links", 0, "identifiers", 0, "scheme"],
      ["links", 0, "parts", 0, "represented_by", 0],
    ]);
  });

  it.each(["2024-02-29", "2000-02-29", "0001-01-01", "9999-12-31"])(
    "accepts an assertion dated %s",
    (date) => {
      const value = manifest([timeline("score")], {
        links: [link({ assertion: { asserted_on: date } })],
      });
      validate(value);
      expect(problems(value)).toEqual([]);
    },
  );

  it.each([
    "2026-02-30",
    "2023-02-29",
    "2100-02-29",
    "2026-11-31",
    "2026-13-01",
    "2026-00-10",
    "2026-11-00",
    "0000-01-01",
  ])("refuses an assertion dated %s", (date) => {
    const value = manifest([timeline("score")], {
      links: [link({ assertion: { asserted_on: date } })],
    });
    const expected = [["links", 0, "assertion", "asserted_on"], "calendar_date", noDate(date)];
    expect(problems(value)).toEqual([expected]);
    try {
      validate(value);
      expect.unreachable();
    } catch (error) {
      const { path, code, detail } = error as SchemaValidationError;
      expect([path, code, detail]).toEqual(expected);
    }
  });

  it("reads a link's dates with its references", () => {
    const dated = (day: string) => ({ asserted_on: `2026-02-${day}` });
    const value = manifest([timeline("score")], {
      links: [
        link({
          assertion: dated("30"),
          identifiers: opus("opus"),
          parts_relation: "has_part",
          parts: [{ represented_by: ["ghost"], assertion: dated("31") }],
          part_of: [{ parts_relation: "has_part", assertion: dated("29") }],
        }),
      ],
    });
    expect(problems(value)).toEqual([
      [["links", 0, "assertion", "asserted_on"], "calendar_date", noDate("2026-02-30")],
      [
        ["links", 0, "identifiers", 0, "scheme"],
        "dangling_target",
        "'opus' names no scheme of this manifest and is no absolute URI",
      ],
      [["links", 0, "parts", 0, "assertion", "asserted_on"], "calendar_date", noDate("2026-02-31")],
      [
        ["links", 0, "parts", 0, "represented_by", 0],
        "dangling_target",
        "'ghost' names no timeline or region of this manifest",
      ],
      [
        ["links", 0, "part_of", 0, "assertion", "asserted_on"],
        "calendar_date",
        noDate("2026-02-29"),
      ],
    ]);
  });

  it("refuses by the schema's rules of slots and links", () => {
    const pathOf = (value: JsonObject): readonly PathSegment[] => {
      try {
        validate(value);
      } catch (error) {
        expect((error as SchemaValidationError).code).toBe("schema");
        return (error as SchemaValidationError).path;
      }
      throw new Error("the manifest validates");
    };
    const withSlots = (...entries: JsonObject[]) =>
      manifest([timeline("score")], {
        links: [link({ parts_relation: "has_part", parts: entries })],
      });
    const slot = ["links", 0, "parts", 0];
    expect(pathOf(withSlots({ represented_by: ["score"], absent: "lost" }))).toEqual([
      ...slot,
      "absent",
    ]);
    expect(pathOf(withSlots({ represented_by: [], absent: null }))).toEqual([...slot, "absent"]);
    expect(pathOf(withSlots({ label: "I." }))).toEqual(slot);
    const agent = { relation: "pertains_to", level: "agent" };
    expect(pathOf(manifest([timeline("score")], { links: [agent] }))).toEqual(["links", 0]);
    validate(manifest([timeline("score")], { links: [{ ...agent, relation: "marcrel:cmp" }] }));
    const parts = [{ absent: "lost" }];
    expect(
      pathOf(manifest([timeline("score")], { links: [link({ parts, parts_relation: null })] })),
    ).toEqual(["links", 0, "parts_relation"]);
    expect(pathOf(manifest([timeline("score")], { links: [link({ parts })] }))).toEqual([
      "links",
      0,
    ]);
    validate(manifest([timeline("score")], { links: [link({ parts: [], parts_relation: null })] }));
    validate(manifest([timeline("score")], { links: [link({ parts: [] })] }));
    const withoutParts: [JsonObject, string][] = [
      [{ parts_relation: "has_part" }, "parts_relation"],
      [{ parts: [], parts_relation: "has_part" }, "parts_relation"],
      [{ parts_ordered: false }, "parts_ordered"],
      [{ parts: [], parts_ordered: false }, "parts_ordered"],
    ];
    for (const [members, member] of withoutParts) {
      expect(pathOf(manifest([timeline("score")], { links: [link(members)] }))).toEqual([
        "links",
        0,
        member,
      ]);
    }
    validate(
      manifest([timeline("score")], {
        links: [
          link({ parts_relation: "has_part", parts: [{ absent: "lost" }], parts_ordered: false }),
        ],
      }),
    );
    const criteria: [string, boolean][] = [
      ["criteria/opus-numbers.html", false],
      ["https://example.org/criteria", false],
      ["", true],
      ["criteria/opus numbers", true],
    ];
    for (const [written, refused] of criteria) {
      const value = manifest([timeline("score")], { schemes: [{ id: "opus", criteria: written }] });
      if (refused) expect(pathOf(value)).toEqual(["schemes", 0, "criteria"]);
      else validate(value);
    }
  });

  it.each([
    [
      "description_slot_represented_by_unresolved",
      "'ghost' names no timeline or region of this manifest",
    ],
    [
      "description_identifier_scheme_unresolved",
      "'opus' names no scheme of this manifest and is no absolute URI",
    ],
    [
      "description_scheme_id_duplicate",
      "'score' is not unique in the manifest, first at #/timelines/0/id",
    ],
    [
      "description_asserted_on_impossible_date",
      "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD",
    ],
  ])("gives the shared case %s its message", (name, message) => {
    const testCase = rejectionCase(name);
    try {
      validate(testCase.manifest);
      expect.unreachable();
    } catch (error) {
      const { path, code, detail } = error as SchemaValidationError;
      expect([path, code, detail]).toEqual([testCase.path, testCase.code, message]);
    }
  });
});

describe("the description layer alone", () => {
  it("shares nineteen cases of links", () => {
    expect(rejectionFileNames().filter((name) => name.startsWith("description_"))).toHaveLength(19);
  });

  it.each(rejectionFileNames())("gives the shared case %s its problem of links or none", (name) => {
    const testCase = rejectionCase(name);
    const found = descriptionProblems(testCase.manifest as JsonObject).map((problem) => [
      problem.path,
      problem.code,
    ]);
    expect(found).toEqual(name.startsWith("description_") ? [[testCase.path, testCase.code]] : []);
  });

  it.each(fixtureFiles())("finds no problem of links in %s", (file) => {
    expect(descriptionProblems(loads(fixtureText(file)) as JsonObject)).toEqual([]);
  });

  const brokenElsewhere = (members: JsonObject = {}): JsonObject => ({
    timetoshare: "9.9.9",
    timelines: [
      {
        id: "a",
        unit: "beats",
        length: [8, 1],
        regions: [{ id: "r", start: [0, 1], end: [4, 1] }, 7],
        children: [{ id: "c", unit: "seconds", length: 60.5, offset: 100.5 }],
      },
      { id: "a", unit: "quarters", length: [8, 1] },
    ],
    groups: [{ id: "grp", members: ["ghost"] }],
    graphical: "none",
    links: [slotLink("r")],
    ...members,
  });

  it("refuses nothing outside the description layer", () => {
    const sound = brokenElsewhere({ schemes: [{ id: "s" }] });
    ((sound.links as JsonObject[])[0] as JsonObject).identifiers = opus("s");
    expect(() => validate(sound)).toThrow(UnsupportedVersionError);
    expect(descriptionProblems(sound)).toEqual([]);
    const broken = brokenElsewhere({ id: "g", schemes: [{ id: "a" }, { id: "g" }] });
    ((broken.links as JsonObject[])[0] as JsonObject).identifiers = opus("q");
    expect(listed(descriptionProblems(broken))).toEqual([
      [
        ["schemes", 0, "id"],
        "duplicate_id",
        "'a' is not unique in the manifest, first at #/timelines/0/id",
      ],
      [["id"], "manifest_id", "'g' is not unique in the manifest, first at #/schemes/1/id"],
      [
        ["links", 0, "identifiers", 0, "scheme"],
        "dangling_target",
        "'q' names no scheme of this manifest and is no absolute URI",
      ],
    ]);
  });

  it("checks each array of the layer", () => {
    const value = manifest(
      [
        timeline("score", "quarters", [8, 1], {
          links: [{ relation: "pertains_to" }],
          regions: [
            { id: "r", start: [0, 1], end: [4, 1], links: [link({ level: "score" })] },
            { id: "s", start: [4, 1], end: [8, 1], links: [link({ identifiers: opus("q") })] },
          ],
          children: [
            timeline("verse", "quarters", [8, 1], {
              offset: [0, 1],
              links: [link({ records: [{ url: "r.json", size: Number.POSITIVE_INFINITY }] })],
            }),
          ],
        }),
      ],
      { schemes: [{ name: "Opus" }], links: "none" },
    );
    const found = descriptionProblems(value);
    expect(found.map((problem) => [problem.path, problem.code])).toEqual([
      [["schemes", 0], "schema"],
      [["links"], "schema"],
      [["timelines", 0, "links", 0], "schema"],
      [["timelines", 0, "regions", 0, "links", 0, "level"], "schema"],
      [["timelines", 0, "children", 0, "links", 0, "records", 0, "size"], "finite_number"],
    ]);
    expect(found.at(-1)?.detail).toBe("size of 'verse' is not a finite number");
  });
});

describe("unregistered terms", () => {
  const terms = (value: JsonObject) =>
    unregisteredTerms(value).map((entry) => [entry.path, entry.term]);

  it("has the vocabularies", () => {
    expect(RELATIONS).toEqual(["pertains_to"]);
    expect(METHODS).toEqual(["manual", "reconciled", "imported", "inferred"]);
    expect(PARTS_RELATIONS).toEqual(["has_part", "aggregates", "incorporates"]);
    expect(ABSENCE_REASONS).toEqual([
      "not_represented",
      "lost",
      "unfinished",
      "unknown",
      "not_recorded",
    ]);
    expect(LEVELS).toEqual(["work", "expression", "manifestation", "item", "agent"]);
  });

  const described = (
    relation: string,
    method: string,
    partsRelation: string,
    absent: string,
    whole: string,
  ) => {
    const assertion = { method };
    return link({
      relation,
      assertion,
      parts_relation: partsRelation,
      parts: [{ absent, assertion }],
      part_of: [{ parts_relation: whole, assertion }],
    });
  };

  it("lists no registered word and no extension term", () => {
    const methods = [...METHODS, METHODS[0]];
    const relations = [...PARTS_RELATIONS, ...PARTS_RELATIONS.slice(0, 2)];
    const links = ABSENCE_REASONS.map((absent, index) =>
      described(
        "pertains_to",
        methods[index] as string,
        relations[index] as string,
        absent,
        relations[index] as string,
      ),
    );
    const premis = "http://id.loc.gov/vocabulary/preservation/eventType/val";
    links.push(
      described(
        "http://id.loc.gov/vocabulary/relators/cmp",
        premis,
        "frbr:hasPart",
        "ex:destroyed",
        "dcterms:isPartOf",
      ),
    );
    links.push({ relation: "marcrel:cmp", level: "agent", assertion: { method: premis } });
    expect(terms(manifest([timeline("score")], { links }))).toEqual([]);
  });

  it("lists every unregistered word in path order", () => {
    const value = manifest(
      [
        timeline("score", "quarters", [8, 1], {
          links: [link({ relation: "about" })],
          regions: [
            {
              id: "intro",
              start: [0, 1],
              end: [4, 1],
              links: [link({ assertion: { method: "guessed" } })],
            },
          ],
        }),
      ],
      { links: [described("has_part", "lost", "contains", "destroyed", "holds")] },
    );
    validate(value);
    expect(terms(value)).toEqual([
      [["links", 0, "assertion", "method"], "lost"],
      [["links", 0, "part_of", 0, "assertion", "method"], "lost"],
      [["links", 0, "part_of", 0, "parts_relation"], "holds"],
      [["links", 0, "parts", 0, "absent"], "destroyed"],
      [["links", 0, "parts", 0, "assertion", "method"], "lost"],
      [["links", 0, "parts_relation"], "contains"],
      [["links", 0, "relation"], "has_part"],
      [["timelines", 0, "links", 0, "relation"], "about"],
      [["timelines", 0, "regions", 0, "links", 0, "assertion", "method"], "guessed"],
    ]);
  });

  it("raises for an invalid manifest before listing a term", () => {
    expect(() =>
      unregisteredTerms(manifest([timeline("score")], { links: [{ relation: "about" }] })),
    ).toThrow(SchemaValidationError);
  });
});
