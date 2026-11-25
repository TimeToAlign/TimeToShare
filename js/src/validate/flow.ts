/**
 * Flow rules: flow control, FlowMaps and virtual timelines.
 *
 * The schema checks the shape of every flow-control element, FlowMap and
 * virtual timeline; the rules here reach beyond it.
 *
 * Before the schema, an element written in the earlier form of flow control
 * (the key `type` with `jump_from`, `jump_to` or `flow_marker`, or the key
 * `target`) is refused with the name of the converter (`flow_control_form`).
 *
 * After the schema, timeline by timeline, the rules read the elements that
 * are not rejected. An element is rejected when an entry of its `provenance`
 * holds a belief `false`: a repair rejects an element and adds another, so a
 * rejected jump and its replacement may share a coordinate. In document
 * order: a coordinate lies from 0 to the timeline's known length
 * (`flow_coordinate`); a root and its descendants have one jump at a
 * position on the root's axis, each coordinate carried to the root by
 * adding the offsets of its ancestors (`jump_repeated`); the destinations of a jump are distinct places
 * (`jump_destination`); a `to` names a jump target or a region of the
 * timeline, a child of it or the timeline itself (`dangling_target`); a place
 * reached by `by` lies from 0 to the known length (`flow_coordinate`); an
 * `after` names exactly one destination of another jump of the timeline
 * (`dangling_target`).
 *
 * Then the FlowMaps: `timeline` names a root (`flow_map_timeline`), every
 * chunk ID a region or a child timeline inside that root's tree, or a virtual
 * timeline of a timeline of it (`flow_map_chunk`), and at most one FlowMap of
 * a timeline is canonical (`flow_map_canonical`); and the virtual timelines:
 * `map` names a FlowMap or a conversion map, `timeline` a timeline or another
 * virtual timeline (`dangling_target`). A virtual timeline comes, virtual
 * timeline by virtual timeline, from a timeline: none comes from itself
 * through others. Where its `map` is a FlowMap and it states no `through`,
 * the timeline it comes from lies in the tree of the FlowMap's root, and its
 * `length` is the sum of the FlowMap's chunks and gaps where all of them lie
 * on its own axis (`virtual_timeline`); with `through` neither is read.
 *
 * A manifestation or a convention outside the format's vocabulary is valid:
 * `flowWarnings` reports it. Python's `timetoshare.validation.flow` holds the
 * same rules, tables and messages.
 */

import type { NumberType, TimeUnit } from "../generated/types.js";
import { isJsonObject, JsonFloat, type JsonObject } from "../json/value.js";
import {
  compareRationals,
  exact,
  exactNumber,
  type Rational,
  rational,
  sameRational,
} from "../numbers/exact.js";
import { spell } from "../serialization/text.js";
import {
  entries,
  jsonPointer,
  lengthOf,
  numberTypeOf,
  type PathSegment,
  SchemaValidationError,
  stringId,
  text,
  treeIds,
} from "./diagnostics.js";

/** The script that converts the earlier form of flow control, by its path in the TimeToShare repository. */
export const CONVERTER = "scripts/convert_flow_control.py";

/** The values of `type` in the earlier form of flow control. */
export const EARLIER_ROLES: readonly string[] = ["jump_from", "jump_to", "flow_marker"];

/**
 * The manifestations the format defines: of a jump's destination, and of an
 * element by its role. The vocabulary is open; any other word is reported as
 * unknown and never refused.
 */
export const MANIFESTATIONS: Readonly<Record<string, readonly string[]>> = {
  destination: [
    "repeat_end",
    "da_capo",
    "da_capo_al_fine",
    "da_capo_al_coda",
    "dal_segno",
    "dal_segno_al_fine",
    "dal_segno_al_coda",
    "to_coda",
    "volta",
    "ossia",
  ],
  jump_target: ["repeat_start", "segno", "coda", "volta", "ossia"],
  break: ["fine", "volta"],
  section_break: [],
  barline: ["double_barline", "final_barline"],
};

/** The conventions the format defines for a FlowMap; the vocabulary is open. */
export const CONVENTIONS: readonly string[] = ["default", "single", "printed"];

const NAMED: Readonly<Record<string, string>> = {
  destination: "a destination",
  jump_target: "a jump target",
  break: "a break",
  section_break: "a section break",
  barline: "a barline",
};

type Path = readonly PathSegment[];

function listed(owner: unknown, key: string): unknown[] {
  const value = isJsonObject(owner) ? owner[key] : undefined;
  return Array.isArray(value) ? value : [];
}

