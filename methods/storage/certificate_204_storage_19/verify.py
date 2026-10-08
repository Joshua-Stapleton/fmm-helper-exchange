#!/usr/bin/env python3
"""Standalone rational replay and destructive-allocation checker; stdlib only."""
from pathlib import Path
from fractions import Fraction as Q
import ast,collections,hashlib,itertools,json,re
from strict_replay import replay,load_sms
HERE=Path(__file__).resolve().parent

def source_graph(text,n,m):
    env={f'i{i}':('w',i) for i in range(n)};nodes=[]
    def expr(t):
        if isinstance(t,ast.Name):return env[t.id]
        if isinstance(t,ast.Constant):assert type(t.value)is int;return ('c',Q(t.value))
        if isinstance(t,ast.UnaryOp):
            kind,a=expr(t.operand);assert kind=='c';return('c',-a if isinstance(t.op,ast.USub) else a)
        assert isinstance(t,ast.BinOp);ak,a=expr(t.left);bk,b=expr(t.right)
        if ak==bk=='c':
            if isinstance(t.op,ast.Add):v=a+b
            elif isinstance(t.op,ast.Sub):v=a-b
            elif isinstance(t.op,ast.Mult):v=a*b
            else:assert isinstance(t.op,ast.Div);v=a/b
            return 'c',v
        if isinstance(t.op,(ast.Add,ast.Sub)):
            assert ak==bk=='w';node={'op':'add','a':a,'sa':1,'b':b,'sb':1 if isinstance(t.op,ast.Add) else -1}
        else:
            if isinstance(t.op,ast.Div):assert ak=='w' and bk=='c';a,q=a,1/b
            else:assert isinstance(t.op,ast.Mult) and ak!=bk;a,q=(a,b) if ak=='w' else(b,a)
            assert q not in(0,1,-1);node={'op':'scale','a':a,'q':str(q)}
        nodes.append(node);return'w',n+len(nodes)-1
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        lhs,rhs=line.rstrip(';').split(':=');env[lhs.strip()]=expr(ast.parse(rhs.strip(),mode='eval').body)
    return {'inputs':n,'nodes':nodes,'outputs':[[env[f'o{i}'][1],1] for i in range(m)]}

def apply(node,a,b=None):
    if node['op']=='add':return [node['sa']*x+node['sb']*y for x,y in zip(a,b)]
    assert node['op']=='scale';return [Q(node['q'])*x for x in a]

def verify_allocation(d,certificate):
    n=d['inputs'];nodes=d['nodes'];inputs=[[Q(i==j) for j in range(n)] for i in range(n)]
    values=inputs[:]
    for node in nodes:values.append(apply(node,values[node['a']],values[node['b']] if 'b' in node else None))
    retained={a for a,s in d['outputs']};uses={i:set() for i in range(len(values))}
    for j,node in enumerate(nodes,n):
        for k in ('a','b'):
            if k in node:uses[node[k]].add(j)
    mutable=certificate['inputs_mutable'];wire_slot={i:i for i in range(n)} if mutable else {};slot_wire={i:i for i in range(n)} if mutable else {}
    memory={i:inputs[i] for i in range(n)} if mutable else {};seen=set();peak=n if mutable else 0;max_slot=n-1 if mutable else -1
    order=certificate['order'];assert sorted(order)==list(range(len(nodes)))
    assert [r['node'] for r in certificate['instructions']]==order
    for record in certificate['instructions']:
        j=record['node'];wire=n+j;node=nodes[j];deps={node[k] for k in('a','b') if k in node}
        assert all(x<n or x in seen for x in deps)
        arguments={}
        for k in('a','b'):
            if k not in node:continue
            dep=node[k];where=record['reads'][k]
            if 'input' in where:assert not mutable and dep<n and where['input']==dep;value=inputs[dep]
            else:assert wire_slot[dep]==where['slot'];value=memory[where['slot']]
            assert value==values[dep];arguments[k]=value
        destination=record['destination_slot'];victim=slot_wire.get(destination)
        reclaim={x for x in deps if x in wire_slot and x not in retained and uses[x]=={wire}}
        assert set(record['released_wires'])==reclaim
        if victim is not None:
            assert certificate['destructive_reuse'] and victim in reclaim and record['reused_wire']==victim
        else:assert record['reused_wire'] is None
        peak=max(peak,len(slot_wire)+(victim is None));max_slot=max(max_slot,destination)
        answer=apply(node,arguments['a'],arguments.get('b'));assert answer==values[wire]
        for old in reclaim:
            slot=wire_slot.pop(old);slot_wire.pop(slot);memory.pop(slot)
        memory[destination]=answer;slot_wire[destination]=wire;wire_slot[wire]=destination
        for dep in deps:uses[dep].remove(wire)
        seen.add(wire)
    assert peak==certificate['peak_slots']==max_slot+1
    actual=[]
    for (wire,sgn),where in zip(d['outputs'],certificate['outputs']):
        assert sgn==1
        if 'input'in where:assert wire<n and where['input']==wire;v=inputs[wire]
        else:assert wire_slot[wire]==where['slot'];v=memory[where['slot']]
        assert v==values[wire];actual.append(v)
    return peak,actual

