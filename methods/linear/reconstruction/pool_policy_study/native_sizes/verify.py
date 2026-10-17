#!/usr/bin/env python3
"""Verify packaged maps, donors, native samples and form provenance; no search."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(p):return json.loads(Path(p).read_text())


def binary(c,target):
    n=c['inputs'];assert type(n) is int and n>0
    values=[tuple(int(i==j) for j in range(n)) for i in range(n)]
    forms=set(values)
    for g in c['gates']:
        assert len(g)==4
        a,sa,b,sb=g
        assert all(type(x) is int for x in g)
        assert 0<=a<len(values) and 0<=b<len(values) and sa in (-1,1) and sb in (-1,1)
        v=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]));values.append(v)
        first=next((x for x in v if x),0)
        if first:forms.add(v if first>0 else tuple(-x for x in v))
    actual=[]
    for wire,sign in c['outputs']:
        assert type(wire) is int and 0<=wire<len(values) and sign in (-1,1)
        actual.append([sign*x for x in values[wire]])
    assert actual==target
    return len(c['gates']),forms


def native(s,target):
    n=s['dimension'];values=[[int(i==j) for j in range(n)] for i in range(n)]
    for g in s['substitutions']:
        a,b,sa,sb=(g[k] for k in ('i','j','ai','aj'))
        assert all(type(x) is int for x in (a,b,sa,sb))
        assert 0<=a<len(values) and 0<=b<len(values) and sa in (-1,1) and sb in (-1,1)
        values.append([sa*x+sb*y for x,y in zip(values[a],values[b])])
    actual=[];cost=len(s['substitutions'])
    for expression in s['expressions']:
        row=[0]*n
        for t in expression:
            i,sign=t['index'],t['value']
            assert type(i) is int and 0<=i<len(values) and sign in (-1,1)
            row=[x+sign*y for x,y in zip(row,values[i])]
        actual.append(row);cost+=max(0,len(expression)-1)
    assert actual==target and cost==s['additions']
    return cost


def main():
    for line in (HERE/'SHA256SUMS').read_text().splitlines():
        h,name=line.split('  ',1)
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==h,name
    manifest=load(HERE/'data/manifest.json');cases={c['id']:c for c in manifest['cases']}
    pool=load(HERE/'observed/pooling_summary.json')
    prior_forms={};export_forms={};candidate_forms={};donors=0;candidates=0
    for cid,c in cases.items():
        target=load(HERE/c['matrix'])
        initial=load(HERE/c['initial'])
        cost,forms=binary(initial,target)
        assert cost==c['initial_additions']
        assert all(sign==1 for wire,sign in initial['outputs'])
        assert all(sa==1 or sb==1 for a,sa,b,sb in initial['gates'])
        prior_forms[cid]=set()
        for donor in load(HERE/c['prior'])['circuits']:
            cost,forms=binary(donor,target);prior_forms[cid].update(forms);donors+=1
        for arm,path in c['exports'].items():
            fs=set()
            bank=load(HERE/path)
            assert len(bank['circuits'])==32
            for donor in bank['circuits']:
                cost,forms=binary(donor,target);fs.update(forms);donors+=1
            export_forms[cid,arm]=fs
        for arm,path in c['candidates'].items():
            cost,forms=binary(load(HERE/path),target)
            observed=next(r for r in pool['results'] if r['case_id']==cid and r['arm']==arm)
            assert cost==observed['best_signed_additions']
            candidate_forms[cid,arm]=forms;candidates+=1
    samples=load(HERE/'data/native_samples.json')
    assert len(samples)==40
    for sample in samples:
        target=load(HERE/cases[sample['case_id']]['matrix'])
        e=sample['draw'];assert e['status']=='complete'
        native(e['solution'],target)
        lo,hi=next((lo,hi) for arm,lo,hi in manifest['arms'] if arm==sample['arm'])
        k=len(e['removed_helper_indices'])
        assert len(set(e['removed_helper_indices']))==k and lo<=k<=hi
    for f in load(HERE/'observed/form_provenance.json')['findings']:
        cid=f['case_id']
        novel=candidate_forms[cid,'with_new_native_donors']-prior_forms[cid]
        recorded={tuple(row['coefficients']) for row in f['new_forms']}
        assert novel==recorded and len(novel)==f['final_new_to_old_pool']
        for row in f['new_forms']:
            v=tuple(row['coefficients'])
            actual={arm for arm,lo,hi in manifest['arms'] if v in export_forms[cid,arm]}
            assert actual==set(row['source_arms'])
    result=dict(status='PASS',fixed_maps=len(cases),incumbents=len(cases),
                bounded_donors=donors,signed_candidates=candidates,native_representative_completions=len(samples),
                provenance_findings=2,
                scope='Independent integer replay of packaged evidence only. Full local2357-completion audit is an observed report; full raw dumps intentionally omitted. Strict final record certificates live separately.')
    print(json.dumps(result))


if __name__=='__main__':main()
