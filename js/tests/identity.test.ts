import { describe, expect, it } from "vitest";
import {
  identityProblems,
  isJsonObject,
  JsonFloat,
  SchemaValidationError,
  validate,
} from "../src/index.js";
import type { JsonObject } from "../src/json/value.js";
import { bundle, group, manifest, rejectionCase, timeline } from "./fixtures.js";

type Problem = [readonly (string | number)[], string];

function problems(value: JsonObject): Problem[] {
  return identityProblems(value).map((problem) => [problem.path, problem.detail]);
}

/** The one problem of a value, which `validate` raises too. */
function only(value: JsonObject): Problem {
  const found = problems(value);
  expect(found.length).toBe(1);
  try {
    validate(value);
  } catch (error) {
    expect(error).toBeInstanceOf(SchemaValidationError);
    expect([
      (error as SchemaValidationError).path,
      (error as SchemaValidationError).detail,
    ]).toEqual(found[0]);
    return found[0] as Problem;
  }
  throw new Error("value was accepted");
}

const targets = (...ids: string[]) =>
  ids.map((id, index) => ({ id, type: "jump_to", manifestation: "segno", coordinate: [index, 1] }));

const jump = (id: string, target: string | null, manifestation = "dal_segno") => ({
  id,
  type: "jump_from",
  manifestation,
  coordinate: [4, 1],
  ...(target === null ? {} : { target }),
});

const ROWS = [{ count: 1, qstamp: [0, 1], actual_length: [4, 1] }];

const table = (xValues: unknown[], yValues: unknown[], id = "tempo") => ({
  type: "TableMap",
  id,
  source_unit: "quarters",
  target_unit: null,
  x_values: xValues,
  y_values: yValues,
});

const piecewise = (breaks: unknown[], maps: JsonObject[]) => ({
  type: "PiecewiseMap",
  id: "sections",
  source_unit: "quarters",
  target_unit: null,
  breaks,
  maps,
});

const linear = (id: string) => ({ type: "LinearMap", id, source_unit: null, target_unit: null });

const view = (id: string, reference: string) => ({
  type: "MeasureNumberMap",
  id,
  source_unit: "quarters",
  target_unit: null,
  measure_map: reference,
});

const maps = (...conversionMaps: JsonObject[]) =>
  manifest([timeline("score", "quarters", [8, 1], { conversion_maps: conversionMaps })]);

