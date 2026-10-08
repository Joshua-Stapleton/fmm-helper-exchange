# Linked helper and root exchange

Each `data/*/pool.json` stores exact rational vectors, target signs, incumbent helpers and every retained binary production. The search uses free signed wires as a relaxation. A negative result is a neighborhood exclusion; a positive signed result must be reoriented and all literal signs/scalings counted before it is an upper-bound circuit.

`audit.py` independently validates 124,431 exact production identities in seven pools, their native graph exports, incumbent programs and positive-control closure. It also replays the adjacent strict 4×4 169/43 baseline, including its tensor and two-level recursive check.

`exchange.cpp` exhausts up to three helper removals with fewer insertions. `exchange4.cpp` is the original four-for-three implementation. `exchange4_pruned.cpp` selects the lexicographically least topological insertion order and skips reinstating a removed helper, since that belongs to an already tested smaller exchange. `exchange_roots.cpp` permits the incumbent circuit to be temporarily disconnected after a root change. Only exact constructible productions restore closure.

Run from the repository root:

```sh
python3 -B methods/basis/exchanges/audit.py
python3 -B methods/basis/exchanges/replay.py --case all --output /tmp/fmm-exchanges.json
```

A single pool may be selected with `--case kernel_L_exchange4` or another directory name under `data`. `--case roots` regenerates and checks all 60 nonsingular replacements of one or two canonical input roots by the four available norm-three target roots, combined with helper search. `--seconds 900` is the default **per run**; a timeout reports `INCOMPLETE`, never exhaustion. Python standard library and C++17 are sufficient.

The input four-for-three neighborhood exhausts 495 removal quadruples / 106,850,274 closure states; the output-transpose neighborhood exhausts 2,380 / 200,519,150. Archive-enriched input and output pools contain 582 and 2,614 forms; their three-for-two searches also exhaust without improvement. This does not prove finite-pool global optimality, optimality under larger moves, or optimality under arbitrary basis changes.

The public wrapper regenerates all root graph inputs from included pools. It replaces archive-dependent discovery entry points; those old paths are not needed. `fullarchive` in a data-directory name describes how that frozen pool was originally collected, not a dependency on a private archive. The exact search engines and frozen pool coefficients are retained.
