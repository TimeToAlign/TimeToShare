# Fixtures

The fixtures of the current version, 0.2.0, are kept in `fixtures/0.2.0/`,
its drawings in `fixtures/0.2.0/drawings/`, its rejection cases under
`fixtures/rejections/0.2.0/` and its warning cases under
`fixtures/warnings/0.2.0/`. A version a later one replaces keeps its
fixtures in the git history at its tag and in its released packages, as
0.1.0, which 0.2.0 replaces, does.

Every generated fixture is a TimeToShare manifest of the one shape
`{timetoshare, timelines, …}`, and every manifest is an alignment bundle.
In every manifest file each ID and each reference to an ID is written `#`
followed by the ID, as the [main README](../README.md#written-in-a-file)
states; the descriptions below name IDs bare, as the libraries hold them.
The directories sort the manifests by content only:

- directly under `fixtures/0.2.0/`, manifests of one root timeline and no
  group;
- under `groups/`, manifests holding one group;
- under `bundles/`, manifests of several groups, several ungrouped roots,
  or both;
- under `statements/`, manifests whose elements carry statements and
  provenance ([Statement fixtures](#statement-fixtures)).

Version 0.2.0 has 51 manifests directly under `fixtures/0.2.0/`, 14 under
`groups/`, 16 under `bundles/` and 4 under `statements/`, 85 in all, each
with its minimal twin, so 170 files. Beside them lie the expected RDF of
the 4 statement fixtures under `fixtures/rdf/0.2.0/`, the table fixture
under `fixtures/tables/0.2.0/` ([The table fixture](#the-table-fixture)),
175 rejection cases, 16 warning cases and one table of acceptances under
`fixtures/acceptances/0.2.0/` ([Acceptance cases](#acceptance-cases)).

Every accepted fixture is written in the complete form, every key with a
default written with it, and has a **minimal twin** beside it,
`<name>.minimal.yaml`, the same manifest in the minimal form, as
timetoalign's `to_dict()` writes it by default. The two obey one law:
`minimal(fixture)` equals the twin, `complete(twin)` equals the fixture,
and the library reads both to equal objects. The manifests are emitted by
timetoalign through the catalogue and pipeline in `scripts/fixtures/`, with
`scripts/emit_fixtures.py` as its CLI; that pipeline is their only writer.
Regenerate them after a serialization change and review the diff. The CLI
refuses to replace the fixtures of a version whose tag
`v<version>` exists, so a released version's fixtures stay as released.

The rejection cases under `fixtures/rejections/<version>/` and the warning
cases under `fixtures/warnings/<version>/` are hand-authored. The emission
script does not touch them.

## Formats

Every manifest fixture, its twin, every rejection case and every warning
case is written in canonical YAML (`.yaml`) by `dumps` of either package,
as the [main README](../README.md#serializations) specifies it, and read
with `loads`. A rejection or warning case about JSON text itself would be
written in JSON (`.json`); none is at present. The drawings' `inputs.json`
files are JSON, read by the drawing writers alone: TiLiE's drawing input, no
manifest file, so the addresses of its layers and the keys of its `places`
hold bare IDs, without the `#` a manifest file writes.

`fixtures/serializations/` holds the hand-derived cases of the three
serializations (canonical YAML, pretty JSON and RFC 8785 JSON): values in
each serialization, readings with their expected canonical YAML, texts every
reader refuses and values a writer refuses. They are derived by hand from
the main README, never written with `dumps`, which they test; their own
[README](serializations/README.md) lists them and states how a package test
uses them.

`fixtures/file_forms/` holds the hand-written cases of a manifest file's
form ([main README](../README.md#forms-and-defaults-for-applications)):
each text `<name>.<ext>` beside the `<name>.expected.<ext>` that both
packages write back in the file form they infer for it. `neither.yaml`
states some defaults and leaves out others, so it is neither minimal nor
complete and comes back complete; `one_line.json` comes back in the pretty
JSON layout; `crlf.yaml`, canonical YAML with carriage returns, comes back
with line feeds alone. `jcs_minimal.json` is RFC 8785 JSON on a seconds
axis, its integral floats written as integers; it is minimal and comes
back as its own bytes. `jcs_float_default.json` is the same with a
LinearMap's default `offset` stated, so it is not minimal and comes back
complete in RFC 8785 JSON. The package test READMEs state the form each
text is read as.

The [drawing specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/drawing.md)
pins how a manifest is drawn. A drawing is derived; these directories contain no drawing schema.

## Provenance

Each generated manifest records the timetoalign revision that produced it
in its free `meta` object, under `generator`:

```text
timetoalign <installed version> (<commit>)
```

To regenerate the files, run the script with an interpreter containing
the represented timetoalign revision:

```bash
python scripts/emit_fixtures.py --timetoalign-commit "$(git -C <timetoalign-checkout> rev-parse --short HEAD)"
```

The package `scripts/fixtures/` holds the corpus: the builders in
`timelines.py`, `groups.py` and `bundles.py` (each builder's docstring
describes its case), the `graphical` objects and the band-order manifests in
`graphical.py`, the ordered catalogue in `plan.py`, and the laws in
`verify.py`. A new case is appended to the catalogue within its directory.
The CLI writes each manifest and its twin in canonical YAML with
`timetoshare.dumps` (object keys sorted by code point, arrays in canonical
order), reads both back with `timetoshare.loads`,
validates them, checks that neither draws a warning, checks the law
above, and fails unless the manifest is
stable through the library: read by the class that holds its content
(`Timeline.from_dict` for one root and no group, `TimelineGroup.from_dict`
for one group, `AlignmentBundle.from_dict` otherwise) and written back with
`to_dict(minimal=False)` byte for byte, its arrays already in canonical order. A group's
display order in `graphical.order` is the library's own member order. The
`graphical` object the script composes for a manifest, its styles,
rules and band orders, is read back by the library, which keeps it as
written, and takes part in the round trip too: the library must write the
composed manifest back unchanged. Every fixture but the corpus fixtures
and `timestamps` also names the origin and length of each root it draws,
every group member and every root that is neither a member nor holds one,
as an editor marks a new root: the named timestamp `origin` at 0 and, where
the length is known, `length` at the root's length, each with the `display`
`["wedge", "coordinate"]` and the smallest `timestamp_N` the manifest
leaves free, minted by timeline ID and then coordinate
(`origin_and_length` in `graphical.py`). Every timeline, MeasureMap, conversion
map, region and flow-control element carries an ID; IDs the script does not give are
minted by timetoalign and depend on the construction order within the
builder, which is part of the fixture contract. Every manifest carries the
inline `@context` of the
[description specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/description.md),
written last by `with_context`: the format's terms and the prefixes its
statements use, their namespaces taken from the catalogue
(`catalogue/catalogue.yaml`), so a manifest without statements holds the
terms alone.

A catalogue case writes `<name>.yaml` in its directory. Several cases of
one name, such as the four of `conversion_maps`, write
`<name>__<slug>.yaml` each, where `<slug>` is the built object's ID with
every character outside `[A-Za-z0-9_-]` replaced by `_`. The script refuses
two IDs that would produce the same file name.

## Coverage of single timelines

The six axis fixtures cover every combination of continuous or discrete with
logical, physical, or graphical:

| File | Construction | Coverage |
| --- | --- | --- |
| `continuous_logical.yaml` | 12 quarters with children at `1/3` and `2` | fraction coordinates |
| `discrete_logical.yaml` | 480 ticks with two children | integer logical coordinates |
| `continuous_physical.yaml` | 12.5 seconds with children at 0.5 and 6.0 | float physical coordinates |
| `discrete_physical.yaml` | 44100 samples with two children | integer physical coordinates |
| `continuous_graphical.yaml` | 600.0 points with two children | float graphical coordinates |
| `discrete_graphical.yaml` | 1920 pixels with two children | integer graphical coordinates |

The structural fixtures add focused examples:

| File | Coverage |
| --- | --- |
| `with_region.yaml` | a named region |
| `nested.yaml` | three levels of timelines |
| `flow_control.yaml` | the flow marker `fine`, a repeat end taken twice to a named repeat start, and a dal segno to a named segno |
| `conversion_maps__*.yaml` | the conversion maps of one timeline per unit: `maps_quarters` every map type, a MeasureMap read through its `MeasureRecordMap` and the three other measure views, a `CombinationMap` holding a measure view, and `TableMap`s of both kinds and the three extrapolations; `maps_ticks`, `maps_samples` and `maps_seconds` a `LinearMap` each; `maps_whole_notes` a MeasureMap read through a `ChainMap` from whole notes |
| `bare.yaml` | one named timeline |
| `css_pixels.yaml` | 800.0 CSS pixels with children at 16.0 and 400.0: a continuous graphical axis in `css_pixels`, the unit of an SVG's outermost viewport |
| `contiguous.yaml` | children that touch and overlap |
| `map.yaml` | conversion maps on a root and a child |
| `styled__score.yaml`, `styled__performance.yaml` | `graphical.rules` selecting elements by type, address, class, domain, modality, and `within`, with a colour of its own for every drawn element and label of the score; the score's band order in `graphical.order` lays its markers band against its line above it and its conversion maps band against its line below it |
| `locked_root.yaml` | a root of 16 quarters locked at construction, with a child `coda` of 4 quarters at 12 |
| `segment_line.yaml` | a nested segment line of quarters: `form` (32) of the segments `a` (8), `b` (12) and `c` (12), each a segment line itself, `b` of `b1` and `b2` (6 each) |
| `segment_pages.yaml` | an unlocked segment line `pages` of four pages of 1754 pixels |
| `segment_pages_locked.yaml` | the same segment line, locked once built |
| `segment_pages_accolades.yaml` | an unlocked segment line of four pages, each a segment line of four accolades of 400, 450, 452 and 452 pixels |
| `segment_children.yaml` | an unlocked root of 32 quarters whose three children are segment lines, two of them overlapping |
| `timestamps.yaml` | named timestamps: a root `clt_1` of 8 quarters with the child `clt_2` (4 at 2), the timestamps `Downbeat` at 3/2 and `Climax` at 6 on the root and `Entry` at 1 on the child; `Downbeat` draws the default `display` (wedge, name, cross-section line), `Climax` `["wedge", "name"]`, and `Entry` all five, its name, ID and coordinate stacked |
| `timestamp_wedge_rotation.yaml` | turned wedges: a root `melody` ("Melody", 16 quarters) with the child `phrase` ("Phrase", 12 at 1), whose band order lays its markers band against its line above it; each named timestamp is named after its wedge's `rotation`. On the root, at quarters 2, 4, 6, 8, 10 and 12, rules naming each wedge's address turn it -135, -45, 0, 45, 135 and 180 (0 written); on the child, at its quarters 2 and 6, addressed rules turn the wedges -45 and 45, mirrored above the line, and at its quarter 10 only the rule `{"element": "wedge", "within": "phrase"}`, which the addressed rules outrank, turns it 90; the root's `origin` and `length` keep the unturned wedge |

The corpus fixtures exercise public timetoalign loaders; the synthetic
fixtures are emitted first:

| File or prefix | Loader input |
| --- | --- |
| `corpus_audio_audio.yaml` | an audio file, its timeline in samples with a map to seconds |
| `corpus_midi_score_midi.yaml` | a score MIDI file |
| `corpus_score_ms3.yaml` | an ms3 score with MeasureMap and flow-control data |
| `corpus_supra_iiif.yaml` | an IIIF manifest |
| `corpus_parangonar_parangonada__score_dlt_1.yaml` | the discrete score timeline of a Parangonada alignment |

Every generated manifest is in the complete form, as timetoalign's
`to_dict(minimal=False)` writes it: `name` is `null` when absent, every
timeline states `number_type`, `locked` and `is_segment_line`, empty flow
control is `[]`, and a manifest without MeasureMaps writes `measure_maps`
as `[]`. Its minimal twin leaves all of these out. The children of these
fixtures are locked, as timetoalign embeds a child by default, except the
segments: a segment is never locked, its segment line's lock governs it, so
its `locked` is `false` and is left out of the minimal form. A segment line
that is a child, a segment or a group member is locked by default, and
its `locked: true` stays in the minimal form, since the table's default is
`false`. A manifest may equally hold an unlocked child that is
not a segment line, whose `locked` is `false` and is left out of the
minimal form.

Two more manifests cover the manifest's own keys:

| File | Coverage |
| --- | --- |
| `negative_offset.yaml` | a root carrying a negative `offset`, its origin on its unit's absolute axis |
| `named_without_id.yaml` | a manifest with a `name` and no `id` |

No fixture holds a child with a negative `offset`: the schema and the
validators accept one, but timetoalign, which emits the fixtures, does not
support it yet, and no rejection case refuses one.

Six manifests draw timelines of unknown length (`length: null`), one case
each:

| File | Coverage |
| --- | --- |
| `unknown_length.yaml` | a root of unknown length with content |
| `unknown_length_empty.yaml` | a root of unknown length without content |
| `unknown_length_locked.yaml` | a locked root of unknown length |
| `unknown_length_child.yaml` | a child of unknown length in a parent of known length |
| `groups/group_unknown_length.yaml` | a group with a member of unknown length |
| `unknown_length_segments.yaml` | a segment line whose last segment has an unknown length |

Seven manifests cover band orders and the bands of children (drawing
specification, section 6.4):

| File | Coverage |
| --- | --- |
| `map_child_band_order.yaml` | the timelines of `map`, with a band order for the child `phrase` alone that lays its conversion maps against its line below it |
| `map_root_band_order.yaml` | the timelines of `map`, with such a band order for the root `melody` and none for `phrase`, which follows the band order of `melody` |
| `map_band_order_subset.yaml` | the timelines of `map`, with a band order for the root `melody` listing only `markers` above `line`; the facets it leaves out keep their side of the default order, so `melody` draws `children`, `conversion_maps`, `markers`, `line`, `regions`, `flow_control`, and `phrase`, without an entry, follows that completed order |
| `styled_score_flow_inner.yaml` | `styled__score` with a band order whose flow control band lies nearer the line than its regions band |
| `joint_rows.yaml` | a root `piece` of 16 quarters whose children `b` and `d` each hold a child holding one more, so that each depth's two lines share a row and their children bands are laid out together, at two depths; `b` carries one map, `d1` and `d11` two each |
| `child_flow_control.yaml` | a root `piece` of 16 quarters whose child `verse` (8 at 4) holds a da capo al fine, the flow marker "Fine" at 4 and the jump origin "D.C. al Fine" at 8 back to 0, while the root holds no flow control |
| `child_jumps.yaml` | a root `piece` of 16 quarters whose child `verse` (8 at 4) holds the jump target `segno` at 2, the jump origin "Repeat" at 4, a repeat end taken twice back to the child's start, and the jump origin "D.S." at 8, a dal segno to `segno`, while the root holds no flow control |

Three manifests cover the slots of conversion maps bands (drawing
specification, section 6.4, Conversion maps), and one the label of a float
coordinate (section 5.2). Every map of the three is a `LinearMap` named
"Tempo" (to seconds, half a second per quarter) or "Ticks" (to ticks, 480
per quarter):

| File | Coverage |
| --- | --- |
| `map_row_siblings.yaml` | a root `piece` of 8 quarters whose children `ante` (4 at 0) and `cons` (4 at 4) touch and so share a row; `ante` carries the maps `a_ticks` ("Ticks") and `b_tempo` ("Tempo"), `cons` the maps `a_tempo` ("Tempo") and `b_ticks` ("Ticks"), so both Tempo maps lie in slot 1 and both Ticks maps in slot 2, although `ante`'s Ticks map comes first in its canonical order |
| `map_row_subslots.yaml` | an unlocked segment line `form` of 32 quarters of the unnamed segments `a` (8), `b` (12) and `c` (12), whose own map `ticks_form` and the maps `ticks_b` of `b` and `ticks_c` of `c` share the key "Ticks": `ticks_form` takes sub-slot 1, and `ticks_b` and `ticks_c`, which touch, share sub-slot 2 |
| `map_row_moved.yaml` | a root `piece` of 8 quarters whose children `ante` (4 at 0, the maps `tempo_ante` and `ticks_ante`) and `cons` (4 at 3, the map `ticks_cons`) overlap and so lie in two rows, each with slots of its own: `ticks_cons` takes slot 1 of its row, where in one row with `ante` it would take slot 2 |
| `label_float_rounding.yaml` | a root `take` of 312.48979591836735 seconds and its two named timestamps, `origin` at 0.0 and `length` at its length, each with the `display` `["wedge", "coordinate"]`; the coordinate label of `length` reads `5′12.49″`, its coordinate rounded to three decimals and split into minutes and seconds |

## Coverage of groups and bundles

Every builder writes its files; the constructed files are built first. The
conversion maps of the constructed groups and bundles are of five kinds,
each a `LinearMap`, each ID minted and no name given: a map to ticks (480
per quarter), a tempo map to seconds (half a second per quarter), a map to
samples (44100 per second), a map to seconds (1/44100 of a second per
sample) and a map to points (3/4 of a point per pixel). A repeat is a jump
origin labelled "Repeat" back to an earlier coordinate (`repeat_end`,
`repeat_count` 1).

| Builder | Construction |
| --- | --- |
| `group_number_types` | a group of three timelines whose axes have different number types (quarters as fractions, seconds as floats, pixels as integers), in a display order that differs from their ID order |
| `group_child_member` | a group of the second half of a score, a child of the score placed at its exact offset, with a whole recording |
| `group_styled` | the group of `group_number_types` with conversion maps, a region, a jump origin and styling: the score has a map to ticks, the region "Theme" from 0 to 8 and a repeat from 8 back to 0, the performance a map to samples and the page a map to points; its `styles` and `rules` give every group frame the style `frame-highlight` (a violet stroke), fill the group's title `group_1/name` violet, and give every card inside a frame a light violet `shadow` and a corner radius `rx` of 2 |
| `group_parent_right` | a child `first-half` (8 quarters at 0) of a piece of 16 quarters, with a whole recording; the piece runs on to the right of the member |
| `group_parent_both` | as above with the child `middle` (8 quarters at 4); the piece runs on to both sides |
| `group_parent_exact` | as above with the child `whole` (16 quarters at 0); the piece coincides with the member |
| `group_parents_mixed` | three child members of different parents (an exposition of 32 quarters at 16 in a locked sonata of 48; a take of 25.5 seconds at 30.0 in a session of 90.0 seconds, with a map to samples; a system of 600 pixels at 0 in a page of 1754) and the root `audio` of 1323000 samples, with a map to seconds |
| `group_grandchild` | a grandchild `theme` (8 quarters at 8 in a movement of 16 quarters at 16 in a score of 64) with a recording of 12.0 seconds |
| `group_groupstamp` | the group "Performance" of the score `score` ("Score", 8 quarters, with a map to ticks) and the performance `performance` ("Performance", 4.0 seconds, with a map to samples), so that each member has a conversion maps band; the timestamp `timestamp_1` "Bar 2" at quarter 4 of the score is a groupstamp, its line across both cards of the frame |
| `group_groupstamp_child_member` | the group "Performance" of the score `score` ("Score", 8 quarters), holding the child `second-half` ("Second half", 4 quarters at 4), and the performance `performance` ("Performance", 4.0 seconds), no timeline carrying a map; the timestamp `timestamp_1` "Bar 4" at quarter 2 of the child is a groupstamp, since the child lies in the group through its parent |
| `group_child_member_stamps` | the group of `group_parent_both` (the child member `middle`, 8 quarters at 4 in the piece `piece` of 16, and the root member `recording`, 10.0 seconds), whose child member carries both kinds of line: the timestamp `timestamp_1` "Bar 2" at quarter 2 of `middle`, drawing its cross-section line alone (`display` `["cross_section"]`), and the match timestamps `timestamp_2`, without a name, at quarter 4 of `middle` and `timestamp_3` at second 5.0 of `recording`, which the MatchStamp `matchstamp_1` ("Middle, bar 3") joins by the anchor `anchor_1`, drawing the name, from `claim_1`; no timestamp is a groupstamp. The child's lines reach up to the ancestor line of `piece` in its card, and the anchor attaches there |
| `bundle_mixed` | the bundle "Mixed" of two groups, a score with its performance and a page with an excerpt (a child of a recording); `annotations` is ungrouped, and the recording, which no group names, contains the member `excerpt` and is drawn only as its ancestor line. The score has a map to ticks, then a tempo map to seconds, and a repeat from 8 back to 0; the performance a map to samples; the page a map to points; the excerpt a map to seconds; the recording a map to seconds, kept in the manifest and not drawn; `annotations` the regions "Verse" from 0 to 4 and "Chorus" from 4 to 12, and no map |
| `bundle_shared_parent` | the bundle "Sonata" of two groups whose members are two children of one score (an exposition at 0 and a recapitulation at 20, 12 quarters each), each with a take; a page is ungrouped, and the score, which no group names, contains both members and is drawn only as an ancestor line of each. Both children are segment lines: the exposition, with a map to ticks, of the segments "First theme" and "Second theme" of 6 quarters, the second with a tempo map to seconds; the recapitulation, with no map, of the segment lines "First theme" and "Second theme" of 6 quarters, each of the segments "Phrase 1" and "Phrase 2" of 3 quarters, and only its "Second theme" has a map to ticks. The take `take_1` is a segment line, with a map to samples, of "First theme" (14.0 seconds) and "Second theme" (16.0 seconds); the take `take_2` and the page carry no map. The score has a map to ticks, the region "Development" from 12 to 20 and a repeat from 12 back to 0, kept in the manifest and not drawn. A segment's ID begins with its segment line's (`exposition_first`, `recapitulation_second_1`) |
| `bundle_ungrouped` | the bundle "Sketches" of three ungrouped roots and no group: a score of 16 quarters with a map to ticks and a da capo al fine, the flow marker "Fine" at 8 (`fine`) and the jump origin "D.C. al Fine" at 16 back to 0 (`da_capo_al_fine`); a recording with a map to seconds; and an unlocked segment line, with a map to points, of three pages of 1754 pixels that carry none |
| `bundle_shared_member` | the bundle "Shared" of two groups that share a member: the score `t` ("Score", 8 quarters) is a member of the group `g1` ("Performance") beside the performance `u` (4.0 seconds) and of the group `g2` ("Page") beside the page `v` (800 pixels); no timeline carries a map, a region or flow control |
| `bundle_free_ids` | the bundle "Free IDs" of the group `group_1` ("Piece") of two roots whose IDs are free strings: the score `https://example.org/piece/score` ("Score", 8 quarters) with the region "Exposition" `https://example.org/piece/score#exposition` from 0 to 4, and the take `perf/take 2` ("Take 2", 4.0 seconds) with the region "Intro" `take 2/intro` from 0.0 to 1.0; one rule selects the take's region by its address `{"id": "#take 2/intro"}` and strokes it teal |
| `bundle_resources` | the bundle "Resources" of the score `score` (8 quarters) and the recording `take_1` (352800 samples), ungrouped, with two resources: `resource_1`, the MatchClaim table `match_claims.parquet` holding data for both timelines, with its media type `application/vnd.apache.parquet`, and `resource_2`, the Projections table `projections.parquet` (an experimental type) holding data for `take_1`, with nothing optional; neither file lies beside the fixture, so neither states a size or a digest (the table fixture's manifest states both of its own tables')
| `bundle_matchstamps` | the bundle "MatchStamps" of the score `score` ("Score", 8 quarters) and the takes `take_1` ("Take 1", 352800 samples) and `take_2` ("Take 2", 396900 samples), ungrouped; the match timestamp `timestamp_1` at quarter 4 of the score, without a name, shared by two MatchStamps: `matchstamp_1` ("Bar 2, downbeat (take 1)") joins it to sample 88200 of `take_1` by the anchor `anchor_1`, which also draws the name, from the MatchClaims `claim_1` and `claim_2`; `matchstamp_2` ("Bar 2, downbeat (take 2)") to sample 99225 of `take_2` (the match timestamp `timestamp_3`, named "Take 2, bar 2" and drawing its name) by `anchor_2`, from `claim_3` |
| `bundle_matchstamp_cards` | the bundle "MatchStamp cards" of two groups that share a member, as `bundle_shared_member`: the score `score` ("Score", 8 quarters), holding the child `second-half` ("Second half", 4 quarters at 4), is a member of the group `group_1` ("Performance") beside the performance `performance` (4.0 seconds) and of the group `group_2` ("Page") beside the page `page` (800 pixels); three match timestamps without a name, `timestamp_1` at quarter 4 of the score, `timestamp_2` at second 1.0 of the performance and `timestamp_3` at quarter 2 of the child; `matchstamp_1` ("Bar 2, performed") joins the performance to the score, drawn in two cards, by `anchor_1`, from `claim_1`; `matchstamp_2` ("Second half, bar 1") the score to its child, whose lines lie in one card, by `anchor_2`, from `claim_2`; both anchors draw the name |
| `bundle_matchstamp_groupstamp` | the bundle of `bundle_matchstamp_cards` whose match timestamp `timestamp_1` at quarter 4 of the score, a member of both groups, is a groupstamp, its line across the frame of `group_1` and that of `group_2` |
| `bundle_groupstamp_shared_member` | the bundle of `bundle_shared_member` with the timestamp `timestamp_1` "Bar 2" at quarter 4 of the shared member `t`, a groupstamp, its line across the frame of `g1` and that of `g2`; no member has a band |
| `group_measure_map` | the group "Edition" of a score of 16 quarters and its MIDI rendering of 7680 ticks, both reading one entry of `measure_maps`, four bars of 4/4: the score through its `MeasureRecordMap`, the rendering through a `ChainMap` of the `LinearMap` `ppq` to quarters (480 ticks per quarter) and its `MeasureRecordMap` |

The corpus builders, prefixed `corpus_`, write the groups and bundles that
public timetoalign loaders create from corpus specimens: the group of a
TiLiA export, and the bundles of a Parangonada alignment, a Matchfile, an
MPM performance, an IEEE 1599 document, a Listen Here! export and a TiLiA
export. No bundle fixture carries MatchClaims.

Conversion maps, regions and flow control are spread over the constructed
groups and bundles and the single-timeline fixtures `styled__score`,
`unknown_length_child`, `unknown_length_segments`, `child_flow_control`,
`child_jumps`, `map_row_siblings`, `map_row_subslots` and `map_row_moved`
so that each case below occurs in one of them at least.
`group_number_types`, `group_child_member`, the three `group_parent_*`,
`group_grandchild` and `group_groupstamp_child_member` hold none of them, and `group_unknown_length` holds only
a region. The segment lines of the single-timeline fixtures but
`map_row_subslots` (`segment_line`, `segment_pages`, `segment_pages_locked`,
`segment_pages_accolades`, `segment_children` and
`unknown_length_segments`) and their segments carry no conversion map;
among the constructed fixtures, segment lines with maps occur only in
`bundle_shared_parent` and `bundle_ungrouped`, and a segment that is not a
segment line carries a map only in `bundle_shared_parent`.

| Case | Timeline |
| --- | --- |
| a logical segment line with a map, the child of a timeline that is not a segment line, and a group member | `exposition` of `bundle_shared_parent` |
| a segment line whose segments are segment lines, the child of a timeline that is not a segment line | `recapitulation` of `bundle_shared_parent` |
| a segment line that is a segment of a segment line, with a map, beside one without | `recapitulation_second` and `recapitulation_first` of `bundle_shared_parent` |
| a map on a segment that is not a segment line, joining its segment line's conversion maps band with the key of the line's own map, whose timeline overlaps it, so in the next sub-slot | `exposition_second` of `bundle_shared_parent` |
| a physical segment line with a map, a root and a group member | `take_1` of `bundle_shared_parent` |
| a graphical segment line with a map, an unlocked ungrouped root | `pages` of `bundle_ungrouped` |
| two maps of one key on one timeline, in two sub-slots, and flow control on a group member | `score` of `bundle_mixed` |
| a map on a root member and on a child member of a group | `performance` and `excerpt` of `bundle_mixed`; `audio` and `take` of `group_parents_mixed` |
| a map on a pixel axis | `page` of `bundle_mixed` and of `group_styled`; `pages` of `bundle_ungrouped` |
| regions on an ungrouped root | `annotations` of `bundle_mixed` |
| a map, children, a region and flow control on one timeline | `score` of `styled__score` |
| a map, a region and flow control on a root that contains group members and is drawn only as an ancestor line of each, kept in the manifest and not drawn | `score` of `bundle_shared_parent` |
| a flow marker and a jump origin together | `score` of `bundle_ungrouped` |
| a map, a region and flow control inside a styled frame | `score` of `group_styled` |
| a region on a child | `movement` of `unknown_length_child` |
| regions on segments without a line of their own, joining their segment line's regions band | `a` and `c` of `unknown_length_segments` |
| a flow marker and a jump origin on a child, its root holding none | `verse` of `child_flow_control` |
| a jump target, a repeat end with a repeat count and a targeted dal segno on a child, its root holding none | `verse` of `child_jumps` |
| a MeasureMap shared by two timelines, one reading it through a `ChainMap` from ticks | `score` and `midi` of `group_measure_map` |
| maps of two keys on two lines of one row, sharing the row's slots | `ante` and `cons` of `map_row_siblings` |
| maps of one key on a segment line and two of its segments that are not segment lines, in two sub-slots | `form`, `b` and `c` of `map_row_subslots` |
| maps on two siblings in two rows, each row with slots of its own | `ante` and `cons` of `map_row_moved` |

The conversion maps bands of the lines of one row share their slots, a
map's key being its `name` and `type`, or its `type` alone when it has no
name (drawing specification, section 6.4, Conversion maps). Only
`map_row_siblings` holds two lines with maps in one row; in every other
drawn manifest a row's slots are those of one line and its segments. The keys still order the maps of one
line: the twelve unnamed maps of ten types of
`conversion_maps__maps_quarters` have ten keys, in an order other than that
of their IDs; the maps of `map`, `map_child_band_order`,
`map_root_band_order`, `styled__score`, `styled_score_flow_inner`,
`map_row_siblings`, `map_row_subslots` and `map_row_moved` carry names
(`Tempo`, `Ticks`); every other map outside the corpus fixtures is
unnamed, so maps of one type on one line share a key and, spanning one
timeline, take a sub-slot each, in canonical order.

The defaults hide the regions and flow control bands of every
timeline held by a band, every timeline of a member drawing but its root
(drawing specification, section 4). So a child's regions or flow control,
or a segment's, is drawn in a figure only where a rule of the manifest
or an application layer displays its band: the drawings
`unknown_length_child__regions-shown`,
`unknown_length_segments__regions-shown` and
`child_flow_control__flow-shown` add such a layer (Drawings, below).

## Statement fixtures

The four manifests under `statements/` exercise the statements and
provenance of the
[description specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/description.md).
Their builders in `statements.py` build the temporal structure through
timetoalign, read as a whole by `AlignmentBundle.from_dict`; the
statements and provenance of each subject are attached when the manifest
is composed, from `descriptions/<name>.yaml`, which holds `{prefixes?,
subjects}`: the prefixes a manifest declares beside the catalogue's, and
for each subject, named by its ID as written in the file (the manifest's
own ID naming the bundle), its `statements` and `provenance` as they are
written. A subject naming no element stops the run. The statement
fixtures are not drawn and name no origin or length timestamps.

| File | Structure | Statements |
| --- | --- | --- |
| `op106_work.yaml` | the bundle `op106` ("Beethoven, Piano Sonata No. 29, Op. 106") of five roots of quarters side by side, none nesting another, each a manifestation: the first edition `clt_1` ("Op. 106, first edition (Vienna: Artaria, 1819)", of unknown length) and the movements' encodings `clt_2` ("I. Allegro (sonata29-1.krn)", 1645), `clt_3` ("II. Scherzo. Assai vivace (sonata29-2.krn)", 510), `clt_4` ("III. Adagio sostenuto (sonata29-3.krn)", 561) and `clt_5` ("IV. Introduzione. Largo – Allegro risoluto (sonata29-4.krn)", 9911/8) | under the bundle's `schema:about` the sonata, a value node named by its MusicBrainz ID: "is a" in three vocabularies and Wikidata's, identity with Wikidata, the GND and VIAF, the composer in Wikidata's and the GND's terms, the opus number and the IMSLP page name as literals, and the four parts MusicBrainz lists with `schema:position`; on `clt_1` "is a" in two vocabularies, its work in MusicBrainz's and Wikidata's terms and its publication as a node; on each movement "is a" and its MusicBrainz work; the manifest's own prefix `mbw`; 8 entries, each of a stated pair; one of them with a person's belief `true` |
| `layerit_recording.yaml` | the bundle `layerit_clair_de_lune` of the MEI encoding `clt_6` (27 quarters), the video `cpt_1` (seconds, of unknown length) with the stretch `cpt_2` (33.353016 seconds at 0.0), and the audio file `dpt_1` (1470868 samples, with the map `cmap_1` of 44100 samples per second); the group `group_1` ("recording") aligns `cpt_2` with `dpt_1` | the bundle's `rdfs:seeAlso` and its `schema:about`, the work in Wikidata; the encoding's work in Wikidata's and MusicBrainz's terms, tied by `schema:sameAs`, and its encoding date as an `xsd:date`; "is a" a manifestation on the encoding, the video and the audio file; the video's performer in two vocabularies; a candidate whose value is the element `#cpt_1`; provenance on a value node; 10 entries: 7 of stated pairs, 3 candidates, one of them believed `false` by the editor; the editor's beliefs `true` in the pairs the editor stated |
| `djset_segment.yaml` | the bundle `moriero_halloween_xxl_2025` of the set's recording `cpt_1` (5277.0 seconds) and its segment `cpt_2` (91.0 seconds at 437.0) | under the bundle's `schema:about` the set, a value node that "is a" DJ mix; the recording "is a" music recording and audio object and names the set by "recording of" (`wdt:P2550`); the segment based on a recording in Wikidata's and MusicBrainz's terms, with its ISRC on the value node; a performer known by name alone, a candidate; an identity the editor believes `false`; a performer the editor believes `unlikely`; 6 entries: 3 of stated pairs, 3 candidates |
| `nielsen_record.yaml` | the bundle `cnw0133` of the sources `cgt_1` ("Score, print (Wilhelm Hansen, 1906)") and `cgt_2` ("Score, autograph, printer's manuscript"), millimeters of unknown length, neither nesting the other | a record taken over from an MEI header in MeLODy's and LRMoo's terms: the bundle's `rdfs:seeAlso`; under its `schema:about` the work, a value node with titles with languages, identifier nodes, a date node, its relations to CNW 7 and its realisation in the expression; the print and the autograph as manifestations, the print embodying the expression, a value node with the medium of performance; the autograph's copy proposed as an item; names awaiting reconciliation; 29 entries: 24 of stated pairs, 5 candidates, one of them believed `false` |

`fixtures/rdf/<version>/<name>.nq` holds the expected RDF of each statement
fixture: the canonical N-Quads (RDFC-1.0) of its JSON-LD reading with the
base `https://example.org/manifests/<name>.yaml`, line feeds only.
`scripts/emit_rdf.py` writes them with PyLD (run from `python/` as `uv run
python ../scripts/emit_rdf.py`, after the fixtures), with a document
loader that refuses every fetch; it rewrites a file only when its bytes
change, removes the file of a fixture that is gone, and refuses to replace
the files of a version whose tag `v<version>` exists. The RDF tests of both
packages, PyLD in Python and jsonld.js in TypeScript, read each statement
fixture and its twin, and check that their canonical N-Quads equal the
file byte for byte; that every other fixture reads to the empty graph;
that every IRI is expanded and absolute; that every predicate is a
property of a statement, `rdf:type`, `rdfs:label` or a term of the
format's context; that no candidate (an entry of a pair its subject does
not state) whose subject has an IRI and whose value is a thing or a plain
literal is asserted; and that
each provenance entry gives one reified statement.

## The table fixture

`fixtures/tables/<version>/` holds the fixture of the two table types,
outside `fixtures/<version>/` so that no reader of the manifest fixtures
takes it for one: `manifest.yaml`, the MatchClaim table
`match_claims.parquet`, the Projections table `projections.parquet` and
`expected.yaml`, the AlignmentAnchors and potential MatchStamps expected
of the MatchClaim table under seven belief filters, each a believer and
the states it keeps, in this order: no believer, every state but `false`;
for one actor every state but `false` (the default), then `true` alone;
for a second actor `true` alone; for the first actor `undecided` alone,
then `unlikely` with `false`; and the first actor written as the compact
IRI `orcid:0000-0002-1825-0097`, `true` alone, which keeps what the third
filter keeps. Every filter reads actors under the manifest's `@context`,
which declares the prefix `orcid`. The manifest holds three roots
(`clt_1`, quarters, with the child `clt_2`; `dpt_1`, samples; `cpt_1`,
seconds) and names both tables in its `resources`, each with its media
type, its size, its SHA-256 digest and the timelines its table holds data
for: `resource_1`, the MatchClaim table, names `clt_1`, `clt_2`, `dpt_1`
and `cpt_1`; `resource_2`, the Projections table, names `clt_2`, `dpt_1`
and `cpt_1`. The MatchClaim table holds 15 rows. The Projections table
holds 11 Projections and each number type of a cell: ints on `dpt_1`
(instants and one interval), a float instant and a float interval on
`cpt_1`, and a fraction interval (start 7/2, duration 1/2) on `clt_2`;
the float interval and the fraction interval are named by no MatchClaim.
Its rows lie sorted stably by `timeline_id` (`clt_2`, then `cpt_1`, then
`dpt_1`), each timeline's in the order the script lists them: the order in
which timetoalign writes a bundle's Projections table, so that the two
files are equal byte for byte. The script
`scripts/emit_tables.py` (run from `python/` as `uv run python
../scripts/emit_tables.py`; it needs pyarrow, a development dependency) is
its only writer: every row and every expected value is literal data in the
script, never computed by the derivation the tests check, and only the
sizes and digests are read from the bytes written. It rewrites a Parquet
file only when its table changes and refuses to replace the files of a
version whose tag `v<version>` exists. Python's
`timetoshare.tables.fixture_path(name)` gives the path of each file.

## Drawings

Each directory `fixtures/<version>/drawings/<name>/` pins one drawing of the
[drawing specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/drawing.md)
as it stands in that version, with exactly three files; the drawings of the
current version follow `docs/drawing.md` as it stands, and those of a
released version follow the specification tagged with it.

The drawings of 0.2.0 are every fixture in the complete form but the corpus
ones (`corpus_*`) and the statement fixtures, at the default placement, and
twenty-one variants. The
drawing of a manifest directly under `fixtures/0.2.0/` is named as the file
(`nested`); that of a manifest under `groups/` or `bundles/` as the
directory's singular and the file (`group__group_child_member`,
`bundle__bundle_mixed`). The variants draw `nested` at the lengths 200, 400
and 800 (`nested__length-<L>`), with the card spacings 0 and 8 of its one card
(`nested__card-spacing-<S>`), with both the length 800 and the card spacing
8 (`nested__length-800-card-spacing-8`), in a block 120 wider and 60 higher than its content (`nested__block`) and at
scale 2 (`nested__scale-2`); `bundle_mixed` with the places `{group_2: {x:
40, y: 200, width: 700}, annotations: {x: -30, length: 300}}`
(`bundle_mixed__places`) and with the places `{group_1: {scale: 1.25,
cards: {performance: {width: 650, height: 120}}}}` (`bundle_mixed__cards`), with
the frame spacing `{group_1: {spacing: 16}}`, the gap between the frame's
two cards (`bundle_mixed__frame-spacing-16`), and with the card spacing
`{group_1: {cards: {score: {spacing: 8}}}}` of a member card, which deepens the arc of
`score`'s jump origin (`bundle_mixed__member-card-spacing-8`);
`bundle_ungrouped` with the place `{score: {x: -60, y: -150, height: 120}}`
(`bundle_ungrouped__places`), with the place `{recording: {scale: 1.5}}`
(`bundle_ungrouped__scale`) and with the block's spacing 24 and the card
spacing `{score: {spacing: 8}}`, which deepens `score`'s flow control band
(`bundle_ungrouped__spacing`); and three manifests with an application
layer of one rule that sets `display` to `inline` on bands the
defaults hide: `unknown_length_child` on the band `{"id": "movement",
"facet": "regions"}` (`unknown_length_child__regions-shown`),
`unknown_length_segments` on every regions band, `{"element": "band",
"facet": "regions"}` (`unknown_length_segments__regions-shown`), and
`child_flow_control` on the band `{"id": "verse", "facet":
"flow_control"}` (`child_flow_control__flow-shown`); and three groups with
an application layer of one rule that shows the ancestor cards the
defaults hide, `{"element": "ancestor_card"}` set to `display` `inline`:
`group_parent_both`, `group_parent_right` and `group_parents_mixed`
(`group__<name>__ancestor-cards`): 90 drawings in all.
`bundle__bundle_shared_member` draws the timeline `t`, a member of both
`g1` and `g2`, once in each frame, in two cards that both carry the
address `{"id": "t", "part": ["card"]}`, every element of its two drawings
carrying the same address in both. No variant sets a band order: band orders are the manifests' own,
in their `graphical.order` (`styled__score`, `styled_score_flow_inner`,
`map_child_band_order`, `map_root_band_order`, `map_band_order_subset`, `timestamp_wedge_rotation`). Each directory holds:

- `inputs.json`, everything a drawing needs besides the manifest itself and
  the two fonts, written with `dumps` in pretty JSON:
  - `manifest`: the path of the manifest's canonical YAML file relative to
    the same version's directory (`nested.yaml`,
    `groups/group_child_member.yaml`);
  - `placement`: `length`, `spacing`, `width`, `height` and `places`, all
    five always written, defaults included (400, 8, `null`, `null`, `{}`);
    `spacing` is the block's, the gap between its items at their default
    `y`, and a place's `spacing` the gap between that frame's cards or that
    card's rows and bands (drawing specification, section 8.6);
  - `scale`: the scale `z` at which the writers place the drawing;
  - `layers`: the rule lists an application supplies, lowest
    precedence first. The defaults and the manifest's own `graphical` object
    are not repeated here: the layers of the drawing are the defaults, then
    these (an empty list when there are none), then the manifest's
    `graphical`, which no layer outranks.
- `figure.svg`: the SVG of the drawing alone, placed at `(0, 0)` with the
  scale `z`;
- `figure.tex`: the TikZ of the same placement, a standalone document that
  finds both font files in the directory `.`.

Two implementations that follow the specification write both figures byte
for byte. Thirty-six `figure.svg` files are derived by hand from the
specification alone and are never regenerated, among them every drawing of
a timeline of unknown length, the three variants of `bundle_ungrouped`, the
three variants that display a band the defaults hide, the band orders of
`styled_score_flow_inner`, `map_child_band_order`, `map_root_band_order`
and `map_band_order_subset`, `joint_rows`, the three drawings of conversion map
slots (`map_row_siblings`, `map_row_subslots`, `map_row_moved`),
`label_float_rounding`, the alignment anchors of
`bundle__bundle_matchstamp_cards` and the cross-section lines and the
anchor on a child member of `group__group_child_member_stamps`;
`drawings/README.md` lists them with their arithmetic. Every other figure, and every `inputs.json`, is
emitted by TimeLineEditor's writers with `pnpm emit-drawings --into
<TimeToShare checkout>` (run in its `app/packages/writers/`), which
compares the hand-derived SVGs with its own output instead of writing them.
The script refuses to replace the drawings of a version whose tag
`v<version>` exists.

## Rejection coverage

Each rejection case breaks one rule of an accepted manifest and records the
`path` and the `code` both validators must report, and a `reason`. A rule
inside a timeline is located under the root that holds it, `/timelines/0/…`.
Tests in both packages load the same files and compare the error's path and
code with the case's. The cases cover every code:

| Code | Rule | Cases |
| --- | --- | --- |
| `not_a_manifest` | the value is an object holding `timetoshare` | `root_missing_marker` |
| `finite_number` | every number is finite | `infinite_length`, `nan_offset` |
| `schema` | the schema document | 89 cases named after the member they break: units and number types (a number type the unit does not admit: `timeline_ticks_float`, `timeline_seconds_int`, `timeline_quarters_int`), lengths and offsets (a Fraction member with a fractional part, `length_fraction_member_not_integral`, among them), IDs (an empty ID, `id_empty`, and IDs holding a control character, a root ID followed by a newline, `id_control_character_trailing_newline`, among them; an ID written without its `#`, `id_without_hash` and the one-character `id_without_hash_short`, and a reference written without its `#`, `reference_without_hash`), conversion maps, flow control, MeasureMaps, groups, `graphical` selectors, declarations and `order`, 23 cases of statements: a context term altered or missing, a prefix that is no namespace or bears a reserved name (`context_*`); a `type` or a key that is a bare word, a key that is a JSON-LD keyword, an empty container, an empty or repeating value list, a value that is a fractional float or `null`, a `null` in an ordered list, a value object with both a language and a datatype, an empty node and a node whose `id` is a blank-node label (`type_bare_word`, `statement_*`, `statements_empty`, `ordered_values_null`, `value_object_language_and_type`, `value_node_*`); an empty `provenance`, an unknown method or match, a property that is a bare word and a date not written `YYYY-MM-DD` (`provenance_*`), and a belief that is none of the strings `true`, `false` and `unlikely`, a word or the JSON boolean `true` (`belief_value_unknown`, `belief_value_boolean`); and 3 cases of MatchStamps and resources: a word of an anchor's `display` other than `line` and `name` (`alignment_anchor_display_unknown`), a MatchClaim ID listed twice (`matchstamp_claims_repeated`) and a digest whose hash function the PREMIS vocabulary does not name (`resource_integrity_algorithm_unknown`) |
| `representation` | an own-axis value is accepted when its axis's number type reads it exactly, in any terms of a fraction, and is written in the form that number type takes (a bare number on an `int` or a `float` axis, a pair of integers on a `fraction` axis; in the tables the cell members that form fills); another form, or a value the number type cannot hold exactly, is refused; a statement value is never a float | `length_int_on_fraction_axis`, `length_fraction_on_int_axis`, `length_float_on_int_axis`, `float_axis_int_not_exact`, `region_start_float_on_fraction_axis`, `child_offset_fraction_on_float_axis`, `statement_value_integral_float` |
| `duplicate_id` | every ID unique across the manifest, that of a map another map holds of a named timestamp, a MatchStamp, an alignment anchor and a resource included | `id_duplicate_across_kinds`, `nested_map_id_duplicate`, `timelines_id_duplicate_across_roots`, `timelines_child_id_duplicate_across_roots`, `region_id_duplicate_across_roots`, `region_id_is_timeline_id`, `group_id_duplicate`, `group_id_is_timeline_id`, `group_id_is_descendant_id`, `measure_map_id_is_timeline_id`, `timestamp_id_is_timeline_id`, `alignment_anchor_id_repeated` |
| `dangling_target` | a jump origin's target names a jump target of its own timeline, a measure view's `measure_map` an entry of `measure_maps`, and a `#` reference of the statements an element of the manifest | `jump_target_flow_marker`, `timelines_root_jump_target_dangling`, `measure_view_dangling`, `element_value_dangling` |
| `conversion_map` | a map attached to a timeline converts from the timeline's unit, and a map a `PiecewiseMap` or `CombinationMap` holds, or a `ChainMap`'s first map, from its holder's source unit, wherever both are stated; a `TableMap`'s x and y values agree in length and its x values increase strictly; a `PiecewiseMap` has one map fewer than breaks, and its breaks increase strictly | `map_source_unit_mismatch`, `table_map_lengths_differ`, `table_map_x_not_increasing`, `piecewise_map_maps_count`, `piecewise_map_breaks_not_increasing` |
| `child_unit` | a child has its parent's unit | `child_unit_differs` |
| `child_offset` | a child starts within its parent's known length | `child_offset_beyond_parent` |
| `child_end` | a child ends within its parent's known length | `child_end_beyond_parent` |
| `segment_line` | segments run contiguously from 0 to the line's length, with one `is_segment_line` value | `segment_line_not_from_zero`, `segment_line_gap`, `segment_line_gap_in_later_root`, `segment_line_short_of_length`, `segment_line_segment_flag` |
| `manifest_id` | the manifest's ID is no other ID of the manifest | `manifest_id_is_group_id`, `manifest_id_is_descendant_id`, `manifest_id_is_measure_map_id` |
| `group_member` | a member names a timeline of the manifest, and neither contains nor lies inside another member of its group | `member_dangling`, `members_contain_member`, `members_inside_member` |
| `order_key` | a key of `graphical.order` names a group or a timeline | `order_unknown_group` |
| `display_order` | a group's display order is a permutation of its members | `group_order_not_member`, `order_missing_member` |
| `band_order` | a band order lists `line` and any of the five facets, each once | `band_order_unknown_entry`, `band_order_missing_line`, `band_order_old_form` |
| `timestamp_timeline` | a named timestamp names a timeline of the manifest | `timestamp_timeline_unknown` |
| `timestamp_coordinate` | a named timestamp's coordinate lies from 0 to its timeline's own length, from 0 on where the length is unknown | `timestamp_coordinate_beyond_length`, `timestamp_coordinate_negative` |
| `groupstamp` | a groupstamp, a match timestamp included, lies in a group, its timeline or one of its ancestors being a member (an ancestor of a member lies in none through it) | `groupstamp_without_group`, `groupstamp_child_without_group`, `groupstamp_member_parent`, `groupstamp_match_without_group` |
| `context` | a manifest whose elements carry `statements` or `provenance` holds `@context` | `context_absent_with_statements`, `context_absent_with_provenance` |
| `reserved_key` | no element key is one JSON-LD would read | `reserved_key_term_on_timeline` (`label`), `reserved_key_iri_on_region`, `reserved_key_statements_on_group`, `reserved_key_prefix_on_manifest`, `reserved_key_context_on_timeline`, `reserved_key_children_on_region` |
| `iri` | every compact IRI names a declared prefix, and every element with statements has an ID that is an IRI fragment | `iri_prefix_undeclared_key`, `iri_prefix_undeclared_id`, `iri_prefix_undeclared_type`, `provenance_basis_prefix_undeclared`, `subject_id_not_fragment` |
| `element_value` | a value naming an element holds its `id` alone | `element_value_with_label` |
| `calendar_date` | a provenance entry's or a belief's `date` names a day of the Gregorian calendar from 0001-01-01 | `provenance_date_impossible`, `belief_date_impossible` |
| `provenance_duplicate` | a subject has one entry per pair | `provenance_repeated` |
| `belief_actor` | an actor holds at most one belief in an entry, actors compared as IRIs | `belief_actor_repeated` |
| `alignment_anchor` | an alignment anchor names two match timestamps of the manifest, on two timelines | `alignment_anchor_timestamp_unknown`, `alignment_anchor_timestamp_not_match`, `alignment_anchor_one_timeline` |
| `matchstamp` | the alignment anchors of a MatchStamp are one connected set | `matchstamp_not_connected` |
| `match_timestamp` | some MatchStamp names every match timestamp, and no two match timestamps lie on one coordinate | `match_timestamp_in_no_matchstamp`, `match_timestamp_coordinate_repeated` |
| `resource_timeline` | a resource's `timelines` name timelines of the manifest | `resource_timeline_unknown` |
| `resource_type` | at most one resource has the type `MatchClaim`, at most one the type `Projection` | `resource_match_claim_twice`, `resource_projection_twice` |

Every case of statements starts from one manifest: the format's context
with the prefixes `schema`, `wd` and `wdt` (others where a case says so)
and one root `clt_1` of 8 quarters, in the complete form.

`version_unknown` names the version 0.1.0, which 0.2.0 replaces; its `code` is `null` and its
`"error": "UnsupportedVersionError"` names the error both packages raise
instead. No serialization writes a non-finite number, so the two `finite_number` cases hold
a finite placeholder at their path and name in `non_finite` (`"Infinity"` or
`"NaN"`) the value a test puts there before validating; Python's
`timetoshare.fixtures.rejection_case` reads a case with that value in place.

## Acceptance cases

`fixtures/acceptances/<version>/numbers.yaml`, hand-authored in canonical
YAML, is the one table of how an own-axis value is read: the number type
fixes the form, the spelling within the form is free. It is a list of rows
`{number_type, value}`, each with either `read`, the value read written as
its number type spells it (a Fraction in lowest terms with integer
members, an int as a JSON integer, a float as a JSON number with a
fractional part), or `refused: representation`, the code both validators
report at the value. Every reader of own-axis values runs every row; the
package tests read the value as the `offset` of a root whose unit takes
the row's number type (`ticks` for int, `seconds` for float, `quarters`
for fraction). A Fraction member with a fractional part is the schema's
refusal (`length_fraction_member_not_integral`), no row here.

| `number_type` | `value` | Read |
| --- | --- | --- |
| fraction | `[2, 4]` | `[1, 2]` |
| fraction | `[1, 8.0]` | `[1, 8]` |
| fraction | `[4, 8.0]` | `[1, 2]` |
| fraction | `[-3, 6]` | `[-1, 2]` |
| int | `480` | `480` |
| int | `480.0` | `480` |
| float | `2` | `2.0` |
| float | `0.1` | `0.1` |
| int | `[480, 1]` | refused |
| int | `2.5` | refused |
| fraction | `12` | refused |
| fraction | `12.0` | refused |
| float | `[25, 2]` | refused |
| float | `9007199254740993` | refused (2^53 + 1 is no float) |

## Warning cases

A warning is never an error. Each of the 16 warning cases under
`fixtures/warnings/<version>/` holds a manifest together with the two lists
both packages must return for it: `unknown_keys`, the `{path, key}`
entries `unknown_keys` and `unknownKeys` return, sorted by path and then by
key, and `warnings`, the `{code, path, message}` entries
`manifest_warnings` and `manifestWarnings` return, sorted by path and then
by code. Three cases hold one warning each and no unknown key:
`context_absent`, a manifest without `@context` (`context_absent` at the
root), and `bundle_blank_statements` and `bundle_blank_provenance`, a
manifest without `id` that carries `statements` or only `provenance`
(`bundle_blank` at that key). The other thirteen hold the format's context,
unknown keys and no warning. `several_depths` places unknown keys at every
depth of a manifest; each of the other twelve holds one or two keys its
object does not declare, among them keys a writer might plausibly add,
such as `support_policy`, a timeline's `class`, a selector's former `ids`
or an address's `root`. Python's `warning_paths()` lists the cases. Both
packages read the same files and compare their lists with them.

See the [main README](../README.md) for the manifest shape, the schema API
and the serializations.
