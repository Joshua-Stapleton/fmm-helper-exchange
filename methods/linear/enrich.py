#!/usr/bin/env python3
"""Add exact helper pairs linked through target residuals; standard library only.

This is the arbitrary-precision portable version of the 7 October pair generator.
It includes degree ranking and a connected-density selection heuristic.
Only one endpoint is beam-limited; its residual may be any generated pair form.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from common import core


def canonical(v):
    first = next((x for x in v if x), 0)
    if not first:
        return None, 1
    sign = 1 if first > 0 else -1
    return tuple(sign * x for x in v), sign


def pair_forms(forms):
    known = set(forms)
    representations = defaultdict(list)
    for a, left in enumerate(forms):
        for b in range(a + 1, len(forms)):
            for sign in (1, -1):
                form, orientation = canonical(tuple(x + sign * y for x, y in zip(left, forms[b])))
                if form and form not in known:
                    representations[form].append((a, orientation, b, orientation * sign))
    return representations


def productions(forms, inputs):
    index = {v: i for i, v in enumerate(forms)}
    result = defaultdict(set)
    for a, left in enumerate(forms):
        for b in range(a, len(forms)):
            for sign in (1, -1):
                form, orientation = canonical(tuple(x + sign * y for x, y in zip(left, forms[b])))
                out = index.get(form)
                if out is not None and out >= inputs and out not in (a, b):
                    result[out].add((a, orientation, b, orientation * sign))
    return {str(o): [list(p) for p in sorted(rows)] for o, rows in sorted(result.items())}


def enrich(data, cap=32, beam=4096, mode="linked", selection="degree"):
    forms = [tuple(v) for v in data["forms"]]
    core.require(len(set(forms)) == len(forms), "Pool must contain unique forms")
    core.require(all(canonical(v)[0] == v for v in forms), "Pool must be sign canonical")
    reps = pair_forms(forms)
    targets = sorted({forms[o] for o, _ in data["outputs"]})
    incumbent = {int(i) for i in data["incumbent"]} - {o for o, _ in data["outputs"]}
    incidences = {v: {i for a, _, b, _ in rows for i in (a, b)} for v, rows in reps.items()}
    if mode == "shared":
        def shared_score(v):
            return (-len(incidences[v] & incumbent), -len(incidences[v]), -len(reps[v]),
                    sum(x != 0 for x in v), sum(abs(x) for x in v), v)
        appended = sorted((v for v in reps if len(reps[v]) >= 2), key=shared_score)[:cap]
        result = dict(data)
        result["forms"] = [list(v) for v in forms + appended]
        result["productions"] = productions(forms + appended, data["inputs"])
        for out, rows in data["productions"].items():
            merged = {tuple(p) for p in result["productions"].get(out, [])} | {tuple(p) for p in rows}
            result["productions"][out] = [list(p) for p in sorted(merged)]
        return result, dict(old_forms=len(forms), candidate_forms=len(reps), added_forms=len(appended),
                            mode=mode, selected_pairs=[dict(form=v, productions=reps[v]) for v in appended],
                            scope="Shared pair-form heuristic; no optimality claim")
    def preliminary(v):
        return (-len(incidences[v] & incumbent), -len(reps[v]),
                sum(x != 0 for x in v), sum(abs(x) for x in v), v)
    ordered = sorted(reps, key=preliminary)[:beam]
    witnesses = defaultdict(set)
    target_degrees = defaultdict(set)
    for target in targets:
        for left in ordered:
            for sign in (1, -1):
                right, orientation = canonical(tuple(t - sign * x for t, x in zip(target, left)))
                if right not in reps or right == left:
                    continue
                core.require(tuple(sign*x + orientation*y for x, y in zip(left, right)) == target,
                             "Target residual identity failed")
                a, b = sorted((left, right))
                sa, sb = (sign, orientation) if a == left else (orientation, sign)
                witnesses[a, b].add((target, sa, sb))
                target_degrees[a].add(target)
                target_degrees[b].add(target)
    def score(pair):
        a, b = pair
        return (-len(target_degrees[a]) - len(target_degrees[b]),
                -len({t for t, _, _ in witnesses[pair]}),
                -len((incidences[a] | incidences[b]) & incumbent),
                -len(reps[a]) - len(reps[b]),
                sum(x != 0 for x in a) + sum(x != 0 for x in b), pair)
    selected, appended, pairs = set(), [], []
    ranked = sorted(witnesses, key=score)
    selected_pairs = []
    if selection == "degree":
        for a, b in ranked:
            needed = [v for v in (a, b) if v not in selected]
            if not needed or len(selected) + len(needed) > cap:
                continue
            selected.update(needed)
            appended.extend(needed)
            selected_pairs.append((a, b))
    elif cap >= 2:
        # Prefer actual reuse within a selected connected witness graph over
        # hypothetical degree through many helpers that will remain unchosen.
        adjacency = defaultdict(dict)
        for (a, b), rows in witnesses.items():
            labels = {t for t, _, _ in rows}
            adjacency[a][b] = labels
            adjacency[b][a] = labels
        best = None
        for seed in ranked[:16]:
            kept, sequence = set(seed), list(seed)
            covered = set(adjacency[seed[0]][seed[1]])
            front = (set(adjacency[seed[0]]) | set(adjacency[seed[1]])) - kept
            while len(kept) < cap and front:
                def grow_score(v):
                    hits = {t for neighbor, labels in adjacency[v].items() if neighbor in kept for t in labels}
                    edges = sum(neighbor in kept for neighbor in adjacency[v])
                    return (-len(hits-covered), -edges, -len(hits),
                            -len(incidences[v] & incumbent), sum(x != 0 for x in v), v)
                v = min(front, key=grow_score)
                front.remove(v)
                covered.update(t for neighbor, labels in adjacency[v].items() if neighbor in kept for t in labels)
                kept.add(v)
                sequence.append(v)
                front.update(set(adjacency[v]) - kept)
            edges = sum(b in kept for a in kept for b in adjacency[a]) // 2
            quality = (len(covered), edges, -sum(x != 0 for v in kept for x in v))
            if best is None or quality > best[0]:
                best = quality, sequence, kept
        if best:
            _, appended, selected = best
            selected_pairs = [(a, b) for a, b in ranked if a in selected and b in selected]
    for a, b in selected_pairs:
        target, sa, sb = sorted(witnesses[a, b])[0]
        pairs.append(dict(left=a, right=b, target=target, signs=[sa, sb],
                          left_productions=reps[a], right_productions=reps[b]))
    result = dict(data)
    result["forms"] = [list(v) for v in forms + appended]
    result["productions"] = productions(forms + appended, data["inputs"])
    # Preserve all original identities, including noncanonical operand order.
    for out, rows in data["productions"].items():
        merged = {tuple(p) for p in result["productions"].get(out, [])} | {tuple(p) for p in rows}
        result["productions"][out] = [list(p) for p in sorted(merged)]
    report = dict(old_forms=len(forms), candidate_forms=len(reps), beam=len(ordered),
                  witnessed_pairs=len(witnesses), added_forms=len(appended), selection=selection, selected_pairs=pairs,
                  scope="Heuristic finite-pool enrichment; no optimality claim")
    return result, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cap", type=int, default=32)
    parser.add_argument("--beam", type=int, default=4096)
    parser.add_argument("--mode", choices=("shared", "linked"), default="linked")
    parser.add_argument("--selection", choices=("degree", "density"), default="degree")
    args = parser.parse_args()
    core.require(args.cap >= 0 and args.beam > 0, "Invalid cap/beam")
    data, _, _, _ = core.load(args.data)
    args.out.mkdir(parents=True, exist_ok=False)
    result, report = enrich(data, args.cap, args.beam, args.mode, args.selection)
    pool = args.out / "pool.json"
    pool.write_text(json.dumps(result, separators=(",", ":")) + "\n")
    core.load(pool)  # Recheck every production, incumbent and saved witness.
    (args.out / "witnesses.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "selected_pairs"}, indent=2))


if __name__ == "__main__":
    main()
