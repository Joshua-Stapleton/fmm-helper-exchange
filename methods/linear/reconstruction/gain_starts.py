#!/usr/bin/env python3
"""Paid starts selected by exact signed L1 target gain per marginal ancestor cost.
This L1 proxy is not a shortest-circuit distance or a lower bound. Every gate is
charged. Only unit sign aliases are merged and first producers are never changed.
"""
import argparse, importlib.util, json, math, random, subprocess, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
api = None
pool = None

def configure(api_path=None):
 """Load sibling common.py, or a caller-specified compatible adapter.
 Importing this module does not load external dependencies or create files.
 """
 global api, pool
 path = Path(api_path) if api_path is not None else HERE / 'common.py'
 if not path.is_file():
  raise ValueError('Circuit adapter common.py not found; use --api')
 spec = importlib.util.spec_from_file_location('chain_start_common', path)
 api = importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
 pool_path = path.parent / 'pool_starts.py'
 if not pool_path.is_file():
  raise ValueError('Sibling pool_starts.py is required by the adapter')
 spec = importlib.util.spec_from_file_location('chain_start_pool', pool_path)
 pool = importlib.util.module_from_spec(spec);spec.loader.exec_module(pool)
 pool.api = api
 return api

def validate(args):
 configure(getattr(args, 'api', None))
 api.finite(args.seconds, 'Overall time budget');api.finite(args.timeout, 'Per-call timeout')
 api.require(type(args.attempts) is int and args.attempts > 0, 'Positive attempts required')
 api.require(type(args.sources) is int and args.sources > 0, 'Positive source count required')
 api.require(type(args.seed) is int and 0 <= args.seed < 2**32, 'Seed must be uint32')
 api.require(math.isfinite(args.savings) and args.savings >= 0 and type(args.slack) is int and args.slack >= -1, 'Invalid scorer parameters')
 modes = args.modes.split(',')
 allowed = {'random', 'gain'}
 api.require(modes and all(m in allowed for m in modes) and len(modes) == len(set(modes)), 'Unique known selector modes required')
 try:budgets = [int(x) for x in args.budgets.split(',')]
 except (ValueError, TypeError):raise ValueError('Integer gate budgets required')
 api.require(budgets and all(b > 0 for b in budgets) and len(budgets) == len(set(budgets)), 'Unique positive gate budgets required')
 api.require(args.seed + max(budgets) * 100 + args.attempts <= 2**32, 'Derived solver seed exceeds uint32')
 api.require(not args.out.exists(), 'Output directory already exists; refusing to overwrite')
 source = api.json_read(args.donors)
 api.require(isinstance(source, dict) and type(source.get('inputs')) is int and source['inputs'] > 0, 'Positive integer input count required')
 api.require(isinstance(source.get('circuits'), list) and source['circuits'], 'Nonempty donor circuit list required')
 n, target, profiles = pool.bank(source)
 return n, target, profiles, modes, budgets

