import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect } from "vitest";
import * as timetoshare from "../src/index.js";
import {
  dumps,
  isJsonObject,
  type Json,
  JsonFloat,
  type Lossless,
  loads,
  type PathSegment,
  SCHEMA_VERSION,
  serializationOf,
  withFileIds,
} from "../src/index.js";
import type { JsonObject } from "../src/json/value.js";

const here = dirname(fileURLToPath(import.meta.url));

/** The repository root, which holds the only copies of `schema/` and `fixtures/`. */
export const repositoryRoot = resolve(here, "../..");

/** The directory of the manifest fixtures. */
export const fixtureDirectory = resolve(repositoryRoot, "fixtures", SCHEMA_VERSION);

/** The extensions a stored text may have: it is found by its name, in either. */
const EXTENSIONS = [".yaml", ".json"] as const;

/** A file's name without its extension, or `null` for a file of another kind. */
function stem(name: string): string | null {
  const extension = EXTENSIONS.find((candidate) => name.endsWith(candidate));
  return extension === undefined ? null : name.slice(0, -extension.length);
}

/** The text of the file `name` (without extension) in `directory`, whatever its extension. */
export function storedText(directory: string, name: string): string {
  for (const extension of EXTENSIONS) {
    const path = resolve(directory, `${name}${extension}`);
    if (existsSync(path)) return readFileSync(path, "utf8");
  }
  throw new Error(`no file ${name} in ${directory}`);
}

/** The names, without extension, of the stored texts in `directory`, sorted. */
function storedNames(directory: string): string[] {
  return readdirSync(directory)
    .map(stem)
    .filter((name): name is string => name !== null)
    .sort();
}

/**
 * The manifest fixtures, as paths relative to `fixtureDirectory` without
 * their extension (`bare`, `bare.minimal`, `bundles/…`), sorted: every text
 * below it except the drawings.
 */
export function fixtureFiles(directory = ""): string[] {
  const files: string[] = [];
  for (const name of readdirSync(resolve(fixtureDirectory, directory)).sort()) {
    const path = join(directory, name).replaceAll("\\", "/");
    if (statSync(resolve(fixtureDirectory, path)).isDirectory()) {
      if (path !== "drawings") files.push(...fixtureFiles(path));
    } else {
      const named = stem(path);
      if (named !== null) files.push(named);
    }
  }
  return files.sort();
}

/** The text of one fixture, by its path relative to `fixtureDirectory` without extension. */
export function fixtureText(path: string): string {
  return storedText(fixtureDirectory, path);
}

function caseDirectory(kind: "rejections" | "warnings"): string {
  return resolve(repositoryRoot, "fixtures", kind, SCHEMA_VERSION);
}

/** The names of the rejection cases, without extension. */
export function rejectionFileNames(): string[] {
  return storedNames(caseDirectory("rejections"));
}

/** The text of one rejection case, by its name without extension. */
export function rejectionText(name: string): string {
  return storedText(caseDirectory("rejections"), name);
}

/**
 * Assert that a stored text is what the writers write for its value, byte
 * for byte: a text in canonical YAML is `dumps`'s bytes, a text in JSON
 * those of `dumps` in pretty JSON.
 */
export function expectWrittenAsStored(text: string): void {
  const value = loads(text);
  const serialization = serializationOf(text) === "yaml" ? "yaml" : "json";
  expect(dumps(value, { serialization })).toBe(text);
}

/** One shared rejection case, read for validation. */
export interface RejectionCase {
  /** The value to validate, with any non-finite number in place. */
  readonly manifest: Lossless<Json>;
  /** Where the validator reports the problem. */
  readonly path: readonly PathSegment[];
  /** The rule's code, or `null` where the case raises an error without one. */
  readonly code: string | null;
  /** The error class where it is not `SchemaValidationError`, else `null`. */
  readonly error: string | null;
  /** The rule the case breaks, in words. */
  readonly reason: string;
}

type LosslessObject = { [key: string]: Lossless<Json> };

