# Storage scheduling for the existing 204-operation algorithm

The matrices, operation DAGs, and arithmetic counts are unchanged. We reorder
independent operations and reuse a buffer when its old value has had its last
read. This is a local scheduling result, not a new matrix-multiplication scheme.

## Result and exact storage model

| Stage | Source order | New order | What the number includes |
|---|---:|---:|---|
| L, destructive last-use reuse | 38 | 38 | All 38 non-alias retained input combinations |
| R, destructive last-use reuse | 38 | 38 | All 38 non-alias retained input combinations |
| All L/R precomputed before any product | 76 | 76 | Both sets above; twenty other term inputs are aliases |
| P, immutable 48 products, destructive reuse | 26 | **19** | Sixteen output blocks and working buffers |
| P, immutable 48 products, allocate before freeing | 27 | **20** | Sixteen output blocks and working buffers |
| P, mutable product buffers, destructive reuse | 48 | 48 | Includes the 48 initial product blocks |

Thus the output-combination stage can use **three auxiliary blocks in addition
to its sixteen destination blocks**, instead of ten for source order under the
same destructive-reuse policy. The forty-eight product blocks are separate and
remain read-only in this central comparison. Counting those as well gives
74 blocks before and 67 after for this stage, excluding unrelated storage.

For the precompute-all-inputs policy, 76 is an attained lower bound: L and R
each have 38 distinct non-alias outputs that must coexist before the first
product, plus ten direct immutable-input aliases. Both serial L-then-R and
interleaving the two original orders attain 76. This does not rule out lower
memory under a fused/streaming policy that consumes combinations earlier.

Every step is one atomic scalar/block addition, subtraction, or scaling.
Compound source statements are expanded into their individual operations;
for example, `(x+y)/2` is an addition followed by a scaling and can reuse one
buffer across the two operations. Inputs are immutable unless explicitly
labelled as the separate mutable-product policy. Destination blocks may hold
intermediate values before their final output values are computed. All blocks
are assumed to have equal shape and size. Pointer metadata is excluded.

The total remains **200 additions/subtractions, four halvings, and 48 bilinear
products**. P still has exactly 90 additions/subtractions and no scalings.
The 19-block schedule is an attained upper bound, not a proof of an optimal
P schedule. There is no measured runtime, memory-traffic, bandwidth, or
whole-recursion memory claim.

## Verification

Run the standalone verifier with Python's standard library only:

```sh
python3 -S -B verify.py
```

It independently rebuilds the operation DAG from each original source SLP,
checks that the scheduled version has exactly the same rational map and
arithmetic counts, and replays every physical buffer read and write. It
rejects a write over a still-needed value and verifies the stated live-slot
peaks. It also checks all 4096 matrix-multiplication tensor coefficients and
checks the generated C assignments against the allocation certificate.

`P_certificate.json` contains the explicit 19-slot instruction schedule and
its mappings of the sixteen output blocks. The input certificates establish
the 76-block precompute-all floor and its attained serial/interleaved orders.
`verification.json` records a successful exact replay.

## Practical C99 kernel

`P_scheduled.c` defines:

```c
void pernet_P_scheduled(size_t length,
    const double *const products[48],
    double *const output[16],
    double *const scratch[3]);
```

Each pointer denotes a block containing `length` entries. Product, output,
and scratch blocks must be pairwise disjoint. Products are read-only. The
kernel binds sixteen slots to the output blocks and the other three to
scratch blocks, then performs ninety elementwise passes. No final output
copy is necessary. Outputs are workspace until their final values exist.
This double-valued implementation illustrates the allocation; the SLP and
certificate are exact rational artifacts.

`test_c.c` tests 1000 seeded batches of 13-element integer-valued blocks
against direct evaluation of the exact P matrix:

```sh
cc -O2 -Wall -Wextra -std=c99 test_c.c -o test_c
./test_c
```

The public-release check compiled this C99 test with the host compiler and ran
all1000 seeded13-entry batches successfully. This is a correctness test of the
allocation example, not a timing benchmark. The independently verified SLP and
allocation certificate remain the exact arithmetic evidence.

## Search provenance

A bounded beam search over topological orders retained up to 1200 states.
The first pass found 20 slots. Four fixed-seed tie-break variants with width
600 found 19; seed 30 is the exported schedule. Six further width-400 variants
did not find 18. Full search records remain in the local research directory.
These finite searches do not prove that 18 is impossible.

Original files come from the 29 September local GitLab source snapshot:
`Data/4x4x4_48_204_alt_sqr_174/4x4x4_48_204_{L,R,P}.{sms,slp}`.
No GitLab, paper, email, or remote repository was modified.
