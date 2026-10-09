# Partial reconstruction and finite-pool rebuild

These experimental adapters combine Andrey Perminov's partial-solution
restart with exact donor pooling and our helper-set searches. The public LEO
library is installed separately; none of its implementation or binaries are
vendored here. All exported donors are replayed using Python integers against
the fixed ordered target matrix before pool admission.

This module makes three operations portable:

1. Select related gate groups, remove them and their descendants, retain the
   unaffected SLP, and ask LEO to complete it with retention probability one.
   The completion can discover coefficient forms absent from an existing pool.
2. Export populations from complete upstream restart rounds, including
   equal-cost or worse circuits whose intermediate forms may help another SLP.
3. Search a fixed form pool by deleting helpers, repairing missing targets
   using exact production closure, pruning, and keeping a bounded population
   of shorter or near-equal helper sets.

Generic vector covering, local reconstruction and population search are
established methods. This combination and its witnesses are research artifacts;
no theorem of novelty or general superiority is claimed.

## Verify the saved 158 result

From the repository root; Python 3.10+, standard library only:

```sh
python3 -I -B methods/linear/reconstruction/verify_fixture.py
python3 -I -B methods/linear/reconstruction/test_reconstruction.py --with-cpp
```

The independent fixture verifier checks the exact 113-by-48 V linear map
and its strict literal program: **158 additions/subtractions**, all 5,424
coefficients, zero unary negations, nonunit scalar operations or dead gates.
Inputs and outputs have their original fixed signs. This is a certificate
for one linear map, not by itself a whole matrix-multiplication certificate.

The source map is the V factor of Perminov's ternary rank-113 3x6x8 scheme
`3x6x8_m113_cr445_fv243_cn1240_ZT_reduced`. The `159` source SLP and the
`158` result use the same ordered coefficient matrix. Fixtures contain only
numeric circuits, the prepared partial SLP and the strict result; see
`PROVENANCE.json` and `fixtures/SHA256.json`.

## Install the external LEO branch and replay the winning repair

The adapters require the partial-solution API introduced on
`solution_optimization`, pinned here at commit
`2abd2fd8f15dc1c97dd24777515324f865e77504`.

```sh
git clone https://github.com/dronperminov/linear-expressions-optimization /tmp/leo
git -C /tmp/leo checkout 2abd2fd8f15dc1c97dd24777515324f865e77504
python3 -I -B methods/linear/reconstruction/reconstruct.py \
  --leo /tmp/leo --prepared methods/linear/reconstruction/fixtures/winning_368_V.txt \
  --out /tmp/fmm-158-replay --seed 4064 --savings 0 --slack 4 --timeout 30
```

This compiles our adapter and the clean external library into the new output
directory, then exactly checks the returned 158-gate circuit. Compilation is
outside the timed search budget. A C++17 compiler is required. `--compiler`
selects one explicitly; `--binary` can reuse a previously compiled adapter.

```sh
python3 -I -B methods/linear/reconstruction/build.py --leo /tmp/leo \
  --driver repair --out /tmp/fmm-repair-driver
python3 -I -B methods/linear/reconstruction/reconstruct.py \
  --binary /tmp/fmm-repair-driver \
  --candidate methods/linear/reconstruction/fixtures/368_V_159.json \
  --cut-seeds 51,117 --out /tmp/fmm-158-explicit \
  --seed 4064 --savings 0 --slack 4 --timeout 30
```

Cut indices refer to the normalized source circuit. The winning cut removed
nine gates, including five target forms, preserved 150 gates, and rebuilt
eight. Four resulting intermediate vectors were absent from the incumbent.

## Structured searches and controls

The source candidate format is `{inputs, gates, outputs, target_matrix}`,
using the root `run.py` wire/sign convention. Only signed aliases are merged;
coefficient magnitudes and ordered output signs are preserved. Zero target
rows and zero intermediate forms are unsupported by this format.
Export accepts binary additions/subtractions and unit signs; a raw solution
using nonunit terminal scalar operations is rejected rather than undercounted.

