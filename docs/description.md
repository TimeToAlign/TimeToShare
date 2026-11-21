# Describing what a manifest is about

This specification states how a TimeToShare manifest says what its
elements stand for and how those things relate to others: by
property–value statements in published vocabularies, optionally annotated
with their provenance, and read as linked data through the manifest's
inline JSON-LD context. It covers the two planes of a manifest (section
1), the subject of a statement (section 2), the bibliographic classes of
the things a manifest holds (section 3), pairs and their values (section
4), "is a" (section 5), vocabularies and patterns (section 6), values that
name elements (section 7), YAML-LD and the inline context (section 8),
provenance and beliefs (section 9), the catalogue of identifier systems,
verbs and types (section 10), the package functions that edit statements
(section 11) and validation (section 12). Section 13 lists the statement
fixtures.

The definitions `Context`, `Statements` and `StatementValue` of the
manifest's schema document and the provenance entry of its provenance
document, `provenance.schema.json`, with the definitions they use
(`PrefixName`, `PrefixIri`, `Iri`, `IriReference`, `LanguageTag`, `Types`,
`Values`, `SingleValue`, `OrderedValues`, `ValueObject`, `ValueNode`,
`Provenance`, `ProvenanceEntry`, `EntryValue` and the belief), state the
format normatively; `Context`, `Statements`, `StatementValue` and
`ProvenanceEntry` are public, and so is the provenance document as a whole
(README, "The schema document"). The same
provenance entry annotates the rows of the MatchClaim table (README,
"Provenance and beliefs"); this specification states it for statements. Terms in `code` are JSON
members. Statements hold no events, and neither the drawing
(`docs/drawing.md`) nor any rule of the temporal structure reads them.

The examples are excerpts of the statement fixtures under
`fixtures/0.2.0/statements/`, written in canonical YAML (README,
"Serializations"), with the format's context left out. Their Turtle
readings take the manifest to lie at
`https://example.org/manifests/<name>.yaml` and write the empty prefix `:`
for that address followed by `#`; the other prefixes are those of the
manifest's context.

## 1. Two planes

A manifest holds two kinds of information. Its **temporal structure**
(timelines and their nesting, groups, conversion maps, MeasureMaps,
regions and flow control) states how coordinates relate: which axis a
position lies on, where a child lies on its parent, how one unit converts
into another, and in which order passages are played. Its **statements**
state what a thing is and how it relates to other things: that a timeline
is the axis of a video, who performs in it, which work it records, and
where a statement came from. Each plane does its own work. A statement
never nests, orders or aligns timelines, and the temporal structure never
says what an element is: a child timeline is a stretch of its parent's
axis and implies no parthood, and a statement that one thing is part of
another implies nothing about the timelines.

## 2. The subject

Three kinds of element may carry statements, each in an object
`statements`, with their annotations in a list `provenance` (section 9):
the manifest as a whole, every timeline at any depth (children and
segments included) and every region. No other element carries either: a
group, a conversion map, a MeasureMap, a flow-control element and a named
timestamp have none, and the validators refuse the two keys on a group
(section 12).

As the subject of statements, each of these elements stands for a thing:

- the **bundle**, the manifest itself, for the package it is, which names
  the work it is about, a sonata or a DJ set, by `schema:about` and is
  never that work;
- a **timeline** for the manifestation it is the time axis of: this
  edition, this encoding, this scan, this recording file, this video;
- a **region** for the stretch of that manifestation it marks, such as a
  movement of a recording or a track of a set.

The subject's IRI is the manifest's address with the element's ID as its
fragment, `<manifest address>#<id>` (README, "Identity"), and an element
carrying statements must have an ID that is an IRI fragment (section 12).
A manifest without `id` is a blank node as a subject, which no other
document can name; the validators warn of it (`bundle_blank`).

## 3. Work, expression, manifestation, item

The things a manifest holds are classified after the IFLA Library
Reference Model and its object-oriented form LRMoo. A manifest bundles
the manifestations of one or more expressions of one work, including the
expressions that work's expression aggregates or incorporates.

| Class | The thing | In a manifest |
| --- | --- | --- |
| work | a creation in the abstract, intangible and without fixed bounds | never packaged; a value node, named by the bundle's `schema:about` and by a timeline's "example of work" |
| expression | one realisation of a work: the notated text of a version, a recorded performance | a value node, named by a timeline's "embodies"; a performance is an event, and its recording an expression of its own |
| manifestation | one embodiment of an expression: an edition, an encoding, a scan of a score; a release, an upload, an audio file, a video | the thing a timeline is the axis of, each timeline of exactly one |
| item | one exemplar of a manifestation: a copy in a library, a file at an address | a value node on its manifestation's timeline, holding its location and, for a file, its digest |

A work has no time axis, and a manifest never delineates one; an
expression has none of its own either. Works and expressions therefore
occur only as values. The bundle names its work by `schema:about` and is
typed as nothing that is a work; a timeline names what it manifests, an
expression by `lrmoo:R4_embodies`, a work by Wikidata's `wdt:P629` or
schema.org's `schema:exampleOfWork`. Such a value node states its own
"is a" and its identity with an authority's IRI by "same as". The "is a"
of a timeline or a region names a manifestation class or a kind of
manifestation, never a class of work or expression (section 5). Whatever
has no axis in the manifest stays a value node.

