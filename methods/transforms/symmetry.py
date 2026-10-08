"""Signed row/column equivalence: exact Gram screening and full-map replay.
Portable extraction of the historical symmetry finder; UNKNOWN is not a proof.
"""
from fractions import Fraction as Q
import collections,itertools,time
def canonical(r):
 s=next((1 if x>0 else -1 for x in r if x),1);return tuple(s*x for x in r),s
def gram(M):return [[sum(r[i]*r[j] for r in M) for j in range(len(M[0]))] for i in range(len(M[0]))]
def find(A,B,limit=12):
 A=[[Q(x) for x in r] for r in A];B=[[Q(x) for x in r] for r in B]
 if not A or not B or len(A)!=len(B) or len(A[0])!=len(B[0]):raise ValueError("shape mismatch")
 if any(len(r)!=len(A[0]) for r in A+B):raise ValueError("ragged matrix")
 start=time.process_time();GA=gram(A);GB=gram(B);n=len(GA);tried=0;nodes=0
 def labels(G):
  colors=[str((G[i][i],sorted(map(abs,G[i])))) for i in range(n)]
  for _ in range(3):colors=[str((colors[i],sorted((str(abs(G[i][j])),colors[j]) for j in range(n)))) for i in range(n)]
  return colors
 ca,cb=labels(GA),labels(GB);mapping={};used=set();answer=None
 if collections.Counter(ca)!=collections.Counter(cb):return {'status':'NON_EQUIVALENT_GRAM'}
 def test():
  nonlocal tried,answer
  tried+=1;p=[mapping[i] for i in range(n)];sign={};components=[]
  for i in range(n):
   if i in sign:continue
   sign[i]=1;comp=[i];queue=[i]
   while queue:
    a=queue.pop()
    for b in range(n):
     if not GB[a][b]:continue
     ratio=GB[a][b]/GA[p[a]][p[b]]
     if ratio not in (-1,1):return
     s=sign[a]*ratio
     if b in sign:
      if sign[b]!=s:return
     else:sign[b]=s;comp.append(b);queue.append(b)
   components.append(comp)
  idx=collections.defaultdict(list)
  for i,r in enumerate(B):idx[canonical(r)[0]].append(i)
  for flips in itertools.product((-1,1),repeat=max(0,len(components)-1)):
   ss=dict(sign)
   for comp,z in zip(components[1:],flips):
    for i in comp:ss[i]*=z
   shifted=[[r[p[j]]*ss[j] for j in range(n)] for r in A]
   if collections.Counter(canonical(r)[0] for r in shifted)!=collections.Counter(canonical(r)[0] for r in B):continue
   avail={k:v[:] for k,v in idx.items()};rp=[None]*len(B);rs=[None]*len(B)
   for ai,r in enumerate(shifted):
    key,sg=canonical(r);bi=avail[key].pop();rp[bi]=ai;rs[bi]=sg*canonical(B[bi])[1]
   cs=[ss[i] for i in range(n)]
   if any(B[i][j]!=rs[i]*cs[j]*A[rp[i]][p[j]] for i in range(len(B)) for j in range(n)):raise ValueError('full map replay failed')
   answer={'status':'EQUIVALENT','column_permutation':p,'column_signs':cs,'row_permutation':rp,'row_signs':rs,'exact_coordinates':len(B)*n};return
 def dfs():
  nonlocal nodes
  nodes+=1
  if time.process_time()-start>limit:raise TimeoutError
  if answer:return
  if len(mapping)==n:test();return
  choices=[]
  for i in range(n):
   if i in mapping:continue
   cand=[j for j in range(n) if j not in used and ca[j]==cb[i] and all(abs(GA[j][v])==abs(GB[i][k]) for k,v in mapping.items())]
   choices.append((len(cand),i,cand))
  _,i,cand=min(choices)
  for j in cand:
   mapping[i]=j;used.add(j);dfs();used.remove(j);del mapping[i]
   if answer:return
 try:dfs()
 except TimeoutError:pass
 return {**(answer or {'status':'UNKNOWN'}),'complete_gram_maps_tried':tried,'nodes':nodes,'CPU_seconds':time.process_time()-start}