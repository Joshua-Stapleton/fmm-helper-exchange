"""Exact tiny-update algebra for I + <=3 distinct signed off-diagonal entries.

A slot (i,j,s) means B[i,j]=s, with all diagonal entries equal to 1.
This module does not estimate or claim an optimal arithmetic circuit.
"""
from itertools import combinations, product
from math import comb

def counts(n, free_rows=None):
    m=n if free_rows is None else len(set(free_rows))
    k=m*(n-1)
    result=[]
    for r in (1,2,3):
        total=2**r*comb(k,r) if k>=r else 0
        cyclic=0 if r==1 else (2*comb(m,2) if r==2 else 4*comb(m,2)*(k-2)+8*comb(m,3))
        result.append(dict(entries=r,total=total,det0=cyclic,det1=total-2*cyclic,det2=cyclic))
    return result

def candidates(n,r,free_rows=None):
    rows=range(n) if free_rows is None else sorted(set(free_rows))
    slots=[(i,j) for i in rows for j in range(n) if i!=j]
    for locations in combinations(slots,r):
        for signs in product((-1,1),repeat=r):
            yield tuple((i,j,s) for (i,j),s in zip(locations,signs))

def determinant(edges):
    """det(I+UV) = det(I+VU); at most a 3x3 determinant."""
    r=len(edges)
    assert r<=3
    a=[[int(i==j)+s*int(col==row2) for j,(row2,col2,s2) in enumerate(edges)]
       for i,(row,col,s) in enumerate(edges)]
    if not r:return 1
    if r==1:return a[0][0]
    if r==2:return a[0][0]*a[1][1]-a[0][1]*a[1][0]
    return (a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
           -a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
           +a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]))

def dense(n,edges):
    b=[[int(i==j) for j in range(n)] for i in range(n)]
    assert len({(i,j) for i,j,s in edges})==len(edges)
    for i,j,s in edges:
        assert 0<=i<n and 0<=j<n and i!=j and s in (-1,1)
        b[i][j]=s
    return b

def preserves_singletons(edges,protected):
    return not any(i in protected for i,j,s in edges)

def inverse_circuit(n,edges):
    """For acyclic support, B^-1 has a circuit of exactly len(edges) gates.

Solve x_i = y_i - sum_j E_ij x_j after all dependencies x_j are ready.
Returns None for a cycle, including invertible determinant-two cycles.
Wires 0..n-1 are input y; output indices specify x in ordinary order.
"""
    deps={i:[] for i in range(n)}
    for i,j,s in edges:deps[i].append((j,s))
    done={};nodes=[]
    while len(done)<n:
        ready=[i for i in range(n) if i not in done and all(j in done for j,s in deps[i])]
        if not ready:return None
        for i in ready:
            wire=i
            for j,s in sorted(deps[i]):
                nodes.append((wire,done[j],-s));wire=n+len(nodes)-1
            done[i]=wire
    return {'inputs':n,'nodes':nodes,'outputs':[done[i] for i in range(n)]}