An edition, an encoding and a scan of the score are manifestations of the
notated expression; a release, an upload or a file of a recording are
manifestations of the recorded expression. A copy is an item, a value
node on its manifestation's timeline that holds its location and, for a
file, its digest; for a digital carrier the location is the item
statement. A compound is itself the one work. A disc is an aggregate
whose release embodies the compilation's expression and the pieces'
expressions with it, so the disc's timeline and its tracks' children are
axes of that one manifestation. A DJ set is a work of its own whose
recorded expression incorporates the tracks' expressions in altered form.
Its timeline is the axis of the set's recording, which names the set by
"recording of" (`wdt:P2550`); the tracks' own timelines, where a manifest
holds them, are manifestations of those expressions and relate to the
set by alignment alone.

The four classes are types of published vocabularies, and the format has
no key for them: a manifest states them where it wants them, as
`type: ["lrmoo:F3_Manifestation"]` or `type: ["melod:Manifestation"]`
(section 5). In `nielsen_record`, a catalogue record of Carl Nielsen's
song CNW 133, the bundle is about the catalogue's work, which is realised
in one expression. The print and the autograph are manifestations, each a
timeline; the print embodies the expression, a value node. The one copy
of the autograph, held by the Royal Danish Library under the shelfmark
CNS 342e, is a candidate for its exemplar on the autograph's timeline,
the library's siglum awaiting reconciliation (abridged):

```yaml
id: "#cnw0133"
statements:
  "schema:about":
    -
      id: "https://www.kb.dk/dcm/cnw/document.xq?doc=cnw0133.xml#work_d1e191187"
      "lrmoo:R3_is_realised_in":
        -
          id: "https://www.kb.dk/dcm/cnw/document.xq?doc=cnw0133.xml#expression_1"
      type: ["melod:Work"]
timelines:
  -
    id: "#cgt_1"
    length: null
    name: "Score, print (Wilhelm Hansen, 1906)"
    statements:
      "lrmoo:R4_embodies":
        -
          id: "https://www.kb.dk/dcm/cnw/document.xq?doc=cnw0133.xml#expression_1"
          type: ["melod:Expression"]
      type: ["melod:Manifestation"]
    unit: millimeters
  -
    id: "#cgt_2"
    length: null
    name: "Score, autograph, printer's manuscript"
    provenance:
      -
        property: "lrmoo:R7i_is_exemplified_by"
        value:
          "bf:heldBy":
            -
              label: DK-Kk
              "skos:notation": [DK-Kk]
          "melod:hasShelfmark": ["CNS 342e"]
          type: ["melod:Item"]
    statements:
      type: ["melod:Manifestation"]
    unit: millimeters
```

Read as linked data, the excerpt types no element of the manifest as a
work or an expression, and the candidate exemplar is reified only
(section 9):

```turtle
:cnw0133 schema:about
    <https://www.kb.dk/dcm/cnw/document.xq?doc=cnw0133.xml#work_d1e191187> .

<https://www.kb.dk/dcm/cnw/document.xq?doc=cnw0133.xml#work_d1e191187>
    a melod:Work ;
    lrmoo:R3_is_realised_in
        <https://www.kb.dk/dcm/cnw/document.xq?doc=cnw0133.xml#expression_1> .

:cgt_1 a melod:Manifestation ;
    lrmoo:R4_embodies
        <https://www.kb.dk/dcm/cnw/document.xq?doc=cnw0133.xml#expression_1> .

<https://www.kb.dk/dcm/cnw/document.xq?doc=cnw0133.xml#expression_1>
    a melod:Expression .

:cgt_2 a melod:Manifestation .
```

## 4. Pairs

A statement is a **pair** of a property and a value, both technical
identifiers where they name things. The container `statements` holds an
element's pairs: each key is `type` (section 5) or a property IRI, written
as a compact IRI `prefix:suffix` with a prefix of the manifest's context
(section 8) or as an absolute IRI; each value is the non-empty list of
that property's values, without repeats and in the order given. Writers
keep that order, and canonical order (README, "Canonical order") moves no
value and no entry of `provenance`. A container is never empty.

A value is one of four kinds:

| Value | Written | Read as |
| --- | --- | --- |
| a literal | a string, an integer or a boolean: `"op. 106"`, `1`, `true` | a plain literal, an `xsd:integer` or an `xsd:boolean` |
| a value object | `@value` with `@language` or with `@type`: `{"@value": "Hr. Olufs Sang", "@language": da}`, `{"@value": "2025-12-05", "@type": "xsd:date"}` | a literal with a language or a datatype |
| a node | an object with `id`, `type`, `label`, its own pairs and its own `provenance`, each optional, at least one present | a thing: the IRI of its `id`, or a blank node without one |
| an ordered list | `{list: [...]}` of single values | an RDF list |

A string is never read as an IRI: a thing is always a node, `{id: …}`.
A statement value is never a float and never `null`; a number with a
fractional part is a value object with its datatype, as
`{"@value": "33.35", "@type": "xsd:decimal"}`. A node's `label` is a
cache of the thing's name, kept for display; the thing's own source
remains authoritative for it. A node's own pairs are written directly
as its keys, so a node is described as an element is. A node whose `id`
names an element of the manifest holds that `id` alone (section 7).

