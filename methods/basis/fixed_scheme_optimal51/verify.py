#!/usr/bin/env python3
"""Reproduce fixed-scaled-scheme 333 addition-only kernel optimality at 51.

Python standard library only. Source coefficients are re-derived from the exact
51-addition circuit and its complete multiplication identity is verified first.
The lower bound allows arbitrary independent input/output bases, but no nonunit
scalar gates or free nonunit rank-term rescalings in the kernel.
"""
from pathlib import Path
from fractions import Fraction as Q
from itertools import combinations
from functools import lru_cache
import json,hashlib,sys,time,math
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
from verify_source import verify,replay
started=time.monotonic();manifest=json.loads((H/'manifest.json').read_text())
for name,expected in manifest['sha256'].items():
 assert hashlib.sha256((H/name).read_bytes()).hexdigest()==expected,name
source=json.loads((H/'333.json').read_text());source_check=verify(source)
assert source['dimensions']==[3,3,3] and source['rank']==23
assert source['expected']['kernel']==51

def rank(A):
 a=[list(r) for r in A];r=0
 for j in range(len(a[0])):
  p=next((i for i in range(r,len(a)) if a[i][j]),None)
  if p is None:continue
  a[r],a[p]=a[p],a[r];q=a[r][j];a[r]=[x/q for x in a[r]]
  for i in range(len(a)):
   if i!=r:
    q=a[i][j];a[i]=[x-q*y for x,y in zip(a[i],a[r])]
  r+=1
 return r

def canon(v):
 sign=next((1 if x>0 else -1 for x in v if x),1)
 return tuple(sign*x for x in v)

def rules(forms):
 ids={v:i for i,v in enumerate(forms)};r=set()
 for i,u in enumerate(forms):
  for j in range(i,len(forms)):
   for s in (-1,1):
    w=canon(tuple(x+s*y for x,y in zip(u,forms[j])));o=ids.get(w)
    if o is not None and o not in (i,j):r.add(((1<<i)|(1<<j),1<<o))
 return tuple(sorted(r))

def initial_masks(k):
 for ids in combinations(range(20),k):yield sum(1<<i for i in ids)

FULL=(1<<20)-1;HB=1<<20;checks={};source_costs={}
for role,ni,no in [('U',9,23),('V',9,23),('W',23,9)]:
 M,cost=replay(source['maps'][role],ni,no,role);source_costs[role]=cost
 assert cost['nonunit_scalars']==0 and cost['additions']=={'U':12,'V':12,'W':27}[role]
 if role=='W':
  assert rank(M)==9 and all(any(col) for col in zip(*M))
  M=[list(col) for col in zip(*M)]
 assert rank(M)==9 and all(x.denominator==1 and abs(x)<=1 for row in M for x in row)
 # Global factor two keeps half-target candidates integral without changing
 # any linear addition relation or gate cost.
 F=sorted({canon(tuple(int(2*x) for x in row)) for row in M if any(row)})
 assert len(F)==20;rr=rules(F)
 @lru_cache(None)
 def close(mask):
  for need,out in rr:
   if mask&need==need and not mask&out:return close(mask|out)
  return mask
 roots9={close(mask) for mask in initial_masks(9)}
 assert FULL not in roots9
 check={'unique_signed_targets':20,'rank':9,'base_rules':len(rr),'root9_subsets_covered':math.comb(20,9),'distinct_root9_closures':len(roots9),'largest_root9_closure':max(x.bit_count() for x in roots9),'no_11_gate_circuit':True}
 if role=='W':
  text=(H/'W_targets_scaled2.txt').read_text().split();assert list(map(int,text[:2]))==[20,9]
  imported=[tuple(map(int,text[2+9*i:2+9*(i+1)])) for i in range(20)]
  assert imported==F,'Independent C++ input differs from the supplied 51 circuit'
  roots8={close(mask) for mask in initial_masks(8)}
  helpers=set()
  for i,u in enumerate(F):
   assert all(x%2==0 for x in u);helpers.add(canon(tuple(x//2 for x in u)))
   for v in F[i:]:
    for s in (-1,1):helpers.add(canon(tuple(x+s*y for x,y in zip(u,v))))
  helpers.discard((0,)*9);helpers-=set(F);assert len(helpers)==358
  cases=0;largest=0;per_helper=[]
  for helper in sorted(helpers):
   extra=tuple((need,out) for need,out in rules(F+[helper]) if (need|out)&HB)
   reached=0
   for family,with_h in [(roots9,False),(roots8,True)]:
    for seed in family:
     mask=seed|(HB if with_h else 0)
     while True:
      before=mask
      for need,out in extra:
       if mask&need==need and not mask&out:
        mask|=out;mask=(mask&HB)|close(mask&FULL)
      if before==mask:break
     assert mask&FULL!=FULL,('12-gate witness',helper,seed,with_h)
     reached=max(reached,(mask&FULL).bit_count());cases+=1
   largest=max(largest,reached);per_helper.append([list(helper),len(extra),reached])
  assert cases==4918562 and largest==19
  digest=hashlib.sha256(json.dumps(per_helper,separators=(',',':')).encode()).hexdigest()
  check.update({'helper_candidates':len(helpers),'root8_subsets_covered':math.comb(20,8),'distinct_root8_closures':len(roots8),'covered_root_subsets_with_helpers':len(helpers)*(math.comb(20,8)+math.comb(20,9)),'distinct_closure_tests':cases,'max_targets_reached':largest,'per_helper_digest':digest,'no_12_gate_circuit':True,'transposed_decoder_lower_bound':13})
 checks[role]=check
result={'status':'PASS','source_sha256':hashlib.sha256((H/'333.json').read_bytes()).hexdigest(),'source_verification':source_check,'source_kernel_additions':51,'source_kernel_split':[12,12,27],'source_costs':source_costs,'closure_checks':checks,'decoder_all23_product_inputs_used':True,'decoder_rank':9,'transposition_offset':14,'fixed_scaled_scheme_kernel_lower_bound':51,'lower_bound_split':[12,12,27],'optimal_in_stated_class':True,'field':'Q','kernel_model':'three separate linear factor SLPs; addition/subtraction only; copies/signs/fanout free; no nonunit scalings','basis_scope':'arbitrary independent invertible9-dimensional input/output basis changes; boundary costs excluded','excluded_scope':'cross-factor or cross-degree sharing, nonunit rank-term rescalings, different decompositions, nonlinear kernels, unrestricted matrix multiplication','seconds':time.monotonic()-started}
print(json.dumps(result,indent=2))
