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
    protocol=json.loads((HERE/'campaign_protocol.json').read_text())
    by_directory={item['directory']:item for item in claims['schemes']}
    campaign_maps=set()
    for group,base in [('a',46160000),('b',47160000),('c',48160000)]:
        jobs=json.loads((HERE/('manifest_group_'+group+'.json')).read_text())
        assert len(jobs)==(21 if group=='a' else 18)
        assert protocol['groups'][group]['primary_base_seed']==base
        w_index=0
        for index,job in enumerate(jobs):
            shape=job['scheme'].split('_')[0];factor=job['factor'];item=by_directory[shape]
            assert job['filename']==job['scheme']+'_'+factor+'.sms'
            assert job['matrix']==shape+'/'+factor+'.sms'
            assert job['historical_source']==shape+'/source.json'
            assert sha(HERE/job['matrix'])==job['source_sha256']==item['source_matrix_sha256'][factor]
            assert sha(HERE/job['historical_source'])==job['source_json_sha256']==item['source_json_sha256']
            assert job['baseline_annotation']==item['historical_phase_counts'][factor]
            assert job['campaign_primary_seed']==base+1000*index
            assert job['primary_rerun_directory']==f'{index:02d}_'+factor
            assert job['filename'] not in campaign_maps;campaign_maps.add(job['filename'])
            if job.get('candidate'):
                assert job['candidate']=='provenance/previous/'+shape+'/'+factor+'.json'
                assert job['previous_strict_count']==item['previous_verified_or_source_phase_counts'][factor]
                assert (HERE/job['candidate']).is_file()
            if factor=='W':
                expected=base+1000*index+900 if group=='a' else base+50000+1000*index if group=='b' else base+500+1000*w_index
                assert job['campaign_w_adjoint_seed']==expected;w_index+=1
    assert len(campaign_maps)==57
    results=[]
    for item in claims['schemes']:
        folder=HERE/item['directory']
        source=json.loads((folder/'source.json').read_text())
        assert source['z2'] is False and source['n']==item['dimensions'] and source['m']==item['products']
        assert sha(folder/'source.json')==item['source_json_sha256']
        counts={}
        baseline={}
        previous={}
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
            provenance=json.loads((HERE/'provenance'/(item['directory']+'_'+factor+'.json')).read_text())
            assert provenance['status']=='PASS' and provenance['basis_change'] is False
            assert provenance['source_matrix_sha256']==matrix_sha
            assert provenance['historical_additions']==baseline[factor]
            assert provenance['selected_additions']==counts[factor]
            assert provenance['literal_counts']==stats
            assert item['selected_provenance'][factor]==provenance['selected_provenance']
            corrections=provenance['paid_output_correction_additions']
            assert isinstance(corrections,int) and corrections>=0
            assert item['paid_output_correction_additions'][factor]==corrections
            assert item['paid_sign_net_addition_overhead'][factor]==provenance['paid_sign_net_addition_overhead']
            recovery=provenance['paid_sign_recovery']
            if recovery is None:
                assert corrections==0
            else:
                metadata=recovery['metadata']
                base_path=HERE/recovery['base_candidate']
                base_signed,base_cost,_=replay_signed(json.loads(base_path.read_text()),len(matrix[0]))
                assert base_signed==matrix
                assert base_cost==metadata['original_signed_additions']
                assert metadata['final_strict_additions']==base_cost+metadata['net_addition_overhead']
                assert len(metadata['gate_tags'])==metadata['final_strict_additions']
                assert metadata['gate_tags'].count('output_sign_correction')==metadata['paid_output_correction_additions']
                assert metadata['gate_tags'].count('internal_sign_correction')==metadata['paid_internal_correction_additions']
                assert metadata['gate_tags'].count('shared_zero')==metadata['paid_zero_additions']
                if recovery['selected_recovery']:
                    assert corrections==metadata['paid_output_correction_additions']
                    assert counts[factor]==base_cost+metadata['net_addition_overhead']
                    assert provenance['paid_sign_net_addition_overhead']==metadata['net_addition_overhead']
                else:
                    assert corrections==0
            old_count=provenance['previous_strict_count']
            if old_count is not None:
                prior=HERE/'provenance'/'previous'/item['directory']
                prior_actual,prior_stats=replay((prior/(factor+'.slp')).read_text(),len(matrix[0]))
                assert prior_actual==matrix
                assert all(prior_stats[key]==0 for key in ('unary_negations','nonunit_scalars','unused_noninput_assignments'))
                assert prior_stats['binary_additions']==old_count
                prior_signed,prior_cost,_=replay_signed(json.loads((prior/(factor+'.json')).read_text()),len(matrix[0]))
                assert prior_signed==matrix and prior_cost==old_count
                assert counts[factor]<=old_count
            previous[factor]=baseline[factor] if old_count is None else old_count
            timing=provenance['timing']
            assert all(isinstance(timing[key],(int,float)) and timing[key]>=0 for key in ('donor_build_seconds','pool_build_seconds','pool_search_seconds','strict_orientation_seconds','other_primary_seconds','primary_total_seconds','adjoint_extra_total_seconds','paid_output_correction_seconds','additional_recovery_seconds','total_current_campaign_seconds'))
            assert abs(timing['primary_total_seconds']+timing['adjoint_extra_total_seconds']+timing['additional_recovery_seconds']-timing['total_current_campaign_seconds'])<1e-6
            assert item['current_campaign_seconds_per_factor'][factor]==timing['total_current_campaign_seconds']
        assert baseline==item['historical_phase_counts']
        assert sum(baseline.values())==source['complexity']['reduced']==item['historical_additions']
        additions=sum(counts.values())
        assert additions==item['final_additions']
        assert additions+source['m']==item['total_scalar_operations']
        assert item['historical_additions']-additions==item['saved_additions']
        assert previous==item['previous_verified_or_source_phase_counts']
        assert sum(previous.values())==item['previous_verified_or_source_additions']
        assert sum(previous.values())-additions==item['saved_since_previous_verified_or_source']
        if 'previous_published_additions' in item:
            assert item['previous_published_additions']-additions==item['saved_since_previous_publication']
        tensor=verify_tensor(folder/'U.sms',folder/'V.sms',folder/'W.sms',*source['n'])
        results.append(dict(dimensions=source['n'],products=source['m'],counts=counts,
                            additions=additions,total_scalar_operations=additions+source['m'],
                            saved_additions=item['saved_additions'],tensor=tensor,status='PASS'))
    from verify_joint_product_signs import verify as verify_joint
    variants=verify_joint(HERE)
    assert len(variants)==1
    return dict(status='PASS',schemes=results,joint_product_sign_variants=variants,basis_change=False,
                scope='Exact upper bounds for nineteen uploaded fixed decompositions. No global-record, rank-reduction or optimality claim.')


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