The literals of `op106_work` are pairs of the work the bundle is about, a
value node: a catalogue number in GND's ontology and the work's IMSLP
page name, Wikidata's external-identifier property holding a string
(abridged):

```yaml
statements:
  "schema:about":
    -
      "gndo:opusNumericDesignationOfMusicalWork": ["op. 106"]
      id: "mbw:4a622b0d-b0c0-405e-b49e-05b70c108284"
      label: "Piano Sonata No. 29, Op. 106"
      "wdt:P839": ["Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)"]
```

and the encoding of `layerit_recording` states its encoding date as a
typed literal, `"dcterms:created": [{"@type": "xsd:date", "@value":
"2025-12-05"}]`.

## 5. "Is a"

The first statement about a thing says what kind of thing it is, in as
many vocabularies as wanted. A vocabulary of classes is stated with
`type`, JSON-LD's `@type`, whose values are class IRIs; a system that
types by property is stated with its property, as Wikidata's "instance of"
`wdt:P31`. The video of `layerit_recording` is a video in schema.org's
terms, a manifestation in MeLODy's and of the class "video"
(`wd:Q98069877`) in Wikidata's:

```yaml
statements:
  type: ["schema:VideoObject", "melod:Manifestation"]
  "wdt:P31":
    -
      id: "wd:Q98069877"
```

On a timeline or a region every "is a" names a manifestation class or a
kind of manifestation, as each of these three does; a class of work or
expression is stated on the value node that stands for the work or the
expression (section 3).

`type` holds one or more distinct IRIs and never a literal. In
`provenance`, the pair `type` X is written with the property `rdf:type`
and the value `{id: X}`; an entry giving the class as a literal string
names no pair (section 9).

## 6. Vocabularies and patterns

Each identifier system is used with the properties its own knowledge
graph publishes: a Wikidata item with Wikidata's properties (`wdt:`), a
MusicBrainz ID with schema.org as MusicBrainz's own JSON-LD writes it, a
GND ID with the GND ontology (`gndo:`), a MeLODy entity with LRMoo and
MeLODy's terms, a library authority with the MARC relators (`rel:`). The
same relation may therefore be stated in several vocabularies side by
side, each with its own value. The video of `layerit_recording` names its
performer twice, as Wikidata states performers and as libraries do, and
ties the two values together by `schema:sameAs` inside the Wikidata node;
the pairs are those of the fixture's `#cpt_1`, the video of unknown
length:

```yaml
id: "#cpt_1"
length: null
statements:
  "rel:prf":
    -
      id: "viaf:113931950"
  "schema:sameAs":
    -
      id: "https://www.youtube.com/watch?v=Ch2mrPm1JnM"
  type: ["schema:VideoObject", "melod:Manifestation"]
  "wdt:P175":
    -
      id: "wd:Q235650"
      label: "Maria João Pires"
      "schema:sameAs":
        -
          id: "viaf:113931950"
        -
          id: "gnd:124927521"
  "wdt:P31":
    -
      id: "wd:Q98069877"
unit: seconds
```

A JSON-LD processor reads it as these triples, the timeline's unit and
length yielding none:

```turtle
:cpt_1 a schema:VideoObject, melod:Manifestation ;
    rel:prf viaf:113931950 ;
    schema:sameAs <https://www.youtube.com/watch?v=Ch2mrPm1JnM> ;
    wdt:P175 wd:Q235650 ;
    wdt:P31 wd:Q98069877 .

wd:Q235650 rdfs:label "Maria João Pires" ;
    schema:sameAs viaf:113931950, gnd:124927521 .
```

The file holds properties only. A relation in words, "performed by" or
"is a recording of", is a **verb** of the catalogue (section 10), which
maps each verb and identifier system to a **pattern**, the properties
that express the verb in that system's vocabulary with a slot for the
value. A plain pair is the simplest pattern (`wdt:P175` with a thing);
some vocabularies need a small node, as MusicBrainz states a performer by
a `schema:contributor` node holding the agent and the role, and MeLODy by
a `melod:Contribution`. Tools use the catalogue to offer the properties
of a verb and to print a pair in words; a property the catalogue does not
know is as valid as any other.

## 7. Values that name elements

A node whose `id` begins with `#` names an element of the same manifest,
`{id: "#cpt_1"}`, which reads as `<manifest address>#cpt_1`, the IRI of
that element as a subject. An element of another manifest is named by
that manifest's address with the ID as fragment, relative
(`other.yaml#clt_1`) or absolute. Any property may take such a value;
"derived from", relating one manifestation to another, is the usual case.
A work or an expression is never such a value, since no element stands
for one (section 3). A node naming an
element of the manifest holds its `id` alone: the element describes
itself through its own statements, so a label or pair beside the `id`
would describe it a second time.

These values are IRI references, written and held alike. A reader that
strips the `#` from IDs and references of the temporal structure (README,
"Written in a file") leaves every IRI inside `statements` and
`provenance` as written, and the validators resolve each `#` reference
there against every ID of the manifest, whatever its kind (section 12).

## 8. YAML-LD and the inline context

