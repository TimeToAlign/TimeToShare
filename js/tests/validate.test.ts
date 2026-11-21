import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import * as timetoshare from "../src/index.js";
import {
  compactJson,
  dumps,
  type Json,
  JsonFloat,
  jsonPointer,
  type Lossless,
  type LosslessManifest,
  loads,
  type Manifest,
  parse,
  parseJson,
  SchemaValidationError,
  UnsupportedVersionError,
} from "../src/index.js";
import { type JsonObject, plain } from "../src/json/value.js";
import {
  expectWrittenAsStored,
  fixtureFiles,
  fixtureText,
  group,
  manifest,
  rejectionCase,
  rejectionFileNames,
  rejectionText,
  repositoryRoot,
  respellable,
  timeline,
  unknownKeys,
  validate,
} from "./fixtures.js";

const SMALLEST = {
  timetoshare: "0.2.0",
  timelines: [{ id: "piece", unit: "quarters", length: [32, 1] }],
};

const REJECTIONS = [
  "address_facet_with_part",
  "address_facet_without_id",
  "alignment_anchor_display_unknown",
  "alignment_anchor_id_repeated",
  "alignment_anchor_one_timeline",
  "alignment_anchor_timestamp_not_match",
  "alignment_anchor_timestamp_unknown",
  "band_order_missing_band",
  "band_order_old_form",
  "band_order_unknown_entry",
  "belief_actor_repeated",
  "belief_date_impossible",
  "belief_value_boolean",
  "belief_value_unknown",
  "child_end_beyond_parent",
  "child_id_control_character_newline",
  "child_missing_offset",
  "child_offset_beyond_parent",
  "child_offset_fraction_on_float_axis",
  "child_unit_differs",
  "context_absent_with_provenance",
  "context_absent_with_statements",
  "context_prefix_not_namespace",
  "context_prefix_reserved_name",
  "context_term_altered",
  "context_term_missing",
  "conversion_map_unknown_type",
  "dal_segno_without_target",
  "element_value_dangling",
  "element_value_with_label",
  "float_axis_int_not_exact",
  "flow_control_coordinate_dict",
  "flow_control_object",
  "flow_control_type_break",
  "flow_marker_manifestation_segno",
  "group_id_duplicate",
  "group_id_is_descendant_id",
  "group_id_is_timeline_id",
  "group_members_repeated",
  "group_missing_id",
  "group_missing_members",
  "group_order_not_member",
  "group_order_repeated",
  "groupstamp_child_without_group",
  "groupstamp_match_timestamp",
  "groupstamp_member_parent",
  "groupstamp_without_group",
  "id_control_character_tab",
  "id_control_character_trailing_newline",
  "id_duplicate_across_kinds",
  "id_empty",
  "id_without_hash",
  "id_without_hash_short",
  "infinite_length",
  "iri_prefix_undeclared_id",
  "iri_prefix_undeclared_key",
  "iri_prefix_undeclared_type",
  "jump_target_flow_marker",
  "jump_to_target",
  "later_root_missing_unit",
  "length_coordinate_dict",
  "length_float_on_int_axis",
  "length_fraction_member_not_integral",
  "length_fraction_on_int_axis",
  "length_int_on_fraction_axis",
  "length_negative",
  "length_string_fraction",
  "length_three_element_fraction",
  "length_zero_denominator",
  "manifest_id_is_descendant_id",
  "manifest_id_is_group_id",
  "manifest_id_is_measure_map_id",
  "map_source_unit_mismatch",
  "match_timestamp_coordinate_repeated",
  "match_timestamp_in_no_matchstamp",
  "matchstamp_claims_repeated",
  "matchstamp_not_connected",
  "measure_map_id_is_timeline_id",
  "measure_map_row_actual_length_negative",
  "measure_map_row_offset_within_measure_zero",
  "measure_map_row_qstamp_negative",
  "measure_map_row_qstamp_string",
  "measure_map_row_without_count_or_id",
  "measure_map_rows_empty",
  "measure_map_rows_not_array",
  "measure_view_dangling",
  "measure_view_source_unit_ticks",
  "member_dangling",
  "members_contain_member",
  "members_inside_member",
  "nan_offset",
  "nested_map_id_duplicate",
  "order_missing_member",
  "order_not_array",
  "order_unknown_group",
  "ordered_values_null",
  "piecewise_map_breaks_not_increasing",
  "piecewise_map_maps_count",
  "provenance_basis_prefix_undeclared",
  "provenance_date_impossible",
  "provenance_date_not_written_so",
  "provenance_empty",
  "provenance_match_unknown",
  "provenance_method_unknown",
  "provenance_property_bare_word",
  "provenance_repeated",
  "reference_without_hash",
  "region_id_duplicate_across_roots",
  "region_id_is_timeline_id",
  "region_start_float_on_fraction_axis",
  "repeat_count_zero",
  "reserved_key_children_on_region",
  "reserved_key_context_on_timeline",
  "reserved_key_iri_on_region",
  "reserved_key_prefix_on_manifest",
  "reserved_key_statements_on_group",
  "reserved_key_term_on_timeline",
  "resource_integrity_algorithm_unknown",
  "resource_match_claim_twice",
  "resource_projection_twice",
  "resource_timeline_unknown",
  "root_missing_marker",
  "root_missing_timelines",
  "rule_select_empty_addresses",
  "rule_select_inside_unknown_element",
  "rule_select_projection",
  "rule_select_unknown_element",
  "rule_set_content_not_string",
  "rule_set_dasharray_malformed",
  "rule_set_max_width_zero",
  "rule_set_neither_object_nor_string",
  "rule_set_opacity_above_one",
  "rule_set_shadow_lower_case",
  "rule_set_stroke_lower_case",
  "segment_line_flag_not_boolean",
  "segment_line_gap",
  "segment_line_gap_in_later_root",
  "segment_line_not_from_zero",
  "segment_line_segment_flag",
  "segment_line_short_of_length",
  "statement_key_bare_word",
  "statement_key_keyword",
  "statement_value_float",
  "statement_value_integral_float",
  "statement_value_null",
  "statement_values_empty",
  "statement_values_repeated",
  "statements_empty",
  "subject_id_not_fragment",
  "table_map_kind_nearest",
  "table_map_lengths_differ",
  "table_map_missing_x_values",
  "table_map_x_not_increasing",
  "timeline_missing_length",
  "timeline_name_not_string",
  "timeline_number_type_unknown",
  "timeline_unit_unknown",
  "timelines_child_id_duplicate_across_roots",
  "timelines_id_duplicate_across_roots",
  "timelines_root_jump_target_dangling",
  "timestamp_coordinate_beyond_length",
  "timestamp_coordinate_negative",
  "timestamp_display_repeated",
  "timestamp_display_unknown",
  "timestamp_id_is_timeline_id",
  "timestamp_timeline_unknown",
  "to_coda_with_repeat_count",
  "type_bare_word",
  "value_node_blank_node_id",
  "value_node_empty",
  "value_object_language_and_type",
  "version_unknown",
];

