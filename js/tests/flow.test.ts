import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import * as timetoshare from "../src/index.js";
import {
  ATOMIC_SECTION,
  canonicalOrder,
  complete,
  dumps,
  loads,
  NAMESPACE,
  SchemaValidationError,
  usedPrefixes,
  withBareIds,
  withContext,
} from "../src/index.js";
import { JsonFloat, type JsonObject } from "../src/json/value.js";
import { compareRationals, exact, type Rational, rational } from "../src/numbers/exact.js";
import {
  CONVENTIONS,
  CONVERTER,
  EARLIER_ROLES,
  MANIFESTATIONS,
  rejected,
} from "../src/validate/flow.js";
import {
  fixtureText,
  identityProblems,
  loadSchemaFile,
  manifest,
  manifestWarnings,
  repositoryRoot,
  statementProblems,
  timeline,
  unknownKeys,
  validate,
} from "./fixtures.js";

type Node = Record<string, unknown>;
type Found = [string, readonly (string | number)[], string];

const defs = (loadSchemaFile() as { $defs: Record<string, Node> }).$defs;
const properties = (name: string) => (defs[name] as Node).properties as Record<string, Node>;
const EDITOR = "https://example.org/people/editor";
const FALSE = { beliefs: [{ actor: EDITOR, belief: "false", date: "2026-11-25" }] };
const FLOWS = resolve(repositoryRoot, "fixtures", "flows", "0.2.0");

const jump = (id: string, at: number, targets: JsonObject[], members: JsonObject = {}) => ({
  id,
  role: "jump",
  coordinate: [at, 1],
  targets,
  ...members,
});

const element = (id: string, role: string, at: number, members: JsonObject = {}) => ({
  id,
  role,
  coordinate: [at, 1],
  ...members,
});

const score = (flow: JsonObject[], members: JsonObject = {}) =>
  manifest([timeline("score", "quarters", [8, 1], { flow_control: flow, ...members })]);

function problems(value: JsonObject): Found[] {
  return identityProblems(value).map((problem) => [problem.code, problem.path, problem.detail]);
}

function refusal(check: () => void): Found {
  try {
    check();
  } catch (error) {
    if (!(error instanceof SchemaValidationError)) throw error;
    return [error.code, error.path, error.detail];
  }
  throw new Error("value was accepted");
}

describe("the schema of flow control", () => {
  it("has five roles, each carrying its own members", () => {
    const flow = defs.FlowControlElement as Node;
    expect(properties("FlowControlElement").role?.enum).toEqual([
      "jump",
      "jump_target",
      "break",
      "section_break",
      "barline",
    ]);
    expect(flow.required).toEqual(["id", "role", "coordinate"]);
    expect(Object.keys(properties("FlowControlElement"))).toEqual([
      "id",
      "role",
      "coordinate",
      "targets",
      "manifestation",
      "ends",
      "name",
      "label",
      "meta",
      "provenance",
    ]);
    expect(properties("FlowControlElement").manifestation).not.toHaveProperty("enum");
    expect(Object.keys(properties("JumpDestination"))).toEqual([
      "to",
      "by",
      "passes",
      "repeat_count",
      "after",
      "determined",
      "reset",
      "manifestation",
      "label",
    ]);
    expect(defs.JumpDestination).not.toHaveProperty("required");
    expect((defs.JumpDestination as Node).not).toEqual({ required: ["to", "by"] });
    expect((defs.BreakCondition as Node).anyOf).toEqual([
      { required: ["passes"] },
      { required: ["after"] },
    ]);
    expect((defs.BreakCondition as Node).minProperties).toBe(1);
  });

  it("lists FlowMaps and virtual timelines at the top level", () => {
    expect(properties("Manifest").flow_maps?.items).toEqual({ $ref: "#/$defs/FlowMap" });
    expect(properties("Manifest").virtual_timelines?.items).toEqual({
      $ref: "#/$defs/VirtualTimeline",
    });
    expect((defs.FlowMap as Node).required).toEqual(["id", "timeline", "chunks"]);
    expect(properties("FlowMap").convention).not.toHaveProperty("enum");
    expect((defs.VirtualTimeline as Node).required).toEqual([
      "id",
      "map",
      "timeline",
      "unit",
      "number_type",
      "length",
    ]);
    for (const keyword of ["if", "then", "else"]) {
      expect((defs.VirtualTimeline as Node)[keyword], keyword).toEqual(
        (defs.Timeline as Node)[keyword],
      );
    }
  });

  it("names every word of the open vocabularies and the class of an atomic section", () => {
    const words = String(properties("FlowControlElement").manifestation?.description);
    for (const role of ["jump_target", "break", "barline"]) {
      for (const word of MANIFESTATIONS[role] ?? []) expect(words, word).toContain(`\`${word}\``);
    }
    expect(MANIFESTATIONS.section_break).toEqual([]);
    const destination = String(properties("JumpDestination").manifestation?.description);
    for (const word of MANIFESTATIONS.destination ?? []) {
      expect(destination, word).toContain(`\`${word}\``);
    }
    expect(CONVENTIONS).toEqual(["default", "single", "printed"]);
    const convention = String(properties("FlowMap").convention?.description);
    for (const word of CONVENTIONS) expect(convention, word).toContain(`\`${word}\``);
    expect(ATOMIC_SECTION).toBe(`${NAMESPACE}AtomicSection`);
    expect(String((defs.Region as Node).description)).toContain(`\`${ATOMIC_SECTION}\``);
    expect(EARLIER_ROLES).toEqual(["jump_from", "jump_to", "flow_marker"]);
  });
});

