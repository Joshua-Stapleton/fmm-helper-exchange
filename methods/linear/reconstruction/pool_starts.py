#!/usr/bin/env python3
"""Assemble paid, acyclic mixed-donor partial circuits before LEO completion."""
import argparse
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import time

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pooled_start_common',HERE/'common.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)


def bank(source):
    n=source['inputs'];profiles=[];target=None;seen=set()
    for entry in source['circuits']:
        data=api.normalize(dict(entry,inputs=n));actual=api.exact_circuit(data,n)
        if target is None:target=actual
        api.require(actual==target,'Donors must compute the same ordered signed map')
        key=json.dumps([data['gates'],data['outputs']],separators=(',',':'))
        if key in seen:continue
        seen.add(key)
        values=[tuple(int(i==j) for j in range(n)) for i in range(n)]
        uses=[0]*(n+len(data['gates']))
        for a,sa,b,sb in data['gates']:
            values.append(tuple(sa*x+sb*y for x,y in zip(values[a],values[b])))
            uses[a]+=1;uses[b]+=1
        for wire,_ in data['outputs']:uses[wire]+=1
        profiles.append(dict(gates=data['gates'],values=values,uses=uses,
                             name=entry.get('name',f'donor-{len(profiles)}')))
    api.require(profiles,'At least one nonzero donor required')
    api.matrix_check(target)
    return n,target,profiles


def closure(profile,wire,known,n):
    needed=set();pending=[wire]
    while pending:
        value=pending.pop()
        if value<n or value in needed or api.canonical(profile['values'][value])[0] in known:continue
        needed.add(value);a,_,b,_=profile['gates'][value-n];pending.extend((a,b))
    return sorted(needed)


def append_chain(profile,needed,known,gates,values,n):
    added=0
    for wire in needed:
        vector=profile['values'][wire];form,orientation=api.canonical(vector)
        if form in known:continue
        a,sa,b,sb=profile['gates'][wire-n]
        af,asign=api.canonical(profile['values'][a]);bf,bsign=api.canonical(profile['values'][b])
        left,right=known[af],known[bf]
        gate=[left,sa*asign*orientation,right,sb*bsign*orientation]
        actual=tuple(gate[1]*x+gate[3]*y for x,y in zip(values[left],values[right]))
        api.require(actual==form,'Chain import changed an exact coefficient vector')
        known[form]=n+len(gates);gates.append(gate);values.append(form);added+=1
    return added