describe("conversion maps and MeasureMaps", () => {
  it("holds a TableMap's arrays to agree", () => {
    expect(
      only(
        maps(
          table(
            [
              [0, 1],
              [4, 1],
              [8, 1],
            ],
            [60, 72],
          ),
        ),
      ),
    ).toEqual([
      ["timelines", 0, "conversion_maps", 0, "y_values"],
      "TableMap 'tempo' has 3 x values and 2 y values",
    ]);
    expect(only(maps(table([[0, 1], [2, 1], new JsonFloat(2)], [1, 2, 3])))).toEqual([
      ["timelines", 0, "conversion_maps", 0, "x_values", 2],
      "x value 2.0 of TableMap 'tempo' does not exceed the one before it",
    ]);
    const accepted = maps(table([[0, 1], 0.5, [3, 4]], [1, 2, 3]));
    expect(problems(accepted)).toEqual([]);
    validate(accepted);
  });

  it("gives a PiecewiseMap one map per interval", () => {
    const three = [
      [0, 1],
      [8, 1],
      [16, 1],
    ];
    expect(only(maps(piecewise(three, [linear("a")])))).toEqual([
      ["timelines", 0, "conversion_maps", 0, "maps"],
      "PiecewiseMap 'sections' has 1 map for 3 breaks; it needs 2 maps",
    ]);
    const back = [
      [0, 1],
      [8, 1],
      [4, 1],
    ];
    expect(only(maps(piecewise(back, [linear("a"), linear("b")])))).toEqual([
      ["timelines", 0, "conversion_maps", 0, "breaks", 2],
      "break [4, 1] of PiecewiseMap 'sections' does not exceed the one before it",
    ]);
  });

  it("checks a nested map at its own path", () => {
    const repeated = (id: string) =>
      table(
        [
          [1, 1],
          [1, 1],
        ],
        [1, 2],
        id,
      );
    const chain = {
      type: "ChainMap",
      id: "chain",
      source_unit: "quarters",
      target_unit: null,
      maps: [repeated("tc")],
    };
    const both = {
      type: "CombinationMap",
      id: "both",
      source_unit: "quarters",
      target_unit: null,
      maps: { b: repeated("tb"), a: repeated("ta") },
    };
    const pieces = piecewise(
      [
        [0, 1],
        [8, 1],
      ],
      [repeated("tp")],
    );
    const child = timeline("c", "quarters", [8, 1], {
      offset: [0, 1],
      conversion_maps: [repeated("tk")],
    });
    const root = timeline("score", "quarters", [8, 1], {
      conversion_maps: [chain, both, pieces],
      children: [child],
    });
    const message = (id: string) =>
      `x value [1, 1] of TableMap '${id}' does not exceed the one before it`;
    expect(problems(manifest([root]))).toEqual([
      [["timelines", 0, "conversion_maps", 0, "maps", 0, "x_values", 1], message("tc")],
      [["timelines", 0, "conversion_maps", 1, "maps", "a", "x_values", 1], message("ta")],
      [["timelines", 0, "conversion_maps", 1, "maps", "b", "x_values", 1], message("tb")],
      [["timelines", 0, "conversion_maps", 2, "maps", 0, "x_values", 1], message("tp")],
      [["timelines", 0, "children", 0, "conversion_maps", 0, "x_values", 1], message("tk")],
    ]);
    expect(new Set(identityProblems(manifest([root])).map((problem) => problem.code))).toEqual(
      new Set(["conversion_map"]),
    );
  });

  const record = (id = "bars") => ({
    type: "MeasureRecordMap",
    id,
    source_unit: "quarters",
    target_unit: null,
    measure_map: "measures",
  });
  const scale = (source: string | null, target: string | null = "quarters", id = "scale") => ({
    type: "LinearMap",
    id,
    source_unit: source,
    target_unit: target,
    scalar: [1, 480],
  });
  const HOLDER_IDS: Readonly<Record<string, string>> = {
    ChainMap: "chain",
    CombinationMap: "both",
  };
  const holder = (
    kind: string,
    source: string | null,
    maps: JsonObject[] | JsonObject,
    rest: JsonObject = {},
  ) => ({
    type: kind,
    id: HOLDER_IDS[kind] ?? "sections",
    source_unit: source,
    target_unit: null,
    maps,
    ...rest,
  });
  const ticks = (conversionMaps: JsonObject[], children: JsonObject[] = []) =>
    manifest([timeline("score", "ticks", 3840, { conversion_maps: conversionMaps, children })], {
      measure_maps: [{ id: "measures", rows: ROWS }],
    });

  it("holds a map to convert from its timeline's unit", () => {
    expect(only(ticks([record()]))).toEqual([
      ["timelines", 0, "conversion_maps", 0, "source_unit"],
      "MeasureRecordMap 'bars' has source unit 'quarters', its timeline 'score' has 'ticks'",
    ]);
    const child = timeline("c", "ticks", 960, { offset: 0, conversion_maps: [record()] });
    expect(only(ticks([], [child]))).toEqual([
      ["timelines", 0, "children", 0, "conversion_maps", 0, "source_unit"],
      "MeasureRecordMap 'bars' has source unit 'quarters', its timeline 'c' has 'ticks'",
    ]);
    const chained = holder("ChainMap", "ticks", [scale("ticks"), record()]);
    const loose = scale(null, null, "loose");
    const unstated = holder("PiecewiseMap", null, [scale("seconds", "quarters", "held")], {
      breaks: [0, 960],
    });
    const accepted = ticks([chained, loose, unstated]);
    expect(problems(accepted)).toEqual([]);
    validate(accepted);
  });

  it("holds a held map to convert from its holder's source unit", () => {
    const later = scale("seconds", "quarters", "later");
    const chain = holder("ChainMap", "quarters", [scale("ticks"), later]);
    expect(only(maps(chain))).toEqual([
      ["timelines", 0, "conversion_maps", 0, "maps", 0, "source_unit"],
      "LinearMap 'scale' has source unit 'ticks', its ChainMap 'chain' has 'quarters'",
    ]);
    const both = holder("CombinationMap", "ticks", { bar: record("bar") });
    expect(only(ticks([both]))).toEqual([
      ["timelines", 0, "conversion_maps", 0, "maps", "bar", "source_unit"],
      "MeasureRecordMap 'bar' has source unit 'quarters', its CombinationMap 'both' has 'ticks'",
    ]);
    const pieces = holder("PiecewiseMap", "quarters", [scale("seconds")], {
      breaks: [
        [0, 1],
        [8, 1],
      ],
    });
    expect(only(maps(pieces))).toEqual([
      ["timelines", 0, "conversion_maps", 0, "maps", 0, "source_unit"],
      "LinearMap 'scale' has source unit 'seconds', its PiecewiseMap 'sections' has 'quarters'",
    ]);
    expect(new Set(identityProblems(maps(chain)).map((problem) => problem.code))).toEqual(
      new Set(["conversion_map"]),
    );
  });

  it("holds a measure view to name a MeasureMap", () => {
    const both = {
      type: "CombinationMap",
      id: "both",
      source_unit: "quarters",
      target_unit: null,
      maps: { bar: view("bar", "ghost") },
    };
    const value = manifest(
      [timeline("score", "quarters", [8, 1], { conversion_maps: [view("number", "ghost"), both] })],
      { measure_maps: [{ id: "measures", rows: ROWS }] },
    );
    expect(problems(value)).toEqual([
      [
        ["timelines", 0, "conversion_maps", 0, "measure_map"],
        "'ghost' names no MeasureMap of this manifest",
      ],
      [
        ["timelines", 0, "conversion_maps", 1, "maps", "bar", "measure_map"],
        "'ghost' names no MeasureMap of this manifest",
      ],
    ]);
    expect(new Set(identityProblems(value).map((problem) => problem.code))).toEqual(
      new Set(["dangling_target"]),
    );
    const named = manifest(
      [
        timeline("score", "quarters", [8, 1], { conversion_maps: [view("number", "measures")] }),
        timeline("take", "seconds", new JsonFloat(60)),
      ],
      { measure_maps: [{ id: "measures", rows: ROWS }] },
    );
    expect(problems(named)).toEqual([]);
    validate(named);
  });

  it("shares the manifest scope between MeasureMap ids", () => {
    const value = manifest([timeline("score")], {
      groups: [group("g", ["score"])],
      measure_maps: ["score", "g", "m", "m"].map((id) => ({ id, rows: ROWS })),
    });
    expect(problems(value)).toEqual([
      [
        ["measure_maps", 0, "id"],
        "'score' is not unique in the manifest, first at #/timelines/0/id",
      ],
      [["measure_maps", 1, "id"], "'g' is not unique in the manifest, first at #/groups/0/id"],
      [
        ["measure_maps", 3, "id"],
        "'m' is not unique in the manifest, first at #/measure_maps/2/id",
      ],
    ]);
    expect(new Set(identityProblems(value).map((problem) => problem.code))).toEqual(
      new Set(["duplicate_id"]),
    );
    const named = manifest([timeline("score")], {
      id: "m",
      measure_maps: [{ id: "m", rows: ROWS }],
    });
    expect(only(named)).toEqual([
      ["id"],
      "'m' is not unique in the manifest, first at #/measure_maps/0/id",
    ]);
    expect(identityProblems(named).map((problem) => problem.code)).toEqual(["manifest_id"]);
  });
});

