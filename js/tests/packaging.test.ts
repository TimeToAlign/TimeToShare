import { execFileSync, execSync } from "node:child_process";
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

/** Whether the package directory's copy of a repository file holds the same bytes. */
const copied = (path: string): boolean =>
  readFileSync(resolve(packageDirectory, path)).equals(readFileSync(resolve(repositoryRoot, path)));

describe("the npm package", () => {
  beforeAll(() => {
    execFileSync(process.execPath, ["scripts/copy-assets.ts"], { cwd: packageDirectory });
    // Through the shell: on Windows `npm` is the script `npm.cmd`, which Node
    // starts only through a shell; the command line is fixed.
    const [report] = JSON.parse(
      execSync("npm pack --dry-run --json --ignore-scripts", {
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
    expect(copied("docs/drawing.md")).toBe(true);
    const manifest = JSON.parse(readFileSync(resolve(packageDirectory, "package.json"), "utf8"));
    expect(manifest.exports["./docs/*"]).toBe("./docs/*");
  });

  it("ships the schema document", () => {
    const path = "schema/0.2.0/timetoshare.schema.json";
    expect(shipped).toContain(path);
    expect(shipped.filter((file) => file.startsWith("schema/"))).toEqual([path]);
    expect(copied(path)).toBe(true);
  });

  it("ships the catalogue and its schema", () => {
    const paths = ["catalogue/catalogue.schema.json", "catalogue/catalogue.yaml"];
    expect(shipped.filter((file) => file.startsWith("catalogue/")).sort()).toEqual(paths);
    for (const path of paths) expect(copied(path), path).toBe(true);
    expect(shipped.filter((file) => file.startsWith("registry/"))).toEqual([]);
    const manifest = JSON.parse(readFileSync(resolve(packageDirectory, "package.json"), "utf8"));
    expect(manifest.exports["./catalogue/*"]).toBe("./catalogue/*");
    expect(manifest.exports["./registry/*"]).toBeUndefined();
  });

  it("ships both fonts, their licences and the metrics table", () => {
    const fonts = [
      "fonts/DejaVuSans-LICENSE",
      "fonts/DejaVuSans.ttf",
      "fonts/NotoMusic-LICENSE",
      "fonts/NotoMusic-Regular.ttf",
      "fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json",
    ];
    expect(shipped.filter((file) => file.startsWith("fonts/")).sort()).toEqual(fonts);
    for (const path of fonts) expect(copied(path), path).toBe(true);
  });

  it("ships the repository's licence", () => {
    expect(shipped).toContain("LICENSE");
    expect(copied("LICENSE")).toBe(true);
  });
});
