#!/usr/bin/env python3
"""Standalone exact finite-grid verification; standard library and C++17 only."""
from pathlib import Path
from fractions import Fraction as F
from itertools import product,combinations
from math import gcd,lcm
from collections import Counter
import argparse,hashlib,json,subprocess,tempfile,time
from verify_source import verify,replay,multiply
H=Path(__file__).resolve().parent
G=((12,21),(22,18))
def canon(v):
 v=tuple(v);s=next((1 if x>0 else -1 for x in v if x),1);return tuple(s*x for x in v)
def inv2(p):
 a,b=p[0];c,d=p[1];z=a*d-b*c;assert z;return [[d/z,-b/z],[-c/z,a/z]]
def factor(s):return [[F(x)for x in r]for r in s]
def build(D,P,Q):
 o={s:[r[:]for r in D[s]]for s in D};pi,qi=inv2(P),inv2(Q)
 for i,j in product(range(2),repeat=2):
  t=G[i][j];o['v'][t]=[sum(P[i][a]*D['v'][G[a][0]][k]for a in range(2))for k in range(9)];o['w'][t]=[sum(Q[j][b]*D['w'][G[0][b]][k]for b in range(2))for k in range(9)];o['u'][t]=[sum(pi[a][i]*qi[b][j]*D['u'][G[a][b]][k]for a,b in product(range(2),repeat=2))for k in range(9)]
 return o

def signature(M):
 T=sorted(set(canon(v)for v in M));ids={v:i for i,v in enumerate(T)};rels=set();deg=[0]*len(T)
 for a,b in combinations(range(len(T)),2):
  for s in (-1,1):
   w=canon(x+s*y for x,y in zip(T[a],T[b]));k=ids.get(w)
   if k is not None and k not in(a,b):rels.add(tuple(sorted((a,b,k))))
 # Include target doubling relations explicitly, including proportional U forms.
 for a,v in enumerate(T):
  k=ids.get(tuple(2*x for x in v))
  if k is not None:rels.add((a,a,k))
 for r in rels:
  for i in r:deg[i]+=1
 return T,{'targets':len(T),'triangles':len(rels),'degree':sorted(deg)}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fast',action='store_true',help='validate all data, but do not replay native closure; not a completed lower-bound verification');a=ap.parse_args();start=time.monotonic()
 manifest=json.loads((H/'manifest.json').read_text())
 for p,sha in manifest.items():assert hashlib.sha256((H/p).read_bytes()).hexdigest()==sha,p
 source=json.loads((H/'source.json').read_text());D={s:factor(source[s])for s in ('u','v','w')};old=json.loads((H/'333.json').read_text());upper=verify(old);assert upper['kernel']==51
 maps={}
 for s,ni,no in [('U',9,23),('V',9,23),('W',23,9),('A_boundary',9,9),('B_boundary',9,9),('C_boundary',9,9)]:maps[s]=replay(old['maps'][s],ni,no,s)[0]
 assert D['u']==multiply(maps['U'],maps['A_boundary']);assert D['v']==multiply(maps['V'],maps['B_boundary']);assert D['w']==[list(v)for v in zip(*multiply(maps['C_boundary'],maps['W']))]
 dirs=sorted({canon((F(i),F(j)))for i,j in product(range(-2,3),repeat=2)if gcd(i,j)==1});bases=[p for p in combinations(dirs,2)if p[0][0]*p[1][1]!=p[0][1]*p[1][0]];assert len(dirs)==8 and len(bases)==28
 expected={(p,q)for p,q in product(bases,repeat=2)};grid=json.loads((H/'grid.json').read_text());assert len(grid)==784;seen=set();wsets={};floors=Counter();block=set(sum((list(x)for x in G),[]));supports={s:sorted({j for i in block for j,x in enumerate(D[s][i])if x})for s in D};block_checks=0
 for r in grid:
  P=tuple(tuple(F(x)for x in v)for v in r['P']);Q=tuple(tuple(F(x)for x in v)for v in r['Q']);assert(P,Q)in expected and(P,Q)not in seen;seen.add((P,Q));m={s:factor(r['factors'][s])for s in D};assert m==build(D,P,Q)
  for s in D:assert all(m[s][i]==D[s][i]for i in range(23)if i not in block)
  for i,j,k in product(supports['u'],supports['v'],supports['w']):
   assert sum(m['u'][t][i]*m['v'][t][j]*m['w'][t][k]for t in block)==sum(D['u'][t][i]*D['v'][t][j]*D['w'][t][k]for t in block);block_checks+=1
  for s in D:
   T,sig=signature(m[s]);assert sig==r['signature'][s]
   if s=='u':assert sig['targets']==21 or(sig['targets']==20 and sig['triangles']<=10)
   else:assert sig['targets']==20 and sig['triangles']<=9
   if s=='w':
    if Q in wsets:assert wsets[Q]==T
    else:wsets[Q]=T
  floor=52 if r['signature']['u']['targets']==21 and r['signature']['u']['triangles']<12 else 51;assert r['kernel_floor']==floor;floors[floor]+=1
 assert seen==expected and len(wsets)==28
 # The simultaneous row-swap member just permutes the source's four block terms.
 sw=((F(0),F(1)),(F(1),F(0)));M=build(D,sw,sw);assert sorted(tuple(tuple(M[s][i])for s in ('u','v','w'))for i in range(23))==sorted(tuple(tuple(D[s][i])for s in ('u','v','w'))for i in range(23))
 results=json.loads((H/'decoder_results.json').read_text());assert len(results)==28;covered=tests=0
 with tempfile.TemporaryDirectory(prefix='segre-grid-')as td:
  exe=Path(td)/'one_helper'
  if not a.fast:subprocess.run(['c++','-O3','-std=c++17',str(H/'one_helper.cpp'),'-o',str(exe)],check=True)
  for row in results:
   Q=tuple(tuple(F(x)for x in v)for v in row['Q']);T=wsets[Q];den=2*lcm(*(x.denominator for v in T for x in v));desired=[int(x*den)for v in T for x in v];path=H/'decoder_inputs'/row['input'];words=list(map(int,path.read_text().split()));assert words[:2]==[20,9]and words[2:]==desired
   known=row['native_result'];assert known['status']=='PASS'and known['no_12_gate_circuit']
   if not a.fast:
    proc=subprocess.run([str(exe),str(path)],capture_output=True,text=True,check=True);got=json.loads(proc.stdout)
    assert{k:v for k,v in got.items()if k!='seconds'}=={k:v for k,v in known.items()if k!='seconds'}
   covered+=known['covered_root_subsets'];tests+=known['distinct_closure_tests']
 result={'status':'DATA_ONLY_PASS'if a.fast else'PASS','transformed_decompositions':len(grid),'exact_changed_block_coefficients':block_checks,'source_tensor_coefficients':upper['tensor_identities'],'decoder_cases':28,'covered_root_helper_cases':covered,'distinct_decoder_closures':tests,'kernel_floor_histogram':dict(floors),'finite_grid_minimum':51,'attained_by_source_term_permutation':True,'seconds':time.monotonic()-start,'scope':'Specified784 rational transforms only; arbitrary independent bases; copies/signs free; no nonunit scalar gates or additional nonunit term gauges; conversion costs excluded.'};print(json.dumps(result,indent=2))
if __name__=='__main__':main()
