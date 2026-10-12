# Testing Perminov's weighted helper pool

We tested the published `HelperPool` code at [commit 21906e0](https://github.com/dronperminov/linear-expressions-optimization/tree/21906e043ab0d652b588864893a07199b915a8e7), on the `solvers-time-limit` branch. It already shares previously constructed sums, rejects cycles and rolls back failed constructions. Our earlier suggestion that its backward walks did not account for sharing was incorrect.

The experiment did not improve any of our existing addition counts. It did identify why repeated sampling can stall: a fixed collection of sums and their observed constructions can exclude a better circuit that we already know exists.

## Matched completion tests

We froze four native donor banks, preserving the original split between internal substitutions and terminal expressions. The actual upstream pool imports only internal substitutions. We compared its quality-weighted pool, equal donor weights, and the earlier 50% single-donor restart. Equal donor weights retain production-frequency weighting; they are not equal probabilities for every possible construction.

Each condition used eight seeds, the same completion solver and a five-second per-call limit. Weighted and equal-weight sampling used identical seed/cap schedules. The 50% restart retained a different number of gates because descendants of removed gates are also dropped. There were 96 calls: 77 completed exactly and 19 stopped incomplete.

| Fixed linear map | Weighted pool | Equal donor weights | 50% restart | Existing best |
|---|---:|---:|---:|---:|
| 5x5 U | 88 | 90 | 88 | 87 |
| 5x5x11 U | 197 | 202 | 197 | 195 |
| 5x7x7 U | 180 | 180 | 179 | 178 |
| 5x7x7 V | 207 | 208 | 211 | 205 |

These are best completed counts, not inherited incumbents. For V, only 2/8 weighted, 2/8 equal-weight and 1/8 restart calls completed. This small, timeout-limited comparison does not establish a general winner. Counts use abstract signed wires; the existing comparator programs have separate strict fixed-sign certificates. All prefixes and completed coefficient maps were independently replayed with Python integers. No basis change was used.

The native budget references were 88, 201, 180 and 205. The better known programs were not silently added to those donor banks.

## Additional tests

Four hundred 5x5 completions compared temperatures 0.25, 1 and 4 with the 50% restart. Every condition had best 88. Temperature 0.25 reached a median of 88 rather than 89 in the other conditions. A four-round run of the unmodified upstream CLI, with its accumulating pool, also returned 88.

We also tried choosing the best of four actual upstream prefixes using signed L1 proximity to the targets. All 32 first prefixes matched the ordinary weighted sampler exactly; 25 calls completed. The best counts were 88, 200, 179 and 208. This helped the 5x7x7 U pilot by one over its matched weighted control, but still missed the known 178. An extra exact one-gate target-coverage score did not improve the records either. These scores are heuristics, not shortest-circuit distances or lower bounds.

Separately, we reconstructed the complete-target backward-walk description. This explicitly expands terminal expressions into charged binary gates and therefore uses a different catalogue from the published partial initializer. Ten thousand quality-weighted walks gave best 88, median 89, and 1,861 hits at 88. Ten thousand equal-donor-weight walks gave best 90 and median 104. All 20,000 completed, in 4.70 seconds for this Python walk experiment. That timing excludes graph construction and says nothing about general solver speed. Neither condition found 87.

## A finite catalogue limit

The complete-walk catalogue contains 287 sign-canonical coefficient vectors and 468 observed binary constructions. Two fresh single-worker CP-SAT runs reported that 87 gates are impossible in that catalogue; a paid 88-gate program replays exactly. Seven manually decidable model controls pass. This is a solver-reported minimum for the frozen observed catalogue, with no independent UNSAT proof certificate. It is not a lower bound for arbitrary SLPs or for Perminov's completion solver, which can create new sums.

Allowing all 1,753 exact binary relations among the same 287 vectors gave an unresolved result at 87 within the tested limit. We therefore do not claim that the vector set alone has minimum 88.

The known 87-gate circuit uses one vector missing from this collection and two constructions between existing vectors that were absent from the observed relations. Relative to the tested 88-gate circuit, it removes eight auxiliary sums and introduces seven: six already occur elsewhere in the pool and one does not. This comparison was made after the search, as a diagnostic; the known 87 circuit was not supplied to the new-form generator.

We then tested all 54,106 absent ternary sums or differences of pairs of catalogue vectors. For each, we removed every pair of the starting circuit's fourteen auxiliary sums and globally reconnected the allowed constructions. None of those 4,923,646 specified two-for-one exchanges reached 87. Independent checks regenerated the candidate inventory and compared 204 native closure evaluations with a slower Python implementation. This rules out only that neighborhood around that particular 88-gate circuit. It does not rule out larger changes or a better intermediate starting circuit.

The practical implication is to combine new-sum generation with changes to several linked auxiliaries. Repeatedly sampling the same observed constructions cannot reach a solution they exclude. The tests support this diagnosis on this example; they do not establish a new generally superior minimizer.

## Code and replay

[Portable adapters](../methods/linear/reconstruction/pool_method_adapters/README.md) call the unchanged external sampler, implement the four-prefix experiment and reproduce the complete-target variation. [The frozen study](../methods/linear/reconstruction/pool_method_study/README.md) contains the raw banks, attempts, prefixes, completed maps, finite models, exact witnesses and structural search inputs.

From the repository root:

```sh
python3 -I -B methods/linear/reconstruction/pool_method_study/verify.py
python3 -B -m unittest discover -s methods/linear/reconstruction/pool_method_adapters -p 'test_*.py'
```

Default study replay uses the standard library and checks the completed arithmetic and finite 88-gate witness. The infeasibility models require a separate optional OR-Tools rerun; default replay does not verify an UNSAT proof. Native sampling/completion requires a clean external checkout at the pinned commit and a C++17 compiler. NumPy is required only for the prefix scoring controls.

No new strict addition record, multiplication rank, exponent or measured matrix-multiplication runtime is claimed. Perminov's decompositions, donor circuits and reduction code retain their attribution.
