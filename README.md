# Exact helper exchange and matrix-multiplication research methods

Code, worked examples, exact certificates and scoped lower-bound proofs from Joshua Stapleton's matrix-multiplication research. Existing decompositions and upstream reducers are credited separately; this repository does not claim their discovery or a generally optimal SLP minimizer.

[Download the complete methods bundle](downloads/fmm_research_methods.zip) · [Original compact helper-exchange bundle](downloads/fmm_helper_exchange_scripts.zip) · [Attribution and model conventions](docs/METHODS.md)

## Latest update: 17 October 2026

Further controlled tests improve **5x7x7 V to 203**, **4x4x16 V to 219**,
**5x5x12 V to 229**, and **6x7x8 V to 279**. The full scheme totals are
**694, 633, 721, 952** additions. All four tensors and literal programs verify.
Trying several starting helper sets helped, and an exact dependency filter
accelerates the final replacement step of three-helper exchange searches.

[New counts, controls and limitations](docs/pool-policies-20261017.md) ·
[Four-scheme certificate ZIP](downloads/fmm_pool_multistart_certificates_20261017.zip) ·
[Portable study](methods/linear/reconstruction/pool_policy_study/README.md).

Earlier in the day:

New certificates improve seven checked-in maps across six schemes, saving
sixteen additions. Six improvements use Perminov's retained-vector restarts
combined with pooled reconstruction. Examples:
**3x6x8 V uses 155**, **4x4x16 uses 634 total additions**, and **5x7x7 uses 695**.
The original signed maps, multiplication ranks and ordinary bases are preserved.
All six full tensors and literal programs replay independently.

[Counts, controlled comparisons and negative results](docs/vector-targets-20261017.md) ·
[Portable methods](methods/linear/reconstruction/vector_targets/README.md) ·
[Standalone certificates](downloads/fmm_vector_targets_certificates_20261017.zip).
The four-addition W improvement for 4x4x16 came from the old donor pool alone;
attribution and every transpose return cost are explicit.

## Previous update: 16 October 2026

The supplied **hl_tests** archive now has independently verified circuits for all **57 maps and 19 multiplication tensors**. 19 scheme totals improve their source annotations. Products and the original signed coordinates are unchanged. A separately certified 7x7x8 variant coordinates product signs to use **1179 additions and 279 products**, with no basis change.

[All U/V/W counts and timings](docs/hl-tests-20261016.md) · [Standalone certificate ZIP](downloads/fmm_hl_tests_certificates_20261016.zip) · [Portable replay](certificates/hl_tests_20261016/README.md). Prior results and new reductions are identified separately.

## Previous update: 12 October 2026

A new [GF(2) MixColumns study](docs/gf2-mixcolumns-20261012.md) transfers the
search machinery to exact XOR circuits. It includes verified NIST sources,
finite-pool experiments and a complete depth-three pure-XOR formulation under
stated assumptions. All bounded searches retained their starting counts;
**no improved circuit or hardware speedup was found**.
[Portable code and read-only verification](methods/linear/gf2_mixcolumns_study/README.md) ·
[Standalone study ZIP](downloads/gf2_mixcolumns_study_20261012.zip).


The new 57-map archive has exact certificates for all nineteen supplied schemes.
Fifty-four factors improve the archive annotations. New totals include **580
additions for 5×6×7** and **763 for 6×6×8**. Two previously certified totals
improve by one: **5×6×9 uses 754**, and **6×7×7 uses 847**. Original coordinates
and products are unchanged, with no extra unary negations or scalar operations.

[Full U/V/W counts and methodology](docs/tests-archive-20261012.md) ·
[Counts CSV](certificates/tests_archive_20261012/counts.csv) ·
[Standalone certificates](downloads/fmm_tests_archive_certificates_20261012.zip) ·
[Portable batch scripts](methods/linear/reconstruction/archive_batch_README.md)

The original source graphs, all 57 literal programs and nineteen multiplication
tensors replay with standard-library Python. Weighted initialization and both
pool orientations are recorded separately; no generally superior solver or
unrestricted optimality is claimed.

