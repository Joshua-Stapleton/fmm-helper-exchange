#!/usr/bin/env python3
"""Opt-in reruns of the archived small protocols; default is verification only."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_search import run_one
from support import cases,read

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--suite',choices=['radius','frontier','historical','historical-goal','witness','historical-filtered'],default='frontier');p.add_argument('--seconds',type=float,default=5);p.add_argument('--out',type=Path);p.add_argument('--repo',type=Path);a=p.parse_args()
    if not a.run:
        from verify import verify
        verify();return
    if a.out is None:p.error('--out required with --run')
    assert a.seconds>0;a.out.mkdir(parents=True,exist_ok=False);entries=cases();jobs=[]
    if a.suite in ['radius','frontier']:
        seeds=[171701,172701] if a.suite=='radius' else [171701]
        arms=[('exhaustive',2),('exhaustive',3),('plateau',6)] if a.suite=='radius' else [('exhaustive',3),('frontier',3)]
        for case in entries:
            if entries[case]['group']!='current':continue
            for seed in seeds:
                for engine,radius in arms:jobs.append((case,engine,radius,seed,None,False))
    else:
        for case in ['u','wt']:
            target=read(entries[case]['path'])['expected']['additions']
            if a.suite=='historical-filtered':jobs.append((case,'frontier',3,171701,None,False))
            elif a.suite=='witness':jobs.append((case,'exhaustive',3,171701,target,True))
            else:
                for radius in [2,3]:jobs.append((case,'exhaustive',radius,171701,target if a.suite=='historical-goal' else None,False))
    rows=[]
    for case,engine,radius,seed,goal,known in jobs:
        out=a.out/case/f'{engine}_{radius}'/f'seed_{seed}';row=run_one(case,out,engine,radius,a.seconds,seed,a.repo,goal,known);rows.append(row)
        print(json.dumps({key:row[key] for key in ['case','engine','candidate_signed_additions','elapsed_seconds']}),flush=True)
    (a.out/'report.json').write_text(json.dumps(dict(suite=a.suite,results=rows),indent=2)+'\n')
if __name__=='__main__':main()