/**
 * The cases whose offending value `JSON.parse` cannot read: an integer beyond
 * 2^53 comes back as the float next to it, and an integral float as the
 * integer it equals.
 */
const LOST_BY_JSON_PARSE = new Set(["float_axis_int_not_exact", "statement_value_integral_float"]);

/** The path and message of the error `validate` raises. */
function problem(value: unknown): [readonly (string | number)[], string] {
  try {
    validate(value);
  } catch (error) {
    if (!(error instanceof SchemaValidationError)) throw error;
    return [error.path, error.detail];
  }
  throw new Error("value was accepted");
}

/** Whether `validate` accepts a value; any other error than a refusal is thrown. */
function accepted(value: unknown): boolean {
  try {
    validate(value);
  } catch (error) {
    if (!(error instanceof SchemaValidationError)) throw error;
    return false;
  }
  return true;
}

describe("the units", () => {
  it.each(
    ["css_pixels", "user_units"].flatMap((unit) =>
      (
        [
          ["float", 600.5],
          ["fraction", [1201, 2]],
          ["int", 600],
        ] as const
      ).map(([numberType, length]) => [unit, numberType, length] as const),
    ),
  )("reads %s with the number type %s as points is read", (unit, numberType, length) => {
    const points = manifest([timeline("page", "points", length, { number_type: numberType })]);
    const root = manifest([timeline("page", unit, length, { number_type: numberType })]);
    expect(accepted(points)).toBe(true);
    expect(accepted(root)).toBe(true);
  });

  it.each(["px", "uu"])("refuses the abbreviation %s as no unit", (unit) => {
    try {
      validate(manifest([timeline("page", unit, 600.5)]));
    } catch (error) {
      expect(error).toBeInstanceOf(SchemaValidationError);
      expect((error as SchemaValidationError).path).toEqual(["timelines", 0, "unit"]);
      expect((error as SchemaValidationError).code).toBe("schema");
      return;
    }
    throw new Error(`${unit} was accepted`);
  });
});

