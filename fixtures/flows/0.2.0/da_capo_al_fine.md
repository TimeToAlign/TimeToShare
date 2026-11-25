# da_capo_al_fine

`score`, 16 quarters. Break `break_1` (Fine) at 8, ending the flow after
the destination of `jump_1`. Jump `jump_1` at 16 (D.C. al Fine): no place,
taken once, not restoring.

Boundaries 0, 8, 16. Atomic sections A [0, 8), B [8, 16).

## default

1. Up to 8: run [0, 8). `break_1`, arrival 1: its `ends` does not hold, so
   it is no break now. The flow goes on.
2. Up to 16: run [8, 16). `jump_1`, pass 1: its destination holds and is
   taken to 0, the timeline's start (no section break lies before 16). The
   `after` of `break_1` now holds.
3. Up to 8: run [0, 8). `break_1`, arrival 2: `ends` holds. No jump lies at
   8, so the flow ends there. The break has `ends`: no finding. No section
   break lies at or after 8: the flow does not begin again.

Runs [0, 8), [8, 16), [0, 8): A B A. No finding.

## single

No `after` holds, so the Fine is passed; the da capo lies before its jump
and is not taken. Runs [0, 8), [8, 16): A B.

## printed

A B.
