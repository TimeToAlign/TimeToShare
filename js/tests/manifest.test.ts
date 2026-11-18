import { describe, expect, it } from "vitest";
import { complete, minimal } from "../src/defaults.js";
import type { JsonObject } from "../src/json/value.js";
import {
  isJsonFloat,
  isJsonObject,
  type Json,
  JsonFloat,
  type Lossless,
} from "../src/json/value.js";
import { canonicalOrder } from "../src/manifest/order.js";
import { JsonSyntaxError } from "../src/serialization/errors.js";
import { parseJson } from "../src/serialization/json.js";
import { loads } from "../src/serialization/read.js";
import { compactJson } from "../src/serialization/text.js";
import { dumps } from "../src/serialization/write.js";
import { parse, validate } from "../src/validate.js";
import {
  bundle,
  expectWrittenAsStored,
  fixtureFiles,
  fixtureText,
  manifest,
  rejectionFileNames,
  rejectionText,
  respellable,
  respelled,
  timeline,
  warningFileNames,
  warningText,
} from "./fixtures.js";
import { PYTHON_REPR_SPELLINGS } from "./python-repr.js";

function storedFiles(): [string, string][] {
  return [
    ...fixtureFiles().map((file): [string, string] => [file, fixtureText(file)]),
    ...rejectionFileNames().map((file): [string, string] => [
      `rejections/${file}`,
      rejectionText(file),
    ]),
    ...warningFileNames().map((file): [string, string] => [`warnings/${file}`, warningText(file)]),
  ];
}