const NON_FINITE: ReadonlyMap<string, number> = new Map([
  ["NaN", Number.NaN],
  ["Infinity", Number.POSITIVE_INFINITY],
  ["-Infinity", Number.NEGATIVE_INFINITY],
]);

function isLosslessObject(value: Lossless<Json> | undefined): value is LosslessObject {
  return isJsonObject(value);
}

function member(owner: Lossless<Json>, segment: PathSegment, name: string): Lossless<Json> {
  const value = Array.isArray(owner)
    ? owner[Number(segment)]
    : isLosslessObject(owner)
      ? owner[String(segment)]
      : undefined;
  if (value === undefined) throw new Error(`${name}: the path names no value at ${segment}`);
  return value;
}

function stringOrNull(value: Lossless<Json> | undefined, key: string, name: string): string | null {
  if (value === undefined || value === null) return null;
  if (typeof value !== "string") throw new Error(`${name}: ${key} is not a string`);
  return value;
}

/**
 * Read one shared rejection case by its name, as Python's
 * `timetoshare.rejection_case` does. JSON holds no NaN and no infinity, so a
 * case about the finite rule stores a finite placeholder at its path and
 * names the value to put there under `non_finite`; the reader puts it in place.
 */
export function rejectionCase(name: string): RejectionCase {
  const read = loads(rejectionText(name));
  if (!isLosslessObject(read)) throw new Error(`${name}: a case is an object`);
  const { manifest, path, code, error, reason, non_finite: nonFinite } = read;
  if (manifest === undefined) throw new Error(`${name}: a case holds a manifest`);
  if (!Array.isArray(path)) throw new Error(`${name}: a case's path is a list`);
  const steps = path.map((step) => {
    if (typeof step !== "string" && typeof step !== "number") {
      throw new Error(`${name}: a path step is a key or an index`);
    }
    return step;
  });
  if (typeof reason !== "string") throw new Error(`${name}: a case states its reason`);
  if (nonFinite !== undefined) {
    const number = typeof nonFinite === "string" ? NON_FINITE.get(nonFinite) : undefined;
    if (number === undefined) {
      throw new Error(`${name}: ${String(nonFinite)} names no non-finite number`);
    }
    const last = steps.at(-1);
    if (last === undefined) throw new Error(`${name}: a non-finite case names a path`);
    const owner = steps.slice(0, -1).reduce((at, step) => member(at, step, name), manifest);
    if (Array.isArray(owner)) owner[Number(last)] = number;
    else if (isLosslessObject(owner)) owner[String(last)] = number;
    else throw new Error(`${name}: the path ends inside a scalar`);
  }
  return {
    manifest,
    path: steps,
    code: stringOrNull(code, "code", name),
    error: stringOrNull(error, "error", name),
    reason,
  };
}

/** The names of the warning cases, without extension. */
export function warningFileNames(): string[] {
  return storedNames(caseDirectory("warnings"));
}

/** The text of one warning case, by its name without extension. */
export function warningText(name: string): string {
  return storedText(caseDirectory("warnings"), name);
}

/** Parse the schema document from the repository root. */
export function loadSchemaFile(): Record<string, unknown> {
  const path = resolve(repositoryRoot, "schema", SCHEMA_VERSION, "timetoshare.schema.json");
  return loads(readFileSync(path, "utf8")) as Record<string, unknown>;
}

/** A timeline of the minimal form. */
export function timeline(
  id: string,
  unit = "quarters",
  length: unknown = [8, 1],
  members: JsonObject = {},
): JsonObject {
  return { id, unit, length, ...members };
}

/** A manifest of the given roots in the minimal form. */
export function manifest(timelines: JsonObject[], members: JsonObject = {}): JsonObject {
  return { timetoshare: "0.2.0", timelines, ...members };
}

export function group(id: string, members: string[], rest: JsonObject = {}): JsonObject {
  return { id, members, ...rest };
}