describe("identity", () => {
  it("finds nothing in the bundle document", () => {
    expect(problems(bundle())).toEqual([]);
    validate(bundle());
  });

  it("reports a repeated id within a root at its later occurrence", () => {
    const child = timeline("c", "quarters", [8, 1], { offset: [0, 1], flow_control: targets("m") });
    const root = timeline("bare", "quarters", [8, 1], {
      flow_control: targets("m", "m", "bare"),
      children: [child],
    });
    expect(problems(manifest([root]))).toEqual([
      [
        ["timelines", 0, "flow_control", 1, "id"],
        "'m' is not unique in the manifest, first at #/timelines/0/flow_control/0/id",
      ],
      [
        ["timelines", 0, "flow_control", 2, "id"],
        "'bare' is not unique in the manifest, first at #/timelines/0/id",
      ],
      [
        ["timelines", 0, "children", 0, "flow_control", 0, "id"],
        "'m' is not unique in the manifest, first at #/timelines/0/flow_control/0/id",
      ],
    ]);
  });

  it("scopes a nested map id with its root", () => {
    const units = { source_unit: null, target_unit: null };
    const linear = (id: string): JsonObject => ({ type: "LinearMap", id, ...units });
    const chain = { type: "ChainMap", id: "c", maps: [linear("l"), linear("l")], ...units };
    const piecewise = {
      type: "PiecewiseMap",
      id: "p",
      breaks: [
        [0, 1],
        [4, 1],
      ],
      maps: [linear("l")],
      ...units,
    };
    const combination = {
      type: "CombinationMap",
      id: "cmap_1",
      maps: { output: linear("cmap_1") },
      ...units,
    };
    const region = { id: "l", start: [0, 1], end: [1, 1] };
    const held = ["timelines", 0, "conversion_maps", 0, "maps"];
    expect(
      only(manifest([timeline("s", "quarters", [8, 1], { conversion_maps: [chain] })])),
    ).toEqual([
      [...held, 1, "id"],
      "'l' is not unique in the manifest, first at #/timelines/0/conversion_maps/0/maps/0/id",
    ]);
    expect(
      only(
        manifest([
          timeline("s", "quarters", [8, 1], { conversion_maps: [piecewise], regions: [region] }),
        ]),
      ),
    ).toEqual([
      [...held, 0, "id"],
      "'l' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    ]);
    expect(
      only(manifest([timeline("s", "quarters", [8, 1], { conversion_maps: [combination] })])),
    ).toEqual([
      [...held, "output", "id"],
      "'cmap_1' is not unique in the manifest, first at #/timelines/0/conversion_maps/0/id",
    ]);
  });

  it("holds every id unique across the manifest", () => {
    expect(
      only(
        manifest([
          timeline("a", "quarters", [8, 1], { flow_control: targets("m") }),
          timeline("b", "quarters", [8, 1], { flow_control: targets("m") }),
        ]),
      ),
    ).toEqual([
      ["timelines", 1, "flow_control", 0, "id"],
      "'m' is not unique in the manifest, first at #/timelines/0/flow_control/0/id",
    ]);
    const score = () =>
      timeline("score", "quarters", [8, 1], {
        regions: [{ id: "perf", start: [0, 1], end: [1, 1] }],
      });
    const take = timeline("take", "quarters", [8, 1], {
      children: [timeline("perf", "quarters", [8, 1], { offset: [0, 1] })],
    });
    expect(only(manifest([score(), take]))).toEqual([
      ["timelines", 1, "children", 0, "id"],
      "'perf' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    ]);
    const chain = (id: string) => ({
      type: "ChainMap",
      id,
      source_unit: null,
      target_unit: null,
      maps: [linear("l")],
    });
    expect(
      only(
        manifest([
          timeline("a", "quarters", [8, 1], { conversion_maps: [chain("c")] }),
          timeline("b", "quarters", [8, 1], { conversion_maps: [chain("d")] }),
        ]),
      ),
    ).toEqual([
      ["timelines", 1, "conversion_maps", 0, "maps", 0, "id"],
      "'l' is not unique in the manifest, first at #/timelines/0/conversion_maps/0/maps/0/id",
    ]);
    expect(only(manifest([score()], { groups: [group("perf", ["score"])] }))).toEqual([
      ["groups", 0, "id"],
      "'perf' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    ]);
    const named = manifest([score()], { id: "perf" });
    expect(only(named)).toEqual([
      ["id"],
      "'perf' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    ]);
    expect(identityProblems(named).map((problem) => problem.code)).toEqual(["manifest_id"]);
  });

  it("keeps targets within their timeline", () => {
    const child = timeline("c", "quarters", [8, 1], {
      offset: [0, 1],
      flow_control: [...targets("there"), jump("cj", "here")],
    });
    const fine = { id: "fine", type: "flow_marker", manifestation: "fine", coordinate: [6, 1] };
    const root = timeline("bare", "quarters", [8, 1], {
      flow_control: [
        ...targets("here"),
        fine,
        jump("j1", "here"),
        jump("j2", null, "da_capo"),
        jump("j3", "there"),
        jump("j4", "fine"),
        jump("j5", null, "repeat_end"),
      ],
      children: [child],
    });
    expect(problems(manifest([root]))).toEqual([
      [["timelines", 0, "flow_control", 4, "target"], "'there' names no jump_to of this timeline"],
      [["timelines", 0, "flow_control", 5, "target"], "'fine' names no jump_to of this timeline"],
      [
        ["timelines", 0, "children", 0, "flow_control", 1, "target"],
        "'here' names no jump_to of this timeline",
      ],
    ]);
  });

  /** A document for each place an id is checked, with the path of `word` in it. */
  const idDocuments = (word: string): [JsonObject, (string | number)[]][] => {
    const linear = { type: "LinearMap", id: word, source_unit: null, target_unit: null };
    const holders: [JsonObject, (string | number)[]][] = [
      [{ type: "ChainMap", id: "c", maps: [linear] }, ["maps", 0, "id"]],
      [
        {
          type: "PiecewiseMap",
          id: "p",
          breaks: [
            [0, 1],
            [4, 1],
          ],
          maps: [linear],
        },
        ["maps", 0, "id"],
      ],
      [{ type: "CombinationMap", id: "o", maps: { output: linear } }, ["maps", "output", "id"]],
    ];
    const flow: JsonObject[] = [
      { id: word, type: "flow_marker", manifestation: "fine", coordinate: [1, 1] },
      { id: word, type: "jump_from", manifestation: "da_capo", coordinate: [1, 1] },
      { id: word, type: "jump_to", manifestation: "coda", coordinate: [1, 1] },
    ];
    return [
      [manifest([timeline(word)]), ["timelines", 0, "id"]],
      [
        manifest([
          timeline("s", "quarters", [8, 1], {
            children: [timeline(word, "quarters", [8, 1], { offset: [0, 1] })],
          }),
        ]),
        ["timelines", 0, "children", 0, "id"],
      ],
      [
        manifest([timeline("s", "quarters", [8, 1], { conversion_maps: [linear] })]),
        ["timelines", 0, "conversion_maps", 0, "id"],
      ],
      ...holders.map(([holder, at]): [JsonObject, (string | number)[]] => [
        manifest([
          timeline("s", "quarters", [8, 1], {
            conversion_maps: [{ source_unit: null, target_unit: null, ...holder }],
          }),
        ]),
        ["timelines", 0, "conversion_maps", 0, ...at],
      ]),
      [
        manifest([
          timeline("s", "quarters", [8, 1], {
            regions: [{ id: word, start: [0, 1], end: [1, 1] }],
          }),
        ]),
        ["timelines", 0, "regions", 0, "id"],
      ],
      [manifest([timeline("s")], { groups: [group(word, ["s"])] }), ["groups", 0, "id"]],
      [
        manifest([timeline("s")], { measure_maps: [{ id: word, rows: ROWS }] }),
        ["measure_maps", 0, "id"],
      ],
      [manifest([timeline("s")], { id: word }), ["id"]],
      ...flow.map((element): [JsonObject, (string | number)[]] => [
        manifest([timeline("s", "quarters", [8, 1], { flow_control: [element] })]),
        ["timelines", 0, "flow_control", 0, "id"],
      ]),
    ];
  };

  it.each([
    "start",
    "end",
    "name",
    "label",
    "card",
    "regions_1",
    "flow_control_907",
    "perf/take 2",
    "https://example.org/piece/score#exposition",
  ])("accepts %s as any id", (word) => {
    for (const [document] of idDocuments(word)) {
      expect(problems(document)).toEqual([]);
      validate(document);
    }
  });

  it("keeps timeline ids unique across roots", () => {
    expect(only(manifest([timeline("piece"), timeline("piece")]))).toEqual([
      ["timelines", 1, "id"],
      "'piece' is not unique in the manifest, first at #/timelines/0/id",
    ]);
    const child = () => timeline("excerpt", "quarters", [8, 1], { offset: [0, 1] });
    const value = manifest([
      timeline("a", "quarters", [8, 1], { children: [child()] }),
      timeline("b", "quarters", [8, 1], { children: [child()] }),
    ]);
    expect(only(value)).toEqual([
      ["timelines", 1, "children", 0, "id"],
      "'excerpt' is not unique in the manifest, first at #/timelines/0/children/0/id",
    ]);
  });

  it("reports a timeline id repeated within a root once", () => {
    const value = manifest([
      timeline("a", "quarters", [8, 1], {
        children: [timeline("a", "quarters", [8, 1], { offset: [0, 1] })],
      }),
    ]);
    expect(problems(value)).toEqual([
      [
        ["timelines", 0, "children", 0, "id"],
        "'a' is not unique in the manifest, first at #/timelines/0/id",
      ],
    ]);
  });

  it("keeps group ids apart", () => {
    expect(only(manifest([timeline("score")], { groups: [group("score", [])] }))).toEqual([
      ["groups", 0, "id"],
      "'score' is not unique in the manifest, first at #/timelines/0/id",
    ]);
    expect(
      only(manifest([timeline("score")], { groups: [group("g", []), group("g", [])] })),
    ).toEqual([["groups", 1, "id"], "'g' is not unique in the manifest, first at #/groups/0/id"]);
  });

  it("keeps the manifest id apart", () => {
    expect(only(manifest([timeline("score")], { id: "score" }))).toEqual([
      ["id"],
      "'score' is not unique in the manifest, first at #/timelines/0/id",
    ]);
    expect(only(manifest([timeline("score")], { id: "g", groups: [group("g", [])] }))).toEqual([
      ["id"],
      "'g' is not unique in the manifest, first at #/groups/0/id",
    ]);
    expect(problems(manifest([timeline("g")], { id: "g", groups: [group("g", [])] }))).toEqual([
      [["groups", 0, "id"], "'g' is not unique in the manifest, first at #/timelines/0/id"],
      [["id"], "'g' is not unique in the manifest, first at #/timelines/0/id"],
    ]);
  });

  it("checks members", () => {
    expect(only(manifest([timeline("score")], { groups: [group("g", ["tempo"])] }))).toEqual([
      ["groups", 0, "members", 0],
      "'tempo' names no timeline of this manifest",
    ]);
    const piece = () =>
      timeline("piece", "quarters", [8, 1], {
        children: [timeline("half", "quarters", [4, 1], { offset: [4, 1] })],
      });
    expect(only(manifest([piece()], { groups: [group("g", ["piece", "half"])] }))).toEqual([
      ["groups", 0, "members", 1],
      "member 'half' lies inside member 'piece' of the same group",
    ]);
    expect(only(manifest([piece()], { groups: [group("g", ["half", "piece"])] }))).toEqual([
      ["groups", 0, "members", 1],
      "member 'piece' contains member 'half' of the same group",
    ]);
  });

  it("accepts a child and its root in other groups or none", () => {
    const value = bundle();
    validate(value);
    ((value.groups as unknown as [JsonObject])[0].members as string[]).push("recording");
    (((value.graphical as unknown as JsonObject).order as JsonObject).group_1 as string[]).push(
      "recording",
    );
    validate(value);
  });

  it("accepts a timeline in two groups", () => {
    const value = manifest([timeline("t"), timeline("u"), timeline("v")], {
      groups: [group("g1", ["t", "u"]), group("g2", ["t", "v"])],
    });
    expect(problems(value)).toEqual([]);
    validate(value);
  });

  it("keeps a group without members", () => {
    validate(manifest([timeline("score")], { groups: [group("empty", [])] }));
  });

  it("checks display orders", () => {
    const order = (value: JsonObject) => (value.graphical as JsonObject).order as JsonObject;
    let value = bundle();
    order(value).g9 = [];
    expect(only(value)).toEqual([
      ["graphical", "order", "g9"],
      "'g9' names no group or timeline of this manifest",
    ]);
    value = bundle();
    order(value).group_1 = ["score", "page", "performance"];
    expect(only(value)).toEqual([
      ["graphical", "order", "group_1", 1],
      "'page' is not a member of group 'group_1'",
    ]);
    value = bundle();
    order(value).group_2 = ["page"];
    expect(only(value)).toEqual([
      ["graphical", "order", "group_2"],
      "member 'excerpt' of group 'group_2' is missing",
    ]);
    value = bundle();
    delete order(value).group_2;
    validate(value);
  });

  /** `score` with a region `intro` and a child `take` holding a child `bar`. */
  const banded = (order: JsonObject, rest: JsonObject = {}) =>
    manifest(
      [
        timeline("score", "quarters", [8, 1], {
          regions: [{ id: "intro", start: [0, 1], end: [1, 1] }],
          children: [
            timeline("take", "quarters", [4, 1], {
              offset: [0, 1],
              children: [timeline("bar", "quarters", [2, 1], { offset: [0, 1] })],
            }),
          ],
        }),
      ],
      { ...rest, graphical: { order } },
    );

  const DEFAULT_BANDS = [
    "children",
    "conversion_maps",
    "line",
    "markers",
    "regions",
    "flow_control",
  ];
  const SCORE_BANDS = ["children", "markers", "line", "conversion_maps", "regions", "flow_control"];

  it("accepts a band order at a root and at a descendant", () => {
    for (const value of [
      banded({ score: DEFAULT_BANDS }),
      banded({ score: SCORE_BANDS }),
      banded({
        take: [...DEFAULT_BANDS].reverse(),
        bar: ["line", "children", "conversion_maps", "markers", "regions", "flow_control"],
      }),
    ]) {
      expect(problems(value)).toEqual([]);
      validate(value);
    }
  });

  it.each(["annotations", "region", "score", "score/regions_1", "Regions"])(
    "refuses %s in a band order",
    (stranger) => {
      expect(only(banded({ score: [...SCORE_BANDS, stranger] }))).toEqual([
        ["graphical", "order", "score", 6],
        `'${stranger}' is not 'line' or a facet, in the band order of 'score'`,
      ]);
    },
  );

  it("checks band orders", () => {
    expect(only(banded({ score: SCORE_BANDS.slice(0, -1) }))).toEqual([
      ["graphical", "order", "score"],
      "'flow_control' is missing from the band order of 'score'",
    ]);
    expect(problems(banded({ score: [] }))).toEqual(
      DEFAULT_BANDS.map((entry) => [
        ["graphical", "order", "score"],
        `'${entry}' is missing from the band order of 'score'`,
      ]),
    );
    expect(only(banded({ intro: DEFAULT_BANDS }))).toEqual([
      ["graphical", "order", "intro"],
      "'intro' names no group or timeline of this manifest",
    ]);
    expect(only(banded({ nothing: [] }))).toEqual([
      ["graphical", "order", "nothing"],
      "'nothing' names no group or timeline of this manifest",
    ]);
  });

  it("reads a key naming a group and a timeline as the group's", () => {
    const value = banded({ score: ["score"] }, { groups: [group("score", [])] });
    expect(problems(value)).toEqual([
      [["groups", 0, "id"], "'score' is not unique in the manifest, first at #/timelines/0/id"],
      [["graphical", "order", "score", 0], "'score' is not a member of group 'score'"],
    ]);
  });

  it("requires a child to share its parent's unit", () => {
    expect(
      only(
        manifest([
          timeline("score", "quarters", [8, 1], {
            children: [timeline("take", "seconds", 4, { offset: [2, 1] })],
          }),
        ]),
      ),
    ).toEqual([
      ["timelines", 0, "children", 0, "unit"],
      "child 'take' has unit 'seconds', its parent 'score' has 'quarters'",
    ]);
    const number = timeline("n", "number", [4, 1], { offset: [0, 1], number_type: "fraction" });
    expect(only(manifest([timeline("score", "quarters", [8, 1], { children: [number] })]))).toEqual(
      [
        ["timelines", 0, "children", 0, "unit"],
        "child 'n' has unit 'number', its parent 'score' has 'quarters'",
      ],
    );
    const grandchild = timeline("b", "ticks", 4, { offset: [1, 1] });
    const parent = timeline("a", "quarters", [8, 1], { offset: [0, 1], children: [grandchild] });
    expect(only(manifest([timeline("score", "quarters", [8, 1], { children: [parent] })]))).toEqual(
      [
        ["timelines", 0, "children", 0, "children", 0, "unit"],
        "child 'b' has unit 'ticks', its parent 'a' has 'quarters'",
      ],
    );
    const same = timeline("c", "quarters", [8, 1], { offset: [0, 1] });
    expect(
      problems(manifest([timeline("score", "quarters", [8, 1], { children: [same] })])),
    ).toEqual([]);
  });

  it("accepts a negative offset, of a child or a root", () => {
    const take = (offset: unknown) =>
      manifest([
        timeline("recording", "seconds", 60, {
          children: [timeline("take", "seconds", 4, { offset })],
        }),
      ]);
    const child = (offset: unknown) =>
      manifest([
        timeline("score", "quarters", [8, 1], {
          children: [timeline("c", "quarters", [8, 1], { offset })],
        }),
      ]);
    const grandchild = timeline("b", "quarters", [8, 1], { offset: [-1, 2] });
    const parent = timeline("a", "quarters", [8, 1], { offset: [0, 1], children: [grandchild] });
    for (const value of [
      take(-1.5),
      child([-1, 1000000]),
      manifest([timeline("score", "quarters", [8, 1], { children: [parent] })]),
      {
        timetoshare: "0.1.0",
        timelines: [
          {
            id: "piece",
            unit: "quarters",
            length: [32, 1],
            children: [{ id: "take", unit: "quarters", offset: [-3, 2], length: [4, 1] }],
          },
        ],
      },
      child([0, 1]),
      take(-0),
      manifest([timeline("take", "seconds", 2.5, { offset: -1700000000.25 })]),
      manifest([timeline("score", "quarters", [8, 1], { offset: [-3, 2] })]),
    ]) {
      expect(problems(value)).toEqual([]);
      validate(value);
    }
    const long = timeline("take", "quarters", [40, 1], { offset: [-3, 2] });
    expect(only(manifest([timeline("piece", "quarters", [32, 1], { children: [long] })]))).toEqual([
      ["timelines", 0, "children", 0, "length"],
      "child 'take' ends at [77, 2], beyond the length [32, 1] of its parent 'piece'",
    ]);
  });

  it("requires a child to lie within its parent's known length", () => {
    const recording = (length: unknown, ...children: JsonObject[]) =>
      manifest([timeline("recording", "seconds", length, { children })]);
    const take = (length: unknown, offset: unknown) =>
      timeline("take", "seconds", length, { offset });
    const score = (length: unknown, ...children: JsonObject[]) =>
      manifest([timeline("score", "quarters", length, { children })]);
    expect(only(recording(new JsonFloat(60), take(null, new JsonFloat(75))))).toEqual([
      ["timelines", 0, "children", 0, "offset"],
      "offset 75.0 of 'take' is beyond the length 60.0 of its parent 'recording'",
    ]);
    expect(only(score([8, 1], timeline("c", "quarters", [2, 1], { offset: [9, 1] })))).toEqual([
      ["timelines", 0, "children", 0, "offset"],
      "offset [9, 1] of 'c' is beyond the length [8, 1] of its parent 'score'",
    ]);
    expect(only(score([10, 1], timeline("coda", "quarters", [4, 1], { offset: [8, 1] })))).toEqual([
      ["timelines", 0, "children", 0, "length"],
      "child 'coda' ends at [12, 1], beyond the length [10, 1] of its parent 'score'",
    ]);
    expect(only(recording(0.75, take(0.5, 0.5)))).toEqual([
      ["timelines", 0, "children", 0, "length"],
      "child 'take' ends at 1.0, beyond the length 0.75 of its parent 'recording'",
    ]);
    expect(only(recording(0.3, take(0.2, 0.1)))).toEqual([
      ["timelines", 0, "children", 0, "length"],
      "child 'take' ends at [10808639105689191, 36028797018963968], beyond the length 0.3 of its parent 'recording'",
    ]);
    const midi = timeline("midi", "ticks", 480, {
      children: [timeline("m", "ticks", 240, { offset: 480 })],
    });
    expect(only(manifest([midi]))).toEqual([
      ["timelines", 0, "children", 0, "length"],
      "child 'm' ends at 720, beyond the length 480 of its parent 'midi'",
    ]);
    const loose = timeline("f", "quarters", 2.5, { offset: [7, 1], number_type: "float" });
    expect(only(score([8, 1], loose))).toEqual([
      ["timelines", 0, "children", 0, "length"],
      "child 'f' ends at [19, 2], beyond the length [8, 1] of its parent 'score'",
    ]);
    const other = timeline("take", "seconds", new JsonFloat(100), { offset: [2, 1] });
    expect(problems(score([8, 1], other))).toEqual([
      [
        ["timelines", 0, "children", 0, "unit"],
        "child 'take' has unit 'seconds', its parent 'score' has 'quarters'",
      ],
    ]);
    const grandchild = timeline("b", "quarters", [2, 1], { offset: [3, 1] });
    const child = timeline("a", "quarters", [4, 1], { offset: [0, 1], children: [grandchild] });
    expect(only(score([8, 1], child))).toEqual([
      ["timelines", 0, "children", 0, "children", 0, "length"],
      "child 'b' ends at [5, 1], beyond the length [4, 1] of its parent 'a'",
    ]);
    const line = timeline("line", "quarters", [8, 1], {
      is_segment_line: true,
      children: [
        timeline("a", "quarters", null, { offset: [0, 1] }),
        timeline("b", "quarters", [1, 1], { offset: [10, 1] }),
      ],
    });
    expect(problems(manifest([line]))).toEqual([
      [
        ["timelines", 0, "children", 0, "length"],
        "child 'a' ends at [10, 1], beyond the length [8, 1] of its parent 'line'",
      ],
      [
        ["timelines", 0, "children", 1, "offset"],
        "offset [10, 1] of 'b' is beyond the length [8, 1] of its parent 'line'",
      ],
      [["timelines", 0, "length"], "the segments of segment line 'line' do not end at its length"],
    ]);
    for (const value of [
      recording(new JsonFloat(60), take(null, new JsonFloat(60))),
      score([10, 1], timeline("c", "quarters", [2, 1], { offset: [8, 1] })),
      recording(0.75, take(0.25, 0.5)),
      score(null, timeline("c", "quarters", [8, 1], { offset: [100, 1] })),
    ]) {
      expect(problems(value)).toEqual([]);
      validate(value);
    }
  });

  it.each([
    [
      "region_id_duplicate_across_roots",
      "'region_1' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    ],
    ["band_order_missing_band", "'markers' is missing from the band order of 'score'"],
    [
      "band_order_unknown_entry",
      "'annotations' is not 'line' or a facet, in the band order of 'score'",
    ],
    [
      "band_order_old_form",
      "'score/regions_1' is not 'line' or a facet, in the band order of 'score'",
    ],
    ["order_unknown_group", "'group_9' names no group or timeline of this manifest"],
    ["child_unit_differs", "child 'take' has unit 'seconds', its parent 'score' has 'quarters'"],
    [
      "child_offset_beyond_parent",
      "offset 75.0 of 'take' is beyond the length 60.0 of its parent 'recording'",
    ],
    [
      "child_end_beyond_parent",
      "child 'coda' ends at [12, 1], beyond the length [10, 1] of its parent 'score'",
    ],
  ])("states the message of the shared case %s", (name, message) => {
    const testCase = rejectionCase(`${name}.json`);
    if (!isJsonObject(testCase.manifest)) throw new Error(`${name} holds no manifest object`);
    expect(only(testCase.manifest)).toEqual([testCase.path, message]);
  });

  it("reports every step in order", () => {
    const first = timeline("first", "quarters", [8, 1], {
      flow_control: [jump("j", "nowhere")],
      conversion_maps: [
        view("bars", "no-measures"),
        table(
          [
            [0, 1],
            [4, 1],
            [8, 1],
          ],
          [60, 72],
        ),
      ],
      children: [
        timeline("kid", "seconds", 1, { offset: [-1, 1] }),
        timeline("gone", "quarters", null, { offset: [9, 1] }),
        timeline("late", "quarters", [8, 1], { offset: [6, 1] }),
      ],
    });
    const second = timeline("second", "quarters", [8, 1], {
      regions: [{ id: "kid", start: [0, 1], end: [1, 1] }],
    });
    const value = manifest([first, second, timeline("second")], {
      id: "g2",
      groups: [group("first", ["ghost", "second"]), group("g2", ["second"])],
      measure_maps: [{ id: "first", rows: ROWS }],
      graphical: {
        order: {
          zz: [],
          kid: ["regions_2", "line", "children", "conversion_maps", "markers", "regions"],
          g2: ["stranger"],
        },
      },
    });
    expect(problems(value)).toEqual([
      [
        ["timelines", 0, "flow_control", 0, "target"],
        "'nowhere' names no jump_to of this timeline",
      ],
      [
        ["timelines", 0, "conversion_maps", 0, "measure_map"],
        "'no-measures' names no MeasureMap of this manifest",
      ],
      [
        ["timelines", 0, "conversion_maps", 1, "y_values"],
        "TableMap 'tempo' has 3 x values and 2 y values",
      ],
      [
        ["timelines", 0, "children", 0, "unit"],
        "child 'kid' has unit 'seconds', its parent 'first' has 'quarters'",
      ],
      [
        ["timelines", 0, "children", 1, "offset"],
        "offset [9, 1] of 'gone' is beyond the length [8, 1] of its parent 'first'",
      ],
      [
        ["timelines", 0, "children", 2, "length"],
        "child 'late' ends at [14, 1], beyond the length [8, 1] of its parent 'first'",
      ],
      [
        ["timelines", 1, "regions", 0, "id"],
        "'kid' is not unique in the manifest, first at #/timelines/0/children/0/id",
      ],
      [["timelines", 2, "id"], "'second' is not unique in the manifest, first at #/timelines/1/id"],
      [["groups", 0, "id"], "'first' is not unique in the manifest, first at #/timelines/0/id"],
      [
        ["measure_maps", 0, "id"],
        "'first' is not unique in the manifest, first at #/timelines/0/id",
      ],
      [["id"], "'g2' is not unique in the manifest, first at #/groups/1/id"],
      [["groups", 0, "members", 0], "'ghost' names no timeline of this manifest"],
      [["graphical", "order", "g2", 0], "'stranger' is not a member of group 'g2'"],
      [["graphical", "order", "g2"], "member 'second' of group 'g2' is missing"],
      [
        ["graphical", "order", "kid", 0],
        "'regions_2' is not 'line' or a facet, in the band order of 'kid'",
      ],
      [["graphical", "order", "kid"], "'flow_control' is missing from the band order of 'kid'"],
      [["graphical", "order", "zz"], "'zz' names no group or timeline of this manifest"],
    ]);
    expect(identityProblems(value).map((problem) => problem.code)).toEqual([
      ...Array<string>(2).fill("dangling_target"),
      "conversion_map",
      "child_unit",
      "child_offset",
      "child_end",
      ...Array<string>(4).fill("duplicate_id"),
      "manifest_id",
      "group_member",
      ...Array<string>(2).fill("display_order"),
      ...Array<string>(2).fill("band_order"),
      "order_key",
    ]);
    expect(() => validate(value)).toThrow(identityProblems(value)[0]?.message);
  });
});
