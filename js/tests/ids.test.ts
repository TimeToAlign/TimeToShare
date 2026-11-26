import { describe, expect, it } from "vitest";
import { CONTAINERS, definitionsOf, ID_POSITIONS, MEASURE_VIEWS } from "../src/ids.js";
import {
  CHUNK_SENTINEL,
  compactJson,
  FileIdError,
  FORMAT_CONTEXT,
  fromFileId,
  isJsonObject,
  JsonFloat,
  loads,
  NOMATCH_SENTINEL,
  SchemaValidationError,
  schema,
  statementProblems,
  toFileId,
  validate,
  withBareIds,
  withFileIds,
} from "../src/index.js";
import type { JsonObject } from "../src/json/value.js";
import { fixtureFiles, fixtureText } from "./fixtures.js";

/** A bare manifest naming an ID at every position of the table, once each (as in Python). */
const EVERY_POSITION = `
timetoshare: 0.2.0
id: op35
timelines:
- id: score
  unit: quarters
  length: [8, 1]
  extra: score
  children:
  - {id: verse, unit: quarters, length: 2.0}
  conversion_maps:
  - type: ChainMap
    id: chain
    maps:
    - {type: LinearMap, id: inner, scalar: 2.0}
    - {type: MeasureRecordMap, id: view, measure_map: mm}
  - type: CombinationMap
    id: combined
    maps:
      out: {type: ConstantMap, id: constant}
  regions:
  - id: intro
    statements:
      dcterms:source: [{id: "#verse"}]
  flow_control:
  - {id: jump_target_1, role: jump_target}
  - id: jump_1
    role: jump
    targets:
    - {to: jump_target_1}
    - by: [0, 1]
      after: {jump: jump_2, to: intro}
  - {id: jump_2, role: jump, targets: [{to: intro}]}
  - id: break_1
    role: break
    ends:
      after: {jump: jump_1, to: jump_target_1}
flow_maps:
- id: flow_map_1
  timeline: score
  chunks: [intro, {gap: [1, 1]}, verse, virtual_1]
virtual_timelines:
- {id: virtual_1, map: flow_map_1, timeline: score, through: g}
groups:
- {id: g, members: [score]}
measure_maps:
- {id: mm, rows: []}
graphical:
  order:
    score: [line, children]
    g: [score]
  rules:
  - select:
      addresses: [{id: verse, part: [name]}]
      within: score
    set: {stroke: red}
  timestamps:
  - {id: timestamp_1, timeline: verse, coordinate: 1}
  elisions:
  - {id: elision_1, timeline: verse, start: 0, end: 1}
meta: {id: untouched}
`;

const IN_FILE_FORM = `
timetoshare: 0.2.0
id: "#op35"
timelines:
- id: "#score"
  unit: quarters
  length: [8, 1]
  extra: score
  children:
  - {id: "#verse", unit: quarters, length: 2.0}
  conversion_maps:
  - type: ChainMap
    id: "#chain"
    maps:
    - {type: LinearMap, id: "#inner", scalar: 2.0}
    - {type: MeasureRecordMap, id: "#view", measure_map: "#mm"}
  - type: CombinationMap
    id: "#combined"
    maps:
      out: {type: ConstantMap, id: "#constant"}
  regions:
  - id: "#intro"
    statements:
      dcterms:source: [{id: "#verse"}]
  flow_control:
  - {id: "#jump_target_1", role: jump_target}
  - id: "#jump_1"
    role: jump
    targets:
    - {to: "#jump_target_1"}
    - by: [0, 1]
      after: {jump: "#jump_2", to: "#intro"}
  - {id: "#jump_2", role: jump, targets: [{to: "#intro"}]}
  - id: "#break_1"
    role: break
    ends:
      after: {jump: "#jump_1", to: "#jump_target_1"}
flow_maps:
- id: "#flow_map_1"
  timeline: "#score"
  chunks: ["#intro", {gap: [1, 1]}, "#verse", "#virtual_1"]
virtual_timelines:
- {id: "#virtual_1", map: "#flow_map_1", timeline: "#score", through: "#g"}
groups:
- {id: "#g", members: ["#score"]}
measure_maps:
- {id: "#mm", rows: []}
graphical:
  order:
    "#score": [line, children]
    "#g": ["#score"]
  rules:
  - select:
      addresses: [{id: "#verse", part: [name]}]
      within: "#score"
    set: {stroke: red}
  timestamps:
  - {id: "#timestamp_1", timeline: "#verse", coordinate: 1}
  elisions:
  - {id: "#elision_1", timeline: "#verse", start: 0, end: 1}
meta: {id: untouched}
`;

