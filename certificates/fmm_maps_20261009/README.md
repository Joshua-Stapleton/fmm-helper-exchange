# Exact FMM linear-map certificates, 9 October 2026

These programs compute the bundled matrices with their original coordinates
and signs. Every program consists of binary additions/subtractions and copies,
with no basis change, standalone negations or scalar multiplications.

The matrices match factors in [Andrey Perminov's public FMM collection](https://github.com/dronperminov/FastMatrixMultiplication/tree/6c75fd36564b177165d6968efd4c9e6199266191/schemes/results/addition_reduced_ZT).
`PUBLIC_SOURCES.json` records the public JSON source, its hash, the exact
coefficient match and the addition count obtained by expanding that source's
published factor program.

| Fixed map | Published factor program | Certified program |
|---|---:|---:|
| 2x4x14 V | 138 | 133 |
| 3x4x7 V | 82 | 78 |
| 3x4x7 W | 119 | 113 |
| 3x6x6 V | 127 | 110 |
| 3x6x6 W | 147 | 141 |
| 3x6x8 U | 65 | 56 |
| 3x6x8 V | 171 | 158 |
| 3x6x8 W | 209 | 200 |
| 3x8x8 V | 188 | 173 |

## Verification

From the repository root:

```sh
python3 -I -B certificates/fmm_maps_20261009/verify.py
```

Alternatively, extract the standalone archive, enter its directory and run
`python3 -I -B verify.py`. Python's standard library is sufficient. The
verifier checks payload hashes, every coefficient, literal operation counts,
fixed signs and unused assignments independently of the search code.

All five parent multiplication tensors are checked. Missing factors are
explicitly identified in `corpus_completion/` and reconstructed from the
same public source. The complete 3x6x8 triple uses **414 additions and 113
products**, totaling **527 scalar operations**. A and B use row-major inputs;
C uses column-major outputs, as in the source. Storage order costs no arithmetic.

## Method and attribution

The searches use Perminov's unmodified [linear-expressions-optimization](https://github.com/dronperminov/linear-expressions-optimization/tree/2abd2fd8f15dc1c97dd24777515324f865e77504)
at commit `2abd2fd8f15dc1c97dd24777515324f865e77504`, together with selective
partial reconstruction and exact intermediate-form pooling implemented in
this repository. The upstream rounds CLI produced the 113, 141 and 200
programs for the W factors. Per-map provenance identifies the other methods.

The included 3x6x8 V witness starts from a 159-gate circuit, removes nine
dependent gates, retains 150 and rebuilds eight, producing 158. The prepared
input, exact raw solution and seed 4064 are in `method/`. A separate pooled
158-gate alternative is also verified. For 3x8x8 V, the new donor programs
individually required at least 174 additions; their combined pool admitted 173.

[Method details and witness replay](method/METHOD.md) describe how to use the
[portable reconstruction module](../../methods/linear/reconstruction/README.md).
The randomized-order control also reached 158 and was faster in the recorded
run, so the current cut-ranking rule has no demonstrated advantage.

[Saved donor-pool search examples](search/README.md) contain the complete donor
circuits and finite pools for three successful searches. These make pool
assembly and search reproducible without recovering the original experiments.

These are feasible bounds for named fixed maps. They establish neither
global optimality nor improvements in rank, exponent, practical runtime or
energy use. Single-factor counts do not determine a full multiplication cost.
