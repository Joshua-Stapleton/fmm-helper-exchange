#!/usr/bin/env python3
"""Bounded exact-DAG scheduling and register allocation; source arithmetic fixed."""
from pathlib import Path
from fractions import Fraction as Q
import argparse,json,sys,time,random
HERE=Path(__file__).resolve().parent

def bits(mask):
    while mask:
        bit=mask&-mask; yield bit.bit_length()-1; mask^=bit

def setup(d):
    N=d['inputs']; nn=len(d['nodes']);req=[];succ=[0]*nn
    for i,node in enumerate(d['nodes']):
        mask=sum(1<<(a-N) for a in {node[k] for k in ('a','b') if k in node} if a>=N);req.append(mask)
        for j in bits(mask):succ[j]|=1<<i
    hold=sum(1<<(a-N) for a in {a for a,s in d['outputs']} if a>=N)
    ready=sum(1<<i for i,m in enumerate(req) if not m)
    return req,succ,hold,ready

def replay_order(d,order,destructive=True,mutable_inputs=False):
    N=d['inputs'];nn=len(d['nodes']);assert sorted(order)==list(range(nn));req,succ,hold,_=setup(d)
    uses={i:set() for i in range(N+nn)}
    for j,node in enumerate(d['nodes'],N):
        for k in ('a','b'):
            if k in node:uses[node[k]].add(j)
    retained={a for a,s in d['outputs']};wire_slots={};free=[];capacity=0;records=[];done=set()
    if mutable_inputs:
        wire_slots={i:i for i in range(N)};capacity=N
    for ix in order:
        node=d['nodes'][ix];wire=N+ix;deps={node[k] for k in ('a','b') if k in node}
        assert all(x<N or x in done for x in deps)
        reclaim=[x for x in sorted(deps) if x in wire_slots and x not in retained and uses[x]=={wire}]
        chosen=reclaim[0] if destructive and reclaim else None
        reads={k:({'slot':wire_slots[node[k]]} if node[k] in wire_slots else {'input':node[k]}) for k in ('a','b') if k in node}
        if chosen is not None:slot=wire_slots[chosen]
        elif free:slot=free.pop(0)
        else:slot=capacity;capacity+=1
        for old in reclaim:
            oldslot=wire_slots.pop(old)
            if old!=chosen:free.append(oldslot)
        wire_slots[wire]=slot;free.sort()
        for x in deps:uses[x].remove(wire)
        done.add(wire);records.append({'node':ix,'destination_slot':slot,'reads':reads,'reused_wire':chosen,'released_wires':reclaim})
    out=[]
    for a,s in d['outputs']:
        out.append({'slot':wire_slots[a]} if a in wire_slots else {'input':a})
    return {'peak_slots':capacity,'final_distinct_output_slots':len({v['slot'] for v in out if 'slot' in v}),
            'destructive_reuse':destructive,'inputs_mutable':mutable_inputs,'order':order,'instructions':records,'outputs':out}

def beam(d,width,seconds,seed=None):
    req,succ,hold,ready=setup(d);nn=len(req);start=time.monotonic()
    # done, ready, live, peak, order. Reclaim is valid only on the last read.
    states=[(0,ready,0,0,())]; expanded=0;last_depth=0
    priority=list(range(nn))
    if seed is not None:random.Random(seed).shuffle(priority)
    baseline=replay_order(d,list(range(nn)))['peak_slots']
    for depth in range(nn):
        unique={}
        for done,ready,live,peak,order in states:
            for node in bits(ready):
                bit=1<<node;nd=done|bit;freed=0
                for dep in bits(req[node]&~hold):
                    if not(succ[dep]&~nd):freed|=1<<dep
                np=max(peak,live.bit_count()+(not freed))
                if np>baseline:continue
                nl=(live|bit)&~freed;nr=ready&~bit
                for child in bits(succ[node]):
                    if not(req[child]&~nd):nr|=1<<child
                record=(nd,nr,nl,np,order+(node,));prior=unique.get(nd)
                if prior is None or np<prior[3]:unique[nd]=record
                expanded+=1
        states=sorted(unique.values(),key=lambda s:(s[3],s[2].bit_count(),(s[2]&~hold).bit_count(),tuple(priority[i] for i in s[4])))[:width]
        last_depth=depth+1
        if not states or time.monotonic()-start>seconds:break
    if states and last_depth==nn:
        winner=min(states,key=lambda s:s[3]);order=list(winner[4]);peak=winner[3]
    else:order=list(range(nn));peak=baseline
    return order,{'width':width,'seed':seed,'seconds':time.monotonic()-start,'expanded_transitions':expanded,'depth_completed':last_depth,
                  'peak':peak,'optimality':'bounded beam upper bound; not a global schedule-optimality proof'}

def emit(d,order):
    N=d['inputs'];name=lambda i:'i'+str(i) if i<N else 't'+str(i-N);lines=[]
    for j in order:
        node=d['nodes'][j]
        if node['op']=='add':
            a,b,sa,sb=node['a'],node['b'],node['sa'],node['sb']
            if sa==sb==1:e=name(a)+'+'+name(b)
            elif sa==1:e=name(a)+'-'+name(b)
            else:e=name(b)+'-'+name(a)
        elif node['op']=='scale':e=name(node['a'])+'*('+str(node['q'])+')'
        else:e='0'
        lines.append(name(N+j)+':='+e+';')
    lines.extend(f'o{i}:={name(a)};' for i,(a,s) in enumerate(d['outputs']))
    return '\n'.join(lines)+'\n'

def combine(A,B):
    # Distinct external inputs and disjoint arithmetic DAGs.
    ni=A['inputs']+B['inputs'];na=len(A['nodes']);nodes=[]
    def remap(a,d,side):
        if a<d['inputs']:return a+(A['inputs'] if side else 0)
        return ni+(na if side else 0)+a-d['inputs']
    for side,d in enumerate((A,B)):
        for node in d['nodes']:
            node=dict(node)
            for k in ('a','b'):
                if k in node:node[k]=remap(node[k],d,side)
            nodes.append(node)
    return {'inputs':ni,'nodes':nodes,'outputs':[(remap(a,d,side),s) for side,d in enumerate((A,B)) for a,s in d['outputs']]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--graph',type=Path,default=HERE/'certificate_204_storage_19/P_certificate.json')
    ap.add_argument('--width',type=int,default=600);ap.add_argument('--seconds',type=float,default=30);ap.add_argument('--seed',type=int,default=30);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();data=json.loads(args.graph.read_text());d=data.get('graph',data)
    order,search=beam(d,args.width,args.seconds,args.seed)
    replay=replay_order(d,order)
    result={'search':search,'allocation':replay,'source_sha256':__import__('hashlib').sha256(args.graph.read_bytes()).hexdigest()}
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'schedule.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.out/'scheduled.slp').write_text(emit(d,order))
    print(json.dumps({'peak_slots':replay['peak_slots'],'search':search},indent=2))
if __name__=='__main__':main()
