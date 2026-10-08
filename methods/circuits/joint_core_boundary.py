"""Two finite DAGs, with exact pool union across historical basis changes.

Source certificates are read-only. Coordinate pullbacks make historical helper
forms comparable in the current basis before the new joint search begins.
"""
from joint_basis import *
import argparse, hashlib
ap=argparse.ArgumentParser()
ap.add_argument('--side',choices=['L','P'],default='P')
ap.add_argument('--core',type=int,default=50);ap.add_argument('--boundary',type=int,default=11)
ap.add_argument('--seconds',type=float,default=300);ap.add_argument('--cap',type=int,default=32)
ap.add_argument('--boundary-cap',type=int,default=24);ap.add_argument('--legacy',type=Path,action='append',default=[],help='Historical certificate folder; repeat to pool across bases')
ap.add_argument('--structural-cuts',action='store_true');ap.add_argument('--scale-helpers',action='store_true');ap.add_argument('--allow-scalars',action='store_true');ap.add_argument('--incumbent-priority',action='store_true');ap.add_argument('--ordinary-roots',action='store_true');ap.add_argument('--fixed-roots',action='store_true',help='Fix incumbent roots AND incumbent boundary productions');ap.add_argument('--all-roots',action='store_true');ap.add_argument('--objective',choices=['boundary','core','weighted','none'],default='boundary')
ap.add_argument('--base',type=Path);ap.add_argument('--reuse-pool',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--seed',type=int,default=20261004)
a=ap.parse_args();out=a.out;out.mkdir(parents=True,exist_ok=False)
if a.base:BASE=a.base.resolve()
current=parse_slp((BASE/f'ALT_{a.side}.slp').read_text(),16 if a.side=='L' else 48,48 if a.side=='L' else 16)
bound=parse_slp((BASE/f'CoB_{a.side}.slp').read_text(),16,16)
M=read_sms(BASE/f'ALT_{a.side}.sms');C=read_sms(BASE/f'CoB_{a.side}.sms')
if a.side=='P': current=current.transposed();bound=bound.transposed();M=transpose(M);C=transpose(C)
legacy=[];sources=[]
if a.legacy:
 folders=a.legacy
 for folder in folders:
  if not folder.is_dir() or not (folder/f'ALT_{a.side}.slp').exists():continue
  oc=parse_slp((folder/f'ALT_{a.side}.slp').read_text(),16 if a.side=='L' else 48,48 if a.side=='L' else 16)
  bc=read_sms(folder/f'CoB_{a.side}.sms')
  if a.side=='P':oc=oc.transposed();bc=transpose(bc)
  pull=matmul(bc,inv(C));legacy.extend(matmul(values(oc),pull));sources.append(str(folder))
if a.reuse_pool:
 data=json.loads(a.reuse_pool.read_text())
 if 'coordinate_boundary' not in data:raise ValueError('reuse pool requires explicit coordinate_boundary')
 oldC=[[Q(x) for x in v] for v in data['coordinate_boundary']]
 pull=matmul(oldC,inv(C));legacy.extend(matmul([[Q(x) for x in v] for v in data['forms']],pull))
if a.scale_helpers:
 actual=values(current);mandatory={canonical(actual[j])[0] for j in current.outputs};hs={canonical(v)[0] for v in actual[16:] if any(v)}-mandatory
 legacy.extend(tuple(k*x for x in v) for v in hs for k in (Q(2),Q(1,2)))
if a.ordinary_roots:legacy.extend(inv(C))
F,_,O,_=make_pool(current,a.cap,legacy,a.incumbent_priority);P=make_all_prods(F)
rootimages=matmul(F,C)
G,Qp,_,_=make_pool(bound,a.boundary_cap,rootimages);idx={v:i for i,v in enumerate(G)};links=[(idx[canonical(v)[0]],canonical(v)[1]) for v in rootimages]
model=cp_model.CpModel();n=len(F);active=[model.new_bool_var(f'a{i}') for i in range(n)];roots=[model.new_bool_var(f'r{i}') for i in range(n)];lev=[model.new_int_var(0,a.core,f'l{i}') for i in range(n)];choice={}
for i in range(n):
 if a.fixed_roots:model.add(roots[i]==int(i<16))
 if not a.all_roots and i not in {v for v,s in O}:model.add(roots[i]==0)
 model.add_implication(roots[i],active[i]);model.add(lev[i]==0).only_enforce_if(roots[i]);model.add(lev[i]>=1).only_enforce_if([active[i],roots[i].Not()]);model.add(lev[i]==0).only_enforce_if(active[i].Not());opts=[]
 for j,(u,su,v,sv) in enumerate(P.get(i,())):
  q=model.new_bool_var(f'p{i}_{j}');opts.append(q)
  if v<0 and not a.allow_scalars:model.add(q==0)
  model.add_implication(q,active[u]);model.add(lev[i]>lev[u]).only_enforce_if(q)
  if v>=0:model.add_implication(q,active[v]);model.add(lev[i]>lev[v]).only_enforce_if(q)
 choice[i]=opts;model.add(sum(opts)==active[i]-roots[i])
for i,s in O:model.add(active[i]==1)
model.add(sum(roots)==16);model.add(sum(active)<=16+a.core)
if a.structural_cuts:
 triangle_choices=defaultdict(list)
 for i,opts in choice.items():
  for j,q in enumerate(opts):
   u,su,v,sv=P[i][j]
   if v>=0 and len({i,u,v})==3:triangle_choices[tuple(sorted((i,u,v)))].append(q)
 for qs in triangle_choices.values():
  if len(qs)>1:model.add_at_most_one(qs)
 targets={i for i,s in O}
 typed=(not a.all_roots and all(v>=0 and int(u in targets)+int(v in targets)==1 for i in targets for u,su,v,sv in P.get(i,())))
 if typed:
  pairs=defaultdict(set);seeds=[]
  for i,opts in choice.items():
   if i in targets:continue
   for j,q in enumerate(opts):
    u,su,v,sv=P[i][j]
    if u in targets and v in targets:pairs[i].add(tuple(sorted((u,v))));seeds.append(q)
  model.add(sum(len(v)*active[i] for i,v in pairs.items())-sum(seeds)>=len(targets)-16)
  if len(targets)>16:model.add(sum(seeds)>=1)
 print(json.dumps({'triangle_cliques':len(triangle_choices),'typed_target_coverage_cut':typed}),flush=True)
ng=len(G);ba=[model.new_bool_var(f'b{i}') for i in range(ng)];bl=[model.new_int_var(0,a.boundary,f'bl{i}') for i in range(ng)];bc={}
for i in range(16):model.add(ba[i]==1);model.add(bl[i]==0)
for i in range(16,ng):
 model.add(bl[i]>=1).only_enforce_if(ba[i]);model.add(bl[i]==0).only_enforce_if(ba[i].Not());opts=[]
 for j,(u,su,v,sv) in enumerate(Qp.get(i,())):
  q=model.new_bool_var(f'bp{i}_{j}');opts.append(q);model.add_implication(q,ba[u]);model.add(bl[i]>bl[u]).only_enforce_if(q)
  if v>=0:model.add_implication(q,ba[v]);model.add(bl[i]>bl[v]).only_enforce_if(q)
 bc[i]=opts;model.add(sum(opts)==ba[i])
for i,(j,s) in enumerate(links):model.add_implication(roots[i],ba[j])
model.add(sum(ba[16:])<=a.boundary)
if a.objective=='boundary':model.minimize(sum(ba[16:]))
elif a.objective=='core':model.minimize(sum(active)-16)
elif a.objective=='weighted':model.minimize(100*(sum(active)-16)+sum(ba[16:]))
for i in range(n):model.add_hint(roots[i],int(i<16))

def hint(c,forms,prods,choices,levels,acts):
 index={v:i for i,v in enumerate(forms)};vs=values(c);ids=[index[canonical(v)[0]] if any(v) else -1 for v in vs];sg=[canonical(v)[1] for v in vs];picked={};dep={i:0 for i in range(16)}
 for j,node in enumerate(c.nodes,c.inputs):
  i=ids[j]
  if i<16 or i in picked:continue
  if node['op']=='scale':
   aa=ids[node['a']];ratio=Q(node['c'])*sg[j]*sg[node['a']]
   if abs(ratio)==1:continue
   wanted=(aa,ratio,-1,Q(0))
  elif node['op']=='add':
   aa,bb=ids[node['a']],ids[node['b']];sa,sb=Q(sg[j]*sg[node['a']]),Q(sg[j]*sg[node['b']])
   if aa>bb:aa,bb,sa,sb=bb,aa,sb,sa
   wanted=(aa,sa,bb,sb)
  else:continue
  if wanted not in prods.get(i,()):continue
  picked[i]=prods[i].index(wanted);aa,sa,bb,sb=wanted;dep[i]=1+max(dep.get(aa,0),dep.get(bb,0) if bb>=0 else 0)
 for i,opts in choices.items():
  for j,q in enumerate(opts):
   model.add_hint(q,int(picked.get(i)==j))
   if a.fixed_roots and acts is ba:model.add(q==int(picked.get(i)==j))
  model.add_hint(levels[i],min(dep.get(i,0),a.core if acts is active else a.boundary))
 for i,q in enumerate(acts):model.add_hint(q,int(i in picked or i<16))
 return len(picked)
print(json.dumps({'core_forms':n,'boundary_forms':ng,'core_productions':sum(map(len,P.values())),'boundary_productions':sum(map(len,Qp.values())),'hint_core':hint(current,F,P,choice,lev,active),'hint_boundary':hint(bound,G,Qp,bc,bl,ba),'sources':sources}),flush=True)
dump(out/'pool.json',{'forms':F,'productions':P,'outputs':O,'boundary_forms':G,'boundary_productions':Qp,'links':links,'sources':sources,'coordinate_boundary':C})

def circuit(sol,forms,prods,choices,levels,rids,outs):
 c=Circuit(len(rids));memo={i:j for j,i in enumerate(rids)};selected={i:next(j for j,q in enumerate(choices[i]) if sol.value(q)) for i in choices if any(sol.value(q) for q in choices[i])}
 for i in sorted(selected,key=lambda i:(sol.value(levels[i]),i)):
  u,su,v,sv=prods[i][selected[i]];memo[i]=c.scale(memo[u],su) if v<0 else c.add(c.scale(memo[u],su),c.scale(memo[v],sv))
 c.outputs=[c.scale(memo[i],s) for i,s in outs];c.prune();return c

def save(sol):
 r=[i for i in range(n) if sol.value(roots[i])];B=[F[i] for i in r];assert rank(B)==16
 core=circuit(sol,F,P,choice,lev,r,O);boundary=circuit(sol,G,Qp,bc,bl,list(range(16)),[links[i] for i in r]);coremat=matmul(M,inv(B));bmat=matmul(B,C);core.check(coremat);boundary.check(bmat)
 cg=sum(sol.value(q) for q in active)-16;bg=sum(sol.value(q) for q in ba[16:]);d=out/f'c{cg}_b{bg}';d.mkdir(exist_ok=True)
 for name,circ,mat in [('core',core,coremat),('boundary',boundary,bmat)]:
  (d/f'{name}T.slp').write_text(circ.slp());write_sms(d/f'{name}T.sms',mat)
  if a.side=='P':circ=circ.transposed();mat=transpose(mat)
  tag=f'ALT_{a.side}' if name=='core' else f'CoB_{a.side}'
  (d/f'{tag}_raw.slp').write_text(circ.slp());write_sms(d/f'{tag}.sms',mat)
 write_sms(d/'basis.sms',B);info={'core':cg,'boundary':bg,'basis_roots':r,'core_cost':core.cost(),'boundary_cost':boundary.cost(),'status':'exact linear factorizations verified; strict orientation pending'};dump(d/'result.json',info);print(json.dumps(info),flush=True)
class Callback(cp_model.CpSolverSolutionCallback):
 def on_solution_callback(self):save(self)
sol=cp_model.CpSolver();sol.parameters.max_time_in_seconds=a.seconds;sol.parameters.num_search_workers=2;sol.parameters.random_seed=a.seed
start=time.monotonic();status=sol.solve(model,Callback());info={'status':sol.status_name(status),'seconds':time.monotonic()-start,'core_forms':n,'boundary_forms':ng,'arguments':{k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},'objective':sol.objective_value,'best_bound':sol.best_objective_bound,'branches':sol.num_branches,'conflicts':sol.num_conflicts,'scope':'finite rational pool, no unrestricted lower bound'};dump(out/'result.json',info);print(json.dumps(info),flush=True)
