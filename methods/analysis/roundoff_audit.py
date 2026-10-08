#!/usr/bin/env python3
"""Exact first-order roundoff majorants for literal one-level bilinear SLPs.

Assume |A_ij|,|B_ij|<=1, exact input data, round-to-nearest operations, and
no overflow/underflow. Powers of two and signs are exact. An addition or a
non-power-of-two scaling gets one independent local relative-error symbol.
The result bounds max-entry error by C*u+O(u**2), not an all-orders theorem.
Local errors are propagated through the exact complete downstream map, so
reconvergent paths can cancel before absolute values are taken.
"""
import ast, hashlib, json
from fractions import Fraction as Q
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def plus(a,b,c=Q(1)):
    out=a.copy()
    for k,v in b.items():
        out[k]=out.get(k,Q(0))+c*v
        if not out[k]:del out[k]
    return out

def scale(a,c):return {k:v*c for k,v in a.items() if v*c}
def norm(a):return sum(map(abs,a.values()),Q(0))
def pow2(q):
    q=abs(q)
    return q and q.numerator&(q.numerator-1)==0 and q.denominator&(q.denominator-1)==0

class Circuit:
    def __init__(self,n):
        self.n=n;self.env={f'i{i}':({i:Q(1)}, {}) for i in range(n)}
        self.sites=[];self.pre_errors=[];self.stage_outputs=[];self.programs=[]
    def local(self,form,errors):
        j=len(self.sites);self.sites.append(form.copy());self.pre_errors.append(errors.copy());errors=errors.copy();errors[j]=Q(1)
        return form,errors
    def evaluate(self,node):
        if isinstance(node,ast.Name):return self.env[node.id]
        if isinstance(node,ast.UnaryOp):
            f,e=self.evaluate(node.operand);c=-1 if isinstance(node.op,ast.USub) else 1
            return scale(f,c),scale(e,c)
        if isinstance(node,ast.BinOp):
            f,e=self.evaluate(node.left)
            if isinstance(node.op,(ast.Add,ast.Sub)):
                g,h=self.evaluate(node.right);c=-1 if isinstance(node.op,ast.Sub) else 1
                return self.local(plus(f,g,c),plus(e,h,c))
            c=Q(ast.literal_eval(node.right))
            if isinstance(node.op,ast.Div):c=1/c
            else:assert isinstance(node.op,ast.Mult)
            f,e=scale(f,c),scale(e,c)
            return (f,e) if pow2(c) else self.local(f,e)
        raise ValueError(ast.dump(node))
    def append(self,path):
        program=[];outputs={}
        for line in Path(path).read_text().splitlines():
            line=line.split('#')[0].strip()
            if ':=' not in line:continue
            lhs,rhs=map(str.strip,line.rstrip(';').split(':='));node=ast.parse(rhs,mode='eval').body
            self.env[lhs]=self.evaluate(node);program.append((lhs,node))
            if lhs.startswith('o'):outputs[int(lhs[1:])]=self.env[lhs]
        ys=[outputs[i] for i in range(len(outputs))]
        self.stage_outputs.append(ys);self.programs.append(program)
        self.env={f'i{i}':v for i,v in enumerate(ys)}
        return self
    @property
    def outputs(self):return self.stage_outputs[-1]
    def float_eval(self,x):
        def calc(node,env):
            if isinstance(node,ast.Name):return env[node.id]
            if isinstance(node,ast.UnaryOp):return -calc(node.operand,env) if isinstance(node.op,ast.USub) else calc(node.operand,env)
            a=calc(node.left,env)
            if isinstance(node.op,(ast.Add,ast.Sub)):
                b=calc(node.right,env);return a+b if isinstance(node.op,ast.Add) else a-b
            b=x.dtype.type(ast.literal_eval(node.right))
            return a*b if isinstance(node.op,ast.Mult) else a/b
        import numpy as np
        for program in self.programs:
            env={f'i{i}':x[:,i] for i in range(x.shape[1])};out={}
            for lhs,node in program:
                env[lhs]=calc(node,env)
                if lhs.startswith('o'):out[int(lhs[1:])]=env[lhs]
            x=np.stack([out[i] for i in range(len(out))],axis=1)
        return x

def circuit(paths,n):
    c=Circuit(n)
    for p in paths:c.append(p)
    return c

def cases():
    d=HERE.parent/'basis/certificate_4x4_169_43'
    yield 'alt_169_43',[d/'CoB_L.slp',d/'ALT_L.slp'],[d/'CoB_R.slp',d/'ALT_R.slp'],[d/'ALT_P.slp',d/'CoB_P.slp']

def analyze(name,lp,rp,pp):
    L,R=circuit(lp,16),circuit(rp,16);rank=len(L.outputs);P=circuit(pp,rank)
    U=[f for f,e in L.outputs];V=[f for f,e in R.outputs];W=[f for f,e in P.outputs]
    products=[{(a,b):x*y for a,x in u.items() for b,y in v.items()} for u,v in zip(U,V)]
    def polynomial(row):
        out={}
        for i,w in row.items():out=plus(out,products[i],w)
        return out
    def input_bound(C,other,w):
        total=Q(0)
        for j,site in enumerate(C.sites):
            sensitivity={}
            for i,weight in w.items():
                c=C.outputs[i][1].get(j,Q(0))*weight
                if c:sensitivity=plus(sensitivity,other[i],c)
            total+=norm(site)*norm(sensitivity)
        return total
    result=[]
    for o,w in enumerate(W):
        actual=polynomial(w);i,k=divmod(o,4)
        assert actual=={(4*i+j,4*j+k):Q(1) for j in range(4)},(name,o)
        left=input_bound(L,V,w);right=input_bound(R,U,w)
        mult=sum((abs(v)*norm(products[i]) for i,v in w.items()),Q(0))
        decode=sum((abs(c)*norm(polynomial(P.sites[j])) for j,c in P.outputs[o][1].items()),Q(0))
        result.append({'L':str(left),'R':str(right),'products':str(mult),'P':str(decode),'total':str(left+right+mult+decode)})
    return {'name':name,'max_first_order_coefficient':str(max(Q(x['total']) for x in result)),
            'per_output':result,'rounded_sites':[len(L.sites),len(R.sites),len(P.sites)],
            'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in lp+rp+pp}},(L,R,P)

def main():
    results=[]
    for name,l,r,p in cases():
        item,_=analyze(name,l,r,p);results.append(item)
        print(name,item['max_first_order_coefficient'],item['rounded_sites'],flush=True)
    report={'model':__doc__,'results':results}
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