describe("the earlier form of flow control", () => {
  it.each([
    [{ type: "jump_from", manifestation: "da_capo" }],
    [{ type: "jump_to", manifestation: "segno" }],
    [{ type: "flow_marker", manifestation: "fine" }],
    [{ role: "flow_marker", manifestation: "fine" }],
    [{ manifestation: "dal_segno", target: "s" }],
    [{ role: "jump", type: "jump_from", targets: [{}] }],
  ])("is refused with the converter named: %o", (earlier) => {
    const child = timeline("c", "quarters", [8, 1], {
      offset: [0, 1],
      flow_control: [element("ok", "barline", 1), { id: "old", coordinate: [2, 1], ...earlier }],
    });
    const value = manifest([timeline("score", "quarters", [8, 1], { children: [child] })]);
    expect(refusal(() => validate(value))).toEqual([
      "flow_control_form",
      ["timelines", 0, "children", 0, "flow_control", 1],
      `flow-control element 'old' is written in the earlier form of flow control (type, target): convert the manifest with ${CONVERTER}`,
    ]);
    expect(existsSync(resolve(repositoryRoot, CONVERTER))).toBe(true);
  });

  it("is reported before the schema, an element without an ID by its pointer", () => {
    const value = manifest([
      timeline("score", "furlongs", [8, 1], { flow_control: [{ type: "jump_to" }] }),
    ]);
    expect(refusal(() => timetoshare.validate(value))).toEqual([
      "flow_control_form",
      ["timelines", 0, "flow_control", 0],
      `the flow-control element at #/timelines/0/flow_control/0 is written in the earlier form of flow control (type, target): convert the manifest with ${CONVERTER}`,
    ]);
  });

  it("leaves a type beside a role an unknown key", () => {
    const value = score([element("b", "barline", 1, { type: "thin" })]);
    validate(value);
    expect(unknownKeys(value)).toEqual([
      { path: ["timelines", 0, "flow_control", 0], key: "type" },
    ]);
  });
});

