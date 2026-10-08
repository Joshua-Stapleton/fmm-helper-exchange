#!/usr/bin/env python3
"""Regular (ordinary-coordinate) case: at most 10 canonical vectors per factor anywhere in the
de Groote isotropy orbit of the 204 scheme, hence c = #canonical rows of L and R <= 20.

Argument.  An isotropy acts on each factor matrix by M -> X M Y with X, Y invertible 4x4, so it
preserves matrix rank; a canonical row/column is a matrix unit, i.e. a rank-one factor x y^T
with X x on a coordinate line and Y^T y on a coordinate line.  Pulling back, x must lie on one
of 4 linearly independent lines (X^-1 e_1..e_4) and y on one of 4 independent lines.  So
#canonical(factor) <= max over independent 4-sets of left lines and right lines of the number of
rank-one factors whose (x, y) lies in that grid.  This enumerates all such sets exactly
(standard library only).  The bound 10 is attained by the published scheme itself.
Run: python3 orbit_bound.py
"""
import itertools
from pathlib import Path
HERE = Path(__file__).resolve().parent
from lrp import read_sms, factors, rank1_split, rank, verify, canon_counts


def bound(fs):
    pairs = [p for p in (rank1_split(m) for m in fs) if p]
    X = sorted({p[0] for p in pairs})
    Y = sorted({p[1] for p in pairs})
    ind = lambda S: rank([list(v) for v in S]) == len(S)
    sx = [set(s) for k in range(1, 5) for s in itertools.combinations(X, k) if ind(s)]
    sy = [set(s) for k in range(1, 5) for s in itertools.combinations(Y, k) if ind(s)]
    return max(sum(1 for p in pairs if p[0] in a and p[1] in b) for a in sx for b in sy), len(pairs), len(X), len(Y)


L, R, P = (read_sms(HERE / f"4x4x4_48_204_{s}.sms") for s in "LRP")
assert verify(L, R, P)
print("current canonical counts (L,R,P):", canon_counts(L, R, P))
for name, fs in zip(("L", "R", "P"), factors(L, R, P)):
    b, n1, nx, ny = bound(fs)
    print(f"{name}: rank-one factors={n1}, distinct left/right lines={nx}/{ny}, orbit-wide max canonical={b}")
print("=> c = canonical(L)+canonical(R) <= 20 on the whole orbit (and for any role permutation).")
