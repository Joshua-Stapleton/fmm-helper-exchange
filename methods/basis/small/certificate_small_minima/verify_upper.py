"""Independent exact replay of the retained small-scheme witnesses."""
from pathlib import Path
from fractions import Fraction as Q
from itertools import product
import json,hashlib
HERE=Path(__file__).resolve().parent
def transpose(a):return list(map(list,zip(*a)))
def matmul(a,b):return [[sum(Q(x)*Q(y)for x,y in zip(r,c))for c in zip(*b)]for r in a]
def rank(a):
 a=[list(map(Q,r))for r in a];k=0
 for j in range(len(a[0])):
  i=next((i for i in range(k,len(a))if a[i][j]),None)
  if i is None:continue
  a[k],a[i]=a[i],a[k];z=a[k][j];a[k]=[x/z for x in a[k]]
  for i in range(len(a)):
   if i!=k:
    z=a[i][j];a[i]=[x-z*y for x,y in zip(a[i],a[k])]
  k+=1
 return k
def matrix(c):
 n=c['inputs'];v=[[Q(i==j)for j in range(n)]for i in range(n)];counts={'additions':0,'free_negations':0}
 for node in c['nodes']:
  op=node['op'];a=v[node['a']]
  if op=='scale':
   s=Q(node['c']);assert s in [-1,1];v.append([s*x for x in a]);counts['free_negations']+=s==-1
  else:
   assert op in ['add','sub'];s=1 if op=='add'else-1;v.append([x+s*y for x,y in zip(a,v[node['b']])]);counts['additions']+=1
 return [v[i]for i in c['outputs']],counts
def main():
 result={}
 for shape,expected in [('224',[3,6,12]),('233',[9,11,18]),('234',[12,12,24]),('234_46',[10,12,24])]:
  p=HERE/f'scheme{shape}.json';d=json.loads(p.read_text());source=d['source'];dims=source['n'];r=source['m'];maps={};counts={}
  for side in 'uvw':
   inner=[[Q(x)for x in row]for row in d['inner_forward'][side]];outer=[[Q(x)for x in row]for row in d['outer_matrices'][side]]
   assert rank(outer)==len(outer)==len(outer[0])
   assert matmul(inner,outer if side!='w'else transpose(outer))==source[side];M,c=matrix(d['kernel'][side]);assert M==(inner if side!='w'else transpose(inner));maps[side]=M;counts[side]=c
  assert [counts[s]['additions']for s in 'uvw']==expected
  n,m,k=dims;eqs=0
  for a,b,c in product(range(n*m),range(m*k),range(k*n)):
   wanted=int(a//m==c%n and a%m==b//k and b%k==c//n)
   assert sum(Q(source['u'][t][a])*Q(source['v'][t][b])*Q(source['w'][t][c])for t in range(r))==wanted;eqs+=1
  result[shape]={'status':'PASS','rank':r,'kernel_additions':sum(expected),'split':counts,'exact_tensor_coefficients':eqs,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'model':'Signed binary addition/subtraction with free signs and copies; no nonunit scalar gates. Boundary conversions excluded.'}
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