describe("the version marker", () => {
  it.each([
    ["no marker", { timelines: [] }],
    ["version in meta", { meta: { schema_version: "0.2.0" }, timelines: [] }],
    ["a list", []],
    ["a string", "0.2.0"],
  ])("refuses %s at the root", (_name, value) => {
    expect(problem(value)).toEqual([[], "not a TimeToShare manifest"]);
  });

  it.each(["9.9.9", "0.1.0", "0.1", 1])("refuses version %s as unsupported", (version) => {
    try {
      validate({ timetoshare: version });
    } catch (error) {
      expect(error).toBeInstanceOf(UnsupportedVersionError);
      expect((error as UnsupportedVersionError).version).toBe(version);
      return;
    }
    throw new Error("value was accepted");
  });

  it("names the version it reads", () => {
    expect(() => validate({ timetoshare: "9.9.9", timelines: [] })).toThrow(
      'unsupported TimeToShare version "9.9.9"; this package reads 0.2.0 only',
    );
  });

  it("accepts the smallest and the empty manifest", () => {
    validate(SMALLEST);
    validate({ timetoshare: "0.2.0", timelines: [] });
  });
});

describe("own-axis representation", () => {
  it.each([
    [
      timeline("score", "quarters", 32),
      "length 32 of 'score' is an int on a fraction axis: write [32, 1]",
    ],
    [
      timeline("score", "quarters", 0.5),
      "length 0.5 of 'score' is a float on a fraction axis: write [1, 2]",
    ],
    [
      timeline("score", "quarters", 0.1),
      "length 0.1 of 'score' is a float on a fraction axis: write [3602879701896397, 36028797018963968]",
    ],
    [
      timeline("take", "seconds", [3, 4]),
      "length [3, 4] of 'take' is a fraction on a float axis: write 0.75",
    ],
    [
      timeline("take", "seconds", [1, 3]),
      "length [1, 3] of 'take' is a fraction on a float axis: write a float",
    ],
    [
      timeline("midi", "ticks", [480, 1]),
      "length [480, 1] of 'midi' is a fraction on an int axis: write 480",
    ],
    [
      timeline("midi", "ticks", 0.5),
      "length 0.5 of 'midi' is a float on an int axis: write an int",
    ],
    [
      timeline("midi", "ticks", [1, 2]),
      "length [1, 2] of 'midi' is a fraction on an int axis: write an int",
    ],
    [
      timeline("take", "seconds", 9007199254740993n),
      "length 9007199254740993 of 'take' is an int on a float axis: write a float",
    ],
    [
      timeline("take", "seconds", new JsonFloat(2), { number_type: "fraction" }),
      "length 2.0 of 'take' is a float on a fraction axis: write [2, 1]",
    ],
    [
      timeline("score", "quarters", [2, 1], { number_type: "float" }),
      "length [2, 1] of 'score' is a fraction on a float axis: write 2.0",
    ],
    [
      timeline("score", "quarters", [8, 1], { offset: 3 }),
      "offset 3 of 'score' is an int on a fraction axis: write [3, 1]",
    ],
  ])("refuses %o", (root, message) => {
    const key = message.split(" ", 1)[0] as string;
    expect(problem(manifest([root]))).toEqual([["timelines", 0, key], message]);
  });

  it.each([
    [
      timeline("score"),
      3,
      "coordinate 3 of 'timestamp_1' is an int on a fraction axis: write [3, 1]",
    ],
    [
      timeline("take", "seconds", new JsonFloat(60)),
      [1, 2],
      "coordinate [1, 2] of 'timestamp_1' is a fraction on a float axis: write 0.5",
    ],
    [
      timeline("midi", "ticks", 480),
      0.5,
      "coordinate 0.5 of 'timestamp_1' is a float on an int axis: write an int",
    ],
  ])(
    "reads a named timestamp's coordinate on its timeline's axis: %o",
    (root, coordinate, message) => {
      const stamp = { id: "timestamp_1", timeline: root.id, coordinate, name: "Entry" };
      expect(problem(manifest([root], { graphical: { timestamps: [stamp] } }))).toEqual([
        ["graphical", "timestamps", 0, "coordinate"],
        message,
      ]);
    },
  );

  it("reads a named timestamp on a child on the child's axis", () => {
    const child = timeline("verse", "seconds", new JsonFloat(4), { offset: new JsonFloat(1) });
    const root = timeline("take", "seconds", new JsonFloat(60), { children: [child] });
    const stamp = { id: "timestamp_1", timeline: "verse", coordinate: 2, name: "x" };
    validate(manifest([root], { graphical: { timestamps: [stamp] } }));
    const fraction = { ...stamp, coordinate: [2, 1] };
    expect(problem(manifest([root], { graphical: { timestamps: [fraction] } }))).toEqual([
      ["graphical", "timestamps", 0, "coordinate"],
      "coordinate [2, 1] of 'timestamp_1' is a fraction on a float axis: write 2.0",
    ]);
  });

  it.each(["seconds", "quarters"])("reads a %s child's offset on its parent's axis", (unit) => {
    const child = timeline("take", unit, unit === "seconds" ? 4.5 : [4, 1], { offset: [1, 2] });
    expect(
      problem(manifest([timeline("recording", "seconds", 60.5, { children: [child] })])),
    ).toEqual([
      ["timelines", 0, "children", 0, "offset"],
      "offset [1, 2] of 'take' is a fraction on a float axis: write 0.5",
    ]);
  });

  it.each([
    ["regions", { id: "intro", start: 1, end: [2, 1] }, "start"],
    ["regions", { id: "intro", start: [1, 1], end: 2 }, "end"],
    [
      "flow_control",
      { id: "fine", type: "flow_marker", manifestation: "fine", coordinate: 4 },
      "coordinate",
    ],
    [
      "flow_control",
      { id: "segno", type: "jump_to", manifestation: "segno", coordinate: 4 },
      "coordinate",
    ],
    [
      "flow_control",
      { id: "back", type: "jump_from", manifestation: "da_capo", coordinate: 4 },
      "coordinate",
    ],
  ] as const)("checks every own-axis value: %s %o", (member, entry, key) => {
    const root = timeline("score", "quarters", [8, 1], { [member]: [entry] });
    const path = ["timelines", 0, member, 0, key];
    const value = (entry as JsonObject)[key];
    expect(problem(manifest([root]))).toEqual([
      path,
      `${key} ${value} of '${entry.id}' is an int on a fraction axis: write [${value}, 1]`,
    ]);
  });

  it.each([
    timeline("midi", "ticks", 8),
    timeline("midi", "ticks", new JsonFloat(8)),
    timeline("take", "seconds", 8),
    timeline("take", "seconds", 0.5),
    timeline("take", "seconds", 9007199254740992n),
    timeline("take", "seconds", 10n ** 20n),
    timeline("score"),
    timeline("score", "quarters", null),
    timeline("take", "seconds", 2.5, { offset: -1700000000.25 }),
    timeline("score", "quarters", [8, 1], { offset: [-3, 2] }),
  ])("accepts %o", (root) => {
    validate(manifest([root]));
  });

  it("raises the first problem", () => {
    const root = timeline("score", "quarters", 8, {
      regions: [{ id: "r", start: 0, end: [1, 1] }],
    });
    expect(problem(manifest([root]))[0]).toEqual(["timelines", 0, "length"]);
  });

  it("reads every value by its declared number type", () => {
    const value: unknown = respellable();
    const text = () => compactJson(value);
    const written = text();
    validate(value);
    expect(unknownKeys(value)).toEqual([]);
    expect(text()).toBe(written);
  });
});

