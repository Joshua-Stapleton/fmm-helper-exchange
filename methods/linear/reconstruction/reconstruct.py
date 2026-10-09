#!/usr/bin/env python3
"""Dependency cuts or Bernoulli retention, then exact LEO partial reconstruction."""
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import random
import subprocess
import time

spec = importlib.util.spec_from_file_location("reconstruction_common", Path(__file__).with_name("common.py"))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def groups(data, max_removed=12, neighbors=8, max_seeds=3):
    n = data["inputs"]
    wires = list(range(n, n + len(data["gates"])))
    parents = {n+j: {g[0], g[2]} for j, g in enumerate(data["gates"])}
    result, seen = [], set()
    for seed in wires:
        near = {seed}
        for j, (a, _, b, _) in enumerate(data["gates"]):
            if a == seed or b == seed:
                near.update((n+j, a, b))
            if parents[seed] & {a, b}:
                near.add(n+j)
        near = sorted((near & set(wires)) - {seed},
                      key=lambda w: (-len(parents[seed] & parents[w]), w))[:neighbors]
        candidates = [(seed,)]
        for size in range(1, max_seeds):
            candidates.extend((seed, *others) for others in itertools.combinations(near, size))
        for seeds in candidates:
            removed, lost, kept = api.cut(data, seeds)
            key = tuple(sorted(removed))
            if key in seen or not lost or not 2 <= len(removed) <= max_removed:
                continue
            seen.add(key)
            result.append((len(removed)-len(lost), len(removed), len(lost),
                           tuple(sorted(seeds)), kept))
    result.sort(key=lambda row: (-row[0], row[2], row[1], row[3]))
    return result


