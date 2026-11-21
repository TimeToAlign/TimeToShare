/** Helpers for reading the styles of a manifest's `graphical` object. */

import type { Graphical } from "./generated/types.js";
import { clone } from "./json/value.js";

function compareCodePoints(left: string, right: string): number {
  const leftPoints = Array.from(left, (character) => character.codePointAt(0) as number);
  const rightPoints = Array.from(right, (character) => character.codePointAt(0) as number);
  const length = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < length; index += 1) {
    const difference = (leftPoints[index] as number) - (rightPoints[index] as number);
    if (difference !== 0) return difference;
  }
  return leftPoints.length - rightPoints.length;
}

/**
 * Return a copied `graphical` object with empty declarations for every missing style.
 *
 * The copy keeps every number as `loads` read it: an integral float stays a `JsonFloat`.
 */
export function completeStyles(graphical: Graphical): {
  graphical: Graphical;
  missing: string[];
} {
  const completed = clone(graphical);
  const styles = completed.styles ?? {};
  const missing = Array.from(
    new Set(
      (completed.rules ?? [])
        .map((rule) => rule.set)
        .filter((setting): setting is string => typeof setting === "string")
        .filter((name) => !Object.hasOwn(styles, name)),
    ),
  ).sort(compareCodePoints);
  if (missing.length > 0) {
    completed.styles = styles;
    for (const name of missing) {
      Object.defineProperty(styles, name, {
        value: {},
        enumerable: true,
        configurable: true,
        writable: true,
      });
    }
    const names = missing.map((name) => `'${name}'`).join(", ");
    console.warn(`Missing graphical styles: ${names}`);
  }
  return { graphical: completed, missing };
}
