import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  compactJson,
  dumps,
  JsonFloat,
  JsonSyntaxError,
  loads,
  parseJson,
  parseYaml,
  type Serialization,
  serializationOf,
  YamlSyntaxError,
} from "../src/index.js";
import { repositoryRoot } from "./fixtures.js";

const directory = resolve(repositoryRoot, "fixtures", "serializations");

/** A file of the serialization cases, decoded as UTF-8 with a leading U+FEFF kept. */
function text(path: string): string {
  return readFileSync(resolve(directory, path), "utf8");
}

function names(subdirectory: string): string[] {
  return readdirSync(resolve(directory, subdirectory)).sort();
}

/**
 * A value with every number tagged by its kind, so that values compare kind
 * for kind: an integer equals only an integer, a float only a float, and
 * `-0.0` differs from `0.0`; objects compare by their members.
 */
function tagged(value: unknown): unknown {
  if (typeof value === "bigint") return `integer ${value}`;
  if (value instanceof JsonFloat) return `float ${Object.is(value.value, -0) ? "-0" : value.value}`;
  if (typeof value === "number") {
    return Number.isInteger(value) ? `integer ${BigInt(value)}` : `float ${value}`;
  }
  if (Array.isArray(value)) return value.map(tagged);
  if (typeof value === "object" && value !== null) {
    return Object.fromEntries(
      Object.entries(value).map(([key, member]) => [key, tagged(member)] as const),
    );
  }
  return value;
}

/** The value with every float RFC 8785 JSON spells without `.` or exponent as its integer. */
function asRfc8785Reads(value: unknown): unknown {
  if (value instanceof JsonFloat) {
    const spelled = String(value.value);
    return /[.e]/.test(spelled) ? value : Number(spelled);
  }
  if (Array.isArray(value)) return value.map(asRfc8785Reads);
  if (typeof value === "object" && value !== null) {
    return Object.fromEntries(
      Object.entries(value).map(([key, member]) => [key, asRfc8785Reads(member)] as const),
    );
  }
  return value;
}

const MANIFEST_CASES = new Set([
  "readme_manifest",
  "manifest_canonical_order",
  "manifest_order_by_value",
  "manifest_ties_kept",
  "manifest_display_order",
]);

const JSON_CANONICAL_CASES = new Set([
  "top_level_empty_object",
  "top_level_empty_array",
  "top_level_integer",
  "top_level_float",
  "top_level_null",
  "top_level_true",
  "top_level_quoted_string",
  "top_level_string_yaml_escapes",
]);

describe("the serialization cases", () => {
  const cases = names("cases");

  it("are the thirty-five cases of the case table", () => {
    expect(cases.length).toBe(35);
    for (const name of [...MANIFEST_CASES, ...JSON_CANONICAL_CASES]) expect(cases).toContain(name);
  });

  describe.each(cases)("%s", (name) => {
    const canonical = text(`cases/${name}/canonical.yaml`);
    const pretty = text(`cases/${name}/pretty.json`);
    const rfc8785Path = `cases/${name}/rfc8785.json`;
    const rfc8785 = existsSync(resolve(directory, rfc8785Path)) ? text(rfc8785Path) : null;
    // The value of the case, read from its pretty JSON, which reads to it.
    const value = loads(pretty);

    it("reads canonical.yaml to the value of pretty.json", () => {
      expect(tagged(loads(canonical))).toEqual(tagged(value));
    });

    it("writes the bytes of each file", () => {
      expect(dumps(value)).toBe(canonical);
      expect(dumps(value, { serialization: "yaml" })).toBe(canonical);
      expect(dumps(value, { serialization: "json" })).toBe(pretty);
      if (rfc8785 === null) {
        expect(() => dumps(value, { serialization: "jcs" })).toThrow(RangeError);
      } else {
        expect(dumps(value, { serialization: "jcs" })).toBe(rfc8785);
      }
    });

    it("reads rfc8785.json to the value, its integral floats as integers", () => {
      if (rfc8785 === null) return;
      expect(tagged(loads(rfc8785))).toEqual(tagged(asRfc8785Reads(value)));
    });

    it("gives each text its own bytes when read and written again", () => {
      expect(dumps(loads(pretty), { serialization: "json" })).toBe(pretty);
      if (rfc8785 !== null) expect(dumps(loads(rfc8785), { serialization: "jcs" })).toBe(rfc8785);
      expect(dumps(loads(canonical))).toBe(canonical);
    });

    it("names each file's serialization", () => {
      expect(serializationOf(canonical)).toBe(JSON_CANONICAL_CASES.has(name) ? "json" : "yaml");
      expect(serializationOf(pretty)).toBe("json");
      if (rfc8785 !== null) expect(serializationOf(rfc8785)).toBe("jcs");
    });
  });
});

