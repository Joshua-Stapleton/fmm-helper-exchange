#!/usr/bin/env python3
"""Complete finite-field rank-one locus of a fixed two-factor span. Standard library."""
from pathlib import Path
from fractions import Fraction as Q
import json,hashlib,subprocess,sys,itertools,time,importlib.util
HERE=Path(__file__).resolve().parent

def rref(rows,p):
 a=[list(r) for r in rows];piv=[];k=0
 if not a:return [],[]
 for j in range(len(a[0])):
  t=next((t for t in range(k,len(a)) if a[t][j]%p),None)
  if t is None:continue
  a[k],a[t]=a[t],a[k];z=pow(a[k][j],-1,p);a[k]=[x*z%p for x in a[k]]
  for i in range(len(a)):
   if i!=k and a[i][j]%p:
    z=a[i][j];a[i]=[(x-z*y)%p for x,y in zip(a[i],a[k])]
  piv.append(j);k+=1
  if k==len(a):break
 return a[:k],piv

def canon(v,p):
 z=next(x for x in v if x);iz=pow(z,-1,p);return tuple(x*iz%p for x in v)
def mod(x,p):
 x=Q(x);return x.numerator*pow(x.denominator,-1,p)%p

def load_sources():
 return [json.loads((HERE/(name+'_source.json')).read_text()) for name in ('rank49','rank48')]

def verify_tensor(D,p):
 n,m,k=D['n'];r=D['m'];F=[[[mod(x,p)for x in row]for row in D[s]]for s in 'uvw'];ct=0
 for a,b,c in itertools.product(range(n*m),range(m*k),range(n*k)):
  expect=int(a//m==c//k and a%m==b//k and b%k==c%k)
  got=sum(F[0][t][a]*F[1][t][b]*F[2][t][c]for t in range(r))%p
  # The rank49 source stores C factors column major (trace convention).
  if got!=expect:return False,ct
  ct+=1
 return True,ct

def scan(D,p,axes):
 A,B=[[[mod(x,p)for x in row]for row in D[s]]for s in axes];n=len(A[0]);m=len(B[0]);rows=[[a*b%p for a in aa for b in bb]for aa,bb in zip(A,B)];R,piv=rref(rows,p);eq=[]
 for j in range(n*m):
  if j in piv:continue
  z=[0]*(n*m);z[j]=1
  for i,k in enumerate(piv):z[k]=-R[i][j]%p
  eq.append(z)
 tag=f"{D['name']}_p{p}_{axes}";ip=HERE/(tag+'.txt');hp=HERE/(tag+'_hits.txt')
 ip.write_text(f'{p} {n} {m} {len(eq)}\n'+'\n'.join(' '.join(map(str,z))for z in eq)+'\n')
 proc=subprocess.run([str(HERE/'span_scan'),str(ip),str(hp)],text=True,capture_output=True,check=True);result=json.loads(proc.stdout)
 old=set((canon(a,p),canon(b,p))for a,b in zip(A,B));hits=[]
 for line in hp.read_text().splitlines():
  a,b=line.split('|');a=tuple(map(int,a.split()));b=tuple(map(int,b.split()));outer=[x*y%p for x in a for y in b]
  # Independent membership check by direct reduction in the original span RREF.
  rem=outer[:]
  for row,k in zip(R,piv):
   z=rem[k];rem=[(x-z*y)%p for x,y in zip(rem,row)]
  assert not any(rem)
  hits.append((a,b))
 assert len(hits)==len(set(hits))==result['rank_one_points'];assert old<=set(hits)
 result.update(tag=tag,prime=p,axes=axes,shape=[n,m],source_terms=D['m'],span_dimension=len(R),old_rank_one_points=len(old),new_rank_one_points=len(set(hits)-old),source_sha256=D['source_sha256'],independent_exact_hit_membership='PASS',all_original_points_found=True,complete_projective_first_factor_domain=(p**n-1)//(p-1))
 assert result['tested_projective_first_factors']==result['complete_projective_first_factor_domain']
 (HERE/(tag+'_result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result

if __name__=='__main__':
 sources=load_sources();out=[]
 for D in sources:
  primes=[3] if D['name']=='rank48' else [2]
  for p in primes:
   ok,ct=verify_tensor(D,p)
   if not ok:
    n=D['n'][0];D['w']=[[row[j*n+i]for i in range(n)for j in range(n)]for row in D['w']];ok,ct=verify_tensor(D,p);assert ok
    (HERE/(D['name']+'_source.json')).write_text(json.dumps(D,default=str,indent=2)+'\n')
   print(json.dumps({'tensor':D['name'],'prime':p,'identities':ct,'status':'PASS'}),flush=True)
   for axes in ['uv','uw','vw']:out.append(scan(D,p,axes))
 (HERE/'span_results.json').write_text(json.dumps(out,indent=2)+'\n')
