#!/usr/bin/env python3
"""Independent replay of source chains, all pilot completions and strict bests."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'certificates/tests_archive_20261009'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

literal=load('verify_literal');signed=load('verify_signed')

def read(path):return json.loads(path.read_text())

def check():
    for name,digest in read(HERE/'SHA256.json').items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,name
    reports=[]
    for arm in ('toy','single','mixed'):
        source=read(HERE/('toy_donors.json' if arm=='toy' else 'source_donors.json'))
        matrix,_=literal.read_sms(HERE/('toy.sms' if arm=='toy' else '2x4x7_V.sms'))
        n=source['inputs'];forms=set()
        for donor in source['circuits']:
            actual,_,values=signed.replay(dict(donor,inputs=n),n)
            assert actual==matrix
            forms.update(signed.canonical(x)[0] for x in values)
        data=read(HERE/arm/'donors.json');records=read(HERE/arm/'records.json')
        starts=read(HERE/arm/'starts.json');assert len(data['circuits'])==len(records)==len(starts)
        assert len(records)==(1 if arm=='toy' else 30)
        for donor,row,prefix in zip(data['circuits'],records,starts):
            actual,count,_=signed.replay(dict(donor,inputs=n),n)
            assert actual==matrix and count==row['additions_signed'] and row['status']=='PASS'
            assert prefix['inputs']==n and len(prefix['gates'])==prefix['initial_additions']==row['initial_additions']
            partial=dict(inputs=n,gates=prefix['gates'],outputs=[[n+i,1] for i in range(len(prefix['gates']))])
            _,_,values=signed.replay(partial,n)
            assert all(signed.canonical(x)[0] in forms for x in values)
            assert len({signed.canonical(x)[0] for x in values})==len(values)
            assert prefix['contributing_donors']==row['contributing_donors']==({'toy':2,'single':1,'mixed':3}[arm])
        actual,counts=literal.replay((HERE/arm/'best.slp').read_text(),n)
        expected=4 if arm=='toy' else 67
        assert actual==matrix and counts['binary_additions']==expected
        assert counts['unary_negations']==counts['nonunit_scalars']==counts['unused_noninput_assignments']==0
        actual,count,_=signed.replay(read(HERE/arm/'best_candidate.json'),n)
        assert actual==matrix and count==expected
        assert min(r['additions_signed'] for r in records)==expected
        reports.append(dict(arm=arm,completed_circuits=len(records),strict_best=expected,exact_coefficients=len(matrix)*n))
    return dict(status='PASS',source_and_initial_chains_replayed=True,arms=reports,no_new_real_map_bound=True)

if __name__=='__main__':print(json.dumps(check(),indent=2))
