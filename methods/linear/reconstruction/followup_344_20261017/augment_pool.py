#!/usr/bin/env python3
"""Target-subset and pair-form augmentation for a fixed signed integer map."""
import argparse, math, hashlib, importlib.util, itertools, json, shutil, subprocess, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
PUB=HERE.parents[3]
def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
common=mod('aug_common',PUB/'methods/linear/reconstruction/common.py')
fast=mod('aug_fast',PUB/'methods/linear/fast_pool.py')
core=mod('aug_core',PUB/'run.py')
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def load(p):return json.loads(p.read_text())
def canon(v):
 sign=next((1 if x>0 else -1 for x in v if x),1)
 return tuple(sign*x for x in v),sign
def augment(target,mode):
 n=len(target[0]);forms=set()
 for row in target:
  entries=[i for i,x in enumerate(row) if x]
  for k in range(2,len(entries)+1):
   for subset in itertools.combinations(entries,k):
    forms.add(canon(tuple(x if i in subset else 0 for i,x in enumerate(row)))[0])
 if mode=='pairs':
  for a,b in itertools.combinations(range(n),2):
   for sign in (1,-1):forms.add(tuple(1 if i==a else sign if i==b else 0 for i in range(n)))
 known={tuple(int(i==j) for j in range(n)):(i,1) for i in range(n)};gates=[]
 def emit(v):
  v,orient=canon(v)
  if v in known:
   w,s=known[v];return w,s*orient
  terms=[(i,x) for i,x in enumerate(v) if x]
  assert len(terms)>1 and all(abs(x)==1 for i,x in terms)
  j,x=terms[-1];prefix=list(v);prefix[j]=0;a,sa=emit(tuple(prefix))
  gates.append([a,sa,j,x]);known[v]=(n+len(gates)-1,1)
  return n+len(gates)-1,orient
 for v in sorted(forms,key=lambda v:(sum(x!=0 for x in v),v)):emit(v)
 outputs=[list(emit(tuple(r))) for r in target]
 c=dict(inputs=n,gates=gates,outputs=outputs,target_matrix=target,name='synthetic_'+mode)
 assert common.exact_circuit(c,n)==target
 return c,len(forms)
def run(bank_path,mode,out,seconds,seed,perturb,relations=None,plateau=None):
 out.mkdir(parents=True,exist_ok=False);started=time.monotonic();bank=load(bank_path)
 donors=bank['circuits'];target=donors[0]['target_matrix'];extra,count=augment(target,mode)
 source=dict(inputs=len(target[0]),name='344_'+mode,circuits=donors+[extra])
 dump(out/'donors.json',source)
 data=fast.build_pool(source,binary=relations);dump(out/'pool.json',data)
 data,prods,best,_=core.load(out/'pool.json');core.export(best,data,out)
 targets={o for o,s in data['outputs']};helpers=sorted(set(best)-targets)
 edges=[(o,*p) for o in sorted(prods) for p in prods[o]]
 text=f"{len(data['forms'])} {data['inputs']} {len(targets)} {len(helpers)} {len(edges)}\n"+' '.join(map(str,sorted(targets)))+'\n'+' '.join(map(str,helpers))+'\n'+''.join(f'{o} {a} {b}\n' for o,a,sa,b,sb in edges)
 (out/'input.txt').write_text(text);prep=time.monotonic()-started
 if plateau is None:
  compiler=shutil.which('c++');assert compiler,'C++17 compiler required'
  plateau=out/'plateau'
  subprocess.run([compiler,'-std=c++17','-O3',str(PUB/'methods/linear/plateau.cpp'),'-o',str(plateau)],check=True)
 cmd=[str(plateau.resolve()),str((out/'input.txt').resolve()),str(seconds),str(seed),str(perturb),str((out/'selection.txt').resolve())]
 st=time.monotonic();p=subprocess.run(cmd,capture_output=True,text=True,timeout=seconds+10);elapsed=time.monotonic()-st
 assert p.returncode==0,p.stderr;(out/'stderr.txt').write_text(p.stderr)
 if (out/'selection.txt').exists():
  selected={}
  for line in (out/'selection.txt').read_text().splitlines()[1:]:
   o,e=map(int,line.split());oo,*prod=edges[e];assert oo==o;selected[o]=tuple(prod)
  chosen=core.audit(selected,data,prods)
  if len(chosen)<len(best):best=chosen;core.export(best,data,out)
 c=load(out/'candidate.json');assert common.exact_circuit(c,c['inputs'])==target
 r=dict(mode=mode,input_bank_sha256=hashlib.sha256(bank_path.read_bytes()).hexdigest(),donors=len(donors),generated_target_forms=count,pool_forms=len(data['forms']),productions=len(edges),preparation_seconds=prep,search_seconds=elapsed,budget_seconds=seconds,seed=seed,perturbation=perturb,signed_additions=len(best),total_elapsed_seconds=time.monotonic()-started,scope='Fixed original signed map, all live helper computations charged; strict orientation checked separately.')
 dump(out/'report.json',r);print(json.dumps(r),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bank',type=Path,required=True);p.add_argument('--mode',choices=['subsets','pairs'],default='pairs');p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=float,default=15);p.add_argument('--seed',type=int,default=172001);p.add_argument('--perturbation',type=int,default=6);p.add_argument('--relations',type=Path);p.add_argument('--plateau',type=Path);a=p.parse_args();assert math.isfinite(a.seconds) and a.seconds>0 and a.perturbation>0,'Positive finite budget and perturbation required';run(a.bank,a.mode,a.out,a.seconds,a.seed,a.perturbation,a.relations,a.plateau)
