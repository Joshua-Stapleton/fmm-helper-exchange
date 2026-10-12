# Archive batch experiments

`archive_batch.py` is the portable version of the October 12 batch harness.
It runs CSE, vector cover, 50% and 90% retention, dependency cuts, residual
output forests, the actual weighted HelperPool, and finite-pool reconnection.
Each map runs sequentially, with one upstream solver thread. The final result
must pass fixed-sign orientation and integer replay of the literal program.
There is no basis change.

All executable paths are explicit. Run these commands from the repository
root. Python's standard library suffices for preparation; final orientation
requires OR-Tools in the Python supplied by `--runtime-python`.

Required tools:

* `--leo-cli`: upstream `reduce`, built from clean commit
  `2abd2fd8f15dc1c97dd24777515324f865e77504`.
* `--repair-binary`: the published repair adapter, built against that same
  clean upstream commit with `build.py --driver repair`.
* `--pool-binary`: `methods/linear/pool_relations.cpp`, compiled with C++17.
* `--weighted-binary`: `pool_method_adapters/pool_driver.cpp`, built against
  clean commit `21906e043ab0d652b588864893a07199b915a8e7`. Its matching
  `.build.json` metadata is required by the adapter.

The two upstream commits require separate clean checkouts. The weighted
adapter's existing `run.py --leo ... --sample-only ...` command builds its
driver and metadata into the requested new output directory. See
[the adapter instructions](pool_method_adapters/README.md). For the other
native tools:

```sh
python3 -B methods/linear/reconstruction/build.py \
  --leo /path/to/leo-repair --driver repair --out /path/to/repair
c++ -O3 -std=c++17 methods/linear/pool_relations.cpp \
  -o /path/to/pool_relations
```

Supply an input directory containing SMS maps whose filenames end in `_U`,
`_V`, or `_W`. A JSON manifest may provide `filename`, `source_sha256`,
`scheme`, `factor`, `baseline_annotation`, and an optional `candidate` path.
Relative candidate paths resolve from the manifest's directory. A candidate
is accepted only if it computes the exact ordered input map.
Optional `matrix` and `historical_source` fields select the exact SMS and
original source JSON; relative paths also resolve from the manifest directory.
The certificate bundle includes `campaign_group_a.json`, `campaign_group_b.json`
and `campaign_group_c.json` with the exact starting circuits and original order.
Their base seeds were 43012000, 44012000 and 45012000 respectively; each
map adds 1000 times its zero-based position to that seed. These manifests avoid
requiring a separate history checkout. Supply the extracted certificate folder
as `--inputs` and one of these files as `--manifest`, plus the binaries below.

`--history` optionally supplies the original reduced scheme JSON directory,
with files named `SCHEME.json`. The October 12 experiment used those original
circuits and, where available, previously certified incumbents. Omitting both
history and supplied candidates starts from a paid naive circuit instead and
changes the experiment. The annotated source counts are not certificates.

```sh
python3 -B methods/linear/reconstruction/archive_batch.py \
  --inputs /path/to/sms-maps --manifest /path/to/manifest.json \
  --history /path/to/original-reduced-json --out /path/to/new-batch \
  --leo-cli /path/to/reduce --repair-binary /path/to/repair \
  --pool-binary /path/to/pool_relations \
  --weighted-binary /path/to/pool_driver \
  --runtime-python /path/to/python-with-ortools \
  --method-seconds 4 --call-timeout 1 --attempts 12 \
  --search-seconds 8 --orientation-seconds 5 --strict-candidates 6 \
  --seed 44012000
```

`--files NAME.sms ...` selects specific maps. `--prepare-only` verifies and
records starting circuits without running any search and does not require
the four executables. Output directories must be new.

The weighted stage makes two completion calls, each capped at 1.5 seconds,
using default temperature 1 and mixing 0.01. Its intake is explicitly fully
binary: every expanded terminal sum is paid and available as a donor helper.
This differs from the earlier study that preserved the native distinction
between internal substitutions and terminal expressions. The two weighted
calls are an additional search stage, not a matched timing control against
the retention runs. Completion failure is not an impossibility result.

For each W case, the batch saves the original transpose-search donors. The
optional second pass pools those donors directly, transposes the resulting
circuit back with every accumulation charged, and keeps only a strictly
better final literal program:

```sh
python3 -B methods/linear/reconstruction/archive_wt_extra.py \
  --source /path/to/new-batch/02_SCHEME_W \
  --out /path/to/new-batch/02_SCHEME_W/adjoint_extra \
  --pool-binary /path/to/pool_relations \
  --runtime-python /path/to/python-with-ortools \
  --seconds 8 --orientation-seconds 5 --seed 44012500
```

The scripts preserve completed donor circuits, partial-call records, seeds,
the pooled relations, separate timings, and exact literal certificates.
Intermediate search counts allow signed wires; only `best.slp` with a PASS
literal verification is a final fixed-sign addition count. Timing depends on
machine load, and bounded heuristic runs need not reproduce the same count.
