#!/usr/bin/env python3
"""Standard-library exact replay of a restricted catalogue's upper witness."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('verify_paid',HERE/'verify_paid.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def verify(directory):
    directory=Path(directory);manifest=json.loads((directory/'MANIFEST.json').read_text())
    for name,expected in manifest['files'].items():
        path=directory/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,name
    graph=json.loads((directory/'observed.json').read_text());n=graph['inputs'];forms=graph['forms']
    target=audit.read_matrix(directory/'matrix.sms')
    assert graph['target_matrix']==target and len(set(map(tuple,forms)))==len(forms)
    assert forms[:n]==[[int(i==j)for j in range(n)]for i in range(n)]
    ids={tuple(row):i for i,row in enumerate(forms)}
    for row in forms:assert list(audit.canonical(row)[0])==row
    for child,options in graph['productions'].items():
        i=int(child);assert n<=i<len(forms)
        for a,sa,b,sb in options:
            assert 0<=a<=b<len(forms) and i not in (a,b) and sa in (-1,1)and sb in (-1,1)
            assert [sa*x+sb*y for x,y in zip(forms[a],forms[b])]==forms[i]
    assert [[sign*x for x in forms[wire]]for wire,sign in graph['outputs']]==target
    witness=json.loads((directory/'candidate88.json').read_text());report=audit.replay(witness,target,budget=88)
    assert len(witness['gates'])==88
    values=[tuple(int(i==j)for j in range(n))for i in range(n)]
    for a,sa,b,sb in witness['gates']:
        vector=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]));values.append(vector)
        child,sc=audit.canonical(vector);left,sl=audit.canonical(values[a]);right,sr=audit.canonical(values[b])
        out=ids[child];pair=sorted([(ids[left],sa*sl*sc),(ids[right],sb*sr*sc)])
        assert [pair[0][0],pair[0][1],pair[1][0],pair[1][1]]in graph['productions'][str(out)]
    report.update(observed_forms=len(forms),observed_productions=sum(map(len,graph['productions'].values())),
                  every_witness_production_in_observed_graph=True,
                  unsat_proof_checked=False,
                  scope='Exact signed upper witness only; solver infeasibility is separate')
    return report


if __name__=='__main__':print(json.dumps(verify(HERE),indent=2))
