#!/usr/bin/env python3
"""Replay frozen starts, complete solver outputs and strict literal witnesses."""
import importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def test():
 api=module('pilot_exact_api',HERE.parents[1]/'common.py')
 pool=module('pilot_chain_api',HERE.parents[1]/'pool_starts.py')
 matrix=ROOT/'certificates/scheme_5x7x7_176/V.sms';target=api.read_matrix(matrix);n=len(target[0])
 for name,count in [('bank20.json',20),('bank23.json',23)]:
  source=api.json_read(HERE/name);nn,tt,profiles=pool.bank(source)
  api.require(nn==n and tt==target and len(profiles)==count,'Frozen donor bank changed target or unique count')
 checked=accepted=timeouts=0
 for experiment in ['pilot2','pair_pilot','pair_control']:
  directory=HERE/experiment;records=api.json_read(directory/'records.json');summary=api.json_read(directory/'summary.json')
  api.require(len(records)==summary['attempts'],'Recorded attempt count mismatch')
  local_pass=0
  for row in records:
   stem=f"{row['mode']}_{row['budget']}_{row['attempt']:02d}"
   prefix=api.json_read(directory/(stem+'.partial.json'));gates=prefix['gates']
   api.require(prefix['inputs']==n and len(gates)==row['initial_additions'],'Original roots or charged gate count changed')
   values=[tuple(int(i==j)for j in range(n))for i in range(n)];known=set(values)
   for j,g in enumerate(gates):
    api.core.production(g,n+j);a,sa,b,sb=g;v=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]));form,_=api.canonical(v)
    api.require(form not in known,'Prefix contains a duplicate signed form');known.add(form);values.append(v)
   forms=[api.canonical(t)[0]for t in target]
   api.require(len(set(forms)&known)==row['covered_target_forms'],'Distinct target coverage differs')
   api.require(sum(f in known for f in forms)==row['covered_target_rows'],'Ordered target coverage differs')
   if row['status']=='PASS':
    donor=api.convert(api.json_read(directory/(stem+'.raw.json')),target)
    api.require(len(donor['gates'])==row['additions_signed'],'Reported completion count differs')
    accepted+=1;local_pass+=1
   elif row['status']=='TIMEOUT':timeouts+=1
   else:api.require(False,'Unexpected pilot failure status')
   checked+=1
  api.require(local_pass==summary['accepted'],'Accepted completion summary differs')
  bank=api.json_read(directory/'donors.json')
  api.require(len(bank['circuits'])==local_pass,'Completed donor export count differs')
  for circuit in bank['circuits']:
   api.require(api.exact_circuit(circuit,n)==target,'Exported completion changed the target')
  candidate=api.json_read(directory/'best_candidate.json')
  api.require(api.exact_circuit(candidate,n)==target and len(candidate['gates'])==summary['best_signed'],'Best witness differs')
 literal=module('pilot_strict_literal',ROOT/'certificates/scheme_5x7x7_176/verify_literal.py')
 for path,count in [(HERE/'pilot2/best.slp',213),(HERE/'pair_control/best.slp',211),(HERE/'ablation/candidate205.slp',205)]:
  actual,counts=literal.replay(path.read_text(),n)
  api.require(actual==target,'Strict literal witness changed the target')
  api.require(counts==dict(binary_additions=count,unary_negations=0,nonunit_scalars=0,unused_noninput_assignments=0),'Strict literal cost differs')
 ablation=api.json_read(HERE/'ablation/summary.json');used=api.json_read(HERE/'ablation/extra_form_usage.json')
 api.require(ablation['removed_direct_intelligent_donors']==20 and ablation['best_signed']==205 and ablation['with_intelligent_best_signed']==205,'Ablation endpoint changed')
 api.require(used['new_pool_forms']==19 and used['used_by_205']==0,'Unique mixed-start form claim changed')
 candidate=api.json_read(HERE/'ablation/candidate205.json');api.require(api.exact_circuit(candidate,n)==target and len(candidate['gates'])==205,'Ablation candidate differs')
 full_pool=api.json_read(HERE.parent/'V/pool.json');old_pool=api.json_read(HERE.parent/'V/ablation/pool.json')
 new_forms={api.canonical(v)[0] for v in full_pool['forms']}-{api.canonical(v)[0] for v in old_pool['forms']}
 full_candidate=api.json_read(HERE.parent/'V/candidate205.json')
 gate_values=api.exact_circuit(dict(inputs=n,gates=full_candidate['gates'],outputs=[[n+j,1] for j in range(len(full_candidate['gates']))]),n)
 api.require(len(new_forms)==19 and not new_forms&{api.canonical(v)[0] for v in gate_values},'Winning full-pool program uses forms unique to direct mixed starts')
 return dict(status='PASS',frozen_donor_entries=43,partial_starts=checked,exact_completions=accepted,timeouts=timeouts,strict_witnesses=3,original_inputs=n,ordered_outputs=len(target),scope='Exact witness replay; not a reproduction of heuristic timing or a general optimality proof')

if __name__=='__main__':print(json.dumps(test(),indent=2))
