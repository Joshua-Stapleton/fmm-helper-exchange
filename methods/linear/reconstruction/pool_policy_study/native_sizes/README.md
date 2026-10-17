# Optional vector omission size and later pooling

These are fixed-map experiments on Perminov's native optional-vector restart
method. An omitted vector is a hint omitted from the restart. This differs from
deleting helper gates in the pooled circuit search. Surviving hints can be unused
and pruned from the finished native circuit.

Five verified initial circuits are frozen at 155, 220, 204, 230 and 280 additions
for 3x6x8 V, 4x4x16 V, 5x7x7 V, 5x5x12 V and 6x7x8 V. Four arms omit exactly 2,
exactly 3, uniformly 1 through 3, or uniformly 1 through 8 eligible helper vectors.
Each arm uses two seeds and 6 seconds per seed. The 40 calls run one at a time,
with coefficient magnitude at most 1 for new forms and live-dependency accounting
for optional unused hints. The same incumbent is frozen for every arm and seed.

## What happened

The native comparison made 2,522 draws and completed 2,357 exact signed solutions.
No arm directly improved any initial count. Exactly 2 omissions produced 716
finished circuits; exactly 3 produced 523 under equal aggregate time budgets.
Nevertheless the selected 32-donor banks from 3 omissions introduced more forms
than those from 2 omissions on all five maps. Two seeds and short budgets do not
establish a general ranking.

A separate follow-up compared prior-bank-only pooling against that same bank
expanded with the bounded native donor exports. Both got 15 seconds per map and
the same plateau seed. The control/expanded results were 155/155, 220/220,
203/204, 230/229 and 279/279. The 203 and 279 improvements already occur using the
old banks. The expanded 229 circuit uses two helper forms absent from its prior
pool. One came from a 231-addition donor found with seven optional vectors omitted.
Keeping a slightly worse circuit therefore supplied a useful sum for later
pooling. This does not prove seven omissions were necessary.

These packaged candidate circuits are signed-wire discovery evidence. Strict
final certificates and whole-scheme tensor checks are maintained separately;
no global optimum, basis-change advantage or hardware speedup is claimed here.
The nominal native budget was 240 seconds, measured native process wall time
241.83 seconds, and total native-study wall time 274.36 seconds including
validation. The follow-up used 150 nominal search seconds and took 161.60 seconds
including pool preparation and validation. Machine contention and cooperative
time checks affect measured throughput.

## Verify without compiling or searching

From the repository root:

```sh
python3 -I -B methods/linear/reconstruction/pool_policy_study/native_sizes/verify.py
```

The standard-library verifier checks file hashes, five ordered input maps and
initial circuits, all bounded prior/new donor banks, ten final signed candidates,
40 representative completed native draws, and the new-form provenance. Every
archived object is replayed with exact integer vectors. The full local audit of
2,357 completions is retained as an observed report; its raw dumps are deliberately
omitted. The 40 representative draws are explicitly a bounded sample, not those
full dumps. Original source-file hashes in observed reports refer to the original
JSON encoding; SHA256SUMS covers the compact packaged encoding.

## Optional native and pooling searches

These commands do real work; default verification above does not. Run them from
the repository root. The default native search is about 240 seconds plus setup
and validation; the default pooling comparison is about 150 seconds plus setup.

```sh
python3 methods/linear/reconstruction/pool_policy_study/native_sizes/run_sizes.py --out /tmp/fmm-native-size-run
python3 methods/linear/reconstruction/pool_policy_study/native_sizes/pool_followup.py --out /tmp/fmm-native-size-pooling
```

The native runner clones and checks out the pinned upstream only when invoked,
then reuses the existing sibling `vector_targets/toolchain` adapter/source to
compile a single-worker driver inside the chosen output directory. An existing
compatible driver can instead be supplied with `--binary`. Pooling defaults to
the frozen bounded banks here; `--native-run /tmp/fmm-native-size-run` uses newly
generated exports. Both runners require this package inside the helper repository
or an explicit FMM_HELPER_REPO environment variable pointing to that checkout.
Stochastic timed searches need not reproduce the same trajectory on every system.

## Source and scope

Native source: [Andrew Perminov's linear-expressions-optimization](https://github.com/dronperminov/linear-expressions-optimization),
pinned at `7c8b59864e000bdc880938428d8a1991ec1f0bea`. Build/source hashes are in
`observed/native_build.json`. The MIT license is copied as UPSTREAM_LICENSE.
The latest inspected branch commit is recorded separately; its two helper-vector
generation function bodies are identical apart from const qualifiers on their
signatures. No reported 228/276 certificates were present in its tracked files.

No chat text, correspondence, raw bulk dumps, compiled binaries or upstream
checkout are included. Each new donor arm is capped at 32 circuits, preserving
eight cheapest then selecting marginal canonical-form diversity per cost penalty.
