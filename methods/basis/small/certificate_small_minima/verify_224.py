"""The retained224 witness attains a projective direction-count lower bound."""
from fractions import Fraction as Q
from pathlib import Path
import json
from verify_upper import matrix, rank, transpose, matmul

HERE=Path(__file__).resolve().parent
def projective(row):
    row=tuple(map(Q,row));v=next(x for x in row if x)
    return tuple(x/v for x in row)
def main():
    d=json.loads((HERE/'scheme224.json').read_text())
    result={};total=0
    for s in 'uvw':
        target=d['inner_forward'][s];dim=len(target[0])
        q=len({projective(row)for row in target});assert rank(target)==dim
        M,c=matrix(d['kernel'][s]);assert M==([[Q(x)for x in r]for r in target] if s!='w' else transpose(target))
        bound=q-dim+(d['source']['m']-dim if s=='w' else 0)
        assert c['additions']==bound
        result[s]={'target_directions':q,'dimension':dim,'attained_lower_bound':bound}
        total+=bound
    assert total==21
    out={'status':'PASS','kernel_minimum':total,'maps':result,
         'scope':'Selected rank14 decomposition; arbitrary rational entry bases and term gauges; direction bound also holds with free scalar weights.'}
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
