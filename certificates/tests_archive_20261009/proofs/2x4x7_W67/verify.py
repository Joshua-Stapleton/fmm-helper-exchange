#!/usr/bin/env python3
"""Check the attaining circuit and explicit directions in a fixed-map proof."""
from pathlib import Path
from fractions import Fraction
import hashlib,json,sys
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
from verify_literal import read_sms,replay

def main():
 proof=json.loads((H/'proof.json').read_text());a,sha=read_sms(H/'W.sms');assert sha==proof['source_sha256'];m,n=len(a),len(a[0]);assert (m,n)==(14,45)
 actual,counts=replay((H/'W.slp').read_text(),n);assert actual==a;assert counts['binary_additions']==67;assert counts['unary_negations']==counts['nonunit_scalars']==counts['unused_noninput_assignments']==0
 assert hashlib.sha256((H/'W.slp').read_bytes()).hexdigest()==proof['attaining_program_sha256']
 directions=set();used=0
 for column in zip(*a):
  first=next((x for x in column if x),None);assert first is not None;used+=1
  direction=tuple(x/first for x in column)
  if sum(bool(x) for x in direction)>1:directions.add(direction)
 expected={tuple(Fraction(x) for x in row) for row in proof['canonical_nonroot_targets']};assert expected==directions;assert len(expected)==len(proof['canonical_nonroot_targets'])==36
 lower=len(directions)+n-m;assert lower==proof['lower_bound']==proof['upper_bound']==67
 print(json.dumps(dict(status='PASS',source_sha256=sha,all_input_columns_used=used,noncoordinate_projective_target_directions=len(directions),exact_coefficient_identities=m*n,transpose_input_count=m,transpose_output_count=n,lower_bound=lower,attaining_additions=counts['binary_additions'],fixed_map_optimality_over_Q=True,scope='Only this fixed linear map, binary linear gates with free scalar copies; not all schemes or basis changes.'),indent=2))
if __name__=='__main__':main()
