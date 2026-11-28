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
  provenance ([Statement fixtures](#statement-fixtures));
- under `flow/`, manifests of flow control, FlowMaps and virtual timelines
  ([Flow fixtures and expected flows](#flow-fixtures-and-expected-flows)).

Version 0.2.0 has 52 manifests directly under `fixtures/0.2.0/`, 19 under
`groups/`, 20 under `bundles/`, 4 under `statements/` and 12 under
`flow/`, 107 in all, each with its minimal twin, so 214 files. Beside them
lie the expected RDF of the 4 statement fixtures under
`fixtures/rdf/0.2.0/`, the expected flows of 10 flow fixtures under
`fixtures/flows/0.2.0/`, the table fixture under `fixtures/tables/0.2.0/`
([The table fixture](#the-table-fixture)), the vectors of minted IDs under
`fixtures/ids/` ([Minted ID vectors](#minted-id-vectors)), the package
fixtures under `fixtures/packages/0.2.0/` ([The package
fixtures](#the-package-fixtures)), 259 rejection
cases, 19 warning cases, one table of acceptances under
`fixtures/acceptances/0.2.0/` ([Acceptance cases](#acceptance-cases)) and
one list of cases of several problems under `fixtures/precedence/0.2.0/`
([Cases of several problems](#cases-of-several-problems)).

Every accepted fixture is written in the complete form, every key with a
default written with it, and has a **minimal twin** beside it,
`<name>.minimal.yaml`, the same manifest in the minimal form, as
timetoalign's `to_dict()` writes it by default. The two obey one law:
`minimal(fixture)` equals the twin, `complete(twin)` equals the fixture,
and the library reads both to equal objects. The manifests are emitted by
timetoalign through the catalogue and pipeline in `scripts/fixtures/`, with
`scripts/emit_fixtures.py` as its CLI; that pipeline is their only writer,
the manifests under `flow/` included ([Flow fixtures and expected
flows](#flow-fixtures-and-expected-flows)).
Regenerate them after a serialization change and review the diff. The CLI
refuses to replace the fixtures of a version whose tag
`v<version>` exists, so a released version's fixtures stay as released.

The rejection cases under `fixtures/rejections/<version>/`, the warning
cases under `fixtures/warnings/<version>/`, the cases of several
problems under `fixtures/precedence/<version>/` and the expected flows
under `fixtures/flows/<version>/` are hand-authored. The
emission script does not touch them.

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
every group member, a virtual timeline a group names among them, and
every root that is neither a member nor holds one, as an editor marks a
new root: the named timestamp `origin` at 0 and, where
the length is known, `length` at the root's length, each with the `display`
`["wedge", "coordinate"]` and an ID the script gives, `timestamp_N`
with the smallest `N` the manifest leaves free, by timeline ID and then
coordinate (`origin_and_length` in `graphical.py`). On a member that is a child
timeline both are groupstamps with the `display` `["wedge", "coordinate",
"cross_section"]`, as an editor gives them to a child joining a group, so
that their lines cross the frame and the member's ancestor lines. Every timeline, MeasureMap, conversion
map, region and flow-control element carries an ID; IDs the script does not give are
minted by timetoalign when it constructs the element: the type prefix, `_`
and 13 random base-36 characters, seeded from the element's content (by
a loader, from the bytes it reads), so that every run of the script mints
the same IDs. Elements of equal content
take their IDs in the order they are constructed, so that order is part of
the fixture contract. Every manifest carries the
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
| `flow_control.yaml` | a repeat end at 8 taken twice to the jump target named "repeat-start" at 2, a Fine at 12 (a break of the manifestation `fine` whose `ends.after` names the dal segno), and a dal segno at 16 to the jump target named "segno" at 4 |
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
| `timestamp_wedge_rotation.yaml` | turned wedges: a root `melody` ("Melody", 16 quarters) with the child `phrase` ("Phrase", 12 at 1), whose band order lays its markers band against its line above it; each named timestamp is named after its wedge's `rotation`. On the root, at quarters 2, 4, 6, 8, 10 and 12, rules naming each wedge's address turn it -135, -45, 0, 45, 135 and 180 (0 written); on the child, at its quarters 2 and 6, addressed rules turn the wedges -45 and 45, mirrored above the line, and at its quarter 10 only the rule `{"element": "wedge", "within": "phrase"}`, which the addressed rules outrank, turns it 90; each turned wedge carries its name label round to its thick end, upright and centred on the wedge's axis, without moving any other label; the root's `origin` and `length` keep the unturned wedge. Every timestamp but `origin` and `length` draws its cross-section line across the whole card, from border to border, cut only where its own wedge's body or its own label lies across it: the line of the wedge at 0, from its tip to the end of its label, and that of the wedge at 180, from the label carried across the line to the tip; every other line runs uncut |

The corpus fixtures exercise public timetoalign loaders; the synthetic
fixtures are emitted first:

| File or prefix | Loader input |
| --- | --- |
| `corpus_audio_audio.yaml` | an audio file, its timeline in samples with a map to seconds |
| `corpus_midi_score_midi.yaml` | a score MIDI file |
| `corpus_score_ms3.yaml` | an ms3 score with MeasureMap and flow-control data: the loader writes its repeats, volta brackets, breaks and barlines as flow-control elements |
| `corpus_supra_iiif.yaml` | an IIIF manifest: the display image of its canvas, a locked timeline in pixels that names the canvas in `meta.image` |
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
| `child_flow_control.yaml` | a root `piece` of 16 quarters whose child `verse` (8 at 4) holds a da capo al fine, the break "Fine" at 4, whose `ends.after` names the da capo, and the jump "D.C. al Fine" at 8 back to 0, while the root holds no flow control |
| `child_jumps.yaml` | a root `piece` of 16 quarters whose child `verse` (8 at 4) holds the jump target `segno` at 2, the jump "Repeat" at 4, a repeat end taken twice back to the child's start, and the jump "D.S." at 8, a dal segno to `segno`, while the root holds no flow control |
| `volta_run.yaml` | a root `score` of 24 quarters with a run of three volta brackets: the jump `jump_1` at 8 with the destinations `by` 0 on pass 1, to `jump_target_1` at 12 on pass 2 and to `jump_target_2` at 16 on pass 3, the volta breaks `break_1` at 12 and `break_2` at 16 each with the repeat end closing the bracket before it (`jump_2`, `jump_3`, the second with `reset` false), and the section break `section_break_1` at 20 closing the third bracket; the atomic sections A to E the library computes, regions typed `tts:AtomicSection`, beside the region "Exposition" (0 to 16), which is none, and the FlowMaps of the three conventions |

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
labelled "Repeat" whose one destination, a repeat end (`repeat_end`,
`repeat_count` 1), has no place and goes back to the timeline's start.

| Builder | Construction |
| --- | --- |
| `group_number_types` | a group of three timelines whose axes have different number types (quarters as fractions, seconds as floats, pixels as integers), in a display order that differs from their ID order |
| `group_child_member` | a group of the second half of a score, a child of the score placed at its exact offset, with a whole recording |
| `group_styled` | the group of `group_number_types` with conversion maps, a region, a jump and styling: the score has a map to ticks, the region "Theme" from 0 to 8 and a repeat from 8 back to 0, the performance a map to samples and the page a map to points; its `styles` and `rules` give every group frame the style `frame-highlight` (a violet stroke), fill the group's title `group_1/name` violet, and give every card inside a frame a light violet `shadow` and a corner radius `rx` of 2 |
| `group_parent_right` | a child `first-half` (8 quarters at 0) of a piece of 16 quarters, with a whole recording; the piece runs on to the right of the member |
| `group_parent_both` | as above with the child `middle` (8 quarters at 4); the piece runs on to both sides |
| `group_parent_exact` | as above with the child `whole` (16 quarters at 0); the piece coincides with the member |
| `group_parents_mixed` | three child members of different parents (an exposition of 32 quarters at 16 in a locked sonata of 48; a take of 25.5 seconds at 30.0 in a session of 90.0 seconds, with a map to samples; a system of 600 pixels at 0 in a page of 1754) and the root `audio` of 1323000 samples, with a map to seconds |
| `group_grandchild` | a grandchild `theme` (8 quarters at 8 in a movement of 16 quarters at 16 in a score of 64) with a recording of 12.0 seconds |
| `group_grandchild_parent_on_top` | the group of `group_grandchild` with the band order `["line", "children", "conversion_maps", "markers", "regions", "flow_control"]` for the movement `movement` in `graphical.order`, which puts its children band below its line: in the card of `theme` the ancestor line of `movement` lies above the member and that of `score`, of the default order, below it |
| `group_groupstamp` | the group "Performance" of the score `score` ("Score", 8 quarters, with a map to ticks) and the performance `performance` ("Performance", 4.0 seconds, with a map to samples), so that each member has a conversion maps band; the timestamp `timestamp_1` "Bar 2" at quarter 4 of the score is a groupstamp, its wedge unturned: its own line crosses the score's card, cut where its wedge and its label stand, and its frame line runs on across the performance's card |
| `group_groupstamp_child_member` | the group "Performance" of the score `score` ("Score", 8 quarters), holding the child `second-half` ("Second half", 4 quarters at 4), and the performance `performance` ("Performance", 4.0 seconds), no timeline carrying a map; the timestamp `timestamp_1` "Bar 4" at quarter 2 of the child is a groupstamp, since the child lies in the group through its parent, its wedge unturned: its own line crosses the score's card, cut where its wedge and its label stand below the child's line, and its frame line runs on across the performance's card |
| `group_child_member_stamps` | the group of `group_parent_both` (the child member `middle`, 8 quarters at 4 in the piece `piece` of 16, and the root member `recording`, 10.0 seconds), whose child member carries both kinds of line: the timestamp `timestamp_1` "Bar 2" at quarter 2 of `middle`, drawing its cross-section line alone (`display` `["cross_section"]`), and the match timestamps `timestamp_2`, without a name, at quarter 4 of `middle` and `timestamp_3` at second 5.0 of `recording`, which the MatchStamp `matchstamp_1` ("Middle, bar 3") joins by the anchor `anchor_1`, drawing the name, from `claim_1`; these three are no groupstamps, while the child member's `origin` and `length` (`timestamp_4` at quarter 0 and `timestamp_5` at quarter 8 of `middle`) are groupstamps drawing their wedge, coordinate and line (`display` `["wedge", "coordinate", "cross_section"]`), as every child member's are, and the recording's `origin` and `length` (`timestamp_6`, `timestamp_7`) draw their wedge and coordinate. Each line of the three runs from border to border across every card that draws its timeline's line, uncut: the child's card, where it crosses the ancestor line of `piece`, the ancestor card of `piece`, which draws `middle` as its child, and the recording's card; the anchor joins the bottom of the child's card to the top of the recording's |
| `group_elided_inside` | the group "Excerpt" of the excerpt `excerpt` ("Excerpt", 8 quarters at 8 in the movement `first`, 32 quarters at 0 in the piece `piece` of 64, whose second movement `second` lies at 32) and the recording `recording` (10.0 seconds); `first` and `second` share one row of `piece`'s children band, and the piece's ancestor card, under the mode `auto`, elides both movements around the excerpt |
| `group_elided_members` | the group "Theme" of the excerpt `excerpt` ("Excerpt", 16 quarters at 16 in the piece `piece` of 48), the voice `voice` ("Voice", 24 quarters, holding the phrase `phrase`, 8 quarters at 12) and the sketch `sketch` ("Sketch", seconds, of unknown length), in that display order. Two elisions lie on timelines lying in the group, so each is drawn across the frame: `elision_1` "Development" on `excerpt` from 2 to 8 (the frame's proportions 1/8 to 1/2), without `width`, drawing its ellipsis, its name and its coordinates, and `elision_2` on `phrase` from 2 to 6 (14 to 18 of `voice`, the proportions 7/12 to 3/4) with `{"ratio": 0.5}`. The groupstamps `timestamp_1` "Climax" at 15 and `timestamp_2` "Return" at 21 of `voice` lie in the second gap and after it; `piece`'s ancestor card carries the two gaps into the member's span and, under the mode `auto`, draws its derived elisions around it |
| `bundle_mixed` | the bundle "Mixed" of two groups, a score with its performance and a page with an excerpt (a child of a recording); `annotations` is ungrouped, and the recording, which no group names, contains the member `excerpt` and is drawn as its ancestor line and whole in its ancestor card behind the frame. The score has a map to ticks, then a tempo map to seconds, and a repeat from 8 back to 0; the performance a map to samples; the page a map to points; the excerpt a map to seconds; the recording a map to seconds, drawn in its ancestor card only; `annotations` the regions "Verse" from 0 to 4 and "Chorus" from 4 to 12, and no map |
| `bundle_shared_parent` | the bundle "Sonata" of two groups whose members are two children of one score (an exposition at 0 and a recapitulation at 20, 12 quarters each), each with a take; a page is ungrouped, and the score, which no group names, contains both members and is drawn as an ancestor line of each and whole in an ancestor card behind each frame. Both children are segment lines: the exposition, with a map to ticks, of the segments "First theme" and "Second theme" of 6 quarters, the second with a tempo map to seconds; the recapitulation, with no map, of the segment lines "First theme" and "Second theme" of 6 quarters, each of the segments "Phrase 1" and "Phrase 2" of 3 quarters, and only its "Second theme" has a map to ticks. The take `take_1` is a segment line, with a map to samples, of "First theme" (14.0 seconds) and "Second theme" (16.0 seconds); the take `take_2` and the page carry no map. The score has a map to ticks, the region "Development" from 12 to 20 and a repeat from 12 back to 0, drawn in its ancestor cards only. A segment's ID begins with its segment line's (`exposition_first`, `recapitulation_second_1`) |
| `bundle_ungrouped` | the bundle "Sketches" of three ungrouped roots and no group: a score of 16 quarters with a map to ticks and a da capo al fine, the break "Fine" at 8 (`fine`, its `ends.after` naming the da capo) and the jump "D.C. al Fine" at 16 back to 0 (a destination `da_capo_al_fine` without a place); a recording with a map to seconds; and an unlocked segment line, with a map to points, of three pages of 1754 pixels that carry none |
| `bundle_shared_member` | the bundle "Shared" of two groups that share a member: the score `t` ("Score", 8 quarters) is a member of the group `g1` ("Performance") beside the performance `u` (4.0 seconds) and of the group `g2` ("Page") beside the page `v` (800 pixels); no timeline carries a map, a region or flow control |
| `bundle_free_ids` | the bundle "Free IDs" of the group `group_1` ("Piece") of two roots whose IDs are free strings: the score `https://example.org/piece/score` ("Score", 8 quarters) with the region "Exposition" `https://example.org/piece/score#exposition` from 0 to 4, and the take `perf/take 2` ("Take 2", 4.0 seconds) with the region "Intro" `take 2/intro` from 0.0 to 1.0; one rule selects the take's region by its address `{"id": "#take 2/intro"}` and strokes it teal |
| `bundle_resources` | the bundle "Resources" of the score `score` (8 quarters) and the recording `take_1` (352800 samples), ungrouped, with two resources: `resource_1`, the MatchClaim table `match_claims.parquet` holding data for both timelines, with its media type `application/vnd.apache.parquet`, and `resource_2`, the registry `registry.parquet` (the type `Registry`), holding rows of `take_1`, with nothing optional (an event's registry row names its pre-parsed table, so a manifest names no pre-parsed table); neither file lies beside the fixture, so neither states a size or a digest (the table fixture's manifest states both of its own tables')
| `bundle_matchstamps` | the bundle "MatchStamps" of the score `score` ("Score", 8 quarters) and the takes `take_1` ("Take 1", 352800 samples) and `take_2` ("Take 2", 396900 samples), ungrouped; the match timestamp `timestamp_1` at quarter 4 of the score, without a name, shared by two MatchStamps: `matchstamp_1` ("Bar 2, downbeat (take 1)") joins it to sample 88200 of `take_1` by the anchor `anchor_1`, which also draws the name, from the MatchClaims `claim_1` and `claim_2`; `matchstamp_2` ("Bar 2, downbeat (take 2)") to sample 99225 of `take_2` (the match timestamp `timestamp_3`, named "Take 2, bar 2" and drawing its name) by `anchor_2`, from `claim_3` |
| `bundle_matchstamp_cards` | the bundle "MatchStamp cards" of two groups that share a member, as `bundle_shared_member`: the score `score` ("Score", 8 quarters), holding the child `second-half` ("Second half", 4 quarters at 4), is a member of the group `group_1` ("Performance") beside the performance `performance` (4.0 seconds) and of the group `group_2` ("Page") beside the page `page` (800 pixels); three match timestamps without a name, `timestamp_1` at quarter 4 of the score, `timestamp_2` at second 1.0 of the performance and `timestamp_3` at quarter 2 of the child; `matchstamp_1` ("Bar 2, performed") joins the performance to the score, drawn in two cards, by `anchor_1`, from `claim_1`; `matchstamp_2` ("Second half, bar 1") the score to its child, whose lines lie in one card, by `anchor_2`, from `claim_2`; both anchors draw the name |
| `bundle_matchstamp_groupstamp` | the bundle of `bundle_matchstamp_cards` whose match timestamp `timestamp_1` at quarter 4 of the score, a member of both groups, is a groupstamp, its line across the frame of `group_1` and that of `group_2` |
| `bundle_groupstamp_shared_member` | the bundle of `bundle_shared_member` with the timestamp `timestamp_1` "Bar 2" at quarter 4 of the shared member `t`, a groupstamp, its wedge unturned, its line across the frame of `g1` and that of `g2`: in each, its own line crosses `t`'s card, cut where its wedge and its label stand, and its frame line runs on across the other member's card; no member has a band. The elision `elision_1` on `t` from 1 to 3 with `{"canvas": 24}` lies in both groups, so it is drawn across both frames |
| `bundle_elisions_stored` | the bundle "Elisions" of the group "Theme" of the child `theme` (8 quarters at 16 in the score `score` of 64, which also holds the coda `coda`, 8 quarters at 56), the child `take` (25.5 seconds at 30.0 in the session `session` of 90.0 seconds) and the root `recording` (10.0 seconds), and of the ungrouped page `page` (1754 pixels); one rule hides the line of `coda`, another, `{"element": "elision", "within": "session"}`, hides every elision within the session, and a third, addressed to the cards of the session, `{"elision-mode": "full"}`, draws them whole. Seven stored elisions, in canonical order: `elision_1` on `coda` from 0 to 8, a child whose line is hidden; `elision_2` "Appendix" on `page` from 600 to 1754, in an ungrouped root's card, drawing its ellipsis, name and coordinates; `elision_3` on the member root `recording` from 0.0 to 2.0, which lies in the group and so is drawn across its frame and carried into the ancestor cards behind it, drawing its ellipsis and coordinates; on `score`, behind the frame of `theme` (16 to 24 on its axis), `elision_4` from 0 to 20 with the width `{"ratio": 0.5}`, which overlaps the member and draws its ellipsis, ID and continuations, `elision_5` "Development" from 32 to 48 with `{"span": [4, 1]}`, drawing its name alone, and `elision_6` from 40 to 56 with `{"canvas": 30}`, which overlaps `elision_5` and draws a bare gap; and `elision_7` on `session` from 0.0 to 30.0, kept and not drawn under the session's `full` and hidden a second time by the rule within the session. The gap of `elision_3` carried into the ancestor card of `session` stays drawn under both rules: a carried gap is drawn by the frame's mode and display, not by the card's cascade |
| `bundle_elided_layerit` | the bundle "Suite bergamasque" of the suite `clt_1` (1616 quarters) and its four movements, locked and without maps, `clt_2` "Prelude" (356 at 0), `clt_3` "Menuet" (312 at 356), `clt_4` "Clair de Lune" (324 at 668) and `clt_5` "Passepied" (624 at 992); each movement holds one excerpt on its own axis, `clt_6` "Prelude mm. 1–4" (16 at 0), `clt_7` "Menuet mm. 41–44" (12 at 120), `clt_8` "Clair de Lune mm. 1–6" (27 at 0) and `clt_9` "Passepied mm. 153–156" (16 at 608), and four groups, each named as its excerpt, list the excerpt and a recording in seconds (`cpt_1` to `cpt_4`: 14.0, 6.5, 33.35 and 5.5 seconds): the suite's ancestor card behind each frame, under the mode `auto`, elides it around the opening of the work, an excerpt inside a movement, the opening of a later movement and the ending |
| `bundle_arranged_roots` | the bundle "Arranged" for the arrangement side by side (drawing specification, section 8.8, Drawn once): the score `score` (48 quarters) holds three touching movements, `exposition`, `development` and `recapitulation` (16 quarters at 0, 16 and 32), the session `session` (130.0 seconds) the takes `take_a` and `take_b` (30.0 seconds at 0.0 and 100.0); the group "Exposition" lists `exposition` and `take_a`, "Development" `development` and the root `notes` (800 pixels), "Recapitulation" `recapitulation`, the root `annotations` (600 pixels) and `take_b`, and the page `page` (1754 pixels) is ungrouped. Side by side the three groups follow one another along the score, touching (seams), Exposition and Recapitulation hang on the session too with Development between them (a gap, the session passing behind Development), the annotations make Recapitulation's two anchors lie further apart than Exposition's (padding), and the page hangs on nothing |
| `bundle_arranged_conflict` | the bundle "Conflict" of the score `score` (32 quarters) holding the themes `theme_a` (16 quarters at 0) and `theme_b` (16 quarters at 8), each alone in a group named as it, "Theme A" and "Theme B": their stretches on the score overlap from 8 to 16, so the two groups cannot stand side by side |
| `group_measure_map` | the group "Edition" of a score of 16 quarters and its MIDI rendering of 7680 ticks, both reading one entry of `measure_maps`, four bars of 4/4: the score through its `MeasureRecordMap`, the rendering through a `ChainMap` of the `LinearMap` `ppq` to quarters (480 ticks per quarter) and its `MeasureRecordMap` |
| `virtual_member` | the group "Performance" `performance` of the virtual timeline `allegro_default` ("Allegro, default", 4241/2 quarters), which applies the FlowMap `default` to the root `allegro` of `flow/virtual_cards`, and the recording `recording` ("Recording", 702.5 seconds), in that display order. The root is no member and contains none, a virtual timeline lying in no tree, so it is an ungrouped root; it is written whole, its flow control, atomic sections, FlowMaps and three virtual timelines with it. The virtual member's `origin` and `length` are named as every member's |
| `switched_frame` | the group "Performance" `performance` of the root `allegro` of `flow/virtual_cards`, written whole, and the recording `recording` ("Recording", 702.5 seconds), with one rule of `graphical` setting the property `flow` of the card of `allegro` to the FlowMap `default`, so that the frame is drawn on that FlowMap's virtual axis |

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
`group_grandchild`, `group_grandchild_parent_on_top`, `group_groupstamp_child_member`, `group_elided_inside`, `group_elided_members`, `bundle_elisions_stored`, `bundle_elided_layerit`, `bundle_arranged_roots` and `bundle_arranged_conflict` hold none of them, and `group_unknown_length` holds only
a region. The table also names where each side of a child member's
ancestor band occurs (drawing specification, section 8.3). The segment lines of the single-timeline fixtures but
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
| a map, a region and flow control on a root that contains group members and is drawn as an ancestor line of each, drawn in its ancestor cards only | `score` of `bundle_shared_parent` |
| a break and a jump together | `score` of `bundle_ungrouped` |
| a map, a region and flow control inside a styled frame | `score` of `group_styled` |
| a region on a child | `movement` of `unknown_length_child` |
| regions on segments without a line of their own, joining their segment line's regions band | `a` and `c` of `unknown_length_segments` |
| a break and a jump on a child, its root holding none | `verse` of `child_flow_control` |
| a jump target, a repeat end with a repeat count and a dal segno to a jump target on a child, its root holding none | `verse` of `child_jumps` |
| a run of three volta brackets, the last closed by a section break, and atomic sections beside another region | `score` of `volta_run` |
| a MeasureMap shared by two timelines, one reading it through a `ChainMap` from ticks | `score` and `midi` of `group_measure_map` |
| maps of two keys on two lines of one row, sharing the row's slots | `ante` and `cons` of `map_row_siblings` |
| maps of one key on a segment line and two of its segments that are not segment lines, in two sub-slots | `form`, `b` and `c` of `map_row_subslots` |
| maps on two siblings in two rows, each row with slots of its own | `ante` and `cons` of `map_row_moved` |
| ancestor lines below a child member, beyond its markers band, in the default band order: one ancestor, one with a map on the member's other side, and two | `second-half` of `group_child_member`; `take` of `group_parents_mixed`; `theme` of `group_grandchild` |
| an ancestor line above a child member, its ancestor's band order putting the children band below its line, and one below it in the default order | `theme` of `group_grandchild_parent_on_top` |

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

No default hides a band (drawing specification, section 4): a child's
regions, or a segment's, are drawn at its own line, and the flow control
of a root's whole tree, its descendants' included, in the root's flow
control band (section 6.4, Gathering); no child draws a flow control
band of its own.

## Flow fixtures and expected flows

The twelve manifests under `flow/`, each with its minimal twin, cover flow
control, FlowMaps and virtual timelines ([main
README](../README.md#flow-control)). Like every other manifest fixture
they are emitted (their builders are in `scripts/fixtures/flow.py`, which
builds the flow control from timetoalign's element classes) and obey the
same laws: `minimal(fixture)` equals the twin, `complete(twin)` equals the
fixture, both validate and neither draws a warning. None names the origin
and length of its root.
Each holds one root of quarters, but `loop`, in seconds:

| File | Holds |
| --- | --- |
| `sonata_exposition.yaml` | "Sonata exposition", 24 quarters: two volta brackets, the Jump `jump_1` at 12 with the destinations `by` 0 on pass 1 and to `jump_target_1` on pass 2, and at 16 the Break `break_1` between the brackets, the first bracket's repeat sign `jump_2` (`repeat_end`, `repeat_count` 1, no place) and `jump_target_1`; its three atomic sections as regions typed `tts:AtomicSection`, the FlowMaps of the three conventions, each with a provenance entry of method `inferred` since they are computed, and the virtual timeline `virtual_1` of the `default` FlowMap, 36 quarters (the main README's example) |
| `dal_segno_al_coda.yaml` | 32 quarters: a segno at 4, a To Coda at 12 to the coda at 24, holding `after` the dal segno al coda at 24 back to the segno |
| `da_capo_al_fine.yaml` | 16 quarters: a Fine at 8, a break whose `ends.after` names the da capo al fine at 16, which has no place |
| `repeat_end_and_dal_segno.yaml` | 24 quarters: one Jump at 16 with two destinations, a repeat end to the repeat start at 4 and a dal segno to the segno at 8 |
| `volta_passes.yaml` | 16 quarters: brackets for the passes `[1, 3]` and `[2]` from the Jump at 8; at 12 the Break between the brackets, a Fine whose `ends.after` names the repeat sign at 16, the first bracket's repeat sign and the second bracket's start; the second bracket closed at 16 by a repeat sign with `reset: false` |
| `ossia.yaml` | 24 quarters with the child `ossia` at 16, laid out after the main text: a Jump at 4 with `by` 0 and a destination `determined: false` to the child, a Break at 16 ending the main text, and at 24 a Jump back to a jump target at 12 |
| `sections.yaml` | 32 quarters of two sections: a Fine at 8 naming the da capo al fine at 16, a section break without a manifestation at 16, and a da capo without a place at 32, which goes back to the section break |
| `loop.yaml` | 10.0 seconds: a Jump at 6.0 to a jump target at 2.0, taken 127 times, without a manifestation |
| `flow_map_by_hand.yaml` | "Set list", 20 quarters with the children `first` (8 at 0) and `second` (12 at 8) and no flow control: the FlowMap "Encore order" of `second`, a gap of 4 quarters and `first`, with no convention and `manual` provenance believed `true` by the editor |
| `repairs.yaml` | 16 quarters: an imported double barline at 8, an imported repeat end at 16 to the start that the editor believes `false`, and the repeat start at 8 and the repeat end at 16 to it, both added by hand (`manual`): the rejected Jump and its replacement at one coordinate |
| `virtual_cards.yaml` | "Allegro" `allegro`, 1644 quarters, the first movement of a sonata whose exposition is repeated through two volta brackets: the Jump `volta_jump` at 953/2 with the destinations `by` 0 on pass 1 and to the jump target `second_ending` at 500 on pass 2, and at 500 the Break `volta_break` and the repeat sign `repeat_end` (`repeat_end`, `repeat_count` 1, no place); its atomic sections, the regions `section_a` "A" [0, 953/2), `section_b` "B" [953/2, 500) and `section_c` "C" [500, 1644) typed `tts:AtomicSection` with the method `inferred`; the computed FlowMaps `default` (A B A C, 4241/2 quarters), `single` (A C, 3241/2) and `printed` (A B C), each naming its convention with the method `inferred`; the FlowMap `by_hand` ("Practice"), written by the editor, of a run of four `section_a`, a gap of 4 quarters and `section_c` (3054 quarters); and the virtual timelines `allegro_default` ("Allegro, default"), `allegro_single` ("Allegro, single") and `allegro_by_hand` ("Allegro, practice") applying `default`, `single` and `by_hand`. B is 47/2 of 1644 quarters, under 1.5 % of the written axis. Every ID is given; the library computes the sections and the three FlowMaps from the flow control under them |
| `switched_card.yaml` | the timelines, FlowMaps and virtual timelines of `virtual_cards`, and one rule of `graphical` setting the property `flow` of the card of `allegro`, `{"id": "allegro", "part": ["card"]}`, to the FlowMap `default` |

`fixtures/flows/<version>/` holds the expected flows of the flow fixtures
that hold flow control, ten files, one file `<name>.yaml` in canonical YAML
each, beside the trace `<name>.md` it was derived by hand with;
`switched_card`, whose timelines are those of `virtual_cards`, has the
flows of `virtual_cards.yaml`:

```yaml
manifest: flow/sonata_exposition   # the fixture's path under fixtures/<version>/, no extension
timeline: score                    # the timeline's ID, bare
atomic_sections:                   # in the order of the axis, lettered from A
  - {name: A, start: [0, 1], end: [12, 1]}
conventions:
  default: {runs: [...], sections: [...], findings: [...]}
  single: {runs: [...], sections: [...], findings: [...]}
  printed: {runs: [...], sections: [...], findings: []}
```

A run is a pair `[start, end]`, the end not played, one per stretch up to
a Jump, a Break or the length, as the main README's "Computing a flow"
plays them; `sections` lists the atomic sections the runs cover, in
order, so that an implementation that joins touching runs compares the
sections. Every value is spelled in the timeline's number type. A finding
is `{kind, coordinate}`, a `never_played` finding also with the `end`
of its stretch and any finding with its `cause` where it has one, in the
order the findings arise, `never_played` last, its kind one of `flow_ends_at_break`, `never_played`,
`endless_loop`, `ambiguous_targets` and `undetermined_target`, as the
main README's "Computing a flow" states them: `flow_ends_at_break` is not
stated where a Break with `ends` holds at the coordinate the flow ends at
(`volta_passes` ends at 12, where the Fine holds, with no finding), and
`never_played` is stated once for each stretch of the axis that no run
covers, from its start to its end, however many atomic sections it
holds. Findings
are stated for every convention. The only cause is `single_playback`: a
stretch `single` never plays that the `default` flow plays, divided
where the `default` flow begins or ends playing it, so that each
`never_played` of `single` either has that cause or lies where the
`default` flow does not play either and has none; no other finding has a
cause. `printed` plays the whole axis and its findings are always empty.

| Case | `default` | `single` | Findings of `default` | Findings of `single` |
| --- | --- | --- | --- | --- |
| `sonata_exposition` | A B A C | A C | none | `never_played` 12 to 16, `single_playback` |
| `dal_segno_al_coda` | A B C B D | A B C D | none | none |
| `da_capo_al_fine` | A B A | A B | none | none |
| `repeat_end_and_dal_segno` | A B C B C C D | A B C D | none | none |
| `volta_passes` | A B A C A B | A C | none | `never_played` 8 to 12, `single_playback` |
| `ossia` | A B C | A B C | `undetermined_target` at 4, `flow_ends_at_break` at 16, `never_played` 16 to 24 | the same, without cause |
| `sections` | A B A C C | A B C | none | none |
| `loop` | A, B 128 times, C | A B C | none | none |
| `repairs` | A B B | A B | none | none |
| `virtual_cards` | A B A C | A C | none | `never_played` 953/2 to 500, `single_playback` |

`printed` is the atomic sections in order in every case. The package
tests compute no flow: they check that each file agrees with its manifest
(its atomic sections, its runs on their boundaries, its `printed` flow and
the `never_played` findings of each convention with their causes), and an implementation that computes flows
is run against the files.

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

`fixtures/tables/<version>/` holds the fixture of the table types,
outside `fixtures/<version>/` so that no reader of the manifest fixtures
takes it for one, a manifest alone with the tables beside it:
`manifest.yaml`, the MatchClaim table `match_claims.parquet`, the registry
`registry.parquet` (one file), the pre-parsed Projection table
`projections.parquet`, the Extraction table `extractions.parquet` and
`expected.yaml`, the AlignmentAnchors and potential MatchStamps expected
of the MatchClaim table under seven belief filters, each a believer and
the states it keeps, in this order: no believer, every state but `false`;
for one actor every state but `false` (the default), then `true` alone;
for a second actor `true` alone; for the first actor `undecided` alone,
then `unlikely` with `false`; and the first actor written as the compact
IRI `orcid:0000-0002-1825-0097`, `true` alone, which keeps what the third
filter keeps. Every filter reads actors under the manifest's `@context`,
which declares the prefix `orcid`. The manifest holds three roots
(`clt_1`, quarters, with the child `clt_2` starting at the quarter 8;
`dpt_1`, samples; `cpt_1`, seconds) and names two tables in its
`resources`, each with its media type, its size, its SHA-256 digest and
the timelines its table holds data for: `resource_1`, the MatchClaim
table, names `clt_1`, `clt_2`, `dpt_1` and `cpt_1`; `resource_2`, the
registry, names `clt_2`, `dpt_1` and `cpt_1`, the timelines its event
rows lie on. The pre-parsed Projection table
and the Extraction table are named by the registry's rows, not by the
manifest. The MatchClaim table holds 18 rows; an event ID column holds
an event's ID or a sentinel's reserved string, never a null: `claim_12` is
a NOMATCH (`NOMATCH_SENTINEL` on its `dpt_1` side), `claim_11` a
synchronous MatchClaim with `CHUNK_SENTINEL` on both sides (`dpt_1` and
`cpt_1`, whose anchor joins the set of `claim_13`), its `dpt_1` side named
`downbeat 3` (a CHUNK side may name the position it states), and `claim_16` an
instant MatchClaim between `CHUNK_SENTINEL` on `cpt_1` (side A) and the
note at the quarter 1 of `clt_1`, whose anchor joins `claim_2`'s start into
one potential MatchStamp; `claim_17` joins the note at the quarter 45/4 of
`clt_1` and its Projection `projection_12` at the second 11.25 of `cpt_1`;
`claim_18` is a NOMATCH stated from `inserted_1`, a Projection on `dpt_1`
under the source's ID for a note the package does not hold
(`NOMATCH_SENTINEL` on its `clt_1` side), which states no anchor.

The registry holds 11 event rows, one per Projection, none where a side
is CHUNK (a CHUNK is no Projection; the Projections keep their numbers, so
`projection_6` and `projection_7` are not held), and each number type:
ints on `dpt_1` (instants and one interval), a float instant and a float
interval on `cpt_1`, and a fraction interval on the child `clt_2`,
`projection_10`, at 7/2 on the child and stored at 23/2, its position on
the axis of its root `clt_1`, with the duration 1/2; the float interval
and the fraction interval are named by no MatchClaim. Every event row
names the one extraction `extraction_1`, a run of an aligner without a
source file (`source` null), and the location `projections.parquet`. The
pre-parsed Projection table holds each Projection's `projection_of`:
every Projection but one names the event it stands for; `inserted_1`, an
int instant at the sample 573300, names none (`projection_of` null). The
registry's file holds its non-event rows first, the extraction at
`extractions.parquet`, each element of the manifest at `manifest.yaml`
and each MatchClaim at `match_claims.parquet`, sorted by location and ID,
then its event rows, sorted by timeline (code point), start (exact value)
and ID, as a writer writes them; the pre-parsed rows lie in the order of
the event rows. The script
`scripts/emit_tables.py` (run from `python/` as `uv run python
../scripts/emit_tables.py`; it needs pyarrow, a development dependency) is
its only writer: every row and every expected value is literal data in the
script, never computed by the derivation the tests check, and only the
sizes and digests are read from the bytes written. It rewrites a Parquet
file only when its table changes and refuses to replace the files of a
version whose tag `v<version>` exists. Python's
`timetoshare.tables.fixture_path(name)` gives the path of each file.

## The package fixtures

`fixtures/packages/<version>/` holds packages: folders with a
`package.yaml` at their root, listing their manifests and their tables.
`shared/` is a package of two manifests sharing their registry and their
tables: `bach/manifest.yaml` (a score `clt_1` in quarters, a performance
`dpt_1` in samples) and `handel/manifest.yaml` (a score `clt_2` with a
child `clt_3` starting at the quarter 4, a performance `dpt_2`). They
share the registry `registry/`, a folder of parts: `non_events.parquet`,
the non-event rows of both manifests' elements, of the MatchClaims and of the
extractions, sorted by location and ID, and one part per extraction
holding its event rows, sorted by timeline, start and ID:
`extraction_1.parquet`, Bach's Projections, made from the source file
`bach/alignment.csv`, each with its locator, and `extraction_2.parquet`,
Handel's, made by a tool without a source file, the two on the child
`clt_3` stored at their positions on its root `clt_2`. The Extraction
table `tables/extractions.parquet` records both runs, the first with the
source file's digest. The pre-parsed Projection table `tables/Projection/`
holds each Projection's `projection_of` in two files, `part_a.parquet`
and `part_b.parquet`, whose rows interleave the two manifests'. The
folder of
MatchClaims `tables/MatchClaim/` holds one file, which states one
provenance for every row (`timetoshare:provenance`), filled into the rows
by a reader of the folder. Each manifest's resources name the registry,
with the timelines whose event rows it keeps, and the MatchClaims, with
the timelines whose MatchClaims it reads; neither names the Projection
table or the Extraction table. Every file states its type
(`timetoshare:type`) and the version (`timetoshare:version`) in its
metadata. `expected.yaml` lists under `read`, per manifest and resource,
the IDs of the rows read for the resource's timelines, sorted, and under
`resolutions` the resolutions of some IDs, each a `path` (a manifest, or
`.` for the package root), an `id` and the `found` list of `Resolution`s,
each its `kind`, `location`, `manifest` and the registry `row`, in the
order `resolve` returns them: through a manifest, its element first, then
the registry rows belonging to it in the registry's order (the files of
the registry folder in code-point order, then each file's rows); through
the package root, every row of the ID in the registry's order.

`acceptances/<case>/` are the shared package with one change each that
the package check accepts, beside an `expected.yaml` listing no problem
(`problems: []`), the `reason` and, where the case concerns them, the
resolutions of some IDs:

| Case | Change |
| --- | --- |
| `external_location` | the content of Bach's `projection_1` lies outside the package: its `location` is the absolute URI `https://example.org/events/projection_1`, which the package check does not follow, and the pre-parsed tables hold no row of it; it resolves through Bach's manifest with that location |
| `recording_resource` | Bach's manifest names a recording beside it (`Audio`, `recording.flac`, `audio/flac`), a resource naming no table, which `package.yaml` does not list; the registry holds a non-event row of the resource |
| `timeline_in_two_manifests` | Handel's manifest holds a timeline `dpt_1`, as Bach's does, and keeps its event rows too; `dpt_1` resolves through each manifest to its own element, and through the package root to both, and Bach's `projection_1` resolves through Handel's manifest |
| `single_file_registry` | the registry is one file, `registry.parquet`, holding the non-event rows and the event rows of both extractions |
| `re_parsable_event` | an onset of Bach's extraction, `onset_9`, has no pre-parsed content: its `location` is null, its content re-parsable from the extraction's source file; it resolves through Bach's manifest with the location `None` |

`rejections/<case>/` are the shared package with one change each, beside
an `expected.yaml` listing every problem the package check reports, in
order (`code`, `file` from the package's root, `row` in that file or null,
`path`, `message`), and the `reason`:

| Case | Change | Code |
| --- | --- | --- |
| `row_of_no_manifest` | an event row on `dpt_9`, which no manifest holds | `unknown_timeline` |
| `projection_id_in_two_files` | the ID `projection_3` names a pre-parsed Projection of Handel's in `part_a` and, in `part_b`, the one of Bach's `projection_9`, whose content is then missing | `duplicate_id` |
| `claim_across_manifests` | a MatchClaim between Bach's score and Handel's performance | `claim_across_manifests` |
| `column_in_two_types` | a further column `velocity`, an integer in one file of the Projection table and a string in the other | `column_type_mismatch` |
| `version_mismatch` | a file declares the version 0.1.0 | `version_mismatch` |
| `resource_naming_no_table` | a resource names a folder of `Box` events `package.yaml` does not list | `unknown_table` |
| `folder_with_size` | `package.yaml` states a size for a folder | `folder_descriptor` |
| `timeline_unlisted` | Handel's registry resource no longer lists its child `clt_3`, whose event rows the registry holds | `unlisted_timeline` |
| `axis_mismatch` | an event row on the samples timeline `dpt_1` written in seconds | `axis_mismatch` |
| `file_of_another_type` | a file of the Projection folder states the type `MatchClaim` | `table_type` |
| `table_listed_twice` | `package.yaml` lists the folder of Projections twice | `duplicate_url` (`validate_package`) |
| `file_in_a_listed_folder` | `package.yaml` lists a file of the folder of Projections as a table of its own | `duplicate_url` |
| `registry_missing` | `package.yaml` lists no registry | `missing_registry` |
| `registry_listed_twice` | `package.yaml` lists a second registry | `duplicate_registry` |
| `extraction_table_listed_twice` | `package.yaml` lists a second Extraction table | `duplicate_extraction` |
| `unknown_extraction` | an event row of Handel's names `extraction_9`, which the Extraction table does not hold | `unknown_extraction` |
| `vanished_in_an_unknown_extraction` | an event row of Handel's vanished in `extraction_3`, which the Extraction table does not hold | `unknown_extraction` |
| `unknown_location` | an event row names `tables/Note/`, which `package.yaml` does not list, as its content's table | `unknown_location` |
| `missing_content` | an event row names the pre-parsed Projections, which hold no row of its ID | `missing_content` |
| `unregistered_id` | a pre-parsed Projection has an ID no event row of the registry has | `unregistered_id` |
| `locator_twice` | two event rows of Bach's extraction give the locator `row 1` | `duplicate_locator` |
| `registry_id_twice` | an onset of Handel's has the ID `claim_1`, a MatchClaim's | `duplicate_id` |
| `non_event_row_with_a_position` | a non-event row states a position | `schema_violation` |
| `stale_non_event_row` | the non-event rows give Bach's score timeline the kind of a virtual timeline, hold a region the manifest does not hold, and lack the group Handel's manifest gained | `stale_non_event_row` (three rows) |
| `projection_of_its_own_timeline` | a pre-parsed Projection of Bach's on `dpt_1` stands for an event of `dpt_1` | `invalid_projection_of` |
| `projection_of_no_timeline` | a pre-parsed Projection stands for an event of `clt_9`, which no manifest holds | `unknown_timeline` |
| `foreign_table` | `package.yaml` lists a table of the type `Features` whose file holds a column `x` and no `id` | `foreign_table` |

The script `scripts/emit_packages.py` (run from `python/` as `uv run
python ../scripts/emit_packages.py`; it needs pyarrow) is their only
writer: every row, every manifest, the rows read, the resolutions and
the problems expected are literal data in the script, the digest of the
first extraction's source file alone being read from its bytes, and the
script checks that the package check agrees before it writes. It rewrites a Parquet file only when its table
changes and refuses to replace the files of a version whose tag
`v<version>` exists. Python's
`timetoshare.tables.package_fixture_path(*parts)` gives the path of a
package or of a file in it.

## Minted ID vectors

`fixtures/ids/minted_ids.json` holds the test vectors of minted IDs. The
format requires nothing of an ID beyond its character rule, and neither
package mints one; a tool that mints IDs writes the element's type prefix,
`_` and random base-36 characters, seeded so that it can mint them again
([main README](../README.md#identity)). Two tools that mint from one seed
must mint the same IDs, and the file holds the values both check against:
timetoalign's tests read it at `timetoshare.validate.data_root() /
"fixtures" / "ids" / "minted_ids.json"`, TimeLineEditor's at
`@timetoalign/timetoshare/fixtures/ids/minted_ids.json`. It is JSON with
sorted keys, an indent of two spaces and a final line feed:

- `description`: the algorithm, as `scripts/emit_id_vectors.py` states it.
- `mix64`: pairs `{input, output}` of SplitMix64's finalizer for the inputs
  0, 1, 2, 42, 2^63, 2^64 − 1 and 0x0123456789abcdef.
- `minters`: for each seed 0, 1, 42, 81985529216486895
  (0x0123456789abcdef), 18446744073709551615 and −1, at each length 13,
  10 and 7, the first five IDs a fresh minter mints (`ids`) with the
  `prefixes` `note`, `clt`, `note`, `claim` and `score:clt`, in order: one
  counter serves every prefix, a prefix led by a role is a prefix like any
  other, and the seed −1, taken modulo 2^64, gives the IDs of
  18446744073709551615.
- `later_ids`: for the seed 42 at each length, the ID (`id`) a fresh
  minter mints at the `counter` 1000, every ID before it minted with the
  same `prefix`, `note`.

Seeds and the inputs and outputs of `mix64` are decimal strings, since they
may exceed 2^53 (JavaScript reads them as BigInt); lengths and counters are
integers. The script `scripts/emit_id_vectors.py`, a reference
implementation of the algorithm in the standard library alone, is the
file's only writer (`python3 scripts/emit_id_vectors.py` from the
repository root); it rewrites the file only when its bytes change. The
Python suite regenerates the file in memory and compares it byte for byte,
and checks every value apart from the script (`python/tests/README.md`,
"Minted ID vectors").

## Drawings

Each directory `fixtures/<version>/drawings/<name>/` pins one drawing of the
[drawing specification](https://github.com/TimeToAlign/TimeToShare/blob/main/docs/drawing.md)
as it stands in that version, with exactly three files; the drawings of the
current version follow `docs/drawing.md` as it stands, and those of a
released version follow the specification tagged with it.

The drawings of 0.2.0 are every fixture in the complete form but the corpus
ones (`corpus_*`) and the statement fixtures, at the default placement, and
thirty-four variants. The
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
`score`'s jump (`bundle_mixed__member-card-spacing-8`);
`bundle_ungrouped` with the place `{score: {x: -60, y: -150, height: 120}}`
(`bundle_ungrouped__places`), with the place `{recording: {scale: 1.5}}`
(`bundle_ungrouped__scale`) and with the block's spacing 24 and the card
spacing `{score: {spacing: 8}}`, which deepens `score`'s flow control band
(`bundle_ungrouped__spacing`). The drawings that show the elisions an
ancestor card derives take, at the default placement and in their
variants, an application layer whose first rule sets `elision-mode` to
`auto` on every ancestor card, `{"element": "ancestor_card"}`, since
the initial `custom` derives none: `group_child_member`,
`group_parents_mixed`, `group_grandchild`,
`group_grandchild_parent_on_top`, `group_elided_inside` and
`group_elided_members` (`group__<name>`), `bundle_elided_layerit`
(`bundle__bundle_elided_layerit`), and the variants
`group__group_elided_inside__labels`,
`group__group_elided_members__full` and
`bundle__bundle_elided_layerit__view-1024x640`; every other drawing
shows the defaults, which draw every ancestor card whole but for the
elisions stored for it. Then three groups with
an application layer of one rule that hides the ancestor cards the
defaults show, `{"element": "ancestor_card"}` set to `display` `none`:
`group_parent_both`, `group_parent_right` and `group_parents_mixed`
(`group__<name>__ancestor-cards-hidden`); and four groups with an
application layer of one rule that hides every elision,
`{"element": "elision"}` set to `display` `none`, so that each ancestor
card is drawn whole, as the defaults draw it: `group_grandchild`, `group_grandchild_parent_on_top`,
`group_parents_mixed` and `group_elided_inside` (`group__<name>__full`);
and `bundle_elided_layerit` in the view 1024 × 640
(`bundle__bundle_elided_layerit__view-1024x640`), where the bound of the
view sets the default proportion of the excerpts at the opening and the
ending; and `group_elided_inside` with an application layer of one rule
addressed to the cards of `piece`, `{"addresses": [{"id": "piece",
"part": ["card"]}]}`: setting `elision-display` to `ellipsis name
coordinate`, so that the derived elisions of its ancestor card show their
name and coordinate labels (`group__group_elided_inside__labels`), and
setting `elision-mode` to `custom`, the initial value, which draws that
card whole while no card elision is stored
(`group__group_elided_inside__custom`); and
`group_elided_members` with an application layer of one rule addressed to
the frame, `{"addresses": [{"id": "group_1"}]}`, setting `elision-mode` to
`full`, so that the frame and the ancestor card behind it are drawn without
the group's two gaps, the ancestor card keeping its derived elisions
around the member (`group__group_elided_members__full`); and
`bundle_groupstamp_shared_member` with the place `{g2: {scale: 1.5}}`, where
the gap of the elision on the shared member `t` is drawn in both frames,
the second at the scale 1.5
(`bundle__bundle_groupstamp_shared_member__scaled`); and
`bundle_arranged_roots` arranged side by side in the order
`page`, `group_3`, `group_1`, `group_2`
(`bundle__bundle_arranged_roots__horizontal`), whose row the rules of the
arrangement repair to `page`, `group_1`, `group_2`, `group_3`, and one
under another in that order (`bundle__bundle_arranged_roots__vertical`);
`bundle_arranged_conflict`, `bundle_elided_layerit` and
`bundle_shared_parent` arranged side by side with an empty order
(`bundle__<name>__horizontal`), the first refused, its two groups
overlapping on the score, and so drawn one under another; and
`flow/virtual_cards` with the places `{allegro_by_hand: {}, allegro_default:
{}, allegro_single: {}}`, its three virtual timelines placed as cards of
their own, one with a run drawn once and a gap line
(`flow__virtual_cards`); and `flow/switched_card`, whose card of `allegro`
its own rule switches to the FlowMap `default` (`flow__switched_card`).
Among the drawings at the default placement, `group__virtual_member`
draws a virtual timeline as a group member and `group__switched_frame` a
frame switched by its member's card, the other member carried through
the group onto the FlowMap's axis (drawing specification, section 8.10).
113 drawings lie here.
`bundle__bundle_shared_member` draws the timeline `t`, a member of both
`g1` and `g2`, once in each frame, in two cards that both carry the
address `{"id": "t", "part": ["card"]}`, every element of its two drawings
carrying the same address in both. No variant sets a band order: band orders are the manifests' own,
in their `graphical.order` (`styled__score`, `styled_score_flow_inner`,
`map_child_band_order`, `map_root_band_order`, `map_band_order_subset`, `timestamp_wedge_rotation`,
`group_grandchild_parent_on_top`). Each directory holds:

- `inputs.json`, everything a drawing needs besides the manifest itself and
  the two fonts, written with `dumps` in pretty JSON:
  - `manifest`: the path of the manifest's canonical YAML file relative to
    the same version's directory (`nested.yaml`,
    `groups/group_child_member.yaml`);
  - `placement`: `length`, `spacing`, `width`, `height` and `places`, all
    five always written, defaults included (400, 8, `null`, `null`, `{}`),
    and `view`, the view `{width, height}` the drawing is shown in,
    written only where a variant states one (default `{width: 1280,
    height: 720}`, drawing specification, section 1), and
    `arrangement`, the block's arrangement `{direction, order}`,
    likewise written only where a variant states one (default `null`,
    each item at its place; drawing specification, sections 1 and 8.6);
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
for byte. Forty-one `figure.svg` files are derived by hand from the
specification alone and are never regenerated, among them every drawing of
a timeline of unknown length, the three variants of `bundle_ungrouped`, the
band orders of
`styled_score_flow_inner`, `map_child_band_order`, `map_root_band_order`
and `map_band_order_subset`, `joint_rows`, the three drawings of conversion map
slots (`map_row_siblings`, `map_row_subslots`, `map_row_moved`),
`label_float_rounding`, the alignment anchors of
`bundle__bundle_matchstamp_cards`, the cross-section lines and the
anchor on a child member of `group__group_child_member_stamps` and the
ancestor lines on both sides of the member of
`group__group_grandchild_parent_on_top`, the derived elisions of
`group__group_elided_inside` and the four `__full` cases, which draw the
same ancestor cards whole, the group elisions of
`group__group_elided_members`, drawn across its frame and carried into the
ancestor card behind it, and the arrangement side by side of
`bundle__bundle_arranged_roots__horizontal`;
`drawings/README.md` lists them with their arithmetic. Every other figure, and every `inputs.json`, is
emitted by TimeLineEditor's writers with `pnpm emit-drawings --into
<TimeToShare checkout>` (run in its `app/packages/writers/`), which
compares the hand-derived SVGs with its own output instead of writing them.
The script refuses to replace the drawings of a version whose tag
`v<version>` exists.

## Rejection coverage

Each rejection case breaks one rule of an accepted manifest and records the
`path` and the `code` any validator must report, the `message` the two
reference packages report, and a `reason`. A rule inside a timeline is
located under the root that holds it, `/timelines/0/…`. Tests in both
packages load the same files and compare the error's path, code and message
with the case's. The `message` is the wording of the two reference
packages, held equal by their suites; another implementation must report
the `code` and the `path`, and may word the message its own way. A `schema`
message is the one Python's `jsonschema` 4.26 gives, each value spelled as
Python's `repr` spells it, but for the shapes both packages word themselves
(the admitted constants of a `oneOf` of constants, a key no value is
admitted at, the part of a string a `not` refuses). The cases cover every
code:

| Code | Rule | Cases |
| --- | --- | --- |
| `not_a_manifest` | the value is an object holding `timetoshare` | `root_missing_marker` |
| `finite_number` | every number is finite | `infinite_length`, `nan_offset` |
| `flow_control_form` | before the schema, no flow-control element is written in the earlier form: the key `type` (`jump_from`, `jump_to`, `flow_marker`), one of those words as `role`, or `target` without `role` | `flow_control_earlier_form`, `flow_control_earlier_role` |
| `schema` | the schema document | 122 cases named after the member they break: units and number types (a number type the unit does not admit: `timeline_ticks_float`, `timeline_seconds_int`, `timeline_quarters_int`), lengths and offsets (a Fraction member with a fractional part, `length_fraction_member_not_integral`, among them), IDs (an empty ID, `id_empty`, and IDs holding a control character, a root ID followed by a newline, `id_control_character_trailing_newline`, among them; an ID that is one of the strings a MatchClaim table writes for a sentinel, `id_chunk_sentinel`; an ID written without its `#`, `id_without_hash` and the one-character `id_without_hash_short`, and a reference written without its `#`, `reference_without_hash`), conversion maps (a map that is no object: `conversion_map_not_object`, `conversion_map_null`, and an output of a `CombinationMap` that is none, `combination_map_member_not_object`), flow control (a role none of the five, `flow_control_role_unknown`; a jump without destinations or with an empty list, `jump_without_targets`, `jump_targets_empty`; a member its role does not admit, `jump_with_manifestation`, `jump_target_with_targets`, `barline_with_ends`; a destination or an `after` with both `to` and `by`, `destination_to_and_by`, `after_to_and_by`; an empty `ends`, `ends_empty`; passes empty, repeated, holding 0 or from 0, `passes_*`; a `repeat_count` of 0, `repeat_count_zero`), FlowMaps and virtual timelines (a gap of 0, `flow_map_gap_zero`; a virtual timeline without `length` or in ticks with fractions, `virtual_timeline_without_length`, `virtual_timeline_ticks_fraction`), MeasureMaps (among them a row's `volta` empty, repeating a pass, 0, holding a negative pass or one that is no integer, `measure_map_row_volta_empty`, `measure_map_row_volta_repeated`, `measure_map_row_volta_zero`, `measure_map_row_volta_member_negative`, `measure_map_row_volta_member_not_integer`), groups, `graphical` selectors (a word of a selector's `coordinates` other than `primary` and `secondary`, `rule_select_coordinates_unknown`, among them), declarations (a word of `label-display` other than `name`, `id` and `label`, `rule_set_label_display_unknown`, among them) and `order`, elisions (a `width` given in two forms, `elision_width_two_forms`, and a `ratio` of 0, `elision_ratio_zero`), 23 cases of statements: a context term altered or missing, a prefix that is no namespace or bears a reserved name (`context_*`); a `type` or a key that is a bare word, a key that is a JSON-LD keyword, an empty container, an empty or repeating value list, a value that is a fractional float or `null`, a `null` in an ordered list, a value object with both a language and a datatype, an empty node and a node whose `id` is a blank-node label (`type_bare_word`, `statement_*`, `statements_empty`, `ordered_values_null`, `value_object_language_and_type`, `value_node_*`); an empty `provenance`, an unknown method or match, a property that is a bare word and a date not written `YYYY-MM-DD` (`provenance_*`), and a belief that is none of the strings `true`, `false` and `unlikely`, a word or the JSON boolean `true` (`belief_value_unknown`, `belief_value_boolean`); and 3 cases of MatchStamps and resources: a word of an anchor's `display` other than `line` and `name` (`alignment_anchor_display_unknown`), a MatchClaim ID listed twice (`matchstamp_claims_repeated`) and a digest whose hash function the PREMIS vocabulary does not name (`resource_integrity_algorithm_unknown`) |
| `representation` | an own-axis value is accepted when its axis's number type reads it exactly, in any terms of a fraction, and is written in the form that number type takes (a bare number on an `int` or a `float` axis, a pair of integers on a `fraction` axis; in the tables the cell members that form fills); another form, or a value the number type cannot hold exactly, is refused; a statement value is never a float | `length_int_on_fraction_axis`, `length_fraction_on_int_axis`, `length_float_on_int_axis`, `float_axis_int_not_exact`, `region_start_float_on_fraction_axis`, `child_offset_fraction_on_float_axis`, `destination_by_int_on_fraction_axis`, `flow_map_gap_int_on_fraction_axis`, `virtual_timeline_length_int_on_fraction_axis`, `statement_value_integral_float` |
| `duplicate_id` | every ID unique across the manifest, that of a map another map holds, of a named timestamp, an elision, a MatchStamp, an alignment anchor, a resource, a FlowMap and a virtual timeline included | `id_duplicate_across_kinds`, `nested_map_id_duplicate`, `timelines_id_duplicate_across_roots`, `timelines_child_id_duplicate_across_roots`, `region_id_duplicate_across_roots`, `region_id_is_timeline_id`, `group_id_duplicate`, `group_id_is_timeline_id`, `group_id_is_descendant_id`, `measure_map_id_is_timeline_id`, `timestamp_id_is_timeline_id`, `elision_id_is_timeline_id`, `alignment_anchor_id_repeated`, `flow_map_id_is_region_id`, `virtual_timeline_id_is_timeline_id` |
| `dangling_target` | a destination's `to` names a jump target, a region or a child of its own timeline or the timeline itself, and an `after` exactly one destination of another jump of the timeline, the element named not rejected; a virtual timeline's `map` names a FlowMap or a conversion map and its `timeline` a timeline or another virtual timeline, never itself; a measure view's `measure_map` an entry of `measure_maps`; and a `#` reference of the statements an element of the manifest | `destination_to_break`, `destination_to_child_jump_target`, `destination_to_rejected_jump_target`, `timelines_root_destination_to_dangling`, `after_jump_unknown`, `after_jump_rejected`, `after_own_jump`, `after_place_missing`, `after_place_unknown`, `after_distance_unknown`, `virtual_timeline_map_unknown`, `virtual_timeline_timeline_unknown`, `virtual_timeline_timeline_itself`, `measure_view_dangling`, `element_value_dangling` |
| `flow_coordinate` | a flow-control element's coordinate, and the place a destination's `by` reaches, lie from 0 to the timeline's known length | `flow_control_coordinate_beyond_length`, `flow_control_coordinate_negative`, `destination_by_beyond_length`, `destination_by_before_start` |
| `jump_repeated` | a root and its descendants have one jump at a position on the root's axis | `jump_repeated` (two on one timeline), `jump_repeated_across_tree` (one on the root, one on a child at the same position) |
| `jump_destination` | the destinations of a jump lie at distinct places | `jump_destinations_same_place`, `jump_destinations_same_distance`, `jump_destinations_both_without_place` |
| `conversion_map` | a map attached to a timeline converts from the timeline's unit, and a map a `PiecewiseMap` or `CombinationMap` holds, or a `ChainMap`'s first map, from its holder's source unit, wherever both are stated; a `TableMap`'s x and y values agree in length and its x values increase strictly; a `PiecewiseMap` has one map fewer than breaks, and its breaks increase strictly | `map_source_unit_mismatch`, `table_map_lengths_differ`, `table_map_x_not_increasing`, `piecewise_map_maps_count`, `piecewise_map_breaks_not_increasing` |
| `child_unit` | a child has its parent's unit | `child_unit_differs` |
| `child_number_type` | a child has its parent's number type, each the declared one or its unit's default | `child_number_type_differs` |
| `child_offset` | a child starts within its parent's known length | `child_offset_beyond_parent` |
| `child_end` | a child ends within its parent's known length | `child_end_beyond_parent` |
| `segment_line` | segments run contiguously from 0 to the line's length, with one `is_segment_line` value | `segment_line_not_from_zero`, `segment_line_gap`, `segment_line_gap_in_later_root`, `segment_line_short_of_length`, `segment_line_segment_flag` |
| `manifest_id` | the manifest's ID is no other ID of the manifest | `manifest_id_is_group_id`, `manifest_id_is_descendant_id`, `manifest_id_is_measure_map_id` |
| `group_member` | a member names a timeline or a virtual timeline of the manifest, and neither contains nor lies inside another member of its group | `member_dangling`, `group_member_flow_map` (a FlowMap's ID), `group_member_virtual_unknown` (beside a virtual timeline), `members_contain_member`, `members_inside_member` |
| `order_key` | a key of `graphical.order` names a group, a timeline or a virtual timeline | `order_unknown_group` |
| `display_order` | a group's display order is a permutation of its members | `group_order_not_member`, `order_missing_member` |
| `band_order` | a band order lists `line` and any of the five facets, each once | `band_order_unknown_entry`, `band_order_missing_line`, `band_order_old_form` |
| `timestamp_timeline` | a named timestamp names a timeline or a virtual timeline of the manifest | `timestamp_timeline_unknown` |
| `timestamp_coordinate` | a named timestamp's coordinate lies from 0 to its timeline's own length, from 0 on where the length is unknown | `timestamp_coordinate_beyond_length`, `timestamp_coordinate_negative` |
| `groupstamp` | a groupstamp, a match timestamp included, lies in a group, its timeline or one of its ancestors being a member (an ancestor of a member lies in none through it) | `groupstamp_without_group`, `groupstamp_child_without_group`, `groupstamp_member_parent`, `groupstamp_match_without_group` |
| `elision_timeline` | an elision names a timeline or a virtual timeline of the manifest | `elision_timeline_unknown` |
| `elision_stretch` | an elision starts at 0 or later, ends within its timeline's known length, and starts before it ends | `elision_end_beyond_length`, `elision_start_not_before_end` |
| `context` | a manifest whose elements carry `statements` or `provenance` holds `@context` | `context_absent_with_statements`, `context_absent_with_provenance` |
| `reserved_key` | no element key is one JSON-LD would read | `reserved_key_term_on_timeline` (`label`), `reserved_key_iri_on_region`, `reserved_key_statements_on_group`, `reserved_key_prefix_on_manifest`, `reserved_key_context_on_timeline`, `reserved_key_children_on_region` |
| `iri` | every compact IRI names a declared prefix, a selector's `class` included (`tts` excepted, the format's namespace in every selector), and every element with statements has an ID that is an IRI fragment | `iri_prefix_undeclared_key`, `iri_prefix_undeclared_id`, `iri_prefix_undeclared_type`, `provenance_basis_prefix_undeclared`, `subject_id_not_fragment`, `iri_prefix_undeclared_selector_class` |
| `element_value` | a value naming an element holds its `id` alone | `element_value_with_label` |
| `calendar_date` | a provenance entry's or a belief's `date` names a day of the Gregorian calendar from 0001-01-01 | `provenance_date_impossible`, `belief_date_impossible` |
| `provenance_duplicate` | a subject has one entry per pair | `provenance_repeated` |
| `belief_actor` | an actor holds at most one belief in an entry, actors compared as IRIs | `belief_actor_repeated` |
| `alignment_anchor` | an alignment anchor names two match timestamps of the manifest, on two timelines | `alignment_anchor_timestamp_unknown`, `alignment_anchor_timestamp_not_match`, `alignment_anchor_one_timeline` |
| `matchstamp` | the alignment anchors of a MatchStamp are one connected set | `matchstamp_not_connected` |
| `match_timestamp` | some MatchStamp names every match timestamp, and no two match timestamps lie on one coordinate | `match_timestamp_in_no_matchstamp`, `match_timestamp_coordinate_repeated` |
| `resource_timeline` | a resource's `timelines` name timelines or virtual timelines of the manifest | `resource_timeline_unknown` |
| `resource_type` | a timeline is listed by at most one resource of each type, every type | `resource_match_claim_twice`, `resource_projection_twice`, `resource_event_timeline_twice` |
| `folder_descriptor` | a resource naming a folder (a `url` ending in `/`) has no `size` and no `integrity` | `resource_folder_size` |
| `flow_map_timeline` | a FlowMap names a root timeline | `flow_map_timeline_child`, `flow_map_timeline_unknown` |
| `flow_map_chunk` | every ID among a FlowMap's chunks names a region, a child timeline or a virtual timeline inside the tree of its root | `flow_map_chunk_unknown`, `flow_map_chunk_other_root`, `flow_map_chunk_root` |
| `flow_map_canonical` | at most one FlowMap of a timeline is canonical | `flow_map_canonical_twice` |
| `virtual_timeline` | a virtual timeline comes, virtual timeline by virtual timeline, from a timeline of the manifest; without `through`, a FlowMap it applies is one of the root of the tree its timeline comes from, and its `length` is the sum of that FlowMap's chunks and gaps where every chunk has a known length on its axis and the axis is not `float` | `virtual_timeline_cycle`, `virtual_timeline_map_other_root`, `virtual_timeline_length_not_the_sum` |
| `flow_rule` | no style sets `flow`; a rule setting it selects the cards of timelines by their addresses alone, and its value names, for each, a FlowMap of that timeline or a virtual timeline applying one to it without `through` | `flow_rule_in_style`, `flow_rule_selector_not_addresses`, `flow_rule_value_region`, `flow_rule_flow_map_of_other_timeline`, `flow_rule_virtual_of_other_timeline` |

Every case of statements starts from one manifest: the format's context
with the prefixes `schema`, `wd` and `wdt` (others where a case says so)
and one root `clt_1` of 8 quarters, in the complete form.

`version_unknown` names the version 0.1.0, which 0.2.0 replaces; its `code` is `null` and its
`"error": "UnsupportedVersionError"` names the error both packages raise
instead. No serialization writes a non-finite number, so the two `finite_number` cases hold
a finite placeholder at their path and name in `non_finite` (`"Infinity"` or
`"NaN"`) the value a test puts there before validating; Python's
`timetoshare.fixtures.rejection_case` reads a case with that value in place.

## Cases of several problems

`fixtures/precedence/<version>/cases.yaml`, hand-authored in canonical
YAML, pins which problem both validators report when a manifest breaks
the schema more than once: the deepest; among problems equally deep, the
one whose path comes first compared element by element (indices by
number, keys by code point); among problems at one path, the first the
walk of `jsonschema` reports, which visits the schemas applied there in
the order the document writes their keywords. Each case names a
`fixture` under `fixtures/<version>/` (its path without extension) and a
list `set` of `{path, value}`, the members a test sets on the fixture as
read, in order, and records the `code`, `path` and `message` reported,
with a `name` and a `reason`:

| Case | Problems | Reported |
| --- | --- | --- |
| `declarations_by_key` | two declarations of `graphical.styles` | the one under `alpha`, before `zeta` |
| `prefixes_by_key` | two prefixes of `@context` that are no namespaces | `aa`, before `zz` |
| `deeper_root_wins` | an unknown unit in the first root, a conversion map `null` in the third | the conversion map, the deeper |
| `timeline_members_by_key` | `locked` and `is_segment_line` no booleans | `is_segment_line` |
| `conversion_maps_by_index` | the conversion maps 3 (`0`) and 1 (`null`) no objects | index 1 |
| `number_type_first_applied` | a number type outside the list of number types and its unit's | the list of number types, which the walk applies first |

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

A warning is never an error. Each of the 19 warning cases under
`fixtures/warnings/<version>/` holds a manifest together with the two lists
both packages must return for it: `unknown_keys`, the `{path, key}`
entries `unknown_keys` and `unknownKeys` return, sorted by path and then by
key, and `warnings`, the `{code, path, message}` entries
`manifest_warnings` and `manifestWarnings` return, sorted by path and then
by code. Three cases hold one warning each and no unknown key:
`context_absent`, a manifest without `@context` (`context_absent` at the
root), and `bundle_blank_statements` and `bundle_blank_provenance`, a
manifest without `id` that carries `statements` or only `provenance`
(`bundle_blank` at that key). `manifestation_unknown` holds three
warnings of that code, at the manifestation of a jump target, of a section
break and of a destination, `convention_unknown` one, at a FlowMap's
`convention`, and `flow_conflict` one, at the `members` of a group two of
whose members' cards rules switch to a FlowMap of each, neither an
unknown key. The other thirteen hold the format's context,
unknown keys and no warning. `several_depths` places unknown keys at every
depth of a manifest; each of the other twelve holds one or two keys its
object does not declare, among them keys a writer might plausibly add,
such as `support_policy`, a timeline's `class`, a selector's former `ids`
or an address's `root`. Python's `warning_paths()` lists the cases. Both
packages read the same files and compare their lists with them.

## Version cases

`fixtures/versions/<case>/` holds the cases of the version
step a change of a repository of manifests requires ([main
README](../README.md#versions-of-a-dataset)): an `old/` and a `new/` tree
of manifests and `expected.yaml`, the `step`, the `scope`, the flags
`refused` and `undetermined`, and the `findings` as `{kind, step, id}` in
the order the report lists them (by path, kind and ID). They are not
versioned by schema version: a case compares two states of data, not two
formats. Every manifest is written in canonical YAML with `dumps` (one
with comment lines added by hand) and validates; every `new/` but four is
one edit of the one base manifest `old/base.yaml`: a quarters score with a
child, three regions, a LinearMap and a flow-control element, a statement
and its provenance with a belief, two seconds takes, a sketch, a group, a
MeasureMap, a FlowMap and the virtual timeline applying it, an audio
resource with its digest, a styling rule, a named timestamp, an elision, a
named MatchStamp with two alignment anchors, and a prefix `ex` beside the
default context. There is one case per rule:

| Case | Change | Step |
| --- | --- | --- |
| `timeline_removed` | the root `sketch` removed | major |
| `child_removed` | the child `movement_2` removed | major |
| `group_removed` | the group `pair` removed | major |
| `measure_map_removed` | the MeasureMap `bars` removed | major |
| `conversion_map_removed` | the LinearMap `tempo` removed | major |
| `flow_control_removed` | the flow-control element `fine` removed | major |
| `flow_map_removed` | the FlowMap `reading` and the virtual timeline `score_read` applying it removed | major |
| `virtual_timeline_removed` | the virtual timeline `score_read` removed | major |
| `resource_removed` | the resource `recording` removed | major |
| `matchstamp_removed` | the named MatchStamp `ms_1` removed, with its anchors and match timestamps | major |
| `anchor_removed` | the anchor `anchor_2` removed, with the match timestamp `ts_m3` only it names | major |
| `member_removed` | `take_1` taken out of the group `pair` | major |
| `member_added` | `sketch` put into the group `pair` | minor |
| `pair_removed` | the statement pair `wdt:P31` of `score` removed | major |
| `pair_replaced` | its value replaced | minor |
| `pair_added` | a pair `wdt:P86` added | minor |
| `prefix_removed` | the prefix `ex` removed from `@context` | major |
| `prefix_added` | a prefix `dcterms` added | minor |
| `prefix_iri_edited` | the IRI of `ex` | minor |
| `offset_edited` | the offset of `movement_2` | minor |
| `unit_edited` | the unit of `sketch` | minor |
| `number_type_edited` | the number type of `sketch`, `float`, its length `8.0` | minor |
| `length_edited` | the length of `sketch` | minor |
| `map_numbers_edited` | the `scalar` of `tempo`, `2.0` to `2.5` | minor |
| `coordinate_edited` | the coordinate of the named timestamp `ts_start` | minor |
| `chunks_edited` | the chunks of `reading`, `coda` to `bridge` | minor |
| `region_added` | a region `region_2` added | minor |
| `belief_added` | a second actor's belief on the provenance of `score` | patch |
| `belief_changed` | the editor's belief changed from `true` to `false` | patch |
| `name_changed` | the `name` of `score` | patch |
| `graphical_rule_changed` | a styling rule's `fill` | patch |
| `elision_added` | an elision `elision_2` added | patch |
| `elision_edited` | the end of `elision_1` | patch |
| `elision_removed` | the elision `elision_1` removed | patch |
| `timestamp_display_edited` | the `display` of `ts_start` | patch |
| `timestamp_removed` | the named timestamp `ts_start` removed | major |
| `meta_changed` | the manifest's `meta` | patch |
| `resource_moved` | the resource's `url`, its `integrity` equal | patch |
| `id_changed` | `sketch` renamed `sketch_a`: a removal and an addition | major |
| `id_reused` | `region_1` removed and its ID given to the timeline `sketch` | refused (and major) |
| `minimal_to_complete` | the minimal form rewritten in the complete form | none |
| `yaml_to_json` | `base.yaml` rewritten as pretty JSON, `base.json` | none |
| `comments_only` | two comment lines added | none |
| `numbers_respelled` | `tempo`'s `scalar` `2.0` as `2` and `offset` `[1, 2]` as `[2, 4]`, a MeasureMap row's `actual_length` `[3, 1]` as `3` | none |
| `manifest_removed` | a second manifest file `sketches.yaml` removed | major |
| `manifest_added` | that file added | minor |

The cases of tables compare packages: an `old/` and a `new/` package,
each a `package.yaml`, the manifest `score.yaml`, a registry folder of a
non-event part and one extraction part, an Extraction table and a pre-parsed
Projection table, the `new/` one edit of the `old/`. Every finding lies at
the manifest whose registry resource lists the row's timeline
(`score.yaml`, scope `score`); the manifests validate and the non-event
parts are not stale. Their YAML files and `expected.yaml` are written by hand,
like every other case; their Parquet files are emitted by
`scripts/emit_versions.py` (run from `python/` as `uv run python
../scripts/emit_versions.py`; it needs pyarrow), whose rows are literal
data in the script, the non-event part of each tree written by
`write_non_event_rows`
from the tree's manifest and tables. It rewrites a Parquet file only when
its table changes and refuses to replace the files while the tag
`v<version>` of the current version exists:

| Case | Change | Findings |
| --- | --- | --- |
| `registry_row_removed` | the event `note_2` removed from its extraction part | `removed_row`, major |
| `registry_row_added` | an event `note_3` added | `added_row`, minor |
| `registry_projection_moved` | the start of the Projection `proj_1` moved | `edited_row`, minor |
| `registry_row_vanished` | the `vanished_in` of `note_2` set | `vanished_row`, minor |
| `registry_non_event_rows_only` | the timeline `score` renamed in the manifest; its non-event row stays as it was, the registry holding no name | `label`, patch (the manifest's finding alone) |
| `projection_row_edited` | the `projection_of` of `proj_1` edited in the pre-parsed table | `edited_row`, minor |
| `projection_row_removed` | `proj_1` removed from the registry and the pre-parsed table | `removed_row` twice, major |

See the [main README](../README.md) for the manifest shape, the schema API
and the serializations.
