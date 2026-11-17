import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { generate, generatedDirectory, schemaSource } from "../scripts/generate.js";
import { schemes } from "../src/generated/registry.js";
import { schema } from "../src/generated/schema.js";
import { dumps } from "../src/index.js";
import { repositoryRoot } from "./fixtures.js";

type Node = Record<string, unknown>;

/** The names a generated module exports, sorted. */
function exportsOf(text: string): string[] {
  return [...text.matchAll(/^export (?:interface|type|const) (\w+)/gm)]
    .map((match) => match[1] as string)
    .sort();
}

const committed = (name: string) => readFileSync(resolve(generatedDirectory, name), "utf8");
const defs = (schema as Node).$defs as Record<string, Node>;
const mapTypes = ((defs.ConversionMap as Node).oneOf as Node[]).map((branch) =>
  (branch.$ref as string).slice("#/$defs/".length),
);

describe("generated files", () => {
  it("export what a fresh run of the generator exports", async () => {
    const fresh = await generate();
    expect(Object.keys(fresh).sort()).toEqual(["font.ts", "registry.ts", "schema.ts", "types.ts"]);
    for (const [name, content] of Object.entries(fresh)) {
      expect(exportsOf(committed(name)), name).toEqual(exportsOf(content));
    }
  });

  it("bundle the registry file's entries", () => {
    expect(exportsOf(committed("registry.ts"))).toEqual(["schemes"]);
    const file = readFileSync(resolve(repositoryRoot, "registry", "schemes.json"), "utf8");
    expect(dumps(schemes)).toBe(file);
  });

  it("come from the one schema document", () => {
    expect(schemaSource()).toBe("0.2.0/timetoshare.schema.json");
  });

  it("export every definition and its complete form where it has defaults", () => {
    const definitions = Object.keys(defs);
    const completed = [
      "Manifest",
      "Timeline",
      "Group",
      "Graphical",
      "ConversionMap",
      "MapBase",
      "MeasureView",
      ...mapTypes,
      "Region",
      "FlowControlElement",
      "MeasureMap",
      "Timestamp",
      "Scheme",
      "Link",
      "Descriptor",
      "Assertion",
      "PartSlot",
      "PartOf",
    ];
    expect(exportsOf(committed("types.ts"))).toEqual(
      [...definitions, ...completed.map((name) => `Complete${name}`), "LosslessManifest"].sort(),
    );
  });
});
