#!/usr/bin/env python3
"""Standalone exact nineteen-scheme certificate verifier; Python standard library only."""
from pathlib import Path
from fractions import Fraction as Q
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from verify_literal import read_sms, replay
from verify_tensor import verify as verify_tensor
from verify_signed import replay as replay_signed


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expand(data,factor):
    n,m,k=data['n']
    width={'U':n*m,'V':m*k,'W':data['m']}[factor]
    values=[[Q(i==j) for j in range(width)] for i in range(width)]
    raw_additions=0
    def expression(terms):
        assert isinstance(terms,list) and terms
        result=[Q(0)]*width
        seen=set()
        for term in terms:
            assert set(term)=={'index','value'}
            index=term['index']
            assert isinstance(index,int) and not isinstance(index,bool)
            assert 0<=index<len(values) and index not in seen
            seen.add(index)
            coefficient=Q(term['value'])
            assert coefficient in (-1,1)
            for j,value in enumerate(values[index]):
                result[j]+=coefficient*value
        return result
    for terms in data[factor.lower()+'_fresh']:
        values.append(expression(terms)); raw_additions+=len(terms)-1
    outputs=[]
    for terms in data[factor.lower()]:
        outputs.append(expression(terms)); raw_additions+=len(terms)-1
    return outputs,raw_additions


def verify():
    manifest=json.loads((HERE/'MANIFEST.json').read_text())
    assert manifest and isinstance(manifest,dict)
    files={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.name!='MANIFEST.json'}
    assert files==set(manifest), 'Certificate files differ from manifest'
    for name,expected in manifest.items():
        path=HERE/name
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert sha(path)==expected,'File SHA256 mismatch: '+name
    claims=json.loads((HERE/'claims.json').read_text())
    assert claims['basis_change'] is False
    assert len(claims['schemes'])==19
    results=[]
    for item in claims['schemes']:
        folder=HERE/item['directory']
        source=json.loads((folder/'source.json').read_text())
        assert source['z2'] is False and source['n']==item['dimensions'] and source['m']==item['products']
        assert sha(folder/'source.json')==item['source_json_sha256']
        counts={}
        baseline={}
        for factor in ('U','V','W'):
            matrix,matrix_sha=read_sms(folder/(factor+'.sms'))
            assert matrix_sha==item['source_matrix_sha256'][factor]
            source_matrix,baseline[factor]=expand(source,factor)
            assert source_matrix==matrix,'Published source expansion differs from uploaded '+factor
            actual,stats=replay((folder/(factor+'.slp')).read_text(),len(matrix[0]))
            assert actual==matrix,'Final literal program differs from fixed signed '+factor
            assert all(stats[key]==0 for key in ('unary_negations','nonunit_scalars','unused_noninput_assignments'))
            counts[factor]=stats['binary_additions']
            assert counts[factor]==item['phase_counts'][factor]
            candidate_path=folder/(factor+'.json')
            if candidate_path.exists():
                candidate_actual,candidate_additions,_=replay_signed(json.loads(candidate_path.read_text()),len(matrix[0]))
                assert candidate_actual==matrix and candidate_additions==counts[factor]
        assert baseline==item['historical_phase_counts']
        assert sum(baseline.values())==source['complexity']['reduced']==item['historical_additions']
        additions=sum(counts.values())
        assert additions==item['final_additions']
        assert additions+source['m']==item['total_scalar_operations']
        assert item['historical_additions']-additions==item['saved_additions']
        if 'previous_published_additions' in item:
            assert item['previous_published_additions']-additions==item['saved_since_previous_publication']
        tensor=verify_tensor(folder/'U.sms',folder/'V.sms',folder/'W.sms',*source['n'])
        results.append(dict(dimensions=source['n'],products=source['m'],counts=counts,
                            additions=additions,total_scalar_operations=additions+source['m'],
                            saved_additions=item['saved_additions'],tensor=tensor,status='PASS'))
    return dict(status='PASS',schemes=results,basis_change=False,
                scope='Exact upper bounds for nineteen uploaded fixed decompositions. No global-record, rank-reduction or optimality claim.')


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