describe("rejected elements", () => {
  it("are rejected by a belief false", () => {
    expect(rejected({})).toBe(false);
    expect(rejected({ provenance: [{ method: "imported" }] })).toBe(false);
    const unlikely = { beliefs: [{ actor: EDITOR, belief: "unlikely", date: "x" }] };
    expect(rejected({ provenance: [unlikely] })).toBe(false);
    expect(rejected({ provenance: [{ method: "imported" }, FALSE] })).toBe(true);
  });

  it("share a coordinate with their replacement", () => {
    const old = jump("old", 8, [{ repeat_count: 1 }], { provenance: [FALSE] });
    const flow = [
      element("start", "jump_target", 2),
      old,
      jump("new", 8, [{ to: "start", repeat_count: 1 }]),
    ];
    expect(problems(score(flow))).toEqual([]);
    flow[1] = jump("old", 8, [{ repeat_count: 1 }]);
    expect(problems(score(flow))).toEqual([
      [
        "jump_repeated",
        ["timelines", 0, "flow_control", 2],
        "'new' is a second jump at coordinate [8, 1] of 'score', after 'old': several signs at one place are destinations of one jump",
      ],
    ]);
  });

  it("are neither checked nor named", () => {
    const flow = [
      element("gone", "jump_target", 2, { provenance: [FALSE] }),
      jump("wild", 99, [{ to: "nowhere" }, { to: "nowhere" }], { provenance: [FALSE] }),
      jump("j", 4, [{ to: "gone" }]),
      element("fine", "break", 6, { ends: { after: { jump: "wild" } } }),
    ];
    expect(problems(score(flow))).toEqual([
      [
        "dangling_target",
        ["timelines", 0, "flow_control", 2, "targets", 0, "to"],
        "'gone' names no jump target, region or child of this timeline, nor the timeline itself",
      ],
      [
        "dangling_target",
        ["timelines", 0, "flow_control", 3, "ends", "after", "jump"],
        "'wild' names no jump of this timeline",
      ],
    ]);
  });
});

describe("coordinates and places", () => {
  it("are bounded at zero only on a timeline of unknown length", () => {
    const flow = [jump("far", 1000, [{ by: [500, 1] }]), jump("back", 4, [{ by: [-5, 1] }])];
    const value = manifest([timeline("score", "quarters", null, { flow_control: flow })]);
    expect(problems(value)).toEqual([
      [
        "flow_coordinate",
        ["timelines", 0, "flow_control", 1, "targets", 0, "by"],
        "by [-5, 1] from coordinate [4, 1] of 'back' is not on 'score': it lies before 0",
      ],
    ]);
  });

  it("include the ends of the axis", () => {
    const flow = [jump("first", 0, [{ by: [8, 1] }]), jump("last", 8, [{ by: [-8, 1] }])];
    expect(problems(score(flow))).toEqual([]);
  });

  it("add as doubles on a float axis", () => {
    expect(0.1 + 0.2).toBeGreaterThan(0.3);
    const flow = [{ id: "j", role: "jump", coordinate: 0.1, targets: [{ by: 0.2 }] }];
    const take = (length: number) =>
      manifest([timeline("take", "seconds", length, { flow_control: flow })]);
    expect(problems(take(0.30000000000000004))).toEqual([]);
    expect(problems(take(0.3))).toEqual([
      [
        "flow_coordinate",
        ["timelines", 0, "flow_control", 0, "targets", 0, "by"],
        "by 0.2 from coordinate 0.1 of 'j' is not on 'take': it lies outside 0 to the length 0.3",
      ],
    ]);
  });

  it("tell a distance from an element at one coordinate", () => {
    const flow = [
      element("there", "jump_target", 2),
      jump("j", 4, [
        { to: "there", passes: [1] },
        { by: [-2, 1], passes: [2] },
      ]),
    ];
    expect(problems(score(flow))).toEqual([]);
  });
});

