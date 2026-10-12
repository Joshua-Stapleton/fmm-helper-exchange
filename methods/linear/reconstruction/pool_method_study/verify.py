#!/usr/bin/env python3
"""Verify all released raw prefixes/maps and numerical study inventories."""
import csv
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('study_lib',HERE/'lib.py')
lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)


def verify():
    manifest=lib.read(HERE/'MANIFEST.json')
    for name,expected in manifest['files'].items():lib.require(lib.digest(HERE/name)==expected,'Hash mismatch '+name)
    study=lib.read(HERE/'STUDY.json');sources={};prefixes=0;complete=0;paired_attempts=0;paired_complete=0
    for case in study['cases']:
        target=lib.matrix(HERE/'data/maps'/(case+'.sms'));n=len(target[0]);bank=lib.read(HERE/'data/maps'/(case+'.native.json'))
        prods,helpers=lib.native_productions(bank,n,target);sources[case]=(target,n,bank,prods)
        lib.binary(lib.read(HERE/'data/maps'/(case+'.known_binary.json')),target)
        for mode in ['weighted','uniform','bernoulli']:
            data=lib.read(HERE/'data/paired'/(case+'_'+mode+'.json'));costs=[s['additions']for s in bank['solutions']]
            if mode in ('weighted','bernoulli'):
                counts=Counter(costs);T=data['temperature'];eps=data['epsilon'];best=min(costs)
                values=[math.exp(-(c-best)/T)/counts[c]for c in costs];total=sum(values)
                weights=[(1-eps)*v/total+eps/len(values)for v in values]
            else:weights=[1/len(costs)]*len(costs)
            lib.require(all(abs(a-b)<1e-12 for a,b in zip(weights,data['weights'])),'Weight formula changed')
            for draw in data['draws']:
                lib.prefix(draw['prefix'],n,prods,draw['gate_limit']);prefixes+=1;paired_attempts+=1
                if draw['solution']is not None:
                    lib.raw(draw['solution'],n,target);complete+=1;paired_complete+=1
        for mode in ['weighted','uniform']:
            data=lib.read(HERE/'data/sampling'/(case+'_'+mode+'.json'))
            for draw in data['draws']:
                lib.prefix(draw['prefix'],n,prods,draw['gate_limit']);prefixes+=1
        weighted=lib.read(HERE/'data/paired'/(case+'_weighted.json'))['draws']
        uniform=lib.read(HERE/'data/paired'/(case+'_uniform.json'))['draws']
        lib.require([(d['seed'],d['gate_limit'])for d in weighted]==[(d['seed'],d['gate_limit'])for d in uniform],
                    'Weighted/uniform paired seeds or caps changed')
    target,n,bank,prods=sources['5x5_U']
    for path in (HERE/'data/temperature').glob('*.json'):
        data=lib.read(path)
        for draw in data['draws']:
            lib.prefix(draw['prefix'],n,prods,draw['gate_limit']);prefixes+=1
            if draw['solution']is not None:lib.raw(draw['solution'],n,target);complete+=1
    k4=lib.read(HERE/'data/lookahead.json')['draws'];k4_complete=0
    for draw in k4:
        target,n,bank,prods=sources[draw['case']]
        for program in draw['prefixes']:
            raw=dict(dimension=n,additions=len(program['gates']),
                substitutions=[dict(i=a,ai=sa,j=b,aj=sb)for a,sa,b,sb in program['gates']],expressions=[])
            lib.prefix(raw,n,prods,draw['gate_limit']);prefixes+=1
        if draw['completion']['solution']is not None:
            lib.raw(draw['completion']['solution'],n,target);complete+=1;k4_complete+=1
    lib.require((paired_attempts,paired_complete,k4_complete)==(96,77,25),'Completion census changed')
    lib.raw(lib.read(HERE/'data/full_cli88.json'),25,sources['5x5_U'][0]);complete+=1
    for mode,expected in [('weighted',88),('uniform',90)]:
        count=lib.binary(lib.read(HERE/'data/target_walk'/(mode+'_best.json')),sources['5x5_U'][0])
        lib.require(count==expected,'Target-walk best changed')
    rows=list(csv.DictReader((HERE/'data/target_walk/draws.csv').open()))
    summary=lib.read(HERE/'data/target_walk/summary.json')
    lib.require(len(rows)==20000,'Target-walk sample census changed')
    for condition in summary['conditions']:
        histogram=dict(Counter(r['paid_gates']for r in rows if r['mode']==condition['mode']and r['status']=='complete'))
        lib.require(histogram==condition['success_size_distribution'],'Target-walk histogram changed')
    spec=importlib.util.spec_from_file_location('finite_upper',HERE/'finite_export/verify_upper.py')
    finite=importlib.util.module_from_spec(spec);spec.loader.exec_module(finite);finite.verify(HERE/'finite_export')
    for lane in ['cp_observed','cp_observed_repeat']:
        results=lib.read(HERE/'data/finite'/lane/'summary.json')
        lib.require(results[0]['bound']==87 and results[0]['status']=='INFEASIBLE','Observed solver result changed')
        lib.require(results[1]['selected_gates']==88,'Observed upper witness changed')
    return dict(status='PASS',paired_attempts=paired_attempts,paired_complete=paired_complete,
                raw_prefixes_checked=prefixes,complete_raw_maps_checked=complete,
                target_walk_rows=20000,finite_upper88_exact=True,
                independently_checked_unsat_proof=False,
                scope='Paid unit signed wires; no new strict count or global lower bound')


if __name__=='__main__':print(json.dumps(verify(),indent=2))
