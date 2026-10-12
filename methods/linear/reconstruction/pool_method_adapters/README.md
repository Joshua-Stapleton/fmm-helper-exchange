# Testing Perminov's pool method

`run.py` calls the unchanged `HelperPool` implementation at upstream commit
`21906e043ab0d652b588864893a07199b915a8e7`. It takes native solutions with
internal substitutions and terminal expressions. Only the substitutions enter
the pool, as they do upstream. Use a separately obtained clean checkout of
[Perminov's solver](https://github.com/dronperminov/linear-expressions-optimization).
The thin driver builds without OpenMP and runs one completion worker.

`lookahead.py` tries four starting sets of sums at the same gate cap, chooses
one using its distance to the desired outputs, then lets the same solver finish
it. The first start exactly matches the ordinary weighted sampler, including
the randomly drawn cap. The three extra seeds and their construction time are
recorded. The score can prefer a start that finishes worse; the experiment did
not establish a general improvement. NumPy is optional and required only for
this score and `pair_probe.py`.

From the repository root, with `LEO` pointing to the clean pinned checkout:

```sh
adapter_dir=methods/linear/reconstruction/pool_method_adapters
study_dir=methods/linear/reconstruction/pool_method_study/data
python3 "$adapter_dir/lookahead.py" --leo "$LEO" \
  --bank "$study_dir/maps/5x5_U.native.json" \
  --matrix "$study_dir/maps/5x5_U.sms" --best 88 \
  --seed 30200 --solver-seed 30200 --out /tmp/fmm-four-starts --complete
```

`--binary` reuses a previously built driver with matching `.build.json`
metadata. `--driver-module` can select another thin adapter instead of the
sibling `run.py`. Outputs include the raw sampler responses, all paid prefixes,
selection scores, completion, exact replay and separate setup timings. The raw
reference count used for sampling is recorded separately from any better known
binary circuit; the latter is never silently inserted into the bank.

`target_walk.py` tests the complete backward-walk description separately. It
visits every desired output in a random order and builds its dependencies,
reusing sums already built for previous outputs. Cycles are rejected and failed
attempts are rolled back. This Python reproduction visits complete targets;
the published upstream initializer samples arbitrary helpers only up to a
partial gate cap.

For this separate experiment, `build_graph.py` explicitly expands every donor's
terminal expressions into paid binary additions. It preserves the original
native solution costs when computing quality weights. Its graph contains only
observed productions; it does not add every possible relation between forms.
Both the builder and complete walk use the standard library.

```sh
python3 "$adapter_dir/build_graph.py" \
  --bank "$study_dir/maps/5x5_U.native.json" \
  --matrix "$study_dir/maps/5x5_U.sms" --out /tmp/fmm-observed.json
python3 "$adapter_dir/target_walk.py" --graph /tmp/fmm-observed.json \
  --draws 10000 --seed 42000 --out /tmp/fmm-complete-walks
```

The saved study used 10,000 walks per condition on the same observed graph.
Quality weighting found 88 gates 1,861 times, with median 89. Equal donor
weights found a best of 90 and median 104. None improved the known 87-gate
circuit. Counts, proofs and bounded comparison data are in
[the study](../pool_method_study/README.md).

Every helper is paid and computed from the original inputs. Only opposite
signs are identified; coefficient magnitudes are preserved. The programs use
abstract signed wires. A claim about literal additions with fixed input and
output signs still needs the separate strict orientation check. These methods
do not establish rank, exponent or execution-time improvements.

`target_unlock.py` generates new ternary sums that open at least two target
constructions and can themselves be built from existing forms. It ranks them
by target coverage and available parents, then adds all exact binary relations
among the selected forms. No better circuit is supplied to the generator.
`run_one_new.py` separately checks the exact neighborhood in which one new
form replaces two incumbent auxiliary forms. It can reconnect all mandatory
targets; its exhausted result applies only to that starting circuit and that
specified neighborhood. Both tools use the repository root's exact pool
verifier, selectable through `--core`.

```sh
python3 "$adapter_dir/target_unlock.py" \
  --source "$study_dir/finite/observed.json" --cap 128 \
  --output /tmp/fmm-target-unlocks
python3 "$adapter_dir/run_one_new.py" \
  --source "$study_dir/finite/observed.json" --all-one-hop \
  --output /tmp/fmm-one-new-helper --seconds 10
```

Run the controls with:

```sh
python3 -B -m unittest discover -s "$adapter_dir" -p 'test_*.py' -v
```

Without NumPy, the scoring controls are explicitly skipped; paid replay and
walk controls still run. With NumPy, all 14 wrapper and walk controls run.
`NOTICE` supplies the MIT attribution for the adapted backward-walk structure;
`SOURCE_NOTICE.md` identifies the separate driver dependency.
`test_driver.py` checks the raw intake and numeric guards without dependencies;
its `--binary` or `--leo` option additionally runs four actual native API
controls. Those controls are explicitly skipped in a standard-library run.