def sample_start(n,target,profiles,seed,budget,sources=3):
    api.require(budget>0 and sources>0,'Positive budget and source count required')
    generator=random.Random(seed);selected=generator.sample(range(len(profiles)),min(sources,len(profiles)))
    values=[tuple(int(i==j) for j in range(n)) for i in range(n)]
    known={value:i for i,value in enumerate(values)};gates=[];contributions={};choices_log=[]
    while len(gates)<budget:
        remaining=budget-len(gates);missing=[i for i in selected if i not in contributions]
        source_ids=missing[:1] if missing else selected
        cap=max(1,remaining//len(missing)) if missing else remaining
        choices=[]
        for donor in source_ids:
            profile=profiles[donor]
            for wire in range(n,n+len(profile['gates'])):
                needed=closure(profile,wire,known,n)
                if 0<len(needed)<=cap:
                    choices.append((donor,wire,needed,max(1,profile['uses'][wire])/len(needed)))
        if not choices:
            if missing:
                selected.remove(missing[0])
                if not selected:break
                continue
            break
        donor,wire,needed,_=generator.choices(choices,weights=[x[3] for x in choices],k=1)[0]
        added=append_chain(profiles[donor],needed,known,gates,values,n)
        contributions[donor]=contributions.get(donor,0)+added
        choices_log.append(dict(donor=donor,endpoint=wire,added_gates=added))
    target_forms={api.canonical(row)[0] for row in target}
    result=dict(inputs=n,gates=gates,initial_additions=len(gates),
                contributing_donors=len(contributions),contributions=contributions,
                covered_target_forms=len(target_forms&set(known)),chain_choices=choices_log)
    # Check every computed form from the original n roots; no helper is a free input.
    if gates:
        audit=dict(inputs=n,gates=gates,outputs=[[n+i,1] for i in range(len(gates))])
        api.require(api.exact_circuit(audit,n)==[list(x) for x in values[n:]],'Partial circuit replay failed')
    return result


def run(args):
    api.finite(args.seconds,'Time budget');api.finite(args.timeout,'Repair timeout')
    api.require(args.attempts>0 and args.gates>0 and args.sources>0,'Positive sampling parameters required')
    api.require(0<=args.seed<2**32 and args.seed+args.attempts<=2**32,'Invalid seed range')
    api.require(api.math.isfinite(args.savings) and args.savings>=0 and args.slack>=-1,
                'Invalid scorer parameters')
    n,target,profiles=bank(api.json_read(args.donors));args.out.mkdir(parents=True,exist_ok=False)
    driver,build=api.binary(args,args.out,'repair');start=time.monotonic();records=[];donors=[];best=None
    for attempt in range(args.attempts):
        if time.monotonic()-start>=args.seconds:break
        seed=args.seed+attempt;t=time.monotonic();prefix=sample_start(n,target,profiles,seed,args.gates,args.sources)
        partial=args.out/f'start_{attempt:03d}.txt';raw=args.out/f'solution_{attempt:03d}.json'
        api.write_partial(partial,target,prefix['gates']);api.dump(partial.with_suffix('.partial.json'),prefix)
        row=dict(attempt=attempt,seed=seed,initial_additions=prefix['initial_additions'],
                 contributing_donors=prefix['contributing_donors'],covered_target_forms=prefix['covered_target_forms'],
                 assembly_seconds=time.monotonic()-t)
        try:
            remaining=args.seconds-(time.monotonic()-start)
            if remaining<=0:break
            process=subprocess.run([str(driver),str(partial),str(raw),str(seed),str(args.savings),
                                    str(args.slack),'1',str(max(abs(x) for r in target for x in r))],
                                   capture_output=True,text=True,timeout=min(args.timeout,remaining))
            api.require(process.returncode==0,process.stderr.strip())
            donor=api.convert(api.json_read(raw),target);donor['name']=f'pooled-start-{seed}';donors.append(donor)
            count=len(donor['gates']);row.update(status='PASS',additions_signed=count,exact_map_verified=True)
            if best is None or count<best:
                best=count;api.save_candidate(args.out/'best_candidate.json',donor,target)
        except subprocess.TimeoutExpired:row['status']='TIMEOUT'
        except ValueError as error:row.update(status='ERROR',diagnostic=str(error))
        row['seconds']=time.monotonic()-t;records.append(row)
        api.dump(args.out/'records.json',records)
    api.dump(args.out/'donors.json',dict(inputs=n,circuits=donors))
    report=dict(status='COMPLETED_BUDGET',source_entries=len(api.json_read(args.donors)['circuits']),
                unique_donors=len(profiles),sources_per_start=args.sources,initial_gate_budget=args.gates,
                attempts=len(records),accepted=len(donors),best_signed=best,elapsed_seconds=time.monotonic()-start,
                build=build,scope='Paid partial circuits; generic signed counts require final strict orientation')
    api.dump(args.out/'summary.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--donors',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--leo',type=Path);p.add_argument('--binary',type=Path)
    p.add_argument('--compiler');p.add_argument('--sources',type=int,default=3);p.add_argument('--gates',type=int,default=20)
    p.add_argument('--attempts',type=int,default=40);p.add_argument('--seconds',type=float,default=30)
    p.add_argument('--timeout',type=float,default=3);p.add_argument('--seed',type=int,default=4000)
    p.add_argument('--savings',type=float,default=.01);p.add_argument('--slack',type=int,default=4)
    print(json.dumps(run(p.parse_args()),indent=2))
