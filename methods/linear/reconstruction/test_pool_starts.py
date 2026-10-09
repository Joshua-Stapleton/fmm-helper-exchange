#!/usr/bin/env python3
"""Paid mixed-chain starts: exact sign, magnitude, ancestry and cycle controls."""
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pool_start_api',HERE/'pool_starts.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def test():
    a=dict(name='a-chain',gates=[[0,1,1,1],[4,1,2,1],[5,1,3,1],[4,1,2,-1],[7,1,3,-1]],outputs=[[6,1],[8,1]])
    b=dict(name='b-chain',gates=[[2,1,3,1],[0,1,4,1],[5,1,1,1],[0,1,4,-1],[7,1,1,1]],outputs=[[6,1],[8,1]])
    n,target,profiles=mod.bank(dict(inputs=4,circuits=[a,b,a]))
    assert len(profiles)==2 and target==[[1,1,1,1],[1,1,-1,-1]]
    partial=mod.sample_start(n,target,profiles,4000,2,2)
    assert partial['initial_additions']==2 and partial['contributing_donors']==2
    assert {mod.api.canonical(x)[0] for x in mod.api.exact_circuit(dict(inputs=4,gates=partial['gates'],outputs=[[4,1],[5,1]]),4)}=={(1,1,0,0),(0,0,1,1)}
    doubled=dict(name='doubling',gates=[[0,1,0,1],[1,-1,1,-1]],outputs=[[2,-1]])
    nn,tt,pp=mod.bank(dict(inputs=1,circuits=[doubled]))
    prefix=mod.sample_start(nn,tt,pp,1,1,1)
    values=mod.api.exact_circuit(dict(inputs=1,gates=prefix['gates'],outputs=[[1,1]]),1)
    assert values==[[2]] and prefix['initial_additions']==1,'Magnitudes were merged with roots'
    # Both sources contain valid opposite-looking dependencies. Sequential chain
    # import must reuse already computed values without replacing their producer.
    c=dict(name='a-before-b',gates=[[0,1,1,1],[3,1,2,1]],outputs=[[3,1],[4,1]])
    d=dict(name='b-before-a',gates=[[0,1,2,1],[3,1,1,1],[4,1,2,-1]],outputs=[[5,1],[4,1]])
    nn,tt,pp=mod.bank(dict(inputs=3,circuits=[c,d]))
    for seed in range(20):
        p=mod.sample_start(nn,tt,pp,seed,3,2)
        assert all(g[0]<nn+j and g[2]<nn+j for j,g in enumerate(p['gates']))
    nn,tt,pp=mod.bank(dict(inputs=1,circuits=[dict(name='identity',gates=[],outputs=[[0,1]])]))
    p=mod.sample_start(nn,tt,pp,0,3,2);assert p['initial_additions']==0
    return dict(status='PASS',paid_two_source_example=True,donor_dedup=True,
                magnitude_preserved=True,cycle_free_chain_union=True,identity_partial=True)


if __name__=='__main__':print(json.dumps(test(),indent=2))