function bare(id: string): string {
  return id.startsWith("#") && id.length > 1 ? id.slice(1) : id;
}

function earlier(element: unknown): boolean {
  if (!isJsonObject(element)) return false;
  const { type, role } = element;
  return (
    (typeof type === "string" && EARLIER_ROLES.includes(type)) ||
    (typeof role === "string" && EARLIER_ROLES.includes(role)) ||
    (Object.hasOwn(element, "target") && !Object.hasOwn(element, "role"))
  );
}

function* earlierForm(timeline: unknown, path: Path): Generator<SchemaValidationError> {
  for (const [index, element] of listed(timeline, "flow_control").entries()) {
    if (!earlier(element)) continue;
    const at = [...path, "flow_control", index];
    const id = stringId(element);
    const named =
      id !== null
        ? `flow-control element '${bare(id)}'`
        : `the flow-control element at ${jsonPointer(at)}`;
    yield new SchemaValidationError(
      "flow_control_form",
      at,
      `${named} is written in the earlier form of flow control (type, target): convert the manifest with ${CONVERTER}`,
    );
  }
  for (const [index, child] of listed(timeline, "children").entries()) {
    yield* earlierForm(child, [...path, "children", index]);
  }
}

/**
 * Yield every flow-control element written in the earlier form: root by root,
 * each timeline's elements before its children's. The walk reads any value
 * and either form of an ID.
 */
export function* earlierFormProblems(manifest: unknown): Generator<SchemaValidationError> {
  for (const [index, root] of listed(manifest, "timelines").entries()) {
    yield* earlierForm(root, ["timelines", index]);
  }
}

/** Whether an entry of an element's provenance holds a belief `false`. */
export function rejected(element: unknown): boolean {
  return listed(element, "provenance").some((entry) =>
    listed(entry, "beliefs").some((belief) => isJsonObject(belief) && belief.belief === "false"),
  );
}

const ZERO = rational(0n, 1n);

function add(left: Rational, right: Rational): Rational {
  return rational(
    left.numerator * right.denominator + right.numerator * left.denominator,
    left.denominator * right.denominator,
  );
}

/** The double a reader reads from a JSON number, or `null` for none. */
function double(value: unknown): number | null {
  const number =
    value instanceof JsonFloat ? value.value : typeof value === "bigint" ? Number(value) : value;
  return typeof number === "number" && Number.isFinite(number) ? number : null;
}

type Axis = { unit: TimeUnit; number_type?: NumberType };

/**
 * Where a distance `by` from `coordinate` lands on the timeline's axis. On a
 * `float` axis the two JSON numbers are added as doubles, as a reader adds
 * them; on every other axis the sum is exact.
 */
function placeOf(timeline: JsonObject, coordinate: unknown, by: unknown): Rational {
  if (numberTypeOf(timeline as Axis) === "float") {
    const from = double(coordinate);
    const distance = double(by);
    if (from !== null && distance !== null && Number.isFinite(from + distance)) {
      return exactNumber(from + distance) as Rational;
    }
  }
  return add(exact(coordinate), exact(by));
}

/** The place of a destination or of a reference: its kind and what it is compared by. */
type Place =
  | { readonly kind: "to"; readonly id: unknown }
  | { readonly kind: "by"; readonly value: Rational }
  | { readonly kind: "" };

function placeKey(destination: JsonObject): Place {
  if (Object.hasOwn(destination, "to")) return { kind: "to", id: destination.to };
  if (Object.hasOwn(destination, "by")) return { kind: "by", value: exact(destination.by) };
  return { kind: "" };
}

function samePlace(left: Place, right: Place): boolean {
  if (left.kind === "to" && right.kind === "to") return left.id === right.id;
  if (left.kind === "by" && right.kind === "by") return sameRational(left.value, right.value);
  return left.kind === "" && right.kind === "";
}

function placeWords(destination: JsonObject): string {
  if (Object.hasOwn(destination, "to")) return `to '${destination.to}'`;
  if (Object.hasOwn(destination, "by")) return `by ${spell(destination.by)}`;
  return "without a place";
}

