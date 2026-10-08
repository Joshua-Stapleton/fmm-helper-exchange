# Exact linear-circuit search methods

This directory makes the helper-pool experiments portable: donor pooling,
shared-pair and linked-pair generation, exact production closure, equal-cost
population search, bounded exchanges, reachability cuts, circuit transposition,
and coordinated signs across the whole bilinear algorithm. It includes a
standalone **5×5 certificate with 332 additions/subtractions and 93 products**.

The source decomposition and LEO reducer are Andrey Perminov's. Generic common
subexpression elimination, vector covering, transposition, local search and
plateau search are established ideas. The contribution here is the specific
combination, candidate generators, exact finite-pool formulations, executable
witnesses and controls. No general superiority or algorithmic novelty theorem
is claimed. See [provenance](PROVENANCE.json).

## Run the exact certificate first

Commands below run from the repository root, with Python 3.10 or later.

```sh
python3 -I -B methods/linear/certificate_555_332/verify.py
python3 -I -B methods/linear/independent_verify.py methods/linear/certificate_555_332
python3 -B methods/linear/test_methods.py
```

All three require only the standard library. The first two use separate literal
executors and exact integer tensor reconstruction. The split is **87 + 88 + 157
= 332**, plus 93 products = **425 scalar operations in ordinary coordinates**.
All 15,625 tensor identities pass. There is no basis change, unary-negation gate
or nonunit scalar gate. Output storage is transposed as explicitly specified in
the certificate README. The ZIP can also be extracted and verified in isolation.

This improves our earlier exact 334 certificate by two; U87 reproduces a count
already reported by Perminov. Neither priority, a global record, a lower rank,
an exponent improvement nor a measured speedup follows.

## Search and verify saved witnesses

The root `run.py` validates every supplied production with exact integers and
replays every resulting circuit. The frozen pools include the successful U87
and W-transpose89 witnesses. Search counts use **free signed wires**; the strict
whole-tensor orientation below is what makes the 332 claim valid.

```sh
python3 run.py --data methods/linear/data/5u_pool.json --verify-only
python3 run.py --data methods/linear/data/5w_pool.json --verify-only
python3 methods/linear/search.py --data methods/linear/data/5u_pool.json --out /tmp/fmm-u-search --engine plateau --seconds 240 --seed 8 --width 6
python3 run.py --data methods/linear/data/5w_pool.json --out /tmp/fmm-w-exchange --seconds 30
```

Output directories must be new. Search needs a C++17 compiler and builds into a
temporary directory. `--width` means maximum inserted helpers for `plateau`,
or retained beam width for `--engine beam`. Randomized trajectories and time
budgets can vary across machines; the saved witnesses are deterministic checks.

Each plateau step inserts 1–6 currently constructible helpers, randomly orders
deletion attempts, recomputes exact closure after each attempt, and prunes to
the outputs. It keeps shorter circuits **and distinct equal-cost helper sets**.
Closure reconnects all available productions rather than preserving a particular
old dependency graph. A population of up to 512 states diversifies subsequent
steps. `beam.cpp` tries removing four incumbent helpers and inserts up to three
with priority for missing targets and newly reachable forms. Its pruned
insertions are heuristic: visiting all removal quadruples is not exhaustive
four-for-three search.

## Generate donor pools and new linked helpers

The root `make_pool.py` combines donor circuits with identical exact targets.
It canonicalizes only signs, never magnitudes. `sampling/sample.py` adapts the
separately downloaded, pinned LEO API and converts each result into that format.
No upstream LEO implementation is copied into this repository.

```sh
git clone https://github.com/dronperminov/linear-expressions-optimization /tmp/leo
git -C /tmp/leo checkout 60272dc3cdd751ce53e43e5c021dbb6021fcbf51
python3 methods/linear/sampling/sample.py --leo /tmp/leo --data methods/linear/data/5u_pool.json --out /tmp/fmm-donors
python3 make_pool.py /tmp/fmm-donors/donors.json /tmp/fmm-donor-pool.json
python3 methods/linear/enrich.py --data /tmp/fmm-donor-pool.json --out /tmp/fmm-shared --mode shared --cap 96
python3 methods/linear/enrich.py --data /tmp/fmm-shared/pool.json --out /tmp/fmm-linked --mode linked --cap 64 --beam 8192
```

