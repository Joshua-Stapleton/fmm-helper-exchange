#!/usr/bin/env python3
"""Independent exact linear-map verifier, Python standard library only.

No search/reduction code is imported. SMS entries and literal assignments are
evaluated as Fraction coefficient vectors. All source output signs are fixed.
"""
import argparse
import ast
from collections import Counter
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path


def read_sms(path):
    raw = Path(path).read_bytes()
    rows = [r.split() for r in raw.decode().splitlines()
            if r.strip() and not r.lstrip().startswith('#')]
    n, m = map(int, rows.pop(0)[:2])
    matrix = [[Q(0) for _ in range(m)] for _ in range(n)]
    seen = set()
    for r in rows:
        i, j = map(int, r[:2]); x = Q(r[2])
        if (i, j, x) == (0, 0, 0):
            continue
        assert 1 <= i <= n and 1 <= j <= m
        assert (i, j) not in seen, 'Duplicate SMS entry'
        seen.add((i, j)); matrix[i - 1][j - 1] = x
    return matrix, hashlib.sha256(raw).hexdigest()


def source_stats(matrix, sha):
    canonical = []
    for row in matrix:
        first = next((x for x in row if x), Q(0))
        canonical.append(tuple(x if first >= 0 else -x for x in row))
    signs = Counter(canonical)
    return {'source_sha256': sha, 'outputs': len(matrix),
            'inputs': len(matrix[0]),
            'nonzero_entries': sum(x != 0 for row in matrix for x in row),
            'naive_row_additions': sum(max(0, sum(x != 0 for x in row)-1) for row in matrix),
            'signed_distinct_rows': len(signs),
            'signed_duplicate_groups': [idx for row, count in signs.items() if count > 1
                                       for idx in [[j for j, x in enumerate(canonical) if x == row]]],
            'row_support_histogram': dict(sorted(Counter(sum(x != 0 for x in row) for row in matrix).items()))}


def replay(text, width):
    env = {f'i{i}': [Q(i == j) for j in range(width)] for i in range(width)}
    counts = Counter(binary_additions=0, unary_negations=0, nonunit_scalars=0)
    dependencies = {}
    current_deps = set()
    def expr(node):
        if isinstance(node, ast.Name):
            assert node.id in env, f'Undefined name {node.id}'
            current_deps.add(node.id)
            return env[node.id]
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            assert node.value == 0, 'Only scalar zero is a vector literal'
            return [Q(0)] * width
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = expr(node.operand)
            if isinstance(node.op, ast.USub):
                counts['unary_negations'] += 1
                return [-x for x in value]
            return value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            a, b = expr(node.left), expr(node.right)
            counts['binary_additions'] += 1
            sign = 1 if isinstance(node.op, ast.Add) else -1
            return [x + sign*y for x, y in zip(a, b)]
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Div)):
            def scalar(n):
                if isinstance(n, ast.Constant) and isinstance(n.value, int):
                    return Q(n.value)
                if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
                    return -scalar(n.operand)
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                    return scalar(n.left) / scalar(n.right)
                raise ValueError('Not a rational scalar')
            if isinstance(node.op, ast.Div):
                factor = 1/scalar(node.right); value = expr(node.left)
            else:
                try:
                    factor = scalar(node.left); value = expr(node.right)
                except ValueError:
                    factor = scalar(node.right); value = expr(node.left)
            if factor == -1:
                counts['unary_negations'] += 1
            elif factor not in (0, 1):
                counts['nonunit_scalars'] += 1
            return [factor*x for x in value]
        raise ValueError('Unsupported expression: ' + ast.dump(node))
    for rawline in text.splitlines():
        rawline = rawline.split('#')[0].strip()
        if not rawline:
            continue
        for line in rawline.split(';'):
            if not line.strip():
                continue
            statement = ast.parse(line.strip().replace(':=', '='), mode='exec')
            assert len(statement.body) == 1
            node = statement.body[0]
            assert isinstance(node, ast.Assign) and len(node.targets) == 1
            assert isinstance(node.targets[0], ast.Name)
            name = node.targets[0].id
            assert name not in env, f'Reassigned name {name}'
            current_deps.clear(); value = expr(node.value)
            env[name] = value; dependencies[name] = set(current_deps)
    outputs = [key for key in env if key.startswith('o') and key[1:].isdigit()]
    assert set(outputs) == {f'o{i}' for i in range(len(outputs))}, 'Nonconsecutive outputs'
    used = set(outputs)
    todo = list(outputs)
    while todo:
        for name in dependencies.get(todo.pop(), ()):
            if name not in used:
                used.add(name); todo.append(name)
    counts['unused_noninput_assignments'] = len(set(dependencies) - used)
    return [env[f'o{i}'] for i in range(len(outputs))], dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path)
    parser.add_argument('slp', type=Path, nargs='?')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    matrix, sha = read_sms(args.matrix)
    report = source_stats(matrix, sha)
    if args.slp:
        actual, counts = replay(args.slp.read_text(), len(matrix[0]))
        assert actual == matrix, 'Literal SLP differs from fixed signed source matrix'
        report.update(status='PASS', exact_coefficient_identities=len(matrix)*len(matrix[0]),
                      counts=counts, literal_sha256=hashlib.sha256(args.slp.read_bytes()).hexdigest(),
                      basis_change=False, scope='Only the supplied V linear map; not the full bilinear scheme.')
    else:
        report['status'] = 'SOURCE_AUDIT_PASS'
    text = json.dumps(report, indent=2) + '\n'
    if args.out:
        args.out.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