describe("the writers", () => {
  it.each(storedFiles())("write %s as it is stored", (_name, text) => {
    expectWrittenAsStored(text);
  });

  it.each(storedFiles())("write %s alike from any order", (name, text) => {
    // A rejection or warning case holds its manifest under `manifest`, which
    // the canonical order does not reach, so only its keys are reversed.
    const value = loads(text);
    const reversed = reverse(value, false, !/^(rejections|warnings)\//.test(name));
    for (const serialization of ["yaml", "json", "jcs"] as const) {
      const written = (given: unknown) => {
        try {
          return dumps(given, { serialization });
        } catch (error) {
          return (error as Error).constructor.name;
        }
      };
      expect(written(reversed), serialization).toBe(written(value));
    }
  });

  it("spell 2000 doubles as Python's repr, with a fractional digit in every mantissa", () => {
    // A deterministic xorshift64 sequence; `python-repr.ts` holds Python's
    // spellings of the same doubles, in the same order.
    let state = 0x9e3779b97f4a7c15n;
    const view = new DataView(new ArrayBuffer(8));
    const values: number[] = [];
    while (values.length < 2000) {
      state ^= (state << 13n) & 0xffffffffffffffffn;
      state ^= state >> 7n;
      state ^= (state << 17n) & 0xffffffffffffffffn;
      // Odd draws are raw bit patterns (every exponent, subnormals included);
      // even draws scatter around the switch between fixed and exponent notation.
      // The power is built from a string, which ECMAScript rounds correctly; `10 **` need not.
      view.setFloat64(
        0,
        (Number(state >> 11n) / 2 ** 53) * Number(`1e${Number(state % 44n) - 22}`),
      );
      if (values.length % 2 === 1) view.setBigUint64(0, state);
      const value = view.getFloat64(0);
      if (Number.isFinite(value)) values.push(value);
    }
    const spelled = values.map((value) => {
      const number = Number.isInteger(value) ? new JsonFloat(value) : value;
      return dumps(number).trimEnd();
    });
    expect(spelled).toEqual(PYTHON_REPR_SPELLINGS);
  });
});

describe("parseJson", () => {
  it("keeps integers exact and floats floats", () => {
    const [half, two, big, minusZeroInteger, minusZero, exponent] = parseJson(
      "[0.5, 2.0, 123456789012345678, -0, -0.0, 1E5]",
    ) as unknown[];
    expect(half).toBe(0.5);
    expect(two).toEqual(new JsonFloat(2));
    expect(big).toBe(123456789012345678n);
    expect(Object.is(minusZeroInteger, 0)).toBe(true);
    expect(minusZero).toBeInstanceOf(JsonFloat);
    expect(Object.is((minusZero as JsonFloat).value, -0)).toBe(true);
    expect(exponent).toEqual(new JsonFloat(100000));
  });

  it("keeps the written order of array-index keys", () => {
    const text = '{\n  "b": 1,\n  "10": 2,\n  "2": 3\n}\n';
    const value = parseJson(text) as JsonObject;
    expect(Object.keys(value)).toEqual(["2", "10", "b"]);
    expect(compactJson(value)).toBe('{"b":1,"10":2,"2":3}');
  });

  it("refuses text that is not one JSON value where it breaks", () => {
    const refusals = [
      "",
      "[1,]",
      "{1: 2}",
      "01",
      "[1] 2",
      "nul",
      "[1, 2",
      '"abc',
      '["\\x"]',
      '{\n  "a": ,\n}',
      '{\n  "a": 1\n  "b": 2\n}',
    ];
    expect(refusals.map(refusal)).toEqual([
      ["unexpected end at line 1, column 1 of the JSON text", 0, 1, 1],
      ["unexpected character at line 1, column 4 of the JSON text", 3, 1, 4],
      ["expected a string key at line 1, column 2 of the JSON text", 1, 1, 2],
      ["unexpected text after the JSON value at line 1, column 2 of the JSON text", 1, 1, 2],
      ["unexpected text after the JSON value at line 1, column 5 of the JSON text", 4, 1, 5],
      ["unexpected character at line 1, column 1 of the JSON text", 0, 1, 1],
      ['expected "]" at line 1, column 6 of the JSON text', 5, 1, 6],
      ["unterminated string at line 1, column 5 of the JSON text", 4, 1, 5],
      ["malformed string at line 1, column 3 of the JSON text", 2, 1, 3],
      ["unexpected character at line 2, column 8 of the JSON text", 9, 2, 8],
      ['expected "}" at line 3, column 3 of the JSON text', 13, 3, 3],
    ]);
    expect(() => parseJson("[1e400]")).toThrow(
      new RangeError("1e400 rounds to an infinity at line 1, column 2 of the JSON text"),
    );
  });

  it("refuses a repeated key and a lone surrogate where they stand", () => {
    const refusals = [
      '{"a": 1, "a": 2}',
      '{"a": 1, "\\u0061": 2}',
      '[{}, {"b": {"c": 1}, "b": 2}]',
      '"x\\ud800"',
      '"\\udc00x"',
      '"\\udc00\\ud800"',
      '"\\ud83dA"',
      '{"\\ud800": 1}',
      '["a\uD800"]',
      '["a\uDC00b"]',
      '"\\ud83d\uDE00"',
      '"\uD83D\\ude00"',
    ];
    expect(refusals.map(refusal)).toEqual([
      ['duplicate key "a" at line 1, column 10 of the JSON text', 9, 1, 10],
      ['duplicate key "a" at line 1, column 10 of the JSON text', 9, 1, 10],
      ['duplicate key "b" at line 1, column 22 of the JSON text', 21, 1, 22],
      ["lone surrogate at line 1, column 3 of the JSON text", 2, 1, 3],
      ["lone surrogate at line 1, column 2 of the JSON text", 1, 1, 2],
      ["lone surrogate at line 1, column 2 of the JSON text", 1, 1, 2],
      ["lone surrogate at line 1, column 2 of the JSON text", 1, 1, 2],
      ["lone surrogate at line 1, column 3 of the JSON text", 2, 1, 3],
      ["lone surrogate at line 1, column 4 of the JSON text", 3, 1, 4],
      ["lone surrogate at line 1, column 4 of the JSON text", 3, 1, 4],
      ["lone surrogate at line 1, column 2 of the JSON text", 1, 1, 2],
      ["lone surrogate at line 1, column 2 of the JSON text", 1, 1, 2],
    ]);
  });

  it("reads a pair of surrogate escapes as one character and removes one byte order mark", () => {
    expect(parseJson('"\\ud83d\\ude00"')).toBe("\u{1F600}");
    expect(parseJson('"\uD83D\uDE00"')).toBe("\u{1F600}");
    expect(parseJson('﻿{"a": "﻿"}')).toEqual({ a: "﻿" });
    expect(refusal('﻿﻿{"a": 1}')).toEqual([
      "unexpected character at line 1, column 1 of the JSON text",
      0,
      1,
      1,
    ]);
  });
});

/** The message, offset, line and column of the `JsonSyntaxError` reading a text throws. */
function refusal(text: string): [string, number, number, number] | null {
  try {
    parseJson(text);
    return null;
  } catch (error) {
    if (!(error instanceof JsonSyntaxError)) throw error;
    expect(error).toBeInstanceOf(SyntaxError);
    expect(error.name).toBe("JsonSyntaxError");
    return [error.message, error.offset, error.line, error.column];
  }
}

describe("canonical order", () => {
  it("sorts every object by key, array-index keys included", () => {
    const value = parseJson(
      '{"b": 1, "\\ud83d\\ude00": 2, "\\ufb00": 3, "A": {"z": 0, "10": 1, "2": 2}}',
    );
    expect(dumps(value)).toBe(
      ["A:", '  "10": 1', '  "2": 2', "  z: 0", "b: 1", '"\u{FB00}": 3', '"\u{1F600}": 2', ""].join(
        "\n",
      ),
    );
    expect(dumps(value, { serialization: "jcs" })).toBe(
      '{"A":{"10":1,"2":2,"z":0},"b":1,"\u{1F600}":2,"\u{FB00}":3}',
    );
  });

  it("copies, and leaves a value that is no manifest unchanged", () => {
    const value = manifest([timeline("b"), timeline("a")]);
    const given = compactJson(value as Lossless<Json>);
    const ordered = canonicalOrder(value);
    expect((ordered.timelines as JsonObject[]).map((root) => root.id)).toEqual(["a", "b"]);
    expect(compactJson(value as Lossless<Json>)).toBe(given);
    const other = parseJson('{"b": [3, 1], "timeline": {"regions": [{"id": "z"}, {"id": "a"}]}}');
    expect(compactJson(canonicalOrder(other))).toBe(
      '{"b":[3,1],"timeline":{"regions":[{"id":"z"},{"id":"a"}]}}',
    );
  });

  it("refuses a collection it cannot order", () => {
    const value = { timelines: [{ id: "t", regions: [{ id: "r" }, { id: "s" }] }] };
    expect(() => dumps(value)).toThrow(TypeError);
    const members = { timelines: [], groups: [{ id: "g", members: ["a", 5] }] };
    expect(() => canonicalOrder(members)).toThrow(TypeError);
  });

  it("resolves every tie", () => {
    const result = canonicalOrder(tiedManifest());
    validate(result);
    const root = (result.timelines as unknown as JsonObject[])[0] as JsonObject;
    const ids = (entries: unknown) => (entries as JsonObject[]).map((entry) => entry.id);
    expect(ids(root.children)).toEqual(["b", "a", "m", "z"]);
    expect(ids((root.children as JsonObject[])[3]?.children)).toEqual(["x", "y"]);
    expect(ids(root.conversion_maps)).toEqual(["B", "B2", "a2", "\u{FB00}", "\u{1F600}"]);
    expect(ids(root.regions)).toEqual(["rd", "rc", "ra", "rb"]);
    expect(ids(root.flow_control)).toEqual([
      "je",
      "kz",
      "starting",
      "Coda",
      "\u{E9}",
      "\u{FB00}!",
      "\u{1F600}!",
      "jd",
      "jj",
      "js",
      "ka",
      "kb",
    ]);
    expect(ids(result.measure_maps)).toEqual(["ma", "mb", "m\u{FB00}"]);
  });

  it("compares bare values by exact value", () => {
    const take = timeline("take", "seconds", 10.5, {
      children: [
        timeline("late", "seconds", 1.5, { offset: 2 }),
        timeline("tie-b", "seconds", 1.5, { offset: 0.625 }),
        timeline("tie-a", "seconds", 1.5, { offset: 0.625 }),
        timeline("early", "seconds", 1.5, { offset: new JsonFloat(0) }),
      ],
      regions: [
        { id: "r2", start: 1, end: 2.5 },
        { id: "r1", start: new JsonFloat(1), end: 2 },
      ],
    });
    const result = (canonicalOrder(manifest([take])).timelines as JsonObject[])[0] as JsonObject;
    const ids = (entries: unknown) => (entries as JsonObject[]).map((entry) => entry.id);
    expect(ids(result.children)).toEqual(["early", "tie-a", "tie-b", "late"]);
    expect(ids(result.regions)).toEqual(["r1", "r2"]);
    const mixed = canonicalOrder({
      timelines: [
        {
          id: "q",
          children: [
            { id: "c", offset: [5, 8] },
            { id: "b", offset: 0.625 },
            { id: "a", offset: [2, 1] },
          ],
        },
      ],
    });
    expect(ids(mixed.timelines[0]?.children)).toEqual(["b", "c", "a"]);
  });

  it("orders roots, groups and members, and keeps display orders", () => {
    const value = bundle();
    (value.timelines as JsonObject[]).reverse();
    const groups = value.groups as JsonObject[];
    groups.reverse();
    for (const group of groups) (group.members as string[]).reverse();
    (value.graphical as JsonObject).order = {
      group_2: ["excerpt", "page"],
      group_1: ["performance", "score"],
    };
    const given = compactJson(value as Lossless<Json>);
    const result = canonicalOrder(value);
    expect(compactJson(value as Lossless<Json>)).toBe(given);
    expect((result.timelines as JsonObject[]).map((root) => root.id)).toEqual([
      "annotations",
      "page",
      "performance",
      "recording",
      "score",
    ]);
    expect((result.groups as JsonObject[]).map((group) => group.id)).toEqual([
      "group_1",
      "group_2",
    ]);
    expect((result.groups as JsonObject[]).map((group) => group.members)).toEqual([
      ["performance", "score"],
      ["excerpt", "page"],
    ]);
    expect((result.graphical as JsonObject).order).toEqual({
      group_2: ["excerpt", "page"],
      group_1: ["performance", "score"],
    });
    validate(result);
  });

  it("orders named timestamps by timeline, coordinate and id", () => {
    const value = manifest([timeline("a"), timeline("b")], {
      graphical: {
        timestamps: [
          stamp("timestamp_4", "b", [1, 1]),
          stamp("timestamp_3", "a", [3, 2]),
          stamp("timestamp_2", "a", [3, 2]),
          stamp("timestamp_1", "a", [5, 1]),
        ],
      },
    });
    const given = compactJson(value as Lossless<Json>);
    const result = canonicalOrder(value);
    expect(compactJson(value as Lossless<Json>)).toBe(given);
    const timestamps = (result.graphical as JsonObject).timestamps as JsonObject[];
    expect(timestamps.map((entry) => entry.id)).toEqual([
      "timestamp_2",
      "timestamp_3",
      "timestamp_1",
      "timestamp_4",
    ]);
    validate(result);
  });

  it("puts the display of a named timestamp in canonical order", () => {
    const displays = [
      ["cross_section", "coordinate", "id", "name", "wedge"],
      ["zeta", "alpha", "wedge"],
      [2, "name", 1, "zeta", "wedge"],
    ];
    const value = manifest([timeline("a")], {
      graphical: {
        timestamps: displays.map((display, index) => ({
          ...stamp(`timestamp_${index + 1}`, "a", [index + 1, 1]),
          display,
        })),
      },
    });
    const given = compactJson(value as Lossless<Json>);
    const result = canonicalOrder(value);
    expect(compactJson(value as Lossless<Json>)).toBe(given);
    const timestamps = (result.graphical as JsonObject).timestamps as JsonObject[];
    expect(timestamps.map((entry) => entry.display)).toEqual([
      ["wedge", "name", "id", "coordinate", "cross_section"],
      ["wedge", "alpha", "zeta"],
      ["wedge", "name", "zeta", 2, 1],
    ]);
    validate({ ...result, graphical: { timestamps: timestamps.slice(0, 1) } });
  });

  it("orders members by code point", () => {
    const value = { timelines: [], groups: [{ id: "g", members: ["\u{1F600}", "\u{FB00}", "b"] }] };
    expect(canonicalOrder(value).groups[0]?.members).toEqual(["b", "\u{FB00}", "\u{1F600}"]);
  });
});

/** A manifest with ties at every key level, own-axis values in mixed forms. */
function tiedManifest(): JsonObject {
  const regions: [string, unknown, unknown][] = [
    ["rb", [2, 1], [6, 1]],
    ["ra", [2, 1], [6, 1]],
    ["rc", [2, 1], [4, 1]],
    ["rd", [5, 8], [2, 3]],
  ];
  const at = (offset: unknown) => ({ offset });
  return manifest(
    [
      timeline("piece", "quarters", [16, 1], {
        children: [
          timeline("z", "quarters", [8, 1], {
            ...at([1, 1]),
            children: [
              timeline("y", "quarters", [2, 1], at([1, 1])),
              timeline("x", "quarters", [2, 1], at([0, 1])),
            ],
          }),
          timeline("m", "quarters", [8, 1], at([1, 1])),
          timeline("b", "quarters", [8, 1], at([5, 8])),
          timeline("a", "quarters", [8, 1], at([2, 3])),
        ],
        conversion_maps: ["\u{1F600}", "\u{FB00}", "B2", "a2", "B"].map((id) => ({
          type: "LinearMap",
          id,
          source_unit: "quarters",
          target_unit: null,
          offset: [1, 2],
        })),
        regions: regions.map(([id, start, end]) => ({ id, start, end })),
        flow_control: [
          ...(
            [
              ["kb", [12, 1]],
              ["ka", [12, 1]],
              ["kz", [5, 8]],
            ] as const
          ).map(([id, coordinate]) => ({
            id,
            type: "flow_marker",
            manifestation: "fine",
            coordinate,
          })),
          {
            id: "jj",
            type: "jump_from",
            manifestation: "dal_segno",
            coordinate: [8, 1],
            target: "Coda",
          },
          ...(
            [
              ["jd", [8, 1]],
              ["js", [8, 1]],
              ["je", [5, 8]],
            ] as const
          ).map(([id, coordinate]) => ({
            id,
            type: "jump_from",
            manifestation: "da_capo",
            coordinate,
          })),
          ...(
            [
              ["\u{1F600}!", [2, 1]],
              ["\u{FB00}!", [2, 1]],
              ["\u{E9}", [2, 1]],
              ["Coda", [2, 1]],
              ["starting", [5, 8]],
            ] as const
          ).map(([id, coordinate]) => ({
            id,
            type: "jump_to",
            manifestation: "segno",
            coordinate,
          })),
        ],
      }),
    ],
    {
      measure_maps: ["m\u{FB00}", "mb", "ma"].map((id) => ({
        id,
        rows: [{ count: 1, qstamp: [0, 1], actual_length: [4, 1] }],
      })),
    },
  );
}

/** A named timestamp `id` on `line` at `coordinate`, named `x`. */
function stamp(id: string, line: string, coordinate: unknown): JsonObject {
  return { id, timeline: line, coordinate, name: "x" };
}

/**
 * The value with every object's keys reversed, and the items of every array
 * whose order carries no meaning: `timelines`, `groups` and `measure_maps`, a group's
 * `members`, a timeline's `children`, `conversion_maps`, `regions` and
 * `flow_control`, `graphical.timestamps` and a timestamp's `display`.
 */
function reverse(value: unknown, unordered = false, arrays = true): Lossless<Json> {
  if (Array.isArray(value)) {
    const items = value.map((item) => reverse(item, false, arrays));
    return unordered ? items.reverse() : items;
  }
  if (isJsonObject(value)) {
    const members = !arrays
      ? []
      : "timelines" in value
        ? ["timelines", "groups", "measure_maps", "schemes"]
        : "timestamps" in value && "statements" in value
          ? ["timestamps"]
          : "timeline" in value && "display" in value
            ? ["display"]
            : "unit" in value && "length" in value
              ? ["children", "conversion_maps", "regions", "flow_control"]
              : "members" in value && "id" in value
                ? ["members"]
                : [];
    return Object.fromEntries(
      Object.keys(value)
        .reverse()
        .map((member) => [member, reverse(value[member], members.includes(member), arrays)]),
    ) as Lossless<Json>;
  }
  return value as Lossless<Json>;
}

describe("canonical spelling", () => {
  it("is what readers give and writers write", () => {
    const value = respellable();
    const twin = respelled();
    const written = compactJson(value);
    expect(written).not.toBe(compactJson(twin));
    expect(compactJson(canonicalOrder(twin))).toBe(compactJson(twin));
    for (const convert of [complete, minimal, canonicalOrder]) {
      expect(compactJson(convert(value)), convert.name).toBe(compactJson(convert(twin)));
    }
    expect(dumps(value)).toBe(dumps(twin));
    expect(compactJson(value)).toBe(written);
  });

  it("spells a named timestamp on the axis of the one timeline it names", () => {
    const value = manifest(
      [
        timeline("score"),
        timeline("take", "seconds", new JsonFloat(60)),
        timeline("twice", "seconds", 1.5),
        timeline("twice", "seconds", 2.5),
      ],
      {
        graphical: {
          timestamps: [
            stamp("timestamp_1", "score", [new JsonFloat(6), 2]),
            stamp("timestamp_2", "take", 2),
            stamp("timestamp_3", "ghost", 2),
            stamp("timestamp_4", "twice", 1),
          ],
        },
      },
    );
    for (const convert of [complete, minimal, canonicalOrder]) {
      const timestamps = (convert(value).graphical as JsonObject).timestamps as JsonObject[];
      const coordinates = Object.fromEntries(
        timestamps
          .map((entry) => [entry.id as string, entry.coordinate] as const)
          .sort(([a], [b]) => (a < b ? -1 : 1)),
      );
      expect(compactJson(coordinates), convert.name).toBe(
        '{"timestamp_1":[3,1],"timestamp_2":2.0,"timestamp_3":2,"timestamp_4":1}',
      );
    }
  });

  it("respells by the axis each value lies on, and writes the rest as given", () => {
    const value = manifest([
      timeline("a_int", "samples", new JsonFloat(4), {
        offset: new JsonFloat(-0),
        children: [timeline("child", "samples", new JsonFloat(1e20), { offset: 2.5 })],
      }),
      timeline("b_float", "seconds", 2, {
        offset: 9007199254740993n,
        regions: [{ id: "r", start: 0, end: 9007199254740992n }],
        flow_control: [{ id: "f", type: "flow_marker", manifestation: "fine", coordinate: -0 }],
      }),
      timeline("c_fraction", "quarters", [new JsonFloat(6), 4], {
        children: [
          timeline("float_child", "quarters", [4, 8], { number_type: "float", offset: [2, 4] }),
          timeline("int_child", "quarters", 3, { number_type: "int", offset: 2 }),
        ],
        regions: [{ id: "q", start: [0, 5], end: [6, 4] }],
      }),
      timeline("d_unknown_unit", "furlongs", new JsonFloat(2), {
        number_type: "int",
        children: [timeline("known", "quarters", [2, 4], { offset: [2, 4] })],
      }),
      timeline("e_no_unit", "quarters", new JsonFloat(2)),
      timeline("f_type", "seconds", 2, { number_type: "decimal" }),
      timeline("g_type_null", "seconds", 2, { number_type: null }),
      timeline("h_denominator", "quarters", [3, -2]),
    ]);
    delete ((value.timelines as JsonObject[])[4] as JsonObject).unit;
    const [aInt, bFloat, cFraction, dUnknown, eNoUnit, fType, gNull, hDenominator] = canonicalOrder(
      value,
    ).timelines as JsonObject[];
    const spelled = (timeline: JsonObject | undefined) => compactJson(timeline);
    expect(spelled(aInt)).toBe(
      '{"id":"a_int","unit":"samples","length":4,"offset":0,"children":' +
        '[{"id":"child","unit":"samples","length":100000000000000000000,"offset":2.5}]}',
    );
    expect(spelled(bFloat)).toBe(
      '{"id":"b_float","unit":"seconds","length":2.0,"offset":9007199254740993,' +
        '"regions":[{"id":"r","start":0.0,"end":9007199254740992.0}],' +
        '"flow_control":[{"id":"f","type":"flow_marker","manifestation":"fine","coordinate":0.0}]}',
    );
    expect(spelled(cFraction)).toBe(
      '{"id":"c_fraction","unit":"quarters","length":[3,2],"children":' +
        '[{"id":"float_child","unit":"quarters","length":[4,8],"number_type":"float","offset":[1,2]},' +
        '{"id":"int_child","unit":"quarters","length":3,"number_type":"int","offset":2}],' +
        '"regions":[{"id":"q","start":[0,1],"end":[3,2]}]}',
    );
    expect(spelled(dUnknown)).toBe(
      '{"id":"d_unknown_unit","unit":"furlongs","length":2.0,"number_type":"int",' +
        '"children":[{"id":"known","unit":"quarters","length":[1,2],"offset":[2,4]}]}',
    );
    expect(spelled(eNoUnit)).toBe('{"id":"e_no_unit","length":2.0}');
    expect(spelled(fType)).toBe(
      '{"id":"f_type","unit":"seconds","length":2,"number_type":"decimal"}',
    );
    expect(spelled(gNull)).toBe(
      '{"id":"g_type_null","unit":"seconds","length":2,"number_type":null}',
    );
    expect(spelled(hDenominator)).toBe('{"id":"h_denominator","unit":"quarters","length":[3,-2]}');
  });

  it("writes as given an integer on a float axis that no double can hold", () => {
    const huge = 10n ** 400n;
    const digits = huge.toString();
    const value = manifest([
      timeline("take", "seconds", huge, { regions: [{ id: "r", start: 0, end: huge }] }),
    ]);
    const yaml =
      `timelines:\n  -\n    id: take\n    length: ${digits}\n    regions:\n      -\n` +
      `        end: ${digits}\n        id: r\n        start: 0.0\n` +
      '    unit: seconds\ntimetoshare: "0.2.0"\n';
    const json =
      `{\n  "timelines": [\n    {\n      "id": "take",\n      "length": ${digits},\n` +
      `      "regions": [\n        {\n          "end": ${digits},\n` +
      '          "id": "r",\n          "start": 0.0\n        }\n      ],\n' +
      '      "unit": "seconds"\n    }\n  ],\n  "timetoshare": "0.2.0"\n}\n';
    expect(dumps(value)).toBe(yaml);
    expect(dumps(value, { serialization: "json" })).toBe(json);
    expect(dumps(loads(yaml))).toBe(yaml);
    expect(dumps(loads(json), { serialization: "json" })).toBe(json);
    expect(() => dumps(value, { serialization: "jcs" })).toThrow(RangeError);
  });

  it("writes an integral plain number as the integer of its exact value", () => {
    expect(dumps([-0, 1e300, 2 ** 53])).toBe(`- 0\n- ${BigInt(1e300)}\n- 9007199254740992\n`);
    expect(() => dumps([1e300], { serialization: "jcs" })).toThrow(RangeError);
    expect(dumps([-0, 0.5, new JsonFloat(-0)], { serialization: "jcs" })).toBe("[0,0.5,0]");
  });
});

describe("values the writers refuse", () => {
  const all = ["yaml", "json", "jcs"] as const;

  it.each([
    ["a lone surrogate", ["\u{D800}"]],
    ["a key with a lone surrogate", [{ "\u{DFFF}": 1 }]],
    ["NaN", [Number.NaN]],
    ["an infinity", [Number.POSITIVE_INFINITY]],
    ["a plain key of 1025 characters", { ["a".repeat(1025)]: 1 }],
    ["a key quoted to 1025 code units", { [`\t${"a".repeat(1021)}`]: 1 }],
    ["512 characters above U+FFFF", { ["\u{1F600}".repeat(512)]: 1 }],
    ["a nested key of 1025 characters", { outer: { ["a".repeat(1025)]: 1 } }],
  ])("refuses %s in every serialization", (_name, value) => {
    for (const serialization of all) {
      expect(() => dumps(value, { serialization }), serialization).toThrow(RangeError);
    }
  });

  it("writes a key of 1024 code units in every serialization", () => {
    for (const key of ["a".repeat(1024), `\t${"a".repeat(1020)}`, "\u{1F600}".repeat(511)]) {
      for (const serialization of all)
        expect(() => dumps({ [key]: 1 }, { serialization })).not.toThrow();
    }
  });

  it.each([
    ["the integer 2^53", 2n ** 53n],
    ["the integer -2^53", -(2n ** 53n)],
    ["the integer 2^64", 2n ** 64n],
    ["the integral float 2^53", new JsonFloat(2 ** 53)],
    ["the integral float -10^16", new JsonFloat(-1e16)],
    ["the largest double below 10^21", new JsonFloat(1e21 - 2 ** 17)],
  ])("refuses %s in RFC 8785 JSON only", (_name, number) => {
    expect(() => dumps({ a: number }, { serialization: "jcs" })).toThrow(RangeError);
    expect(() => dumps({ a: number })).not.toThrow();
    expect(() => dumps({ a: number }, { serialization: "json" })).not.toThrow();
  });

  it("writes ±(2^53 − 1) and 10^21 in RFC 8785 JSON", () => {
    const safe = 2n ** 53n - 1n;
    expect(dumps([safe, -safe, new JsonFloat(1e21)], { serialization: "jcs" })).toBe(
      "[9007199254740991,-9007199254740991,1e+21]",
    );
  });

  it.each([
    ["undefined", [undefined]],
    ["a function", [() => 1]],
    ["a symbol", [Symbol("x")]],
    ["a date", [new Date(0)]],
    ["a map", [new Map()]],
  ])("refuses %s as no JSON value", (_name, value) => {
    for (const serialization of all) {
      expect(() => dumps(value, { serialization })).toThrow(TypeError);
    }
  });

  it("refuses an unknown serialization", () => {
    for (const serialization of ["toml", "YAML", ""]) {
      expect(() => dumps({}, { serialization: serialization as "yaml" })).toThrow(
        new RangeError(`unknown serialization "${serialization}"`),
      );
    }
  });
});

describe("parse", () => {
  it("reads and validates a manifest without losing a float", () => {
    const value = parse(
      '{"timetoshare": "0.2.0", "timelines": [{"id": "take", "unit": "seconds", "length": 12.0,' +
        ' "children": [{"id": "a", "unit": "seconds", "length": 1.5, "offset": 0.5},' +
        ' {"id": "b", "unit": "seconds", "length": 1.5, "offset": 6.0}]}]}',
    ) as unknown as JsonObject;
    const root = (value.timelines as JsonObject[])[0] as JsonObject;
    const offsets = (root.children as JsonObject[]).map((child) => child.offset);
    expect(offsets).toEqual([0.5, new JsonFloat(6)]);
    expect(isJsonFloat(offsets[1])).toBe(true);
    expect(root.length).toEqual(new JsonFloat(12));
  });
});

describe("JsonFloat", () => {
  it("is a frozen class told apart by instanceof and isJsonFloat", () => {
    const two = new JsonFloat(2);
    expect(Object.isFrozen(two)).toBe(true);
    expect(two instanceof JsonFloat).toBe(true);
    expect(isJsonFloat(two)).toBe(true);
    expect(isJsonFloat(2)).toBe(false);
    expect(isJsonFloat({ value: 2 })).toBe(false);
    expect(isJsonObject(two)).toBe(false);
    expect(isJsonObject({ value: 2 })).toBe(true);
    expect(() => new JsonFloat(Number.NaN)).toThrow(RangeError);
  });
});

function atoms(value: Lossless<Json>, into: Lossless<Json>[] = []): Lossless<Json>[] {
  into.push(value);
  if (Array.isArray(value)) for (const item of value) atoms(item, into);
  else if (isJsonObject(value))
    for (const item of Object.values(value)) atoms(item as Lossless<Json>, into);
  return into;
}

describe("compactJson", () => {
  it("is a fixpoint for every value nested in every fixture", () => {
    let count = 0;
    for (const file of fixtureFiles()) {
      for (const atom of atoms(loads(fixtureText(file)))) {
        const text = compactJson(atom);
        expect(compactJson(parseJson(text))).toBe(text);
        count++;
      }
    }
    expect(count).toBeGreaterThan(0);
  });

  it("keeps every key in its written order and spells numbers as the writers do", () => {
    expect(compactJson(parseJson('{"b": 1, "10": 2.0, "2": [1e-07, 1e16, -0.0, -0]}'))).toBe(
      '{"b":1,"10":2.0,"2":[1.0e-07,1.0e+16,-0.0,0]}',
    );
  });
});
