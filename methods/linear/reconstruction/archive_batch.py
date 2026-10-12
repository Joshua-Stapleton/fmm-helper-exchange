#!/usr/bin/env python3
"""Portable bounded, separately timed experiments on supplied fixed integer maps.

This local harness deliberately runs each solver with one thread. Bernoulli
retention probabilities start from the same initial circuit and use the same
seeds, before pooling all exactly verified complete donors. Strict output-sign
orientation and literal replay are required before calling a count a result.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RECON = HERE
HISTORY = None
CLI = None
REPAIR = None
NATIVE = None
WEIGHTED = None
ORIENT = Path(__file__).resolve()
ORIENT_PYTHON = Path(sys.executable)
THREAD_ENV = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
sys.path.insert(0, str(REPO/'methods/circuits'))
from circuits import Circuit, Q, from_reduced, read_sms, transpose


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


api = module('new_archive_common', RECON/'common.py')
core = module('new_archive_core', REPO/'run.py')
fast = module('new_archive_fast_pool', REPO/'methods/linear/fast_pool.py')
adjoint = module('archive_fixed_orientation', HERE/'adjoint_pool.py')


def dump(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')


def signed_from_circuit(circuit, name, target):
    circuit.prune()
    n, aliases, gates = circuit.inputs, [], []
    aliases.extend((i, 1) for i in range(n))
    for node in circuit.nodes:
        if node['op'] == 'scale':
            if abs(Q(node['c'])) != 1:
                raise ValueError('Nonunit scales cannot be free')
            wire, sign = aliases[node['a']]
            aliases.append((wire, sign*int(Q(node['c']))))
        elif node['op'] == 'add':
            a, sa = aliases[node['a']]
            b, sb = aliases[node['b']]
            gates.append([a, sa, b, sb])
            aliases.append((n+len(gates)-1, 1))
        else:
            raise ValueError('Unsupported circuit node: '+str(node))
    data = dict(inputs=n, gates=gates,
                outputs=[list(aliases[o]) for o in circuit.outputs])
    data = api.normalize(data)
    if api.exact_circuit(data, n) != target:
        raise ValueError('Circuit changed original map')
    return dict(data, name=name, target_matrix=target)


def circuit_from_signed(data):
    circuit = Circuit(data['inputs'])
    wires = list(range(data['inputs']))
    for a, sa, b, sb in data['gates']:
        wires.append(circuit.add(circuit.scale(wires[a], sa), circuit.scale(wires[b], sb)))
    circuit.outputs = [circuit.scale(wires[w], sign) for w, sign in data['outputs']]
    return circuit.prune()


def naive(target):
    # All multiplications by integer constants are charged repeated additions.
    # Unit signs are abstract at this point, and require the separate orienter.
    n = len(target[0]); gates = []; outputs = []
    for row in target:
        terms = []
        for i, value in enumerate(row):
            terms.extend((i, 1 if value > 0 else -1) for _ in range(abs(value)))
        if not terms:
            raise ValueError('Zero target rows are unsupported')
        wire, sign = terms[0]
        for b, sb in terms[1:]:
            gates.append([wire, sign, b, sb]); wire, sign = n+len(gates)-1, 1
        outputs.append([wire, sign])
    data = api.normalize(dict(inputs=n, gates=gates, outputs=outputs))
    return dict(data, name='naive_fallback', target_matrix=target)


def infer_job(path):
    filename = path.name
    match = re.fullmatch(r'(.+)_([UVW])(?: \(\d+\))?\.sms', filename)
    if not match:
        raise ValueError('Expected factor suffix _U, _V or _W: '+filename)
    scheme, factor = match.groups()
    text = path.read_text()
    baseline = re.search(r'was\s*:?\s*(\d+)', text)
    return dict(filename=filename, scheme=scheme, factor=factor,
                baseline_annotation=int(baseline.group(1)) if baseline else None,
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def execute(command, timeout, log):
    start = time.monotonic()
    record = dict(command=[str(x) for x in command], budget_seconds=timeout,
                  upstream_threads=1)
    try:
        process = subprocess.run(record['command'], capture_output=True, text=True,
                                 timeout=timeout, env=THREAD_ENV)
        log.write_text(process.stdout+'\n'+process.stderr)
        record.update(status='COMPLETE' if process.returncode == 0 else 'ERROR',
                      returncode=process.returncode)
    except subprocess.TimeoutExpired as error:
        convert = lambda x: x.decode(errors='replace') if isinstance(x, bytes) else x or ''
        log.write_text(convert(error.stdout)+'\n'+convert(error.stderr))
        record['status'] = 'TIMEOUT'
    record['elapsed_seconds'] = time.monotonic()-start
    return record


def replay_literal(text, width):
    """Independent integer replay of the exact restricted writer grammar."""
    env = {f'i{i}': [int(i == j) for j in range(width)] for i in range(width)}
    dependencies = {}; count = 0
    for line in text.splitlines():
        match = re.fullmatch(r'([to]\d+):=([it]\d+)(?:([+-])([it]\d+))?;', line.strip())
        if match is None:
            raise ValueError('Literal program contains an unsupported operation')
        name, a, op, b = match.groups()
        if name in env or a not in env or (b is not None and b not in env):
            raise ValueError('Reassigned or future literal wire')
        if op is None:
            env[name] = list(env[a]); dependencies[name] = {a}
        else:
            count += 1; sign = 1 if op == '+' else -1
            env[name] = [x + sign*y for x, y in zip(env[a], env[b])]
            dependencies[name] = {a, b}
    outputs = {key for key in env if key.startswith('o')}
    if outputs != {f'o{i}' for i in range(len(outputs))}:
        raise ValueError('Literal output order is not consecutive')
    used = set(outputs); todo = list(outputs)
    while todo:
        for parent in dependencies.get(todo.pop(), ()):
            if parent not in used:
                used.add(parent); todo.append(parent)
    return [env[f'o{i}'] for i in range(len(outputs))], dict(
        binary_additions=count, unary_negations=0, nonunit_scalars=0,
        unused_noninput_assignments=len(set(dependencies)-used))


def orient_one(argv):
    parser = argparse.ArgumentParser(description='Freeze original map signs using the published orienter')
    parser.add_argument('candidate', type=Path)
    parser.add_argument('matrix', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--seconds', type=float, required=True)
    args = parser.parse_args(argv)
    target = api.read_matrix(args.matrix)
    data = api.json_read(args.candidate)
    literal, text, report = adjoint.orient_fixed(data, target, args.seconds)
    dump(args.out.with_suffix('.orientation.json'), report)
    if text is not None:
        actual, counts = replay_literal(text, len(target[0]))
        if actual != target or counts['unused_noninput_assignments']:
            raise ValueError('Independent literal replay failed')
        args.out.write_text(text)
    print(json.dumps(report, indent=2))


def configure(args):
    global CLI, REPAIR, NATIVE, WEIGHTED, HISTORY, ORIENT_PYTHON
    CLI = args.leo_cli; REPAIR = args.repair_binary; NATIVE = args.pool_binary
    WEIGHTED = args.weighted_binary; HISTORY = args.history
    ORIENT_PYTHON = Path(args.runtime_python)
    for value in (CLI, REPAIR, NATIVE, WEIGHTED):
        if value is not None and not value.is_file():
            raise ValueError('Missing executable: '+str(value))
    if HISTORY is not None and not HISTORY.is_dir():
        raise ValueError('Missing historical JSON directory')


def strict(candidate, source, dest, seconds):
    record = execute([ORIENT_PYTHON, ORIENT, '--orient-one', candidate, source, dest,
                      '--seconds', str(seconds)], seconds+8, dest.with_suffix('.log'))
    if not dest.exists():
        return record, None
    actual, counts = replay_literal(dest.read_text(), len(api.read_matrix(source)[0]))
    if actual != api.read_matrix(source):
        raise ValueError('Strict literal circuit does not match source')
    if any(counts[k] for k in ('unary_negations', 'nonunit_scalars',
                              'unused_noninput_assignments')):
        raise ValueError('Strict literal circuit has unpaid extra operations')
    return record, dict(status='PASS', exact_original_ordered_map=True,
                        counts=counts, basis_change=False)


def prepare(path, job, out):
    target = api.read_matrix(path)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(path, out/'input.sms')
    data = naive(target)
    dump(out/'naive_candidate.json', data)
    sources = [dict(name='naive', data=data, path=out/'naive_candidate.json')]
    historical_path = (Path(job['historical_source']) if job.get('historical_source')
                       else HISTORY/(job['scheme']+'.json') if HISTORY is not None else None)
    for name, candidate in [('supplied_candidate', job.get('candidate'))]:
        if candidate:
            candidate = Path(candidate)
            supplied, actual = api.candidate(candidate)
            if actual != target:
                raise ValueError('Supplied incumbent differs from source '+str(path))
            normalized = dict(api.normalize(supplied), name=name, target_matrix=target)
            dump(out/(name+'.json'), normalized)
            sources.append(dict(name=name, data=normalized, path=out/(name+'.json')))
    if historical_path is not None and historical_path.exists():
        circuit = from_reduced(json.loads(historical_path.read_text()), job['factor'].lower())
        circuit.check(target)
        original = signed_from_circuit(circuit, 'historical', target)
        dump(out/'historical_candidate.json', original)
        sources.append(dict(name='historical', data=original, path=out/'historical_candidate.json'))
    incumbent = min(sources, key=lambda x: len(x['data']['gates']))
    dump(out/'incumbent.json', incumbent['data'])
    stats = dict(job=job, inputs=len(target[0]), outputs=len(target),
                 source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                 available_sources=[dict(name=s['name'], signed_additions=len(s['data']['gates']))
                                    for s in sources],
                 incumbent_signed_additions=len(incumbent['data']['gates']),
                 naive_additions=sum(sum(abs(x) for x in row)-1 for row in target),
                 external_threads=1)
    dump(out/'preparation.json', stats)
    return target, sources, incumbent, stats


def run_one(path, job, out, args, index):
    total_start = time.monotonic()
    target, initial_sources, incumbent, prepared = prepare(path, job, out)
    n = len(target[0]); donors = []; records = []
    def admit(data, name):
        actual = api.exact_circuit(data, data.get('inputs', n))
        if actual != target:
            raise ValueError('Donor differs from original map')
        data = dict(api.normalize(dict(data, inputs=n)), name=name, target_matrix=target)
        donors.append(data)
        dump(out/'donors_original_map.json', dict(inputs=n, circuits=donors))
        return data
    for source in initial_sources:
        admit(source['data'], source['name'])
    seed = args.seed+index*1000
    donor_start = time.monotonic()
    for mode, vec, cse in [('cse_only', 0, 8), ('vector_cover', 4, 0)]:
        raw = out/(mode+'.raw.json')
        command = [CLI, '-i', path, '-o', raw, '-f', 'json', '--threads', '1',
                   '--seed', str(seed), '--rounds', '1', '--vec-preset', 'default',
                   '--vec-iterations', str(vec), '--cse-iterations', str(cse),
                   '--try-transpose', '--inline-substitutions', '--validate']
        record = execute(command, args.method_seconds, out/(mode+'.log'))
        record['method'] = mode
        if record['status'] == 'COMPLETE':
            try:
                data = dict(api.convert(api.json_read(raw), target), inputs=n)
                donor = admit(data, mode)
                record.update(status='PASS', signed_additions=len(donor['gates']),
                              exact_map_verified=True)
            except Exception as error:
                record.update(status='ERROR', diagnostic=str(error))
        records.append(record); dump(out/'donor_records.json', records)
    # Use the same incumbent for both probabilities and all dependency-cut starts.
    # Choosing a better donor between the controls would confound their comparison.
    initial = circuit_from_signed(incumbent['data'])
    transposed = n > len(target)
    local_target = [[int(x) for x in row] for row in transpose(target)] if transposed else target
    if transposed:
        initial = initial.transposed()
    local_seed = signed_from_circuit(initial, 'matched_initial', local_target)
    dump(out/'matched_initial.json', local_seed)
    dump(out/'local_target.json', dict(target_matrix=local_target))
    for mode, probability in [('bernoulli05', '.5'), ('bernoulli09', '.9'),
                              ('scored_dependency_cuts', None)]:
        stage = out/mode
        command = [sys.executable, '-B', RECON/'reconstruct.py', '--candidate',
                   out/'matched_initial.json', '--binary', REPAIR, '--out', stage,
                   '--seconds', str(args.method_seconds), '--timeout', str(args.call_timeout),
                   '--attempts', str(args.attempts), '--seed', str(seed+100),
                   '--max-seeds', '3', '--max-removed', '14']
        if probability is not None:
            command += ['--retention', probability]
        record = execute(command, args.method_seconds+8, out/(mode+'.log'))
        record.update(method=mode, transposed_search=transposed,
                      matched_initial_signed_additions=len(local_seed['gates']))
        if (stage/'donors.json').exists():
            counts=[]
            for j, data in enumerate(api.json_read(stage/'donors.json')['circuits']):
                data = dict(data, inputs=len(local_target[0]))
                if api.exact_circuit(data, data['inputs']) != local_target:
                    raise ValueError('Repair donor changed local search map')
                circuit = circuit_from_signed(data)
                if transposed:
                    circuit = circuit.transposed()
                donor = admit(signed_from_circuit(circuit, f'{mode}_{j}', target), f'{mode}_{j}')
                counts.append(len(donor['gates']))
            record['completed_donors'] = len(counts)
            record['best_original_map_signed'] = min(counts) if counts else None
            record['summary'] = api.json_read(stage/'summary.json') if (stage/'summary.json').exists() else None
        records.append(record); dump(out/'donor_records.json', records)
    mode='residual_forest'; stage=out/mode
    command = [sys.executable, '-B', RECON/'output_forest.py', '--matrix',
               out/'local_target.json', '--binary', REPAIR, '--out', stage,
               '--seconds', str(args.method_seconds), '--timeout', str(args.call_timeout),
               '--trials', str(args.attempts), '--seed', str(seed+300)]
    record = execute(command, args.method_seconds+8, out/(mode+'.log'))
    record.update(method=mode, transposed_search=transposed,
                  all_residual_and_output_reconstruction_gates_charged=True)
    counts=[]
    if (stage/'donors.json').exists():
        for j, data in enumerate(api.json_read(stage/'donors.json')['circuits']):
            data = dict(data, inputs=len(local_target[0]))
            if api.exact_circuit(data, data['inputs']) != local_target:
                raise ValueError('Forest donor changed local search map')
            circuit=circuit_from_signed(data)
            if transposed:
                circuit=circuit.transposed()
            donor=admit(signed_from_circuit(circuit, f'{mode}_{j}', target), f'{mode}_{j}')
            counts.append(len(donor['gates']))
        record['completed_donors']=len(counts)
        record['best_original_map_signed']=min(counts) if counts else None
        record['summary']=api.json_read(stage/'summary.json') if (stage/'summary.json').exists() else None
    records.append(record); dump(out/'donor_records.json', records)
    # Actual new upstream HelperPool; every binary donor helper is paid.
    # This is an explicitly materialized catalogue for optimization, not the
    # raw internal/terminal-boundary comparison used in yesterday's study.
    native_bank=[]
    for donor in donors:
        native_bank.append(dict(dimension=n, additions=len(donor['gates']),
            substitutions=[dict(i=a, ai=sa, j=b, aj=sb) for a,sa,b,sb in donor['gates']],
            expressions=[[dict(index=w,value=sign)] for w,sign in donor['outputs']]))
    dump(out/'weighted_materialized_bank.json', dict(solutions=native_bank,
        representation='Fully binary paid original-map circuits; terminal expansion explicit'))
    mode='weighted_pool';stage=out/mode
    command=[sys.executable,'-B',RECON/'pool_method_adapters/run.py',
             '--bank',out/'weighted_materialized_bank.json','--matrix',path,
             '--best',str(min(x['additions'] for x in native_bank)),
             '--binary',WEIGHTED,
             '--mode','weighted','--seed',str(seed+410),'--draws','2',
             '--seconds','1.5','--output',stage]
    record=execute(command,10,out/(mode+'.log'))
    record.update(method=mode,upstream_commit='21906e043ab0d652b588864893a07199b915a8e7',
                  donor_representation='Explicitly materialized binary; all helpers paid',
                  shared_seed_control=False)
    weighted_counts=[]
    if (stage/'result.json').exists():
        wr=api.json_read(stage/'result.json')
        for j,draw in enumerate(wr['draws']):
            if draw.get('solution') is not None:
                candidate=dict(api.convert(draw['solution'],target),inputs=n)
                donor=admit(candidate,f'weighted_pool_{j}')
                weighted_counts.append(len(donor['gates']))
        record.update(completed_donors=len(weighted_counts),
                      best_original_map_signed=min(weighted_counts) if weighted_counts else None,
                      attempts=[dict(seed=x['seed'],status=x['status'],
                                     prefix_gates=x['prefix_gates'],
                                     solver_seconds=x.get('solver_seconds'),
                                     additions=x['solution']['additions'] if x.get('solution') else None)
                                for x in wr['draws']])
    records.append(record);dump(out/'donor_records.json',records)
    donor_seconds=time.monotonic()-donor_start
    bank=dict(inputs=n, circuits=donors); dump(out/'donors.json', bank)
    pool_start=time.monotonic(); pool=fast.build_pool(bank, binary=NATIVE)
    dump(out/'pool.json', pool)
    data, productions, best, _ = core.load(out/'pool.json')
    (out/'pool_baseline').mkdir(); core.export(best, data, out/'pool_baseline')
    pool_seconds=time.monotonic()-pool_start
    command=[sys.executable, '-B', REPO/'methods/linear/search.py', '--data',
             out/'pool.json', '--out', out/'plateau', '--engine', 'plateau',
             '--seconds', str(args.search_seconds), '--seed', str(seed+500),
             '--width', '10']
    search_record=execute(command, args.search_seconds+12, out/'plateau.log')
    search_record['result']=api.json_read(out/'plateau/result.json') if (out/'plateau/result.json').exists() else None
    candidates=[out/'pool_baseline/candidate.json', out/'incumbent.json', out/'naive_candidate.json']
    if (out/'plateau/candidate.json').exists():candidates.append(out/'plateau/candidate.json')
    candidates += [out/(d['name']+'_candidate.json') for d in []]
    for j, donor in enumerate(sorted(donors, key=lambda x:len(x['gates']))[:3]):
        dump(out/f'donor_candidate_{j}.json', donor); candidates.append(out/f'donor_candidate_{j}.json')
    candidates=sorted(candidates, key=lambda p:len(api.json_read(p)['gates']))
    orientations=[]; selected=None
    for j, candidate in enumerate(candidates):
        if j >= args.strict_candidates:
            break
        dest=out/f'strict_{j}.slp'
        orient, proof=strict(candidate, path, dest, args.orientation_seconds)
        orient['signed_additions']=len(api.json_read(candidate)['gates'])
        orientations.append(orient)
        if proof is not None:
            selected=(candidate, dest, proof); break
    if selected:
        candidate, dest, proof=selected
        shutil.copy2(candidate, out/'best_candidate.json'); shutil.copy2(dest, out/'best.slp')
        dump(out/'literal_verification.json', proof)
    report=dict(job=job, original_inputs=n, original_outputs=len(target),
                annotation_additions=job.get('baseline_annotation'),
                initial_verified_signed_additions=len(incumbent['data']['gates']),
                final_strict_additions=selected[2]['counts']['binary_additions'] if selected else None,
                best_signed_additions=len(api.json_read(candidates[0])['gates']),
                strict_status='PASS' if selected else 'NO_COMPLETED_STRICT_CERTIFICATE',
                donor_count=len(donors), donor_build_seconds=donor_seconds,
                pool_build_seconds=pool_seconds, pool_forms=len(pool['forms']),
                pool_productions=sum(map(len, productions.values())), search=search_record,
                records=records, orientations=orientations,
                total_seconds=time.monotonic()-total_start,
                upstream_threads=1, harness_parallel_maps=1, basis_change=False,
                scope='Fixed original integer map. Heuristic upper bounds; incomplete calls are timeouts, not impossibility results.')
    dump(out/'summary.json', report)
    print(path.name, 'strict',report['final_strict_additions'],'signed',report['best_signed_additions'],flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--files', nargs='*', help='Optional exact manifest filenames')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--leo-cli', type=Path, help='Compiled upstream reduce CLI')
    parser.add_argument('--repair-binary', type=Path, help='Compiled published repair adapter')
    parser.add_argument('--pool-binary', type=Path, help='Compiled published pool_relations backend')
    parser.add_argument('--weighted-binary', type=Path, help='Compiled pool_method_adapters driver pinned to upstream219')
    parser.add_argument('--history', type=Path, help='Optional original reduced factor JSON directory')
    parser.add_argument('--runtime-python', default=sys.executable, help='Python with OR-Tools for sign orientation')
    parser.add_argument('--method-seconds', type=float, default=12)
    parser.add_argument('--call-timeout', type=float, default=2)
    parser.add_argument('--search-seconds', type=float, default=25)
    parser.add_argument('--attempts', type=int, default=24)
    parser.add_argument('--orientation-seconds', type=float, default=6)
    parser.add_argument('--strict-candidates', type=int, default=4)
    parser.add_argument('--seed', type=int, default=11011000)
    args=parser.parse_args()
    if not args.prepare_only and any(getattr(args, name) is None for name in ('leo_cli','repair_binary','pool_binary','weighted_binary')):
        parser.error('Search requires all four explicit binary paths')
    configure(args)
    for name in ('method_seconds','call_timeout','search_seconds','orientation_seconds'):
        if not math.isfinite(getattr(args,name)) or getattr(args,name)<=0:
            parser.error(name+' must be positive and finite')
    if args.attempts<=0 or args.strict_candidates<=0 or not 0<args.seed<2**32-100000:
        parser.error('Invalid attempts, strict candidates, or seed')
    jobs=json.loads(args.manifest.read_text()) if args.manifest else [infer_job(p) for p in sorted(args.inputs.glob('*.sms'))]
    if args.files:jobs=[job for job in jobs if job['filename'] in args.files]
    for job in jobs:
        if Path(job['filename']).name != job['filename']:
            parser.error('Manifest filenames must be basenames')
        for field in ('candidate','matrix','historical_source'):
            if job.get(field) and not Path(job[field]).is_absolute():
                job[field] = str((args.manifest.parent if args.manifest else Path.cwd()) / job[field])
    if not jobs:parser.error('No selected maps')
    args.out.mkdir(parents=True, exist_ok=False)
    dump(args.out/'protocol.json', dict(method_seconds=args.method_seconds,
                                      call_timeout=args.call_timeout, attempts=args.attempts,
                                      search_seconds=args.search_seconds, seed=args.seed,
                                      matched_controls='retention 0.5 versus 0.9 start from same incumbent and seeds',
                                      original_map_only=True, upstream_threads=1,
                                      search_started=not args.prepare_only))
    results=[]
    for index, job in enumerate(jobs):
        path=Path(job['matrix']) if job.get('matrix') else args.inputs/job['filename']
        expected=job.get('source_sha256')
        if expected and hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Source hash mismatch '+str(path))
        key=f'{index:02d}_'+path.stem
        if args.prepare_only:
            *_, stats=prepare(path,job,args.out/key); results.append(stats)
        else:
            results.append(run_one(path,job,args.out/key,args,index))
        dump(args.out/'summary.json',results)


if __name__=='__main__':
    if sys.argv[1:2] == ['--orient-one']:
        orient_one(sys.argv[2:])
    else:
        main()
