# Guided omission of helper-vector hints

This selector prepares experiments for Perminov's public `new-improvements`
branch. It does not replace his native reconstruction. That mode keeps the
original outputs required and uses retained helper **vectors** as optional
`wanted` hints. It eagerly inserts a wanted form once constructible, but stops
when the original outputs are complete and can prune unused hints. It need not
construct or retain every surviving hint. Omitted vectors may still be
rediscovered. It does not retain a partial
straight-line program or delete all descendants of an omitted gate.

## What is scored

For each proposed omission of 1–8 helper vectors:

1. **For the scoring surrogate only**, require every surviving hint vector and
   every original output. This is stronger than the native method.
2. Inspect exact alternative binary productions for the affected forms. A
   production is admitted only after replaying its integer coefficients.
3. Compute forward reachability from the inputs while forbidding the omitted
   forms. Prefer candidate omission sets that still allow the retained targets
   to be reached with few extra pool-only helpers and few broken direct
   dependencies. Shared ancestors are counted as a **union**, not once for
   every output that uses them.

The forward closure is exhaustive reachability in the supplied finite graph.
The associated acyclic derivation is chosen greedily and need not minimize its
gate count. The native solver is less restricted: it can leave surviving hints
unbuilt, prune them if unused, recreate omitted forms, introduce forms outside
this graph, or make a different choice of sums.
Scores therefore order native trials; they are neither global lower bounds nor
predictions of the native solver's final result. A matched timing study must
include the cost of preparing the scores.

There is a useful accounting identity for a normalized signed-wire binary
circuit, provided every original nonoutput helper is in the indexed hint list.
Write `k` for the omitted hints, `d` for surviving hints unused in the final
circuit, `b` for omitted hints that are recreated, and `q` for new helper forms
absent from the original circuit. Then `gain = k + d - b - q`. In particular,
the gain is **not** bounded by `k` in the native method. The stronger scoring
surrogate has `d=b=0` and therefore uses `k-q` as a heuristic target. The
`account_forms.py` checker independently replays two exact circuits, prunes to
their original outputs, counts distinct signed forms, and checks this identity.
Literal costs for paid sign corrections are separate.

## A small exact example

An initial four-addition circuit computes two outputs:

```
t0 = x0 + x1
y0 = t0 + x2
t1 = x1 + x2
y1 = t1 + x3
```

Omit `t0` as an auxiliary target, but retain `t1`, `y0` and `y1`. The exact
identity `y0 = x0 + t1` makes all three retained forms constructible without
`t0`, so they need only three additions. Omitting a helper from the chain
`t0 = x0+x1; y0 = t0+x2` instead leaves the required output unreachable in
that smaller form pool. The selector distinguishes these cases.

## Native indices and reproducibility

`removed_native_helper_indices` addresses the native branch's **dense filtered
helper list**, not the original wire IDs or gate indices. This list excludes
forms with fewer than two nonzero coordinates, excludes forms equal up to sign
to any original output, and keeps the first occurrence of each sign-canonical
form. Audit fields retain the corresponding raw wire and gate indices.

The frozen ten-case schedules are under `bank/manifest.json`. Each case has 16
guided rows and 16 seeded uniform-random controls: two rows at each omission
count from one through eight, with identical count ordering. The Python list
of helper indices, original wires, and complete canonical coefficient vectors
was compared with the actual native driver's `--inspect` output for every
case. All ten comparisons passed. Each selection JSON records its pool source,
scores, rationale and preparation time. Generated CSV rows are direct inputs
to native `--removed-file` in `--mode explicit`.

API:

```python
from select_removals import select_removals
result = select_removals(circuit, pool=optional_exact_pool,
                         k_values=range(1, 9), seed=17017, per_k=2)
```

Tests:

```sh
python3 -B -m unittest discover -s methods/linear/reconstruction/vector_targets/guidance -p 'test_*.py' -v
```

The fifteen tests cover native filtering/indexing, preservation of all required
outputs and auxiliary vectors in the stronger scoring surrogate, an exact reconnection, shared-ancestor counting,
rejection of a corrupted production, reproducible matched controls, and form
accounting when omitted hints are recreated and surviving hints are abandoned.
