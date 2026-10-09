"""Portable exact circuit helpers and adapter for externally installed LEO."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = "2abd2fd8f15dc1c97dd24777515324f865e77504"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


core = module("reconstruction_core", ROOT / "run.py")
builder = module("reconstruction_pool", ROOT / "make_pool.py")
sampler = module("reconstruction_sampler", HERE.parent / "sampling/sample.py")


def require(value, message):
    core.require(value, message)


def finite(value, label):
    require(math.isfinite(value) and value > 0, label + " must be positive and finite")


def json_read(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=core.unique_object)


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def canonical(vector):
    sign = next((1 if x > 0 else -1 for x in vector if x), None)
    require(sign is not None, "Zero intermediate forms are unsupported")
    return tuple(sign * x for x in vector), sign


def exact_circuit(circuit, n):
    roots = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    return builder.read_circuit(circuit, roots, 0)[3]


def candidate(path):
    data = json_read(path)
    n = data.get("inputs")
    require(type(n) is int and n > 0, "Positive integer inputs required")
    actual = exact_circuit(data, n)
    target = data.get("target_matrix", actual)
    require(actual == target, "Source circuit differs from target_matrix")
    matrix_check(target)
    return data, target


def matrix_check(target):
    require(isinstance(target, list) and target and isinstance(target[0], list)
            and target[0], "Nonempty rectangular matrix required")
    n = len(target[0])
    for row in target:
        require(isinstance(row, list) and len(row) == n and any(row),
                "Rectangular nonzero target rows required")
        require(all(type(x) is int and -(2**31) < x < 2**31 for x in row),
                "LEO input coefficients must be 32-bit integers")


def normalize(data):
    """Merge only signed aliases, prune, and preserve all ordered output signs."""
    n = data["inputs"]
    expected = exact_circuit(data, n)
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    known = {v: (i, 1) for i, v in enumerate(values)}
    aliases = [(i, 1) for i in range(n)]
    gates = []
    for a, sa, b, sb in data["gates"]:
        vector = tuple(sa * x + sb * y for x, y in zip(values[a], values[b]))
        values.append(vector)
        form, orientation = canonical(vector)
        if form in known:
            wire, sign = known[form]
            aliases.append((wire, sign * orientation))
            continue
        aa, asa = aliases[a]
        bb, bsb = aliases[b]
        wire = n + len(gates)
        gates.append([aa, sa * asa, bb, sb * bsb])
        known[form] = (wire, orientation)
        aliases.append((wire, 1))
    outputs = [[aliases[w][0], s * aliases[w][1]] for w, s in data["outputs"]]
    live, pending = set(), [w for w, _ in outputs]
    while pending:
        wire = pending.pop()
        if wire < n or wire in live:
            continue
        live.add(wire)
        a, _, b, _ = gates[wire - n]
        pending.extend((a, b))
    remap, pruned = {i: i for i in range(n)}, []
    for wire in sorted(live):
        a, sa, b, sb = gates[wire - n]
        remap[wire] = n + len(pruned)
        pruned.append([remap[a], sa, remap[b], sb])
    result = dict(inputs=n, gates=pruned,
                  outputs=[[remap[w], s] for w, s in outputs])
    require(exact_circuit(result, n) == expected, "Normalization changed the map")
    return result


def cut(data, seeds):
    n = data["inputs"]
    require(all(type(w) is int and n <= w < n + len(data["gates"]) for w in seeds),
            "Cut seeds must be gate wires in the normalized source circuit")
    removed, kept = set(seeds), []
    remap = {i: i for i in range(n)}
    for j, (a, sa, b, sb) in enumerate(data["gates"]):
        wire = n + j
        if wire in removed or a in removed or b in removed:
            removed.add(wire)
            continue
        remap[wire] = n + len(kept)
        kept.append([remap[a], sa, remap[b], sb])
    lost = {w for w, _ in data["outputs"] if w in removed}
    return removed, lost, kept


def write_partial(path, target, gates):
    matrix_check(target)
    n = len(target[0])
    for j, gate in enumerate(gates):
        core.production(gate, n + j)
    Path(path).write_text(f"{len(target)} {n} {len(gates)}\n"
                         + "\n".join(" ".join(map(str, row)) for row in target) + "\n"
                         + "\n".join(" ".join(map(str, gate)) for gate in gates) + "\n")


def read_partial(path):
    tokens = Path(path).read_text().split()
    require(len(tokens) >= 3, "Partial input header required")
    values = list(map(int, tokens))
    rows, n, count = values[:3]
    require(rows > 0 and n > 0 and count >= 0, "Invalid partial input dimensions")
    require(len(values) == 3 + rows * n + 4 * count, "Partial input length mismatch")
    target = [values[3 + j*n:3 + (j+1)*n] for j in range(rows)]
    matrix_check(target)
    offset = 3 + rows * n
    gates = [values[offset + 4*j:offset + 4*j + 4] for j in range(count)]
    signals = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    seen = set(signals)
    for j, gate in enumerate(gates):
        core.production(gate, n + j)
        a, sa, b, sb = gate
        signal = tuple(sa*x+sb*y for x, y in zip(signals[a], signals[b]))
        form, _ = canonical(signal)
        require(form not in seen, "Prepared partial circuit has signed aliases; normalize a candidate first")
        seen.add(form)
        signals.append(signal)
    return target, gates


def read_matrix(path):
    path = Path(path)
    if path.suffix.lower() == ".json":
        value = json_read(path)
        target = value.get("target_matrix") if isinstance(value, dict) else value
    else:
        rows = [line.split() for line in path.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")]
        require(rows and len(rows[0]) >= 2, "Matrix header required")
        r, n = map(int, rows[0][:2])
        require(r > 0 and n > 0, "Positive matrix dimensions required")
        if path.suffix.lower() == ".sms":
            target = [[0] * n for _ in range(r)]
            seen = set()
            for row in rows[1:]:
                require(len(row) == 3, "SMS entries must be row column value")
                a, b, x = map(int, row)
                if (a, b, x) == (0, 0, 0):
                    continue
                require(1 <= a <= r and 1 <= b <= n and (a, b) not in seen,
                        "Invalid or duplicate SMS coordinate")
                seen.add((a, b))
                target[a - 1][b - 1] = x
        else:
            require(len(rows) == r + 1 and all(len(row) == n for row in rows[1:]),
                    "Dense input shape mismatch")
            target = [list(map(int, row)) for row in rows[1:]]
    matrix_check(target)
    return target


def convert(solution, target):
    donor = sampler.convert(solution, target)
    require(exact_circuit(donor, len(target[0])) == target, "Exact donor replay failed")
    return donor


def build(leo, binary, driver="repair", compiler=None, pin=PIN):
    """Compile only our adapter and an external clean, explicitly pinned library."""
    leo, binary = Path(leo).resolve(), Path(binary).resolve()
    commit = subprocess.check_output(["git", "-C", str(leo), "rev-parse", "HEAD"], text=True).strip()
    require(commit == pin, "External LEO checkout must be pinned at " + pin)
    subprocess.run(["git", "-C", str(leo), "diff", "--quiet", "HEAD", "--", "include", "src/leo"], check=True)
    compiler = compiler or next((shutil.which(c) for c in ("c++", "g++", "clang++") if shutil.which(c)), None)
    require(compiler is not None, "A C++17 compiler is required")
    require(driver in ("repair", "population"), "Unknown driver")
    require(not binary.exists(), "Refusing to overwrite binary: " + str(binary))
    binary.parent.mkdir(parents=True, exist_ok=True)
    sources = sorted((leo / "src/leo").rglob("*.cpp"))
    require(sources, "External LEO sources not found")
    command = [compiler, "-std=c++17", "-O3", "-I" + str(leo / "include"),
               str(HERE / (driver + "_driver.cpp")), *map(str, sources), "-o", str(binary)]
    subprocess.run(command, check=True, timeout=180)
    report = dict(leo_commit=commit, driver=driver, compiler=compiler,
                  upstream_unmodified=True,
                  driver_sha256=hashlib.sha256((HERE / (driver + "_driver.cpp")).read_bytes()).hexdigest())
    dump(binary.with_suffix(binary.suffix + ".build.json"), report)
    return report


def binary(args, directory, driver):
    if args.binary is not None:
        path = args.binary.resolve()
        require(path.is_file(), "Driver binary does not exist")
        report_path = path.with_suffix(path.suffix + ".build.json")
        return path, json_read(report_path) if report_path.exists() else dict(external_binary=True)
    require(args.leo is not None, "Supply --leo for compilation or --binary for an existing driver")
    path = directory / (driver + "_driver")
    return path, build(args.leo, path, driver, args.compiler)


def save_candidate(path, circuit, target):
    n = len(target[0])
    require(exact_circuit(circuit, n) == target, "Exported circuit differs from target")
    dump(path, {**circuit, "inputs": n, "target_matrix": target,
                "additions_signed": len(circuit["gates"]), "free_signed_wires": True})
