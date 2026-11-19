import { describe, expect, it } from "vitest";
import { complete, minimal } from "../src/defaults.js";
import { canonicalManifest, completeManifest, minimalManifest } from "../src/forms.js";
import type {
  CompleteFlowControlElement,
  CompleteManifest,
  CompleteMeasureRecordMap,
  CompleteTimeline,
  Fraction,
  LosslessManifest,
} from "../src/generated/types.js";
import type { JsonObject } from "../src/json/value.js";
import { type Json, JsonFloat, type Lossless } from "../src/json/value.js";
import { loads } from "../src/serialization/read.js";
import { compactJson } from "../src/serialization/text.js";
import { dumps } from "../src/serialization/write.js";
import { parse } from "../src/validate.js";
import { bundle, fixtureFiles, fixtureText, manifest, timeline, validate } from "./fixtures.js";

const SMALLEST = {
  timetoshare: "0.2.0",
  timelines: [{ id: "piece", unit: "quarters", length: [32, 1] }],
};
const REGION = { id: "r", start: [0, 1], end: [1, 1] };
const REPEAT = { id: "b", type: "jump_from", manifestation: "repeat_end" };
const root = (value: unknown) => ((value as JsonObject).timelines as JsonObject[])[0] as JsonObject;
const ASSERTION = {
  asserted_by: [],
  asserted_on: null,
  method: null,
  service: null,
  based_on: [],
  match: null,
  status: null,
};
const LINK = {
  relation: "pertains_to",
  level: "work",
  records: [{ url: "records/op106.json" }],
  assertion: { method: "manual" },
  parts_relation: "has_part",
  parts: [{ absent: "lost", assertion: { status: "confirmed" } }],
  part_of: [{ parts_relation: "has_part" }],
};

/** A manifest with a scheme and one link on itself, its root and a region. */
function described(): JsonObject {
  return manifest(
    [
      timeline("score", "quarters", [8, 1], {
        links: [LINK],
        regions: [{ ...REGION, links: [LINK] }],
      }),
    ],
    { schemes: [{ id: "opus" }], links: [LINK] },
  );
}

