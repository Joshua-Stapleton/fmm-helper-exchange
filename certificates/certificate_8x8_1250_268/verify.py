#!/usr/bin/env python3
"""Standalone exact verifier for a64-coordinate alternative-basis rank336 circuit."""
from pathlib import Path
from fractions import Fraction as F
import json,random,hashlib,sys
from strict_verify import replay as strict_replay
H=Path(__file__).resolve().parent

def need(x,s):
 if not x:raise ValueError(s)

def sms(name):
 ls=(H/name).read_text().split();r,c=int(ls[0]),int(ls[1]);M=[[F(0)]*c for _ in range(r)]
 for k in range(3,len(ls)-2,3):
  i,j,v=int(ls[k]),int(ls[k+1]),ls[k+2]
  if i==j==0:break
  M[i-1][j-1]=F(v)
 return M

def mul(A,B):return [[sum(x*y for x,y in zip(r,c))for c in zip(*B)]for r in A]

def kron(A,B):return [[x*y for x in a for y in b]for a in A for b in B]

def brent(L,R,P,n,rank):
 for a in range(n*n):
  i,j=divmod(a,n)
  for b in range(n*n):
   jj,k=divmod(b,n)
   for o in range(n*n):need(sum(L[t][a]*R[t][b]*P[o][t]for t in range(rank))==int(j==jj and o==n*i+k),'base tensor identity')
 return n**6

def ev(A,x):return [sum(v*w for v,w in zip(row,x))for row in A]

def main():
 roles=['ALT_L','ALT_R','ALT_P','CoB_L','CoB_R','CoB_P'];small={};basechecks={}
 for n,rank in [(4,48),(2,7)]:
  d={role:sms(f'{role}{n}.sms')for role in roles};small[n]=d
  L=mul(d['ALT_L'],d['CoB_L']);R=mul(d['ALT_R'],d['CoB_R']);P=mul(d['CoB_P'],d['ALT_P']);basechecks[n]=brent(L,R,P,n,rank)
 mats={};counts={};scalars={}
 for role in roles:
  ni,no=(336,64)if role=='ALT_P'else(64,336)if role.startswith('ALT')else(64,64)
  mats[role],counts[role],scalars[role]=strict_replay((H/(role+'.slp')).read_text(),ni,no)
  need(counts[role]['negations']==0,'unary negation in '+role);need(mats[role]==kron(small[4][role],small[2][role]),'Kronecker map mismatch '+role)
 rng=random.Random(261002)
 for trial in range(3):
  A=[[F(rng.randint(-8,8))for _ in range(8)]for _ in range(8)];B=[[F(rng.randint(-8,8))for _ in range(8)]for _ in range(8)];flat=lambda X:[X[2*(o//4)+q//2][2*(o%4)+q%2]for o in range(16)for q in range(4)]
  a=ev(mats['CoB_L'],flat(A));b=ev(mats['CoB_R'],flat(B));u=ev(mats['ALT_L'],a);v=ev(mats['ALT_R'],b);c=ev(mats['CoB_P'],ev(mats['ALT_P'],[x*y for x,y in zip(u,v)]))
  for i in range(8):
   for j in range(8):need(c[((i//2)*4+j//2)*4+(i%2)*2+j%2]==sum(A[i][k]*B[k][j]for k in range(8)),'8x8 product failure')
 core=sum(sum(counts[x].values())for x in roles[:3]);conv=sum(sum(counts[x].values())for x in roles[3:]);r=dict(status='PASS',products=336,coordinates='alternative basis of dimension64; conversion maps explicitly included',counts=counts,core=core,conversions=conv,one_level_standard_total=336+core+conv,leading_constant=str(1+F(core,336-64)),base_brent_checks=basechecks,product_trials=3,scalars=scalars,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in H.glob('*.slp')})
 (H/'verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
