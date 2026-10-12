#!/usr/bin/env python3
"""Informed GF(2) depth-three helper extension for FIPS 197 MixColumns.

All output-support subsets of weights 2..4; all primary-input pairs; all
observed forms. Never reads an improved oracle circuit. No random helpers.
Optional CP-SAT is single-worker and limited to 180 seconds.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
import time
import shutil
import sys
sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
spec = importlib.util.spec_from_file_location("mixcolumns_audit", PARENT / "probe.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


ALLOW_WRITE = False


def dump(name, value):
    if not ALLOW_WRITE:
        return
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def build():
    begin = time.perf_counter()
    old = json.loads((PARENT / "catalogue.json").read_text())
    original = set(old["forms"])
    roots = {1 << i for i in range(32)}
    pairs = {a ^ b for a, b in itertools.combinations(sorted(roots), 2)}
    targets = audit.fips_masks()
    subsets = set()
    for target in targets:
        support = [1 << i for i in range(32) if (target >> i) & 1]
        for weight in (2, 3, 4):
            for group in itertools.combinations(support, weight):
                subsets.add(sum(group))
    values = sorted(original | pairs | subsets)
    index = {v: i for i, v in enumerate(values)}
    root_indices = {index[v] for v in roots}
    target_indices = {index[v] for v in targets}
    all_edges, shallow_edges = [], []
    weights = [v.bit_count() for v in values]
    for a, b in itertools.combinations(range(len(values)), 2):
        c = index.get(values[a] ^ values[b])
        if c is None or c in root_indices:
            continue
        all_edges.append((c, a, b))
        wa, wb, wc = weights[a], weights[b], weights[c]
        # Any selected output parent must have support at most four at depth two.
        if c in target_indices:
            keep = wa <= 4 and wb <= 4
        elif wc == 2:
            # Direct root XOR dominates all other one-gate constructions.
            keep = wa == wb == 1
        elif wc == 3:
            keep = sorted((wa, wb)) == [1, 2]
        elif wc == 4:
            keep = wa == wb == 2
        else:
            keep = False  # Non-output support >4 cannot be a depth-two parent.
        if keep:
            shallow_edges.append((c, a, b))
    graph = {"field": "GF(2)", "inputs": 32, "forms": values,
             "root_indices": [index[1 << i] for i in range(32)],
             "target_indices": [index[t] for t in targets],
             "all_exact_productions": all_edges,
             "depth3_admissible_productions": shallow_edges}
    inventory = {"original_forms": len(original), "all_input_pairs": len(pairs),
                 "target_support_subsets_weights2to4": len(subsets),
                 "forms": len(values), "new_forms": len(set(values) - original),
                 "all_exact_productions": len(all_edges),
                 "depth3_admissible_productions": len(shallow_edges),
                 "generation_wall_seconds": time.perf_counter() - begin,
                 "generator": "All weight-2/3/4 output-support subsets plus all 496 input pairs plus observed forms",
                 "field": "GF(2)", "cancellation_allowed": True,
                 "restriction": "New forms are target-support subsets/input pairs; original non-subset forms retained. Arbitrary other masks are not searched."}
    dump("catalogue.json", graph)
    dump("inventory.json", inventory)
    return graph, inventory


def original_hint(graph):
    name = "aes-mixcols-xor97-depth3.circ.txt"
    provenance = json.loads((PARENT / "provenance.json").read_text())
    expected = next(r["sha256"] for r in provenance["sources"] if r["file"] == name)
    body = (PARENT / "sources" / name).read_bytes()
    if hashlib.sha256(body).hexdigest() != expected:
        raise ValueError("Official source hash mismatch")
    circuit = audit.parse_ncFF(body.decode())
    idx = {v: i for i, v in enumerate(graph["forms"])}
    result = []
    for gate in circuit["gates"]:
        a, b = sorted((idx[gate["left_value"]], idx[gate["right_value"]]))
        result.append((idx[gate["value"]], a, b))
    witness = {"productions": result}
    actual = audit.verify_witness(graph, witness)
    if actual["gate_count"] != 97 or actual["depth"] != 3:
        raise ValueError("Invalid starting circuit")
    if any(edge not in set(map(tuple, graph["depth3_admissible_productions"])) for edge in result):
        raise ValueError("A dominance rule removed a verified depth-three production")
    return witness


def solve(graph, seconds):
    import ortools
    from ortools.sat.python import cp_model
    begin = time.perf_counter()
    m = cp_model.CpModel()
    roots = set(graph["root_indices"])
    targets = set(graph["target_indices"])
    n = len(graph["forms"])
    edges = graph["depth3_admissible_productions"]
    used = [m.NewBoolVar(f"u{i}") for i in range(n)]
    takes = [m.NewBoolVar(f"p{i}") for i in range(len(edges))]
    incoming = [[] for _ in range(n)]
    for e, (c, a, b) in enumerate(edges):
        incoming[c].append(takes[e])
        m.Add(used[a] == 1).OnlyEnforceIf(takes[e])
        m.Add(used[b] == 1).OnlyEnforceIf(takes[e])
    # Admissible support layers strictly increase along dependencies:
    # roots -> pairs -> three/four-bit helpers -> five/seven-bit outputs.
    # Thus this model does not need a separate DAG/depth encoding.
    for i in range(n):
        if i in roots:
            m.Add(used[i] == 1)
        else:
            m.Add(sum(incoming[i]) == used[i])
        if i in targets:
            m.Add(used[i] == 1)
    paid = sum(used[i] for i in range(n) if i not in roots)
    m.Minimize(paid)
    m.Add(paid <= 97)
    hint = original_hint(graph)
    hint_edges = set(map(tuple, hint["productions"]))
    hint_used = roots | {edge[0] for edge in hint_edges}
    for i, var in enumerate(used):
        m.AddHint(var, int(i in hint_used))
    for edge, var in zip(edges, takes):
        m.AddHint(var, int(tuple(edge) in hint_edges))
    model = str(m.Proto()).encode()
    (HERE / "depth3.model.pbtxt").write_bytes(model)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 12013
    status = solver.Solve(m)
    result = {"status": solver.StatusName(status), "max_time_seconds": seconds,
              "workers": 1, "seed": 12013, "ortools_version": ortools.__version__,
              "solver_wall_seconds": solver.WallTime(), "model_and_solver_wall_seconds": time.perf_counter() - begin,
              "model_sha256": hashlib.sha256(model).hexdigest(),
              "best_bound": solver.BestObjectiveBound(), "statistics": solver.ResponseStats(),
              "scope": "Depth <=3 with output-support subset/input-pair/observed-form catalogue"}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        witness = {"productions": [edge for edge, var in zip(edges, takes) if solver.Value(var)]}
        result["objective"] = solver.ObjectiveValue()
        result["exact_replay"] = audit.verify_witness(graph, witness)
        if result["exact_replay"]["depth"] > 3:
            raise ValueError("Depth contract violated")
        result["target93_met"] = result["exact_replay"]["gate_count"] <= 93
        dump("depth3.witness.json", witness)
    dump("depth3.result.json", result)
    return result


def main():
    global HERE, ALLOW_WRITE
    global PARENT
    p = argparse.ArgumentParser()
    p.add_argument("--search", action="store_true")
    p.add_argument("--seconds", type=float, default=180)
    p.add_argument("--out", type=Path, help="Fresh output directory outside this study; required for mutation")
    args = p.parse_args()
    if not 0 < args.seconds <= 180:
        p.error("--seconds must be in (0,180]")
    if args.search:
        if args.out is None:
            p.error("Mutation requires --out with a fresh directory outside this study")
        source_root = PARENT.resolve()
        output_root = args.out.expanduser().resolve()
        if output_root == source_root or source_root in output_root.parents:
            p.error("--out must be outside the input study")
        if output_root.exists():
            p.error("--out must not already exist")
        shutil.copytree(source_root, output_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.model.pbtxt"))
        HERE = output_root / "target_subsets"
        PARENT = output_root
        ALLOW_WRITE = True
    graph, inventory = build()
    print(json.dumps(inventory, indent=2), flush=True)
    hint = original_hint(graph)
    print("Original depth-three circuit:", audit.verify_witness(graph, hint), flush=True)
    if args.search:
        print(json.dumps(solve(graph, args.seconds), indent=2), flush=True)
    else:
        existing = HERE / "depth3.witness.json"
        if existing.exists():
            print("Saved witness:", audit.verify_witness(graph, json.loads(existing.read_text())))


if __name__ == "__main__":
    main()