describe("unknown length", () => {
  it.each([
    ["a root", manifest([timeline("score", "quarters", null)])],
    ["a locked root", manifest([timeline("score", "quarters", null, { locked: true })])],
    [
      "a child",
      manifest([
        timeline("score", "quarters", [8, 1], {
          children: [timeline("c", "quarters", null, { offset: [2, 1] })],
        }),
      ]),
    ],
    [
      "a known child of an unknown parent",
      manifest([
        timeline("score", "quarters", null, {
          children: [timeline("c", "quarters", [8, 1], { offset: [2, 1] })],
        }),
      ]),
    ],
    [
      "a group member",
      manifest([timeline("score"), timeline("perf", "seconds", null)], {
        groups: [{ id: "g", members: ["perf", "score"] }],
      }),
    ],
  ])("is no violation on %s", (_name, value) => {
    validate(value);
  });
});

describe("the shared rejection cases", () => {
  it("are stated", () => {
    expect(rejectionFileNames()).toEqual(REJECTIONS);
  });

  it.each(rejectionFileNames())("refuse %s at the stored path", (name) => {
    expectWrittenAsStored(rejectionText(name));
    const testCase = rejectionCase(name);
    // JSON text holds no non-finite number, so a case about the finite rule
    // has one reading: the reader's, with the value in place.
    const readings =
      testCase.code === "finite_number"
        ? [() => timetoshare.validate(testCase.manifest)]
        : [
            () => timetoshare.validate(testCase.manifest),
            () => timetoshare.validate(plain(testCase.manifest)),
            () => parse(compactJson(testCase.manifest)),
          ];
    for (const [index, read] of readings.entries()) {
      if (index === 1 && LOST_BY_JSON_PARSE.has(name)) {
        // JSON.parse reads the offending number as another one, which validates.
        read();
        continue;
      }
      if (testCase.error === "UnsupportedVersionError") {
        expect(testCase.path).toEqual(["timetoshare"]);
        expect(testCase.code).toBeNull();
        expect(read).toThrow(UnsupportedVersionError);
        continue;
      }
      expect(testCase.error).toBeNull();
      try {
        read();
      } catch (error) {
        expect(error).toBeInstanceOf(SchemaValidationError);
        expect((error as SchemaValidationError).path).toEqual(testCase.path);
        expect((error as SchemaValidationError).code).toBe(testCase.code);
        continue;
      }
      throw new Error(`${name} was accepted`);
    }
  });

  it("are read with the non-finite value in place", () => {
    const nan = rejectionCase("nan_offset");
    expect(nan.manifest).toMatchObject({ timelines: [{ children: [{ offset: Number.NaN }] }] });
    expect(nan.path).toEqual(["timelines", 0, "children", 0, "offset"]);
    expect(problem(timetoshare.withBareIds(nan.manifest))).toEqual([
      ["timelines", 0, "children", 0, "offset"],
      "offset of 'take' is not a finite number",
    ]);
    const infinite = rejectionCase("infinite_length");
    expect(infinite.manifest).toMatchObject({
      timelines: [{ length: Number.POSITIVE_INFINITY }],
    });
    expect([infinite.path, infinite.code, infinite.error]).toEqual([
      ["timelines", 0, "length"],
      "finite_number",
      null,
    ]);
    expect(problem(timetoshare.withBareIds(infinite.manifest))).toEqual([
      ["timelines", 0, "length"],
      "length of 'recording' is not a finite number",
    ]);
  });

  it("are read as written where no value is substituted", () => {
    const text = rejectionText("id_empty");
    const testCase = rejectionCase("id_empty");
    expect(compactJson(testCase.manifest)).toBe(
      compactJson((loads(text) as { manifest: Lossless<Json> }).manifest),
    );
    expect([testCase.path, testCase.code, testCase.error, testCase.reason]).toEqual([
      ["timelines", 0, "flow_control", 0, "id"],
      "schema",
      null,
      "An id must not be empty.",
    ]);
  });

  it("covers every schema and semantic rule code", () => {
    const codes = new Set(rejectionFileNames().map((name) => rejectionCase(name).code));
    expect([...codes].filter((code) => code !== null).sort()).toEqual([
      "alignment_anchor",
      "band_order",
      "belief_actor",
      "calendar_date",
      "child_end",
      "child_offset",
      "child_unit",
      "context",
      "conversion_map",
      "dangling_target",
      "display_order",
      "duplicate_id",
      "element_value",
      "finite_number",
      "group_member",
      "groupstamp",
      "iri",
      "manifest_id",
      "match_timestamp",
      "matchstamp",
      "not_a_manifest",
      "order_key",
      "provenance_duplicate",
      "representation",
      "reserved_key",
      "resource_timeline",
      "resource_type",
      "schema",
      "segment_line",
      "timestamp_coordinate",
      "timestamp_timeline",
    ]);
  });
});

