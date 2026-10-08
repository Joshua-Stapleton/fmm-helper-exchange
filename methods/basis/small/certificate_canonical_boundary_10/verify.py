"""Exhaustive basis census for the ordinary cost of fully canonical V bases.
Targets are fixed; literal upper6 is known. Exclude every5-addition target basis.
"""
from pathlib import Path
from itertools import combinations,combinations_with_replacement
from math import lcm
from collections import Counter
import json,subprocess,time,os,platform
HERE=Path(__file__).resolve().parent
from pattern_utils import canon,det,rtype,matrix_canon

def rankmod(A):
 A=[list(r)for r in A];k=0;p=1009
 for j in range(len(A[0])):
  i=next((i for i in range(k,len(A))if A[i][j]%p),None)
  if i is None:continue
  A[k],A[i]=A[i],A[k];z=pow(A[k][j]%p,-1,p);A[k]=[x*z%p for x in A[k]]
  for i in range(k+1,len(A)):
   z=A[i][j];A[i]=[(x-z*y)%p for x,y in zip(A[i],A[k])]
  k+=1
 return k

def closure(T,H,roots):
 F=T+H;idx={v:i for i,v in enumerate(F)};known={idx[r]for r in roots};rules=[]
 for i,u in enumerate(F):
  for j in range(i,len(F)):
   for s in [-1,1]:
    k=idx.get(canon(x+s*y for x,y in zip(u,F[j])))
    if k is not None and k not in(i,j):rules.append((i,j,k))
 while True:
  old=len(known)
  for i,j,k in rules:
   if i in known and j in known:known.add(k)
  if len(known)==old:return all(i in known for i in range(len(T)))

def main():
 start=time.monotonic();out=HERE/'replay';out.mkdir(exist_ok=True);D=json.loads((HERE/'scheme233.json').read_text());M=sorted({canon(r)for r in D['source']['v']});units=[tuple(int(i==j)for j in range(9))for i in range(9)];unitset=set(units);assert len(M)==15
 B=D['outer_matrices']['v'];c=D['boundary']['v'];assert len(c['nodes'])==6 and all(x['op']in['add','sub']for x in c['nodes']);vv=[tuple(int(i==j)for j in range(9))for i in range(9)]
 for z in c['nodes']:vv.append(tuple(x+(1 if z['op']=='add'else-1)*y for x,y in zip(vv[z['a']],vv[z['b']])))
 assert [list(vv[i])for i in c['outputs']]==B;assert rankmod(B)==9;assert all(canon(r)in M for r in B)
 for side in'uw':
  MM=D['source'][side];assert len(MM[0])==6;assert len({canon(r)for r in MM if sum(bool(x)for x in r)==1})==4
  cc=D['boundary'][side];assert cc['inputs']==6 and len(cc['nodes'])==2;ww=[tuple(int(i==j)for j in range(6))for i in range(6)]
  for z in cc['nodes']:
   assert z['op']in['add','sub'];ww.append(tuple(x+(1 if z['op']=='add'else-1)*y for x,y in zip(ww[z['a']],ww[z['b']])))
  BB=[ww[i]for i in cc['outputs']];assert[list(r)for r in BB]==D['outer_matrices'][side]
  BF=BB if side=='u'else list(zip(*BB));assert rankmod(BF)==6;assert all(canon(r)in{canon(t)for t in MM}for r in BF)
 # Hadamard's determinant bound makes rank modulo1009 exact for these9x9 matrices.
 assert max(sum(x*x for x in r)for r in M)**9<1009**2
 rows=[(1,0),(2,0),(0,1),(0,2),(1,1),(1,-1),(2,1),(2,-1),(1,2),(1,-2)];patterns=sorted({matrix_canon(A)for A in combinations(rows,2)if det(A)and any(rtype(r)for r in A)});scale=lcm(2,*[abs(det(A))for A in patterns]);suffix=''.join(' '.join(map(str,[det(A),*[rtype(r)for r in A],A[1][1],-A[0][1],-A[1][0],A[0][0]]))+'\n'for A in patterns);binary=out/'complete_two';clt=Path('/Library/Developer/CommandLineTools');cmd=[os.environ.get('CXX','c++'),'-O3','-std=c++17'];
 if platform.system()=='Darwin'and'CXX'not in os.environ:cmd=[str(clt/'usr/bin/clang++'),'-O3','-std=c++17','-isysroot',str(clt/'SDKs/MacOSX.sdk'),'-B'+str(clt/'usr/bin')]
 subprocess.run(cmd+[str(HERE/'complete_two.cpp'),'-o',str(binary)],check=True)
 hist=Counter();tested=0;hits=[];h1cases=0;h2trials=0;h2valid=0
 for ids in combinations(range(15),9):
  B=[M[i]for i in ids];non=[v for v in B if v not in unitset];t=len(non)
  if t>5:hist['too_many_nonunits']+=1;continue
  if rankmod(B)<9:hist['singular']+=1;continue
  hist[str(t)]+=1;tested+=1;h=5-t;assert 0<=h<=2
  T=sorted(set(tuple(scale*x for x in r)for r in units+non));U=[tuple(scale*x for x in r)for r in units]
  if h==0:
   if closure(T,[],U):hits.append({'ids':ids,'helpers':[]})
  elif h==1:
   helpers={canon(x+s*y for x,y in zip(u,v))for u,v in combinations_with_replacement(T,2)for s in[-1,1]}|{tuple(x//2 for x in u)for u in T};helpers={v for v in helpers if any(v)and v not in T}
   for H in helpers:
    h1cases+=1
    if closure(T,[H],U):hits.append({'ids':ids,'helpers':[H]});break
  else:
   inp=out/f'basis_{tested}.txt';passes=out/f'basis_{tested}_passes.txt';inp.write_text(f'{len(T)} 9 {len(patterns)}\n'+''.join(' '.join(map(str,t))+'\n'for t in T)+suffix);cp=subprocess.run([str(binary),str(inp),str(passes)],check=True,capture_output=True,text=True);rr=json.loads(cp.stdout.splitlines()[-1]);h2trials+=rr['trials'];h2valid+=rr['valid']
   for line in passes.read_text().splitlines():
    nums=list(map(int,line.split()));H=[tuple(nums[2+i*9:2+(i+1)*9])for i in range(2)]
    if closure(T,H,U):hits.append({'ids':ids,'helpers':H});break
  if tested%100==0:print('PROGRESS',tested,dict(hist),time.monotonic()-start,flush=True)
  if hits:print('HIT',hits[-1],flush=True);break
 assert not hits and sum(hist.values())==5005
 result={'status':'PASS'if not hits else'COUNTEREXAMPLE','basis_subsets_total':5005,'tested_full_rank_bases_with_at_most_five_nonunits':tested,'classification':hist,'single_helper_cases':h1cases,'two_helper_assignments':h2trials,'two_helper_valid':h2valid,'hits':hits,'seconds':time.monotonic()-start,'claim':'Every basis formed from9 signed target rows costs at least6 ordinary additions, with arbitrary rational helper forms; counts ignore unary signs.'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
