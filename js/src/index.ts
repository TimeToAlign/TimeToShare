/**
 * @timetoalign/timetoshare: the TimeToShare schema, generated types, a
 * validator, the complete and minimal forms, reading and writing in three
 * serializations (canonical YAML, pretty JSON and RFC 8785 JSON),
 * and the fonts that draw a drawing's text with the table that measures it.
 *
 * A TimeToShare manifest is one JSON object holding the version marker
 * `timetoshare` and an array of root timelines, each describing a musical
 * timeline as timetoalign serializes it, optionally named, optionally
 * attributing timelines to groups, optionally describing the manifest, its
 * timelines and its regions by property–value statements with their
 * provenance (the catalogue of identifier systems, verbs and types guiding
 * tools that write them) and optionally styled for drawing. A manifest
 * carrying statements is a YAML-LD document through its inline `@context`.
 * An
 * editor can place many manifests on a canvas, but a manifest knows nothing
 * about where or how often it is placed.
 */

export { complete, DEFAULTS, minimal } from "./defaults.js";
export { dumpsFile, type FileForm, fileForm } from "./files.js";
export { FONT_FILES, type FontMetrics, fontMetrics } from "./font.js";
export { canonicalManifest, completeManifest, minimalManifest } from "./forms.js";
export { schema } from "./generated/schema.js";
export type {
  Address,
  CompleteConversionMap,
  CompleteElision,
  CompleteFlowControlElement,
  CompleteGraphical,
  CompleteGroup,
  CompleteManifest,
  CompleteMeasureMap,
  CompleteRegion,
  CompleteTimeline,
  CompleteTimestamp,
  Context,
  ConversionMap,
  Coordinate,
  Declaration,
  ElementType,
  Elision,
  Facet,
  FlowControlElement,
  Fraction,
  Graphical,
  Group,
  Id,
  Iri,
  IriReference,
  LinearMap,
  LosslessManifest,
  Manifest,
  MeasureMap,
  MeasureMapRow,
  Number,
  NumberType,
  Order,
  Paint,
  Part,
  Provenance,
  ProvenanceEntry,
  Region,
  Rule,
  Selector,
  Statements,
  StatementValue,
  Timeline,
  Timestamp,
  TimeUnit,
  ValueNode,
  ValueObject,
} from "./generated/types.js";
export { FileIdError, fromFileId, toFileId, withBareIds, withFileIds } from "./ids.js";
export {
  isJsonFloat,
  isJsonObject,
  type Json,
  JsonFloat,
  type JsonNumber,
  type Lossless,
} from "./json/value.js";
export {
  ANCHOR_DISPLAY,
  canonicalOrder,
  ELISION_DISPLAY,
  TIMESTAMP_DISPLAY,
} from "./manifest/order.js";
export { UNITS, type UnitEntry } from "./manifest/units.js";
export { exactValue, jsonInteger, type Rational } from "./numbers/exact.js";
export { JsonSyntaxError, YamlSyntaxError } from "./serialization/errors.js";
export { parseJson } from "./serialization/json.js";
export { loads, serializationOf } from "./serialization/read.js";
export { compactJson, compactSortedJson } from "./serialization/text.js";
export {
  type DumpsOptions,
  dumps,
  isSerialization,
  SERIALIZATIONS,
  type Serialization,
} from "./serialization/write.js";
export { parseYaml } from "./serialization/yaml.js";
export {
  type Alternative,
  type Catalogue,
  type CatalogueSystem,
  type CatalogueThing,
  type CatalogueType,
  type CatalogueVerb,
  defaultCatalogue,
  type InstantiateOptions,
  instantiate,
  type Lookup,
  type Recognition,
  type Rectangle,
  readCatalogue,
  recognize,
  rectangles,
  verbOf,
} from "./statements/catalogue.js";
export {
  BELIEF_STATES,
  BELIEFS,
  type Belief,
  type BeliefOptions,
  type BeliefState,
  BLANK,
  type CandidateOptions,
  candidates,
  checkBeliefFilter,
  compactIri,
  DEFAULT_BELIEFS,
  entries,
  expandIri,
  FORMAT_CONTEXT,
  MATCHES,
  METHODS,
  NAMESPACE,
  type Pair,
  type PairOptions,
  type PairProvenance,
  pairs,
  type Subject,
  type SubjectElement,
  samePair,
  subjectPath,
  subjects,
  usedPrefixes,
  withBelief,
  withCandidate,
  withContext,
  withoutPair,
  withPair,
  withReferencesRenamed,
} from "./statements/statements.js";
export { completeStyles } from "./styles.js";
export {
  childEnds,
  identityProblems,
  jsonPointer,
  type ManifestWarning,
  manifestWarnings,
  matchstampProblems,
  numberTypeOf,
  type PathSegment,
  parse,
  SCHEMA_VERSION,
  SchemaValidationError,
  statementProblems,
  type UnknownKey,
  UnsupportedVersionError,
  unknownKeys,
  type ValidationCode,
  validate,
  type WarningCode,
} from "./validate.js";