A manifest is a YAML-LD document (W3C YAML-LD 1.0, media type
`application/ld+yaml`): every manifest maps to JSON-LD 1.1, and canonical
YAML is a subset of the YAML it reads. A manifest carrying statements or
provenance holds the key `@context` at its top level and nowhere else:
one object, the format's terms each exactly as the schema fixes them and
the prefixes its statements and provenance use. The context is inline,
so the manifest is self-contained and a processor reads it without
fetching anything. Writers write the prefixes used and no others, taking
their namespaces from the manifest's own context first and from the
catalogue otherwise (Python's `with_context`, npm's `withContext`,
section 11); every generated fixture of 0.2.0 holds a context, the 35
terms alone where it states nothing.

A **prefix** is a name beginning with a letter, followed by letters,
digits, `_` or `-`, which is no key of the manifest's elements and no URI
scheme the format reads as such (`http`, `https`, `info`, `mailto`,
`tag`, `urn`); it stands for a namespace, an absolute IRI ending in `/`
or `#`. A manifest may declare a prefix of its own beside those of the
catalogue, as `op106_work` declares `mbw` for MusicBrainz works. A compact
IRI whose prefix the context does not declare is refused (section 12); an
absolute IRI is always valid, and an IRI of the schemes `info`, `mailto`,
`tag` and `urn` is read as written.

The format's 35 terms:

| Term | Maps to | Role |
| --- | --- | --- |
| `@version` | `1.1` | JSON-LD 1.1 processing |
| `id`, `type` | `@id`, `@type` | the subject or thing, and its classes |
| `statements` | `@nest` | the container's keys are read as the element's own pairs |
| `list` | `@list` | an ordered list |
| `timelines`, `children`, `regions`, `groups` | `@included` | every element is a node of the graph, its pairs on its own IRI |
| `label` | `rdfs:label` | a node's cached name |
| `provenance` | the reverse of `rdf:subject` | each entry is a reified statement whose subject is the holder |
| `property`, `value` | `rdf:predicate`, `rdf:object` | the pair an entry annotates |
| `stated_by`, `basis` | `prov:wasAttributedTo`, `prov:hadPrimarySource` | IRIs |
| `date` | `dcterms:date`, an `xsd:date` | |
| `note` | `rdfs:comment` | |
| `method`, `service`, `match`, `beliefs`, `actor`, `belief` | the format's namespace, `https://timetoalign.github.io/timetoshare/ns#` | `actor` an IRI |
| `manual`, `reconciled`, `imported`, `inferred` | `Manual`, `Reconciled`, `Imported`, `Inferred` in that namespace | the words of `method` |
| `true`, `false`, `unlikely` | `True`, `False`, `Unlikely` in that namespace | the words of `belief` |
| `exact`, `close`, `broad`, `narrow`, `related` | `skos:exactMatch`, `skos:closeMatch`, `skos:broadMatch`, `skos:narrowMatch`, `skos:relatedMatch` | the words of `match` |

The context writes each term with its full IRI, so the format itself
needs no prefix. A key the context does not define, such as `unit`,
`length`, `name` or `graphical`, yields nothing: a manifest without
statements and provenance reads as the empty graph, and a manifest with
them as their triples alone. Every term of a JSON-LD context is read
wherever it stands, so an element key JSON-LD would read is refused there
(`reserved_key`): a key beginning with `@`, `@context` on the manifest
excepted; a key holding a colon; a term the element does not use, such as
`label` on a timeline or `statements` on a group; and a prefix of the
context. A timeline's displayed `name` is therefore no `rdfs:label` of
its subject, and a statement `rdfs:label` states one where wanted.

## 9. Provenance and beliefs

A pair may be annotated with how it was made, its paradata (who stated
it, when, how and on what basis), and with who believes it. The
annotations of an element's pairs are the entries of its `provenance`, a
non-empty list beside its `statements`; the pairs of a value node are
annotated in that node's own `provenance`. A pair without an entry is
stated by the manifest's publisher. Each entry names its pair again, by
its property and its value:

| Key | Required | Holds |
| --- | --- | --- |
| `property` | yes | the pair's property, a compact or absolute IRI; the pair `type` X is written `rdf:type` |
| `value` | yes | the pair's value: a literal, a value object, a thing by its `id` alone, or a node without `id`, compared as a whole |
| `stated_by` | no | the agents who stated it, IRIs or references |
| `date` | no | the day it was stated, `YYYY-MM-DD` |
| `method` | no | `manual`, `reconciled` (looked up in a service and matched), `imported` (taken over from a source document) or `inferred` (derived by a tool), or the IRI of another method |
| `service` | no | the lookup service, an IRI |
| `basis` | no | the sources it rests on: IRIs, or references resolved against the manifest's address, such as `#clt_6` or a file beside the manifest |
| `match` | no | how closely the value matches what was looked up: `exact`, `close`, `broad`, `narrow` or `related` |
| `note` | no | a note in words |
| `beliefs` | no | who believes the pair, a non-empty list of beliefs (below) |

