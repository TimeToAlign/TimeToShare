import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { Ajv2020 } from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import { bundleSchemas } from "../scripts/generate.js";
import { DEFAULTS } from "../src/defaults.js";
import { schema } from "../src/generated/schema.js";
import { TIMESTAMP_DISPLAY } from "../src/manifest/order.js";
import { UNITS } from "../src/manifest/units.js";
import { loads } from "../src/serialization/read.js";
import { BELIEFS, BLANK, FORMAT_CONTEXT, MATCHES, METHODS } from "../src/statements/statements.js";
import { SCHEMA_VERSION } from "../src/validate.js";
import { loadSchemaFile, repositoryRoot } from "./fixtures.js";

type Node = Record<string, unknown>;

const PUBLIC = [
  "Manifest",
  "Timeline",
  "Group",
  "Graphical",
  "ConversionMap",
  "Coordinate",
  "Number",
  "Fraction",
  "TimeUnit",
  "NumberType",
  "Id",
  "MeasureMap",
  "MeasureMapRow",
  "Resource",
  "Timestamp",
  "MatchStamp",
  "AlignmentAnchor",
  "Context",
  "Statements",
  "StatementValue",
  "ProvenanceEntry",
];

/** Every node whose pattern ends in `$`, by its path below `$defs`, with a value its pattern accepts. */
const ANCHORED: [string[], string][] = [
  [["Paint"], "none"],
  [["Declaration", "properties", "stroke-dasharray"], "4 2"],
  [["CalendarDate"], "2026-11-17"],
  [["Resource", "properties", "media_type"], "application/vnd.apache.parquet"],
  [["Resource", "properties", "integrity", "properties", "digest"], "00ff"],
];

const MAP_TYPES = [
  "ChainMap",
  "CombinationMap",
  "ConstantMap",
  "FloatingMeasureMap",
  "LinearMap",
  "MeasureBeatMap",
  "MeasureNumberMap",
  "MeasureRecordMap",
  "PiecewiseMap",
  "TableMap",
];

const MEASURE_VIEWS: Readonly<Record<string, string | null>> = {
  FloatingMeasureMap: "floating_measures",
  MeasureBeatMap: null,
  MeasureNumberMap: null,
  MeasureRecordMap: null,
};

const document: Node = schema;
const defs = document.$defs as Record<string, Node>;
const properties = (name: string) => defs[name]?.properties as Record<string, Node>;
const target = (node: Node): Node =>
  typeof node.$ref === "string" ? (defs[node.$ref.slice("#/$defs/".length)] as Node) : node;
/** The conversion map types: the definitions `ConversionMap` chooses between. */
const mapTypes = ((defs.ConversionMap as Node).oneOf as Node[]).map((branch) =>
  (branch.$ref as string).slice("#/$defs/".length),
);

/** The defaults a definition declares, through references and its bases. */
function defaultsOf(definition: Node): Record<string, unknown> {
  const members = { ...((definition.properties ?? {}) as Record<string, Node>) };
  for (const entry of (definition.allOf ?? []) as Node[]) {
    for (const [key, value] of Object.entries(defaultsOf(target(entry)))) {
      if (!(key in members)) members[key] = { default: value };
    }
  }
  return Object.fromEntries(
    Object.entries(members)
      .map(([key, member]) => [key, "default" in member ? member : target(member)] as const)
      .filter(([, owner]) => "default" in owner)
      .map(([key, owner]) => [key, owner.default]),
  );
}

/** The keys a node declares, its `allOf` bases' included, at any depth. */
function declaredKeys(node: Node): Set<string> {
  const declared = new Set(Object.keys((node.properties ?? {}) as Node));
  for (const entry of (node.allOf ?? []) as Node[]) {
    for (const key of declaredKeys(target(entry))) declared.add(key);
  }
  return declared;
}

/** Every key of the document that begins with `x-`. */
function customKeys(node: unknown): string[] {
  if (Array.isArray(node)) return node.flatMap(customKeys);
  if (typeof node !== "object" || node === null) return [];
  const own = Object.keys(node).filter((key) => key.startsWith("x-"));
  return [...own, ...Object.values(node).flatMap(customKeys)];
}

