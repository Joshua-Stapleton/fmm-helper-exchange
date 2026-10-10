#!/usr/bin/env python3
"""Standard-library-only exact certificate check, including the complete tensor.

Run with Python 3: python3 -I -B verify.py
The script writes no files. No solver, numerical library or repository installation
is needed. Addition counts come from literal programs, rather than annotations.
"""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_SHA256 = "5dd82fa0ee198f63108e1dbf412cc33a683b3c493697180a739bf83fb89464f2"
UPLOADED_V_SHA256 = "5df6fc138883423e9b6467264760b1b4b783539b075c77e934dff1c845f1134e"
spec = importlib.util.spec_from_file_location("literal_verifier", HERE / "verify_literal.py")
literal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(literal)


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest():
    manifest = json.loads((HERE / "manifest.json").read_text())
    expected = manifest["files"]
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob("*")
              if p.is_file() and p.name != "manifest.json"}
    assert set(expected) == actual, "Checksum manifest does not cover exactly the bundle files"
    for relative, sha in expected.items():
        assert checksum(HERE / relative) == sha, "Checksum mismatch: " + relative
    assert checksum(HERE / "source.json") == SOURCE_SHA256, "Original scheme source mismatch"
    assert checksum(HERE / "V.sms") == UPLOADED_V_SHA256, "Uploaded V bytes mismatch"
    return len(expected)


def expand_source(source, side, inputs):
    """Replay the original reduced source's fresh forms and ordered outputs."""
    values = [[int(i == j) for j in range(inputs)] for i in range(inputs)]

    def expression(terms):
        result = [0] * inputs
        assert isinstance(terms, list) and terms, "Empty original expression"
        for term in terms:
            index, coefficient = term["index"], term["value"]
            assert type(index) is int and 0 <= index < len(values)
            assert type(coefficient) is int
            result = [a + coefficient * b for a, b in zip(result, values[index])]
        return result

    for terms in source.get(side + "_fresh", []):
        values.append(expression(terms))
    return [expression(terms) for terms in source[side]]


def replay_numeric(candidate):
    """Check the separate numeric DAG without using search or circuit helpers."""
    inputs = candidate["inputs"]
    assert type(inputs) is int and inputs > 0
    values = [[int(i == j) for j in range(inputs)] for i in range(inputs)]
    for a, sa, b, sb in candidate["gates"]:
        assert type(a) is int and type(b) is int
        assert 0 <= a < len(values) and 0 <= b < len(values)
        assert type(sa) is int and type(sb) is int and sa in (-1, 1) and sb in (-1, 1)
        values.append([sa * x + sb * y for x, y in zip(values[a], values[b])])
    output = []
    for wire, sign in candidate["outputs"]:
        assert type(wire) is int and 0 <= wire < len(values)
        assert type(sign) is int and sign in (-1, 1)
        output.append([sign * x for x in values[wire]])
    return output


def check_program(side, matrix, expected_additions, baseline=False):
    prefix = HERE / "baseline" if baseline else HERE
    candidate = json.loads((prefix / (side + ".json")).read_text())
    assert candidate["inputs"] == len(matrix[0])
    assert replay_numeric(candidate) == matrix, "Numeric DAG changed the original map"
    actual, counts = literal.replay((prefix / (side + ".slp")).read_text(), len(matrix[0]))
    assert actual == matrix, "Literal program changed the original map"
    assert counts["binary_additions"] == expected_additions == len(candidate["gates"])
    for field in ("unary_negations", "nonunit_scalars", "unused_noninput_assignments"):
        assert counts[field] == 0, "Uncharged or unused computation: " + field
    return actual, dict(counts=counts,
                        coefficient_identities=len(matrix) * len(matrix[0]),
                        numeric_dag_verified=True, fixed_original_map=True)


def check_tensor(maps):
    U, V, W = maps["U"], maps["V"], maps["W"]
    assert len(U) == len(V) == 176 and len(W) == 35
    assert all(len(row) == 35 for row in U)
    assert all(len(row) == 49 for row in V)
    assert all(len(row) == 176 for row in W)
    coefficients = collections.defaultdict(int)
    for product in range(176):
        us = [(a, x) for a, x in enumerate(U[product]) if x]
        vs = [(b, x) for b, x in enumerate(V[product]) if x]
        ws = [(o, row[product]) for o, row in enumerate(W) if row[product]]
        for a, u in us:
            for b, v in vs:
                for o, w in ws:
                    coefficients[o, a, b] += u * v * w
    coefficients = {key: value for key, value in coefficients.items() if value}
    expected = {(i + 5*k, 7*i + j, 7*j + k): 1
                for i in range(5) for j in range(7) for k in range(7)}
    assert coefficients == expected, "The complete matrix multiplication tensor differs"
    return dict(status="PASS", coefficient_identities=35 * 35 * 49,
                nonzero_coefficients=len(coefficients), products=176,
                coordinate_order=dict(A="a[7*i+j]", B="b[7*j+k]", C="c[5*k+i]"))


def main():
    files = verify_manifest()
    source = json.loads((HERE / "source.json").read_text())
    assert source["n"] == [5, 7, 7] and source["m"] == 176
    assert source["z2"] is False and source["complexity"]["reduced"] == 788
    counts_before, counts_after = dict(U=205, V=236, W=347), dict(U=180, V=205, W=316)
    maps, before, after = {}, {}, {}
    for side, inputs in (("U", 35), ("V", 49), ("W", 176)):
        matrix, _ = literal.read_sms(HERE / (side + ".sms"))
        assert matrix == expand_source(source, side.lower(), inputs), "Source coordinate order changed"
        _, before[side] = check_program(side, matrix, counts_before[side], baseline=True)
        maps[side], after[side] = check_program(side, matrix, counts_after[side])
    tensor = check_tensor(maps)
    before_total = sum(row["counts"]["binary_additions"] for row in before.values())
    after_total = sum(row["counts"]["binary_additions"] for row in after.values())
    assert before_total == 788 and after_total == 701
    print(json.dumps(dict(status="PASS", scheme="5x7x7", products=176,
                          additions_before=before_total, additions_after=after_total,
                          total_operations_before=before_total+176,
                          total_operations_after=after_total+176,
                          original_maps_unchanged=True, basis_change=False,
                          before=before, after=after, tensor=tensor,
                          checksum_files_verified=files,
                          scope="Exact arithmetic upper bound; no optimality, runtime or global-record claim"),
                     indent=2))


if __name__ == "__main__":
    main()
