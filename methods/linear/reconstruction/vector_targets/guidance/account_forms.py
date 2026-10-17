#!/usr/bin/env python3
"""Account for skipped hints, recreated omissions and novel helper forms.

Counts below normalize signed aliases and prune to original outputs. They are
signed-wire counts, not a certificate for a strict paid-negation cost model.
"""
import argparse
import json
from pathlib import Path
from select_removals import RemovalSelector, canonical, require


def live_forms(circuit):
    n = circuit["inputs"]
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    for j, (a, sa, b, sb) in enumerate(circuit["gates"]):
        require(0 <= a < n + j and 0 <= b < n + j and sa in (-1, 1)
                and sb in (-1, 1), "Invalid binary gate")
        values.append(tuple(sa*x + sb*y for x, y in zip(values[a], values[b])))
    matrix = [[s*x for x in values[w]] for w, s in circuit["outputs"]]
    require(matrix == circuit.get("target_matrix", matrix), "Circuit target mismatch")
    live, stack = set(), [w for w, _ in circuit["outputs"]]
    while stack:
        w = stack.pop()
        if w < n or w in live:
            continue
        live.add(w)
        a, _, b, _ = circuit["gates"][w-n]
        stack.extend((a, b))
    roots = set(values[:n])
    forms = {canonical(values[w])[0] for w in live} - roots
    targets = {canonical(v)[0] for v in matrix} - roots
    return dict(matrix=matrix, forms=forms, targets=targets, live_raw_gates=len(live))


def account(original, reconstructed, removed_native_helper_indices):
    old, new = live_forms(original), live_forms(reconstructed)
    require(original["inputs"] == reconstructed["inputs"] and old["matrix"] == new["matrix"],
            "Original and reconstructed maps differ")
    # Native indexing needs replay/filtering only, not quadratic production mining.
    n = original["inputs"]
    selector = RemovalSelector(original, dict(inputs=n,
        forms=[[int(i == j) for j in range(n)] for i in range(n)], productions={}))
    helper_forms = [tuple(h["canonical_coefficients"]) for h in selector.helpers]
    old_helpers = set(helper_forms)
    require(old_helpers | old["targets"] == old["forms"],
            "Identity assumes all original helpers are live and every nonoutput/noninput form has support>=2")
    removed_indices = sorted(set(removed_native_helper_indices))
    require(len(removed_indices) == len(removed_native_helper_indices), "Duplicate removal index")
    require(all(type(i) is int and 0 <= i < len(helper_forms) for i in removed_indices),
            "Removal index out of range")
    removed = {helper_forms[i] for i in removed_indices}
    survivors = old_helpers - removed
    new_helpers = new["forms"] - new["targets"]
    dropped = survivors - new_helpers
    recreated = removed & new_helpers
    novel = new_helpers - old_helpers
    gain = len(old["forms"]) - len(new["forms"])
    predicted = len(removed) + len(dropped) - len(recreated) - len(novel)
    require(gain == predicted, "Set-accounting identity failed")
    return dict(status="EXACT_FORM_ACCOUNTING_PASS", scope="live sign-canonical forms; aliases normalized; not paid-negation cost",
                original_signed_normalized_gates=len(old["forms"]),
                reconstructed_signed_normalized_gates=len(new["forms"]),
                original_live_raw_gates=old["live_raw_gates"],
                reconstructed_live_raw_gates=new["live_raw_gates"],
                omitted_hint_count_k=len(removed), unused_survivor_count_d=len(dropped),
                recreated_omission_count_b=len(recreated), novel_helper_count_q=len(novel),
                normalized_gain=gain, identity="gain = k + d - b - q",
                removed_native_helper_indices=removed_indices,
                unused_survivor_native_helper_indices=[i for i, f in enumerate(helper_forms) if f in dropped],
                recreated_omission_native_helper_indices=[i for i, f in enumerate(helper_forms) if f in recreated],
                novel_helper_vectors=[list(f) for f in sorted(novel)])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original", type=Path)
    p.add_argument("reconstructed", type=Path)
    p.add_argument("--removed", required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    result = account(json.loads(args.original.read_text()), json.loads(args.reconstructed.read_text()),
                     list(map(int, args.removed.split(","))))
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
