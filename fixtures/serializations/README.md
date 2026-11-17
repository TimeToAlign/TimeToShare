# Serialization cases

These cases pin the three serializations of the repository README's
"Serializations" section, and the "Canonical order" a writer applies, to
the byte. Every text here is derived by hand from those sections, never
written with `dumps`, which they test. Both packages must reproduce every
text byte for byte, read every readable text to the value stated, and
refuse every refused text. A case the README does not determine is a
defect of the README; a change to a serialization rule changes the README
and these cases together.

## Layout

| Path | Holds |
| --- | --- |
| `cases/<name>/canonical.yaml` | the canonical YAML of one value |
| `cases/<name>/pretty.json` | the pretty JSON of the same value |
| `cases/<name>/rfc8785.json` | its RFC 8785 JSON, without a final line feed; absent where the RFC 8785 writer refuses the value |
| `readings/<name>.<ext>` | a text that is not canonical and that every reader reads, `<ext>` being `yaml` or `json` |
| `readings/<name>.expected.yaml` | the canonical YAML of the value that text is read as |
| `refusals/<name>.<ext>` | a text that every reader refuses, one rule per text |
| `refusals-writing/<name>.<ext>` | a text every reader reads, whose value a writer refuses in the serializations stated below |

The extension names the language the text was written in, not the
serialization a reader chooses: `refusals/flow_mapping_unquoted_key.yaml`
is meant as YAML and is read as JSON, and `refusals/bom_second_json.json`
is meant as JSON and is read as YAML. Every file is UTF-8, and only the
`readings/bom_*` texts, `refusals/bom_only.yaml` and the two
`refusals/bom_second_*` texts begin with a byte order mark (U+FEFF), the
last two with two. The bytes of every file are significant, final
line feeds included; `refusals/empty.yaml` is empty.

## How a package test uses them

Read each file as bytes and decode it as UTF-8, keeping a leading U+FEFF:
in Python `data.decode("utf-8")` (not `"utf-8-sig"`), in TypeScript
`new TextDecoder("utf-8", { ignoreBOM: true })` or
`readFileSync(path, "utf8")`. "Read" below means the package's reader of
any serialization, which chooses between JSON and YAML as the README's
"Reading" states: Python's `loads`, TypeScript's `loads` (`parse` also
validates, and most values here are not manifests). Values are compared
kind for kind: an integer equals only an integer, a float only a float,
`-0.0` differs from `0.0`, arrays compare in order and objects by their
members.

1. **Cases.** Let V be the value read from `canonical.yaml`.
   - `pretty.json` reads to V.
   - `rfc8785.json` reads to V with every float whose RFC 8785 spelling has
     neither `.` nor an exponent (an integral float of magnitude below
     2^53, a zero of either sign) replaced by the integer of equal value.
   - `dumps(V)` in each serialization gives the bytes of its file; where
     `rfc8785.json` is absent, `dumps(V, "jcs")` raises (Python
     `ValueError`, TypeScript `RangeError`).
   - Each text read and written again in the serialization its file name
     names gives its own bytes.
   - For the manifest cases (`readme_manifest`, `manifest_canonical_order`,
     `manifest_order_by_value`, `manifest_ties_kept`,
     `manifest_display_order`), the value read from
     `rfc8785.json` written in canonical YAML gives the bytes of
     `canonical.yaml`: the declared number types restore the floats RFC
     8785 JSON spells as integers. These cases hold no float off a
     timeline's own axis.
2. **Readings.** `dumps(read(text), "yaml")` gives the bytes of
   `<name>.expected.yaml`, and the expected text read and written again
   gives its own bytes.
3. **Refusals.** Reading the text raises: Python `ValueError`; TypeScript
   `JsonSyntaxError` for a text read as JSON and `YamlSyntaxError` for a
   text read as YAML, except a `RangeError` for a float that rounds to an
   infinity (`json_float_overflow*`, `json_top_level_float_overflow`,
   `yaml_float_overflow*`).
