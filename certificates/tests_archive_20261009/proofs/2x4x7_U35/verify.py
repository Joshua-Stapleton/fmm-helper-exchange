#!/usr/bin/env python3
"""Check the attaining circuit and explicit directions for the fixed U35 map."""
from pathlib import Path
from fractions import Fraction
import hashlib,json,sys
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
from verify_literal import read_sms,replay

def main():
 proof=json.loads((H/'proof.json').read_text());a,sha=read_sms(H/'U.sms');assert sha==proof['source_sha256'];m,n=len(a),len(a[0]);assert (m,n)==(45,8)
 actual,counts=replay((H/'U.slp').read_text(),n);assert actual==a;assert counts['binary_additions']==35;assert counts['unary_negations']==counts['nonunit_scalars']==counts['unused_noninput_assignments']==0
 assert hashlib.sha256((H/'U.slp').read_bytes()).hexdigest()==proof['attaining_program_sha256']
 directions=set()
 for row in a:
  if sum(bool(x) for x in row)<=1:continue
  first=next(x for x in row if x);directions.add(tuple(x/first for x in row))
 expected={tuple(Fraction(x) for x in row) for row in proof['row_noncoordinate_classes']};assert expected==directions;assert len(expected)==len(proof['row_noncoordinate_classes'])==35;assert proof['lower_bound']==proof['upper_bound']==35
 print(json.dumps(dict(status='PASS',source_sha256=sha,noncoordinate_projective_target_directions=len(directions),exact_coefficient_identities=m*n,lower_bound=35,attaining_additions=counts['binary_additions'],fixed_map_optimality_over_Q=True,scope='Only this fixed U map, binary linear gates with free scalar copies; not all schemes or basis changes.'),indent=2))
if __name__=='__main__':main()
