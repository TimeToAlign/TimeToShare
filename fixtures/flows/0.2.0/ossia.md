# ossia

`score`, 24 quarters, its child `ossia` at 16 to 24, laid out after the
main text. Jump `jump_1` at 4, the place of choice: `by` 0, the main text,
and to `ossia` (16), not determined. Jump target `jump_target_1` at 12,
where the ossia returns. Break `break_1` at 16, the end of the main text.
Jump `jump_2` at 24, the end of the ossia: to `jump_target_1`.

Boundaries 0, 4, 12, 16, 24. Atomic sections A [0, 4), B [4, 12),
C [12, 16), D [16, 24).

## default

1. Up to 4: run [0, 4). `jump_1`, pass 1: `by` 0 never competes; the
   destination to `ossia` is not determined and is never taken: finding
   `undetermined_target` at 4. The flow goes on.
2. Up to 16 (a jump target is no stop): run [4, 16). `break_1` has no
   `ends` and holds; no jump lies at 16; the flow ends there. It is not the
   length, no section break lies at 16 and the break has no `ends`: finding
   `flow_ends_at_break` at 16.
3. [16, 24) lies in no run: finding `never_played` at 16.

Runs [0, 4), [4, 16): A B C.

## single

The same walk: runs [0, 4), [4, 16), A B C.

## printed

A B C D.
