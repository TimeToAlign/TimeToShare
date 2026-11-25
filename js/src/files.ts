/**
 * Manifest files: the form a file writes its manifest in, and writing it
 * back. A manifest file is the text of one manifest in one serialization, in
 * the minimal or the complete form, with or without its `graphical` object.
 * `fileForm` reads that `FileForm` off a text and `dumpsFile` writes a
 * manifest in a given one, so that an editor or a library writes a file back
 * as it came: `dumpsFile(loads(text), fileForm(text))` gives `text` for
 * every text a writer of this package wrote. Python's `file_form` and
 * `dumps_file` give the same form and the same bytes.
 */

import { complete, minimal } from "./defaults.js";
import { isJsonObject } from "./json/value.js";
import { loads, serializationOf } from "./serialization/read.js";
import { dumps, type Serialization } from "./serialization/write.js";

/** How a manifest file writes its manifest. */
export interface FileForm {
  /** Whether the manifest is in the minimal form rather than the complete form. */
  readonly minimal: boolean;
  /** Whether the manifest's `graphical` object is written. */
  readonly styling: boolean;
  /** `"yaml"` (canonical YAML), `"json"` (pretty JSON) or `"jcs"` (RFC 8785 JSON). */
  readonly serialization: Serialization;
}

/**
 * Read the form of a manifest file off its text. The manifest is minimal
 * when its minimal form writes the same canonical YAML as the value the text
 * holds: a key stated at its default makes a text not minimal, and the order
 * canonical order sorts does not count. Defaults are recognized by exact
 * value (a `LinearMap`'s `scalar: 1.0` is the default `1`) and own-axis values
 * respelled by the declared number type on both sides, so an RFC 8785 JSON text, which writes
 * an integral float as an integer, reads as the form it was written in. It
 * holds its styling when it has a top-level `graphical` key; the
 * serialization is the one `serializationOf` names. A text whose value
 * states some defaults and leaves out others is not minimal. The value is not
 * validated.
 *
 * @throws {JsonSyntaxError} for a text read as JSON that `loads` refuses.
 * @throws {YamlSyntaxError} for a text read as YAML that `loads` refuses.
 * @throws {RangeError} for a value canonical YAML refuses, as `dumps` throws it.
 * @throws {TypeError} for a manifest that cannot be put in canonical order.
 */
export function fileForm(text: string): FileForm {
  const value = loads(text);
  return {
    minimal: dumps(minimal(value)) === dumps(value),
    styling: isJsonObject(value) && Object.hasOwn(value, "graphical"),
    serialization: serializationOf(text),
  };
}

/**
 * The text of a manifest as a file of the given form writes it: a top-level
 * `graphical` left out unless `form.styling`, the rest in the minimal form
 * if `form.minimal`, else in the complete form, in `form.serialization`.
 * `value` is not changed.
 *
 * @throws {RangeError} for a value the serialization refuses, or an unknown serialization.
 * @throws {TypeError} for a value that is not JSON.
 */
export function dumpsFile(value: unknown, form: FileForm): string {
  let written = value;
  if (!form.styling && isJsonObject(value) && Object.hasOwn(value, "graphical")) {
    const { graphical: _graphical, ...unstyled } = value;
    written = unstyled;
  }
  return dumps(form.minimal ? minimal(written) : complete(written), {
    serialization: form.serialization,
  });
}
