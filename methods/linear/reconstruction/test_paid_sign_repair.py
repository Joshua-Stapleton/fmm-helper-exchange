#!/usr/bin/env python3
"""Small solver tests with independent integer and literal-program replay.

Place beside paid_sign_repair.py. Requires its OR-Tools dependency. Expected
counts below describe these explicit test witnesses, not general optimality.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def coefficients(data, strict=True):
    n = data['inputs']
    check(type(n) is int and n > 0, 'Invalid input count')
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    for index, gate in enumerate(data['gates']):
        check(len(gate) == 4 and all(type(x) is int for x in gate), 'Invalid gate')
        a, sa, b, sb = gate
        check(0 <= a < n + index and 0 <= b < n + index, 'Future reference')
        check(sa in (-1, 1) and sb in (-1, 1), 'Nonunit scalar')
        if strict:
            check(sa == 1 or sb == 1, 'Unpaid unary negation')
        values.append(tuple(sa*x + sb*y for x, y in zip(values[a], values[b])))
    result, pending, live = [], [], set()
    for wire, sign in data['outputs']:
        check(type(wire) is int and 0 <= wire < len(values), 'Invalid output')
        check(type(sign) is int and sign in (-1, 1), 'Invalid output sign')
        if strict:
            check(sign == 1, 'Unpaid output negation')
        result.append([sign*x for x in values[wire]])
        pending.append(wire)
    while pending:
        wire = pending.pop()
        if wire < n or wire in live:
            continue
        live.add(wire)
        a, _, b, _ = data['gates'][wire-n]
        pending.extend((a, b))
    if strict:
        check(len(live) == len(data['gates']), 'Unused paid gate')
    return result, values


def literal_data(text, n):
    names = {f'i{i}': i for i in range(n)}
    gates, outputs = [], {}
    for line in text.splitlines():
        match = re.fullmatch(r'([to]\d+):=([it]\d+)(?:([+-])([it]\d+))?;', line.strip())
        check(match is not None, 'Unsupported literal grammar')
        name, a, op, b = match.groups()
        check(name not in names and a in names and (b is None or b in names), 'Invalid literal reference')
        if name.startswith('t'):
            check(name == f't{len(gates)}' and op is not None, 'Uncharged temporary alias')
            gates.append([names[a], 1, names[b], 1 if op == '+' else -1])
            names[name] = n + len(gates) - 1
        else:
            check(op is None, 'Uncharged output arithmetic')
            outputs[int(name[1:])] = [names[a], 1]
            names[name] = names[a]
    check(set(outputs) == set(range(len(outputs))), 'Nonconsecutive output order')
    return dict(inputs=n, gates=gates, outputs=[outputs[i] for i in range(len(outputs))])


CASES = [
    ('negative_single_input', dict(inputs=1, gates=[], outputs=[[0, -1]]), [[-1]], 2),
    ('opposite_difference_outputs', dict(inputs=2, gates=[[0, 1, 1, -1]], outputs=[[2, 1], [2, -1]]), [[1, -1], [-1, 1]], 2),
    ('two_negative_inputs_shared_zero', dict(inputs=2, gates=[], outputs=[[0, -1], [1, -1]]), [[-1, 0], [0, -1]], 3),
    ('double_negative_internal', dict(inputs=2, gates=[[0, -1, 1, -1]], outputs=[[2, 1]]), [[-1, -1]], 3),
    ('paid_zero_output', dict(inputs=1, gates=[[0, 1, 0, -1]], outputs=[[1, 1]]), [[0]], 1),
    ('negated_paid_zero_output', dict(inputs=1, gates=[[0, 1, 0, -1]], outputs=[[1, -1]]), [[0]], 1),
    ('duplicate_negative_alias', dict(inputs=1, gates=[], outputs=[[0, 1], [0, -1], [0, -1]]), [[1], [-1], [-1]], 2),
]


def main():
    implementation = Path(__file__).with_name('paid_sign_repair.py')
    spec = importlib.util.spec_from_file_location('paid_sign_repair_under_test', implementation)
    repair = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repair)
    reports = []
    for index, (name, source, target, expected) in enumerate(CASES):
        check(coefficients(source, strict=False)[0] == target, name + ': invalid fixture')
        data, text, metadata = repair.repair(deepcopy(source), target, 1.0, 47169900 + index)
        actual, values = coefficients(data)
        check(actual == target, name + ': JSON coefficient mismatch')
        check(len(data['gates']) == expected == metadata['final_strict_additions'], name + ': incorrect paid count')
        literal = literal_data(text, source['inputs'])
        for key in ('inputs', 'gates', 'outputs'):
            check(literal[key] == data[key], name + ': JSON/literal mismatch')
        check(coefficients(literal)[0] == target, name + ': literal coefficient mismatch')
        # Mutants bypass liveness checks: their rejection must follow from the
        # changed coefficients, not merely from leaving a gate unused.
        sign_rejected = False
        for gate in reversed(range(len(data['gates']))):
            mutant = deepcopy(data)
            mutant['gates'][gate][3] *= -1
            if coefficients(mutant, strict=False)[0] != target:
                sign_rejected = True
                break
        check(sign_rejected, name + ': sign mutation was not rejected')
        omitted_rejected = None
        for output, (wire, _) in enumerate(data['outputs']):
            if wire < data['inputs'] or metadata['gate_tags'][wire-data['inputs']] != 'output_sign_correction':
                continue
            a, _, b, _ = data['gates'][wire-data['inputs']]
            for parent in (a, b):
                mutant = deepcopy(data)
                mutant['outputs'][output] = [parent, 1]
                if coefficients(mutant, strict=False)[0] != target:
                    omitted_rejected = True
                    break
            check(omitted_rejected, name + ': omitted correction was not rejected')
            break
        reports.append(dict(name=name, status='PASS', binary_additions=expected,
                            zero_valued_gates=sum(not any(v) for v in values[source['inputs']:]),
                            sign_mutation_rejected=True,
                            omitted_output_correction_rejected=omitted_rejected))
    print(json.dumps(dict(status='PASS', cases=reports, solver_threads=1,
                          scope='Explicit small witnesses; independent exact replay; no general addition-optimality claim'), indent=2))


if __name__ == '__main__':
    main()
