#!/usr/bin/env python3
"""Pool adjoint circuits, charge every return gate, and verify the fixed map.

The donor bank computes the transpose of --matrix. Linear transposition and
finite-pool reconnection are established operations; this wrapper combines
them and does not claim a new general minimization algorithm. Default outputs
use the signed-wire search model. Optional fixed-sign orientation certifies
literal additions/subtractions without changing original input/output signs.
"""
import argparse
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


api = module("adjoint_reconstruction_common", HERE/"common.py")
circuits = module("adjoint_exact_circuits", ROOT/"methods/circuits/circuits.py")
fast = module("adjoint_native_pool", HERE.parent/"fast_pool.py")


def transpose_matrix(target):
    api.matrix_check(target)
    return [list(row) for row in zip(*target)]


def checked(candidate, target):
    api.matrix_check(target)
    n = len(target[0])
    api.require(isinstance(candidate, dict), "Candidate must be an object")
    api.require(type(candidate.get("inputs", n)) is int and
                candidate.get("inputs", n) == n, "Candidate input dimension mismatch")
    api.require(api.exact_circuit(candidate, n) == target, "Candidate differs from ordered fixed map")
    if "target_matrix" in candidate:
        api.require(candidate["target_matrix"] == target, "Candidate target metadata mismatch")
    result = api.normalize(dict(candidate, inputs=n))
    api.require(api.exact_circuit(result, n) == target, "Normalization changed the fixed map")
    return dict(result, target_matrix=target)


def to_circuit(candidate, target):
    data = checked(candidate, target)
    circuit = circuits.Circuit(data["inputs"])
    wires = list(range(data["inputs"]))
    for a, sa, b, sb in data["gates"]:
        wires.append(circuit.add(circuit.scale(wires[a], sa), circuit.scale(wires[b], sb)))
    circuit.outputs = [circuit.scale(wires[w], sign) for w, sign in data["outputs"]]
    circuit.prune().check(target)
    return circuit


def from_circuit(circuit, target):
    """Count every binary node; only unit signs may become signed aliases."""
    circuit.prune().check(target)
    n = circuit.inputs
    aliases, gates = [(i, 1) for i in range(n)], []
    for node in circuit.nodes:
        if node["op"] == "scale":
            coefficient = circuits.Q(node["c"])
            api.require(coefficient in (-1, 1), "Nonunit scales cannot be free")
            wire, sign = aliases[node["a"]]
            aliases.append((wire, sign*int(coefficient)))
        elif node["op"] == "add":
            a, sa = aliases[node["a"]]
            b, sb = aliases[node["b"]]
            gates.append([a, sa, b, sb])
            aliases.append((n+len(gates)-1, 1))
        else:
            raise ValueError("Unsupported nonbinary circuit node: "+str(node["op"]))
    raw = dict(inputs=n, gates=gates, outputs=[list(aliases[o]) for o in circuit.outputs])
    return checked(raw, target)


def paid_transpose(candidate, target):
    """Return an exact paid circuit for target transpose in its original roots."""
    transposed = transpose_matrix(target)
    api.matrix_check(transposed)  # The nonzero-wire schema cannot encode zero columns.
    circuit = to_circuit(candidate, target).transposed()
    return from_circuit(circuit, transposed)


def prepare_bank(bank, original, current=None):
    target = transpose_matrix(original)
    api.matrix_check(target)
    n = len(target[0])
    api.require(isinstance(bank, dict) and type(bank.get("inputs")) is int
                and bank["inputs"] == n, "Adjoint donor input dimension mismatch")
    api.require(isinstance(bank.get("circuits"), list) and bank["circuits"],
                "A nonempty adjoint donor bank is required")
    donors = []
    for index, source in enumerate(bank["circuits"]):
        donor = checked(source, target)
        donors.append(dict(donor, name="adjoint_donor_"+str(index)))
    direct = checked(current, original) if current is not None else None
    if direct is not None:
        donors.append(dict(paid_transpose(direct, original), name="current_original_transposed"))
    return dict(inputs=n, circuits=donors), target, direct


def linear_orientation_helpers():
    """Load existing orient.py without leaking its generic common-module name.

    Its public CLI jointly orients U,V,W and permits compensated product signs.
    A single fixed map instead needs all roots and ordered output signs frozen.
    The helper and gate constraints below use the same existing implementation.
    """
    shared = module("adjoint_linear_common", HERE.parent/"common.py")
    previous = sys.modules.get("common")
    sys.modules["common"] = shared
    try:
        return module("adjoint_linear_orient", HERE.parent/"orient.py")
    finally:
        if previous is None:
            sys.modules.pop("common", None)
        else:
            sys.modules["common"] = previous


