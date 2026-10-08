#!/usr/bin/env python3
"""Exact rational all-orders absolute roundoff envelopes for one-level 4x4 SLPs.

Inputs are exact with max entry magnitude <=1. Each binary arithmetic operation
satisfies fl(z)=z(1+delta), |delta|<=u; signs and powers of two are exact.
No overflow or underflow is allowed. All conversions are included.
We represent each local rounding error as an additive noise. Its upper bound
uses exact downstream coefficients and previously bounded noises. Bilinear
cross terms between input-side noises are included, not discarded.
"""
import json
from fractions import Fraction as Q
from roundoff_audit import HERE, cases, circuit, plus, norm


def bound(name,lp,rp,pp,u):
    L,R,P = circuit(lp,16),circuit(rp,16),circuit(pp,48)
    U=[f for f,e in L.outputs];V=[f for f,e in R.outputs]
    X=[e for f,e in L.outputs];Y=[e for f,e in R.outputs]
    def encoder(C):
        E=[]
        for f,pre in zip(C.sites,C.pre_errors):
            E.append(u*(norm(f)+sum((abs(c)*E[j] for j,c in pre.items()),Q(0))))
        return E
    A,B=encoder(L),encoder(R)
    input_error=lambda es,E:sum((abs(c)*E[j] for j,c in es.items()),Q(0))
    M=[u*(norm(a)+input_error(x,A))*(norm(b)+input_error(y,B)) for a,b,x,y in zip(U,V,X,Y)]
    cache={}
    def base_and_error(w):
        key=tuple(sorted(w.items()))
        if key in cache:return cache[key]
        polynomial={};left={};right={};cross={}
        for i,c in w.items():
            for a,x in U[i].items():
                for b,y in V[i].items():
                    ab=(a,b);polynomial[ab]=polynomial.get(ab,Q(0))+c*x*y
            for j,x in X[i].items():
                left[j]=plus(left.get(j,{}),V[i],c*x)
                for k,y in Y[i].items():
                    jk=(j,k);cross[jk]=cross.get(jk,Q(0))+c*x*y
            for k,y in Y[i].items():right[k]=plus(right.get(k,{}),U[i],c*y)
        error=sum((A[j]*norm(f) for j,f in left.items()),Q(0))
        error+=sum((B[k]*norm(f) for k,f in right.items()),Q(0))
        error+=sum((abs(c)*A[j]*B[k] for (j,k),c in cross.items() if c),Q(0))
        error+=sum((abs(c)*M[i] for i,c in w.items()),Q(0))
        cache[key]=norm(polynomial),error
        return cache[key]
    D=[]
    for site,pre in zip(P.sites,P.pre_errors):
        value,error=base_and_error(site)
        D.append(u*(value+error+sum((abs(c)*D[j] for j,c in pre.items()),Q(0))))
    output=[]
    for f,e in P.outputs:
        _,error=base_and_error(f)
        output.append(error+sum((abs(c)*D[j] for j,c in e.items()),Q(0)))
    maximum=max(output)
    return {'name':name,'unit_roundoff':str(u),'max_absolute_error_bound':str(maximum),
        'max_absolute_error_bound_decimal':float(maximum),'bound_divided_by_u':float(maximum/u),
        'per_output_absolute_bounds':[str(x) for x in output]}


def main():
    results=[]
    for name,l,r,p in cases():
        if name not in ('ordinary_204','alt_170_43','alt_169_43'):continue
        for precision,bits in [('binary32',24),('binary64',53)]:
            result=bound(name,l,r,p,Q(1,2**bits));result['precision']=precision
            results.append(result)
            print(name,precision,result['bound_divided_by_u'],flush=True)
    print(json.dumps({'model':__doc__,'results':results},indent=2))


if __name__=='__main__':main()
