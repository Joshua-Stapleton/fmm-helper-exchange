#!/usr/bin/env python3
"""Exact compensated product-sign checks; Python standard library only."""
from pathlib import Path
import json
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from verify_literal import read_sms,replay
from verify_signed import replay as replay_signed
from verify_tensor import verify as verify_tensor

def verify(root=HERE):
    claims=json.loads((root/'claims.json').read_text())
    results=[]
    for item in claims.get('joint_product_sign_variants',[]):
        folder=root/item['directory'];source=root/item['original_directory']
        assert item['basis_change'] is False
        original={f:read_sms(source/(f+'.sms'))[0] for f in 'UVW'}
        actual={};counts={};signs={}
        for factor in 'UVW':
            matrix,_=read_sms(folder/(factor+'.sms'));actual[factor]=matrix
            literal,stats=replay((folder/(factor+'.slp')).read_text(),len(matrix[0]))
            assert literal==matrix
            assert all(stats[k]==0 for k in ('unary_negations','nonunit_scalars','unused_noninput_assignments'))
            signed,cost,_=replay_signed(json.loads((folder/(factor+'.json')).read_text()),len(matrix[0]))
            assert signed==matrix and cost==stats['binary_additions']
            counts[factor]=cost
            initial=json.loads((folder/'input_candidates'/(factor+'.json')).read_text())
            initial_map,initial_cost,_=replay_signed(initial,len(original[factor][0]))
            assert initial_map==original[factor]
            assert initial_cost==cost,'Joint orientation must preserve binary gate count'
        for factor in 'UV':
            assert len(actual[factor])==len(original[factor])==item['products']
            signs[factor]=[]
            for row,old in zip(actual[factor],original[factor]):
                assert any(old)
                if row==old:sign=1
                else:assert row==[-x for x in old];sign=-1
                signs[factor].append(sign)
        assert len(actual['W'])==len(original['W'])
        for row,old in zip(actual['W'],original['W']):
            assert row==[signs['U'][r]*signs['V'][r]*x for r,x in enumerate(old)]
        assert counts==item['phase_counts']
        assert sum(counts.values())==item['final_additions']
        assert item['products']+sum(counts.values())==item['total_scalar_operations']
        tensor=verify_tensor(folder/'U.sms',folder/'V.sms',folder/'W.sms',*item['dimensions'])
        results.append(dict(status='PASS',directory=item['directory'],dimensions=item['dimensions'],products=item['products'],counts=counts,additions=sum(counts.values()),total_scalar_operations=item['total_scalar_operations'],compensated_product_sign_relation='PASS',tensor=tensor,basis_change=False,scope='Whole multiplication tensor preserved. Individual fixed maps differ by compensated product signs. Separate from the nineteen original fixed-map results.'))
    return results
if __name__=='__main__':print(json.dumps(dict(status='PASS',joint_product_sign_variants=verify()),indent=2))
