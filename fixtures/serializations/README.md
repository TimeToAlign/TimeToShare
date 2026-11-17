# Serialization cases

These cases pin the three serializations of the repository README's
"Serializations" section to the byte. Every text here is derived by hand
from that section, never written with `dumps`, which they test. Both
packages must reproduce every text byte for byte, read every readable text
to the value stated, and refuse every refused text. A case the README does
not determine is a defect of the README; a change to a serialization rule
changes the README and these cases together.

## Layout

| Path | Holds |
| --- | --- |
| `cases/<name>/canonical.yaml` | the canonical YAML of one value |
| `cases/<name>/pretty.json` | the pretty JSON of the same value |
| `cases/<name>/rfc8785.json` | its RFC 8785 JSON, without a final line feed; absent where the RFC 8785 writer refuses the value |
| `readings/<name>.yaml`, `readings/<name>.json` | a text that is not canonical and that a reader must accept |
| `readings/<name>.expected.yaml` | the canonical YAML of the value that text is written as |
| `refusals/<name>.yaml`, `refusals/<name>.json` | a text that every reader refuses, one rule per text |
| `refusals-writing/<name>.yaml`, `refusals-writing/<name>.json` | a readable text whose value a writer refuses in the serializations stated below |

The extension names the language the text was written in, not the
serialization a reader detects: `refusals/flow_mapping_unquoted_key.yaml`
is meant as YAML and is read as JSON. Every file is UTF-8 without a byte
order mark. The bytes of every file are significant, final line feeds
included; `refusals/empty.yaml` is empty.

## How a package test uses them

Read each file as bytes and decode it as UTF-8. "Read" below means the
package's reader of any serialization: Python's `loads`; in TypeScript
`parseJson` for a text whose first character other than a space, a tab, a
line feed or a carriage return is `{` or `[`, and `parseYaml` for every
other text (`parse` also validates, and most values here are not
manifests). Values are compared kind for kind: an integer equals only an
integer, a float only a float, `-0.0` differs from `0.0`, arrays compare
in order and objects by their members.

1. **Cases.** Let V be the value read from `canonical.yaml`.
   - `pretty.json` reads to V.
   - `rfc8785.json` reads to V with every float whose RFC 8785 spelling has
     neither `.` nor an exponent (an integral float of magnitude below
     10^21, a zero of either sign) replaced by the integer of equal value.
   - `dumps(V)` in each serialization gives the bytes of its file; where
     `rfc8785.json` is absent, `dumps(V, "jcs")` raises (Python
     `ValueError`, TypeScript `RangeError`).
   - Each text read and written again in the serialization its file name
     names gives its own bytes.
   - For the manifest cases (`readme_manifest`, `manifest_canonical_order`),
     the value read from `rfc8785.json` written in canonical YAML gives the
     bytes of `canonical.yaml`: the declared number types restore the
     floats RFC 8785 JSON spells as integers.
2. **Readings.** `dumps(read(text), "yaml")` gives the bytes of
   `<name>.expected.yaml`, and the expected text read and written again
   gives its own bytes.
3. **Refusals.** Reading the text raises (Python `ValueError`; TypeScript
   `JsonSyntaxError`, `YamlSyntaxError` or, for a float beyond the range of
   a double, `RangeError`).
4. **Writer refusals.** The text reads; writing its value raises in each
   serialization the table names, and succeeds in the others.
5. **`serialization_of`** (`serializationOf`) never raises on any file
   here and returns:
   - `"json"` for `cases/top_level_empty_object/canonical.yaml` and
     `cases/top_level_empty_array/canonical.yaml`, `"yaml"` for every other
     `canonical.yaml`;
   - `"yaml"` for `pretty.json` and `rfc8785.json` of the five
     `top_level_*` cases holding a scalar (their texts do not begin with
     `{` or `[`); otherwise `"json"` for every `pretty.json` and `"jcs"` for
     every `rfc8785.json`;
   - for a reading, refusal or writer refusal: `"yaml"` when the text's
     first character other than a space, a tab, a line feed or a carriage
     return is neither `{` nor `[` (the empty text included), and `"json"`
     otherwise. No such text is RFC 8785 JSON: the compact texts in
     `refusals-writing/` hold values the RFC 8785 writer refuses, and so
     are `"json"`.

## Cases