describe("the finite-number rule", () => {
  it.each([
    [
      manifest([timeline("take", "seconds", Number.POSITIVE_INFINITY)]),
      ["timelines", 0, "length"],
      "length of 'take' is not a finite number",
    ],
    [
      manifest([
        timeline("score", "quarters", [8, 1], {
          regions: [{ id: "r", start: [0, 1], end: [Number.NaN, 1] }],
        }),
      ]),
      ["timelines", 0, "regions", 0, "end", 0],
      "end of 'r' is not a finite number",
    ],
    [
      manifest([timeline("take")], {
        graphical: { styles: { s: { opacity: Number.NEGATIVE_INFINITY } } },
      }),
      ["graphical", "styles", "s", "opacity"],
      "#/graphical/styles/s/opacity is not a finite number",
    ],
  ])("refuses a non-finite number before any other rule", (value, path, detail) => {
    // A repeated root breaks the identity rules too; the finite rule runs first.
    const roots = value.timelines as JsonObject[];
    roots.push(roots[0] as JsonObject);
    try {
      validate(value);
    } catch (error) {
      const { code, path: at, detail: text } = error as SchemaValidationError;
      expect([code, at, text]).toEqual(["finite_number", path, detail]);
      return;
    }
    throw new Error("value was accepted");
  });
});

describe("unknown keys of one run", () => {
  it("never carry over from an earlier run", () => {
    const refused = manifest([timeline("score", "beats")], { stale: 1 });
    expect(() => unknownKeys(refused)).toThrow(SchemaValidationError);
    expect(unknownKeys(manifest([timeline("score")], { fresh: 1 }))).toEqual([
      { path: [], key: "fresh" },
    ]);
  });
});

