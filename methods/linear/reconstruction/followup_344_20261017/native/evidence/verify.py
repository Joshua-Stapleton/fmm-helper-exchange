#!/usr/bin/env python3
"""Verify the shared exact map, native witness and all bounded donors."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
load=lambda name:json.loads((H/name).read_text())
target=load('target.json');n=len(target[0]);assert (len(target),n)==(38,16)
lines=[l.split() for l in (H/'matrix.sms').read_text().splitlines() if l.strip() and not l.lstrip().startswith('#')]
r,c=map(int,lines[0][:2]);matrix=[[0]*c for _ in range(r)];seen=set()
for row in lines[1:]:
 a,b,v=map(int,row)
 if (a,b,v)==(0,0,0):continue
 assert 1<=a<=r and 1<=b<=c and (a,b)not in seen;seen.add((a,b));matrix[a-1][b-1]=v
assert matrix==target
roots=lambda:[[int(i==j)for j in range(n)]for i in range(n)]
def add(values,a,sa,b,sb):
 assert type(a)is int and type(b)is int and 0<=a<len(values)and 0<=b<len(values)and sa in(-1,1)and sb in(-1,1)
 value=[sa*x+sb*y for x,y in zip(values[a],values[b])];assert any(value);values.append(value)
def replay(c):
 assert c['inputs']==n;values=roots()
 for a,sa,b,sb in c['gates']:add(values,a,sa,b,sb)
 actual=[]
 for w,s in c['outputs']:
  assert type(w)is int and 0<=w<len(values)and s in(-1,1);actual.append([s*x for x in values[w]])
 assert actual==target
 return len(c['gates'])
bank=load('donors.json');assert bank['inputs']==n and len(bank['circuits'])==128
costs=[replay(c)for c in bank['circuits']];assert min(costs)==41
raw=load('representative_native_solution.json');solution=raw['solution'];assert raw['seed']==1719348 and solution['dimension']==n
values=roots()
for g in solution['substitutions']:add(values,g['i'],g['ai'],g['j'],g['aj'])
actual=[];cost=len(solution['substitutions'])
for expression in solution['expressions']:
 out=[0]*n
 for t in expression:
  w,s=t['index'],t['value'];assert type(w)is int and 0<=w<len(values)and s in(-1,1);out=[x+s*y for x,y in zip(out,values[w])]
 actual.append(out);cost+=max(0,len(expression)-1)
assert actual==target and cost==solution['additions']==41
report=load('report.json');assert report['direct_draws']==34430 and report['direct_completed']==34429
print(json.dumps(dict(status='PASS',map=[38,16],native_witness=41,donors=128,best_donor=min(costs),scope='Exact ordered signedmap only; strict paid-sign certificate verified separately.')))
