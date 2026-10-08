#!/usr/bin/env python3
"""Transpose signed circuits and jointly orient a bilinear algorithm's wires.

Inputs use the candidate.json schema emitted by run.py. Wt is the decoder
transpose. The output uses literal add/sub gates and no explicit negations.
OR-Tools is used for a finite Boolean feasibility problem, not cost minimization.
"""
import argparse
import itertools
import json
from pathlib import Path
from common import core


def matrix(c):
    n = c["inputs"]
    core.require(type(n) is int and n > 0, "Invalid input count")
    values = [[int(i == j) for j in range(n)] for i in range(n)]
    for gate in c["gates"]:
        a, sa, b, sb = gate
        core.index(a, len(values)); core.index(b, len(values)); core.sign(sa); core.sign(sb)
        values.append(core.combine(values[a], sa, values[b], sb))
    result = []
    for o, sign in c["outputs"]:
        core.index(o, len(values)); core.sign(sign)
        result.append([sign * x for x in values[o]])
    if "target_matrix" in c:
        core.require(result == c["target_matrix"], "Signed circuit target mismatch")
    return result


def transpose(c):
    original = matrix(c)
    n = len(c["outputs"])
    result = dict(inputs=n, gates=[], outputs=[])
    adjoint = {}
    def accumulate(old, wire, sign):
        if old in adjoint:
            other, other_sign = adjoint[old]
            result["gates"].append([other, other_sign, wire, sign])
            adjoint[old] = (n + len(result["gates"]) - 1, 1)
        else:
            adjoint[old] = (wire, sign)
    for j, (wire, sign) in enumerate(c["outputs"]):
        accumulate(wire, j, sign)
    for k in reversed(range(len(c["gates"]))):
        out = c["inputs"] + k
        if out not in adjoint:
            continue
        wire, sign = adjoint[out]
        a, sa, b, sb = c["gates"][k]
        accumulate(a, wire, sign * sa)
        accumulate(b, wire, sign * sb)
    core.require(all(i in adjoint for i in range(c["inputs"])),
                 "Zero columns are unsupported by the nonzero-wire format")
    result["outputs"] = [list(adjoint[i]) for i in range(c["inputs"])]
    result["target_matrix"] = list(map(list, zip(*original)))
    matrix(result)
    return result


def orient(circuits, seconds=30):
    from ortools.sat.python import cp_model
    originals = {s: matrix(c) for s, c in circuits.items()}
    rank = len(circuits["u"]["outputs"])
    core.require(rank == len(circuits["v"]["outputs"]) == circuits["w"]["inputs"],
                 "The three factors have inconsistent product counts")
    model = cp_model.CpModel()
    bits = {}
    for side, c in circuits.items():
        bits[side] = [model.new_bool_var(f"{side}_{i}")
                      for i in range(c["inputs"] + len(c["gates"]))]
        for k, (a, sa, b, sb) in enumerate(c["gates"]):
            out = c["inputs"] + k
            allowed = [(z, x, y) for z, x, y in itertools.product((0, 1), repeat=3)
                       if not (sa * (-1)**(z+x) < 0 and sb * (-1)**(z+y) < 0)]
            model.add_allowed_assignments([bits[side][out], bits[side][a], bits[side][b]], allowed)
    for side in "uv":
        for i in range(circuits[side]["inputs"]):
            model.add(bits[side][i] == 0)
    for o, sign in circuits["w"]["outputs"]:
        model.add(bits["w"][o] == int(sign < 0))
    for t in range(rank):
        u, su = circuits["u"]["outputs"][t]
        v, sv = circuits["v"]["outputs"][t]
        parity = int(su * sv < 0)
        model.add_allowed_assignments([bits["u"][u], bits["v"][v], bits["w"][t]],
                                      [(x, y, x ^ y ^ parity) for x, y in itertools.product((0, 1), repeat=2)])
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = seconds
    status = solver.solve(model)
    core.require(status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
                 "No orientation returned: " + solver.status_name(status))
    result = {}
    signed_final = {}
    for side, c in circuits.items():
        literal = dict(inputs=c["inputs"], nodes=[], outputs=[o for o, _ in c["outputs"]])
        for k, (a, sa, b, sb) in enumerate(c["gates"]):
            out = c["inputs"] + k
            aa = sa * (-1)**(solver.value(bits[side][out]) + solver.value(bits[side][a]))
            bb = sb * (-1)**(solver.value(bits[side][out]) + solver.value(bits[side][b]))
            core.require(max(aa, bb) == 1, "Unaccounted unary negation")
            literal["nodes"].append(dict(op="add" if aa == bb else "sub",
                                         a=a if aa == 1 else b, b=b if aa == 1 else a))
        result[side] = literal
        signed_final[side] = dict(inputs=literal["inputs"],
                                 gates=[[g["a"], 1, g["b"], 1 if g["op"] == "add" else -1]
                                        for g in literal["nodes"]],
                                 outputs=[[o, 1] for o in literal["outputs"]])
    maps = {s: matrix(c) for s, c in signed_final.items()}
    signs = {s: [] for s in "uv"}
    for s in "uv":
        for actual, original in zip(maps[s], originals[s]):
            core.require(any(original), "Zero product factor unsupported")
            if actual == original:
                signs[s].append(1)
            else:
                core.require(actual == [-x for x in original], "Input factor changed by more than a sign")
                signs[s].append(-1)
    for row, original in zip(maps["w"], originals["w"]):
        core.require(row == [signs["u"][t] * signs["v"][t] * x for t, x in enumerate(original)],
                     "Product sign compensation failed")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for side in ("u", "v", "wt"):
        parser.add_argument("--" + side, type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    candidates = {s: json.loads(getattr(args, s).read_text()) for s in ("u", "v", "wt")}
    circuits = dict(u=candidates["u"], v=candidates["v"], w=transpose(candidates["wt"]))
    literal = orient(circuits)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "circuits.json").write_text(json.dumps(literal, indent=2) + "\n")
    for side, c in literal.items():
        label = lambda i: f"i{i}" if i < c["inputs"] else f"t{i-c['inputs']}"
        lines = [f"t{k}:={label(g['a'])}{'+' if g['op']=='add' else '-'}{label(g['b'])};"
                 for k, g in enumerate(c["nodes"])]
        lines.extend(f"o{k}:={label(i)};" for k, i in enumerate(c["outputs"]))
        (args.out / (side + ".slp")).write_text("\n".join(lines) + "\n")
    report = dict(status="EXACT_SIGN_COMPENSATION_PASS",
                  split=[len(literal[s]["nodes"]) for s in "uvw"],
                  scope="Original tensor preserved by compensated product signs. Verify the original tensor separately.")
    (args.out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