```sh
python3 -I -B methods/linear/reconstruction/reconstruct.py \
  --binary /tmp/fmm-repair-driver \
  --candidate methods/linear/reconstruction/fixtures/368_V_159.json \
  --out /tmp/fmm-ranked --seed 4000 --seconds 80 --timeout 2 --attempts 250
python3 -I -B methods/linear/reconstruction/reconstruct.py \
  --binary /tmp/fmm-repair-driver \
  --candidate methods/linear/reconstruction/fixtures/368_V_159.json \
  --out /tmp/fmm-random-order --seed 4000 --seconds 80 --timeout 2 --attempts 250 \
  --order random
python3 -I -B methods/linear/reconstruction/reconstruct.py \
  --binary /tmp/fmm-repair-driver \
  --candidate methods/linear/reconstruction/fixtures/368_V_159.json \
  --out /tmp/fmm-retention --seed 4000 --seconds 30 --attempts 20 --retention .7
```

Groups contain one to three nearby gates sharing parents or dependencies.
Defaults cap a cut at 12 removed gates and eight neighboring seeds. The score
is removed gates minus lost distinct target forms: an optimistic repair margin
if unaffected gates remain. `--order random` shuffles **the same eligible
groups**. `--retention p` instead starts from the complete incumbent and uses
the upstream Bernoulli-retention control. A chain of six dependent gates
survives with probability p^6; branching depends on all distinct ancestor gates.

In the recorded experiment, the ranked order found 158 after 52.256 seconds;
random order found the same count after 3.645 seconds. The latter completed
250 attempts in 62.284 seconds, versus 123 attempts in 80.014 seconds for the
ranked order. **This does not establish an advantage for the ranking.** Both
orders use structured groups. Machine load and timeout decisions affect search
trajectories; the prepared winning input is the deterministic replay target.

Successful calls export `donors.json`, records, exact candidates and build
provenance. Generic counts assume free signed wires. A strict fixed-sign
orientation and independent literal replay are additional requirements before
claiming a count without separately charged negations; the saved 158 fixture
already supplies those checks.

## Export complete round populations and pool them

```sh
python3 -I -B methods/linear/reconstruction/population.py \
  --leo /tmp/leo --matrix methods/linear/reconstruction/fixtures/368_V_159.json \
  --out /tmp/fmm-population --rounds 6 --iterations 4 --seconds 75 \
  --seed 20261009 --preset distance
python3 -I -B make_pool.py /tmp/fmm-population/donors.json /tmp/fmm-population-pool.json
python3 -I -B methods/linear/reconstruction/rebuild.py \
  --data /tmp/fmm-population-pool.json --out /tmp/fmm-rebuild --seconds 45 --seed 32
```

Matrix input accepts SMS, dense text (`outputs inputs`, then integer rows), or
JSON containing `target_matrix`. Population export defaults to **all** members
of a completed round (`--export-gap -1`); a nonnegative gap limits cost relative
to the current best. Poorer donor SLPs can still contain useful forms. Upstream
parent selection remains its temperature-one cost weighting and retention .5;
this instrumentation does not change the library's search logic.

Only completed rounds can be salvaged after a timeout. Large cases may time
out before exporting their first round; that is not a negative result about
population quality. `--first-cse 0` disables the ten initial CSE tasks;
`--preset default` selects the other upstream vector-covering portfolio.

The finite-pool rebuild engine removes 2 through `perturb+1` helpers, repairs
using constructible pool forms, prioritizes newly reached targets and recovered
old forms, greedily deletes redundant helpers, and retains up to 256 states
within two helpers of the best. Every accepted state is closure-feasible.
The exported program is checked exactly and pruned; timeouts and exhausted
budgets do not prove global or finite-pool optimality. Unlike partial LEO repair,
this engine cannot invent a form outside the supplied pool.
