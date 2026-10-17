"""Independent exact signed-circuit replay and finite-pool membership checks."""
from fractions import Fraction


def require_sign(value):
    assert type(value) is int and value in (-1, 1)
    return value


def at(values, index):
    assert type(index) is int and 0 <= index < len(values)
    return values[index]


def add(a, sa, b, sb):
    return tuple(sa*x + sb*y for x, y in zip(a, b))


def canonical(value):
    first = next((x for x in value if x), None)
    assert first is not None
    sign = 1 if first > 0 else -1
    return tuple(sign*x for x in value), sign


def replay(data, inputs):
    assert data['inputs'] == inputs
    values = [tuple(int(i == j) for j in range(inputs)) for i in range(inputs)]
    if 'gates' in data:
        for a, sa, b, sb in data['gates']:
            values.append(add(at(values, a), require_sign(sa),
                              at(values, b), require_sign(sb)))
        outputs = [tuple(require_sign(s)*x for x in at(values, o))
                   for o, s in data['outputs']]
        additions = len(data['gates'])
    else:
        assert data.get('modulus') is None
        additions = 0
        for node in data['nodes']:
            if node['op'] == 'add':
                values.append(add(at(values, node['a']), 1, at(values, node['b']), 1))
                additions += 1
            else:
                assert node['op'] == 'scale'
                coefficient = Fraction(node['c'])
                assert coefficient in (-1, 1)
                values.append(tuple(coefficient*x for x in at(values, node['a'])))
        outputs = [at(values, o) for o in data['outputs']]
    actual = [list(row) for row in outputs]
    if 'target_matrix' in data:
        assert data['target_matrix'] == actual
    return actual, additions, values


def check_pool(pool, donor_data, candidate, expected):
    n = pool['inputs']
    assert n == len(expected[0]) and pool['target_matrix'] == expected
    forms = list(map(tuple, pool['forms']))
    assert forms[:n] == [tuple(int(i == j) for j in range(n)) for i in range(n)]
    assert all(len(f) == n and any(f) for f in forms)
    assert len(set(forms)) == len(forms)
    assert all(next(x for x in f if x) > 0 for f in forms)
    index = {f: i for i, f in enumerate(forms)}
    assert donor_data['inputs'] == n
    supplied = set()
    for donor in donor_data['circuits']:
        actual, _, values = replay(donor, n)
        assert actual == expected
        supplied.update(canonical(v)[0] for v in values)
    assert supplied == set(forms), 'Pool forms differ from exact donor union'
    productions = pool['productions']
    relation_count = 0
    for out, options in productions.items():
        out = int(out)
        assert n <= out < len(forms)
        for a, sa, b, sb in options:
            assert out not in (a, b)
            assert add(at(forms, a), require_sign(sa),
                       at(forms, b), require_sign(sb)) == forms[out]
            relation_count += 1
    assert [[require_sign(s)*x for x in at(forms, o)]
            for o, s in pool['outputs']] == expected
    actual, cost, values = replay(candidate, n)
    assert actual == expected and 'gates' in candidate
    used = {}
    for wire, (a, sa, b, sb) in enumerate(candidate['gates'], n):
        out, so = canonical(values[wire])
        left, sl = canonical(values[a]); right, sr = canonical(values[b])
        oi, ai, bi = index[out], index[left], index[right]
        sa, sb = sa*so*sl, sb*so*sr
        if ai > bi:
            ai, bi, sa, sb = bi, ai, sb, sa
        production = [ai, sa, bi, sb]
        assert production in productions[str(oi)], 'Candidate gate absent from pool'
        assert oi not in used, 'Repeated canonical candidate gate'
        used[oi] = production
    selectors = candidate.get('pool_selection')
    if selectors is not None:
        assert {int(k): v for k, v in selectors.items()} == used
    incumbent = {int(k): v for k, v in pool['incumbent'].items()}
    done, pending = set(range(n)), set()

    def visit(wire):
        if wire in done:
            return
        assert wire not in pending and wire in incumbent
        pending.add(wire)
        production = incumbent[wire]
        assert production in productions[str(wire)]
        visit(production[0]); visit(production[2])
        pending.remove(wire); done.add(wire)

    for wire, _ in pool['outputs']:
        visit(wire)
    assert done-set(range(n)) == set(incumbent)
    return dict(status='PASS',inputs=n,outputs=len(expected),forms=len(forms),
                exact_relations=relation_count,donor_entries=len(donor_data['circuits']),
                kernel_candidate_additions=cost,signed_candidate_membership=True)
