#!/usr/bin/env python3
"""Replay one frozen-pool solution with standard-library exact integers only.

This checks the feasible circuit, not the solver's lower bound or optimality
status. Use --pool and --candidate to point at an exported frozen-pool result.
"""
import argparse
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('finite_pool_model', Path(__file__).with_name('finite_pool_cpsat.py'))
model_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model_module)
checked_circuit = model_module.checked_circuit


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pool', required=True, type=Path)
    ap.add_argument('--candidate', required=True, type=Path)
    args = ap.parse_args()
    pool = json.loads(args.pool.read_text())
    candidate = json.loads(args.candidate.read_text())
    n = pool['inputs']
    assert candidate['inputs'] == n
    assert pool['forms'][:n] == [[int(i == j) for j in range(n)] for i in range(n)]
    assert all(len(v) == n and all(type(x) is int for x in v) for v in pool['forms'])
    for t, productions in pool['productions'].items():
        for a, sa, b, sb in productions:
            assert sa in (-1, 1) and sb in (-1, 1)
            assert [sa*x + sb*y for x, y in zip(pool['forms'][a], pool['forms'][b])] == pool['forms'][int(t)]
    selection = {int(t): p for t, p in candidate['pool_selection'].items()}
    for t, prod in selection.items():
        assert prod in pool['productions'][str(t)]
    rebuilt = checked_circuit(pool, selection)
    wires = pool['forms'][:n].copy()
    for a, sa, b, sb in candidate['gates']:
        assert 0 <= a < len(wires) and 0 <= b < len(wires)
        assert sa in (-1, 1) and sb in (-1, 1)
        wires.append([sa*x + sb*y for x, y in zip(wires[a], wires[b])])
    actual = [[s*x for x in wires[t]] for t, s in candidate['outputs']]
    assert actual == candidate['target_matrix'] == pool['target_matrix']
    assert len(candidate['gates']) == candidate['additions_signed'] == len(selection)
    assert len(rebuilt['gates']) == len(candidate['gates'])
    print(json.dumps({'exact_integer_replay': True, 'all_selected_productions_in_pool': True,
                      'acyclic_selected_DAG': True, 'unused_selected_gates': 0,
                      'inputs': n, 'outputs': len(actual), 'signed_additions': len(selection),
                      'optimality_verified': False}, indent=2))


if __name__ == '__main__':
    main()
