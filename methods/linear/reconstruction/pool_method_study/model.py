#!/usr/bin/env python3
"""Bounded exact CP-SAT feasibility for one immutable signed-form pool."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from ortools.sat.python import cp_model

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('study_lib',HERE/'lib.py')
lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)

def prune(data):
    n=data['inputs'];needed=set();pending=[w for w,s in data['outputs']]
    while pending:
        wire=pending.pop()
        if wire<n or wire in needed:continue
        needed.add(wire);a,sa,b,sb=data['gates'][wire-n];pending.extend((a,b))
    remap={i:i for i in range(n)};gates=[]
    for wire in sorted(needed):
        a,sa,b,sb=data['gates'][wire-n];remap[wire]=n+len(gates)
        gates.append([remap[a],sa,remap[b],sb])
    return dict(inputs=n,gates=gates,outputs=[[remap[w],s]for w,s in data['outputs']])


def solve(path,out,bound,seconds,seed):
    data=json.loads(path.read_text());n=data['inputs'];forms=data['forms'];total=len(forms)
    assert len(set(map(tuple,forms)))==total
    assert forms[:n]==[[int(i==j)for j in range(n)]for i in range(n)]
    model=cp_model.CpModel();used={i:model.new_bool_var('u'+str(i))for i in range(n,total)}
    ranks={i:model.new_int_var(0,total-n,'r'+str(i))for i in range(n,total)}
    selected={};selection_vars=[]
    for i in range(n,total):
        model.add(ranks[i]>=1).only_enforce_if(used[i])
        model.add(ranks[i]==0).only_enforce_if(used[i].Not())
        options=data['productions'][str(i)];variables=[]
        for k,(a,sa,b,sb)in enumerate(options):
            assert i not in (a,b) and 0<=a<=b<total and sa in (-1,1) and sb in (-1,1)
            assert [sa*x+sb*y for x,y in zip(forms[a],forms[b])]==forms[i]
            choose=model.new_bool_var(f'p{i}_{k}');selected[(i,k)]=choose;selection_vars.append(choose);variables.append(choose)
            for parent in (a,b):
                if parent>=n:
                    model.add_implication(choose,used[parent]);model.add(ranks[parent]<ranks[i]).only_enforce_if(choose)
                else:model.add(ranks[i]>0).only_enforce_if(choose)
        model.add(sum(variables)==used[i])
    target_ids=set(i for i,_ in data['outputs'])
    for i in target_ids:
        if i>=n:model.add(used[i]==1)
    model.add(sum(used.values())<=bound)
    # An 88-gate hint is used only for the feasible88 control, never for87.
    hint=data['incumbent'];hint_used=set(map(int,hint))
    if len(hint)<=bound:
        hint_rank={i:0 for i in range(n)}
        pending=set(hint_used)
        while pending:
            progress=False
            for i in list(pending):
                a,_,b,_=hint[str(i)]
                if a in hint_rank and b in hint_rank:
                    hint_rank[i]=1+max(hint_rank[a],hint_rank[b]);pending.remove(i);progress=True
            assert progress,'Hint cycle'
        for i in used:
            model.add_hint(used[i],i in hint_used);model.add_hint(ranks[i],hint_rank.get(i,0))
        for(i,k),variable in selected.items():model.add_hint(variable,str(i)in hint and data['productions'][str(i)][k]==hint[str(i)])
    model_path=out/f'bound{bound}.model.pb';model.export_to_file(str(model_path))
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.max_time_in_seconds=seconds
    solver.parameters.random_seed=seed;start=time.monotonic();status=solver.solve(model)
    record=dict(bound=bound,seconds_allowance=seconds,seed=seed,workers=1,status=solver.status_name(status),
                elapsed_seconds=time.monotonic()-start,solver_wall_seconds=solver.wall_time,
                branches=solver.num_branches,conflicts=solver.num_conflicts,pool_sha256=lib.digest(path),
                model_sha256=lib.digest(model_path),variables=len(used)+len(ranks)+len(selected),
                productions=len(selected),forms=total,target_nonroots=sum(i>=n for i in target_ids),
                scope='Finite fixed signed-unit production pool only; no global SLP lower bound')
    if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        chosen={i:k for(i,k),variable in selected.items()if solver.value(variable)}
        wires={i:i for i in range(n)};gates=[]
        for i in sorted(chosen,key=lambda i:(solver.value(ranks[i]),i)):
            a,sa,b,sb=data['productions'][str(i)][chosen[i]]
            assert a in wires and b in wires
            wires[i]=n+len(gates);gates.append([wires[a],sa,wires[b],sb])
        candidate=dict(inputs=n,gates=gates,outputs=[[wires[i],sign]for i,sign in data['outputs']])
        assert lib.binary(candidate,data['target_matrix'])<=bound
        raw_candidate=candidate;candidate=prune(candidate)
        assert lib.binary(candidate,data['target_matrix'])<=bound
        (out/f'bound{bound}.model_candidate.json').write_text(json.dumps(raw_candidate,indent=2)+'\n')
        (out/f'bound{bound}.candidate.json').write_text(json.dumps(dict(candidate,target_matrix=data['target_matrix']),indent=2)+'\n')
        record.update(selected_gates=len(gates),pruned_exact_signed_gates=len(candidate['gates']),
                      candidate_sha256=lib.digest(out/f'bound{bound}.candidate.json'),exact_map_verified=True,
                      strict_sign_orientation='Not performed; signed upper bound only')
    (out/f'bound{bound}.result.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pool',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds87',type=float,default=20)
    p.add_argument('--seconds88',type=float,default=2);p.add_argument('--seed',type=int,default=11115001)
    args=p.parse_args();assert 0<args.seconds87<=60 and 0<args.seconds88<=60
    assert 0<=args.seed<2**31
    args.out.mkdir(exist_ok=False)
    records=[solve(args.pool,args.out,87,args.seconds87,args.seed),solve(args.pool,args.out,88,args.seconds88,args.seed)]
    (args.out/'summary.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records,indent=2))


if __name__=='__main__':main()
