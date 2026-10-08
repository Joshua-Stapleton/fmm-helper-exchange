# Exact helper exchange and matrix-multiplication research methods

Code, worked examples, exact certificates and scoped lower-bound proofs from Joshua Stapleton's matrix-multiplication research. Existing decompositions and upstream reducers are credited separately; this repository does not claim their discovery or a generally optimal SLP minimizer.

[Download the complete methods bundle](downloads/fmm_research_methods.zip) · [Original compact helper-exchange bundle](downloads/fmm_helper_exchange_scripts.zip) · [Attribution and model conventions](docs/METHODS.md)

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
| Intelligent transformations | [Transformation tools](methods/transforms/README.md) | Exact sparse inverses, ternarity screens, both-order endpoint checks, signed-column classes, matching-based sparsity selection and symmetry transfer |
| Joint circuit/basis search | [Circuit tools](methods/circuits/README.md) | Exact SLP replay/transposition, acyclic CP-SAT selection, jointly chosen roots, linked conversion/kernel search, historical helper transport |
| Exact addition lower bounds | [Basis proofs](methods/basis/README.md) | Finite complete rational helper classifications, exhaustive root closure, canonical boundary bounds and a coordinated transformation grid |
| Rank/decomposition restrictions | [Structural methods](methods/structure/README.md), [span moves](methods/decomposition/README.md) | Rational pair-span rigidity, finite-field rank-one enumeration and exact coordinated four-term moves |
| Persistent experiments | [Research queue](methods/orchestration/README.md) | Exact-map caching, reducer/seed provenance, leases, verification and correctly separated portfolios |
| Storage and recursion | [Storage](methods/storage/README.md), [analysis](methods/analysis/README.md) | Fixed-DAG buffer scheduling, conversion-inclusive recursion counts and rational roundoff envelopes |

## Representative certificates

| Shape / products | Certified arithmetic | Coordinates and scope |
|---|---|---|
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
