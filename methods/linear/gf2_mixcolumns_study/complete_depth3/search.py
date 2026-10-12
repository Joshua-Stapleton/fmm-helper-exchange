#!/usr/bin/env python3
"""Complete pure two-input XOR depth-three model for FIPS 197 MixColumns.

The completeness argument assumes free copies and unbounded fanout. No AND,
XNOR, scalar multipliers, hardware timing model, or integer sign equivalence.
Stdlib replay; optional single-worker OR-Tools search is capped at 180 seconds.
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


def dump(name, obj):
    if not ALLOW_WRITE:
        return
    (HERE / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def bits(value):
    return [1 << i for i in range(32) if (value >> i) & 1]


def output_splits(target):
    support = bits(target)
    pairs = set()
    if len(support) == 7:
        for part in itertools.combinations(support, 3):
            a = sum(part)
            pairs.add(tuple(sorted((a, target ^ a))))
        assert len(pairs) == 35
    elif len(support) == 5:
        for weight in (1, 2):
            for part in itertools.combinations(support, weight):
                a = sum(part)
                pairs.add(tuple(sorted((a, target ^ a))))
        # A three-bit/four-bit pair with weight-five XOR shares exactly one
        # cancelling bit, which must lie outside the output support.
        for outside in [1 << i for i in range(32) if not (target >> i) & 1]:
            for part in itertools.combinations(support, 2):
                a = outside | sum(part)
                pairs.add(tuple(sorted((a, target ^ a))))
        assert len(pairs) == 285
    else:
        raise ValueError("This complete model specializes to output weights five/seven")
    assert all(a ^ b == target and 1 <= a.bit_count() <= 4 and 1 <= b.bit_count() <= 4 for a, b in pairs)
    return sorted(pairs)


def build():
    begin = time.perf_counter()
    roots = {1 << i for i in range(32)}
    pair_forms = {a ^ b for a, b in itertools.combinations(sorted(roots), 2)}
    targets = audit.fips_masks()
    splits = {t: output_splits(t) for t in targets}
    endpoints = {v for choices in splits.values() for pair in choices for v in pair}
    triples = {v for v in endpoints if v.bit_count() == 3}
    quads = {v for v in endpoints if v.bit_count() == 4}
    values = sorted(roots | pair_forms | triples | quads | set(targets))
    idx = {v: i for i, v in enumerate(values)}
    edges = set()

    def add(c, a, b):
        ai, bi = sorted((idx[a], idx[b]))
        edges.add((idx[c], ai, bi))

    for pair in pair_forms:
        a, b = bits(pair)
        add(pair, a, b)
    for triple in triples:
        for root in bits(triple):
            add(triple, root, triple ^ root)
    for quad in quads:
        for group in itertools.combinations(bits(quad), 2):
            a = sum(group)
            b = quad ^ a
            if a < b:
                add(quad, a, b)
    for target, choices in splits.items():
        for a, b in choices:
            add(target, a, b)
    graph = {"field": "GF(2)", "inputs": 32, "forms": values,
             "root_indices": [idx[1 << i] for i in range(32)],
             "target_indices": [idx[t] for t in targets],
             "all_exact_productions": sorted(edges),
             "production_scope": "All depth-three output endpoints and dominated-normalized depth-two helper constructions"}
    inventory = {"forms": len(values), "roots": 32, "input_pair_forms": len(pair_forms),
                 "triple_forms": len(triples), "quad_forms": len(quads), "output_forms": len(targets),
                 "productions": len(edges), "output_productions": sum(map(len, splits.values())),
                 "weight5_output_choices_each": 285, "weight7_output_choices_each": 35,
                 "generation_wall_seconds": time.perf_counter() - begin,
                 "cancellation_case": "Triple/quad sharing exactly one bit outside the weight-five output support",
                 "completeness_scope": "Pure two-input XOR, depth <=3, free copies, unbounded fanout; argument described in README, not a formal independently certified theorem"}
    dump("catalogue.json", graph)
    dump("inventory.json", inventory)
    return graph, inventory


def independent_split_check(graph):
    # A separate exhaustive parent-mask enumeration, not the case generator.
    roots = [1 << i for i in range(32)]
    masks = set()
    for k in (1, 2, 3, 4):
        masks.update(sum(group) for group in itertools.combinations(roots, k))
    values = graph["forms"]
    targets = set(graph["target_indices"])
    listed = {values[i]: set() for i in targets}
    for c, a, b in graph["all_exact_productions"]:
        if c in targets:
            listed[values[c]].add(tuple(sorted((values[a], values[b]))))
    checks = []
    for target, supplied in sorted(listed.items()):
        expected = {tuple(sorted((a, a ^ target))) for a in masks if a ^ target in masks and a != a ^ target}
        if supplied != expected:
            raise ValueError("Incomplete output split generator")
        checks.append({"output_mask": target, "weight": target.bit_count(), "choices": len(expected), "pass": True})
    return {"parent_masks_enumerated": len(masks), "outputs_checked": len(checks),
            "all_split_sets_equal": True, "checks": checks}


def official_hint(graph):
    name = "aes-mixcols-xor97-depth3.circ.txt"
    provenance = json.loads((PARENT / "provenance.json").read_text())
    expected = next(r["sha256"] for r in provenance["sources"] if r["file"] == name)
    body = (PARENT / "sources" / name).read_bytes()
    if hashlib.sha256(body).hexdigest() != expected:
        raise ValueError("Official source hash mismatch")
    circuit = audit.parse_ncFF(body.decode())
    idx = {v: i for i, v in enumerate(graph["forms"])}
    chosen = set()
    for g in circuit["gates"]:
        a, b = sorted((idx[g["left_value"]], idx[g["right_value"]]))
        chosen.add((idx[g["value"]], a, b))
    hint = {"productions": sorted(chosen)}
    exact = audit.verify_witness(graph, hint)
    if (exact["gate_count"], exact["depth"]) != (97, 3):
        raise ValueError("Bad official hint")
    return hint


def solve(graph, seconds):
    import ortools
    from ortools.sat.python import cp_model
    begin = time.perf_counter()
    m = cp_model.CpModel()
    roots = set(graph["root_indices"])
    targets = set(graph["target_indices"])
    helpers = set(range(len(graph["forms"]))) - roots - targets
    selected = {i: m.NewBoolVar(f"u{i}") for i in sorted(helpers)}
    edges = graph["all_exact_productions"]
    choice = [m.NewBoolVar(f"p{i}") for i in range(len(edges))]
    incoming = {i: [] for i in helpers | targets}
    for var, (c, a, b) in zip(choice, edges):
        incoming[c].append(var)
        for parent in (a, b):
            if parent not in roots:
                if parent not in selected:
                    raise ValueError("Output form illegally used as a depth-two parent")
                # Explicit linear implication, exposed to the LP relaxation.
                m.Add(var <= selected[parent])
    for i in helpers:
        m.Add(sum(incoming[i]) == selected[i])
    for i in targets:
        m.Add(sum(incoming[i]) == 1)
    paid_aux = sum(selected.values())
    m.Minimize(paid_aux)
    m.Add(paid_aux <= 65)  # 97 total gates is the verified incumbent.
    hint = official_hint(graph)
    hint_edges = set(map(tuple, hint["productions"]))
    hint_helpers = {c for c, a, b in hint_edges} - targets
    for i, var in selected.items():
        m.AddHint(var, int(i in hint_helpers))
    for var, edge in zip(choice, edges):
        m.AddHint(var, int(tuple(edge) in hint_edges))
    body = str(m.Proto()).encode()
    (HERE / "depth3.model.pbtxt").write_bytes(body)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 12014
    solver.parameters.linearization_level = 2
    status = solver.Solve(m)
    result = {"status": solver.StatusName(status), "max_time_seconds": seconds, "workers": 1,
              "seed": 12014, "linearization_level": 2, "ortools_version": ortools.__version__,
              "solver_wall_seconds": solver.WallTime(), "model_and_solver_wall_seconds": time.perf_counter() - begin,
              "model_sha256": hashlib.sha256(body).hexdigest(), "best_aux_bound": solver.BestObjectiveBound(),
              "best_total_bound": 32 + solver.BestObjectiveBound(), "target_aux_count": 61, "target_total_count": 93,
              "statistics": solver.ResponseStats(), "model_scope": "Complete depth<=3 pure two-input XOR formulation under the argument in README"}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        witness = {"productions": [edge for var, edge in zip(choice, edges) if solver.Value(var)]}
        exact = audit.verify_witness(graph, witness)
        if exact["depth"] > 3 or exact["gate_count"] != 32 + solver.ObjectiveValue():
            raise ValueError("Incorrect gate/depth accounting")
        result["objective_aux"] = solver.ObjectiveValue()
        result["objective_total"] = exact["gate_count"]
        result["exact_replay"] = exact
        result["target93_met"] = exact["gate_count"] <= 93
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
        HERE = output_root / "complete_depth3"
        PARENT = output_root
        ALLOW_WRITE = True
    graph, inventory = build()
    split_check = independent_split_check(graph)
    dump("independent_split_check.json", split_check)
    print(json.dumps(inventory, indent=2), flush=True)
    print("Independent exhaustive output split check:", split_check["all_split_sets_equal"], flush=True)
    print("Verified official hint:", audit.verify_witness(graph, official_hint(graph)), flush=True)
    if args.search:
        print(json.dumps(solve(graph, args.seconds), indent=2), flush=True)
    elif (HERE / "depth3.witness.json").exists():
        print("Saved witness:", audit.verify_witness(graph, json.loads((HERE / "depth3.witness.json").read_text())))


if __name__ == "__main__":
    main()
