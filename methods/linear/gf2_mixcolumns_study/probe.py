#!/usr/bin/env python3
"""Exact GF(2) replay and bounded finite-catalogue MixColumns reconstruction.

Standard-library verification; optional --search requires OR-Tools.
Only two-input XOR gates, no sign equivalence, free helpers or integer arithmetic.
"""
import argparse
import hashlib
import json
import re
import time
import shutil
import sys
sys.dont_write_bytecode = True
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = "113aec82e939be46ad72522032df90cb4355f46c"
PATH = "data/slp/aes/aes-mixcols/"
FILES = [(88, 5), (90, 4), (97, 3)]
BYTE_MATRIX = ((2, 3, 1, 1), (1, 2, 3, 1), (1, 1, 2, 3), (3, 1, 1, 2))


ALLOW_WRITE = False


def dump(path, obj):
    if not ALLOW_WRITE:
        return
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def xtime(x):
    assert 0 <= x < 256
    return ((x << 1) ^ (0x11B if x & 0x80 else 0)) & 255


def mix_column(column):
    out = []
    for row in BYTE_MATRIX:
        y = 0
        for c, x in zip(row, column):
            y ^= x if c == 1 else xtime(x) if c == 2 else xtime(x) ^ x
        out.append(y)
    return out


def fips_masks():
    # Independently construct all 32 columns of the FIPS 197 byte map.
    masks = [0] * 32
    for bit in range(32):
        column = [0] * 4
        column[bit // 8] = 1 << (bit % 8)
        image = mix_column(column)
        for byte, value in enumerate(image):
            for r in range(8):
                if (value >> r) & 1:
                    masks[8 * byte + r] |= 1 << bit
    assert mix_column([0xDB, 0x13, 0x53, 0x45]) == [0x8E, 0x4D, 0xA1, 0xBC]
    return masks


def parse_ncFF(text):
    if not text.startswith("%NCFF-0.1-2026"):
        raise ValueError("Unsupported circuit format")
    env = {"x" + str(i): 1 << i for i in range(32)}
    depth = {key: 0 for key in env}
    gates = []
    in_slp = False
    completed = False
    for raw in text.splitlines():
        line = raw.split("%", 1)[0].strip()
        if line == "begin SLP":
            if in_slp or completed:
                raise ValueError("Multiple SLP sections")
            in_slp = True
        elif line == "end SLP":
            in_slp = False
            completed = True
        elif in_slp and line:
            match = re.fullmatch(r"XOR\s+([xty]\d+)\s+([xty]\d+)\s+([xty]\d+)", line)
            if not match:
                raise ValueError("Only two-input XOR gates allowed: " + line)
            dest, left, right = match.groups()
            if dest in env or left not in env or right not in env or left == right:
                raise ValueError("Invalid dependency or gate: " + line)
            value = env[left] ^ env[right]
            env[dest] = value
            depth[dest] = 1 + max(depth[left], depth[right])
            gates.append({"name": dest, "left": left, "right": right, "value": value,
                          "left_value": env[left], "right_value": env[right], "depth": depth[dest]})
    if not completed or any("y" + str(i) not in env for i in range(32)):
        raise ValueError("Incomplete circuit")
    outputs = [env["y" + str(i)] for i in range(32)]
    if outputs != fips_masks():
        raise ValueError("Not the FIPS 197 forward MixColumns map")
    return {"gates": gates, "outputs": outputs, "gate_count": len(gates),
            "depth": max(depth["y" + str(i)] for i in range(32))}


def fetch():
    (HERE / "sources").mkdir(exist_ok=True)
    records = []
    for count, depth in FILES:
        name = f"aes-mixcols-xor{count}-depth{depth}.circ.txt"
        url = f"https://raw.githubusercontent.com/usnistgov/Circuits/{PIN}/{PATH}{name}"
        body = urllib.request.urlopen(url, timeout=30).read()
        (HERE / "sources" / name).write_bytes(body)
        records.append({"file": name, "sha256": hashlib.sha256(body).hexdigest(), "url": url})
    dump(HERE / "provenance.json", {"repository": "https://github.com/usnistgov/Circuits",
         "commit": PIN, "sources": records, "standard": "https://doi.org/10.6028/NIST.FIPS.197-upd1",
         "retrieved_date": "2026-10-12", "source_attribution": "NIST circuit complexity team"})


def catalogue(circuits):
    roots = {1 << i for i in range(32)}
    forms = roots | {g["value"] for circuit in circuits for g in circuit["gates"]}
    assert 0 not in forms
    values = sorted(forms)
    indices = {v: i for i, v in enumerate(values)}
    observed = set()
    for circuit in circuits:
        for g in circuit["gates"]:
            a, b = sorted((indices[g["left_value"]], indices[g["right_value"]]))
            observed.add((indices[g["value"]], a, b))
    edges = []
    for a in range(len(values)):
        for b in range(a + 1, len(values)):
            c = indices.get(values[a] ^ values[b])
            if c is not None and values[c] not in roots:
                edges.append((c, a, b))
    return {"field": "GF(2)", "inputs": 32, "forms": values,
            "root_indices": [indices[1 << i] for i in range(32)],
            "target_indices": [indices[v] for v in fips_masks()],
            "observed_productions": sorted(observed), "all_exact_productions": edges}


def verify_witness(graph, witness):
    roots = set(graph["root_indices"])
    outputs = graph["target_indices"]
    selected = {int(c): (int(a), int(b)) for c, a, b in witness["productions"]}
    if len(selected) != len(witness["productions"]):
        raise ValueError("Duplicate helper production")
    allowed = set(map(tuple, graph["all_exact_productions"]))
    memo = {i: (graph["forms"][i], 0) for i in roots}
    active = set()
    used = set()

    def visit(i):
        if i in memo:
            return memo[i]
        if i in active or i not in selected:
            raise ValueError("Cycle or missing production")
        active.add(i)
        a, b = selected[i]
        if (i, a, b) not in allowed:
            raise ValueError("Production outside catalogue")
        va, da = visit(a)
        vb, db = visit(b)
        if va ^ vb != graph["forms"][i]:
            raise ValueError("GF(2) identity mismatch")
        active.remove(i)
        used.add(i)
        memo[i] = (va ^ vb, 1 + max(da, db))
        return memo[i]

    actual = [visit(i) for i in outputs]
    if [v for v, d in actual] != fips_masks():
        raise ValueError("Output map mismatch")
    return {"exact_fips_map": True, "gate_count": len(used),
            "depth": max(d for v, d in actual), "selected_count": len(selected),
            "unused_selected": len(selected) - len(used)}


def search(graph, name, seconds, max_depth, hint_circuit):
    from ortools.sat.python import cp_model
    import ortools
    begin = time.perf_counter()
    m = cp_model.CpModel()
    n = len(graph["forms"])
    roots = set(graph["root_indices"])
    targets = set(graph["target_indices"])
    edges = graph["all_exact_productions"]
    used = [m.NewBoolVar(f"u{i}") for i in range(n)]
    ranks = [m.NewIntVar(0, max_depth, f"d{i}") for i in range(n)]
    choices = [m.NewBoolVar(f"p{e}") for e in range(len(edges))]
    incoming = [[] for _ in range(n)]
    for e, (c, a, b) in enumerate(edges):
        take = choices[e]
        incoming[c].append(take)
        m.Add(used[a] == 1).OnlyEnforceIf(take)
        m.Add(used[b] == 1).OnlyEnforceIf(take)
        m.Add(ranks[c] >= ranks[a] + 1).OnlyEnforceIf(take)
        m.Add(ranks[c] >= ranks[b] + 1).OnlyEnforceIf(take)
    for i in range(n):
        if i in roots:
            m.Add(used[i] == 1)
            m.Add(ranks[i] == 0)
        else:
            m.Add(sum(incoming[i]) == used[i])
            m.Add(ranks[i] >= 1).OnlyEnforceIf(used[i])
            m.Add(ranks[i] == 0).OnlyEnforceIf(used[i].Not())
        if i in targets:
            m.Add(used[i] == 1)
    paid = sum(used[i] for i in range(n) if i not in roots)
    m.Minimize(paid)
    # A verified original circuit supplies a feasible upper bound and hint.
    idx = {v: i for i, v in enumerate(graph["forms"])}
    hint_edges = set()
    hint_depth = {i: 0 for i in roots}
    for gate in hint_circuit["gates"]:
        c = idx[gate["value"]]
        a, b = sorted((idx[gate["left_value"]], idx[gate["right_value"]]))
        hint_edges.add((c, a, b))
        hint_depth[c] = gate["depth"]
    assert len(hint_edges) == hint_circuit["gate_count"]
    hint_used = roots | {e[0] for e in hint_edges}
    for i in range(n):
        m.AddHint(used[i], int(i in hint_used))
        m.AddHint(ranks[i], hint_depth.get(i, 0))
    for e, edge in enumerate(edges):
        m.AddHint(choices[e], int(tuple(edge) in hint_edges))
    m.Add(paid <= hint_circuit["gate_count"])
    proto = str(m.Proto()).encode()
    (HERE / (name + ".model.pbtxt")).write_bytes(proto)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 12012
    solver.parameters.log_search_progress = False
    status = solver.Solve(m)
    result = {"name": name, "status": solver.StatusName(status), "time_limit_seconds": seconds,
              "workers": 1, "seed": 12012, "ortools_version": ortools.__version__,
              "maximum_depth": max_depth, "wall_seconds": time.perf_counter() - begin,
              "solver_wall_seconds": solver.WallTime(), "model_sha256": hashlib.sha256(proto).hexdigest(),
              "best_objective_bound": solver.BestObjectiveBound(), "statistics": solver.ResponseStats(),
              "scope": "Minimum paid XOR helpers within this fixed finite set of forms and exact productions"}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        productions = [edge for edge, var in zip(edges, choices) if solver.Value(var)]
        witness = {"productions": productions}
        result["objective"] = solver.ObjectiveValue()
        result["exact_replay"] = verify_witness(graph, witness)
        dump(HERE / (name + ".witness.json"), witness)
    dump(HERE / (name + ".result.json"), result)
    return result


def main():
    global HERE, ALLOW_WRITE
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--out", type=Path, help="Fresh output directory outside this study; required for mutation")
    args = ap.parse_args()
    if not 0 < args.seconds <= 60:
        ap.error("--seconds must be in (0,60] per model")
    if args.fetch or args.search:
        if args.out is None:
            ap.error("Mutation requires --out with a fresh directory outside this study")
        source_root = HERE.resolve()
        output_root = args.out.expanduser().resolve()
        if output_root == source_root or source_root in output_root.parents:
            ap.error("--out must be outside the input study")
        if output_root.exists():
            ap.error("--out must not already exist")
        shutil.copytree(source_root, output_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.model.pbtxt"))
        HERE = output_root
        ALLOW_WRITE = True
    if args.fetch:
        fetch()
    provenance = json.loads((HERE / "provenance.json").read_text())
    expected_hash = {r["file"]: r["sha256"] for r in provenance["sources"]}
    circuits, records = [], []
    for count, depth in FILES:
        name = f"aes-mixcols-xor{count}-depth{depth}.circ.txt"
        body = (HERE / "sources" / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != expected_hash[name]:
            raise ValueError("Source hash mismatch")
        c = parse_ncFF(body.decode())
        if (c["gate_count"], c["depth"]) != (count, depth):
            raise ValueError("Computed metrics differ from filename")
        circuits.append(c)
        record = {"file": name, "gate_count": count, "depth": depth, "exact_fips_map": True,
                  "unique_nonroot_forms": len({g["value"] for g in c["gates"]}),
                  "sha256": expected_hash[name]}
        records.append(record)
    graph = catalogue(circuits)
    dump(HERE / "catalogue.json", graph)
    summary = {"source_commit": PIN, "field": "GF(2)", "baselines": records,
               "forms": len(graph["forms"]), "input_forms": len(graph["root_indices"]),
               "required_target_forms": len(set(graph["target_indices"])),
               "observed_productions": len(graph["observed_productions"]),
               "all_exact_productions": len(graph["all_exact_productions"]),
               "fips_basis_images_verified": 32, "fips_sample_column_verified": True,
               "scope_warning": "Finite-pool optimality, if obtained, is not unrestricted XOR-circuit optimality"}
    dump(HERE / "baseline_verification.json", summary)
    if args.search:
        unrestricted = search(graph, "pool_any_depth", args.seconds, len(graph["forms"]), circuits[0])
        shallow = search(graph, "pool_depth3", args.seconds, 3, circuits[2])
        summary["search"] = [unrestricted, shallow]
        summary["target86_met"] = unrestricted.get("exact_replay", {}).get("gate_count", 10**9) <= 86
        summary["target93_depth3_met"] = shallow.get("exact_replay", {}).get("gate_count", 10**9) <= 93
        dump(HERE / "summary.json", summary)
    # Existing witnesses remain independently replayable without OR-Tools.
    for name in ("pool_any_depth", "pool_depth3"):
        path = HERE / (name + ".witness.json")
        if path.exists():
            print(name, verify_witness(graph, json.loads(path.read_text())))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
