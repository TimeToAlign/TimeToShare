# repeat_end_and_dal_segno

`score`, 24 quarters. Jump targets `jump_target_1` (repeat start) at 4 and
`jump_target_2` (segno) at 8. Jump `jump_1` at 16 with two destinations: to
`jump_target_1`, taken once, restoring (the repeat end), and to
`jump_target_2`, taken once, not restoring (the dal segno).

Boundaries 0, 4, 8, 16, 24. Atomic sections A [0, 4), B [4, 8), C [8, 16),
D [16, 24).

## default

1. Up to 16: run [0, 16). `jump_1`, pass 1: both destinations hold. Both
   lie before the jump; the restoring one is taken first: to 4.
2. Up to 16: run [4, 16). Pass 2: the repeat has been taken 1 of 1 times;
   the dal segno holds and is taken: to 8.
3. Up to 16: run [8, 16). Pass 3: neither holds. The flow goes on.
4. From 16: run [16, 24).

Runs [0, 16), [4, 16), [8, 16), [16, 24): A B C, B C, C, D. No finding: the
two destinations holding together on pass 1 are of two kinds.

## single

Neither destination is taken, both lying before the jump. Runs [0, 16),
[16, 24): A B C D.

## printed

A B C D.
