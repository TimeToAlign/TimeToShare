# Describing a TimeToShare manifest

This specification states how a TimeToShare manifest relates its content
to the external entities it is about: works, expressions, manifestations,
items and agents. These relations are the manifest's **description
layer**. It covers the link (section 1), the URIs and identifiers that
name an entity and the registry of identifier schemes (section 2), the
records that describe an entity (section 3), the assertion that attributes
a link (section 4), the parts and wholes of an entity (section 5), absent
parts (section 6), the open vocabularies (section 7) and validation,
of a whole manifest and of the layer alone (section 8). Section 9 works
through one manifest, and section 10 maps every term of the layer to
established vocabularies.

The definitions `Link`, `PartSlot`, `PartOf`, `Assertion`, `Descriptor`,
`Identifier`, `Scheme`, `Level`, `Term`, `Uri` and `UriReference` of the
schema document state the layer normatively; this specification states
what they mean together. `Link` and `Scheme` are public definitions, which
a host schema may refer to (README, "The schema document"). Every key with
a default may be left out, and readers supply the default (README,
"Defaults"). Terms in `code` are JSON members. The description layer holds no events, and the drawing
(`docs/drawing.md`) does not read it.

## 1. Links

### 1.1 What a link states

A **link** is a typed relation from the element holding it to an external
entity at a stated level. Three kinds of element hold links, each in an
array `links`: the manifest as a whole, every timeline at any depth
(segments included) and every region. No other element holds links: a
group, a conversion map, a MeasureMap, a flow-control element and a named
timestamp have none.

| Key | Required | Holds |
| --- | --- | --- |
| `relation` | yes | how the element relates to the entity, a term (section 1.3) |
| `level` | yes | the kind of entity (section 1.2) |
| `uri` | no | URIs of the entity, the first preferred (section 2.1) |
| `identifiers` | no | identifiers of the entity in schemes that mint no URI for it (section 2.1) |
| `records` | no | documents that describe the entity (section 3) |
| `label` | no | a human-readable label of the entity, or null |
| `assertion` | no | who stated the link, when, how and how surely, or null (section 4) |
| `parts_relation` | no | how the entity holds the parts of `parts`, a term, or null (section 5.1) |
| `parts` | no | the parts of the entity in this reading, complete and in order (section 5.1) |
| `parts_ordered` | no | whether the order of `parts` is the entity's own (`true`, the default) or a display order (`false`) |
| `part_of` | no | the wholes the entity belongs to (section 5.3) |

A link never claims that its element is the entity. It states that the
element **pertains to** the entity or, at the level `agent`, in which role
the agent stands to the element's content. A timeline is the time axis
of some content, such as a score, an encoding or a recording, and its
unit, length and nesting describe that axis. A work has no axis, and has
many recordings and editions. A timeline declared identical with a work
would lend the work its length, and two timelines of two performances
declared identical with one work would be one entity. The format
therefore has no identity link and no key such as `same_as` or
`equivalent`: the URIs of a link name the linked entity, and the element
keeps its own ID (README, "Identity").

**One link is one attributed reading.** Where sources disagree about an
entity, as two editions that order the movements of a work differently,
each reading is a link of its own with its own assertion (section 5.2).
Links keep the order in which they are given, and writers keep it: the
canonical order (README, "Canonical order") moves neither the links nor
any array of a link.

### 1.2 Levels

`level` is one of five words, a closed vocabulary. The four bibliographic
levels are those of the IFLA Library Reference Model:

| Level | The entity | In music |
| --- | --- | --- |
| `work` | a creation in the abstract | a sonata, one of its movements, a song |
| `expression` | one realisation of a work | a version, an arrangement, a recorded performance |
| `manifestation` | one embodiment of an expression | an edition, a release |
| `item` | one exemplar of a manifestation | a copy of an edition, a file |
| `agent` | a person or a corporate body | a performer, a compiler |

The level states what kind of entity the link reaches and nothing about
the element. A timeline encoded from a printed score may pertain to the
work and to the edition, in two links at two levels.

### 1.3 Relations

At the four bibliographic levels the relation is the registered word
`pertains_to`. At the level `agent` the relation names the agent's role
instead, as an extension term (section 7): a relator from a published
vocabulary, written as its URI or as a prefixed name, such as
`http://id.loc.gov/vocabulary/relators/prf`, the performer of the MARC
relators. A link at the level `agent` never uses `pertains_to`; the schema
refuses one that does. The format declares no prefixes, so a URI keeps its
meaning wherever the manifest travels, whereas a prefixed name such as
`marcrel:prf` needs a reader who knows the prefix. An unregistered bare
word is read as an unspecified relation at the stated level.

## 2. Naming the entity

### 2.1 URIs and identifiers

A link names its entity in two ways. `uri` lists **entity URIs**, absolute
URIs that identify the entity itself, the first preferred, such as
`http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284` and
`http://www.wikidata.org/entity/Q146730`. `identifiers` lists
**identifiers** of the entity in schemes that mint no URI for it, such as
the IMSLP page name of a work or its number in a composer's catalogue:

| Key of an identifier | Holds |
| --- | --- |
| `scheme` | the scheme: an absolute URI identifying it, or the ID of a scheme of the manifest (section 2.2) |
| `value` | the identifier in its scheme, as the scheme writes it |

**Each fact is stored once.** Where a scheme mints a URI for the entity,
the URI belongs in `uri`, and the value is not repeated as an identifier;
an identifier carries a value that has no URI. The builders of section
2.3 keep to this: an identifier given to them in a scheme whose registry
entry mints entity URIs is stored as its entity URI. Every URI of `uri`
names the linked entity. A part slot
(section 5.1) and a `part_of` entry (section 5.3) name their entities with
the same two keys.

### 2.2 Schemes

An identifier's `scheme` is an absolute URI or the ID of a scheme the
manifest declares. A scheme with a URI of its own is named by it. The
external-identifier properties of Wikidata provide such URIs for many
registries, as `http://www.wikidata.org/entity/P839` does for IMSLP IDs,
and the standard identifier source codes of the Library of Congress
provide others, as `http://id.loc.gov/vocabulary/identifiers/wikidata`
does for Wikidata. A scheme without a URI of its own, such as one
composer's opus numbers or a thematic catalogue, is declared once in the
manifest's `schemes` and named by its ID:

