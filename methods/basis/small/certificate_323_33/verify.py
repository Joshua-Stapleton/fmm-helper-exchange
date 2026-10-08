"""Independent exact replay of the retained small-scheme witnesses."""
from pathlib import Path
from fractions import Fraction as Q
from itertools import product
import json,hashlib,ast
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
def slp_matrix(path,n,strict=False):
 env={f'i{i}':[Q(i==j)for j in range(n)]for i in range(n)};outs={};adds=0
 def expr(x):
  nonlocal adds
  if isinstance(x,ast.Name):return env[x.id]
  if isinstance(x,ast.Constant):return Q(x.value)
  if isinstance(x,ast.UnaryOp) and isinstance(x.op,ast.USub):
   v=expr(x.operand);return [-z for z in v]if isinstance(v,list)else-v
  assert isinstance(x,ast.BinOp)
  a,b=expr(x.left),expr(x.right)
  if isinstance(x.op,(ast.Add,ast.Sub)):
   assert isinstance(a,list)and isinstance(b,list);adds+=1;sg=1 if isinstance(x.op,ast.Add)else-1;return[u+sg*v for u,v in zip(a,b)]
  assert isinstance(x.op,ast.Mult)
  if not isinstance(a,list):a,b=b,a
  assert isinstance(a,list)and b in [-1,1];return[b*z for z in a]
 for line in path.read_text().splitlines():
  name,text=line.rstrip(';').split(':=');tree=ast.parse(text,mode='eval');
  if strict:assert not any(isinstance(x,(ast.UnaryOp,ast.Mult,ast.Div))for x in ast.walk(tree))
  value=expr(tree.body);env[name]=value
  if name.startswith('o'):outs[int(name[1:])]=value
 return[outs[i]for i in range(len(outs))],adds
def main():
 result={}
 for shape,expected in [('323',[9,9,15])]:
  p=HERE/f'scheme{shape}.json';d=json.loads(p.read_text());source=d['source'];dims=source['n'];r=source['m'];maps={};counts={}
  for side in 'uvw':
   inner=[[Q(x)for x in row]for row in d['inner_forward'][side]];outer=[[Q(x)for x in row]for row in d['outer_matrices'][side]]
   assert rank(outer)==len(outer)==len(outer[0])
   assert matmul(inner,outer if side!='w'else transpose(outer))==source[side];M,c=matrix(d['kernel'][side]);assert M==(inner if side!='w'else transpose(inner));maps[side]=M;counts[side]=c
  assert [counts[s]['additions']for s in 'uvw']==expected
  for side in 'uvw':
   SM,SC=slp_matrix(HERE/(side+'.slp'),d['kernel'][side]['inputs'],d.get('strict_negation_free',False));assert SM==maps[side]and SC==counts[side]['additions']
  n,m,k=dims;eqs=0
  for a,b,c in product(range(n*m),range(m*k),range(k*n)):
   wanted=int(a//m==c%n and a%m==b//k and b%k==c//n)
   assert sum(Q(source['u'][t][a])*Q(source['v'][t][b])*Q(source['w'][t][c])for t in range(r))==wanted;eqs+=1
  boundary={}
  for side in 'uvw':
   BM,bc=matrix(d['boundary'][side]);assert BM==[[Q(x)for x in row]for row in d['outer_matrices'][side]];boundary[side]=bc['additions'];SM,SC=slp_matrix(HERE/(side+'_boundary.slp'),d['boundary'][side]['inputs'],d.get('strict_negation_free',False));assert SM==BM and SC==bc['additions']
  assert boundary==d['boundary_split']
  if d.get('strict_negation_free'):
   assert all(node['op']in['add','sub']for section in ['kernel','boundary']for c in d[section].values()for node in c['nodes'])
  canon={side:len({next(i for i,x in enumerate(r)if Q(x))for r in d['inner_forward'][side]if sum(Q(x)!=0 for x in r)==1 and abs(sum(map(Q,r)))==1})for side in'uvw'}
  assert canon==d['canonical_counts']
  assert sum(boundary.values())==d['boundary_additions']
  result[shape]={'boundary_additions':boundary,'one_level_additions':sum(expected)+sum(boundary.values()),'status':'PASS','rank':r,'kernel_additions':sum(expected),'split':counts,'exact_tensor_coefficients':eqs,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'canonical_counts':canon,'strict_negation_free':d.get('strict_negation_free',False),'model':d['model']}
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
