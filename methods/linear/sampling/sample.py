#!/usr/bin/env python3
"""Build the local driver against a separately obtained pinned LEO checkout.

No upstream implementation is vendored. Outputs include raw LEO solutions and
exactly replayed portable donor circuits accepted by the root make_pool.py.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pool_core", HERE.parents[2] / "run.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
PIN = "60272dc3cdd751ce53e43e5c021dbb6021fcbf51"
CONFIGS = [("distance", 0, 2, "0"), ("distance", 1, 2, ".01"),
           ("distance", 1, 4, ".01"), ("distance", 1, 8, ".01"),
           ("distance", 1, 2, ".1"), ("distance", 1, 2, "1"),
           ("default", 0, 2, "0"), ("default", 5, 2, "0"),
           ("default", 8, 2, "0"), ("default", 9, 2, "0"),
           ("cse", 0, 2, "0"), ("cse", 1, 2, "0"), ("cse", 2, 2, "0")]


def convert(solution, target):
    n = len(target[0])
    values = [[int(i == j) for j in range(n)] for i in range(n)]
    gates = []
    for g in solution["substitutions"]:
        a, sa, b, sb = (g[k] for k in ("i", "ai", "j", "aj"))
        core.index(a, len(values)); core.index(b, len(values)); core.sign(sa); core.sign(sb)
        values.append(core.combine(values[a], sa, values[b], sb))
        gates.append([a, sa, b, sb])
    outputs = []
    for expression in solution["expressions"]:
        terms = [(term["index"], term["value"]) for term in expression]
        core.require(terms, "Zero expressions are unsupported")
        for wire, sign in terms:
            core.index(wire, n + len(solution["substitutions"])); core.sign(sign)
        wire, sign = terms[0]
        for right, sr in terms[1:]:
            gates.append([wire, sign, right, sr])
            values.append(core.combine(values[wire], sign, values[right], sr))
            wire, sign = len(values)-1, 1
        outputs.append([wire, sign])
    actual = [[s*x for x in values[o]] for o, s in outputs]
    core.require(actual == target, "LEO donor differs from exact target")
    core.require(len(gates) == solution["additions"], "LEO gate count mismatch")
    return dict(gates=gates, outputs=outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leo", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seeds", default="800,801,802")
    parser.add_argument("--first-config-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    commit = subprocess.check_output(["git", "-C", str(args.leo), "rev-parse", "HEAD"], text=True).strip()
    core.require(commit == PIN, "LEO checkout must be pinned at " + PIN)
    subprocess.run(["git", "-C", str(args.leo), "diff", "--quiet", "HEAD", "--", "include", "src/leo"],
                   check=True)
    data, _, _, _ = core.load(args.data)
    target = data["target_matrix"]
    args.out.mkdir(parents=True, exist_ok=False)
    compiler = next((shutil.which(c) for c in ("c++", "g++", "clang++") if shutil.which(c)), None)
    core.require(compiler is not None, "C++17 compiler required")
    binary = args.out / "leo_sample"
    sources = sorted((args.leo / "src/leo").rglob("*.cpp"))
    subprocess.run([compiler, "-std=c++17", "-O3", "-I"+str(args.leo / "include"),
                    str(HERE / "sample_driver.cpp"), *map(str, sources), "-o", str(binary)], check=True)
    input_path = args.out / "matrix.txt"
    input_path.write_text(f"{len(target)} {len(target[0])}\n" +
                          "\n".join(" ".join(map(str, row)) for row in target) + "\n")
    records, donors = [], []
    for mode, preset, slack, savings in CONFIGS[:1] if args.first_config_only else CONFIGS:
        for seed in map(int, args.seeds.split(",")):
            name = f"{mode}_p{preset}_slack{slack}_save{savings}_s{seed}"
            dest = args.out / (name + ".json")
            command = [str(binary.resolve()), "--input", str(input_path.resolve()), "--output", str(dest.resolve()),
                       "--mode", mode, "--preset", str(preset), "--seed", str(seed),
                       "--support-slack", str(slack), "--savings", savings, "--inline", "1"]
            start = time.monotonic()
            record = dict(name=name, mode=mode, preset=preset, slack=slack, savings=savings, seed=seed)
            try:
                process = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout)
                core.require(process.returncode == 0, process.stderr)
                solution = json.loads(dest.read_text())
                donor = convert(solution, target)
                donor["name"] = name
                donors.append(donor)
                record.update(status="PASS", additions=len(donor["gates"]), diagnostic=process.stdout.strip())
            except subprocess.TimeoutExpired:
                record["status"] = "TIMEOUT"
            record["seconds"] = time.monotonic() - start
            records.append(record)
            (args.out / "report.json").write_text(json.dumps(records, indent=2) + "\n")
    (args.out / "donors.json").write_text(json.dumps(dict(inputs=data["inputs"], circuits=donors), separators=(",", ":"))+"\n")
    print(json.dumps(dict(attempts=len(records), exact_donors=len(donors), leo_commit=commit), indent=2))


if __name__ == "__main__":
    main()
