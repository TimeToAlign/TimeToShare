/**
 * @timetoalign/timetoshare: the TimeToShare schema, generated types, a
 * validator, the complete and minimal forms, reading and writing in three
 * serializations (canonical YAML, pretty JSON and RFC 8785 JSON),
 * and the fonts that draw a drawing's text with the table that measures it.
 *
 * A TimeToShare manifest is one JSON object holding the version marker
 * `timetoshare` and an array of root timelines, each describing a musical
 * timeline as timetoalign serializes it, optionally named, optionally
 * attributing timelines to groups, optionally linking the manifest, its
 * timelines and its regions to external entities (built from URLs through
 * the registry of known identifier schemes) and optionally styled for
 * drawing. An
 * editor can place many manifests on a canvas, but a manifest knows nothing
 * about where or how often it is placed.
 */

export { complete, DEFAULTS, minimal } from "./defaults.js";
export {
  ABSENCE_REASONS,
  assertionFor,
  LEVELS,
  type LinkOptions,
  linkFromUrl,
  linkFromUrls,
  MATCHES,
  METHODS,
  PARTS_RELATIONS,
  type PartSlotOptions,
  type PartsOptions,
  partSlotFromUrl,
  RELATIONS,
  STATUSES,
  withAssertion,
  withIdentifier,
  withLabel,
  withPartOf,
  withParts,
  withRecord,
  withUri,
} from "./description/link.js";
export {
  defaultRegistry,
  type KnownScheme,
  type Recognition,
  recognize,
  type SchemeEntry,
  type SchemeRegistry,
  withSchemes,
} from "./description/registry.js";
export { FONT_FILES, type FontMetrics, fontMetrics } from "./font.js";
export { canonicalManifest, completeManifest, minimalManifest } from "./forms.js";
export { schema } from "./generated/schema.js";
export type {
  Address,
  Assertion,
  CompleteAssertion,
  CompleteConversionMap,
  CompleteDescriptor,
  CompleteFlowControlElement,
  CompleteGraphical,
  CompleteGroup,
  CompleteLink,
  CompleteManifest,
  CompleteMeasureMap,
  CompletePartOf,
  CompletePartSlot,
  CompleteRegion,
  CompleteScheme,
  CompleteTimeline,
  CompleteTimestamp,
  ConversionMap,
  Coordinate,
  Declaration,
  Descriptor,
  ElementType,
  Facet,
  FlowControlElement,
  Fraction,
  Graphical,
  Group,
  Id,
  Identifier,
  Level,
  LinearMap,
  Link,
  LosslessManifest,
  Manifest,
  MeasureMap,
  MeasureMapRow,
  Number,
  NumberType,
  Order,
  Paint,
  Part,
  PartOf,
  PartSlot,
  Region,
  Scheme,
  Selector,
  Statement,
  Term,
  Timeline,
  Timestamp,
  TimeUnit,
  Uri,
  UriReference,
} from "./generated/types.js";
export {
  isJsonFloat,
  isJsonObject,
  type Json,
  JsonFloat,
  type JsonNumber,
  type Lossless,
} from "./json/value.js";
export { canonicalOrder, TIMESTAMP_DISPLAY } from "./manifest/order.js";
export { JsonSyntaxError, YamlSyntaxError } from "./serialization/errors.js";
export { parseJson } from "./serialization/json.js";
export { loads, serializationOf } from "./serialization/read.js";
export { compactJson } from "./serialization/text.js";
export { type DumpsOptions, dumps, type Serialization } from "./serialization/write.js";
export { parseYaml } from "./serialization/yaml.js";
export { completeStyles } from "./styles.js";
export {
  descriptionProblems,
  identityProblems,
  jsonPointer,
  numberTypeOf,
  type PathSegment,
  parse,
  SCHEMA_VERSION,
  SchemaValidationError,
  type UnknownKey,
  type UnregisteredTerm,
  UnsupportedVersionError,
  unknownKeys,
  unregisteredTerms,
  type ValidationCode,
  validate,
} from "./validate.js";