4. **Writer refusals.** The text reads; writing its value raises in each
   serialization the table names, and succeeds in the others: Python
   `ValueError`; TypeScript `RangeError` for a value a serialization
   refuses and `TypeError` for a manifest that cannot be put in canonical
   order (the `order_*` texts).
5. **`serialization_of`** (`serializationOf`) never raises on any file
   here and returns:
   - for `canonical.yaml`: `"json"` for the cases `top_level_empty_object`,
     `top_level_empty_array`, `top_level_integer`, `top_level_float`,
     `top_level_null`, `top_level_true`, `top_level_quoted_string` and
     `top_level_string_yaml_escapes`, whose texts are JSON texts and, ending
     in a line feed, not RFC 8785 JSON; `"yaml"` for every other case;
   - `"json"` for every `pretty.json` and `"jcs"` for every `rfc8785.json`,
     the scalar ones included;
   - for a reading, refusal or writer refusal: `"json"` for every `.json`
     text but `refusals/bom_second_json.json` and for
     `refusals/flow_mapping_unquoted_key.yaml`,
     `refusals/flow_sequence_plain.yaml` and
     `refusals/flow_sequence_then_comment.yaml`, and `"yaml"` for every
     other text (`refusals/empty.yaml`, `refusals/bom_only.yaml` and
     `refusals/bom_second_json.json`, whose first character once the byte
     order mark is removed is a second U+FEFF, included). None of these texts is RFC 8785 JSON: the compact ones are
     unsorted (`readings/json_compact.json`), begin with U+FEFF
     (`readings/bom_rfc8785.json`), or hold values the RFC 8785 writer
     refuses (`refusals-writing/integer_2_53.json`, `key_1025_*.json`).

A lone surrogate standing as itself, which only a text held in memory can
hold, cannot be stored in a UTF-8 file; package tests build such a text in
memory.

## Cases