class Selector:
 def __init__(self,n,target,profiles):
  if api is None:configure()
  api.require(type(n) is int and n > 0 and profiles, 'Nonempty valid donor bank required')
  api.matrix_check(target)
  api.require(all(len(row)==n for row in target), 'Target input dimension mismatch')
  self.n=n;self.target=target;self.profiles=profiles
  self.forms=[];self.index={};self.endpoints=[];self.profile_indices=[]
  for d,p in enumerate(profiles):
   ids=[]
   for w,v in enumerate(p['values']):
    form=api.canonical(v)[0]
    if form not in self.index:self.index[form]=len(self.forms);self.forms.append(form)
    i=self.index[form];ids.append(i)
    if w>=n:
     full=pool.closure(p,w,{},n)
     self.endpoints.append((d,w,i,len(full)))
   self.profile_indices.append(ids)
  # Bound both coordinate arithmetic and the later sum over target gains.
  # Distances use int64, and 2*n*rows*bound <= 2**62 leaves headroom.
  safe_bound=(2**63-1)//(4*n*len(target))
  api.require(all(abs(x)<=safe_bound for row in target for x in row) and all(abs(x)<=safe_bound for form in self.forms for x in form), 'Coefficient magnitude exceeds safe int64 target-distance range')
  t=np.asarray([api.canonical(r)[0] for r in target],dtype=np.int64);v=np.asarray(self.forms,dtype=np.int64)
  self.distance=np.minimum(np.abs(t[:,None,:]-v[None,:,:]).sum(2),np.abs(t[:,None,:]+v[None,:,:]).sum(2))
  self.root_ids=[self.index[tuple(int(i==j) for j in range(n))] for i in range(n)]
 def sample(self,seed,budget,sources=6):
  api.require(type(seed) is int and 0 <= seed < 2**32 and type(budget) is int and budget > 0 and type(sources) is int and sources > 0, 'Valid seed and positive sampling parameters required')
  rng=random.Random(seed);n=self.n;ps=self.profiles
  values=[tuple(int(i==j) for j in range(n)) for i in range(n)];known={v:i for i,v in enumerate(values)}
  gates=[];log=[];contributions={};best=self.distance[:,self.root_ids].min(1)
  selected=set(rng.sample(range(len(ps)),min(sources,len(ps))))
  endpoint_ids=[j for j,e in enumerate(self.endpoints) if e[0] in selected]
  initial_proxy=int(best.sum());begin=time.monotonic()
  while len(gates)<budget:
   remaining=budget-len(gates);gain=np.maximum(best[:,None]-self.distance,0).sum(0)
   # Initial ranking scores endpoints; exact marginal closures and the gain of
   # every newly imported ancestor are evaluated for the best 64 candidates.
   rough=[]
   for j in endpoint_ids:
    d,w,i,cost=self.endpoints[j]
    if self.forms[i] in known:continue
    novelty=1/(1+contributions.get(d,0)/max(1,len(gates)))
    rough.append((float(gain[i])*novelty/math.sqrt(max(1,cost)),j))
   rough.sort(reverse=True);short=[j for _,j in rough[:64]]
   if len(rough)>64:short+=rng.sample([j for _,j in rough[64:]],min(16,len(rough)-64))
   candidates=[]
   for j in short:
    d,w,i,_=self.endpoints[j];needed=pool.closure(ps[d],w,known,n);cost=len(needed)
    if not cost or cost>remaining:continue
    ids=[self.profile_indices[d][wire] for wire in needed]
    after=np.minimum(best,self.distance[:,ids].min(1));target_gain=int((best-after).sum())
    newlycovered=int(((best>0)&(after==0)).sum())
    novelty=1/(1+contributions.get(d,0)/max(1,len(gates)))
    score=(target_gain+2*newlycovered)*novelty/cost
    candidates.append((score,d,w,needed,after,target_gain,newlycovered))
   if not candidates:
    # Budget tails need cheap endpoints that might have missed the shortlist.
    for _,j in rough:
     d,w,i,_=self.endpoints[j];needed=pool.closure(ps[d],w,known,n)
     if 0<len(needed)<=remaining:
      ids=[self.profile_indices[d][wire] for wire in needed];after=np.minimum(best,self.distance[:,ids].min(1))
      candidates.append((0,d,w,needed,after,int((best-after).sum()),int(((best>0)&(after==0)).sum())))
      if len(candidates)>=16:break
   if not candidates:break
   candidates.sort(key=lambda x:x[0],reverse=True);leaders=candidates[:min(8,len(candidates))]
   # Randomized top-ranked choices, rather than one deterministic greedy path.
   ceiling=leaders[0][0];weights=[math.exp(3*(c[0]/ceiling-1)) if ceiling>0 else 1 for c in leaders]
   score,d,w,needed,after,gain_value,covered=rng.choices(leaders,weights=weights,k=1)[0]
   added=pool.append_chain(ps[d],needed,known,gates,values,n);contributions[d]=contributions.get(d,0)+added;best=after
   log.append(dict(donor=d,endpoint=w,added=added,target_L1_gain=gain_value,newly_covered=covered,score=score))
  replay=api.exact_circuit(dict(inputs=n,gates=gates,outputs=[[n+i,1] for i in range(len(gates))]),n) if gates else []
  api.require(replay==[list(v) for v in values[n:]],'Paid chain replay differs')
  return dict(inputs=n,gates=gates,initial_additions=len(gates),contributing_donors=len(contributions),contributions=contributions,covered_target_forms=len({api.canonical(row)[0] for row in self.target}&set(known)),covered_target_rows=int((best==0).sum()),initial_L1_proxy=initial_proxy,final_L1_proxy=int(best.sum()),chain_choices=log,assembly_seconds=time.monotonic()-begin)

