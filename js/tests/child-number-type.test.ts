/**
 * Test strategy of the rule `child_number_type`: a child timeline has its
 * parent's number type, the declared one or the unit's default. The rule is
 * proved on inline manifests that differ from each other in the one thing under
 * test: (1) a child declaring a number type other than its parent's, reported at
 * the child's `number_type`; (2) a child declaring none whose unit's default
 * differs from the parent's declared type, reported at the child's `unit`;
 * (3) a parent and child that agree, by declaration, by default or mixed,
 * accepted; (4) a child that breaks both rules, reported by `child_unit` first
 * and then by `child_number_type`; (5) a grandchild checked against its own
 * parent, not the root. Every expected path and message is spelled out.
 */

import { describe, expect, it } from "vitest";
import { JsonFloat, SchemaValidationError } from "../src/index.js";
import type { JsonObject } from "../src/json/value.js";
import { identityProblems, manifest, timeline, validate } from "./fixtures.js";

type Found = [string, readonly (string | number)[], string];

function found(value: JsonObject): Found[] {
  return identityProblems(value).map((problem) => [problem.code, problem.path, problem.detail]);
}

/** The one problem of a value, which `validate` raises too. */
function only(value: JsonObject): Found {
  const problems = found(value);
  expect(problems.length).toBe(1);
  let raised: unknown;
  try {
    validate(value);
  } catch (error) {
    raised = error;
  }
  expect(raised).toBeInstanceOf(SchemaValidationError);
  const error = raised as SchemaValidationError;
  expect([error.code, error.path, error.detail]).toEqual(problems[0]);
  return problems[0] as Found;
}

const floatRoot = (children: JsonObject[]): JsonObject =>
  manifest([timeline("score", "quarters", new JsonFloat(8), { number_type: "float", children })]);

describe("child_number_type", () => {
  it("rejects a fraction child under a float root, at the child's number_type", () => {
    const value = floatRoot([
      timeline("verse", "quarters", [4, 1], {
        number_type: "fraction",
        offset: new JsonFloat(2),
      }),
    ]);
    expect(only(value)).toEqual([
      "child_number_type",
      ["timelines", 0, "children", 0, "number_type"],
      "child 'verse' has the number type 'fraction', its parent 'score' has 'float'",
    ]);
  });

  it("rejects a child without number_type whose unit default differs, at the child's unit", () => {
    const value = floatRoot([timeline("verse", "quarters", [4, 1], { offset: new JsonFloat(2) })]);
    expect(only(value)).toEqual([
      "child_number_type",
      ["timelines", 0, "children", 0, "unit"],
      "child 'verse' has the number type 'fraction', its parent 'score' has 'float'",
    ]);
  });

  it("takes the parent's type from its unit where it declares none", () => {
    const value = manifest([
      timeline("score", "quarters", [8, 1], {
        children: [
          timeline("verse", "quarters", new JsonFloat(4), {
            number_type: "float",
            offset: [2, 1],
          }),
        ],
      }),
    ]);
    expect(only(value)).toEqual([
      "child_number_type",
      ["timelines", 0, "children", 0, "number_type"],
      "child 'verse' has the number type 'float', its parent 'score' has 'fraction'",
    ]);
  });

  it("accepts a child of the parent's number type, declared, defaulted or mixed", () => {
    const declared = floatRoot([
      timeline("verse", "quarters", new JsonFloat(4), {
        number_type: "float",
        offset: new JsonFloat(2),
      }),
    ]);
    const defaulted = manifest([
      timeline("score", "quarters", [8, 1], {
        children: [timeline("verse", "quarters", [4, 1], { offset: [2, 1] })],
      }),
    ]);
    const mixed = manifest([
      timeline("score", "quarters", [8, 1], {
        number_type: "fraction",
        children: [timeline("verse", "quarters", [4, 1], { offset: [2, 1] })],
      }),
    ]);
    for (const value of [declared, defaulted, mixed]) {
      expect(found(value)).toEqual([]);
      expect(() => validate(value)).not.toThrow();
    }
  });

  it("reports child_unit, then child_number_type, for a child on another unit and type", () => {
    const value = manifest([
      timeline("score", "quarters", [8, 1], {
        children: [timeline("take", "milliseconds", new JsonFloat(4), { offset: [2, 1] })],
      }),
    ]);
    expect(found(value)).toEqual([
      [
        "child_unit",
        ["timelines", 0, "children", 0, "unit"],
        "child 'take' has unit 'milliseconds', its parent 'score' has 'quarters'",
      ],
      [
        "child_number_type",
        ["timelines", 0, "children", 0, "unit"],
        "child 'take' has the number type 'float', its parent 'score' has 'fraction'",
      ],
    ]);
  });

  it("checks a grandchild against its own parent", () => {
    const value = floatRoot([
      timeline("verse", "quarters", new JsonFloat(4), {
        number_type: "float",
        offset: new JsonFloat(2),
        children: [
          timeline("line", "quarters", [1, 1], {
            number_type: "fraction",
            offset: new JsonFloat(0),
          }),
        ],
      }),
    ]);
    expect(only(value)).toEqual([
      "child_number_type",
      ["timelines", 0, "children", 0, "children", 0, "number_type"],
      "child 'line' has the number type 'fraction', its parent 'verse' has 'float'",
    ]);
  });
});
