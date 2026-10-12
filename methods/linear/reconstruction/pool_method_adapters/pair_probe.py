#!/usr/bin/env python3
"""Construction-only reranking of frozen prefixes by exact one-gate outputs.

No solver is called. This is a different proposed selection policy, recorded
separately from the preregistered L1 experiment.
"""
import json
from pathlib import Path
import time

import lookahead as m

HERE = Path(__file__).resolve().parent


def pair_score(program, target):
    base = m.score_prefix(program, target)
    values = m.expanded_values(program)
    signed = {vector for value in values for vector in (value, tuple(-x for x in value))}
    canonical_targets = {m.audit.canonical(row)[0] for row in target}
    covered = canonical_targets & signed
    unlocked = set()
    # Both parent vectors must already be present. A repeated parent is valid
    # and costs one doubling addition; zero vectors are never admitted.
    for target_form in canonical_targets-covered:
        for value in signed:
            residual = tuple(a-b for a, b in zip(target_form, value))
            if residual in signed:
                unlocked.add(target_form)
                break
    # Reduce the existing L1 proxy only where a concrete one-gate producer is
    # exhibited. All prefix construction gates remain paid and unchanged.
    adjusted = base['closest_signed_l1_ordered_sum']
    ordered_unlocked = 0
    for target_row in target:
        form = m.audit.canonical(target_row)[0]
        if form not in unlocked:
            continue
        ordered_unlocked += 1
        distance = min(sum(abs(a-b) for a, b in zip(form, vector)) for vector in signed)
        adjusted -= max(0, distance-1)
    return dict(base=base, adjusted_remaining_proxy=adjusted,
                exact_one_gate_unique_targets=len(unlocked),
                exact_one_gate_ordered_targets=ordered_unlocked,
                key=[adjusted, -len(covered), -len(unlocked), len(program['gates'])],
                scope='Whole-prefix rerank; exact additional one-gate outputs; still a heuristic for total completion')



def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, required=True,
                        help='Explicit paid binary prefix JSON; original roots only')
    parser.add_argument('--matrix', type=Path, required=True)
    args = parser.parse_args()
    score = pair_score(json.loads(args.prefix.read_text()), m.audit.read_matrix(args.matrix))
    print(json.dumps(score, indent=2))


if __name__ == '__main__':
    main()
