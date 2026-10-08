"""Choose a canonical input basis and its entire finite-pool DAG jointly.

Sixteen freely selected target forms are the only zero-cost roots. If all target
forms (rank16) are computed acyclically from these roots, root independence is
automatic. Exact rational inversion and matrix replay still verify every hit.
"""
from cp_pool import *
from lrp import inv,matmul,write_sms,rank

def make_all_prods(forms):
    index={v:i for i,v in enumerate(forms)};prods=defaultdict(set)
    for a,u in enumerate(forms):
        for b in range(a,len(forms)):
            for sb in (1,-1):
                w,s=canonical(tuple(x+sb*y for x,y in zip(u,forms[b])));o=index.get(w)
                if o is not None and o not in (a,b):prods[o].add((a,Q(s),b,Q(s*sb)))
    groups=defaultdict(list)
    for a,v in enumerate(forms):
        first=next(x for x in v if x);groups[tuple(x/first for x in v)].append((a,first))
    for group in groups.values():
        for a,x in group:
            for o,y in group:
                ratio=y/x
                if a!=o and (ratio.numerator==1 or ratio.denominator==1):prods[o].add((a,ratio,-1,Q(0)))
    return {i:sorted(ps) for i,ps in prods.items()}

def solve_joint(forms,prods,outs,nin,bound,seconds,seed=1,strict=True,roots_all=False):
    m=cp_model.CpModel();n=len(forms);eligible=set(range(n)) if roots_all else {o for o,s in outs}
    active=[m.new_bool_var(f'a{i}') for i in range(n)]
    root=[m.new_bool_var(f'r{i}') for i in range(n)]
    neg=[m.new_bool_var(f's{i}') for i in range(n)]
    level=[m.new_int_var(0,bound,f'l{i}') for i in range(n)];choice={}
    for i in range(n):
        if i not in eligible:m.add(root[i]==0)
        m.add_implication(root[i],active[i]);m.add(level[i]==0).only_enforce_if(root[i])
        m.add(level[i]>=1).only_enforce_if([active[i],root[i].Not()])
        m.add(level[i]==0).only_enforce_if(active[i].Not())
        opts=[]
        for j,(a,sa,b,sb) in enumerate(prods.get(i,())):
            q=m.new_bool_var(f'g{i}_{j}');opts.append(q)
            m.add_implication(q,active[a]);m.add(level[i]>level[a]).only_enforce_if(q)
            if b<0 and strict:m.add(neg[i]==neg[a]).only_enforce_if(q)
            elif b>=0:
                m.add_implication(q,active[b]);m.add(level[i]>level[b]).only_enforce_if(q)
                allowed=[(so,sx,sy) for so in (0,1) for sx in (0,1) for sy in (0,1) if not ((-1)**(so+sx)*sa<0 and (-1)**(so+sy)*sb<0)]
                if strict:m.add_allowed_assignments([neg[i],neg[a],neg[b]],allowed).only_enforce_if(q)
        choice[i]=opts;m.add(sum(opts)==active[i]-root[i])
    for o,s in outs:
        m.add(active[o]==1)
        if strict:m.add(neg[o]==int(s<0))
    m.add(sum(root)==nin);m.add(sum(active)<=nin+bound)
    for i in range(n):m.add_hint(root[i],int(i<nin))
    sol=cp_model.CpSolver();sol.parameters.max_time_in_seconds=seconds;sol.parameters.num_search_workers=2;sol.parameters.random_seed=seed
    start=time.monotonic();status=sol.solve(m)
    info={'status':sol.status_name(status),'seconds':time.monotonic()-start,'bound':bound,'forms':n,'productions':sum(map(len,prods.values())),'eligible_roots':len(eligible),'root_count':nin,'branches':sol.num_branches,'conflicts':sol.num_conflicts,'scope':'joint basis and circuit search within finite exact form pool','strict_negation_free':strict,'roots_all':roots_all}
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None,None,info
    roots=[i for i in range(n) if sol.value(root[i])];sg=lambda i:-1 if strict and sol.value(neg[i]) else 1
    B=[[sg(i)*x for x in forms[i]] for i in roots];assert rank(B)==nin
    names={i:f'i{k}' for k,i in enumerate(roots)};lines=[]
    selected={i:next(j for j,q in enumerate(choice[i]) if sol.value(q)) for i in range(n) if sol.value(active[i]) and not sol.value(root[i])}
    if not strict:
        c=Circuit(nin);memo={i:j for j,i in enumerate(roots)}
        for i in sorted(selected,key=lambda i:(sol.value(level[i]),i)):
            a,sa,b,sb=prods[i][selected[i]]
            memo[i]=c.scale(memo[a],sa) if b<0 else c.add(c.scale(memo[a],sa),c.scale(memo[b],sb))
        c.outputs=[c.scale(memo[o],s) for o,s in outs];c.prune()
        target=[[s*x for x in forms[o]] for o,s in outs];A=matmul(target,inv(B));info['cost']=c.check(A);info['basis_roots']=roots;info['basis_rank']=rank(B);info['selected']=len(selected)
        return c.slp(),B,info
    for i in sorted(selected,key=lambda i:(sol.value(level[i]),i)):
        a,sa,b,sb=prods[i][selected[i]];name=f't{i}'
        if b<0:
            f=sa*sg(i)*sg(a);assert f>0;rhs=f'{names[a]}*{f.numerator}' if f.denominator==1 else f'{names[a]}/{f.denominator}'
        else:
            ca=sa*sg(i)*sg(a);cb=sb*sg(i)*sg(b);assert ca in (1,-1) and cb in (1,-1) and max(ca,cb)>0
            rhs=f'{names[a]}+{names[b]}' if ca==cb else (f'{names[a]}-{names[b]}' if ca>0 else f'{names[b]}-{names[a]}')
        lines.append(f'{name}:={rhs};');names[i]=name
    for k,(o,s) in enumerate(outs):assert sg(o)==s;lines.append(f'o{k}:={names[o]};')
    text='\n'.join(lines)+'\n';target=[[s*x for x in forms[o]] for o,s in outs];A=matmul(target,inv(B));c=parse_slp(text,nin,len(outs));info['cost']=c.check(A);info['basis_roots']=roots;info['basis_rank']=rank(B);info['selected']=len(selected)
    return text,B,info