/** The problem of one `after`: it names one destination of another jump. */
function* afterProblems(
  after: JsonObject,
  path: Path,
  holder: string | null,
  jumps: ReadonlyMap<string, JsonObject>,
): Generator<SchemaValidationError> {
  const name = text(after, "jump");
  if (name === holder) {
    yield new SchemaValidationError(
      "dangling_target",
      [...path, "jump"],
      `'${name}' is the jump holding this destination; after names a destination of another jump`,
    );
    return;
  }
  const jump = jumps.get(name);
  if (jump === undefined) {
    yield new SchemaValidationError(
      "dangling_target",
      [...path, "jump"],
      `'${name}' names no jump of this timeline`,
    );
    return;
  }
  const destinations = entries(jump, "targets");
  for (const key of ["to", "by"]) {
    if (!Object.hasOwn(after, key)) continue;
    const named = { [key]: after[key] };
    const wanted = placeKey(named);
    const found = destinations.filter((entry) => samePlace(placeKey(entry), wanted)).length;
    if (found !== 1) {
      yield new SchemaValidationError(
        "dangling_target",
        [...path, key],
        `jump '${name}' has no destination ${placeWords(named)}`,
      );
    }
    return;
  }
  const placeless = destinations.filter((entry) => placeKey(entry).kind === "").length;
  if (placeless !== 1 && destinations.length !== 1) {
    yield new SchemaValidationError(
      "dangling_target",
      path,
      `jump '${name}' has ${destinations.length} destinations and none without a place; after names one by its to or by`,
    );
  }
}

/**
 * The jumps of a root's tree by their exact position on the root's axis:
 * the ID of the first jump there and of the timeline stating it.
 */
export type JumpPositions = { position: Rational; id: string; timeline: string }[];

/** The start of a child on its root's axis: its parent's start plus its offset. */
export function childStart(start: Rational, child: JsonObject): Rational {
  return add(start, exact(child.offset));
}

/**
 * Yield the problems of one timeline's flow control, in document order: the
 * timeline's own elements only; its children are the caller's, who passes
 * `start`, the timeline's start on its root's axis (the sum of the offsets
 * from the root down), and one `jumpsAt` for the whole tree, so that a jump
 * at the position of an earlier jump of the root or of another descendant
 * is refused as one at a coordinate of its own timeline is.
 */
export function* timelineFlowProblems(
  timeline: JsonObject,
  path: Path,
  start: Rational = ZERO,
  jumpsAt: JumpPositions = [],
): Generator<SchemaValidationError> {
  const flow = entries(timeline, "flow_control");
  const read = [...flow.entries()].filter(([, entry]) => !rejected(entry));
  if (read.length === 0) return;
  const length = lengthOf(timeline);
  const end = length === null ? null : exact(length);
  const owner = text(timeline, "id");
  const jumps = new Map<string, JsonObject>();
  const places = new Set<string>();
  for (const [, entry] of read) {
    if (entry.role === "jump") jumps.set(text(entry, "id"), entry);
    if (entry.role === "jump_target") places.add(text(entry, "id"));
  }
  for (const region of entries(timeline, "regions")) places.add(text(region, "id"));
  for (const child of entries(timeline, "children")) places.add(text(child, "id"));
  places.add(owner);
  const outside = (value: Rational): boolean =>
    compareRationals(value, ZERO) < 0 || (end !== null && compareRationals(value, end) > 0);
  const beyond = (): string =>
    end === null ? "it lies before 0" : `it lies outside 0 to the length ${spell(length)}`;

  for (const [index, entry] of read) {
    const at = [...path, "flow_control", index];
    const id = text(entry, "id");
    const coordinate = exact(entry.coordinate);
    if (outside(coordinate)) {
      yield new SchemaValidationError(
        "flow_coordinate",
        [...at, "coordinate"],
        `coordinate ${spell(entry.coordinate)} of '${id}' is not on '${owner}': ${beyond()}`,
      );
    }
    const ends = entry.ends;
    if (entry.role === "break" && isJsonObject(ends) && isJsonObject(ends.after)) {
      yield* afterProblems(ends.after, [...at, "ends", "after"], null, jumps);
    }
    if (entry.role !== "jump") continue;
    const position = add(start, coordinate);
    const before = jumpsAt.find((found) => sameRational(found.position, position));
    if (before !== undefined) {
      const where =
        before.timeline === owner
          ? ""
          : ` of '${before.timeline}' at the same position on their root's axis`;
      yield new SchemaValidationError(
        "jump_repeated",
        at,
        `'${id}' is a second jump at coordinate ${spell(entry.coordinate)} of '${owner}', after '${before.id}'${where}: several signs at one place are destinations of one jump`,
      );
    } else jumpsAt.push({ position, id, timeline: owner });
    const seen: Place[] = [];
    for (const [number, destination] of entries(entry, "targets").entries()) {
      const here = [...at, "targets", number];
      const key = placeKey(destination);
      const first = seen.findIndex((place) => samePlace(place, key));
      if (first >= 0) {
        yield new SchemaValidationError(
          "jump_destination",
          here,
          `destination ${number} of '${id}' has the place of destination ${first}, ${placeWords(destination)}`,
        );
      }
      seen.push(key);
      if (Object.hasOwn(destination, "to") && !places.has(destination.to as string)) {
        yield new SchemaValidationError(
          "dangling_target",
          [...here, "to"],
          `'${destination.to}' names no jump target, region or child of this timeline, nor the timeline itself`,
        );
      }
      if (Object.hasOwn(destination, "by")) {
        if (outside(placeOf(timeline, entry.coordinate, destination.by))) {
          yield new SchemaValidationError(
            "flow_coordinate",
            [...here, "by"],
            `by ${spell(destination.by)} from coordinate ${spell(entry.coordinate)} of '${id}' is not on '${owner}': ${beyond()}`,
          );
        }
      }
      if (isJsonObject(destination.after)) {
        yield* afterProblems(destination.after, [...here, "after"], id, jumps);
      }
    }
  }
}

