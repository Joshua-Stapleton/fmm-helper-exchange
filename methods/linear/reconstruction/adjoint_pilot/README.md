# Frozen adjoint-pool pilot, 11 October 2026

These six cases preserve the actual donor banks and finite pools used for six
20-second follow-up searches on Perminov's fixed W maps. Optimize W transpose,
then transpose the resulting circuit back and charge every accumulation. No
input basis changes or conversion costs are omitted.

| Case | W before extra | W after extra | Selected WT gates |
| --- | ---: | ---: | ---: |
| 5x5x11 | 377 | 355 | 208 |
| 5x6x8 | 318 | 311 | 181 |
| 5x6x9 | 355 | 340 | 188 |
| 5x7x7 | 314 | 314 | 173 |
| 6x7x7 | 397 | 390 | 217 |
| 7x7x7 | 487 | 477 | 276 |

Five extra passes improved W. The 5x7x7 pass retained its existing 314-gate W
program; it did not find another improvement. These are heuristic results for
specific maps and finite pools, not general lower bounds or runtime records.

Each case contains the ordered adjoint `donors.json`, full `pool.json`, original
`W.sms`, saved WT baseline and selected candidates, and the selected final
original W candidate. JSON compaction removes only repeated donor
`target_matrix` fields. Every donor gate and output remains in its original
order. The full pool retains its target matrix, incumbent and all relations.
`MANIFEST.json` hashes the packed files and records the hashes of the original
experimental bank, pool and candidate files before compaction.

## Verify without optional dependencies

From this directory:

```sh
python3 -I -B verify.py
```

The standard-library verifier checks every donor's exact ordered WT map, every
frozen relation identity, the acyclic incumbent, selected WT counts, and an
independently constructed reverse accumulation DAG. It replays and charges
that return against the original W map and checks the final original W
candidate. Signed aliases in these JSON circuits still require a separate
literal-sign certificate. The complete original-coordinate programs, strict
addition counts and multiplication tensor checks are in the
[certificate bundle](../../../../certificates/new_tests_20261011/README.txt).

This verifier checks relations that are present. It does not prove relation
enumeration completeness. The native pool builder can regenerate the pool
from the frozen bank as a separate check.

## Re-run a bounded experiment

From the repository root, using the seed recorded for the chosen case in
`MANIFEST.json`, and a fresh output directory:

```sh
python3 methods/linear/reconstruction/adjoint_pool.py \
  --matrix methods/linear/reconstruction/adjoint_pilot/5x6x9/W.sms \
  --donors methods/linear/reconstruction/adjoint_pilot/5x6x9/donors.json \
  --out /tmp/fmm-adjoint-5x6x9-replay \
  --backend native --search-seconds 20 --seed 11220100 --width 10
```

The native builder and search require a C++17 compiler. Add `--orient-seconds 8`
with the optional solver dependencies installed to request literal input and
output sign verification. Searches use wall-clock limits and can choose
different results on different machines. The frozen candidates remain
independently verifiable without rerunning a search.

The wrapper combines established linear circuit transposition and existing
finite-pool reconnection. This pilot supports searching in both orientations;
it does not establish a new general SLP minimization algorithm.
