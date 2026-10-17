#!/usr/bin/env python3
"""Replay the frozen donor bank and published restart controls without dependencies."""
from pathlib import Path
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('vector_target_adapter', HERE/'toolchain/adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def load(path):
    return json.loads(Path(path).read_text())


def verify():
    bank = load(HERE/'benchmarks/manifest.json')
    assert len(bank['cases']) == 10
    total = 0
    for case in bank['cases']:
        target = load(HERE/case['matrix'])
        incumbent = load(HERE/case['candidate'])
        assert adapter.replay(incumbent, target) == case['local_signed_additions']
        donors = load(HERE/case['donors'])
        assert len(donors['circuits']) == case['donor_count']
        for donor in donors['circuits']:
            assert adapter.replay(donor, target) == len(donor['gates'])
            total += 1
    assert total == 185
    metadata = load(HERE/'toolchain/native_driver_v2.build.json')
    assert metadata['upstream_commit'] == adapter.PIN
    assert hashlib.sha256((HERE/'toolchain/native_driver.cpp').read_bytes()).hexdigest() == metadata['driver_sha256']
    control = load(HERE/'toolchain/bound_control.json')
    false_draw = next(x for x in control[0] if x['event'] == 'draw')
    true_draw = next(x for x in control[1] if x['event'] == 'draw')
    assert false_draw['solution'] is None
    assert adapter.replay(true_draw['solution'], [[1, 1, 1, 1, 0, 0]]) == 3
    study = load(HERE/'observed/native_main_report.json')
    assert study['status'] == 'COMPLETE' and len(study['results']) == 100
    assert study['exact_validation_failures'] == 0
    assert sum(r['completed'] for r in study['results']) == 8594
    assert not any(r['wrapper_killed'] for r in study['results'])
    spec = importlib.util.spec_from_file_location('vector_target_provenance', HERE/'pooling/trace_provenance.py')
    provenance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(provenance)
    base = load(HERE/'benchmarks/old_3x6x8_V/donors.json')['circuits']
    new = load(HERE/'observed/3x6x8_V155_donors.json')['circuits']
    candidate = load(HERE/'observed/3x6x8_V155_signed.json')
    assert adapter.replay(candidate, candidate['target_matrix']) == 155
    frozen_forms, frozen_recipes = set(), set()
    new_forms, new_recipes = [], set()
    for donor in base:
        _, forms, recipes = provenance.evaluate(donor, 48)
        frozen_forms.update(forms)
        frozen_recipes.update(recipes)
    for donor in new:
        adapter.replay(donor, candidate['target_matrix'])
        _, forms, recipes = provenance.evaluate(donor, 48)
        new_forms.append(forms)
        new_recipes.update(recipes)
    values, _, recipes = provenance.evaluate(candidate, 48)
    outputs = {provenance.canonical(v)[0] for v in candidate['target_matrix']}
    helpers = {provenance.canonical(v)[0] for v in values[48:]
               if sum(bool(x) for x in v) >= 2 and provenance.canonical(v)[0] not in outputs}
    novel = helpers-frozen_forms
    assert len(helpers) == 54 and len(novel) == 7
    incidence = [{i for i, forms in enumerate(new_forms) if v in forms} for v in sorted(novel)]
    assert all(incidence)
    assert all(not a & b for i, a in enumerate(incidence) for b in incidence[i+1:])
    # Seven disjoint nonempty incidence groups require seven donors to cover
    # these particular forms. This is not a circuit-size lower bound.
    assert sum(p not in frozen_recipes | new_recipes for p in recipes) == 7
    print(json.dumps(dict(status='PASS', cases=10, frozen_donors=total,
                          completed_native_draws=8594, native_api_source_pin=adapter.PIN,
                          optional_hint_bound_control='PASS',
                          pooled_witness=155, new_witness_helpers=7,
                          donor_cover_for_these_forms=7, new_witness_recipes=7)))


if __name__ == '__main__':
    verify()
