#!/usr/bin/env python3
"""Optimize signed output forests, charging residual and reconstruction programs.

The solver receives the original input coordinates. An internal residual map
is solved, then every original output is reconstructed by paid binary gates.
This heuristic does not establish a minimum tree or a globally optimal SLP.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import time


def load_api(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name("common.py")
    spec = importlib.util.spec_from_file_location("output_forest_common", path)
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    return api


def target_forms(target, api):
    api.matrix_check(target)
    return list(dict.fromkeys(api.canonical(row)[0] for row in target))


def prepare_graph(target, api):
    """Keep the minimum-support signed difference for each ordered pair."""
    forms = target_forms(target, api)
    edges, frequencies = [], {}
    for i, row in enumerate(forms):
        neighbors = []
        for j, column in enumerate(forms):
            if i == j:
                continue
            choices = []
            for sign in (1, -1):
                residual = tuple(x - sign*y for x, y in zip(row, column))
                form, orientation = api.canonical(residual)
                choices.append((sum(x != 0 for x in residual), j, sign,
                                form, orientation))
            value = min(choices, key=lambda item: item[0])
            neighbors.append(value)
            frequencies[value[3]] = frequencies.get(value[3], 0) + 1
        edges.append(neighbors)
    return dict(forms=forms, edges=edges, frequencies=frequencies)


def make_plan(target, seed, reward, noise, api, graph=None):
    """Choose an acyclic rooted plan; repeat-residual rewards are heuristic."""
    api.require(type(seed) is int and 0 <= seed < 2**32, "Invalid seed")
    api.require(math.isfinite(reward) and reward >= 0 and
                math.isfinite(noise) and noise >= 0, "Invalid edge weights")
    graph = prepare_graph(target, api) if graph is None else graph
    api.require(graph["forms"] == target_forms(target, api), "Graph target mismatch")
    forms, edges, frequencies = (graph[key] for key in ("forms", "edges", "frequencies"))
    rng = random.Random(seed)
    reached, plan, available = set(), [], {}
    for i, row in enumerate(forms):
        cost = sum(x != 0 for x in row) - 1
        available[i] = (cost + rng.random()*noise, -1, 1, row, 1)
    while len(reached) < len(forms):
        i = min(available, key=lambda index: available[index][0])
        _, parent, sign, residual, orientation = available.pop(i)
        reached.add(i)
        plan.append((i, parent, sign, residual, orientation))
        for support, j, edge_sign, form, edge_orientation in edges[i]:
            if j in reached:
                continue
            # The stored difference is forms[i] - edge_sign*forms[j].
            # Reverse it to express j from the already reached parent i.
            residual_sign = -edge_sign*edge_orientation
            cost = support - reward*frequencies[form]**0.5 + rng.random()*noise
            if cost < available[j][0]:
                available[j] = (cost, i, edge_sign, form, residual_sign)
    return plan


def latent_forms(plan):
    return list(dict.fromkeys(tuple(row[3]) for row in plan))


def reconstruct_plan(target, plan, latent_circuit, api):
    """Compose a validated latent circuit and all charged output-tree gates.

    Do not mutate the latent solver circuit. Its complete converted gate count
    is measured before appending reconstruction, independently of raw metadata.
    Returned outputs have the original ordered signs and duplicate rows.
    """
    forms = target_forms(target, api)
    n = len(target[0])
    api.require(len(plan) == len(forms), "Plan must cover every target form")
    seen = set()
    for row in plan:
        api.require(isinstance(row, (list, tuple)) and len(row) == 5, "Invalid plan row")
        i, parent, sign, residual, orientation = row
        api.require(type(i) is int and 0 <= i < len(forms) and i not in seen,
                    "Invalid or duplicate plan vertex")
        api.require(type(parent) is int and (parent == -1 or parent in seen),
                    "Parent must already be computed; cyclic plans are unsupported")
        api.require(type(sign) is int and sign in (-1, 1) and
                    type(orientation) is int and orientation in (-1, 1), "Invalid plan signs")
        api.require(isinstance(residual, (list, tuple)) and len(residual) == n
                    and all(type(x) is int for x in residual), "Invalid residual vector")
        canonical, _ = api.canonical(residual)
        api.require(tuple(residual) == canonical, "Residual must have canonical sign")
        expected = tuple(orientation*x for x in residual)
        if parent != -1:
            expected = tuple(sign*x + y for x, y in zip(forms[parent], expected))
        api.require(expected == forms[i], "Plan does not reconstruct the required row")
        seen.add(i)
    latent = latent_forms(plan)
    api.require(latent_circuit.get("inputs", n) == n, "Latent input dimension mismatch")
    api.require(api.exact_circuit(latent_circuit, n) == [list(row) for row in latent],
                "Latent circuit differs from the ordered residual map")
    gates = [list(gate) for gate in latent_circuit["gates"]]
    initial_gates = len(gates)
    residual_wires = dict(zip(latent, latent_circuit["outputs"]))
    target_wires, reconstruction_gates = {}, 0
    for i, parent, sign, residual, orientation in plan:
        wire, output_sign = residual_wires[tuple(residual)]
        if parent == -1:
            target_wires[i] = (wire, output_sign*orientation)
        else:
            parent_wire, parent_sign = target_wires[parent]
            gates.append([parent_wire, sign*parent_sign, wire, output_sign*orientation])
            target_wires[i] = (n + len(gates) - 1, 1)
            reconstruction_gates += 1
    index = {form: i for i, form in enumerate(forms)}
    outputs = []
    for row in target:
        form, sign = api.canonical(row)
        wire, output_sign = target_wires[index[form]]
        outputs.append([wire, sign*output_sign])
    charged = dict(inputs=n, gates=gates, outputs=outputs)
    api.require(len(gates) == initial_gates + reconstruction_gates,
                "Charged gate-count mismatch")
    api.require(api.exact_circuit(charged, n) == target, "Charged composition changed the target")
    normalized = api.normalize(charged)
    api.require(api.exact_circuit(normalized, n) == target, "Normalization changed the target")
    counts = dict(latent_additions=initial_gates,
                  reconstruction_additions=reconstruction_gates,
                  charged_additions=len(gates),
                  normalization_savings=len(gates)-len(normalized["gates"]),
                  additions_signed=len(normalized["gates"]))
    return normalized, charged, counts


def run(args):
    api = load_api(args.api)
    api.require(type(args.trials) is int and args.trials > 0, "Positive trial count required")
    api.finite(args.timeout, "Per-call time budget")
    api.finite(args.seconds, "Total time budget")
    api.require(type(args.seed) is int and 0 <= args.seed < 2**32 and
                args.seed + args.trials <= 2**32, "Invalid seed range")
    api.require(math.isfinite(args.savings) and args.savings >= 0 and
                type(args.slack) is int and args.slack >= -1, "Invalid scorer parameters")
    target = api.read_matrix(args.matrix)
    args.out.mkdir(parents=True, exist_ok=False)
    driver, build = api.binary(args, args.out, "repair")
    start = time.monotonic()
    graph = prepare_graph(target, api)
    records, circuits, best = [], [], None
    for trial in range(args.trials):
        remaining = args.seconds - (time.monotonic() - start)
        if remaining <= 0:
            break
        seed = args.seed + trial
        reward = (0, .12, .3, .5)[trial % 4]
        noise = (0, .15, .4, .8)[(trial // 4) % 4]
        plan = make_plan(target, seed, reward, noise, api, graph)
        latent = [list(row) for row in latent_forms(plan)]
        partial, raw_path = args.out/"input.txt", args.out/"raw.json"
        api.write_partial(partial, latent, [])
        bound = max(abs(x) for row in latent for x in row)
        record = dict(trial=trial, seed=seed, reward=reward, noise=noise,
                      latent_forms=len(latent), coefficient_bound=bound,
                      reconstruction_additions=sum(row[1] != -1 for row in plan))
        attempt = time.monotonic()
        try:
            remaining = args.seconds - (attempt - start)
            if remaining <= 0:
                break
            process = subprocess.run([str(driver), str(partial), str(raw_path),
                                      str(seed), str(args.savings), str(args.slack),
                                      "1", str(bound)], capture_output=True, text=True,
                                     timeout=min(args.timeout, remaining))
            api.require(process.returncode == 0, process.stderr.strip())
            raw = api.json_read(raw_path)
            converted = api.convert(raw, latent)
            candidate, charged, counts = reconstruct_plan(target, plan, converted, api)
            record.update(status="PASS", exact_map_verified=True, **counts,
                          raw_solver_additions=raw.get("additions"))
            candidate["name"] = "output_forest_" + str(trial)
            circuits.append(candidate)
            if best is None or counts["additions_signed"] < best:
                best = counts["additions_signed"]
                record["discovery_seconds"] = time.monotonic() - start
                api.save_candidate(args.out/"best_candidate.json", candidate, target)
                api.save_candidate(args.out/"before_normalization.json", charged, target)
                api.dump(args.out/"best.latent.json", latent)
                api.dump(args.out/"best.raw.json", raw)
                api.dump(args.out/"best_plan.json", dict(plan=plan, record=record))
                print("Best", best, "at", record["discovery_seconds"], flush=True)
        except subprocess.TimeoutExpired:
            record["status"] = "TIMEOUT"
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            record.update(status="ERROR", diagnostic=str(error))
        record["seconds"] = time.monotonic() - attempt
        records.append(record)
        api.dump(args.out/"records.json", records)
        api.dump(args.out/"donors.json", dict(inputs=len(target[0]), circuits=circuits))
    summary = dict(best_additions_signed=best, attempts=len(records), accepted=len(circuits),
                   elapsed_seconds=time.monotonic()-start, seed=args.seed,
                   trial_budget=args.trials, seconds=args.seconds, timeout=args.timeout,
                   scorer_savings=args.savings, scorer_slack=args.slack, build=build,
                   source_sha256=api.hashlib.sha256(args.matrix.read_bytes()).hexdigest(),
                   original_inputs=len(target[0]), original_outputs=len(target),
                   target_forms=len(graph["forms"]), free_signed_wires=True,
                   scope="Heuristic internal output factorization; all reconstruction gates charged; strict sign orientation is a separate check")
    api.dump(args.out/"summary.json", summary)
    api.dump(args.out/"records.json", records)
    api.dump(args.out/"donors.json", dict(inputs=len(target[0]), circuits=circuits))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", type=Path, help="Defaults to sibling common.py")
    parser.add_argument("--matrix", required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--binary", type=Path, help="Existing external LEO repair driver")
    source.add_argument("--leo", type=Path, help="Pinned external LEO checkout to compile")
    parser.add_argument("--compiler")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--trials", type=int, default=60)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--seed", type=int, default=8800)
    parser.add_argument("--savings", type=float, default=.01)
    parser.add_argument("--slack", type=int, default=4)
    print(json.dumps(run(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
