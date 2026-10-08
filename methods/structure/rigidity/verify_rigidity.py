#!/usr/bin/env python3
"""Read-only exact verifier of arithmetic premises of the p-adic rigidity proof.
Does not trust saved annihilators; rebuilds them over Q using p-unit pivot minors.
Full finite-field exhaustiveness is separately replayed by independent_scan.cpp.
"""
from pathlib import Path
from fractions import Fraction as F
from math import gcd
import json,itertools,hashlib
HERE=Path(__file__).resolve().parent

def mod(x,p):return x.numerator*pow(x.denominator,-1,p)%p

def pivots(rows,p):
 rows=[r[:]for r in rows];result=[];k=0
 for j in range(len(rows[0])):
  q=next((i for i in range(k,len(rows))if rows[i][j]),None)
  if q is None:continue
  rows[k],rows[q]=rows[q],rows[k];z=pow(rows[k][j],-1,p);rows[k]=[x*z%p for x in rows[k]]
  for i in range(k+1,len(rows)):
   z=rows[i][j]
   if z:rows[i]=[(x-z*y)%p for x,y in zip(rows[i],rows[k])]
  result.append(j);k+=1
  if k==len(rows):break
 return result

def unit_rref(A,cols,p):
 A=[r[:]for r in A];det=F(1)
 for k,j in enumerate(cols):
  q=next(i for i in range(k,len(A))if mod(A[i][j],p))
  if q!=k:A[k],A[q]=A[q],A[k];det=-det
  z=A[k][j];det*=z;A[k]=[x/z for x in A[k]]
  for i in range(len(A)):
   if i==k:continue
   z=A[i][j]
   if z:A[i]=[x-z*y for x,y in zip(A[i],A[k])]
 assert mod(det,p)!=0
 assert all(gcd(x.denominator,p)==1 for row in A for x in row)
 return A,det

def verify_one(name,p):
 D=json.loads((HERE/(name+'_source.json')).read_text());fac={s:[[F(x)for x in row]for row in D[s]]for s in 'uvw'};n,m,k=D['n'];r=D['m'];tensorchecks=0
 for ai,bi,ci in itertools.product(range(n*m),range(m*k),range(n*k)):
  got=sum(fac['u'][t][ai]*fac['v'][t][bi]*fac['w'][t][ci]for t in range(r));expect=int(ai//m==ci//k and ai%m==bi//k and bi%k==ci%k);assert got==expect;tensorchecks+=1
 result=[]
 for axes in ['uv','uw','vw']:
  a,b=[fac[x]for x in axes];d=len(a[0]);e=len(b[0]);P=[[x*y for x in u for y in v]for u,v in zip(a,b)];cols=pivots([[mod(x,p)for x in row]for row in P],p);assert len(cols)==r
  R,det=unit_rref(P,cols,p);NN=[]
  for j in range(d*e):
   if j in cols:continue
   v=[F(0)]*(d*e);v[j]=F(1)
   for i,c in enumerate(cols):v[c]=-R[i][j]
   # Direct original-span annihilation, independently of row-reduction logic.
   assert all(sum(x*y for x,y in zip(row,v))==0 for row in P)
   NN.append(v)
  saved=list(map(int,(HERE/f'{name}_p{p}_{axes}.txt').read_text().split()));assert saved[:4]==[p,d,e,len(NN)];assert saved[4:]==[mod(x,p)for row in NN for x in row]
  ranks=[]
  for u,v in zip(a,b):
   im=next(i for i,x in enumerate(u)if mod(x,p));jm=next(i for i,x in enumerate(v)if mod(x,p));u=[x/u[im]for x in u];v=[x/v[jm]for x in v]
   assert all(gcd(x.denominator,p)==1 for x in u+v)
   J=[[sum(N[i*e+j]*v[j]for j in range(e))for i in range(d)if i!=im]+[sum(N[i*e+j]*u[i]for i in range(d))for j in range(e)if j!=jm]for N in NN]
   rk=len(pivots([[mod(x,p)for x in row]for row in J],p));assert rk==d+e-2;ranks.append(rk)
  enum=json.loads((HERE/f'{name}_p{p}_{axes}_result.json').read_text());assert enum['span_dimension']==r and enum['rank_one_points']==r and enum['new_rank_one_points']==0
  indep=next(x for x in json.loads((HERE/'independent_results.json').read_text())if x['tag']==f'{name}_p{p}_{axes}');assert indep['comparison']=='PASS'
  result.append({'axes':axes,'prime':p,'rational_pair_span_dimension':r,'p_unit_minor_determinant':str(det),'rational_annihilator_rows':len(NN),'exact_annihilator_checks':len(NN)*r,'all_tangent_ranks':sorted(set(ranks)),'original_projective_points':len(ranks),'complete_scan_projective_domain':enum['tested_projective_first_factors'],'independent_complete_scan':'PASS','rational_pair_span_rigidity':'PASS'})
 return {'name':name,'source_sha256':D['source_sha256'],'rational_tensor_coefficients_verified':tensorchecks,'pairs':result}

if __name__=='__main__':
 results=[verify_one('rank49',2),verify_one('rank48',3)]
 print(json.dumps({'status':'PASS','results':results},indent=2))
