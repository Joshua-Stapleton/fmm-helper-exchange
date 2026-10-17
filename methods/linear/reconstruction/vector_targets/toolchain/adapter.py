#!/usr/bin/env python3
"""Build and feed one-worker unmodified LEO vector/prefix API comparisons."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE.parent / "upstream"
PIN = "7c8b59864e000bdc880938428d8a1991ec1f0bea"

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def raw(donor):
    if "gates" in donor:
        return dict(dimension=donor["inputs"], substitutions=[dict(i=a,ai=sa,j=b,aj=sb) for a,sa,b,sb in donor["gates"]], expressions=[[dict(index=w,value=s)] for w,s in donor["outputs"]])
    return donor

def replay(donor, target):
    donor = raw(donor)
    n = donor["dimension"]
    require(n > 0 and target and all(len(row)==n for row in target), "Bad map dimensions")
    values = [[int(i==j) for j in range(n)] for i in range(n)]
    for g in donor["substitutions"]:
        a,b,sa,sb = (g[k] for k in ["i","j","ai","aj"])
        require(all(type(x) is int for x in [a,b,sa,sb]) and 0<=a<len(values) and 0<=b<len(values) and sa in [-1,1] and sb in [-1,1], "Invalid binary gate")
        values.append([sa*x+sb*y for x,y in zip(values[a],values[b])])
        require(any(values[-1]) and max(map(abs,values[-1]))<=1000000, "Invalid/unsafe intermediate")
    outputs=[]
    for expression in donor["expressions"]:
        value=[0]*n
        for t in expression:
            require(type(t["index"]) is int and 0<=t["index"]<len(values) and type(t["value"]) is int and t["value"] in [-1,1], "Invalid terminal term")
            value=[a+t["value"]*b for a,b in zip(value,values[t["index"]])]
        outputs.append(value)
    require(outputs==target, "Exact ordered signed map mismatch")
    return len(donor["substitutions"])+sum(max(0,len(e)-1) for e in donor["expressions"])

def write_input(path, target, donor):
    donor=raw(donor); replay(donor,target)
    lines=[f'{donor["dimension"]} {len(target)} {len(donor["substitutions"])}']
    lines.extend(' '.join(map(str,row)) for row in target)
    lines.extend(' '.join(str(g[k]) for k in ['i','ai','j','aj']) for g in donor['substitutions'])
    lines.extend(' '.join(map(str,[len(e),*[x for t in e for x in [t['index'],t['value']]]])) for e in donor['expressions'])
    Path(path).write_text('\n'.join(lines)+'\n')

def build(binary=None):
    binary=Path(binary or HERE/'native_driver_v2').resolve()
    head=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()
    require(head==PIN,'Wrong upstream source commit')
    subprocess.run(['git','-C',str(UPSTREAM),'diff','--quiet','HEAD','--','include','src/leo'],check=True)
    tracked=subprocess.check_output(['git','-C',str(UPSTREAM),'ls-files','include/leo','src/leo'],text=True).splitlines()
    manifest={path:digest(UPSTREAM/path) for path in tracked}
    sources=[str(UPSTREAM/path) for path in tracked if path.startswith('src/leo/') and path.endswith('.cpp')]
    compiler=shutil.which('c++') or shutil.which('clang++')
    require(compiler,'No C++ compiler')
    snapshot=binary.with_suffix('.source.cpp'); snapshot.write_bytes((HERE/'native_driver.cpp').read_bytes())
    command=[compiler,'-std=c++17','-O3','-I'+str(UPSTREAM/'include'),str(snapshot),*sources,'-o',str(binary)]
    start=time.monotonic(); subprocess.run(command,check=True,timeout=180)
    meta=dict(upstream_commit=PIN,upstream_branch='new-improvements',upstream_unmodified=True,upstream_source_sha256=manifest,driver_sha256=digest(snapshot),driver_source_snapshot=str(snapshot),binary_sha256=digest(binary),compiler=compiler,command=command,build_seconds=time.monotonic()-start,worker_count=1,threading='One CPU worker, no OpenMP enabled; direct Solver/HelperPool APIs only')
    binary.with_suffix('.build.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',action='store_true')
    p.add_argument('--candidate',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.build:
        m=build(); print(json.dumps({k:v for k,v in m.items() if k not in ['upstream_source_sha256','command']},indent=2))
    elif a.candidate and a.output:
        candidate=json.loads(a.candidate.read_text()); write_input(a.output,candidate['target_matrix'],candidate)
    else:
        p.error('Choose --build or --candidate FILE --output TEXT')
