import { describe, expect, it } from "vitest";
import * as timetoshare from "../src/index.js";
import { dumps, loads, SchemaValidationError, UnsupportedVersionError } from "../src/index.js";
import type { JsonObject } from "../src/json/value.js";
import {
  expectWrittenAsStored,
  fixtureText,
  group,
  manifest,
  timeline,
  unknownKeys,
  warningFileNames,
  warningText,
} from "./fixtures.js";

const WARNINGS = [
  "address_unknown_member",
  "bundle_blank_provenance",
  "bundle_blank_statements",
  "combination_map_names",
  "context_absent",
  "declaration_show_projections",
  "declaration_unknown_key",
  "graphical_unknown_key",
  "group_unknown_key",
  "measure_map_row_offset_key",
  "measure_map_row_unknown_key",
  "selector_ids",
  "selector_unknown_key",
  "several_depths",
  "support_policy",
  "timeline_class",
];

describe("unknown keys", () => {
  it("has the stated warning cases", () => {
    expect(warningFileNames()).toEqual(WARNINGS);
  });

  it.each(warningFileNames())("lists the warnings of %s as Python does", (name) => {
    const text = warningText(name);
    const testCase = loads(text) as JsonObject;
    expect(Object.keys(testCase).sort()).toEqual(["manifest", "unknown_keys", "warnings"]);
    expectWrittenAsStored(text);
    timetoshare.validate(testCase.manifest);
    expect(dumps(timetoshare.unknownKeys(testCase.manifest))).toBe(dumps(testCase.unknown_keys));
    expect(dumps(timetoshare.manifestWarnings(testCase.manifest))).toBe(dumps(testCase.warnings));
  });

  it("finds them at several depths, in order", () => {
    const testCase = loads(warningText("several_depths")) as JsonObject;
    expect(
      timetoshare.unknownKeys(testCase.manifest).map((entry) => [entry.path, entry.key]),
    ).toEqual([
      [[], "x-editor"],
      [["graphical"], "arrangement"],
      [["graphical", "rules", 0], "comment"],
      [["graphical", "rules", 0, "select"], "kind"],
      [["graphical", "rules", 0, "set"], "colour"],
      [["groups", 0], "colour"],
      [["measure_maps", 0], "source"],
      [["measure_maps", 0, "rows", 0], "tempo"],
      [["timelines", 0], "lenght"],
      [["timelines", 0, "children", 0], "x-tilia"],
      [["timelines", 0, "conversion_maps", 0], "note"],
      [["timelines", 0, "conversion_maps", 0, "maps", 0], "note"],
      [["timelines", 0, "flow_control", 0], "glyph"],
      [["timelines", 0, "flow_control", 1], "via"],
      [["timelines", 0, "flow_control", 2], "pause"],
      [["timelines", 0, "regions", 0], "colour"],
    ]);
  });

  it("does not look into free objects, maps keyed by data or unknown values", () => {
    const value = manifest(
      [
        timeline("score", "quarters", [8, 1], {
          meta: { anything: { deep: 1 } },
          regions: [{ id: "r", start: [0, 1], end: [1, 1], meta: { x: 1 } }],
        }),
      ],
      {
        meta: { source: "hand" },
        groups: [group("g", ["score"], { meta: { note: 1 } })],
        graphical: {
          styles: { "any-name": { stroke: "#000000" } },
          order: { g: ["score"] },
          rules: [{ select: {}, set: "any-name" }],
        },
      },
    );
    expect(unknownKeys(value)).toEqual([]);
    value.x = { inner: { also: 1 } };
    expect(unknownKeys(value)).toEqual([{ path: [], key: "x" }]);
  });

  it("reports side as an unknown key of a declaration", () => {
    const value = manifest([timeline("score")], {
      graphical: {
        styles: { below: { side: "below" } },
        rules: [{ select: { element: "map" }, set: { fill: "#000000", side: "above" } }],
      },
    });
    expect(unknownKeys(value)).toEqual([
      { path: ["graphical", "rules", 0, "set"], key: "side" },
      { path: ["graphical", "styles", "below"], key: "side" },
    ]);
  });

  it("counts the keys of both bases of a measure view as declared", () => {
    const view = {
      type: "MeasureNumberMap",
      id: "bars",
      name: "bars",
      source_unit: "quarters",
      target_unit: null,
      measure_map: "measures",
      colour: "red",
    };
    const rows = [{ count: 1, qstamp: [0, 1], actual_length: [4, 1] }];
    const value = manifest([timeline("score", "quarters", [8, 1], { conversion_maps: [view] })], {
      measure_maps: [{ id: "measures", rows }],
    });
    expect(unknownKeys(value)).toEqual([
      { path: ["timelines", 0, "conversion_maps", 0], key: "colour" },
    ]);
  });

  it("sorts keys by code point and indices by number", () => {
    const roots = Array.from({ length: 11 }, (_, index) => timeline(`t${index}`));
    (roots[2] as JsonObject).zz = 1;
    (roots[10] as JsonObject).zz = 1;
    const value = manifest(roots, { zz: 1, aa: 1, "\u{FB00}": 1, "\u{1F600}": 1 });
    expect(unknownKeys(value)).toEqual([
      { path: [], key: "aa" },
      { path: [], key: "zz" },
      { path: [], key: "\u{FB00}" },
      { path: [], key: "\u{1F600}" },
      { path: ["timelines", 2], key: "zz" },
      { path: ["timelines", 10], key: "zz" },
    ]);
  });

  it("lists an undeclared key below a statement alone", () => {
    const value = loads(fixtureText("statements/nielsen_record")) as JsonObject;
    const subject = ((value.statements as JsonObject)["schema:about"] as JsonObject[])[0];
    (((subject as JsonObject).provenance as JsonObject[])[0] as JsonObject).x = 1;
    expect(timetoshare.unknownKeys(value)).toEqual([
      { path: ["statements", "schema:about", 0, "provenance", 0], key: "x" },
    ]);
  });

  it("lists no key of the maps keyed by data, only the undeclared keys around them", () => {
    const value = loads(fixtureText("statements/nielsen_record")) as JsonObject;
    (value["@context"] as JsonObject).ex = "http://example.org/";
    value.x = { inner: 1 };
    const subject = ((value.statements as JsonObject)["schema:about"] as JsonObject[])[0];
    (subject as JsonObject)["ex:extra"] = [
      {
        label: "b",
        "ex:part": ["c"],
        provenance: [{ method: "manual", property: "ex:part", value: "c", zz: 1 }],
      },
    ];
    expect(timetoshare.unknownKeys(value)).toEqual([
      { path: [], key: "x" },
      { path: ["statements", "schema:about", 0, "ex:extra", 0, "provenance", 0], key: "zz" },
    ]);
  });

  it("lists an undeclared key of a belief alone, not the keys of the record around it", () => {
    const value = loads(fixtureText("bare.minimal")) as JsonObject;
    value.provenance = [
      {
        property: "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        value: { id: "http://example.org/work" },
        beliefs: [{ actor: "http://example.org/editor", belief: "true", date: "2026-11-18", x: 1 }],
      },
    ];
    expect(timetoshare.unknownKeys(value)).toEqual([
      { path: ["provenance", 0, "beliefs", 0], key: "x" },
    ]);
  });

  it("raises for an invalid value before listing any key", () => {
    expect(() => unknownKeys(manifest([timeline("score", "quarters", 32)], { extra: 1 }))).toThrow(
      SchemaValidationError,
    );
    expect(() => unknownKeys({ timetoshare: "9.9.9", extra: 1 })).toThrow(UnsupportedVersionError);
  });
});
