# dal_segno_al_coda

`score`, 32 quarters. Jump target `jump_target_1` (segno) at 4. Jump
`jump_1` at 12 (To Coda): to `jump_target_2` (24), after the destination of
`jump_2`. Jump `jump_2` at 24 (D.S. al Coda): to `jump_target_1`, taken
once, not restoring. Jump target `jump_target_2` (coda) at 24.

Boundaries 0, 4, 12, 24, 32. Atomic sections A [0, 4), B [4, 12),
C [12, 24), D [24, 32).

## default

1. Up to 12: run [0, 12). `jump_1`, pass 1: the destination of `jump_2` has
   not been taken, so `after` does not hold. The flow goes on.
2. Up to 24: run [12, 24). `jump_2`, pass 1: its destination holds (taken 0
   of 1 times) and is taken to 4. It does not restore. The `after` of
   `jump_1`'s destination now holds.
3. From 4 up to 12: run [4, 12). `jump_1`, pass 2: its destination holds
   and is taken to 24; its `after` is used up.
4. From 24 nothing follows: run [24, 32).

Runs [0, 12), [12, 24), [4, 12), [24, 32): A B C B D. No finding.

## single

No `after` holds, so `jump_1` is not taken; the destination of `jump_2`
lies before its jump and is not taken. Runs [0, 12), [12, 24), [24, 32):
A B C D.

Every stretch is played, and the walk finds nothing: no finding.

## printed

A B C D. The whole axis is played: no finding.
