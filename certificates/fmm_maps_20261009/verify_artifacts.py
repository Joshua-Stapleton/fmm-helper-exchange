"""Independent standard-library checks of signed programs and pool fixtures."""
from fractions import Fraction
import hashlib
import json


def sign(value):
    assert type(value) is int and value in (-1, 1)
    return value


def wire(index, values):
    assert type(index) is int and 0 <= index < len(values)
    return values[index]


def combine(left, a, right, b):
    return [a*x + b*y for x, y in zip(left, right)]


def circuit_matrix(data, n):
    assert data.get('inputs', n) == n
    values = [[int(i == j) for j in range(n)] for i in range(n)]
    if 'gates' in data:
        for a, sa, b, sb in data['gates']:
            values.append(combine(wire(a, values), sign(sa),
                                  wire(b, values), sign(sb)))
        return [[sign(s)*x for x in wire(o, values)]
                for o, s in data['outputs']]
    assert data.get('modulus') is None
    for node in data['nodes']:
        if node['op'] == 'add':
            values.append(combine(wire(node['a'], values), 1,
                                  wire(node['b'], values), 1))
        else:
            assert node['op'] == 'scale'
            coefficient = Fraction(node['c'])
            assert coefficient in (-1, 1)
            values.append([coefficient*x for x in wire(node['a'], values)])
    return [wire(o, values) for o in data['outputs']]


def raw_leo_matrix(data, n):
    values = [[int(i == j) for j in range(n)] for i in range(n)]
    for gate in data['substitutions']:
        values.append(combine(wire(gate['i'], values), sign(gate['ai']),
                              wire(gate['j'], values), sign(gate['aj'])))
    actual = []
    for terms in data['expressions']:
        assert terms
        row = [0]*n
        for term in terms:
            row = combine(row, 1, wire(term['index'], values), sign(term['value']))
        actual.append(row)
    count = len(data['substitutions']) + sum(len(t)-1 for t in data['expressions'])
    assert count == data['additions']
    return actual


def check_search_fixtures(home, matrices):
    reports = []
    for item in json.loads((home/'search/SEARCH.json').read_text()):
        pool_path = home/'search'/item['pool']
        pool = json.loads(pool_path.read_text())
        assert hashlib.sha256(pool_path.read_bytes()).hexdigest() == item['data_sha256']
        record = json.loads((home/'search'/item['record']).read_text())
        assert record['data_sha256'] == item['data_sha256']
        assert record['seed'] == item['seed']
        assert record['width_or_perturbation'] == item['width']
        assert record['budget_seconds'] == item['seconds']
        assert record['additions_signed'] == item['certified_additions']
        role = {'2414_V133': '2x4x14_V', '388_V173': '3x8x8_V',
                '368_V158': '3x6x8_V'}[item['name']]
        expected = matrices[role]
        assert pool['target_matrix'] == expected
        n = pool['inputs']
        assert n == len(expected[0])
        donors = json.loads((home/'search'/item['donors']).read_text())
        assert donors['inputs'] == n
        assert len(donors['circuits']) == item['donor_entries']
        for donor in donors['circuits']:
            assert circuit_matrix(donor, n) == expected
        forms = pool['forms']
        assert forms[:n] == [[int(i == j) for j in range(n)] for i in range(n)]
        assert all(len(f) == n and any(f) for f in forms)
        assert len({tuple(f) for f in forms}) == len(forms)
        assert all(next(x for x in f if x) > 0 for f in forms)
        productions = pool['productions']
        relation_count = 0
        for out, options in productions.items():
            out = int(out)
            assert n <= out < len(forms)
            for a, sa, b, sb in options:
                assert out not in (a, b)
                assert combine(wire(a, forms), sign(sa),
                               wire(b, forms), sign(sb)) == forms[out]
                relation_count += 1
        outputs = [[sign(s)*x for x in wire(o, forms)] for o, s in pool['outputs']]
        assert outputs == expected
        incumbent = {int(k): value for k, value in pool['incumbent'].items()}
        visited, pending = set(range(n)), set()

        def visit(index):
            if index in visited:
                return
            assert index not in pending and index in incumbent
            pending.add(index)
            gate = incumbent[index]
            assert gate in productions[str(index)]
            visit(gate[0]); visit(gate[2])
            pending.remove(index); visited.add(index)

        for o, _ in pool['outputs']:
            visit(o)
        assert visited-set(range(n)) == set(incumbent)
        reports.append(dict(name=item['name'], status='PASS',
                            exact_donor_entries=item['donor_entries'],
                            forms=len(forms), exact_production_relations=relation_count,
                            saved_incumbent_additions=len(incumbent),
                            certified_search_result=item['certified_additions']))
    return reports