describe.each([...MANIFEST_CASES])("the manifest case %s", (name) => {
  it("writes the value of rfc8785.json as canonical.yaml, the number types restoring floats", () => {
    const canonical = text(`cases/${name}/canonical.yaml`);
    expect(dumps(loads(text(`cases/${name}/rfc8785.json`)))).toBe(canonical);
  });
});

const EXPECTED = /\.expected\.(yaml|rfc8785\.json)$/;

describe("the readings", () => {
  const readings = names("readings").filter((name) => !EXPECTED.test(name));

  it("are paired with their expected texts, and every expected text with its reading", () => {
    const stems = new Set(readings.map((file) => file.replace(/\.(yaml|json)$/, "")));
    expect(stems.size).toBe(readings.length);
    for (const file of names("readings").filter((name) => EXPECTED.test(name))) {
      expect(stems).toContain(file.replace(EXPECTED, ""));
    }
    for (const stem of stems) expect(names("readings")).toContain(`${stem}.expected.yaml`);
  });

  describe.each(readings)("%s", (file) => {
    const stem = file.replace(/\.(yaml|json)$/, "");
    const reading = text(`readings/${file}`);
    const expected = text(`readings/${stem}.expected.yaml`);
    const rfc8785Path = `readings/${stem}.expected.rfc8785.json`;
    const rfc8785 = existsSync(resolve(directory, rfc8785Path)) ? text(rfc8785Path) : null;

    it("reads to the value of its expected canonical YAML", () => {
      const value = loads(reading);
      expect(dumps(value)).toBe(expected);
      if (rfc8785 !== null) expect(dumps(value, { serialization: "jcs" })).toBe(rfc8785);
    });

    it("has an expected text that gives its own bytes", () => {
      expect(dumps(loads(expected))).toBe(expected);
      if (rfc8785 !== null) {
        expect(dumps(loads(expected), { serialization: "jcs" })).toBe(rfc8785);
      }
    });

    it("names the serializations", () => {
      expect(serializationOf(reading)).toBe(file.endsWith(".json") ? "json" : "yaml");
      if (rfc8785 !== null) expect(serializationOf(rfc8785)).toBe("jcs");
    });
  });
});

type Refusal = typeof JsonSyntaxError | typeof YamlSyntaxError | typeof RangeError;

/**
 * The error reading each refusal throws, as the fixtures README states: a
 * `YamlSyntaxError` for a text read as YAML, a `JsonSyntaxError` for one
 * read as JSON (the three `flow_*` texts meant as YAML among them), a
 * `RangeError` for a JSON number that rounds to an infinity.
 */
