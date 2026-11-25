# volta_passes

`score`, 24 quarters. Jump `jump_1` at 8 (before the brackets): `by` 0 on
passes 1 and 3, to `jump_target_1` (12) on pass 2. Jump `jump_2` at 12 (the
repeat sign at the end of the first bracket): no place, taken twice at
most. Break `break_1` and jump target `jump_target_1` at 12.

Boundaries 0, 8, 12, 24. Atomic sections A [0, 8), B [8, 12), C [12, 24).

## default

1. Up to 8: run [0, 8). `jump_1`, pass 1: `by` 0 never competes; the
   destination to `jump_target_1` does not hold. The flow goes on.
2. Up to 12: run [8, 12). `jump_2`, pass 1: taken (1 of 2) to 0. `jump_1`
   is not wholly inside [0, 12), one of its places being 12, and keeps its
   passes.
3. Up to 8: run [0, 8). `jump_1`, pass 2: taken to 12.
4. From 12 nothing follows: run [12, 24). The flow ends at the length.

Runs [0, 8), [8, 12), [0, 8), [12, 24): A B A C. The flow never comes back
to `jump_1` for a third pass, and the repeat's second time is not used. No
finding.

## single

`jump_1` is arrived at on pass 1 + 2, the repeat count of `jump_2`'s
restoring destination, whose stretch [0, 12) contains 8. On pass 3 only
`by` 0 holds: the flow goes on into the first bracket, run [8, 12). At 12
the repeat lies before its jump and is not taken, and `break_1`, which has
no `ends`, ends the flow. Runs [0, 8), [8, 12): A B.

## printed

A B C.
