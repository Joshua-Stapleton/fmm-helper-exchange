#!/usr/bin/env python3
"""Fixed-start, single-worker optional-vector omission-size comparison.

These omit optional native hint vectors, not gates from a mandatory pool circuit.
All finished native solutions are saved and exactly replayed. No strict sign or
optimality claim is made for normalized signed candidate exports.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

PACKAGE = Path(__file__).resolve().parent
HERE = PACKAGE
PREV = PACKAGE / 'data'
from runtime import public_root, native_adapter, native_binary, module
PUB = public_root()
adapter = native_adapter()
common = module('native_size_common', PUB / 'methods/linear/reconstruction/common.py')
NATIVE_BINARY = None
BUILD_META = None


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def canonical_features(c):
    n=c['inputs']
    values=[tuple(int(i==j) for j in range(n)) for i in range(n)]
    forms=set()
    for a,sa,b,sb in c['gates']:
        v=tuple(sa*x+sb*y for x,y in zip(values[a],values[b]))
        values.append(v)
        first=next((x for x in v if x),0)
        if first:
            forms.add(v if first>0 else tuple(-x for x in v))
    return forms


def capped_donors(circuits,cap=32):
    ordered=sorted(circuits.items(),key=lambda v:(len(v[1]['gates']),v[0]))
    if len(ordered)<=cap:
        return ordered
    chosen=ordered[:8]
    remaining=ordered[8:]
    features={h:canonical_features(c) for h,c in ordered}
    seen=set().union(*(features[h] for h,c in chosen))
    best=len(ordered[0][1]['gates'])
    while remaining and len(chosen)<cap:
        i=max(range(len(remaining)),key=lambda i:(
            len(features[remaining[i][0]]-seen)/(1+len(remaining[i][1]['gates'])-best),
            -len(remaining[i][1]['gates']),remaining[i][0]))
        item=remaining.pop(i)
        chosen.append(item)
        seen.update(features[item[0]])
    return chosen


CASES = [
    ('old_3x6x8_V', 'old_3x6x8_V155', 155),
    ('hl_4x4x16_V', 'hl_4x4x16_V220', 220),
    ('hl_5x7x7_V', 'hl_5x7x7_V204', 204),
    ('hl_5x5x12_V', 'hl_5x5x12_V230', 230),
    ('hl_6x7x8_V', 'hl_6x7x8_V280', 280),
]
ARMS = [('k2', 2, 2), ('k3', 3, 3), ('uniform1to3', 1, 3), ('uniform1to8', 1, 8)]
SEEDS = [1717101, 1718101]


def run_one(cid, cert, incumbent, arm, low, high, seed, seconds):
    folder = HERE / 'results' / cid / arm / str(seed)
    folder.mkdir(parents=True, exist_ok=True)
    candidate_path = PREV / 'certificates' / cert / 'circuit.json'
    candidate = load(candidate_path)
    target = candidate['target_matrix']
    assert len(candidate['gates']) == incumbent
    assert common.exact_circuit(candidate, candidate['inputs']) == target
    input_path = folder / 'input.txt'
    adapter.write_input(input_path, target, candidate)
    raw_path = folder / 'raw.jsonl'
    binary = NATIVE_BINARY
    cmd = [str(binary), '--input', str(input_path), '--mode', 'vectors',
           '--seed', str(seed), '--draws', '1000', '--seconds-per-draw', '.25',
           '--budget-seconds', str(seconds), '--jsonl', '--output', str(raw_path),
           '--ignore-unused-bound', '1', '--max-abs', '1',
           '--min-remove', str(low), '--max-remove', str(high)]
    command = dict(case_id=cid, incumbent=incumbent, arm=arm, min_remove=low,
                   max_remove=high, seed=seed, command=cmd, budget_seconds=seconds,
                   wrapper_timeout_seconds=seconds+2, candidate_sha256=sha(candidate_path),
                   binary_sha256=sha(binary), single_native_worker=True,
                   optional_hints=True, frozen_incumbent=True)
    dump(folder / 'command.json', command)
    received = []
    offset = 0
    pending = ''
    killed = False
    start = time.monotonic()
    with (folder / 'stderr.txt').open('w') as err, (folder / 'stdout.txt').open('w') as out:
        p = subprocess.Popen(cmd, stderr=err, stdout=out)
        while True:
            if raw_path.exists():
                with raw_path.open() as f:
                    f.seek(offset)
                    pending += f.read()
                    offset = f.tell()
                while '\n' in pending:
                    line, pending = pending.split('\n', 1)
                    if line.strip():
                        received.append((json.loads(line), time.monotonic()-start))
            if p.poll() is not None:
                # One final pass catches bytes written after the previous read.
                if raw_path.exists():
                    with raw_path.open() as f:
                        f.seek(offset)
                        pending += f.read()
                    while '\n' in pending:
                        line, pending = pending.split('\n', 1)
                        if line.strip():
                            received.append((json.loads(line), time.monotonic()-start))
                break
            if time.monotonic()-start > seconds+2:
                p.kill()
                p.wait()
                killed = True
            time.sleep(.005)
    process_wall = time.monotonic()-start
    stats = dict(**command, returncode=p.returncode, wrapper_killed=killed,
                 process_wall_seconds=process_wall, partial_tail_bytes=len(pending.encode()),
                 draws=0, completed=0, unsuccessful=0, invalid=0, duplicates=0,
                 raw_counts=[], normalized_counts=[], anytime=[], best=incumbent)
    unique = {}
    cache = {}
    events = []
    validation_start = time.monotonic()
    for event, observed in received:
        if event.get('event') != 'draw':
            stats[event.get('event', 'unknown')] = event
            continue
        stats['draws'] += 1
        e = {k: v for k, v in event.items() if k != 'solution'}
        e['observed_wall_seconds'] = observed
        if event.get('status') != 'complete' or event.get('solution') is None:
            stats['unsuccessful'] += 1
            events.append(e)
            continue
        try:
            raw = event['solution']
            raw_cost = adapter.replay(raw, target)
            assert raw_cost == raw['additions']
            key_raw = digest(raw)
            if key_raw not in cache:
                c = common.convert(raw, target)
                c['inputs'] = candidate['inputs']
                c = common.normalize(c)
                c['target_matrix'] = target
                assert common.exact_circuit(c, c['inputs']) == target
                cache[key_raw] = c
            c = cache[key_raw]
            h = digest({k: c[k] for k in ('inputs', 'gates', 'outputs')})
            if h in unique:
                stats['duplicates'] += 1
            else:
                unique[h] = c
            stats['completed'] += 1
            stats['raw_counts'].append(raw_cost)
            stats['normalized_counts'].append(len(c['gates']))
            e.update(status='EXACT_PASS', signed_additions=len(c['gates']), candidate_hash=h)
            if len(c['gates']) < stats['best']:
                stats['best'] = len(c['gates'])
                stats['anytime'].append(dict(count=stats['best'], observed_wall_seconds=observed,
                                             draw=stats['draws'], candidate_hash=h))
        except Exception as exc:
            stats['invalid'] += 1
            e.update(status='EXACT_REPLAY_FAILED', error=str(exc))
        events.append(e)
    stats['validation_seconds'] = time.monotonic()-validation_start
    stats['distinct_signed_circuits'] = len(unique)
    stats['best_generated'] = min((len(c['gates']) for c in unique.values()), default=None)
    stats['completed_per_process_wall_second'] = stats['completed']/process_wall
    dump(folder / 'events.json', events)
    dump(folder / 'stats.json', stats)
    # Preserve all distinct completed signed circuits; raw native completions also retained.
    dump(folder / 'donors.json', dict(inputs=candidate['inputs'], circuits=[
        dict(c, name=f'{arm}_{seed}_{h[:12]}') for h, c in sorted(unique.items())]))
    best_dir = HERE / 'candidates' / cid
    best_dir.mkdir(parents=True, exist_ok=True)
    for h, c in unique.items():
        if len(c['gates']) < incumbent:
            dump(best_dir / f"{len(c['gates'])}_{h[:16]}.json", c)
    return stats


def main(seconds=6):
    HERE.mkdir(parents=True, exist_ok=True)
    jobs = [(cid, cert, incumbent, arm, lo, hi, seed, seconds)
            for cid, cert, incumbent in CASES
            for arm, lo, hi in ARMS
            for seed in SEEDS]
    protocol = dict(cases=CASES, arms=ARMS, seeds=SEEDS, seconds_per_job=seconds,
                    jobs=len(jobs), nominal_native_seconds=len(jobs)*seconds,
                    concurrency=1, max_abs=1, ignore_unused_bound=True,
                    initialization='Current strict verified circuit frozen independently for every arm/seed.',
                    interpretation='Native optional helper-vector omissions; not pool removals.',
                    source=BUILD_META,
                    arrival_times='Parent monotonic receipt of complete flushed JSONL lines.',
                    caution='Wall budgets include native preparation; cooperative limits can overrun. Signed candidates need strict sign checks before record claims.')
    dump(HERE/'protocol.json', protocol)
    results = []
    started = time.monotonic()
    for job in jobs:
        stats = run_one(*job)
        results.append(stats)
        dump(HERE/'progress.json', dict(finished=len(results), jobs=len(jobs), wall_seconds=time.monotonic()-started, results=results))
        print(json.dumps({k: stats[k] for k in ('case_id','arm','seed','draws','completed','invalid','best','best_generated','process_wall_seconds')}), flush=True)
    compact = []
    exports = []
    for cid, cert, incumbent in CASES:
        for arm, lo, hi in ARMS:
            r = [v for v in results if v['case_id']==cid and v['arm']==arm]
            completed = sum(v['completed'] for v in r)
            wall = sum(v['process_wall_seconds'] for v in r)
            compact.append(dict(case_id=cid, arm=arm, incumbent=incumbent,
                                best=min(v['best'] for v in r),
                                draws=sum(v['draws'] for v in r), completed=completed,
                                distinct_per_call_sum=sum(v['distinct_signed_circuits'] for v in r),
                                process_wall_seconds=wall, completed_per_second=completed/wall))
            combined={}
            for seed in SEEDS:
                for c in load(HERE/'results'/cid/arm/str(seed)/'donors.json')['circuits']:
                    h=digest({k:c[k] for k in ('inputs','gates','outputs')})
                    combined[h]=c
            selected=capped_donors(combined)
            output=HERE/'exports'/cid/arm
            output.mkdir(parents=True,exist_ok=True)
            dump(output/'donors.json',dict(inputs=load(PREV/'certificates'/cert/'circuit.json')['inputs'],
                                           circuits=[c for h,c in selected]))
            exports.append(dict(case_id=cid,arm=arm,uncapped_unique=len(combined),exported=len(selected),
                                path=str(output/'donors.json'),sha256=sha(output/'donors.json')))
    report = dict(status='COMPLETE', wall_seconds=time.monotonic()-started, protocol=protocol,
                  results=results, comparison=compact, exports=exports,
                  invalid=sum(r['invalid'] for r in results))
    dump(HERE/'report.json', report)
    print(json.dumps(dict(status=report['status'], wall_seconds=report['wall_seconds'], invalid=report['invalid'])), flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=float,default=6)
    p.add_argument('--out',type=Path,default=PACKAGE/'runs/native')
    p.add_argument('--binary',type=Path,help='Existing compatible native driver; otherwise clone pinned source and compile locally.')
    args=p.parse_args()
    HERE=args.out.resolve();HERE.mkdir(parents=True,exist_ok=False)
    NATIVE_BINARY,BUILD_META=native_binary(HERE/'runtime',args.binary)
    main(args.seconds)
