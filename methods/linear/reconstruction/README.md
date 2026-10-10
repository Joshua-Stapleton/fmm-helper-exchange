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

## Random initialization from several donors

[`pool_starts.py`](pool_starts.py) samples intermediate endpoints and imports
their ancestor chains from several same-map donors into a paid partial SLP.
It reuses sign-equivalent forms without merging different magnitudes and
keeps existing producers to avoid reciprocal-dependency cycles. LEO completes
the original target using retention one; unused initial gates are pruned and
all live initial gates count. This differs from upstream rounds, which start
from a single selected solution, and from finite-pool search, which cannot
invent new forms.

```sh
python3 -I -B methods/linear/reconstruction/pool_starts.py \
  --leo /tmp/leo --donors methods/linear/reconstruction/pooled_start_pilot/source_donors.json \
  --out /tmp/fmm-pooled-starts --sources 3 --gates 20 \
  --attempts 30 --seconds 25 --timeout 2 --seed 4500
python3 -I -B methods/linear/reconstruction/test_pool_starts.py
python3 -I -B methods/linear/reconstruction/pooled_start_pilot/verify.py
```

[The small pilot](../../../docs/pooled-starts-20261009.md) provides a four-gate
toy witness and 30 single-source versus 30 mixed-source real-map completions.
Both arms reach the existing 67-addition 2x4x7 V result; no new bound or
general advantage is claimed. This adapter uses the same pinned external
library and repair driver as the reconstruction commands below.

## Shared residuals and guided initialization

The [10 October report](../../../docs/experiments-20261010.md) records a
fixed-coordinate **5×7×7 rank-176 scheme with 701 additions**, split into
**U180 + V 205 + W316**. The supplied V map previously used 236; the complete
historical scheme used 788. [Standalone certificates](../../../certificates/scheme_5x7x7_176/README.md)
check every coefficient and the full multiplication tensor.

[`output_forest.py`](output_forest.py) connects related target vectors using
`t_child = ±t_parent + residual`. It chooses a rooted acyclic plan, deduplicates
signed residuals, solves their latent map using external LEO, and appends all
reconstruction gates. Original input roots and output signs are retained; every
latent and reconstruction operation is charged. A coefficient2 requires actual
doubling additions. The saved V 224 example uses 80 latent gates and 147
reconstruction gates; normalization removes three redundant gates.

```sh
python3 -I -B methods/linear/reconstruction/output_forest.py \
  --leo /tmp/leo --matrix certificates/scheme_5x7x7_176/V.sms \
  --out /tmp/fmm-forest --trials 90 --seconds 90 --timeout 3 --seed 8800
python3 -I -B methods/linear/reconstruction/test_output_forest.py
python3 -I -B methods/linear/reconstruction/forest_pilot/verify.py
python3 -I -B certificates/scheme_5x7x7_176/verify.py
```

Independent linear transposition lets the same forest method explore W through
its transpose. The final certificate checks the resulting program in the
original W frame and charges all operations. The final U/V/W witnesses come
from pooling the diverse resulting circuits and globally reconnecting their
forms; forest selection alone does not attain 701.

[`gain_starts.py`](gain_starts.py) selects paid donor chains using marginal
signed L1 proximity to targets, new target coverage, and complementary donor
participation per added ancestor gate. It is a heuristic distance proxy, not a
shortest-circuit distance or lower bound. Both it and
[`pair_starts.py`](pair_starts.py) require optional NumPy from
`requirements-search.txt`; standard certificate replay does not.

```sh
python3 -I -B methods/linear/reconstruction/gain_starts.py \
  --leo /tmp/leo --donors methods/linear/reconstruction/forest_pilot/intelligent/bank20.json \
  --out /tmp/fmm-gain-starts --budgets 80,130,180 --modes random,gain \
  --sources 6 --attempts 3 --seconds 120 --timeout 8 --seed 7000
python3 -I -B methods/linear/reconstruction/test_gain_starts.py
python3 -I -B methods/linear/reconstruction/test_pair_starts.py
```

The pair selector adds exact one-gate target unlocks `t=±a±b`. Its tested bonus
completed faster but gave worse circuits than the L1 control. In a frozen-bank
pilot the gain selector attained 213, against random 223. Removing its donors
from the final V pool nevertheless still attained 205. The final count therefore
does not establish a contribution from guided starts or general superiority.
Three earlier V records remained unchanged under the new forest-plus-pool
control. [Search witnesses](forest_pilot/README.md) preserve those controls.

Signed intermediate search costs require strict orientation before claiming
addition/subtraction counts with no extra negations. The final 701 certificate
has zero unary negations, nonunit scalar operations, or unused gates. Both
selectors validate their NumPy int64 coefficient range to reject overflow;
exact circuit replay otherwise uses Python integers. Generic tools refuse
existing output directories and report malformed external output as an error.

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
parent selection remains its temperature one cost weighting and retention .5;
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
