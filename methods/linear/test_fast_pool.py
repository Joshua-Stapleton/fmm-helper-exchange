#!/usr/bin/env python3
"""Compare native and reference relation sets on signed and randomized DAGs."""
import importlib.util
import json
from pathlib import Path
import random
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_pool_api',HERE/'fast_pool.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)


def main():
    cases=[dict(inputs=2,circuits=[dict(name='signed-alias-and-doubling',
                gates=[[0,1,1,-1],[0,-1,1,1],[2,1,2,1]],
                outputs=[[2,1],[3,-1],[4,1]])])]
    generator=random.Random(20261009)
    for number in range(12):
        n=2+number%4
        values=[tuple(int(i==j) for j in range(n)) for i in range(n)]
        gates=[]
        while len(gates)<12:
            a,b=generator.randrange(len(values)),generator.randrange(len(values))
            sa,sb=generator.choice((-1,1)),generator.choice((-1,1))
            value=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]))
            if not any(value):continue
            values.append(value);gates.append([a,sa,b,sb])
        cases.append(dict(inputs=n,circuits=[dict(name=f'random-{number}',gates=gates,
                           outputs=[[len(values)-1,1],[n,1]])]))
    with tempfile.TemporaryDirectory(prefix='native-pool-check-') as tmp:
        binary=api.compile_backend(Path(tmp)/'relations')
        for source in cases:
            expected=api.reference.build_pool(source)
            actual=api.build_pool(source,binary=binary)
            assert actual==expected,'Native and reference pools differ'
        huge=dict(inputs=1,circuits=[dict(name='large-integer',
                 gates=[[i,1,i,1] for i in range(63)],outputs=[[63,1]])])
        try:api.build_pool(huge,binary=binary)
        except ValueError as error:assert 'int64' in str(error)
        else:raise AssertionError('Unsafe native integer range was accepted')
    print(json.dumps(dict(status='PASS',exact_reference_equivalence_cases=len(cases),
                          signed_alias_and_doubling=True,unsafe_integer_range_rejected=True),indent=2))


if __name__=='__main__':main()