/** Every schema node with whether it lies in a branch or an arm. */
function* nodes(node: unknown, inside = false): Generator<[Node, boolean]> {
  if (Array.isArray(node)) {
    for (const item of node) yield* nodes(item, inside);
    return;
  }
  if (typeof node !== "object" || node === null) return;
  const value = node as Node;
  yield [value, inside];
  for (const [key, child] of Object.entries(value)) {
    if (["oneOf", "anyOf", "if", "then", "else"].includes(key)) yield* nodes(child, true);
    else if (key === "properties" || key === "$defs") {
      for (const member of Object.values(child as Node)) yield* nodes(member, false);
    } else if (!["default", "const", "enum"].includes(key)) yield* nodes(child, inside);
  }
}

describe("the schema document", () => {
  it("is the bundled file, with one root", () => {
    expect(JSON.parse(JSON.stringify(loadSchemaFile()))).toEqual(document);
    expect(document.$id).toBe(
      "https://timetoalign.github.io/timetoshare/0.2.0/timetoshare.schema.json",
    );
    expect(document.$schema).toBe("https://json-schema.org/draft/2020-12/schema");
    expect(document.$ref).toBe("#/$defs/Manifest");
  });

  it("bundles the provenance schema, which refers to the manifest schema", () => {
    const directory = resolve(repositoryRoot, "schema", SCHEMA_VERSION);
    const read = (name: string) =>
      loads(readFileSync(resolve(directory, name), "utf8")) as Record<string, unknown>;
    const provenance = read("provenance.schema.json");
    const manifest = read("timetoshare.schema.json");
    expect(provenance.$id).toBe(
      "https://timetoalign.github.io/timetoshare/0.2.0/provenance.schema.json",
    );
    expect(((manifest.$defs as Node).ProvenanceEntry as Node).allOf).toEqual([
      { $ref: "provenance.schema.json" },
    ]);
    expect(Object.keys(provenance.$defs as Node).sort()).toEqual(["Belief", "CalendarDate"]);
    const references = [...nodes(provenance)]
      .map(([node]) => node.$ref)
      .filter((reference) => typeof reference === "string");
    expect([...new Set(references)].sort()).toEqual([
      "#/$defs/Belief",
      "#/$defs/CalendarDate",
      "timetoshare.schema.json#/$defs/Iri",
      "timetoshare.schema.json#/$defs/IriReference",
    ]);
    expect(JSON.parse(JSON.stringify(bundleSchemas(manifest, provenance)))).toEqual(document);
    expect(() => bundleSchemas(manifest, { ...provenance, $defs: { Timeline: {} } })).toThrow(
      "both schemas define 'Timeline'",
    );
  });

  it("refers locally, without anchors", () => {
    const all = [...nodes(document)].map(([node]) => node);
    const references = all.filter((node) => typeof node.$ref === "string");
    expect(references.map((node) => node.$ref)).toContain("#/$defs/Timeline");
    for (const node of references) {
      const reference = node.$ref as string;
      expect(reference.startsWith("#/$defs/")).toBe(true);
      expect(Object.hasOwn(defs, reference.slice("#/$defs/".length))).toBe(true);
    }
    expect(all.filter((node) => "$anchor" in node)).toEqual([]);
  });

  it("holds the public definitions", () => {
    for (const name of PUBLIC) expect(Object.hasOwn(defs, name)).toBe(true);
    const [, named] =
      /The definitions (.+?) are public:/.exec(document.description as string) ?? [];
    expect(named).toBe(`${PUBLIC.slice(0, -1).join(", ")} and ${PUBLIC.at(-1)}`);
  });

  it("chooses between the ten map types", () => {
    expect(mapTypes).toEqual(MAP_TYPES);
    expect(properties("Selector").class?.enum).toEqual([
      "ContinuousLogicalTimeline",
      "ContinuousPhysicalTimeline",
      "ContinuousGraphicalTimeline",
      "DiscreteLogicalTimeline",
      "DiscretePhysicalTimeline",
      "DiscreteGraphicalTimeline",
      ...MAP_TYPES,
    ]);
    expect(defs.Facet?.enum).toEqual([
      "markers",
      "conversion_maps",
      "children",
      "regions",
      "flow_control",
    ]);
    expect(defs.Part?.enum).toEqual([
      "start",
      "end",
      "name",
      "label",
      "card",
      "line",
      "id",
      "coordinate",
    ]);
    const display = ((defs.Timestamp as Node).properties as Node).display as Node;
    expect((display.items as Node).enum).toEqual([...TIMESTAMP_DISPLAY]);
    expect(TIMESTAMP_DISPLAY).toEqual(["wedge", "name", "id", "coordinate", "cross_section"]);
    expect(display.uniqueItems).toBe(true);
    expect(properties("Selector").facet?.$ref).toBe("#/$defs/Facet");
    expect(properties("Selector").coordinates?.enum).toEqual(["primary", "secondary"]);
    expect(defs.ElementType?.enum).toEqual([
      "block",
      "timeline",
      "child",
      "band",
      "map",
      "region",
      "flow_marker",
      "jump_from",
      "wedge",
      "name",
      "label",
      "boundary",
      "ancestor",
      "frame",
      "card",
      "cross_section",
      "alignment_anchor",
      "ancestor_card",
    ]);
    expect(properties("MeasureView").source_unit?.const).toBe("quarters");
    for (const [name, unit] of Object.entries(MEASURE_VIEWS)) {
      expect(defs[name]?.allOf, name).toEqual([{ $ref: "#/$defs/MeasureView" }]);
      expect(properties(name).target_unit?.const, name).toBe(unit);
    }
  });

  it("holds the unit table, row by row", () => {
    const continuous = ["float", "fraction"];
    expect(
      Object.entries(UNITS).map(([unit, row]) => [
        unit,
        row.domain,
        row.modality,
        row.numberType,
        row.numberTypes,
      ]),
    ).toEqual([
      ["number", "logical", "continuous", "float", ["int", "float", "fraction"]],
      ["floating_measures", "logical", "continuous", "float", continuous],
      ["whole_notes", "logical", "continuous", "fraction", continuous],
      ["quarters", "logical", "continuous", "fraction", continuous],
      ["ticks", "logical", "discrete", "int", ["int"]],
      ["milliseconds", "physical", "continuous", "float", continuous],
      ["seconds", "physical", "continuous", "float", continuous],
      ["minutes", "physical", "continuous", "float", continuous],
      ["samples", "physical", "discrete", "int", ["int"]],
      ["frames", "physical", "discrete", "int", ["int"]],
      ["pixels", "graphical", "discrete", "int", ["int"]],
      ["meters", "graphical", "continuous", "float", continuous],
      ["centimeters", "graphical", "continuous", "float", continuous],
      ["millimeters", "graphical", "continuous", "float", continuous],
      ["inches", "graphical", "continuous", "float", continuous],
      ["points", "graphical", "continuous", "float", continuous],
      ["css_pixels", "graphical", "continuous", "float", continuous],
      ["user_units", "graphical", "continuous", "float", continuous],
    ]);
  });

  it("states the domain, modality and default number type of every unit in the unit table", () => {
    const unit = defs.TimeUnit as Node;
    expect(unit.type).toBe("string");
    expect(unit.enum).toBeUndefined();
    const entries = unit.oneOf as Node[];
    expect(entries.map((entry) => entry.const)).toEqual(Object.keys(UNITS));
    const pattern =
      /^(Logical|Physical|Graphical), (continuous|discrete); default number type (int|float|fraction)\.(?: \S.*\.)?$/;
    for (const entry of entries) {
      expect(Object.keys(entry).sort()).toEqual(["const", "description"]);
      const match = pattern.exec(entry.description as string);
      const row = UNITS[entry.const as keyof typeof UNITS];
      expect([match?.[1]?.toLowerCase(), match?.[2], match?.[3]]).toEqual([
        row.domain,
        row.modality,
        row.numberType,
      ]);
    }
  });

  it("states in the timeline which number types a unit admits", () => {
    const timeline = defs.Timeline as Node;
    const rows = Object.entries(UNITS);
    const discrete = rows.filter(([, row]) => row.numberTypes.join() === "int").map(([u]) => u);
    expect(timeline.if).toEqual({ properties: { unit: { enum: discrete } }, required: ["unit"] });
    expect(timeline.then).toEqual({ properties: { number_type: { const: "int" } } });
    expect(rows.filter(([, row]) => row.numberTypes.length === 3).map(([u]) => u)).toEqual([
      "number",
    ]);
    expect(
      new Set(
        rows
          .filter(([, row]) => row.numberTypes.length === 2)
          .map(([, row]) => row.numberTypes.join()),
      ),
    ).toEqual(new Set(["float,fraction"]));
    expect(rows.every(([, row]) => [1, 2, 3].includes(row.numberTypes.length))).toBe(true);
    expect(timeline.else).toEqual({
      if: { properties: { unit: { const: "number" } }, required: ["unit"] },
      else: { properties: { number_type: { enum: ["float", "fraction"] } } },
    });
    const coordinate = defs.Coordinate as Node;
    for (const key of ["if", "then", "else"]) expect(coordinate[key]).toEqual(timeline[key]);
  });

  const THEN = "#/then/properties/number_type/const";
  const ELSE = "#/else/else/properties/number_type/enum";
  it.each([
    ["ticks_float", { unit: "ticks", number_type: "float", value: 1.5 }, THEN],
    ["seconds_int", { unit: "seconds", number_type: "int", value: 10 }, ELSE],
    ["quarters_int", { unit: "quarters", number_type: "int", value: 8 }, ELSE],
    ["ticks_int", { unit: "ticks", number_type: "int", value: 480 }, null],
    ["seconds_float", { unit: "seconds", number_type: "float", value: 1.5 }, null],
    ["quarters_fraction", { unit: "quarters", number_type: "fraction", value: [1, 2] }, null],
    ["number_int", { unit: "number", number_type: "int", value: 2 }, null],
  ])("admits in a coordinate the number types of its unit (%s)", (_, coordinate, keyword) => {
    const check = new Ajv2020({ strict: false, allErrors: true }).compile({
      $ref: "#/$defs/Coordinate",
      $defs: defs,
    });
    check(coordinate);
    const errors = (check.errors ?? [])
      .filter((error) => error.keyword !== "if")
      .map((error) => [error.instancePath, error.schemaPath]);
    expect(errors).toEqual(keyword === null ? [] : [["/number_type", keyword]]);
  });

  it("defines a repeated shape once", () => {
    expect(defs.Name).toEqual({
      type: ["string", "null"],
      description: "Human-readable name, or null when none was given.",
      default: null,
    });
    expect(defs.Meta).toEqual({
      type: "object",
      additionalProperties: true,
      description: "Free-form metadata.",
      default: {},
    });
    const names = [
      "Manifest",
      "Timeline",
      "Group",
      "Region",
      "FlowControlElement",
      "MeasureMap",
      "MapBase",
    ];
    for (const owner of names) expect(properties(owner).name?.$ref).toBe("#/$defs/Name");
    const metas = ["Manifest", "Timeline", "Group", "Region", "FlowControlElement", "MeasureMap"];
    for (const owner of metas) expect(properties(owner).meta?.$ref).toBe("#/$defs/Meta");
    for (const [node] of nodes(document)) {
      const members = (node.properties ?? {}) as Record<string, Node>;
      if ("meta" in members) expect(members.meta?.$ref).toBe("#/$defs/Meta");
      expect(members.name?.type).not.toEqual(["string", "null"]);
    }
  });

  it("extends the map base in every conversion map", () => {
    const base = defs.MapBase as Node;
    const baseKeys = Object.keys(base.properties as Node);
    expect(baseKeys).toEqual(["type", "id", "name", "source_unit", "target_unit"]);
    expect(base.required).toEqual(["type", "id", "source_unit", "target_unit"]);
    const view = defs.MeasureView as Node;
    expect(view.type).toBe("object");
    expect(view.allOf).toEqual([{ $ref: "#/$defs/MapBase" }]);
    expect(Object.keys(view.properties as Node)).toEqual(["source_unit", "measure_map"]);
    expect(properties("MeasureView").source_unit?.const).toBe("quarters");
    expect(view.required).toEqual(["measure_map"]);
    const bases = [...baseKeys, ...Object.keys(view.properties as Node)];
    for (const name of mapTypes) {
      const definition = defs[name] as Node;
      expect(definition.type).toBe("object");
      const parent = name in MEASURE_VIEWS ? "MeasureView" : "MapBase";
      expect(definition.allOf, name).toEqual([{ $ref: `#/$defs/${parent}` }]);
      const own = Object.keys(definition.properties as Node).filter((key) => bases.includes(key));
      const units = name in MEASURE_VIEWS ? ["target_unit"] : [];
      expect(own, name).toEqual(["type", ...units]);
      for (const key of units) expect(properties(name)[key], name).toHaveProperty("const");
      expect(properties(name).type).toEqual({ const: name });
      const required = definition.required as string[];
      expect(required).toContain("type");
      for (const key of ["id", "source_unit", "target_unit"]) expect(required).not.toContain(key);
    }
  });

  it("refers by ID and addresses by Address", () => {
    const selector = properties("Selector");
    expect(selector.within?.$ref).toBe("#/$defs/Id");
    expect(selector.addresses?.items).toEqual({ $ref: "#/$defs/Address" });
    expect(properties("FlowControlElement").target?.$ref).toBe("#/$defs/Id");
    expect(properties("MeasureView").measure_map?.$ref).toBe("#/$defs/Id");
    const ajv = new Ajv2020({ strict: false });
    const identifier = ajv.compile({ $ref: "#/$defs/Id", $defs: defs });
    for (const accepted of [
      "#score",
      "#Bass Kick",
      "#perf/take 2",
      "#https://example.org/piece/score#exposition",
      "#start",
      "#regions_1",
      "##x",
      "# ",
    ]) {
      expect(identifier(accepted), accepted).toBe(true);
    }
    for (const refused of ["", "#", "score", "score#", "#score\t", "#score\n", "#\u001f"]) {
      expect(identifier(refused), refused).toBe(false);
    }
    const address = ajv.compile({ $ref: "#/$defs/Address", $defs: defs });
    for (const accepted of [
      {},
      { part: ["name"] },
      { id: "#score" },
      { id: "#perf/take 2" },
      { id: "#score", facet: "regions" },
      { id: "#score", part: ["card"] },
      { id: "#score", part: ["end", "label"] },
      { id: "#timestamp_1", part: ["line"] },
      { id: "#timestamp_1", part: ["label"] },
      { id: "#timestamp_1", part: ["name"] },
      { id: "#timestamp_1", part: ["id"] },
      { id: "#timestamp_1", part: ["coordinate"] },
      { id: "#score", root: "score" },
    ]) {
      expect(address(accepted), JSON.stringify(accepted)).toBe(true);
    }
    for (const refused of [
      "score",
      { facet: "regions" },
      { id: "#score", facet: "regions", part: ["label"] },
      { id: "#score", part: [] },
      { id: "#score", part: ["wedge"] },
      { id: "#score", facet: "regions_1" },
    ]) {
      expect(address(refused), JSON.stringify(refused)).toBe(false);
    }
  });

  it("lets no pattern take a trailing newline", () => {
    const anchored: string[][] = [];
    const walk = (node: unknown, path: string[]): void => {
      if (Array.isArray(node)) {
        for (const item of node) walk(item, path);
      } else if (typeof node === "object" && node !== null) {
        const { pattern } = node as Node;
        if (typeof pattern === "string" && pattern.endsWith("$")) anchored.push(path);
        for (const [key, value] of Object.entries(node)) walk(value, [...path, key]);
      }
    };
    walk(defs, []);
    const key = (path: string[]) => path.join("/");
    expect(anchored.map(key).sort()).toEqual(ANCHORED.map(([path]) => key(path)).sort());
    const ajv = new Ajv2020({ strict: false });
    for (const [path, value] of ANCHORED) {
      const node = path.reduce<unknown>((at, name) => (at as Node)[name], defs) as Node;
      const accepts = ajv.compile({ ...node, $defs: defs });
      expect(accepts(value), key(path)).toBe(true);
      expect(accepts(`${value}\n`), key(path)).toBe(false);
    }
    const order = ajv.compile({ $ref: "#/$defs/Order", $defs: defs });
    expect(order(["line", "markers"])).toBe(true);
    expect(order(["line\n", "markers"])).toBe(false);
    expect(order([""])).toBe(false);
  });

  it("keeps every object open without a custom keyword", () => {
    const all = [...nodes(document)].map(([node]) => node);
    expect(all.filter((node) => node.additionalProperties === false)).toEqual([]);
    expect(all.filter((node) => "unevaluatedProperties" in node)).toEqual([]);
    expect(customKeys(document)).toEqual([]);
    expect(all.filter((node) => node.additionalProperties === true)).toEqual([defs.Meta]);
    expect(defs.Meta?.properties).toBeUndefined();
  });

  it("declares on every object what its branches and arms declare", () => {
    for (const [node, inside] of nodes(document)) {
      if (inside || node.type !== "object" || node.properties === undefined) continue;
      const declared = declaredKeys(node);
      expect(node.patternProperties).toBeUndefined();
      const branches = [
        ...((node.oneOf ?? []) as Node[]),
        ...((node.anyOf ?? []) as Node[]),
        ...(["if", "then", "else"].map((key) => node[key] ?? {}) as Node[]),
      ];
      for (const branch of branches) {
        for (const key of Object.keys((branch.properties ?? {}) as Node)) {
          expect(declared.has(key)).toBe(true);
        }
      }
    }
  });

  it("tags every branch of a discriminated union with a distinct constant", () => {
    const unions = [...nodes(document)].filter(([node]) => "discriminator" in node);
    expect(unions.map(([node]) => (node.discriminator as Node).propertyName).sort()).toEqual([
      "number_type",
      "type",
    ]);
    for (const [node] of unions) {
      const key = (node.discriminator as Node).propertyName as string;
      const tags = (node.oneOf as Node[]).map(
        (branch) => ((target(branch).properties as Record<string, Node>)[key] as Node).const,
      );
      expect(tags.every((tag) => typeof tag === "string")).toBe(true);
      expect(new Set(tags).size).toBe(tags.length);
      const required = (branch: Node) => (target(branch).required ?? node.required) as string[];
      for (const branch of node.oneOf as Node[]) expect(required(branch)).toContain(key);
    }
  });

  it("declares the defaults of the table and no other", () => {
    type Kind = keyof typeof DEFAULTS;
    const kinds: Partial<Record<Kind, string[]>> = {
      manifest: ["Manifest"],
      timeline: ["Timeline"],
      region: ["Region"],
      measure_map: ["MeasureMap"],
      group: ["Group"],
      graphical: ["Graphical"],
      timestamp: ["Timestamp"],
      alignment_anchor: ["AlignmentAnchor"],
    };
    const own: Readonly<Record<string, Kind>> = { LinearMap: "linear_map", TableMap: "table_map" };
    const element = ["flow_control_element", "repeat_end"];
    expect(
      [
        ...Object.keys(kinds),
        "conversion_map",
        "match_timestamp",
        ...Object.values(own),
        ...element,
      ].sort(),
    ).toEqual(Object.keys(DEFAULTS).sort());
    const matched = defs.Timestamp as Node;
    expect(matched.if).toEqual({
      properties: { matchstamp: { const: true } },
      required: ["matchstamp"],
    });
    expect(defaultsOf(matched.then as Node)).toEqual(DEFAULTS.match_timestamp);
    expect(matched.else).toEqual({ required: ["name"] });
    const covered = new Set<string>(["MapBase", "MeasureView", "FlowControlElement"]);
    const flowControl = defs.FlowControlElement as Node;
    expect(defaultsOf(flowControl)).toEqual(DEFAULTS.flow_control_element);
    const repeatEnd = (flowControl.then as Node).else as Node;
    expect(((repeatEnd.if as Node).properties as Node).manifestation).toEqual({
      const: "repeat_end",
    });
    expect(defaultsOf(repeatEnd.then as Node)).toEqual(DEFAULTS.repeat_end);
    for (const [kind, names] of Object.entries(kinds)) {
      for (const name of names) {
        covered.add(name);
        expect(defaultsOf(defs[name] as Node), name).toEqual(DEFAULTS[kind as Kind]);
      }
    }
    for (const name of mapTypes) {
      covered.add(name);
      const added = Object.hasOwn(own, name) ? DEFAULTS[own[name] as Kind] : {};
      expect(defaultsOf(defs[name] as Node), name).toEqual({
        ...DEFAULTS.conversion_map,
        ...added,
      });
    }
    for (const [name, definition] of Object.entries(defs)) {
      if (!covered.has(name)) expect(defaultsOf(definition), name).toEqual({});
    }
    expect(properties("Timeline").number_type?.default).toBeUndefined();
  });

  it("states statements on the manifest, its timelines and its regions only", () => {
    const holding = (key: string) =>
      Object.entries(defs)
        .filter(([name]) => name !== "Context")
        .filter(([, definition]) => key in ((definition.properties ?? {}) as Node))
        .map(([name]) => name)
        .sort();
    // `Context` declares every format term, `statements` and `provenance` among them.
    expect(holding("statements")).toEqual(["Manifest", "Region", "Timeline"]);
    expect(holding("@context")).toEqual(["Manifest"]);
    expect(holding("links")).toEqual([]);
    expect(holding("schemes")).toEqual([]);
    for (const name of ["Manifest", "Region", "Timeline"]) {
      expect(properties(name).statements, name).toMatchObject({ $ref: "#/$defs/Statements" });
      expect(properties(name).provenance, name).toMatchObject({ $ref: "#/$defs/Provenance" });
      expect("default" in (properties(name).statements as Node)).toBe(false);
      expect("default" in (properties(name).provenance as Node)).toBe(false);
    }
    expect((defs.ProvenanceEntry as Node).allOf).toEqual([{ $ref: "#/$defs/ProvenanceRecord" }]);
    expect((defs.ProvenanceEntry as Node).required).toEqual(["property", "value"]);
    expect(Object.keys(properties("ProvenanceRecord")).sort()).toEqual([
      "basis",
      "beliefs",
      "date",
      "match",
      "method",
      "note",
      "service",
      "stated_by",
    ]);
    expect(properties("Belief").belief?.enum).toEqual([...BELIEFS]);
    expect((defs.Belief as Node).required).toEqual(["actor", "belief", "date"]);
    expect(properties("ProvenanceRecord").match?.enum).toEqual([...MATCHES]);
    const method = properties("ProvenanceRecord").method?.anyOf as Node[];
    expect(method[0]?.enum).toEqual([...METHODS]);
    expect(defs.Iri?.not).toEqual({ pattern: BLANK });
    expect(defs.PrefixIri?.not).toEqual({ pattern: BLANK });
    const reference = (defs.IriReference as Node).not as Node;
    expect((reference.anyOf as Node[])[0]).toEqual({ pattern: BLANK });
  });

  it("fixes the format's terms of the context as the package states them", () => {
    const context = defs.Context as Node;
    const terms = context.properties as Record<string, Node>;
    expect(Object.keys(terms)).toEqual(Object.keys(FORMAT_CONTEXT));
    expect(context.required).toEqual(Object.keys(FORMAT_CONTEXT));
    for (const [term, value] of Object.entries(FORMAT_CONTEXT)) {
      expect(terms[term]?.const, term).toEqual(value);
    }
    expect(context.additionalProperties).toEqual({ $ref: "#/$defs/PrefixIri" });
  });

  it("accepts and refuses IRIs, prefixes and language tags", () => {
    const ajv = new Ajv2020({ strict: false });
    const accepts = (name: string, value: string) =>
      ajv.compile({ $ref: `#/$defs/${name}`, $defs: defs })(value);
    const cases: [string, string[], string[]][] = [
      [
        "Iri",
        ["wdt:P175", "http://schema.org/name", "urn:isbn:0451450523", "melodTerms:Performer"],
        ["type", "P175", ":x", "1wd:Q1", "wd:", "wd:Q 1", "wd:Q1\n", "wd:Q\u00a01", "wd:Q1\ufeff"],
      ],
      [
        "IriReference",
        ["#clt_1", "other.yaml#clt_1", "wd:Q1", "records/op106.json"],
        ["", "_:b0", "@id", "#a b", "#a\n"],
      ],
      [
        "PrefixName",
        ["wd", "melodTerms", "my-vocab_2"],
        ["1wd", "w.d", "unit", "http", "urn", "members"],
      ],
      [
        "PrefixIri",
        ["http://schema.org/", "http://www.w3.org/2001/XMLSchema#"],
        ["http://www.wikidata.org/entity", "schema.org/", "http://a b/", "http://x/\n"],
      ],
      ["LanguageTag", ["en", "de-CH", "zh-Hant-TW"], ["", "en_GB", "toolonglanguage", "en-"]],
    ];
    for (const [name, accepted, refused] of cases) {
      for (const value of accepted) expect(accepts(name, value), `${name} ${value}`).toBe(true);
      for (const value of refused) expect(accepts(name, value), `${name} ${value}`).toBe(false);
    }
  });
});
