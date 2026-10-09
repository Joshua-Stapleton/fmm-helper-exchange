#!/usr/bin/env python3
"""Independent stdlib replay of the fixed-sign 3x6x8 V, 158-addition fixture.

No optimizer, pool builder, LEO code or solver package is imported.
"""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def require(value, message):
    if not value:
        raise ValueError(message)


def signed(circuit):
    n = circuit["inputs"]
    values = [[int(i == j) for j in range(n)] for i in range(n)]
    for a, sa, b, sb in circuit["gates"]:
        require(type(a) is int and type(b) is int and 0 <= a < len(values) and 0 <= b < len(values),
                "Invalid signed dependency")
        require(type(sa) is int and type(sb) is int and sa in (-1, 1) and sb in (-1, 1), "Invalid sign")
        values.append([sa*x+sb*y for x, y in zip(values[a], values[b])])
    result = []
    for wire, sign in circuit["outputs"]:
        require(type(wire) is int and 0 <= wire < len(values) and type(sign) is int and sign in (-1, 1),
                "Invalid signed output")
        result.append([sign*x for x in values[wire]])
    return result


def literal(path, n, outputs):
    values = {f"i{k}": [int(k == j) for j in range(n)] for k in range(n)}
    dependencies, result, gates = {}, {}, 0
    for raw in path.read_text().splitlines():
        require(raw.endswith(";") and raw.count(":=") == 1, "Invalid literal assignment")
        lhs, rhs = raw[:-1].split(":=")
        require(lhs not in values and lhs not in result, "Reassigned wire")
        if lhs.startswith("o"):
            require(re.fullmatch(r"o\d+", lhs) and rhs in values, "Invalid literal output")
            result[lhs] = values[rhs]
            dependencies[lhs] = (rhs,)
            continue
        require(lhs == f"t{gates}", "Nonconsecutive literal gate")
        match = re.fullmatch(r"((?:i|t)\d+)([+-])((?:i|t)\d+)", rhs)
        require(match is not None, "Expected one ordinary binary addition/subtraction")
        a, op, b = match.groups()
        require(a in values and b in values, "Undefined literal dependency")
        values[lhs] = [x+y if op == "+" else x-y for x, y in zip(values[a], values[b])]
        dependencies[lhs] = (a, b)
        gates += 1
    require(set(result) == {f"o{k}" for k in range(outputs)}, "Output count mismatch")
    used, pending = set(result), list(result)
    while pending:
        for parent in dependencies.get(pending.pop(), ()):
            if parent not in used:
                used.add(parent)
                pending.append(parent)
    unused = len(set(dependencies)-used)
    return [result[f"o{k}"] for k in range(outputs)], gates, unused


def verify():
    fixtures = HERE/"fixtures"
    manifest = json.loads((fixtures/"SHA256.json").read_text())
    for name, digest in manifest.items():
        require(Path(name).name == name, "Unsafe manifest path")
        require(hashlib.sha256((fixtures/name).read_bytes()).hexdigest() == digest, "Hash mismatch: "+name)
    original = json.loads((fixtures/"368_V_159.json").read_text())
    candidate = json.loads((fixtures/"368_V_158.json").read_text())
    target = original["target_matrix"]
    require(original["inputs"] == candidate["inputs"] == 48 and len(target) == 113, "Fixture dimensions")
    require(signed(original) == signed(candidate) == candidate["target_matrix"] == target, "Signed coefficient mismatch")
    actual, count, unused = literal(fixtures/"winning_368_V.slp", 48, 113)
    require(actual == target and count == 158 and unused == 0, "Literal certificate mismatch")
    return dict(status="PASS", inputs=48, outputs=113, exact_coefficients=5424,
                additions=158, unary_negations=0, nonunit_scalars=0, dead_assignments=0,
                basis_change=False, scope="Only the supplied V linear map; not a complete multiplication claim")


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
