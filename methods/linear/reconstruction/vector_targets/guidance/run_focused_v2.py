#!/usr/bin/env python3
"""Matched frozen-incumbent native trials for v1/random/output-only v2.

Run only after the main study and initial native-pooling phase have finished.
No external publications, pushes, or messages. Every admitted candidate is
replayed exactly; raw completed solutions are retained, partial lines excluded.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
E = HERE.parent
PUBLIC = E.parents[3]
CASES = ("old_3x6x8_V", "hl_4x4x16_V")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


adapter = module("guided_v2_native_adapter", E / "toolchain/adapter.py")
common = module("guided_v2_common", PUBLIC / "methods/linear/reconstruction/common.py")
from account_forms import account


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_one(job):
    case, arm, seed, args, out = job
    folder = out / case["id"] / arm / str(seed)
    folder.mkdir(parents=True, exist_ok=False)
    raw_path = folder / "raw.jsonl"
    if arm == "guided_v2":
        schedule = HERE / "v2" / (case["id"] + ".guided.csv")
    elif arm == "guided_v1":
        schedule = HERE / "bank" / (case["id"] + ".guided.csv")
    else:
        schedule = HERE / "bank" / (case["id"] + ".random_controls.csv")
    command = [str(E / "toolchain/native_driver_v2"), "--input",
               str(E / "toolchain" / (case["id"] + ".txt")), "--mode", "explicit",
               "--seed", str(seed), "--draws", "1000", "--seconds-per-draw", str(args.per_draw),
               "--budget-seconds", str(args.seconds), "--jsonl", "--output", str(raw_path),
               "--ignore-unused-bound", "1", "--max-abs", "1", "--removed-file", str(schedule)]
    record = dict(case_id=case["id"], arm=arm, seed=seed, command=command,
                  input_sha256=sha(E / "toolchain" / (case["id"] + ".txt")),
                  incumbent_sha256=sha(case["candidate"]), schedule_sha256=sha(schedule),
                  native_binary_sha256=sha(E / "toolchain/native_driver_v2"),
                  initial_signed_additions=case["local_signed_additions"],
                  seconds_per_draw=args.per_draw, native_budget_seconds=args.seconds,
                  all_steps_bound_disabled=True, max_abs=1, native_worker_threads=1)
    dump(folder / "command.json", record)
    start = time.perf_counter()
    with (folder / "stdout.txt").open("w") as stdout, (folder / "stderr.txt").open("w") as stderr:
        try:
            proc = subprocess.run(command, stdout=stdout, stderr=stderr,
                                  timeout=args.seconds + args.per_draw + 2)
            record.update(returncode=proc.returncode, wrapper_timeout=False)
        except subprocess.TimeoutExpired:
            record.update(returncode=None, wrapper_timeout=True)
    record["native_process_wall_seconds"] = time.perf_counter() - start
    target = load(case["matrix"])
    original = load(case["candidate"])
    complete, invalid, incomplete = 0, 0, 0
    events, donor_by_hash = [], {}
    best = None
    best_event = None
    if raw_path.exists():
        content = raw_path.read_text()
        lines = content.splitlines(keepends=True)
    else:
        lines = []
    validation_start = time.perf_counter()
    for line in lines:
        if not line.endswith("\n"):
            incomplete += 1
            continue
        event = json.loads(line)
        if event.get("event") != "draw":
            continue
        entry = {k:v for k,v in event.items() if k != "solution"}
        if event.get("status") != "complete" or event.get("solution") is None:
            events.append(entry)
            continue
        try:
            raw = event["solution"]
            raw_cost = adapter.replay(raw, target)
            assert raw_cost == raw["additions"]
            converted = common.convert(raw, target)
            converted["inputs"] = len(target[0])
            candidate = common.normalize(converted)
            candidate["target_matrix"] = target
            assert common.exact_circuit(candidate, candidate["inputs"]) == target
            digest = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()
            donor_by_hash[digest] = candidate
            complete += 1
            entry.update(exact_status="PASS", raw_additions=raw_cost,
                         signed_binary_additions=len(candidate["gates"]), candidate_sha256=digest)
            if best is None or len(candidate["gates"]) < len(best["gates"]):
                best, best_event = candidate, entry
                dump(folder / "best_candidate.json", best)
                dump(folder / "best_form_accounting.json",
                     account(original, best, event["removed_helper_indices"]))
        except Exception as exc:
            invalid += 1
            entry.update(exact_status="FAILED", error=str(exc))
        events.append(entry)
    record.update(validation_wall_seconds=time.perf_counter() - validation_start,
                  completed_exact=complete, invalid_exact=invalid,
                  discarded_partial_lines=incomplete, draws=len(events),
                  distinct_exact_circuits=len(donor_by_hash),
                  best_generated_signed_additions=len(best["gates"]) if best else None,
                  best_with_incumbent_signed_additions=min(case["local_signed_additions"], len(best["gates"])) if best else case["local_signed_additions"],
                  best_event=best_event)
    donors = sorted(donor_by_hash.items(), key=lambda item:(len(item[1]["gates"]), item[0]))[:32]
    dump(folder / "donors.json", dict(inputs=case["inputs"],
        circuits=[dict(c, name=arm + "_" + h[:12]) for h,c in donors]))
    dump(folder / "events.json", events)
    dump(folder / "stats.json", record)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=HERE / "v2" / "native_study")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--seconds", type=float, default=10)
    p.add_argument("--per-draw", type=float, default=.5)
    p.add_argument("--cases", default=",".join(CASES))
    args = p.parse_args()
    assert 1 <= args.workers <= 3 and args.seconds > 0 and args.per_draw > 0
    args.out.mkdir(parents=True, exist_ok=False)
    requested = tuple(args.cases.split(","))
    cases = [c for c in load(E / "benchmarks/manifest.json")["cases"] if c["id"] in requested]
    for case in cases:
        for key in ('matrix','original_matrix','candidate','native','donors','native_donors','strict_incumbent'):
            case[key]=str(E/case[key])
        adapter.write_input(E/'toolchain'/(case['id']+'.txt'), load(case['matrix']), load(case['candidate']))
    jobs = [(case, arm, seed, args, args.out) for case in cases
            for arm in ("guided_v1", "balanced_random", "guided_v2")
            for seed in (1701701, 1702701)]
    selection_v1 = {c["case_id"]:c for c in load(HERE / "bank/manifest.json")["cases"]}
    selection_v2 = {c["case_id"]:c for c in load(HERE / "v2/manifest.json")["cases"]}
    protocol = dict(case_ids=[c["id"] for c in cases], arms=["guided_v1", "balanced_random", "guided_v2"],
                    seeds=[1701701, 1702701], jobs=len(jobs), max_workers=args.workers,
                    seconds_per_arm_seed=args.seconds, seconds_per_draw=args.per_draw,
                    max_abs=1, ignore_unused_bound=True, baseline="same frozen original incumbent in every job",
                    optional_seed_scope="surviving wanted hints may be skipped or pruned; original outputs only are mandatory",
                    selector_preparation_seconds={cid:dict(v1=selection_v1[cid]["selector_wall_seconds"],
                        v2=selection_v2[cid]["selector_wall_seconds"]) for cid in requested},
                    resource_scope="one native CPU worker per process; no more than three concurrent jobs; run after initial pooling phase",
                    claim_scope="finite posthoc mechanistic refinement trial; no global optimality, general speed superiority or paid-literal record claim")
    dump(args.out / "protocol.json", protocol)
    start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_one, job):job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = dict(case_id=job[0]["id"], arm=job[1], seed=job[2], status="WRAPPER_EXCEPTION", error=str(exc))
            results.append(record)
            dump(args.out / "progress.json", dict(finished=len(results), jobs=len(jobs), wall_seconds=time.perf_counter()-start, results=results))
            print(json.dumps({k:record.get(k) for k in ("case_id", "arm", "seed", "draws", "completed_exact", "best_with_incumbent_signed_additions", "invalid_exact", "status")}), flush=True)
    report = dict(status="COMPLETE", wall_seconds=time.perf_counter()-start,
                  protocol=protocol, results=results,
                  invalid_exact=sum(r.get("invalid_exact", 0) for r in results))
    dump(args.out / "report.json", report)


if __name__ == "__main__":
    main()
