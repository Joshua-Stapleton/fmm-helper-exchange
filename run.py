#!/usr/bin/env python3
"""Portable exact helper exchanges. Python standard library; C++ only for search."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
SCOPE = "Fixed form pool; at most 3 incumbent helpers removed and 2 added; free signed wires."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, message):
    require(type(value) is int, message)
    return value


def unique_object(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def index(value, size):
    integer(value, "Form indices must be integers")
    require(0 <= value < size, "Form index out of bounds: " + str(value))
    return value


def sign(value):
    require(type(value) is int and value in (-1, 1), "Signs must be integer -1 or +1")
    return value


def production(value, size):
    require(isinstance(value, list) and len(value) == 4, "Production must be [a, sa, b, sb]")
    a, sa, b, sb = value
    return index(a, size), sign(sa), index(b, size), sign(sb)


def mapping(value, size, inputs, many=False):
    require(isinstance(value, dict), "Productions/selections must be JSON objects")
    result = {}
    for key, rows in value.items():
        require(key.isascii() and key.isdigit() and str(int(key)) == key, "Noncanonical form key: " + key)
        out = index(int(key), size)
        require(out >= inputs, "An input cannot have a production")
        if many:
            require(isinstance(rows, list), "Production options must be a list")
            result[out] = [production(row, size) for row in rows]
        else:
            result[out] = production(rows, size)
    return result


def combine(a, sa, b, sb):
    return [sa * x + sb * y for x, y in zip(a, b)]


def audit(selected, data, prods):
    """Check every selected gate, reject any cycle, then prune to the outputs."""
    inputs, forms, outputs = data["inputs"], data["forms"], data["outputs"]
    values = {i: forms[i] for i in range(inputs)}
    pending, order = set(selected), []
    for out, p in selected.items():
        require(p in prods.get(out, ()), "Selected production absent from pool: " + str(out))
    while pending:
        ready = sorted(o for o in pending if selected[o][0] in values and selected[o][2] in values)
        require(ready, "Selected productions contain a cycle or an undefined parent")
        for out in ready:
            a, sa, b, sb = selected[out]
            values[out] = combine(values[a], sa, values[b], sb)
            require(values[out] == forms[out], "Selected production identity failed")
            pending.remove(out)
            order.append(out)
    actual = []
    for out, s in outputs:
        require(out in values, "An output is not computed: " + str(out))
        actual.append([s * x for x in values[out]])
    require(actual == data["target_matrix"], "Exact target matrix mismatch")
    needed, stack = set(), [o for o, _ in outputs]
    while stack:
        out = stack.pop()
        if out < inputs or out in needed:
            continue
        needed.add(out)
        stack.extend((selected[out][0], selected[out][2]))
    order = [o for o in order if o in needed]
    return {o: selected[o] for o in order}


def load(path):
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    require(isinstance(data, dict), "Data must be a JSON object")
    inputs = integer(data["inputs"], "inputs must be an integer")
    forms = data["forms"]
    require(inputs > 0 and isinstance(forms, list) and len(forms) >= inputs, "Invalid input/form count")
    for row in forms:
        require(isinstance(row, list) and len(row) == inputs, "Wrong coefficient vector length")
        require(all(type(x) is int for x in row), "Coefficients must be exact JSON integers")
    for i in range(inputs):
        require(forms[i] == [int(i == j) for j in range(inputs)], "Root inputs must be unit vectors in order")
    prods = mapping(data["productions"], len(forms), inputs, many=True)
    for out, rows in prods.items():
        for a, sa, b, sb in rows:
            require(forms[out] == combine(forms[a], sa, forms[b], sb), "Pool identity failed at form " + str(out))
    require(isinstance(data["outputs"], list), "outputs must be a list")
    for output in data["outputs"]:
        require(isinstance(output, list) and len(output) == 2, "Output must be [form, sign]")
        index(output[0], len(forms))
        sign(output[1])
    target = data["target_matrix"]
    require(isinstance(target, list) and len(target) == len(data["outputs"]), "Target row count mismatch")
    for row in target:
        require(isinstance(row, list) and len(row) == inputs and all(type(x) is int for x in row), "Target must be an integer matrix")
    incumbent = audit(mapping(data["incumbent"], len(forms), inputs), data, prods)
    expected = data.get("expected", {})
    require(isinstance(expected, dict), "expected must be an object")
    if "baseline" in expected:
        require(integer(expected["baseline"], "Expected baseline must be integer") == len(incumbent), "Baseline count mismatch")
    witness = None
    if "witness" in data:
        selected = mapping(data["witness"], len(forms), inputs)
        if "removed" in expected or "added" in expected:
            check_exchange(selected, expected["removed"], expected["added"], incumbent, data)
        witness = audit(selected, data, prods)
        if "additions" in expected:
            require(integer(expected["additions"], "Expected additions must be integer") == len(witness), "Saved witness count mismatch")
    return data, prods, incumbent, witness


def check_exchange(selected, removed, added, incumbent, data):
    targets = {o for o, _ in data["outputs"]}
    helpers = set(incumbent) - targets
    for group in (removed, added):
        require(isinstance(group, list), "Exchange lists must be arrays")
        for out in group:
            index(out, len(data["forms"]))
        require(len(set(group)) == len(group), "Duplicate exchange helper")
    require(0 <= len(added) < len(removed) <= 3 and len(added) <= 2, "Exchange exceeds search bounds")
    require(set(removed) <= helpers, "Removed helper is not an incumbent helper")
    allowed = (helpers - set(removed)) | targets
    require(all(o >= data["inputs"] and o not in allowed for o in added), "Added helper is already allowed or is an input")
    require(set(selected) <= allowed | set(added), "Selection uses a helper outside the exchange")


def export(selected, data, directory):
    inputs = data["inputs"]
    wires, operations = {i: i for i in range(inputs)}, []
    lines = ["# Signed-wire SLP: each binary gate counts as one addition.",
             "# All input, internal-wire and output signs are free; not a literal no-negation count."]
    label = lambda i: "x" + str(i) if i < inputs else "t" + str(i - inputs)
    signed = lambda i, s: ("+" if s == 1 else "-") + label(i)
    for out, (a, sa, b, sb) in selected.items():
        a, b = wires[a], wires[b]
        wires[out] = inputs + len(operations)
        operations.append([a, sa, b, sb])
        lines.append(f"{label(wires[out])} = ({signed(a, sa)}) + ({signed(b, sb)})")
    outputs = [[wires[o], s] for o, s in data["outputs"]]
    lines.extend(f"y{i} = {signed(o, s)}" for i, (o, s) in enumerate(outputs))
    candidate = dict(name=data.get("name", "custom"), inputs=inputs, additions_signed=len(selected),
                     free_signed_wires=True, gates=operations, outputs=outputs,
                     target_matrix=data["target_matrix"], pool_selection=selected)
    (directory / "candidate.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    (directory / "candidate.slp").write_text("\n".join(lines) + "\n", encoding="utf-8")


def search(data, prods, incumbent, seconds, directory):
    # Preserve option order within each numerically sorted output exactly.
    edges = [(o, *p) for o in sorted(prods) for p in prods[o]]
    targets = {o for o, _ in data["outputs"]}
    helpers = sorted(set(incumbent) - targets)
    text = f'{len(data["forms"])} {data["inputs"]} {len(targets)} {len(helpers)} {len(edges)}\n'
    text += " ".join(map(str, sorted(targets))) + "\n" + " ".join(map(str, helpers)) + "\n"
    text += "".join(f"{o} {a} {b}\n" for o, a, sa, b, sb in edges)
    compiler = next((shutil.which(c) for c in ("c++", "g++", "clang++") if shutil.which(c)), None)
    require(compiler is not None, "Search needs a C++17 compiler; --verify-only does not")
    with tempfile.TemporaryDirectory(prefix="helper-exchange-") as temp:
        temp = Path(temp)
        built = subprocess.run([compiler, "-O3", "-std=c++17", str(HERE / "exchange.cpp"), "-o", str(temp / "exchange")], capture_output=True, text=True, timeout=120)
        require(built.returncode == 0, "C++ compilation failed:\n" + built.stderr)
        (temp / "input.txt").write_text(text, encoding="utf-8")
        start = time.monotonic()
        try:
            proc = subprocess.run([str(temp / "exchange"), str(temp / "input.txt"), str(seconds)], capture_output=True, text=True, timeout=seconds + 30)
            stdout, stderr = proc.stdout, proc.stderr
            require(proc.returncode == 0, "Search failed: " + stderr)
            hard_timeout = False
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout or b""
            stderr = error.stderr or b""
            stdout = stdout.decode() if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode() if isinstance(stderr, bytes) else stderr
            hard_timeout = True
        elapsed = time.monotonic() - start
    if directory:
        for name, value in (("input.txt", text), ("stdout.txt", stdout), ("stderr.txt", stderr)):
            (directory / name).write_text(value, encoding="utf-8")
    result = dict(seconds=elapsed, diagnostic=stderr.strip())
    selected = None
    if hard_timeout:
        result["status"] = "TIME_LIMIT_HARD"
    elif stdout.startswith("FOUND\n"):
        lines = stdout.splitlines()
        groups = [list(map(int, line.split())) for line in lines[1:3]]
        require(len(groups) == 2 and all(g and g[0] == len(g) - 1 for g in groups), "Malformed exchange output")
        removed, added = [g[1:] for g in groups]
        raw = {}
        for line in lines[3:]:
            out, edge = map(int, line.split())
            index(edge, len(edges))
            oo, a, sa, b, sb = edges[edge]
            require(oo == out and out not in raw, "Invalid indexed production in search output")
            raw[out] = (a, sa, b, sb)
        check_exchange(raw, removed, added, incumbent, data)
        selected = audit(raw, data, prods)
        require(len(selected) < len(incumbent), "Search returned no strict improvement")
        result.update(status="FOUND", removed=removed, added=added)
    else:
        status = stderr.split()[0] if stderr.split() else ""
        require(not stdout.strip() and status in ("TIME_LIMIT", "EXHAUSTED_3_FOR_2"), "Unrecognized search response")
        result["status"] = status
    return result, selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--example", choices=("u", "wt"))
    source.add_argument("--data", type=Path, help="Custom JSON pool with exact target and incumbent")
    parser.add_argument("--verify-only", action="store_true", help="Verify saved witness, or incumbent if absent; no compiler needed")
    parser.add_argument("--seconds", type=float, default=180, help="Search time budget (default: 180)")
    parser.add_argument("--out", type=Path, help="New output directory; existing paths are never overwritten")
    args = parser.parse_args()
    require(math.isfinite(args.seconds) and args.seconds > 0, "--seconds must be finite and positive")
    data, prods, incumbent, witness = load(args.data or HERE / "data" / ((args.example or "wt") + ".json"))
    if args.out:
        args.out.mkdir(parents=True, exist_ok=False)
    result = dict(name=data.get("name", "custom"), baseline_additions_signed=len(incumbent),
                  saved_witness_additions_signed=None if witness is None else len(witness),
                  free_signed_wires=True, scope=SCOPE)
    if args.verify_only:
        selected = witness if witness is not None else incumbent
        result["status"] = "VERIFIED_SAVED_WITNESS" if witness is not None else "VERIFIED_INCUMBENT"
    else:
        searched, selected = search(data, prods, incumbent, args.seconds, args.out)
        result.update(searched)
    result["additions_signed"] = None if selected is None else len(selected)
    if args.out:
        if selected is not None:
            export(selected, data, args.out)
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)
