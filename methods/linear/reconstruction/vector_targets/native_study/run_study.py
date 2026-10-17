#!/usr/bin/env python3
"""Frozen-incumbent, equal-budget native API experiments; local outputs only."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib, importlib.util, json, os, subprocess, time
from pathlib import Path

HERE=Path(__file__).resolve().parent; E=HERE.parent
PUB=E.parents[3]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
adapter=module('study_adapter',E/'toolchain/adapter.py')
common=module('study_common',PUB/'methods/linear/reconstruction/common.py')
def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def features(c):
    n=c['inputs'];values=[tuple(int(i==j) for j in range(n)) for i in range(n)];out=set()
    for a,sa,b,sb in c['gates']:
        v=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]));values.append(v)
        sign=next(1 if x>0 else -1 for x in v if x)
        out.add(tuple(sign*x for x in v))
    return out

def export_selection(circuits,cap=32):
    """Eight cheapest, then marginal new-form coverage divided by cost penalty."""
    ordered=sorted(circuits.items(),key=lambda x:(len(x[1]['gates']),x[0]))
    if len(ordered)<=cap:return ordered
    selected=ordered[:8];remaining=ordered[8:];covered=set()
    forms={key:features(c) for key,c in ordered}
    for key,c in selected:covered.update(forms[key])
    best=len(ordered[0][1]['gates'])
    while remaining and len(selected)<cap:
        bestidx=max(range(len(remaining)),key=lambda i:(
            len(forms[remaining[i][0]]-covered)/(1+len(remaining[i][1]['gates'])-best),
            -len(remaining[i][1]['gates']),remaining[i][0]))
        item=remaining.pop(bestidx);selected.append(item);covered.update(forms[item[0]])
    return selected

def run_one(job):
    case,arm,seed,bound,seconds,stage=job; folder=HERE/stage/case['id']/arm/f'seed_{seed}_bound_{bound}'
    folder.mkdir(parents=True,exist_ok=False);output=folder/'raw.jsonl';inputfile=folder/'input.txt'
    target=load(case['matrix']);incumbent=load(case['candidate']);adapter.write_input(inputfile,target,incumbent)
    mode='explicit' if arm in ('guided','balanced_random') else arm
    cmd=[str(E/'toolchain/native_driver_v2'),'--input',str(inputfile),'--mode',mode,'--seed',str(seed),'--draws','1000',
         '--seconds-per-draw','.25','--budget-seconds',str(seconds),'--jsonl','--output',str(output),'--ignore-unused-bound',str(bound),'--max-abs','1']
    selection=None
    if arm in ('guided','balanced_random'):
        suffix='guided' if arm=='guided' else 'random_controls'
        selection=E/'guidance/bank'/f"{case['id']}.{suffix}.csv";cmd.extend(['--removed-file',str(selection)])
    record=dict(case_id=case['id'],arm=arm,seed=seed,ignore_unused_bound=bool(bound),native_seconds=seconds,
        wrapper_timeout_seconds=seconds+2,command=cmd,incumbent_sha256=sha(case['candidate']),
        matrix_sha256=sha(case['matrix']),binary_sha256=sha(E/'toolchain/native_driver_v2'),
        selection_file=str(selection) if selection else None,selection_sha256=sha(selection) if selection else None,
        initial_signed_additions=case['local_signed_additions'],initial_max_abs_intermediate=case['max_abs_intermediate'],
        frozen_incumbent=True,workers=1)
    dump(folder/'command.json',record)
    start=time.monotonic();received=[];pending='';offset=0;killed=False
    with (folder/'stderr.txt').open('w') as err,(folder/'stdout.txt').open('w') as stdout:
        process=subprocess.Popen(cmd,stderr=err,stdout=stdout)
        while True:
            if output.exists():
                with output.open() as f:f.seek(offset);new=f.read();offset=f.tell()
                pending+=new
                while '\n' in pending:
                    line,pending=pending.split('\n',1)
                    if line.strip():
                        try:received.append((json.loads(line),time.monotonic()-start))
                        except json.JSONDecodeError:received.append((dict(event='malformed_complete_jsonl_record',raw=line),time.monotonic()-start))
            finished=process.poll() is not None
            if finished:
                # One final read captures bytes written between read and process exit.
                if output.exists():
                    with output.open() as f:f.seek(offset);pending+=f.read();offset=f.tell()
                    while '\n' in pending:
                        line,pending=pending.split('\n',1)
                        if line.strip():
                            try:received.append((json.loads(line),time.monotonic()-start))
                            except json.JSONDecodeError:received.append((dict(event='malformed_complete_jsonl_record',raw=line),time.monotonic()-start))
                break
            if time.monotonic()-start>seconds+2:
                process.kill();process.wait();killed=True;continue
            time.sleep(.005)
    native_wall=time.monotonic()-start
    stats=dict(**record,returncode=process.returncode,wrapper_killed=killed,process_wall_seconds=native_wall,
        complete_jsonl_records=len(received),ignored_partial_tail_bytes=len(pending.encode()),draws=0,completed=0,
        unsuccessful_or_bound=0,invalid=0,duplicates=0,raw_counts=[],normalized_counts=[],anytime=[],metadata=None,summary=None)
    circuits={};cache={};events=[];best=case['local_signed_additions'];validation_start=time.monotonic()
    for event,observed in received:
        if event.get('event')=='metadata':stats['metadata']=event;continue
        if event.get('event')=='summary':stats['summary']=event;continue
        if event.get('event')!='draw':stats['invalid']+=1;continue
        stats['draws']+=1;entry={k:v for k,v in event.items() if k!='solution'};entry['observed_wall_seconds']=observed
        if event.get('status')!='complete' or event.get('solution') is None:
            stats['unsuccessful_or_bound']+=1;events.append(entry);continue
        raw=event['solution']
        try:
            rawcost=adapter.replay(raw,target)
            assert rawcost==raw['additions']
            rawkey=digest(raw)
            if rawkey in cache:c=cache[rawkey]
            else:
                c=common.convert(raw,target);c['inputs']=len(target[0]);c=common.normalize(c);c['target_matrix']=target
                assert common.exact_circuit(c,c['inputs'])==target
                cache[rawkey]=c
            key=digest({k:c[k] for k in ('inputs','gates','outputs')})
            stats['completed']+=1;stats['raw_counts'].append(rawcost);stats['normalized_counts'].append(len(c['gates']))
            if key in circuits:stats['duplicates']+=1
            else:circuits[key]=c
            entry.update(status='EXACT_PASS',raw_additions=rawcost,signed_additions=len(c['gates']),candidate_hash=key)
            if len(c['gates'])<best:
                best=len(c['gates']);stats['anytime'].append(dict(observed_wall_seconds=observed,best_signed_additions=best,draw=stats['draws']))
        except Exception as exc:
            stats['invalid']+=1;entry.update(status='EXACT_REPLAY_FAILED',error=str(exc))
        events.append(entry)
    stats['validation_seconds']=time.monotonic()-validation_start;stats['distinct_signed_circuits']=len(circuits)
    stats['best_generated_signed_additions']=min((len(c['gates']) for c in circuits.values()),default=None)
    stats['best_with_incumbent_signed_additions']=best;stats['total_wall_seconds']=time.monotonic()-start
    stats['raw_solutions_path']=str(output);stats['received_timestamp_semantics']='Parent monotonic receipt time of each complete flushed JSONL line; may lag native completion by poll interval/output parse time.'
    dump(folder/'events.json',events);dump(folder/'stats.json',stats)
    return stats,circuits

def run_stage(stage,bound=1):
    bank=load(E/'benchmarks/manifest.json');cases=bank['cases'];started=time.monotonic()
    for c in cases:
        for k in ('matrix','original_matrix','candidate','native','donors','native_donors','strict_incumbent'):
            c[k]=str(E/c[k])
    if stage=='pilot':
        cases=[c for c in cases if c['id'] in ('hl_3x4x7_V','hl_5x7x7_V')]
        jobs=[(c,a,1701701,b,3,stage) for c in cases for b in (0,1) for a in ('helpers','vectors')]
    else:
        jobs=[(c,a,s,bound,6,stage) for c in cases for a in ('helpers','vectors','mixed','guided','balanced_random') for s in (1701701,1702701)]
    root=HERE/stage;root.mkdir(exist_ok=False);protocol=dict(stage=stage,cases=[c['id'] for c in cases],
        jobs=len(jobs),max_concurrent_native_workers=3,bound_flag=bound if stage!='pilot' else [0,1],
        worker_threads_per_call=1,per_draw_seconds=.25,attempt_cap=1000,initialization='Same frozen current best for every arm and seed; never updated within study.',
        scope='Native signed discovery only; no pooling, orientation or strict record claim. Exact current original-map literal certificates remain incumbent.',
        exports='Keep all raw completed solutions in JSONL. Per-arm export cap32: eight cheapest distinct normalized DAGs, then maximize new canonical helper-form coverage/(1+cost-bestcost), deterministic hash tie-break.',
        source_metadata=load(E/'toolchain/native_driver_v2.build.json'),
        benchmark_manifest_sha256=sha(E/'benchmarks/manifest.json'),guidance_manifest_sha256=sha(E/'guidance/bank/manifest.json'))
    dump(root/'protocol.json',protocol);results=[];collected={}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futuremap={executor.submit(run_one,job):job for job in jobs}
        for future in as_completed(futuremap):
            job=futuremap[future]
            try:stats,circuits=future.result()
            except Exception as exc:
                stats=dict(case_id=job[0]['id'],arm=job[1],seed=job[2],ignore_unused_bound=bool(job[3]),status='WRAPPER_EXCEPTION',error=str(exc));circuits={}
            results.append(stats)
            key=(stats['case_id'],stats['arm'],stats.get('ignore_unused_bound'))
            collected.setdefault(key,{}).update(circuits)
            dump(root/'progress.json',dict(finished=len(results),jobs=len(jobs),wall_seconds=time.monotonic()-started,results=results))
            print(json.dumps({k:stats.get(k) for k in ('case_id','arm','seed','ignore_unused_bound','draws','completed','best_generated_signed_additions','process_wall_seconds','invalid','status')}),flush=True)
    guidance={c['case_id']:c for c in load(E/'guidance/bank/manifest.json')['cases']};exports=[]
    for (cid,arm,flag),circuits in collected.items():
        out=root/cid/arm/(f'bound_{int(flag)}_export' if stage=='pilot' else 'export');out.mkdir(parents=True,exist_ok=True)
        selected=export_selection(circuits);c=next(c for c in cases if c['id']==cid)
        dump(out/'donors.json',dict(inputs=c['inputs'],circuits=[dict(v,name=f'{arm}_{k[:12]}') for k,v in selected]))
        entry=dict(case_id=cid,arm=arm,ignore_unused_bound=flag,uncapped_distinct_circuits=len(circuits),exported=len(selected),donors=str(out/'donors.json'),
            selector_seconds=guidance[cid]['selector_wall_seconds'] if arm=='guided' else 0,
            selector_time_scope='Guided schedule preparation is shared across both seeds; add once to total arm end-to-end time. Native run budgets exclude it.',
            counts=[len(v['gates']) for k,v in selected],hashes=[k for k,v in selected])
        dump(out/'manifest.json',entry);exports.append(entry)
    report=dict(status='COMPLETE',stage=stage,wall_seconds=time.monotonic()-started,results=results,exports=exports,
        exact_validation_failures=sum(r.get('invalid',0) for r in results),raw_solution_retention='Every complete flushed JSONL record retained; partial records never admitted.')
    dump(root/'report.json',report)
    print(json.dumps(dict(stage=stage,wall_seconds=report['wall_seconds'],jobs=len(results),invalid=report['exact_validation_failures'])),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',choices=['pilot','main'],required=True);p.add_argument('--ignore-unused-bound',type=int,choices=[0,1],default=1);a=p.parse_args()
    run_stage(a.stage,a.ignore_unused_bound)
