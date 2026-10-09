# Bounded strict finite-pool feasibility checks

These records use fixed original input/output signs and binary additions or
subtractions, prohibiting separately charged unary negations. A CP-SAT model
selects active forms and exact productions and uses rank variables to prohibit
cycles. Results concern their exact finite form pools, not arbitrary linear
circuits or basis changes.

| Fixed map | Requested bound | Status | Budget |
|---|---:|---|---:|
| 3x6x8 U | 55 | INFEASIBLE | 30 s |
| 3x6x8 W | 199 | UNKNOWN | 30 s |
| 3x6x6 W | 140 | UNKNOWN | 30 s |
| 2x4x14 V | 132 | UNKNOWN | 30 s |
| 3x8x8 V | 172 | UNKNOWN | 30 s |

The U check completed in 0.104 seconds and excludes 55 gates only in its
118-form, 446-production fixed-sign model. Its complete pool is bundled in
`368_U55/pool.json`. The 2x4x14 pool is also bundled as `../2414_V133/pool.json`.
The other timeout records retain historical artifact identifiers; their
larger experimental pools are not included. UNKNOWN provides no exclusion or
lower-bound proof. No global minimum follows from any of these results.

The model implementation is `methods/circuits/cp_pool.py` at repository level.
Reproducing solver statuses requires OR-Tools; standard-library certificate
verification checks the exact successful programs and does not invoke CP-SAT.