/**
 * The IDs of a root's timelines and of what gives an interval inside its
 * tree: the root and every descendant; every descendant and every region of
 * the root or a descendant.
 */
function treeOf(root: JsonObject): { timelines: Set<string>; intervals: Set<string> } {
  const timelines = new Set<string>();
  const intervals = new Set<string>();
  const visit = (timeline: JsonObject, child: boolean): void => {
    const id = text(timeline, "id");
    timelines.add(id);
    if (child) intervals.add(id);
    for (const region of entries(timeline, "regions")) intervals.add(text(region, "id"));
    for (const entry of entries(timeline, "children")) visit(entry, true);
  };
  visit(root, false);
  return { timelines, intervals };
}

/** The unit and the number type of an axis. */
type AxisOf = readonly [unit: string, numberType: string];

/** The axis and the length (`null` where unknown) of what a chunk may name. */
type Extent = { readonly axis: AxisOf; readonly length: Rational | null };

function sameAxis(left: AxisOf, right: AxisOf): boolean {
  return left[0] === right[0] && left[1] === right[1];
}

function subtract(left: Rational, right: Rational): Rational {
  return add(left, rational(-right.numerator, right.denominator));
}

/**
 * The axis and the length of everything a chunk may name, by ID: a region
 * (its end less its start, on its timeline's axis), a child timeline (its
 * length on its own axis, `null` where unknown) and a virtual timeline. Of a
 * repeated ID the first in this order is kept.
 */
function extentsOf(manifest: JsonObject): Map<string, Extent> {
  const found = new Map<string, Extent>();
  const keep = (id: string, extent: Extent): void => {
    if (!found.has(id)) found.set(id, extent);
  };
  const visit = (timeline: JsonObject, child: boolean): void => {
    const axis: AxisOf = [text(timeline, "unit"), numberTypeOf(timeline as Axis)];
    const length = lengthOf(timeline);
    if (child) keep(text(timeline, "id"), { axis, length: length === null ? null : exact(length) });
    for (const region of entries(timeline, "regions")) {
      keep(text(region, "id"), { axis, length: subtract(exact(region.end), exact(region.start)) });
    }
    for (const entry of entries(timeline, "children")) visit(entry, true);
  };
  for (const root of entries(manifest, "timelines")) visit(root, false);
  for (const entry of entries(manifest, "virtual_timelines")) {
    keep(text(entry, "id"), {
      axis: [text(entry, "unit"), text(entry, "number_type")],
      length: exact(entry.length),
    });
  }
  return found;
}

/**
 * The sum of a FlowMap's chunks and gaps on `axis`, or `null` where the sum
 * is not read: on a `float` axis, whose sum depends on the order of its
 * additions, and where a chunk names nothing, has no known length or lies on
 * another axis than `axis` (a gap lies on the axis `gaps` of the FlowMap's
 * timeline).
 */
function played(
  flowMap: JsonObject,
  axis: AxisOf,
  gaps: AxisOf,
  extents: ReadonlyMap<string, Extent>,
): Rational | null {
  if (axis[1] === "float") return null;
  let total = ZERO;
  for (const chunk of listed(flowMap, "chunks")) {
    if (typeof chunk === "string") {
      const extent = extents.get(chunk);
      if (extent === undefined || !sameAxis(extent.axis, axis) || extent.length === null) {
        return null;
      }
      total = add(total, extent.length);
    } else {
      if (!sameAxis(gaps, axis)) return null;
      total = add(total, exact((chunk as JsonObject).gap));
    }
  }
  return total;
}

