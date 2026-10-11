#!/usr/bin/env python3
"""Stdlib-only replay of six frozen adjoint donor banks and paid returns.

This checks exact integer maps and binary gate counts. Final literal signs and
the complete multiplication tensors are certified by the separate bundle.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text())


def read_sms(path):
    lines = [line.split() for line in path.read_text().splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    require(lines and len(lines[0]) == 3, 'Invalid SMS header')
    rows, columns = map(int, lines[0][:2])
    require(rows > 0 and columns > 0, 'Positive matrix dimensions required')
    target = [[0]*columns for _ in range(rows)]
    for fields in lines[1:]:
        require(len(fields) == 3, 'Invalid SMS entry')
        row, column, value = map(int, fields)
        if row == column == value == 0:
            continue
        require(1 <= row <= rows and 1 <= column <= columns, 'SMS index out of range')
        target[row-1][column-1] += value
    return target


def integer(value):
    return type(value) is int


def matrix(target):
    require(isinstance(target, list) and target and isinstance(target[0], list)
            and target[0], 'Nonempty matrix required')
    require(all(isinstance(row, list) and len(row) == len(target[0])
                and all(integer(x) for x in row) for row in target), 'Invalid integer matrix')


def transpose(target):
    matrix(target)
    return [list(row) for row in zip(*target)]


def gate(value, size):
    require(isinstance(value, list) and len(value) == 4, 'Invalid binary gate')
    a, sa, b, sb = value
    require(all(integer(x) for x in value) and 0 <= a < size and 0 <= b < size
            and sa in (-1, 1) and sb in (-1, 1), 'Invalid signed gate references')
    return a, sa, b, sb


def replay(candidate, target):
    matrix(target)
    n = len(target[0])
    require(candidate.get('inputs', n) == n and integer(candidate.get('inputs', n)),
            'Candidate input dimension mismatch')
    require(isinstance(candidate.get('gates'), list)
            and isinstance(candidate.get('outputs'), list), 'Invalid candidate schema')
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    for raw in candidate['gates']:
        a, sa, b, sb = gate(raw, len(values))
        values.append(tuple(sa*x+sb*y for x, y in zip(values[a], values[b])))
    actual = []
    active = set()

    def visit(wire):
        if wire < n or wire in active:
            return
        active.add(wire)
        a, _, b, _ = candidate['gates'][wire-n]
        visit(a)
        visit(b)

    for output in candidate['outputs']:
        require(isinstance(output, list) and len(output) == 2, 'Invalid output alias')
        wire, sign = output
        require(integer(wire) and 0 <= wire < len(values) and integer(sign)
                and sign in (-1, 1), 'Invalid signed output reference')
        actual.append([sign*x for x in values[wire]])
        visit(wire)
    require(actual == target, 'Candidate differs from exact ordered target')
    require(len(active) == len(candidate['gates']), 'Candidate has unused paid gates')
    if 'target_matrix' in candidate:
        require(candidate['target_matrix'] == target, 'Candidate target metadata differs')
    if 'additions_signed' in candidate:
        require(candidate['additions_signed'] == len(candidate['gates']), 'Candidate count metadata differs')
    return len(candidate['gates'])


def return_dag(candidate, original):
    """Construct every reverse accumulation, charging its binary gates.

    Signed aliases remain explicit; this is an integer circuit transposition,
    not an input basis conversion or a strict-sign feasibility claim.
    """
    target = transpose(original)
    replay(candidate, target)
    forward_inputs = len(target[0])
    reverse_inputs = len(candidate['outputs'])
    contributions = [[] for _ in range(forward_inputs+len(candidate['gates']))]
    for index, (wire, sign) in enumerate(candidate['outputs']):
        contributions[wire].append((index, sign))
    gates = []

    def accumulate(terms):
        require(terms, 'Adjoint has an unused wire or a zero column')
        wire, sign = terms[0]
        for other, coefficient in terms[1:]:
            gates.append([wire, sign, other, coefficient])
            wire, sign = reverse_inputs+len(gates)-1, 1
        return wire, sign

    for wire in range(len(contributions)-1, forward_inputs-1, -1):
        reverse_wire, reverse_sign = accumulate(contributions[wire])
        a, sa, b, sb = candidate['gates'][wire-forward_inputs]
        contributions[a].append((reverse_wire, reverse_sign*sa))
        contributions[b].append((reverse_wire, reverse_sign*sb))
    outputs = [list(accumulate(terms)) for terms in contributions[:forward_inputs]]
    result = dict(inputs=reverse_inputs, gates=gates, outputs=outputs)
    return replay(result, original)


def pool_check(pool, target, selection=None):
    n = len(target[0])
    require(pool['inputs'] == n and integer(pool['inputs']), 'Pool input dimension mismatch')
    require(pool['target_matrix'] == target, 'Pool target metadata differs')
    forms = pool['forms']
    matrix(forms)
    require(len(forms[0]) == n, 'Pool form dimension mismatch')
    require(forms[:n] == [[int(i == j) for j in range(n)] for i in range(n)],
            'Pool roots must be original unit inputs')
    require(len({tuple(row) for row in forms}) == len(forms), 'Duplicate pool forms')
    require(all(next((x for x in row if x), 0) > 0 for row in forms), 'Pool forms not sign canonical')
    productions = pool['productions']
    relation_count = 0
    for output_text, alternatives in productions.items():
        output = int(output_text)
        require(str(output) == output_text and n <= output < len(forms), 'Invalid relation output')
        require(isinstance(alternatives, list) and alternatives, 'Nonempty relation list required')
        require(len({tuple(raw) for raw in alternatives}) == len(alternatives), 'Duplicate pool relations')
        for raw in alternatives:
            a, sa, b, sb = gate(raw, len(forms))
            require([sa*x+sb*y for x, y in zip(forms[a], forms[b])] == forms[output],
                    'Pool relation fails exact integer identity')
            relation_count += 1
    for raw, row in zip(pool['outputs'], target):
        require(isinstance(raw, list) and len(raw) == 2, 'Invalid pool output alias')
        wire, sign = raw
        require(integer(wire) and 0 <= wire < len(forms) and integer(sign)
                and sign in (-1, 1), 'Invalid pool output reference')
        require([sign*x for x in forms[wire]] == row, 'Pool output differs from ordered target')
    require(len(pool['outputs']) == len(target), 'Pool output count differs')
    incumbent = pool['incumbent'] if selection is None else selection
    require(isinstance(incumbent, dict), 'Invalid pool selection')
    visited, visiting = set(), set()

    def visit(wire):
        if wire < n or wire in visited:
            return
        require(wire not in visiting, 'Cyclic pool incumbent')
        raw = incumbent.get(str(wire))
        require(raw is not None and raw in productions.get(str(wire), []), 'Missing incumbent production')
        visiting.add(wire)
        a, _, b, _ = gate(raw, len(forms))
        visit(a)
        visit(b)
        visiting.remove(wire)
        visited.add(wire)

    for wire, _ in pool['outputs']:
        visit(wire)
    require(visited == {int(wire) for wire in incumbent}, 'Unused incumbent production')
    return relation_count, len(visited)


def verify(directory=HERE):
    directory = Path(directory)
    manifest = load(directory/'MANIFEST.json')
    for relative, expected in manifest['files'].items():
        path = directory/relative
        require(path.is_file(), 'Missing frozen file: '+relative)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                'Frozen file hash mismatch: '+relative)
    reports = []
    for case in manifest['cases']:
        path = directory/case['directory']
        require(hashlib.sha256((path/'W.sms').read_bytes()).hexdigest() == case['source_W_sha256'],
                'Source W map hash differs')
        original = read_sms(path/'W.sms')
        target = transpose(original)
        bank = load(path/'donors.json')
        require(bank['inputs'] == len(target[0]), 'Bank input dimension mismatch')
        require(len(bank['circuits']) == case['donor_count'], 'Bank donor count differs')
        for candidate in bank['circuits']:
            replay(candidate, target)
        pool = load(path/'pool.json')
        relation_count, baseline_count = pool_check(pool, target)
        require(baseline_count == case['WT_baseline_additions'], 'Pool baseline count differs')
        require(replay(load(path/'WT_baseline.json'), target) == baseline_count,
                'Saved baseline count differs')
        selected = load(path/'WT_selected.json')
        selected_count = replay(selected, target)
        require(selected_count == case['WT_selected_additions'], 'Saved WT count differs')
        require('pool_selection' in selected, 'Selected candidate has no frozen pool witness')
        _, selection_count = pool_check(pool, target, selected['pool_selection'])
        require(selection_count == selected_count, 'Selected DAG cost differs from pool witness')
        returned_count = return_dag(selected, original)
        require(returned_count == case['final_W_additions'], 'Paid returned W count differs')
        final_count = replay(load(path/'W_final.json'), original)
        require(final_count == case['final_W_additions'], 'Final original W count differs')
        require(case['improved_in_extra'] == (case['final_W_additions'] < case['before_extra_W_additions']),
                'Improvement metadata differs')
        reports.append(dict(case=case['directory'], status='PASS',
                            exact_coefficient_identities_per_W=len(original)*len(original[0]),
                            adjoint_donors=len(bank['circuits']), exact_pool_relations=relation_count,
                            baseline_WT_additions=baseline_count, selected_WT_additions=selected_count,
                            paid_returned_W_additions=returned_count, final_original_W_additions=final_count,
                            improved_in_extra=case['improved_in_extra']))
    require(len(reports) == 6 and sum(row['improved_in_extra'] for row in reports) == 5,
            'Expected six extra passes and five improvements')
    return dict(status='PASS', cases=reports, all_gates_charged=True,
                basis_change=False, strict_sign_and_tensor_certificate='../../../../certificates/new_tests_20261011/README.txt',
                scope='Signed integer DAGs, all frozen relation identities, acyclic incumbents and paid adjoints. No relation-completeness, global optimality, timing or strict-sign claim from this verifier alone.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=HERE)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = verify(args.directory)
    text = json.dumps(report, indent=2)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
