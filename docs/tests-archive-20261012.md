# tests (1).zip: 57 fixed maps, 19 schemes

All 57 supplied linear maps and all 19 multiplication tensors pass independent exact checks. The final programs use the original signed input/output coordinates, with zero unary negations, nonunit scalar operations or unused gates. Product ranks are unchanged.

| Scheme | Products | Supplied additions | U | V | W | Final additions | Saved |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2x7x8 | 90 | 329 | 38 | 138 | 144 | 320 | 9 |
| 3x3x13 | 94 | 334 | 50 | 106 | 165 | 321 | 13 |
| 3x4x8 | 74 | 267 | 50 | 83 | 127 | 260 | 7 |
| 3x4x9 | 84 | 316 | 70 | 93 | 139 | 302 | 14 |
| 3x4x13 | 121 | 455 | 88 | 136 | 213 | 437 | 18 |
| 3x7x7 | 115 | 432 | 81 | 126 | 206 | 413 | 19 |
| 4x4x11 | 134 | 519 | 111 | 141 | 223 | 475 | 44 |
| 4x5x6 | 90 | 380 | 80 | 103 | 162 | 345 | 35 |
| 4x5x7 | 104 | 400 | 89 | 112 | 176 | 377 | 23 |
| 4x6x7 | 123 | 517 | 114 | 140 | 215 | 469 | 48 |
| 4x6x9 | 160 | 646 | 124 | 188 | 285 | 597 | 49 |
| 4x7x7 | 145 | 629 | 145 | 178 | 262 | 585 | 44 |
| 5x5x7 | 127 | 531 | 115 | 136 | 231 | 482 | 49 |
| 5x6x7 | 150 | 664 | 145 | 170 | 265 | 580 | 84 |
| 5x6x8 | 170 | 720 | 159 | 199 | 311 | 669 | 51 |
| 5x6x9 | 197 | 840 | 202 | 212 | 340 | 754 | 86 |
| 6x6x8 | 203 | 836 | 183 | 214 | 366 | 763 | 73 |
| 6x7x7 | 215 | 880 | 217 | 241 | 389 | 847 | 33 |
| 7x7x7 | 250 | 1067 | 269 | 274 | 477 | 1020 | 47 |

Products are excluded from the addition totals. Full scalar counts, including products, are in [counts.csv](../certificates/tests_archive_20261012/counts.csv). A/B entries use row-major storage; C uses column-major storage. That storage convention is not an arithmetic basis change.

All 19 totals are below the supplied annotations, saving 746 additions in aggregate. Fifty-four of 57 individual factors improve those annotations. Twelve factors already had strict certificates: ten retain the previous best and two improve it. The 5x6x9 total falls from 755 to 754, and 6x7x7 from 848 to 847. The earlier 5x6x8 count 669 and 7x7x7 count 1020 remain unchanged. The archive savings include reductions certified before this batch; they are not all new gains.

The campaign recovered each original source circuit, retained matching previous witnesses, generated donors using CSE, vector covering, partial reconstruction and shared-residual forests, pooled their exact relations, and searched both W orientations with every return accumulation charged. Each external solver had one thread; three campaign workers ran concurrently. Per-method donor, sampling, assembly, search and sign-orientation timings are retained in [method_summary.json](../certificates/tests_archive_20261012/method_summary.json).

The actual weighted HelperPool from unchanged commit `21906e043ab0d652b588864893a07199b915a8e7` ran two additional 1.5-second completion attempts per map. It used explicitly expanded binary donor circuits: all terminal sums were paid and available as internal helpers. This differs from the previous study preserving native terminal boundaries. Of 114 calls, 54 completed and 60 were incomplete. Every completed map was checked before admission. The weighted stage produced a better donor than the earlier stages on ten maps, but it consumed their donor bank, so this is not a fair ablation showing a generally better solver.

The main portfolio had 399 method invocations: 327 completed and 72 were stopped at their limits, with no errors. Incomplete calls never became donors. The extra W searches improved twelve final phases by 58 additions after all reverse accumulations were charged. Time limits and non-improvements do not prove impossibility.

[The portable batch harness](../methods/linear/reconstruction/archive_batch_README.md) records the dependency pins, explicit binary paths, budgets, starting circuits and output conventions. Donor/completion methods use Perminov's external reducers; global reconnection and orchestration wrappers are separate. Generic CSE, restarts, transposition and weighted sampling are established operations. No general novelty, optimality, rank reduction or global record is claimed.

Source decompositions and original reduced circuits: Andrey Perminov, [FastMatrixMultiplication](https://github.com/dronperminov/FastMatrixMultiplication/tree/6c75fd36564b177165d6968efd4c9e6199266191). Every supplied matrix matches its pinned original source expansion, and the complete multiplication tensor is checked.

Download [the standalone certificates](../downloads/fmm_tests_archive_certificates_20261012.zip), extract them and run:

```sh
python3 -I -B verify_all.py
```

Only the standard library is required. Replay checks the full file manifest, original source expansions, all 57 final programs, strict operation accounting and all 19 tensors. Search need not reproduce the same heuristic result for the arithmetic witnesses to verify.
