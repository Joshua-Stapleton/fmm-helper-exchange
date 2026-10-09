# Fixed-map reconstruction experiments, 9 October 2026

These experiments optimize the addition/subtraction programs for specified linear maps in existing matrix multiplication schemes. The factors, input coordinates and output signs remain fixed. The results below are executable upper bounds; they do not establish global optimality, a lower multiplication rank, a lower exponent, or faster numerical matrix multiplication.

The [certificate collection](../certificates/fmm_maps_20261009/README.md) includes the input matrices, literal programs and an independent standard-library verifier. The [reconstruction module](../methods/linear/reconstruction/README.md) describes the portable search interfaces. Earlier standalone certificates are available for [3x4x7 V78](../certificates/fmm_maps_20261008/347_V78/README.md), [5x5x8 V161](../certificates/fmm_maps_20261008/558_V161/README.md), and [7x8x8 V401](../certificates/fmm_maps_20261008/788_V401/README.md).

## Sources and attribution

The input schemes come from [Andrey Perminov's FastMatrixMultiplication collection](https://github.com/dronperminov/FastMatrixMultiplication), with source identifiers and hashes preserved in the certificate manifests. The new partial-reconstruction API and rounds solver come from [linear-expressions-optimization](https://github.com/dronperminov/linear-expressions-optimization/tree/2abd2fd8f15dc1c97dd24777515324f865e77504), pinned at `2abd2fd8f15dc1c97dd24777515324f865e77504` on the `solution_optimization` branch. The upstream library was not edited.

The earlier donor portfolios also used LEO at `60272dc3cdd751ce53e43e5c021dbb6021fcbf51` and [PLinOpt](https://github.com/jgdumas/plinopt). The contribution tested here is the combination of retained circuits, dependency cuts, upstream completion, exact intermediate-form pooling and subsequent searches over alternative dependencies. Results obtained directly by the new upstream CLI are identified separately below.

## Verified counts

An addition or subtraction costs one operation. Output copies and coordinate storage order cost no arithmetic. Every listed final program has zero standalone negations, zero nonunit scalar operations and zero unused noninput assignments. Intermediate sign canonicalization is an internal search representation; the final programs are checked with the original input and output signs fixed.

| Supplied linear map | Earlier certificate | 9 October certificate | Source of current bound |
|---|---:|---:|---|
| 2x4x14 V | 134 | 133 | Retention variants followed by pooled search |
| 3x4x7 V | 78 | 78 | Earlier certificate retained |
| 3x4x7 W | 114 | 113 | New upstream rounds CLI |
| 3x6x6 V | 110 | 110 | Earlier certificate retained |
| 3x6x6 W | 142 | 141 | New upstream rounds CLI |
| 3x6x8 U | 56 | 56 | New upstream rounds CLI reproduces the earlier bound |
| 3x6x8 V | 159 | 158 | Selective reconstruction; an independent pooled alternative also attains 158 |
| 3x6x8 W | 202 | 200 | New upstream rounds CLI |
| 3x8x8 V | 174 | 173 | Retention variants followed by pooled search |

The complete 3x6x8 triple uses **414 additions/subtractions and 113 products**, for **527 scalar operations** under this model. Its tensor identity is checked exactly. Other rows in the table are individual linear-map bounds; a count for V alone is not the total cost of a multiplication scheme. These comparisons concern named inputs, not global record claims.

## What was combined

A donor is a complete, exactly replayed circuit for the same ordered target matrix. The pool merges intermediate coefficient vectors only up to sign, preserves their exact magnitudes, and enumerates all binary productions among the retained forms. The search can reconnect dependencies across different donors. It is not restricted to following the edges of one starting circuit.

For 2x4x14 V, the new retention-control circuits individually cost at least 134 operations; their shared pool admits 133. For 3x8x8 V, the new control circuits individually cost at least 174; their pool admits 173. Thus these two reductions are improvements over every contributing control donor, rather than selection of the best donor alone.

The pool sizes count circuit entries, which may include repeated incumbents and signed aliases. They should not be read as counts of pairwise unique algorithms or unique form sets.

| Result | Circuit entries | Forms | Binary production options | Pool incumbent |
|---|---:|---:|---:|---:|
| Earlier 2x4x14 V134 | 28 | 646 | 3,911 | 135 |
| 2x4x14 V133 | 50 | 687 | 4,473 | 134 |
| 3x8x8 V173 | 60 | 961 | 5,910 | 174 |

The 50-entry pool contains 20 distinct selected control circuits, plus the earlier portfolio and retained incumbent entries. The 20 are distinct within that control selection; some can overlap with existing circuits or produce the same canonical forms.

The exact winning pools, donor circuit entries and search records are preserved in [the search replay fixtures](../certificates/fmm_maps_20261009/search/README.md). From the repository root, for example:

```sh
python3 -B methods/linear/search.py \
  --data certificates/fmm_maps_20261009/search/2414_V133/pool.json \
  --out /tmp/fmm-2414-search-replay --engine plateau --seconds 45 --seed 53 --width 8
python3 -B methods/linear/search.py \
  --data certificates/fmm_maps_20261009/search/388_V173/pool.json \
  --out /tmp/fmm-388-search-replay --engine plateau --seconds 45 --seed 53 --width 8
```

These replays begin with the preserved incumbent and pool. They do not rerun donor generation. Use new output directories; the search refuses to overwrite an existing run. Returned generic circuits still require strict fixed-sign orientation before claiming a count without extra negations. The already certified literal programs provide that independent check.

## Timing and parallelism

The figures are observed elapsed times on one development machine, with other maps running concurrently. They are not controlled hardware benchmarks. Donor solvers and graph searches were sequential per invocation; the new upstream CLI was explicitly run with `--threads 1`. Different matrices were processed in parallel. CP tests used their separately recorded worker settings; these are distinct from the single-threaded donor and graph searches.

The final search hit time begins after the pool is assembled. It excludes compilation, input preparation, verification and packaging. The donor and assembly columns distinguish this from the much shorter search step. A successful hit did not end the experiment: searches usually continued to their full budgets.

| Result | Timed donor phase | Pool assembly | First successful solver/search step |
|---|---:|---:|---:|
| Earlier 2x4x14 V134 | 24.539 s | 2.303 s | 0.039663 s |
| 2x4x14 V133, starting from V134 | 87.833 s | 3.046 s | 2.5437 s |
| 3x8x8 V173, starting from V174 | 90.020 s | 11.506 s | 0.251941 s |
| 3x4x7 W113 | 11.063 s for the successful upstream run | Not required to attain 113 | Included in the upstream run time |
| 3x6x6 W141 | 18.579 s for the successful upstream run | Not required to attain 141 | Included in the upstream run time |

The earlier approximately **4.5-second** discovery figure belongs to **3x4x7 W114**, not 2x4x14 V. Its first successful transposed-distance donor took 0.089316 s; the sum of the preceding timed donor calls through that success was 4.447328 s. Pooling and later searches followed the discovery.

For V133 and V173, the donor phases above start from the existing certified V134 and V174 circuits. They do not include the cost of earlier experiments that obtained those starting points. In particular, bounded new CLI attempts that failed to export a complete program are not credited as successful donors merely because their progress logs printed a low count.

## Retention controls

The upstream partial solver can retain each gate with probability p, conditional on retaining its parents. A gate with a distinct noninput ancestral set of size a, including itself, survives with probability p^a. This favors shallow computations when p is small. The controls below vary p from the complete incumbent, with fixed 30-second budgets and three-second per-repair timeouts. Accepted circuits were exactly replayed before pool admission.

| Map and starting bound | p | Attempts | Accepted circuits | Best accepted count | Median accepted count | Repair-loop time |
|---|---:|---:|---:|---:|---:|---:|
| 2x4x14 V134 | 0.9 | 40 | 36 | 134 | 134 | 27.819 s |
| 2x4x14 V134 | 0.7 | 18 | 10 | 134 | 135 | 30.006 s |
| 2x4x14 V134 | 0.5 | 13 | 6 | 134 | 135.5 | 30.008 s |
| 3x8x8 V174 | 0.9 | 22 | 19 | 174 | 174 | 30.009 s |
| 3x8x8 V174 | 0.7 | 13 | 6 | 174 | 175 | 30.006 s |
| 3x8x8 V174 | 0.5 | 12 | 5 | 174 | 175 | 30.006 s |

Higher retention permitted more completed attempts and preserved better median costs in these runs. This is a small diagnostic comparison, not evidence that one probability is generally best. The eventual V133 and V173 gains came from pooling these circuits.

The controls used seed schedules beginning at 7000, 8000 and 9000 for p=0.9, 0.7 and 0.5 respectively. Each schedule incremented the seed by one per attempt, alternated distance-scorer savings 0 and 0.01, and cycled support slack 2, 4 and 8. The subsequent plateau searches used seed 53, width 8 and a 45-second search budget.

## Selective cuts and orientation

The selective method chooses one to three nearby gates sharing parents or dependencies, removes these gates and all descendants, and retains the unaffected circuit. Retained gate indices are compacted into a valid partial SLP. Completion then calls upstream `solve(partial, 1.0)`, so the deliberate retained circuit is kept. This can introduce forms absent from the original finite pool.

For the 3x6x8 V witness, removing nine gates from a 159-gate circuit leaves 150 retained gates. Completion uses eight replacement gates and attains 158. Four repaired intermediate forms were absent from the incumbent. The strict program verifies all 5,424 matrix coefficients.

The ranking by removed gates minus lost distinct output forms is a heuristic. On the same set of 743 eligible groups, both the ranked order and a randomized order attained 158. The randomized order found it sooner in the recorded run. These results support trying selective reconstruction, but do not demonstrate superiority of the ranking rule. The preserved comparison in the certificate collection gives the discovery times and attempt counts.

Orientation also affects search effort. The direct 3x6x6 W map has 85 inputs and 18 outputs; each direct retention arm exported zero complete repairs within ten three-second attempts. Transposing the already certified 141-gate circuit produces a 74-gate circuit for the transposed linear map. This is circuit transposition, not a change of basis in the multiplication scheme; every returned donor is transposed back and checked against the original W matrix.

| Transposed 3x6x6 W experiment | Attempts | Accepted | Best transposed count | Repair-loop time |
|---|---:|---:|---:|---:|
| Retention p=0.9 | 50 | 50 | 74 | 1.958 s |
| Retention p=0.7 | 50 | 50 | 74 | 4.065 s |
| Ranked selective cuts | 40 | 40 | 74 | 0.638 s |

These experiments enlarged the original W pool to 1,923 forms and 13,258 binary productions, but a further 45-second search retained 141. Likewise, 50 selective repairs from the new 3x8x8 V173 circuit completed in 9.520 s; pooling 112 entries and searching for another 45 seconds retained 173.

## Bounded negative results

| Test | Recorded outcome | What it establishes |
|---|---|---|
| 3x6x8 U at most 55, strict signs, 118-form pool | INFEASIBLE, 0.104 s | Excludes 55 only in that specified finite pool/model |
| 3x6x6 W at most 140, strict signs, expanded 1,923-form pool | UNKNOWN after 30.065 s | No exclusion or lower bound |
| 3x8x8 V at most 172, strict signs, expanded 979-form pool | UNKNOWN after 30.005 s | No exclusion or lower bound |
| Additional 5x5x8 V population experiment | 75-second timeout; 20 distinct completed donors recovered | Subsequent pool/search retained the existing 161 certificate |
| Additional 7x8x8 V population experiment | 90-second timeout; zero completed new donors | Subsequent pool/search retained the existing 401 certificate |

The 5x5x8 follow-up pool contained 161 entries, 461 forms and 2,832 productions; assembly took 1.104 s and search continued for 45 seconds. The 7x8x8 follow-up pool contained 36 entries, 1,828 forms and 14,412 productions; assembly took 22.743 s and search continued for 45 seconds. Neither produced a further improvement.

An UNKNOWN solver status is not an infeasibility proof. INFEASIBLE is also qualified by the supplied pool and sign model. Verifier success proves the specified arithmetic identities and counts; it does not prove optimality, numerical stability, storage efficiency or practical speed.
