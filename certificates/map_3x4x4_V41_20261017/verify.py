#!/usr/bin/env python3
"""Independent exact integer replay of the original map, literal text and JSON."""
import hashlib,json,re
from pathlib import Path
H=Path(__file__).resolve().parent
def verify():
 rows=[line.split() for line in (H/'V.sms').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
 m,n=map(int,rows[0][:2]);assert(m,n)==(38,16)
 target=[[0]*n for _ in range(m)];seen=set()
 for row in rows[1:]:
  i,j,x=map(int,row)
  if(i,j,x)==(0,0,0):continue
  assert 1<=i<=m and 1<=j<=n and(i,j)not in seen
  seen.add((i,j));target[i-1][j-1]=x
 assert target==json.loads((H/'matrix.json').read_text())
 env={f'i{i}':tuple(int(i==j)for j in range(n))for i in range(n)};deps={};gates=0
 for line in(H/'certificate.slp').read_text().splitlines():
  match=re.fullmatch(r'([to]\d+):=([it]\d+)(?:([+-])([it]\d+))?;',line.strip());assert match
  out,a,op,b=match.groups();assert out not in env and a in env and(b is None or b in env)
  env[out]=env[a]if op is None else tuple(x+(1 if op=='+'else-1)*y for x,y in zip(env[a],env[b]))
  deps[out]={a}if b is None else{a,b};gates+=op is not None
 assert set(k for k in env if k.startswith('o'))=={f'o{i}'for i in range(m)}
 assert [list(env[f'o{i}'])for i in range(m)]==target and gates==41
 live={f'o{i}'for i in range(m)};todo=list(live)
 while todo:
  for p in deps.get(todo.pop(),()):
   if p not in live:live.add(p);todo.append(p)
 assert set(deps)<=live
 c=json.loads((H/'circuit.json').read_text());assert c['inputs']==n and len(c['gates'])==41
 values=[tuple(int(i==j)for j in range(n))for i in range(n)]
 for a,sa,b,sb in c['gates']:
  assert type(a)is int and type(b)is int and 0<=a<len(values)and 0<=b<len(values)
  assert sa in(-1,1)and sb in(-1,1)and(sa==1 or sb==1)
  values.append(tuple(sa*x+sb*y for x,y in zip(values[a],values[b])))
 assert all(s==1 for w,s in c['outputs'])
 assert [list(values[w])for w,s in c['outputs']]==target
 return dict(status='PASS',rows=m,inputs=n,coefficients=m*n,additions_subtractions=gates,extra_unary_negations=0,basis_change=False,scope='Fixed ordered V map, not a complete tensor or global optimum',sms_sha256=hashlib.sha256((H/'V.sms').read_bytes()).hexdigest())
if __name__=='__main__':print(json.dumps(verify(),indent=2))
