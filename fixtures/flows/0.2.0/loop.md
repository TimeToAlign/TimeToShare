# loop

`take`, 10.0 seconds. Jump target `jump_target_1` at 2.0. Jump `jump_1` at
6.0: to `jump_target_1`, taken 127 times at most. No manifestation.

Boundaries 0.0, 2.0, 6.0, 10.0. Atomic sections A [0.0, 2.0), B [2.0, 6.0),
C [6.0, 10.0).

## default

1. Up to 6.0: run [0.0, 6.0). `jump_1`, pass 1: taken (1 of 127) to 2.0.
2. Passes 2 to 127: each time the run [2.0, 6.0), and the destination is
   taken again, 126 more times.
3. Pass 128: run [2.0, 6.0); the destination has been taken 127 of 127
   times and does not hold. The flow goes on.
4. From 6.0: run [6.0, 10.0).

Runs: [0.0, 6.0), then [2.0, 6.0) 127 times, then [6.0, 10.0), 129 in all:
A, B 128 times, C. No finding.

## single

The destination lies before its jump and is not taken: runs [0.0, 6.0),
[6.0, 10.0), A B C.

## printed

A B C.
