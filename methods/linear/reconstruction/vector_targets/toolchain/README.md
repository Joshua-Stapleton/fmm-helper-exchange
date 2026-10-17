# Testing retained helper vectors with unmodified LEO

The source is the public `new-improvements` branch of
https://github.com/dronperminov/linear-expressions-optimization, pinned at
`7c8b59864e000bdc880938428d8a1991ec1f0bea`. The separately observed master
`4a6dc158731ab2f29510bc30ad1846544512fc6e` lacks vector seeding. The scratch
checkout is detached at the former commit. Its upstream files are unchanged.

`native_driver_v2` links the unchanged library sources directly. It has one
CPU worker and is compiled without OpenMP. `native_driver_v2.build.json`
records every upstream source hash, compiler command, executable hash and
its frozen adapter source, `native_driver_v2.source.cpp` (generated during a new build).

## What vector retention does

Upstream `Reducer::getIntermediates(targets, solution)` evaluates the donor's
substitutions. It discards forms with support below two, forms equal up to
sign to any original output, and repeated canonical forms. The first
remaining occurrence supplies the stable zero-based helper index. Removing
indices from this list does **not** remove their descendants.

The survivors go to `VectorCoveringSolver::solve(vector<Vector>)`. Starting
from the original inputs, the solver immediately computes a survivor when
two available wires can produce it. This may trigger a cascade. Original
outputs receive the same immediate treatment. The survivor forms are
optional; the distance scorer still scores only unfinished original outputs.
They are not extra mandatory outputs and are not free inputs. Every computed
sum is charged; the native end pass discards sums unused by final outputs.

This differs from a hard prefix: a prefix supplies both the intermediate
forms and their particular construction, while vector seeding supplies only
the forms and allows their constructions to change.

## Invocation

`adapter.py.write_input(path, target_matrix, donor)` validates and writes the
native text bundle. Donors may use this project's binary-circuit schema or
upstream raw `Solution` JSON. A fully materialized binary donor is a distinct
experimental boundary from an original native donor with terminal sums.

```
toolchain/native_driver_v2 --input toolchain/bound_control.txt \
  --mode explicit --removed 2,3,4,5 --bound 3 --seed 123 --draws 1 --seconds-per-draw 0.25 \
  --budget-seconds 6 --ignore-unused-bound 1 --jsonl --output results.jsonl
```

Run from the parent experiment directory. Modes are:

- `vectors`: upstream uniform removal of 1 through 8 eligible helper forms.
- `explicit`: removal indices supplied by `--removed 0,2` or
  `--removed-file choices.csv`, one comma-separated row per draw, cycled.
- `helpers`: upstream `HelperPool` supplies an executable prefix with a
  uniformly sampled cap of 10% through 50% of this frozen donor's additions.
- `mixed`: upstream's 50/50 choice between `helpers` and `vectors`.
- `retention`: the historical dependency-aware Bernoulli prefix policy,
  implemented in the adapter; `--retention 0.5` or `0.9`. This does not retain
  exactly that fraction of gates because removed parents remove descendants.
- `scratch`: a fresh native solve without either initializer.

`--inspect` emits each eligible helper's index, original wire and exact
canonical coefficients. `--savings 0` and `--savings 0.01` select the two
upstream distance-scorer weights; `--slack 2` is their common default.

Each JSONL draw is flushed after the native solver returns. Complete records
include raw native solutions and undergo native exact replay. Independent
Python `adapter.replay(solution, target_matrix)` replays every coefficient
and the ordered output signs. `null` means unresolved and is never a count.
The native API combines timeout, bound and exhausted candidates into one
unresolved return, so the wrapper does not invent a cause.

The batch budget includes input, pool and helper preparation. Each solve
gets the smaller of its per-draw budget and remaining batch budget. The
native timer is cooperative: candidate initialization, scoring, forced
cascades and finalization can exceed the limit between checks. Report actual
elapsed time. A longer external process cap can preserve previous completed
draws through JSONL if necessary; partial final lines must be ignored.

## Optional-helper bound control

`--ignore-unused-bound 1` uses native `usedCount + uncovered.size()` for its
bound; `0` uses `steps.size() + uncovered.size()`. Upstream's new CLI sets
the latter, while this experiment explicitly controls both.

`bound_control.txt` gives a small witness: the requested output is
`a+b+c+d`. The retained helper forms are `a+e` and `b+f`. They are derivable
immediately but can be unused in the final three-gate circuit. With bound
three, seed 123, and identical solver settings, mode `0` aborts while mode
`1` returns a valid three-gate result. See `bound_control.json`. Counting
optional intermediate forms before their eventual removal can therefore
abort a branch that would fit the final budget. The witness establishes
this pruning issue, not a general search-quality or runtime advantage.


See the parent README for the frozen benchmark and exact certificate checks.
