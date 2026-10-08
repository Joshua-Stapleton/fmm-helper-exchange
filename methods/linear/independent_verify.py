#!/usr/bin/env python3
"""Independent literal executor and exact integer tensor audit for the 332 example.

Does not import orient.py, run.py or the bundled verifier. This adaptation of the
earlier independent parser removes dependencies on private checkout paths.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


def check(value, message):
    if not value:
        raise ValueError(message)


def literal(path, nin, nout):
    wires = {f"i{k}": tuple(int(k == j) for j in range(nin)) for k in range(nin)}
    outputs, gates = {}, 0
    for line in path.read_text().splitlines():
        check(line.endswith(";"), "Missing statement terminator")
        lhs, rhs = line[:-1].split(":=")
        if lhs.startswith("o"):
            check(re.fullmatch(r"o\d+", lhs) and rhs in wires and lhs not in outputs,
                  "Invalid output")
            outputs[lhs] = wires[rhs]
        else:
            check(re.fullmatch(r"t\d+", lhs) and lhs not in wires, "Invalid gate")
            match = re.fullmatch(r"((?:t|i)\d+)([+-])((?:t|i)\d+)", rhs)
            check(match is not None, "Nonbinary statement")
            a, op, b = match.groups()
            check(a in wires and b in wires, "Undefined dependency")
            wires[lhs] = tuple(x+y if op == "+" else x-y for x, y in zip(wires[a], wires[b]))
            gates += 1
    check(set(outputs) == {f"o{k}" for k in range(nout)}, "Output count")
    return [outputs[f"o{k}"] for k in range(nout)], gates


def expand(source, side):
    n = 93 if side == "w" else 25
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    def expression(terms):
        result = [0] * n
        for term in terms:
            i, coefficient = term["index"], term["value"]
            check(type(i) is int and 0 <= i < len(values) and type(coefficient) is int,
                  "Nonintegral or invalid source term")
            for k, value in enumerate(values[i]):
                result[k] += coefficient * value
        return tuple(result)
    for terms in source.get(side + "_fresh", []):
        values.append(expression(terms))
    return [expression(terms) for terms in source[side]]


def verify(directory, source_path=None):
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        for name, digest in json.loads(manifest_path.read_text()).items():
            check(Path(name).name == name, "Manifest path must name a local file")
            check(hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest,
                  "Manifest digest mismatch: " + name)
    source_path = source_path or directory / "source.json"
    check(hashlib.sha256(source_path.read_bytes()).hexdigest() ==
          "808285b8fb393d2e950ecff4ffe9881a209b6d3eff0d787e34d801a3f22293da", "Pinned source hash")
    source = json.loads(source_path.read_text())
    maps, costs, originals = {}, {}, {}
    for side in "uvw":
        maps[side], costs[side] = literal(directory / (side + ".slp"),
                                          93 if side == "w" else 25,
                                          25 if side == "w" else 93)
        originals[side] = expand(source, side)
    signs = {}
    for side in "uv":
        signs[side] = []
        for actual, expected in zip(maps[side], originals[side]):
            check(actual == expected or actual == tuple(-x for x in expected), "Input term changed")
            signs[side].append(1 if actual == expected else -1)
    for c in range(25):
        for t in range(93):
            check(maps["w"][c][t] == signs["u"][t] * signs["v"][t] * originals["w"][c][t],
                  "Uncompensated term sign")
    tensor = defaultdict(int)
    for t in range(93):
        for a, x in enumerate(maps["u"][t]):
            if x:
                for b, y in enumerate(maps["v"][t]):
                    if y:
                        for c in range(25):
                            tensor[a, b, c] += x * y * maps["w"][c][t]
    actual = {key: value for key, value in tensor.items() if value}
    expected = {(5*i+j, 5*j+k, 5*k+i): 1 for i in range(5) for j in range(5) for k in range(5)}
    check(actual == expected, "Tensor identity")
    check(costs == dict(u=87, v=88, w=157), "Circuit counts")
    return dict(status="PASS", split=costs, additions=332, products=93, scalar_total=425,
                basis_change=False, unary_negations=0, nonunit_scalars=0, tensor_identities=15625)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.source), indent=2))
