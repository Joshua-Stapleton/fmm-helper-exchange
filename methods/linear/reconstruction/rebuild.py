#!/usr/bin/env python3
"""Experimental finite-pool delete/repair population; exact map replay on export."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time

spec = importlib.util.spec_from_file_location("reconstruction_common", Path(__file__).with_name("common.py"))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def run(args):
    api.finite(args.seconds, "Search budget")
    api.require(args.perturb > 0 and 0 <= args.seed < 2**32, "Invalid perturbation or seed")
    data, prods, incumbent, _ = api.core.load(args.data)
    edges = [(out, *row) for out in sorted(prods) for row in prods[out]]
    targets = sorted({out for out, _ in data["outputs"]})
    helpers = sorted(set(incumbent)-set(targets))
    args.out.mkdir(parents=True, exist_ok=False)
    text = f"{len(data['forms'])} {data['inputs']} {len(targets)} {len(helpers)} {len(edges)}\n"
    text += " ".join(map(str, targets))+"\n"+" ".join(map(str, helpers))+"\n"
    text += "".join(f"{out} {a} {b}\n" for out, a, sa, b, sb in edges)
    source, selection = args.out/"input.txt", args.out/"selection.txt"
    source.write_text(text)
    compiler = args.compiler or next((api.shutil.which(c) for c in ("c++", "g++", "clang++") if api.shutil.which(c)), None)
    api.require(args.binary is not None or compiler is not None, "A C++17 compiler or --binary is required")
    with tempfile.TemporaryDirectory(prefix="fmm-rebuild-") as temp:
        binary = args.binary.resolve() if args.binary else Path(temp)/"rebuild"
        if args.binary is None:
            subprocess.run([compiler, "-std=c++17", "-O3", str(api.HERE/"rebuild.cpp"), "-o", str(binary)], check=True, timeout=120)
        start = time.monotonic()
        try:
            process = subprocess.run([str(binary), str(source), str(args.seconds), str(args.seed),
                                      str(args.perturb), str(selection)], capture_output=True, text=True,
                                     timeout=args.seconds+10)
            api.require(process.returncode == 0, "Search failed: "+process.stderr)
            diagnostic, status = process.stderr, "COMPLETED_BUDGET"
        except subprocess.TimeoutExpired as error:
            diagnostic = error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr or ""
            status = "TIMEOUT_HARD"
        elapsed = time.monotonic()-start
    (args.out/"stderr.txt").write_text(diagnostic)
    report = dict(status=status, baseline_additions_signed=len(incumbent),
                  data_sha256=api.hashlib.sha256(args.data.read_bytes()).hexdigest(),
                  seconds=args.seconds, elapsed_seconds=elapsed, seed=args.seed, perturb=args.perturb,
                  free_signed_wires=True, scope="Heuristic finite pool; bounded deletion/closure repair, no optimality proof")
    if selection.exists():
        rows = selection.read_text().splitlines()
        api.require(rows and rows[0] == "FOUND", "Invalid selection header")
        selected = {}
        for line in rows[1:]:
            out, edge = map(int, line.split())
            api.core.index(edge, len(edges))
            actual, *production = edges[edge]
            api.require(actual == out and out not in selected, "Invalid indexed production")
            selected[out] = tuple(production)
        selected = api.core.audit(selected, data, prods)
        api.require(len(selected) < len(incumbent), "Search output is not a strict improvement")
        api.core.export(selected, data, args.out)
        report.update(additions_signed=len(selected), exact_map_verified=True)
    api.dump(args.out/"result.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--seed", type=int, default=32)
    parser.add_argument("--perturb", type=int, default=4)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--compiler")
    print(json.dumps(run(parser.parse_args()), indent=2))
