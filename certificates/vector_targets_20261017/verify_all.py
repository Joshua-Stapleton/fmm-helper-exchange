#!/usr/bin/env python3
"""Verify all signed circuits, literal costs and full tensors exactly. Standard library only."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H))
from verify_literal import read_sms,replay
from verify_signed import replay as signed_replay
from verify_tensor import verify
def main():
    manifest=json.loads((H/'SHA256SUMS.json').read_text())
    actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json' and '__pycache__' not in p.parts}
    assert actual==set(manifest),'Bundle file set differs from SHA256 manifest'
    for name,digest in manifest.items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert hashlib.sha256((H/name).read_bytes()).hexdigest()==digest,name
    claims=json.loads((H/'claims.json').read_text());reports=[]
    for claim in claims['schemes']:
        folder=H/claim['scheme'];counts={};previous={}
        for factor in ('U','V','W'):
            matrix,_=read_sms(folder/(factor+'.sms'))
            value,stats=replay((folder/(factor+'.slp')).read_text(),len(matrix[0]));assert value==matrix
            assert stats['unary_negations']==stats['nonunit_scalars']==stats['unused_noninput_assignments']==0
            counts[factor]=stats['binary_additions'];assert counts[factor]==claim['counts'][factor]
            value,stats=replay((folder/'previous'/(factor+'.slp')).read_text(),len(matrix[0]));assert value==matrix
            assert stats['unary_negations']==stats['nonunit_scalars']==stats['unused_noninput_assignments']==0
            previous[factor]=stats['binary_additions'];assert previous[factor]==claim['previous_counts'][factor]
            value,cost,_=signed_replay(json.loads((folder/(factor+'.json')).read_text()),len(matrix[0]))
            assert value==matrix and cost==counts[factor]
        tensor=verify(folder/'U.sms',folder/'V.sms',folder/'W.sms',*claim['dimensions'])
        assert tensor['rank']==claim['rank'] and sum(counts.values())==claim['total_additions']
        assert claim['basis_change'] is False
        reports.append(dict(scheme=claim['scheme'],rank=tensor['rank'],counts=counts,total_additions=sum(counts.values()),previous_total_additions=sum(previous.values()),total_scalar_operations=sum(counts.values())+tensor['rank'],status='PASS'))
    witnesses=json.loads((H/'native_witnesses.json').read_text())
    for witness in witnesses:
        folder=H/witness['directory'];matrix,_=read_sms(H/witness['scheme']/(witness['factor']+'.sms'))
        value,stats=replay((folder/'certificate.slp').read_text(),len(matrix[0]));assert value==matrix
        assert stats['binary_additions']==witness['additions']
        assert stats['unary_negations']==stats['nonunit_scalars']==stats['unused_noninput_assignments']==0
        value,cost,_=signed_replay(json.loads((folder/'circuit.json').read_text()),len(matrix[0]))
        assert value==matrix and cost==witness['additions']
    print(json.dumps(dict(status='PASS',schemes=reports),indent=2))
if __name__=='__main__':main()
