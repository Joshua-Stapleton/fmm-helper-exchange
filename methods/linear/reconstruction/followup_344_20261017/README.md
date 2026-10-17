# A supplied 3x4x4 V map and a three-for-two exchange counterexample

Run the saved-data checks from the repository root:

```sh
python3 -I -B methods/linear/reconstruction/followup_344_20261017/verify.py
```

No third-party package is needed for verification. This checks the strict
41-addition original-map certificate, selected native donors and raw witness,
two exact frozen pools and their saved circuits, both CP-SAT feasible DAGs,
and a four-input seven-to-six-addition counterexample. It starts no searches.
Solver-reported lower bounds are not verified by this command.

The source matrix's comment reports 43 additions. Perminov's unmodified solver
finds 41 directly; our pooling, restarts and paid transpose return did not
improve it. Only V was supplied; no complete multiplication tensor is claimed.
See the [report](../../../../docs/344-and-exchange-20261017.md) and
[standalone literal certificate](../../../../certificates/map_3x4x4_V41_20261017/README.md).

## Reproduce the native search

Use the external source pin and adapter build instructions in
[vector_targets](../vector_targets/README.md). Then run, from this directory:

```sh
../vector_targets/toolchain/native_driver_v2 \
  --input native/scratch20_input.txt --mode scratch --seed 1719344 \
  --draws 10000 --seconds-per-draw .25 --budget-seconds 20 \
  --jsonl --output /tmp/344-native-draws.jsonl \
  --ignore-unused-bound 1 --max-abs 1 --min-remove 1 --max-remove 8
```

Each invocation uses one CPU worker. Timed stopping can change draw counts;
the published seed-1719348 numeric circuit verifies deterministically.
`native/evidence` includes 128 selected donors, a separate standard-library
verifier and a sanitized audit report. Full repetitive logs remain local;
the report records their hashes and the original full-audit counts.

## Reproduce target-driven form augmentation

`augment_pool.py` admits signed subsets of target rows; `--mode pairs` also
admits every signed two-input sum/difference. These forms are materialized in
a synthetic donor so the usual exact production enumeration can consider
them. They are candidate intermediate vectors, never free inputs. The search
still charges every live gate and retains the best original-map circuit.

```sh
python3 methods/linear/reconstruction/followup_344_20261017/augment_pool.py \
  --bank methods/linear/reconstruction/followup_344_20261017/native/early_donors.json \
  --mode pairs --out /tmp/344-augmented-search --seconds 30 --seed 172101
```

A C++17 compiler is needed for discovery; existing compatible executables can
be passed with `--relations` and `--plateau`. The output directory must be new.
Search, pool preparation and total elapsed times are reported separately.
The archived 179-form pool used the elementary normalized donor alone, while
the 390-form pool included the selected native donors. Repeating subsets with
the 64-donor bank therefore produces a different, larger pool.

## Exact DAG model and exchange question

The [optional CP-SAT model](exact/README.md) selects paid forms and exact binary
producers, with strict topological ranks to exclude cycles. It reported 41 as
the optimum in the 179-form dictionary; the 390-form run retained 41 at its
110-second limit. These are restricted searches, not a global SLP proof.

[Three-for-two example and verifier](three_for_two/README.md) explain why a
joint replacement need not admit two successive improving pair moves. The
four-input example permits any one-gate integer replacement in the negative
pair checks, rather than restricting replacements to a saved dictionary.