describe("errors and paths", () => {
  it("render as JSON pointers", () => {
    try {
      validate(manifest([timeline("score", "beats")]));
    } catch (error) {
      expect((error as SchemaValidationError).path).toEqual(["timelines", 0, "unit"]);
      expect((error as Error).message.startsWith("#/timelines/0/unit: ")).toBe(true);
    }
    expect(jsonPointer([])).toBe("#");
    expect(jsonPointer(["a/b", "c~d", 0])).toBe("#/a~1b/c~0d/0");
  });
});

describe("a checked value", () => {
  it("is typed as the lossless form the reader returns", () => {
    const value: unknown = parseJson(
      '{"timetoshare": "0.2.0", "timelines": [' +
        '{"id": "#midi", "unit": "ticks", "length": 9007199254740993},' +
        '{"id": "#audio", "unit": "seconds", "length": 2.0}]}',
    );
    timetoshare.validate(value);
    // The compiler is the test of the next two lines: a checked value is a
    // LosslessManifest, whose numbers may be bigints and JsonFloats.
    const checked: LosslessManifest = value;
    // @ts-expect-error a lossless number is no plain number, so the value is no Manifest
    const unchecked: Manifest = value;
    expect(unchecked).toBe(checked);
    expect(checked.timelines[0]?.length).toBe(9007199254740993n);
    expect(checked.timelines[1]?.length).toEqual(new JsonFloat(2));
  });
});

describe("integer boundaries", () => {
  it("reads beyond the safe range only with parseJson", () => {
    expect(JSON.parse("9007199254740993")).toBe(9007199254740992);
    expect(parseJson("9007199254740993")).toBe(9007199254740993n);
  });

  it.each([9007199254740993n, 9223372036854775807n])("validates and writes %s exactly", (value) => {
    const document = manifest([timeline("midi", "ticks", value)]);
    validate(document);
    const text = dumps(document);
    expect(text).toContain(`\n    length: ${value}\n`);
    const read = loads(text) as JsonObject;
    expect(((read.timelines as JsonObject[])[0] as JsonObject).length).toBe(value);
  });
});

describe("the graphical object", () => {
  const styled = (declaration: JsonObject) =>
    manifest([timeline("score")], {
      graphical: { rules: [{ select: { element: "timeline" }, set: declaration }] },
    });

  it.each([
    { "stroke-width": 0, rx: 0 },
    { opacity: 0 },
    { opacity: 1 },
    { "font-size": 0.5, "max-width": 1 },
    { "max-width": "none", content: "Score" },
    { "stroke-dasharray": "none" },
    { "stroke-dasharray": "4 2.5" },
  ])("accepts %o", (declaration) => {
    validate(styled(declaration));
  });

  it.each([
    [{ "stroke-width": -1 }, "stroke-width"],
    [{ rx: -0.5 }, "rx"],
    [{ opacity: -0.1 }, "opacity"],
    [{ opacity: 1.1 }, "opacity"],
    [{ "font-size": 0 }, "font-size"],
    [{ "max-width": 0 }, "max-width"],
    [{ content: 5 }, "content"],
    [{ "stroke-dasharray": "4,2" }, "stroke-dasharray"],
  ])("refuses %o at the property", (declaration, member) => {
    expect(problem(styled(declaration))[0]).toEqual(["graphical", "rules", 0, "set", member]);
  });

  it.each([
    { select: { element: "card" }, set: { rx: 5 } },
    { select: { inside: "ancestor" }, set: { opacity: 0.35 } },
    { select: { element: "card" }, set: { shadow: "#B8BEC8" } },
    { select: { element: "frame" }, set: { stroke: "#7F00FF" } },
    { select: { element: "band" }, set: { display: "none" } },
    { select: { inside: "band" }, set: { opacity: 0.5 } },
    { select: { addresses: [{ id: "score", facet: "regions" }] }, set: { display: "inline" } },
    ...["markers", "conversion_maps", "children", "regions", "flow_control"].map((facet) => ({
      select: { element: "band", facet },
      set: { display: "none" },
    })),
  ])("accepts %o", (rule) => {
    validate(manifest([timeline("score")], { graphical: { rules: [rule] } }));
  });

  it("accepts a selector naming every card of a timeline in several groups", () => {
    const card = { id: "t", part: ["card"] };
    const rule = { select: { addresses: [card] }, set: { stroke: "#B8BEC8" } };
    validate(
      manifest([timeline("t"), timeline("u"), timeline("v")], {
        groups: [group("g1", ["t", "u"]), group("g2", ["t", "v"])],
        graphical: { rules: [rule] },
      }),
    );
  });

  it("refuses an empty order entry by the schema", () => {
    const value = manifest([timeline("score")], { graphical: { order: { score: [""] } } });
    expect(problem(value)).toEqual([
      ["graphical", "order", "#score", 0],
      "must NOT have fewer than 1 characters",
    ]);
  });

  it("refuses a repeated band order entry by the schema", () => {
    const value = manifest([timeline("score")], {
      graphical: { order: { score: ["line", "markers", "line"] } },
    });
    expect(problem(value)).toEqual([
      ["graphical", "order", "#score"],
      "must NOT have duplicate items (items ## 2 and 0 are identical)",
    ]);
  });

  it.each([
    [{ class: "regions" }, "class"],
    [{ class: "band" }, "class"],
    [{ element: "group" }, "element"],
    [{ inside: "group" }, "inside"],
    [{ addresses: [] }, "addresses"],
  ])("refuses the older vocabulary %o at the selector's member", (select, member) => {
    const rule = { select, set: { display: "none" } };
    const value = manifest([timeline("score")], { graphical: { rules: [rule] } });
    expect(problem(value)[0]).toEqual(["graphical", "rules", 0, "select", member]);
  });

  it("needs no target on a da capo or a repeat end", () => {
    const origin = (id: string, manifestation: string) => ({
      id,
      type: "jump_from",
      manifestation,
      coordinate: [8, 1],
    });
    const value = manifest([
      timeline("score", "quarters", [8, 1], {
        flow_control: [
          origin("dc", "da_capo"),
          origin("dcf", "da_capo_al_fine"),
          origin("dcc", "da_capo_al_coda"),
          { ...origin("again", "repeat_end"), repeat_count: 2 },
        ],
      }),
    ]);
    validate(value);
    expect(unknownKeys(value)).toEqual([]);
    const missing = manifest([
      timeline("score", "quarters", [8, 1], { flow_control: [origin("ds", "dal_segno")] }),
    ]);
    expect(problem(missing)[0]).toEqual(["timelines", 0, "flow_control", 0]);
  });

  it("accepts the defaults of the drawing specification", () => {
    const text = readFileSync(resolve(repositoryRoot, "docs", "drawing.md"), "utf8");
    const section = text.split("\n## 4. Defaults\n", 2)[1] as string;
    const block = (section.split("```json\n", 2)[1] as string).split("\n```", 1)[0] as string;
    const defaults = parseJson(block) as JsonObject;
    expect(Object.keys(defaults.styles as JsonObject).length).toBe(3);
    expect((defaults.rules as unknown[]).length).toBe(31);
    validate({ ...SMALLEST, graphical: defaults });
  });

  it("leaves names unrestricted", () => {
    validate(manifest([timeline("score", "quarters", [8, 1], { name: "tab\there\nnewline" })]));
  });
});

