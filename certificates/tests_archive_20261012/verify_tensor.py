#!/usr/bin/env python3
"""Independently verify a full matrix multiplication tensor, standard library only.

Coordinates: U acts on row-major A, V on row-major B, and supplied W returns
column-major C. The latter is a storage order, not an arithmetic basis change.
"""
from pathlib import Path
import argparse
import json
from fractions import Fraction
from verify_literal import read_sms


def verify(u_path, v_path, w_path, n, m, k):
    u, _ = read_sms(u_path)
    v, _ = read_sms(v_path)
    w, _ = read_sms(w_path)
    rank = len(u)
    assert len(v) == rank and len(w) == n*k
    assert all(len(row) == n*m for row in u)
    assert all(len(row) == m*k for row in v)
    assert all(len(row) == rank for row in w)
    actual = {}
    for c, row in enumerate(w):
        for r, wc in enumerate(row):
            if not wc:
                continue
            for a, ua in enumerate(u[r]):
                if not ua:
                    continue
                for b, vb in enumerate(v[r]):
                    if vb:
                        key = c, a, b
                        actual[key] = actual.get(key, Fraction(0)) + wc*ua*vb
    actual = {key: value for key, value in actual.items() if value}
    expected = {(i+n*j, i*m+t, t*k+j): 1
                for i in range(n) for j in range(k) for t in range(m)}
    assert actual == expected, 'Bilinear tensor differs from standard matrix multiplication'
    return dict(status='PASS', dimensions=[n,m,k], rank=rank,
                exact_tensor_coefficients=(n*k)*(n*m)*(m*k),
                nonzero_tensor_coefficients=n*m*k,
                coordinates='A and B row-major; C column-major', basis_change=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('u','v','w'):
        p.add_argument(name, type=Path)
    p.add_argument('--dims', nargs=3, required=True, type=int)
    a = p.parse_args()
    print(json.dumps(verify(a.u,a.v,a.w,*a.dims),indent=2))