/** An exact value as an axis of `numberType` spells it. */
function spelled(value: Rational, numberType: string): string {
  return numberType === "fraction"
    ? spell([value.numerator, value.denominator])
    : spell(value.numerator);
}

/** The IDs of every conversion map of a manifest, at any depth. */
function mapIds(manifest: JsonObject): Set<string> {
  const found = new Set<string>();
  for (const [index, root] of entries(manifest, "timelines").entries()) {
    for (const [id, path] of treeIds(root, ["timelines", index])) {
      if (path.includes("conversion_maps")) found.add(id);
    }
  }
  return found;
}

/**
 * Yield the problems of the FlowMaps, then of the virtual timelines. FlowMap
 * by FlowMap: its timeline, its chunks in their order (none where the
 * timeline is no root), then a second canonical FlowMap of its timeline.
 * Virtual timeline by virtual timeline: its map, then its timeline, then the
 * virtual timelines it comes from itself through, and, where it comes from a
 * timeline and applies a FlowMap of a root without `through`, the FlowMap of
 * another root, else its length.
 */
export function* flowMapProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const roots = new Map<string, JsonObject>();
  const trees = new Map<string, { timelines: Set<string>; intervals: Set<string> }>();
  const every = new Set<string>();
  // Of a repeated root ID the last root's tree is read.
  for (const root of entries(manifest, "timelines")) {
    roots.set(text(root, "id"), root);
    trees.set(text(root, "id"), treeOf(root));
  }
  for (const tree of trees.values()) for (const timeline of tree.timelines) every.add(timeline);
  const flowMaps = entries(manifest, "flow_maps");
  const virtual = entries(manifest, "virtual_timelines");
  const comesFrom = new Map<string, string>();
  for (const entry of virtual) {
    const id = text(entry, "id");
    if (!comesFrom.has(id)) comesFrom.set(id, text(entry, "timeline"));
  }
  const liesIn = (start: string, timelines: ReadonlySet<string>): boolean => {
    const visited = new Set<string>();
    let id = start;
    while (comesFrom.has(id) && !visited.has(id)) {
      visited.add(id);
      id = comesFrom.get(id) as string;
    }
    return timelines.has(id);
  };

  const canonical = new Map<string, string>();
  for (const [index, flowMap] of flowMaps.entries()) {
    const at = ["flow_maps", index];
    const name = text(flowMap, "timeline");
    const tree = trees.get(name);
    if (tree === undefined) {
      yield new SchemaValidationError(
        "flow_map_timeline",
        [...at, "timeline"],
        every.has(name)
          ? `'${name}' is a child timeline; a FlowMap names a root timeline`
          : `'${name}' names no root timeline of this manifest`,
      );
    } else {
      for (const [number, chunk] of listed(flowMap, "chunks").entries()) {
        if (typeof chunk !== "string") continue;
        if (tree.intervals.has(chunk)) continue;
        if (comesFrom.has(chunk) && liesIn(chunk, tree.timelines)) continue;
        yield new SchemaValidationError(
          "flow_map_chunk",
          [...at, "chunks", number],
          `'${chunk}' names no region, child timeline or virtual timeline in the tree of '${name}'`,
        );
      }
    }
    if (flowMap.canonical === true) {
      const first = canonical.get(name);
      if (first !== undefined) {
        yield new SchemaValidationError(
          "flow_map_canonical",
          [...at, "canonical"],
          `'${text(flowMap, "id")}' is a second canonical FlowMap of '${name}', after '${first}'`,
        );
      } else canonical.set(name, text(flowMap, "id"));
    }
  }

  const maps = mapIds(manifest);
  const applied = new Map<string, JsonObject>();
  for (const flowMap of flowMaps) {
    const id = text(flowMap, "id");
    maps.add(id);
    if (!applied.has(id)) applied.set(id, flowMap);
  }
  const rootOf = new Map<string, string>();
  for (const [id, tree] of trees) {
    for (const member of tree.timelines) if (!rootOf.has(member)) rootOf.set(member, id);
  }
  const extents = extentsOf(manifest);
  for (const [index, entry] of virtual.entries()) {
    const at = ["virtual_timelines", index];
    if (!maps.has(text(entry, "map"))) {
      yield new SchemaValidationError(
        "dangling_target",
        [...at, "map"],
        `'${entry.map}' names no FlowMap or conversion map of this manifest`,
      );
    }
    const id = text(entry, "id");
    let name = text(entry, "timeline");
    if (name === id || (!every.has(name) && !comesFrom.has(name))) {
      yield new SchemaValidationError(
        "dangling_target",
        [...at, "timeline"],
        `'${name}' names no timeline and no other virtual timeline of this manifest`,
      );
      continue;
    }
    const chain = [id];
    while (comesFrom.has(name) && !chain.includes(name)) {
      chain.push(name);
      name = comesFrom.get(name) as string;
    }
    if (name === id) {
      const through = chain
        .slice(1)
        .map((other) => `'${other}'`)
        .join(", ");
      yield new SchemaValidationError(
        "virtual_timeline",
        [...at, "timeline"],
        `'${name}' comes from itself through ${through}: a virtual timeline comes, virtual timeline by virtual timeline, from a timeline of this manifest`,
      );
    }
    const flowMap = applied.get(text(entry, "map"));
    const root = rootOf.get(name);
    if (root === undefined || flowMap === undefined || (entry.through ?? null) !== null) continue;
    const of = text(flowMap, "timeline");
    const ofRoot = roots.get(of);
    if (ofRoot === undefined) continue;
    if (of !== root) {
      yield new SchemaValidationError(
        "virtual_timeline",
        [...at, "map"],
        `'${entry.map}' is a FlowMap of '${of}', and '${entry.timeline}' comes from the tree of '${root}': without through, a virtual timeline applies a FlowMap within the tree of the FlowMap's root timeline`,
      );
      continue;
    }
    const axis: AxisOf = [text(entry, "unit"), text(entry, "number_type")];
    const gaps: AxisOf = [text(ofRoot, "unit"), numberTypeOf(ofRoot as Axis)];
    const sum = played(flowMap, axis, gaps, extents);
    if (sum !== null && !sameRational(sum, exact(entry.length))) {
      yield new SchemaValidationError(
        "virtual_timeline",
        [...at, "length"],
        `length ${spell(entry.length)} of '${id}' is not the sum of the chunks and gaps of '${entry.map}', ${spelled(sum, axis[1])}`,
      );
    }
  }
}

