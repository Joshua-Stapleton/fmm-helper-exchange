"""Portable repository discovery and independent exact integer replayers."""
import importlib.util
import json
import os
from pathlib import Path

HERE=Path(__file__).resolve().parent
def read(path):return json.loads(Path(path).read_text())
def repo_root(explicit=None):
    candidates=[]
    if explicit or os.environ.get('FMM_HELPER_EXCHANGE_REPO'):
        candidates.append(Path(explicit or os.environ['FMM_HELPER_EXCHANGE_REPO']).resolve())
    candidates.extend(HERE.parents)
    for path in candidates:
        if (path/'run.py').is_file() and (path/'methods/linear/plateau.cpp').is_file():return path
    raise ValueError('Place this study inside fmm-helper-exchange, pass --repo, or set FMM_HELPER_EXCHANGE_REPO')
def core(explicit=None):
    root=repo_root(explicit);spec=importlib.util.spec_from_file_location('portable_radius_core',root/'run.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def cases():
    return {entry['id']:dict(entry,path=HERE/entry['pool']) for entry in read(HERE/'CASES.json')}
def replay_candidate(candidate,target):
    n=candidate['inputs'];assert type(n)is int and n>0
    assert target and all(len(row)==n and all(type(x)is int for x in row) for row in target)
    wires=[[int(i==j) for j in range(n)] for i in range(n)]
    for gate in candidate['gates']:
        assert len(gate)==4;a,sa,b,sb=gate
        assert all(type(x)is int for x in gate) and 0<=a<len(wires) and 0<=b<len(wires) and sa in(-1,1) and sb in(-1,1)
        wires.append([sa*x+sb*y for x,y in zip(wires[a],wires[b])])
    actual=[]
    for wire,sign in candidate['outputs']:
        assert type(wire)is int and 0<=wire<len(wires) and type(sign)is int and sign in(-1,1)
        actual.append([sign*x for x in wires[wire]])
    assert actual==target,'Candidate differs from frozen ordered map'
    if 'target_matrix' in candidate:assert candidate['target_matrix']==target
    if 'additions_signed' in candidate:assert candidate['additions_signed']==len(candidate['gates'])
    return len(candidate['gates'])
def replay_selection(pool,selected):
    n=pool['inputs'];forms=pool['forms'];values={i:[int(i==j) for j in range(n)] for i in range(n)};pending={int(k):tuple(v) for k,v in selected.items()};chosen=dict(pending)
    while pending:
        ready=[o for o,(a,sa,b,sb) in pending.items() if a in values and b in values];assert ready,'Cycle or missing selected parent'
        for o in ready:
            a,sa,b,sb=pending.pop(o);assert list((a,sa,b,sb)) in pool['productions'][str(o)]
            values[o]=[sa*x+sb*y for x,y in zip(values[a],values[b])];assert values[o]==forms[o]
    actual=[[sign*x for x in values[o]] for o,sign in pool['outputs']];assert actual==pool['target_matrix']
    used=set();queue=[o for o,_ in pool['outputs']]
    while queue:
        o=queue.pop()
        if o<n or o in used:continue
        used.add(o);a,_,b,_=chosen[o];queue.extend([a,b])
    return len(used)
def verify_pool(pool):
    n=pool['inputs'];forms=pool['forms'];assert type(n)is int and n>0
    assert all(len(row)==n and all(type(x)is int for x in row) for row in forms)
    for i in range(n):assert forms[i]==[int(i==j) for j in range(n)]
    for text,productions in pool['productions'].items():
        o=int(text);assert n<=o<len(forms)
        for a,sa,b,sb in productions:
            assert all(type(x)is int for x in (a,sa,b,sb)) and 0<=a<len(forms) and 0<=b<len(forms) and sa in(-1,1) and sb in(-1,1)
            assert forms[o]==[sa*x+sb*y for x,y in zip(forms[a],forms[b])]
    return replay_selection(pool,pool['incumbent'])
