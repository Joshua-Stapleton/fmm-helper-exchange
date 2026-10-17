#!/usr/bin/env python3
"""Portable rerunner. Without --run, only verifies archived evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from support import HERE,cases,core,read,replay_candidate

def run_one(case,out,engine='exhaustive',radius=3,seconds=5,seed=171701,repo=None,goal=None,known_triple=False):
    entry=cases()[case];api=core(repo);data,prods,inc,witness=api.load(entry['path']);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    edges=[(o,*p) for o in sorted(prods) for p in prods[o]];targets={o for o,_ in data['outputs']};helpers=sorted(set(inc)-targets)
    content=f"{len(data['forms'])} {data['inputs']} {len(targets)} {len(helpers)} {len(edges)}\n"+' '.join(map(str,sorted(targets)))+'\n'+' '.join(map(str,helpers))+'\n'+''.join(f'{o} {a} {b}\n' for o,a,sa,b,sb in edges);(out/'input.txt').write_text(content)
    source={'exhaustive':'exhaustive.cpp','frontier':'frontier.cpp','plateau':'published_plateau.cpp'}[engine]
    if goal is not None:assert engine=='exhaustive';source='exhaustive_goal.cpp'
    if known_triple:assert goal is not None and 'expected' in data;source='witness_replay.cpp'
    compiler=next((shutil.which(c) for c in ('c++','g++','clang++') if shutil.which(c)),None);assert compiler,'C++17 compiler required for --run'
    with tempfile.TemporaryDirectory(prefix='pool-radius-') as temporary:
        binary=Path(temporary)/'engine';subprocess.run([compiler,'-O3','-std=c++17',str(HERE/'sources'/source),'-o',str(binary)],check=True,timeout=120)
        if engine=='plateau':command=[str(binary),str(out/'input.txt'),str(seconds),str(seed),str(radius),str(out/'selection.txt')]
        else:command=[str(binary),str(out/'input.txt'),str(seconds),str(radius),str(seed)]
        if goal is not None:command.append(str(goal))
        if known_triple:command.append(','.join(map(str,data['expected']['removed'])))
        started=time.monotonic();p=subprocess.run(command,capture_output=True,text=True,timeout=seconds+15);elapsed=time.monotonic()-started
        assert p.returncode==0,p.stderr
    (out/'stdout.txt').write_text(p.stdout);(out/'stderr.txt').write_text(p.stderr);selected=inc;removed=[];added=[]
    if p.stdout.startswith('FOUND\n'):
        lines=p.stdout.splitlines();removed=list(map(int,lines[1].split()))[1:];added=list(map(int,lines[2].split()))[1:];(out/'selection.txt').write_text('FOUND\n'+'\n'.join(lines[3:])+'\n')
    if (out/'selection.txt').exists():
        raw={}
        for line in (out/'selection.txt').read_text().splitlines()[1:]:
            o,e=map(int,line.split());oo,*production=edges[e];assert oo==o and o not in raw;raw[o]=tuple(production)
        selected=api.audit(raw,data,prods)
        if removed:api.check_exchange(selected,removed,added,inc,data)
    api.export(selected,data,out);count=replay_candidate(read(out/'candidate.json'),data['target_matrix'])
    result=dict(case=case,engine=engine,radius_or_insertion_limit=radius,seed=seed,budget_seconds=seconds,elapsed_seconds=elapsed,baseline_signed_additions=len(inc),candidate_signed_additions=count,exact_ordered_map_verified=True,free_signed_wires=True,selected_removed=removed,selected_added=added,known_triple_prioritized=known_triple,goal=goal,pool_sha256=hashlib.sha256(entry['path'].read_bytes()).hexdigest(),source=source,source_sha256=hashlib.sha256((HERE/'sources'/source).read_bytes()).hexdigest(),diagnostic=p.stderr.strip())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--case',choices=sorted(cases()),default='u');p.add_argument('--engine',choices=['exhaustive','frontier','plateau'],default='exhaustive');p.add_argument('--radius',type=int,choices=[2,3,6],default=3);p.add_argument('--seconds',type=float,default=5);p.add_argument('--seed',type=int,default=171701);p.add_argument('--out',type=Path);p.add_argument('--repo',type=Path);p.add_argument('--goal',type=int);p.add_argument('--known-triple',action='store_true');a=p.parse_args()
    if not a.run:
        from verify import verify
        verify();return
    p.error('--out is required with --run') if a.out is None else None
    assert a.seconds>0 and a.radius in ([2,3] if a.engine!='plateau' else [2,3,6])
    print(json.dumps(run_one(a.case,a.out,a.engine,a.radius,a.seconds,a.seed,a.repo,a.goal,a.known_triple),indent=2))
if __name__=='__main__':main()
