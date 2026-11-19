/**
 * The test catalogue of the specification, shared with the Python suite: ten
 * prefixes, the schema.org alias, four systems (Wikidata and MusicBrainz with
 * the registry's patterns for their items and works, MeLODy and the
 * fallback without things), six verbs and one type.
 */

import type { Catalogue } from "../src/index.js";

export const CATALOGUE_TEST: Catalogue = {
  prefixes: {
    dcterms: "http://purl.org/dc/terms/",
    gnd: "https://d-nb.info/gnd/",
    melod: "https://lod.academy/melod/vocab/ontology#",
    melodTerms: "https://lod.academy/melod/vocab/terms#",
    rel: "http://id.loc.gov/vocabulary/relators/",
    schema: "http://schema.org/",
    viaf: "http://viaf.org/viaf/",
    wd: "http://www.wikidata.org/entity/",
    wdt: "http://www.wikidata.org/prop/direct/",
    xsd: "http://www.w3.org/2001/XMLSchema#",
  },
  aliases: {
    "https://schema.org/": "http://schema.org/",
  },
  systems: [
    {
      id: "wikidata",
      name: "Wikidata",
      prefixes: ["wd", "wdt"],
      things: [
        {
          id: "wikidata",
          kind: "item",
          name: "Wikidata",
          iri: "http://www.wikidata.org/entity/{value}",
          prefix: "wd",
          scheme_uri: "http://id.loc.gov/vocabulary/identifiers/wikidata",
          lrmoo_class: null,
          lowercase: false,
          patterns: [
            "https?://(?:www\\.|m\\.)?wikidata\\.org/(?:wiki|entity)/(Q[1-9][0-9]*)/?(?:[?#].*)?",
          ],
        },
      ],
      lookup: {
        route: "browser",
      },
    },
    {
      id: "musicbrainz",
      name: "MusicBrainz",
      prefixes: ["schema"],
      things: [
        {
          id: "musicbrainz_work",
          kind: "work",
          name: "MusicBrainz work ID",
          iri: "http://musicbrainz.org/work/{value}",
          scheme_uri: "http://www.wikidata.org/entity/P435",
          lrmoo_class: null,
          lowercase: true,
          patterns: [
            "https?://(?:www\\.)?musicbrainz\\.org/work/([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})/?(?:[?#].*)?",
          ],
        },
      ],
      lookup: {
        route: "server",
      },
    },
    {
      id: "melody",
      name: "MeLODy",
      prefixes: ["melod", "melodTerms"],
      things: [],
      lookup: {
        route: "none",
      },
    },
    {
      id: "fallback",
      name: "Fallback",
      prefixes: ["dcterms", "rel", "schema"],
      things: [],
      lookup: {
        route: "none",
      },
    },
  ],
  verbs: [
    {
      id: "is_a",
      label: "is a",
      patterns: {
        wikidata: [
          {
            pattern: {
              "wdt:P31": [
                {
                  id: "?",
                },
              ],
            },
          },
        ],
        fallback: [
          {
            pattern: {
              type: ["?"],
            },
          },
        ],
      },
    },
    {
      id: "same_as",
      label: "same as",
      patterns: {
        fallback: [
          {
            pattern: {
              "schema:sameAs": [
                {
                  id: "?",
                },
              ],
            },
          },
        ],
      },
    },
    {
      id: "performed_by",
      label: "performed by",
      patterns: {
        wikidata: [
          {
            pattern: {
              "wdt:P175": [
                {
                  id: "?",
                },
              ],
            },
          },
        ],
        musicbrainz: [
          {
            pattern: {
              "schema:contributor": [
                {
                  type: ["schema:OrganizationRole"],
                  "schema:contributor": [
                    {
                      id: "?",
                    },
                  ],
                  "schema:roleName": ["?role"],
                },
              ],
            },
          },
        ],
        melody: [
          {
            pattern: {
              "melod:hasContribution": [
                {
                  type: ["melod:Contribution"],
                  "melod:hasAgent": [
                    {
                      id: "?",
                    },
                  ],
                  "melod:hasRole": [
                    {
                      id: "melodTerms:Performer",
                    },
                  ],
                },
              ],
            },
          },
        ],
        fallback: [
          {
            pattern: {
              "rel:prf": [
                {
                  id: "?",
                },
              ],
            },
          },
        ],
      },
    },
    {
      id: "conducted_by",
      label: "conducted by",
      patterns: {
        musicbrainz: [
          {
            pattern: {
              "schema:contributor": [
                {
                  type: ["schema:OrganizationRole"],
                  "schema:contributor": [
                    {
                      id: "?",
                    },
                  ],
                  "schema:roleName": ["conductor"],
                },
              ],
            },
          },
        ],
      },
    },
    {
      id: "version_or_edition_of",
      label: "version or edition of",
      patterns: {
        wikidata: [
          {
            pattern: {
              "wdt:P629": [
                {
                  id: "?",
                },
              ],
            },
          },
        ],
        fallback: [
          {
            pattern: {
              "schema:exampleOfWork": [
                {
                  id: "?",
                },
              ],
            },
          },
        ],
      },
    },
    {
      id: "part_of",
      label: "part of",
      inverse_label: "has part",
      patterns: {
        fallback: [
          {
            pattern: {
              "dcterms:isPartOf": [
                {
                  id: "?",
                },
              ],
            },
          },
          {
            pattern: {
              "dcterms:hasPart": [
                {
                  id: "?",
                },
              ],
            },
            inverse: true,
          },
        ],
      },
    },
  ],
  types: [
    {
      id: "video",
      label: "video",
      is_a: {
        wikidata: [
          {
            pattern: {
              "wdt:P31": [
                {
                  id: "wd:Q193977",
                },
              ],
            },
          },
        ],
        fallback: [
          {
            pattern: {
              type: ["schema:VideoObject"],
            },
          },
        ],
      },
      verbs: ["performed_by"],
      lookup: ["wikidata"],
    },
  ],
};
