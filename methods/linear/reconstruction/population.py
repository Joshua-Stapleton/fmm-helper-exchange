#!/usr/bin/env python3
"""Export exact donor populations from bounded LEO partial-restart rounds."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import time

spec = importlib.util.spec_from_file_location("reconstruction_common", Path(__file__).with_name("common.py"))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def run(args):
    api.finite(args.seconds, "Population budget")
    api.require(args.rounds > 0 and args.iterations > 0 and args.first_cse >= 0
                and args.export_gap >= -1 and 0 <= args.seed < 2**32, "Invalid population parameters")
    target = api.read_matrix(args.matrix)
    args.out.mkdir(parents=True, exist_ok=False)
    driver, build = api.binary(args, args.out, "population")
    raw = args.out/"raw"
    raw.mkdir()
    dense = args.out/"matrix.txt"
    dense.write_text(f"{len(target)} {len(target[0])}\n"
                     + "\n".join(" ".join(map(str, row)) for row in target) + "\n")
    command = [str(driver), "--input", str(dense), "--out", str(raw),
               "--rounds", str(args.rounds), "--iterations", str(args.iterations),
               "--seed", str(args.seed), "--preset", args.preset,
               "--first-cse", str(args.first_cse), "--export-gap", str(args.export_gap)]
    start = time.monotonic()
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=args.seconds)
        log = process.stdout + "\n" + process.stderr
        status = "COMPLETED" if process.returncode == 0 else "ERROR"
    except subprocess.TimeoutExpired as error:
        def text(value):
            return value.decode() if isinstance(value, bytes) else value or ""
        log = text(error.stdout) + "\n" + text(error.stderr)
        status = "TIMEOUT"
    elapsed = time.monotonic()-start
    (args.out/"population.log").write_text(log)
    donors, records, seen = [], [], set()
    for path in sorted(raw.glob("*.json")):
        try:
            donor = api.convert(api.json_read(path), target)
            key = json.dumps([donor["gates"], donor["outputs"]], separators=(",", ":"))
            if key not in seen:
                seen.add(key)
                donor["name"] = path.stem
                donors.append(donor)
            records.append(dict(file=path.name, status="PASS", additions_signed=len(donor["gates"])))
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            records.append(dict(file=path.name, status="ERROR", diagnostic=str(error)))
    api.dump(args.out/"donors.json", dict(inputs=len(target[0]), circuits=donors))
    api.dump(args.out/"records.json", records)
    if donors:
        best = min(donors, key=lambda circuit: len(circuit["gates"]))
        api.save_candidate(args.out/"best_candidate.json", best, target)
    report = dict(status=status, build=build,
                  source_sha256=api.hashlib.sha256(args.matrix.read_bytes()).hexdigest(),
                  seed=args.seed, rounds=args.rounds, iterations=args.iterations,
                  preset=args.preset, first_round_cse=args.first_cse, export_gap=args.export_gap,
                  seconds=args.seconds, elapsed_seconds=elapsed,
                  exact_unique_donors=len(donors), raw_exports=len(records),
                  best_additions_signed=min((len(circuit["gates"]) for circuit in donors), default=None),
                  free_signed_wires=True,
                  scope="Completed restart-round populations only; timeout is not an exclusion")
    api.dump(args.out/"summary.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True, help="SMS, dense text, or target_matrix JSON")
    parser.add_argument("--leo", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--compiler")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=6)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--seconds", type=float, default=75)
    parser.add_argument("--seed", type=int, default=20261009)
    parser.add_argument("--preset", choices=("distance", "default"), default="distance")
    parser.add_argument("--first-cse", type=int, default=10)
    parser.add_argument("--export-gap", type=int, default=-1,
                        help="-1 exports all population members; otherwise keep costs within this gap of best")
    print(json.dumps(run(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
