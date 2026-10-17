#!/usr/bin/env python3
"""Exact four-input counterexample to decomposing every 3-for-2 exchange.

Standard library only. The unrestricted pair test enumerates every possible
single addition/subtraction replacement, including repeated arguments. It is
a local-neighborhood statement, not a global SLP lower bound.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


FORMS = {
    "a": (1, 0, 0, 0), "b": (0, 1, 0, 0),
    "c": (0, 0, 1, 0), "d": (0, 0, 0, 1),
    "y1": (0, 1, 0, 1), "y2": (0, 1, 0, -1),
    "y3": (1, -1, -1, 1), "y4": (1, -1, 1, 0),
    "p": (1, 0, 0, 1), "q": (0, 1, -1, 1),
    "r": (0, 1, 1, 0), "u": (0, 0, 1, -1),
    "v": (1, -1, 0, 1),
}
INPUTS = {FORMS[n] for n in ("a", "b", "c", "d")}
OUTPUTS = {FORMS[n] for n in ("y1", "y2", "y3", "y4")}
OLD_HELPERS = {FORMS[n] for n in ("p", "q", "r")}
NEW_HELPERS = {FORMS[n] for n in ("u", "v")}
# Each record is (result, left operand, operation, right operand).
OLD = [
    ("y1", "b", "+", "d"), ("y2", "b", "-", "d"),
    ("p", "a", "+", "d"), ("q", "y1", "-", "c"),
    ("r", "b", "+", "c"), ("y3", "p", "-", "r"),
    ("y4", "p", "-", "q"),
]
NEW = [
    ("y1", "b", "+", "d"), ("y2", "b", "-", "d"),
    ("u", "c", "-", "d"), ("v", "a", "-", "y2"),
    ("y3", "v", "-", "c"), ("y4", "v", "+", "u"),
]


def canonical(vector):
    """Identify a linear form and its negative; zero adds no useful helper."""
    for x in vector:
        if x:
            return tuple(z if x > 0 else -z for z in vector)
    return None


def one_gate_forms(ready):
    # Both parent signs are covered after canonicalization. Including repeated
    # arguments also covers doubling; no scalar multiplication is assumed.
    return {
        result
        for a, b in itertools.combinations_with_replacement(sorted(ready), 2)
        for sign in (-1, 1)
        if (result := canonical(tuple(x + sign * y for x, y in zip(a, b)))) is not None
    }


def closure(allowed):
    ready = set(INPUTS)
    while True:
        newly_ready = (one_gate_forms(ready) & allowed) - ready
        if not newly_ready:
            return ready
        ready |= newly_ready


def replay(circuit):
    values = {n: FORMS[n] for n in ("a", "b", "c", "d")}
    parents = {}
    for out, left, operation, right in circuit:
        assert out not in values
        sign = 1 if operation == "+" else -1
        result = tuple(x + sign * y for x, y in zip(values[left], values[right]))
        assert result == FORMS[out]
        values[out] = result
        parents[out] = (left, right)
    for name in ("y1", "y2", "y3", "y4"):
        assert values[name] == FORMS[name]
    used, pending = set(), ["y1", "y2", "y3", "y4"]
    while pending:
        node = pending.pop()
        if node in used or node not in parents:
            continue
        used.add(node)
        pending.extend(parents[node])
    assert len(used) == len(circuit), "Every counted gate must be live."
    return len(used)


def verify():
    assert replay(OLD) == 7 and replay(NEW) == 6
    assert OUTPUTS <= closure(OUTPUTS | OLD_HELPERS)
    assert OUTPUTS <= closure(OUTPUTS | NEW_HELPERS)
    names = {v: k for k, v in FORMS.items()}
    single_checks = []
    for removed in sorted(OLD_HELPERS):
        assert not OUTPUTS <= closure(OUTPUTS | (OLD_HELPERS - {removed}))
        single_checks.append(names[removed])
    pair_checks = []
    finite_pool = set(FORMS.values())
    for removed in itertools.combinations(sorted(OLD_HELPERS), 2):
        allowed = OUTPUTS | (OLD_HELPERS - set(removed))
        ready = closure(allowed)
        assert not OUTPUTS <= ready
        # This list is complete even for an arbitrary integer replacement:
        # before its one defining gate, only already reachable forms exist.
        candidates = one_gate_forms(ready) - INPUTS - allowed
        successes = [candidate for candidate in sorted(candidates)
                     if OUTPUTS <= closure(allowed | {candidate})]
        assert not successes
        pair_checks.append({
            "removed": sorted(names[v] for v in removed),
            "ready_forms_before_repair": len(ready),
            "all_one_gate_forms_before_excluding_existing": len(one_gate_forms(ready)),
            "arbitrary_new_integer_forms_tested": len(candidates),
            "saved_pool_forms_among_candidates": len(candidates & finite_pool),
            "successful_repairs": successes,
        })
    return {
        "status": "PASS",
        "old_additions": 7,
        "new_additions": 6,
        "old_helpers": ["p", "q", "r"],
        "new_helpers": ["u", "v"],
        "single_deletions_exhausted": single_checks,
        "all_pairs_exhausted": pair_checks,
        "proof_scope": "No first strictly improving one-deletion or two-deletion/one-insertion exchange exists at the old circuit, even allowing any one-addition/subtraction integer replacement form. A joint three-deletion/two-insertion replacement exists.",
        "does_not_claim": "Global SLP optimality, impossibility of equal-cost or temporarily larger paths, or a new matrix-multiplication record.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path for a JSON receipt.")
    args = parser.parse_args()
    receipt = verify()
    if args.output:
        args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
