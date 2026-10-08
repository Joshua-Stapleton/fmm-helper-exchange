"""Exact finite rational-form circuit extraction with CP-SAT and strict signs.

Search is deliberately finite: INFEASIBLE excludes this form pool only.
CP-SAT rank variables prohibit cycles. Selected gate sign constraints prohibit
hidden unary negations, and a separately parsed output certificate is replayed.
"""
from pathlib import Path
from fractions import Fraction as Q
from collections import defaultdict,Counter
import argparse, json, sys, time, importlib.util

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from circuits import Circuit,parse_slp,read_sms,transpose,dump
from ortools.sat.python import cp_model
BASE=HERE.parent/'basis/certificate_4x4_169_43'

def canonical(v):
    s=next((1 if x>0 else -1 for x in v if x),1)
    return tuple(s*x for x in v),s

def values(c):
    vs=[tuple(Q(i==j) for j in range(c.inputs)) for i in range(c.inputs)]
    for n in c.nodes:
        if n['op']=='add':v=tuple(a+b for a,b in zip(vs[n['a']],vs[n['b']]))
        elif n['op']=='scale':v=tuple(Q(n['c'])*a for a in vs[n['a']])
        else:v=(Q(0),)*c.inputs
        vs.append(v)
    return vs

def make_pool(c,extra=32,additional=(),incumbent_priority=False):
    vs=values(c)
    if any(not any(vs[o]) for o in c.outputs):
        raise ValueError("finite-pool synthesis requires nonzero target forms")
    forms=list(dict.fromkeys(canonical(v)[0] for v in vs if any(v)))
    assert len(forms)>=c.inputs
    initial=len(forms); index={v:i for i,v in enumerate(forms)}
    for v in additional:
        v=canonical(v)[0]
        if any(v) and v not in index:index[v]=len(forms);forms.append(v)
    known=len(forms)
    if extra:
        reps=defaultdict(list)
        for a,u in enumerate(forms):
            for b in range(a+1,len(forms)):
                v=forms[b]
                for sb in (1,-1):
                    w,s=canonical(tuple(x+sb*y for x,y in zip(u,v)))
                    if any(w) and w not in index:reps[w].append((a,b))
        # Prioritize distinct incidences, especially currently nonoutput nodes.
        mandatory={canonical(vs[o])[0] for o in c.outputs}
        incumbent={canonical(v)[0] for v in vs[c.inputs:] if any(v)}-mandatory
        def score(item):
            v,rs=item; ids={i for r in rs for i in r}
            score=(-sum(forms[i] not in mandatory and i>=c.inputs for i in ids),-len(rs),sum(bool(x) for x in v),sum(abs(x) for x in v),v)
            return (-sum(forms[i] in incumbent for i in ids),)+score if incumbent_priority else score
        candidates=sorted(((v,r) for v,r in reps.items() if len(r)>=2),key=score)
        forms.extend(v for v,r in candidates[:extra]);index={v:i for i,v in enumerate(forms)}
    prods=defaultdict(set)
    for a,u in enumerate(forms):
        for b in range(a,len(forms)):
            v=forms[b]
            for sb in (1,-1):
                w,s=canonical(tuple(x+sb*y for x,y in zip(u,v)));o=index.get(w)
                if o is not None and o>=c.inputs and o not in (a,b):prods[o].add((a,Q(s),b,Q(s*sb)))
    groups=defaultdict(list)
    for a,v in enumerate(forms):
        first=next(x for x in v if x);groups[tuple(x/first for x in v)].append((a,first))
    for group in groups.values():
        for a,x in group:
            for o,y in group:
                # A rational multiply/divide counts one only if numerator or
                # denominator is 1. Others require two literal scalar ops.
                ratio=y/x
                if a!=o and o>=c.inputs and (ratio.numerator==1 or ratio.denominator==1):prods[o].add((a,ratio,-1,Q(0)))
    outs=[(index[canonical(vs[o])[0]],canonical(vs[o])[1]) for o in c.outputs]
    return forms,{i:sorted(ps) for i,ps in prods.items()},outs,initial

