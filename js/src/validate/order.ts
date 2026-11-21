import { isJsonObject, type JsonObject } from "../json/value.js";
import { compareCodePoints } from "../serialization/text.js";
import { entries, type PathSegment, SchemaValidationError } from "./diagnostics.js";

/**
 * Yield each entry of `order` that `expected` lacks, then each entry of
 * `required` (all of `expected` where it is absent) that `order` lacks, in the
 * order of `expected`.
 */
function* listingProblems(
  code: "display_order" | "band_order",
  order: readonly string[],
  expected: readonly string[],
  path: readonly PathSegment[],
  stranger: (entry: string) => string,
  missing: (item: string) => string,
  required: readonly string[] = expected,
): Generator<SchemaValidationError> {
  const wanted = new Set(expected);
  const listed = new Set(order);
  const needed = new Set(required);
  for (const [index, entry] of order.entries()) {
    if (!wanted.has(entry)) {
      yield new SchemaValidationError(code, [...path, index], stranger(entry));
    }
  }
  for (const item of expected) {
    if (needed.has(item) && !listed.has(item)) {
      yield new SchemaValidationError(code, path, missing(item));
    }
  }
}

function* displayOrderProblems(
  group: JsonObject,
  order: readonly string[],
  path: readonly PathSegment[],
): Generator<SchemaValidationError> {
  const id = `'${group.id}'`;
  yield* listingProblems(
    "display_order",
    order,
    group.members as string[],
    path,
    (entry) => `'${entry}' is not a member of group ${id}`,
    (member) => `member '${member}' of group ${id} is missing`,
  );
}

/** The band order of a root without an entry: `line` and the five facets. */
const DEFAULT_BAND_ORDER: readonly string[] = [
  "children",
  "conversion_maps",
  "line",
  "markers",
  "regions",
  "flow_control",
];

/**
 * A band order lists `line` and any of the five facets, each once; a facet it
 * leaves out takes its place from the order the timeline follows without an
 * entry.
 */
function* bandOrderProblems(
  timeline: string,
  order: readonly string[],
  path: readonly PathSegment[],
): Generator<SchemaValidationError> {
  const id = `'${timeline}'`;
  yield* listingProblems(
    "band_order",
    order,
    DEFAULT_BAND_ORDER,
    path,
    (entry) => `'${entry}' is not 'line' or a facet, in the band order of ${id}`,
    (item) => `'${item}' is missing from the band order of ${id}`,
    ["line"],
  );
}

/**
 * Yield unknown order keys, display-order problems and band-order problems.
 *
 * `timelines` holds every timeline ID and `firstGroup` the index of the
 * first group of each group ID, as the identity rules collected them.
 */
export function* orderProblems(
  manifest: JsonObject,
  timelines: ReadonlyMap<string, unknown>,
  firstGroup: ReadonlyMap<string, number>,
): Generator<SchemaValidationError> {
  const groups = entries(manifest, "groups");
  const graphical = isJsonObject(manifest.graphical) ? manifest.graphical : {};
  const orders = isJsonObject(graphical.order) ? (graphical.order as Record<string, string[]>) : {};
  for (const key of Object.keys(orders).sort(compareCodePoints)) {
    const path = ["graphical", "order", key];
    const order = orders[key] ?? [];
    const index = firstGroup.get(key);
    if (index !== undefined) {
      yield* displayOrderProblems(groups[index] as JsonObject, order, path);
    } else if (timelines.has(key)) {
      yield* bandOrderProblems(key, order, path);
    } else {
      yield new SchemaValidationError(
        "order_key",
        path,
        `'${key}' names no group or timeline of this manifest`,
      );
    }
  }
}
