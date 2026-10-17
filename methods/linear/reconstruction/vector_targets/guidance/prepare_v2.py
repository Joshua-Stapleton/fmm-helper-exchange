#!/usr/bin/env python3
"""Prepare two output-only v2 schedules without changing frozen v1 files."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time
from select_removals_v2 import OptionalSurvivorSelector

HERE = Path(__file__).resolve().parent
E = HERE.parent
CASES = ("old_3x6x8_V", "hl_4x4x16_V")


def load(path):
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default=",".join(CASES))
    parser.add_argument("--seconds", type=float, default=20)
    args = parser.parse_args()
    out = HERE / "v2"
    out.mkdir(exist_ok=True)
    bank = {c["id"]:c for c in load(E / "benchmarks/manifest.json")["cases"]}
    old = {c["case_id"]:c for c in load(HERE / "bank/manifest.json")["cases"]}
    manifest = []
    for cid in args.cases.split(","):
        start = time.perf_counter()
        c = dict(bank[cid])
        c['candidate']=str(E/c['candidate'])
        pool_path = HERE / "data" / (cid + ".pool.json")
        selector = OptionalSurvivorSelector(load(c["candidate"]), load(pool_path) if pool_path else None,
                                            max_abs=1, recreation_penalty_quarters=1)
        previous = load(HERE / "bank" / (cid + ".selection.json"))
        rng = random.Random(17017)
        catalogue = {k:[] for k in range(1,9)}
        for row in previous["guided"] + previous["random_controls"]:
            key = tuple(row["removed_native_helper_indices"])
            if key not in catalogue[row["k"]]:
                catalogue[row["k"]].append(key)
        for k in range(1,9):
            while len(catalogue[k]) < 12:
                key = tuple(sorted(rng.sample(range(len(selector.helpers)),k)))
                if key not in catalogue[k]:
                    catalogue[k].append(key)
        scored = {k:[] for k in range(1,9)}
        deadline = start + args.seconds
        expired = False
        for depth in range(12):
            for k in range(1,9):
                if time.perf_counter() >= deadline:
                    expired = True
                    break
                key = catalogue[k][depth]
                scored[k].append(selector.score(key))
            if expired:
                break
        guided = []
        for k in range(1,9):
            ranked = sorted(scored[k], key=lambda r:(r["priority"],r["removed_native_helper_indices"]))
            for rank,row in enumerate(ranked[:2],1):
                guided.append(dict(row,k=k,rank=rank,kind="guided_v2_catalogue"))
            # A deadline can stop before two sets at each count are scored.
            # Preserve the matched k schedule by using an explicitly labelled
            # frozen-v1 fallback; never pretend it received a v2 score.
            used = {tuple(r["removed_native_helper_indices"]) for r in ranked[:2]}
            for fallback in [r for r in previous["guided"] if r["k"]==k]:
                if len(used) >= 2:
                    break
                key = tuple(fallback["removed_native_helper_indices"])
                if key not in used:
                    guided.append(dict(fallback,kind="unscored_v1_budget_fallback",
                                       v2_proxy_scored=False,rank=len(used)+1))
                    used.add(key)
        result = dict(schema="perminov-vector-target-removal-selection-v2-catalogue",
                      guided=guided,helpers=selector.helpers,
                      eligible_native_helpers=len(selector.helpers),pool_forms=len(selector.forms),
                      pool_productions=len(selector.edges),selection_method="small fixed catalogue: frozen v1 guided and random controls, then seeded new random sets; rank only-output ancestor union proxies",
                      budget_seconds=args.seconds,deadline_reached=expired,
                      scored_candidate_sets=sum(map(len,scored.values())),
                      max_abs_proxy=1,recreation_penalty_quarters=1)
        assert [h["wire_id"] for h in selector.helpers] == c["removable_helper_wire_indices"]
        schedule = out / (cid + ".guided.csv")
        schedule.write_text("\n".join(",".join(map(str, r["removed_native_helper_indices"]))
                                     for r in result["guided"]) + "\n")
        result.update(case_id=cid, circuit_file=c["candidate"], pool_file=str(pool_path),
                      pool_sha256=hashlib.sha256(pool_path.read_bytes()).hexdigest() if pool_path else None,
                      native_mapping_preserved=True, selector_wall_seconds=time.perf_counter()-start,
                      score_pool_comparison_caveat=("v1 used incumbent-only pool; v2 uses previously available 9Oct pooled graph, so score and pool both differ" if cid == "old_3x6x8_V" else "v1 and v2 use identical exact production pool"))
        selected = out / (cid + ".selection.json")
        selected.write_text(json.dumps(result, indent=2) + "\n")
        entry = dict(case_id=cid, selection=str(selected), schedule=str(schedule),
                     schedule_sha256=hashlib.sha256(schedule.read_bytes()).hexdigest(),
                     pool_file=str(pool_path), selector_wall_seconds=result["selector_wall_seconds"],
                     trials=len(result["guided"]), source="frozen original benchmark incumbent, not newly improved results")
        manifest.append(entry)
        print(json.dumps(entry), flush=True)
    report = dict(schema="output-only-v2-native-removal-schedules-v1", cases=manifest,
                  v1_schedules_changed=False, seed=17017,
                  date="2026-10-17", source_sha256=hashlib.sha256((HERE / "select_removals_v2.py").read_bytes()).hexdigest(),
                  note="Post-main-study semantic refinement; does not consume winning native circuits or outcomes for score computation.")
    (out / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
