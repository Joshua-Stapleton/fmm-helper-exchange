#!/usr/bin/env python3
"""Independent complete-target-walk replication of Perminov's description.

Unlike the published partial HelperPool sampler, this visits every desired
target in a random order and attempts to construct its entire chain. It uses
one shared computed state, explicit cycle rejection, failed-attempt rollback,
and at most 1000 attempted productions per top-level target.

Weighted production permutation, shared-state cycle rejection and rollback
follow the structure of Perminov's MIT-licensed HelperPool. See NOTICE.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('targetwalk_paid', HERE/'paid.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_graph(data):
    n = data['inputs']
    require(type(n) is int and n > 0, 'Positive input count required')
    forms = data['forms']
    require(isinstance(forms, list) and len(forms) >= n, 'Form array required')
    for row in forms:
        require(isinstance(row, list) and len(row) == n
                and all(type(x) is int for x in row), 'Exact integer form required')
        require(any(row) and audit.canonical(row)[0] == tuple(row), 'Nonzero canonical signed form required')
    require(len({tuple(row) for row in forms}) == len(forms), 'Duplicate signed form')
    require(forms[:n] == [[int(i == j) for j in range(n)] for i in range(n)], 'Original unit roots required')
    prods = {}
    for output, rows in data['productions'].items():
        require(output.isascii() and output.isdigit() and str(int(output)) == output, 'Noncanonical production key')
        output = int(output)
        require(n <= output < len(forms) and isinstance(rows, list), 'Production output invalid')
        options = []
        for row in rows:
            require(isinstance(row, list) and len(row) == 4, 'Binary production required')
            a, sa, b, sb = row
            require(type(a) is int and type(b) is int and 0 <= a < len(forms)
                    and 0 <= b < len(forms), 'Missing production parent')
            require(type(sa) is int and type(sb) is int and sa in (-1, 1)
                    and sb in (-1, 1), 'Free nonunit scalar')
            require(forms[output] == [sa*x+sb*y for x, y in zip(forms[a], forms[b])], 'Production identity failed')
            options.append(tuple(row))
        require(len(set(options)) == len(options), 'Repeated production')
        prods[output] = options
    outputs = data['outputs']
    require(isinstance(outputs, list) and outputs, 'Ordered output list required')
    target = data['target_matrix']
    require(isinstance(target, list) and len(target) == len(outputs)
            and all(isinstance(row, list) and len(row) == n
                    and all(type(x) is int for x in row) for row in target),
            'Ordered exact integer target matrix required')
    actual = []
    for row in outputs:
        require(isinstance(row, list) and len(row) == 2, 'Signed output required')
        index, sign = row
        require(type(index) is int and 0 <= index < len(forms) and type(sign) is int
                and sign in (-1, 1), 'Invalid signed output')
        actual.append([sign*x for x in forms[index]])
    require(actual == target, 'Graph changes ordered target map')
    weights = data['production_weights']
    for mode in ('weighted', 'uniform'):
        require(mode in weights, 'Missing production weight condition')
        for output, options in prods.items():
            values = weights[mode][str(output)]
            require(isinstance(values, list) and len(values) == len(options), 'Weight alignment mismatch')
            require(all(type(value) in (int, float) and math.isfinite(value) and value >= 0
                        for value in values), 'Invalid production weights')
            require(not options or any(value > 0 for value in values), 'No eligible producer')
    return n, forms, prods, outputs


def weighted_permutation(weights, rng):
    # Exponential races implement a weighted permutation without replacement.
    # Zero-weight productions cannot be selected. No endpoint-cost ranking is
    # inserted into this reproduction of the stated frequency-based policy.
    return [index for _, index in sorted((-math.log1p(-rng.random())/weight, index)
                                        for index, weight in enumerate(weights) if weight > 0)]


def draw_program(data, prods, mode, seed, max_steps=1000):
    n = data['inputs']
    rng = random.Random(seed)
    order = list(range(len(data['outputs'])))
    rng.shuffle(order)
    computed = {i: i for i in range(n)}
    active = set()
    schedule = []
    productions_attempted = 0
    cycle_rejections = 0
    rolled_back_gates = 0
    failed_targets = []

    def rollback(mark):
        nonlocal rolled_back_gates
        while len(schedule) > mark:
            form, _ = schedule.pop()
            del computed[form]
            rolled_back_gates += 1

    def build(form, attempts):
        nonlocal productions_attempted, cycle_rejections
        if form in computed:
            return True
        if form in active:
            cycle_rejections += 1
            return False
        active.add(form)
        options = prods.get(form, ())
        weights = data['production_weights'][mode].get(str(form), [])
        for choice in weighted_permutation(weights, rng):
            attempts[0] += 1
            if attempts[0] > max_steps:
                break
            productions_attempted += 1
            production = options[choice]
            a, _, b, _ = production
            mark = len(schedule)
            if build(a, attempts) and build(b, attempts):
                computed[form] = n+len(schedule)
                schedule.append((form, production))
                active.remove(form)
                return True
            rollback(mark)
        active.remove(form)
        return False

    for row_index in order:
        output, _ = data['outputs'][row_index]
        if not build(output, [0]):
            failed_targets.append(row_index)
            break
    stats = dict(productions_attempted=productions_attempted,
                 cycle_rejections=cycle_rejections, rolled_back_gates=rolled_back_gates,
                 failed_targets=failed_targets, paid_gates=len(schedule))
    if failed_targets:
        return None, stats
    gates = []
    emitted = {i: i for i in range(n)}
    for form, (a, sa, b, sb) in schedule:
        require(a in emitted and b in emitted, 'Schedule lost a dependency')
        gates.append([emitted[a], sa, emitted[b], sb])
        emitted[form] = n+len(gates)-1
    program = dict(inputs=n, gates=gates,
                   outputs=[[emitted[form], sign] for form, sign in data['outputs']])
    # The graph and schedule are exact; replay each best program independently
    # in run(). This fast per-draw check also ensures no gate is unused.
    needed = set()
    stack = [form for form, _ in data['outputs']]
    selected = dict(schedule)
    while stack:
        form = stack.pop()
        if form < n or form in needed:
            continue
        needed.add(form)
        a, _, b, _ = selected[form]
        stack.extend((a, b))
    require(len(needed) == len(schedule), 'A complete walk retained unused gates')
    stats['target_visit_order'] = order
    return program, stats


def run(args):
    require(args.draws > 0 and args.seed >= 0 and args.max_steps > 0, 'Invalid finite campaign parameters')
    require(math.isfinite(args.wall_limit) and args.wall_limit > 0, 'Invalid wall limit')
    require(not args.out.exists(), 'Refusing to replace experiment output')
    raw = args.graph.read_bytes()
    data = json.loads(raw)
    setup_start = time.monotonic()
    _, _, prods, _ = validate_graph(data)
    setup_seconds = time.monotonic()-setup_start
    args.out.mkdir(parents=True)
    plan = dict(graph_sha256=hashlib.sha256(raw).hexdigest(), draws_per_mode=args.draws,
                modes=['weighted', 'uniform'], seed_start=args.seed,
                max_production_attempts_per_top_level_target=args.max_steps,
                global_wall_limit=args.wall_limit,
                setup_validation_seconds=setup_seconds,
                method='Independent complete-target-walk replication of described policy; not published partial HelperPool API',
                paid_model='Original inputs; unit signed wires; strict orientation separate')
    (args.out/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    rows = []
    bests = {}
    histograms = {mode:Counter() for mode in plan['modes']}
    start = time.monotonic()
    with (args.out/'draws.csv').open('w') as csv:
        csv.write('mode,seed,status,paid_gates,seconds,cumulative_seconds,productions_attempted,cycle_rejections,rolled_back_gates\n')
        for index in range(args.draws):
            if time.monotonic()-start >= args.wall_limit:
                break
            # Same seed schedule for both conditions. Alternate their order.
            modes = plan['modes'] if index % 2 == 0 else list(reversed(plan['modes']))
            for mode in modes:
                seed = args.seed+index
                begin = time.monotonic()
                program, stats = draw_program(data, prods, mode, seed, args.max_steps)
                elapsed = time.monotonic()-begin
                row = dict(mode=mode, seed=seed, status='complete' if program else 'failed_walk',
                           paid_gates=None if program is None else len(program['gates']),
                           seconds=elapsed, cumulative_seconds=time.monotonic()-start,
                           **{k:stats[k] for k in ('productions_attempted','cycle_rejections','rolled_back_gates')})
                rows.append(row)
                csv.write(','.join(str(row[key]) for key in ('mode','seed','status','paid_gates','seconds',
                          'cumulative_seconds','productions_attempted','cycle_rejections','rolled_back_gates'))+'\n')
                if program is None:
                    continue
                count = len(program['gates'])
                histograms[mode][count] += 1
                if mode not in bests or count < bests[mode]['paid_gates']:
                    proof = audit.replay(program, data['target_matrix'])
                    bests[mode] = dict(row, exact_verification=proof, program=program)
                    (args.out/(mode+'_best.json')).write_text(json.dumps(program, indent=2)+'\n')
                    (args.out/(mode+'_best_report.json')).write_text(json.dumps(bests[mode], indent=2)+'\n')
                    print(mode, seed, 'best', count, 'at', round(row['cumulative_seconds'], 6), flush=True)
    summary = dict(plan=plan, status='DONE' if len(rows)==2*args.draws else 'WALL_LIMIT',
                   attempted_draws=len(rows), wall_seconds=time.monotonic()-start, conditions=[])
    for mode in plan['modes']:
        selected = [row for row in rows if row['mode'] == mode]
        completed = [row for row in selected if row['status'] == 'complete']
        summary['conditions'].append(dict(mode=mode, attempts=len(selected), completions=len(completed),
                                          failed_walks=len(selected)-len(completed),
                                          best=min(histograms[mode], default=None),
                                          best_discovered_at_seconds=bests.get(mode, {}).get('cumulative_seconds'),
                                          success_size_distribution=dict(sorted(histograms[mode].items())),
                                          total_draw_seconds=sum(row['seconds'] for row in selected),
                                          productions_attempted=sum(row['productions_attempted'] for row in selected),
                                          cycle_rejections=sum(row['cycle_rejections'] for row in selected),
                                          rolled_back_gates=sum(row['rolled_back_gates'] for row in selected)))
    (args.out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graph', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--draws', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=42000)
    parser.add_argument('--max-steps', type=int, default=1000)
    parser.add_argument('--wall-limit', type=float, default=120)
    run(parser.parse_args())