describe("an after", () => {
  const afterOf = (reference: JsonObject, targets: JsonObject[]) =>
    problems(
      score([
        element("there", "jump_target", 1),
        jump("leap", 6, targets),
        element("fine", "break", 4, { ends: { after: reference } }),
      ]),
    );
  const there = { to: "there" };
  const back = { by: [-2, 1] };
  const bare = { repeat_count: 1 };
  const at = ["timelines", 0, "flow_control", 2, "ends", "after"];

  it("names one destination by its place", () => {
    expect(afterOf({ jump: "leap" }, [there])).toEqual([]);
    expect(afterOf({ jump: "leap" }, [there, bare])).toEqual([]);
    expect(afterOf({ jump: "leap", to: "there" }, [there, back, bare])).toEqual([]);
    expect(afterOf({ jump: "leap", by: [-4, 2] }, [there, back, bare])).toEqual([]);
    expect(afterOf({ jump: "leap" }, [there, back])).toEqual([
      [
        "dangling_target",
        at,
        "jump 'leap' has 2 destinations and none without a place; after names one by its to or by",
      ],
    ]);
    expect(afterOf({ jump: "leap", by: [-3, 1] }, [there, back])).toEqual([
      ["dangling_target", [...at, "by"], "jump 'leap' has no destination by [-3, 1]"],
    ]);
    expect(afterOf({ jump: "leap", to: "score" }, [there, back])).toEqual([
      ["dangling_target", [...at, "to"], "jump 'leap' has no destination to 'score'"],
    ]);
  });

  it("stays within its timeline", () => {
    const child = timeline("c", "quarters", [8, 1], {
      offset: [0, 1],
      flow_control: [jump("inner", 2, [{ repeat_count: 1 }])],
    });
    const fine = element("fine", "break", 4, { ends: { after: { jump: "inner" } } });
    expect(problems(score([fine], { children: [child] }))).toEqual([
      [
        "dangling_target",
        ["timelines", 0, "flow_control", 0, "ends", "after", "jump"],
        "'inner' names no jump of this timeline",
      ],
    ]);
  });
});

