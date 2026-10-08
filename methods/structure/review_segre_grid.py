#!/usr/bin/env python3
"""Independent data and mathematical-premise audit of sibling Segre grid.
Reads sibling artifacts; writes only this directory. Does not import sibling code.
"""
from pathlib import Path
from fractions import Fraction as F
from math import gcd,lcm,comb
from itertools import product,combinations
from collections import Counter
import json,hashlib
from segre_family import transform
H=Path(__file__).resolve().parent;B=H.parent/'basis'/'segre_grid_floor51'

def canon(v):
 v=tuple(v)
 for x in v:
  if x:return v if x>0 else tuple(-y for y in v)
 return v

def inspect(rows):
 rows=[tuple(F(x)for x in row)for row in rows];den=lcm(*(x.denominator for row in rows for x in row));T=sorted({canon(tuple(int(den*x)for x in row))for row in rows});ids={v:i for i,v in enumerate(T)};rels=set()
 for i in range(len(T)):
  for j in range(i,len(T)):
   for sign in (-1,1):
    v=canon(tuple(a+sign*b for a,b in zip(T[i],T[j])));k=ids.get(v)
    if k is not None and k not in(i,j):rels.add(tuple(sorted((i,j,k))))
 degree=[0]*len(T)
 for r in rels:
  for i in r:degree[i]+=1
 primitive=[]
 for row in T:
  g=gcd(*row);primitive.append(tuple(x//g for x in row))
 return T,{'targets':len(T),'triangles':len(rels),'degree':sorted(degree)},len(primitive)-len(set(primitive))

D=json.loads((H/'rank23_source.json').read_text());assert json.loads((B/'source.json').read_text())==D
vectors=sorted({canon((a,b))for a,b in product(range(-2,3),repeat=2)if gcd(a,b)==1});pairs=list(combinations(vectors,2));assert len(vectors)==8 and len(pairs)==28;assert all(p[0][0]*p[1][1]-p[0][1]*p[1][0]for p in pairs)
expected=set(product(pairs,pairs));grid=json.loads((B/'grid.json').read_text());actual=set();hist=Counter();properties=Counter();proportional=Counter();wbyq={};counts=Counter()
for row in grid:
 P=tuple(tuple(F(x)for x in r)for r in row['P']);Q=tuple(tuple(F(x)for x in r)for r in row['Q']);assert(P,Q)in expected and(P,Q)not in actual;actual.add((P,Q));ours=transform(D,P,Q)
 sig={}
 for s in 'uvw':
  factors=[[F(x)for x in r]for r in row['factors'][s]];assert factors==ours[s]
  forms,signature,prop=inspect(factors);assert signature==row['signature'][s];sig[s]=signature;proportional[s]+=prop
  if s=='w':
   if Q in wbyq:assert wbyq[Q]==forms
   else:wbyq[Q]=forms
 u,v,w=[sig[s]for s in 'uvw'];assert v['targets']==w['targets']==20 and v['triangles']<=9 and w['triangles']<=9
 assert u['targets']==21 or (u['targets']==20 and u['triangles']<=10)
 ulo=13 if u['targets']==21 and u['triangles']<12 else 12
 floor=ulo+12+13+14;assert floor==row['kernel_floor'];hist[floor]+=1;properties[(u['targets'],u['triangles'],v['triangles'],w['triangles'])]+=1
assert actual==expected and len(grid)==784 and len(wbyq)==28
cases=json.loads((B/'decoder_results.json').read_text());qs=set();helper_counts=Counter();coverage=0;closures=0
for row in cases:
 Q=tuple(tuple(F(x)for x in r)for r in row['Q']);assert Q not in qs;qs.add(Q)
 # Check each native input matches exact decoder factors, with common scale.
 words=list(map(int,(B/'decoder_inputs'/row['input']).read_text().split()));assert words[:2]==[20,9];T=[tuple(words[2+i*9:2+(i+1)*9])for i in range(20)];ours=wbyq[Q]
 scale=next(F(y,x)for r,t in zip(ours,T)for x,y in zip(r,t)if x)
 assert all(F(y)==scale*x for r,t in zip(ours,T)for x,y in zip(r,t))
 assert all(x%2==0 for r in T for x in r);helpers={canon(tuple(x//2 for x in t))for t in T}
 for a,b in combinations(range(20),2):
  for sign in (-1,1):helpers.add(canon(tuple(x+sign*y for x,y in zip(T[a],T[b]))))
 helpers.update(canon(tuple(2*x for x in t))for t in T);helpers.discard((0,)*9);helpers-=set(T)
 r=row['native_result'];assert r['status']=='PASS'and r['no_12_gate_circuit'];assert len(helpers)==r['helpers'];assert r['root_subsets_per_helper']==comb(20,8)+comb(20,9)==293930
 assert r['covered_root_subsets']==len(helpers)*293930;assert r['max_targets_reached']<20;helper_counts[len(helpers)]+=1;coverage+=r['covered_root_subsets'];closures+=r['distinct_closure_tests']
assert qs==set(wbyq)
result={'status':'PASS','independent_of_sibling_verifier':True,'exact_grid_completeness':{'directions':len(vectors),'bases':len(pairs),'P_Q_pairs':len(actual)},'all_saved_factors_match_independent_tensor_preserving_constructor':True,'all_signatures_match_independent_integer_relations':True,'nonunit_proportional_target_pairs':dict(proportional),'floor_histogram':dict(hist),'decoder_Q_cases':len(qs),'helper_count_histogram':dict(helper_counts),'root_helper_cases':coverage,'distinct_native_closures_reviewed':closures,'native_algorithm_review':'Closure recurrence, all helper types, and both root cases reviewed; no independent native exhaustive rerun in this audit','scope':'Finite exact784 transforms; separate signed addition/subtraction SLPs, arbitrary rational coordinate bases, fixed term scales, free copies/signs, paid conversions excluded'}
(H/'segre_grid_independent_review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
