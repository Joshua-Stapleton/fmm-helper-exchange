# Finite-pool exact DAG search

`finite_pool_cpsat.py` minimizes the number of selected noninput linear forms
over the exact binary productions in a supplied pool. Selected forms have
exactly one production, both parents must be selected, and conditional strict
topological ranks exclude cycles. Every output form is compulsory. All live
selected noninput forms are paid, including shared helpers and output forms.

This does not optimize over all possible linear forms. It therefore cannot
establish a global SLP lower bound. A reported `OPTIMAL` status and lower bound
are OR-Tools solver output, not an independently checkable optimality proof.
The standard-library verifier checks the resulting feasible DAG separately.

Run a search with OR-Tools installed:

```sh
python3 finite_pool_cpsat.py POOL.json INCUMBENT.json --output OUT --seconds 110
```

One CPU worker is used. The incumbent JSON must carry the canonical
`pool_selection` mapping, whose entries are exact productions from this pool.
Preparation, checking and model construction are outside the solver time cap.

Verify an exported solution without OR-Tools:

```sh
python3 -I -B verify.py --pool POOL.json --candidate OUT/candidate.json
```

`verify.py` checks every pool production, the selected acyclic production DAG,
absence of unused selected gates, and literal circuit outputs over the integers.
It does not verify the solver's lower bound. Signed additions allow signed wires;
ordinary-basis strict-sign accounting must be checked separately before making
claims under a stricter gate convention.

## Observed 3x4x4 V runs, 17 October 2026

Both runs used one CPU worker, seed 171744, and a 110-second search cap.

| Frozen pool | Forms | Exact productions | Solver status | Best circuit | Solver bound | Solver seconds |
|---|---:|---:|---|---:|---:|---:|
| Target-subset pool | 179 | 1,715 | OPTIMAL | 41 | 41 | 0.131 |
| Expanded pair/native pool | 390 | 10,126 | FEASIBLE at cap | 41 | 30 | 110.007 |

Both exported 41-gate circuits pass the separate standard-library integer
replay. The smaller pool's optimum is solver-reported only. The larger pool
has no optimality conclusion, and neither run establishes an unrestricted
lower bound. These searches did not improve the 41-addition native incumbent.
