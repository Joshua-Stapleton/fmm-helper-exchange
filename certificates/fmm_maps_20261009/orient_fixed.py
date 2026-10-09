#!/usr/bin/env python3
"""Find negation-free signs for a fixed signed binary circuit and fixed outputs.

This is feasibility on the given DAG, not global optimization. OR-Tools is used
only to choose wire signs. Inputs and required outputs cannot be reoriented.
The resulting literal program is checked by the independent stdlib verifier.
"""
import argparse
import itertools
import json
from pathlib import Path
from fractions import Fraction as Q
from ortools.sat.python import cp_model
from verify_literal import read_sms, replay


def compact(c):
    if 'gates' in c:
        return c
    n = c['inputs']; alias = [(i, 1) for i in range(n)]; gates = []
    for node in c['nodes']:
        op = node['op']
        if op == 'scale':
            coefficient = Q(node['c'])
            assert coefficient in (-1, 1), 'Nonunit scale unsupported'
            a, sa = alias[node['a']]
            alias.append((a, sa * int(coefficient)))
        elif op in ('add', 'sub'):
            a, sa = alias[node['a']]; b, sb = alias[node['b']]
            gates.append([a, sa, b, sb * (-1 if op == 'sub' else 1)])
            alias.append((n + len(gates) - 1, 1))
        else:
            raise ValueError(op)
    return dict(inputs=n, gates=gates, outputs=[alias[i] for i in c['outputs']])


def orient(c, seconds):
    c = compact(c); n = c['inputs']
    m = cp_model.CpModel()
    neg = [m.new_bool_var(f'neg_{i}') for i in range(n + len(c['gates']))]
    for bit in neg[:n]:
        m.add(bit == 0)
    for o, s in c['outputs']:
        m.add(neg[o] == int(s < 0))
    for k, (a, sa, b, sb) in enumerate(c['gates'], n):
        allowed = [(z, x, y) for z, x, y in itertools.product((0, 1), repeat=3)
                   if sa * (-1)**(z+x) > 0 or sb * (-1)**(z+y) > 0]
        m.add_allowed_assignments([neg[k], neg[a], neg[b]], allowed)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = seconds
    status = solver.solve(m)
    report = dict(status=solver.status_name(status), signed_gate_count=len(c['gates']),
                  scope='Fixed DAG; fixed input signs and all fixed output signs', seconds=solver.wall_time)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, report
    name = lambda i: f'i{i}' if i < n else f't{i-n}'
    lines = []
    for k, (a, sa, b, sb) in enumerate(c['gates'], n):
        aa = sa * (-1)**(solver.value(neg[k]) + solver.value(neg[a]))
        bb = sb * (-1)**(solver.value(neg[k]) + solver.value(neg[b]))
        assert aa == 1 or bb == 1
        if aa < 0:
            a, b = b, a; aa, bb = bb, aa
        lines.append(f'{name(k)}:={name(a)}{"+" if bb == 1 else "-"}{name(b)};')
    for k, (o, s) in enumerate(c['outputs']):
        assert s * (-1)**solver.value(neg[o]) == 1
        lines.append(f'o{k}:={name(o)};')
    return '\n'.join(lines) + '\n', report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('candidate', type=Path)
    p.add_argument('matrix', type=Path)
    p.add_argument('out', type=Path)
    p.add_argument('--seconds', type=float, default=30)
    a = p.parse_args()
    c = json.loads(a.candidate.read_text())
    text, result = orient(c, a.seconds)
    if text is not None:
        matrix, _ = read_sms(a.matrix)
        actual, counts = replay(text, len(matrix[0]))
        assert matrix == actual
        assert counts['unary_negations'] == counts['nonunit_scalars'] == 0
        result.update(exact_coefficient_identities=len(matrix)*len(matrix[0]), counts=counts)
        a.out.write_text(text)
    a.out.with_suffix('.orientation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