def orient_fixed(candidate, target, seconds):
    """Optional finite feasibility pass, freezing every original input/output."""
    api.finite(seconds, "Orientation time")
    data = checked(candidate, target)
    helper = linear_orientation_helpers()
    api.require(helper.matrix(data) == target, "Existing orientation replay mismatch")
    from ortools.sat.python import cp_model
    n = data["inputs"]
    model = cp_model.CpModel()
    bits = [model.new_bool_var("negative_"+str(i)) for i in range(n+len(data["gates"]))]
    for bit in bits[:n]:
        model.add(bit == 0)
    for wire, sign in data["outputs"]:
        model.add(bits[wire] == int(sign < 0))
    for k, (a, sa, b, sb) in enumerate(data["gates"], n):
        allowed = [(z, x, y) for z, x, y in itertools.product((0, 1), repeat=3)
                   if sa*(-1)**(z+x) > 0 or sb*(-1)**(z+y) > 0]
        model.add_allowed_assignments([bits[k], bits[a], bits[b]], allowed)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = seconds
    status = solver.solve(model)
    report = dict(status=solver.status_name(status), elapsed_seconds=solver.wall_time,
                  input_signs_fixed=True, ordered_output_signs_fixed=True)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, None, report
    literal = dict(inputs=n, gates=[], outputs=[[wire, 1] for wire, _ in data["outputs"]])
    label = lambda wire: "i"+str(wire) if wire < n else "t"+str(wire-n)
    lines = []
    for k, (a, sa, b, sb) in enumerate(data["gates"], n):
        aa = sa*(-1)**(solver.value(bits[k])+solver.value(bits[a]))
        bb = sb*(-1)**(solver.value(bits[k])+solver.value(bits[b]))
        api.require(aa > 0 or bb > 0, "Unpaid unary negation")
        if aa < 0:
            a, b, aa, bb = b, a, bb, aa
        literal["gates"].append([a, aa, b, bb])
        lines.append("t"+str(k-n)+":="+label(a)+("+" if bb == 1 else "-")+label(b)+";")
    lines.extend("o"+str(k)+":="+label(wire)+";" for k, (wire, _) in enumerate(literal["outputs"]))
    api.require(helper.matrix(literal) == target, "Literal orientation changed the original fixed map")
    api.require(api.exact_circuit(literal, n) == target, "Independent integer orientation replay failed")
    normalized = api.normalize(literal)
    api.require(len(normalized["gates"]) == len(literal["gates"]), "Literal orientation has unused or aliased gates")
    report.update(exact_original_map_verified=True, binary_additions=len(literal["gates"]),
                  unary_negations=0, nonunit_scalars=0, unused_gates=0)
    return dict(literal, target_matrix=target), "\n".join(lines)+"\n", report


def validate(args):
    api.require(math.isfinite(args.search_seconds) and args.search_seconds >= 0,
                "Search time must be nonnegative and finite; zero disables search")
    api.require(type(args.seed) is int and 0 <= args.seed < 2**32 and
                type(args.width) is int and args.width > 0, "Invalid search seed or width")
    api.require(args.backend in ("native", "python"), "Unknown relation backend")
    api.require(args.backend == "native" or args.binary is None and args.compiler is None,
                "Binary/compiler options require the native backend")
    if args.orient_seconds is not None:
        api.finite(args.orient_seconds, "Orientation time")
    api.require(not args.out.exists(), "Output directory already exists")