def main():
    ap=argparse.ArgumentParser();ap.add_argument('role');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cap',type=int,default=32);ap.add_argument('--seconds',type=float,default=120);ap.add_argument('--bound',type=int);ap.add_argument('--seed',type=int,default=1);ap.add_argument('--transpose',action='store_true');ap.add_argument('--tag');ap.add_argument('--free-signs',action='store_true');ap.add_argument('--roots-all',action='store_true');ap.add_argument('--source',type=Path);a=ap.parse_args()
    M=read_sms(BASE/(a.role+'.sms'));c=parse_slp((a.source or BASE/(a.role+'.slp')).read_text(),len(M[0]),len(M));c.check(M)
    if a.transpose:c=c.transposed();M=transpose(M)
    forms,_,outs,initial=make_pool(c,a.cap);prods=make_all_prods(forms)
    count=c.cost();bound=a.bound if a.bound is not None else count['additions']+count['scalar_multiplications']-1
    text,B,info=solve_joint(forms,prods,outs,c.inputs,bound,a.seconds,a.seed,strict=not a.free_signs,roots_all=a.roots_all)
    info.update(role=a.role,transpose=a.transpose,extra=a.cap,baseline=count)
    tag=a.tag or f'joint_{a.role}{"T" if a.transpose else ""}_cap{a.cap}_b{bound}';out=a.out;out.mkdir(parents=True,exist_ok=False);dump(out/'result.json',info);dump(out/'pool.json',{'forms':forms,'productions':prods,'outputs':outs})
    if text:
        (out/'candidate.slp').write_text(text);A=matmul(M,inv(B));write_sms(out/'candidate.sms',A);write_sms(out/'basis.sms',B)
    print(json.dumps(info),flush=True)

if __name__=='__main__':main()
