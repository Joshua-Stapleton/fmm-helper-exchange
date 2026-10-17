#!/usr/bin/env python3
"""Optimize an exact signed addition DAG over one explicitly frozen form pool.

Every noninput selected form costs one addition. Exactly one supplied binary
production is chosen for each selected form, parents must be selected, and
strict conditional topological ranks forbid cyclic support. This is a finite
pool model, not an unrestricted SLP lower-bound method.
"""
import argparse
import json
import time
from pathlib import Path

def checked_circuit(pool, selection):
    n = pool['inputs']
    forms = pool['forms']
    ready = {i: i for i in range(n)}
    wires = list(forms[:n])
    gates = []
    pending = dict(selection)
    while pending:
        advanced = False
        for t, prod in list(pending.items()):
            a, sa, b, sb = prod
            if a not in ready or b not in ready:
                continue
            value = [sa*x + sb*y for x, y in zip(wires[ready[a]], wires[ready[b]])]
            assert value == forms[t], (t, prod)
            gates.append([ready[a], sa, ready[b], sb])
            ready[t] = len(wires)
            wires.append(value)
            del pending[t]
            advanced = True
        if not advanced:
            raise ValueError('Cyclic or missing selected production')
    outputs = [[ready[t], s] for t, s in pool['outputs']]
    actual = [[s*x for x in wires[t]] for t, s in outputs]
    assert actual == pool['target_matrix']
    # Require that the saved gate count has no unused selected forms.
    needed = {t for t, _ in pool['outputs']}
    todo = list(needed)
    while todo:
        t = todo.pop()
        if t < n:
            continue
        a, _, b, _ = selection[t]
        for parent in (a, b):
            if parent not in needed:
                needed.add(parent)
                todo.append(parent)
    assert set(selection) <= needed
    return {'name': pool['name'] + '_cpsat', 'inputs': n,
            'additions_signed': len(gates), 'free_signed_wires': True,
            'gates': gates, 'outputs': outputs, 'target_matrix': pool['target_matrix'],
            'pool_selection': {str(t): p for t, p in selection.items()}}


def main():
    from ortools.sat.python import cp_model

    ap = argparse.ArgumentParser()
    ap.add_argument('pool')
    ap.add_argument('candidate')
    ap.add_argument('--output', required=True)
    ap.add_argument('--seconds', type=float, default=120)
    ap.add_argument('--seed', type=int, default=171744)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    pool = json.loads(Path(args.pool).read_text())
    initial = json.loads(Path(args.candidate).read_text())
    n, forms = pool['inputs'], pool['forms']
    count = len(forms)
    productions = {int(t): p for t, p in pool['productions'].items()}
    hint = {int(t): p for t, p in initial['pool_selection'].items()}
    checked_circuit(pool, hint)
    model = cp_model.CpModel()
    active = [model.new_bool_var(f'active_{t}') for t in range(count)]
    rank = [model.new_int_var(0, count-n, f'rank_{t}') for t in range(count)]
    selectors = {}
    for t in range(n):
        model.add(active[t] == 1)
        model.add(rank[t] == 0)
    for t in range(n, count):
        choices = []
        for j, prod in enumerate(productions.get(t, [])):
            a, sa, b, sb = prod
            assert [sa*x + sb*y for x,y in zip(forms[a], forms[b])] == forms[t]
            chosen = model.new_bool_var(f'producer_{t}_{j}')
            selectors[t, j] = chosen
            choices.append(chosen)
            model.add_implication(chosen, active[a])
            model.add_implication(chosen, active[b])
            model.add(rank[t] > rank[a]).only_enforce_if(chosen)
            model.add(rank[t] > rank[b]).only_enforce_if(chosen)
            model.add_hint(chosen, int(hint.get(t) == prod))
        model.add(sum(choices) == active[t])
        model.add(rank[t] >= 1).only_enforce_if(active[t])
        model.add(rank[t] == 0).only_enforce_if(active[t].Not())
        model.add_hint(active[t], int(t in hint))
    for t, s in pool['outputs']:
        model.add(active[t] == 1)
    cost = sum(active[n:])
    model.add(cost <= len(hint))
    model.minimize(cost)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = args.seed
    solver.parameters.log_search_progress = True
    solver.parameters.log_to_stdout = False
    log = []
    solver.log_callback = log.append
    started = time.monotonic()
    status = solver.solve(model)
    elapsed = time.monotonic() - started
    record = {'pool': args.pool, 'candidate': args.candidate,
              'form_count': count, 'production_count': len(selectors),
              'workers': 1, 'time_limit_seconds': args.seconds,
              'wall_seconds': elapsed, 'seed': args.seed,
              'status': solver.status_name(status),
              'best_bound': solver.best_objective_bound,
              'scope': 'Exact finite-pool DAG model; no unrestricted SLP claim or proof certificate.'}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected = {}
        for (t, j), var in selectors.items():
            if solver.value(var):
                selected[t] = productions[t][j]
        # Removing unused gates preserves validity and improves any feasible
        # nonoptimal incumbent before writing it as an independently replayed DAG.
        needed = {t for t, _ in pool['outputs']}
        todo = list(needed)
        while todo:
            t = todo.pop()
            if t >= n:
                a, _, b, _ = selected[t]
                for p in (a,b):
                    if p not in needed:
                        needed.add(p); todo.append(p)
        selected = {t:p for t,p in selected.items() if t in needed}
        certificate = checked_circuit(pool, selected)
        (out/'candidate.json').write_text(json.dumps(certificate, indent=2)+'\n')
        record['objective'] = solver.objective_value
        record['replayed_gate_count'] = len(selected)
        record['independent_integer_replay'] = True
    (out/'solver.log').write_text(''.join(log)+'\n'+solver.response_stats()+'\n')
    (out/'report.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
