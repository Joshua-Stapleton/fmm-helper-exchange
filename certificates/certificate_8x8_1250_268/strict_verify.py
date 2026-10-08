#!/usr/bin/env python3
"""Independent exact SLP interpreter: explicit negations each cost one operation.

Only constants are folded for free. No rewrites or sign propagation occur here.
Uses the Python standard library only. Input/output names are i0,... and o0,... .
"""
from pathlib import Path
from fractions import Fraction as F
import ast,argparse,json,hashlib

def need(c,msg):
 if not c:raise ValueError(msg)

def replay(text,n,m):
 env={f'i{i}':[F(i==j)for j in range(n)]for i in range(n)}
 counts={'additions_subtractions':0,'nonunit_scalings':0,'negations':0};scalars=[]
 def ev(t):
  if isinstance(t,ast.Name):return env[t.id]
  if isinstance(t,ast.Constant):need(type(t.value)is int,'noninteger literal');return F(t.value)
  if isinstance(t,ast.UnaryOp):
   need(isinstance(t.op,(ast.USub,ast.UAdd)),'unsupported unary')
   v=ev(t.operand);sgn=-1 if isinstance(t.op,ast.USub)else 1
   if isinstance(v,list):
    counts['negations']+=sgn<0;return[sgn*x for x in v]
   return sgn*v
  need(isinstance(t,ast.BinOp),'unsupported expression');a,b=ev(t.left),ev(t.right);av,bv=isinstance(a,list),isinstance(b,list)
  if not av and not bv:
   if isinstance(t.op,ast.Add):return a+b
   if isinstance(t.op,ast.Sub):return a-b
   if isinstance(t.op,ast.Mult):return a*b
   if isinstance(t.op,ast.Div):return a/b
   raise ValueError('constant operator')
  if isinstance(t.op,(ast.Add,ast.Sub)):
   need(av and bv,'affine gate');counts['additions_subtractions']+=1;s=1 if isinstance(t.op,ast.Add)else -1
   return[x+s*y for x,y in zip(a,b)]
  if isinstance(t.op,ast.Div):need(av and not bv,'nonlinear division');v,s=a,1/b
  else:need(isinstance(t.op,ast.Mult)and av!=bv,'nonlinear gate');v,s=(a,b)if av else(b,a)
  if s==-1:counts['negations']+=1
  elif s not in [0,1]:counts['nonunit_scalings']+=1;scalars.append(s)
  return[s*x for x in v]
 for line in text.splitlines():
  line=line.strip()
  if not line or line.startswith('#'):continue
  need(line.endswith(';')and line.count(':=')==1,'SLP assignment syntax')
  k,e=line[:-1].split(':=');k=k.strip();need(k not in env,'wire reassigned')
  env[k]=ev(ast.parse(e.strip(),mode='eval').body)
  if not isinstance(env[k],list):need(env[k]==0,'affine gate');env[k]=[F(0)]*n
 for s in scalars:
  d=s.denominator;need(d&(d-1)==0,'nondyadic constant')
 return[env[f'o{i}']for i in range(m)],counts,[str(x)for x in scalars]

def mul(A,B):return[[sum(x*y for x,y in zip(r,c))for c in zip(*B)]for r in A]
def sms(path):
 ls=[x.strip()for x in Path(path).read_text().splitlines()if x.strip()and not x.startswith('#')];m,n,_=ls[0].split();A=[[F(0)]*int(n)for _ in range(int(m))]
 for line in ls[1:]:
  i,j,v=line.split();i,j=int(i),int(j)
  if i==j==0:break
  need(1<=i<=int(m) and 1<=j<=int(n),'SMS index');A[i-1][j-1]=F(v)
 return A

def audit(directory,basis=True,require_zero_negations=False,coordinates=16):
 directory=Path(directory);maps={};counts={};scalars={};pins={}
 need(16<=coordinates<48,'invalid coordinate dimension')
 c=coordinates if basis else 16
 for k in (['L','R','P','CL','CR','CP']if basis else ['L','R','P']):
  n,m=(c,48)if k in ['L','R']else(48,c)if k=='P'else(c,16)if k=='CP'else(16,c);p=directory/(k+'.slp')
  maps[k],counts[k],scalars[k]=replay(p.read_text(),n,m);pins[k]=hashlib.sha256(p.read_bytes()).hexdigest()
  if require_zero_negations:need(counts[k]['negations']==0,'literal negations in '+k)
 if basis:L,R,P=mul(maps['L'],maps['CL']),mul(maps['R'],maps['CR']),mul(maps['CP'],maps['P'])
 else:L,R,P=(maps[k]for k in ['L','R','P'])
 for ai in range(16):
  i,j=divmod(ai,4)
  for bi in range(16):
   jj,k=divmod(bi,4)
   for ci in range(16):
    need(sum(P[ci][t]*L[t][ai]*R[t][bi]for t in range(48))==int(j==jj and ci==4*i+k),'tensor coefficient failure')
 kernel=sum(sum(counts[k].values())for k in ['L','R','P']);boundary=sum(sum(counts['C'+k].values())for k in ['L','R','P'])if basis else 0
 return {'status':'PASS','coordinates':c,'costs':counts,'kernel_operations':kernel,'boundary_operations':boundary,'linear_operations':kernel+boundary,'bilinear_products':48,'complete_operations':kernel+boundary+48,'recursive_leading_constant':str(1+F(kernel,48-c)),'tensor_identities_checked':4096,'nonunit_constants':scalars,'sha256':pins}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--ordinary',action='store_true');ap.add_argument('--require-zero-negations',action='store_true');ap.add_argument('--coordinates',type=int,default=16);ap.add_argument('--out',type=Path);args=ap.parse_args()
 r=audit(args.directory,not args.ordinary,args.require_zero_negations,args.coordinates);s=json.dumps(r,indent=2)+'\n'
 if args.out:args.out.write_text(s)
 print(s)
if __name__=='__main__':main()
