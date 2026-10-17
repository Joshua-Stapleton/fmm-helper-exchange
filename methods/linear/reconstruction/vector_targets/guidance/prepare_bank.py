#!/usr/bin/env python3
"""Prepare deterministic guided and random schedules for a frozen native bank."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from select_removals import RemovalSelector


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--pool-base", type=Path)
    p.add_argument("--native-driver", type=Path)
    p.add_argument("--native-inputs", type=Path)
    p.add_argument("--out", type=Path, default=Path(__file__).parent / "bank")
    p.add_argument("--per-k", type=int, default=2)
    p.add_argument("--seed", type=int, default=17017)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.manifest.read_text())
    results = []
    for case in manifest["cases"]:
        start = time.perf_counter()
        cpath = Path(case["candidate"])
        c = json.loads(cpath.read_text())
        pool = None
        poolpath = None
        if args.pool_base and not case["transposed"]:
            paths = sorted(args.pool_base.glob(f"group*/*_{case['shape']}_*_{case['factor']}/pool.json"))
            for candidate in paths:
                loaded = json.loads(candidate.read_text())
                if loaded["inputs"] == c["inputs"] and loaded["target_matrix"] == c["target_matrix"]:
                    pool, poolpath = loaded, candidate
                    break
        selector = RemovalSelector(c, pool)
        actual_wires = [h["wire_id"] for h in selector.helpers]
        assert actual_wires == case["removable_helper_wire_indices"], case["id"] + " bank mapping mismatch"
        inspected = False
        if args.native_driver:
            textpath = args.native_inputs / (case["id"] + ".txt")
            inspection = json.loads(subprocess.check_output([str(args.native_driver), "--input", str(textpath), "--inspect"], text=True))
            expected = [dict(helper_index=h["native_helper_index"], wire=h["wire_id"],
                             coefficients=h["canonical_coefficients"]) for h in selector.helpers]
            assert inspection["helpers"] == expected, case["id"] + " native mapping mismatch"
            (args.out / (case["id"] + ".inspection.json")).write_text(json.dumps(inspection, indent=2) + "\n")
            inspected = True
        selected = selector.select(seed=args.seed, per_k=args.per_k)
        selected.update(case_id=case["id"], circuit_file=str(cpath),
                        pool_file=str(poolpath) if poolpath else None,
                        native_mapping_verified=inspected)
        schedules = {}
        for kind in ("guided", "random_controls"):
            dest = args.out / (case["id"] + "." + kind + ".csv")
            dest.write_text("\n".join(",".join(map(str, row["removed_native_helper_indices"]))
                                      for row in selected[kind]) + "\n")
            schedules[kind] = str(dest.resolve())
        selected.update(selector_wall_seconds=time.perf_counter() - start, schedules=schedules)
        dest = args.out / (case["id"] + ".selection.json")
        dest.write_text(json.dumps(selected, indent=2) + "\n")
        row = dict(case_id=case["id"], candidate=str(cpath), selection=str(dest.resolve()),
                   native_mapping_verified=inspected, schedules=schedules,
                   eligible_helpers=len(selector.helpers), guided_trials=len(selected["guided"]),
                   random_trials=len(selected["random_controls"]),
                   selector_wall_seconds=selected["selector_wall_seconds"],
                   pool_file=str(poolpath) if poolpath else None)
        results.append(row)
        print(json.dumps(row), flush=True)
    (args.out / "manifest.json").write_text(json.dumps(dict(cases=results, source_manifest=str(args.manifest),
        seed=args.seed, schema="guided-native-removal-bank-v1"), indent=2) + "\n")


if __name__ == "__main__":
    main()