The same entry, without `property` and `value`, annotates a MatchClaim in
the `provenance` column of the MatchClaim table (README, "Provenance and
beliefs"); `provenance.schema.json` defines it once for both.

**Stated pairs and candidates.** A pair listed in `statements` is stated
by the manifest, and its entry, where it has one, annotates it. An entry
whose pair is not listed holds a **candidate**: a name imported without
an identifier, a value a lookup suggested. A candidate
is never stated: it exists only as its entry, and no processor reading
the manifest asserts it. Stating a candidate lists its pair, and its entry
then annotates the stated pair. A subject has at most one entry per pair.

**Beliefs.** A belief is `{actor, belief, date, note?}`: `actor` the
person or organisation who holds it, an IRI, written absolute or as a
reference resolved against the manifest's address as in `stated_by`;
`belief` one of the three strings `"true"`, `"false"` and `"unlikely"`,
words like those of `method` and never JSON booleans; `date` the day it
was stated, `YYYY-MM-DD`; and `note` a note in words. An actor holds at
most one belief per entry: a later belief of the same actor replaces the
earlier one, and one actor's belief leaves every other actor's standing.
A belief is its actor's alone. Nothing in the format derives a truth
value from the beliefs, and nobody imposes one: a belief changes neither
whether a pair is stated nor any other actor's belief, so believing a
stated pair `false` records the belief and leaves the pair stated;
removing it is an edit of its own. A person who states a pair through an editor or the functions of
section 11 is recorded with the belief `true`; a loader or a service
records how the pair was made and holds no belief. A candidate an actor
believes `false` is not offered to that actor again.

**The belief filter** selects, for one actor, the items whose state for
that actor is one of the states it is given. An item has one of four
**states** for an actor: the actor's belief, `true`, `unlikely` or
`false`, or `undecided` where the actor holds no belief on it. The filter
keeps any set of these four states, by default every state but `false`;
without an actor, nothing is filtered. Actors compare as the IRIs they
stand for. Where an item holds beliefs of the actor under two spellings
of one IRI, which a valid manifest never does and a MatchClaim table
checked without its manifest may, its state is the most critical of
them: `false`, then `unlikely`, then `true`. The filter selects the
candidates an editor offers and the MatchClaims that give anchors (README,
"From MatchClaims to anchors") alike.

**Which pair an entry names.** An entry and a pair are the same pair when
their properties are equal after expansion (`type` equals `rdf:type`) and
their values are: literals equal with the same JSON type (`true` is not
`1`); value objects equal after their `@type` is expanded; a node with an
`id` equal to any node with the same expanded `id`, its other keys
ignored, a `type` item X counting as `{id: X}`; nodes without `id` equal
as JSON once their own `provenance` is dropped; lists equal item by item.
Relative references compare as written. Python's `same_pair` and npm's
`samePair` decide it.

**Reading.** Each entry reads as RDF's reification of its pair, a node
with `rdf:subject`, `rdf:predicate` and `rdf:object`, the form RDF 1.2
turns into an annotation of a triple; JSON-LD 1.1 cannot produce a triple
and its annotation from one object. Each belief reads as a node of its
own under `tts:beliefs`. In `layerit_recording` the performer of the
video was reconciled in Wikidata by an editor, who believes it, and the
audio file is a candidate for being derived from the video, the value an
element:

```yaml
timelines:
  -
    id: "#cpt_1"
    provenance:
      -
        beliefs:
          -
            actor: "https://example.org/people/editor"
            belief: "true"
            date: "2026-11-18"
        date: "2026-11-18"
        method: reconciled
        note: "Portuguese pianist; the video's title names her"
        property: "wdt:P175"
        service: "https://www.wikidata.org/w/api.php"
        stated_by: ["https://example.org/people/editor"]
        value:
          id: "wd:Q235650"
    statements:
      "wdt:P175":
        -
          id: "wd:Q235650"
          label: "Maria João Pires"
  -
    id: "#dpt_1"
    provenance:
      -
        date: "2026-11-18"
        method: inferred
        note: "assumed ripped from the video's sound and cut"
        property: "dcterms:source"
        stated_by: ["https://example.org/people/editor"]
        value:
          id: "#cpt_1"
    statements:
      type: ["schema:AudioObject", "melod:Manifestation"]
```

```turtle
:cpt_1 wdt:P175 wd:Q235650 .
wd:Q235650 rdfs:label "Maria João Pires" .
:dpt_1 a schema:AudioObject, melod:Manifestation .

[] rdf:subject :cpt_1 ; rdf:predicate wdt:P175 ; rdf:object wd:Q235650 ;
    dcterms:date "2026-11-18"^^xsd:date ;
    rdfs:comment "Portuguese pianist; the video's title names her" ;
    prov:wasAttributedTo <https://example.org/people/editor> ;
    tts:method tts:Reconciled ;
    tts:service <https://www.wikidata.org/w/api.php> ;
    tts:beliefs [
        tts:actor <https://example.org/people/editor> ;
        tts:belief tts:True ;
        dcterms:date "2026-11-18"^^xsd:date
    ] .

[] rdf:subject :dpt_1 ; rdf:predicate dcterms:source ; rdf:object :cpt_1 ;
    dcterms:date "2026-11-18"^^xsd:date ;
    rdfs:comment "assumed ripped from the video's sound and cut" ;
    prov:wasAttributedTo <https://example.org/people/editor> ;
    tts:method tts:Inferred .
```

with `tts:` standing for the format's namespace. The triple `:dpt_1
dcterms:source :cpt_1` is absent: the candidate is reified and never
asserted. In `djset_segment`, the segment's `sameAs` to the original
MusicBrainz recording is likewise a candidate, which an actor believes
`false`, and nowhere asserted, and the
ISRC of the recording the segment is based on is annotated on the node
that states it, its reified statement having that thing, `wd:Q65658996`,
as its subject. A node value without `id` in an entry, such as a name not
yet reconciled, reads as a blank node of its own: the format identifies
it with the pair by the comparison above, while RDF holds two distinct
blank nodes.

## 10. The catalogue

The catalogue is data shipped with both packages,
`catalogue/catalogue.yaml`, written in canonical YAML with `dumps`, and
described by its JSON Schema `catalogue/catalogue.schema.json`. Tools
read it to offer properties and values and to print pairs in words. The
validators never consult it: it guides a writer, and whether a property
suits a subject is never refused. It holds five members:

- `prefixes`: the namespaces of the vocabularies its patterns use, 21 in
  all (`bf`, `cidoc`, `dcterms`, `gnd`, `gndo`, `lrmoo`, `melod`,
  `melodTerms`, `mus`, `owl`, `prov`, `rdf`, `rdfs`, `rel`, `schema`,
  `skos`, `viaf`, `wd`, `wdt`, `wdtn`, `xsd`), from which writers take
  the prefixes a manifest's context declares.
- `aliases`: namespaces read as equal. `https://schema.org/` is read as
  `http://schema.org/`, the form Wikidata, the GND, VIAF and MusicBrainz
  write.
- `systems`: the **identifier systems**, each with its name, the prefixes
  of the vocabulary its linked data uses, how to look its things up
  (`lookup`, whose `route` is `browser`, `server`, `cross_reference`,
  `database` or `none`) and its **things**, the kinds of identifier it
  mints. A thing has an IRI template (`http://www.wikidata.org/entity/{value}`)
  or none, the URL patterns that recognise an address copied from the
  system's site, each with one capturing group, whether its values are
  written in lower case, the URI of its identifier scheme and the LRMoo
  class of what it identifies, where one applies. The systems are
  Wikidata, MusicBrainz, the GND, VIAF, MeLODy with LRMoo, IMSLP, YouTube,
  ISRC, DOI and the fallback vocabularies (Dublin Core, schema.org, the
  MARC relators, BIBFRAME and others) that state a relation where a
  system has no property of its own.
- `verbs`: the relations in words, `is_a` first, then `same_as`,
  `recording_of`, `performed_by`, `conducted_by`, `composed_by`,
  `version_or_edition_of`, `exemplar_of`, `part_of`, `derived_from`,
  `released_on` and `recorded_at_on`. A verb has a `label`, an
  `inverse_label` where it is read in both directions ("is part of", "has
  part"), and per system a list of alternative patterns
  `{pattern, when?, inverse?, note?}`. A pattern is written as a
  statements container, every value a one-item list: the slot `{id: "?"}`
  takes a thing, `"?"` a literal or class IRI, and `"?role"`, `"?date"`,
  `"?value"` and `"?position"` named literals; `inverse: true` marks the
  inverse reading, and `when` limits an alternative to subjects of some
  types or values of some things.
- `types`: the kinds of thing a subject or a value node is, each with a `label`, its "is
  a" patterns per system, the verbs usually stated of it in order and the
  systems to look its values up in: musical work, recorded performance,
  release, video, printed or scanned edition, score encoding and DJ set.

The verb "performed by" reads, in part:

```yaml
id: performed_by
label: "performed by"
patterns:
  fallback:
    -
      pattern:
        "rel:prf":
          -
            id: "?"
  musicbrainz:
    -
      pattern:
        "schema:contributor":
          -
            "schema:contributor":
              -
                id: "?"
            "schema:roleName": ["?role"]
            type: ["schema:OrganizationRole"]
  wikidata:
    -
      pattern:
        "wdt:P175":
          -
            id: "?"
```

Both packages read it alike. Python's `load_catalogue()` returns the
shipped catalogue as a `Catalogue`, and `read_catalogue(document)` reads
another, checking that no system, thing, verb or type is held twice, that
every prefix it uses is declared, that every system, thing, verb and type
it names exists and that every URL pattern has one capturing group; npm's
`defaultCatalogue()` and `readCatalogue(document)` do the same. Over a
catalogue:

- `recognize(catalogue, url)` returns the system, thing, value and IRI of
  an address copied from a system's site, or none: `https://www.wikidata.org/wiki/Q235650`
  gives the Wikidata item `Q235650` and its IRI
  `http://www.wikidata.org/entity/Q235650`;
- `instantiate(catalogue, verb, system, value, …)` returns the pairs that
  state a verb in a system, its slots filled; `performed_by` in Wikidata
  with `wd:Q235650` gives `("wdt:P175", {"id": "wd:Q235650"})`;
- `verb_of` (npm `verbOf`) returns the verb a pair states, and whether it
  states it inversely: `rel:prf` with a VIAF ID gives `performed_by`,
  `dcterms:hasPart` gives `part_of` read inversely;
- `rectangles(catalogue, manifest, subject)` groups a subject's pairs by
  verb and thing, the unit an editor displays: pairs of one verb, read the
  same way, form one group, transitively, when their values are one
  thing, through their `id`s and the IDs under their `schema:sameAs` and
  `owl:sameAs`, or when their value nodes carry the same string `label`,
  compared as written; "is a" comes always first. The two performer pairs
  of the video in section 6 form one group, and so do
  `schema:exampleOfWork` and `wdt:P629` naming one work in two systems
  under one label.

## 11. Editing statements

Both packages edit statements with pure functions that return a changed
copy of a manifest, Python's in `timetoshare.statements` and npm's under
camel-case names, both exported from the package root. A subject is
addressed by its path in the manifest: `()` the bundle, a path ending in
`timelines`, `children` or `regions` and an index an element, and a path
through a container or a node's key a value node. `subject_path(manifest,
id)` returns the path of the timeline or region of an ID as written in the
manifest, `#cpt_1` in the file form, and `None` names the bundle.

| Python | Does |
| --- | --- |
| `pairs(manifest, subject)`, `entries(manifest, subject)` | the subject's pairs, keys in code-point order and values in list order, and its provenance entries |
| `candidates(manifest, subject, actor=None)` | the subject's candidates, the entries of pairs it does not state; with `actor`, those the actor believes `false` left out, so that a candidate is not offered to that actor again |
| `with_pair(manifest, subject, property, value, *, provenance=None, actor=None, date=None)` | states a pair; an entry the pair already has, a candidate's until now, stays as the stated pair's entry. With `provenance` (the keys of an entry but `property`, `value` and `beliefs`) they are set on the pair's entry, added where there is none; with `actor`, the person stating the pair, the entry records that actor's belief `true` on `date`, replacing the actor's earlier belief |
| `without_pair(manifest, subject, property, value)` | removes a pair and its entry; an emptied list, container or `provenance` is removed |
| `with_candidate(manifest, subject, property, value, *, stated_by, date, method, service=None, basis=(), match=None, note=None)` | adds the entry of a candidate, replacing in place an earlier entry of the pair and keeping its `beliefs`, and leaves the statements as they are; a loader or a service proposing a pair holds no belief |
| `with_belief(manifest, subject, property, value, *, actor, belief, date, note=None)` | records the actor's belief, `"true"`, `"false"` or `"unlikely"`, in the pair's entry, adding the entry where there is none and replacing in place the actor's earlier belief; whether the pair is stated is left as it is |
| `same_pair(context, a, b)` | the comparison of section 9 |
| `expand_iri(context, text)`, `used_prefixes(manifest)` | an IRI expanded through a context, and the prefixes a manifest's statements use |
| `with_context(manifest, prefixes)` | the manifest with its `@context`: the format's terms and the prefixes used, each namespace from its own context first, else from `prefixes` |

npm's `withPair`, `withCandidate` and `withBelief` take the keyword
arguments in an options object, `withPair(manifest, subject, property,
value, { provenance, actor, date })`, and `candidates(manifest, subject,
actor?)` the actor last. Actors compare as their IRIs. Believing a pair
`false` never removes it: the belief is recorded and the statement stays;
`without_pair` removes a pair.

A function refuses a pair already stated (`'<property>' already has this
value`), the removal of a pair not stated (`'<property>' does not have
this value`), a candidate of a stated pair (`'<property>' already has
this value; a stated pair is no candidate`), an actor given without a
date (`a belief needs a date`), a belief none of the three words, a
property that is neither `type` nor an IRI (`'<property>' is no property:
write 'type', a compact IRI or an absolute IRI`), a path that addresses
nothing (`<pointer> addresses no element and no value node`) and a date
the calendar lacks (`'<date>' is no Gregorian calendar date written
YYYY-MM-DD`), raising `ValueError` in Python and `Error` in npm with the
same message. `FORMAT_CONTEXT` holds the 35 terms, `NAMESPACE` the
format's namespace, and `BELIEFS`, `METHODS` and `MATCHES` the words of
the three keys.

## 12. Validation

The validators read the version marker, then finite numbers, then the
schema, the representation of own-axis values and the identity rules
(README, "Identity"), and last the **statement rules**. The schema refuses,
with the code `schema`:

- a context that lacks one of the 35 terms or alters one, a prefix whose
  name is an element key or a URI scheme the format reads, and a
  namespace that does not end in `/` or `#`;
- a container that is empty, a key that is neither `type` nor a compact or
  absolute IRI, a `type` that is not a list of IRIs, a value list that is
  empty or repeats a value, and a value that is `null` or a float with a
  fractional part;
- a value object with both `@language` and `@type`, or with neither; an
  empty node; a node whose `id` is a blank-node label (`_:b0`);
- an empty `provenance`, an entry without `property` or `value`, an
  empty `beliefs`, a belief without `actor`, `belief` or `date`, a
  belief, method or match outside its words, a `property` that is no IRI,
  and a date not written `YYYY-MM-DD`.

The statement rules run after every other rule and report their first
problem, in this order: the context rule over every subject; the
reserved keys of the manifest, the timelines and regions in subject order
and the groups, each element's keys in code-point order; then subject by
subject in subject order, the manifest first, then root by root the
timeline, its regions in array order and its children, depth first. For
each subject they read its ID, its container's keys in code-point order
with their values, a value node where it stands, then its provenance
entries, each entry's keys in code-point order and its beliefs in list
order, and last, entry by entry, the actors of its beliefs against each
other and the entry against the earlier ones.

| Rule | Code | Location | Message |
| --- | --- | --- | --- |
| A manifest without `@context` carries `statements` or `provenance` | `context` | the first such key, `provenance` before `statements` within an element | `statements and provenance need the manifest's @context` |
| An element key that JSON-LD would read (section 8) | `reserved_key` | the key | `'<key>' is reserved on the manifest` (`a timeline`, `a region`, `a group`) |
| An element carrying statements or provenance has an ID that is no IRI fragment, such as one holding a space | `iri` | the element's `id` | `the ID '<id>' of an element with statements is no IRI fragment` |
| A compact IRI names a prefix the context does not declare | `iri` | the IRI | `'<iri>': the prefix '<prefix>' is not declared in @context` |
| A reference beginning with `#` names no element of the manifest | `dangling_target` | the reference | `'<reference>' names no element of this manifest` |
| A node naming an element holds another key | `element_value` | the node | `'<id>' names an element; a value naming an element holds its id alone` |
| A statement value is an integral float, such as `1.0` | `representation` | the value | `a statement value is an integer or a string, never a float: <value>` |
| An entry's `date` names no day of the Gregorian calendar | `calendar_date` | the `date` | `'<date>' is no Gregorian calendar date written YYYY-MM-DD` |
| A belief names the actor of an earlier belief of its entry, actors compared as their IRIs | `belief_actor` | the later belief's `actor` | `'<actor>' already holds belief <index> of this entry; an actor holds one belief` |
| An entry names the pair of an earlier entry of its subject | `provenance_duplicate` | the entry | `the entry repeats the pair of entry <index>` |

An IRI fragment is a string of the characters `A`–`Z`, `a`–`z`, `0`–`9`,
`-._~!$&'()*+,;=:@/?`, code points from U+0080 on (white space excluded)
and `%` followed by two hexadecimal digits. A reference that does not
begin with a scheme and a colon and does not begin with `#` is a relative
reference to another document and is not resolved. The `#` references of
statements and provenance name any ID of the manifest: the manifest's
own, a timeline's, a group's, a MeasureMap's, a conversion map's at any
depth, a region's, a flow-control element's, a named timestamp's, a named
MatchStamp's, an alignment anchor's or a resource's. The
Gregorian calendar's years run from 1 to 9999, so `2026-02-30` is refused.
The messages are the same in both packages, but for a `schema` problem,
whose message is the package's own schema validator's.

**Warnings.** A valid manifest may draw two warnings, which refuse nothing:
`context_absent` at the root (`the manifest has no @context`) for any
manifest without `@context`, and `bundle_blank` at `statements`, else at
`provenance` (`the manifest has statements but no ID; its subject is a
blank node`), for a manifest that states pairs or provenance without an
`id`. Python's `manifest_warnings(value)` and npm's
`manifestWarnings(value)` validate a manifest and return them as
`{code, path, message}` entries, sorted by path and then by code. An
unknown key inside a provenance entry is reported as an unknown key
(README, "Unknown keys"), while the MatchClaim table, whose `provenance`
column holds the entry's members alone, refuses one (README, "Checking
the tables"); `@context`, a container and its values are
closed, and a key they do not declare is refused.

**The statements alone.** Python's `statement_problems(value)` and npm's
`statementProblems(value)` check the statements of a manifest and nothing
else, so that a library reading part of a manifest checks them without
restating which other parts the rules read. They return a list of
problems, empty where the statements are sound: first, member by member,
the manifest's `@context` and every `statements` and `provenance` of the
manifest, a timeline or a region in subject order, each checked for a
number that is not finite (`finite_number`), else against the schema
(`schema`), each member's first problem at its own path; then, only where
no member has one, all the problems of the statement rules. They refuse
nothing outside the statements and do not read the version marker.

## 13. The statement fixtures

Four fixtures under `fixtures/0.2.0/statements/`, each with its minimal
twin, carry statements; every other fixture holds the format's context
and no statement. Their structure is built by timetoalign and their
statements and provenance are attached from
`scripts/fixtures/descriptions/<name>.yaml` when they are emitted.

| Fixture | Holds |
| --- | --- |
| `op106_work` | a bundle about Beethoven's Piano Sonata No. 29, Op. 106, whose five roots side by side are manifestations: the first edition and an encoding of each movement, each naming its work; under `schema:about`, the sonata with its identity in Wikidata, the GND, VIAF and MusicBrainz, the composer, the opus number, the IMSLP page name, and the parts MusicBrainz lists with their positions; the manifest's own prefix `mbw` |
| `layerit_recording` | a bundle about Debussy's "Clair de lune": an MEI encoding of its opening, a video of a performance by Maria João Pires and an audio file cut from it, each a manifestation; "is a" in three vocabularies, the encoding's work in two, the performer in two, a GND candidate believed `false`, provenance on a value node, and a candidate whose value is an element |
| `djset_segment` | a bundle about a DJ set: the set's recording, naming the set by "recording of", and one segment of it, based on a recording stated in Wikidata and MusicBrainz with its ISRC; a performer known only by name, a candidate, and an identity believed `false` |
| `nielsen_record` | the catalogue record of Carl Nielsen's song CNW 133 taken over from its MEI header: the work under `schema:about` with titles in two languages, catalogue numbers and the date; the print and the autograph as manifestation timelines, the print embodying the expression, a value node with the medium of performance; every pair imported with its provenance, and names awaiting reconciliation |

`fixtures/rdf/0.2.0/<name>.nq` holds the expected reading of each, the
canonical N-Quads (RDFC-1.0) of its JSON-LD reading with the base
`https://example.org/manifests/<name>.yaml`, which both packages' tests
reproduce byte for byte with a JSON-LD processor that fetches nothing.
The fixture and its twin read to the same graph, and every other fixture
reads to the empty graph.
