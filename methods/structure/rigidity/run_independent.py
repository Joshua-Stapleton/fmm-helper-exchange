from span_exhaust import *
results=[]
for name,p in [('rank49',2),('rank48',3)]:
 D=json.loads((HERE/(name+'_source.json')).read_text())
 for axes in ['uv','uw','vw']:
  tag=f'{name}_p{p}_{axes}';hp=HERE/(tag+'_independent_hits.txt')
  proc=subprocess.run([str(HERE/'independent_scan'),str(HERE/(tag+'.txt')),str(hp)],text=True,capture_output=True,check=True);res=json.loads(proc.stdout)
  old=set(canon([mod(x,p)for x in row],p)for row in D[axes[0]])
  actual=set()
  for line in hp.read_text().splitlines():
   a,dim=line.split('|');assert int(dim)==1;actual.add(canon(list(map(int,a.split())),p))
  assert actual==old;assert res['projective_first_factors']==(p**16-1)//(p-1)
  original=json.loads((HERE/(tag+'_result.json')).read_text());assert res['kernel_dimension_histogram']==original['kernel_dimension_histogram']
  res.update(tag=tag,comparison='PASS',method='bit-plane arithmetic; reverse elimination; last-nonzero projective charts');results.append(res);print(json.dumps(res),flush=True)
(HERE/'independent_results.json').write_text(json.dumps(results,indent=2)+'\n')
