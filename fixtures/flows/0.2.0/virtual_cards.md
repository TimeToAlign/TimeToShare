# virtual_cards

`allegro`, 1644 quarters. Jump `volta_jump` at 953/2 (before the
brackets): `by` 0 on pass 1, to `second_ending` (500) on pass 2. Jump
`repeat_end` at 500 (the repeat sign at the end of the first bracket): no
place, taken once. Break `volta_break` and jump target `second_ending` at
500.

Boundaries: 0, 953/2 (`volta_jump`), 500 (`repeat_end`, `volta_break`,
`second_ending`, the place of `volta_jump`'s second destination), 1644; the
place of `repeat_end`'s destination is 0. Atomic sections A [0, 953/2),
B [953/2, 500), C [500, 1644).

## default

1. From 0 the flow plays up to 953/2: run [0, 953/2). `volta_jump`,
   pass 1: `by` 0 never competes, the destination to `second_ending` holds
   on pass 2 only. Nothing is taken; no break at 953/2; the flow goes on.
2. From 953/2 up to 500: run [953/2, 500). `repeat_end`, pass 1: its
   destination has been taken 0 of 1 times and holds. It has no place and
   no section break lies before 500, so it lands at 0. It lies before the
   jump and restores what lies wholly inside [0, 500): `volta_jump` does
   not, since one of its places is 500; its passes are kept. The flow is
   at 0.
3. From 0 up to 953/2: run [0, 953/2). `volta_jump`, pass 2: the
   destination to `second_ending` holds and is taken. The flow is at 500;
   the break at 500 is not played up to and does not act.
4. From 500 no jump or break follows: run [500, 1644). The flow ends at
   the length.

Runs [0, 953/2), [953/2, 500), [0, 953/2), [500, 1644): A B A C,
953/2 + 47/2 + 953/2 + 1144 = 4241/2 quarters, the length of the virtual
timeline `allegro_default`. Every stretch is played; no finding.

## single

`volta_jump` is arrived at on pass 1 + 1: the destination of `repeat_end`
restores, is taken once, and its stretch [0, 500) contains 953/2. On
pass 2 the destination to `second_ending` holds and lies ahead: runs
[0, 953/2), [500, 1644), A C, 953/2 + 1144 = 3241/2 quarters, the length
of the virtual timeline `allegro_single`.

The stretch [953/2, 500), B, lies in no run, and the `default` flow plays
it: finding `never_played` from 953/2 to 500, cause `single_playback`
(going through once takes the second bracket at once and leaves out the
first).

## printed

A B C, 1644 quarters. The whole axis is played: no finding.