const REFUSALS: Readonly<Record<string, Refusal>> = {
  "flow_mapping_unquoted_key.yaml": JsonSyntaxError,
  "flow_sequence_plain.yaml": JsonSyntaxError,
  "flow_sequence_then_comment.yaml": JsonSyntaxError,
  "json_bom_after_value.json": JsonSyntaxError,
  "json_bom_between_tokens.json": JsonSyntaxError,
  "json_comment.json": JsonSyntaxError,
  "json_duplicate_key.json": JsonSyntaxError,
  "json_duplicate_key_escaped.json": JsonSyntaxError,
  "json_duplicate_key_nested.json": JsonSyntaxError,
  "json_float_overflow.json": RangeError,
  "json_float_overflow_above_largest.json": RangeError,
  "json_float_overflow_negative.json": RangeError,
  "json_infinity.json": JsonSyntaxError,
  "json_lone_surrogate_high.json": JsonSyntaxError,
  "json_lone_surrogate_key.json": JsonSyntaxError,
  "json_lone_surrogate_low.json": JsonSyntaxError,
  "json_lone_surrogate_reversed.json": JsonSyntaxError,
  "json_lone_surrogate_then_letter.json": JsonSyntaxError,
  "json_nan.json": JsonSyntaxError,
  "json_negative_infinity.json": JsonSyntaxError,
  "json_single_quotes.json": JsonSyntaxError,
  "json_top_level_float_overflow.json": RangeError,
  "json_trailing_comma.json": JsonSyntaxError,
  "json_two_values.json": JsonSyntaxError,
  "json_u0001_in_string.json": JsonSyntaxError,
  "json_unclosed.json": JsonSyntaxError,
  "yaml_alias.yaml": YamlSyntaxError,
  "yaml_anchor.yaml": YamlSyntaxError,
  "yaml_duplicate_key.yaml": YamlSyntaxError,
  "yaml_duplicate_key_escaped.yaml": YamlSyntaxError,
  "yaml_duplicate_key_flow.yaml": YamlSyntaxError,
  "yaml_duplicate_key_nested.yaml": YamlSyntaxError,
  "yaml_duplicate_key_quoted.yaml": YamlSyntaxError,
  "yaml_float_overflow.yaml": YamlSyntaxError,
  "yaml_float_overflow_above_largest.yaml": YamlSyntaxError,
  "yaml_float_overflow_negative.yaml": YamlSyntaxError,
  "yaml_inf_lower.yaml": YamlSyntaxError,
  "yaml_inf_minus_lower.yaml": YamlSyntaxError,
  "yaml_inf_minus_title.yaml": YamlSyntaxError,
  "yaml_inf_minus_upper.yaml": YamlSyntaxError,
  "yaml_inf_plus_lower.yaml": YamlSyntaxError,
  "yaml_inf_plus_title.yaml": YamlSyntaxError,
  "yaml_inf_plus_upper.yaml": YamlSyntaxError,
  "yaml_inf_title.yaml": YamlSyntaxError,
  "yaml_inf_upper.yaml": YamlSyntaxError,
  "yaml_key_collection.yaml": YamlSyntaxError,
  "yaml_key_empty.yaml": YamlSyntaxError,
  "yaml_key_float.yaml": YamlSyntaxError,
  "yaml_key_integer.yaml": YamlSyntaxError,
  "yaml_key_null.yaml": YamlSyntaxError,
  "yaml_key_tilde.yaml": YamlSyntaxError,
  "yaml_key_true.yaml": YamlSyntaxError,
  "yaml_lone_surrogate_32bit_escape.yaml": YamlSyntaxError,
  "yaml_lone_surrogate_high.yaml": YamlSyntaxError,
  "yaml_lone_surrogate_key.yaml": YamlSyntaxError,
  "yaml_lone_surrogate_low.yaml": YamlSyntaxError,
  "yaml_lone_surrogate_reversed.yaml": YamlSyntaxError,
  "yaml_nan_lower.yaml": YamlSyntaxError,
  "yaml_nan_title.yaml": YamlSyntaxError,
  "yaml_nan_upper.yaml": YamlSyntaxError,
  "yaml_tag_binary.yaml": YamlSyntaxError,
  "yaml_tag_local.yaml": YamlSyntaxError,
  "yaml_tag_omap.yaml": YamlSyntaxError,
  "yaml_tag_set.yaml": YamlSyntaxError,
  "yaml_tag_timestamp.yaml": YamlSyntaxError,
  "yaml_two_documents.yaml": YamlSyntaxError,
  "yaml_unclosed_quote.yaml": YamlSyntaxError,
};

describe("the refusals", () => {
  it("are the files of the refusal table", () => {
    expect(names("refusals")).toEqual(Object.keys(REFUSALS).sort());
  });

  it.for(Object.entries(REFUSALS))("%s is refused", ([file, error]) => {
    const refused = text(`refusals/${file}`);
    const read = error === YamlSyntaxError ? parseYaml : parseJson;
    expect(serializationOf(refused)).toBe(error === YamlSyntaxError ? "yaml" : "json");
    expect(() => loads(refused)).toThrow(error);
    expect(() => read(refused)).toThrow(error);
  });
});

const ALL: readonly Serialization[] = ["yaml", "json", "jcs"];
const JCS: readonly Serialization[] = ["jcs"];

/** The serializations that refuse each writer refusal's value. */
const WRITER_REFUSALS: Readonly<Record<string, readonly Serialization[]>> = {
  "key_1025_plain.json": ALL,
  "key_1025_quoted.json": ALL,
  "key_1025_utf16_units.json": ALL,
  "key_1025_nested.yaml": ALL,
  "integer_2_53.json": JCS,
  "integer_minus_2_53.yaml": JCS,
  "integer_2_64.yaml": JCS,
  "float_2_53.yaml": JCS,
  "float_minus_1e16.yaml": JCS,
  "float_1e20.json": JCS,
  "float_below_1e21.yaml": JCS,
  "order_entry_not_object.yaml": ALL,
  "order_entries_not_objects_without_version.json": ALL,
  "order_member_missing.yaml": ALL,
  "order_member_wrong_type.yaml": ALL,
  "order_id_wrong_type.yaml": ALL,
  "order_timestamp_timeline_not_string.yaml": ALL,
  "order_group_member_not_string.yaml": ALL,
  "order_coordinate_zero_denominator.yaml": ALL,
  "order_coordinate_three_members.yaml": ALL,
  "order_coordinate_boolean.yaml": ALL,
};

