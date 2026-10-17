#!/usr/bin/env python3
"""Default: stdlib-only archived-pool/certificate checks; no compiler or searches."""
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from support import HERE,cases,read,replay_candidate,replay_selection,verify_pool

def verify():
    manifest=read(HERE/'MANIFEST.json')
    for name,digest in manifest['files'].items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,name
    for row in read(HERE/'SOURCES.json'):
        raw=(HERE/row['destination']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw.splitlines())==row['lines']
    entries=cases();pools={case:read(entry['path']) for case,entry in entries.items()}
    for case,pool in pools.items():
        assert hashlib.sha256(entries[case]['path'].read_bytes()).hexdigest()==entries[case]['pool_sha256']
        assert verify_pool(pool)==entries[case]['baseline_signed_additions']
        if 'witness' in pool:
            assert replay_selection(pool,pool['witness'])==pool['expected']['additions']
            helpers={int(k) for k in pool['incumbent']}-{o for o,_ in pool['outputs']};removed=set(pool['expected']['removed']);added=set(pool['expected']['added'])
            assert len(removed)==3 and len(added)==2 and removed<=helpers
            assert {int(k) for k in pool['witness']}<=((helpers-removed)|{o for o,_ in pool['outputs']}|added)
    checked=0
    for path in sorted(HERE.rglob('candidate.json')):
        labels=[p.name for p in path.parents];matches=[case for case in entries if case in labels];assert len(matches)==1,(path,matches)
        case=matches[0];candidate=read(path);cost=replay_candidate(candidate,pools[case]['target_matrix']);checked+=1
        result=path.with_name('result.json')
        if result.exists():
            metadata=read(result)
            for key in ['signed_additions','candidate_signed_additions']:
                if key in metadata:assert metadata[key]==cost,(path,key)
    historical=read(HERE/'observed/historical_report.json')['results']
    for row in historical:
        if row['radius']!=2:continue
        assert row['pool_sha256']==entries[row['case']]['pool_sha256']
        assert row['status']=='EXHAUSTED_2_FOR_1' and row['statistics']['triples']==0
        pool=pools[row['case']];helpers={int(k) for k in pool['incumbent']}-{o for o,_ in pool['outputs']}
        assert row['statistics']['pairs']==math.comb(len(helpers),2)
        assert row['candidate_signed_additions']==row['baseline']
    for row in read(HERE/'observed/witness_replay_report.json')['results']:
        assert row['candidate_signed_additions']<row['baseline'] and row['known_removed_triple_prioritized']
    current=read(HERE/'observed/exact_report.json')['results']
    for row in current:
        assert row['pool_sha256']==entries[row['case']]['pool_sha256']
        if row['arm']!='exhaustive_2':continue
        assert row['status']=='EXHAUSTED_2_FOR_1'
        pool=pools[row['case']];helpers={int(k) for k in pool['incumbent']}-{o for o,_ in pool['outputs']}
        assert row['statistics']['pairs']==math.comb(len(helpers),2) and row['statistics']['triples']==0
    print(f'PASS: {len(pools)} exact pools, {checked} ordered-map candidates, historical three-helper witnesses and archived pair-exhaustion counts')
    return dict(status='PASS',pools=len(pools),candidate_maps=checked)
if __name__=='__main__':verify()
