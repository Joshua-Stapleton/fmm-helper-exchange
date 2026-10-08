"""Portable exact transformation helpers extracted from the research methods.

All matrices use rows as linear forms. These functions generate candidates;
optimized arithmetic counts and boundary costs must be verified separately.
"""
from fractions import Fraction as Q
from itertools import permutations
from copy import deepcopy
from ternary_shears import identity, product, shear, ternary


def canonical_columns(matrix, sort_columns=True):
    """Return C[:,j] = signs[j] * M[:,permutation[j]].

    Canonicalize each column's first nonzero coefficient to positive, then
    optionally sort columns. Zero columns have sign +1. This is a quotient by
    signed coordinate permutations, not general proportionality. Free signs
    are a search convention, not a strict literal circuit certificate.
    """
    if not matrix or not matrix[0] or any(len(r) != len(matrix[0]) for r in matrix):
        raise ValueError("nonempty rectangular matrix required")
    columns = []
    for j, raw in enumerate(zip(*matrix)):
        col = tuple(Q(x) for x in raw)
        first = next((x for x in col if x), Q(1))
        sign = 1 if first > 0 else -1
        columns.append((tuple(sign*x for x in col), j, sign))
    if sort_columns:
        columns.sort(key=lambda x: (x[0], x[1]))
    return {"matrix": [list(r) for r in zip(*(c[0] for c in columns))],
            "permutation": [c[1] for c in columns],
            "signs": [c[2] for c in columns]}


def two_shear_endpoints(matrix, first, second):
    """Test BOTH specified orders, including nonternary intermediate states.

    Each move is {'destination': j, 'donors': [(i, sign), ...]}. The returned
    endpoint is retained only if ternary. A retained endpoint need not admit
    a ternary intermediate in that ordering. Noncommuting orders are distinct.
    """
    if not ternary(matrix):
        raise ValueError("source must be ternary")
    n = len(matrix[0])
    out = []
    for order in ((first, second), (second, first)):
        a, b = [shear(n, m['destination'], m['donors']) for m in order]
        mid = product(matrix, a)
        end = product(mid, b)
        if ternary(end):
            inv_b, inv_a = [shear(n, m['destination'], m['donors'], -1)
                            for m in reversed(order)]
            basis, inverse = product(a, b), product(inv_b, inv_a)
            if product(basis, inverse) != identity(n):
                raise ValueError("inverse replay failed")
            out.append({"moves": list(order), "matrix": end,
                        "intermediate_ternary": ternary(mid),
                        "right_basis": basis, "inverse": inverse})
    return out


def sandwich_shear(source, axis, i, j, sign):
    """An elementary paired matrix-index isotropy, preserving ordinary MM.

    source = {'shape':[n,m,k], 'u':rows, 'v':rows, 'w':rows}; W uses flattened
    k-by-n trace orientation. Unlike independent flattened bases, this paired
    action does not require external conversions. Returns exact endpoint and
    right-acting factor maps, whether or not that endpoint remains ternary.
    """
    dims = source['shape']
    if len(dims) != 3 or axis not in (0, 1, 2):
        raise ValueError("bad shape or axis")
    if i == j or not (0 <= i < dims[axis] and 0 <= j < dims[axis]) or sign not in (-1, 1):
        raise ValueError("bad signed shear")
    target, maps = deepcopy(source), {}
    for a, side in enumerate('uvw'):
        width = dims[a]*dims[(a+1) % 3]
        if any(len(r) != width for r in source[side]):
            raise ValueError("bad factor dimensions")
        linear = identity(width)
        if a == axis:
            cols = dims[(axis+1) % 3]
            for col in range(cols):
                linear[i*cols+col][j*cols+col] += sign
        elif a == (axis+2) % 3:
            cols = dims[axis]
            for start in range(0, width, cols):
                linear[start+j][start+i] -= sign
        else:
            continue
        target[side] = product(source[side], linear)
        maps[side] = linear
    return target, maps


def transfer_matrix(matrix, equivalence):
    """Replay a symmetry certificate from symmetry.find exactly."""
    if equivalence['status'] != 'EQUIVALENT':
        raise ValueError("verified equivalence required")
    rp, rs, cp, cs = [equivalence[k] for k in
                     ('row_permutation', 'row_signs', 'column_permutation', 'column_signs')]
    return [[Q(rs[i])*Q(cs[j])*Q(matrix[rp[i]][cp[j]])
             for j in range(len(cp))] for i in range(len(rp))]
