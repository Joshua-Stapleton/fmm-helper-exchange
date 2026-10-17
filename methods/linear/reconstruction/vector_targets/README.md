# Retained helper vectors and finite-pool reconstruction

This experiment uses Andrew Perminov's unmodified LEO library at commit
`7c8b59864e000bdc880938428d8a1991ec1f0bea` on its public
[`new-improvements` branch](https://github.com/dronperminov/linear-expressions-optimization/tree/7c8b59864e000bdc880938428d8a1991ec1f0bea).
The vector-restart idea and solver are his. The adapter, controlled comparisons,
guided omission scores, and combination with this repository's exact circuit
pool search are provided here with their limitations.

## Method

1. Start from a verified complete circuit. Evaluate its helper vectors, identify
   vectors equal up to sign, and exclude original output forms and forms with
   fewer than two nonzero coordinates. These filtered helpers have dense indices.
2. Omit one through eight helper vectors. Supply the remaining **vectors** to
   LEO as optional wanted forms. They are neither free inputs nor compulsory
   outputs. The solver may change their construction, recreate omitted forms,
   skip retained forms, and prune unused gates.
3. Replay every completed circuit against the original ordered integer map.
   Keep useful complete circuits, including some that cost more than the best.
4. Build a pool of their exact vector identities. Search for a smaller acyclic
   circuit using shared forms across donors. Reorient signs with original roots
   and output signs fixed; pay any required correction gates. For W-transpose
   searches, transpose the circuit back and pay the full return cost first.

The ten frozen maps and 185 prior donors are under `benchmarks/`. This is a
small warm-start study, not an evaluation across all matrices or a global
minimality result. Fully materialized binary donors are the input boundary;
native terminal sums are explicitly expanded when making pool circuits.

## Reproduce the native study

Run from the repository root. Python's standard library and a C++17 compiler
suffice for native discovery, pool reconstruction, and the frozen-data checks.
Optional literal sign orientation uses OR-Tools, as in the existing adjoint tools.

```sh
cd methods/linear/reconstruction/vector_targets
git clone https://github.com/dronperminov/linear-expressions-optimization.git upstream
git -C upstream checkout 7c8b59864e000bdc880938428d8a1991ec1f0bea
python3 -B toolchain/adapter.py --build
python3 -B verify.py
python3 -B -m unittest discover -s guidance -p 'test_*.py' -v
python3 -B native_study/run_study.py --stage main --ignore-unused-bound 1
python3 -B pooling/run_pooling.py
```

Study execution creates fresh outputs below `native_study/main/` and
`pooling/results/`; don't treat archived observations in `observed/` as new runs.
Wall-time stopping makes exact draw counts machine-dependent. The checked-in
literal certificates give deterministic verification of the achieved counts.
Each native invocation uses one CPU worker; batch runners permit three
concurrent processes. Native timing is cooperative; incomplete output records
are excluded and actual elapsed times are recorded.

The main comparison gives each of five initializers two six-second native
budgets on each frozen incumbent: executable helper prefix, random vector
omission, a 50/50 mix, guided omission, and random omission with the same sizes
as the guided schedules. Per-draw limit: 0.25 seconds; at most 1,000 draws.
Guided schedule preparation is additional. No incumbents change during that
comparison. The later adaptive feedback stage is a separate experiment.

Our main experiment explicitly sets `ignoreUnusedInBound=true`. Upstream's
CLI sets it false, so this is an API experiment with a disclosed setting, not
a reproduction of default CLI behavior. New candidate coefficients are capped
at magnitude one, although a frozen donor can contain a magnitude-two form.
Unresolved statuses combine timeout, bound pruning and exhausted candidates;
they do not prove infeasibility.

## Guided removals

`guidance/select_removals.py` scores omission sets using a stronger finite-pool
surrogate that requires surviving hints. This first selector underperformed
random removal in the direct native experiment. Its donors nevertheless helped
the pooled 4x4x14 W result. `select_removals_v2.py` instead makes only original
outputs compulsory in its score. These are heuristic scores, not addition
lower bounds. Preparation time and post-hoc changes must be included in any
comparison; see the recorded protocols.

For normalized distinct nonoutput forms, the accounting identity is
`gain = k + d - b - q`: k omitted hints, d other retained hints unused at the
end, b omitted hints recreated, and q genuinely new helpers. Thus omitting k
hints does not limit the achievable gain to k. `account_forms.py` checks the
identity on exact circuits; it does not substitute for literal arithmetic counts.

## Optional hints and pruning

`toolchain/bound_control.json` records a six-input example. The only output is
`a+b+c+d`, requiring three sums in the exhibited circuit. Optional hints `a+e`
and `b+f` can be computed immediately but are unused in that circuit. Counting
all materialized steps against a bound of three aborts the tested run; counting
the currently used dependencies permits its valid three-gate completion.
This is a concrete pruning witness, not a general search-quality theorem.

Exact source hashes and the original compiler metadata are recorded in
`toolchain/native_driver_v2.build.json`. Locations in archived observations are
sanitized labels; they are not live filesystem paths. The executable and
upstream checkout are deliberately excluded from the publication.
