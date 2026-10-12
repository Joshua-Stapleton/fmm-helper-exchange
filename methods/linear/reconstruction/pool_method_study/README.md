# Testing Perminov's current helper-pool method

These data test the actual unmodified `HelperPool` implementation on
[solvers-time-limit, commit 21906e0](https://github.com/dronperminov/linear-expressions-optimization/tree/21906e043ab0d652b588864893a07199b915a8e7).
The comparison uses the earlier master's 50% restart policy at commit
`606edc0b0805f05161098e3ab3b1d1c4b867d5fe`, plus a uniform-weight control.
Original decompositions, donor solutions and completion solvers are credited
to Andrey Perminov. Our contribution here is the controlled experiment,
independent replay, complete-target variation and catalogue diagnostic.

The source already reuses shared ancestors, prevents cycles and rolls back
failed constructions. The earlier suggestion that it performs independent
walks without sharing was incorrect. It chooses helpers and productions by
weighted permutations. Default donor temperature is 1, with 1% uniform mixing;
addition-count classes receive balanced weight. Prefix limits are sampled
between 10% and 50% of the native incumbent count.

Ninety-six matched completion calls produced 77 complete exact maps and 19
incomplete calls. Best completed signed counts were:

| Fixed map | Weighted pool | Uniform pool | 50% restart | Previously known count |
|---|---:|---:|---:|---:|
| 5x5 U | 88 | 90 | 88 | 87 |
| 5x5x11 U | 197 | 202 | 197 | 195 |
| 5x7x7 U | 180 | 180 | 179 | 178 |
| 5x7x7 V | 207 | 208 | 211 | 205 |

The counts did not improve after signed-alias normalization. Weighted and
uniform arms share seed/cap schedules;50% restart has a different retained
gate count because it rejects chains whose ancestors were removed. All calls
use the same completion settings and budget. The native reference counts
88/201/180/205 are distinct from the previously known 87/195/178/205 programs.
Unchanged inherited incumbents are not described as completed repairs.

There are also 800 sampled prefixes, 400 5x5 temperature completion calls and
32 four-candidate lookahead calls. None improved the previous records.
Temperature 0.25 gave a completed-count median 88 rather than 89 on that 5x5
test; all four temperature/restart arms still had best 88. This is a useful
pilot comparison, not general superiority. The full current CLI, including
its accumulating multi-round pool, returned 88 on that same map.

Raw donor files preserve their original boundary between internal
substitutions and terminal expressions. `HelperPool.addSolution` imports
internal substitutions only. Expanding terminal expressions adds producers
to a different pool, although every terminal gate is still paid. Renamed donor
labels and removed machine paths are documented in `TRANSFORMATIONS.json`;
these are newly serialized public bytes, not byte-identical source files.

Our complete-target walk variation explicitly expands the terminals and
builds every output. Twenty thousand walks on that frozen graph gave best 88
with quality weights and 90 with uniform weights. This variation is labelled
separately from the upstream partial initializer. Its source and generic
builder are in [pool_method_adapters](../pool_method_adapters/README.md).

The expanded observed graph has 287 vectors and 468 productions. Two fresh
single-worker CP-SAT calls reported INFEASIBLE at 87 gates; an 88-gate program
replays exactly. Seven manually decidable model controls pass. This identifies
a solver-reported minimum inside that observed catalogue. No independent
UNSAT proof certificate is supplied, and it is not a global lower bound.
The same 287 vectors with all 1,753 exact binary relations remain unresolved
at 87. The known 87 program uses one missing vector and two unobserved
productions. That comparison is diagnostic only; it was not fed into the
candidate generator.

A heuristic generator selected 128 new ternary sums by how many desired
target directions they connect and how many operands are already available.
The 30-second pooled search did not improve 88. A broader, exact monotone
reachability screen checked all 54,106 absent ternary one-hop sums against
all 91 choices of two removed incumbent auxiliaries. It found no 87-gate
program in that specified neighborhood. This is only an exchange around
that 88-gate incumbent, preserving its other auxiliary directions; it does
not rule out larger exchanges, other 88-gate circuits or other 87 programs.
The known 87 witness replaces eight of this incumbent's auxiliaries by seven.

Run the independent standard-library data checks:

```sh
python3 -I -B methods/linear/reconstruction/pool_method_study/verify.py
```

The finite observed catalogue has its own small export:

```sh
python3 -I -B methods/linear/reconstruction/pool_method_study/finite_export/verify_upper.py
# Optional, with OR-Tools 9.15.6755 installed:
python3 -I -B methods/linear/reconstruction/pool_method_study/finite_export/rerun_model.py --bound 87 --seconds 30
```

The optional `model.py` rebuilds the finite CP-SAT model directly from a
standard graph file. Its 88-gate rebuilt model has the same hash as the saved
model. It selects one production per used form and enforces operand ranks
below child ranks. OR-Tools is required only for solving or rebuilding models.

All candidate counts here use the abstract unit signed-wire convention.
Exact coefficient replay proves the fixed map, while strict literal sign
orientation is a separate check. No new strict addition record, basis change,
rank reduction, exponent improvement or matrix multiplication runtime result
is claimed by this study.
