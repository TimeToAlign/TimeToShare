# sections

`score`, 32 quarters, two sections divided by the section break
`section_break_1` at 16. First section: break `break_1` (Fine) at 8, ending
the flow after the destination of `jump_1`; jump `jump_1` at 16 (D.C. al
Fine), no place, taken once, not restoring. Second section: jump `jump_2`
at 32 (D.C.), no place, taken once, not restoring.

Boundaries 0, 8, 16, 32. Atomic sections A [0, 8), B [8, 16), C [16, 32).

## default

1. Up to 8: run [0, 8). `break_1`: `ends` does not hold. The flow goes on.
2. Up to 16: run [8, 16). `jump_1`, pass 1: taken. No section break lies
   before 16 (the one at 16 does not), so it lands at 0. The `after` of
   `break_1` now holds.
3. Up to 8: run [0, 8). `break_1`: `ends` holds, no jump at 8: the flow
   ends there, without a finding since the break has `ends`. The nearest
   section break at or after 8 lies at 16, before the length: the flow
   begins again at 16.
4. From 16 up to 32: run [16, 32). `jump_2`, pass 1: taken; the nearest
   section break before 32 lies at 16, where it lands.
5. Up to 32: run [16, 32). `jump_2`, pass 2: taken 1 of 1 times, it does
   not hold. The flow ends at the length.

Runs [0, 8), [8, 16), [0, 8), [16, 32), [16, 32): A B A C C. No finding.

## single

No `after` holds and neither da capo is taken: runs [0, 8), [8, 16),
[16, 32), A B C.

## printed

A B C.
