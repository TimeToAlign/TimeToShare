import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  compactJson,
  compactSortedJson,
  dumps,
  dumpsFile,
  type FileForm,
  fileForm,
  isJsonObject,
  isSerialization,
  JsonFloat,
  loads,
  SERIALIZATIONS,
  type Serialization,
} from "../src/index.js";
import { fixtureDirectory, fixtureFiles, fixtureText, repositoryRoot } from "./fixtures.js";

const directory = resolve(repositoryRoot, "fixtures", "file_forms");

/** The form each text of `fixtures/file_forms/` is read as, as the test README states it. */
const CASES: Record<string, FileForm> = {
  "neither.yaml": { minimal: false, styling: true, serialization: "yaml" },
  "one_line.json": { minimal: true, styling: false, serialization: "json" },
  "crlf.yaml": { minimal: true, styling: true, serialization: "yaml" },
  "jcs_minimal.json": { minimal: true, styling: false, serialization: "jcs" },
  "jcs_float_default.json": { minimal: false, styling: false, serialization: "jcs" },
};

/** `jcs_minimal.json` in canonical YAML after its `@context`, its own-axis floats spelled as floats. */
const JCS_MINIMAL_AS_YAML = `timelines:
  -
    conversion_maps:
      -
        id: "#cmap_1"
        scalar: 0.5
        source_unit: seconds
        target_unit: samples
        type: LinearMap
    id: "#s"
    length: 8.0
    offset: 0.0
    regions:
      -
        end: 4.5
        id: "#region_1"
        start: 0.0
    unit: seconds
timetoshare: "0.2.0"
`;

/** A file decoded as UTF-8, its line ends kept. */
function text(path: string): string {
  return readFileSync(path, "utf8");
}

/** The canonical YAML of the format's `@context`, with which every fixture opens. */
function contextBlock(): string {
  const twin = text(resolve(fixtureDirectory, "bare.minimal.yaml"));
  return twin.slice(0, twin.indexOf("\ngraphical:") + 1);
}

function expectedName(name: string): string {
  const dot = name.lastIndexOf(".");
  return `${name.slice(0, dot)}.expected${name.slice(dot)}`;
}

/**
 * Every text of a fixture, its value and its value without `graphical`, in
 * each serialization, with that serialization and whether it holds
 * `graphical`.
 */
function written(name: string): [string, Serialization, boolean][] {
  const value = loads(fixtureText(name));
  if (!isJsonObject(value)) throw new TypeError(`${name} is not an object`);
  const { graphical: _graphical, ...unstyled } = value;
  const values = Object.hasOwn(value, "graphical") ? [value, unstyled] : [value];
  return values.flatMap((each) =>
    SERIALIZATIONS.map((serialization): [string, Serialization, boolean] => [
      dumps(each, { serialization }),
      serialization,
      Object.hasOwn(each, "graphical"),
    ]),
  );
}

describe("manifest files", () => {
  const fixtures = fixtureFiles();

  it("cover every fixture and twin, bundles and groups included", () => {
    expect(fixtures).toHaveLength(180);
    expect(new Set(fixtures.map((name) => name.split("/").slice(0, -1).join("/")))).toEqual(
      new Set(["", "bundles", "groups", "statements"]),
    );
  });

  it.each(fixtures)("write %s back byte for byte", (name) => {
    const isTwin = name.endsWith(".minimal");
    for (const [given, serialization, styled] of written(name)) {
      const form = fileForm(given);
      expect(form).toEqual({ minimal: isTwin, styling: styled, serialization });
      expect(dumpsFile(loads(given), form)).toBe(given);
    }
  });

  it("name every text of the cases in the table", () => {
    const files = readdirSync(directory);
    const texts = files.filter((name) => !name.includes(".expected."));
    expect(new Set(texts)).toEqual(new Set(Object.keys(CASES)));
    expect(new Set(files.filter((name) => name.includes(".expected.")))).toEqual(
      new Set(Object.keys(CASES).map(expectedName)),
    );
  });

  it.each(Object.keys(CASES))("read %s as its form and write it back as expected", (name) => {
    const given = text(resolve(directory, name));
    expect(fileForm(given)).toEqual(CASES[name]);
    expect(dumpsFile(loads(given), fileForm(given))).toBe(
      text(resolve(directory, expectedName(name))),
    );
  });

  it("derive the cases from the fixtures", () => {
    const complete = text(resolve(fixtureDirectory, "bare.yaml"));
    const twin = text(resolve(fixtureDirectory, "bare.minimal.yaml"));
    expect(text(resolve(directory, "neither.expected.yaml"))).toBe(complete);
    expect(text(resolve(directory, "crlf.expected.yaml"))).toBe(twin);
    expect(text(resolve(directory, "crlf.yaml"))).toBe(twin.replaceAll("\n", "\r\n"));
    expect(text(resolve(directory, "one_line.json"))).not.toContain("\n");
  });

  it("read RFC 8785 integers that the declared number type respells", () => {
    const given = text(resolve(directory, "jcs_minimal.json"));
    const value = loads(given);
    const [root] = (value as { timelines: { length: unknown; offset: unknown }[] }).timelines;
    expect([typeof root?.length, typeof root?.offset]).toEqual(["number", "number"]);
    expect([root?.length, root?.offset]).toEqual([8, 0]);
    const asYaml: FileForm = { ...fileForm(given), serialization: "yaml" };
    const expected = contextBlock() + JCS_MINIMAL_AS_YAML;
    expect(dumpsFile(value, asYaml)).toBe(expected);
    expect(fileForm(expected)).toEqual(asYaml);
  });

  it("leave the value unchanged", () => {
    const value = loads(text(resolve(directory, "neither.yaml")));
    const before = dumps([value], { serialization: "json" });
    dumpsFile(value, { minimal: true, styling: false, serialization: "jcs" });
    dumpsFile(value, { minimal: false, styling: true, serialization: "yaml" });
    expect(dumps([value], { serialization: "json" })).toBe(before);
  });
});

describe("serialization names", () => {
  it("list the three serializations in order", () => {
    expect(SERIALIZATIONS).toEqual(["yaml", "json", "jcs"]);
  });

  it.each(["yaml", "json", "jcs"])("know %s", (name) => {
    expect(isSerialization(name)).toBe(true);
  });

  it.each(["YAML", "toml", "", null, undefined, 1])("refuse %s", (name) => {
    expect(isSerialization(name)).toBe(false);
  });
});

describe("compactSortedJson", () => {
  const value = {
    b: 1,
    z: { y: 1, x: 2 },
    "😀": null,
    "｡": true,
    a: [new JsonFloat(2), 0.5, 2n ** 60n, new JsonFloat(1e21)],
  };

  it("sorts keys by code point at every depth and spells kinds apart", () => {
    expect(compactSortedJson(value)).toBe(
      '{"a":[2.0,0.5,1152921504606846976,1.0e+21],"b":1,"z":{"x":2,"y":1},"｡":true,"😀":null}',
    );
  });

  it("differs from compactJson in key order alone", () => {
    expect(compactJson(value)).toBe(
      '{"b":1,"z":{"y":1,"x":2},"😀":null,"｡":true,"a":[2.0,0.5,1152921504606846976,1.0e+21]}',
    );
  });

  it("keeps a manifest's arrays in their order", () => {
    const manifest = { timetoshare: "0.2.0", timelines: [{ id: "b" }, { id: "a" }] };
    expect(compactSortedJson(manifest)).toBe(
      '{"timelines":[{"id":"b"},{"id":"a"}],"timetoshare":"0.2.0"}',
    );
  });
});