describe("FlowMaps and virtual timelines", () => {
  const mapped = (members: JsonObject): JsonObject =>
    manifest(
      [
        timeline("score", "quarters", [8, 1], {
          regions: [{ id: "intro", start: [0, 1], end: [2, 1] }],
          children: [
            timeline("verse", "quarters", [4, 1], {
              offset: [2, 1],
              regions: [{ id: "line", start: [0, 1], end: [1, 1] }],
            }),
          ],
        }),
        timeline("sketch", "quarters", [8, 1], {
          regions: [{ id: "idea", start: [0, 1], end: [1, 1] }],
        }),
      ],
      members,
    );
  const virtual = (id: string, map: string, line: string): JsonObject => ({
    id,
    map,
    timeline: line,
    unit: "quarters",
    number_type: "fraction",
    length: [2, 1],
  });
  const noChunk = (name: string) =>
    `'${name}' names no region, child timeline or virtual timeline in the tree of 'score'`;

  it("take as a chunk anything giving an interval inside the root's tree", () => {
    const virtuals = [
      virtual("v1", "f", "verse"),
      virtual("v2", "f", "v1"),
      virtual("v3", "g", "sketch"),
    ];
    const second = { id: "g", timeline: "sketch", chunks: ["idea", "v3"] };
    const good = { id: "f", timeline: "score", chunks: ["intro", "verse", "line", "v2"] };
    expect(problems(mapped({ flow_maps: [good, second], virtual_timelines: virtuals }))).toEqual(
      [],
    );
    const chunks = ["v3", "idea", "sketch", "score", "f", "nowhere"];
    const bad = { id: "f", timeline: "score", chunks };
    expect(problems(mapped({ flow_maps: [bad, second], virtual_timelines: virtuals }))).toEqual(
      chunks.map((name, index) => [
        "flow_map_chunk",
        ["flow_maps", 0, "chunks", index],
        noChunk(name),
      ]),
    );
  });

  it("resolve virtual timelines naming each other to no tree", () => {
    const value = mapped({
      flow_maps: [{ id: "f", timeline: "score", chunks: ["a"] }],
      virtual_timelines: [virtual("a", "f", "b"), virtual("b", "f", "a")],
    });
    expect(problems(value)).toEqual([
      ["flow_map_chunk", ["flow_maps", 0, "chunks", 0], noChunk("a")],
    ]);
  });

  it("apply a FlowMap or a conversion map, a held one included", () => {
    const linear = {
      type: "LinearMap",
      id: "tempo",
      source_unit: "quarters",
      target_unit: "seconds",
    };
    const chain = { ...linear, type: "ChainMap", id: "chain", maps: [linear] };
    const value = mapped({ virtual_timelines: [virtual("v", "tempo", "score")] });
    const [root] = value.timelines as [JsonObject];
    const [verse] = root.children as [JsonObject];
    verse.conversion_maps = [chain];
    expect(problems(value)).toEqual([]);
    (value.virtual_timelines as JsonObject[])[0] = virtual("v", "intro", "score");
    expect(problems(value)).toEqual([
      [
        "dangling_target",
        ["virtual_timelines", 0, "map"],
        "'intro' names no FlowMap or conversion map of this manifest",
      ],
    ]);
  });

  it("allow one canonical FlowMap per timeline", () => {
    const flowMaps = (third: boolean) => [
      { id: "a", timeline: "score", chunks: [], canonical: true },
      { id: "b", timeline: "sketch", chunks: [], canonical: true },
      { id: "c", timeline: "score", chunks: [], canonical: third },
    ];
    expect(problems(mapped({ flow_maps: flowMaps(false) }))).toEqual([]);
    expect(problems(mapped({ flow_maps: flowMaps(true) }))).toEqual([
      [
        "flow_map_canonical",
        ["flow_maps", 2, "canonical"],
        "'c' is a second canonical FlowMap of 'score', after 'a'",
      ],
    ]);
  });

  it("count their IDs among the manifest's", () => {
    const value = mapped({
      flow_maps: [{ id: "intro", timeline: "score", chunks: [] }],
      virtual_timelines: [virtual("score", "intro", "score")],
      id: "score",
    });
    expect(problems(value).map(([code, path]) => [code, path])).toEqual([
      ["duplicate_id", ["flow_maps", 0, "id"]],
      ["duplicate_id", ["virtual_timelines", 0, "id"]],
      ["manifest_id", ["id"]],
      ["dangling_target", ["virtual_timelines", 0, "timeline"]],
    ]);
  });

  it("are ordered by ID, chunks kept, gaps and lengths respelled", () => {
    const value = mapped({
      flow_maps: [
        { id: "z", timeline: "score", chunks: ["verse", { gap: [4, 2] }, "intro"] },
        { id: "a", timeline: "sketch", chunks: ["idea", "idea"] },
      ],
      virtual_timelines: [
        { ...virtual("w", "z", "score"), length: [new JsonFloat(16), 2] },
        virtual("v", "a", "sketch"),
      ],
    });
    const result = canonicalOrder(value);
    const flowMaps = result.flow_maps as JsonObject[];
    const virtuals = result.virtual_timelines as JsonObject[];
    expect(flowMaps.map((entry) => entry.id)).toEqual(["a", "z"]);
    expect(flowMaps[1]?.chunks).toEqual(["verse", { gap: [2, 1] }, "intro"]);
    expect(virtuals.map((entry) => entry.id)).toEqual(["v", "w"]);
    expect(virtuals[1]?.length).toEqual([8, 1]);
    const completed = complete(value) as JsonObject;
    const [first] = completed.flow_maps as [JsonObject];
    expect((first.chunks as unknown[])[1]).toEqual({ gap: [2, 1] });
  });
});