function respellableManifest(canonical: boolean): JsonObject {
  const number = (written: unknown, spelled: unknown) => (canonical ? spelled : written);
  const float = (value: number) => new JsonFloat(value);
  return manifest(
    [
      timeline("midi", "ticks", number(float(480), 480), {
        children: [timeline("b", "ticks", 120, { offset: number(float(240), 240) })],
      }),
      timeline("score", "quarters", [32, number(float(1), 1)], {
        children: [timeline("a", "quarters", [4, 1], { offset: [number(float(8), 8), 1] })],
        conversion_maps: [
          {
            type: "ChainMap",
            id: "chain",
            source_unit: "quarters",
            target_unit: "seconds",
            maps: [
              {
                type: "TableMap",
                id: "table",
                source_unit: "quarters",
                target_unit: "seconds",
                x_values: [
                  [0, 1],
                  [float(1), 2],
                ],
                y_values: [float(0), 0.5],
                kind: "linear",
                extrapolate: "none",
              },
            ],
          },
          {
            type: "LinearMap",
            id: "linear",
            source_unit: "quarters",
            target_unit: "seconds",
            scalar: float(1),
            offset: [0, float(1)],
          },
        ],
        regions: [{ id: "r", start: [0, number(float(1), 1)], end: [number(float(1), 1), 2] }],
        flow_control: [
          {
            id: "m",
            type: "jump_to",
            manifestation: "segno",
            coordinate: [number(float(2), 2), 1],
          },
        ],
      }),
      timeline("take", "seconds", number(60, float(60)), {
        regions: [{ id: "s", start: number(0, float(0)), end: 1.5 }],
      }),
    ],
    {
      measure_maps: [
        {
          id: "bars",
          rows: [
            {
              count: 1,
              qstamp: [0, float(1)],
              actual_length: [float(4), 1],
              nominal_length: float(4),
            },
          ],
        },
      ],
    },
  );
}

/**
 * Python's `respellable()`: a manifest in canonical order whose own-axis
 * values are spelled unlike their number types, integral floats as
 * `JsonFloat`s, beside conversion-map numbers and MeasureMap rows, which no
 * number type governs and which are written as given.
 */
export function respellable(): JsonObject {
  return respellableManifest(false);
}

/** `respellable()` with every own-axis value spelled as its number type selects. */
export function respelled(): JsonObject {
  return respellableManifest(true);
}

/** A named manifest: two groups, two ungrouped roots, a child as a member. */
export function bundle(): JsonObject {
  return manifest(
    [
      timeline("annotations"),
      timeline("page", "pixels", 1200),
      timeline("performance", "seconds", 61.5),
      timeline("recording", "seconds", 120.5, {
        children: [timeline("excerpt", "seconds", 30.5, { offset: 2.5 })],
      }),
      timeline("score"),
    ],
    {
      id: "op35",
      name: "Mixed",
      groups: [group("group_1", ["performance", "score"]), group("group_2", ["excerpt", "page"])],
      graphical: { order: { group_1: ["score", "performance"], group_2: ["page", "excerpt"] } },
    },
  );
}

// The inline documents of this suite write IDs bare, as in memory; a check
// reads a manifest file, so these wrappers hand it the file form, every ID
// written '#' + the ID (`withFileIds`, proven in `ids.test.ts`).

/** The file form of an inline document; any other value as it is. */
export function filed(value: unknown): unknown {
  return isJsonObject(value) ? withFileIds(value) : value;
}

/** `validate` of the file form of an inline document. */
export function validate(value: unknown): void {
  timetoshare.validate(filed(value));
}

export function unknownKeys(value: unknown): timetoshare.UnknownKey[] {
  return timetoshare.unknownKeys(filed(value));
}

export function manifestWarnings(value: unknown): timetoshare.ManifestWarning[] {
  return timetoshare.manifestWarnings(filed(value));
}

export function identityProblems(value: JsonObject): timetoshare.SchemaValidationError[] {
  return timetoshare.identityProblems(filed(value) as JsonObject);
}

export function statementProblems(value: JsonObject): timetoshare.SchemaValidationError[] {
  return timetoshare.statementProblems(filed(value) as JsonObject);
}
