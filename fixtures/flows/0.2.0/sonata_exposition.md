# sonata_exposition

`score`, 24 quarters. Jump `jump_1` at 12 (before the brackets): `by` 0 on
pass 1, to `jump_target_1` (16) on pass 2. Jump `jump_2` at 16 (the repeat
sign at the end of the first bracket): no place, taken once. Break `break_1`
and jump target `jump_target_1` at 16.

Boundaries: 0, 12 (`jump_1`), 16 (`jump_2`, `break_1`, `jump_target_1`, the
place of `jump_1`'s second destination), 24; the place of `jump_2`'s
destination is 0. Atomic sections A [0, 12), B [12, 16), C [16, 24).

## default

1. From 0 the flow plays up to 12: run [0, 12). `jump_1`, pass 1: `by` 0
   never competes, the destination to `jump_target_1` holds on pass 2 only.
   Nothing is taken; no break at 12; the flow goes on.
2. From 12 up to 16: run [12, 16). `jump_2`, pass 1: its destination has
   been taken 0 of 1 times and holds. It has no place and no section break
   lies before 16, so it lands at 0. It lies before the jump and restores
   what lies wholly inside [0, 16): `jump_1` does not, since one of its
   places is 16; its passes are kept. The flow is at 0.
3. From 0 up to 12: run [0, 12). `jump_1`, pass 2: the destination to
   `jump_target_1` holds and is taken. The flow is at 16; the break at 16
   is not played up to and does not act.
4. From 16 no jump or break follows: run [16, 24). The flow ends at the
   length.

Runs [0, 12), [12, 16), [0, 12), [16, 24): A B A C, 36 quarters, the length
of the virtual timeline `virtual_1`. Every stretch is played; no finding.

## single

`jump_1` is arrived at on pass 1 + 1: the destination of `jump_2` restores,
is taken once, and its stretch [0, 16) contains 12. On pass 2 the
destination to `jump_target_1` holds and lies ahead: runs [0, 12),
[16, 24), A C.

## printed

A B C.
