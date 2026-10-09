# Exact certificates for the 25-matrix test archive

The original `tests.zip` contains 25 fixed linear maps from nine multiplication
schemes in [Perminov's public collection](https://github.com/dronperminov/FastMatrixMultiplication/tree/6c75fd36564b177165d6968efd4c9e6199266191/schemes/results/addition_reduced_ZT).
This directory preserves those matrix files byte for byte and supplies their
certified literal addition/subtraction programs. Two unchanged U factors from
the public corpus complete the 3x3x14 and 3x4x6 triples. `uploaded` in
`RESULTS.json` distinguishes the original 25 maps from these supplements.

| Scheme | Rank/products | Original additions | Certified additions | Certified U/V/W |
|---|---:|---:|---:|---|
| 2x4x7 | 45 | 174 | 169 | 35 / 67 / 67 |
| 3x3x14 | 101 | 361 | 355 | 49 / 123 / 183 |
| 3x4x6 | 56 | 209 | 202 | 44 / 64 / 94 |
| 4x5x7 | 104 | 400 | 379 | 89 / 112 / 178 |
| 4x5x9 | 137 | 542 | 507 | 130 / 144 / 233 |
| 4x6x7 | 123 | 517 | 469 | 114 / 140 / 215 |
| 5x6x6 | 130 | 562 | 503 | 129 / 147 / 227 |
| 6x6x7 | 183 | 769 | 705 | 185 / 186 / 334 |
| 8x8x8 | 343 | 1661 | 1408 | 383 / 375 / 650 |

All programs preserve the original signed coordinates. No basis change,
standalone negations or nonunit scalar multiplications are required. A/B inputs
are row-major and C outputs column-major, as in the source. These are bounds
for the named fixed schemes, not state-of-the-art or runtime claims.

## Verify

From the repository root:

```sh
python3 -I -B certificates/tests_archive_20261009/verify_all.py
```

After extracting a standalone archive, enter its directory and run
`python3 -I -B verify_all.py`. Python's standard library is sufficient. This
checks hashes and every literal coefficient, independently replays all 27
signed candidates, recounts operations, verifies all nine parent tensors,
checks the representative pool witnesses and runs both fixed-map proof checks.
No compiler or optimizer is required for verification.

`RESULTS.json` records each matrix header's original count, its certified
count, file hashes, rank and source. `SCHEMES.json` records complete triples.
`ARCHIVE.json` gives the source ZIP hash; the source ZIP itself is not included.
`corpus_completion/` is explicit about the two added source factors.

## Methods and representative data

The programs were found using the public upstream LEO library at commit
`2abd2fd8f15dc1c97dd24777515324f865e77504`, partial reconstruction, exact
intermediate-form pooling and bounded graph selection. Some output factors
were optimized in their transposed frame and then converted back, with the
actual original-map program independently checked. This optimization frame
is unrelated to a change of basis in the multiplication algorithm.

Per-map `provenance/` records preserve logical configurations and measured
stages. Timeouts establish no exclusion. Reported timings are affected by
concurrent machine load and are search timings, not multiplication runtimes.
Unshipped historical artifacts are identified as such rather than presented
as runnable local paths.

[Representative pools](search/README.md) include three successful transposed-W
searches and all three frozen 8x8x8 validation pools. The latter contain an
already known attaining witness and were reconstructed after discovery;
they do not recreate the original causal discovery datasets. Earlier mixed
controller auxiliaries are excluded. Every pool and witness is checked in its
own stated coordinate frame. In particular, the 8x8x8 W kernel witness has
371 gates in the transposed frame; the certified original W program has650.

## Fixed-map lower bounds

`direction_floor.py` applies elementary projective-direction bounds to the
25 original maps and both supplements; results are in `LOWER_BOUNDS.json`.
This considers binary linear gates over Q with free scalar copies, a more
permissive model than the supplied literal signed programs.

Two bounds are attained and have standalone proofs:

- [2x4x7 U: 35 additions](proofs/2x4x7_U35/PROOF.md).
- [2x4x7 W: 67 additions](proofs/2x4x7_W67/PROOF.md).

These establish optimality for those two exact fixed linear maps in the stated
model. They do not establish optimality over multiplication schemes, ranks or
changes of basis, and the lower-bound claims are not characteristic-two claims.
