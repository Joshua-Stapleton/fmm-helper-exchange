#!/usr/bin/env python3
"""Check all nine fixed linear maps and the complete 3x6x8 tensor exactly."""
from pathlib import Path
import hashlib
import json
import sys

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
from verify_literal import read_sms, replay
from verify_tensor import verify
from verify_artifacts import circuit_matrix, raw_leo_matrix, check_search_fixtures


def main():
    manifest = json.loads((H/'SHA256SUMS.json').read_text())
    for name, expected in manifest.items():
        assert hashlib.sha256((H/name).read_bytes()).hexdigest() == expected, name
    records = json.loads((H/'RESULTS.json').read_text())
    assert len(records) == 9
    reports = []
    matrices = {}
    for item in records:
        matrix, sha = read_sms(H/item['matrix'])
        matrices[item['name']] = matrix
        assert sha == item['source_sha256']
        assert circuit_matrix(json.loads((H/item['candidate']).read_text()), len(matrix[0])) == matrix
        actual, counts = replay((H/item['slp']).read_text(), len(matrix[0]))
        assert actual == matrix, item['name'] + ': coefficient mismatch'
        assert counts['binary_additions'] == item['additions']
        assert counts['unary_negations'] == counts['nonunit_scalars'] == 0
        assert counts['unused_noninput_assignments'] == 0
        reports.append(dict(name=item['name'],status='PASS',additions=item['additions'],
                            exact_coefficient_identities=len(matrix)*len(matrix[0]),
                            extra_negations=0,nonunit_scalars=0,basis_change=False))
    full = {item['factor']: H/item['matrix'] for item in records if item['scheme']=='3x6x8'}
    tensor = verify(full['U'],full['V'],full['W'],3,6,8)
    tensor['total_additions'] = sum(item['additions'] for item in records if item['scheme']=='3x6x8')
    tensor['total_scalar_operations'] = tensor['total_additions'] + tensor['rank']
    matrix,_=read_sms(H/'maps/3x6x8_m113_cr445_fv243_cn1240_ZT_reduced_V.sms')
    actual,counts=replay((H/'programs/3x6x8_V_pooled_alternative.slp').read_text(),48)
    assert actual==matrix and counts['binary_additions']==158
    assert counts['unary_negations']==counts['nonunit_scalars']==counts['unused_noninput_assignments']==0
    assert circuit_matrix(json.loads((H/'programs/3x6x8_V_pooled_alternative.json').read_text()),48)==matrix
    raw=json.loads((H/'method/cut_064.raw.json').read_text())
    assert raw_leo_matrix(raw,48)==matrix and raw['additions']==158
    searches=check_search_fixtures(H,matrices)
    tensor_checks = []
    for item in json.loads((H/'TENSORS.json').read_text()):
        report = verify(H/item['U'],H/item['V'],H/item['W'],*item['dimensions'])
        report['scheme'] = item['scheme']
        tensor_checks.append(report)
    print(json.dumps(dict(status='PASS',linear_maps=reports,full_tensor=tensor,
                          tensor_checks_with_corpus_completion=tensor_checks,
                          raw_witness_additions=raw['additions'],search_fixtures=searches),indent=2))


if __name__ == '__main__':
    main()
