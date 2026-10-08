# Persistent exact-map reduction queue

`store.py` extracts the SQLite registry and worker from the September 9
scheme–transform–reducer experiment. It keeps exact coefficient domains,
ordinary/alternative coordinates, kernel/boundary costs, seeds, reducer hashes,
leases, failures and retained programs separate. It is a local research harness,
not an unattended scheduler. Python's standard library suffices for the bundled
direct and signed-CSE adapters.

```sh
python3 -B test_store.py
python3 -B demo.py
```

The demo uses a temporary database and shows that repeating a map/configuration/
seed request after reopening the database runs no extra reduction. Tests also
reject false circuits, wrong boundaries, F2 circuits in the Q namespace, changed
reducer implementations, and completion by an expired/replaced lease owner.

The registry hashes **literal exact maps**, not inferred GL-equivalence classes.
Every accepted circuit is expanded exactly and its emitted SLP parsed again.
`Store.variant` verifies all tensor coefficients and every alternative-basis
composition. `Store.export` reports both factor-wise portfolios and complete
same-reducer/same-seed evaluations. A portfolio is never credited to one reducer.

The cost model in this historical registry makes copies and signs free and
counts nonunit scalar operations separately. It does not replace the final
whole-algorithm strict sign/cost certification. The zero-nonunit portfolio board
intentionally omits circuits requiring paid scalar gates. A timeout/UNKNOWN or
an unexecuted queue row does not establish a lower bound.

Optional PLinOpt adapters are retained, without bundling PLinOpt. Register an
installed executable explicitly:

```python
reducer = store.reducer('plinopt_D', {
    'binary': '/absolute/path/to/optimizer',
    'loops': 100,
    'call_timeout_seconds': 3,
})
```

Use `plinopt_K` or `plinopt_G` for the other modes. The executable and adapter
contents are hashed into the reducer identity; changing either requires a new
registration. A larger time budget is a new configuration. Source and
installation instructions: [PLinOpt](https://github.com/jgdumas/plinopt).

The portable release deliberately excludes the old corpus importers and
campaign-specific neighborhood runner. Candidate generators can call
`variant`, `request`, `run`, and `export` explicitly; transformation primitives
are in `../transforms/`. This preserves the implemented cache/verification logic
without pretending the earlier experimental scheduler is a universal optimizer.
