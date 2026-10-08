#!/usr/bin/env python3
"""Verify six SLP maps as one exact rational matrix-multiplication program.

Standard library only; no repository imports, optimizer, or trusted coefficient
matrix. All A, B, and C entries use row-major order. Copies, signs, and zero are
free. Each addition/subtraction of linear forms costs one; a multiplication or
division by a constant outside {0,1,-1} costs one nonunit scalar instruction.
Numerical constant expressions are evaluated exactly before applying a scale.
Default operation is read-only. Exit status is nonzero on any failed check.
"""
import argparse
import ast
import copy
import hashlib
import json
import re
import sys
from fractions import Fraction
from pathlib import Path


class Invalid(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def replay(lines, inputs, outputs, role):
    require(isinstance(lines, list) and all(isinstance(x, str) for x in lines), role + ': expected SLP-line list')
    env = {'i' + str(i): ('vector', tuple(Fraction(i == j) for j in range(inputs))) for i in range(inputs)}
    additions = scalars = 0

    def expr(node):
        nonlocal additions, scalars
        if isinstance(node, ast.Name):
            require(node.id in env, role + ': undefined wire ' + node.id)
            return env[node.id]
        if isinstance(node, ast.Constant):
            require(type(node.value) is int, role + ': only exact integer literals are allowed')
            return 'scalar', Fraction(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            kind, value = expr(node.operand)
            sign = -1 if isinstance(node.op, ast.USub) else 1
            return kind, tuple(sign*x for x in value) if kind == 'vector' else sign*value
        require(isinstance(node, ast.BinOp), role + ': unsupported expression')
        ka, a = expr(node.left)
        kb, b = expr(node.right)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            sign = -1 if isinstance(node.op, ast.Sub) else 1
            if ka == kb == 'scalar':
                return 'scalar', a + sign*b
            if ka == 'scalar' and a == 0:
                ka, a = 'vector', (Fraction(0),)*inputs
            if kb == 'scalar' and b == 0:
                kb, b = 'vector', (Fraction(0),)*inputs
            require(ka == kb == 'vector', role + ': nonzero affine constant')
            additions += 1
            return 'vector', tuple(x + sign*y for x, y in zip(a, b))
        if isinstance(node.op, ast.Mult):
            require(not (ka == kb == 'vector'), role + ': nonlinear product')
            if ka == kb == 'scalar':
                return 'scalar', a*b
            vector, scale = (a, b) if ka == 'vector' else (b, a)
            scalars += scale not in (-1, 0, 1)
            return 'vector', tuple(scale*x for x in vector)
        if isinstance(node.op, ast.Div):
            require(kb == 'scalar' and b != 0, role + ': nonlinear division or division by zero')
            if ka == 'scalar':
                return 'scalar', a/b
            scale = 1/b
            scalars += scale not in (-1, 0, 1)
            return 'vector', tuple(scale*x for x in a)
        raise Invalid(role + ': unsupported arithmetic operator')

    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue
        require(line.endswith(';') and line.count(':=') == 1, role + ': malformed line ' + str(number))
        name, rhs = (s.strip() for s in line[:-1].split(':=', 1))
        require(re.fullmatch(r'(?:t|o)\d+', name) is not None, role + ': destination must be tN or oN; inputs cannot be overwritten')
        if name.startswith('o'):
            require(int(name[1:]) < outputs, role + ': output index exceeds role dimensions')
        try:
            value = expr(ast.parse(rhs, mode='eval').body)
        except (SyntaxError, RecursionError) as error:
            raise Invalid(role + ': invalid expression on line ' + str(number)) from error
        if value[0] == 'scalar':
            require(value[1] == 0, role + ': nonzero affine wire')
            value = 'vector', (Fraction(0),)*inputs
        env[name] = value
    rows = []
    for index in range(outputs):
        name = 'o' + str(index)
        require(name in env and env[name][0] == 'vector', role + ': missing output ' + name)
        rows.append(list(env[name][1]))
    return rows, {'additions': additions, 'nonunit_scalars': scalars}


def multiply(a, b):
    require(a and b and len(a[0]) == len(b), 'composition dimension mismatch')
    return [[sum(x*y for x, y in zip(row, column)) for column in zip(*b)] for row in a]


def nonsingular(matrix):
    n = len(matrix)
    require(n > 0 and all(len(row) == n for row in matrix), 'boundary must be square')
    a = copy.deepcopy(matrix)
    determinant = Fraction(1)
    for column in range(n):
        pivot = next((r for r in range(column, n) if a[r][column]), None)
        require(pivot is not None, 'singular boundary map')
        if pivot != column:
            determinant = -determinant
        a[column], a[pivot] = a[pivot], a[column]
        scale = a[column][column]
        determinant *= scale
        a[column] = [x/scale for x in a[column]]
        for row in range(column + 1, n):
            scale = a[row][column]
            a[row] = [x - scale*y for x, y in zip(a[row], a[column])]
    return determinant


def verify(certificate):
    require(isinstance(certificate, dict), 'certificate must be an object')
    require(certificate.get('format') == 'fmm-basis-kernel-v1', 'unsupported format')
    require(certificate.get('field') == 'Q', 'only exact rational arithmetic Q is supported')
    require(certificate.get('coordinate_layout') == {k: 'row-major' for k in ('A', 'B', 'C')}, 'A/B/C layout must be explicitly row-major')
    dims = certificate.get('dimensions')
    require(isinstance(dims, list) and len(dims) == 3 and all(type(x) is int and x > 0 for x in dims), 'three positive integer dimensions required')
    r = certificate.get('rank')
    require(type(r) is int and r > 0, 'positive integer rank required')
    n, m, k = dims
    roles = {'A_boundary': (n*m, n*m), 'B_boundary': (m*k, m*k), 'U': (n*m, r),
             'V': (m*k, r), 'W': (r, n*k), 'C_boundary': (n*k, n*k)}
    programs = certificate.get('maps')
    require(isinstance(programs, dict) and set(programs) == set(roles), 'exactly the six named role maps are required')
    matrices, costs = {}, {}
    for role, (inputs, outputs) in roles.items():
        matrices[role], costs[role] = replay(programs[role], inputs, outputs, role)
    determinants = {role: nonsingular(matrices[role]) for role in ('A_boundary', 'B_boundary', 'C_boundary')}
    if certificate.get('boundary_unimodular', False):
        require(all(x.denominator == 1 for role in determinants for row in matrices[role] for x in row), 'declared unimodular boundary has a noninteger coefficient')
        require(all(value in (-1, 1) for value in determinants.values()), 'declared unimodular boundary determinant is not +1 or -1')
    u = multiply(matrices['U'], matrices['A_boundary'])
    v = multiply(matrices['V'], matrices['B_boundary'])
    w = multiply(matrices['C_boundary'], matrices['W'])
    require(all(any(row) for row in u), 'inactive product: zero U row')
    require(all(any(row) for row in v), 'inactive product: zero V row')
    require(all(any(w[i][t] for i in range(n*k)) for t in range(r)), 'inactive product: zero reconstructed W column')
    identities = 0
    for ai in range(n*m):
        i, j = divmod(ai, m)
        for bi in range(m*k):
            jj, ell = divmod(bi, k)
            for ci in range(n*k):
                ii, ll = divmod(ci, k)
                actual = sum(u[t][ai]*v[t][bi]*w[ci][t] for t in range(r))
                expected = int(i == ii and j == jj and ell == ll)
                require(actual == expected, 'tensor identity failed at A['+str(ai)+'], B['+str(bi)+'], C['+str(ci)+']: '+str(actual)+' != '+str(expected))
                identities += 1
    kernel = sum(costs[role]['additions'] for role in ('U', 'V', 'W'))
    boundary = sum(costs[role]['additions'] for role in ('A_boundary', 'B_boundary', 'C_boundary'))
    actual = {'kernel': kernel, 'boundary': boundary, 'full': kernel + boundary,
              'nonunit_scalars': sum(value['nonunit_scalars'] for value in costs.values())}
    declared = certificate.get('expected')
    require(isinstance(declared, dict) and set(actual) <= set(declared) <= set(actual) | {'per_map'}, 'expected requires kernel, boundary, full, nonunit_scalars; optional per_map')
    require(all(type(declared[k]) is int and declared[k] >= 0 for k in actual), 'expected costs must be nonnegative integers')
    require({k: declared[k] for k in actual} == actual, 'operation counts disagree: expected '+str(declared)+', actual '+str(actual))
    if 'per_map' in declared:
        per_map = declared['per_map']
        require(isinstance(per_map, dict) and set(per_map) == set(roles) and all(type(v) is int and v >= 0 for v in per_map.values()), 'per_map must give the six ADD counts')
        require(per_map == {role: value['additions'] for role, value in costs.items()}, 'per-map ADD counts disagree')
    return {'status': 'PASS', 'dimensions': dims, 'rank': r, **actual, 'tensor_identities': identities, 'map_costs': costs,
            'boundary_determinants': {role: int(value) if value.denominator == 1 else str(value) for role, value in determinants.items()}}


def classical(dims):
    """Synthetic positive controls; these are not research results."""
    n, m, k = dims
    terms = [(i, j, ell) for i in range(n) for j in range(m) for ell in range(k)]
    copies = lambda count: ['o'+str(i)+':=i'+str(i)+';' for i in range(count)]
    maps = {'A_boundary': copies(n*m), 'B_boundary': copies(m*k), 'C_boundary': copies(n*k),
            'U': ['o'+str(t)+':=i'+str(i*m+j)+';' for t, (i,j,ell) in enumerate(terms)],
            'V': ['o'+str(t)+':=i'+str(j*k+ell)+';' for t, (i,j,ell) in enumerate(terms)],
            'W': ['o'+str(i*k+ell)+':='+'+'.join('i'+str(t) for t, (ii,j,ll) in enumerate(terms) if ii == i and ll == ell)+';' for i in range(n) for ell in range(k)]}
    return {'format': 'fmm-basis-kernel-v1', 'dimensions': dims, 'rank': len(terms), 'field': 'Q',
            'coordinate_layout': {s: 'row-major' for s in ('A','B','C')}, 'maps': maps,
            'expected': {'kernel': n*k*(m-1), 'boundary': 0, 'full': n*k*(m-1), 'nonunit_scalars': 0}}


def self_test():
    passed = []
    def rejects(c, label):
        try:
            verify(c)
        except (Invalid, ValueError, KeyError, IndexError):
            passed.append(label)
            return
        raise Invalid('self-test accepted bad certificate: '+label)
    for dims in ([2,3,3], [3,2,3], [2,2,2]):
        good = classical(list(dims)); verify(good)
        bad = copy.deepcopy(good); bad['maps']['V'] = copy.deepcopy(good['maps']['U'])
        rejects(bad, 'U-for-V-'+''.join(map(str,dims)))
        if dims[1] == dims[2]:
            u, _ = replay(good['maps']['U'], dims[0]*dims[1], good['rank'], 'control-U')
            wrong = ['o'+str(i)+':='+'+'.join('i'+str(t) for t in range(good['rank']) if u[t][i])+';' for i in range(len(u[0]))]
            bad = copy.deepcopy(good); bad['maps']['W'] = wrong
            rejects(bad, 'same-width-U-transpose-for-W-'+''.join(map(str,dims)))
            bad['maps']['V'] = copy.deepcopy(good['maps']['U'])
            rejects(bad, 'combined-U-U-U-transpose-'+''.join(map(str,dims)))
    good = classical([1,1,1])
    bad = copy.deepcopy(good); bad['expected']['full'] += 1; rejects(bad, 'wrong-declared-count')
    bad = copy.deepcopy(good); bad['maps']['U'] = ['o0:=2*i0;']; bad['expected']['nonunit_scalars'] = 1; rejects(bad, 'wrong-coefficient-with-honest-scalar-count')
    bad = copy.deepcopy(good); bad['maps']['A_boundary'] = ['o0:=0;']; rejects(bad, 'singular-boundary')
    bad = copy.deepcopy(good); bad['maps']['U'] = ['o0:=i0*i0;']; rejects(bad, 'nonlinear-expression')
    bad = copy.deepcopy(good); bad['maps']['U'] = ['i0:=i0;','o0:=i0;']; rejects(bad, 'input-overwrite')
    bad = copy.deepcopy(good); bad['field'] = 'F2'; rejects(bad, 'wrong-field')
    bad = copy.deepcopy(good); bad['coordinate_layout']['C'] = 'column-major'; rejects(bad, 'wrong-output-layout')
    scaled = copy.deepcopy(good)
    scaled['maps']['A_boundary'] = ['o0:=2*i0;']; scaled['maps']['U'] = ['o0:=i0/2;']; scaled['expected']['nonunit_scalars'] = 2
    verify(scaled); passed.append('exact-division-and-two-scalars-positive')
    free_sign = copy.deepcopy(good); free_sign['maps']['U'] = ['o0:=-i0;']; free_sign['maps']['W'] = ['o0:=i0/(-1);']
    verify(free_sign); passed.append('free-sign-and-unit-division-positive')
    return {'status': 'PASS', 'self_tests': passed}


def actual_role_tests(certificate):
    """Wrong roles are tested on the supplied exact maps, including equal widths."""
    n, m, k = certificate['dimensions']; r = certificate['rank']
    require(n == m == k, 'actual U/U/U-transpose control requires equal factor widths')
    u, _ = replay(certificate['maps']['U'], n*m, r, 'actual-control-U')
    wrong_w = []
    for column in range(n*m):
        terms = []
        for row in range(r):
            coefficient = u[row][column]
            if coefficient:
                terms.append('('+str(coefficient)+')*i'+str(row))
        wrong_w.append('o'+str(column)+':='+('+'.join(terms) if terms else '0')+';')
    passed = []
    for label, replace_v, replace_w in [('actual-U-for-V', True, False), ('actual-U-transpose-for-W', False, True), ('actual-U-U-U-transpose', True, True)]:
        bad = copy.deepcopy(certificate)
        if replace_v:
            bad['maps']['V'] = copy.deepcopy(certificate['maps']['U'])
        if replace_w:
            bad['maps']['W'] = wrong_w
        try:
            verify(bad)
        except Invalid as error:
            # Reject on the arithmetic identity, rather than merely on changed gate counts.
            require('tensor identity failed' in str(error), 'actual role control failed for an unrelated reason: '+str(error))
            passed.append({'case': label, 'rejected_by': str(error)})
        else:
            raise Invalid('actual wrong-role certificate was accepted: '+label)
    return {'status': 'PASS', 'actual_role_controls': passed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', type=Path, nargs='*', help='certificate JSON files; default sibling 333.json')
    parser.add_argument('--self-test', action='store_true', help='also run synthetic positive and mutation controls')
    args = parser.parse_args()
    paths = args.files or [Path(__file__).resolve().parent/'333.json']
    try:
        if args.self_test:
            print(json.dumps(self_test(), separators=(',', ':')))
        for path in paths:
            raw = path.read_bytes()
            certificate = json.loads(raw)
            result = verify(certificate)
            print(json.dumps({'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest(), **result}, separators=(',', ':')))
            if args.self_test:
                print(json.dumps(actual_role_tests(certificate), separators=(',', ':')))
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError) as error:
        print('FAIL: '+str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
