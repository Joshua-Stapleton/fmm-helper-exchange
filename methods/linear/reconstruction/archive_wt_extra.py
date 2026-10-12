#!/usr/bin/env python3
"""One bounded paid adjoint-pool search, returned and verified in W coordinates."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
import archive_batch as batch
from archive_batch import (api, core, fast, REPO, dump, execute, strict,
                      signed_from_circuit, circuit_from_signed, transpose)


def run(args):
    total_start=time.monotonic()
    source=args.source
    target=api.read_matrix(source/'input.sms')
    wt=[[int(x) for x in row] for row in transpose(target)]
    args.out.mkdir(parents=True,exist_ok=False)
    donor_start=time.monotonic()
    donors=[]
    # Preserve the saved local WT dependency programs. Transposing W donors
    # twice would reproduce the map, but need not preserve these useful DAGs.
    local=api.json_read(source/'local_target.json')['target_matrix']
    if local!=wt:raise ValueError('Saved local search was not WT')
    originals=[api.json_read(source/'matched_initial.json')]
    for stage in ('bernoulli05','bernoulli09','scored_dependency_cuts','residual_forest'):
        donor_file=source/stage/'donors.json'
        if donor_file.exists():originals.extend(api.json_read(donor_file)['circuits'])
    for index,donor in enumerate(originals):
        data=dict(donor,inputs=len(wt[0]))
        if api.exact_circuit(data,len(wt[0]))!=wt:
            raise ValueError('Saved WT donor differs from exact transpose')
        donors.append(dict(api.normalize(data),name=f'wt_{index}',target_matrix=wt))
    best_w=api.json_read(source/'best_candidate.json')
    if api.exact_circuit(best_w,len(target[0]))!=target:
        raise ValueError('Current W incumbent differs from uploaded map')
    circuit=circuit_from_signed(dict(best_w,inputs=len(target[0])))
    donors.append(signed_from_circuit(circuit.transposed(),'current_strict_W_transposed',wt))
    bank=dict(inputs=len(wt[0]),circuits=donors)
    dump(args.out/'donors.json',bank);dump(args.out/'target.json',dict(target_matrix=wt))
    donor_seconds=time.monotonic()-donor_start
    start=time.monotonic();pool=fast.build_pool(bank,binary=args.pool_binary)
    dump(args.out/'pool.json',pool)
    data,productions,incumbent,_=core.load(args.out/'pool.json')
    (args.out/'baseline').mkdir();core.export(incumbent,data,args.out/'baseline')
    pool_seconds=time.monotonic()-start
    command=[sys.executable,'-B',REPO/'methods/linear/search.py','--data',args.out/'pool.json',
             '--out',args.out/'plateau','--engine','plateau','--seconds',str(args.seconds),
             '--seed',str(args.seed),'--width','10']
    search=execute(command,args.seconds+12,args.out/'search.log')
    search['result']=api.json_read(args.out/'plateau/result.json') if (args.out/'plateau/result.json').exists() else None
    candidates=[args.out/'baseline/candidate.json']
    if (args.out/'plateau/candidate.json').exists():candidates.append(args.out/'plateau/candidate.json')
    returned=[]
    for index,path in enumerate(candidates):
        candidate=api.json_read(path)
        if api.exact_circuit(candidate,len(wt[0]))!=wt:
            raise ValueError('Transposed pool output differs from exact transpose')
        circuit=circuit_from_signed(dict(candidate,inputs=len(wt[0])))
        original=signed_from_circuit(circuit.transposed(),f'W_returned_{index}',target)
        destination=args.out/f'W_candidate_{index}.json';dump(destination,original)
        returned.append((destination,original))
    returned.sort(key=lambda entry:len(entry[1]['gates']))
    initial_count=len(api.json_read(source/'best_candidate.json')['gates'])
    orientations=[];selected=None
    for index,(path,data) in enumerate(returned):
        if len(data['gates'])>=initial_count:continue
        slp=args.out/f'W_strict_{index}.slp'
        orientation,proof=strict(path,source/'input.sms',slp,args.orientation_seconds)
        orientations.append(orientation)
        if proof:
            shutil.copy2(path,args.out/'best_candidate.json');shutil.copy2(slp,args.out/'best.slp')
            dump(args.out/'literal_verification.json',proof)
            selected=proof;break
    report=dict(original_strict_additions=initial_count,
                best_returned_signed=min(len(data['gates']) for _,data in returned),
                strict_additions=selected['counts']['binary_additions'] if selected else initial_count,
                strict_improvement_verified=selected is not None,
                donor_transposition_seconds=donor_seconds,pool_build_seconds=pool_seconds,
                pool_forms=len(pool['forms']),pool_productions=sum(map(len,productions.values())),
                transposed_donors=len(donors),search=search,orientations=orientations,
                total_seconds=time.monotonic()-total_start,
                basis_change=False,scope='All adjoint accumulations charged; final original W fixed signs verified')
    dump(args.out/'summary.json',report);print(json.dumps(report,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--pool-binary',type=Path,required=True)
    parser.add_argument('--runtime-python',default=sys.executable,help='Python with OR-Tools for orientation')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=20)
    parser.add_argument('--seed',type=int,default=11117000)
    parser.add_argument('--orientation-seconds',type=float,default=8)
    args=parser.parse_args()
    api.require(args.pool_binary.is_file(),'Missing pool_relations binary')
    batch.ORIENT_PYTHON=Path(args.runtime_python)
    api.finite(args.seconds,'Search time');api.finite(args.orientation_seconds,'Orientation time')
    api.require(0<args.seed<2**32,'Invalid seed')
    run(args)


if __name__=='__main__':main()
