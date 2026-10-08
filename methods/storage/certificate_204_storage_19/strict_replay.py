"""Independent literal rational-SLP evaluator with paid unary negations.
No optimizer, circuit-normalizer, or solver imports. Scalar arithmetic on constants
is compile-time; multiplication by any nonunit rational costs one, including a
negative rational such as -1/2. Multiplication/division by -1 costs one negation.
"""
from fractions import Fraction as F
from pathlib import Path
import ast

def need(c,m):
 if not c:raise ValueError(m)

def replay(text,n,m):
 env={f'i{i}':[F(i==j)for j in range(n)]for i in range(n)};counts=dict(additions=0,scalar_multiplications=0,negations=0)
 def ev(t):
  if isinstance(t,ast.Name):need(t.id in env,'undefined wire');return env[t.id]
  if isinstance(t,ast.Constant):need(type(t.value)is int,'inexact constant');return F(t.value)
  if isinstance(t,ast.UnaryOp):
   need(isinstance(t.op,(ast.UAdd,ast.USub)),'unsupported unary operator');v=ev(t.operand);negative=isinstance(t.op,ast.USub)
   if isinstance(v,list):counts['negations']+=int(negative);return[-x for x in v]if negative else v
   return-v if negative else v
  need(isinstance(t,ast.BinOp),'unsupported syntax');a,b=ev(t.left),ev(t.right);av,bv=isinstance(a,list),isinstance(b,list)
  if not av and not bv:
   if isinstance(t.op,ast.Add):return a+b
   if isinstance(t.op,ast.Sub):return a-b
   if isinstance(t.op,ast.Mult):return a*b
   if isinstance(t.op,ast.Div):need(b!=0,'constant zero division');return a/b
  if isinstance(t.op,(ast.Add,ast.Sub)):
   need(av and bv,'affine constant addition');counts['additions']+=1;s=-1 if isinstance(t.op,ast.Sub)else 1;return[x+s*y for x,y in zip(a,b)]
  if isinstance(t.op,ast.Div):
   need(av and not bv and b!=0,'nonlinear division');v,q=a,1/b
  else:
   need(isinstance(t.op,ast.Mult)and av!=bv,'nonlinear gate');v,q=(a,b)if av else(b,a)
  need(q.denominator&(q.denominator-1)==0,'non-dyadic scalar')
  if q==-1:counts['negations']+=1
  elif q not in(0,1):counts['scalar_multiplications']+=1
  return[q*x for x in v]
 for line in text.splitlines():
  line=line.strip()
  if not line or line.startswith('#'):continue
  need(line.endswith(';')and line.count(':=')==1,'assignment syntax');k,expr=line[:-1].split(':=');k=k.strip();need(k not in env,'wire overwrite');env[k]=ev(ast.parse(expr.strip(),mode='eval').body)
  if not isinstance(env[k],list):need(env[k]==0,'nonzero affine constant');env[k]=[F(0)]*n
 out=[]
 for i in range(m):need('o'+str(i)in env,'missing output');out.append(env['o'+str(i)])
 return out,counts

def load_sms(path):
 lines=[l.strip()for l in Path(path).read_text().splitlines()if l.strip()and not l.startswith('#')];m,n,_=lines[0].split();A=[[F(0)]*int(n)for _ in range(int(m))]
 for line in lines[1:]:
  i,j,v=line.split();i,j=int(i),int(j)
  if i==j==0:break
  need(1<=i<=int(m)and 1<=j<=int(n),'matrix index');A[i-1][j-1]=F(v)
 return A

def mul(A,B):return[[sum(x*y for x,y in zip(row,col))for col in zip(*B)]for row in A]
