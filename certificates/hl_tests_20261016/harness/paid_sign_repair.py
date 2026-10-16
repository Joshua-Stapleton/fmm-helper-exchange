#!/usr/bin/env python3
"""Pay for sign conflicts in a signed binary circuit, preserving a fixed map.

A bounded CP-SAT subproblem chooses signs for existing wires. Its objective
counts double-negative gates plus distinct incorrectly signed output aliases.
That orientation objective is not a global addition lower bound. The emitter
then pays every remaining sign correction, searches available literal wires
for one-addition realizations, and otherwise constructs a shared paid zero.
Final zero and duplicate wires are preserved rather than sign-normalized away.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time
from ortools.sat.python import cp_model


def matrix(path):
    text=path.read_text()
    if path.suffix=='.json':
        data=json.loads(text);return data.get('target_matrix',data) if isinstance(data,dict) else data
    lines=[x.strip() for x in text.splitlines() if x.strip() and not x.lstrip().startswith('#')]
    height,width,_=lines[0].split();height,width=int(height),int(width)
    result=[[0]*width for _ in range(height)]
    for line in lines[1:]:
        i,j,value=map(int,line.split())
        if (i,j,value)==(0,0,0):break
        assert 1<=i<=height and 1<=j<=width
        result[i-1][j-1]+=value
    return result


def replay(data):
    n=data['inputs'];values=[tuple(int(i==j) for j in range(n)) for i in range(n)]
    for k,(a,sa,b,sb) in enumerate(data['gates'],n):
        assert 0<=a<k and 0<=b<k and sa in(-1,1) and sb in(-1,1)
        values.append(tuple(sa*x+sb*y for x,y in zip(values[a],values[b])))
    return [list(s*v for v in values[w]) for w,s in data['outputs']]


def prune(n,gates,outputs,tags):
    live=set();pending=[w for w,_ in outputs]
    while pending:
        w=pending.pop()
        if w<n or w in live:continue
        live.add(w);a,_,b,_=gates[w-n];pending.extend([a,b])
    mapping={i:i for i in range(n)};kept=[];newtags=[]
    for old,gate in enumerate(gates,n):
        if old not in live:continue
        a,sa,b,sb=gate;mapping[old]=n+len(kept)
        kept.append([mapping[a],sa,mapping[b],sb]);newtags.append(tags[old-n])
    return kept,[[mapping[w],s] for w,s in outputs],newtags


def repair(source,target,seconds,seed):
    n=source['inputs'];assert replay(source)==target
    model=cp_model.CpModel();bits=[model.new_bool_var(f'negative_{i}') for i in range(n+len(source['gates']))]
    for x in bits[:n]:model.add(x==0)
    penalties=[]
    for k,(a,sa,b,sb) in enumerate(source['gates'],n):
        penalty=model.new_bool_var(f'paid_internal_{k}')
        table=[(z,x,y,int(sa*(-1)**(z+x)<0 and sb*(-1)**(z+y)<0)) for z,x,y in itertools.product((0,1),repeat=3)]
        model.add_allowed_assignments([bits[k],bits[a],bits[b],penalty],table);penalties.append(penalty)
    for w,s in sorted(set(map(tuple,source['outputs']))):
        penalty=model.new_bool_var(f'paid_output_{w}_{s}')
        if s<0:model.add(penalty+bits[w]==1)
        else:model.add(penalty==bits[w])
        penalties.append(penalty)
    model.minimize(sum(penalties))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds
    solver.parameters.num_search_workers=1;solver.parameters.random_seed=seed
    status=solver.solve(model)
    assert status in (cp_model.OPTIMAL,cp_model.FEASIBLE),solver.status_name(status)
    chosen=[solver.value(x) for x in bits]
    values=[tuple(int(i==j) for j in range(n)) for i in range(n)]
    available={v:i for i,v in enumerate(values)};gates=[];tags=[];mapped=list(range(n))
    counters=dict(existing_aliases=0,alternative_single_addition=0,shared_zero=0)
    def append(a,sa,b,sb,tag):
        assert sa==1 or sb==1
        if sa<0:a,b,sa,sb=b,a,sb,sa
        w=n+len(gates);gates.append([a,sa,b,sb]);tags.append(tag)
        v=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]));values.append(v)
        if v not in available:available[v]=w
        return w
    def known_or_one(v,tag):
        if v in available:counters['existing_aliases']+=1;return available[v]
        for a,u in enumerate(values):
            plus=tuple(x-y for x,y in zip(v,u))
            if plus in available:
                counters['alternative_single_addition']+=1
                return append(a,1,available[plus],1,tag)
            difference=tuple(x-y for x,y in zip(u,v))
            if difference in available:
                counters['alternative_single_addition']+=1
                return append(a,1,available[difference],-1,tag)
        return None
    def negative(a,tag):
        desired=tuple(-v for v in values[a]);found=known_or_one(desired,tag)
        if found is not None:return found
        zero=(0,)*n
        z=available.get(zero)
        if z is None:z=append(0,1,0,-1,'shared_zero');counters['shared_zero']+=1
        return append(z,1,a,-1,tag)
    for k,(a,sa,b,sb) in enumerate(source['gates'],n):
        aa=sa*(-1)**(chosen[k]+chosen[a]);bb=sb*(-1)**(chosen[k]+chosen[b])
        a,b=mapped[a],mapped[b]
        desired=tuple(aa*x+bb*y for x,y in zip(values[a],values[b]))
        if desired in available:w=available[desired];counters['existing_aliases']+=1
        elif aa>0 or bb>0:w=append(a,aa,b,bb,'base_gate')
        else:
            w=known_or_one(desired,'base_gate')
            if w is None:
                positive=append(a,1,b,1,'base_gate')
                w=negative(positive,'internal_sign_correction')
        mapped.append(w)
    outputs=[]
    for w,s in source['outputs']:
        literal=mapped[w]
        if s*(-1)**chosen[w]<0:literal=negative(literal,'output_sign_correction')
        outputs.append([literal,1])
    raw_gate_count=len(gates)
    raw_added_gates=sum(tag!='base_gate' for tag in tags)
    original_gate_elisions=len(source['gates'])-tags.count('base_gate')
    gates,outputs,tags=prune(n,gates,outputs,tags)
    result=dict(inputs=n,gates=gates,outputs=outputs,name='paid_literal_sign_repair',target_matrix=target,
        basis_change=False,preserve_paid_zero_and_alias_gates=True)
    assert replay(result)==target
    labels=lambda w:f'i{w}' if w<n else f't{w-n}'
    lines=[f't{k}:={labels(a)}'+('+' if sb==1 else '-')+f'{labels(b)};' for k,(a,sa,b,sb) in enumerate(gates)]
    assert all(sa==1 for a,sa,b,sb in gates)
    lines.extend(f'o{k}:={labels(w)};' for k,(w,s) in enumerate(outputs))
    return result,'\n'.join(lines)+'\n',dict(
        orientation_status=solver.status_name(status),orientation_solver_seconds=solver.wall_time,
        orientation_objective=solver.objective_value,orientation_bound=solver.best_objective_bound,
        orientation_scope='Fixed source DAG orientation penalty subproblem; not global circuit optimality',
        original_signed_additions=len(source['gates']),final_strict_additions=len(gates),
        paid_correction_additions=len(gates)-len(source['gates']),
        raw_added_gates=raw_added_gates,pruned_gate_count=raw_gate_count-len(gates),
        original_gate_elisions=original_gate_elisions,
        correction_gate_indices=[i for i,tag in enumerate(tags) if tag!='base_gate'],
        paid_output_correction_additions=tags.count('output_sign_correction'),
        paid_internal_correction_additions=tags.count('internal_sign_correction'),
        paid_zero_additions=tags.count('shared_zero'),net_addition_overhead=len(gates)-len(source['gates']),
        emitter_statistics=counters,gate_tags=tags)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,required=True);p.add_argument('--matrix',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=float,default=5)
    p.add_argument('--seed',type=int,default=46190000);args=p.parse_args()
    if not math.isfinite(args.seconds) or args.seconds<=0:p.error('--seconds must be positive and finite')
    if not 0<=args.seed<2**31:p.error('--seed must fit a nonnegative signed32-bit integer')
    started=time.monotonic();args.out.mkdir(exist_ok=False,parents=True)
    source=json.loads(args.candidate.read_text());target=matrix(args.matrix)
    candidate,text,report=repair(source,target,args.seconds,args.seed)
    (args.out/'best_candidate.json').write_text(json.dumps(candidate,indent=2)+'\n')
    (args.out/'best.slp').write_text(text)
    report.update(status='PASS',exact_original_ordered_map=True,basis_change=False,
        unary_negations=0,nonunit_scalars=0,unused_noninput_assignments=0,
        elapsed_seconds=time.monotonic()-started,included_in_primary_total=False,
        correction_method='Bounded minimum-penalty wire orientation; explicit paid signs; existing-wire differences before shared paid zero; dead gates pruned',
        original_candidate=str(args.candidate.resolve()),original_candidate_sha256=hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        matrix=str(args.matrix.resolve()),repair_code='harness/paid_sign_repair.py',
        command=[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],
        seed=args.seed,limits=dict(orientation_seconds=args.seconds,solver_threads=1),
        literal_sha256=hashlib.sha256(text.encode()).hexdigest())
    (args.out/'paid_sign_recovery.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='gate_tags'},indent=2))

if __name__=='__main__':main()
