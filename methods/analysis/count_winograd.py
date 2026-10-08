"""Independent exact counted Winograd and odd-border construction.

No search/research implementation imports. Classical leaves <=10.
"""
import json
import random
import time
from pathlib import Path

COUNTS = {"multiplications": 0, "additions": 0}
LEAF_CUTOFF = 10


def plus(x, y):
    COUNTS["additions"] += 1
    return x + y


def minus(x, y):
    COUNTS["additions"] += 1
    return x - y


def times(x, y):
    COUNTS["multiplications"] += 1
    return x * y


def dot(a, b):
    ans = times(a[0], b[0])
    for x, y in zip(a[1:], b[1:]):
        ans = plus(ans, times(x, y))
    return ans


def classical(a, b):
    bt = list(zip(*b))
    return [[dot(row, col) for col in bt] for row in a]


def add(a, b):
    return [[plus(x, y) for x, y in zip(ar, br)] for ar, br in zip(a, b)]


def sub(a, b):
    return [[minus(x, y) for x, y in zip(ar, br)] for ar, br in zip(a, b)]


def split(a):
    h = len(a) // 2
    return [r[:h] for r in a[:h]], [r[h:] for r in a[:h]], [r[:h] for r in a[h:]], [r[h:] for r in a[h:]]


def winograd(a, b):
    n = len(a)
    if n <= LEAF_CUTOFF:
        return classical(a, b)
    if n % 2:
        q = n - 1
        core = winograd([r[:q] for r in a[:q]], [r[:q] for r in b[:q]])
        c = [[0] * n for _ in range(n)]
        for i in range(q):
            for j in range(q):
                c[i][j] = plus(core[i][j], times(a[i][q], b[q][j]))
            c[i][q] = plus(dot(a[i][:q], [b[k][q] for k in range(q)]), times(a[i][q], b[q][q]))
        for j in range(q):
            c[q][j] = plus(dot(a[q][:q], [b[k][j] for k in range(q)]), times(a[q][q], b[q][j]))
        c[q][q] = plus(dot(a[q][:q], [b[k][q] for k in range(q)]), times(a[q][q], b[q][q]))
        return c
    a11, a12, a21, a22 = split(a)
    b11, b12, b21, b22 = split(b)
    s1 = add(a21, a22)
    s2 = sub(s1, a11)
    s3 = sub(a11, a21)
    s4 = sub(a12, s2)
    t1 = sub(b12, b11)
    t2 = sub(b22, t1)
    t3 = sub(b22, b12)
    t4 = sub(t2, b21)
    p1 = winograd(a11, b11)
    p2 = winograd(a12, b21)
    p3 = winograd(s4, b22)
    p4 = winograd(a22, t4)
    p5 = winograd(s1, t1)
    p6 = winograd(s2, t2)
    p7 = winograd(s3, t3)
    c11 = add(p1, p2)
    u2 = add(p1, p6)
    u3 = add(u2, p7)
    u4 = add(u2, p5)
    c12 = add(u4, p3)
    c21 = sub(u3, p4)
    c22 = add(u3, p5)
    return [x + y for x, y in zip(c11, c12)] + [x + y for x, y in zip(c21, c22)]


def predicted(n):
    if n <= LEAF_CUTOFF:
        return n**3, n**3 - n*n
    if n % 2:
        q = n-1
        m,a = predicted(q)
        return m + 3*q*q + 3*q + 1, a + 3*q*q + q
    m,a = predicted(n//2)
    return 7*m, 7*a + 15*(n//2)**2


def main():
    global LEAF_CUTOFF
    results = []
    start = time.monotonic()
    # Verify every ordered bilinear tensor coefficient of the Winograd base.
    LEAF_CUTOFF = 1
    coefficients_checked = 0
    for left in range(4):
        for right in range(4):
            a = [[int(2*i+j == left) for j in range(2)] for i in range(2)]
            b = [[int(2*i+j == right) for j in range(2)] for i in range(2)]
            c = winograd(a, b)
            target = [[sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]
            assert c == target
            coefficients_checked += 4
    LEAF_CUTOFF = 10
    for n in [9, 81]:
        for seed in [917, 1823, 5911]:
            rng = random.Random(seed)
            a = [[rng.randrange(-5, 6) for _ in range(n)] for _ in range(n)]
            b = [[rng.randrange(-5, 6) for _ in range(n)] for _ in range(n)]
            COUNTS.update(multiplications=0, additions=0)
            c = winograd(a, b)
            counts = dict(COUNTS)
            target = [[sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
            assert c == target
            assert (counts['multiplications'], counts['additions']) == predicted(n)
            results.append(dict(n=n, seed=seed, tensor_outputs_checked=n*n, **counts, total=sum(counts.values()), status='PASS'))
    report = dict(status='PASS', base_tensor_coefficients_checked=coefficients_checked, construction='Classical up to 10; even dimensions use Winograd 7 products and 15 additions of blocks; odd dimensions peel the final row/column.', tests=results, scope='Exact integer example replay, complete bilinear coefficient check of the base, and actual scalar-operation counters. No runtime performance comparison.', seconds=time.monotonic()-start)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