describe("the complete and the minimal form", () => {
  it("completes the smallest file to the literal complete form", () => {
    expect(complete(SMALLEST)).toEqual({
      timetoshare: "0.2.0",
      name: null,
      meta: {},
      groups: [],
      measure_maps: [],
      schemes: [],
      links: [],
      timelines: [
        {
          id: "piece",
          unit: "quarters",
          length: [32, 1],
          name: null,
          number_type: "fraction",
          locked: false,
          is_segment_line: false,
          meta: {},
          children: [],
          conversion_maps: [],
          regions: [],
          flow_control: [],
          links: [],
        },
      ],
    });
    expect(minimal(complete(SMALLEST))).toEqual(SMALLEST);
  });

  it("gives every object exactly its defaults", () => {
    const linear = { type: "LinearMap", id: "s", source_unit: null, target_unit: null };
    const table = {
      type: "TableMap",
      id: "t",
      source_unit: "quarters",
      target_unit: "seconds",
      x_values: [
        [0, 1],
        [4, 1],
      ],
      y_values: [0.5, 2.5],
    };
    const view = {
      type: "MeasureNumberMap",
      id: "bar",
      source_unit: "quarters",
      target_unit: null,
      measure_map: "bars",
    };
    const rows = [{ count: 1, qstamp: [0, 1], actual_length: [4, 1] }];
    const value = complete(
      manifest(
        [
          timeline("score", "quarters", [8, 1], {
            regions: [{ id: "r", start: [0, 1], end: [1, 1] }],
            flow_control: [
              { id: "b", type: "flow_marker", manifestation: "fine", coordinate: [1, 1] },
              { id: "j", type: "jump_from", manifestation: "da_capo", coordinate: [1, 1] },
              { id: "again", type: "jump_from", manifestation: "repeat_end", coordinate: [1, 1] },
              { id: "m", type: "jump_to", manifestation: "segno", coordinate: [0, 1] },
            ],
            conversion_maps: [
              {
                type: "ChainMap",
                id: "chain",
                source_unit: null,
                target_unit: null,
                maps: [linear],
              },
              {
                type: "CombinationMap",
                id: "combo",
                source_unit: null,
                target_unit: null,
                maps: { x: { ...linear, id: "x" }, bar: view },
              },
              {
                type: "PiecewiseMap",
                id: "pieces",
                source_unit: "quarters",
                target_unit: "seconds",
                breaks: [
                  [0, 1],
                  [4, 1],
                ],
                maps: [table],
              },
            ],
          }),
        ],
        {
          groups: [{ id: "g", members: ["score"] }],
          measure_maps: [{ id: "bars", rows }],
          graphical: {},
        },
      ),
    );
    const done = root(value);
    expect((done.regions as JsonObject[])[0]).toEqual({
      id: "r",
      start: [0, 1],
      end: [1, 1],
      name: null,
      meta: {},
      links: [],
    });
    const defaults = { name: null, label: null, meta: {} };
    expect(done.flow_control).toEqual([
      { id: "b", type: "flow_marker", manifestation: "fine", coordinate: [1, 1], ...defaults },
      { id: "j", type: "jump_from", manifestation: "da_capo", coordinate: [1, 1], ...defaults },
      {
        id: "again",
        type: "jump_from",
        manifestation: "repeat_end",
        coordinate: [1, 1],
        ...defaults,
        repeat_count: 1,
      },
      { id: "m", type: "jump_to", manifestation: "segno", coordinate: [0, 1], ...defaults },
    ]);
    const [chain, combo, pieces] = done.conversion_maps as [JsonObject, JsonObject, JsonObject];
    expect(chain).toEqual({
      type: "ChainMap",
      id: "chain",
      source_unit: null,
      target_unit: null,
      name: null,
      maps: [{ ...linear, name: null, scalar: 1, offset: 0 }],
    });
    expect(combo.name).toBeNull();
    expect((combo.maps as JsonObject).x).toEqual({
      ...linear,
      id: "x",
      name: null,
      scalar: 1,
      offset: 0,
    });
    expect((combo.maps as JsonObject).bar).toEqual({ ...view, name: null });
    expect(pieces.name).toBeNull();
    expect(pieces.maps).toEqual([{ ...table, name: null, kind: "linear", extrapolate: "none" }]);
    expect(value.groups).toEqual([{ id: "g", members: ["score"], name: null, meta: {} }]);
    expect(value.measure_maps).toEqual([{ id: "bars", rows, name: null, meta: {} }]);
    expect(value.graphical).toEqual({ styles: {}, rules: [], order: {}, timestamps: [] });
    validate(value);
  });

  it("gives every object of the description layer exactly its defaults", () => {
    const value = described();
    const done = complete(value);
    const link = {
      relation: "pertains_to",
      level: "work",
      uri: [],
      identifiers: [],
      records: [{ url: "records/op106.json", media_type: null, size: null, integrity: null }],
      label: null,
      assertion: { ...ASSERTION, method: "manual" },
      parts_relation: "has_part",
      parts: [
        {
          uri: [],
          identifiers: [],
          label: null,
          represented_by: [],
          absent: "lost",
          assertion: { ...ASSERTION, status: "confirmed" },
        },
      ],
      parts_ordered: true,
      part_of: [
        {
          parts_relation: "has_part",
          uri: [],
          identifiers: [],
          label: null,
          position: null,
          assertion: null,
        },
      ],
    };
    expect(done.schemes).toEqual([{ id: "opus", name: null, uri: [], criteria: null }]);
    const first = root(done);
    expect([done.links, first.links, (first.regions as JsonObject[])[0]?.links]).toEqual([
      [link],
      [link],
      [link],
    ]);
    expect(minimal(value)).toEqual(value);
    expect(dumps(minimal(done))).toBe(dumps(value));
    validate(done);
  });

  it.each([
    ["ticks", "int"],
    ["seconds", "float"],
    ["whole_notes", "fraction"],
    ["pixels", "int"],
    ["css_pixels", "float"],
    ["user_units", "float"],
  ])("takes the number type of %s from the unit: %s", (unit, numberType) => {
    const value = complete(manifest([timeline("t", unit, null)]));
    expect(root(value).number_type).toBe(numberType);
    expect(Object.hasOwn(root(minimal(value)), "number_type")).toBe(false);
  });

  it("never adds or removes a key whose default is absent", () => {
    const value = complete(SMALLEST) as JsonObject;
    expect(Object.hasOwn(value, "id")).toBe(false);
    expect(Object.hasOwn(value, "graphical")).toBe(false);
    expect(Object.hasOwn(root(value), "offset")).toBe(false);
    const styled = manifest([timeline("score")], { graphical: {} });
    expect(minimal(styled).graphical).toEqual({});
    expect(complete(styled).graphical).toEqual({
      styles: {},
      rules: [],
      order: {},
      timestamps: [],
    });
    const child = manifest([
      timeline("score", "quarters", [8, 1], {
        children: [timeline("c", "quarters", [8, 1], { offset: [0, 1] })],
      }),
    ]);
    expect((root(minimal(child)).children as JsonObject[])[0]?.offset).toEqual([0, 1]);
  });

  it("completes the display of a named timestamp", () => {
    const stamp = (number: number, members: JsonObject = {}): JsonObject => ({
      id: `timestamp_${number}`,
      timeline: "score",
      coordinate: [1, 1],
      name: "Entry",
      ...members,
    });
    const value = manifest([timeline("score")], {
      graphical: {
        timestamps: [
          stamp(1),
          stamp(2, { display: ["cross_section", "wedge", "name"] }),
          stamp(3, { display: ["name", "wedge"] }),
          stamp(4, { display: [] }),
        ],
      },
    });
    const display = ["wedge", "name", "cross_section"];
    expect((complete(value).graphical as JsonObject).timestamps).toEqual([
      stamp(1, { display }),
      stamp(2, { display }),
      stamp(3, { display: ["wedge", "name"] }),
      stamp(4, { display: [] }),
    ]);
    expect((minimal(value).graphical as JsonObject).timestamps).toEqual([
      stamp(1),
      stamp(2),
      stamp(3, { display: ["wedge", "name"] }),
      stamp(4, { display: [] }),
    ]);
  });

  it("keeps values other than the default", () => {
    const value = manifest([
      timeline("score", "quarters", 8.5, {
        locked: true,
        number_type: "float",
        flow_control: [{ ...REPEAT, coordinate: 1.5, repeat_count: 2, label: null }],
      }),
    ]);
    expect(minimal(value)).toEqual(
      manifest([
        timeline("score", "quarters", 8.5, {
          locked: true,
          number_type: "float",
          flow_control: [{ ...REPEAT, coordinate: 1.5, repeat_count: 2 }],
        }),
      ]),
    );
  });

  it("omits a value of another kind equal to its default", () => {
    const map = { type: "LinearMap", id: "l", source_unit: "quarters", target_unit: "seconds" };
    const value = manifest([
      timeline("score", "quarters", [8, 1], {
        flow_control: [{ ...REPEAT, coordinate: [1, 1], repeat_count: new JsonFloat(1) }],
        conversion_maps: [{ ...map, scalar: [1, 1], offset: new JsonFloat(-0) }],
      }),
    ]);
    const stripped = manifest([
      timeline("score", "quarters", [8, 1], {
        flow_control: [{ ...REPEAT, coordinate: [1, 1] }],
        conversion_maps: [map],
      }),
    ]);
    expect(minimal(value)).toEqual(stripped);
    expect(dumps(complete(minimal(value)))).toBe(dumps(complete(stripped)));
    const completed = root(complete(value));
    expect((completed.flow_control as JsonObject[])[0]?.repeat_count).toEqual(new JsonFloat(1));
    expect((completed.conversion_maps as JsonObject[])[0]?.scalar).toEqual([1, 1]);
  });

  it("passes unknown keys through", () => {
    const value = manifest(
      [
        timeline("score", "quarters", [8, 1], {
          lenght: 1,
          flow_control: [],
          regions: [{ ...REGION, codas: [] }],
        }),
      ],
      { extra: { meta: {} } },
    );
    expect(minimal(value)).toEqual(
      manifest(
        [
          timeline("score", "quarters", [8, 1], {
            lenght: 1,
            regions: [{ ...REGION, codas: [] }],
          }),
        ],
        { extra: { meta: {} } },
      ),
    );
    expect(complete(value).extra).toEqual({ meta: {} });
    expect((root(complete(value)).regions as JsonObject[])[0]?.codas).toEqual([]);
  });

  it("keeps the length in both forms", () => {
    for (const length of [null, [8, 1]]) {
      const value = manifest([timeline("score", "quarters", length)]);
      expect(root(complete(value)).length).toEqual(length);
      expect(root(minimal(value)).length).toEqual(length);
    }
  });

  it("hands out fresh objects, never the table's own", () => {
    const first = complete(SMALLEST) as JsonObject;
    const second = complete(SMALLEST) as JsonObject;
    expect(first.meta).not.toBe(second.meta);
    expect(root(first).flow_control).not.toBe(root(second).flow_control);
  });

  it.each([
    ["the smallest file", SMALLEST],
    ["its complete form", complete(SMALLEST)],
    ["the bundle document", bundle()],
    ["a described manifest", described()],
    [
      "unknown keys",
      manifest([
        timeline("score", "quarters", [8, 1], { lenght: 1, regions: [{ ...REGION, codas: [] }] }),
      ]),
    ],
    [
      "a locked parent and a styled manifest",
      manifest(
        [
          timeline("score", "quarters", [8, 1], {
            locked: true,
            children: [timeline("c", "quarters", [8, 1], { offset: [0, 1] })],
          }),
        ],
        { graphical: {} },
      ),
    ],
  ])("round-trips %s", (_name, value) => {
    const given = compactJson(value as Lossless<Json>);
    expect(dumps(minimal(complete(value)))).toBe(dumps(minimal(value)));
    expect(dumps(complete(minimal(value)))).toBe(dumps(complete(value)));
    expect(complete(value)).not.toBe(value);
    expect(minimal(value)).not.toBe(value);
    expect(compactJson(value as Lossless<Json>)).toBe(given);
    validate(complete(value));
    validate(minimal(value));
  });
});