describe("the MatchStamp and resource rules", () => {
  const MESSAGES: Readonly<Record<string, string>> = {
    alignment_anchor_timestamp_unknown: "'timestamp_99' names no timestamp of this manifest",
    alignment_anchor_timestamp_not_match: "'timestamp_2' is no match timestamp",
    alignment_anchor_one_timeline: "the timestamps of 'anchor_2' both lie on the timeline 'score'",
    groupstamp_match_timestamp: "'timestamp_1' is both a match timestamp and a groupstamp",
    match_timestamp_in_no_matchstamp: "the match timestamp 'timestamp_11' belongs to no MatchStamp",
    match_timestamp_coordinate_repeated:
      "'timestamp_11' lies on the coordinate of the match timestamp 'timestamp_1'",
    matchstamp_not_connected: "the alignment anchors of 'matchstamp_1' are not one connected set",
    alignment_anchor_id_repeated:
      "'anchor_1' is not unique in the manifest, first at #/graphical/matchstamps/0/alignment_anchors/0/id",
    resource_timeline_unknown: "'take_3' names no timeline of this manifest",
    resource_match_claim_twice:
      "a manifest names at most one resource of the type MatchClaim; 'resource_1' is one",
    resource_projection_twice:
      "a manifest names at most one resource of the type Projection; 'resource_2' is one",
  };

  it.each(Object.keys(MESSAGES).sort())("pin the message of %s", (name) => {
    const testCase = rejectionCase(name);
    let message: string | undefined;
    try {
      timetoshare.validate(testCase.manifest);
    } catch (error) {
      message = (error as timetoshare.SchemaValidationError).detail;
    }
    expect(message).toBe(MESSAGES[name]);
  });

  it("report every problem", () => {
    const value = plain(rejectionCase("matchstamp_not_connected").manifest) as JsonObject;
    const graphical = value.graphical as JsonObject;
    (graphical.timestamps as JsonObject[]).push({
      coordinate: [6, 1],
      display: ["cross_section"],
      groupstamp: true,
      id: "#timestamp_12",
      matchstamp: true,
      timeline: "#score",
    });
    const [first] = graphical.matchstamps as JsonObject[];
    const [anchor] = (first as JsonObject).alignment_anchors as JsonObject[];
    (anchor as JsonObject).timestamps = ["#timestamp_7", "#timestamp_8"];
    const anchors = ["graphical", "matchstamps", 0, "alignment_anchors"];
    expect(
      timetoshare.identityProblems(value).map((problem) => [problem.code, problem.path]),
    ).toEqual([
      ["alignment_anchor", [...anchors, 0, "timestamps", 0]],
      ["alignment_anchor", [...anchors, 0, "timestamps", 1]],
      ["matchstamp", anchors],
      ["match_timestamp", ["graphical", "timestamps", 1]],
      ["match_timestamp", ["graphical", "timestamps", 4]],
      ["groupstamp", ["graphical", "timestamps", 10, "groupstamp"]],
      ["match_timestamp", ["graphical", "timestamps", 10]],
      ["match_timestamp", ["graphical", "timestamps", 10]],
    ]);
  });
});