describe("the flow warnings", () => {
  it("know every word of the vocabularies", () => {
    const flow: JsonObject[] = [];
    for (const role of ["jump_target", "break", "barline"]) {
      for (const word of MANIFESTATIONS[role] ?? []) {
        flow.push(element(`${role}-${word}`, role, 1, { manifestation: word }));
      }
    }
    flow.push(element("plain", "section_break", 1));
    flow.push(
      jump("j", 2, [
        ...(MANIFESTATIONS.jump_target ?? []).map((word) => ({ to: `jump_target-${word}` })),
        ...(MANIFESTATIONS.destination ?? []).map((word, number) => ({
          by: [number, 1],
          manifestation: word,
        })),
      ]),
    );
    const root = timeline("score", "quarters", [16, 1], { flow_control: flow });
    const value = withContext(manifest([root]), {});
    value.flow_maps = [
      ...CONVENTIONS.map((word) => ({ id: word, timeline: "score", chunks: [], convention: word })),
      { id: "hand", timeline: "score", chunks: [] },
    ];
    validate(value);
    expect(manifestWarnings(value)).toEqual([]);
  });

  it("report a word of another role, sorted by path, then code", () => {
    const child = timeline("c", "quarters", [8, 1], {
      offset: [0, 1],
      flow_control: [element("x", "barline", 1, { manifestation: "fine" })],
    });
    const value = score(
      [
        element("y", "break", 1, { manifestation: "segno" }),
        jump("d", 4, [{ manifestation: "segno" }]),
      ],
      { children: [child] },
    );
    value.flow_maps = [{ id: "f", timeline: "score", chunks: [], convention: "mine" }];
    expect(manifestWarnings(value)).toEqual([
      { code: "context_absent", path: [], message: "the manifest has no @context" },
      {
        code: "convention_unknown",
        path: ["flow_maps", 0, "convention"],
        message: "'mine' is no convention the format defines",
      },
      {
        code: "manifestation_unknown",
        path: ["timelines", 0, "children", 0, "flow_control", 0, "manifestation"],
        message: "'fine' is no manifestation the format defines for a barline",
      },
      {
        code: "manifestation_unknown",
        path: ["timelines", 0, "flow_control", 0, "manifestation"],
        message: "'segno' is no manifestation the format defines for a break",
      },
      {
        code: "manifestation_unknown",
        path: ["timelines", 0, "flow_control", 1, "targets", 0, "manifestation"],
        message: "'segno' is no manifestation the format defines for a destination",
      },
    ]);
  });
});

describe("the provenance of an element", () => {
  const withProvenance = (entry: JsonObject): JsonObject => {
    const value = withContext(manifest([timeline("score")]), {});
    ((value.timelines as JsonObject[])[0] as JsonObject).flow_control = [
      element("b", "barline", 1, { provenance: [{ method: "imported" }, entry] }),
    ];
    value.flow_maps = [{ id: "f", timeline: "score", chunks: [], provenance: [entry] }];
    return value;
  };

  it.each([
    [
      { date: "2026-02-30" },
      "calendar_date",
      ["date"],
      "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD",
    ],
    [
      { stated_by: ["viaf:1"] },
      "iri",
      ["stated_by", 0],
      "'viaf:1': the prefix 'viaf' is not declared in @context",
    ],
    [
      { basis: ["#ghost"] },
      "dangling_target",
      ["basis", 0],
      "'#ghost' names no element of this manifest",
    ],
    [
      {
        beliefs: [
          { actor: EDITOR, belief: "true", date: "2026-11-25" },
          { actor: EDITOR, belief: "unlikely", date: "2026-11-25" },
        ],
      },
      "belief_actor",
      ["beliefs", 1, "actor"],
      `'${EDITOR}' already holds belief 0 of this entry; an actor holds one belief`,
    ],
  ] as const)("obeys the entry rules: %o", (entry, code, tail, message) => {
    const value = withProvenance(entry as unknown as JsonObject);
    const here = ["timelines", 0, "flow_control", 0, "provenance", 1, ...tail];
    expect(
      statementProblems(value).map((problem) => [problem.code, problem.path, problem.detail]),
    ).toEqual([
      [code, here, message],
      [code, ["flow_maps", 0, "provenance", 0, ...tail], message],
    ]);
    expect(refusal(() => validate(value)).slice(0, 2)).toEqual([code, here]);
  });

  it("names no pair, needs no context and counts among the used prefixes", () => {
    const plain = withProvenance({ method: "manual", stated_by: [EDITOR], basis: ["#score"] });
    delete plain["@context"];
    validate(plain);
    expect(manifestWarnings(plain).map((warning) => warning.code)).toEqual(["context_absent"]);
    const value = withProvenance({ stated_by: ["viaf:1"], method: "prov:Activity" });
    expect(usedPrefixes(value)).toEqual(["prov", "viaf"]);
    const namespaces = { viaf: "http://viaf.org/viaf/", prov: "http://www.w3.org/ns/prov#" };
    const kept = withContext(value, namespaces);
    expect((kept["@context"] as JsonObject).viaf).toBe(namespaces.viaf);
    expect((kept["@context"] as JsonObject).prov).toBe(namespaces.prov);
    validate(kept);
  });
});