def run(args):
    validate(args)
    total_start = time.monotonic()
    original = api.read_matrix(args.matrix)
    raw_bank = api.json_read(args.donors)
    current = api.json_read(args.candidate) if args.candidate is not None else None
    start = time.monotonic()
    bank, adjoint, direct = prepare_bank(raw_bank, original, current)
    donor_seconds = time.monotonic()-start
    args.out.mkdir(parents=True, exist_ok=False)
    api.dump(args.out/"adjoint_donors.json", bank)
    api.dump(args.out/"original_matrix.json", original)
    binary = args.binary
    build_seconds = 0
    if args.backend == "native" and binary is None:
        build_start = time.monotonic()
        binary = fast.compile_backend(args.out/"pool_relations", args.compiler)
        build_seconds = time.monotonic()-build_start
    pool_start = time.monotonic()
    pool = (fast.build_pool(bank, binary=binary) if args.backend == "native"
            else api.builder.build_pool(bank))
    api.dump(args.out/"pool.json", pool)
    data, productions, incumbent, _ = api.core.load(args.out/"pool.json")
    (args.out/"baseline").mkdir()
    api.core.export(incumbent, data, args.out/"baseline")
    pool_seconds = time.monotonic()-pool_start
    search = dict(status="DISABLED", elapsed_seconds=0)
    paths = [args.out/"baseline/candidate.json"]
    if args.search_seconds > 0:
        command = [sys.executable, "-B", str(HERE.parent/"search.py"), "--data",
                   str(args.out/"pool.json"), "--out", str(args.out/"search"), "--engine", "plateau",
                   "--seconds", str(args.search_seconds), "--seed", str(args.seed), "--width", str(args.width)]
        # search.py uses its sibling common.py under a direct script invocation.
        search_start = time.monotonic()
        environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
        try:
            process = subprocess.run(command, capture_output=True, text=True,
                                     timeout=args.search_seconds+45, env=environment)
            (args.out/"search.log").write_text(process.stdout+"\n"+process.stderr)
            search = dict(status="COMPLETE" if process.returncode == 0 else "ERROR",
                          returncode=process.returncode)
        except subprocess.TimeoutExpired:
            search = dict(status="TIMEOUT", scope="Incomplete bounded search; not an impossibility result")
        search.update(command=command, elapsed_seconds=time.monotonic()-search_start,
                      requested_search_seconds=args.search_seconds)
        result = args.out/"search/result.json"
        if result.exists():
            search["result"] = api.json_read(result)
        if (args.out/"search/candidate.json").exists():
            paths.append(args.out/"search/candidate.json")
    start = time.monotonic()
    returned = []
    for index, path in enumerate(paths):
        candidate = checked(api.json_read(path), adjoint)
        result = paid_transpose(candidate, adjoint)
        api.dump(args.out/("returned_"+str(index)+".json"), result)
        returned.append((len(result["gates"]), "returned_"+str(index), result))
    if direct is not None:
        returned.append((len(direct["gates"]), "current_original", direct))
    count, selection, best = min(returned, key=lambda entry: entry[0])
    api.dump(args.out/"best_candidate.json", best)
    return_seconds = time.monotonic()-start
    orientation = dict(status="NOT_REQUESTED", scope="Signed-wire count only; strict signs require separate verification")
    if args.orient_seconds is not None:
        literal, text, orientation = orient_fixed(best, original, args.orient_seconds)
        if literal is not None:
            api.dump(args.out/"strict_candidate.json", literal)
            (args.out/"best.slp").write_text(text)
        api.dump(args.out/"orientation.json", orientation)
    report = dict(original_inputs=len(original[0]), original_outputs=len(original),
                  adjoint_inputs=len(adjoint[0]), adjoint_outputs=len(adjoint),
                  donor_source_sha256=api.hashlib.sha256(args.donors.read_bytes()).hexdigest(),
                  matrix_source_sha256=api.hashlib.sha256(args.matrix.read_bytes()).hexdigest(),
                  current_candidate_sha256=None if args.candidate is None else
                      api.hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
                  donor_count=len(bank["circuits"]), donor_preparation_seconds=donor_seconds,
                  relation_backend=args.backend, relation_binary_build_seconds=build_seconds,
                  pool_build_seconds=pool_seconds, pool_forms=len(pool["forms"]),
                  pool_productions=sum(map(len, productions.values())), search=search,
                  return_seconds=return_seconds, selected=selection,
                  initial_original_additions_signed=None if direct is None else len(direct["gates"]),
                  additions_signed=count, exact_ordered_original_map_verified=True,
                  free_signed_wires=True, basis_change=False, orientation=orientation,
                  total_seconds=time.monotonic()-total_start,
                  scope="Exact fixed map; all binary adjoint accumulations charged. Heuristic finite pool, no global optimum or runtime claim.")
    api.dump(args.out/"summary.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--donors", type=Path, required=True, help="Donor bank computing transpose of --matrix")
    parser.add_argument("--matrix", type=Path, required=True, help="Original fixed matrix, SMS or JSON")
    parser.add_argument("--candidate", type=Path, help="Optional current original-map candidate")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--backend", choices=("native", "python"), default="native")
    parser.add_argument("--binary", type=Path, help="Reuse a native exact relation binary")
    parser.add_argument("--compiler", help="Compiler for native relations when --binary is absent")
    parser.add_argument("--search-seconds", type=float, default=20, help="Zero disables plateau search")
    parser.add_argument("--seed", type=int, default=11117000)
    parser.add_argument("--width", type=int, default=10)
    parser.add_argument("--orient-seconds", type=float, help="Optional fixed-sign OR-Tools feasibility budget")
    print(json.dumps(run(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
