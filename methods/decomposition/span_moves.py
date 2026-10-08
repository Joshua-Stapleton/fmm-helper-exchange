"""Exact rank-one pair-span replacement and four-target helper intersections.

Rational coefficient arrays are rank-term rows. These implement the algebraic
moves used by the October4 exploration; candidate enumeration is caller-owned.
"""
from fractions import Fraction as Q
from itertools import combinations

def rref(M):
    a=[[Q(x)for x in row]for row in M];p=[];i=0
    for j in range(len(a[0])):
        k=next((k for k in range(i,len(a))if a[k][j]),None)
        if k is None:continue
        a[i],a[k]=a[k],a[i];c=a[i][j];a[i]=[x/c for x in a[i]]
        for k in range(len(a)):
            if k!=i:
                c=a[k][j];a[k]=[x-c*y for x,y in zip(a[k],a[i])]
        p.append(j);i+=1
        if i==len(a):break
    return a,p

def tensor(A,B,C):
    return [sum((Q(a[i])*Q(b[j])*Q(c[k])for a,b,c in zip(A,B,C)),Q(0))
            for i in range(len(A[0]))for j in range(len(B[0]))for k in range(len(C[0]))]

def replace(A,B,C,av,bv,drop):
    """Replace a pair direction by av⊗bv, compensate all third-factor rows.

    Requires linearly independent old pair products and nonzero drop coefficient.
    Returns factors, coefficients. This preserves rank budget, not ternarity/cost.
    """
    if not A or not(len(A)==len(B)==len(C)):raise ValueError('equal nonzero rank required')
    r=len(A);da,db=len(A[0]),len(B[0])
    if any(len(a)!=da for a in A)or any(len(b)!=db for b in B)or any(len(c)!=len(C[0])for c in C):raise ValueError('ragged factors')
    if len(av)!=da or len(bv)!=db or not any(av)or not any(bv):raise ValueError('nonzero pair directions of matching dimensions required')
    P=[[Q(A[t][i])*Q(B[t][j])for t in range(r)]for i in range(da)for j in range(db)]
    h=[Q(av[i])*Q(bv[j])for i in range(da)for j in range(db)]
    M,p=rref([row+[x]for row,x in zip(P,h)])
    if p!=list(range(r)):raise ValueError('old pair span dependent or candidate outside span')
    cs=[M[i][-1]for i in range(r)]
    if not 0<=drop<r or not cs[drop]:raise ValueError('drop coefficient must be nonzero')
    D=[[list(map(Q,v))for v in F]for F in (A,B,C)]
    old=D[2][drop][:];D[0][drop]=list(map(Q,av));D[1][drop]=list(map(Q,bv))
    for t in range(r):
        D[2][t]=[z/cs[drop]for z in old]if t==drop else [z-cs[t]*w/cs[drop]for z,w in zip(D[2][t],old)]
    if tensor(*D)!=tensor(A,B,C):raise AssertionError('tensor mismatch')
    return D,cs

def four_target_directions(rows):
    """Intersect pair spans from every minimally dependent target quadruple.

    Outputs projective directions only. Choose magnitudes/gate constructions
    separately before charging a helper as a single addition.
    """
    F=[list(map(Q,v))for v in rows];found={}
    for ids in combinations(range(len(F)),4):
        M,p=rref([[F[t][j]for t in ids]for j in range(len(F[0]))])
        if len(p)!=3:continue
        free=next(j for j in range(4)if j not in p);c=[Q(0)]*4;c[free]=1
        for i,j in enumerate(p):c[j]=-M[i][free]
        if not all(c):continue
        for pair in [(0,1),(0,2),(0,3)]:
            v=tuple(sum(c[t]*F[ids[t]][j]for t in pair)for j in range(len(F[0])))
            if not any(v):continue
            lead=next(x for x in v if x);v=tuple(x/lead for x in v)
            found.setdefault(v,{'targets':ids,'relation':[str(x)for x in c],'pair':pair})
    return found

if __name__=='__main__':
    # A 2x2 Segre block with independent pair products.
    A=[[1,0],[1,0],[0,1],[0,1]];B=[[1,0],[0,1],[1,0],[0,1]];C=[[1,2],[2,0],[0,1],[3,1]]
    D,c=replace(A,B,C,[1,1],[1,-1],0)
    assert c==[1,-1,1,-1]and tensor(*D)==tensor(A,B,C)
    try:replace([[1,0]],[[1,0]],[[1]],[0,1],[1,0],0)
    except ValueError:pass
    else:raise AssertionError('out-of-span candidate accepted')
    H=four_target_directions([[1,0,0],[0,1,0],[0,0,1],[1,1,1]])
    assert len(H)==3 and (Q(1),Q(1),Q(0))in H
    print('PASS: exact replacement, outside-span rejection, all three helper intersections')
