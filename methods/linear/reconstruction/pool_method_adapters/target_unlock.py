#!/usr/bin/env python3
"""Generate paid new forms by the target constructions they open.

The frozen pool and its incumbent are the only inputs. Ranking is a heuristic,
not a lower bound. No separate better circuit is accepted as a search input.
"""
import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent

canonical=lambda v: (tuple(v) if next((x for x in v if x),0)>0 else tuple(-x for x in v)) if any(v) else None

def generate(source,cap=128):
 start=time.monotonic();forms=list(map(tuple,source['forms']));known=set(forms);targets={forms[i] for i,s in source['outputs']};used=set(range(source['inputs']))|{int(k)for k in source['incumbent']}
 hits=defaultdict(set)
 for ti,t in enumerate(sorted(targets)):
  for f in forms:
   for sign in (-1,1):
    v=canonical(tuple(a+sign*b for a,b in zip(t,f)))
    if v is not None and v not in known and max(map(abs,v))<=1:hits[v].add(ti)
 hits={v:ts for v,ts in hits.items()if len(ts)>=2};reps=defaultdict(list)
 for a,fa in enumerate(forms):
  for b in range(a+1,len(forms)):
   for sign in (-1,1):
    raw=tuple(x+sign*y for x,y in zip(fa,forms[b]));v=canonical(raw)
    if v in hits:
     s=1 if raw==v else -1;reps[v].append([a,s,b,s*sign])
 def score(v):
  rows=reps[v];cost=min(len({a,b}-used)for a,sa,b,sb in rows)
  inside=sum(a in used and b in used for a,sa,b,sb in rows)
  return (-len(hits[v]),cost,-inside,-len(rows),sum(x != 0 for x in v),v)
 selected=sorted(reps,key=score)[:cap];values=forms+selected;ids={v:i for i,v in enumerate(values)};productions=defaultdict(set)
 for a,fa in enumerate(values):
  for b in range(a,len(values)):
   for sign in (-1,1):
    raw=tuple(x+sign*y for x,y in zip(fa,values[b]));v=canonical(raw);out=ids.get(v)
    if out is not None and out>=source['inputs'] and out not in (a,b):
     s=1 if raw==v else -1;productions[out].add((a,s,b,s*sign))
 for out,rows in source['productions'].items():productions[int(out)].update(map(tuple,rows))
 result=dict(source,forms=list(map(list,values)),productions={str(k):[list(p)for p in sorted(v)]for k,v in sorted(productions.items())})
 report=dict(old_forms=len(forms),target_routes_candidates=len(hits),computable_candidates=len(reps),selected_count=len(selected),cap=cap,elapsed_seconds=time.monotonic()-start,source='Frozen observed pool plus88incumbent only; no87witness input',ranking='More target routes, fewer currently missing parent forms, more already available constructions, lower support',selection=[dict(vector=v,target_routes=len(hits[v]),best_missing_parents=min(len({a,b}-used)for a,sa,b,sb in reps[v]),constructions=reps[v])for v in selected],scope='Heuristic candidate generation; exact identities verified, no optimality claim')
 return result,report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cap', type=int, default=128)
    parser.add_argument('--core', type=Path, default=HERE.parents[3]/'run.py')
    args = parser.parse_args()
    if args.cap <= 0:
        raise ValueError('Positive integer candidate cap required')
    spec = importlib.util.spec_from_file_location('unlock_core', args.core)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    source = json.loads(args.source.read_text(), object_pairs_hook=core.unique_object)
    core.require('witness' not in source, 'A separate better witness is not a search input')
    checked, _, incumbent, _ = core.load(args.source)
    core.require(not args.output.exists(), 'Refusing to overwrite output directory')
    result, report = generate(checked, args.cap)
    report['source'] = 'Frozen pool and its incumbent only; no separate witness input'
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'pool.json').write_text(json.dumps(result, separators=(',', ':'))+'\n')
    core.load(args.output/'pool.json')
    (args.output/'generation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'selection'}))


if __name__ == '__main__':
    main()
