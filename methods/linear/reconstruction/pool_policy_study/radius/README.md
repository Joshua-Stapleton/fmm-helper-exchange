# Fixed-pool exchange radius and exact last-insertion filtering

This directory contains eight frozen exact linear-map pools, unchanged native source snapshots, observed search reports, and portable verification/rerun tools. Six current V anchors have counts 77, 110, 155, 204, 230, 280. Two historical controls have anchors 160 and 156, with known three-helper witnesses 158 and 155. Counts use the signed-wire model; this study makes no new literal paid-sign record claim.

## Verify without dependencies or searches

From the repository root:

```bash
python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/verify.py
python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/test_frontier.py
```

Verification needs only the Python standard library. It checks file hashes, all pool coefficient identities, acyclic incumbent/witness evaluations, every archived candidate's exact ordered map against its frozen pool, and the complete pair-enumeration counters. It neither invokes a compiler nor starts a timed search. The safety suite runs three graph tests by default and skips the native comparison. To opt into compiling the actual native filter and comparing it to an independent reference on 200 small randomized cyclic graphs:

```bash
FMM_RADIUS_NATIVE_TESTS=1 python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/test_frontier.py
```

The manifest checks the archived evidence; checking saved exhaustion reports is not an independent rerun of their enumeration. A small fresh enumeration and a historical known-triple replay can be requested explicitly:

```bash
python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/run_search.py --run --case u --engine exhaustive --radius 2 --seconds 1 --out /tmp/radius-u-pairs
python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/run_search.py --run --case u --engine exhaustive --radius 3 --goal 158 --known-triple --seconds 1 --out /tmp/radius-u-known-triple
```

Timed runs require a C++17 compiler. A temporary binary is built from the included source snapshot, and each result is replayed against the frozen ordered map through the repository's exact validator and the independent evaluator. No compiler output is kept in this directory. Output directories must not already exist. The historical replay deliberately prioritizes the known removed triple and is not an independent rediscovery or a new record.

Runners discover the repository by searching ancestors for both root `run.py` and `methods/linear/plateau.cpp`; alternatively pass `--repo` or set `FMM_HELPER_EXCHANGE_REPO`. Therefore defaults work when this directory is copied to `methods/linear/reconstruction/pool_policy_study/radius` without any machine-specific path.

## Reproduce the bounded protocols

All suite invocations require `--run`; omitting it performs only default verification. Each suite uses one native worker at a time:

```bash
python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/run_suite.py --run --suite radius --seconds 5 --out /tmp/radius-comparison
python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/run_suite.py --run --suite frontier --seconds 5 --out /tmp/radius-frontier
python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/run_suite.py --run --suite historical --seconds 10 --out /tmp/radius-historical
python3 -I -B methods/linear/reconstruction/pool_policy_study/radius/run_suite.py --run --suite historical-filtered --seconds 10 --out /tmp/radius-historical-filtered
```

`radius` uses six maps, two seeds, exhaustive radius two/radius three and plateau insertion limit six: 36 invocations, at most180 nominal search seconds. Fully exhausted pair searches stop early. `frontier` uses six maps, one paired seed and two engines: 12 five-second calls. `historical-goal` requests costs158/155 explicitly; `witness` prioritizes the known removed triples. Reruns can vary with machine load and compiler. These are bounded finite-pool experiments, not global optimization proofs.

## What is removed, and what is filtered?

The original root exchange engine explicitly disables up to three internal canonical helper forms, excluding final-output forms. Exact closure then tries every available production of each remaining permitted form. Descendants without an alternative derivation become unavailable automatically; they are not explicitly deleted as a separate operation. New helper forms can reconnect several descendants, and unused work is pruned after success.

The later plateau engine uses a different neighborhood: insert one to six currently reachable helper forms, then greedily try deleting every helper. Its parameter6 limits insertions, not removals. Perminov's optional wanted-vector hints are another distinct initialization strategy.

The exact final-insertion filter starts at missing outputs, traverses backward through every production of an allowed but unready form, stops at ready forms, and records disallowed boundary forms. Only viable forms on that boundary are tested for the last insertion. If one insertion completes an output, its actual forward derivation traces a causal path from the inserted form through previously allowed/unready forms to that output. The reverse walk necessarily reaches that inserted boundary form. Filtering outside this boundary therefore removes no successful last insertion.

The first insertion of a two-insertion repair is deliberately unfiltered: it may unlock a second new form on the boundary. A regression test includes that counterexample. Cycles in the rule graph are handled by a visited set; realized forward derivations remain acyclic.

## Observed scope

See `RESULTS.md` for exact numbers. On the six current anchors, all twelve pair-neighborhood runs exhaust without improvement; neither bounded triple search nor plateau lowers their current counts in this study. Two historical same-pool witnesses demonstrate that triple exchanges can improve an anchor with no improving single/pair exchange. This separates those finite neighborhoods; it is not a lower bound on the underlying unrestricted linear maps.

The safe filter increases triple starts by 3.17 to 10.06 times in the six paired five-second runs. The native counter increments when a triple is started, and the final triple at a timeout may be partial. These are small traversal-throughput observations, not complete-layer speedups or universal runtime multipliers. Blind filtered search rediscovers the known historical Wt155 circuit in 8.180 seconds, whereas the original same-seed ten-second search times out.

`SOURCES.json` records byte-identical source snapshots and line counts. `observed/` contains sanitized reports and raw native selections. `data/` contains the frozen coefficient pools and exact incumbents/witnesses. Report paths prefixed `archive/` label historical provenance; they are not required local paths. No binaries, caches or correspondence are included.
