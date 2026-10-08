#!/usr/bin/env python3
"""Complete coefficient patterns for three helper wires in a signed circuit."""
from itertools import combinations, product, permutations
from collections import Counter
from pathlib import Path
import json

def patterns():
 rows=set()
 for i in range(3):
  for c in [1,2]:
   a=[0]*3;a[i]=c;rows.add(tuple(a))
 for i,j in combinations(range(3),2):
  for s in [-1,1]:
   a=[0]*3;a[i]=1;a[j]=s;rows.add(tuple(a))
 for i,j in permutations(range(3),2):
  for s in [-1,1]:
   a=[0]*3;a[i]=2;a[j]=s
   if next(x for x in a if x)<0:a=[-x for x in a]
   rows.add(tuple(a))
 for s,t in product([-1,1],repeat=2):rows.add((1,s,t))
 return sorted(rows)
def det(A):
 a,b,c=A;return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
def canon(A):
 vals=[]
 for p in permutations(range(3)):
  for s in product([-1,1],repeat=3):
   B=[]
   for row in A:
    a=tuple(row[p[j]]*s[j] for j in range(3));sg=1 if next(x for x in a if x)>0 else -1;B.append(tuple(sg*x for x in a))
   vals.append(tuple(sorted(B)))
 return min(vals)
def main():
 rows=patterns();allm=[A for A in combinations(rows,3) if det(A)];orb={canon(A) for A in allm};hist=Counter(abs(det(A)) for A in orb)
 out={'row_patterns':len(rows),'invertible_pattern_triples':len(allm),'signed_permutation_orbits':len(orb),'determinants':dict(sorted(hist.items())),'patterns':[[list(r) for r in A] for A in sorted(orb)]}
 (Path(__file__).resolve().parent/'three_helper_patterns.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='patterns'})
if __name__=='__main__':main()