describe("the expected flows", () => {
  const names = readdirSync(FLOWS)
    .filter((name) => name.endsWith(".yaml"))
    .map((name) => name.slice(0, -".yaml".length))
    .sort();
  const ZERO = rational(0n, 1n);
  const within = (start: Rational, value: Rational, end: Rational) =>
    compareRationals(start, value) <= 0 && compareRationals(value, end) <= 0;

  it("are stated, each beside its trace and its manifest", () => {
    expect(names).toEqual([
      "da_capo_al_fine",
      "dal_segno_al_coda",
      "loop",
      "ossia",
      "repairs",
      "repeat_end_and_dal_segno",
      "sections",
      "sonata_exposition",
      "volta_passes",
    ]);
    for (const name of names) {
      expect(existsSync(resolve(FLOWS, `${name}.md`)), name).toBe(true);
      fixtureText(`flow/${name}`);
    }
  });

  /** The boundaries of a timeline's atomic sections, as the schema states them. */
  function boundaries(root: JsonObject): Rational[] {
    const flow = ((root.flow_control ?? []) as JsonObject[]).filter((entry) => !rejected(entry));
    const starts = new Map<string, Rational>([[root.id as string, ZERO]]);
    for (const region of (root.regions ?? []) as JsonObject[]) {
      starts.set(region.id as string, exact(region.start));
    }
    for (const child of (root.children ?? []) as JsonObject[]) {
      starts.set(child.id as string, exact(child.offset));
    }
    for (const entry of flow) {
      if (entry.role === "jump_target") starts.set(entry.id as string, exact(entry.coordinate));
    }
    const sections = flow
      .filter((entry) => entry.role === "section_break")
      .map((entry) => exact(entry.coordinate));
    const found: Rational[] = [ZERO, exact(root.length)];
    const sum = (a: Rational, b: Rational) =>
      rational(
        a.numerator * b.denominator + b.numerator * a.denominator,
        a.denominator * b.denominator,
      );
    for (const entry of flow) {
      const at = exact(entry.coordinate);
      if (entry.role !== "barline") found.push(at);
      for (const destination of (entry.targets ?? []) as JsonObject[]) {
        if ("to" in destination) found.push(starts.get(destination.to as string) as Rational);
        else if (!("by" in destination)) {
          const before = sections.filter((section) => compareRationals(section, at) < 0);
          found.push(before.sort(compareRationals).at(-1) ?? ZERO);
        } else if (compareRationals(exact(destination.by), ZERO) !== 0) {
          found.push(sum(at, exact(destination.by)));
        }
      }
    }
    found.sort(compareRationals);
    return found.filter(
      (value, index) => index === 0 || compareRationals(value, found[index - 1] as Rational) !== 0,
    );
  }

  // Findings are stated for `default` only, and that is the rule of the form:
  // under `single` and `printed` a file states runs and sections and says
  // nothing of findings.
  it.each(names)("of %s agree with its manifest", (name) => {
    const text = readFileSync(resolve(FLOWS, `${name}.yaml`), "utf8");
    const flows = loads(text) as JsonObject;
    expect(dumps(flows)).toBe(text);
    expect(Object.keys(flows).sort()).toEqual([
      "atomic_sections",
      "conventions",
      "manifest",
      "timeline",
    ]);
    expect(flows.manifest).toBe(`flow/${name}`);
    const value = withBareIds(loads(fixtureText(flows.manifest as string))) as JsonObject;
    const root = (value.timelines as JsonObject[]).find(
      (entry) => entry.id === flows.timeline,
    ) as JsonObject;
    const bounds = boundaries(root);
    const sections = flows.atomic_sections as JsonObject[];
    expect(sections.map((section) => [exact(section.start), exact(section.end)])).toEqual(
      bounds.slice(0, -1).map((start, index) => [start, bounds[index + 1]]),
    );
    expect(sections.map((section) => section.name)).toEqual(
      sections.map((_, index) => String.fromCharCode(65 + index)),
    );
    const conventions = flows.conventions as Record<string, JsonObject>;
    expect(Object.keys(conventions).sort()).toEqual(["default", "printed", "single"]);
    expect(Object.keys(conventions.default as JsonObject).sort()).toEqual([
      "findings",
      "runs",
      "sections",
    ]);
    const onBound = (point: Rational) =>
      bounds.some((bound) => compareRationals(bound, point) === 0);
    for (const [convention, flow] of Object.entries(conventions)) {
      if (convention !== "default") expect(Object.keys(flow).sort()).toEqual(["runs", "sections"]);
      const covered: unknown[] = [];
      for (const [start, end] of flow.runs as [unknown, unknown][]) {
        const from = exact(start);
        const to = exact(end);
        expect(compareRationals(ZERO, from) <= 0 && compareRationals(from, to) < 0).toBe(true);
        expect(compareRationals(to, exact(root.length)) <= 0).toBe(true);
        expect(onBound(from) && onBound(to)).toBe(true);
        const inside = sections.filter(
          (section) =>
            within(from, exact(section.start), to) && within(from, exact(section.end), to),
        );
        expect(inside.length).toBeGreaterThan(0);
        covered.push(...inside.map((section) => section.name));
      }
      expect(covered, convention).toEqual(flow.sections);
    }
    expect(conventions.printed?.sections).toEqual(sections.map((section) => section.name));
    expect(conventions.printed?.runs).toEqual(
      sections.map((section) => [section.start, section.end]),
    );
    const played = new Set(conventions.default?.sections as unknown[]);
    const findings = conventions.default?.findings as JsonObject[];
    const kinds = [
      "flow_ends_at_break",
      "never_played",
      "endless_loop",
      "ambiguous_targets",
      "undetermined_target",
    ];
    for (const finding of findings) {
      expect(Object.keys(finding).sort()).toEqual(["coordinate", "kind"]);
      expect(kinds).toContain(finding.kind);
      expect(onBound(exact(finding.coordinate))).toBe(true);
    }
    expect(
      findings
        .filter((finding) => finding.kind === "never_played")
        .map((finding) => finding.coordinate),
    ).toEqual(
      sections.filter((section) => !played.has(section.name)).map((section) => section.start),
    );
  });

  it("of the sonata exposition are its FlowMaps and its virtual timeline", () => {
    const flows = loads(
      readFileSync(resolve(FLOWS, "sonata_exposition.yaml"), "utf8"),
    ) as JsonObject;
    const value = withBareIds(loads(fixtureText("flow/sonata_exposition"))) as JsonObject;
    const root = (value.timelines as JsonObject[])[0] as JsonObject;
    const regions = root.regions as JsonObject[];
    expect(regions.map((region) => [region.name, region.start, region.end])).toEqual(
      (flows.atomic_sections as JsonObject[]).map((s) => [s.name, s.start, s.end]),
    );
    for (const region of regions) {
      expect(region.statements).toEqual({ type: ["tts:AtomicSection"] });
      expect(region.provenance).toEqual([
        { method: "inferred", property: "rdf:type", value: { id: "tts:AtomicSection" } },
      ]);
    }
    expect((value["@context"] as JsonObject).tts).toBe(NAMESPACE);
    expect(timetoshare.expandIri(value["@context"], "tts:AtomicSection")).toBe(ATOMIC_SECTION);
    const byName = new Map(regions.map((region) => [region.name, region.id]));
    const flowMaps = value.flow_maps as JsonObject[];
    for (const [convention, flow] of Object.entries(
      flows.conventions as Record<string, JsonObject>,
    )) {
      const flowMap = flowMaps.find((entry) => entry.convention === convention) as JsonObject;
      expect(flowMap.chunks, convention).toEqual(
        (flow.sections as string[]).map((section) => byName.get(section)),
      );
      expect(flowMap.timeline).toBe("score");
    }
    const [virtual] = value.virtual_timelines as [JsonObject];
    expect(virtual.map).toBe(flowMaps.find((entry) => entry.convention === "default")?.id);
    expect([virtual.length, virtual.unit, virtual.number_type]).toEqual([
      [36, 1],
      "quarters",
      "fraction",
    ]);
  });
});
