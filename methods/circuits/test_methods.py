"""Portable controls for exact replay, basis transport and acyclic finite-pool synthesis."""
from pathlib import Path
import sys, json
from fractions import Fraction as Q
sys.path.insert(0,str(Path(__file__).resolve().parent))
from circuits import parse_slp, transpose
from lrp import inv,matmul
from transport import transport

A=[[1,1,0],[1,1,1],[0,1,-1]]
c=parse_slp('t0:=i0+i1; t1:=t0+i2; t2:=i1-i2; o0:=t0; o1:=t1; o2:=t2;'.replace('; ',';\n'),3,3)
assert c.check(A)['additions']==3
assert c.transposed().check(transpose(A))['additions']==3
assert inv([[2,1],[1,1]])==[[Q(1),Q(-1)],[Q(-1),Q(2)]]
assert inv([[2,0],[0,3]])==[[Q(1,2),Q(0)],[Q(0),Q(1,3)]]
old=[[1,1],[0,1]];new=[[1,0],[1,1]];forms=[[2,-1],[1,0]]
assert matmul(transport(forms,old,new),new)==matmul(forms,old)
try:parse_slp('t0:=i0+t1; t1:=i0+i1; o0:=t0;'.replace('; ',';\n'),2,1)
except (ValueError,KeyError,AssertionError):pass
else:raise AssertionError('forward reference accepted')
results={'linear_replay':'PASS','transpose':'PASS','fractional_inverse':'PASS','basis_transport':'PASS','invalid_dependency':'PASS'}
if '--solver' in sys.argv:
 from cp_pool import make_pool,solve
 from joint_basis import make_all_prods,solve_joint
 zero=parse_slp("o0:=i0-i0;",1,1)
 try:make_pool(zero,extra=0)
 except ValueError:pass
 else:raise AssertionError("zero target accepted")
 F,P,O,_=make_pool(c,extra=0)
 text,info=solve(F,P,O,3,3,10,workers=1)
 assert text and parse_slp(text,3,3).check(A)['additions']==3
 text2,info2=solve(F,P,O,3,2,10,workers=1)
 assert text2 is None and info2['status']=='INFEASIBLE'
 target=parse_slp('t0:=i0+i1; t1:=i0-i1; t2:=t0+t1; o0:=i0; o1:=i1; o2:=t0; o3:=t1; o4:=t2;'.replace('; ',';\n'),2,5)
 F,P,O,_=make_pool(target,0)
 text,B,info=solve_joint(F,make_all_prods(F),O,2,3,10)
 assert text is not None
 assert matmul(parse_slp(text,2,5).matrix(),B)==target.matrix()
 results['finite_pool_solver']='PASS';results['joint_basis_solver']='PASS'
print(json.dumps(results,indent=2))
