"""Independent integer replay; no optimizer or third-party library is imported."""
import hashlib
import json
from pathlib import Path


def require(value,message):
    if not value:raise ValueError(message)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())


def canonical(vector):
    first=next((x for x in vector if x),0);require(first!=0,'Zero helper unsupported')
    sign=1 if first>0 else -1
    return tuple(sign*x for x in vector),sign


def matrix(path):
    rows=[line.split()for line in Path(path).read_text().splitlines()
          if line.strip()and not line.lstrip().startswith('#')]
    m,n=map(int,rows[0][:2]);require(m>0 and n>0,'Positive matrix dimensions required')
    target=[[0]*n for _ in range(m)];seen=set()
    for tokens in rows[1:]:
        require(len(tokens)==3,'SMS triple required');i,j,x=map(int,tokens)
        if (i,j,x)==(0,0,0):continue
        require(1<=i<=m and 1<=j<=n and(i,j)not in seen,'Invalid SMS coordinate')
        seen.add((i,j));target[i-1][j-1]=x
    require(all(any(row)for row in target),'Nonzero target rows required')
    return target


def signals(gates,n,unique=False):
    require(type(n)is int and n>0,'Positive integer dimension required')
    values=[tuple(int(i==j)for j in range(n))for i in range(n)];known=set(values)
    for k,gate in enumerate(gates):
        require(isinstance(gate,list)and len(gate)==4,'Binary gate required')
        a,sa,b,sb=gate
        require(type(a)is int and type(b)is int and 0<=a<n+k and 0<=b<n+k,
                'Missing, forward or cyclic parent')
        require(type(sa)is int and type(sb)is int and sa in(-1,1)and sb in(-1,1),
                'Free scalar multiplication')
        vector=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]));form,_=canonical(vector)
        if unique:require(form not in known,'Repeated signed helper')
        known.add(form);values.append(vector)
    return values


def raw(solution,n,target=None,unique=False):
    require(solution.get('dimension',solution.get('inputs',n))==n,'Input dimension changed')
    gates=[[s['i'],s['ai'],s['j'],s['aj']]for s in solution['substitutions']]
    values=signals(gates,n,unique);expressions=solution['expressions'];actual=[]
    for expression in expressions:
        require(isinstance(expression,list)and expression,'Nonzero terminal expression required')
        row=[0]*n
        for term in expression:
            index,value=term['index'],term['value']
            require(type(index)is int and 0<=index<len(values)and type(value)is int and value in(-1,1),
                    'Invalid terminal reference/scalar')
            row=[a+value*b for a,b in zip(row,values[index])]
        actual.append(row)
    cost=len(gates)+sum(len(row)-1 for row in expressions)
    require(type(solution['additions'])is int and solution['additions']==cost,'Raw addition count changed')
    if target is not None:require(actual==target,'Ordered signed map changed')
    return dict(additions=cost,internal_substitutions=len(gates),
                terminal_additions=cost-len(gates),values=values)


def binary(program,target):
    n=len(target[0]);require(program['inputs']==n,'Binary input dimension changed')
    values=signals(program['gates'],n,unique=True);actual=[]
    for wire,sign in program['outputs']:
        require(type(wire)is int and 0<=wire<len(values)and type(sign)is int and sign in(-1,1),
                'Invalid signed output')
        actual.append([sign*x for x in values[wire]])
    require(actual==target,'Binary ordered signed map changed')
    return len(program['gates'])


def native_productions(bank,n,target):
    productions=set();helpers=set()
    for solution in bank['solutions']:
        raw(solution,n,target)
        values=signals([[s['i'],s['ai'],s['j'],s['aj']]for s in solution['substitutions']],n)
        for k,s in enumerate(solution['substitutions']):
            child,sc=canonical(values[n+k]);left,sl=canonical(values[s['i']]);right,sr=canonical(values[s['j']])
            if child in(left,right):continue
            pair=sorted([(left,s['ai']*sl*sc),(right,s['aj']*sr*sc)])
            productions.add((child,*pair));helpers.add(child)
    return productions,helpers


def prefix(program,n,productions,limit=None):
    check=raw(program,n,unique=True);require(not program['expressions'],'Prefix contains terminal outputs')
    if limit is not None:require(check['additions']<=limit,'Prefix exceeds cap')
    values=check['values']
    for k,s in enumerate(program['substitutions']):
        child,sc=canonical(values[n+k]);left,sl=canonical(values[s['i']]);right,sr=canonical(values[s['j']])
        pair=sorted([(left,s['ai']*sl*sc),(right,s['aj']*sr*sc)])
        require((child,*pair)in productions,'Prefix producer absent from native intake')
    return check['additions']
