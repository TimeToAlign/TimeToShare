import type { JsonObject } from "../json/value.js";
import { compareExact } from "../numbers/exact.js";
import { spell } from "../serialization/text.js";
import {
  lengthOf,
  SchemaValidationError,
  text,
  timelinesById,
  timestampsOf,
} from "./diagnostics.js";

/**
 * Yield timestamps off the manifest's timelines or outside their extent.
 *
 * A timestamp names a timeline of the manifest, at any depth, and its
 * coordinate lies between 0 and that timeline's length, or at or after 0
 * where the length is not known.
 */
export function* timestampProblems(manifest: JsonObject): Generator<SchemaValidationError> {
  const timelines = timelinesById(manifest);
  for (const [index, timestamp] of timestampsOf(manifest).entries()) {
    const path = ["graphical", "timestamps", index];
    const id = text(timestamp, "timeline");
    const timeline = timelines.get(id);
    if (timeline === undefined) {
      yield new SchemaValidationError(
        "timestamp_timeline",
        [...path, "timeline"],
        `'${id}' names no timeline of this manifest`,
      );
      continue;
    }
    const { coordinate } = timestamp;
    const length = lengthOf(timeline);
    const where = `coordinate ${spell(coordinate)} of '${text(timestamp, "id")}'`;
    if (compareExact(coordinate, 0) < 0) {
      yield new SchemaValidationError(
        "timestamp_coordinate",
        [...path, "coordinate"],
        `${where} lies before the start of its timeline '${id}'`,
      );
    } else if (length !== null && compareExact(coordinate, length) > 0) {
      yield new SchemaValidationError(
        "timestamp_coordinate",
        [...path, "coordinate"],
        `${where} is beyond the length ${spell(length)} of its timeline '${id}'`,
      );
    }
  }
}