`shared` ranks absent signed pair sums by how many incumbent helpers and distinct
old forms they reconnect. `linked` generates constructible pairs **c, h** satisfying
an exact target identity **t = ±c ±h**. It retains complete pairs, preferring
reuse across targets and connections to incumbent helpers. Only the first
endpoint is beam-limited; its residual can be any generated pair form. The
portable implementation uses arbitrary-precision Python integers. Add
`--selection density` to grow a connected graph of linked helpers, preferring
reuse within the chosen set rather than through unchosen neighbors. This is a
restricted generator, not a completeness argument. `witnesses.json` records all
selected identities and construction options.

The sampler defaults to 13 configurations × 3 seeds per map: distance settings,
default vector covering and three CSE presets, with upstream substitution
inlining. `--first-config-only --seeds 800` gives a quick smoke test. A generated
pool need not reproduce the frozen pool: the latter also includes historical
donors and previously optimized circuits. Those exact frozen inputs are retained
for reproducing the stated search controls.

## Reachability cuts and strict signs

Install optional solver dependencies in your own virtual environment:

```sh
python3 -m pip install -r methods/linear/requirements-optional.txt
python3 methods/linear/reachability.py --data methods/linear/data/toy_exchange_pool.json --out /tmp/fmm-cuts --seconds 10
python3 methods/linear/reachability.py --data methods/linear/data/toy_exchange_pool.json --verify-cuts /tmp/fmm-cuts/cuts.json
python3 methods/linear/orient.py --u methods/linear/data/5u_candidate.json --v methods/linear/data/5v_candidate.json --wt methods/linear/data/5w_candidate.json --out /tmp/fmm-332-literal
python3 methods/linear/independent_verify.py /tmp/fmm-332-literal --source methods/linear/certificate_555_332/source.json
python3 methods/linear/test_methods.py --with-cpp --with-solvers
```

The reachability model selects helper forms under a gate budget, without first
choosing a dependency graph. If closure reaches a set R containing all inputs
but missing a target, every valid circuit must eventually compute something
outside R whose two parents are in R. Requiring at least one such frontier form
is therefore a necessary cut. `--objective overlap` favors retaining incumbent
helpers; `--grow-cuts 4` constructs extra cuts by provisionally granting forms
when building unreachable sets (never when validating returned circuits). `verify-cuts` checks each exact frontier identity;
it does **not** independently certify a solver's infeasibility result. A timeout
is not an exclusion. A completed infeasibility claim applies only to the supplied
finite dictionary and productions with free signs.

`orient.py` transposes Wᵀ by reverse accumulation and solves Boolean wire signs
jointly for U, V and W. Each binary gate must have at least one positive operand;
product-sign changes on U and V must be compensated in W. Thus every final gate
is an ordinary addition or subtraction, with no hidden standalone negation. It
exactly checks compensated factors; the separate tensor verifier establishes
matrix multiplication. General signed circuits may have no feasible orientation.

## What the controls establish

* **U88→87:** the successful witness replaces nine helpers with eight. Five new
  helpers were absent from the older saved pool. The deterministic engine
  exhausted all three-for-two exchanges from the same incumbent in the same
  enriched pool—11,617,323 closures—without improving. Plateau search escapes
  this fixed neighborhood. Donor membership does not prove any scorer necessary.
* **Wᵀ90→89:** a two-for-one exchange in the richer pool suffices. Plateau search
  also found a larger witness but is not necessary for this construction.
  Transposition adds 93−25=68 gates, giving direct W157.
* **6×6 remains 587:** frozen pools start at U158, V157 and Wᵀ155, hence W272.
  Plateau and pruned four-for-three runs found no improvement. An additional
  78 donor attempts produced 69 exact programs and 9 timeouts. These are bounded
  negative experiments, not optimality proofs.

Historical records in `evidence/` retain original experiment-relative paths and
budgets for provenance; those paths are not reproduction commands. Public
distribution hashes differ from original local hashes where private filesystem
prefixes were removed. Mathematical coefficients and literal SLP bytes were
preserved. The public ZIP's current digest is in `PROVENANCE.json`.
