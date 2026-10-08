"""Exact LRP utilities for <4x4x4:48> schemes (PLinOpt .sms convention).

L: r x 16 (rows = linear forms on vec(A)), R: r x 16, P: 16 x r.
vec is row-major: index 4*i+j <-> A[i][j].
"""
from fractions import Fraction as F
from itertools import product
import sys

N = 4


def read_sms(path):
    with open(path) as fh:
        toks = fh.read().split()
    rows, cols = int(toks[0]), int(toks[1])
    M = [[F(0)] * cols for _ in range(rows)]
    k = 3
    while k + 2 < len(toks):
        i, j, v = int(toks[k]), int(toks[k + 1]), toks[k + 2]
        k += 3
        if i == 0 and j == 0:
            break
        M[i - 1][j - 1] = F(v)
    return M


def write_sms(path, M):
    rows, cols = len(M), len(M[0])
    with open(path, "w") as fh:
        fh.write(f"{rows} {cols} R\n")
        for i in range(rows):
            for j in range(cols):
                if M[i][j] != 0:
                    fh.write(f"{i+1} {j+1} {M[i][j]}\n")
        fh.write("0 0 0\n")


def transpose(M):
    return [list(r) for r in zip(*M)]


def to_mat(vec):
    return [[vec[N * i + j] for j in range(N)] for i in range(N)]


def to_vec(M):
    return [M[i][j] for i in range(N) for j in range(N)]


def matmul(A, B):
    n, m, k = len(A), len(B), len(B[0])
    return [[sum((A[i][t] * B[t][j] for t in range(m)), F(0)) for j in range(k)] for i in range(n)]


def factors(L, R, P):
    """Return lists alpha, beta, gamma of 4x4 matrices (gamma = output coefficient matrix)."""
    r = len(L)
    Pt = transpose(P)
    return ([to_mat(L[i]) for i in range(r)],
            [to_mat(R[i]) for i in range(r)],
            [to_mat(Pt[i]) for i in range(r)])


def verify(L, R, P):
    """Exact Brent equations: C = AB with C[i][k] = sum_j A[i][j] B[j][k]."""
    r = len(L)
    for ci in range(N):
        for ck in range(N):
            out = 4 * ci + ck
            for a in range(16):
                for b in range(16):
                    s = sum((P[out][t] * L[t][a] * R[t][b] for t in range(r)), F(0))
                    ai, aj = divmod(a, 4)
                    bj, bk = divmod(b, 4)
                    want = 1 if (ai == ci and aj == bj and bk == ck) else 0
                    if s != want:
                        return False
    return True


def rank(M):
    M = [list(r) for r in M]
    rows, cols = len(M), len(M[0])
    rk = 0
    for c in range(cols):
        piv = next((i for i in range(rk, rows) if M[i][c] != 0), None)
        if piv is None:
            continue
        M[rk], M[piv] = M[piv], M[rk]
        for i in range(rows):
            if i != rk and M[i][c] != 0:
                f = M[i][c] / M[rk][c]
                M[i] = [M[i][t] - f * M[rk][t] for t in range(cols)]
        rk += 1
    return rk


def normline(v):
    """Canonical representative of the line through v (first nonzero = 1)."""
    v = [F(x) for x in v]
    p = next(x for x in v if x != 0)
    return tuple(x / p for x in v)


def rank1_split(M):
    """If M = x y^T return (line(x), line(y)); else None."""
    if rank(M) != 1:
        return None
    col = next(j for j in range(N) if any(M[i][j] != 0 for i in range(N)))
    row = next(i for i in range(N) if M[i][col] != 0)
    x = [M[i][col] for i in range(N)]
    y = M[row]
    return normline(x), normline(y)


def is_canonical(vec):
    return sum(1 for v in vec if v != 0) == 1


def canon_counts(L, R, P):
    Pt = transpose(P)
    return (sum(is_canonical(r) for r in L), sum(is_canonical(r) for r in R),
            sum(is_canonical(c) for c in Pt))


def nnz(M):
    return sum(1 for r in M for v in r if v != 0)


def nonunit(M):
    return sum(1 for r in M for v in r if v != 0 and abs(v) != 1)


def inv(M):
    n = len(M)
    A = [list(M[i]) + [F(int(i == j)) for j in range(n)] for i in range(n)]
    for c in range(n):
        piv = next(i for i in range(c, n) if A[i][c] != 0)
        A[c], A[piv] = A[piv], A[c]
        pv = A[c][c]
        A[c] = [x / pv for x in A[c]]
        for i in range(n):
            if i != c and A[i][c] != 0:
                f = A[i][c]
                A[i] = [A[i][t] - f * A[c][t] for t in range(2 * n)]
    return [row[n:] for row in A]


def T(M):
    return [list(r) for r in zip(*M)]


def isotropy(L, R, P, U, V, W):
    """alpha -> U^-T alpha V^T, beta -> V^-T beta W^T, gamma -> U gamma W^-1.

    Keeps C = AB for A' = U A V^-1, B' = V B W^-1, C' = U C W^-1.
    """
    Ui, Vi, Wi = inv(U), inv(V), inv(W)
    UiT, ViT = T(Ui), T(Vi)
    VT, WT = T(V), T(W)
    al, be, ga = factors(L, R, P)
    L2 = [to_vec(matmul(matmul(UiT, a), VT)) for a in al]
    R2 = [to_vec(matmul(matmul(ViT, b), WT)) for b in be]
    G2 = [to_vec(matmul(matmul(U, g), Wi)) for g in ga]
    return L2, R2, transpose(G2)


if __name__ == "__main__":
    pre = sys.argv[1]
    L, R, P = (read_sms(f"{pre}_{s}.sms") for s in "LRP")
    print("rank", len(L), "verify", verify(L, R, P))
    print("canonical L,R,P:", canon_counts(L, R, P))
    print("nnz L,R,P:", nnz(L), nnz(R), nnz(P), " nonunit:", nonunit(L), nonunit(R), nonunit(P))
    al, be, ga = factors(L, R, P)
    for name, fs in (("alpha", al), ("beta", be), ("gamma", ga)):
        rk = [rank(m) for m in fs]
        print(name, "rank histogram", {k: rk.count(k) for k in sorted(set(rk))})
