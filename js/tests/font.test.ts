import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { dumps, FONT_FILES, fontMetrics, loads } from "../src/index.js";
import { repositoryRoot } from "./fixtures.js";

const RELEASE_SHA256 = {
  "DejaVuSans.ttf": "7da195a74c55bef988d0d48f9508bd5d849425c1770dba5d7bfc6ce9ed848954",
  "NotoMusic-Regular.ttf": "26c0a28d7c6f96c70f1401db23066c5ea0ee1cdf155c79bc01ad2efb040de816",
} as const;
const METRICS_FILE = "dejavu-sans-2.37+noto-music-2.004.metrics.json";

function fontFile(name: string): Buffer {
  return readFileSync(resolve(repositoryRoot, "fonts", name));
}

describe("the bundled fonts", () => {
  it("are the upstream release files, in fallback order, with their licences", () => {
    expect(FONT_FILES).toEqual(["DejaVuSans.ttf", "NotoMusic-Regular.ttf"]);
    for (const name of FONT_FILES) {
      expect(createHash("sha256").update(fontFile(name)).digest("hex")).toBe(RELEASE_SHA256[name]);
    }
    expect(fontFile("DejaVuSans-LICENSE").byteLength).toBe(8816);
    expect(fontFile("NotoMusic-LICENSE").byteLength).toBe(4381);
  });

  it("are exported as a package subpath", () => {
    const manifest = loads(readFileSync(resolve(repositoryRoot, "js", "package.json"), "utf8"));
    const record = manifest as { exports: Record<string, string>; files: string[] };
    expect(record.exports["./fonts/*"]).toBe("./fonts/*");
    expect(record.files).toContain("fonts");
  });
});

describe("fontMetrics", () => {
  it("holds the stated values", () => {
    expect(Object.keys(fontMetrics)).toEqual([
      "advances",
      "ascender",
      "descender",
      "fallback",
      "units_per_em",
    ]);
    expect(fontMetrics.units_per_em).toBe(2048);
    expect(fontMetrics.ascender).toBe(1901);
    expect(fontMetrics.descender).toBe(483);
    expect(fontMetrics.fallback).toBe(1229);
    expect(Object.keys(fontMetrics.advances)).toHaveLength(6467);
    expect(fontMetrics.advances["9833"]).toBe(966);
    expect(fontMetrics.advances["48"]).toBe(1303);
    expect(fontMetrics.advances["32"]).toBe(651);
    expect(fontMetrics.advances["119133"]).toBe(1053);
    expect(fontMetrics.advances["119070"]).toBe(1456);
    expect(fontMetrics.advances["119135"]).toBe(819);
    expect(fontMetrics.advances["118784"]).toBe(973);
    expect(fontMetrics.advances["119296"]).toBe(1810);
  });

  it("equals the metrics file, written in pretty JSON", () => {
    const text = readFileSync(resolve(repositoryRoot, "fonts", METRICS_FILE), "utf8");
    expect(dumps(loads(text), { serialization: "json" })).toBe(text);
    expect(dumps(fontMetrics, { serialization: "json" })).toBe(text);
  });
});