describe("the writer refusals", () => {
  it("are the files of the writer refusal table", () => {
    expect(names("refusals-writing")).toEqual(Object.keys(WRITER_REFUSALS).sort());
  });

  it.for(Object.entries(WRITER_REFUSALS))("%s", ([file, refusedIn]) => {
    const given = text(`refusals-writing/${file}`);
    expect(serializationOf(given)).toBe(file.endsWith(".json") ? "json" : "yaml");
    const value = loads(given);
    const error = file.startsWith("order_") ? TypeError : RangeError;
    for (const serialization of ALL) {
      const write = () => dumps(value, { serialization });
      if (refusedIn.includes(serialization)) expect(write, serialization).toThrow(error);
      else expect(write, serialization).not.toThrow();
    }
  });
});

/** The message, offset, line and column of the `YamlSyntaxError` reading a text throws. */
function yamlRefusal(given: string): [string, number, number, number] | null {
  try {
    parseYaml(given);
    return null;
  } catch (error) {
    if (!(error instanceof YamlSyntaxError)) throw error;
    expect(error).toBeInstanceOf(SyntaxError);
    expect(error.name).toBe("YamlSyntaxError");
    return [error.message, error.offset, error.line, error.column];
  }
}

describe("the YAML reader", () => {
  it("reads by the core schema, integers exact, integral floats as JsonFloat", () => {
    const value = loads(
      "a: 0x1F\nb: 0o17\nc: 123456789012345678901234567890\nd: 2.0\ne: -0.0\nf: .5\n" +
        "g: no\nh: 2026-11-17\ni: ~\nj: True\nk: '12'\nl: !!str 1\n",
    );
    expect(tagged(value)).toEqual({
      a: "integer 31",
      b: "integer 15",
      c: "integer 123456789012345678901234567890",
      d: "float 2",
      e: "float -0",
      f: "float 0.5",
      g: "no",
      h: "2026-11-17",
      i: null,
      j: true,
      k: "12",
      l: "1",
    });
    expect(compactJson(loads("b: 1\n'10': 2\na: 3\n'2': 4\n"))).toBe('{"b":1,"10":2,"a":3,"2":4}');
  });

  it("reads an empty text, or one of comments only, as null", () => {
    expect(loads("")).toBeNull();
    expect(loads("# a comment\n\n")).toBeNull();
    expect(loads("\uFEFF")).toBeNull();
  });

  it("refuses each value outside the format where it stands", () => {
    expect(
      [
        "a: 1\nb: &x 2\n",
        "a: 1\nb: *x\n",
        "a: 1\na: 2\n",
        "x:\n  ? [a]\n  : 1\n",
        "1: x\n",
        'x: "\\ud800"\n',
        'x: "a\uD800"\n',
        "x: .inf\n",
        "x: -.Inf\n",
        "x: .nan\n",
        "x: 1e309\n",
        "x: !!binary aGVsbG8=\n",
        "x: !!timestamp 2001-12-14\n",
        "x: !!set {a: null}\n",
        "x: !!omap [{a: 1}]\n",
        "x: !local y\n",
        "a: 1\n---\nb: 2\n",
      ].map(yamlRefusal),
    ).toEqual([
      ["an anchor at line 2, column 7 of the YAML text", 11, 2, 7],
      ["an alias at line 2, column 4 of the YAML text", 8, 2, 4],
      ["DUPLICATE_KEY: Map keys must be unique at line 2, column 1 of the YAML text", 5, 2, 1],
      ["a key that is not a string at line 2, column 5 of the YAML text", 7, 2, 5],
      ["a key that is not a string at line 1, column 1 of the YAML text", 0, 1, 1],
      ["a string holds a lone surrogate at line 1, column 4 of the YAML text", 3, 1, 4],
      ["a string holds a lone surrogate at line 1, column 4 of the YAML text", 3, 1, 4],
      ["the float .inf is not finite at line 1, column 4 of the YAML text", 3, 1, 4],
      ["the float -.Inf is not finite at line 1, column 4 of the YAML text", 3, 1, 4],
      ["the float .nan is not finite at line 1, column 4 of the YAML text", 3, 1, 4],
      ["the float 1e309 is not finite at line 1, column 4 of the YAML text", 3, 1, 4],
      ["a value outside the JSON data model at line 1, column 13 of the YAML text", 12, 1, 13],
      ["a value outside the JSON data model at line 1, column 16 of the YAML text", 15, 1, 16],
      ["a value outside the JSON data model at line 1, column 10 of the YAML text", 9, 1, 10],
      ["a value outside the JSON data model at line 1, column 11 of the YAML text", 10, 1, 11],
      ["TAG_RESOLVE_FAILED: Unresolved tag: !local at line 1, column 4 of the YAML text", 3, 1, 4],
      [
        "MULTIPLE_DOCS: Source contains multiple documents; please use YAML.parseAllDocuments() at line 2, column 1 of the YAML text",
        5,
        2,
        1,
      ],
    ]);
  });

  it("reads a text as YAML whatever its first character, after one byte order mark", () => {
    expect(tagged(parseYaml('\uFEFF{"a": [1, 2.0]}'))).toEqual({ a: ["integer 1", "float 2"] });
    expect(parseYaml("480")).toBe(480);
  });
});

