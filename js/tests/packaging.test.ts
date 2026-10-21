import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import { SCHEMA_VERSION } from "../src/validate.js";
import { repositoryRoot } from "./fixtures.js";

const packageDirectory = resolve(repositoryRoot, "js");

/** The files `npm pack` would ship, after refreshing the copied assets once. */
let shipped: string[] = [];
/** The name and version `npm pack` reports. */
let packed = { name: "", version: "" };

describe("the npm package", () => {
  beforeAll(() => {
    execFileSync(process.execPath, ["scripts/copy-assets.ts"], { cwd: packageDirectory });
    const [report] = JSON.parse(
      execFileSync("npm", ["pack", "--dry-run", "--json", "--ignore-scripts"], {
        cwd: packageDirectory,
        encoding: "utf8",
      }),
    ) as [{ name: string; version: string; files: { path: string }[] }];
    shipped = report.files.map((file) => file.path);
    packed = { name: report.name, version: report.version };
  }, 120_000);

  it("is named for the format and versioned as its schema", () => {
    expect(packed).toEqual({ name: "@timetoalign/timetoshare", version: SCHEMA_VERSION });
  });

  it("ships the drawing specification", () => {
    expect(shipped).toContain("docs/drawing.md");
    expect(readFileSync(resolve(packageDirectory, "docs", "drawing.md"))).toEqual(
      readFileSync(resolve(repositoryRoot, "docs", "drawing.md")),
    );
    const manifest = JSON.parse(readFileSync(resolve(packageDirectory, "package.json"), "utf8"));
    expect(manifest.exports["./docs/*"]).toBe("./docs/*");
  });

  it("ships the schema document", () => {
    const path = "schema/0.1.0/timetoshare.schema.json";
    expect(shipped).toContain(path);
    expect(shipped.filter((file) => file.startsWith("schema/"))).toEqual([path]);
    expect(readFileSync(resolve(packageDirectory, path))).toEqual(
      readFileSync(resolve(repositoryRoot, path)),
    );
  });

  it("ships the repository's licence", () => {
    expect(shipped).toContain("LICENSE");
    expect(readFileSync(resolve(packageDirectory, "LICENSE"))).toEqual(
      readFileSync(resolve(repositoryRoot, "LICENSE")),
    );
  });
});