describe("the MatchStamps alone", () => {
  /** The rejection cases whose fault lies in the named MatchStamps. */
  const MATCHSTAMP_CASES = [
    "alignment_anchor_display_unknown",
    "alignment_anchor_id_repeated",
    "alignment_anchor_one_timeline",
    "alignment_anchor_timestamp_not_match",
    "alignment_anchor_timestamp_unknown",
    "groupstamp_match_timestamp",
    "match_timestamp_coordinate_repeated",
    "match_timestamp_in_no_matchstamp",
    "matchstamp_claims_repeated",
    "matchstamp_not_connected",
  ];

  /** The code, path and message `validate` throws for `value`. */
  function thrown(value: unknown): [string, readonly (string | number)[], string] {
    try {
      timetoshare.validate(value);
    } catch (error) {
      const problem = error as SchemaValidationError;
      return [problem.code, problem.path, problem.detail];
    }
    throw new Error("the value is valid");
  }

  it.each(MATCHSTAMP_CASES)("give the first problem of validate for %s", (name) => {
    const testCase = rejectionCase(name);
    const [first] = timetoshare.matchstampProblems(testCase.manifest as JsonObject);
    expect(first && [first.code, first.path, first.detail]).toEqual(thrown(testCase.manifest));
    expect(first?.path).toEqual(testCase.path);
  });

  it("pass every other case and every fixture", () => {
    const others = rejectionFileNames().filter(
      (name) =>
        !MATCHSTAMP_CASES.includes(name) &&
        timetoshare.matchstampProblems(rejectionCase(name).manifest as JsonObject).length > 0,
    );
    expect(others).toEqual([]);
    for (const file of fixtureFiles()) {
      expect(timetoshare.matchstampProblems(loads(fixtureText(file)) as JsonObject)).toEqual([]);
    }
  });

  it("report a malformed match timestamp by the schema", () => {
    const value = plain(rejectionCase("matchstamp_not_connected").manifest) as JsonObject;
    const timestamps = (value.graphical as JsonObject).timestamps as JsonObject[];
    delete (timestamps[1] as JsonObject).timeline;
    expect(
      timetoshare.matchstampProblems(value).map((problem) => [problem.code, problem.path]),
    ).toEqual([["schema", ["graphical", "timestamps", 1]]]);
  });

  it.each([
    [
      "coordinate",
      ["graphical", "timestamps", 1, "coordinate"],
      "coordinate of 'timestamp_1' is not a finite number",
    ],
    [
      "match_claims",
      ["graphical", "matchstamps", 0, "match_claims", 2],
      "match_claims of 'matchstamp_1' is not a finite number",
    ],
  ])("refuse a non-finite %s as validate does", (member, path, message) => {
    const value = plain(rejectionCase("matchstamp_not_connected").manifest) as JsonObject;
    const graphical = value.graphical as JsonObject;
    if (member === "coordinate") {
      ((graphical.timestamps as JsonObject[])[1] as JsonObject).coordinate =
        Number.POSITIVE_INFINITY;
    } else {
      const [matchstamp] = graphical.matchstamps as JsonObject[];
      ((matchstamp as JsonObject).match_claims as unknown[]).push(Number.POSITIVE_INFINITY);
    }
    const expected = ["finite_number", path, message];
    expect(
      timetoshare
        .matchstampProblems(value)
        .map((problem) => [problem.code, problem.path, problem.detail]),
    ).toEqual([expected]);
    expect(thrown(value)).toEqual(expected);
  });

  it("pass over a timestamp that is no object", () => {
    const value = plain(loads(fixtureText("bundles/bundle_matchstamps"))) as JsonObject;
    ((value.graphical as JsonObject).timestamps as unknown[]).push(null);
    expect(timetoshare.matchstampProblems(value)).toEqual([]);
  });
});
