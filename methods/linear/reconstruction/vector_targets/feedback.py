#!/usr/bin/env python3
"""Feed best complete pooled circuits back to bounded native vector restarts."""
import hashlib
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
PUB = HERE.parents[3]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


adapter = module('feedback_adapter', HERE/'toolchain/adapter.py')
api = module('feedback_common', PUB/'methods/linear/reconstruction/common.py')


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n')


def run_case(case, pool):
    target = load(case['matrix'])
    candidate = load(case['candidate'])
    available = [c for c in pool['results'] if c['case_id'] == case['id'] and c.get('exact_map_verified')]
    if available:
        winner = min(available, key=lambda c: c['best_signed_additions'])
        if winner['best_signed_additions'] < len(candidate['gates']):
            candidate = load(winner['candidate'])
    initial = len(candidate['gates'])
    out = HERE/'feedback_results'/case['id']
    out.mkdir(parents=True, exist_ok=False)
    records = []
    started = time.monotonic()
    for epoch, (cap, min_remove, max_remove, savings, tight) in enumerate([
            (1, 1, 8, 0, False), (2, 2, 12, .01, False), (1, 1, 8, 0, True)]):
        directory = out/str(epoch)
        directory.mkdir()
        adapter.write_input(directory/'input.txt', target, candidate)
        seed = 17170000 + int(hashlib.sha256(case['id'].encode()).hexdigest()[:6], 16) + epoch*10000
        command = [str(HERE/'toolchain/native_driver_v2'), '--input', str(directory/'input.txt'),
                   '--mode', 'vectors', '--seed', str(seed), '--draws', '1000',
                   '--seconds-per-draw', '1', '--budget-seconds', '10',
                   '--jsonl', '--output', str(directory/'raw.jsonl'),
                   '--ignore-unused-bound', '1', '--max-abs', str(cap),
                   '--min-remove', str(min_remove), '--max-remove', str(max_remove),
                   '--savings', str(savings), '--bound', str(len(candidate['gates']) - 1 if tight else len(candidate['gates']) + 1)]
        before = len(candidate['gates'])
        start = time.monotonic()
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=13)
            status = str(process.returncode)
        except subprocess.TimeoutExpired:
            status = 'HARD_TIMEOUT'
        elapsed = time.monotonic()-start
        complete = invalid = 0
        improving = []
        raw = (directory/'raw.jsonl').read_text()
        for line in raw.splitlines(keepends=True):
            if not line.endswith('\n'):
                continue
            event = json.loads(line)
            if event.get('event') != 'draw' or event.get('status') != 'complete':
                continue
            solution = event['solution']
            adapter.replay(solution, target)
            circuit = api.normalize(dict(api.convert(solution, target), inputs=len(target[0])))
            circuit['target_matrix'] = target
            assert api.exact_circuit(circuit, circuit['inputs']) == target
            complete += 1
            if len(circuit['gates']) < len(candidate['gates']):
                candidate = circuit
                improving.append(dict(seed=event['seed'], additions=len(circuit['gates'])))
        record = dict(epoch=epoch, command=command, status=status, elapsed_seconds=elapsed,
                      cap=cap, min_remove=min_remove, max_remove=max_remove, savings=savings,
                      bound_tight=tight, before=before, after=len(candidate['gates']),
                      complete=complete, invalid=invalid, improvements=improving)
        records.append(record)
        dump(directory/'summary.json', record)
        dump(out/'candidate.json', candidate)
    report = dict(case_id=case['id'], initial=initial, best=len(candidate['gates']),
                  elapsed_seconds=time.monotonic()-started, epochs=records,
                  candidate=str(out/'candidate.json'), exact_map_verified=True,
                  scope='Adaptive signed-circuit experiment; different caps/removal sizes/bounds are confounded. Not a matched-method comparison.')
    dump(out/'report.json', report)
    return report


if __name__ == '__main__':
    cases = load(HERE/'benchmarks/manifest.json')['cases']
    for case in cases:
        for key in ('matrix','original_matrix','candidate','native','donors','native_donors','strict_incumbent'):
            case[key]=str(HERE/case[key])
    wanted = {'old_3x6x8_V', 'hl_4x4x16_V', 'hl_5x7x7_V', 'hl_3x6x6_V'}
    pool = load(HERE/'pooling/results/report.json')
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_case, case, pool) for case in cases if case['id'] in wanted]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps({k: result[k] for k in ('case_id', 'initial', 'best', 'elapsed_seconds')}), flush=True)
    dump(HERE/'feedback_results/report.json', dict(status='COMPLETE', results=results))
