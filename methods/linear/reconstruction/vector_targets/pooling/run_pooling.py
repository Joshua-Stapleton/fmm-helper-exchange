#!/usr/bin/env python3
"""Post-study finite-pool recombination; no native runs or changing study banks."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time

HERE=Path(__file__).resolve().parent
E=HERE.parent
PUBLIC=E.parents[3]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value

api=module('pooling_native_adapter',E/'toolchain/adapter.py')
fast=module('pooling_fast_pool',PUBLIC/'methods/linear/fast_pool.py')
core=module('pooling_core',PUBLIC/'run.py')

def load(path):return json.loads(Path(path).read_text())
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def circuits(paths,target):
    output=[];seen=set();records=[]
    for path in paths:
        bank=load(path);validated=0
        for c in bank['circuits']:
            cost=api.replay(c,target)
            key=json.dumps([c['gates'],c['outputs']],separators=(',',':'))
            validated+=1
            if key in seen:continue
            seen.add(key);output.append(dict(c,name=f'donor_{len(output)}'))
        records.append(dict(path=str(path),sha256=sha(path),circuits=validated))
    return output,records

def exact_closure(data,prods,helpers):
    n=data['inputs'];targets={i for i,s in data['outputs']}
    allowed=set(range(n))|targets|set(helpers);ready=set(range(n));chosen={}
    while True:
        change=False
        for out in sorted(prods):
            if out not in allowed or out in ready:continue
            for a,sa,b,sb in prods[out]:
                if a in ready and b in ready:
                    ready.add(out);chosen[out]=(a,sa,b,sb);change=True;break
        if not change:return core.audit(chosen,data,prods)

def job(case,arm,paths,budget,seed,root,binaries):
    start=time.monotonic();out=root/case['id']/arm;out.mkdir(parents=True,exist_ok=False)
    target=load(case['matrix']);donors,sources=circuits(paths,target)
    raw_best=min(len(c['gates']) for c in donors)
    prep=time.monotonic();data=fast.build_pool(dict(name=case['id']+'_'+arm,inputs=case['inputs'],circuits=donors),binary=binaries['relations'])
    poolpath=out/'pool.json';dump(poolpath,data)
    data,prods,incumbent,_=core.load(poolpath)
    initial_count=len(incumbent);targets={o for o,s in data['outputs']}
    reconnected=exact_closure(data,prods,set(incumbent)-targets)
    if len(reconnected)<len(incumbent):
        incumbent=reconnected;data['incumbent']={str(o):list(p) for o,p in incumbent.items()};dump(poolpath,data)
    best=incumbent;core.export(best,data,out)
    # Same exact finite pool and deterministic seed for matched arms.
    edges=[(o,*p) for o in sorted(prods) for p in prods[o]]
    helper=sorted(set(incumbent)-targets)
    content=f"{len(data['forms'])} {data['inputs']} {len(targets)} {len(helper)} {len(edges)}\n"
    content+=' '.join(map(str,sorted(targets)))+'\n'+' '.join(map(str,helper))+'\n'
    content+=''.join(f'{o} {a} {b}\n' for o,a,sa,b,sb in edges)
    (out/'input.txt').write_text(content)
    prepare_seconds=time.monotonic()-prep;search_start=time.monotonic()
    command=[str(binaries['plateau']),str(out/'input.txt'),str(budget),str(seed),'6',str(out/'selection.txt')]
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=budget+15)
        core.require(result.returncode==0,'Plateau engine failure: '+result.stderr)
        stderr=result.stderr;status='COMPLETED'
    except subprocess.TimeoutExpired as error:
        stderr=error.stderr or '';stderr=stderr.decode() if isinstance(stderr,bytes) else stderr;status='HARD_TIMEOUT'
    search_seconds=time.monotonic()-search_start;(out/'stderr.txt').write_text(stderr)
    selection=out/'selection.txt'
    if selection.exists():
        lines=selection.read_text().splitlines();core.require(lines[0]=='FOUND','Bad selection header');selected={}
        for line in lines[1:]:
            o,edge=map(int,line.split());core.index(edge,len(edges));oo,*p=edges[edge]
            core.require(oo==o and o not in selected,'Bad selection indexed edge');selected[o]=tuple(p)
        candidate=core.audit(selected,data,prods)
        if len(candidate)<len(best):best=candidate;core.export(best,data,out)
    candidate=load(out/'candidate.json');cost=api.replay(candidate,target)
    core.require(cost==len(best)<=raw_best,'Pool lost the incumbent or exported count mismatch')
    report=dict(case_id=case['id'],arm=arm,status=status,source_banks=sources,distinct_donors=len(donors),raw_donor_best=raw_best,
                baseline_signed_additions=case['local_signed_additions'],initial_pool_additions=initial_count,initial_reconnected_additions=len(incumbent),
                best_signed_additions=cost,forms=len(data['forms']),exact_binary_relations=len(edges),pool_seconds=prepare_seconds,
                search_budget_seconds=budget,search_elapsed_seconds=search_seconds,total_elapsed_seconds=time.monotonic()-start,
                seed=seed,perturbation=6,scope='Heuristic fixed linear-map signed-wire pool search. All forms are paid. No optimality or literal sign-orientation claim.',
                candidate=str(out/'candidate.json'),candidate_sha256=sha(out/'candidate.json'),pool_sha256=sha(poolpath),exact_map_verified=True)
    dump(out/'result.json',report);return report

def build():
    out=HERE/'toolchain';out.mkdir(exist_ok=True)
    compiler=shutil.which('c++');core.require(compiler,'C++ compiler required')
    srcdir=PUBLIC/'methods/linear';records=[];binaries={}
    for label,name in [('relations','pool_relations.cpp'),('plateau','plateau.cpp')]:
        original=srcdir/name;snapshot=out/name;shutil.copyfile(original,snapshot);binary=out/label
        command=[compiler,'-std=c++17','-O3',str(snapshot),'-o',str(binary)]
        subprocess.run(command,check=True,timeout=120);binaries[label]=binary.resolve()
        records.append(dict(label=label,source=str(original),source_sha256=sha(snapshot),frozen_source=str(snapshot),binary_sha256=sha(binary),command=command))
    dump(out/'build.json',dict(worker_count_per_engine=1,binaries=records,public_repo_modified=False));return binaries

def run(args):
    study=load(E/'native_study/main/report.json');core.require(study['status']=='COMPLETE','Native study must finish before pooling')
    cases=load(E/'benchmarks/manifest.json')['cases']
    for c in cases:
        for key in ('matrix','original_matrix','candidate','native','donors','native_donors','strict_incumbent'):
            c[key]=str(E/c[key])
    byid={c['id']:c for c in cases};exports=study['exports']
    jobs=[]
    for case in cases:
        base=Path(case['donors']);selected=[x for x in exports if x['case_id']==case['id']]
        seed=args.seed+int(hashlib.sha256(case['id'].encode()).hexdigest()[:6],16)
        jobs.append((case,'baseline_frozen',[base],args.seconds,seed))
        for entry in selected:
            jobs.append((case,entry['arm'],[base,Path(entry['donors'])],args.seconds,seed))
        jobs.append((case,'combined',[base,*[Path(x['donors']) for x in selected]],args.combined_seconds,seed))
    args.out.mkdir(parents=True,exist_ok=False)
    dump(args.out/'PLAN.json',dict(native_study_sha256=sha(E/'native_study/main/report.json'),jobs=[dict(case=c['id'],arm=a,banks=list(map(str,p)),seconds=s,seed=r) for c,a,p,s,r in jobs],workers=args.workers))
    binaries=build();started=time.monotonic();results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures={executor.submit(job,*j,args.out,binaries):(j[0]['id'],j[1]) for j in jobs}
        for future in as_completed(futures):
            cid,arm=futures[future]
            try:r=future.result()
            except Exception as error:r=dict(case_id=cid,arm=arm,status='ERROR',error=str(error))
            results.append(r);dump(args.out/'progress.json',results)
            print(json.dumps({k:r.get(k) for k in ['case_id','arm','status','best_signed_additions','pool_seconds','search_elapsed_seconds']}),flush=True)
    best=[]
    for case in cases:
        valid=[r for r in results if r['case_id']==case['id'] and r.get('exact_map_verified')]
        best.append(dict(case_id=case['id'],previous_signed=case['local_signed_additions'],best=min((r['best_signed_additions'] for r in valid),default=None),arms=[{k:r[k] for k in ['arm','best_signed_additions','candidate','total_elapsed_seconds']} for r in valid]))
    report=dict(status='COMPLETE',native_study_sha256=sha(E/'native_study/main/report.json'),workers=args.workers,wall_seconds=time.monotonic()-started,results=results,best=best,errors=sum(r['status']=='ERROR' for r in results),comparison='Each separate arm receives the same frozen-bank circuits plus its capped new donors; baseline uses the frozen bank alone. Combined uses their union with a longer separately disclosed search budget. One plateau seed per case shared across arms; this is not a performance generalization.')
    dump(args.out/'report.json',report);return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=HERE/'results');p.add_argument('--seconds',type=float,default=5);p.add_argument('--combined-seconds',type=float,default=8);p.add_argument('--seed',type=int,default=171000);p.add_argument('--workers',type=int,default=3);a=p.parse_args();run(a)
