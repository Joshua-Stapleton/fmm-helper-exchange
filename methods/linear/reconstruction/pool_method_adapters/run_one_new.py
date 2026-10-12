#!/usr/bin/env python3
"""Generate every target-unlocking one-hop vector and exact local exchanges."""
import hashlib
import importlib.util
import json
import argparse
import shutil
import subprocess
import time
import math
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True,help='Frozen pool JSON, including its starting incumbent')
parser.add_argument('--output',type=Path,required=True,help='New output directory')
parser.add_argument('--core',type=Path,default=HERE.parents[3]/'run.py',help='Repository root verifier module')
parser.add_argument('--all-one-hop',action='store_true')
parser.add_argument('--seconds',type=float,default=45)
args=parser.parse_args()
if not math.isfinite(args.seconds) or not 0<args.seconds<=60:
    raise ValueError('A finite duration in (0,60] seconds is required')
spec=importlib.util.spec_from_file_location('one_new_core',args.core);core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
source=args.source
raw=json.loads(source.read_text(),object_pairs_hook=core.unique_object)
core.require('witness' not in raw, 'Supply the pool and its incumbent; a separate witness is not a search input')
data,_,inc,_=core.load(source)
core.require(all(abs(x)<=(2**31-1)//2 for row in data['forms'] for x in row), 'Coefficient lacks int32 headroom')
OUT=args.output;core.require(not OUT.exists(), 'Refusing to overwrite structural output directory')
start=time.monotonic();forms=list(map(tuple,data['forms']));ids={v:i for i,v in enumerate(forms)};n=data['inputs']
canonical=lambda v:(v if next((x for x in v if x),0)>0 else tuple(-x for x in v)) if any(v) else None
target_vectors={forms[i] for i,s in data['outputs']};hits=defaultdict(set)
for ti,t in enumerate(sorted(target_vectors)):
    for f in forms:
        for s in (-1,1):
            v=canonical(tuple(a+s*b for a,b in zip(t,f)))
            if v is not None and v not in ids and max(map(abs,v))<=1:hits[v].add(ti)
hits={v:ts for v,ts in hits.items() if len(ts)>=2};representations=defaultdict(set);old=defaultdict(set)
for a,fa in enumerate(forms):
    for b in range(a,len(forms)):
        for sign in (-1,1):
            raw=tuple(x+sign*y for x,y in zip(fa,forms[b]));v=canonical(raw)
            if v is None:continue
            s=1 if raw==v else -1;p=(a,s,b,s*sign)
            if a<b and ((args.all_one_hop and v not in ids and max(map(abs,v))<=1) or v in hits):representations[v].add(p)
            out=ids.get(v)
            if out is not None and out>=n and out not in (a,b):old[out].add(p)
for out,rows in data['productions'].items():old[int(out)].update(map(tuple,rows))
candidates=sorted(representations,key=lambda v:(-len(hits.get(v,())),sum(x!=0 for x in v),v))
targets=sorted({i for i,s in data['outputs'] if i>=n});aux=sorted(set(inc)-set(targets))
core.require(len(aux)>=2, 'At least two incumbent non-target helpers are required for this exchange')
baseline=len(inc)
OUT.mkdir(parents=True,exist_ok=False)
rules=[(o,*p) for o in sorted(old) for p in sorted(old[o])]
lines=[f'{len(forms)} {n} {len(rules)} {len(targets)} {len(aux)} {len(candidates)}']
lines.extend(' '.join(map(str,v)) for v in forms);lines.extend(' '.join(map(str,p)) for p in rules)
lines.append(' '.join(map(str,targets)));lines.append(' '.join(map(str,aux)))
for v in candidates:
    lines.append(' '.join(map(str,v)));lines.append(str(len(representations[v])));lines.extend(' '.join(map(str,p)) for p in sorted(representations[v]))
(OUT/'input.txt').write_text('\n'.join(lines)+'\n')
generation=dict(old_forms=len(forms),old_all_binary_productions=len(rules),mandatory_noninput_target_forms=len(targets),incumbent_nontarget_helpers=aux,
                candidates=len(candidates),target_route_candidates=len(hits),generation_seconds=time.monotonic()-start,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                candidate_rule=('Every new ternary v=a +/- b from observed forms; no target-route filter' if args.all_one_hop else 'v=t +/- f absent from observed pool, ternary, at least two target routes, and v=a +/- b for observed forms'),
                separate_witness_input=False,scope='All candidate vectors; old forms plus exactly one candidate at a time',
                candidate_vectors=[list(v) for v in candidates])
(OUT/'generation.json').write_text(json.dumps(generation,indent=2)+'\n')
compiler=shutil.which('c++');command=[compiler,'-std=c++17','-O3',str(HERE/'one_new_helper.cpp'),'-o',str(OUT/'one_new_helper')]
t=time.monotonic();subprocess.run(command,check=True,timeout=60);compile_seconds=time.monotonic()-t
t=time.monotonic();p=subprocess.run([str(OUT/'one_new_helper'),str(OUT/'input.txt'),str(args.seconds)],capture_output=True,text=True,timeout=args.seconds+15)
(OUT/'stdout.json').write_text(p.stdout);(OUT/'stderr.txt').write_text(p.stderr);assert p.returncode==0,p.stderr
result=json.loads(p.stdout);result.update(search_wall_seconds=time.monotonic()-t,compile_seconds=compile_seconds,
                                         generation_seconds=generation['generation_seconds'],command=command,
                                         executable_sha256=hashlib.sha256((OUT/'one_new_helper').read_bytes()).hexdigest(),
                                         driver_sha256=hashlib.sha256((HERE/'one_new_helper.cpp').read_bytes()).hexdigest(),
                                         baseline=baseline,
                                         scope='One generated helper replaces exactly two incumbent non-target helpers; all mandatory targets may be reconnected; old one/two deletions prechecked')
if result['status']=='FOUND':
    ci=result['candidate_index'];values=forms+([candidates[ci]] if ci>=0 else [])
    producers={o:list(sorted(rows)) for o,rows in old.items()};selected={row[0]:tuple(row[1:]) for row in result['selected']}
    for out,production in selected.items():
        producers.setdefault(out,[])
        if production not in producers[out]:producers[out].append(production)
    full=dict(data,forms=list(map(list,values)),productions={str(k):list(map(list,v)) for k,v in producers.items()})
    checked=core.audit(selected,full,{k:list(map(tuple,v)) for k,v in producers.items()})
    assert len(checked)<baseline
    core.export(checked,full,OUT);(OUT/'witness_pool.json').write_text(json.dumps(full,indent=2)+'\n')
    result['independent_existing_core_replay']='PASS';result['addition_count_signed']=len(checked)
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='selected'}),flush=True)
