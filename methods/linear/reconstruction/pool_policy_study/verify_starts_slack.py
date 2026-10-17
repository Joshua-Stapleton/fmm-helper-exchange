#!/usr/bin/env python3
"""Stdlib audit of all frozen schedules and recorded emitted candidates."""
import argparse
import json
from pathlib import Path
import sys
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H))
from study_common import configure,load,replay,sha


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path)
    p.add_argument('--results',type=Path,help='Optional additional fresh rerun output tree')
    args=p.parse_args();repo,core=configure(args.repo)
    manifest=load(H/'STARTS_SLACK_MANIFEST.json')
    owned_files=['study_common.py','verify_starts_slack.py','EXPORT_PROVENANCE.json','STARTS_SLACK.md']
    actual=set(owned_files)
    actual.update(str(p.relative_to(H)) for category in ('starts','slack')
                  for p in (H/category).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    assert actual==set(manifest),'Portable method file set differs from manifest'
    for name,digest in manifest.items():assert sha(H/name)==digest,name
    provenance=load(H/'EXPORT_PROVENANCE.json')
    assert sha(repo/'methods/linear/plateau.cpp')==provenance['plateau_source_sha256']
    assert sha(H/'slack/plateau_slack.cpp')==provenance['slack_source_sha256']
    pools={};schedules=0
    for folder in sorted((H/'starts/data').iterdir()):
        if not folder.is_dir():continue
        data,prods,incumbent,_=core.load(folder/'pool.json');pools[folder.name]=data
        prep=load(folder/'preparation.json')
        assert sha(folder/'pool.json')==prep['pool_sha256']
        targets={o for o,s in data['outputs']};edges=[(o,a,b) for o in sorted(prods) for a,sa,b,sb in prods[o]]
        for arm,rows in prep['arms'].items():
            assert rows and len(rows)<=8
            for j,row in enumerate(rows):
                path=folder/f'{arm}_{j}.txt';lines=path.read_text().splitlines()
                n,i,t,h,e=map(int,lines[0].split())
                assert (n,i,t,h,e)==(len(data['forms']),data['inputs'],len(targets),len(row['helpers']),len(edges))
                assert list(map(int,lines[1].split()))==sorted(targets)
                assert list(map(int,lines[2].split()))==list(row['helpers'])
                assert len(set(row['helpers']))==len(row['helpers']) and not set(row['helpers'])&targets
                assert all(type(helper) is int and i<=helper<n for helper in row['helpers'])
                assert [tuple(map(int,line.split())) for line in lines[3:]]==edges
                allowed=set(range(i))|targets|set(row['helpers']);ready=set(range(i));chosen={}
                while True:
                    changed=False
                    for out in sorted(prods):
                        if out not in allowed or out in ready:continue
                        for a,sa,b,sb in prods[out]:
                            if a in ready and b in ready:
                                chosen[out]=(a,sa,b,sb);ready.add(out);changed=True;break
                    if not changed:break
                chosen=core.audit(chosen,data,prods)
                assert len(chosen)==row['initial_reconnected_cost']
                schedules+=1
    candidates=0
    roots=[H/'starts/observed',H/'slack/observed']
    if args.results:roots.append(args.results)
    for root in roots:
        for path in root.rglob('candidate.json'):
            matches=[cid for cid in pools if cid in path.parts]
            assert len(matches)==1,(path,matches)
            replay(load(path),pools[matches[0]]['target_matrix']);candidates+=1
    report=load(H/'starts/observed/report.json');assert len(report['results'])==36
    for row in report['results']:
        assert row['nominal_search_seconds']==6
        assert abs(sum(c['nominal_search_seconds'] for c in row['calls'])-6)<1e-9
        assert row['best']<=row['initial']
        for j,call in enumerate(row['calls']):
            path=H/'starts/observed/circuits'/row['case_id']/row['arm']/str(row['seed'])/str(j)/'candidate.json'
            assert replay(load(path),pools[row['case_id']]['target_matrix'])==call['final']
    slack=load(H/'slack/observed/report.json');assert len(slack['results'])==16
    assert all(r['best']<=r['initial'] and r['nominal_search_seconds']==6 for r in slack['results'])
    print(json.dumps(dict(status='PASS',frozen_pools=len(pools),input_schedules=schedules,
        completed_candidate_circuits=candidates,observed_portfolios=len(report['results']),
        observed_slack_runs=len(slack['results']),scope='Exact signed linear maps; literal sign orientation is verified in the separate certificate bundle.'),indent=2))


if __name__=='__main__':main()
