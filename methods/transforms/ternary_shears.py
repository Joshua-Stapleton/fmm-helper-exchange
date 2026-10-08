#!/usr/bin/env python3
"""Independent standard-library checks for ternary right-shear histories."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identity(n):
    return [[int(i == j) for j in range(n)] for i in range(n)]


def transpose(a):
    return list(map(list, zip(*a)))


def product(a, b):
    require(len(a[0]) == len(b), 'matrix dimension mismatch')
    return [[sum(x*y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def nnz(a):
    return sum(x != 0 for row in a for x in row)


def ternary(a):
    return all(type(x) is int and -1 <= x <= 1 for row in a for x in row)


def shear(width, destination, donors, sign=1):
    require(0 <= destination < width, 'bad destination')
    require(1 <= len(donors) <= 4, 'expected one to four donors')
    require(len({i for i, _ in donors}) == len(donors), 'repeated donor')
    t = identity(width)
    for i, s in donors:
        require(0 <= i < width and i != destination and s in (-1, 1), 'bad donor')
        t[i][destination] = sign*s
    return t


def safe_bitsets(m, destination, donor, sign):
    pos = [sum((x == 1) << r for r, x in enumerate(c)) for c in zip(*m)]
    neg = [sum((x == -1) << r for r, x in enumerate(c)) for c in zip(*m)]
    p, n = (pos[donor], neg[donor]) if sign == 1 else (neg[donor], pos[donor])
    conflicts = (pos[destination] & p) | (neg[destination] & n)
    births = (p | n) & ~(pos[destination] | neg[destination])
    cancellations = (pos[destination] & n) | (neg[destination] & p)
    return conflicts == 0, births.bit_count() - cancellations.bit_count()


def verify_move(m, destination, donors):
    require(m and m[0] and all(len(row) == len(m[0]) for row in m), 'ragged input')
    require(ternary(m), 'source is not ternary')
    t = shear(len(m[0]), destination, donors)
    inv = shear(len(m[0]), destination, donors, -1)
    updated = product(m, t)
    require(product(t, inv) == identity(len(t)), 'inverse mismatch')
    safe = ternary(updated)
    direct = all(-1 <= row[destination] + sum(s*row[i] for i, s in donors) <= 1 for row in m)
    require(safe == direct, 'linear-constraint criterion mismatch')
    if len(donors) == 1:
        bit_safe, delta = safe_bitsets(m, destination, *donors[0])
        require(bit_safe == safe, 'bitset criterion mismatch')
        if safe:
            require(delta == nnz(updated) - nnz(m), 'nonzero delta mismatch')
    return {'safe': safe, 'matrix': updated, 'right': t, 'inverse': inv,
            'nnz_delta': nnz(updated)-nnz(m), 'literal_outer_additions': len(donors)}


def verify_history(source, moves, expected=None):
    width = len(source[0])
    current, basis, inv = source, identity(width), identity(width)
    counts = 0
    for move in moves:
        result = verify_move(current, move['destination'], move['donors'])
        require(result['safe'], 'unsafe endpoint')
        current = result['matrix']
        basis = product(basis, result['right'])
        inv = product(result['inverse'], inv)
        counts += result['literal_outer_additions']
    require(product(basis, inv) == identity(width), 'accumulated inverse mismatch')
    require(product(source, basis) == current, 'history composition mismatch')
    require(product(current, inv) == source, 'input conversion recovery failed')
    require(product(transpose(inv), transpose(current)) == transpose(source), 'decoder conversion recovery failed')
    if expected is not None:
        require(current == expected, 'expected final factor mismatch')
    return {'matrix': current, 'right_basis': basis, 'input_outer': inv,
            'decoder_outer': transpose(inv), 'literal_outer_additions': counts}


def verify_standard_tensor(dense):
    """Project convention: U/V row-major inputs, W trace/column-major output."""
    n, m, k = dense['shape']
    u, v, w = (dense[key] for key in ('u', 'v', 'w'))
    require(len(u) == len(v) == len(w), 'rank mismatch')
    require(all(len(row) == n*m for row in u), 'U width')
    require(all(len(row) == m*k for row in v), 'V width')
    require(all(len(row) == k*n for row in w), 'W width')
    checks = 0
    for a, b, c in itertools.product(range(n*m), range(m*k), range(k*n)):
        ai, aj = divmod(a, m)
        bj, bh = divmod(b, k)
        ch, ci = divmod(c, n)
        actual = sum(x[a]*y[b]*z[c] for x, y, z in zip(u, v, w))
        require(actual == int(ai == ci and aj == bj and bh == ch), 'standard tensor identity failed')
        checks += 1
    return checks


def self_test():
    scalar_checks = 0
    for row in itertools.product((-1, 0, 1), repeat=3):
        for j in range(3):
            for i in range(3):
                if i == j:
                    continue
                for s in (-1, 1):
                    verify_move([list(row)], j, [(i, s)])
                    scalar_checks += 1
            others = [i for i in range(3) if i != j]
            for signs in itertools.product((-1, 1), repeat=2):
                verify_move([list(row)], j, list(zip(others, signs)))
                scalar_checks += 1
    counter = [[1, 1, -1], [1, -1, 1], [1, -1, 0]]
    require(not verify_move(counter, 0, [(1, 1)])['safe'], 'first unsafe control')
    require(not verify_move(counter, 0, [(2, 1)])['safe'], 'second unsafe control')
    result = verify_move(counter, 0, [(1, 1), (2, 1)])
    require(result['safe'] and result['nnz_delta'] == -1, 'endpoint-only control')
    history = [{'destination': 1, 'donors': [(0, 1)]}, {'destination': 2, 'donors': [(1, -1)]}]
    h = verify_history(identity(3), history)
    wrong_order = product(shear(3, 1, [(0, 1)], -1), shear(3, 2, [(1, -1)], -1))
    require(wrong_order != h['input_outer'], 'inverse-order negative control ineffective')
    rejected = []
    for name, move in [('self donor', (0, [(0, 1)])), ('duplicate donor', (0, [(1, 1), (1, -1)]))]:
        try:
            verify_move(identity(3), *move)
        except ValueError:
            rejected.append(name)
    require(len(rejected) == 2, 'invalid move accepted')
    return {'status': 'PASS', 'exhaustive_three_column_one_row_checks': scalar_checks,
            'endpoint_only_counterexample': result, 'noncommuting_history': h,
            'negative_controls': rejected + ['wrong inverse order distinguished']}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--history-json', type=Path, help='JSON containing source, moves, optional expected')
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    result = self_test()
    if args.history_json:
        supplied = json.loads(args.history_json.read_text())
        result['supplied_history'] = verify_history(**supplied)
        result['history_sha256'] = hashlib.sha256(args.history_json.read_bytes()).hexdigest()
    encoded = json.dumps(result, indent=2)+'\n'
    if args.out:
        args.out.write_text(encoded)
    print(encoded)
