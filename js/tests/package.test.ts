import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { bundlePackageSchema } from "../scripts/generate.js";
import { packageSchema, schema } from "../src/generated/schema.js";
import * as timetoshare from "../src/index.js";
import { type JsonObject, plain } from "../src/json/value.js";
import { loadSchemaFile, repositoryRoot } from "./fixtures.js";

type Node = Record<string, unknown>;

const packages = resolve(repositoryRoot, "fixtures", "packages", timetoshare.SCHEMA_VERSION);
const read = (path: string): JsonObject =>
  timetoshare.loads(readFileSync(path, "utf8")) as JsonObject;
const accepted = readdirSync(resolve(packages, "acceptances")).sort();
const cases = readdirSync(resolve(packages, "rejections")).sort();
const directories = [
  "shared",
  ...accepted.map((name) => `acceptances/${name}`),
  ...cases.map((name) => `rejections/${name}`),
];
/** The rejected packages whose one problem is `package.yaml`'s own. */
const refusedListings = ["rejections/folder_with_size", "rejections/table_listed_twice"];

/** What `call` throws: a `SchemaValidationError`'s code, path and message. */
function refusal(call: () => void): [string, readonly (string | number)[], string] | undefined {
  try {
    call();
  } catch (error) {
    const problem = error as timetoshare.SchemaValidationError;
    return [problem.code, problem.path, problem.detail];
  }
  return undefined;
}

const smallest = { timetoshare: "0.2.0", manifests: [], tables: [] };
const withManifest = (members: Node): Node => ({
  timetoshare: "0.2.0",
  manifests: [{ url: "a.yaml" }],
  tables: [],
  ...members,
});
const FOLDER = { type: "Note", url: "tables/Note/" };
const FILE = { type: "MatchClaim", url: "match_claims.parquet" };
const DIGEST = { algorithm: "SHA-256", digest: "00ff" };

describe("validatePackage", () => {
  it.each(directories)("reads the package.yaml of %s", (directory) => {
    const value = read(resolve(packages, directory, "package.yaml"));
    if (refusedListings.includes(directory)) {
      const [expected] = read(resolve(packages, directory, "expected.yaml")).problems as Node[];
      expect(refusal(() => timetoshare.validatePackage(value))).toEqual([
        expected?.code,
        expected?.path,
        expected?.message,
      ]);
    } else {
      expect(refusal(() => timetoshare.validatePackage(value))).toBeUndefined();
    }
    for (const entry of value.manifests as Node[]) {
      const manifest = read(resolve(packages, directory, entry.url as string));
      expect(() => timetoshare.validate(manifest)).not.toThrow();
    }
  });

  it("names the accepted packages", () => {
    expect(accepted).toEqual([
      "external_location",
      "re_parsable_event",
      "recording_resource",
      "timeline_in_two_manifests",
    ]);
  });

  it("names the rejected packages", () => {
    expect(cases).toEqual([
      "axis_mismatch",
      "claim_across_manifests",
      "column_in_two_types",
      "file_in_a_listed_folder",
      "file_of_another_type",
      "folder_with_size",
      "foreign_table",
      "locator_twice",
      "missing_content",
      "non_event_row_with_a_position",
      "parse_table_listed_twice",
      "projection_of_its_own_timeline",
      "projection_of_no_timeline",
      "projection_of_on_another_kind",
      "registry_folder",
      "registry_id_twice",
      "registry_listed_twice",
      "registry_missing",
      "resource_naming_no_table",
      "row_of_no_manifest",
      "stale_non_event_row",
      "table_listed_twice",
      "timeline_unlisted",
      "unknown_location",
      "unknown_parse",
      "unregistered_id",
      "vanished_in_an_unknown_parse",
      "version_mismatch",
    ]);
  });

  it("accepts the smallest package and a file with a size and an integrity", () => {
    expect(refusal(() => timetoshare.validatePackage(smallest))).toBeUndefined();
    const file = withManifest({ tables: [{ ...FILE, size: 1024, integrity: DIGEST }] });
    expect(refusal(() => timetoshare.validatePackage(file))).toBeUndefined();
  });

  it("accepts one url under two types", () => {
    const value = withManifest({ tables: [FOLDER, { ...FOLDER, type: "Box" }] });
    expect(refusal(() => timetoshare.validatePackage(value))).toBeUndefined();
  });

  it.each([
    [{ manifests: [], tables: [] }, ["not_a_package", [], "not a TimeToShare package"]],
    [[], ["not_a_package", [], "not a TimeToShare package"]],
    [{ timetoshare: "0.2.0", manifests: [] }, ["schema", [], "'tables' is a required property"]],
    [
      withManifest({ tables: [{ url: "x.parquet" }] }),
      ["schema", ["tables", 0], "'type' is a required property"],
    ],
    [
      withManifest({ manifests: [{ url: "a.yaml", size: -1 }] }),
      ["schema", ["manifests", 0, "size"], "-1 is less than the minimum of 0"],
    ],
    [
      withManifest({ manifests: [{ url: "a.yaml" }, { url: "a.yaml" }] }),
      [
        "duplicate_url",
        ["manifests", 1, "url"],
        "the manifest 'a.yaml' is listed twice, first at #/manifests/0/url",
      ],
    ],
    [
      withManifest({ tables: [FOLDER, FOLDER] }),
      [
        "duplicate_url",
        ["tables", 1, "url"],
        "the table 'tables/Note/' of the type Note is listed twice, first at #/tables/0/url",
      ],
    ],
    [
      withManifest({ tables: [FILE, { ...FOLDER, size: 1024 }] }),
      [
        "folder_descriptor",
        ["tables", 1, "size"],
        "'tables/Note/' names a folder, which has no size",
      ],
    ],
    [
      withManifest({ tables: [{ ...FOLDER, integrity: DIGEST }] }),
      [
        "folder_descriptor",
        ["tables", 0, "integrity"],
        "'tables/Note/' names a folder, which has no integrity",
      ],
    ],
    [
      withManifest({ manifests: [{ url: "manifests/", size: 3 }] }),
      [
        "folder_descriptor",
        ["manifests", 0, "size"],
        "'manifests/' names a folder, which has no size",
      ],
    ],
  ])("refuses %j", (value, expected) => {
    expect(refusal(() => timetoshare.validatePackage(value))).toEqual(expected);
  });

  it("refuses another version as Python does", () => {
    expect(() => timetoshare.validatePackage(withManifest({ timetoshare: "0.1.0" }))).toThrow(
      new timetoshare.UnsupportedVersionError("0.1.0"),
    );
    expect(new timetoshare.UnsupportedVersionError("0.1.0").message).toBe(
      'unsupported TimeToShare version "0.1.0"; this package reads 0.2.0 only',
    );
  });
});