| Key of a scheme | Required | Holds |
| --- | --- | --- |
| `id` | yes | the scheme ID, unique across every ID of the manifest |
| `name` | no | the scheme's name, or null |
| `uri` | no | URIs that identify or describe the scheme, the first preferred |
| `criteria` | no | where a document stating how the scheme assigns its values lies, a URI reference (a relative reference resolves against the location of the manifest), or null |

A scheme is one numbering. Catalogues renumber and split their entries
from one edition to the next, so a catalogue number has its meaning only
within its edition: each edition of a catalogue is a scheme of its own,
whose `criteria` names the text that states what the edition counts as one
entry. Scheme IDs share the manifest's ID space (README, "Identity"), and
`schemes` is written sorted by ID.

### 2.3 The registry of identifier schemes

A URL copied from a catalogue's web page is rarely the form a link keeps.
The **registry of identifier schemes**, the file `registry/schemes.json`,
lists well-known schemes with the URLs each recognises. Both packages ship
it, the wheel as `timetoshare/registry/schemes.json` and the npm package as
`@timetoalign/timetoshare/registry/schemes.json`, and read it alike. Each
entry holds:

| Key | Holds |
| --- | --- |
| `id` | the entry's ID, unique within the registry |
| `name` | the scheme's name, a label for people; the registry reads nothing from it |
| `uri` | the URI of the scheme, the `scheme` of the identifiers the entry gives |
| `level` | the level of every entity of the scheme, or null where the address does not tell |
| `entity_uri` | the template of the scheme's entity URIs, holding `{value}`, or null where the scheme mints none |
| `lowercase` | whether the scheme writes its values in lower case |
| `patterns` | regular expressions, each matching a whole URL and capturing the value in its one group |

The registry holds eight entries, in this order (`wd:` stands for
`http://www.wikidata.org/entity/`):

| ID | Scheme URI | Level | Entity URI template | `lowercase` |
| --- | --- | --- | --- | --- |
| `musicbrainz_work` | `wd:P435` | `work` | `http://musicbrainz.org/work/{value}` | true |
| `musicbrainz_recording` | `wd:P4404` | `expression` | `http://musicbrainz.org/recording/{value}` | true |
| `musicbrainz_release` | `wd:P5813` | `manifestation` | `http://musicbrainz.org/release/{value}` | true |
| `wikidata` | `http://id.loc.gov/vocabulary/identifiers/wikidata` | null | `http://www.wikidata.org/entity/{value}` | false |
| `viaf` | `wd:P214` | null | `http://viaf.org/viaf/{value}` | false |
| `gnd` | `wd:P227` | null | `https://d-nb.info/gnd/{value}` | false |
| `imslp` | `wd:P839` | `work` | null | false |
| `doi` | `wd:P356` | null | `https://doi.org/{value}` | false |

An entity URI template is Wikidata's formatter URI for RDF resources
(P1921) where one exists, unless the issuer prescribes the canonical form,
as the DOI Foundation does with `https://doi.org/`. IMSLP mints no URI for
a work, so its entry has no template and gives identifiers.

**Recognition.** A URL is recognised by the first entry, in registry order,
one of whose patterns matches the whole URL. The entry gives exactly one of
two results. Where it has an entity URI template, it gives the entity URI,
the captured value substituted as written; where it has none, it gives the
identifier `{scheme: <the entry's uri>, value}`, the captured value
percent-decoded as UTF-8 and every space written as an underscore, as a
wiki writes a page name. Where the entry's `lowercase` is true, the value
is then written with its letters `A` to `Z` in lower case, and no other
character changes. It never gives both, so each fact lands in one
place. The entry's level, where it states one, is the level of the entity.
A URL holding white space or a control character is no absolute URI and is
never recognised, and neither is an IMSLP page name whose percent-encoding
is not UTF-8.

**Normalisation.** The patterns accept the forms in which addresses are
copied and give one result for all of them: `http` and `https`, an
optional `www.` (or `m.` for Wikidata), Wikidata's `/wiki/` and `/entity/`,
VIAF's language segment (`https://viaf.org/en/viaf/186299955`), a trailing
`/`, a query and a fragment. MusicBrainz, Wikidata and VIAF entity URIs are
written with `http`, so `https://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284`
gives `http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284`,
and both `https://www.wikidata.org/wiki/Q146730` and
`https://m.wikidata.org/entity/Q146730` give
`http://www.wikidata.org/entity/Q146730`. MusicBrainz IDs ignore case, so
the MusicBrainz entries read an ID in capitals or in mixed case and write
it in lower case:
`https://musicbrainz.org/work/4A622B0D-B0C0-405E-B49E-05B70C108284` gives
`http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284`. The
address
`https://imslp.org/wiki/Piano_Sonata_No.29%2C_Op.106_%28Beethoven%2C_Ludwig_van%29`
gives the identifier `{scheme: "http://www.wikidata.org/entity/P839",
value: "Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)"}` at the level
`work`. Only IMSLP's work pages are recognised: neither `Main_Page` nor a
page of a namespace that IMSLP's wiki declares, `Media:`, `Special:`,
`User:`, `IMSLP:`, `Project:`, `File:`, `Image:`, `MediaWiki:`,
`Template:`, `Help:`, `Category:` and `Module:` and the talk pages
(`Talk:`, `User_talk:` and so on), its colon written plainly or as `%3A`.
A work page whose name begins with such a word, such as
`Main_Page_(Example)`, is recognised.

**Building links from URLs.** Both packages build links and part slots
through the registry, the default one unless another is passed as
`registry`:

| Python | TypeScript | Gives |
| --- | --- | --- |
| `Link.from_urls(*urls, level=, relation=, identifiers=, label=, assertion=, registry=)` | `linkFromUrls(urls, options)` | a link naming its entity by the URLs |
| `Link.from_url(url, …)` | `linkFromUrl(url, options)` | the same, from one URL |
| `PartSlot.from_url(url, absent=, represented_by=, label=, assertion=, registry=)` | `partSlotFromUrl(url, options)` | a part slot (section 5.1) |
| `link.with_uri(*urls, registry=)` | `withUri(link, urls, options)` | the link with the URLs appended |
| `link.with_identifier(scheme, value, registry=)` | `withIdentifier(link, scheme, value, options)` | the link with the identifier appended, or its entity URI |
| `link.with_parts(parts_relation, slots, ordered=, registry=)` | `withParts(link, partsRelation, slots, options)` | the link with the parts of its reading replaced |
| `default_registry().recognize(url)` | `recognize(url, registry)` | what the registry recognises in one URL, or none |

