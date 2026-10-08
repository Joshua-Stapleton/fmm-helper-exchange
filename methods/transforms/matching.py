"""Exact cardinality-constrained disjoint-shear sparsity optimization.

This is the reusable DP from the October 7 matching experiment. Its guarantee
concerns nonzero count in this family, not addition-minimal SLPs.
"""
from fractions import Fraction as Q
from functools import lru_cache
from ternary_shears import identity, product


def optimal_disjoint_shears(matrix, pairs, ternary_only=False):
    """Maximize nnz reduction for B = I + sum s*E_uv on disjoint pairs.

    The transformed matrix is M*B^-1, so edge (u,v,s) changes column v to
    column v - s*column u. Both orientations and signs are tested. Every
    unchanged column must be ternary when ternary_only=True. Returns None
    exactly when this finite matching family is infeasible.
    """
    if not matrix or not matrix[0] or any(len(r) != len(matrix[0]) for r in matrix):
        raise ValueError("nonempty rectangular matrix required")
    m = [[Q(x) for x in row] for row in matrix]
    n = len(m[0])
    if type(pairs) is not int or not 0 <= pairs <= n//2:
        raise ValueError("invalid matching cardinality")
    clean = [all(r[j] in (-1, 0, 1) for r in m) for j in range(n)]
    options = {}
    for i in range(n):
        for j in range(i+1, n):
            opts = []
            for u, v in ((i, j), (j, i)):
                for s in (-1, 1):
                    col = [r[v]-s*r[u] for r in m]
                    if ternary_only and (not clean[u] or any(x not in (-1, 0, 1) for x in col)):
                        continue
                    saving = sum(bool(r[v]) for r in m)-sum(bool(x) for x in col)
                    opts.append((saving, u, v, s))
            if opts:
                options[i, j] = max(opts)

    @lru_cache(None)
    def dp(mask, k):
        if not k:
            return (0, ()) if not ternary_only or all(clean[j] for j in range(n) if mask >> j & 1) else None
        if mask.bit_count() < 2*k:
            return None
        i = (mask & -mask).bit_length()-1
        rest = mask ^ (1 << i)
        choices = []
        if not ternary_only or clean[i]:
            skipped = dp(rest, k)
            if skipped is not None:
                choices.append(skipped)
        for j in range(i+1, n):
            if rest >> j & 1 and (i, j) in options:
                tail = dp(rest ^ (1 << j), k-1)
                if tail is not None:
                    saving, u, v, s = options[i, j]
                    choices.append((saving+tail[0], ((u, v, s),)+tail[1]))
        return max(choices) if choices else None

    result = dp((1 << n)-1, pairs)
    if result is None:
        return None
    saving, edges = result
    basis, inverse = identity(n), identity(n)
    for u, v, s in edges:
        basis[u][v] = s
        inverse[u][v] = -s
    transformed = product(m, inverse)
    before, after = [sum(bool(x) for row in mm for x in row) for mm in (m, transformed)]
    if product(basis, inverse) != identity(n) or before-after != saving:
        raise ValueError("exact matching replay failed")
    if ternary_only and any(x not in (-1, 0, 1) for row in transformed for x in row):
        raise ValueError("ternarization replay failed")
    return {"edges": edges, "basis": basis, "inverse": inverse,
            "matrix": transformed, "saving": saving, "nnz_before": before,
            "nnz_after": after, "states": dp.cache_info().currsize}