describe("the package schema", () => {
  /** Every node below `value`. */
  function nodes(value: unknown): unknown[] {
    if (Array.isArray(value)) return [value, ...value.flatMap(nodes)];
    if (typeof value === "object" && value !== null) {
      return [value, ...Object.values(value).flatMap(nodes)];
    }
    return [value];
  }

  it("is bundled with the definitions it reaches", () => {
    const definitions = (packageSchema as Node).$defs as Node;
    const manifestDefinitions = (schema as Node).$defs as Node;
    expect(Object.keys(definitions)).toEqual([
      "Table",
      "Descriptor",
      "Name",
      "Meta",
      "IriReference",
    ]);
    for (const name of ["Descriptor", "Name", "Meta", "IriReference"]) {
      expect(definitions[name]).toEqual(manifestDefinitions[name]);
    }
    const references = nodes(packageSchema)
      .filter((node): node is Node => typeof node === "object" && node !== null && "$ref" in node)
      .map((node) => node.$ref as string);
    expect(references.length).toBeGreaterThan(0);
    for (const reference of references) {
      expect(reference.startsWith("#/$defs/")).toBe(true);
      expect(Object.hasOwn(definitions, reference.slice("#/$defs/".length))).toBe(true);
    }
    const file = read(resolve(repositoryRoot, "schema", "0.2.0", "package.schema.json"));
    expect(plain(bundlePackageSchema(file, loadSchemaFile()))).toEqual(packageSchema);
  });

  it("refuses a reference elsewhere and a definition of a name it reaches", () => {
    expect(() =>
      bundlePackageSchema(
        { properties: { a: { $ref: "https://example.org/other.json" } } },
        schema as Node,
      ),
    ).toThrow(
      "reference 'https://example.org/other.json' leads to no definition of the manifest schema",
    );
    expect(() =>
      bundlePackageSchema(
        {
          properties: { a: { $ref: "timetoshare.schema.json#/$defs/Descriptor" } },
          $defs: { Descriptor: {} },
        },
        schema as Node,
      ),
    ).toThrow("both schemas define 'Descriptor'");
  });
});
