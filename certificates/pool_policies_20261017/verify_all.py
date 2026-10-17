#!/usr/bin/env python3
"""Independently verify literal SLPs, physical JSON and full tensors. Stdlib only."""
from pathlib import Path
import hashlib
import json
import sys
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
from verify_literal import read_sms, replay as replay_text
from verify_tensor import verify as verify_tensor


def physical_json(data, expected):
    n = data['inputs']
    assert type(n) is int and n == len(expected[0])
    values = [tuple(int(i == j) for j in range(n)) for i in range(n)]
    gates = data['gates']
    assert isinstance(gates, list)
    for gate in gates:
        assert isinstance(gate, list) and len(gate) == 4
        a, sa, b, sb = gate
        assert type(a) is type(b) is int and 0 <= a < len(values) and 0 <= b < len(values)
        assert type(sa) is type(sb) is int and sa in (-1, 1) and sb in (-1, 1)
        assert sa == 1 or sb == 1, 'Two negative operands would hide a unary negation'
        values.append(tuple(sa*x + sb*y for x, y in zip(values[a], values[b])))
    actual = []
    pending = []
    for wire, sign in data['outputs']:
        assert type(wire) is int and 0 <= wire < len(values)
        assert type(sign) is int and sign == 1, 'Output signs must already be paid'
        actual.append(list(values[wire])); pending.append(wire)
    used = set()
    while pending:
        wire = pending.pop()
        if wire < n or wire in used:
            continue
        used.add(wire)
        a, _, b, _ = gates[wire - n]
        pending.extend((a, b))
    assert used == set(range(n, len(values))), 'Unused physical gate'
    assert actual == expected, 'Physical JSON differs from original ordered signed map'
    return len(gates), values


def canonical(v):
    first = next((x for x in v if x), 0)
    assert first
    return tuple(x if first > 0 else -x for x in v)


def check_pool(pool, circuit, values):
    n = pool['inputs']; forms = pool['forms']; options = pool['productions']
    assert forms[:n] == [[int(i == j) for j in range(n)] for i in range(n)]
    assert all(len(row) == n and all(type(x) is int for x in row) for row in forms)
    assert len({tuple(v) for v in forms}) == len(forms)
    assert all(tuple(v) == canonical(v) for v in forms)
    for key, productions in options.items():
        out = int(key)
        assert n <= out < len(forms)
        for a, sa, b, sb in productions:
            assert all(type(x) is int for x in (a, sa, b, sb))
            assert 0 <= a < len(forms) and 0 <= b < len(forms)
            assert sa in (-1, 1) and sb in (-1, 1)
            assert [sa*x + sb*y for x, y in zip(forms[a], forms[b])] == forms[out]
    ids = {tuple(f): i for i, f in enumerate(forms)}
    assert all(canonical(v) in ids for v in values), 'A new vector entered the frozen pool'
    for wire, (a, sa, b, sb) in enumerate(circuit['gates'], n):
        out = ids[canonical(values[wire])]
        left, right = ids[canonical(values[a])], ids[canonical(values[b])]
        orientation = 1 if next(x for x in values[wire] if x) > 0 else -1
        left_orientation = 1 if next(x for x in values[a] if x) > 0 else -1
        right_orientation = 1 if next(x for x in values[b] if x) > 0 else -1
        sa, sb = sa*orientation*left_orientation, sb*orientation*right_orientation
        if left > right:
            left, right, sa, sb = right, left, sb, sa
        assert [left, sa, right, sb] in options[str(out)], 'A new production entered the frozen pool'


def main():
    manifest = json.loads((H/'MANIFEST.json').read_text())
    actual = {str(p.relative_to(H)) for p in H.rglob('*') if p.is_file()
              and p.name != 'MANIFEST.json' and '__pycache__' not in p.parts}
    assert actual == set(manifest['sha256']), 'Bundle file set differs from manifest'
    for name, digest in manifest['sha256'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert hashlib.sha256((H/name).read_bytes()).hexdigest() == digest, name
    claims = json.loads((H/'claims.json').read_text()); reports = []
    for claim in claims['schemes']:
        folder = H/claim['scheme']; counts = {}; previous = {}
        for factor in ('U', 'V', 'W'):
            matrix, matrix_sha = read_sms(folder/(factor+'.sms'))
            assert matrix_sha == claim['original_matrix_sha256'][factor]
            for subdir, wanted, recorded in [('', claim['counts'], counts),
                                             ('previous', claim['previous_counts'], previous)]:
                base = folder/subdir
                text_path = base/(factor+'.slp')
                actual, stats = replay_text(text_path.read_text(), len(matrix[0]))
                assert actual == matrix
                assert stats['unary_negations'] == stats['nonunit_scalars'] == stats['unused_noninput_assignments'] == 0
                circuit = json.loads((base/(factor+'.json')).read_text())
                cost, values = physical_json(circuit, matrix)
                assert cost == stats['binary_additions'] == wanted[factor]
                recorded[factor] = cost
                if not subdir and factor == 'V':
                    search = H/'search'/claim['case_id']
                    pool = json.loads((search/'pool.json').read_text())
                    assert hashlib.sha256((search/'pool.json').read_bytes()).hexdigest() == claim['derivation']['pool_sha256']
                    check_pool(pool, circuit, values)
                    assert pool['target_matrix'] == matrix
                    if (search/'prior_pool.json').exists():
                        prior = json.loads((search/'prior_pool.json').read_text())
                        old_forms = {tuple(v) for v in prior['forms']}
                        new_used = {canonical(v) for v in values} - old_forms
                        assert len(new_used) == claim['derivation']['used_forms_absent_prior_pool']
        tensor = verify_tensor(folder/'U.sms', folder/'V.sms', folder/'W.sms', *claim['dimensions'])
        assert tensor['rank'] == claim['rank']
        assert sum(counts.values()) == claim['total_additions']
        assert sum(previous.values()) == claim['previous_total_additions']
        assert sum(counts.values()) + tensor['rank'] == claim['total_scalar_operations']
        assert claim['basis_change'] is False and claim['multiplication_rank_unchanged'] is True
        reports.append(dict(scheme=claim['scheme'], rank=tensor['rank'], counts=counts,
            additions=sum(counts.values()), previous_additions=sum(previous.values()),
            scalar_operations=sum(counts.values())+tensor['rank'],
            exact_tensor_coefficients=tensor['exact_tensor_coefficients'],
            literal_slps_verified=6, physical_json_circuits_verified=6, status='PASS'))
    print(json.dumps(dict(status='PASS', schemes=reports,
        final_linear_maps=3*len(reports), previous_linear_maps=3*len(reports), tensor_identities=len(reports),
        arithmetic='exact rational text replay and independent exact integer JSON replay',
        scope=claims['scope']), indent=2))


if __name__ == '__main__':
    main()