| Case | Exercises | Rule pinned |
| --- | --- | --- |
| `integers` | 0, a negative integer, ±(2^53 − 1) | Shared spelling: integers; RFC 8785 integer range |
| `integers_beyond_double` | ±2^53, 2^53 + 1, ±2^64 | integers exact at any size; RFC 8785 refuses them (no `rfc8785.json`) |
| `floats` | zero, `-0.0`, integral floats, k = −10, −7, −6, −5, −4, 15, 21, 22, 308, −324, a 17-digit value, a 17-digit tie broken to the even digit (1234567890123456.75 → `…56.8`) | float algorithm steps 1–4; RFC 8785 number spelling at k = −7, −6, 20 < k |
| `floats_integral_large` | integral floats 2^53, 10^16, 1.5 × 10^16, 12345678901234568, 10^20 (k = 15, 16, 20) | exponent form from k = 16; RFC 8785 refuses an integral float of magnitude from 2^53 below 10^21 (no `rfc8785.json`) |
| `floats_integral_safe` | integral floats ±(2^53 − 1) | the largest integral floats RFC 8785 JSON writes, as integers' digits |
| `string_values` | plain and quoted strings at every edge of the plain rule: each reserved word in several cases, `_x`, `_`, `a/b`, `a.b`, `a-b`, `1a`, `-a`, `""`, `" "`, `#`, `:`, a URI, `NaN`, `e5`; long scalar sequences | Canonical YAML: plain or double-quoted strings |
| `string_keys` | the same edges as keys, sorted by code point after unquoting | plain and quoted keys; key order |
| `escapes` | U+0000, U+0008–U+000D, U+001B, U+001F, U+007F, U+0085, U+009F, U+00A0, U+2028, U+2029, U+E000, U+FEFF, U+FFFD, U+FFFE, U+FFFF, `"`, `\`, `/`, a non-BMP character | the escapes of canonical YAML and of JSON |
| `key_escapes` | escaped keys; U+FEFF beside U+1F600 | key escapes; code-point order against UTF-16 order |
| `key_order_utf16` | keys `z`, U+E000, U+FF61, U+1F600 | RFC 8785 sorts by UTF-16 code units |
| `empty_collections` | `[]` and `{}` as values, in a sequence, beside a scalar | empty collections; a sequence holding one is a block sequence |
| `top_level_empty_object`, `top_level_empty_array` | `{}` and `[]` alone | top level; canonical YAML texts that are JSON texts read as JSON |
| `top_level_scalar_sequence` | a top-level array of scalars | top-level arrays are block sequences in canonical YAML |
| `top_level_block_sequence` | a top-level array holding an object and a nested block sequence | `-` alone before a non-empty mapping or block sequence |
| `top_level_integer`, `top_level_float`, `top_level_null`, `top_level_true`, `top_level_plain_string`, `top_level_quoted_string` | a scalar alone | a top-level scalar stands alone on the one line; a scalar that is a JSON text is read as JSON, a plain string as YAML |
| `top_level_string_yaml_escapes` | the string `x`, U+007F, U+0085, U+2028, U+FFFE, `y` alone | canonical YAML escapes what pretty and RFC 8785 JSON write as itself; a scalar that is a JSON text is read as JSON, even one holding characters YAML refuses |
| `readme_nesting_example` | the nesting example of the README | block sequences, nested objects, `{}` |
| `nested_sequences` | three levels of block sequences, a mapping inside a sequence inside a mapping, `[[]]` | indentation at c + 2 |
| `scalar_sequences` | a 60-item line, mixed scalars, a one-item sequence | scalar sequences on one line however long |
| `fractions` | Fraction pairs, negative and zero, a sequence of pairs | a Fraction pair is a scalar sequence |
| `key_length_1024_plain` | a plain key of 1024 characters | the key limit, reached and not exceeded |
| `key_length_1024_quoted` | a key whose quoted, escaped form is 1024 UTF-16 code units | quotes and escapes count |
| `key_length_1024_non_bmp` | 511 characters above U+FFFF: 1024 UTF-16 code units quoted | non-BMP characters count two units |
| `embedded_manifest_kept` | a value holding a manifest that is not itself one | arrays of a value that is not a manifest keep their order |
| `readme_manifest` | the manifest of "One manifest in three serializations" | the README's three texts and their byte counts (canonical YAML 259 bytes, pretty JSON 380, RFC 8785 JSON 242) |
| `manifest_canonical_order` | timelines, nested children, conversion maps, a ChainMap's maps (kept), flow control, regions, groups and members, named timestamps and their `display`, `graphical.order` (kept) | canonical order; ties broken by ID in code-point order (`region_10` before `region_2`) |
| `manifest_order_by_value` | children at 3/10 before 1/3, regions and flow control at 9.5 before 10.0, timestamps at 9 before 10, a child at the Fraction pair 1/10 before one at the float 0.1 (whose exact value is greater) on a `float` axis; `measure_maps` and `schemes` by ID; MeasureMap rows and the manifest's `links` kept | coordinates compare by exact numeric value, never by spelling; a value its number type cannot take is written as given |
| `manifest_ties_kept` | duplicate IDs: two timelines, groups, children, conversion maps, regions, flow-control elements, and two named timestamps at `[1, 2]` and `0.5` on a `float` axis, each pair tying on every member it is ordered by and given `Second` before `First` | entries that tie keep their given order |
| `manifest_display_order` | a named timestamp whose `display` holds the five known words, the strings `"2"`, `Alpha`, `Wedge`, `label` and `zeta`, and the values `2`, `null` and `1` | a `display` in canonical order: the known words in their order, other strings by code point, then other values in their given order |

## Readings

| Reading | Exercises | Rule pinned |
| --- | --- | --- |
| `bom_yaml` | U+FEFF before a YAML text | a leading byte order mark is ignored; `serialization_of` gives `"yaml"` |
| `bom_pretty_json` | U+FEFF before pretty JSON | the same; `"json"` |
| `bom_rfc8785` | U+FEFF before RFC 8785 JSON | the same; `"json"`, since the text is not byte for byte RFC 8785 JSON |
| `json_bom_in_string` | a literal U+FEFF inside a JSON string | in JSON a U+FEFF inside a string is content; written `\ufeff` in canonical YAML |
| `yaml_flow_style` | flow collections not at the first character, single quotes | Reading: YAML in any style |
| `yaml_single_quoted` | `''`, `'it''s'`, quoted `null` and `12` | a quoted scalar is a string |
| `yaml_block_scalars` | `\|`, `>`, `\|+`, `\|-`, `\|2` | block scalars; their chomping |
| `yaml_comments` | comments on every kind of line | comments are ignored |
| `yaml_indentation` | four-space indentation, sequences not indented under their key | any layout |
| `yaml_document_markers` | `---` and `...` | an explicit document start and end |
| `yaml_document_start_only` | `---` alone | one document whose value is null |
| `yaml_directive` | `%YAML 1.2` | the one directive read |
| `yaml_core_schema` | every core-schema null and boolean spelling, `+12`, `007`, `0o17`, `0x1F`, `-0`, `.5`, `1.`, `1e5`, `+2.5`, `-0.0`, rounding to the nearest double; and plain scalars that stay strings: `yes`, `On`, `y`, `2001-12-14`, `1:20`, `1_000`, `0b101`, `-0x10`, `.Nan`, `inf`, `.` | the core-schema resolution the README states, not YAML 1.1's |
| `yaml_double_quoted_escapes` | `\a`, `\e`, `\x41`, `\U0001F600`, `\0`, `\N`, `\_`, `\L`, `\P`, `\/`, `\ `, `\v`, upper-case hex, a literal tab, an escaped line break, a folded line | YAML double-quoted scalars |
| `yaml_tab` | a literal tab in a comment, a double-quoted and a single-quoted scalar | the tab is not among the characters a YAML text refuses |
| `yaml_tab_plain` | a literal tab inside a plain scalar, `x<tab>y` | the same in a plain scalar, which YAML 1.2 allows to hold a tab between two of its characters |
| `yaml_refused_characters_escaped` | U+0001, U+001F, U+007F, U+0080, U+0085, U+009F, U+2028, U+FFFE and U+FFFF written as the escapes `\x01`, `\u001F`, `\x7F`, `\u0080`, `\x85`, `\x9f`, `\u2028`, `\uFFFE` and `\U0000FFFF` | a character refused standing as itself is read through an escape; written `\u` and four lower-case digits |
| `yaml_surrogate_pair_escape` | `\ud83d\ude00` and `\uD83D\uDE00` in YAML | a high-surrogate escape followed by a low-surrogate escape is one character |
| `yaml_plain_multiline` | a plain scalar over three lines | plain-scalar folding |
| `yaml_crlf` | CR LF line ends, in a quoted and a literal scalar | line breaks read as line feeds |
| `yaml_comment_before_flow` | a JSON-like text after a comment | neither `{` nor `[` first, and not a JSON text: read as YAML |
| `yaml_document_start_flow` | `--- [1, {a: b}]` | the same, after a document start |
| `yaml_quoted_first_key` | `"b": 1` then `a: 2` | a mapping whose first key is quoted is not a JSON text: read as YAML |
| `yaml_explicit_key` | `? key` | explicit keys |
| `yaml_implicit_key_1023_then_space` | an implicit key of 1023 characters followed by a space and `:` | the key limit counts from the key's first character to its `:`, the space included: a span of 1024 is read |
| `yaml_unsorted_keys` | unsorted keys, a plain key `y` | keys sorted when written; `y` is the string `"y"` under YAML 1.2 |
| `yaml_top_level_quoted_scalar` | `'480'` | a top-level quoted scalar is a string; not a JSON text |
| `yaml_top_level_yaml_escape` | `"\x41"` alone | a double-quoted scalar with an escape JSON lacks is not a JSON text: read as YAML |
| `yaml_top_level_tilde` | `~` alone | not a JSON text: read as YAML, null |
| `yaml_top_level_minus_infinity` | `-Infinity` alone | not a JSON text: read as YAML, where it is a plain string |
| `yaml_float_edges` | `1.7976931348623158e308`, `1e-400` | a float rounding to the largest double, and one underflowing to 0.0, are read |
| `yaml_float_underflow_negative` | `-1e-400` | a negative float underflowing to zero is read as `-0.0` |
| `manifest_unsorted` | `manifest_canonical_order` with every reorderable array shuffled, in flow style | canonical order applied by the writer |
| `manifest_respelled` | `2.0` on an `int` axis, `2` on a `float` axis, `[33, 2.0]`, a child's `offset`, a region, a flow-control coordinate, a root's `offset`, a `number_type` overriding the unit's default | own-axis values respelled as their number type selects |
| `manifest_fraction_reduced` | `[64, 2]`, `[4, 8]`, `[4.0, 2]`, `[6.0, 4.0]`, `[0, 5]`, `[-6, 4]`, `[0, 3]`; a child whose `number_type` is `float` under a `fraction` parent | Fraction pairs reduced to lowest terms, members integers; a child's `offset` takes the parent's number type, its `length` its own |
| `manifest_respelled_edges` | `-0.0` and `1.0e+20` on an `int` axis, 2^53 on a `float` axis | an integral float on an `int` axis written as the integer of its exact value; an integer a float equals written as that float |
| `manifest_written_as_given` | `2.5` and `[1, 2]` on an `int` axis; 2^53 + 1 and `[4, 8]` on a `float` axis; `2`, `2.0`, `[1, 2.5]`, `[3, -2]` and `[1, 0]` on a `fraction` axis; an unknown `unit` (with a child) and an unknown `number_type` | a value its number type cannot take, and every value on an axis whose unit or number type is unknown, is written as given |
| `manifest_timestamp_respelled` | named-timestamp coordinates `3` on a `float` axis, `3.0` on an `int` axis, `[2, 4]` on a child's `fraction` axis | named-timestamp coordinates are own-axis values of the timeline they name, at any depth |
| `timelines_without_version` | an object whose `timelines` is an array, without `timetoshare`, with values to respell | it is a manifest: its timelines are ordered and its own-axis values respelled |
| `embedded_manifest_unsorted` | a manifest inside a value that is not one, with unsorted keys, unordered timelines and values a manifest would respell | of an embedded manifest only the keys are sorted |
| `manifest_display_unsorted` | `manifest_display_order` with its `display` shuffled, the non-strings kept in their order, and the coordinate `1` | a `display` put in canonical order by the writer |
| `manifest_children_not_array` | `children: x`, `regions: 7`, `flow_control: {}` and `groups: g` | a member that should hold an ordered array but holds no array is written as given |
| `manifest_fraction_integral_float` | children at `[1, 8.0]` and `[1, 4]` on a `fraction` axis; regions at `[1, 8.0]` and 0.25, flow control at `[3.0, 16]` and 0.15, on a `float` axis | a Fraction pair with an integral float member counts as the pair of integers it equals: ordered by its value, reduced on a `fraction` axis and written as given on a `float` axis |
| `manifest_unit_missing` | a root without `unit` holding a child in `quarters`, and a root without `unit` whose `number_type` is `int` | a missing `unit` is unknown: the root's values and the child's `offset` written as given, the child's `length` respelled on its own axis |
| `manifest_unit_not_string` | `unit: 1`, and `unit: [seconds]` beside `number_type: float` | a `unit` that is not a string is unknown, whatever the `number_type` |
| `manifest_number_type_not_string` | `number_type` `1`, `null` and `[fraction]` | a `number_type` that is not a string, `null` included, is unknown |
| `manifest_number_type_missing` | roots in `samples` and in `quarters` with `number_type: float`, the latter holding a child in `quarters` without `number_type` | a missing `number_type` is the unit's default, so values are respelled; a child's `offset` takes the parent's number type, its `length` its unit's default |
| `manifest_timestamp_timeline_duplicate` | two timelines `score` in `quarters` and two `take` in `seconds`; named timestamps on `score` at `[2, 4]`, on `take` at `3`, and on the single timeline `perf` at `1` | a timestamp whose `timeline` names more than one timeline has its coordinate written as given, still ordered by value; timelines of equal ID keep their given order |
| `manifest_timestamp_timeline_unknown` | named timestamps on `ghost`, which no timeline is, at `[4, 8]`, `2` and `0.25`, and one on `perf` at `1` | a timestamp whose `timeline` names no timeline has its coordinate written as given, still ordered by value |
| `json_compact` | JSON without whitespace, keys unsorted | JSON in any layout |
| `json_whitespace` | tabs, CR LF, spaces around tokens, leading whitespace | the first-character rule skips whitespace |
| `json_escapes` | `\/`, `\u00e9`, `\u00E9`, a surrogate pair `\ud83d\ude00`, `\u0041`, `\u0009`, `\u007f`, `\ufeff`, `\u0085` | JSON escapes read; written in canonical form |
| `json_numbers` | `1E2`, `-0`, `1.50`, `0.1e1`, `1e-5`, 2^64, `-0.0`, `4.9e-324`, `10E-1`, `1e+2` | a number without `.`, `e`, `E` is an integer; every other a float |
| `json_float_edges` | `1.7976931348623158e308`, `1e-400` | as `yaml_float_edges`, in JSON |
| `json_float_underflow_negative` | `-1e-400` | as `yaml_float_underflow_negative`, in JSON |

## Refusals

| Text | Reason |
| --- | --- |
| `empty.yaml` | holds no document: an empty text |
| `bom_only.yaml` | holds no document: U+FEFF alone, an empty text once it is ignored |
| `bom_second_yaml.yaml` | two U+FEFF before `a: 1`: only the first is removed, and YAML refuses the second |
| `bom_second_json.json` | two U+FEFF before `{"a": 1}`: once the first is removed, the first character is U+FEFF, neither `{` nor `[`, and the text is not a JSON text; read as YAML, which refuses the U+FEFF; `serialization_of` gives `"yaml"` |
| `whitespace_only.yaml` | holds no document: whitespace only |
| `comments_only.yaml` | holds no document: comments only |
| `yaml_document_end_only.yaml` | holds no document: `...` alone |
| `yaml_duplicate_key.yaml` | a key repeats in its object |
| `yaml_duplicate_key_quoted.yaml` | a key repeats, once plain and once single-quoted |
| `yaml_duplicate_key_escaped.yaml` | a key repeats, once through the escape `\u0061` |
| `yaml_duplicate_key_nested.yaml` | a key repeats in a nested object |
| `yaml_duplicate_key_flow.yaml` | a key repeats in a flow mapping |
| `yaml_lone_surrogate_high.yaml` | a lone high surrogate through an escape |
| `yaml_lone_surrogate_low.yaml` | a lone low surrogate through an escape |
| `yaml_lone_surrogate_reversed.yaml` | a low-surrogate escape before a high-surrogate one pairs neither |
| `yaml_lone_surrogate_32bit_escape.yaml` | a surrogate through the escape `\U0000D800` |
| `yaml_lone_surrogate_key.yaml` | a lone surrogate in a key |
| `yaml_nel_in_string.yaml` | a literal U+0085 in a YAML text |
| `yaml_nel_in_comment.yaml` | a literal U+0085 in a YAML text, inside a comment |
| `yaml_ls_in_string.yaml` | a literal U+2028 in a YAML text |
| `yaml_ps_in_string.yaml` | a literal U+2029 in a YAML text |
| `yaml_ls_in_comment.yaml` | a literal U+2028 in a YAML text, inside a comment |
| `yaml_bom_in_string.yaml` | a literal U+FEFF not at the start of a YAML text, inside a double-quoted scalar |
| `yaml_bom_in_comment.yaml` | a literal U+FEFF not at the start of a YAML text, inside a comment |
| `yaml_bom_in_plain.yaml` | a literal U+FEFF not at the start of a YAML text, inside a plain scalar |
| `yaml_u0001_in_string.yaml` | a literal U+0001, a C0 control, in a YAML text |
| `yaml_u001f_in_string.yaml` | a literal U+001F, the last C0 control, in a YAML text |
| `yaml_del_in_string.yaml` | a literal U+007F in a YAML text |
| `yaml_u0080_in_string.yaml` | a literal U+0080 in a YAML text |
| `yaml_u009f_in_string.yaml` | a literal U+009F in a YAML text |
| `yaml_ufffe_in_string.yaml` | a literal U+FFFE in a YAML text |
| `yaml_uffff_in_string.yaml` | a literal U+FFFF in a YAML text |
| `yaml_directive_1_1.yaml` | the directive `%YAML 1.1` |
| `yaml_directive_tag.yaml` | a `%TAG` directive |
| `yaml_directive_reserved.yaml` | a reserved directive |
| `yaml_anchor.yaml` | an anchor |
| `yaml_alias.yaml` | an alias |
| `yaml_tag_core.yaml` | an explicit tag `!!str` |
| `yaml_tag_local.yaml` | an explicit local tag |
| `yaml_tag_non_specific.yaml` | an explicit non-specific tag `!` |
| `yaml_two_documents.yaml` | more than one document |
| `yaml_key_integer.yaml` | a key that is an integer |
| `yaml_key_float.yaml` | a key that is a float |
| `yaml_key_null.yaml` | a key that is `null` |
| `yaml_key_tilde.yaml` | a key that is `~`, null |
| `yaml_key_empty.yaml` | an empty key, null |
| `yaml_key_true.yaml` | a key that is a boolean |
| `yaml_key_collection.yaml` | a key that is a collection |
| `yaml_nan_lower.yaml`, `yaml_nan_title.yaml`, `yaml_nan_upper.yaml` | `.nan`, `.NaN`, `.NAN` (one file each) |
| `yaml_inf_lower.yaml`, `yaml_inf_title.yaml`, `yaml_inf_upper.yaml` | `.inf`, `.Inf`, `.INF` (one file each) |
| `yaml_inf_plus_lower.yaml`, `yaml_inf_plus_title.yaml`, `yaml_inf_plus_upper.yaml` | `+.inf`, `+.Inf`, `+.INF` (one file each) |
| `yaml_inf_minus_lower.yaml`, `yaml_inf_minus_title.yaml`, `yaml_inf_minus_upper.yaml` | `-.inf`, `-.Inf`, `-.INF` (one file each) |
| `yaml_float_overflow.yaml` | a float that rounds to an infinity, `1e309` |
| `yaml_float_overflow_negative.yaml` | a negative float that rounds to an infinity |
| `yaml_float_overflow_above_largest.yaml` | `1.7976931348623159e308`, beyond the midpoint between the largest double and 2^1024 |
| `yaml_implicit_key_1025.yaml` | an implicit key of 1025 characters |
| `yaml_implicit_key_1024_then_space.yaml` | an implicit key of 1024 characters followed by a space and `:`, a span of 1025 to the `:` |
| `yaml_flow_mapping_key_1025.yaml` | an implicit key of 1025 characters in a flow mapping, `k: {a…a: 1}` |
| `yaml_implicit_key_1025_as_written.yaml` | an implicit key of 1025 characters as written (255 escapes `\x41`, three letters and the quotes) whose value has 258 |
| `flow_mapping_unquoted_key.yaml` | YAML flow style from the first character is read as JSON, and `{a: 1}` is not JSON |
| `flow_sequence_plain.yaml` | the same for `[a, b]` |
| `flow_sequence_then_comment.yaml` | read as JSON, and a comment is not JSON |
| `json_duplicate_key.json` | a key repeats in its object |
| `json_duplicate_key_escaped.json` | a key repeats, once through the escape `\u0061` |
| `json_duplicate_key_nested.json` | a key repeats in an object inside an array |
| `json_lone_surrogate_high.json` | a lone high surrogate through an escape |
| `json_lone_surrogate_low.json` | a lone low surrogate through an escape |
| `json_lone_surrogate_reversed.json` | a low-surrogate escape before a high-surrogate one pairs neither |
| `json_lone_surrogate_then_letter.json` | a high-surrogate escape followed by a letter |
| `json_lone_surrogate_key.json` | a lone surrogate in a key |
| `json_u0001_in_string.json` | a literal U+0001, a C0 control, inside a JSON string |
| `json_nan.json` | `NaN` |
| `json_infinity.json` | `Infinity` |
| `json_negative_infinity.json` | `-Infinity` |
| `json_float_overflow.json` | a float that rounds to an infinity, `1e309` |
| `json_float_overflow_negative.json` | a negative float that rounds to an infinity |
| `json_float_overflow_above_largest.json` | `1.7976931348623159e308`, as in YAML |
| `json_top_level_float_overflow.json` | `1e309` alone: a JSON text, read as JSON and refused |
| `json_two_values.json` | not one JSON value: two |
| `json_trailing_comma.json` | not JSON: a trailing comma |
| `json_single_quotes.json` | not JSON: a single-quoted string |
| `json_unclosed.json` | not JSON: an unclosed object |
| `json_comment.json` | not JSON: a comment |
| `json_bom_between_tokens.json` | U+FEFF between `{` and a key: read as JSON, which refuses it outside a string |
| `json_bom_after_value.json` | U+FEFF after `{"a": 1}`: read as JSON, which refuses it outside a string |

## Writer refusals

| Text | Refused in | Reason |
| --- | --- | --- |
| `key_1025_plain.json` | `yaml`, `json`, `jcs` | a plain key of 1025 characters |
| `key_1025_quoted.json` | `yaml`, `json`, `jcs` | a key whose quoted form `"\t…"` is 1025 UTF-16 code units |
| `key_1025_utf16_units.json` | `yaml`, `json`, `jcs` | a key of 512 characters whose quoted form is 1025 UTF-16 code units |
| `key_1024_code_points_non_bmp.yaml` | `yaml`, `json`, `jcs` | an implicit key of 1024 characters that readers accept, whose quoted form is 2046 UTF-16 code units |
| `key_1025_nested.yaml` | `yaml`, `json`, `jcs` | an explicit key of 1025 characters inside an object |
| `integer_2_53.json` | `jcs` | the integer 2^53 |
| `integer_minus_2_53.yaml` | `jcs` | the integer −2^53 |
| `integer_2_64.yaml` | `jcs` | the integer 2^64 |
| `float_2_53.yaml` | `jcs` | the integral float 2^53, which RFC 8785 JSON spells as an integer |
| `float_minus_1e16.yaml` | `jcs` | the integral float −10^16 |
| `float_1e20.json` | `jcs` | the integral float 10^20 |
| `float_below_1e21.yaml` | `jcs` | the integral float 10^21 − 2^17, the largest double below 10^21 |
| `order_entry_not_object.yaml` | `yaml`, `json`, `jcs` | an entry of `timelines` that is not an object |
| `order_entries_not_objects_without_version.json` | `yaml`, `json`, `jcs` | `{"timelines": ["b", "a"]}`: without `timetoshare` still a manifest, whose `timelines` entries are not objects |
| `order_member_missing.yaml` | `yaml`, `json`, `jcs` | a child without the `offset` children are ordered by |
| `order_member_wrong_type.yaml` | `yaml`, `json`, `jcs` | a region whose `start` is a string |
| `order_id_wrong_type.yaml` | `yaml`, `json`, `jcs` | a timeline whose `id` is an integer |
| `order_timestamp_timeline_not_string.yaml` | `yaml`, `json`, `jcs` | a named timestamp whose `timeline` is an integer |
| `order_group_member_not_string.yaml` | `yaml`, `json`, `jcs` | a group whose `members` holds an integer |
| `order_coordinate_zero_denominator.yaml` | `yaml`, `json`, `jcs` | a region whose `start` is `[1, 0]`, a pair whose denominator is below 1 |
| `order_coordinate_three_members.yaml` | `yaml`, `json`, `jcs` | a child whose `offset` is `[1, 2, 3]`, neither a number nor a pair |
| `order_coordinate_boolean.yaml` | `yaml`, `json`, `jcs` | a flow-control element whose `coordinate` is `true` |
