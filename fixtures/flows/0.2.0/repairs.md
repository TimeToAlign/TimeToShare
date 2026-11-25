# repairs

`score`, 16 quarters. The imported jump `jump_1` at 16 (a repeat end
without a place) is rejected: an entry of its provenance holds the belief
`false`. It is left out. Read are the jump target `jump_target_1` (repeat
start) at 8 and the jump `jump_2` at 16, to `jump_target_1`, taken once,
both added by hand, and the imported barline `barline_1` at 8, which has no
effect.

Boundaries 0, 8, 16 (a barline is no boundary; 8 is the jump target's).
Atomic sections A [0, 8), B [8, 16).

## default

1. Up to 16: run [0, 16). `jump_2`, pass 1: taken to 8.
2. Up to 16: run [8, 16). Pass 2: taken 1 of 1 times, it does not hold; 16
   is the length and the flow ends.

Runs [0, 16), [8, 16): A B B. No finding. With `jump_1` read as well, two
jumps would lie at 16.

## single

Runs [0, 16): A B.

## printed

A B.