/** What a valid manifest's flow is warned of, never refused for. */
export type FlowWarningCode = "manifestation_unknown" | "convention_unknown";

/** One flow warning of a valid manifest. */
export interface FlowWarning {
  readonly code: FlowWarningCode;
  readonly path: readonly PathSegment[];
  readonly message: string;
}

function* timelineWarnings(timeline: JsonObject, path: Path): Generator<FlowWarning> {
  for (const [index, entry] of entries(timeline, "flow_control").entries()) {
    const at = [...path, "flow_control", index];
    const checked: [string, JsonObject, PathSegment[]][] = [[text(entry, "role"), entry, at]];
    for (const [number, destination] of entries(entry, "targets").entries()) {
      checked.push(["destination", destination, [...at, "targets", number]]);
    }
    for (const [kind, holder, here] of checked) {
      const word = holder.manifestation;
      if (typeof word === "string" && !(MANIFESTATIONS[kind] ?? []).includes(word)) {
        yield {
          code: "manifestation_unknown",
          path: [...here, "manifestation"],
          message: `'${word}' is no manifestation the format defines for ${NAMED[kind]}`,
        };
      }
    }
  }
  for (const [index, child] of entries(timeline, "children").entries()) {
    yield* timelineWarnings(child, [...path, "children", index]);
  }
}

/**
 * The flow warnings of a valid manifest, in document order:
 * `manifestation_unknown` at the `manifestation` of a flow-control element or
 * of a jump's destination that the format does not define for it, and
 * `convention_unknown` at the `convention` of a FlowMap that is none of the
 * format's.
 */
export function flowWarnings(manifest: JsonObject): FlowWarning[] {
  const found: FlowWarning[] = [];
  for (const [index, root] of entries(manifest, "timelines").entries()) {
    found.push(...timelineWarnings(root, ["timelines", index]));
  }
  for (const [index, flowMap] of entries(manifest, "flow_maps").entries()) {
    const word = flowMap.convention;
    if (typeof word === "string" && !CONVENTIONS.includes(word)) {
      found.push({
        code: "convention_unknown",
        path: ["flow_maps", index, "convention"],
        message: `'${word}' is no convention the format defines`,
      });
    }
  }
  return found;
}