def run(args):
    api.finite(args.seconds, "Time budget")
    api.finite(args.timeout, "Repair timeout")
    api.require(args.attempts > 0 and args.max_removed >= 2 and args.neighbors > 0
                and 1 <= args.max_seeds <= 3, "Invalid attempt/cut parameters")
    api.require(0 <= args.seed < 2**32 and args.seed + args.attempts <= 2**32, "Invalid seed range")
    api.require(args.retention is None or 0 <= args.retention <= 1, "Retention must be in [0,1]")
    api.require(args.savings is None or api.math.isfinite(args.savings) and args.savings >= 0,
                "Savings weight must be nonnegative and finite")
    api.require(args.slack is None or args.slack >= -1, "Support slack must be -1 or nonnegative")
    args.out.mkdir(parents=True, exist_ok=False)
    driver, build = api.binary(args, args.out, "repair")
    if args.prepared:
        target, kept = api.read_partial(args.prepared)
        source, baseline = args.prepared, None
        candidates = [(0, 0, 0, (), kept)]
        initial = []
        selection = "prepared_partial_circuit"
    else:
        source, target = api.candidate(args.candidate)
        normalized = api.normalize(source)
        baseline = len(normalized["gates"])
        initial = [dict(name="normalized_incumbent", gates=normalized["gates"], outputs=normalized["outputs"])]
        if args.retention is not None:
            candidates = [(0, 0, 0, (), normalized["gates"])] * args.attempts
            selection = "bernoulli_retention"
        elif args.cut_seeds:
            seeds = tuple(map(int, args.cut_seeds.split(",")))
            removed, lost, kept = api.cut(normalized, seeds)
            candidates = [(len(removed)-len(lost), len(removed), len(lost), seeds, kept)]
            selection = "explicit_dependency_cut"
        else:
            candidates = groups(normalized, args.max_removed, args.neighbors, args.max_seeds)
            if args.order == "random":
                random.Random(args.seed).shuffle(candidates)
            selection = args.order + "_dependency_cut_order"
        source = args.candidate
    probability = args.retention if args.retention is not None else 1.0
    max_abs = args.max_abs if args.max_abs is not None else max(abs(x) for row in target for x in row)
    api.require(max_abs >= 0, "Maximum coefficient must be nonnegative; zero disables its bound")
    records, donors, best = [], initial, baseline
    start = time.monotonic()
    first_improvement = None
    for index, (score, removed, lost, seeds, kept) in enumerate(candidates[:args.attempts]):
        remaining = args.seconds - (time.monotonic()-start)
        if remaining <= 0:
            break
        name = f"repair_{index:03d}"
        partial, raw = args.out/(name+".txt"), args.out/(name+".raw.json")
        api.write_partial(partial, target, kept)
        savings = args.savings if args.savings is not None else (0.01 if index % 2 else 0.0)
        slack = args.slack if args.slack is not None else (2, 4, 8)[index % 3]
        seed = args.seed + index
        record = dict(name=name, seeds=list(seeds), removed_gates=removed,
                      lost_target_forms=lost, optimistic_margin=score,
                      retained_gates=len(kept), seed=seed, savings=savings,
                      slack=slack, retention=probability)
        attempt = time.monotonic()
        try:
            command = [str(driver), str(partial), str(raw), str(seed), str(savings),
                       str(slack), str(probability), str(max_abs)]
            process = subprocess.run(command, capture_output=True, text=True,
                                     timeout=min(args.timeout, remaining))
            api.require(process.returncode == 0, process.stderr.strip())
            donor = api.convert(api.json_read(raw), target)
            donor["name"] = name
            donors.append(donor)
            count = len(donor["gates"])
            record.update(status="PASS", additions_signed=count, exact_map_verified=True)
            if best is None or count < best:
                best = count
                record["discovery_seconds"] = time.monotonic()-start
                if first_improvement is None:
                    first_improvement = record["discovery_seconds"]
                api.save_candidate(args.out/"best_candidate.json", donor, target)
                print(f"Best {count} at {record['discovery_seconds']:.3f} seconds", flush=True)
        except subprocess.TimeoutExpired:
            record["status"] = "TIMEOUT"
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            record.update(status="ERROR", diagnostic=str(error))
        record["seconds"] = time.monotonic()-attempt
        records.append(record)
        api.dump(args.out/"records.json", records)
        api.dump(args.out/"donors.json", dict(inputs=len(target[0]), circuits=donors))
    report = dict(selection=selection, source_sha256=api.hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                  build=build, baseline_additions_signed=baseline, best_additions_signed=best,
                  eligible_groups=len(candidates), attempts=len(records),
                  first_improvement_seconds=first_improvement, elapsed_seconds=time.monotonic()-start,
                  seconds=args.seconds, repair_timeout=args.timeout, seed=args.seed,
                  max_removed=args.max_removed, neighbors=args.neighbors, max_seeds=args.max_seeds,
                  free_signed_wires=True, scope="Heuristic reconstruction of one fixed linear map; no optimality proof")
    api.dump(args.out/"summary.json", report)
    api.dump(args.out/"donors.json", dict(inputs=len(target[0]), circuits=donors))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--candidate", type=Path)
    source.add_argument("--prepared", type=Path, help="Dense target plus compact partial gates")
    parser.add_argument("--leo", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--compiler")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=80)
    parser.add_argument("--timeout", type=float, default=2)
    parser.add_argument("--attempts", type=int, default=250)
    parser.add_argument("--seed", type=int, default=4000)
    parser.add_argument("--order", choices=("score", "random"), default="score")
    parser.add_argument("--retention", type=float, help="Bernoulli control on the complete incumbent")
    parser.add_argument("--cut-seeds", help="Explicit normalized gate wire indices, comma separated")
    parser.add_argument("--max-removed", type=int, default=12)
    parser.add_argument("--neighbors", type=int, default=8)
    parser.add_argument("--max-seeds", type=int, default=3)
    parser.add_argument("--savings", type=float)
    parser.add_argument("--slack", type=int)
    parser.add_argument("--max-abs", type=int)
    args = parser.parse_args()
    api.require(not (args.retention is not None and args.cut_seeds), "Retention control and explicit cuts are mutually exclusive")
    api.require(not (args.prepared and args.cut_seeds), "Prepared input and explicit cuts are mutually exclusive")
    print(json.dumps(run(args), indent=2))


if __name__ == "__main__":
    main()
