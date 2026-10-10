#!/usr/bin/env python3
"""Independent exact replay of the frozen output-forest search evidence.

The core numeric verification uses only Python's standard library and does
not import the search implementation. A supplementary mixed-start record
check invokes its separate standard-library helper. --native rebuilds each frozen
pool with an externally supplied relation-enumerator executable.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
BANKS = {"V": ("V", 270, 685, 207), "control_V": ("V", 20, 471, 225),
         "U": ("U", 25, 313, 194), "WT": ("WT", 25, 320, 187),
         "V/ablation": ("V", 250, 666, 207)}
CANDIDATES = {"V/candidate205.json": ("V", 205, "V"),
              "control_V/candidate225.json": ("V", 225, "control_V"),
              "U/candidate180.json": ("U", 180, "U"),
              "WT/candidate175.json": ("WT", 175, "WT"),
              "winning_forest/before227.json": ("V", 227, None),
              "winning_forest/candidate224.json": ("V", 224, None)}


def require(value, message):
    if not value:
        raise ValueError(message)


def unique_object(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def integer(value):
    require(type(value) is int, "Exact integer required")
    return value


def index(value, size):
    require(type(value) is int and 0 <= value < size, "Invalid wire index")
    return value


def sign(value):
    require(type(value) is int and value in (-1, 1), "Invalid sign")
    return value


def read_sms(path):
    rows = [line.split() for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")]
    r, n = map(int, rows[0][:2])
    require(r > 0 and n > 0, "Invalid SMS dimensions")
    matrix, seen = [[0]*n for _ in range(r)], set()
    for line in rows[1:]:
        require(len(line) == 3, "Invalid SMS coordinate")
        a, b, x = map(int, line)
        if (a, b, x) == (0, 0, 0):
            continue
        require(1 <= a <= r and 1 <= b <= n and (a, b) not in seen,
                "Invalid/duplicate SMS coordinate")
        seen.add((a, b))
        matrix[a-1][b-1] = x
    return matrix


def canonical(row):
    orientation = next((1 if x > 0 else -1 for x in row if x), None)
    require(orientation is not None, "Zero form unsupported")
    return tuple(orientation*x for x in row), orientation


def roots(n):
    return [tuple(int(i == j) for j in range(n)) for i in range(n)]


def combine(a, sa, b, sb):
    return tuple(sa*x + sb*y for x, y in zip(a, b))


def gate(row, size):
    require(isinstance(row, list) and len(row) == 4, "Invalid binary gate")
    a, sa, b, sb = row
    return index(a, size), sign(sa), index(b, size), sign(sb)


def replay(circuit, target):
    n = len(target[0])
    require(circuit.get("inputs", n) == n, "Changed input dimension")
    require(isinstance(circuit.get("gates"), list), "Gates must be ordered")
    values = roots(n)
    for row in circuit["gates"]:
        a, sa, b, sb = gate(row, len(values))
        values.append(combine(values[a], sa, values[b], sb))
    outputs = circuit.get("outputs")
    require(isinstance(outputs, list) and len(outputs) == len(target), "Changed output count")
    actual = []
    for row in outputs:
        require(isinstance(row, list) and len(row) == 2, "Invalid output reference")
        wire, orientation = row
        index(wire, len(values)); sign(orientation)
        actual.append([orientation*x for x in values[wire]])
    require(actual == target, "Circuit changed an exact target coefficient")
    if "additions_signed" in circuit:
        require(circuit["additions_signed"] == len(circuit["gates"]), "Saved count mismatch")
    return len(circuit["gates"])


def selection(pool, selected, target):
    n, forms = pool["inputs"], pool["forms"]
    parsed = {}
    for key, row in selected.items():
        require(key.isascii() and key.isdigit() and str(int(key)) == key,
                "Noncanonical selected form key")
        out = index(int(key), len(forms))
        require(out >= n, "Cannot produce a root input")
        production = gate(row, len(forms))
        require(list(production) in pool["productions"].get(key, []),
                "Selected edge absent from frozen pool")
        parsed[out] = production
    values, pending = {i: value for i, value in enumerate(roots(n))}, set(parsed)
    while pending:
        ready = sorted(out for out in pending
                       if parsed[out][0] in values and parsed[out][2] in values)
        require(ready, "Cycle or missing producer in selection")
        for out in ready:
            a, sa, b, sb = parsed[out]
            values[out] = combine(values[a], sa, values[b], sb)
            require(list(values[out]) == forms[out], "Selected production identity failed")
            pending.remove(out)
    actual = [[orientation*x for x in values[wire]] for wire, orientation in pool["outputs"]]
    require(actual == target, "Selected program changed the target")
    live, pending = set(), [wire for wire, _ in pool["outputs"]]
    while pending:
        out = pending.pop()
        if out < n or out in live:
            continue
        live.add(out)
        require(out in parsed, "Missing live selected producer")
        pending.extend((parsed[out][0], parsed[out][2]))
    require(len(live) == len(parsed), "Unused selected gates")
    return len(parsed)


def verify_pool(pool, target, expected_forms, expected_initial):
    n = len(target[0])
    require(pool["inputs"] == n and pool["target_matrix"] == target,
            "Pool input coordinates or target changed")
    forms = pool["forms"]
    require(len(forms) == expected_forms and forms[:n] == [list(row) for row in roots(n)],
            "Wrong form count or nonstandard root coordinates")
    seen, relation_count = set(), 0
    for row in forms:
        require(isinstance(row, list) and len(row) == n and all(type(x) is int for x in row),
                "Invalid coefficient vector")
        form, _ = canonical(row)
        require(tuple(row) == form and form not in seen, "Noncanonical or duplicate form")
        seen.add(form)
    for key, productions in pool["productions"].items():
        require(key.isascii() and key.isdigit() and str(int(key)) == key,
                "Noncanonical production key")
        out = index(int(key), len(forms))
        require(out >= n and isinstance(productions, list), "Invalid production list")
        for row in productions:
            a, sa, b, sb = gate(row, len(forms))
            require(list(combine(forms[a], sa, forms[b], sb)) == forms[out],
                    "Frozen-pool production identity failed")
            relation_count += 1
    for wire, orientation in pool["outputs"]:
        index(wire, len(forms)); sign(orientation)
    count = selection(pool, pool["incumbent"], target)
    require(count == expected_initial, "Wrong frozen initial count")
    return dict(forms=len(forms), relations=relation_count, initial_additions_signed=count)


def verify_winning_forest(target):
    n = len(target[0])
    folder = HERE/"winning_forest"
    plan = read_json(folder/"plan.json")["plan"]
    latent = read_json(folder/"latent.json")
    raw = read_json(folder/"raw.json")
    forms = list(dict.fromkeys(canonical(row)[0] for row in target))
    require(len(plan) == len(forms), "Incomplete forest")
    require(latent == [list(row) for row in dict.fromkeys(tuple(row[3]) for row in plan)],
            "Latent target order changed")
    gates, values = [], roots(n)
    for row in raw["substitutions"]:
        production = [row[key] for key in ("i", "ai", "j", "aj")]
        a, sa, b, sb = gate(production, len(values))
        gates.append(production); values.append(combine(values[a], sa, values[b], sb))
    residual_outputs = []
    for expression in raw["expressions"]:
        require(expression, "Empty latent expression")
        terms = [(term["index"], term["value"]) for term in expression]
        for wire, orientation in terms:
            index(wire, len(roots(n))+len(raw["substitutions"])); sign(orientation)
        wire, orientation = terms[0]
        for right, right_sign in terms[1:]:
            gates.append([wire, orientation, right, right_sign])
            values.append(combine(values[wire], orientation, values[right], right_sign))
            wire, orientation = len(values)-1, 1
        residual_outputs.append([wire, orientation])
    require(len(gates) == raw["additions"] == 80, "Latent additions must all be charged")
    replay(dict(inputs=n, gates=gates, outputs=residual_outputs), latent)
    residual_wires = dict(zip(map(tuple, latent), residual_outputs))
    target_wires, seen, reconstructed = {}, set(), 0
    for i, parent, orientation, residual, residual_sign in plan:
        index(i, len(forms)); sign(orientation); sign(residual_sign)
        require(i not in seen and (parent == -1 or parent in seen), "Duplicate/cyclic forest vertex")
        require(canonical(residual)[0] == tuple(residual), "Residual sign is not canonical")
        expected = tuple(residual_sign*x for x in residual)
        if parent != -1:
            expected = combine(forms[parent], orientation, expected, 1)
        require(expected == forms[i], "Forest edge identity failed")
        seen.add(i)
        wire, output_sign = residual_wires[tuple(residual)]
        if parent == -1:
            target_wires[i] = (wire, output_sign*residual_sign)
        else:
            parent_wire, parent_sign = target_wires[parent]
            production = [parent_wire, orientation*parent_sign, wire, output_sign*residual_sign]
            a, sa, b, sb = gate(production, len(values))
            gates.append(production); values.append(combine(values[a], sa, values[b], sb))
            target_wires[i] = (len(values)-1, 1)
            reconstructed += 1
    lookup = {form: i for i, form in enumerate(forms)}
    outputs = []
    for row in target:
        form, orientation = canonical(row)
        wire, output_sign = target_wires[lookup[form]]
        outputs.append([wire, orientation*output_sign])
    charged = dict(inputs=n, gates=gates, outputs=outputs)
    require(reconstructed == 147 and replay(charged, target) == 227,
            "Wrong charged reconstruction count")
    saved = read_json(folder/"before227.json")
    require(charged["gates"] == saved["gates"] and charged["outputs"] == saved["outputs"],
            "Saved charged program differs from independently reconstructed program")
    compatibility = read_json(folder/"compatibility.json")
    require(compatibility["counts"]["latent_additions"] == 80 and
            compatibility["counts"]["reconstruction_additions"] == 147 and
            compatibility["counts"]["normalization_savings"] == 3,
            "Wrong compatibility accounting")
    return dict(latent_forms=len(latent), latent_additions=80,
                reconstruction_additions=147, charged_additions=227,
                normalized_additions_signed=224)


def native_rebuild(binary):
    repo = HERE.parents[3]
    spec = importlib.util.spec_from_file_location("forest_evidence_fast_pool",
                                                 repo/"methods/linear/fast_pool.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    reports = {}
    for name in BANKS:
        bank = read_json(HERE/name/"donors.json")
        frozen = read_json(HERE/name/"pool.json")
        rebuilt = module.build_pool(bank, binary=binary)
        fields = ("inputs", "forms", "productions", "outputs", "target_matrix", "incumbent")
        require(all(rebuilt[key] == frozen[key] for key in fields),
                "Native pool rebuild differs: " + name)
        reports[name] = dict(identical_numeric_pool=True, forms=len(rebuilt["forms"]))
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, help="Optional external pool_relations executable")
    parser.add_argument("--output", type=Path, help="Optional new verification report")
    args = parser.parse_args()
    start = time.monotonic()
    hashes = read_json(HERE/"SHA256SUMS.json")
    for name, expected in hashes.items():
        require(hashlib.sha256((HERE/name).read_bytes()).hexdigest() == expected,
                "Artifact hash mismatch: " + name)
    matrices = {name: read_sms(HERE/"maps"/(name+".sms")) for name in ("U", "V", "W", "WT")}
    require(matrices["WT"] == [list(row) for row in zip(*matrices["W"])],
            "WT must be exactly the transpose of original W")
    report = dict(status="PASS", hashed_files=len(hashes), banks={}, candidates={})
    pools = {}
    for name, (matrix_name, expected_donors, expected_forms, initial) in BANKS.items():
        target = matrices[matrix_name]
        bank = read_json(HERE/name/"donors.json")
        require(bank["inputs"] == len(target[0]) and len(bank["circuits"]) == expected_donors,
                "Frozen donor count/input dimension mismatch")
        counts = [replay(circuit, target) for circuit in bank["circuits"]]
        pool = read_json(HERE/name/"pool.json")
        pools[name] = pool
        pool_result = verify_pool(pool, target, expected_forms, initial)
        report["banks"][name] = dict(donors=len(counts), minimum_donor_additions_signed=min(counts),
                                      maximum_donor_additions_signed=max(counts), **pool_result)
    for name, (matrix_name, expected, pool_name) in CANDIDATES.items():
        circuit = read_json(HERE/name)
        count = replay(circuit, matrices[matrix_name])
        require(count == expected, "Candidate gate count mismatch: " + name)
        if pool_name:
            require(selection(pools[pool_name], circuit["pool_selection"], matrices[matrix_name]) == count,
                    "Candidate selection count differs from literal signed circuit")
        report["candidates"][name] = dict(additions_signed=count,
                                          exact_coefficients=len(matrices[matrix_name])*len(matrices[matrix_name][0]))
    source_rows = read_json(HERE/"V/sources.json")
    frozen = read_json(HERE/"V/donors.json")
    indices = read_json(HERE/"V/ablation/frozen_indices.json")
    require(len(source_rows) == len(frozen["circuits"]) == 270 and
            len(indices["removed"]) == 20 and len(indices["retained"]) == 250,
            "Ablation index counts changed")
    require(indices["removed"] == [i for i, row in enumerate(source_rows)
                                    if row["source"].startswith("intelligent/")],
            "Ablation removed a different family")
    require(sorted(indices["removed"]+indices["retained"]) == list(range(270)),
            "Ablation indices do not partition the frozen bank")
    require(read_json(HERE/"V/ablation/donors.json")["circuits"] ==
            [frozen["circuits"][i] for i in indices["retained"]],
            "Ablation changed retained donor DAGs or order")
    report["winning_forest"] = verify_winning_forest(matrices["V"])
    helper = HERE/"intelligent/verify.py"
    spec = importlib.util.spec_from_file_location("forest_intelligent_record_checks", helper)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    report["intelligent_records"] = module.test()
    if args.native:
        report["native_rebuild"] = native_rebuild(args.native.resolve())
    report["elapsed_seconds"] = time.monotonic()-start
    report["scope"] = "Exact signed circuits and numeric search pools; strict negation-free certificates and complete tensor verification are supplied separately"
    text = json.dumps(report, indent=2)+"\n"
    if args.output:
        with args.output.open("x") as file:
            file.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
