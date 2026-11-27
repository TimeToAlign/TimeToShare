import { describe, expect, it } from "vitest";
import * as api from "../src/index.js";
import { childEnds } from "../src/index.js";
import { JsonFloat, type JsonObject } from "../src/json/value.js";
import { exact, rational, sameRational } from "../src/numbers/exact.js";
import { identityProblems, manifest, timeline, validate } from "./fixtures.js";

type Problem = [readonly (string | number)[], string];

const ID = "segment line 'line'";
const AT = ["timelines", 0];

function segment(
  id: string,
  offset: unknown,
  length: unknown,
  unit = "quarters",
  rest: JsonObject = {},
): JsonObject {
  return timeline(id, unit, length, { offset, ...rest });
}

function line(segments: JsonObject[], length: unknown = [8, 1], unit = "quarters"): JsonObject {
  return manifest([timeline("line", unit, length, { is_segment_line: true, children: segments })]);
}

function problems(value: JsonObject): Problem[] {
  const found = identityProblems(value).map((p): Problem => [p.path, p.detail]);
  if (found.length === 0) validate(value);
  return found;
}

describe("segment lines", () => {
  it.each([
    ["two segments", line([segment("a", [0, 1], [3, 1]), segment("b", [3, 1], [5, 1])])],
    ["empty of length 0", line([], [0, 1])],
    ["empty of unknown length", line([], null)],
    ["offset order", line([segment("b", [3, 1], [5, 1]), segment("a", [0, 1], [3, 1])])],
    [
      "nested",
      line([
        segment("a", [0, 1], [4, 1], "quarters", {
          is_segment_line: true,
          children: [segment("a1", [0, 1], [1, 1]), segment("a2", [1, 1], [3, 1])],
        }),
        segment("b", [4, 1], [4, 1], "quarters", {
          is_segment_line: true,
          children: [segment("b1", [0, 1], [4, 1])],
        }),
      ]),
    ],
    [
      "exact floats",
      line(
        [
          segment("a", 0, 0.5, "seconds"),
          segment("b", 0.5, 0.25, "seconds"),
          segment("c", 0.75, 0.25, "seconds"),
        ],
        1,
        "seconds",
      ),
    ],
  ])("accepts %s", (_name, value) => {
    expect(problems(value)).toEqual([]);
  });

  it("reports each rule once", () => {
    expect(
      problems(line([segment("a", [0, 1], [3, 1]), segment("b", [3, 1], 5, "ticks")])),
    ).toEqual([
      [
        [...AT, "children", 1, "unit"],
        "child 'b' has unit 'ticks', its parent 'line' has 'quarters'",
      ],
      [
        [...AT, "children", 1, "unit"],
        "child 'b' has the number type 'int', its parent 'line' has 'fraction'",
      ],
    ]);
    expect(
      problems(
        line([
          segment("a", [0, 1], [3, 1]),
          segment("b", [3, 1], [5, 1], "quarters", { is_segment_line: true }),
        ]),
      ),
    ).toEqual([
      [
        [...AT, "children", 1, "is_segment_line"],
        `segment 'b' of ${ID} differs from segment 'a' in is_segment_line`,
      ],
      [
        [...AT, "children", 1, "length"],
        "the segments of segment line 'b' do not end at its length",
      ],
    ]);
    expect(
      problems(
        line([
          segment("a", [0, 1], [3, 1], "quarters", { is_segment_line: true }),
          segment("b", [3, 1], [5, 1]),
        ]),
      )[0],
    ).toEqual([
      [...AT, "children", 1],
      `segment 'b' of ${ID} differs from segment 'a' in is_segment_line`,
    ]);
    expect(problems(line([segment("a", [1, 1], [7, 1])]))).toEqual([
      [[...AT, "children", 0, "offset"], `segment 'a' of ${ID} does not start at 0`],
    ]);
    for (const start of [4, 2]) {
      expect(
        problems(line([segment("a", [0, 1], [3, 1]), segment("b", [start, 1], [8 - start, 1])])),
      ).toEqual([
        [
          [...AT, "children", 1, "offset"],
          `segment 'b' of ${ID} does not start where the one before it ends`,
        ],
      ]);
    }
    expect(problems(line([segment("a", [0, 1], [7, 1])]))).toEqual([
      [[...AT, "length"], `the segments of ${ID} do not end at its length`],
    ]);
    expect(problems(line([]))).toEqual([
      [[...AT, "length"], `the segments of ${ID} do not end at its length`],
    ]);
  });

  it("adds a float line as doubles", () => {
    const value = line(
      [
        segment("a", 0, 0.1, "seconds"),
        segment("b", 0.1, 0.2, "seconds"),
        segment("c", 0.3, 0.7, "seconds"),
      ],
      1,
      "seconds",
    );
    expect(0.1 + 0.2).toBe(0.30000000000000004);
    expect(0.3 + 0.7).toBe(1);
    expect(problems(value)).toEqual([
      [
        [...AT, "children", 2, "offset"],
        `segment 'c' of ${ID} does not start where the one before it ends`,
      ],
    ]);
  });

  it("lets the double sum decide where the exact one differs", () => {
    // 76.70371459980326 and 855.5289364103584 are doubles whose exact sum exceeds
    // 932.2326510101616 by 3/2^46 while their double sum equals it.
    const withB = (bOffset: unknown, bLength: unknown, bRest: JsonObject = {}) =>
      line(
        [
          segment("a", new JsonFloat(0), 76.70371459980326, "points"),
          segment("b", bOffset, bLength, "points", bRest),
          segment("c", 932.2326510101616, 67.7673489898384, "points"),
        ],
        new JsonFloat(1000),
        "points",
      );
    // Every value here is a whole number of 2^-46, so the exact sums compare as integers.
    const ulps = (value: number) => {
      const { numerator, denominator } = exact(value);
      return (numerator * 2n ** 46n) / denominator;
    };
    expect(76.70371459980326 + 855.5289364103584).toBe(932.2326510101616);
    expect(932.2326510101616 + 67.7673489898384).toBe(1000);
    expect(ulps(76.70371459980326) + ulps(855.5289364103584) - ulps(932.2326510101616)).toBe(3n);
    expect(ulps(1000) - ulps(932.2326510101616) - ulps(67.7673489898384)).toBe(1n);
    expect(problems(withB(76.70371459980326, 855.5289364103584))).toEqual([]);

    expect(76.70371459980326 + 2 ** -46).toBe(76.70371459980328);
    expect(76.70371459980328 + 855.5289364103584).toBe(932.2326510101616);
    expect(problems(withB(76.70371459980328, 855.5289364103584))).toEqual([
      [
        [...AT, "children", 1, "offset"],
        `segment 'b' of ${ID} does not start where the one before it ends`,
      ],
    ]);

    const pairs: [number, [number, number]][] = [
      [76.70371459980326, [5397544070150107, 70368744177664]],
      [855.5289364103584, [7525312107856185, 8796093022208]],
      [932.2326510101616, [2050001279156237, 2199023255552]],
      [67.7673489898384, [4768703244664415, 70368744177664]],
    ];
    expect(pairs.map(([, pair]) => exact(pair))).toEqual(pairs.map(([value]) => exact(value)));
    const [a, b, c, cLength] = pairs.map(([, pair]) => pair);
    const fraction = { number_type: "fraction" };
    const exactLine = manifest([
      timeline("line", "points", [1000, 1], {
        ...fraction,
        is_segment_line: true,
        children: [
          segment("a", [0, 1], a, "points", fraction),
          segment("b", a, b, "points", fraction),
          segment("c", c, cLength, "points", fraction),
        ],
      }),
    ]);
    expect(problems(exactLine)).toEqual([
      [
        [...AT, "children", 2, "offset"],
        `segment 'c' of ${ID} does not start where the one before it ends`,
      ],
      [[...AT, "length"], `the segments of ${ID} do not end at its length`],
    ]);
    // On the float line a length no double equals, the pair, is added exactly.
    expect(problems(withB(76.70371459980326, b))).toEqual([
      [
        [...AT, "children", 2, "offset"],
        `segment 'c' of ${ID} does not start where the one before it ends`,
      ],
    ]);
  });

  it("ends a segment without a double sum at the exact sum", () => {
    const huge = new JsonFloat(1e308);
    expect(1e308 + 1e308).toBe(Number.POSITIVE_INFINITY);
    const overflowing = line(
      [
        segment("a", new JsonFloat(0), huge, "points"),
        segment("b", huge, huge, "points"),
        segment("c", new JsonFloat(1.7976931348623157e308), new JsonFloat(1), "points"),
      ],
      null,
      "points",
    );
    expect(problems(overflowing)).toEqual([
      [
        [...AT, "children", 2, "offset"],
        `segment 'c' of ${ID} does not start where the one before it ends`,
      ],
    ]);
    const beyond = line(
      [
        segment("a", new JsonFloat(0), 10n ** 400n, "points"),
        segment("b", 10n ** 400n, new JsonFloat(1), "points"),
      ],
      null,
      "points",
    );
    expect(identityProblems(beyond)).toEqual([]);
    expect(() => validate(beyond)).toThrow(expect.objectContaining({ code: "representation" }));
  });

  it.each([
    ["unknown first", line([segment("a", [0, 1], null), segment("b", [5, 1], [3, 1])])],
    [
      "unknown first, late successor",
      line([segment("a", [0, 1], null), segment("b", [7, 1], [1, 1])]),
    ],
    ["unknown last", line([segment("a", [0, 1], [3, 1]), segment("b", [3, 1], null)])],
    ["unknown line", line([segment("a", [0, 1], [3, 1]), segment("b", [3, 1], [5, 1])], null)],
    [
      "unknown line, long segments",
      line([segment("a", [0, 1], [3, 1]), segment("b", [3, 1], [9, 1])], null),
    ],
  ])("skips what needs an unknown length: %s", (_name, value) => {
    expect(problems(value)).toEqual([]);
  });

  it("still checks contiguity on a line of unknown length", () => {
    expect(
      problems(line([segment("a", [0, 1], [3, 1]), segment("b", [4, 1], [4, 1])], null)),
    ).toEqual([
      [
        [...AT, "children", 1, "offset"],
        `segment 'b' of ${ID} does not start where the one before it ends`,
      ],
    ]);
  });

  it("reports in order, segment lines among the descendants at their own path", () => {
    const value = line([
      segment("a", [0, 1], [3, 1]),
      segment("b", [3, 1], 1, "ticks"),
      segment("c", [4, 1], [1, 1], "quarters", { is_segment_line: true }),
      segment("d", [5, 1], [1, 1], "quarters", { is_segment_line: true }),
    ]);
    expect(problems(value)).toEqual([
      [
        [...AT, "children", 1, "unit"],
        "child 'b' has unit 'ticks', its parent 'line' has 'quarters'",
      ],
      [
        [...AT, "children", 1, "unit"],
        "child 'b' has the number type 'int', its parent 'line' has 'fraction'",
      ],
      [
        [...AT, "children", 2, "is_segment_line"],
        `segment 'c' of ${ID} differs from segment 'a' in is_segment_line`,
      ],
      [
        [...AT, "children", 3, "is_segment_line"],
        `segment 'd' of ${ID} differs from segment 'a' in is_segment_line`,
      ],
      [[...AT, "length"], `the segments of ${ID} do not end at its length`],
      [
        [...AT, "children", 2, "length"],
        "the segments of segment line 'c' do not end at its length",
      ],
      [
        [...AT, "children", 3, "length"],
        "the segments of segment line 'd' do not end at its length",
      ],
    ]);
  });

  it("never checks a timeline that is no segment line", () => {
    const value = manifest([
      timeline("free", "quarters", [8, 1], {
        children: [timeline("x", "quarters", [1, 1], { offset: [5, 1] })],
      }),
    ]);
    expect(problems(value)).toEqual([]);
  });
});

describe("childEnds", () => {
  it("is public and adds floats as doubles", () => {
    expect(api.childEnds).toBe(childEnds);
    const line = timeline("line", "seconds", new JsonFloat(1), {
      children: [segment("a", new JsonFloat(0.1), new JsonFloat(0.2), "seconds")],
    });
    expect(childEnds(line)).toEqual([exact(0.1 + 0.2)]);
    const [a, b] = [exact(0.1), exact(0.2)];
    const exactSum = rational(
      a.numerator * b.denominator + b.numerator * a.denominator,
      a.denominator * b.denominator,
    );
    expect(sameRational(exact(0.1 + 0.2), exactSum)).toBe(false);
  });

  it("ends a segment of unknown length at its successor's offset", () => {
    const line = timeline("line", "quarters", [8, 1], {
      is_segment_line: true,
      children: [
        segment("a", [0, 1], [3, 1]),
        segment("c", [5, 1], [3, 1]),
        segment("b", [3, 1], null),
      ],
    });
    expect(childEnds(line)).toEqual([exact([3, 1]), exact([8, 1]), exact([5, 1])]);
  });
});
