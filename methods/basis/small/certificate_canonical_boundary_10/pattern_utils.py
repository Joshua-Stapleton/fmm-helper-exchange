"""Complete two-helper enumeration for the selected 36-addition 233 kernel."""
from pathlib import Path
from fractions import Fraction as Q
from itertools import combinations,permutations,product
from math import lcm
import sys,json,subprocess,os,platform
HERE=Path(__file__).resolve().parent

def canon(v):
 v=tuple(v);return tuple(-x for x in v)if next((x for x in v if x),1)<0 else v

def det(A):return A[0][0]*A[1][1]-A[0][1]*A[1][0]
def matrix_canon(A):
 return min(tuple(sorted(canon(row[p[j]]*ss[j]for j in range(2))for row in A))for p in permutations(range(2))for ss in product([-1,1],repeat=2))
def rtype(row):
 a=sorted(abs(x)for x in row if x);return 2 if a==[1]else 1 if a in ([2],[1,1])else 0

def main():
 out=HERE/'lower_233_36';out.mkdir(exist_ok=True);D=json.loads((HERE/'certificate_233_36/scheme233.json').read_text());T=sorted({canon(map(Q,r))for r in D['source']['v']});q=len(T);d=len(T[0]);assert(q,d)==(15,9)
 rows=[(1,0),(2,0),(0,1),(0,2),(1,1),(1,-1),(2,1),(2,-1),(1,2),(1,-2)];patterns=sorted({matrix_canon(A)for A in combinations(rows,2)if det(A)and any(rtype(row)for row in A)})
 scale=lcm(2,*[abs(det(A))for A in patterns],*[v.denominator for t in T for v in t]);text=f'{q} {d} {len(patterns)}\n'+''.join(' '.join(str(int(x*scale))for x in t)+'\n'for t in T)
 for A in patterns:
  aa,bb=A[0];cc,dd=A[1];text+=' '.join(map(str,[det(A),*[rtype(row)for row in A],dd,-bb,-cc,aa]))+'\n'
 (out/'input.txt').write_text(text);(out/'patterns.json').write_text(json.dumps(patterns,indent=2)+'\n');bin=out/'complete_two';clt=Path('/Library/Developer/CommandLineTools');cmd=[os.environ.get('CXX','c++'),'-O3','-std=c++17']
 if platform.system()=='Darwin'and'CXX'not in os.environ:cmd=[str(clt/'usr/bin/clang++'),'-O3','-std=c++17','-isysroot',str(clt/'SDKs/MacOSX.sdk'),'-B'+str(clt/'usr/bin')]
 subprocess.run(cmd+[str(HERE/'complete_two.cpp'),'-o',str(bin)],check=True);cp=subprocess.run([str(bin),str(out/'input.txt'),str(out/'passes.txt')],check=True,capture_output=True,text=True);(out/'replay.log').write_text(cp.stdout);result=json.loads(cp.stdout.splitlines()[-1]);assert result['complete'] and result['patterns']==12 and result['passes']==0 and result['minimum']>d;print(json.dumps(result,indent=2));(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 # Positive control: three targets in two inputs computed with one addition.
 pos='3 2 '+str(len(patterns))+'\n'+f'{scale} 0\n0 {scale}\n{scale} {scale}\n'+''.join(' '.join(map(str,[det(A),*[rtype(row)for row in A],A[1][1],-A[0][1],-A[1][0],A[0][0]]))+'\n'for A in patterns)
 (out/'positive_input.txt').write_text(pos);pp=subprocess.run([str(bin),str(out/'positive_input.txt'),str(out/'positive_passes.txt')],check=True,capture_output=True,text=True);positive=json.loads(pp.stdout.splitlines()[-1]);assert positive['passes']>0;(out/'positive_result.json').write_text(json.dumps(positive,indent=2)+'\n');print('POSITIVE_CONTROL_PASS',positive['passes'])
if __name__=='__main__':main()
