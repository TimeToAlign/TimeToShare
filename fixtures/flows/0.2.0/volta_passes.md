# volta_passes

`score`, 16 quarters. Jump `jump_1` at 8 (before the brackets): `by` 0 on
passes 1 and 3, to `jump_target_1` (12) on pass 2. At 12, where the first
bracket ends and the second begins: break `break_1` (between the
brackets), break `break_2` (Fine), ending the flow after the destination
of `jump_3`, jump `jump_2` (the repeat sign at the end of the first
bracket): no place, taken once, restoring, and jump target
`jump_target_1`. Jump `jump_3` at 16 (the repeat sign at the end of the
second bracket): no place, taken once, not restoring.

Boundaries: 0, 8 (`jump_1`), 12 (`jump_2`, both breaks, `jump_target_1`,
the place of `jump_1`'s second destination), 16 (`jump_3`, the length);
the place of the destinations of `jump_2` and `jump_3` is 0, no section
break lying before them. Atomic sections A [0, 8), B [8, 12), C [12, 16).

## default

1. Up to 8: run [0, 8). `jump_1`, pass 1: `by` 0 never competes; the
   destination to `jump_target_1` holds on pass 2 only. The flow goes on.
2. Up to 12: run [8, 12). `jump_2`, pass 1: its destination has been taken
   0 of 1 times and holds; it is taken to 0. It restores what lies wholly
   inside [0, 12): `jump_1` does not, one of its places being 12, and
   keeps its passes; `jump_2` and the breaks lie at 12, outside. The jump
   being taken, the breaks at 12 do not act.
3. Up to 8: run [0, 8). `jump_1`, pass 2: taken to 12. The elements at 12
   are landed on, not played up to, and do not act.
4. Up to 16: run [12, 16). `jump_3`, pass 1: its destination holds and is
   taken to 0. It does not restore, so `jump_1` keeps its two passes and
   `jump_2` its one take. The `after` of `break_2` now holds.
5. Up to 8: run [0, 8). `jump_1`, pass 3: the highest pass a destination
   of `jump_1` names is 3, so the destination to `jump_target_1`, which
   names 2, does not hold. The flow goes on into the first bracket.
6. Up to 12: run [8, 12). `jump_2`, pass 2: its destination has been taken
   1 of 1 times and does not hold. `break_1` has no `ends` and holds;
   `break_2`, arrival 1: its `ends` holds. The flow ends there. A break
   with `ends` holds at 12: no finding. No section break lies at or after
   12: the flow does not begin again.

Runs [0, 8), [8, 12), [0, 8), [12, 16), [0, 8), [8, 12): A B A C A B.
Every stretch is played; no finding.

Two things the case shows. With `reset` left at its default, the
destination of `jump_3` would restore `jump_1`, `jump_2` and both breaks,
all lying wholly inside [0, 16): `jump_1` would be at pass 1 again, the
flow would be A B A C A B A C, ending at the length with `jump_3` used up,
and pass 3 would never be reached. And without `break_2` the flow would
end at `break_1` all the same, with the finding `flow_ends_at_break` at
12.

## single

`jump_1` is arrived at on pass 1 + 1: the destination of `jump_2`
restores, is taken once, and its stretch [0, 12) contains 8; the
destination of `jump_3` does not restore and is not counted. On pass 2 the
destination to `jump_target_1` holds and lies ahead: the flow is at 12,
where nothing acts. At 16 the destination of `jump_3` lies before its jump
and is not taken; the flow ends at the length. Runs [0, 8), [12, 16): A C.

The stretch [8, 12), B, lies in no run, and the `default` flow plays it:
finding `never_played` from 8 to 12, cause `single_playback` (going
through once takes the second bracket at once and leaves out the first).

## printed

A B C. The whole axis is played: no finding.