describe("the typed forms", () => {
  const COMPLETE_ROOT: CompleteTimeline = {
    id: "piece",
    name: null,
    unit: "quarters",
    number_type: "fraction",
    length: [32, 1],
    locked: false,
    is_segment_line: false,
    meta: {},
    children: [],
    conversion_maps: [],
    regions: [],
    flow_control: [],
    links: [],
  };
  const COMPLETE: CompleteManifest = {
    timetoshare: "0.2.0",
    name: null,
    meta: {},
    groups: [],
    measure_maps: [],
    schemes: [],
    links: [],
    timelines: [COMPLETE_ROOT],
  };

  it("type every key with a default as present, and no other", () => {
    // The compiler is the test: each `@ts-expect-error` line must fail to type-check.
    const { number_type: _numberType, ...untyped } = COMPLETE_ROOT;
    // @ts-expect-error a complete timeline states its number type
    const unstated: CompleteTimeline = untyped;
    const { groups: _groups, ...ungrouped } = COMPLETE;
    // @ts-expect-error a complete manifest states its groups
    const groupless: CompleteManifest = ungrouped;
    // @ts-expect-error a complete flow-control element states its label
    const uncounted: CompleteFlowControlElement = {
      id: "b",
      type: "flow_marker",
      manifestation: "fine",
      coordinate: 1,
      name: null,
      meta: {},
    };
    // A repeat count is no key of every element, so the complete form keeps it optional.
    const marker: CompleteFlowControlElement = { ...uncounted, label: null };
    // A measure view carries the members of both its bases.
    const view: CompleteMeasureRecordMap = {
      type: "MeasureRecordMap",
      id: "bars",
      name: null,
      source_unit: "quarters",
      target_unit: null,
      measure_map: "measures",
    };
    const { name: _name, ...nameless } = view;
    // @ts-expect-error a complete measure view states its name
    const unnamed: CompleteMeasureRecordMap = nameless;
    // A key whose default is absent stays optional: the manifest's id and
    // `graphical` object, a root's offset.
    const named: CompleteManifest = {
      ...COMPLETE,
      id: "op35",
      graphical: { styles: {}, rules: [], order: {}, timestamps: [] },
    };
    const placed: CompleteTimeline = { ...COMPLETE_ROOT, offset: [-1, 2] };
    // Numbers are lossless and a Fraction stays a pair.
    const exact: CompleteTimeline = { ...COMPLETE_ROOT, length: [new JsonFloat(32), 10n ** 20n] };
    const pair: Lossless<Fraction> = [1, new JsonFloat(2)];
    // @ts-expect-error a Fraction has two members
    const triple: Lossless<Fraction> = [1, 2, 3];
    // The complete form is a lossless manifest.
    const lossless: LosslessManifest = COMPLETE;
    expect([
      unstated,
      groupless,
      uncounted,
      marker,
      view,
      unnamed,
      named,
      placed,
      exact,
      pair,
      triple,
      lossless,
    ]).toHaveLength(12);
  });

  it("complete, strip and order the literal complete form", () => {
    const smallest = minimalManifest(COMPLETE);
    expect(smallest).toEqual({
      timetoshare: "0.2.0",
      timelines: [{ id: "piece", unit: "quarters", length: [32, 1] }],
    });
    expect(completeManifest(smallest)).toEqual(COMPLETE);
    const ordered: CompleteManifest = canonicalManifest(COMPLETE);
    expect(ordered).toEqual(COMPLETE);
    expect(ordered).not.toBe(COMPLETE);
  });

  const twins = fixtureFiles().filter((file) => file.endsWith(".minimal"));

  it("have a minimal twin for every fixture", () => {
    expect(twins.length).toBe(73);
    expect(twins.map((twin) => twin.replace(/\.minimal$/, ""))).toEqual(
      fixtureFiles().filter((file) => !file.endsWith(".minimal")),
    );
  });

  it.each(twins)("complete %s to its fixture, and back", (twin) => {
    const fixture = dumps(loads(fixtureText(twin.replace(/\.minimal$/, ""))));
    const completed = completeManifest(parse(fixtureText(twin)));
    expect(dumps(completed)).toBe(fixture);
    expect(dumps(canonicalManifest(completed))).toBe(fixture);
    expect(dumps(minimalManifest(completed))).toBe(dumps(loads(fixtureText(twin))));
  });
});
