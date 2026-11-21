/**
 * The unit table: every unit's domain, modality, default number type and
 * admitted number types, in the schema's order of `TimeUnit`. A discrete unit
 * admits `int` only, a continuous unit `float` or `fraction`, and `number`
 * all three. Python's `timetoshare.UNITS` holds the same table.
 */

import type { NumberType, TimeUnit } from "../generated/types.js";

/** One row of the unit table. */
export interface UnitEntry {
  /** `logical` (musical time), `physical` (real time) or `graphical` (space). */
  readonly domain: "logical" | "physical" | "graphical";
  readonly modality: "continuous" | "discrete";
  /** The default number type of an axis declaring none. */
  readonly numberType: NumberType;
  /** The number types the unit admits, in the order `int`, `float`, `fraction`. */
  readonly numberTypes: readonly NumberType[];
}

const DISCRETE: readonly NumberType[] = ["int"];
const CONTINUOUS: readonly NumberType[] = ["float", "fraction"];

function unit(
  domain: UnitEntry["domain"],
  modality: UnitEntry["modality"],
  numberType: NumberType,
  numberTypes: readonly NumberType[],
): UnitEntry {
  return Object.freeze({ domain, modality, numberType, numberTypes });
}

/** The unit table, keyed by unit in the schema's order of `TimeUnit`. */
export const UNITS: Readonly<Record<TimeUnit, UnitEntry>> = Object.freeze({
  number: unit("logical", "continuous", "float", ["int", ...CONTINUOUS]),
  floating_measures: unit("logical", "continuous", "float", CONTINUOUS),
  whole_notes: unit("logical", "continuous", "fraction", CONTINUOUS),
  quarters: unit("logical", "continuous", "fraction", CONTINUOUS),
  ticks: unit("logical", "discrete", "int", DISCRETE),
  milliseconds: unit("physical", "continuous", "float", CONTINUOUS),
  seconds: unit("physical", "continuous", "float", CONTINUOUS),
  minutes: unit("physical", "continuous", "float", CONTINUOUS),
  samples: unit("physical", "discrete", "int", DISCRETE),
  frames: unit("physical", "discrete", "int", DISCRETE),
  pixels: unit("graphical", "discrete", "int", DISCRETE),
  meters: unit("graphical", "continuous", "float", CONTINUOUS),
  centimeters: unit("graphical", "continuous", "float", CONTINUOUS),
  millimeters: unit("graphical", "continuous", "float", CONTINUOUS),
  inches: unit("graphical", "continuous", "float", CONTINUOUS),
  points: unit("graphical", "continuous", "float", CONTINUOUS),
  css_pixels: unit("graphical", "continuous", "float", CONTINUOUS),
  user_units: unit("graphical", "continuous", "float", CONTINUOUS),
});

/** Whether a value is a unit of the table. */
export function isUnit(value: unknown): value is TimeUnit {
  return typeof value === "string" && Object.hasOwn(UNITS, value);
}
