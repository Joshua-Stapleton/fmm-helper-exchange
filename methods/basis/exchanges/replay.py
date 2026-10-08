#!/usr/bin/env python3
"""Portable finite-pool and coupled-root replay; Python stdlib + C++17."""
from pathlib import Path
from fractions import Fraction as Q
from itertools import combinations
from collections import defaultdict
import argparse,json,subprocess,tempfile,time
H=Path(__file__).resolve().parent

def rank(A):
 A=[list(r) for r in A];k=0
 for j in range(len(A[0])):
  p=next((i for i in range(k,len(A)) if A[i][j]),None)
  if p is None:continue
  A[k],A[p]=A[p],A[k];z=A[k][j];A[k]=[v/z for v in A[k]]
  for i in range(k+1,len(A)):
   z=A[i][j]
   if z:A[i]=[v-z*w for v,w in zip(A[i],A[k])]
  k+=1
  if k==len(A):break
 return k

def root_inputs():
 d=json.loads((H/'data/kernel_L_exchange3/pool.json').read_text())
 F=[tuple(Q(x)for x in v)for v in d['forms']];T={i for i,s in d['outputs']};P=defaultdict(set)
 for o,edges in d['productions'].items():
  o=int(o)
  for a,sa,b,sb in edges:
   sa,sb=Q(sa),Q(sb);P[o].add((a,sa,b,sb))
   if a!=b:P[a].add((o,sa,b,-sa*sb));P[b].add((o,sb,a,-sa*sb))
 # Validate every reverse relation before exporting its coefficient-free graph.
 for o,edges in P.items():
  for a,sa,b,sb in edges:assert F[o]==tuple(sa*x+sb*y for x,y in zip(F[a],F[b]))
 new=sorted(i for i in T if i>=16 and sum(abs(x)for x in F[i])==3 and max(abs(x)for x in F[i])==1)
 for k in (1,2):
  for take in combinations(new,k):
   support=sorted({j for i in take for j,x in enumerate(F[i])if x})
   for remove in combinations(support,k):
    roots=sorted(set(range(16))-set(remove)|set(take))
    if rank([F[i]for i in roots])!=16:continue
    order=roots+sorted(set(range(len(F)))-set(roots));idx={old:new for new,old in enumerate(order)}
    E=[(idx[o],idx[a],idx[b]) for o,ps in sorted(P.items())for a,sa,b,sb in sorted(ps)if idx[o]>=16]
    targets=sorted(idx[i]for i in T);helpers=sorted(idx[i]for i in d['helpers'])
    text=f'{len(F)} 16 {len(targets)} {len(helpers)} {len(E)}\n'+' '.join(map(str,targets))+'\n'+' '.join(map(str,helpers))+'\n'+'\n'.join(' '.join(map(str,e))for e in E)+'\n'
    yield {'roots':roots,'added_roots':list(take),'removed_roots':list(remove)},text

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--case',default='all',help='all, roots, or a directory name under data');ap.add_argument('--seconds',type=float,default=900,help='per native run; a timeout is not exhaustion');ap.add_argument('--output',type=Path);a=ap.parse_args()
 # This validates the exact productions and baseline before all searches.
 subprocess.run(['python3','-B',str(H/'audit.py')],check=True)
 records=[];start=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='fmm-basis-exchanges-')as td:
  td=Path(td);exes={}
  def run(engine,ip):
   if engine not in exes:
    exe=td/engine;subprocess.run(['c++','-O3','-std=c++17',str(H/(engine+'.cpp')),'-o',str(exe)],check=True);exes[engine]=exe
   p=subprocess.run([str(exes[engine]),str(ip),str(a.seconds)],capture_output=True,text=True,check=True,timeout=a.seconds+30)
   exhausted='EXHAUSTED' in p.stderr
   return {'status':'EXHAUSTED' if exhausted else ('FOUND' if p.stdout.startswith('FOUND')else 'INCOMPLETE'),'diagnostic':p.stderr.strip(),'witness':p.stdout.strip()}
  if a.case!='roots':
   paths=sorted((H/'data').glob('*exchange*/input.txt')) if a.case=='all' else [H/'data'/a.case/'input.txt']
   for p in paths:
    assert p.is_file(),p
    engine='exchange4_pruned' if p.parent.name.endswith('exchange4')else'exchange'
    r={'case':p.parent.name,**run(engine,p)};records.append(r);print(json.dumps(r),flush=True)
  if a.case in ('all','roots'):
   family=list(root_inputs());assert len(family)==60
   old=json.loads((H/'data/canonical_triple_helper_exchange/results.json').read_text())['rows']
   for i,(meta,txt) in enumerate(family):
    assert all(meta[k]==old[i][k]for k in meta)
    ip=td/'roots.txt';ip.write_text(txt)
    r={'case':'roots','number':i,**meta,**run('exchange_roots',ip)};records.append(r)
   print(json.dumps({'root_cases':len(family),'all_exhausted':all(r['status']=='EXHAUSTED' for r in records if r['case']=='roots')}),flush=True)
 result={'status':'PASS' if all(r['status']=='EXHAUSTED'for r in records)else'REVIEW','runs':records,'seconds':time.monotonic()-start,'scope':'Only the stated finite signed helper/root neighborhoods; not a global optimum. Found signed witnesses require strict sign/scalar accounting before use as upper bounds.'}
 if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'runs':len(records),'seconds':result['seconds']}))
if __name__=='__main__':main()
