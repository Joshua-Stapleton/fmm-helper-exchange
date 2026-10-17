#!/usr/bin/env python3
"""Exact canonical-form and production provenance for a pooled witness."""
import argparse
import hashlib
from itertools import combinations
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
E=HERE.parent
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):
    s=next(1 if x>0 else -1 for x in v if x)
    return tuple(s*x for x in v),s

def evaluate(c,n):
    values=[tuple(int(i==j) for j in range(n)) for i in range(n)];productions=[]
    for a,sa,b,sb in c['gates']:
        value=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]));out,so=canonical(value);left,sl=canonical(values[a]);right,sr=canonical(values[b]);values.append(value)
        productions.append((out,tuple(sorted(((left,so*sa*sl),(right,so*sb*sr))))))
    return values,{canonical(v)[0] for v in values},productions

def run(case='old_3x6x8_V',arm='vectors'):
    candidate_path=HERE/'results'/case/arm/'candidate.json';candidate=load(candidate_path);n=candidate['inputs'];target={canonical(v)[0] for v in candidate['target_matrix'] if any(v)}
    base_path=E/'benchmarks'/case/'donors.json';new_path=E/'native_study/main'/case/arm/'export/donors.json'
    base=load(base_path)['circuits'];new=load(new_path)['circuits']
    frozen_forms=set();frozen_productions=set();new_forms=set();new_productions=set();donors=[]
    for i,c in enumerate(base):
        _,f,p=evaluate(c,n);frozen_forms|=f;frozen_productions.update(p)
    for i,c in enumerate(new):
        _,f,p=evaluate(c,n);new_forms|=f;new_productions.update(p);donors.append(dict(index=i,name=c.get('name',str(i)),forms=f,gates=len(c['gates'])))
    values,forms,productions=evaluate(candidate,n)
    helper_forms={canonical(v)[0] for v in values[n:] if sum(bool(x) for x in v)>=2 and canonical(v)[0] not in target}
    novel=helper_forms-frozen_forms;union=frozen_forms|new_forms
    assert not (forms-union),'Witness contains a form outside its exact pool'
    incidence={v:[d['index'] for d in donors if v in d['forms']] for v in sorted(novel)}
    exclusive={ids[0] for ids in incidence.values() if len(ids)==1}
    unique_forms=[dict(coefficients=list(v),used_by_donors=ids) for v,ids in incidence.items()]
    # Exact finite set cover over novel witness forms, not an SLP lower bound.
    ordered=sorted(novel);full=(1<<len(ordered))-1
    masks=[sum(1<<i for i,v in enumerate(ordered) if v in d['forms']) for d in donors]
    cover=[] if not novel else None
    if len(ordered)<=20:
        dp={0:()}
        for index,mask in enumerate(masks):
            if not mask:continue
            for state,ids in list(dp.items()):
                dest=state|mask;proposed=ids+(index,)
                if dest not in dp or (len(proposed),proposed)<(len(dp[dest]),dp[dest]):dp[dest]=proposed
        cover=list(dp[full]) if full in dp else None
    gates=[];consumers={i:[] for i in range(len(values))}
    for j,(a,sa,b,sb) in enumerate(candidate['gates']):
        wire=n+j;consumers[a].append(wire);consumers[b].append(wire);form=canonical(values[wire])[0]
        gates.append(dict(gate_index=j,wire=wire,parents=[a,b],parent_signs=[sa,sb],canonical_form=list(form),
                          auxiliary=form in helper_forms,form_absent_frozen_bank=form not in frozen_forms,
                          production_absent_all_donors=productions[j] not in frozen_productions|new_productions,
                          production_absent_frozen_bank=productions[j] not in frozen_productions,
                          new_donors_with_form=[d['index'] for d in donors if form in d['forms']]))
    for g in gates:g['consumers']=consumers[g['wire']]
    choices=[g for g in gates if g['form_absent_frozen_bank'] and g['auxiliary']]
    choices.sort(key=lambda g:(-len(g['consumers']),not g['production_absent_all_donors'],g['wire']))
    local=[]
    if choices:
        center=choices[0];wires={center['wire'],*center['parents'],*center['consumers']}
        local=[g for g in gates if g['wire'] in wires]
    result=dict(case_id=case,arm=arm,candidate=str(candidate_path),candidate_sha256=sha(candidate_path),
                frozen_bank=str(base_path),frozen_bank_sha256=sha(base_path),new_bank=str(new_path),new_bank_sha256=sha(new_path),
                additions=len(candidate['gates']),inputs=n,frozen_donor_count=len(base),new_exported_donor_count=len(new),
                helper_forms=len(helper_forms),helpers_absent_entire_frozen_bank=len(novel),
                witness_gate_forms_absent_frozen=sum(g['form_absent_frozen_bank'] for g in gates),
                witness_productions_absent_frozen=sum(g['production_absent_frozen_bank'] for g in gates),
                witness_productions_absent_all_supplied_donors=sum(g['production_absent_all_donors'] for g in gates),
                donor_indices_with_exclusive_new_witness_forms=sorted(exclusive),
                minimum_cover_exact_if_found=cover is not None,minimum_new_donor_cover=cover,cover_search='Exact dynamic programming over novel-form coverage masks for at most20 novel forms; this covers witness forms only, not alternative circuits.',
                donor_incidence=[dict(index=d['index'],name=d['name'],gates=d['gates'],witness_helpers=len(d['forms']&helper_forms),new_witness_helpers=len(d['forms']&novel),exclusive_new_witness_helpers=sum(ids==[d['index']] for ids in incidence.values())) for d in donors],
                novel_helpers=unique_forms,local_trace=local,gates=gates,
                pool_timing=load(HERE/'results'/case/arm/'result.json'),
                scope='Exact finite-bank provenance only. Absence from this bank does not prove a lower count impossible using other constructions or schemes.')
    out=HERE/(case+'_'+arm+'_provenance.json');out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['gates','novel_helpers','donor_incidence','pool_timing','local_trace']},indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',default='old_3x6x8_V');p.add_argument('--arm',default='vectors');a=p.parse_args();run(a.case,a.arm)