| Case | Exercises | Rule pinned |
| --- | --- | --- |
| `integers` | 0, a negative integer, ±(2^53 − 1) | Shared spelling: integers; RFC 8785 integer range |
| `integers_beyond_double` | ±2^53, 2^53 + 1, ±2^64 | integers exact at any size; RFC 8785 refuses them (no `rfc8785.json`) |
| `floats` | zero, `-0.0`, integral floats, k = −10, −7, −6, −5, −4, 15, 21, 22, 308, −324, a 17-digit value, a 17-digit tie broken to the even digit (1234567890123456.75 → `…56.8`) | float algorithm steps 1–4; RFC 8785 number spelling at k = −7, −6, 20 < k |
| `floats_integral_large` | integral floats 2^53, 10^16, 1.5 × 10^16, 12345678901234568, 10^20 (k = 15, 16, 20) | exponent form from k = 16; RFC 8785 refuses an integral float outside ±(2^53 − 1) below 10^21 (no `rfc8785.json`) |
| `string_values` | plain and quoted strings at every edge of the plain rule: each reserved word in several cases, `_x`, `_`, `a/b`, `a.b`, `a-b`, `1a`, `-a`, `""`, `" "`, `#`, `:`, a URI, `NaN`, `e5`; long scalar sequences | Canonical YAML: plain or double-quoted strings |
| `string_keys` | the same edges as keys, sorted by code point after unquoting | plain and quoted keys; key order |
| `escapes` | U+0000, U+0008–U+000D, U+001B, U+001F, U+007F, U+0085, U+009F, U+00A0, U+2028, U+2029, U+E000, U+FEFF, U+FFFD, U+FFFE, U+FFFF, `"`, `\`, `/`, a non-BMP character | the escapes of canonical YAML and of JSON |
| `key_escapes` | escaped keys; U+FEFF beside U+1F600 | key escapes; code-point order against UTF-16 order |
| `key_order_utf16` | keys `z`, U+E000, U+FF61, U+1F600 | RFC 8785 sorts by UTF-16 code units |
| `empty_collections` | `[]` and `{}` as values, in a sequence, beside a scalar | empty collections; a sequence holding one is a block sequence |
| `top_level_empty_object`, `top_level_empty_array` | `{}` and `[]` alone | top level; the canonical YAML texts that are JSON |
| `top_level_scalar_sequence` | a top-level array of scalars | top-level arrays are block sequences in canonical YAML |
| `top_level_block_sequence` | a top-level array holding an object and a nested block sequence | `-` alone before a non-empty mapping or block sequence |
| `top_level_integer`, `top_level_float`, `top_level_null`, `top_level_plain_string`, `top_level_quoted_string` | a scalar alone | a top-level scalar stands alone on the one line |
| `readme_nesting_example` | the nesting example of the README | block sequences, nested objects, `{}` |
| `nested_sequences` | three levels of block sequences, a mapping inside a sequence inside a mapping, `[[]]` | indentation at c + 2 |
| `scalar_sequences` | a 60-item line, mixed scalars, a one-item sequence | scalar sequences on one line however long |
| `fractions` | Fraction pairs, negative and zero, a sequence of pairs | a Fraction pair is a scalar sequence |
| `key_length_1024_plain` | a plain key of 1024 characters | the key limit, reached and not exceeded |
| `key_length_1024_quoted` | a key whose quoted, escaped form is 1024 UTF-16 code units | quotes and escapes count |
| `key_length_1024_non_bmp` | 511 characters above U+FFFF: 1024 UTF-16 code units quoted | non-BMP characters count two units |
| `embedded_manifest_kept` | a value holding a manifest that is not itself one | arrays of a value that is not a manifest keep their order |
| `readme_manifest` | the manifest of "One manifest in three serializations" | the README's three texts and their byte counts (canonical YAML 259 bytes in the layout of this directory, pretty JSON 380, RFC 8785 JSON 242) |
| `manifest_canonical_order` | timelines, nested children, conversion maps, a ChainMap's maps (kept), flow control, regions, groups and members, named timestamps and their `display`, `graphical.order` (kept) | canonical order; ties broken by ID in code-point order (`region_10` before `region_2`) |

## Readings

| Reading | Exercises | Rule pinned |
| --- | --- | --- |
| `yaml_flow_style` | flow collections not at the first character, single quotes | Reading: YAML in any style |
| `yaml_single_quoted` | `''`, `'it''s'`, quoted `null` and `12` | a quoted scalar is a string |
| `yaml_block_scalars` | `\|`, `>`, `\|+`, `\|-`, `\|2` | block scalars; their chomping |
| `yaml_comments` | comments on every kind of line | comments are ignored |
| `yaml_indentation` | four-space indentation, sequences not indented under their key | any layout |
| `yaml_document_markers` | `---` and `...` | an explicit document start and end |
| `yaml_directive` | `%YAML 1.2` | any valid YAML 1.2 |
| `yaml_core_schema` | every core-schema null and boolean spelling, `+12`, `007`, `0o17`, `0x1F`, `-0`, `.5`, `1.`, `1e5`, `+2.5`, `-0.0`, rounding to the nearest double; and plain scalars that stay strings: `yes`, `On`, `y`, `2001-12-14`, `1:20`, `1_000`, `0b101`, `-0x10`, `.Nan`, `inf`, `.` | the core-schema resolution the README states, not YAML 1.1's |
| `yaml_double_quoted_escapes` | `\a`, `\e`, `\x41`, `\U0001F600`, `\0`, `\N`, `\_`, `\L`, `\P`, `\/`, `\ `, `\v`, upper-case hex, a literal tab, an escaped line break, a folded line | YAML double-quoted scalars |
| `yaml_surrogate_pair_escape` | `😀` in YAML | a high-surrogate escape followed by a low-surrogate escape is one character |
| `yaml_plain_multiline` | a plain scalar over three lines | plain-scalar folding |
| `yaml_crlf` | CR LF line ends, in a quoted and a literal scalar | line breaks read as line feeds |
| `yaml_comment_before_flow` | a JSON-like text after a comment | the first-character rule sends it to YAML |
| `yaml_document_start_flow` | `--- [1, {a: b}]` | the same, after a document start |
| `yaml_explicit_key` | `? key` | explicit keys |
| `yaml_unsorted_keys` | unsorted keys, a plain key `y` | keys sorted when written; `y` is the string `"y"` under YAML 1.2 |
| `yaml_top_level_quoted_scalar` | `'480'` | a top-level quoted scalar is a string |
| `manifest_unsorted` | `manifest_canonical_order` with every reorderable array shuffled, in flow style | canonical order applied by the writer |
| `manifest_respelled` | `2.0` on an `int` axis, `2` on a `float` axis, `[33, 2.0]`, a child's `offset`, a region, a flow-control coordinate, a root's `offset`, a `number_type` overriding the unit's default | own-axis values spelled as their number type selects |
| `manifest_timestamp_respelled` | an integer `coordinate` of a named timestamp on a `float` axis | named-timestamp coordinates are own-axis values |
| `timelines_without_version` | an object whose `timelines` is an array, without `timetoshare` | it is a manifest, so its timelines are ordered |
| `json_compact` | JSON without whitespace, keys unsorted | JSON in any layout |
| `json_whitespace` | tabs, CR LF, spaces around tokens, leading whitespace | the first-character rule skips whitespace |
| `json_escapes` | `\/`, `é`, a surrogate pair `😀`, `A`, `\u0009`, `\u007f`, `﻿`, `\u0085` | JSON escapes read; written in canonical form |
| `json_numbers` | `1E2`, `-0`, `1.50`, `0.1e1`, `1e-5`, 2^64, `-0.0`, `4.9e-324`, `10E-1`, `1e+2` | a number without `.`, `e`, `E` is an integer; every other a float |

## Refusals

| Text | Reason |
| --- | --- |
| `empty.yaml` | holds no value: an empty text |
| `whitespace_only.yaml` | holds no value: whitespace only |
| `comments_only.yaml` | holds no value: comments only |
| `yaml_duplicate_key.yaml` | a key repeats in its object |
| `yaml_duplicate_key_quoted.yaml` | a key repeats, once plain and once single-quoted |
| `yaml_duplicate_key_escaped.yaml` | a key repeats, once through the escape `a` |
| `yaml_duplicate_key_nested.yaml` | a key repeats in a nested object |
| `yaml_duplicate_key_flow.yaml` | a key repeats in a flow mapping |
| `yaml_lone_surrogate_high.yaml` | a lone high surrogate through an escape |
| `yaml_lone_surrogate_low.yaml` | a lone low surrogate through an escape |
| `yaml_lone_surrogate_reversed.yaml` | a low-surrogate escape before a high-surrogate one pairs neither |
| `yaml_lone_surrogate_32bit_escape.yaml` | a surrogate through the escape `\U0000D800` |
| `yaml_lone_surrogate_key.yaml` | a lone surrogate in a key |
| `yaml_nel_in_string.yaml` | a literal U+0085 in a YAML text |
| `yaml_nel_in_comment.yaml` | a literal U+0085 in a YAML text, inside a comment |
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
| `yaml_float_overflow.yaml` | a float beyond the range of a double |
| `yaml_float_overflow_negative.yaml` | a negative float beyond the range of a double |
| `yaml_implicit_key_1025.yaml` | an implicit key of 1025 characters |
| `flow_mapping_unquoted_key.yaml` | YAML flow style from the first character is read as JSON, and `{a: 1}` is not JSON |
| `flow_sequence_plain.yaml` | the same for `[a, b]` |
| `flow_sequence_then_comment.yaml` | read as JSON, and a comment is not JSON |
| `json_duplicate_key.json` | a key repeats in its object |
| `json_duplicate_key_escaped.json` | a key repeats, once through the escape `a` |
| `json_duplicate_key_nested.json` | a key repeats in an object inside an array |
| `json_lone_surrogate_high.json` | a lone high surrogate through an escape |
| `json_lone_surrogate_low.json` | a lone low surrogate through an escape |
| `json_lone_surrogate_reversed.json` | a low-surrogate escape before a high-surrogate one pairs neither |
| `json_lone_surrogate_then_letter.json` | a high-surrogate escape followed by a letter |
| `json_lone_surrogate_key.json` | a lone surrogate in a key |
| `json_nan.json` | `NaN` |
| `json_infinity.json` | `Infinity` |
| `json_negative_infinity.json` | `-Infinity` |
| `json_float_overflow.json` | a float beyond the range of a double |
| `json_float_overflow_negative.json` | a negative float beyond the range of a double |
| `json_two_values.json` | not one JSON value: two |
| `json_trailing_comma.json` | not JSON: a trailing comma |
| `json_single_quotes.json` | not JSON: a single-quoted string |
| `json_unclosed.json` | not JSON: an unclosed object |
| `json_comment.json` | not JSON: a comment |

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