describe("the choice between JSON and YAML", () => {
  it("reads JSON when the first character is { or [, or the text is a JSON scalar", () => {
    expect(serializationOf(" \t\r\n{}")).toBe("json");
    expect(serializationOf('"x y"\n')).toBe("json");
    expect(serializationOf("-0.5e3")).toBe("json");
    expect(serializationOf("-500")).toBe("jcs");
    expect(serializationOf("'480'\n")).toBe("yaml");
    expect(serializationOf('"\\x41"\n')).toBe("yaml");
    expect(serializationOf("-Infinity\n")).toBe("yaml");
    expect(() => loads("{a: 1}")).toThrow(JsonSyntaxError);
    expect(loads('"a": 1\n')).toEqual({ a: 1 });
    expect(loads('"x\u2028y"')).toBe("x\u2028y");
  });

  it("names a text without ever throwing", () => {
    for (const given of ['"\uD800"', "a: \uDC00\n", "[".repeat(100000), "{", "a: [\n", "1e309"]) {
      expect(["json", "yaml", "jcs"]).toContain(serializationOf(given));
    }
    expect(serializationOf('{"a":1}')).toBe("jcs");
    expect(serializationOf('\uFEFF{"a":1}')).toBe("json");
    expect(serializationOf('{"a":2.0}')).toBe("json");
    expect(serializationOf('{"a":9007199254740992}')).toBe("json");
  });
});

describe("canonical order in the writers", () => {
  it.each([
    ["an id that is not a string, alone in its array", { timelines: [{ id: 1 }] }],
    ["a child without offset, alone", { timelines: [{ id: "t", children: [{ id: "c" }] }] }],
    [
      "a group member that is not a string, alone",
      { timelines: [], groups: [{ id: "g", members: [1] }] },
    ],
    [
      "a timestamp without timeline",
      { timelines: [], graphical: { timestamps: [{ id: "x", coordinate: 1 }] } },
    ],
    [
      "a coordinate whose denominator is 0",
      { timelines: [{ id: "t", regions: [{ id: "r", start: 0, end: [1, 0] }] }] },
    ],
  ])("refuses %s as a TypeError", (_name, value) => {
    for (const serialization of ALL) {
      expect(() => dumps(value, { serialization })).toThrow(TypeError);
    }
  });

  it("orders whatever a display holds, and writes as given a member that holds no array", () => {
    const value = {
      timelines: [{ id: "t", children: "x", regions: 7, flow_control: {} }],
      groups: "g",
      graphical: {
        timestamps: [
          { id: "s", timeline: "t", coordinate: 1, display: [null, "b", "name", 1, "a"] },
        ],
      },
    };
    expect(dumps(value, { serialization: "jcs" })).toBe(
      '{"graphical":{"timestamps":[{"coordinate":1,"display":["name","a","b",null,1],"id":"s","timeline":"t"}]},' +
        '"groups":"g","timelines":[{"children":"x","flow_control":{},"id":"t","regions":7}]}',
    );
  });

  it("keeps the order of entries that tie, and of the arrays it does not order", () => {
    const value = {
      timelines: [
        { id: "b", n: 1 },
        { id: "a", n: 2 },
        { id: "b", n: 3 },
      ],
      links: [{ uri: ["z", "a"] }, { uri: [] }],
      graphical: { order: { b: ["z", "a"] }, statements: [{ s: 2 }, { s: 1 }] },
    };
    expect(dumps(value, { serialization: "jcs" })).toBe(
      '{"graphical":{"order":{"b":["z","a"]},"statements":[{"s":2},{"s":1}]},' +
        '"links":[{"uri":["z","a"]},{"uri":[]}],' +
        '"timelines":[{"id":"a","n":2},{"id":"b","n":1},{"id":"b","n":3}]}',
    );
  });
});
