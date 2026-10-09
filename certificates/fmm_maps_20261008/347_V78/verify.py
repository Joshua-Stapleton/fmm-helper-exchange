#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H))
from verify_literal import read_sms,replay,source_stats
manifest=json.loads((H/'SHA256SUMS.json').read_text())
for name,expected in manifest.items():
    assert hashlib.sha256((H/name).read_bytes()).hexdigest()==expected, name
M,sha=read_sms(H/'V.sms')
assert sha=='2f43ebe13b7581a15465c564e63af33f77a2606e1d02382ceb0e83e8a37597fb'
actual,counts=replay((H/'V.slp').read_text(),28)
assert len(M)==64 and all(len(row)==28 for row in M)
assert actual==M,'Matrix mismatch'
assert counts==dict(binary_additions=78,unary_negations=0,nonunit_scalars=0,unused_noninput_assignments=0)
r=source_stats(M,sha)
r.update(status='PASS',exact_coefficient_identities=1792,counts=counts,basis_change=False)
print(json.dumps(r,indent=2))
