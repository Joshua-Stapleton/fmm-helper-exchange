#!/usr/bin/env python3
"""Verify 25 archive maps, two supplemental factors, nine tensors and proofs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
from verify_literal import read_sms, replay
from verify_tensor import verify as verify_tensor
from verify_signed import replay as replay_signed, check_pool
from direction_floor import analyze


def main():
    hashes = json.loads((H/'SHA256SUMS.json').read_text())
    for name, expected in hashes.items():
        assert hashlib.sha256((H/name).read_bytes()).hexdigest() == expected, name
    records = json.loads((H/'RESULTS.json').read_text())
    assert len(records) == 27 and len({d['name'] for d in records}) == 27
    assert sum(d['uploaded'] for d in records) == 25
    declared = {d['name']: d for d in records}
    matrices, map_reports = {}, []
    source_files = {d['name']: d for d in json.loads((H/'SOURCE_FILES.json').read_text())}
    floors = {d['name']: d for d in json.loads((H/'LOWER_BOUNDS.json').read_text())}
    for item in records:
        path = H/item['matrix']
        matrix, sha = read_sms(path)
        assert sha == item['source_sha256'] == source_files[item['name']]['source_sha256']
        assert source_files[item['name']]['uploaded'] == item['uploaded']
        actual, counts = replay((H/item['program']).read_text(), len(matrix[0]))
        assert actual == matrix, item['name'] + ': literal coefficient mismatch'
        assert counts['binary_additions'] == item['after']
        assert counts['unary_negations'] == counts['nonunit_scalars'] == 0
        assert counts['unused_noninput_assignments'] == 0
        assert hashlib.sha256((H/item['program']).read_bytes()).hexdigest() == item['program_sha256']
        signed, signed_count, _ = replay_signed(json.loads((H/item['candidate']).read_text()),len(matrix[0]))
        assert signed == matrix and signed_count == item['after']
        fresh = analyze(path)
        old = dict(floors[item['name']]); old.pop('name'); old.pop('uploaded')
        assert fresh == old
        assert fresh['addition_lower_bound'] <= item['after']
        matrices[item['name']] = matrix
        map_reports.append(dict(name=item['name'],uploaded=item['uploaded'],before=item['before'],
                                additions=item['after'],extra_negations=0,nonunit_scalars=0,
                                exact_coefficients=len(matrix)*len(matrix[0]),
                                fixed_map_direction_lower_bound=fresh['addition_lower_bound']))
    schemes = json.loads((H/'SCHEMES.json').read_text())
    assert len(schemes) == 9
    tensor_reports = []
    for scheme in schemes:
        members = {f: declared[scheme['factors'][f]] for f in ('U','V','W')}
        report = verify_tensor(*(H/members[f]['matrix'] for f in ('U','V','W')),
                               *scheme['dimensions'])
        assert report['rank'] == scheme['rank'] == scheme['scalar_products']
        assert sum(d['after'] for d in members.values()) == scheme['certified_additions']
        assert sum(d['before'] for d in members.values()) == scheme['original_additions']
        assert scheme['total_scalar_operations'] == scheme['certified_additions']+scheme['rank']
        report.update(name=scheme['name'],additions=scheme['certified_additions'],
                      products=scheme['rank'],total_operations=scheme['total_scalar_operations'])
        tensor_reports.append(report)
    assert [s['additions'] for s in tensor_reports] == [169,355,202,379,507,469,503,705,1408]
    pool_reports = []
    for item in json.loads((H/'SEARCH.json').read_text()):
        matrix = matrices[item['name']]
        expected = [list(row) for row in zip(*matrix)] if item['frame']=='transpose' else matrix
        pool = json.loads((H/item['pool']).read_text())
        assert hashlib.sha256((H/item['pool']).read_bytes()).hexdigest() == item['original_pool_sha256']
        report = check_pool(pool,json.loads((H/item['donors']).read_text()),
                            json.loads((H/item['kernel_candidate']).read_text()),expected)
        report.update(name=item['name'],frame=item['frame'],purpose=item['purpose'])
        pool_reports.append(report)
    proof_reports = []
    for leaf in ['2x4x7_U35','2x4x7_W67']:
        result = subprocess.run([sys.executable,'-I','-B',str(H/'proofs'/leaf/'verify.py')],
                                capture_output=True,text=True,check=True)
        report = json.loads(result.stdout)
        assert report['status'] == 'PASS' and report['fixed_map_optimality_over_Q']
        proof_reports.append(report)
    print(json.dumps(dict(status='PASS',original_archive_maps=25,supplemental_factors=2,
                          linear_maps=map_reports,schemes=tensor_reports,
                          signed_pool_membership=pool_reports,fixed_map_proofs=proof_reports),indent=2))


if __name__ == '__main__':
    main()
