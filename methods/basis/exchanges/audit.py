"""Independent standard-library audit of vectors, graph exports and controls.

Does not invoke optimizer modules or silently interpret free signs as strict.
"""
from pathlib import Path
from fractions import Fraction as Q
import ast,hashlib,json,re,subprocess,sys,time
HERE=Path(__file__).resolve().parent
def canon(v):
 v=tuple(v);s=next((1 if x>0 else -1 for x in v if x),1);return tuple(s*x for x in v)
def replay(text,n):
 env={f'i{i}':tuple(Q(i==j)for j in range(n))for i in range(n)};adds=scales=negs=0
 def expr(a):
  nonlocal adds,scales,negs
  if isinstance(a,ast.Name):return env[a.id]
  if isinstance(a,ast.UnaryOp)and isinstance(a.op,ast.USub):negs+=1;return tuple(-x for x in expr(a.operand))
  if isinstance(a,ast.BinOp):
   if isinstance(a.op,(ast.Add,ast.Sub)):
    adds+=1;l,r=expr(a.left),expr(a.right);s=1 if isinstance(a.op,ast.Add)else -1;return tuple(x+s*y for x,y in zip(l,r))
   if isinstance(a.op,(ast.Mult,ast.Div)):
    x=Q(ast.literal_eval(a.right));x=1/x if isinstance(a.op,ast.Div)else x;scales+=int(abs(x)!=1);negs+=int(x==-1);return tuple(x*y for y in expr(a.left))
  raise AssertionError(ast.dump(a))
 for raw in text.splitlines():
  if not raw.strip():continue
  name,rhs=raw.strip().rstrip(';').split(':=');env[name]=expr(ast.parse(rhs,mode='eval').body)
 outs=[env[f'o{i}']for i in range(sum(k.startswith('o')for k in env))]
 return env,outs,{'additions':adds,'scalings':scales,'explicit_unary_negations':negs}
def main():
 results=[]
 for path in sorted((HERE/'data').glob('*exchange*/pool.json')):
  d=json.loads(path.read_text());F=[tuple(Q(x)for x in v)for v in d['forms']];n=d['inputs'];assert F[:n]==[tuple(Q(i==j)for j in range(n))for i in range(n)];assert len(set(F))==len(F);assert all(v==canon(v)and any(v)for v in F)
  E=[]
  for o,ps in sorted(d['productions'].items(),key=lambda kv:int(kv[0])):
   o=int(o)
   for a,sa,b,sb in ps:
    sa,sb=Q(sa),Q(sb);assert a>=0 and b>=0 and abs(sa)==abs(sb)==1;assert F[o]==tuple(sa*x+sb*y for x,y in zip(F[a],F[b]));E.append((o,a,b))
  target=[[Q(x)for x in v]for v in d['target']];assert [tuple(s*x for x in F[o])for o,s in d['outputs']]==[tuple(v)for v in target]
  env,outs,cost=replay((path.parent/'incumbent.slp').read_text(),n);assert outs==[tuple(v)for v in target]
  helpers=set(d['helpers']);T={o for o,s in d['outputs']};allowed=T|helpers|set(range(n));ready=set(range(n))
  while True:
   before=len(ready)
   for o,a,b in E:
    if o in allowed and a in ready and b in ready:ready.add(o)
   if before==len(ready):break
  assert T<=ready
  txt=(path.parent/'input.txt').read_text().splitlines();N,I,O,H,NE=map(int,txt[0].split());assert(N,I,O,H,NE)==(len(F),n,len(T),len(helpers),len(E));assert list(map(int,txt[1].split()))==sorted(T);assert list(map(int,txt[2].split()))==sorted(helpers);assert[tuple(map(int,line.split()))for line in txt[3:]]==E
  results.append({'pool':path.parent.name,'forms':len(F),'exact_binary_relations':len(E),'positive_control':'PASS','exported_incumbent_signed_cost':cost,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 base=HERE.parent/'certificate_4x4_169_43';p=subprocess.run([sys.executable,'-I','-B',str(base/'verify.py')],capture_output=True,text=True);assert p.returncode==0,p.stderr;v=json.loads(p.stdout);assert v['kernel_total']==169 and v['conversion_total']==43;assert all(x['unary_negations']==0 for x in v['counts'].values())
 result={'status':'PASS','pools':results,'baseline_tensor_and_two_level_replay':v,'scope':'Exact rational graph data and native search input audit; positive-control closure; signed search is distinguished from strict baseline. Exhaustion claims are from native enumeration logs.'};(HERE/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASS','pools':len(results),'exact_binary_relations':sum(x['exact_binary_relations']for x in results),'baseline_tensor':'4096 coefficients and two-level replay PASS'}))
if __name__=='__main__':main()