Each URL gives its entity URI, which joins `uri`, or its identifier, which
joins `identifiers`. An absolute URI the registry does not recognise joins
`uri` as written, and a URL that is neither recognised nor an absolute URI
is refused.

**Each fact is stored once** by the builders too. An identifier given
directly, to `from_urls` as `identifiers` or to `with_identifier`
(TypeScript `linkFromUrls` and `withIdentifier`), whose scheme is the
scheme URI of a registry entry that mints entity URIs, is stored as that
entry's entity URI: the URI is written from the template and read back
through the registry as a URL of the scheme, so it is normalised as a URL
is, and joins `uri` after the URIs of the URLs. The identifier
`{"http://www.wikidata.org/entity/P435": "4A622B0D-B0C0-405E-B49E-05B70C108284"}`
so becomes `http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284`.
A value whose entity URI the registry does not read back as one of that
entry is refused: `'op. 106' is no value of the scheme 'MusicBrainz work
ID'`, the message naming the entry's `name`. Every other given identifier,
such as `{"mb_beethoven_opus": "op. 106"}`, joins `identifiers` after the
identifiers from URLs. URLs and identifiers that give one URI or one
identifier collapse into the first.

The link's level is the one given, which no recognised level may
contradict, else the one level the URLs and the entity URIs tell; URLs
that tell two levels, or none where no level is given, are refused. The
relation is `pertains_to` unless the level is `agent`, where the role must
be given. `with_uri` and `with_identifier` refuse a URI recognised at a
level other than the link's, and `with_parts` a part slot whose URI the
registry recognises at such a level: the parts of a work are works. Python's
objects write themselves with `to_dict()` in the complete form and with
`to_dict(minimal=True)` in the minimal form; the TypeScript functions take
a link in either form and return a new link in the complete form. Every
refusal raises Python's `ValueError` or throws TypeScript's `Error`, with
the same message.

