#!/usr/bin/env python3
"""Equal-total-time single-start and bounded-portfolio searches on frozen pools."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from study_common import configure,load,dump,sha,replay
PUB=core=None


def canonical(v):
    sign = next(1 if x > 0 else -1 for x in v if x)
    return tuple(sign*x for x in v), sign


def bind(candidate, data, prods, lookup):
    """Embed an exact donor in the common graph without preserving its IDs."""
    n = data['inputs']
    replay(candidate, data['target_matrix'])
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    aliases = [(i, 1) for i in range(n)]
    selected = {}
    for a, sa, b, sb in candidate['gates']:
        value = tuple(sa*x+sb*y for x, y in zip(values[a], values[b]))
        form, orient = canonical(value)
        out = lookup[form]
        aa, oa = aliases[a]
        bb, ob = aliases[b]
        left, right = sa*oa*orient, sb*ob*orient
        if aa > bb:
            aa, bb, left, right = bb, aa, right, left
        production = (aa, left, bb, right)
        if out >= n and out not in selected:
            assert out not in (aa, bb) and production in prods[out]
            selected[out] = production
        values.append(value)
        aliases.append((out, orient))
    return core.audit(selected, data, prods)


def reconnect(helpers, data, prods):
    n = data['inputs']
    allowed = set(range(n)) | set(helpers) | {o for o, s in data['outputs']}
    ready, chosen = set(range(n)), {}
    while True:
        changed = False
        for out in sorted(prods):
            if out not in allowed or out in ready:
                continue
            for a, sa, b, sb in prods[out]:
                if a in ready and b in ready:
                    ready.add(out)
                    chosen[out] = (a, sa, b, sb)
                    changed = True
                    break
        if not changed:
            return core.audit(chosen, data, prods)


def prepare_donors(pool_path, candidates, best_candidate, folder):
    """Generic embedding/dedup/selection for a supplied exact common pool."""
    start=time.monotonic()
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    data,prods,_,_=core.load(pool_path)
    lookup={tuple(v):i for i,v in enumerate(data['forms'])}
    candidates=[best_candidate,*candidates]
    targets = {o for o, s in data['outputs']}
    unique = {}
    for index, candidate in enumerate(candidates):
        chosen = bind(candidate, data, prods, lookup)
        helpers = tuple(sorted(set(chosen)-targets))
        unique.setdefault(helpers, dict(index=index, helpers=helpers, selected=chosen,
                                       normalized_cost=len(chosen), raw_cost=len(candidate['gates'])))
    best = bind(best_candidate, data, prods, lookup)
    best_helpers = tuple(sorted(set(best)-targets))
    ordered = sorted(unique.values(), key=lambda r: (r['normalized_cost'], r['helpers']))
    base = unique[best_helpers]
    assert min(r['normalized_cost'] for r in ordered) == len(best), 'Supply the cheapest normalized incumbent from the donor bank'
    cost_ordered = [base] + [r for r in ordered if r['helpers'] != best_helpers][:7]
    diverse = [base]
    used = set(best_helpers)
    eligible = [r for r in ordered if r['normalized_cost'] <= len(best)+8 and r['helpers'] != best_helpers]
    while eligible and len(diverse) < 8:
        selected = max(eligible, key=lambda r: (len(set(r['helpers'])-used)/(1+r['normalized_cost']-len(best)),
                                               -r['normalized_cost'], r['helpers']))
        diverse.append(selected)
        used.update(selected['helpers'])
        eligible.remove(selected)
    arms = dict(best_only=[base], cost_ordered=cost_ordered, diverse=diverse)
    for row in {r['index']: r for rows in arms.values() for r in rows}.values():
        recon = reconnect(row['helpers'], data, prods)
        row['initial_reconnected_cost'] = len(recon)
    dump(folder/'pool.json', data)
    edges = [(o, *p) for o in sorted(prods) for p in prods[o]]
    for arm, rows in arms.items():
        for index, row in enumerate(rows):
            text = f"{len(data['forms'])} {data['inputs']} {len(targets)} {len(row['helpers'])} {len(edges)}\n"
            text += ' '.join(map(str, sorted(targets)))+'\n'+' '.join(map(str, row['helpers']))+'\n'
            text += ''.join(f'{o} {a} {b}\n' for o, a, sa, b, sb in edges)
            path = folder/f'{arm}_{index}.txt'
            path.write_text(text)
            row.setdefault('inputs', {})[arm] = str(path)
    report = dict(case_id='custom', pool_source='supplied exact pool', pool_sha256=sha(pool_path),
                  forms=len(data['forms']), exact_relations=len(edges), supplied_donors=len(candidates),
                  distinct_start_helper_sets=len(unique), incumbent=len(best),
                  seconds=time.monotonic()-start,
                  arms={a:[{k:v for k,v in r.items() if k!='selected'} for r in rows] for a,rows in arms.items()})
    dump(folder/'preparation.json', report)
    return data, prods, edges, best, arms, report


def run(case, data, prods, edges, incumbent, arms, seed, binary, output_root, seconds=6):
    reports = []
    target = data['target_matrix']
    for arm, starts in arms.items():
        folder = output_root/case['id']/arm/str(seed)
        folder.mkdir(parents=True, exist_ok=False)
        best = incumbent
        best_so_far = len(incumbent)
        started = time.monotonic()
        calls = []
        for index, row in enumerate(starts):
            out = folder/str(index)
            out.mkdir()
            # Search time is divided equally. Actual process and audit costs
            # are reported separately, rather than being hidden as free work.
            budget = seconds/len(starts)
            command = [str(binary), row['inputs'][arm], str(budget), str(seed+index), '6', str(out/'selection.txt')]
            start = time.monotonic()
            p = subprocess.run(command, capture_output=True, text=True, timeout=budget+5)
            native_wall = time.monotonic()-start
            assert p.returncode == 0, p.stderr
            (out/'stderr.txt').write_text(p.stderr)
            chosen = row['selected']
            if (out/'selection.txt').exists():
                lines = (out/'selection.txt').read_text().splitlines()
                assert lines[0] == 'FOUND'
                selected = {}
                for line in lines[1:]:
                    form, edge_id = map(int, line.split())
                    form2, *production = edges[edge_id]
                    assert form2 == form and form not in selected
                    selected[form] = tuple(production)
                chosen = core.audit(selected, data, prods)
            else:
                chosen = reconnect(row['helpers'], data, prods)
            core.export(chosen, data, out)
            candidate = load(out/'candidate.json')
            assert replay(candidate, target) == len(chosen)
            if len(chosen) < best_so_far:
                best = chosen
                best_so_far = len(chosen)
                core.export(best, data, folder)
            metrics = re.search(r'FINISHED steps=(\d+) closures=(\d+) accepted=(\d+)', p.stderr)
            calls.append(dict(start_index=row['index'], normalized_start=row['normalized_cost'],
                              initial_reconnected=row['initial_reconnected_cost'], final=len(chosen),
                              nominal_search_seconds=budget, native_process_seconds=native_wall,
                              steps=int(metrics[1]) if metrics else None,
                              closures=int(metrics[2]) if metrics else None,
                              helper_set=list(row['helpers']), command=command))
        report = dict(case_id=case['id'], arm=arm, seed=seed, starts=len(starts),
                      initial=len(incumbent), best=best_so_far, calls=calls,
                      nominal_search_seconds=seconds, wall_seconds=time.monotonic()-started,
                      exact_map_verified=True)
        dump(folder/'report.json', report)
        reports.append(report)
        print(json.dumps({k:report[k] for k in ('case_id','arm','seed','starts','initial','best','wall_seconds')}), flush=True)
    return reports



def frozen(case_id):
    folder = HERE/'data'/case_id
    data, prods, _, _ = core.load(folder/'pool.json')
    prep = load(folder/'preparation.json')
    targets = {o for o,s in data['outputs']}
    arms = prep['arms']
    for arm, rows in arms.items():
        for index, row in enumerate(rows):
            row['helpers'] = tuple(row['helpers'])
            row['selected'] = reconnect(row['helpers'], data, prods)
            row['inputs'] = {arm: str(folder/f'{arm}_{index}.txt')}
    initial = reconnect(arms['best_only'][0]['helpers'], data, prods)
    assert len(initial) == prep['incumbent']
    edges = [(o,*p) for o in sorted(prods) for p in prods[o]]
    return data, prods, edges, initial, arms


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--case', action='append', help='Frozen case ID; repeat to select several')
    parser.add_argument('--seconds', type=float, default=6, help='Total nominal search seconds per arm')
    parser.add_argument('--seed', type=int, action='append')
    parser.add_argument('--out', type=Path, required=True, help='Fresh output directory')
    parser.add_argument('--pool', type=Path, help='Optional custom exact pool')
    parser.add_argument('--donors', type=Path, help='Optional {inputs,circuits} bank for custom pool')
    parser.add_argument('--incumbent', type=Path, help='Optional best circuit for custom pool')
    args = parser.parse_args()
    assert args.seconds > 0
    global PUB, core
    PUB, core = configure(args.repo)
    args.out.mkdir(parents=True, exist_ok=False)
    compiler = next((shutil.which(c) for c in ('c++','g++','clang++') if shutil.which(c)), None)
    assert compiler, 'C++17 compiler required only for timed reruns'
    binary = (args.out/'plateau').resolve()
    subprocess.run([compiler,'-O3','-std=c++17',str(PUB/'methods/linear/plateau.cpp'),'-o',str(binary)],check=True)
    results = []
    started = time.monotonic()
    if args.pool:
        assert args.donors and args.incumbent
        candidates = load(args.donors)['circuits']
        data,prods,edges,incumbent,arms,_ = prepare_donors(args.pool, candidates, load(args.incumbent), args.out/'custom_data')
        cases = [('custom', (data,prods,edges,incumbent,arms))]
    else:
        assert not args.donors and not args.incumbent
        chosen = args.case or sorted(p.name for p in (HERE/'data').iterdir() if p.is_dir())
        cases = [(cid, frozen(cid)) for cid in chosen]
    for cid, payload in cases:
        for seed in args.seed or [171721,171821]:
            results.extend(run(dict(id=cid),*payload,seed,binary,args.out,args.seconds))
    dump(args.out/'report.json',dict(status='COMPLETE',results=results,
        wall_seconds=time.monotonic()-started,
        source_sha256=sha(PUB/'methods/linear/plateau.cpp'),
        scope='Signed discovery. Same fixed pools; total nominal time per arm. More expensive starts inherit a higher plateau size ceiling; this is an operational policy comparison, not an isolated diversity theorem.'))


if __name__ == '__main__':
    main()