def run(args):
 n,target,profiles,modes,budgets=validate(args);precompute_start=time.monotonic();selector=Selector(n,target,profiles);precompute_seconds=time.monotonic()-precompute_start
 args.out.mkdir(parents=True,exist_ok=False);driver,build=api.binary(args,args.out,'repair');start=time.monotonic();records=[];donors=[];best=None
 for budget in budgets:
  for mode in modes:
   for attempt in range(args.attempts):
    if time.monotonic()-start>=args.seconds:break
    seed=args.seed+budget*100+attempt;t=time.monotonic()
    prefix=selector.sample(seed,budget,args.sources) if mode=='gain' else pool.sample_start(n,target,profiles,seed,budget,args.sources)
    prefix_values=[tuple(int(i==j) for j in range(n)) for i in range(n)]
    for a,sa,b,sb in prefix['gates']:prefix_values.append(tuple(sa*x+sb*y for x,y in zip(prefix_values[a],prefix_values[b])))
    known_forms={api.canonical(v)[0] for v in prefix_values};prefix['covered_target_rows']=sum(api.canonical(row)[0] in known_forms for row in target)
    partial=args.out/f'{mode}_{budget}_{attempt:02d}.txt';raw=partial.with_suffix('.raw.json');api.write_partial(partial,target,prefix['gates']);api.dump(partial.with_suffix('.partial.json'),prefix)
    row=dict(mode=mode,budget=budget,seed=seed,attempt=attempt,initial_additions=prefix['initial_additions'],contributing_donors=prefix['contributing_donors'],covered_target_forms=prefix['covered_target_forms'],covered_target_rows=prefix['covered_target_rows'],assembly_seconds=time.monotonic()-t)
    try:
     remain=args.seconds-(time.monotonic()-start)
     if remain<=0:break
     p=subprocess.run([str(driver),str(partial),str(raw),str(seed),str(args.savings),str(args.slack),'1',str(max(abs(x) for r in target for x in r))],capture_output=True,text=True,timeout=min(args.timeout,remain))
     api.require(p.returncode==0,p.stderr.strip());donor=api.convert(api.json_read(raw),target);donor['name']=f'{mode}-{budget}-{seed}';donors.append(donor);count=len(donor['gates']);row.update(status='PASS',additions_signed=count,exact_map_verified=True);api.dump(args.out/'checkpoint_donors.json',dict(inputs=n,circuits=donors))
     if best is None or count<best:best=count;api.save_candidate(args.out/'best_candidate.json',donor,target);api.dump(args.out/'best_progress.json',dict(best_signed=best,mode=mode,budget=budget,seed=seed));print(json.dumps(dict(new_best=best,mode=mode,budget=budget,seed=seed)),flush=True)
    except subprocess.TimeoutExpired:row['status']='TIMEOUT'
    except (ValueError, OSError, json.JSONDecodeError, KeyError, TypeError, IndexError) as e:row.update(status='ERROR',diagnostic=str(e))
    row['seconds']=time.monotonic()-t;records.append(row);api.dump(args.out/'records.json',records)
   if time.monotonic()-start>=args.seconds:break
  if time.monotonic()-start>=args.seconds:break
 api.dump(args.out/'donors.json',dict(inputs=n,circuits=donors));summary=dict(status=('ERROR' if not donors and any(r['status']=='ERROR' for r in records) else 'COMPLETED_BUDGET'),build=build,selector_precompute_seconds=precompute_seconds,elapsed_scope='Starts, completions and their exact checks; excludes bank normalization, selector precompute and driver build',attempts=len(records),accepted=len(donors),best_signed=best,elapsed_seconds=time.monotonic()-start,source_donors=len(profiles),form_count=len(selector.forms),input_dimension=n,target_rows=len(target),scope='Original input roots, paid chains, L1 target distance proxy and provenance complementarity; signed counts require strict orientation')
 for budget in budgets:
  for mode in modes:
   rs=[r for r in records if r['budget']==budget and r['mode']==mode];counts=[r['additions_signed'] for r in rs if r['status']=='PASS']
   summary[f'{mode}_{budget}']=dict(attempts=len(rs),accepted=len(counts),best=min(counts) if counts else None,median=float(np.median(counts)) if counts else None,mean_coverage_unique=float(np.mean([r['covered_target_forms'] for r in rs])) if rs else None,mean_covered_rows=float(np.mean([r['covered_target_rows'] for r in rs])) if rs else None,timeouts=sum(r['status']=='TIMEOUT' for r in rs),total_seconds=sum(r['seconds'] for r in rs),assembly_seconds=sum(r['assembly_seconds'] for r in rs))
 api.dump(args.out/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True);return summary
def parser():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--api',type=Path,help='Optional path to compatible common.py; defaults to sibling')
 p.add_argument('--donors',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--binary',type=Path);p.add_argument('--leo',type=Path);p.add_argument('--compiler')
 p.add_argument('--budgets',default='40,80,130,180');p.add_argument('--modes',default='random,gain')
 p.add_argument('--sources',type=int,default=6);p.add_argument('--attempts',type=int,default=10)
 p.add_argument('--seconds',type=float,default=240);p.add_argument('--timeout',type=float,default=3)
 p.add_argument('--seed',type=int,default=7000);p.add_argument('--savings',type=float,default=.01)
 p.add_argument('--slack',type=int,default=4)
 return p

def main():
 try:return run(parser().parse_args())
 except (ValueError,OSError,json.JSONDecodeError,KeyError,TypeError,IndexError) as error:
  print(json.dumps(dict(status='ERROR',diagnostic=str(error))))
  raise SystemExit(2)

if __name__=='__main__':main()
