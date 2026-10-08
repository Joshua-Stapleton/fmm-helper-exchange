#!/usr/bin/env python3
"""Finite-pool helper optimization using necessary monotone reachability cuts.

Requires OR-Tools only for optimization. The closure/cut checker is stdlib.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
from common import core, closure, frontier


def valid_cut(data, prods, cut):
    ready = set(cut["reached"])
    core.require(all(type(i) is int and 0 <= i < len(data["forms"]) for i in ready),
                 "Invalid cut form index")
    required = {o for o, _ in data["outputs"]}
    core.require(set(range(data["inputs"])) <= ready and not required <= ready,
                 "Cut must include all inputs and omit a target")
    boundary = frontier(ready, prods)
    core.require(boundary == set(cut["boundary"]), "Cut boundary mismatch")
    core.require(not boundary & required, "Mandatory targets cannot be cut variables")
    return True


def optimize(path, directory, seconds=60, seed=507, grow_cuts=0, objective="count"):
    from ortools.sat.python import cp_model
    data, prods, incumbent, _ = core.load(path)
    directory.mkdir(parents=True, exist_ok=False)
    required = {o for o, _ in data["outputs"]}
    optional = set(range(data["inputs"], len(data["forms"]))) - required
    bound = len(incumbent) - 1
    budget = bound - len(required - set(range(data["inputs"])))
    model = cp_model.CpModel()
    xs = {i: model.new_bool_var(f"h{i}") for i in sorted(optional)}
    model.add(sum(xs.values()) <= budget)
    if objective == "overlap":
        model.maximize(100*sum(x for i, x in xs.items() if i in incumbent)
                       - sum(x for i, x in xs.items() if i not in incumbent))
    else:
        model.minimize(sum(xs.values()))
    for i, x in xs.items():
        model.add_hint(x, int(i in incumbent))
    start = time.monotonic()
    cuts = []
    status = "TIME_LIMIT"
    selected = None
    attempts = 0
    while time.monotonic() - start < seconds:
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.max_time_in_seconds = max(.001, seconds - (time.monotonic() - start))
        solver.parameters.random_seed = seed
        st = solver.solve(model)
        attempts += 1
        if st == cp_model.INFEASIBLE:
            status = "FINITE_POOL_INFEASIBLE"
            break
        if st not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            break
        helpers = {i for i, x in xs.items() if solver.value(x)}
        ready, raw = closure(data, prods, helpers)
        if required <= ready:
            selected = core.audit(raw, data, prods)
            core.require(len(selected) <= bound, "Budget error")
            core.export(selected, data, directory)
            status = "FOUND"
            break
        boundary = frontier(ready, prods)
        cut = dict(reached=sorted(ready), boundary=sorted(boundary))
        valid_cut(data, prods, cut)
        core.require(boundary <= optional and not boundary & helpers, "Invalid cut variables")
        model.add(sum(xs[i] for i in boundary) >= 1)
        cuts.append(cut)
        if grow_cuts and attempts % 10 == 0:
            for step in range(grow_cuts):
                # Grants construct another set for a necessary cut only;
                # they are never used to validate a returned candidate.
                trials = []
                options = sorted(boundary, key=lambda i: ((i+attempts*7) % len(data["forms"]), i))[:8]
                for i in options:
                    reached, _ = closure(data, prods, helpers, ready | {i})
                    if not required <= reached:
                        trials.append((len(reached), -i, reached))
                if not trials:
                    break
                ready = max(trials, key=lambda item: item[:2])[2]
                boundary = frontier(ready, prods)
                cut = dict(reached=sorted(ready), boundary=sorted(boundary), grown=True)
                valid_cut(data, prods, cut)
                core.require(boundary <= optional and not boundary & helpers, "Invalid grown cut")
                model.add(sum(xs[i] for i in boundary) >= 1)
                cuts.append(cut)
    result = dict(status=status, baseline_additions_signed=len(incumbent),
                  requested_additions_signed=bound, additions_signed=None if selected is None else len(selected),
                  helper_budget=budget, cuts=len(cuts), attempts=attempts, grow_cuts=grow_cuts, objective=objective,
                  seconds=time.monotonic() - start, data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  scope="Fixed supplied integer-form dictionary and productions; free signs. Timeout proves nothing.")
    (directory / "cuts.json").write_text(json.dumps(cuts, separators=(",", ":")) + "\n")
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--seed", type=int, default=507)
    parser.add_argument("--verify-cuts", type=Path)
    parser.add_argument("--grow-cuts", type=int, default=0)
    parser.add_argument("--objective", choices=("count", "overlap"), default="count")
    args = parser.parse_args()
    if args.verify_cuts:
        data, prods, _, _ = core.load(args.data)
        cuts = json.loads(args.verify_cuts.read_text())
        for cut in cuts:
            valid_cut(data, prods, cut)
        print(json.dumps(dict(status="CUT_IDENTITIES_PASS", cuts=len(cuts),
                             scope="Does not independently certify CP-SAT infeasibility")))
    else:
        core.require(args.out is not None and math.isfinite(args.seconds) and args.seconds > 0,
                     "A new output directory and positive finite time are required")
        core.require(args.grow_cuts >= 0, "Nonnegative cut-growth count required")
        print(json.dumps(optimize(args.data, args.out, args.seconds, args.seed, args.grow_cuts, args.objective), indent=2))


if __name__ == "__main__":
    main()