def main():
    results={};matrices={};counts={}
    for role in'LRP':
        c=json.loads((HERE/(role+'_certificate.json')).read_text());d=c['graph'];n=d['inputs'];m=len(d['outputs'])
        original=(HERE/(role+'_original.slp')).read_text();scheduled=(HERE/(role+'_scheduled.slp')).read_text()
        assert source_graph(original,n,m)==d,'DAG differs from original program: '+role
        M=load_sms(HERE/(role+'.sms'));matrices[role]=M
        old,oc=replay(original,n,m);new,nc=replay(scheduled,n,m);assert old==new==M and oc==nc==c['arithmetic_counts'];counts[role]=nc
        results[role]={}
        for label,allocation in c['allocations'].items():
            peak,actual=verify_allocation(d,allocation);assert actual==M;results[role][label]=peak
    joint=json.loads((HERE/'joint_input_certificate.json').read_text())
    for label in('serial','interleaved'):
        peak,actual=verify_allocation(joint['graph'],joint[label]);assert peak==76
        assert actual==[r+[Q(0)]*16 for r in matrices['L']]+[[Q(0)]*16+r for r in matrices['R']]
    for role in'LR':
        rows=matrices[role];nonalias=[tuple(r) for r in rows if sum(x!=0 for x in r)>1]
        assert len(nonalias)==len(set(nonalias))==38
        assert sum(sum(x!=0 for x in r)==1 and max(r)==1 and min(r)==0 for r in rows)==10
    values=collections.defaultdict(Q)
    for t in range(48):
        for a,x in enumerate(matrices['L'][t]):
            if not x:continue
            for b,y in enumerate(matrices['R'][t]):
                if not y:continue
                for c,row in enumerate(matrices['P']):
                    if row[t]:values[a,b,c]+=x*y*row[t]
    for a,b,c in itertools.product(range(16),repeat=3):
        i,j=divmod(a,4);jj,k=divmod(b,4);assert values[a,b,c]==int(j==jj and c==4*i+k)
    # Check the actual generated C assignments and output/scratch bindings.
    p=json.loads((HERE/'P_certificate.json').read_text());alloc=p['allocations']['chosen_destructive'];code=(HERE/'P_scheduled.c').read_text()
    binding=re.search(r'double \*slot\[(\d+)\] = \{([^}]+)\};',code);assert int(binding[1])==alloc['peak_slots']
    names=[s.strip() for s in binding[2].split(',')]
    assert len(set(names))==len(names)==alloc['peak_slots']
    for i,where in enumerate(alloc['outputs']):assert names[where['slot']]==f'output[{i}]'
    assert sum(s.startswith('scratch[') for s in names)==alloc['peak_slots']-16
    loops=re.findall(r'for \(size_t j=0; j<length; \+\+j\) slot\[(\d+)\]\[j\] = ([^;]+);',code)
    assert len(loops)==90
    def cref(where):return f"products[{where['input']}][j]" if 'input'in where else f"slot[{where['slot']}][j]"
    for (destination,expression),ins in zip(loops,alloc['instructions']):
        node=p['graph']['nodes'][ins['node']];a,b=cref(ins['reads']['a']),cref(ins['reads']['b'])
        expected=a+' + '+b if node['sa']==node['sb']==1 else a+' - '+b if node['sa']==1 else b+' - '+a
        assert expression==expected and int(destination)==ins['destination_slot']
    result={'status':'PASS','storage_peaks':results,'arithmetic':counts,'total_linear_operations':sum(sum(v.values()) for v in counts.values()),
        'tensor_coefficients_checked':4096,'input_lower_bound_and_attained':76,'scope':'Specified fixed DAG and atomic-operation allocation model; no wall-time, bandwidth, or whole-recursion claim.',
        'C_assignments_exactly_match_verified_allocation':90,
        'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*_scheduled.slp')}}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
