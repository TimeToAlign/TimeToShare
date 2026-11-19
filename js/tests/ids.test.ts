import { describe, expect, it } from "vitest";
import {
  compactJson,
  FileIdError,
  fromFileId,
  isJsonObject,
  JsonFloat,
  loads,
  toFileId,
  withBareIds,
  withFileIds,
} from "../src/index.js";
import type { JsonObject } from "../src/json/value.js";

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
    links:
    - parts:
      - represented_by: [verse, intro]
        identifiers: [{scheme: opus, value: "1"}]
      part_of:
      - identifiers: [{scheme: opus, value: "2"}]
  flow_control:
  - {id: jump_to_1, type: jump_to}
  - {id: jump_from_1, type: jump_from, target: jump_to_1}
groups:
- {id: g, members: [score]}
measure_maps:
- {id: mm, rows: []}
schemes:
- {id: opus}
links:
- identifiers:
  - {scheme: opus, value: "3"}
  - {scheme: "http://www.wikidata.org/entity/P839", value: "4"}
graphical:
  order:
    score: [line, children]
    g: [score]
  statements:
  - select:
      addresses: [{id: verse, part: [name]}]
      within: score
    set: {stroke: red}
  timestamps:
  - {id: timestamp_1, timeline: verse, coordinate: 1}
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
    links:
    - parts:
      - represented_by: ["#verse", "#intro"]
        identifiers: [{scheme: "#opus", value: "1"}]
      part_of:
      - identifiers: [{scheme: "#opus", value: "2"}]
  flow_control:
  - {id: "#jump_to_1", type: jump_to}
  - {id: "#jump_from_1", type: jump_from, target: "#jump_to_1"}
groups:
- {id: "#g", members: ["#score"]}
measure_maps:
- {id: "#mm", rows: []}
schemes:
- {id: "#opus"}
links:
- identifiers:
  - {scheme: "#opus", value: "3"}
  - {scheme: "http://www.wikidata.org/entity/P839", value: "4"}
graphical:
  order:
    "#score": [line, children]
    "#g": ["#score"]
  statements:
  - select:
      addresses: [{id: "#verse", part: [name]}]
      within: "#score"
    set: {stroke: red}
  timestamps:
  - {id: "#timestamp_1", timeline: "#verse", coordinate: 1}
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

  it("leaves band words and URIs as written", () => {
    const value = withBareIds(filed());
    expect(at(value, "graphical", "order", "score")).toEqual(["line", "children"]);
    expect(at(value, "links", 0, "identifiers", 1, "scheme")).toBe(
      "http://www.wikidata.org/entity/P839",
    );
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
    [
      (m: JsonObject) => {
        (at(m, "links", 0, "identifiers", 0) as JsonObject).scheme = "opus";
      },
      ["links", 0, "identifiers", 0, "scheme"],
      "'opus' names a scheme of this manifest, so it is written '#opus'",
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
