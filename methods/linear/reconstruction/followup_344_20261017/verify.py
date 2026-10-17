#!/usr/bin/env python3
"""Replay saved maps and the exchange counterexample; no searches by default."""
import importlib.util,json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load(p):return json.loads(p.read_text())
def verify():
 cert=mod('map344certificate',ROOT/'certificates/map_3x4x4_V41_20261017/verify.py').verify()
 toy=mod('exchange344toy',H/'three_for_two/verify_small.py').verify()
 api=mod('followup344adapter',H.parent/'vector_targets/toolchain/adapter.py')
 core=mod('followup344core',ROOT/'run.py')
 target=load(ROOT/'certificates/map_3x4x4_V41_20261017/matrix.json')
 bank=load(H/'native/early_donors.json');assert len(bank['circuits'])==64
 for c in bank['circuits']:api.replay(c,target)
 event=load(H/'native/first_41.json');assert event['seed']==1719348 and api.replay(event['solution'],target)==41
 pools=[]
 for label in ['subsets','pairs_native']:
  p=H/'observed'/label;data,prods,_,_=core.load(p/'pool.json');c=load(p/'candidate.json')
  assert data['target_matrix']==target and api.replay(c,target)==41
  pools.append(dict(name=label,forms=len(data['forms']),productions=sum(map(len,prods.values()))))
 for label in ['subsets','pairs_native']:
  subprocess.run([sys.executable,'-I','-B',str(H/'exact/verify.py'),'--pool',str(H/'observed'/label/'pool.json'),'--candidate',str(H/'exact'/label/'candidate.json')],check=True,capture_output=True,text=True)
 subprocess.run([sys.executable,'-I','-B',str(H/'native/evidence/verify.py')],check=True,capture_output=True,text=True)
 return dict(status='PASS',literal_certificate=cert['additions_subtractions'],selected_native_donors=64,first_native_solution=41,frozen_pools=pools,toy_old=toy['old_additions'],toy_new=toy['new_additions'],scope='Saved maps and local exchange controls; no new timed searches or unrestricted SLP optimality proof.')
if __name__=='__main__':print(json.dumps(verify(),indent=2))