def solve(forms,prods,outs,nin,bound,seconds,seed=1,hint_forms=(),workers=2,objective=False,strict=True,output_signs_free=False):
    m=cp_model.CpModel();n=len(forms)
    active=[m.new_bool_var(f'a{i}') for i in range(n)]
    neg=[m.new_bool_var(f's{i}') for i in range(n)]
    level=[m.new_int_var(0,bound,f'l{i}') for i in range(n)]
    choice={}
    for i in range(nin):m.add(active[i]==1);m.add(neg[i]==0);m.add(level[i]==0)
    for i in range(nin,n):
        opts=[]
        m.add(level[i]>=1).only_enforce_if(active[i]);m.add(level[i]==0).only_enforce_if(active[i].Not())
        for j,(a,sa,b,sb) in enumerate(prods.get(i,())):
            q=m.new_bool_var(f'g{i}_{j}');opts.append(q)
            m.add_implication(q,active[a]);m.add(level[i]>level[a]).only_enforce_if(q)
            if b<0 and strict:
                m.add(neg[i]==neg[a]).only_enforce_if(q)
            elif b>=0:
                m.add_implication(q,active[b]);m.add(level[i]>level[b]).only_enforce_if(q)
                allowed=[]
                for so in (0,1):
                    for sx in (0,1):
                        for sy in (0,1):
                            if not ((-1)**(so+sx)*sa<0 and (-1)**(so+sy)*sb<0):allowed.append((so,sx,sy))
                if strict:m.add_allowed_assignments([neg[i],neg[a],neg[b]],allowed).only_enforce_if(q)
        choice[i]=opts;m.add(sum(opts)==active[i])
    for o,s in outs:
        m.add(active[o]==1)
        if strict and not output_signs_free:m.add(neg[o]==int(s<0))
    m.add(sum(active[nin:])<=bound)
    if objective:m.minimize(sum(active[nin:]))
    hints=set(hint_forms)
    for i in range(nin,n):m.add_hint(active[i],int(forms[i] in hints))
    sol=cp_model.CpSolver();sol.parameters.max_time_in_seconds=seconds
    sol.parameters.num_search_workers=workers;sol.parameters.random_seed=seed
    start=time.monotonic();status=sol.solve(m)
    info={'status':sol.status_name(status),'seconds':time.monotonic()-start,'bound':bound,'forms':n,'productions':sum(map(len,prods.values())),'workers':workers,'seed':seed,'strict_negation_free':strict,'scope':'finite form pool only','branches':sol.num_branches,'conflicts':sol.num_conflicts}
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None,info
    selected={i:next(j for j,q in enumerate(choice[i]) if sol.value(q)) for i in range(nin,n) if sol.value(active[i])}
    ordered=sorted(selected,key=lambda i:(sol.value(level[i]),i))
    if not strict:
        c=Circuit(nin);memo={i:i for i in range(nin)}
        for i in ordered:
            a,sa,b,sb=prods[i][selected[i]]
            memo[i]=c.scale(memo[a],sa) if b<0 else c.add(c.scale(memo[a],sa),c.scale(memo[b],sb))
        c.outputs=[c.scale(memo[o],s) for o,s in outs];c.prune()
        target=[[s*x for x in forms[o]] for o,s in outs];info['cost']=c.check(target);info['selected']=len(selected);info['slp_cost']=info['cost']['additions']+info['cost']['scalar_multiplications']
        return c.slp(),info
    names={i:f'i{i}' for i in range(nin)};lines=[]
    sg=lambda i: -1 if sol.value(neg[i]) else 1
    for i in ordered:
        a,sa,b,sb=prods[i][selected[i]];name=f't{i}'
        if b<0:
            factor=sa*sg(i)*sg(a);assert factor>0
            rhs=f'{names[a]}*{factor.numerator}' if factor.denominator==1 else f'{names[a]}/{factor.denominator}'
        else:
            ca=sa*sg(i)*sg(a);cb=sb*sg(i)*sg(b)
            assert ca in (1,-1) and cb in (1,-1) and max(ca,cb)>0
            rhs=f'{names[a]}+{names[b]}' if ca==cb else (f'{names[a]}-{names[b]}' if ca>0 else f'{names[b]}-{names[a]}')
        lines.append(f'{name}:={rhs};');names[i]=name
    for k,(o,s) in enumerate(outs):
        assert output_signs_free or sg(o)==s
        lines.append(f'o{k}:={names[o]};')
    text='\n'.join(lines)+'\n';c=parse_slp(text,nin,len(outs));c.prune()
    target=[[(sg(o) if output_signs_free else s)*x for x in forms[o]] for o,s in outs];info['cost']=c.check(target)
    if output_signs_free:info['output_signs']=[sg(o)*s for o,s in outs]
    info['selected']=len(selected);info['slp_cost']=info['cost']['additions']+info['cost']['scalar_multiplications']
    return text,info

def main():
    ap=argparse.ArgumentParser();ap.add_argument('role');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--seconds',type=float,default=45);ap.add_argument('--cap',type=int,default=32);ap.add_argument('--bound',type=int);ap.add_argument('--seed',type=int,default=1);ap.add_argument('--transpose',action='store_true');ap.add_argument('--additional',type=Path);ap.add_argument('--tag');ap.add_argument('--source',type=Path);ap.add_argument('--target',type=Path);ap.add_argument('--free-signs',action='store_true');ap.add_argument('--optimize',action='store_true');a=ap.parse_args()
    path=a.source or BASE/(a.role+'.slp');mat=read_sms(a.target or BASE/(a.role+'.sms'));c=parse_slp(path.read_text(),len(mat[0]),len(mat));c.check(mat)
    if a.transpose:c=c.transposed();mat=transpose(mat)
    extra=[]
    if a.additional:
        data=json.loads(a.additional.read_text());extra=[tuple(Q(x) for x in f) for f in data['forms']]
    f,p,o,initial=make_pool(c,a.cap,extra);cost=c.cost();baseline=cost['additions']+cost['scalar_multiplications'];bound=a.bound if a.bound is not None else baseline-1
    text,info=solve(f,p,o,c.inputs,bound,a.seconds,a.seed,[canonical(v)[0] for v in values(c)],strict=not a.free_signs,objective=a.optimize)
    info.update(role=a.role,transpose=a.transpose,baseline=cost,initial=initial,extra=a.cap)
    tag=a.tag or f'{a.role}{"T" if a.transpose else ""}_cap{a.cap}_b{bound}_s{a.seed}';out=a.out;out.mkdir(parents=True,exist_ok=False)
    dump(out/'result.json',info);dump(out/'pool.json',{'forms':f,'productions':p,'outputs':o})
    if text:
        (out/'candidate.slp').write_text(text);parse_slp(text,c.inputs,len(mat)).check(mat)
        if a.transpose:(out/'direct_candidate.slp').write_text(parse_slp(text,c.inputs,len(mat)).transposed().slp())
    print(json.dumps(info),flush=True)

if __name__=='__main__':main()
