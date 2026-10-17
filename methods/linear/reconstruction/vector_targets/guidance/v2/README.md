# Optional-survivor guidance: a small negative result

The native vector-seed method requires only the original outputs. Its surviving
helper vectors are `wanted` hints: a hint is inserted once constructible, but
can remain unbuilt or be pruned afterward. An omitted hint can also reappear.
The initial v1 selector deliberately used a stronger surrogate requiring every
surviving hint. This v2 scores only the ancestor union of the original outputs.

V2 compares two exact finite-pool derivations for each candidate omission set:
one forbids the omitted forms; the other permits their recreation with a small
explicit priority penalty. Derivation priorities favour existing donor forms
to preserve useful sharing. Two bounded reconnection passes can replace a
production by another using already-live forms, then prune unused ancestors.
All pool identities and exported proxy circuits are checked using integer
coefficients. A proxy circuit is a feasible circuit in this graph, not the
native solver's predicted result or a global optimum.

The final fast preparation scored a fixed catalogue of 96 omission sets per
case: earlier guided sets, matched random sets, and seeded additional sets.
It took 1.012 seconds for 3x6x8 V and 0.942 seconds for 4x4x16 V. Each resulting
schedule contains two sets at each omission count from one through eight.
Preliminary implementations took 19.68 and 45.39 seconds on the first two
cases; a third attempt was interrupted without a separate elapsed-time record.
Those costly attempts are retained in `preliminary_costly/`. They are excluded
from the final selector timing, not erased from the research cost.

The focused native comparison used the same frozen original circuit for each
arm, two seeds, ten seconds per arm and seed, a 0.5-second per-draw limit, a
coefficient cap of one, and at most three single-worker native processes.
Unused steps did not count toward the early-abort bound. All 12 jobs completed
in 48.34 seconds including validation; every admitted circuit verified exactly.

| Original factor | Frozen count | V1 guidance | Balanced random | V2 guidance |
|---|---:|---:|---:|---:|
| 3x6x8 V | 158 | 158, 158 | 157, 157 | 158, 158 |
| 4x4x16 V | 222 | 222, 222 | 222, 222 | 222, 222 |

The two numbers in each cell are the two seeds' best counts, including the
frozen incumbent. These are signed-wire discovery counts. This short test gives
no evidence that static guidance improves addition counts. It does not establish
that all guided methods fail. For 3x6x8, v2 also uses a previously available
9 October pooled graph while v1 used its incumbent-only graph, so that case
does not isolate the scoring change from pool diversity.

`summary.json` contains aggregate counts and actual timing; `native_study/`
retains commands, schedules, raw completed solutions, exact best candidates,
per-draw results, and form-accounting checks. Frozen v1 schedules were unchanged.
`POOL_INPUTS.json` and `data/` provide the two exact pool inputs with hashes and
their original provenance. No newly discovered winning native circuit was used
to compute these scores.

The reusable selector is `../select_removals_v2.py`. Supply an exact binary
circuit and optional pool explicitly; the study runners additionally expect
the frozen benchmark bank. The general selector's beam mode is available for
experimentation; the reported fast study instead used the bounded fixed
catalogue in `../prepare_v2.py`.