## Previous update: 11 October 2026

[A direct test of Perminov's new weighted helper pool](docs/perminov-pool-method-20261011.md)
now includes 96 matched completion calls, 400 temperature tests and 20,000
complete backward walks. None improved the existing best counts. The source
already shares ancestors correctly. On the 5x5 example, two solver runs found
87 gates impossible within the frozen observed catalogue and verified 88;
this is a restricted, solver-reported minimum, not an unrestricted lower bound.
[The portable adapters](methods/linear/reconstruction/pool_method_adapters/README.md)
and [frozen data and witnesses](methods/linear/reconstruction/pool_method_study/README.md)
separate the actual partial initializer from the complete-target experiment.
[Download this study](downloads/fmm_pool_method_study_20261011.zip).

All eighteen supplied maps now have strict certificates below their original
annotations. The six complete original schemes use **765, 669, 755, 697, 848 and
1020 additions** for 5×5×11, 5×6×8, 5×6×9, 5×7×7, 6×7×7 and 7×7×7 respectively.
Products and original signed coordinates are unchanged. The 5×7×7 result also
improves the previously published 701 to **697**, split **178+205+314**.

[The experiment report](docs/new-tests-20261011.md) records before/after counts,
matched retention controls, separate timing stages and both orientations of
pool search. [Full certificates](certificates/new_tests_20261011/README.txt)
check all six tensors and eighteen literal programs. [Download the standalone
ZIP](downloads/fmm_new_tests_certificates_20261011.zip), extract it and run
`python3 -I -B verify_all.py`; only standard-library Python is required.

[The adjoint-pool wrapper](methods/linear/reconstruction/adjoint_pool.py) makes
the two-orientation search reusable. Five of six extra W searches improved the
original-coordinate result after all reverse accumulations were charged. The
matched pilots do not establish a universal retention winner, and the extra
paid-chain initialization pilot did not beat its existing incumbent.

## Previous update: 10 October 2026

The supplied **5×7×7 rank-176 scheme now uses 701 additions**, down from 788:
**U 180 + V 205 + W 316**. The uploaded V map falls from 236 to 205. All programs
use the original fixed coordinates, with zero extra negations, scalars or
unused gates. Including 176 products gives **877 arithmetic operations**.

[The report](docs/experiments-20261010.md) explains shared-residual circuit
generation, paid chain selection, transposition and global pool reconnection.
[Full exact certificates](certificates/scheme_5x7x7_176/README.md) check all 60,025
tensor identities. [Download the standalone bundle](downloads/fmm_5x7x7_176_certificates_20261010.zip),
extract it and run `python3 -I -B verify.py` with standard-library Python.

Matched controls distinguish the ideas: residual-based donor diversity helped
the final pooled witness; guided starts improved a small pilot, but an ablation
still reproduced V 205 without their donors. The pair-unlock bonus gave worse
counts, and three earlier V records stayed unchanged. These are fixed-scheme
improvements and experimental methods, not global records or an optimal SLP
algorithm.

## Previous update: 9 October 2026

[Mixed-donor initialization](docs/pooled-starts-20261009.md) now imports paid
computation chains from several solutions before external LEO completion.
The exact small pilot verifies all 60 real-map completions; both control and
mixed starts reach the existing 67-addition 2x4x7 V count. This is a tested
experimental method, with no new bound or demonstrated general advantage.

The additional [25-map test-archive report](docs/tests-archive-20261009.md) improves 24 supplied maps with exact fixed-sign programs. Complete additions fell from 1,661 to **1,408 for the supplied 8×8×8 rank-343 scheme**, and from 769 to **705 for 6×6×7**. [All nine triples and their certificates](certificates/tests_archive_20261009/README.md) preserve the original multiplication tensors and coordinates. The 2×4×7 U35 and W67 phases also have matching [fixed-map rational lower bounds](methods/circuits/directions_README.md).

[Download the 25-map certificate bundle](downloads/fmm_tests_archive_certificates_20261009.zip). Extract it and run `python3 -I -B verify_all.py`; only Python's standard library is needed.

New reusable components include [conditional tensor-factor reuse](methods/linear/tensor_factors/README.md) and [native exact pool construction](methods/linear/README.md#native-exact-pool-construction). The native backend returns the same pool objects as the reference and independently rechecks its relations. The largest-case pools are explicitly frozen reconstructed validations containing known witnesses; they are not claimed as first-discovery replays.

The [partial-reconstruction module](methods/linear/reconstruction/README.md) combines Perminov's new partial-solution API with dependency cuts, adjustable retention, population export and exact donor pooling. [The experiment report](docs/experiments-20261009.md) records the results, timings, donor counts, controls and bounded failures. The [interactive illustration](docs/reconstruction.html) shows chain retention, the nine-for-eight repair and the combined search workflow; download it to open locally.

[Download the latest standalone certificate bundle](downloads/fmm_reoptimization_certificates_20261009.zip).

The [new certificates](certificates/fmm_maps_20261009/README.md) include **3×6×8 V in 158 additions**, **3×8×8 V in 173**, and the complete supplied **3×6×8 triple in 414 additions plus 113 products**. They preserve the original signed maps, with no basis change or extra negations/scalings. The 158 result is available as both a selective repair and a separately pooled circuit. The 173 result improves on every contributing restart donor. These are specific benchmark improvements, not global records or runtime claims.

The same follow-up reproduces 133 for 2×4×14 V, 113 for 3×4×7 W, 141 for 3×6×6 W and 200 for 3×6×8 W. Cut ranking has not demonstrated superiority: randomized ordering of the same structured cuts also found 158, faster in this recorded test.

```sh
python3 -I -B certificates/fmm_maps_20261009/verify.py
python3 -I -B methods/linear/reconstruction/test_reconstruction.py
```

The [earlier supplied-map certificates](certificates/fmm_maps_20261008/README.md) retain 3×4×7 V78, 5×5×8 V161 and 7×8×8 V401. All portable certificate checks are included in the release verifier.

## Start here

Python 3.10+ is sufficient for the standard-library checks. C++17 is needed for native searches/proof enumeration. Optional solver-backed methods use `requirements-search.txt` (Python3.11+ for the pinned environment).

```sh
python3 -B verify_release.py
python3 -B run.py --example wt --verify-only
python3 -B methods/linear/certificate_555_332/verify.py
```

`verify_release.py` checks file hashes and runs portable controls plus upper-bound certificates in a temporary copy. Use `--full` to rerun the exhaustive lower-bound/structural proofs; `--solvers` additionally requires the optional dependencies. Tests never need access to the original research workspace. Full proof checks take longer than circuit replay.

## Method map

| Area | Implementations and explanation | What it contributes |
|---|---|---|
| Helper exchange | [Original search](docs/helper-exchange.md), [`exchange.cpp`](exchange.cpp), [`make_pool.py`](make_pool.py) | Pool reusable exact forms; reconnect the entire reachable circuit after linked replacements |
| Larger and equal-cost search | [Linear methods](methods/linear/README.md) | Population of equal-cost helper sets, larger exchange beams, linked-pair generation, necessary reachability cuts, whole-tensor sign orientation |
| Partial reconstruction | [Repair and restart methods](methods/linear/reconstruction/README.md) | Related dependency cuts, paid mixed-donor starts, shared residual forests, guided chain selection and globally combined donors |
| Binary linear circuits | [GF(2) studies](methods/linear/gf2_mixcolumns_study/README.md) | Field-correct XOR replay, restricted pools and normalized depth-three synthesis, with bounded non-improvements |
| Repeated factor reuse | [Conditional tensor factors](methods/linear/tensor_factors/README.md) | Extract exact smaller maps, charge their lifted computations, and expose cross-group expression sharing |
| Intelligent transformations | [Transformation tools](methods/transforms/README.md) | Exact sparse inverses, ternarity screens, both-order endpoint checks, signed-column classes, matching-based sparsity selection and symmetry transfer |
| Joint circuit/basis search | [Circuit tools](methods/circuits/README.md) | Exact SLP replay/transposition, acyclic CP-SAT selection, jointly chosen roots, linked conversion/kernel search, historical helper transport |
| Exact addition lower bounds | [Basis proofs](methods/basis/README.md) | Finite complete rational helper classifications, exhaustive root closure, canonical boundary bounds and a coordinated transformation grid |
| Rank/decomposition restrictions | [Structural methods](methods/structure/README.md), [span moves](methods/decomposition/README.md) | Rational pair-span rigidity, finite-field rank-one enumeration and exact coordinated four-term moves |
| Persistent experiments | [Research queue](methods/orchestration/README.md) | Exact-map caching, reducer/seed provenance, leases, verification and correctly separated portfolios |
| Storage and recursion | [Storage](methods/storage/README.md), [analysis](methods/analysis/README.md) | Fixed-DAG buffer scheduling, conversion-inclusive recursion counts and rational roundoff envelopes |

## Representative certificates

| Shape / products | Certified arithmetic | Coordinates and scope |
|---|---|---|
| 5×7×7 / 176 | **701 additions = 180+205+316**; 877 operations with products | Original coordinates; [certificate](certificates/scheme_5x7x7_176/) |
| 5×5 / 93 | **332 additions = 87+88+157**; 425 operations with products | Ordinary coordinates, no conversions or hidden negations/scalings; [certificate](methods/linear/certificate_555_332/) |
| 6×6 / 153 | **587 additions = 158+157+272**; 740 with products | Ordinary coordinates; [certificate ZIP](certificate_666_587.zip) |
| 4×4 / 48 | **169 kernel additions** + 39 boundary additions + 4 halvings | Alternative basis; 260 one-level operations including products; [certificate](methods/basis/certificate_4x4_169_43/) |
| 4×4 / 48 | **204 linear operations** = 200 additions + 4 halvings | Ordinary coordinates; 252 with products; [allocation certificate](methods/storage/certificate_204_storage_19/) |
| 8×8 / 336 | **1250 kernel additions** + 268 boundary operations | Mixed4×4/2×2 composition; 1854 one-level operations with products; [certificate](certificates/certificate_8x8_1250_268/) |
| 2×3×3 / 15 and 3×2×3 / 15 | **36+10** and **33+10** additions, kernel+boundary | Fixed-source canonical constructions and scoped matching bounds; [small schemes](methods/basis/small/README.md) |
| 3×3 / 23 | **51 minimum kernel additions** in the stated models | Fixed-source proof plus specified784-member decomposition-changing grid; [proofs](methods/basis/README.md) |

These are attained counts and precisely delimited computational proofs, not global records, measured hardware speedups, or new tensor ranks/exponents. The 5×5 input count87 matches Perminov's previously reported count. Copies/signs are free in several search/lower-bound models; strict final algorithm certificates explicitly check literal signs, scalings and conversions.

A useful controlled result: the 5×5 U search reached87 from88 using a different equal-cost helper population after the same enriched pool's entire three-for-two neighborhood failed. Its W improvement, however, also follows from a simple two-for-one exchange after pool enrichment. The evidence supports these specific mechanisms, not superiority over every reducer.

## Reproduction and provenance

Each method directory supplies its inputs, source identifiers, commands and limitations. `PUBLICATION.json` maps the release to original experiments; `SHA256SUMS` covers the published files. [Proof and search details](docs/METHODS.md) distinguish complete enumerations from beams, finite-pool infeasibility, timeouts and heuristic failures.

The distribution contains readable implementations, representative exact data, and standalone certificates. It excludes private correspondence, raw browser/chat exports, credentials, local binaries, upstream dependency checkouts and duplicate campaign checkpoints. Upstream PLinOpt and Perminov optimizers remain external, with pinned attribution. Existing upstream license notices are retained; see [NOTICE](NOTICE.md).
