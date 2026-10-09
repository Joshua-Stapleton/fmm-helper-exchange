#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H))
from verify_literal import read_sms,replay,source_stats
manifest=json.loads((H/'SHA256SUMS.json').read_text())
for name,expected in manifest.items():
    assert hashlib.sha256((H/name).read_bytes()).hexdigest()==expected,name
M,sha=read_sms(H/'V.sms')
assert sha=='5e2021ac33b1b262c87c756911fda6593e7b18f30f4fc1e8ec5df56bda34f910'
actual,counts=replay((H/'V.slp').read_text(),64)
assert len(M)==310 and all(len(row)==64 for row in M)
assert actual==M,'Matrix mismatch'
assert counts=={'binary_additions': 401, 'unary_negations': 0, 'nonunit_scalars': 0, 'unused_noninput_assignments': 0}
r=source_stats(M,sha)
r.update(status='PASS',exact_coefficient_identities=19840,counts=counts,basis_change=False)
print(json.dumps(r,indent=2))
