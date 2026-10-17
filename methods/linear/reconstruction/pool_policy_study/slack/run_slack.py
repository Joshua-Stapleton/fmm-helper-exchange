#!/usr/bin/env python3
"""Optional bounded uphill-state rerun; original incumbent is always retained."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from study_common import configure,load,dump,sha,replay


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path)
    p.add_argument('--case',action='append')
    p.add_argument('--seconds',type=float,default=6)
    p.add_argument('--slack',type=int,action='append')
    p.add_argument('--seed',type=int,action='append')
    p.add_argument('--out',type=Path,required=True,help='Fresh output directory')
    a=p.parse_args();assert a.seconds>0
    root,core=configure(a.repo)
    a.out.mkdir(parents=True,exist_ok=False)
    compiler=next((shutil.which(c) for c in ('c++','g++','clang++') if shutil.which(c)),None)
    assert compiler,'C++17 compiler required only for timed reruns'
    binary=(a.out/'plateau_slack').resolve()
    subprocess.run([compiler,'-O3','-std=c++17',str(HERE/'plateau_slack.cpp'),'-o',str(binary)],check=True)
    results=[];started=time.monotonic()
    cases=a.case or ['old_3x6x8_V','hl_5x7x7_V','hl_4x4x16_V','hl_4x4x16_Wt']
    for cid in cases:
        folder=HERE.parent/'starts/data'/cid
        data,prods,_,_=core.load(folder/'pool.json')
        edges=[(o,*p) for o in sorted(prods) for p in prods[o]]
        initial=load(folder/'preparation.json')['incumbent']
        for slack in a.slack or [1,2]:
            assert 0<=slack<=8
            for seed in a.seed or [171721,171821]:
                out=a.out/cid/str(slack)/str(seed);out.mkdir(parents=True,exist_ok=False)
                cmd=[str(binary),str(folder/'best_only_0.txt'),str(a.seconds),str(seed),'6',str(out/'selection.txt'),str(slack)]
                start=time.monotonic();process=subprocess.run(cmd,capture_output=True,text=True,timeout=a.seconds+6)
                assert process.returncode==0,process.stderr
                (out/'stderr.txt').write_text(process.stderr)
                best=initial
                if (out/'selection.txt').exists():
                    lines=(out/'selection.txt').read_text().splitlines();assert lines[0]=='FOUND'
                    chosen={}
                    for line in lines[1:]:
                        form,edge=map(int,line.split());o,*production=edges[edge]
                        assert o==form and o not in chosen
                        chosen[o]=tuple(production)
                    chosen=core.audit(chosen,data,prods);best=len(chosen);assert best<initial
                    core.export(chosen,data,out)
                    assert replay(load(out/'candidate.json'),data['target_matrix'])==best
                row=dict(case_id=cid,slack=slack,seed=seed,initial=initial,best=best,
                    nominal_search_seconds=a.seconds,wall_seconds=time.monotonic()-start,
                    exact_map_verified=True,diagnostic=process.stderr)
                dump(out/'report.json',row);results.append(row);print(row,flush=True)
    dump(a.out/'report.json',dict(status='COMPLETE',results=results,
        wall_seconds=time.monotonic()-started,source_sha256=sha(HERE/'plateau_slack.cpp'),
        baseline='Same frozen pool and best helper set; posthoc mechanistic control, no general superiority claim.'))


if __name__=='__main__':main()
