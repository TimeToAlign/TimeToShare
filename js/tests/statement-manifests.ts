/**
 * The manifests of the specification that the statement and catalogue tests
 * share with the Python suite, in the file form, read from YAML text by
 * `loads` so their numbers are the lossless form.
 */

import { FORMAT_CONTEXT, loads } from "../src/index.js";
import type { JsonObject } from "../src/json/value.js";

/** The format's terms with the given prefixes, as a manifest's `@context`. */
export function contextWith(prefixes: Readonly<Record<string, string>>): JsonObject {
  return { ...structuredClone(FORMAT_CONTEXT), ...prefixes };
}

export const SCHEMA = { schema: "http://schema.org/" };
export const WIKIDATA = {
  wd: "http://www.wikidata.org/entity/",
  wdt: "http://www.wikidata.org/prop/direct/",
};
export const RDF = { rdf: "http://www.w3.org/1999/02/22-rdf-syntax-ns#" };

/** M1: a bundle `#rec` with one root of unknown length, a region and a child. */
export function m1(): JsonObject {
  const value = loads(`timetoshare: 0.2.0
id: "#rec"
timelines:
- id: "#cpt_1"
  unit: seconds
  length: null
  regions:
  - {id: "#region_1", start: 0.0, end: 10.0}
  children:
  - {id: "#cpt_2", unit: seconds, offset: 0.0, length: 5.0}
`) as JsonObject;
  return { "@context": contextWith({ ...SCHEMA, ...WIKIDATA }), ...value };
}

/** The prefixes of M2's context. */
export const M2_PREFIXES = {
  dcterms: "http://purl.org/dc/terms/",
  gnd: "https://d-nb.info/gnd/",
  melod: "https://lod.academy/melod/vocab/ontology#",
  rel: "http://id.loc.gov/vocabulary/relators/",
  schema: "http://schema.org/",
  viaf: "http://viaf.org/viaf/",
  wd: "http://www.wikidata.org/entity/",
  wdt: "http://www.wikidata.org/prop/direct/",
  xsd: "http://www.w3.org/2001/XMLSchema#",
};

/** M2: the score encoding `#clt_6` and the video `#cpt_1` of the LayerIt recording. */
export function m2(): JsonObject {
  const value = loads(`timetoshare: 0.2.0
timelines:
- id: "#clt_6"
  unit: quarters
  length: [27, 1]
  statements:
    dcterms:created: [{"@value": "2025-12-05", "@type": "xsd:date"}]
    schema:exampleOfWork:
    - {id: "http://musicbrainz.org/work/8d331505-4d88-39ae-81c7-bec5da77af96", label: Clair de lune}
    type: [melod:Manifestation, schema:SheetMusic]
    wdt:P629:
    - id: wd:Q29117946
      label: Clair de lune
      schema:sameAs:
      - {id: "http://musicbrainz.org/work/8d331505-4d88-39ae-81c7-bec5da77af96"}
      - {id: "gnd:300042558"}
- id: "#cpt_1"
  unit: seconds
  length: null
  statements:
    rel:prf: [{id: "viaf:113931950"}]
    schema:sameAs: [{id: "https://www.youtube.com/watch?v=Ch2mrPm1JnM"}]
    type: [schema:VideoObject, melod:Manifestation]
    wdt:P175:
    - id: wd:Q235650
      label: Maria João Pires
      schema:sameAs: [{id: "viaf:113931950"}, {id: "gnd:124927521"}]
    wdt:P31: [{id: wd:Q98069877}]
`) as JsonObject;
  return { "@context": contextWith(M2_PREFIXES), ...value };
}
