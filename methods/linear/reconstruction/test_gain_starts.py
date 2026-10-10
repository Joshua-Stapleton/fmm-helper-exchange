#!/usr/bin/env python3
"""Generic paid-chain start controls; no real solver process is launched."""
import argparse, contextlib, importlib.util, io, json, subprocess, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent

def load(path):
 spec=importlib.util.spec_from_file_location('paid_chain_test',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def toy():
 a=dict(name='a-chain',gates=[[0,1,1,1],[4,1,2,1],[5,1,3,1],[4,1,2,-1],[7,1,3,-1]],outputs=[[6,1],[8,1]])
 b=dict(name='b-chain',gates=[[2,1,3,1],[0,1,4,1],[5,1,1,1],[0,1,4,-1],[7,1,1,1]],outputs=[[6,1],[8,1]])
 return dict(inputs=4,circuits=[a,b,a])

def test(api_path=None,module_name="gain_starts.py",mode="gain"):
 m=load(HERE/module_name);assert m.api is None and m.pool is None,'Import performed adapter side effects'
 m.configure(api_path);n,target,profiles=m.pool.bank(toy());assert len(profiles)==2
 selector=m.Selector(n,target,profiles)
 for seed in range(20):
  partial=selector.sample(seed,2,2);assert partial['initial_additions']==2
  assert partial['final_L1_proxy']<=partial['initial_L1_proxy']
  assert all(g[0]<n+j and g[2]<n+j for j,g in enumerate(partial['gates']))
  assert partial['covered_target_forms']<=partial['covered_target_rows']
 c=dict(name='a-before-b',gates=[[0,1,1,1],[3,1,2,1]],outputs=[[3,1],[4,1]])
 d=dict(name='b-before-a',gates=[[0,1,2,1],[3,1,1,1],[4,1,2,-1]],outputs=[[5,1],[4,1]])
 nn,tt,pp=m.pool.bank(dict(inputs=3,circuits=[c,d]));ss=m.Selector(nn,tt,pp)
 for seed in range(20):
  p=ss.sample(seed,3,2);assert all(g[0]<nn+j and g[2]<nn+j for j,g in enumerate(p['gates']))
 doubled=dict(name='double',gates=[[0,1,0,1]],outputs=[[1,-1]])
 nn,tt,pp=m.pool.bank(dict(inputs=1,circuits=[doubled]));p=m.Selector(nn,tt,pp).sample(7,1,1)
 assert p['initial_additions']==1 and p['covered_target_forms']==1
 assert m.api.exact_circuit(dict(inputs=1,gates=p['gates'],outputs=[[1,1]]),1)==[[2]]
 nn,tt,pp=m.pool.bank(dict(inputs=1,circuits=[dict(name='identity',gates=[],outputs=[[0,1]])]));p=m.Selector(nn,tt,pp).sample(0,3,2);assert p['initial_additions']==0
 # A valid but wasteful donor can contain huge intermediates while its target
 # remains3*x. Reject it before NumPy coordinate arithmetic can wrap.
 huge=[];wire=0
 for _ in range(62):huge.append([wire,1,wire,1]);wire=len(huge)
 huge.append([wire,1,1,1]);pa=len(huge);huge.append([wire,1,0,-1]);pb=len(huge);huge.append([pa,1,pb,-1])
 hn,ht,hp=m.pool.bank(dict(inputs=1,circuits=[dict(name='huge-cancellation',gates=huge,outputs=[[len(huge),1]])]))
 try:m.Selector(hn,ht,hp);raise AssertionError('Unsafe int64 proxy arithmetic accepted')
 except ValueError:pass
 for bad in [dict(seed=-1,budget=2,sources=2),dict(seed=1,budget=0,sources=2),dict(seed=1,budget=2,sources=0)]:
  try:selector.sample(**bad);raise AssertionError('Invalid sample accepted')
  except ValueError:pass
 with tempfile.TemporaryDirectory(prefix='paid-chain-test-') as td:
  td=Path(td);source=td/'source.json';source.write_text(json.dumps(toy()));binary=td/'driver';binary.write_text('fake driver; it will never execute')
  argv=['--donors',str(source),'--out',str(td/'result'),'--binary',str(binary),'--modes',mode,'--budgets','2','--attempts','1','--sources','2','--seconds','2','--timeout','1','--seed','7']
  if api_path is not None:argv+=['--api',str(api_path)]
  args=m.parser().parse_args(argv)
  m.validate(args);assert not args.out.exists(),'Validation wrote an output directory'
  for field,value in [('seconds',float('nan')),('sources',0),('attempts',0),('seed',2**32),('budgets','2,2'),('budgets','0'),('modes','gain,gain'),('modes','unknown')]:
   bad=argparse.Namespace(**vars(args));setattr(bad,field,value)
   try:m.validate(bad);raise AssertionError('Invalid arguments accepted')
   except ValueError:pass
   assert not args.out.exists()
  # Existing output contents must be preserved byte for byte.
  args.out.mkdir();sentinel=args.out/'keep.txt';sentinel.write_bytes(b'preserve')
  try:m.validate(args);raise AssertionError('Existing output directory accepted')
  except ValueError:pass
  assert sentinel.read_bytes()==b'preserve';sentinel.unlink();args.out.rmdir()
  source.write_text('{"inputs":4,"inputs":4,"circuits":[]}')
  try:m.validate(args);raise AssertionError('Duplicate JSON field accepted')
  except ValueError:pass
  source.write_text(json.dumps(toy()))
  valid=dict(additions=4,substitutions=[dict(i=0,ai=1,j=1,aj=1),dict(i=2,ai=1,j=3,aj=1),dict(i=4,ai=1,j=5,aj=1),dict(i=4,ai=1,j=5,aj=-1)],expressions=[[dict(index=6,value=1)],[dict(index=7,value=1)]])
  old_run=m.subprocess.run
  def mock(command,**kwargs):
   assert command[-2]=='1','Intended paid prefix was dropped again'
   target,gates=m.api.read_partial(Path(command[1]));assert len(target[0])==4
   Path(command[2]).write_text(json.dumps(valid));return subprocess.CompletedProcess(command,0,'','')
  try:
   m.subprocess.run=mock
   with contextlib.redirect_stdout(io.StringIO()):report=m.run(args)
   assert report['accepted']==1 and report['best_signed']==4 and report['status']=='COMPLETED_BUDGET'
   candidate=m.api.json_read(args.out/'best_candidate.json');assert m.api.exact_circuit(candidate,4)==target
   malformed=argparse.Namespace(**vars(args));malformed.out=td/'malformed'
   def bad_mock(command,**kwargs):
    Path(command[2]).write_text('{}');return subprocess.CompletedProcess(command,0,'','')
   m.subprocess.run=bad_mock
   with contextlib.redirect_stdout(io.StringIO()):bad_report=m.run(malformed)
   assert bad_report['status']=='ERROR' and bad_report['accepted']==0
   assert m.api.json_read(malformed.out/'records.json')[0]['status']=='ERROR'
  finally:m.subprocess.run=old_run
 return dict(status='PASS',paid_ancestry=True,sign_only_aliases=True,magnitude_preserved=True,int64_overflow_guard=True,acyclic=True,import_without_side_effects=True,argument_validation=True,duplicate_JSON_rejected=True,no_output_overwrites=True,mocked_exact_completion=True,malformed_solver_output_reported=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--api',type=Path);print(json.dumps(test(p.parse_args().api),indent=2))
