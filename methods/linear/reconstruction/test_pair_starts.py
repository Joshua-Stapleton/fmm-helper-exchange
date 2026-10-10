#!/usr/bin/env python3
"""Exact pair complementarity and inherited generic paid-chain controls."""
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test(api_path=None):
 generic=module('generic_chain_test',HERE/'test_gain_starts.py')
 report=generic.test(api_path,module_name='pair_starts.py',mode='pair')
 m=module('pair_chain_test',HERE/'pair_starts.py');m.configure(api_path)
 # t=a+b+c; u=t+d+e+f+g and v=d+e+f+g. Neither paid chain
 # alone improves nearest-vector L1 distance2; together t=u-v is one-gate.
 g=[[0,1,3,1],[1,1,4,1],[2,1,5,1],[7,1,8,1],[10,1,9,1],[11,1,6,1],[3,1,4,1],[5,1,6,1],[13,1,14,1],[12,1,15,-1]]
 n,t,p=m.pool.bank(dict(inputs=7,circuits=[dict(name='complement',gates=g,outputs=[[16,1]])]));s=m.Selector(n,t,p)
 h=np.zeros(len(s.forms),dtype=bool);h[s.root_ids]=True;initial=int(s.distance[:,s.root_ids].min(1)[0]);assert initial==2
 for wires in ([7,8,9,10,11,12],[13,14,15]):
  hp=h.copy();ids=[s.profile_indices[0][w]for w in wires];hp[ids]=True
  assert int(s.distance[:,np.flatnonzero(hp)].min(1)[0])==2
  assert not bool(s.reachable(hp)[0])
 hp=h.copy();hp[[s.profile_indices[0][w]for w in range(7,16)]]=True;assert bool(s.reachable(hp)[0])
 for seed in range(10):
  q=s.sample(seed,9,1);assert q['initial_additions']<=9
  assert all(g[0]<n+j and g[2]<n+j for j,g in enumerate(q['gates']))
 report.update(single_chain_L1_unchanged=True,union_exact_one_gate_unlock=True,hyperedges=len(s.hyperedges))
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--api',type=Path);print(json.dumps(test(p.parse_args().api),indent=2))
