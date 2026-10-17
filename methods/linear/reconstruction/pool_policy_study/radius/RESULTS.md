# Findings

No new best addition count was found in this subexperiment. Six frozen current V pools retain 77, 110, 155, 204, 230 and 280 signed-wire additions. All twelve radius-two runs exhaust the one-helper and two-helper improvement neighborhoods. Radius-three and plateau-six searches remain heuristic or time limited at these budgets.

The historical same-pool controls establish a useful distinction: two-helper exchanges cannot improve the saved U160 or Wt156 anchors, whereas checked three-helper exchanges give U158 and Wt155. These are existing historical results, not new count discoveries. Full enumeration reports contain 231 and 171 pairs respectively. Known-triple native replay verifies the constructive moves. This establishes a separation between these two finite exchange neighborhoods, not a global SLP lower bound.

The new exact last-replacement boundary filter lets the same radius-three search start substantially more triples in the same five-second native budget:

| V map | Count | Original triple starts | Filtered triple starts | Ratio | Candidate trials filtered |
|---|---:|---:|---:|---:|---:|
| 3x4x7 | 77 | 312 | 988 | 3.17 | 74.6% |
| 3x6x6 | 110 | 276 | 928 | 3.36 | 79.8% |
| 3x6x8 | 155 | 128 | 431 | 3.37 | 80.8% |
| 5x7x7 | 204 | 84 | 314 | 3.74 | 84.5% |
| 5x5x12 | 230 | 95 | 500 | 5.26 | 89.0% |
| 6x7x8 | 280 | 63 | 634 | 10.06 | 93.3% |

The native `triples` counter increments when a triple is started; the final triple at a time limit may be only partly explored. Ratios describe this small traversal-throughput pilot, not universal wall-time speedups or proof that a complete triple layer finishes. The same original source, pool, anchor and seed are used in each pair. Process startup time is recorded separately from the engine's internal timer.

In a further blind historical control, the filtered Wt search rediscovered the known 156-to-155 improvement in 8.180 seconds, starting 726 triples. The original search using the same seed timed out at ten seconds after starting 203 triples. The known removed triple was not prioritized in this control. Filtered U starts 482 triples versus 90 in ten seconds, without reaching its known witness. These are search-efficiency observations on old certificates, not new records.

Four safety tests pass. One compares the actual native filter against an independent Python reference on 200 randomized cyclic production graphs. Another checks successful last insertions across 2,000 random graph states. The suite includes a counterexample showing why this filter must not be applied to the first of two jointly useful new helpers. A separate standard-library verifier replays all 77 exported ordered integer maps exactly. Counts here retain the signed-wire model; no newly found circuit needs to be represented as a literal paid-sign result because no current bound changed.

The method keeps every feasible last-insertion completion in the fixed pool. See `README.md` for the causal-path proof and the precise distinction between a removed helper, an unavailable descendant, plateau insertion perturbation and Perminov's optional vector hints.
