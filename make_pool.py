#!/usr/bin/env python3
"""Build an exact, sign-canonical helper pool using only Python's standard library.

Usage: python3 make_pool.py INPUT.json OUTPUT.json
Input: {inputs: N, circuits: [{name: str, gates: [[a, sa, b, sb], ...],
outputs: [[wire, sign], ...]}]}. Wires start with N inputs, then sequential gates.
All circuits must have the same ordered, signed output matrix. Zero forms fail;
only +/- aliases are merged, never different magnitudes. All donor forms enter
the pool. The donor with fewest raw live gates supplies the incumbent (ties use
input order), which is then canonicalized, deduplicated, and pruned again.
"""

import argparse
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(vector):
    first = next((x for x in vector if x), 0)
    require(first != 0, "zero forms are unsupported")
    sign = 1 if first > 0 else -1
    return tuple(sign * x for x in vector), sign


def read_circuit(circuit, roots, number):
    require(isinstance(circuit, dict), f"circuit {number}: expected an object")
    label = circuit.get("name", f"circuit {number}")
    require(isinstance(label, str), f"circuit {number}: name must be a string")
    gates, outputs = circuit.get("gates"), circuit.get("outputs")
    require(isinstance(gates, list), f"{label}: gates must be a list")
    require(isinstance(outputs, list) and outputs, f"{label}: outputs must be nonempty")
    vectors, aliases = list(roots), [(r, 1) for r in roots]

    def operand(wire, sign, limit):
        require(type(wire) is int and 0 <= wire < limit,
                f"{label}: wire {wire!r} must be an earlier wire in [0, {limit})")
        require(type(sign) is int and sign in (-1, 1),
                f"{label}: sign {sign!r} must be integer +1 or -1")

    for index, gate in enumerate(gates):
        require(isinstance(gate, list) and len(gate) == 4,
                f"{label}: gate {index} must be [a, sa, b, sb]")
        a, sa, b, sb = gate
        operand(a, sa, len(vectors))
        operand(b, sb, len(vectors))
        vector = tuple(sa * x + sb * y for x, y in zip(vectors[a], vectors[b]))
        require(any(vector), f"{label}: gate {index} creates an unsupported zero form")
        vectors.append(vector)
        aliases.append(canonical(vector))
    matrix = []
    for index, output in enumerate(outputs):
        require(isinstance(output, list) and len(output) == 2,
                f"{label}: output {index} must be [wire, sign]")
        wire, sign = output
        operand(wire, sign, len(vectors))
        matrix.append([sign * x for x in vectors[wire]])
    live, pending = set(), [wire for wire, _ in outputs]
    while pending:
        wire = pending.pop()
        if wire < len(roots) or wire in live:
            continue
        live.add(wire)
        a, _, b, _ = gates[wire - len(roots)]
        pending.extend((a, b))
    return gates, outputs, aliases, matrix, live


def build_pool(source):
    require(isinstance(source, dict), "input must be an object")
    n, circuits = source.get("inputs"), source.get("circuits")
    require(type(n) is int and n > 0, "inputs must be a positive integer")
    require(isinstance(circuits, list) and circuits, "circuits must be a nonempty list")
    roots = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    donors = [read_circuit(c, roots, i) for i, c in enumerate(circuits)]
    target = donors[0][3]
    require(all(d[3] == target for d in donors), "circuits have different exact output matrices")
    pooled = {form for donor in donors for form, _ in donor[2]}
    forms = roots + sorted(pooled - set(roots))
    ids = {form: i for i, form in enumerate(forms)}
    productions = {i: set() for i in range(n, len(forms))}
    for a, left in enumerate(forms):
        for b in range(a, len(forms)):
            right = forms[b]
            for sa, sb in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                out = ids.get(tuple(sa * x + sb * y for x, y in zip(left, right)))
                if out is not None and out >= n and out not in (a, b):
                    productions[out].add((a, sa, b, sb))
    gates, raw_outputs, aliases, _, live = min(donors, key=lambda d: len(d[4]))
    incumbent, available = {}, set(range(n))
    for wire in sorted(live):
        form, orientation = aliases[wire]
        out = ids[form]
        if out in available:
            continue
        a, sa, b, sb = gates[wire - n]
        fa, oa = aliases[a]
        fb, ob = aliases[b]
        a, b, sa, sb = ids[fa], ids[fb], sa * oa * orientation, sb * ob * orientation
        if a > b:
            a, sa, b, sb = b, sb, a, sa
        production = (a, sa, b, sb)
        require(a in available and b in available and out not in (a, b),
                "incumbent has a cycle or unavailable dependency")
        require(production in productions[out], "incumbent production is not exact")
        require(out not in incumbent, "conflicting incumbent productions")
        incumbent[out] = production
        available.add(out)
    outputs = [[ids[aliases[w][0]], s * aliases[w][1]] for w, s in raw_outputs]
    needed, pending = set(), [wire for wire, _ in outputs]
    while pending:
        out = pending.pop()
        if out < n or out in needed:
            continue
        require(out in incumbent, "incumbent is missing an output dependency")
        needed.add(out)
        a, _, b, _ = incumbent[out]
        pending.extend((a, b))
    name = source.get("name", "pooled-donors")
    require(isinstance(name, str), "name must be a string")
    return {"name": name, "inputs": n, "forms": [list(f) for f in forms],
            "productions": {str(k): [list(p) for p in sorted(v)]
                            for k, v in productions.items()},
            "outputs": outputs, "target_matrix": target,
            "incumbent": {str(k): list(incumbent[k]) for k in sorted(needed)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        pool = build_pool(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.write_text(json.dumps(pool, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, RecursionError) as error:
        parser.exit(2, f"make_pool.py: {error}\n")
    count = sum(len(p) for p in pool["productions"].values())
    print(f"Wrote {args.output}: {len(pool['forms'])} forms, {count} productions, "
          f"{len(pool['incumbent'])} incumbent gates")


if __name__ == "__main__":
    main()
