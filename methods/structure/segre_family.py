#!/usr/bin/env python3
"""Exact tensor-preserving GL2 x GL2 family on the fixed51 rank23 source.
All factors are r-by-9 in ordinary row-major coordinates.
"""
from pathlib import Path
from fractions import Fraction as F
import json,itertools,copy
HERE=Path(__file__).resolve().parent
GRID=((12,21),(22,18))
def inv2(P):
 P=[list(map(F,r))for r in P];a,b=P[0];c,d=P[1];det=a*d-b*c
 if not det:raise ValueError('singular transform')
 return [[d/det,-b/det],[-c/det,a/det]]
def transform(D,P,Q):
 D=copy.deepcopy(D);fac={s:[[F(x)for x in r]for r in D[s]]for s in 'uvw'};P=[list(map(F,r))for r in P];Q=[list(map(F,r))for r in Q];IP,IQ=inv2(P),inv2(Q)
 V=[fac['v'][GRID[i][0]]for i in range(2)];W=[fac['w'][GRID[0][j]]for j in range(2)];U=[[fac['u'][GRID[i][j]]for j in range(2)]for i in range(2)]
 assert all(fac['v'][GRID[i][j]]==V[i] and fac['w'][GRID[i][j]]==W[j]for i,j in itertools.product(range(2),repeat=2))
 for i,j in itertools.product(range(2),repeat=2):
  t=GRID[i][j];fac['u'][t]=[sum(IP[a][i]*IQ[b][j]*U[a][b][k]for a,b in itertools.product(range(2),repeat=2))for k in range(9)]
  fac['v'][t]=[sum(P[i][a]*V[a][k]for a in range(2))for k in range(9)]
  fac['w'][t]=[sum(Q[j][b]*W[b][k]for b in range(2))for k in range(9)]
 D.update(fac);return D

def verify(D):
 FQ={s:[[F(x)for x in row]for row in D[s]]for s in 'uvw'}
 for a,b,c in itertools.product(range(9),repeat=3):
  val=sum(FQ['u'][t][a]*FQ['v'][t][b]*FQ['w'][t][c]for t in range(23));assert val==int(a//3==c//3 and a%3==b//3 and b%3==c%3)
 return 729
if __name__=='__main__':
 D=json.loads((HERE/'rank23_source.json').read_text());Ts=[[[1,0],[0,1]],[[1,1],[0,1]],[[1,0],[-1,1]],[[1,1],[1,-1]],[[1,2],[0,1]]];out=[]
 for i,P in enumerate(Ts):
  for j,Q in enumerate(Ts):
   G=transform(D,P,Q);checks=verify(G);out.append({'P':P,'Q':Q,'tensor_coefficients':checks})
   if (i,j)==(1,2):(HERE/'rank23_segre_shear_example.json').write_text(json.dumps(G,default=str,indent=2)+'\n')
 (HERE/'segre_family_verification.json').write_text(json.dumps({'status':'PASS','grid_terms':GRID,'block_factor_ranks':[4,2,2],'cases':out,'total_tensor_coefficients':sum(x['tensor_coefficients']for x in out),'locus_count_formulas':'observed for p=2,3,5 only; explicit Segre subfamily exists over Q'},indent=2)+'\n')
 print('PASS',len(out),'rational GL2 x GL2 transformations;',sum(x['tensor_coefficients']for x in out),'tensor coefficients')