const bare = (): JsonObject => loads(EVERY_POSITION) as JsonObject;
const filed = (): JsonObject => loads(IN_FILE_FORM) as JsonObject;

/** Walk a path of keys and indices into a value. */
function at(value: unknown, ...path: (string | number)[]): unknown {
  let cursor = value;
  for (const segment of path) {
    cursor = (cursor as Record<string | number, unknown>)[segment];
  }
  return cursor;
}

describe("the sentinels of a MatchClaim table", () => {
  it("are the reserved strings the Python package names", () => {
    expect(NOMATCH_SENTINEL).toBe("NOMATCH_SENTINEL");
    expect(CHUNK_SENTINEL).toBe("CHUNK_SENTINEL");
  });
});

describe("one ID", () => {
  it("gains one #", () => {
    expect(toFileId("clt_1")).toBe("#clt_1");
    expect(toFileId("#x")).toBe("##x");
  });

  it("loses exactly one #", () => {
    expect(fromFileId("#clt_1")).toBe("clt_1");
    expect(fromFileId("##x")).toBe("#x");
    expect(fromFileId("# x")).toBe(" x");
  });

  it.each([
    ["clt_1", "'clt_1' is not written as an ID: it does not start with '#'"],
    ["", "'' is not written as an ID: it does not start with '#'"],
    ["#", "'#' is not written as an ID: nothing follows the '#'"],
  ])("refuses %j", (text, message) => {
    let thrown: unknown;
    try {
      fromFileId(text);
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toBeInstanceOf(RangeError);
    expect(thrown).toBeInstanceOf(FileIdError);
    expect((thrown as FileIdError).message).toBe(message);
    expect((thrown as FileIdError).path).toEqual([]);
  });
});

describe("a whole manifest", () => {
  it("converts every position and nothing else", () => {
    expect(compactJson(withFileIds(bare()))).toBe(compactJson(filed()));
    expect(compactJson(withBareIds(filed()))).toBe(compactJson(bare()));
  });

  it("keeps the order of keys, an order key renamed in place included", () => {
    const converted = withFileIds(bare());
    expect(Object.keys(converted)).toEqual(Object.keys(bare()));
    expect(Object.keys(at(converted, "graphical", "order") as object)).toEqual(["#score", "#g"]);
    const back = withBareIds(converted);
    expect(Object.keys(at(back, "graphical", "order") as object)).toEqual(["score", "g"]);
  });

  it("keeps an order key that reads as an array index in its place", () => {
    const value = loads(
      'timetoshare: 0.2.0\ntimelines: []\ngraphical:\n  order:\n    "#b": [line]\n    "#2": [line]\n',
    );
    const back = withBareIds(value);
    expect(compactJson(back)).toBe(
      '{"timetoshare":"0.2.0","timelines":[],"graphical":{"order":{"b":["line"],"2":["line"]}}}',
    );
    expect(compactJson(withFileIds(back))).toBe(compactJson(value));
  });

  it("keeps every number as read", () => {
    const converted = withFileIds(bare());
    expect(at(converted, "timelines", 0, "children", 0, "length")).toEqual(new JsonFloat(2));
    expect(at(converted, "timelines", 0, "conversion_maps", 0, "maps", 0, "scalar")).toBeInstanceOf(
      JsonFloat,
    );
    expect(at(converted, "graphical", "timestamps", 0, "coordinate")).toBe(1);
  });

  it("is pure", () => {
    const original = bare();
    const converted = withFileIds(original);
    (at(converted, "timelines", 0, "length") as unknown[]).push(0);
    (at(converted, "meta") as JsonObject).id = "changed";
    expect(compactJson(original)).toBe(compactJson(bare()));
    const file = filed();
    withBareIds(file);
    expect(compactJson(file)).toBe(compactJson(filed()));
  });

  it("leaves band words and the IRIs of statements as written", () => {
    const value = withBareIds(filed());
    expect(at(value, "graphical", "order", "score")).toEqual(["line", "children"]);
    const reference = ["timelines", 0, "regions", 0, "statements", "dcterms:source", 0, "id"];
    expect(at(value, ...reference)).toBe("#verse");
    expect(at(withFileIds(bare()), ...reference)).toBe("#verse");
  });

  it.each([
    [
      (m: JsonObject) => {
        (at(m, "timelines", 0) as JsonObject).id = "score";
      },
      ["timelines", 0, "id"],
      "'score' is not written as an ID: it does not start with '#'",
    ],
    [
      (m: JsonObject) => {
        (at(m, "groups", 0, "members") as unknown[])[0] = "score";
      },
      ["groups", 0, "members", 0],
      "'score' is not written as an ID: it does not start with '#'",
    ],
    [
      (m: JsonObject) => {
        (at(m, "graphical", "order") as JsonObject)["#g"] = ["score"];
      },
      ["graphical", "order", "#g", 0],
      "'score' is not written as an ID: it does not start with '#'",
    ],
    [
      (m: JsonObject) => {
        (at(m, "graphical", "timestamps", 0) as JsonObject).timeline = "#";
      },
      ["graphical", "timestamps", 0, "timeline"],
      "'#' is not written as an ID: nothing follows the '#'",
    ],
  ])("refuses a bare ID in a file where it stands (%#)", (change, path, message) => {
    const value = filed();
    change(value);
    let thrown: unknown;
    try {
      withBareIds(value);
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toBeInstanceOf(FileIdError);
    expect((thrown as FileIdError).path).toEqual(path);
    expect((thrown as FileIdError).message).toBe(message);
  });

  it("returns a value that is no manifest as a copy", () => {
    expect(withFileIds([1])).toEqual([1]);
    expect(isJsonObject(withBareIds({}))).toBe(true);
  });
});

const ID = "#/$defs/Id";
const HOW: Record<string, string> = {
  id: "value",
  ids: "items",
  order: "propertyNames",
};

type Node = Record<string, unknown>;
const definitions = (schema as unknown as { $defs: Record<string, Node> }).$defs;
const nameOf = (reference: unknown) => String(reference).slice("#/$defs/".length);
const refOf = (node: unknown) => (isJsonObject(node) ? node.$ref : undefined);

/**
 * Where the schema types a value as `$defs/Id`, and how. The items of a list
 * count where each is an ID or one of several shapes of which one is an ID,
 * as a FlowMap's chunks are an ID or a gap.
 */
function schemaIdPositions(): string[] {
  const found: string[] = [];
  for (const [definition, node] of Object.entries(definitions)) {
    for (const [member, declared] of Object.entries((node.properties ?? {}) as Node)) {
      const at = declared as Node;
      if (at.$ref === ID) found.push(`${definition}.${member}.value`);
      const choices = isJsonObject(at.items) ? ((at.items.oneOf ?? []) as Node[]) : [];
      if (refOf(at.items) === ID || choices.some((choice) => choice.$ref === ID)) {
        found.push(`${definition}.${member}.items`);
      }
      if (refOf(at.propertyNames) === ID) found.push(`${definition}.${member}.propertyNames`);
      if (((at.anyOf ?? []) as Node[]).some((branch) => branch.$ref === ID)) {
        found.push(`${definition}.${member}.anyOf`);
      }
    }
  }
  return found.sort();
}

/** The definitions a member refers to, and how it holds them. */
function held(declared: Node): [string, string][] {
  const found: [string, string][] = [];
  if (declared.$ref !== undefined) found.push(["one", nameOf(declared.$ref)]);
  for (const entry of (declared.oneOf ?? []) as Node[]) {
    if (entry.$ref !== undefined) found.push(["one", nameOf(entry.$ref)]);
  }
  if (refOf(declared.items) !== undefined) found.push(["list", nameOf(refOf(declared.items))]);
  if (refOf(declared.additionalProperties) !== undefined) {
    found.push(["values", nameOf(refOf(declared.additionalProperties))]);
  }
  return found;
}

/** The definitions that hold an ID position or hold one that does. */
function reaching(): Set<string> {
  const found = new Set(schemaIdPositions().map((position) => position.split(".")[0] as string));
  let changed = true;
  while (changed) {
    changed = false;
    for (const [definition, node] of Object.entries(definitions)) {
      if (found.has(definition)) continue;
      const refers = [
        ...((node.allOf ?? []) as Node[]).map((entry) => nameOf(entry.$ref)),
        ...((node.oneOf ?? []) as Node[]).filter((e) => e.$ref).map((e) => nameOf(e.$ref)),
        ...Object.values((node.properties ?? {}) as Node).flatMap((declared) =>
          held(declared as Node).map(([, child]) => child),
        ),
      ];
      if (refers.some((name) => found.has(name))) {
        found.add(definition);
        changed = true;
      }
    }
  }
  return found;
}

describe("the tables", () => {
  it("are the schema's ID positions", () => {
    const table = ID_POSITIONS.map(([d, m, shape]) => `${d}.${m}.${HOW[shape]}`).sort();
    expect(table).toEqual(schemaIdPositions());
  });

  it("are the schema's containers", () => {
    const reach = reaching();
    reach.delete("Id");
    const expected: string[] = [];
    for (const [definition, node] of Object.entries(definitions)) {
      for (const [member, declared] of Object.entries((node.properties ?? {}) as Node)) {
        for (const [holding, child] of held(declared as Node)) {
          if (reach.has(child)) expected.push(`${definition}.${member}.${holding}.${child}`);
        }
      }
    }
    expect(CONTAINERS.map((row) => row.join(".")).sort()).toEqual(expected.sort());
  });

  it("give a conversion map its type's definitions", () => {
    const views = Object.entries(definitions)
      .filter(([, node]) => {
        const bases = (node.allOf ?? []) as Node[];
        return bases.length === 1 && bases[0]?.$ref === "#/$defs/MeasureView";
      })
      .map(([name]) => name);
    expect([...MEASURE_VIEWS].sort()).toEqual(views.sort());
    for (const branch of (definitions.ConversionMap as Node).oneOf as Node[]) {
      const name = nameOf(branch.$ref);
      const bases: string[] = [];
      let current = name;
      while (current !== "MapBase") {
        current = nameOf(((definitions[current] as Node).allOf as Node[])[0]?.$ref);
        bases.push(current);
      }
      expect(definitionsOf("ConversionMap", { type: name })).toEqual([name, ...bases]);
    }
  });
});

describe("every fixture", () => {
  it.each(fixtureFiles())("%s round-trips", (file) => {
    const value = loads(fixtureText(file));
    expect(compactJson(withFileIds(withBareIds(value)))).toBe(compactJson(value));
  });
});

describe("the validators", () => {
  const small = (orderValue: string): JsonObject => ({
    timetoshare: "0.2.0",
    timelines: [{ id: "#score", unit: "quarters", length: [8, 1] }],
    groups: [{ id: "#g", members: ["#score"] }],
    graphical: {
      order: {
        "#g": [orderValue],
        "#score": ["line", "markers", "conversion_maps", "children", "regions", "flow_control"],
      },
    },
  });

  it("accept a manifest in the file form", () => {
    validate(small("#score"));
  });

  it("refuse a bare member ID in a group's order, where the schema cannot type it", () => {
    let thrown: unknown;
    try {
      validate(small("score"));
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toBeInstanceOf(SchemaValidationError);
    const { code, path, detail } = thrown as SchemaValidationError;
    expect([code, path, detail]).toEqual([
      "schema",
      ["graphical", "order", "#g", 0],
      "'score' is not written as an ID: it does not start with '#'",
    ]);
  });

  it("read IDs outside the statements as they stand in the statement check", () => {
    expect(statementProblems(small("score"))).toEqual([]);
  });

  it("resolve an element named by a statement against the bare IDs", () => {
    const value = small("#score");
    value["@context"] = { ...FORMAT_CONTEXT, dcterms: "http://purl.org/dc/terms/" };
    (value.timelines as JsonObject[])[0] = {
      id: "#score",
      unit: "quarters",
      length: [8, 1],
      statements: { "dcterms:source": [{ id: "#g" }] },
    };
    validate(value);
    expect(statementProblems(value)).toEqual([]);
  });

  it.each(["s", "score", "#"])("refuse the bare ID %j by the # rule", (written) => {
    const value = small("#score");
    (value.timelines as JsonObject[])[0] = { id: written, unit: "quarters", length: [8, 1] };
    let thrown: unknown;
    try {
      validate(value);
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toBeInstanceOf(SchemaValidationError);
    const { code, path, detail } = thrown as SchemaValidationError;
    expect([code, path, detail]).toEqual([
      "schema",
      ["timelines", 0, "id"],
      `'${written}' does not match '^#[\\\\s\\\\S]'`,
    ]);
  });

  it("accept any character after the # as an ID", () => {
    const value = small("#score");
    (value.timelines as JsonObject[])[0] = { id: "#\u2028", unit: "quarters", length: [8, 1] };
    value.groups = [{ id: "#g", members: ["#\u2028"] }];
    value.graphical = {
      order: {
        "#g": ["#\u2028"],
        "#\u2028": ["line", "markers", "conversion_maps", "children", "regions", "flow_control"],
      },
    };
    validate(value);
  });
});

describe("MatchStamps and resources", () => {
  it("hold IDs, while the MatchClaims a MatchStamp lists do not", () => {
    const value = {
      timetoshare: "0.2.0",
      timelines: [],
      graphical: {
        timestamps: [{ id: "#ts_a", timeline: "#score", coordinate: 0, matchstamp: true }],
        matchstamps: [
          {
            id: "#matchstamp_1",
            name: "M",
            alignment_anchors: [{ id: "#anchor_1", timestamps: ["#ts_a", "#ts_b"] }],
            match_claims: ["claim_1", "#claim_2"],
          },
        ],
      },
      resources: [
        {
          id: "#resource_1",
          type: "MatchClaim",
          timelines: ["#score", "#perf"],
          url: "#fragment.parquet",
        },
      ],
    };
    const bare = withBareIds(value) as typeof value;
    expect(bare.graphical.matchstamps).toEqual([
      {
        id: "matchstamp_1",
        name: "M",
        alignment_anchors: [{ id: "anchor_1", timestamps: ["ts_a", "ts_b"] }],
        match_claims: ["claim_1", "#claim_2"],
      },
    ]);
    expect(bare.resources).toEqual([
      {
        id: "resource_1",
        type: "MatchClaim",
        timelines: ["score", "perf"],
        url: "#fragment.parquet",
      },
    ]);
    expect(withFileIds(bare)).toEqual(value);
  });
});