The registry is read-only. Python's `registry.with_schemes(*entries)` and
TypeScript's `withSchemes(registry, entries)` return a new registry in
which an entry whose ID the registry holds replaces that entry in place
and any other entry is appended. An entry added so may leave out
`level`, `entity_uri` and `lowercase`, which are read as null, null and
false (TypeScript's type `SchemeEntry`). An entry is refused whose pattern
is no regular expression, has other than one capturing group or uses
syntax that Python's `re` and JavaScript's `RegExp` read differently (a
named group, a lookbehind, an inline flag), whose level is not one of the
five, whose template holds no `{value}`, or whose `lowercase` is no
boolean. An entry with a template must recognise the entity URIs its own
template writes: an identifier given in its scheme is written from the
template and read back, and where another entry recognises the result,
or none does, the identifier is refused as no value of the scheme. The
validators never consult the registry: whether a manifest is valid does
not depend on it.

## 3. Records

`records` lists documents that describe the linked entity, such as its
record in a catalogue or a database. Each is a **descriptor**:

| Key | Required | Holds |
| --- | --- | --- |
| `url` | yes | where the document lies, a URI reference; a relative reference resolves against the location of the manifest |
| `media_type` | no | the document's media type, such as `application/ld+json`, or null |
| `size` | no | its size in bytes, or null |
| `integrity` | no | a digest of its bytes as Subresource Integrity writes one (`sha256-`, `sha384-` or `sha512-` followed by the base64 digest), or null |

A database may change a record's bytes, so its size and integrity are
optional. A record locates a document about the entity and does not
identify the entity: `uri` names what the entity is, and a record's `url`
where a document about it can be fetched.

The prefix of an `integrity` names its algorithm as PREMIS's message
digest algorithm names it: `sha256` is SHA-256, `sha384` SHA-384 and
`sha512` SHA-512. Rights, a key in a format registry and terms of
derivation are not yet part of the descriptor.

## 4. Assertions

`assertion` states who stated a link, when, how and how surely. Every key
is optional:

| Key | Holds |
| --- | --- |
| `asserted_by` | URIs of the agents (people, organisations, software) who made the assertion |
| `asserted_on` | the date of the assertion, a day of the Gregorian calendar written `YYYY-MM-DD`, or null |
| `method` | how the assertion was reached, a term, or null |
| `service` | the URI of the service that reached the assertion, such as a reconciliation endpoint, or null |
| `based_on` | URI references of the sources the assertion rests on |
| `match` | how closely the linked entity corresponds to what the element represents, or null |
| `status` | whether the assertion stands, or null |

`method` takes an open vocabulary with four registered words: `manual`
(stated by a person), `reconciled` (matched by a reconciliation service,
named by `service`), `imported` (taken from other data, named by
`based_on`) and `inferred` (derived from other statements). The event
types of PREMIS enter as their URIs at id.loc.gov, which are extension
terms, such as `http://id.loc.gov/vocabulary/preservation/eventType/mee`,
metadata extraction. An unregistered bare word is read as a method not
stated.

`match` reads as the mapping relations of SKOS: `exact`, `close`, `broad`
(the linked entity is broader than what the element represents), `narrow`
(it is narrower) or `related`. A link from a recording of one movement to
the whole sonata is a `broad` match.

`status` is `confirmed`, `unconfirmed` (proposed and not yet checked) or
`rejected` (checked and found wrong). A rejected link is kept so that it is
not proposed again, by a reconciliation service for instance. `match` and
`status` are closed vocabularies; another word is refused. Null, the
default of every key, means that the assertion does not state it.

Python's `Assertion` holds its date as a `datetime.date`. Its constructor,
and so `Assertion.from_dict`, reads a string as a date written
`YYYY-MM-DD` and refuses one written otherwise or naming a day the
calendar lacks, such as `2026-02-30`, and any value that is neither a
string nor a `datetime.date`, with the message of the validators'
`calendar_date` (section 8). TypeScript's functions check the dates of the
assertions of every link they return alike.

**Inheritance.** A part slot (section 5.1) and a `part_of` entry
(section 5.3) may carry an assertion of their own; one that carries none
inherits its link's. Python's `link.assertion_for(entry)` and TypeScript's
`assertionFor(link, entry)` return the assertion that holds for an entry.

**Differing assertions make separate links.** An assertion attributes a
whole link. Where two agents state a link on different grounds, or one
confirms what another rejects, each statement is a link of its own with its
own assertion, so that a reader may choose among them by agent, source,
method or status. Two links of one element may therefore name the same
entity.

## 5. Parts and wholes

### 5.1 Part readings

A link may state the parts of its entity in its reading. `parts_relation`
states how the entity holds them, a term of an open vocabulary with three
registered words:

| Word | The entity | Example |
| --- | --- | --- |
| `has_part` | is made up of the parts | movements make up a sonata |
| `aggregates` | gathers entities that exist on their own | an album gathers recordings |
| `incorporates` | takes in, as an integral part of its own, an entity that realises another work | a pasticcio takes in an aria, a DJ mix a track |

An unregistered bare word is read as an unspecified structural relation.

`parts` lists the parts **complete and in order**. The position of a part
is its place in the list, counted from 1; a slot has no position of its
own. Every part the reading counts has a slot, whether an element of the
manifest represents it or not (section 6), so the list states the reading
whole. `parts_ordered` is `true` by default, making the order of `parts`
the order of the parts in the entity; `false` makes it a display order
only, for a whole whose parts have no order of their own. A non-empty
`parts` requires a `parts_relation`.

Each **part slot** names one part and states what represents it:

| Key | Holds |
| --- | --- |
| `uri` | URIs of the part, the first preferred |
| `identifiers` | identifiers of the part |
| `label` | a human-readable label of the part, or null |
| `represented_by` | the IDs of the timelines (at any depth, segments included) and regions of the manifest that represent the part |
| `absent` | why no element of the manifest represents the part, a term, or null (section 6) |
| `assertion` | who stated the slot, or null, where the link's assertion holds |

Exactly one of `represented_by` and `absent` is stated: either
`represented_by` is non-empty and `absent` null, or `absent` is a term and
`represented_by` empty. Several elements may represent one part, such as a
movement's region in a score and its segment in a recording. The parts of
an entity belong to the link and the nesting of timelines to their
content, so a reading asks for no particular nesting of the elements it
names, and the same elements may serve several readings.

### 5.2 Competing readings

Readings that differ are separate links. Beethoven's Piano Sonata No. 29,
Op. 106, appeared in 1819 in two first editions. Artaria in Vienna printed
the four movements in the order I–II–III–IV. The Regent's Harmonic
Institution in London printed the work in two parts: the first holds the
first three movements in the order I–III–II, the Adagio sostenuto before
the Scherzo, and the second the Introduzione and Fuga
([IMSLP](https://imslp.org/wiki/Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van))
holds both editions). A manifest holding the four movements of a
recording as four timelines, their lengths not stated, states both orders
as two readings of the one work, each resting on its edition:

```json
{
  "timetoshare": "0.2.0",
  "timelines": [
    {"id": "mvt_1", "name": "I. Allegro", "unit": "seconds", "length": null},
    {"id": "mvt_2", "name": "II. Scherzo. Assai vivace", "unit": "seconds", "length": null},
    {"id": "mvt_3", "name": "III. Adagio sostenuto", "unit": "seconds", "length": null},
    {"id": "mvt_4", "name": "IV. Introduzione. Largo – Allegro risoluto", "unit": "seconds", "length": null}
  ],
  "links": [
    {
      "relation": "pertains_to",
      "level": "work",
      "uri": ["http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284"],
      "assertion": {"method": "imported", "based_on": ["https://example.org/editions/vienna-1819"]},
      "parts_relation": "has_part",
      "parts": [
        {"uri": ["http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980"], "represented_by": ["mvt_1"]},
        {"uri": ["http://musicbrainz.org/work/7813c9cf-6054-3ef3-b9ed-8ae4690581c9"], "represented_by": ["mvt_2"]},
        {"uri": ["http://musicbrainz.org/work/7d110747-f011-41d4-9ce5-a1fad9abed2f"], "represented_by": ["mvt_3"]},
        {"uri": ["http://musicbrainz.org/work/cfa82cd6-bcb5-39dd-9beb-c98e275c7c84"], "represented_by": ["mvt_4"]}
      ]
    },
    {
      "relation": "pertains_to",
      "level": "work",
      "uri": ["http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284"],
      "assertion": {"method": "imported", "based_on": ["https://example.org/editions/london-1819"]},
      "parts_relation": "has_part",
      "parts": [
        {"uri": ["http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980"], "represented_by": ["mvt_1"]},
        {"uri": ["http://musicbrainz.org/work/7d110747-f011-41d4-9ce5-a1fad9abed2f"], "represented_by": ["mvt_3"]},
        {"uri": ["http://musicbrainz.org/work/7813c9cf-6054-3ef3-b9ed-8ae4690581c9"], "represented_by": ["mvt_2"]},
        {"uri": ["http://musicbrainz.org/work/cfa82cd6-bcb5-39dd-9beb-c98e275c7c84"], "represented_by": ["mvt_4"]}
      ]
    }
  ]
}
```

The two links name the same work and the same four timelines; they differ
in the order of their slots and in the sources their assertions rest on.
The order of the timelines in the manifest belongs to neither reading. That
the London edition printed the fourth movement as a part of its own is a
fact of the edition, which a link at the level `manifestation` may state
with parts of its own, leaving the work's reading as it is.

### 5.3 Wholes

`part_of` lists the wholes the linked entity belongs to, such as the work a
movement belongs to or the series an edition appears in. Each entry holds:

| Key | Required | Holds |
| --- | --- | --- |
| `parts_relation` | yes | how the whole holds the linked entity, a term of the vocabulary of section 5.1 |
| `uri`, `identifiers`, `label` | no | the whole, named as a link names its entity |
| `position` | no | the position of the linked entity among the parts of the whole, counted from 1, or null where it is not stated |
| `assertion` | no | who stated the entry, or null, where the link's assertion holds |

An entity may belong to several wholes, as a song to several collections,
each an entry of its own. `parts` and `part_of` are independent: a link
may state the whole of its entity without listing the whole's other parts,
and a manifest may state both directions. A recording of the first
movement of Op. 106 alone links its timeline to the movement, which belongs
to the sonata at position 1, and the manifest as a whole to the sonata,
whose other three movements the recording does not contain and no element
of the manifest represents (section 6); a second link of the timeline
names its performer:

```json
{
  "timetoshare": "0.2.0",
  "timelines": [
    {
      "id": "allegro",
      "unit": "seconds",
      "length": null,
      "links": [
        {
          "relation": "pertains_to",
          "level": "work",
          "uri": ["http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980"],
          "label": "I. Allegro",
          "part_of": [
            {
              "parts_relation": "has_part",
              "uri": ["http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284"],
              "position": 1
            }
          ]
        },
        {
          "relation": "http://id.loc.gov/vocabulary/relators/prf",
          "level": "agent",
          "uri": ["https://example.org/people/pianist"]
        }
      ]
    }
  ],
  "links": [
    {
      "relation": "pertains_to",
      "level": "work",
      "uri": ["http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284"],
      "parts_relation": "has_part",
      "parts": [
        {"uri": ["http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980"], "represented_by": ["allegro"]},
        {"uri": ["http://musicbrainz.org/work/7813c9cf-6054-3ef3-b9ed-8ae4690581c9"], "absent": "not_represented"},
        {"uri": ["http://musicbrainz.org/work/7d110747-f011-41d4-9ce5-a1fad9abed2f"], "absent": "not_represented"},
        {"uri": ["http://musicbrainz.org/work/cfa82cd6-bcb5-39dd-9beb-c98e275c7c84"], "absent": "not_represented"}
      ]
    }
  ]
}
```

## 6. Absence

A part slot that no element of the manifest represents states why in
`absent`, a term of an open vocabulary with five registered words:

| Word | Meaning |
| --- | --- |
| `not_represented` | the part exists and is identified, and no element of this manifest represents it |
| `lost` | the part existed, and no source of it survives |
| `unfinished` | the part was begun or planned and never completed |
| `unknown` | whether a part occupies this position, or which part does, is not known |
| `not_recorded` | the slot exists, and the publisher states nothing about how the part is represented |

An unregistered bare word is read as `not_represented`. The first and the
last word differ in what the publisher states. Of a recording of the first
movement alone, as in section 5.3, the other three movements exist, are
identified by their URIs and are represented by no element of the
manifest: their slots are `not_represented`, as they are in the manifest
of a recording of the whole sonata that holds the first movement alone.
`not_recorded` states the slot and nothing more: a dataset that leaves
open whether it covers a movement uses `not_recorded`.

An absent part is a slot, stated explicitly, for three reasons. The list
is complete and its order gives the positions, so a part that nothing
represents still occupies its place, and the parts after it keep theirs.
Omission never means absence: a part left out of the list cannot be told
from a part nobody stated, whereas a slot holds the part's place in the
reading, keeps its identity addressable through its URIs where it is
known, and says why nothing represents it. And a manifest read as linked
data loses a `null`: in
[JSON-LD](https://www.w3.org/TR/json-ld11/) a member whose value is null
has the same meaning as a member not given, and an array is unordered
unless it is declared a list, so a null standing for a part would leave
nothing to read.

## 7. Open vocabularies

Four keys take a **term** (`Term`), a word of an open vocabulary: a
non-empty string without white space or a control character.

| Key | Registered words | An unregistered bare word reads as |
| --- | --- | --- |
| a link's `relation` | `pertains_to` | an unspecified relation at the stated level |
| a link's and a `part_of` entry's `parts_relation` | `has_part`, `aggregates`, `incorporates` | an unspecified structural relation |
| an assertion's `method` | `manual`, `reconciled`, `imported`, `inferred` | a method not stated |
| a part slot's `absent` | `not_represented`, `lost`, `unfinished`, `unknown`, `not_recorded` | `not_represented` |

A term holding a colon is an **extension term**, a prefixed name or a URI,
and is read as written: `marcrel:prf`,
`http://id.loc.gov/vocabulary/relators/prf` or a PREMIS event type. A bare
term is meant to be one of the words registered for its key. One that is
not, a misspelling or a word registered for another key (`has_part` as a
`relation`, `lost` as a `method`), is kept, read as its key's fallback and
listed as a warning, and never refused. Python's
`unregistered_terms(value)` and TypeScript's `unregisteredTerms(value)`
validate a manifest and return its unregistered terms as `{path, term}`
entries sorted by path. Both packages export the registered words as
`RELATIONS`, `PARTS_RELATIONS`, `METHODS` and `ABSENCE_REASONS`.

`level`, `match` and `status` are closed vocabularies, exported as
`LEVELS`, `MATCHES` and `STATUSES`: a word outside them is refused.

## 8. Validation

Besides a value of the wrong JSON type, the schema refuses, with the code
`schema`:

- a link without `relation` or without `level`, or with a level that is not
  one of the five;
- a link at the level `agent` with the relation `pertains_to`;
- a non-empty `parts` whose `parts_relation` is null or left out;
- a link without parts, its `parts` empty or left out, that states a
  `parts_relation` (refused at the `parts_relation`) or `parts_ordered`
  false (refused at the `parts_ordered`), the shared rejection cases
  `description_parts_relation_without_parts` and
  `description_parts_ordered_without_parts`;
- a part slot both represented and absent, or neither;
- a `part_of` entry without `parts_relation`, or with a `position` below 1;
- an assertion whose `match` or `status` lies outside its closed vocabulary,
  or whose `asserted_on` is not written `YYYY-MM-DD`;
- an entry of a `uri` or of `asserted_by`, or a `service`, that is not an
  absolute URI (`Uri`: a scheme name, a colon and at least one more
  character, without white space or a control character);
- a term, an entry of `based_on`, a record's `url` or a scheme's `criteria`
  that is empty or holds white space or a control character (`Term` and
  `UriReference`);
- a record without `url`, with a negative `size` or with an `integrity` not
  written as Subresource Integrity writes one;
- an identifier without `scheme` or `value`, or with either empty, and a
  scheme without `id`.

The description model refuses these links, and a date the calendar lacks,
when it builds or reads them, with the same message in both packages:
Python raises `ValueError`
from the constructors of `Link`, `PartSlot` and `Assertion`, and so from
`from_dict`, the builders and every `with_*` method, and every TypeScript
function that returns a link or a part slot throws `Error`:

| Refused | Message |
| --- | --- |
| a level that is not one of the five | `'<level>' is no level` |
| a link at the level `agent` with the relation `pertains_to` | `an agent link never uses the relation 'pertains_to'` |
| parts without a `parts_relation` | `a link with parts states its parts_relation` |
| a `parts_relation` without parts, also from `with_parts` given no slot | `a link without parts states no parts_relation` |
| `parts_ordered` false without parts | `a link without parts keeps parts_ordered true` |
| a part slot both represented and absent | `a part slot is represented or absent, not both` |
| a part slot neither represented nor absent | `a part slot is represented by an element or absent` |
| an `asserted_on` not written `YYYY-MM-DD` or naming a day the calendar lacks | `'<date>' is no Gregorian calendar date written YYYY-MM-DD` |

After the schema, both validators check the IDs, dates and references of
the layer where the order of the identity rules (README, "Identity")
places them. A scheme's ID is checked with the other IDs unique across
the manifest, after the named timestamps' IDs, and the manifest's ID
after the scheme IDs. The links come last, after every other identity
rule, link by link: the manifest's links first, then root by root each
timeline's own links, its regions' links in array order and its
children's, depth first. Within a link they read its assertion's
`asserted_on` and its `identifiers`, then, slot by slot, each part slot's
assertion's `asserted_on`, its `identifiers` and its `represented_by`,
then, entry by entry, each `part_of` entry's assertion's `asserted_on` and
its `identifiers`.

| Rule | Code | Location | Message |
| --- | --- | --- | --- |
| A scheme's ID repeats an earlier ID of the manifest | `duplicate_id` | the scheme's `id` | `'<id>' is not unique in the manifest, first at <pointer>` |
| The manifest's ID is a scheme's ID | `manifest_id` | `id` | `'<id>' is not unique in the manifest, first at <pointer>` |
| An assertion's `asserted_on` names no day of the Gregorian calendar | `calendar_date` | the `asserted_on` | `'<date>' is no Gregorian calendar date written YYYY-MM-DD` |
| An identifier's `scheme` names no scheme of the manifest and is no absolute URI | `dangling_target` | the `scheme` | `'<scheme>' names no scheme of this manifest and is no absolute URI` |
| A part slot's `represented_by` entry names no timeline (at any depth) or region of the manifest | `dangling_target` | the entry | `'<id>' names no timeline or region of this manifest` |

The schema reads only the form `YYYY-MM-DD` of a date; `calendar_date`
checks that the Gregorian calendar has the day. Its years run from 1 to
9999 and its months from 1 to 12, and February has 29 days in a year
divisible by 4 and not by 100, or by 400, so `2024-02-29` passes and
`2026-02-30`, `2100-02-29` and `0000-01-01` are refused. A manifest the
validators accept is so one the description model reads.

Two findings are warnings, never errors: unknown keys on any object of the
layer (README, "Unknown keys") and unregistered bare terms (section 7).
The validators never consult the registry of identifier schemes, so they do
not compare a link's URIs with its level; the builders of section 2.3 do.

**The description layer alone.** Python's `description_problems(manifest)`
and TypeScript's `descriptionProblems(manifest)` check the description
layer of a manifest and nothing else. They return the list of its
problems, each a `SchemaValidationError` with its `code`, `path` and
message (`message` in Python, `detail` in TypeScript), and an empty list
where the layer is sound. They check, in this order:

1. Each array of the layer where it stands: the manifest's `schemes`, the
   manifest's `links`, then root by root each timeline's `links`, its
   regions' `links` in array order and its children's, depth first. Each
   is checked as `validate` checks it, for a number that is not finite
   (`finite_number`), else against the schema's definition `Scheme` or
   `Link` (`schema`), the violation located by the path rule of the
   validators. Each array gives its first problem at most, at its own
   path in the manifest.
2. Only where no array has a problem, the rules of the table above, over
   the whole manifest and in its order: the scheme IDs (`duplicate_id`),
   the manifest's ID (`manifest_id`), then link by link the dates
   (`calendar_date`) and references (`dangling_target`).

They refuse nothing outside the description layer and do not read the
version marker: a manifest whose timelines, groups or `graphical` object
break other rules, or which declares another version, but whose schemes
and links are sound has no problem here. A library that reads only part
of a manifest, such as its links, so checks the layer without restating
which other parts of the manifest the rules read: the IDs of its
timelines, regions, groups, MeasureMaps and named timestamps. The two
packages give the same codes and paths, and the same messages but for a
`schema` problem, whose message is the package's own schema validator's.

## 9. A worked example: the work bundle of Op. 106

The manifest below describes Beethoven's Piano Sonata No. 29 as a work and
holds no timeline. It is the bundle the tests of both packages build and
read back, written by the standard writer in the minimal form; the fixture
`bundles/op106_work` holds the same manifest, with the generator that
wrote it recorded in `meta`:

```json
{
  "links": [
    {
      "assertion": {
        "asserted_by": [
          "https://example.org/people/editor"
        ],
        "asserted_on": "2026-11-17",
        "method": "manual",
        "status": "confirmed"
      },
      "identifiers": [
        {
          "scheme": "http://www.wikidata.org/entity/P839",
          "value": "Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)"
        },
        {
          "scheme": "mb_beethoven_opus",
          "value": "op. 106"
        }
      ],
      "label": "Piano Sonata No. 29 in B♭ major, Op. 106",
      "level": "work",
      "parts": [
        {
          "absent": "not_represented",
          "label": "I. Allegro",
          "uri": [
            "http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980"
          ]
        },
        {
          "absent": "not_represented",
          "label": "II. Scherzo. Assai vivace",
          "uri": [
            "http://musicbrainz.org/work/7813c9cf-6054-3ef3-b9ed-8ae4690581c9"
          ]
        },
        {
          "absent": "not_represented",
          "label": "III. Adagio sostenuto",
          "uri": [
            "http://musicbrainz.org/work/7d110747-f011-41d4-9ce5-a1fad9abed2f"
          ]
        },
        {
          "absent": "not_represented",
          "label": "IV. Introduzione. Largo – Allegro risoluto",
          "uri": [
            "http://musicbrainz.org/work/cfa82cd6-bcb5-39dd-9beb-c98e275c7c84"
          ]
        }
      ],
      "parts_relation": "has_part",
      "relation": "pertains_to",
      "uri": [
        "http://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284",
        "http://www.wikidata.org/entity/Q146730",
        "http://viaf.org/viaf/186299955"
      ]
    }
  ],
  "name": "Beethoven, Piano Sonata No. 29, Op. 106",
  "schemes": [
    {
      "id": "mb_beethoven_opus",
      "name": "Works of Ludwig van Beethoven by opus number",
      "uri": [
        "https://musicbrainz.org/series/004f17aa-0f46-4fec-b939-c5dfc849e5c6"
      ]
    }
  ],
  "timelines": [],
  "timetoshare": "0.2.0"
}
```

- The manifest's one link pertains to the work. Its `uri` holds the entity
  URIs that the registry gives for the work's pages at MusicBrainz,
  Wikidata and VIAF, the MusicBrainz work first.
- IMSLP mints no URI for a work, so its page name is an identifier in the
  scheme `http://www.wikidata.org/entity/P839`, the IMSLP ID.
- The opus number is an identifier in the scheme `mb_beethoven_opus`,
  declared in `schemes` and identified by the MusicBrainz series of
  Beethoven's works by opus number.
- The four slots name the movements by their MusicBrainz works, in the
  order of the work. The manifest holds no timeline, so each is
  `not_represented`.
- The assertion states who made the link, when and how. No slot carries an
  assertion, so it holds for every slot.
- The complete form adds every default (README, "Defaults"): the link's
  `records`, `parts_ordered`, `part_of`, the assertion's `service`,
  `based_on` and `match`, each slot's `identifiers`, `represented_by` and
  `assertion`, the scheme's `criteria`, and the manifest's `meta`,
  `groups` and `measure_maps`.

In Python the bundle is built from the addresses of the work's pages:

```python
import datetime

from timetoshare import Assertion, Link, PartSlot, Scheme, dumps

MOVEMENTS = [
    ("80cbaf7b-a1da-3fc5-b650-6eb72a803980", "I. Allegro"),
    ("7813c9cf-6054-3ef3-b9ed-8ae4690581c9", "II. Scherzo. Assai vivace"),
    ("7d110747-f011-41d4-9ce5-a1fad9abed2f", "III. Adagio sostenuto"),
    ("cfa82cd6-bcb5-39dd-9beb-c98e275c7c84", "IV. Introduzione. Largo – Allegro risoluto"),
]
scheme = Scheme(
    "mb_beethoven_opus",
    name="Works of Ludwig van Beethoven by opus number",
    uri=("https://musicbrainz.org/series/004f17aa-0f46-4fec-b939-c5dfc849e5c6",),
)
link = Link.from_urls(
    "https://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284",
    "https://www.wikidata.org/wiki/Q146730",
    "https://viaf.org/viaf/186299955",
    "https://imslp.org/wiki/Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)",
    identifiers={"mb_beethoven_opus": "op. 106"},
    label="Piano Sonata No. 29 in B♭ major, Op. 106",
    assertion=Assertion(
        asserted_by=("https://example.org/people/editor",),
        asserted_on=datetime.date(2026, 11, 17),
        method="manual",
        status="confirmed",
    ),
).with_parts(
    "has_part",
    [
        PartSlot.from_url(
            f"https://musicbrainz.org/work/{mbid}", label=label, absent="not_represented"
        )
        for mbid, label in MOVEMENTS
    ],
)
manifest = {
    "timetoshare": "0.2.0",
    "name": "Beethoven, Piano Sonata No. 29, Op. 106",
    "timelines": [],
    "schemes": [scheme.to_dict(minimal=True)],
    "links": [link.to_dict(minimal=True)],
}
text = dumps(manifest)
```

and in TypeScript, with `MOVEMENTS`, `URLS` and `EDITOR` holding the same
values:

```ts
import { dumps, linkFromUrls, minimal, partSlotFromUrl, withParts } from "@timetoalign/timetoshare";

const link = withParts(
  linkFromUrls(URLS, {
    identifiers: { mb_beethoven_opus: "op. 106" },
    label: "Piano Sonata No. 29 in B♭ major, Op. 106",
    assertion: EDITOR,
  }),
  "has_part",
  MOVEMENTS.map(([mbid, label]) =>
    partSlotFromUrl(`https://musicbrainz.org/work/${mbid}`, { label, absent: "not_represented" }),
  ),
);
const text = dumps(
  minimal({
    timetoshare: "0.2.0",
    name: "Beethoven, Piano Sonata No. 29, Op. 106",
    timelines: [],
    schemes: [
      {
        id: "mb_beethoven_opus",
        name: "Works of Ludwig van Beethoven by opus number",
        uri: ["https://musicbrainz.org/series/004f17aa-0f46-4fec-b939-c5dfc849e5c6"],
      },
    ],
    links: [link],
  }),
);
```

Both give the text above. A second reading of the work, its movements in
the London order with an assertion of its own, is a second link beside the
first (section 5.2).

## 10. Vocabulary

Each term of the layer is mapped to its closest term in a widely used
vocabulary, then to the domain model: the IFLA Library Reference Model
(LRM), its object-oriented definition LRMoo and the CIDOC CRM on which
LRMoo builds. LRMoo and CIDOC CRM terms are given by their identifiers
(`F1 Work`, `R67 has part`, `P14 carried out by`). The fit is **exact**
where the terms mean the same, **close** where they agree in everything
the layer uses, and **approximate** where the note states a difference.
This version of the format defines no linked-data form; the table states
correspondences and prescribes no serialisation.

| Prefix | Namespace |
| --- | --- |
| `dcterms:` | `http://purl.org/dc/terms/` |
| `schema:` | `https://schema.org/` |
| `ore:` | `http://www.openarchives.org/ore/terms/` |
| `frbr:` | `http://purl.org/vocab/frbr/core#` |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` |
| `prov:` | `http://www.w3.org/ns/prov#` |
| `oa:` | `http://www.w3.org/ns/oa#` |
| `as:` | `http://www.w3.org/ns/activitystreams#` |
| `relators:` | `http://id.loc.gov/vocabulary/relators/` |
| `eventType:` | `http://id.loc.gov/vocabulary/preservation/eventType/` |
| `wd:` | `http://www.wikidata.org/entity/` |
| `wikibase:` | `http://wikiba.se/ontology#` |

| Term | Widely used | Domain model | Fit |
| --- | --- | --- | --- |
| **Relation** | | | |
| `pertains_to` | `dcterms:relation` | P67 refers to | approximate: both relate a resource to a related resource without a type; the link's `level` adds the type |
| an agent's role (extension term) | a MARC relator, such as `relators:prf` | P14.1 in the role of, on P14 carried out by | close: the relator names the role |
| **Structural relation** | | | |
| `has_part` | `dcterms:hasPart`; `schema:hasPart` | work: LRM-R18, R67 has part; expression: LRM-R23, R5 has component; manifestation: LRM-R26, R71 has part; item: P46 is composed of | close to LRMoo, level by level; Dublin Core and schema.org are broader, any inclusion, physical or logical |
| `aggregates` | `ore:aggregates` | expression: LRM-R25 (aggregated), which LRMoo maps to P165 incorporates | approximate: `ore:aggregates` gathers web resources and is a sub-property of `dcterms:hasPart`; LRM states aggregation between expressions (LRM-R25) apart from whole and part (LRM-R23) |
| `incorporates` | none in Dublin Core or schema.org, whose `hasPart` is broader; MusicBrainz's relationship types *included works* (between works) and *DJ-mix* (between recordings) | expression: R75 incorporates, a sub-property of P165 incorporates; work: R74 uses expression of | close to LRMoo: in both the incorporated entity realises another work; MusicBrainz's types are kinds of it |
| `part_of` entry | `dcterms:isPartOf`; `schema:isPartOf`; under `aggregates` `ore:isAggregatedBy` | the inverse of its `parts_relation`: R67 forms part of, R5 is component of, R71 is part of, R75 is incorporated in, R74 has expression used in | as its `parts_relation` |
| **Level** | | | |
| `work` | `frbr:Work` | LRM-E2 Work; F1 Work | exact in LRM and LRMoo; FRBR core follows the earlier FRBR model |
| `expression` | `frbr:Expression` | LRM-E3 Expression; F2 Expression | as `work` |
| `manifestation` | `frbr:Manifestation` | LRM-E4 Manifestation; F3 Manifestation | as `work` |
| `item` | `frbr:Item` | LRM-E5 Item; F5 Item | as `work` |
| `agent` | `frbr:ResponsibleEntity` | LRM-E6 Agent; E39 Actor | close |
| **Assertion** | | | |
| a link with its assertion | `oa:Annotation` with the motivation `oa:linking`, the element its target and the entity its body | E13 Attribute Assignment, with P140 assigned attribute to and P141 assigned | approximate: an annotation and an attribute assignment are resources of their own; a link is part of its element |
| `asserted_by` | `prov:wasAttributedTo`; an annotation's `dcterms:creator` | P14 carried out by | close |
| `asserted_on` | an annotation's `dcterms:created` | P4 has time-span | close: a date, where `dcterms:created` takes a date and time |
| `method` | none | P32 used general technique | approximate: P32 types the technique of an activity, `method` names how an assertion was reached |
| `service` | an annotation's `as:generator` | P16 used specific object | approximate: the generator is the agent, the service its URI |
| `based_on` | `prov:wasDerivedFrom` | P16 used specific object | approximate: PROV derives one entity from another; `based_on` names sources only |
| `match` | `wd:P4390`, mapping relation type | none | close: P4390 takes the SKOS mapping relations as values, as `match` does |
| `status` | none | none | |
| **Method** | | | |
| `manual` | none | none | |
| `reconciled` | none | none | |
| `imported` | `eventType:mee`, metadata extraction | none | close: both take a statement from data that exists apart from it, which `based_on` names |
| `inferred` | `wd:P3452`, inferred from | none | approximate: a reference property, used where `inferred` is a value |
| **Match** | | | |
| `exact` | `skos:exactMatch` | none | close: SKOS types both ends as concepts, so the five words are values, as under P4390 |
| `close` | `skos:closeMatch` | none | as `exact` |
| `broad` | `skos:broadMatch`: the linked entity is the broader | none | as `exact` |
| `narrow` | `skos:narrowMatch`: the linked entity is the narrower | none | as `exact` |
| `related` | `skos:relatedMatch` | none | as `exact` |
| **Status** | | | |
| `confirmed` | none | none | |
| `unconfirmed` | none | none | |
| `rejected` | `wikibase:DeprecatedRank` | none | approximate: Wikidata deprecates a statement known to include errors and keeps it |

Sources:

- DCMI Metadata Terms, DCMI Recommendation of 2020-01-20:
  <https://www.dublincore.org/specifications/dublin-core/dcmi-terms/>.
- Schema.org, version 30.1 of 2026-09-16: <https://schema.org/hasPart>,
  <https://schema.org/isPartOf>.
- ORE Specification, Vocabulary, version 1.0 of 2008-10-17:
  <http://www.openarchives.org/ore/1.0/vocabulary>.
- Expression of Core FRBR Concepts in RDF, version of 2005-08-10:
  <https://vocab.org/frbr/core>.
- SKOS Simple Knowledge Organization System Reference, W3C Recommendation
  of 2009-08-18, section 10: <https://www.w3.org/TR/skos-reference/>.
- PROV-O: The PROV Ontology, W3C Recommendation of 2013-04-30:
  <https://www.w3.org/TR/prov-o/>.
- Web Annotation Vocabulary, W3C Recommendation of 2017-02-23:
  <https://www.w3.org/TR/annotation-vocab/>.
- PREMIS event types, Library of Congress Preservation Vocabularies:
  <https://id.loc.gov/vocabulary/preservation/eventType>.
- MARC relators, Library of Congress:
  <https://id.loc.gov/vocabulary/relators>.
- MusicBrainz relationship types between works and between recordings:
  <https://musicbrainz.org/relationships/work-work>,
  <https://musicbrainz.org/relationships/recording-recording>.
- Wikidata, the properties P4390 and P3452 and the statement ranks:
  <https://www.wikidata.org/wiki/Property:P4390>,
  <https://www.wikidata.org/wiki/Property:P3452>,
  <https://www.wikidata.org/wiki/Help:Ranking>.
- LRMoo, object-oriented definition and mapping from the IFLA Library
  Reference Model, version 1.0 of April 2024, with its mapping of the LRM
  entities and relationships in section 8:
  <https://cidoc-crm.org/sites/default/files/LRMoo_V1.0.pdf>.
- CIDOC CRM, version 7.1.3 of February 2024, on which LRMoo 1.0 builds:
  <https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html>.
