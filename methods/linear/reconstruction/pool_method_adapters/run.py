#!/usr/bin/env python3
"""Thin JSON/text adapter for the unmodified pinned C++ HelperPool API."""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = '21906e043ab0d652b588864893a07199b915a8e7'
INT32_MAX = 2**31 - 1
# The library forms pair sums and differences before applying its coefficient
# bound. Leave symmetric headroom for those int operations and canonization.
SAFE_COEFFICIENT = INT32_MAX // 2

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def unique_object(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result

def read_json(path):
    def reject_constant(value):
        raise ValueError('Non-finite JSON constant: ' + value)
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)

def integer(value):
    return type(value) is int

def unit(value):
    return integer(value) and value in (-1, 1)

def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')

def matrix(path):
    path = Path(path)
    if path.suffix == '.json':
        obj = read_json(path)
        result = obj.get('target_matrix') if isinstance(obj, dict) else obj
    else:
        lines = [line.split() for line in path.read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        rows, columns = map(int, lines[0][:2])
        require(rows > 0 and columns > 0, 'Invalid matrix size')
        if path.suffix == '.sms':
            result = [[0] * columns for _ in range(rows)]
            seen = set()
            for row, col, value in [list(map(int, line)) for line in lines[1:]]:
                if (row, col, value) == (0, 0, 0):
                    continue
                require(1 <= row <= rows and 1 <= col <= columns and (row,col) not in seen,
                        'Invalid/duplicate SMS coordinate')
                seen.add((row,col)); result[row-1][col-1] = value
        else:
            result = [list(map(int, row)) for row in lines[1:]]
            require(len(result) == rows, 'Wrong matrix row count')
    require(result and result[0] and all(len(r) == len(result[0]) for r in result), 'Invalid rectangular map')
    require(all(integer(v) and abs(v) <= SAFE_COEFFICIENT for r in result for v in r),
            'Matrix coefficient lacks safe int32 addition/negation headroom')
    return result

def raw_solution(value, inputs, allow_materialized=False):
    """Preserve raw expressions exactly; materialization requires an explicit flag."""
    require(integer(inputs) and inputs > 0, 'Positive integer input count required')
    if isinstance(value, dict) and 'solution' in value and isinstance(value['solution'], dict):
        value = value['solution']
    require(isinstance(value, dict), 'Donor is not a dictionary')
    if 'substitutions' not in value:
        require(allow_materialized and 'gates' in value and 'outputs' in value,
                'Raw substitutions required; normalized DAG intake must be explicitly labelled')
        value = dict(dimension=inputs,
                     substitutions=[dict(i=i,j=j,ai=ai,aj=aj) for i,ai,j,aj in value['gates']],
                     expressions=[[dict(index=i,value=s)] for i,s in value['outputs']])
    dimension = value.get('dimension', inputs)
    require(integer(dimension) and dimension == inputs, 'Wrong raw donor dimension or dimension type')
    substitutions, expressions = value.get('substitutions'), value.get('expressions')
    require(isinstance(substitutions,list) and isinstance(expressions,list), 'Raw substitutions and expressions required')
    for k,s in enumerate(substitutions):
        require(isinstance(s,dict) and all(type(s.get(v)) is int for v in ['i','j','ai','aj']), 'Invalid raw substitution')
        require(0 <= s['i'] < inputs+k and 0 <= s['j'] < inputs+k, 'Future/cyclic parent in raw solution')
        require(unit(s['ai']) and unit(s['aj']), 'Raw substitution contains a free nonunit scalar')
    for row in expressions:
        require(isinstance(row,list), 'Invalid raw expression')
        for t in row:
            require(isinstance(t,dict) and type(t.get('index')) is int and type(t.get('value')) is int
                    and 0 <= t['index'] < inputs+len(substitutions) and unit(t['value']),
                    'Invalid raw output term or free nonunit scalar')
    additions = len(substitutions) + sum(max(0,len(row)-1) for row in expressions)
    require('additions' not in value or (integer(value['additions']) and value['additions'] == additions),
            'Raw donor addition count inconsistent')
    return dict(dimension=inputs, substitutions=substitutions, expressions=expressions, additions=additions)

def replay_raw(s):
    n = s['dimension']; wires = [[int(i==j) for j in range(n)] for i in range(n)]
    for gate in s['substitutions']:
        vector = [gate['ai']*a+gate['aj']*b for a,b in zip(wires[gate['i']],wires[gate['j']])]
        require(any(vector), 'Upstream helper pool does not accept zero intermediates')
        require(all(abs(x) <= SAFE_COEFFICIENT for x in vector),
                'Intermediate coefficient could overflow upstream int32 arithmetic')
        wires.append(vector)
    outputs = []
    for row in s['expressions']:
        output = [0] * n
        for term in row:
            output = [a + term['value'] * b for a,b in zip(output,wires[term['index']])]
            require(all(abs(x) <= INT32_MAX for x in output),
                    'Terminal accumulation could overflow upstream int32 validation')
        outputs.append(output)
    require(all(abs(x) <= SAFE_COEFFICIENT for row in outputs for x in row),
            'Output coefficient could overflow upstream int32 arithmetic')
    return outputs

def make_input(bank_path, matrix_path, best, allow_materialized=False):
    targets = matrix(matrix_path); n = len(targets[0]); bank = read_json(bank_path)
    if isinstance(bank,dict):
        bank = bank.get('donors',bank.get('solutions',bank.get('bank')))
    require(isinstance(bank,list) and bank, 'Nonempty raw bank required')
    donors = [raw_solution(d,n,allow_materialized) for d in bank]
    require(all(replay_raw(d)==targets for d in donors), 'Raw donor map differs from matrix')
    require(integer(best) and 0 <= best <= min(d['additions'] for d in donors),
            'Best reference exceeds native donor minimum; upstream size_t subtraction would underflow')
    lines = [f'{n} {len(targets)} {best} {len(donors)}']
    lines.extend(' '.join(map(str,row)) for row in targets)
    for d in donors:
        lines.append(f'{n} {len(d["substitutions"])} {len(d["expressions"])}')
        lines.extend(f'{s["i"]} {s["j"]} {s["ai"]} {s["aj"]}' for s in d['substitutions'])
        lines.extend(' '.join(map(str,[len(row),*[x for t in row for x in (t['index'],t['value'])]])) for row in d['expressions'])
    report = dict(inputs=n, outputs=len(targets), donors=len(donors), raw_bank_sha256=digest(bank_path),
                matrix_sha256=digest(matrix_path), source_representation='explicit materialized DAG control' if allow_materialized else 'raw upstream substitutions and terminal expressions',
                min_donor_additions=min(d['additions'] for d in donors),max_donor_additions=max(d['additions'] for d in donors),
                native_donor_costs=[d['additions'] for d in donors])
    return '\n'.join(lines)+'\n', report

def prepare(bank_path, matrix_path, output, best, allow_materialized=False):
    text, report = make_input(bank_path, matrix_path, best, allow_materialized)
    Path(output).write_text(text)
    return report

def check_sources(leo):
    leo=Path(leo).resolve()
    pin = subprocess.check_output(['git','-C',str(leo),'rev-parse','HEAD'],text=True).strip()
    require(pin == PIN, 'Wrong upstream commit')
    subprocess.run(['git','-C',str(leo),'diff','--quiet','HEAD','--','include','src/leo'],check=True)
    expected = read_json(HERE/'UPSTREAM_PIN.json')
    tracked = subprocess.check_output(['git','-C',str(leo),'ls-files','include/leo','src/leo'],text=True).splitlines()
    require(set(tracked) == set(expected['files']), 'Upstream source inventory differs from pinned manifest')
    require(all(digest(leo/path)==expected['files'][path] for path in tracked), 'Upstream source hash differs from pin')
    return leo, tracked

def build(leo, binary):
    leo,tracked = check_sources(leo)
    binary = Path(binary).resolve()
    require(not binary.exists(), 'Refusing to overwrite binary')
    compiler = next((shutil.which(c) for c in ['c++','g++','clang++'] if shutil.which(c)),None)
    require(compiler is not None, 'C++17 compiler required'); binary.parent.mkdir(parents=True,exist_ok=True)
    sources = sorted(leo/path for path in tracked if path.startswith('src/leo/') and path.endswith('.cpp'))
    command = [compiler,'-std=c++17','-O3','-I'+str(leo/'include'),str(HERE/'pool_driver.cpp'),*map(str,sources),'-o',str(binary)]
    subprocess.run(command,check=True,timeout=180)
    report = dict(upstream_commit=PIN, upstream_unmodified=True, compiler=compiler, command=command,
                  driver_sha256=digest(HERE/'pool_driver.cpp'), executable_sha256=digest(binary),
                  source_manifest_sha256=digest(HERE/'UPSTREAM_PIN.json'),
                  threading='One CPU; OpenMP pragmas disabled, only Reducer.getWeights API used')
    dump(binary.with_suffix('.build.json'),report)
    return report

def validate_parameters(a):
    require(integer(a.best) and a.best >= 0, 'Nonnegative integer best reference required')
    require(integer(a.seed) and integer(a.draws) and a.draws>0 and 0<=a.seed
            and a.seed+a.draws-1<2**32, 'Invalid seed/draw range')
    require(integer(a.gate_limit) and a.gate_limit>=-1, 'Invalid gate limit')
    for name in ['temperature','epsilon','retention','seconds','min_start_ratio','max_start_ratio']:
        value=getattr(a,name)
        require(type(value) in (int,float) and math.isfinite(value), 'Finite numeric '+name+' required')
    require(a.temperature>0 and 0<=a.epsilon<=1 and 0<=a.retention<=1 and a.seconds>0,
            'Invalid temperature, mixing, retention or solver duration')
    require(0<=a.min_start_ratio<=a.max_start_ratio<=1, 'Invalid starting budget ratios')
    require(math.isfinite((a.seconds+5)*a.draws+20), 'Combined runtime allowance is not finite')
    require(a.preset in ('distance','default','all') and integer(a.strategy_index)
            and 0<=a.strategy_index<dict(distance=2,default=10,all=12)[a.preset], 'Invalid completion strategy')
    require(a.bound is None or (integer(a.bound) and a.bound>=0), 'Invalid completion bound')
    require(a.binary is not None or a.leo is not None, 'Supply --leo for compilation or --binary for reuse')

def validate_quality_total(costs, best, temperature):
    """Validate normalization; actual weighting remains delegated upstream."""
    require(costs and integer(best) and 0<=best<=min(costs), 'Invalid quality-weight reference')
    require(type(temperature) in (int,float) and math.isfinite(temperature) and temperature>0,
            'A finite positive temperature is required')
    classes=Counter(costs)
    total=sum(math.exp(-(cost-best)/temperature)/classes[cost] for cost in costs)
    require(math.isfinite(total) and total>0,
            'Upstream quality weights have no finite positive total; use a nearer best reference or larger T')
    return total

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bank',type=Path,required=True);ap.add_argument('--matrix',type=Path,required=True)
    ap.add_argument('--best',type=int,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--leo',type=Path);ap.add_argument('--binary',type=Path)
    ap.add_argument('--mode',choices=['weighted','uniform','bernoulli'],default='weighted');ap.add_argument('--seed',type=int,required=True)
    ap.add_argument('--draws',type=int,default=1);ap.add_argument('--gate-limit',type=int,default=-1);ap.add_argument('--sample-only',action='store_true')
    ap.add_argument('--temperature',type=float,default=1);ap.add_argument('--epsilon',type=float,default=.01);ap.add_argument('--retention',type=float,default=.5)
    ap.add_argument('--min-start-ratio',type=float,default=.1);ap.add_argument('--max-start-ratio',type=float,default=.5)
    ap.add_argument('--seconds',type=float,default=5);ap.add_argument('--preset',choices=['distance','default','all'],default='distance');ap.add_argument('--strategy-index',type=int,default=0)
    ap.add_argument('--bound',type=int);ap.add_argument('--prefix',type=Path);ap.add_argument('--allow-materialized',action='store_true')
    a=ap.parse_args();validate_parameters(a)
    text,prep=make_input(a.bank,a.matrix,a.best,a.allow_materialized)
    if a.mode in ('weighted','bernoulli'):
        reference=a.best if a.mode=='weighted' else prep['min_donor_additions']
        validate_quality_total(prep['native_donor_costs'],reference,a.temperature)
    external_prefix=None
    if a.prefix:
        external_prefix=raw_solution(read_json(a.prefix),prep['inputs'])
        require(not external_prefix['expressions'], 'External prefix should have no terminal expressions')
        replay_raw(external_prefix)
    build_report=None
    if a.binary:
        binary=a.binary.resolve();build_report=read_json(binary.with_suffix('.build.json'))
        require(build_report['upstream_commit']==PIN and build_report['executable_sha256']==digest(binary), 'Wrong/stale binary')
        require(build_report['driver_sha256']==digest(HERE/'pool_driver.cpp'), 'Binary was built from a different adapter')
    else:
        check_sources(a.leo)
    require(not a.output.exists(), 'Refusing to overwrite output directory');a.output.mkdir(parents=True)
    (a.output/'input.txt').write_text(text)
    binary=a.binary.resolve() if a.binary else a.output/'pool_driver'
    build_report=build(a.leo,binary) if not a.binary else build_report
    require(build_report['upstream_commit']==PIN and build_report['executable_sha256']==digest(binary), 'Wrong/stale binary')
    cmd=[str(binary),'--input',str(a.output/'input.txt'),'--mode',a.mode,'--seed',str(a.seed),'--draws',str(a.draws),
         '--gate-limit',str(a.gate_limit),'--temperature',str(a.temperature),'--epsilon',str(a.epsilon),'--retention',str(a.retention),
         '--seconds',str(a.seconds),'--preset',a.preset,'--strategy-index',str(a.strategy_index),
         '--min-start-ratio',str(a.min_start_ratio),'--max-start-ratio',str(a.max_start_ratio)]
    if a.sample_only:cmd.append('--sample-only')
    if a.bound is not None:cmd.extend(['--bound',str(a.bound)])
    if a.prefix:
        prefix=external_prefix
        p=a.output/'external_prefix.txt';p.write_text(f'{prep["inputs"]} {len(prefix["substitutions"])}\n'+'\n'.join(f'{s["i"]} {s["j"]} {s["ai"]} {s["aj"]}' for s in prefix['substitutions'])+'\n')
        cmd.extend(['--prefix-file',str(p)])
    result=subprocess.run(cmd,text=True,capture_output=True,timeout=max(60,(a.seconds+5)*a.draws+20))
    (a.output/'stdout.json').write_text(result.stdout);(a.output/'stderr.txt').write_text(result.stderr)
    require(result.returncode==0,'Native driver failed: '+result.stderr)
    data=json.loads(result.stdout,object_pairs_hook=unique_object);data['source_preparation']=prep;data['build']=build_report;data['command']=cmd
    data['model']='Abstract unit-signed additions; every stored gate paid; strict literal orientation is separate'
    for k,draw in enumerate(data['draws']):
        prefix=raw_solution(draw['prefix'],prep['inputs']);replay_raw(prefix)
        if a.mode=='bernoulli':draw['gate_limit']=None
        dump(a.output/f'prefix_{k:03d}.json',draw['prefix'])
        if draw['solution'] is not None:
            complete=raw_solution(draw['solution'],prep['inputs'])
            require(replay_raw(complete)==matrix(a.matrix), 'Completed circuit failed independent Python replay')
            dump(a.output/f'solution_{k:03d}.json',draw['solution'])
    dump(a.output/'result.json',data)
    print(json.dumps(dict(mode=a.mode,helpers=data['helpers'],draws=len(data['draws']),
                         completed=sum(d['status']=='complete' for d in data['draws']),
                         best=min((d['solution']['additions'] for d in data['draws'] if d['solution']),default=None),
                         sampling_seconds=sum(d['sampling_seconds'] for d in data['draws']),
                         solver_seconds=sum(d.get('solver_seconds',0) for d in data['draws']))))

if __name__=='__main__':
    main()
