#!/usr/bin/env python3
"""Portable plateau/beam searches in an exact finite signed-integer form pool."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from common import core

HERE = Path(__file__).resolve().parent


def search(path, directory, seconds=60, seed=8, width=6, engine="plateau"):
    data, prods, incumbent, _ = core.load(path)
    edges = [(o, *p) for o in sorted(prods) for p in prods[o]]
    targets = {o for o, _ in data["outputs"]}
    helpers = sorted(set(incumbent) - targets)
    compiler = next((shutil.which(c) for c in ("c++", "g++", "clang++") if shutil.which(c)), None)
    core.require(compiler is not None, "A C++17 compiler is required")
    directory.mkdir(parents=True, exist_ok=False)
    content = f"{len(data['forms'])} {data['inputs']} {len(targets)} {len(helpers)} {len(edges)}\n"
    content += " ".join(map(str, sorted(targets))) + "\n" + " ".join(map(str, helpers)) + "\n"
    content += "".join(f"{o} {a} {b}\n" for o, a, sa, b, sb in edges)
    (directory / "input.txt").write_text(content)
    with tempfile.TemporaryDirectory(prefix="fmm-linear-") as temporary:
        binary = Path(temporary) / engine
        subprocess.run([compiler, "-O3", "-std=c++17", str(HERE / (engine + ".cpp")),
                        "-o", str(binary)], check=True, timeout=120)
        start = time.monotonic()
        command = [str(binary), str(directory / "input.txt"), str(seconds), str(seed),
                   str(width), str(directory / "selection.txt")]
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=seconds + 30)
            core.require(process.returncode == 0, "Engine failure: " + process.stderr)
            diagnostic = process.stderr
            status = "COMPLETED" if "TIME_LIMIT" not in diagnostic else "TIME_LIMIT"
        except subprocess.TimeoutExpired as error:
            diagnostic = error.stderr or ""
            if isinstance(diagnostic, bytes):
                diagnostic = diagnostic.decode()
            status = "TIME_LIMIT_HARD"
        elapsed = time.monotonic() - start
    (directory / "stderr.txt").write_text(diagnostic)
    result = dict(engine=engine, seed=seed, width_or_perturbation=width,
                  budget_seconds=seconds, elapsed_seconds=elapsed, status=status,
                  baseline_additions_signed=len(incumbent),
                  data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  free_signed_wires=True, diagnostic=diagnostic.strip(),
                  scope="Finite pool; heuristic search. Beam pruning is not exhaustive.")
    selected = None
    selection = directory / "selection.txt"
    if selection.exists():
        lines = selection.read_text().splitlines()
        core.require(lines[0] == "FOUND", "Unexpected engine selection header")
        raw = {}
        for line in lines[1:]:
            out, edge = map(int, line.split())
            core.index(edge, len(edges))
            oo, *production = edges[edge]
            core.require(oo == out and out not in raw, "Invalid indexed production")
            raw[out] = tuple(production)
        selected = core.audit(raw, data, prods)
        core.require(len(selected) < len(incumbent), "Candidate is not a strict improvement")
        core.export(selected, data, directory)
        result.update(additions_signed=len(selected), exact_map_verified=True)
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--engine", choices=("plateau", "beam"), default="plateau")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--seed", type=int, default=8)
    parser.add_argument("--width", type=int, default=6,
                        help="Maximum inserted helpers for plateau; retained beam width for beam")
    args = parser.parse_args()
    core.require(math.isfinite(args.seconds) and args.seconds > 0, "Positive finite time required")
    core.require(args.width > 0 and 0 <= args.seed < 2**32, "Invalid width or seed")
    print(json.dumps(search(args.data, args.out, args.seconds, args.seed, args.width, args.engine), indent=2))


if __name__ == "__main__":
    main()
