#!/usr/bin/env python3
"""Re-run matched old-bank and expanded-bank pooling, one worker at a time."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from runtime import module,vector_targets,build_pool_engines

HERE=Path(__file__).resolve().parent


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')


def main(args):
    cases=load(HERE/'data/manifest.json')['cases']
    if args.case:
        cases=[c for c in cases if c['id']==args.case]
        if not cases:raise ValueError('Unknown case')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    engines=build_pool_engines(out/'toolchain')
    pool=module('portable_pool_job',vector_targets()/'pooling/run_pooling.py')
    jobs=[]
    for c in cases:
        case=dict(id=c['id'],matrix=str(HERE/c['matrix']),inputs=c['inputs'],local_signed_additions=c['initial_additions'])
        prior=[HERE/c['prior']]
        new=[(args.native_run/'exports'/c['id']/arm/'donors.json' if args.native_run else HERE/path)
             for arm,path in c['exports'].items()]
        seed=172000+int(hashlib.sha256(c['id'].encode()).hexdigest()[:6],16)
        jobs.extend([(case,'prior_bank_control',prior,args.seconds,seed),
                     (case,'with_new_native_donors',prior+new,args.seconds,seed)])
    dump(out/'PLAN.json',dict(seconds_per_call=args.seconds,workers=1,
                             source='Frozen banks by default; optional --native-run uses a newly generated bounded native export.',
                             jobs=[dict(case=c['id'],arm=a,banks=list(map(str,p)),seed=s) for c,a,p,t,s in jobs]))
    started=time.monotonic();results=[]
    for job in jobs:
        r=pool.job(*job,out,engines)
        results.append(r);dump(out/'progress.json',results)
        print(json.dumps({k:r[k] for k in ['case_id','arm','best_signed_additions','exact_map_verified']}),flush=True)
    dump(out/'report.json',dict(status='COMPLETE',results=results,wall_seconds=time.monotonic()-started))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=HERE/'runs/pooling')
    p.add_argument('--seconds',type=float,default=15)
    p.add_argument('--case',help='Optional case ID from data/manifest.json')
    p.add_argument('--native-run',type=Path,help='Optional output of run_sizes.py; otherwise use frozen bounded donors.')
    args=p.parse_args()
    if args.seconds<=0:raise ValueError('Positive search budget required')
    main(args)
